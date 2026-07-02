from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ======================================================================
    # Application
    # ======================================================================

    APP_NAME: str = "Quest2Travel API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    # ======================================================================
    # CORS
    # ======================================================================

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
    ]

    # ======================================================================
    # MongoDB
    # ======================================================================

    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "quest2travel"

    # ======================================================================
    # Gemini AI
    # ======================================================================

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ======================================================================
    # RapidAPI
    # ======================================================================

    # One RapidAPI key for all subscribed APIs
    RAPIDAPI_KEY: str = ""

    # Booking.com15
    BOOKING_COM15_HOST: str = "booking-com15.p.rapidapi.com"

    # IRCTC
    IRCTC_HOST: str = "irctc1.p.rapidapi.com"

    # ======================================================================
    # Legacy API Keys (Backward Compatibility)
    # ======================================================================

    AVIATIONSTACK_API_KEY: str = ""
    BOOKING_API_KEY: str = ""
    RAILYATRI_API_KEY: str = ""
    REDBUS_API_KEY: str = ""
    OPENWEATHER_API_KEY: str = ""

    # ======================================================================
    # Geocoding
    # ======================================================================

    GEOCODING_PROVIDER: str = "nominatim"

    GOOGLE_GEOCODING_KEY: str = ""

    NOMINATIM_BASE_URL: str = "https://nominatim.openstreetmap.org"

    # ======================================================================
    # API Configuration
    # ======================================================================

    API_TIMEOUT: int = 10
    API_RETRY_COUNT: int = 2
    API_RETRY_DELAY: float = 0.5

    MAX_HTTP_CONNECTIONS: int = 100
    MAX_KEEPALIVE_CONNECTIONS: int = 20

    # ======================================================================
    # Cache Configuration
    # ======================================================================

    GEOCODE_CACHE_TTL: int = 86400          # 24 Hours
    LOCATION_ID_CACHE_TTL: int = 604800     # 7 Days
    TRAVEL_RESULT_CACHE_TTL: int = 1800     # 30 Minutes

    AIRPORT_CACHE_TTL: int = 604800
    RAILWAY_CACHE_TTL: int = 604800
    WEATHER_CACHE_TTL: int = 3600
    HOTEL_CACHE_TTL: int = 1800
    SEARCH_CACHE_TTL: int = 1800

    # ======================================================================
    # Journey Planner
    # ======================================================================

    AIRPORT_CHECKIN_MINUTES: int = 90
    INTERNATIONAL_AIRPORT_CHECKIN_MINUTES: int = 180

    CAB_BUFFER_MINUTES: int = 60
    TRAIN_BUFFER_MINUTES: int = 30
    BUS_BUFFER_MINUTES: int = 20

    MEETING_PREP_MINUTES: int = 30

    DEFAULT_HOTEL_RADIUS_KM: int = 5

    # ======================================================================
    # Feature Flags
    # ======================================================================

    ENABLE_PLANNER_AGENT: bool = True
    ENABLE_JOURNEY_PLANNER: bool = True
    ENABLE_MEETING_PLANNER: bool = True
    ENABLE_RETURN_TRIP: bool = True
    ENABLE_TIME_OPTIMIZER: bool = True
    ENABLE_ITINERARY_BUILDER: bool = True

    ENABLE_CONVERSATION_MEMORY: bool = True
    ENABLE_COMPANY_PERMISSIONS: bool = True
    ENABLE_DYNAMIC_LOCATION_RESOLUTION: bool = True
    ENABLE_FUZZY_MATCHING: bool = True
    ENABLE_SEARCH_CACHE: bool = True

    # ======================================================================
    # Fuzzy Matching
    # ======================================================================

    FUZZY_MATCH_THRESHOLD: int = 85

    # ======================================================================
    # Conversation Memory
    # ======================================================================

    MAX_CONVERSATION_MESSAGES: int = 50

    MEMORY_EXPIRY_HOURS: int = 24

    # ======================================================================
    # Company Permissions
    # ======================================================================

    DEFAULT_COMPANY: str = "General"

    # ======================================================================
    # Search Defaults
    # ======================================================================

    DEFAULT_CURRENCY: str = "INR"

    DEFAULT_COUNTRY: str = "India"

    DEFAULT_LANGUAGE: str = "en"

    MAX_SEARCH_RESULTS: int = 20

    # ======================================================================
    # Logging
    # ======================================================================

    LOG_LEVEL: str = "INFO"

    ENABLE_REQUEST_LOGGING: bool = True

    ENABLE_API_LOGGING: bool = True

    ENABLE_PERFORMANCE_LOGGING: bool = True

    # ======================================================================
    # Development
    # ======================================================================

    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()