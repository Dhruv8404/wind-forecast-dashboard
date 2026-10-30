from datetime import datetime, timedelta, timezone
from math import sqrt
from typing import Any, Dict, List, Optional


def parse_datetime(value: Any) -> Optional[datetime]:
    """Convert ISO datetime strings or datetime objects into normalized UTC datetimes."""
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        return dt.replace(second=0, microsecond=0)
    try:
        val_str = str(value).strip().replace("Z", "+00:00")
        result = datetime.fromisoformat(val_str)
        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone.utc)
        else:
            result = result.astimezone(timezone.utc)
        # Normalize seconds and microseconds so half-hourly settlement intervals align exactly
        return result.replace(second=0, microsecond=0)
    except (ValueError, TypeError):
        return None


def calculate_accuracy(
    actual_records: List[Dict[str, Any]],
    forecast_records: List[Dict[str, Any]],
    cutoff_hour: int = 10,
) -> Dict[str, Any]:
    """
    Compare actual wind generation against the latest eligible forecast published
    before the decision cutoff (default: cutoff_hour:00 UTC on the day before delivery).

    :param actual_records: List of metered outturn dicts (FUELHH).
    :param forecast_records: List of forecast dicts (WINDFOR).
    :param cutoff_hour: Cutoff hour in UTC on D-1 (e.g. 10 for 10:00 UTC D-1).
    :return: Dict containing count, MAE, RMSE, Bias, and matched interval rows.
    """
    actuals: Dict[datetime, float] = {}

    # Step 1: Prepare actual generation records (deduplicate by normalized start_time)
    for record in actual_records:
        start_time = parse_datetime(record.get("startTime"))
        generation = record.get("generation")
        if start_time is None or generation is None:
            continue
        try:
            actuals[start_time] = float(generation)
        except (ValueError, TypeError):
            continue

    # Step 2: Group forecasts by target delivery interval
    forecasts: Dict[datetime, List[Dict[str, Any]]] = {}
    for record in forecast_records:
        start_time = parse_datetime(record.get("startTime"))
        publish_time = parse_datetime(record.get("publishTime"))
        generation = record.get("generation")
        if start_time is None or publish_time is None or generation is None:
            continue
        try:
            gen_float = float(generation)
        except (ValueError, TypeError):
            continue
        forecasts.setdefault(start_time, []).append(
            {
                "publish_time": publish_time,
                "generation": gen_float,
            }
        )

    # Step 3: Match actuals with forecasts eligible prior to cutoff
    intervals: List[Dict[str, Any]] = []
    for start_time, actual in sorted(actuals.items()):
        # Decision cutoff: cutoff_hour:00:00 UTC on D-1
        cutoff = start_time.replace(
            hour=cutoff_hour,
            minute=0,
            second=0,
            microsecond=0,
        ) - timedelta(days=1)

        eligible = [
            item
            for item in forecasts.get(start_time, [])
            if item["publish_time"] <= cutoff
        ]
        if not eligible:
            continue

        # Select the latest forecast published on or before the cutoff
        selected = max(
            eligible,
            key=lambda item: item["publish_time"],
        )
        forecast = selected["generation"]
        error = forecast - actual
        intervals.append(
            {
                "startTime": start_time.isoformat(),
                "forecastPublishTime": selected["publish_time"].isoformat(),
                "forecast": forecast,
                "actual": actual,
                "error": round(error, 2),
                "absoluteError": round(abs(error), 2),
            }
        )

    # Step 4: Handle zero matched records
    if not intervals:
        return {
            "count": 0,
            "cutoff_hour": cutoff_hour,
            "mae": None,
            "rmse": None,
            "bias": None,
            "intervals": [],
            "message": "No matching forecast and actual records found for the specified cutoff.",
        }

    # Step 5: Calculate quantitative accuracy metrics
    errors = [item["forecast"] - item["actual"] for item in intervals]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = sqrt(sum(error**2 for error in errors) / len(errors))
    bias = sum(errors) / len(errors)

    return {
        "count": len(intervals),
        "cutoff_hour": cutoff_hour,
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "bias": round(bias, 2),
        "intervals": intervals,
    }
