from datetime import date, datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.generation import ForecastsResponse
from app.services.elexon_client import ElexonClient, get_elexon_client, ElexonAPIError
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
    allow_fallback: Optional[bool] = Query(
        None,
        description="Override system default for synthetic fallback if Elexon API is offline.",
    ),
    client: ElexonClient = Depends(get_elexon_client),
):
    """
    Retrieve wind generation forecast data (WINDFOR).
    Preserves both publishTime and target startTime to ensure strict decision-cutoff filtering.
    """
    # Guard against direct function invocation where Query defaults are passed
    clean_from = from_date if isinstance(from_date, date) else None
    clean_to = to_date if isinstance(to_date, date) else None
    clean_pub_from = publish_from if isinstance(publish_from, datetime) else None
    clean_pub_to = publish_to if isinstance(publish_to, datetime) else None
    clean_cutoff = cutoff_hours if isinstance(cutoff_hours, (int, float)) else None
    clean_allow_fallback = allow_fallback if isinstance(allow_fallback, bool) else None

    effective_to = clean_to or date.today()
    effective_from = clean_from or (effective_to - timedelta(days=2))

    if effective_from > effective_to:
        raise HTTPException(
            status_code=400,
            detail="from_date cannot be later than to_date",
        )

    try:
        res = await client.fetch_windfor_forecasts(
            publish_from=clean_pub_from,
            publish_to=clean_pub_to,
            target_from_date=effective_from,
            target_to_date=effective_to,
            allow_fallback=clean_allow_fallback,
        )

        start_bound = datetime(effective_from.year, effective_from.month, effective_from.day, 0, 0, tzinfo=timezone.utc)
        end_bound = datetime(effective_to.year, effective_to.month, effective_to.day, 23, 59, 59, tzinfo=timezone.utc)

        filtered = [
            r for r in res.records
            if start_bound <= r.start_time <= end_bound
        ]

        if clean_cutoff is not None:
            filtered = ForecastService.select_forecasts_at_cutoff(
                filtered,
                cutoff_hours=clean_cutoff,
            )

        return ForecastsResponse(
            count=len(filtered),
            data_source=res.data_source,
            fallback_reason=res.fallback_reason,
            publish_from=clean_pub_from,
            publish_to=clean_pub_to,
            cutoff_hours=clean_cutoff,
            data=filtered,
        )
    except ElexonAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(exc)}")
