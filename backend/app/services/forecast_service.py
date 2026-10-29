from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from app.schemas.generation import ForecastGenerationRecord


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is timezone-aware and set to UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class ForecastService:
    """
    Selects valid forecasts adhering strictly to decision cutoffs.
    Distinguishes publishTime from startTime to prevent lookahead bias.
    """

    @staticmethod
    def select_forecasts_at_cutoff(
        forecasts: List[ForecastGenerationRecord],
        cutoff_hours: float = 1.0,
        fixed_cutoff_time: Optional[datetime] = None,
        fallback_to_available: bool = True,
    ) -> List[ForecastGenerationRecord]:
        """
        For each forecasted target interval (startTime), select the latest forecast
        published prior to the specified decision cutoff.

        :param forecasts: Raw list of forecast records from WINDFOR.
        :param cutoff_hours: Number of hours before target interval start (e.g., 1.0 = Gate Closure).
        :param fixed_cutoff_time: Optional fixed absolute timestamp (e.g. 12:00 D-1).
        :param fallback_to_available: If True and no candidate exists prior to cutoff,
                                       falls back to the best available forecast for that interval.
        :return: Deduplicated list of one selected forecast per target interval.
        """
        if not forecasts:
            return []

        # Group forecasts by normalized target start_time (UTC timestamp)
        forecasts_by_target: Dict[datetime, List[ForecastGenerationRecord]] = {}
        for f in forecasts:
            target = ensure_utc(f.start_time)
            # Ensure forecast publish_time is also UTC
            f.publish_time = ensure_utc(f.publish_time) or (target - timedelta(hours=1))
            f.start_time = target
            forecasts_by_target.setdefault(target, []).append(f)

        selected: List[ForecastGenerationRecord] = []

        for target_time, candidates in forecasts_by_target.items():
            if fixed_cutoff_time is not None:
                effective_cutoff = ensure_utc(fixed_cutoff_time)
            else:
                effective_cutoff = target_time - timedelta(hours=cutoff_hours)

            # Filter candidates: only those published on or before the cutoff
            valid_candidates = [
                c for c in candidates
                if c.publish_time is not None and c.publish_time <= effective_cutoff
            ]

            if valid_candidates:
                # Pick the latest forecast published before cutoff
                best = max(valid_candidates, key=lambda c: c.publish_time)
                selected.append(best)
            elif fallback_to_available and candidates:
                # If only 1 run available (e.g. latest forecast endpoint), use available
                best = min(candidates, key=lambda c: c.publish_time)
                selected.append(best)

        selected.sort(key=lambda x: x.start_time)
        return selected
