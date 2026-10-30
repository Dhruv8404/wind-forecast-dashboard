from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.actuals import router as actuals_router
from app.api.forecasts import router as forecasts_router
from app.api.accuracy import router as accuracy_router

app = FastAPI(
    title="Wind Forecast Intelligence API",
    description="API for UK national wind generation forecasts (WINDFOR), actuals (FUELHH), and day-ahead accuracy analysis",
    version="1.0.0",
)

# Configure CORS using environment-driven origin whitelist
allowed_origins = settings.ALLOWED_ORIGINS
allow_all = "*" in allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else allowed_origins,
    allow_credentials=False if allow_all else True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(actuals_router)
app.include_router(forecasts_router)
app.include_router(accuracy_router)


@app.get("/api/health", tags=["System"])
def health_check():
    """Health check endpoint to verify backend operational status and configuration."""
    return {
        "status": "healthy",
        "application": "Wind Forecast Intelligence API",
        "version": "1.0.0",
        "environment": settings.ENV,
        "elexon_base_url": settings.ELEXON_BASE_URL,
        "synthetic_fallback_enabled": settings.ALLOW_SYNTHETIC_FALLBACK,
        "default_cutoff_hour": settings.DEFAULT_CUTOFF_HOUR,
    }


@app.get("/api", tags=["System"])
def api_info():
    """Directory of available backend endpoints and configuration."""
    return {
        "message": "Wind Forecast Intelligence API is running",
        "environment": settings.ENV,
        "available_endpoints": [
            "/api/health",
            "/api/actuals",
            "/api/forecasts",
            "/api/accuracy",
            "/docs",
            "/openapi.json",
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=(settings.ENV == "development"))
