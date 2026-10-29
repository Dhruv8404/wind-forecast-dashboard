from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.actuals import router as actuals_router
from app.api.forecasts import router as forecasts_router
from app.api.accuracy import router as accuracy_router

app = FastAPI(
    title="Wind Forecast Intelligence API",
    description="API for UK wind generation forecasts (WINDFOR), actuals (FUELHH), and accuracy analysis",
    version="1.0.0",
)

# Configure CORS for development and deployed frontend environments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(actuals_router)
app.include_router(forecasts_router)
app.include_router(accuracy_router)


@app.get("/api/health", tags=["System"])
def health_check():
    """Health check endpoint to verify backend operational status."""
    return {
        "status": "healthy",
        "application": "Wind Forecast Intelligence API",
    }


@app.get("/api", tags=["System"])
def api_info():
    """Directory of available backend endpoints."""
    return {
        "message": "Wind Forecast Intelligence API is running",
        "available_endpoints": [
            "/api/health",
            "/api/actuals",
            "/api/forecasts",
            "/api/accuracy",
            "/docs",
        ],
    }
