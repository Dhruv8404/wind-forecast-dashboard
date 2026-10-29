from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, Query
from app.services.elexon_client import (
    ElexonAPIError,
    fetch_dataset,
)
from app.services.accuracy_service import calculate_accuracy

router = APIRouter(
    prefix="/api/accuracy",
    tags=["Forecast Accuracy"],
)


@router.get("")
async def get_forecast_accuracy(
    start_date: date = Query(default=date(2026, 1, 1)),
    end_date: date = Query(default=date(2026, 1, 31)),
):
    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date must not be before start_date",
        )
    try:
        # Fetch actual wind generation.
        actual_records = await fetch_dataset(
            dataset="FUELHH",
            start_date=start_date,
            end_date=end_date,
        )
        # Fetch forecasts starting one day earlier,
        # because forecasts may be published before delivery.
        forecast_records = await fetch_dataset(
            dataset="WINDFOR",
            start_date=start_date - timedelta(days=1),
            end_date=end_date,
        )
        # Keep only wind actuals.
        wind_actuals = [
            record
            for record in actual_records
            if str(record.get("fuelType", "")).upper() == "WIND"
        ]
        result = calculate_accuracy(
            actual_records=wind_actuals,
            forecast_records=forecast_records,
        )
        return {
            "dataset": "FUELHH + WINDFOR",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "decision_cutoff": (
                "10:00 UTC on the day before delivery"
            ),
            **result,
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )
    except ElexonAPIError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )
