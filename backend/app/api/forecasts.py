from datetime import date, datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.generation import ForecastsResponse
from app.services.elexon_client import ElexonClient, get_elexon_client
from app.services.forecast_service import ForecastService

router = APIRouter(prefix="/api/forecasts", tags=["Wind Forecasts"])


@router.get("", response_model=ForecastsResponse)
async def get_forecasts(
    from_date: Optional[date] = Query(
        None,
        alias="from_date",
        description="Target start date (YYYY-MM-DD). Defaults to 2 days ago.",
    ),
    to_date: Optional[date] = Query(
        None,
        alias="to_date",
        description="Target end date (YYYY-MM-DD). Defaults to today.",
    ),
    publish_from: Optional[datetime] = Query(
        None,
        description="Filter for forecasts published after this UTC timestamp.",
    ),
    publish_to: Optional[datetime] = Query(
        None,
        description="Filter for forecasts published before this UTC timestamp.",
    ),
    cutoff_hours: Optional[float] = Query(
        None,
        description="If specified, selects the latest forecast available X hours before the interval (e.g. 1.0 for Gate Closure).",
    ),
    client: ElexonClient = Depends(get_elexon_client),
):
    """
    Retrieve wind generation forecast data (WINDFOR).
    Preserves both publishTime and target startTime to ensure strict decision-cutoff filtering.
    """
    effective_to = to_date or date.today()
    effective_from = from_date or (effective_to - timedelta(days=2))

    if effective_from > effective_to:
        raise HTTPException(
            status_code=400,
            detail="from_date cannot be later than to_date",
        )

    try:
        raw_records = await client.fetch_windfor_forecasts(
            publish_from=publish_from,
            publish_to=publish_to,
            target_from_date=effective_from,
            target_to_date=effective_to,
        )

        start_bound = datetime(effective_from.year, effective_from.month, effective_from.day, 0, 0, tzinfo=timezone.utc)
        end_bound = datetime(effective_to.year, effective_to.month, effective_to.day, 23, 59, 59, tzinfo=timezone.utc)

        filtered = [
            r for r in raw_records
            if start_bound <= r.start_time <= end_bound
        ]

        if cutoff_hours is not None:
            filtered = ForecastService.select_forecasts_at_cutoff(
                filtered,
                cutoff_hours=cutoff_hours,
            )

        return ForecastsResponse(
            count=len(filtered),
            publish_from=publish_from,
            publish_to=publish_to,
            cutoff_hours=cutoff_hours,
            data=filtered,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch forecast data: {str(exc)}")
