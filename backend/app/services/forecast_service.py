from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.schemas.generation import ForecastGenerationRecord


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is timezone-aware and normalized to UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc, second=0, microsecond=0)
    return dt.astimezone(timezone.utc).replace(second=0, microsecond=0)


class ForecastService:
    """
    Selects valid forecasts adhering strictly to decision cutoffs.
    Distinguishes publishTime from startTime to prevent lookahead bias.
    """

    @staticmethod
    def select_forecasts_at_cutoff(
        forecasts: List[ForecastGenerationRecord],
        cutoff_hours: Optional[float] = None,
        day_ahead_cutoff_hour: Optional[int] = None,
        fixed_cutoff_time: Optional[datetime] = None,
        fallback_to_available: bool = False,
    ) -> List[ForecastGenerationRecord]:
        """
        For each forecasted target interval (startTime), select the latest forecast
        published prior to the specified decision cutoff.

        :param forecasts: Raw list of forecast records from WINDFOR.
        :param cutoff_hours: Hours prior to interval start (e.g. 1.0 for Gate Closure).
        :param day_ahead_cutoff_hour: UTC hour on D-1 (e.g. 10 for 10:00 UTC D-1).
        :param fixed_cutoff_time: Optional fixed absolute timestamp.
        :param fallback_to_available: If False (recommended), excludes intervals lacking eligible forecasts.
        :return: Deduplicated list of one selected forecast per target interval.
        """
        if not forecasts:
            return []

        # Group forecasts by normalized target start_time (UTC timestamp)
        forecasts_by_target: Dict[datetime, List[ForecastGenerationRecord]] = {}
        for f in forecasts:
            target = ensure_utc(f.start_time)
            if not target:
                continue
            pub = ensure_utc(f.publish_time) or (target - timedelta(hours=1))
            f.publish_time = pub
            f.start_time = target
            forecasts_by_target.setdefault(target, []).append(f)

        selected: List[ForecastGenerationRecord] = []

        for target_time, candidates in forecasts_by_target.items():
            if fixed_cutoff_time is not None:
                effective_cutoff = ensure_utc(fixed_cutoff_time)
            elif day_ahead_cutoff_hour is not None:
                effective_cutoff = target_time.replace(
                    hour=day_ahead_cutoff_hour, minute=0, second=0, microsecond=0
                ) - timedelta(days=1)
            elif cutoff_hours is not None:
                effective_cutoff = target_time - timedelta(hours=cutoff_hours)
            else:
                # Default: 10:00 UTC on the day before delivery (D-1)
                effective_cutoff = target_time.replace(
                    hour=10, minute=0, second=0, microsecond=0
                ) - timedelta(days=1)

            # Strict cutoff filter: candidates published on or before the cutoff
            valid_candidates = [
                c for c in candidates
                if c.publish_time is not None and c.publish_time <= effective_cutoff
            ]

            if valid_candidates:
                # Select the latest forecast available by cutoff
                best = max(valid_candidates, key=lambda c: c.publish_time)
                selected.append(best)
            elif fallback_to_available and candidates:
                # Only if explicitly allowed: select earliest candidate
                best = min(candidates, key=lambda c: c.publish_time)
                selected.append(best)

        selected.sort(key=lambda x: x.start_time)
        return selected
