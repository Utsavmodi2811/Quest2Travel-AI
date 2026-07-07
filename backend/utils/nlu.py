"""
Natural Language Understanding.

Merged Version
--------------
Preserves all old functionality while adding:
- Improved city resolution
- Intent detection
- Meeting information extraction
- Destination-only extraction
- Time extraction
- Better fuzzy matching
"""

import re
import logging

from typing import Optional, Tuple, Dict, List
from datetime import datetime, timedelta

from rapidfuzz import process, fuzz
import dateparser

# -------- New City Database --------
from utils.india_cities import (
    INDIA_CITIES,
    CITY_ALIASES,
    resolve_city as _resolve_city_data,
    get_all_cities,
)

# -------- New Models --------
from models.travel import (
    IntentType,
    MeetingInfo,
)

logger = logging.getLogger(__name__)

# All known cities from database
_ALL_CITIES = get_all_cities()

# ============================================================================
# Legacy aliases (kept for backward compatibility)
# ============================================================================

CITY_ALIASES: Dict[str, str] = {
    "delhii": "delhi",
    "dilhi": "delhi",
    "dilli": "delhi",
    "new dhelhi": "new delhi",

    "mumabi": "mumbai",
    "bombay": "mumbai",
    "mumbay": "mumbai",
    "mumba": "mumbai",

    "banglore": "bangalore",
    "bangalor": "bangalore",
    "bangluru": "bangalore",
    "blr": "bangalore",

    "ahemdabad": "ahmedabad",
    "ahmedabd": "ahmedabad",
    "amdavad": "ahmedabad",

    "punne": "pune",
    "poona": "pune",
    "puna": "pune",

    "hydrabad": "hyderabad",
    "hyd": "hyderabad",

    "chenai": "chennai",
    "madras": "chennai",

    "kolkatta": "kolkata",
    "calcutta": "kolkata",

    "baroda": "vadodara",

    "banaras": "varanasi",
    "benares": "varanasi",
    "kashi": "varanasi",

    "cochin": "kochi",
    "panjim": "goa",
    "panaji": "goa",

    "mysore": "mysuru",
    "trichy": "tiruchirappalli",
    "vizag": "visakhapatnam",

    "nyc": "new york",
    "ny": "new york",
    "la": "los angeles",
    "sf": "san francisco",
}

# ============================================================================
# Route Patterns
# ============================================================================

TRAVEL_ROUTE_PATTERNS = [

    r"(?:from\s+)?([a-zA-Z][a-zA-Z\s]{1,25}?)\s+to\s+([a-zA-Z][a-zA-Z\s]{1,25}?)(?:\s+(?:on|for|date|trip|flight|train|bus|cheap|budget|by)|\s*$)",

    r"([a-zA-Z][a-zA-Z\s]{1,25}?)\s*[-–→]\s*([a-zA-Z][a-zA-Z\s]{1,25})",

    r"book\s+(?:a\s+)?(?:flight|train|bus)\s+(?:from\s+)?([a-zA-Z][a-zA-Z\s]{1,25}?)\s+to\s+([a-zA-Z][a-zA-Z\s]{1,25})",
]

# ============================================================================
# Date Patterns
# ============================================================================

DATE_PATTERNS = [

    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",

    r"\b(today|tomorrow|day after tomorrow|next\s+\w+|this\s+\w+)\b",

    r"\b(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*)\b",

    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}\b",
]

# ============================================================================
# Travel Keywords
# ============================================================================

TRAVEL_KEYWORDS = {

    "flight": [
        "flight",
        "fly",
        "flying",
        "airport",
        "airline",
        "airways",
        "economy",
        "business class",
        "premium economy",
        "first class",
        "non stop",
        "nonstop",
        "direct flight",
    ],

    "train": [
        "train",
        "railway",
        "irctc",
        "rajdhani",
        "shatabdi",
        "express",
        "sleeper",
        "chair car",
        "3ac",
        "2ac",
        "1ac",
    ],

    "bus": [
        "bus",
        "coach",
        "volvo",
        "redbus",
        "ac bus",
        "sleeper bus",
        "semi sleeper",
    ],

    "hotel": [
        "hotel",
        "stay",
        "room",
        "hostel",
        "resort",
        "accommodation",
        "check in",
        "checkout",
        "5 star",
        "4 star",
        "3 star",
        "lodge",
    ],

    "car": [
        "car",
        "cab",
        "taxi",
        "uber",
        "ola",
        "rental",
        "rent",
        "self drive",
        "suv",
        "sedan",
    ],
}

# Old compatibility lists
FLIGHT_KEYWORDS = TRAVEL_KEYWORDS["flight"]
TRAIN_KEYWORDS = TRAVEL_KEYWORDS["train"]
BUS_KEYWORDS = TRAVEL_KEYWORDS["bus"]
HOTEL_KEYWORDS = TRAVEL_KEYWORDS["hotel"]
CAR_KEYWORDS = TRAVEL_KEYWORDS["car"]

# ============================================================================
# Meeting Intent Signals
# ============================================================================

MEETING_SIGNALS = [

    r"\bmeeting\b",
    r"\bconference\b",
    r"\bpresentation\b",
    r"\bclient\b",
    r"\bappointment\b",
    r"\binterview\b",

    r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",

    r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\s+(?:meeting|conference)\b",
]

# ============================================================================
# Stop Words
# ============================================================================

STOP_WORDS = {

    "on",
    "for",
    "by",
    "cheap",
    "cheapest",
    "budget",
    "best",
    "travel",
    "trip",
    "booking",
    "flight",
    "train",
    "bus",
}

# ============================================================================
# Core Functions
# ============================================================================

def normalize_city(raw: str) -> str:
    """
    Normalize city name.
    """
    return re.sub(r"\s+", " ", raw.strip().lower())


def resolve_city(raw: str) -> Tuple[str, float]:
    """
    Resolve a city name using:

    1. india_cities database
    2. Legacy aliases
    3. RapidFuzz
    4. Fallback
    """

    if not raw or not raw.strip():
        return raw or "", 0.0

    normalized = normalize_city(raw)

    # ------------------------------------------------------------------
    # New city database
    # ------------------------------------------------------------------

    try:
        city_data = _resolve_city_data(normalized)

        if city_data:
            return city_data["city"].title(), 1.0

    except Exception:
        pass

    # ------------------------------------------------------------------
    # Legacy aliases
    # ------------------------------------------------------------------

    if normalized in CITY_ALIASES:
        return CITY_ALIASES[normalized].title(), 1.0

    # ------------------------------------------------------------------
    # Exact city match
    # ------------------------------------------------------------------

    if normalized in _ALL_CITIES:
        return normalized.title(), 1.0

    # ------------------------------------------------------------------
    # Fuzzy Match
    # ------------------------------------------------------------------

    match = process.extractOne(
        normalized,
        _ALL_CITIES,
        scorer=fuzz.WRatio,
        score_cutoff=75,
    )

    if match:
        city = match[0]

        if city in CITY_ALIASES:
            city = CITY_ALIASES[city]

        return city.title(), match[1] / 100.0

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    return normalized.title(), 0.5


# ============================================================================
# Intent Detection
# ============================================================================

def detect_intent(text: str) -> IntentType:
    """
    Detect the primary intent of the user message.
    """

    text_lower = text.lower()

    # --------------------------------------------------------------
    # Meeting intent
    # --------------------------------------------------------------

    if any(re.search(pattern, text_lower) for pattern in MEETING_SIGNALS):
        return IntentType.MEETING_PLAN

    # --------------------------------------------------------------
    # Filter refinement
    # --------------------------------------------------------------

    FILTER_WORDS = [
        "only",
        "under",
        "below",
        "above",
        "within",
        "max",
        "minimum",
        "business class",
        "economy",
        "premium economy",
        "first class",
        "5 star",
        "4 star",
        "3 star",
        "direct",
        "non stop",
        "nonstop",
        "refundable",
        "cheapest",
    ]

    if (
        any(word in text_lower for word in FILTER_WORDS)
        and extract_route(text) is None
    ):
        return IntentType.FILTER_REFINE

    # --------------------------------------------------------------
    # Travel Search
    # --------------------------------------------------------------

    if extract_route(text):

        return IntentType.TRAVEL_SEARCH

    for keywords in TRAVEL_KEYWORDS.values():

        for keyword in keywords:

            if keyword in text_lower:

                return IntentType.TRAVEL_SEARCH

    # --------------------------------------------------------------
    # General Chat
    # --------------------------------------------------------------

    return IntentType.GENERAL_CHAT


# ============================================================================
# Route Extraction
# ============================================================================

def extract_route(text: str) -> Optional[Tuple[str, str]]:
    """
    Extract:

    Ahmedabad -> Delhi

    From Ahmedabad to Delhi

    Book flight Ahmedabad to Delhi
    """
    text_lower = text.lower().strip()
    # Ignore trip-type messages
    if text_lower in {
        "one-way",
        "one way",
        "round trip",
        "round-trip",
    }:
        return None
    

    if re.fullmatch(
        r"(one[\s-]?way|round[\s-]?trip)",
        text_lower,
    ):
        return None

    for pattern in TRAVEL_ROUTE_PATTERNS:

        match = re.search(pattern, text_lower, re.IGNORECASE)

        if not match:
            continue

        origin_raw = match.group(1).strip()
        destination_raw = match.group(2).strip()
        # Ignore trip-type phrases like "one-way"
        if (
            f"{origin_raw.lower()}-{destination_raw.lower()}" == "one-way"
            or (
                origin_raw.lower() == "round"
                and destination_raw.lower() == "trip"
            )
        ):
            continue
        origin_raw = " ".join(
            word
            for word in origin_raw.split()
            if word not in STOP_WORDS
        )

        destination_raw = " ".join(
            word
            for word in destination_raw.split()
            if word not in STOP_WORDS
        )

        if len(origin_raw) < 2 or len(destination_raw) < 2:
            continue

        origin, origin_conf = resolve_city(origin_raw)
        destination, dest_conf = resolve_city(destination_raw)

        # Only return if both look like real cities
        if origin_conf < 0.80 or dest_conf < 0.80:
            continue

        return origin, destination

    return None

# ============================================================================
# Destination Extraction
# ============================================================================

def extract_destination_only(text: str) -> Optional[str]:
    """
    Extract destination for hotel/car searches where no origin exists.

    Examples:
        hotels in Goa
        stay at Jaipur
        cars in Ahmedabad
        rooms near Mumbai
    """

    patterns = [

        r"(?:hotel|hotels|stay|accommodation|hostel|room|rooms|resort)\s+(?:in|at|near)\s+([A-Za-z][A-Za-z\s]{1,30})",

        r"(?:car|cars|cab|taxi|rental)\s+(?:in|at|near)\s+([A-Za-z][A-Za-z\s]{1,30})",
    ]

    for pattern in patterns:

        match = re.search(pattern, text, re.IGNORECASE)

        if match:

            city = match.group(1).strip()

            resolved, confidence = resolve_city(city)

            if confidence >= 0.6:
                return resolved

            return city.title()

    return None


# ============================================================================
# Travel Mode Detection
# ============================================================================

def extract_travel_mode(text: str) -> Optional[str]:
    """
    Detect travel mode from text.

    Returns:
        flight
        train
        bus
        hotel
        car
    """

    text_lower = text.lower()

    scores = {
        mode: sum(
            1
            for keyword in keywords
            if keyword in text_lower
        )
        for mode, keywords in TRAVEL_KEYWORDS.items()
    }

    best_mode = max(scores, key=scores.get)

    if scores[best_mode] > 0:
        return best_mode

    return None


# ============================================================================
# Budget Extraction
# ============================================================================

def extract_budget(
    text: str,
) -> Optional[Tuple[Optional[float], Optional[float]]]:
    """
    Returns:

        (None,5000)      under 5000
        (3000,None)      above 3000
        (3000,6000)      3000-6000
    """

    under = re.search(
        r"(?:under|below|less\s+than|max|within)\s*[₹rs.]?\s*(\d[\d,]*)",
        text,
        re.IGNORECASE,
    )

    if under:

        return (
            None,
            float(under.group(1).replace(",", "")),
        )

    above = re.search(
        r"(?:above|over|more\s+than|min|minimum|atleast|at\s+least)\s*[₹rs.]?\s*(\d[\d,]*)",
        text,
        re.IGNORECASE,
    )

    if above:

        return (
            float(above.group(1).replace(",", "")),
            None,
        )

    between = re.search(
        r"[₹rs.]?\s*(\d[\d,]*)\s*(?:to|-)\s*[₹rs.]?\s*(\d[\d,]*)",
        text,
        re.IGNORECASE,
    )

    if between:

        return (
            float(between.group(1).replace(",", "")),
            float(between.group(2).replace(",", "")),
        )

    return None


# ============================================================================
# Date Extraction
# ============================================================================

def extract_date(text: str) -> Optional[str]:
    """
    Extract date and convert to YYYY-MM-DD.

    Supports:
        today
        tomorrow
        day after tomorrow
        next friday
        18 june
        june 18
        18/06/2026
    """

    if not text:
        return None

    # ---------------------------------------------------------
    # Relative dates
    # ---------------------------------------------------------

    candidates = []

    relative_patterns = [

        r"\bday after tomorrow\b",

        r"\btomorrow\b",

        r"\btoday\b",

        r"\bnext\s+(?:mon|tues|wednes|thurs|fri|satur|sun)\w*\b",

        r"\bthis\s+(?:mon|tues|wednes|thurs|fri|satur|sun)\w*\b",
    ]

    for pattern in relative_patterns:

        match = re.search(pattern, text, re.IGNORECASE)

        if match:

            candidates.append(match.group(0))

    absolute_patterns = [

        r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*(?:\s+\d{4})?\b",

        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?\b",

        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    ]

    for pattern in absolute_patterns:

        match = re.search(pattern, text, re.IGNORECASE)

        if match:

            candidates.append(match.group(0))

    if not candidates:
        return None

    raw = max(candidates, key=len)

    try:

        parsed = dateparser.parse(
            raw,
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": datetime.now(),
            },
        )

    except Exception as exc:

        logger.warning(
            "Date parser failed for '%s': %s",
            raw,
            exc,
        )

        parsed = None

    if parsed is None:
        return None

    return parsed.strftime("%Y-%m-%d")

# ============================================================================
# Time Extraction
# ============================================================================

def extract_time(text: str) -> Optional[str]:
    """
    Extract time from natural language.

    Examples:
        10 AM
        10:30 AM
        14:45
        7 pm

    Returns:
        HH:MM (24-hour format)
    """

    if not text:
        return None

    match = re.search(
        r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    ampm = (match.group(3) or "").lower()

    if ampm == "pm" and hour != 12:
        hour += 12

    elif ampm == "am" and hour == 12:
        hour = 0

    return f"{hour:02d}:{minute:02d}"


# ============================================================================
# Cabin Class
# ============================================================================

def extract_cabin_class(text: str) -> Optional[str]:
    """
    Extract cabin class.
    """

    text_lower = text.lower()

    if "first class" in text_lower:
        return "first"

    if "business class" in text_lower or "business" in text_lower:
        return "business"

    if (
        "premium economy" in text_lower
        or "premium" in text_lower
    ):
        return "premium_economy"

    if "economy" in text_lower:
        return "economy"

    return None


# ============================================================================
# Hotel Star Rating
# ============================================================================

def extract_hotel_stars(text: str) -> Optional[int]:
    """
    Extract hotel star rating.
    """

    match = re.search(
        r"(\d)\s*[-]?\s*star",
        text,
        re.IGNORECASE,
    )

    if match:
        return int(match.group(1))

    text_lower = text.lower()

    if "luxury" in text_lower:
        return 5

    if "budget" in text_lower:
        return 2

    return None


# ============================================================================
# Meeting Information Extraction
# ============================================================================

def extract_meeting_info(text: str) -> Optional[MeetingInfo]:
    """
    Extract structured meeting information.

    Example:
        I have a meeting tomorrow at 11 AM
        at Taj Hotel Mumbai.

    Returns:
        MeetingInfo object
    """

    text_lower = text.lower()

    if not any(
        re.search(pattern, text_lower)
        for pattern in MEETING_SIGNALS
    ):
        return None

    meeting = MeetingInfo()

    # ----------------------------------------------------
    # Meeting Time
    # ----------------------------------------------------

    meeting.meeting_time = extract_time(text)

    # ----------------------------------------------------
    # Meeting Date
    # ----------------------------------------------------

    meeting.meeting_date = extract_date(text)

    if meeting.meeting_date is None:

        meeting.meeting_date = (
            datetime.now() + timedelta(days=1)
        ).strftime("%Y-%m-%d")

    # ----------------------------------------------------
    # Location
    # ----------------------------------------------------

    location_match = re.search(
        r"(?:at|in|@)\s+([A-Za-z][A-Za-z0-9\s&',.-]{2,60})",
        text,
        re.IGNORECASE,
    )

    if location_match:

        meeting.meeting_location = (
            location_match.group(1).strip()
        )

    # ----------------------------------------------------
    # Meeting City
    # ----------------------------------------------------

    route = extract_route(text)

    if route:

        meeting.meeting_city = route[1]

    else:

        destination = extract_destination_only(text)

        if destination:

            meeting.meeting_city = destination

    # ----------------------------------------------------
    # Hotel Required
    # ----------------------------------------------------

    if any(
        keyword in text_lower
        for keyword in [
            "hotel",
            "stay",
            "overnight",
            "accommodation",
        ]
    ):
        meeting.hotel_required = True

    # ----------------------------------------------------
    # Duration
    # ----------------------------------------------------

    duration = re.search(
        r"(\d+)\s*(?:day|days)",
        text,
        re.IGNORECASE,
    )

    if duration:

        meeting.meeting_duration_hours = (
            int(duration.group(1)) * 8
        )

        meeting.hotel_required = True

    # ----------------------------------------------------
    # Return Required
    # ----------------------------------------------------

    if any(
        keyword in text_lower
        for keyword in [
            "return",
            "return flight",
            "come back",
            "back home",
            "round trip",
        ]
    ):
        meeting.return_required = True

    return meeting

# ============================================================================
# Greeting Detection
# ============================================================================

def is_greeting(text: str) -> bool:
    """
    Returns True if the user message is only a greeting.
    """

    if not text:
        return False

    greetings = {
        "hi",
        "hello",
        "hey",
        "hola",
        "howdy",
        "namaste",
        "good morning",
        "good afternoon",
        "good evening",
        "sup",
        "what's up",
        "how are you",
        "how r u",
    }

    normalized = normalize_city(text)

    if normalized in greetings:
        return True

    return any(
        normalized.startswith(greeting)
        for greeting in greetings
    )


# ============================================================================
# Travel Query Detection
# ============================================================================

def is_travel_query(text: str) -> bool:
    """
    Determine whether a user message is travel related.
    """

    if not text:
        return False

    text_lower = text.lower()

    # Route present
    if extract_route(text):
        return True

    # Meeting travel
    if extract_meeting_info(text):
        return True

    # Hotel search
    if extract_destination_only(text):
        return True

    # Travel keywords
    for keywords in TRAVEL_KEYWORDS.values():

        for keyword in keywords:

            if keyword in text_lower:
                return True

    travel_words = {
        "travel",
        "trip",
        "journey",
        "vacation",
        "holiday",
        "tour",
        "tourism",
        "visit",
        "booking",
        "book",
        "ticket",
        "destination",
        "airport",
        "station",
        "depart",
        "arrival",
        "departure",
    }

    if any(word in text_lower for word in travel_words):
        return True

    return False


# ============================================================================
# Optional Convenience Function
# ============================================================================

def parse_travel_query(text: str) -> Dict:
    """
    Extract all supported information from a query.

    Example:

        Book flight from Ahmedabad to Delhi tomorrow
        under 5000 in business class

    Returns a structured dictionary.
    """

    return {
        "intent": detect_intent(text),
        "route": extract_route(text),
        "destination": extract_destination_only(text),
        "travel_mode": extract_travel_mode(text),
        "date": extract_date(text),
        "time": extract_time(text),
        "budget": extract_budget(text),
        "cabin_class": extract_cabin_class(text),
        "hotel_stars": extract_hotel_stars(text),
        "meeting": extract_meeting_info(text),
        "is_travel": is_travel_query(text),
    }


# ============================================================================
# Public Exports
# ============================================================================

__all__ = [

    "normalize_city",

    "resolve_city",

    "detect_intent",

    "extract_route",

    "extract_destination_only",

    "extract_travel_mode",

    "extract_budget",

    "extract_date",

    "extract_time",

    "extract_cabin_class",

    "extract_hotel_stars",

    "extract_meeting_info",

    "is_greeting",

    "is_travel_query",

    "parse_travel_query",
]