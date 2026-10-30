from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.schemas.generation import AccuracyReportResponse
from app.services.elexon_client import (
    ElexonAPIError,
    fetch_dataset,
)
from app.services.accuracy_service import calculate_accuracy
from app.config import settings

router = APIRouter(
    prefix="/api/accuracy",
    tags=["Forecast Accuracy"],
)


@router.get("", response_model=AccuracyReportResponse)
async def get_forecast_accuracy(
    start_date: date = Query(
        default=date(2026, 1, 1),
        description="First delivery date (YYYY-MM-DD)",
    ),
    end_date: date = Query(
        default=date(2026, 1, 31),
        description="Last delivery date (YYYY-MM-DD)",
    ),
    cutoff_hour: int = Query(
        default=settings.DEFAULT_CUTOFF_HOUR,
        ge=0,
        le=23,
        description="Day-ahead decision cutoff hour in UTC on the day before delivery (default: 10)",
    ),
    allow_fallback: Optional[bool] = Query(
        None,
        description="Override system default for synthetic fallback if Elexon API is offline.",
    ),
):
    """
    Compute quantitative forecast accuracy metrics (MAE, RMSE, Bias) comparing
    half-hourly wind outturn against forecasts strictly available before the day-ahead decision cutoff.
    """
    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date must not be before start_date",
        )

    try:
        # Fetch actual wind generation (FUELHH)
        actual_res = await fetch_dataset(
            dataset="FUELHH",
            start_date=start_date,
            end_date=end_date,
            allow_fallback=allow_fallback,
            fuel_type="WIND",
        )

        # Fetch forecasts (WINDFOR) starting 2 days earlier to capture runs published on D-2 or D-1
        forecast_res = await fetch_dataset(
            dataset="WINDFOR",
            start_date=start_date - timedelta(days=2),
            end_date=end_date,
            allow_fallback=allow_fallback,
        )

        # Keep only wind generation actuals
        wind_actuals = [
            record
            for record in actual_res.records
            if str(record.get("fuelType", "")).strip().upper() == "WIND"
        ]

        result = calculate_accuracy(
            actual_records=wind_actuals,
            forecast_records=forecast_res.records,
            cutoff_hour=cutoff_hour,
        )

        # Explicitly track whether the dataset contains synthetic fallback data
        data_source = (
            "synthetic"
            if (actual_res.data_source == "synthetic" or forecast_res.data_source == "synthetic")
            else "live"
        )
        fallback_reason = actual_res.fallback_reason or forecast_res.fallback_reason

        return AccuracyReportResponse(
            dataset="FUELHH + WINDFOR",
            data_source=data_source,
            fallback_reason=fallback_reason,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            decision_cutoff=f"{cutoff_hour:02d}:00 UTC on the day before delivery",
            cutoff_hour=cutoff_hour,
            count=result["count"],
            mae=result.get("mae"),
            rmse=result.get("rmse"),
            bias=result.get("bias"),
            message=result.get("message"),
            intervals=result.get("intervals", []),
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ElexonAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(exc)}")
