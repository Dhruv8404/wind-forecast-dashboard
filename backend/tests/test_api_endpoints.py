from datetime import date
from unittest.mock import patch
import pytest
from fastapi import HTTPException

from app.main import health_check, api_info
from app.api.actuals import get_actuals
from app.api.forecasts import get_forecasts
from app.api.accuracy import get_forecast_accuracy
from app.services.elexon_client import DatasetResult, ElexonClient


def run_coro(coro):
    """Run a coroutine synchronously without requiring socket loop initialization."""
    try:
        while True:
            coro.send(None)
    except StopIteration as e:
        return e.value


def test_api_health_endpoint():
    """Verify health_check() returns operational status and diagnostic metadata."""
    res = health_check()
    assert res["status"] == "healthy"
    assert res["application"] == "Wind Forecast Intelligence API"
    assert "version" in res
    assert "synthetic_fallback_enabled" in res
    assert "elexon_base_url" in res


def test_api_directory_endpoint():
    """Verify api_info() returns available endpoint directory."""
    res = api_info()
    assert "available_endpoints" in res
    assert "/api/accuracy" in res["available_endpoints"]
    assert "/api/actuals" in res["available_endpoints"]
    assert "/api/forecasts" in res["available_endpoints"]
    assert "/api/health" in res["available_endpoints"]


def test_api_actuals_date_validation():
    """Verify get_actuals raises HTTP 400 when from_date > to_date."""
    with pytest.raises(HTTPException) as exc:
        run_coro(get_actuals(
            from_date=date(2026, 1, 10),
            to_date=date(2026, 1, 5),
            client=ElexonClient(),
        ))
    assert exc.value.status_code == 400
    assert "from_date cannot be later than to_date" in exc.value.detail


def test_api_forecasts_date_validation():
    """Verify get_forecasts raises HTTP 400 when from_date > to_date."""
    with pytest.raises(HTTPException) as exc:
        run_coro(get_forecasts(
            from_date=date(2026, 1, 15),
            to_date=date(2026, 1, 2),
            client=ElexonClient(),
        ))
    assert exc.value.status_code == 400
    assert "from_date cannot be later than to_date" in exc.value.detail


def test_api_accuracy_date_validation():
    """Verify get_forecast_accuracy raises HTTP 400 when end_date < start_date."""
    with pytest.raises(HTTPException) as exc:
        run_coro(get_forecast_accuracy(
            start_date=date(2026, 1, 10),
            end_date=date(2026, 1, 2),
        ))
    assert exc.value.status_code == 400
    assert "end_date must not be before start_date" in exc.value.detail


def test_api_accuracy_success_response_schema():
    """
    Verify get_forecast_accuracy computes metrics, labels data_source as live,
    and returns typed AccuracyReportResponse structure.
    """
    client_inst = ElexonClient()
    start_d = date(2026, 1, 1)
    end_d = date(2026, 1, 2)

    actuals_mock = client_inst._generate_mock_actuals(start_d, end_d, "WIND")
    forecasts_mock = client_inst._generate_mock_forecasts(date(2025, 12, 30), end_d)

    actuals_dict = [
        {"startTime": a.start_time.isoformat(), "generation": a.generation, "fuelType": a.fuel_type}
        for a in actuals_mock
    ]
    forecasts_dict = [
        {"startTime": f.start_time.isoformat(), "publishTime": f.publish_time.isoformat(), "generation": f.generation}
        for f in forecasts_mock
    ]

    async def mock_fetch_dataset(dataset, start_date, end_date, allow_fallback=True, fuel_type="WIND"):
        if dataset == "FUELHH":
            return DatasetResult(actuals_dict, data_source="live")
        return DatasetResult(forecasts_dict, data_source="live")

    with patch("app.api.accuracy.fetch_dataset", side_effect=mock_fetch_dataset):
        res = run_coro(get_forecast_accuracy(
            start_date=start_d,
            end_date=end_d,
            cutoff_hour=10,
        ))
        assert res.dataset == "FUELHH + WINDFOR"
        assert res.data_source == "live"
        assert res.fallback_reason is None
        assert res.count == 96
        assert res.mae is not None and res.mae > 0
        assert res.rmse is not None and res.rmse > 0
        assert res.bias is not None
        assert len(res.intervals) == 96
        first = res.intervals[0]
        assert first.start_time is not None
        assert first.forecast > 0
        assert first.actual > 0


def test_api_accuracy_synthetic_fallback_labeled():
    """Verify that when synthetic fallback data is served, data_source is strictly labeled 'synthetic'."""
    client_inst = ElexonClient()
    start_d = date(2026, 1, 1)
    end_d = date(2026, 1, 1)

    actuals_mock = client_inst._generate_mock_actuals(start_d, end_d, "WIND")
    forecasts_mock = client_inst._generate_mock_forecasts(date(2025, 12, 31), end_d)

    actuals_dict = [
        {"startTime": a.start_time.isoformat(), "generation": a.generation, "fuelType": a.fuel_type}
        for a in actuals_mock
    ]
    forecasts_dict = [
        {"startTime": f.start_time.isoformat(), "publishTime": f.publish_time.isoformat(), "generation": f.generation}
        for f in forecasts_mock
    ]

    async def mock_fetch_dataset(dataset, start_date, end_date, allow_fallback=True, fuel_type="WIND"):
        return DatasetResult(
            actuals_dict if dataset == "FUELHH" else forecasts_dict,
            data_source="synthetic",
            fallback_reason="Elexon offline in test environment",
        )

    with patch("app.api.accuracy.fetch_dataset", side_effect=mock_fetch_dataset):
        res = run_coro(get_forecast_accuracy(
            start_date=start_d,
            end_date=end_d,
            cutoff_hour=10,
        ))
        assert res.data_source == "synthetic"
        assert res.fallback_reason == "Elexon offline in test environment"
        assert res.count == 48


def test_api_actuals_success_response():
    """Verify get_actuals returns ActualsResponse with proper fuel_type and count."""
    client_inst = ElexonClient()
    start_d = date(2026, 1, 1)
    end_d = date(2026, 1, 2)
    mock_actuals = client_inst._generate_mock_actuals(start_d, end_d, "WIND")

    async def mock_fetch_fuelhh(*args, **kwargs):
        return DatasetResult(mock_actuals, data_source="live")

    mock_client = ElexonClient()
    with patch.object(mock_client, "fetch_fuelhh_actuals", side_effect=mock_fetch_fuelhh):
        res = run_coro(get_actuals(
            from_date=start_d,
            to_date=end_d,
            fuel_type="WIND",
            client=mock_client,
        ))
        assert res.count == 96
        assert res.fuel_type == "WIND"
        assert res.data_source == "live"
        assert len(res.data) == 96


def test_api_forecasts_success_with_cutoff():
    """Verify get_forecasts filters candidates with cutoff_hours."""
    client_inst = ElexonClient()
    start_d = date(2026, 1, 1)
    end_d = date(2026, 1, 2)
    mock_forecasts = client_inst._generate_mock_forecasts(start_d, end_d)

    async def mock_fetch_windfor(*args, **kwargs):
        return DatasetResult(mock_forecasts, data_source="live")

    mock_client = ElexonClient()
    with patch.object(mock_client, "fetch_windfor_forecasts", side_effect=mock_fetch_windfor):
        res = run_coro(get_forecasts(
            from_date=start_d,
            to_date=end_d,
            cutoff_hours=1.0,
            client=mock_client,
        ))
        assert res.count > 0
        assert res.cutoff_hours == 1.0
        assert res.data_source == "live"
