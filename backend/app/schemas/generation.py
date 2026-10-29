from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ActualGenerationRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    dataset: str = "FUELHH"
    publish_time: Optional[datetime] = Field(None, alias="publishTime", description="When outturn was published")
    settlement_date: date = Field(..., alias="settlementDate", description="Settlement date (YYYY-MM-DD)")
    settlement_period: int = Field(..., alias="settlementPeriod", ge=1, le=50, description="Half-hour settlement period (1-50)")
    start_time: datetime = Field(..., alias="startTime", description="Start timestamp of the settlement period (UTC)")
    fuel_type: str = Field("WIND", alias="fuelType", description="Fuel type category")
    generation: float = Field(..., description="Actual generation in Megawatts (MW)")


class ForecastGenerationRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    dataset: str = "WINDFOR"
    publish_time: datetime = Field(..., alias="publishTime", description="When the forecast was published by ESO (UTC)")
    start_time: datetime = Field(..., alias="startTime", description="Target settlement start timestamp (UTC)")
    settlement_date: Optional[date] = Field(None, alias="settlementDate", description="Target settlement date")
    settlement_period: Optional[int] = Field(None, alias="settlementPeriod", ge=1, le=50, description="Target settlement period")
    generation: float = Field(..., description="Forecasted wind generation in Megawatts (MW)")


class AlignedForecastActual(BaseModel):
    start_time: datetime = Field(..., description="Target settlement interval start time (UTC)")
    settlement_date: date = Field(..., description="Settlement date")
    settlement_period: int = Field(..., description="Settlement period (1-50)")
    actual_generation_mw: float = Field(..., description="Actual wind generation (MW)")
    forecast_generation_mw: float = Field(..., description="Selected forecast wind generation (MW)")
    forecast_publish_time: datetime = Field(..., description="Timestamp when selected forecast was published (UTC)")
    error_mw: float = Field(..., description="Forecast Error = Forecast - Actual (MW)")
    abs_error_mw: float = Field(..., description="Absolute Error = |Forecast - Actual| (MW)")
    percent_error: Optional[float] = Field(None, description="Percentage error relative to actual")


class AccuracyMetrics(BaseModel):
    sample_count: int = Field(..., description="Number of aligned settlement intervals evaluated")
    mae: float = Field(..., description="Mean Absolute Error in MW (lower is better)")
    rmse: float = Field(..., description="Root Mean Squared Error in MW (penalizes large misses)")
    bias: float = Field(..., description="Mean Error in MW (positive = over-forecast, negative = under-forecast)")
    mape: Optional[float] = Field(None, description="Mean Absolute Percentage Error (%)")
    max_error_mw: float = Field(..., description="Maximum absolute error observed in MW")
    actual_mean_mw: float = Field(..., description="Average actual wind generation across period in MW")
    forecast_mean_mw: float = Field(..., description="Average forecast wind generation across period in MW")


class ActualsResponse(BaseModel):
    count: int
    fuel_type: str = "WIND"
    from_date: date
    to_date: date
    data: List[ActualGenerationRecord]


class ForecastsResponse(BaseModel):
    count: int
    publish_from: Optional[datetime] = None
    publish_to: Optional[datetime] = None
    cutoff_hours: Optional[float] = None
    data: List[ForecastGenerationRecord]


class AccuracyResponse(BaseModel):
    from_date: date
    to_date: date
    cutoff_hours: float
    metrics: AccuracyMetrics
    data_points: List[AlignedForecastActual]
