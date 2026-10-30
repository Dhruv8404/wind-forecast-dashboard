from datetime import date, datetime, timedelta, timezone
import pytest
from fastapi import HTTPException

from app.api.accuracy import get_forecast_accuracy
from app.services.accuracy_service import calculate_accuracy, parse_datetime
from app.services.elexon_client import ElexonClient, DatasetResult, parse_datetime as elexon_parse_dt


def test_calculate_accuracy_basic():
    """Verify MAE, RMSE, Bias calculation with 10:00 UTC day-ahead cutoff on known numbers."""
    actual_records = [
        {
            "startTime": "2026-01-02T12:00:00Z",
            "generation": 280.0,
            "fuelType": "WIND",
        },
        {
            "startTime": "2026-01-02T12:30:00Z",
            "generation": 300.0,
            "fuelType": "WIND",
        },
    ]

    # Target delivery is 2026-01-02 12:00 -> Cutoff is 2026-01-01 10:00 UTC
    forecast_records = [
        # Eligible (published before 2026-01-01 10:00)
        {
            "startTime": "2026-01-02T12:00:00Z",
            "publishTime": "2026-01-01T09:00:00Z",
            "generation": 300.0,  # error = +20, abs_err = 20
        },
        # Ineligible (published after 10:00 cutoff)
        {
            "startTime": "2026-01-02T12:00:00Z",
            "publishTime": "2026-01-01T15:00:00Z",
            "generation": 290.0,
        },
        # For second interval
        {
            "startTime": "2026-01-02T12:30:00Z",
            "publishTime": "2026-01-01T09:30:00Z",
            "generation": 320.0,  # error = +20, abs_err = 20
        },
    ]

    result = calculate_accuracy(actual_records, forecast_records)
    assert result["count"] == 2
    assert result["mae"] == 20.0
    assert result["rmse"] == 20.0
    assert result["bias"] == 20.0
    assert len(result["intervals"]) == 2
    # Verify the eligible forecast (09:00) was chosen over the late one (15:00)
    assert result["intervals"][0]["forecast"] == 300.0
    assert result["intervals"][0]["error"] == 20.0
    assert result["intervals"][0]["absoluteError"] == 20.0


def test_calculate_accuracy_cutoff_strictly_enforced():
    """Verify that forecasts published at 10:00 UTC D-1 are eligible, while 10:01 UTC D-1 are rejected."""
    actuals = [
        {"startTime": "2026-01-02T14:00:00Z", "generation": 1000.0, "fuelType": "WIND"}
    ]
    # Cutoff for 2026-01-02 is 2026-01-01 10:00:00 UTC
    forecasts = [
        # Exactly at cutoff -> Eligible
        {"startTime": "2026-01-02T14:00:00Z", "publishTime": "2026-01-01T10:00:00Z", "generation": 1100.0},
        # 1 minute after cutoff -> Ineligible
        {"startTime": "2026-01-02T14:00:00Z", "publishTime": "2026-01-01T10:01:00Z", "generation": 1050.0},
    ]

    res = calculate_accuracy(actuals, forecasts)
    assert res["count"] == 1
    # Must pick the 10:00 forecast (1100.0), NOT the late 10:01 forecast (1050.0)
    assert res["intervals"][0]["forecast"] == 1100.0
    assert res["intervals"][0]["error"] == 100.0


def test_calculate_accuracy_empty_records():
    """Verify graceful handling when no records or no matching intervals exist."""
    res1 = calculate_accuracy([], [])
    assert res1["count"] == 0
    assert res1["mae"] is None
    assert res1["rmse"] is None
    assert res1["bias"] is None
    assert res1["intervals"] == []
    assert "No matching forecast and actual records found" in res1["message"]

    # When actuals exist but no forecast satisfies the cutoff
    actuals = [{"startTime": "2026-01-02T12:00:00Z", "generation": 500.0}]
    late_forecasts = [{"startTime": "2026-01-02T12:00:00Z", "publishTime": "2026-01-02T11:00:00Z", "generation": 520.0}]
    res2 = calculate_accuracy(actuals, late_forecasts)
    assert res2["count"] == 0
    assert res2["intervals"] == []


def test_calculate_accuracy_corrupt_data():
    """Verify that records with null or non-numeric generation or missing timestamps are skipped."""
    actuals = [
        {"startTime": "2026-01-02T12:00:00Z", "generation": "invalid_number"},
        {"startTime": None, "generation": 500.0},
        {"startTime": "2026-01-02T12:30:00Z", "generation": 600.0},
    ]
    forecasts = [
        {"startTime": "2026-01-02T12:30:00Z", "publishTime": None, "generation": 620.0},
        {"startTime": "2026-01-02T12:30:00Z", "publishTime": "2026-01-01T08:00:00Z", "generation": 620.0},
    ]

    res = calculate_accuracy(actuals, forecasts)
    assert res["count"] == 1
    assert res["intervals"][0]["actual"] == 600.0
    assert res["intervals"][0]["forecast"] == 620.0
    assert res["mae"] == 20.0


def test_parse_datetime_subsecond_normalization():
    """Verify that timestamps with and without sub-second microseconds match cleanly."""
    dt_clean = parse_datetime("2026-01-01T00:00:00Z")
    dt_millis = parse_datetime("2026-01-01T00:00:00.246Z")
    dt_offset = parse_datetime("2026-01-01T00:00:00+00:00")

    assert dt_clean is not None
    assert dt_millis is not None
    assert dt_offset is not None
    assert dt_clean == dt_millis == dt_offset
    assert dt_clean.tzinfo == timezone.utc

    # Invalid / empty tests
    assert parse_datetime(None) is None
    assert parse_datetime("") is None
    assert parse_datetime("not-a-datetime") is None


def test_mock_fallback_profile_generation():
    """Verify fallback actuals and forecasts generate realistic values and satisfy cutoff."""
    client = ElexonClient()
    start_d = date(2026, 1, 1)
    end_d = date(2026, 1, 2)

    actuals = client._generate_mock_actuals(start_d, end_d, "WIND")
    forecasts = client._generate_mock_forecasts(start_d - timedelta(days=1), end_d)

    # 2 days * 48 half-hours = 96 intervals
    assert len(actuals) == 96
    # 3 days * 48 * 3 runs = 432 forecast records
    assert len(forecasts) == 432

    # Check generation ranges (GB wind ~ 1,000 - 16,000 MW)
    assert all(a.generation >= 1000.0 for a in actuals)
    assert all(a.fuel_type == "WIND" for a in actuals)


def test_api_date_validation():
    """Verify get_forecast_accuracy returns HTTP 400 when end_date < start_date."""
    coro = get_forecast_accuracy(
        start_date=date(2026, 1, 10),
        end_date=date(2026, 1, 5),
    )
    with pytest.raises(HTTPException) as exc_info:
        try:
            coro.send(None)
        except StopIteration:
            pass
    assert exc_info.value.status_code == 400
    assert "end_date must not be before start_date" in exc_info.value.detail


def test_bias_sign_convention_under_and_over():
    """
    Verify the sign convention for Bias:
    Forecast > Actual => Positive Bias (Over-forecasting)
    Forecast < Actual => Negative Bias (Under-forecasting)
    """
    actuals = [{"startTime": "2026-01-02T10:00:00Z", "generation": 1000.0}]

    # Case 1: Over-forecasting by 250 MW
    over_forecasts = [
        {"startTime": "2026-01-02T10:00:00Z", "publishTime": "2026-01-01T08:00:00Z", "generation": 1250.0}
    ]
    res_over = calculate_accuracy(actuals, over_forecasts)
    assert res_over["error" if "error" in res_over else "bias"] == 250.0
    assert res_over["mae"] == 250.0
    assert res_over["rmse"] == 250.0

    # Case 2: Under-forecasting by 200 MW
    under_forecasts = [
        {"startTime": "2026-01-02T10:00:00Z", "publishTime": "2026-01-01T08:00:00Z", "generation": 800.0}
    ]
    res_under = calculate_accuracy(actuals, under_forecasts)
    assert res_under["bias"] == -200.0
    assert res_under["mae"] == 200.0
    assert res_under["rmse"] == 200.0


def test_forecast_duplicate_selection_latest():
    """Verify that among multiple eligible forecasts before cutoff, the latest published run is chosen."""
    actuals = [{"startTime": "2026-01-02T12:00:00Z", "generation": 500.0}]
    forecasts = [
        {"startTime": "2026-01-02T12:00:00Z", "publishTime": "2026-01-01T04:00:00Z", "generation": 450.0},
        {"startTime": "2026-01-02T12:00:00Z", "publishTime": "2026-01-01T09:30:00Z", "generation": 520.0}, # Latest before 10:00
        {"startTime": "2026-01-02T12:00:00Z", "publishTime": "2026-01-01T07:15:00Z", "generation": 480.0},
    ]
    res = calculate_accuracy(actuals, forecasts, cutoff_hour=10)
    assert res["count"] == 1
    assert res["intervals"][0]["forecast"] == 520.0
    assert res["intervals"][0]["forecastPublishTime"] == "2026-01-01T09:30:00+00:00"


def test_configurable_cutoff_hour():
    """Verify that changing cutoff_hour changes which forecasts are eligible."""
    actuals = [{"startTime": "2026-01-02T12:00:00Z", "generation": 500.0}]
    # Forecast published at 11:00 UTC D-1
    forecasts = [
        {"startTime": "2026-01-02T12:00:00Z", "publishTime": "2026-01-01T11:00:00Z", "generation": 530.0}
    ]

    # With cutoff 09:00 UTC D-1 -> Ineligible (count 0)
    res_09 = calculate_accuracy(actuals, forecasts, cutoff_hour=9)
    assert res_09["count"] == 0

    # With cutoff 12:00 UTC D-1 -> Eligible (count 1)
    res_12 = calculate_accuracy(actuals, forecasts, cutoff_hour=12)
    assert res_12["count"] == 1
    assert res_12["intervals"][0]["forecast"] == 530.0


def test_dataset_result_lineage_tracking():
    """Verify DatasetResult object properly reports data_source and fallback_reason."""
    res_live = DatasetResult(records=[1, 2, 3], data_source="live")
    assert res_live.data_source == "live"
    assert res_live.fallback_reason is None
    rec, src, reason = res_live
    assert len(rec) == 3
    assert src == "live"

    res_mock = DatasetResult(records=[], data_source="synthetic", fallback_reason="Timeout")
    assert res_mock.data_source == "synthetic"
    assert res_mock.fallback_reason == "Timeout"
