from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.generation import ActualsResponse
from app.services.elexon_client import ElexonClient, get_elexon_client

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
    client: ElexonClient = Depends(get_elexon_client),
):
    """Retrieve half-hourly generation outturn (FUELHH) for wind or other fuel types."""
    effective_to = to_date or date.today()
    effective_from = from_date or (effective_to - timedelta(days=2))

    if effective_from > effective_to:
        raise HTTPException(
            status_code=400,
            detail="from_date cannot be later than to_date",
        )

    try:
        records = await client.fetch_fuelhh_actuals(
            from_date=effective_from,
            to_date=effective_to,
            fuel_type=fuel_type,
        )
        return ActualsResponse(
            count=len(records),
            fuel_type=fuel_type.upper(),
            from_date=effective_from,
            to_date=effective_to,
            data=records,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch actual generation data: {str(exc)}")
