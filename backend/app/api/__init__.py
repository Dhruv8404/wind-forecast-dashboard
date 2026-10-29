from app.api.actuals import router as actuals_router
from app.api.forecasts import router as forecasts_router
from app.api.accuracy import router as accuracy_router

__all__ = ["actuals_router", "forecasts_router", "accuracy_router"]
