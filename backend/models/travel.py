"""
All Pydantic models for Quest2Travel.
Merged version:
- Preserves all old models
- Adds company/user support
- Adds meeting planner
- Adds journey planner
- Backward compatible
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


# ============================================================================
# ENUMS
# ============================================================================

class TravelMode(str, Enum):
    FLIGHT = "flight"
    TRAIN = "train"
    BUS = "bus"
    HOTEL = "hotel"
    CAR = "car"
    GENERAL = "general"


class CabinClass(str, Enum):
    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class TrainClass(str, Enum):
    SLEEPER = "sleeper"
    THREE_AC = "3ac"
    TWO_AC = "2ac"
    ONE_AC = "1ac"
    CHAIR_CAR = "cc"


# Preserved from old model
class BusType(str, Enum):
    AC = "ac"
    NON_AC = "non_ac"
    SLEEPER = "sleeper"
    SEMI_SLEEPER = "semi_sleeper"
    VOLVO = "volvo"
    LUXURY = "luxury"


# Preserved from old model
class HotelStars(int, Enum):
    THREE = 3
    FOUR = 4
    FIVE = 5


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# Added in new version
class ServiceType(str, Enum):
    FLIGHT = "flight"
    HOTEL = "hotel"
    TRAIN = "train"
    BUS = "bus"
    CAR = "car"


class IntentType(str, Enum):
    MEETING_PLAN = "meeting_plan"
    TRAVEL_SEARCH = "travel_search"
    GENERAL_CHAT = "general_chat"
    FILTER_REFINE = "filter_refine"
    JOURNEY_STATUS = "journey_status"


# ============================================================================
# COMPANY / USER
# ============================================================================

class Company(BaseModel):
    company_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    allowed_services: List[ServiceType] = Field(
        default_factory=lambda: list(ServiceType)
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class User(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Guest"
    email: Optional[str] = None
    company_id: Optional[str] = None
    role: str = "employee"

    preferred_cabin: Optional[CabinClass] = None
    preferred_hotel_stars: Optional[int] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# LOCATION
# ============================================================================

class LocationInfo(BaseModel):
    city: str
    state: Optional[str] = None
    country: str = "India"

    latitude: Optional[float] = None
    longitude: Optional[float] = None

    airport_code: Optional[str] = None
    railway_code: Optional[str] = None

    display_name: Optional[str] = None


# ============================================================================
# MEETING
# ============================================================================

class MeetingInfo(BaseModel):
    """Information extracted from natural language."""

    meeting_time: Optional[str] = None
    meeting_date: Optional[str] = None

    meeting_location: Optional[str] = None
    meeting_city: Optional[str] = None

    meeting_lat: Optional[float] = None
    meeting_lng: Optional[float] = None

    meeting_duration_hours: float = 2.0

    current_city: Optional[str] = None

    return_required: bool = False
    return_time: Optional[str] = None

    hotel_required: bool = False

    traveller_count: int = 1


# ============================================================================
# JOURNEY
# ============================================================================

class JourneyLeg(BaseModel):
    leg_type: str

    description: str

    from_location: str
    to_location: str

    depart_time: Optional[str] = None
    arrive_time: Optional[str] = None

    duration_minutes: Optional[int] = None

    price: Optional[float] = None
    currency: str = "INR"

    result_ref: Optional[Dict[str, Any]] = None

    is_mock: bool = False


class JourneyPlan(BaseModel):
    journey_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    session_id: str

    meeting: Optional[MeetingInfo] = None

    legs: List[JourneyLeg] = Field(default_factory=list)

    total_estimated_cost: float = 0.0

    currency: str = "INR"

    timeline_summary: str = ""

    created_at: datetime = Field(default_factory=datetime.utcnow)

# ============================================================================
# TRAVEL CONTEXT
# ============================================================================

class TravelContext(BaseModel):
    """
    Persistent travel context maintained throughout a conversation.
    Backward compatible with the old version while supporting
    meeting planning and company policies.
    """

    # ------------------------------------------------------------------
    # Basic Route Information
    # ------------------------------------------------------------------

    origin: Optional[str] = None
    destination: Optional[str] = None

    # Preserved from old model
    origin_info: Optional[LocationInfo] = None
    destination_info: Optional[LocationInfo] = None

    travel_date: Optional[str] = None
    return_date: Optional[str] = None

    passengers: int = 1

    # ------------------------------------------------------------------
    # Search Filters
    # ------------------------------------------------------------------

    mode: Optional[TravelMode] = None
    active_filter: Optional[TravelMode] = None

    cabin_class: Optional[CabinClass] = None
    train_class: Optional[TrainClass] = None

    # Preserve enum from old model
    bus_type: Optional[BusType] = None

    hotel_stars: Optional[int] = None

    min_budget: Optional[float] = None
    max_budget: Optional[float] = None

    non_stop_only: bool = False

    amenities: List[str] = Field(default_factory=list)

    # ------------------------------------------------------------------
    # Meeting Planner
    # ------------------------------------------------------------------

    meeting: Optional[MeetingInfo] = None
    journey_plan: Optional[JourneyPlan] = None

    # ------------------------------------------------------------------
    # Company Information
    # ------------------------------------------------------------------

    company_id: Optional[str] = None
    user_id: Optional[str] = None

    allowed_services: List[ServiceType] = Field(
        default_factory=lambda: list(ServiceType)
    )

    # ------------------------------------------------------------------
    # User Preferences
    # ------------------------------------------------------------------

    preferred_cabin: Optional[CabinClass] = None

    preferred_hotel_stars: Optional[int] = None

    preferred_airline: Optional[str] = None

    home_city: Optional[str] = None

    profile_complete: bool = False

    # ------------------------------------------------------------------
    # Meeting Time Constraints
    # ------------------------------------------------------------------

    required_arrival_by: Optional[str] = None

    required_departure_after: Optional[str] = None

    # ------------------------------------------------------------------
    # Search Cache
    # ------------------------------------------------------------------

    last_search_results: Optional[Dict[str, Any]] = None


# ============================================================================
# SESSION
# ============================================================================

class Session(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    created_at: datetime = Field(default_factory=datetime.utcnow)

    updated_at: datetime = Field(default_factory=datetime.utcnow)

    message_count: int = 0

    travel_context: TravelContext = Field(
        default_factory=TravelContext
    )

    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# MESSAGE
# ============================================================================

class Message(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    session_id: str

    role: MessageRole

    content: str

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Existing intent
    travel_intent: Optional[TravelMode] = None

    # New high-level intent
    intent_type: Optional[IntentType] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)

# ============================================================================
# FLIGHT MODELS
# ============================================================================

class FlightSegment(BaseModel):
    flight_number: str
    airline: str
    airline_code: str

    departure_airport: str
    departure_city: str
    departure_time: str

    arrival_airport: str
    arrival_city: str
    arrival_time: str

    duration: str

    aircraft: Optional[str] = None


class FlightResult(BaseModel):
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    segments: List[FlightSegment]

    total_duration: str

    stops: int

    cabin_class: CabinClass

    price: float

    currency: str = "INR"

    # Backward compatible
    baggage_allowance: Optional[str] = None

    is_refundable: bool = False

    source: str

    is_mock: bool = False


# ============================================================================
# TRAIN MODELS
# ============================================================================

class TrainClassInfo(BaseModel):
    class_code: str
    class_name: str
    available_seats: int
    price: float
    quota: str = "GENERAL"


# Backward compatibility
TrainClass_Info = TrainClassInfo


class TrainResult(BaseModel):
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    train_number: str
    train_name: str

    origin_station: str
    origin_code: str

    destination_station: str
    destination_code: str

    departure_time: str
    arrival_time: str

    duration: str

    travel_date: str

    classes: List[TrainClassInfo]

    runs_on: List[str] = Field(default_factory=list)

    source: str

    is_mock: bool = False


# ============================================================================
# BUS MODELS
# ============================================================================

class BusResult(BaseModel):
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    operator: str

    bus_type: str

    departure_city: str
    arrival_city: str

    departure_time: str
    arrival_time: str

    duration: str

    available_seats: int

    price: float

    currency: str = "INR"

    amenities: List[str] = Field(default_factory=list)

    cancellation_policy: Optional[str] = None

    source: str

    is_mock: bool = False


# ============================================================================
# HOTEL MODELS
# ============================================================================

class HotelResult(BaseModel):
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    hotel_id: str

    name: str

    rating: float

    stars: int

    address: str

    city: str

    latitude: Optional[float] = None
    longitude: Optional[float] = None

    price_per_night: float

    currency: str = "INR"

    amenities: List[str] = Field(default_factory=list)

    distance_from_center: Optional[float] = None

    # Added in new version
    distance_from_meeting: Optional[float] = None

    review_score: Optional[float] = None

    review_count: Optional[int] = None

    breakfast_included: bool = False

    free_cancellation: bool = False

    image_url: Optional[str] = None

    source: str

    is_mock: bool = False


# ============================================================================
# CAR MODELS
# ============================================================================

class CarResult(BaseModel):
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    vehicle_name: str

    vehicle_type: str

    vendor: str

    fuel_type: str

    seats: int

    transmission: str

    pickup_location: str

    price_per_day: float

    currency: str = "INR"

    features: List[str] = Field(default_factory=list)

    source: str

    is_mock: bool = False


# ============================================================================
# SEARCH RESULT CONTAINER
# ============================================================================

class TravelSearchResult(BaseModel):
    search_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    session_id: str

    search_type: TravelMode

    origin: Optional[str] = None

    destination: Optional[str] = None

    travel_date: Optional[str] = None

    flights: Optional[List[FlightResult]] = None

    trains: Optional[List[TrainResult]] = None

    buses: Optional[List[BusResult]] = None

    hotels: Optional[List[HotelResult]] = None

    cars: Optional[List[CarResult]] = None

    is_partial_mock: bool = False

    mock_reason: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

# ============================================================================
# API REQUEST / RESPONSE
# ============================================================================

class ChatRequest(BaseModel):
    """
    Incoming chat request.
    Supports both anonymous users and authenticated company users.
    """

    session_id: Optional[str] = None

    message: str

    # New fields
    user_id: Optional[str] = None
    company_id: Optional[str] = None

    timezone: str = "Asia/Kolkata"


class ChatResponse(BaseModel):
    """
    Main chatbot response.
    """

    session_id: str

    message_id: str

    reply: str

    # New intent classification
    intent_type: Optional[IntentType] = None

    # Travel search results
    travel_results: Optional[TravelSearchResult] = None

    # Meeting planner result
    journey_plan: Optional[JourneyPlan] = None

    # Updated conversation state
    travel_context: Optional[TravelContext] = None

    suggestions: List[str] = Field(default_factory=list)

    is_travel_query: bool = False

    # Company policy support
    permission_denied: bool = False

    denied_service: Optional[str] = None


# ============================================================================
# FILTER REQUEST (Preserved from old version)
# ============================================================================

class FilterRequest(BaseModel):
    """
    Apply filters on the last search.
    """

    session_id: str

    filters: Dict[str, Any]

    search_type: TravelMode