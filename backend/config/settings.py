from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Quest2Travel API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
    ]

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "quest2travel"

    # Gemini AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ── RapidAPI (single key for all three: Booking-com15 + IRCTC1) ──────────
    # Get from: https://rapidapi.com — one key works for all subscribed APIs
    RAPIDAPI_KEY: str = ""

    # Booking-com15 (Flights + Hotels + Cars)
    # Subscribe: https://rapidapi.com/DataCrawler/api/booking-com15
    BOOKING_COM15_HOST: str = "booking-com15.p.rapidapi.com"

    # IRCTC1 (Trains)
    # Subscribe: https://rapidapi.com/IRCTCAPI/api/irctc1
    IRCTC_HOST: str = "irctc1.p.rapidapi.com"

    # Legacy keys kept for backward compatibility (ignored if RAPIDAPI_KEY is set)
    AVIATIONSTACK_API_KEY: str = ""
    BOOKING_API_KEY: str = ""
    RAILYATRI_API_KEY: str = ""
    REDBUS_API_KEY: str = ""
    OPENWEATHER_API_KEY: str = ""

    # Geocoding
    GEOCODING_PROVIDER: str = "nominatim"
    GOOGLE_GEOCODING_KEY: str = ""
    NOMINATIM_BASE_URL: str = "https://nominatim.openstreetmap.org"

    # Retry / Fallback
    API_RETRY_COUNT: int = 2
    API_RETRY_DELAY: float = 0.5
    API_TIMEOUT: int = 10

    # Cache TTL (seconds)
    GEOCODE_CACHE_TTL: int = 86400        # 24 hours
    LOCATION_ID_CACHE_TTL: int = 604800   # 7 days (dest IDs don't change)
    TRAVEL_RESULT_CACHE_TTL: int = 1800   # 30 minutes

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
