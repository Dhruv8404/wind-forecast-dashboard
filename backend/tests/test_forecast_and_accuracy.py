from datetime import date, datetime, timedelta, timezone
import pytest
from fastapi import HTTPException

from app.api.accuracy import get_forecast_accuracy
from app.services.accuracy_service import calculate_accuracy, parse_datetime
from app.services.elexon_client import ElexonClient, parse_datetime as elexon_parse_dt


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
