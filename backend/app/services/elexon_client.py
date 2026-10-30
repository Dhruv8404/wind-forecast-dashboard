from datetime import date, datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Literal, Optional, Tuple
import httpx

from app.config import settings
from app.schemas.generation import ActualGenerationRecord, ForecastGenerationRecord

logger = logging.getLogger(__name__)


class ElexonAPIError(Exception):
    """Custom exception raised when an Elexon API request fails."""
    pass


class DatasetResult:
    """Container holding retrieved records along with lineage metadata."""
    def __init__(
        self,
        records: List[Any],
        data_source: Literal["live", "synthetic"] = "live",
        fallback_reason: Optional[str] = None,
    ):
        self.records = records
        self.data_source: Literal["live", "synthetic"] = data_source
        self.fallback_reason = fallback_reason

    def __iter__(self):
        return iter((self.records, self.data_source, self.fallback_reason))


def parse_datetime(val: Any) -> Optional[datetime]:
    """Convert ISO datetime strings or datetime objects to normalized UTC timezone-aware datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        dt = val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val.astimezone(timezone.utc)
        return dt.replace(second=0, microsecond=0)
    if isinstance(val, str):
        cleaned = val.strip()
        if not cleaned:
            return None
        cleaned = cleaned.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt.replace(second=0, microsecond=0)
        except Exception:
            return None
    return None


async def _fetch_dataset_chunk(
    dataset_name: str,
    chunk_start: date,
    chunk_end: date,
    client: httpx.AsyncClient,
    fuel_type: Optional[str] = "WIND",
) -> List[Dict[str, Any]]:
    """Fetch a single chunk of data (<= 6 days) from Elexon BMRS datasets API."""
    endpoint = f"{settings.ELEXON_BASE_URL}/datasets/{dataset_name}"

    # Elexon routing constraints:
    # WINDFOR accepts publishDateTimeFrom / publishDateTimeTo
    # FUELHH accepts settlementDateFrom / settlementDateTo and optional fuelType
    if dataset_name == "WINDFOR":
        from_dt = datetime(chunk_start.year, chunk_start.month, chunk_start.day, 0, 0, tzinfo=timezone.utc)
        to_dt = datetime(chunk_end.year, chunk_end.month, chunk_end.day, 23, 59, 59, tzinfo=timezone.utc)
        params = {
            "publishDateTimeFrom": from_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publishDateTimeTo": to_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    else:
        params = {
            "settlementDateFrom": chunk_start.isoformat(),
            "settlementDateTo": chunk_end.isoformat(),
        }
        if fuel_type:
            params["fuelType"] = fuel_type.strip().upper()

    logger.info(f"fetch_dataset: requesting {endpoint} with {params}")
    response = await client.get(
        endpoint,
        params=params,
        headers={"Accept": "application/json", "User-Agent": "WindForecastDashboard/2.0"},
    )
    response.raise_for_status()
    payload = response.json()
    items = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(items, list):
        return items
    return []


async def fetch_dataset(
    dataset: str,
    start_date: date,
    end_date: date,
    allow_fallback: Optional[bool] = None,
    fuel_type: Optional[str] = "WIND",
) -> DatasetResult:
    """
    Fetch raw records for FUELHH or WINDFOR from the official Elexon Insights Solution API.
    Chunks large date ranges into <= 6-day intervals to avoid Elexon's 7-day query ceiling.
    Explicitly tracks whether data came from live Elexon API or synthetic fallback.
    """
    if allow_fallback is None:
        allow_fallback = settings.ALLOW_SYNTHETIC_FALLBACK

    dataset_name = dataset.strip().upper()
    all_records: List[Dict[str, Any]] = []
    chunk_size_days = 6
    failure_reason: Optional[str] = None

    try:
        timeout_cfg = httpx.Timeout(settings.ELEXON_TIMEOUT, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout_cfg) as client:
            current_start = start_date
            while current_start <= end_date:
                current_end = min(current_start + timedelta(days=chunk_size_days), end_date)
                chunk_items = await _fetch_dataset_chunk(
                    dataset_name, current_start, current_end, client, fuel_type=fuel_type
                )
                all_records.extend(chunk_items)
                current_start = current_end + timedelta(days=1)

        if all_records:
            logger.info(f"Successfully retrieved {len(all_records)} {dataset_name} live records from Elexon")
            return DatasetResult(records=all_records, data_source="live")
        else:
            failure_reason = f"Elexon BMRS API returned 0 records for {dataset_name} ({start_date} to {end_date})"
            logger.warning(failure_reason)

    except Exception as exc:
        failure_reason = f"Elexon API connection error for {dataset_name}: {exc}"
        logger.warning(failure_reason)
        if not allow_fallback:
            raise ElexonAPIError(failure_reason) from exc

    if not allow_fallback:
        raise ElexonAPIError(failure_reason or f"No records returned for {dataset_name}")

    # Explicitly labeled synthetic fallback
    logger.info(f"Engaging synthetic fallback generator for {dataset_name} ({start_date} to {end_date}): {failure_reason}")
    mock_client = ElexonClient()
    if dataset_name == "FUELHH":
        mock_actuals = mock_client._generate_mock_actuals(start_date, end_date, fuel_type or "WIND")
        records = [
            {
                "dataset": "FUELHH",
                "startTime": a.start_time.isoformat(),
                "publishTime": a.publish_time.isoformat() if a.publish_time else None,
                "settlementDate": a.settlement_date.isoformat(),
                "settlementPeriod": a.settlement_period,
                "fuelType": a.fuel_type,
                "generation": a.generation,
            }
            for a in mock_actuals
        ]
        return DatasetResult(
            records=records,
            data_source="synthetic",
            fallback_reason=failure_reason,
        )
    elif dataset_name == "WINDFOR":
        mock_forecasts = mock_client._generate_mock_forecasts(start_date, end_date)
        records = [
            {
                "dataset": "WINDFOR",
                "startTime": f.start_time.isoformat(),
                "publishTime": f.publish_time.isoformat(),
                "settlementDate": f.settlement_date.isoformat() if f.settlement_date else None,
                "settlementPeriod": f.settlement_period,
                "generation": f.generation,
            }
            for f in mock_forecasts
        ]
        return DatasetResult(
            records=records,
            data_source="synthetic",
            fallback_reason=failure_reason,
        )
    return DatasetResult(records=[], data_source="synthetic", fallback_reason="Unknown dataset requested")


class ElexonClient:
    """Client for querying official Elexon BMRS API endpoints with resilience."""

    def __init__(
        self,
        base_url: str = settings.ELEXON_BASE_URL,
        timeout_seconds: float = settings.ELEXON_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds, connect=5.0)

    async def fetch_fuelhh_actuals(
        self,
        from_date: date,
        to_date: date,
        fuel_type: str = "WIND",
        allow_fallback: Optional[bool] = None,
    ) -> DatasetResult:
        """
        Fetch generation outturn from Elexon FUELHH.
        Filters for the specified fuel type (default: WIND).
        """
        result = await fetch_dataset(
            "FUELHH", from_date, to_date, allow_fallback=allow_fallback, fuel_type=fuel_type
        )
        records: List[ActualGenerationRecord] = []
        target_fuel = fuel_type.strip().upper()

        for item in result.records:
            item_fuel = str(item.get("fuelType", "")).strip().upper()
            if item_fuel == target_fuel:
                dt = parse_datetime(item.get("startTime"))
                if not dt:
                    continue
                period = int(item.get("settlementPeriod") or (((dt.hour * 60 + dt.minute) // 30) + 1))
                s_date = item.get("settlementDate") or dt.date()
                records.append(
                    ActualGenerationRecord(
                        publishTime=parse_datetime(item.get("publishTime")),
                        settlementDate=s_date,
                        settlementPeriod=period,
                        startTime=dt,
                        fuelType=item_fuel,
                        generation=float(item.get("generation", 0.0)),
                    )
                )

        if records:
            return DatasetResult(records, data_source=result.data_source, fallback_reason=result.fallback_reason)

        if not (allow_fallback if allow_fallback is not None else settings.ALLOW_SYNTHETIC_FALLBACK):
            raise ElexonAPIError(f"No {fuel_type} records returned from Elexon FUELHH endpoint")

        mock_actuals = self._generate_mock_actuals(from_date, to_date, fuel_type)
        return DatasetResult(
            mock_actuals,
            data_source="synthetic",
            fallback_reason=f"No matching {fuel_type} records found in FUELHH payload",
        )

    async def fetch_windfor_forecasts(
        self,
        publish_from: Optional[datetime] = None,
        publish_to: Optional[datetime] = None,
        target_from_date: Optional[date] = None,
        target_to_date: Optional[date] = None,
        allow_fallback: Optional[bool] = None,
    ) -> DatasetResult:
        """Fetch wind forecasts from WINDFOR dataset."""
        start_d = target_from_date or (date.today() - timedelta(days=2))
        end_d = target_to_date or date.today()

        result = await fetch_dataset("WINDFOR", start_d, end_d, allow_fallback=allow_fallback)
        records = self._parse_forecast_items(result.records)

        if records:
            return DatasetResult(records, data_source=result.data_source, fallback_reason=result.fallback_reason)

        if not (allow_fallback if allow_fallback is not None else settings.ALLOW_SYNTHETIC_FALLBACK):
            raise ElexonAPIError("No forecast records returned from Elexon WINDFOR endpoint")

        mock_forecasts = self._generate_mock_forecasts(start_d, end_d)
        return DatasetResult(
            mock_forecasts,
            data_source="synthetic",
            fallback_reason="No valid forecast records in WINDFOR payload",
        )

    @staticmethod
    def _parse_forecast_items(items: Any) -> List[ForecastGenerationRecord]:
        """Extract and normalize forecast items into ForecastGenerationRecord."""
        records: List[ForecastGenerationRecord] = []
        if not isinstance(items, list):
            return records

        for item in items:
            gen_val = item.get("generation") or item.get("quantity") or item.get("value")
            start_raw = item.get("startTime") or item.get("targetTime")
            if gen_val is not None and start_raw:
                target_time = parse_datetime(start_raw)
                if not target_time:
                    continue

                pub_time = parse_datetime(item.get("publishTime"))
                if not pub_time:
                    pub_time = target_time - timedelta(hours=1)

                period = item.get("settlementPeriod")
                if not period or not (1 <= int(period) <= 50):
                    period = ((target_time.hour * 60 + target_time.minute) // 30) + 1

                records.append(
                    ForecastGenerationRecord(
                        publishTime=pub_time,
                        startTime=target_time,
                        settlementDate=item.get("settlementDate") or target_time.date(),
                        settlementPeriod=int(period),
                        generation=float(gen_val),
                    )
                )
        return records

    @staticmethod
    def _generate_mock_actuals(from_date: date, to_date: date, fuel_type: str = "WIND") -> List[ActualGenerationRecord]:
        """Generate realistic GB wind generation profile (~3,000 - 16,000 MW) across 48 periods/day."""
        import math
        records: List[ActualGenerationRecord] = []
        cur_date = from_date
        while cur_date <= to_date:
            base_trend = 11000.0 + 3000.0 * math.sin((cur_date.toordinal() % 7) * 0.9)
            for period in range(1, 49):
                hour = (period - 1) // 2
                minute = 30 * ((period - 1) % 2)
                dt = datetime(cur_date.year, cur_date.month, cur_date.day, hour, minute, tzinfo=timezone.utc)
                diurnal = 2500.0 * math.cos(2 * math.pi * (period - 6) / 48)
                noise = 500.0 * math.sin(period * 0.7)
                mw = max(1000.0, base_trend + diurnal + noise)
                records.append(
                    ActualGenerationRecord(
                        publishTime=dt + timedelta(minutes=45),
                        settlementDate=cur_date,
                        settlementPeriod=period,
                        startTime=dt,
                        fuelType=fuel_type,
                        generation=round(mw, 1),
                    )
                )
            cur_date += timedelta(days=1)
        return records

    @staticmethod
    def _generate_mock_forecasts(from_date: date, to_date: date) -> List[ForecastGenerationRecord]:
        """
        Generate multiple forecast runs (Day-Ahead at 08:30 D-1, 4h-ahead, 1h-ahead)
        preserving distinct publishTime and target startTime.
        """
        import math
        records: List[ForecastGenerationRecord] = []
        cur_date = from_date
        while cur_date <= to_date:
            base_trend = 11000.0 + 3000.0 * math.sin((cur_date.toordinal() % 7) * 0.9)
            for period in range(1, 49):
                hour = (period - 1) // 2
                minute = 30 * ((period - 1) % 2)
                target_dt = datetime(cur_date.year, cur_date.month, cur_date.day, hour, minute, tzinfo=timezone.utc)
                actual_approx = max(1000.0, base_trend + 2500.0 * math.cos(2 * math.pi * (period - 6) / 48) + 500.0 * math.sin(period * 0.7))

                # 1) Day-ahead published at 08:30 UTC previous day (strictly before 10:00 UTC cutoff)
                da_publish = datetime(cur_date.year, cur_date.month, cur_date.day, 8, 30, tzinfo=timezone.utc) - timedelta(days=1)
                da_gen = actual_approx + 600.0 * math.sin(period * 0.4) + 120.0
                records.append(
                    ForecastGenerationRecord(
                        publishTime=da_publish,
                        startTime=target_dt,
                        settlementDate=cur_date,
                        settlementPeriod=period,
                        generation=round(max(500.0, da_gen), 1),
                    )
                )

                # 2) 4-hours ahead forecast
                four_h_publish = target_dt - timedelta(hours=4)
                four_h_gen = actual_approx + 250.0 * math.sin(period * 0.5) + 50.0
                records.append(
                    ForecastGenerationRecord(
                        publishTime=four_h_publish,
                        startTime=target_dt,
                        settlementDate=cur_date,
                        settlementPeriod=period,
                        generation=round(max(500.0, four_h_gen), 1),
                    )
                )

                # 3) 1-hour ahead (Gate Closure) forecast
                one_h_publish = target_dt - timedelta(hours=1)
                one_h_gen = actual_approx + 90.0 * math.sin(period * 0.6) + 10.0
                records.append(
                    ForecastGenerationRecord(
                        publishTime=one_h_publish,
                        startTime=target_dt,
                        settlementDate=cur_date,
                        settlementPeriod=period,
                        generation=round(max(500.0, one_h_gen), 1),
                    )
                )

            cur_date += timedelta(days=1)
        return records


def get_elexon_client() -> ElexonClient:
    """Dependency provider for ElexonClient."""
    return ElexonClient()
