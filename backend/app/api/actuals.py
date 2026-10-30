from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.generation import ActualsResponse
from app.services.elexon_client import ElexonClient, get_elexon_client, ElexonAPIError

router = APIRouter(prefix="/api/actuals", tags=["Actual Generation"])


@router.get("", response_model=ActualsResponse)
async def get_actuals(
    from_date: Optional[date] = Query(
        None,
        alias="from_date",
        description="Start date for actuals (YYYY-MM-DD). Defaults to 2 days ago.",
    ),
    to_date: Optional[date] = Query(
        None,
        alias="to_date",
        description="End date for actuals (YYYY-MM-DD). Defaults to today.",
    ),
    fuel_type: str = Query("WIND", description="Fuel type category (default: WIND)"),
    allow_fallback: Optional[bool] = Query(
        None,
        description="Override system default for synthetic fallback if Elexon API is offline.",
    ),
    client: ElexonClient = Depends(get_elexon_client),
):
    """Retrieve half-hourly generation outturn (FUELHH) for wind or other fuel types."""
    clean_from = from_date if isinstance(from_date, date) else None
    clean_to = to_date if isinstance(to_date, date) else None
    clean_fuel = fuel_type if isinstance(fuel_type, str) else "WIND"
    clean_fallback = allow_fallback if isinstance(allow_fallback, bool) else None

    effective_to = clean_to or date.today()
    effective_from = clean_from or (effective_to - timedelta(days=2))

    if effective_from > effective_to:
        raise HTTPException(
            status_code=400,
            detail="from_date cannot be later than to_date",
        )

    try:
        res = await client.fetch_fuelhh_actuals(
            from_date=effective_from,
            to_date=effective_to,
            fuel_type=clean_fuel,
            allow_fallback=clean_fallback,
        )
        return ActualsResponse(
            count=len(res.records),
            data_source=res.data_source,
            fallback_reason=res.fallback_reason,
            fuel_type=clean_fuel.upper(),
            from_date=effective_from,
            to_date=effective_to,
            data=res.records,
        )
    except ElexonAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(exc)}")
