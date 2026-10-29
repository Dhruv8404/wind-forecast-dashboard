from datetime import datetime, timedelta, timezone
from math import sqrt


def parse_datetime(value):
    """Convert ISO datetime strings into UTC datetimes normalized to second precision."""
    if not value:
        return None
    try:
        result = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone.utc)
        # Normalize seconds and microseconds so half-hourly settlement intervals match exactly
        return result.astimezone(timezone.utc).replace(second=0, microsecond=0)
    except (ValueError, TypeError):
        return None


def calculate_accuracy(actual_records, forecast_records):
    """
    Compare actual wind generation against the latest eligible forecast.
    Assumption: The purchasing decision is made at 10:00 UTC on the day before delivery.
    """
    actuals = {}

    # Step 1: Prepare actual generation records.
    for record in actual_records:
        start_time = parse_datetime(record.get("startTime"))
        generation = record.get("generation")
        if start_time is None or generation is None:
            continue
        try:
            actuals[start_time] = float(generation)
        except (ValueError, TypeError):
            continue

    # Step 2: Group forecasts by delivery interval.
    forecasts = {}
    for record in forecast_records:
        start_time = parse_datetime(record.get("startTime"))
        publish_time = parse_datetime(record.get("publishTime"))
        generation = record.get("generation")
        if (
            start_time is None or publish_time is None or generation is None
        ):
            continue
        try:
            generation = float(generation)
        except (ValueError, TypeError):
            continue
        forecasts.setdefault(start_time, []).append(
            {
                "publish_time": publish_time,
                "generation": generation,
            }
        )

    # Step 3: Match actuals with forecasts available at the cutoff.
    intervals = []
    for start_time, actual in sorted(actuals.items()):
        cutoff = (
            start_time.replace(
                hour=10,
                minute=0,
                second=0,
                microsecond=0,
            )
            - timedelta(days=1)
        )
        eligible = [
            item
            for item in forecasts.get(start_time, [])
            if item["publish_time"] <= cutoff
        ]
        if not eligible:
            continue
        # Select the latest forecast published before the cutoff.
        selected = max(
            eligible,
            key=lambda item: item["publish_time"],
        )
        forecast = selected["generation"]
        error = forecast - actual
        intervals.append(
            {
                "startTime": start_time.isoformat(),
                "forecastPublishTime": (
                    selected["publish_time"].isoformat()
                ),
                "forecast": forecast,
                "actual": actual,
                "error": round(error, 2),
                "absoluteError": round(abs(error), 2),
            }
        )

    # Step 4: Handle the case where no records match.
    if not intervals:
        return {
            "count": 0,
            "mae": None,
            "rmse": None,
            "bias": None,
            "intervals": [],
            "message": "No matching forecast and actual records found.",
        }

    # Step 5: Calculate accuracy metrics.
    errors = [item["forecast"] - item["actual"] for item in intervals]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = sqrt(sum(error**2 for error in errors) / len(errors))
    bias = sum(errors) / len(errors)

    return {
        "count": len(intervals),
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "bias": round(bias, 2),
        "intervals": intervals,
    }
