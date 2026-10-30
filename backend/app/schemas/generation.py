from datetime import date, datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class ActualGenerationRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    dataset: str = "FUELHH"
    publish_time: Optional[datetime] = Field(None, alias="publishTime", description="When outturn was published (UTC)")
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


class MatchedIntervalRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    start_time: datetime = Field(..., alias="startTime", description="Settlement interval start time (UTC)")
    forecast_publish_time: Optional[datetime] = Field(None, alias="forecastPublishTime", description="When selected forecast was published (UTC)")
    forecast: float = Field(..., description="Selected forecast generation (MW)")
    actual: float = Field(..., description="Actual metered outturn (MW)")
    error: float = Field(..., description="Forecast error = Forecast - Actual (MW)")
    absolute_error: float = Field(..., alias="absoluteError", description="Absolute forecast error |Forecast - Actual| (MW)")


class ActualsResponse(BaseModel):
    count: int
    data_source: Literal["live", "synthetic"] = "live"
    fallback_reason: Optional[str] = None
    fuel_type: str = "WIND"
    from_date: date
    to_date: date
    data: List[ActualGenerationRecord]


class ForecastsResponse(BaseModel):
    count: int
    data_source: Literal["live", "synthetic"] = "live"
    fallback_reason: Optional[str] = None
    publish_from: Optional[datetime] = None
    publish_to: Optional[datetime] = None
    cutoff_hours: Optional[float] = None
    data: List[ForecastGenerationRecord]


class AccuracyReportResponse(BaseModel):
    dataset: str = "FUELHH + WINDFOR"
    data_source: Literal["live", "synthetic"] = "live"
    fallback_reason: Optional[str] = None
    start_date: str
    end_date: str
    decision_cutoff: str
    cutoff_hour: int = 10
    count: int
    mae: Optional[float] = None
    rmse: Optional[float] = None
    bias: Optional[float] = None
    message: Optional[str] = None
    intervals: List[MatchedIntervalRecord] = Field(default_factory=list)


# Export aliases for backward compatibility
AccuracyResponse = AccuracyReportResponse
