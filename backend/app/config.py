import os
from typing import List
from dotenv import load_dotenv

# Load variables from .env file if present
load_dotenv()


class Settings:
    """Application settings with environment variable fallbacks."""

    ENV: str = os.getenv("ENV", "production")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # CORS configuration
    # Comma-separated list of allowed origins or "*"
    ALLOWED_ORIGINS_RAW: str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
    )

    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        raw = self.ALLOWED_ORIGINS_RAW.strip()
        if raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    # Elexon BMRS API configuration
    ELEXON_BASE_URL: str = os.getenv("ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1").rstrip("/")
    ELEXON_TIMEOUT: float = float(os.getenv("ELEXON_TIMEOUT", "20.0"))

    # Decision cutoff configuration (default: 10:00 UTC D-1)
    DEFAULT_CUTOFF_HOUR: int = int(os.getenv("DEFAULT_CUTOFF_HOUR", "10"))

    # Whether to fall back to synthetic profile when Elexon API is offline/empty
    ALLOW_SYNTHETIC_FALLBACK: bool = os.getenv("ALLOW_SYNTHETIC_FALLBACK", "true").lower() in ("true", "1", "yes")


settings = Settings()
