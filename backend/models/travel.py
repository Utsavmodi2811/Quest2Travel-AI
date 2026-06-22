from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum
import uuid


# ─── Enums ────────────────────────────────────────────────────────────────────

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


class BusType(str, Enum):
    AC = "ac"
    NON_AC = "non_ac"
    SLEEPER = "sleeper"
    SEMI_SLEEPER = "semi_sleeper"
    VOLVO = "volvo"
    LUXURY = "luxury"


class HotelStars(int, Enum):
    THREE = 3
    FOUR = 4
    FIVE = 5


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ─── Core Location ────────────────────────────────────────────────────────────

class LocationInfo(BaseModel):
    city: str
    state: Optional[str] = None
    country: str = "India"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    airport_code: Optional[str] = None
    railway_code: Optional[str] = None
    display_name: Optional[str] = None


# ─── Conversation Memory ──────────────────────────────────────────────────────

class TravelContext(BaseModel):
    """Persistent travel context within a conversation session."""
    origin: Optional[str] = None
    destination: Optional[str] = None
    origin_info: Optional[LocationInfo] = None
    destination_info: Optional[LocationInfo] = None
    travel_date: Optional[str] = None
    return_date: Optional[str] = None
    passengers: int = 1
    mode: Optional[TravelMode] = None
    cabin_class: Optional[CabinClass] = None
    train_class: Optional[TrainClass] = None
    bus_type: Optional[BusType] = None
    hotel_stars: Optional[int] = None
    max_budget: Optional[float] = None
    min_budget: Optional[float] = None
    non_stop_only: bool = False
    amenities: List[str] = []
    last_search_results: Optional[Dict[str, Any]] = None
    active_filter: Optional[TravelMode] = None


class Session(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0
    travel_context: TravelContext = Field(default_factory=TravelContext)
    metadata: Dict[str, Any] = {}


class Message(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: MessageRole
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    travel_intent: Optional[TravelMode] = None
    metadata: Dict[str, Any] = {}


# ─── Flight Models ─────────────────────────────────────────────────────────────

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
    baggage_allowance: Optional[str] = None
    is_refundable: bool = False,
    source: str  # amadeus | kiwi | mock
    is_mock: bool = False


# ─── Train Models ──────────────────────────────────────────────────────────────

class TrainClass_Info(BaseModel):
    class_code: str
    class_name: str
    available_seats: int
    price: float
    quota: str = "GENERAL"


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
    classes: List[TrainClass_Info]
    runs_on: List[str]  # days of week
    source: str
    is_mock: bool = False


# ─── Bus Models ────────────────────────────────────────────────────────────────

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
    amenities: List[str] = []
    cancellation_policy: Optional[str] = None
    source: str
    is_mock: bool = False


# ─── Hotel Models ──────────────────────────────────────────────────────────────

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
    review_score: Optional[float] = None
    review_count: Optional[int] = None
    breakfast_included: bool = False
    free_cancellation: bool = False
    image_url: Optional[str] = None
    source: str
    is_mock: bool = False


# ─── Car Models ────────────────────────────────────────────────────────────────

class CarResult(BaseModel):
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vehicle_name: str
    vehicle_type: str  # sedan | suv | hatchback | luxury
    vendor: str
    fuel_type: str
    seats: int
    transmission: str  # automatic | manual
    pickup_location: str
    price_per_day: float
    currency: str = "INR"
    features: List[str] = []
    source: str
    is_mock: bool = False


# ─── Search Results Container ─────────────────────────────────────────────────

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


# ─── API Request/Response ──────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    timezone: str = "Asia/Kolkata"


class ChatResponse(BaseModel):
    session_id: str
    message_id: str
    reply: str
    travel_results: Optional[TravelSearchResult] = None
    travel_context: Optional[TravelContext] = None
    suggestions: List[str] = []
    is_travel_query: bool = False


class FilterRequest(BaseModel):
    session_id: str
    filters: Dict[str, Any]
    search_type: TravelMode
