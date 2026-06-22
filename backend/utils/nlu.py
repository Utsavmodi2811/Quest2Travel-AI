"""
Natural Language Understanding utilities.
Handles fuzzy city matching, spell correction, alias resolution,
and travel intent extraction.
"""

import re
import logging
from typing import Optional, Tuple, Dict, List
from datetime import datetime, timedelta
from rapidfuzz import process, fuzz
import dateparser

logger = logging.getLogger(__name__)

# ─── City Alias & Known Cities Dictionary ────────────────────────────────────

CITY_ALIASES: Dict[str, str] = {
    # Common misspellings and aliases for Indian cities
    "delhii": "delhi", "dilhi": "delhi", "dilli": "delhi", "new dhelhi": "new delhi",
    "mumabi": "mumbai", "bombay": "mumbai", "mumbay": "mumbai", "mumba": "mumbai",
    "banglore": "bangalore", "bengaluru": "bangalore", "bangalor": "bangalore",
    "bangluru": "bangalore", "blr": "bangalore",
    "ahemdabad": "ahmedabad", "ahmedabd": "ahmedabad", "amdavad": "ahmedabad",
    "punne": "pune", "poona": "pune", "puna": "pune",
    "hydrabad": "hyderabad", "hyderabad": "hyderabad", "hyd": "hyderabad",
    "chenai": "chennai", "madras": "chennai", "chennaai": "chennai",
    "kolkatta": "kolkata", "calcutta": "kolkata", "kolkota": "kolkata",
    "jaipur": "jaipur", "jaipure": "jaipur", "pinkcity": "jaipur",
    "goa": "goa", "panaji": "goa", "panjim": "goa",
    "kochi": "kochi", "cochin": "kochi", "ernakulam": "kochi",
    "thiruvananthapuram": "trivandrum", "trivandrum": "trivandrum",
    "bhopal": "bhopal", "lucknow": "lucknow", "lko": "lucknow",
    "nagpur": "nagpur", "indore": "indore", "surat": "surat",
    "vadodara": "vadodara", "baroda": "vadodara",
    "amritsar": "amritsar", "chandigarh": "chandigarh",
    "shimla": "shimla", "simla": "shimla", "manali": "manali",
    "varanasi": "varanasi", "banaras": "varanasi", "benares": "varanasi", "kashi": "varanasi",
    "agra": "agra", "mathura": "mathura", "vrindavan": "vrindavan",
    "dehradun": "dehradun", "doon": "dehradun",
    "haridwar": "haridwar", "rishikesh": "rishikesh",
    "darjeeling": "darjeeling", "gangtok": "gangtok",
    "puri": "puri", "bhubaneswar": "bhubaneswar", "cuttack": "cuttack",
    "patna": "patna", "ranchi": "ranchi", "raipur": "raipur",
    "coimbatore": "coimbatore", "madurai": "madurai", "trichy": "tiruchirappalli",
    "vizag": "visakhapatnam", "visakhapatnam": "visakhapatnam",
    "rajkot": "rajkot", "surat": "surat", "gandhinagar": "gandhinagar",
    "jodhpur": "jodhpur", "udaipur": "udaipur", "ajmer": "ajmer",
    "mysore": "mysuru", "mysuru": "mysuru", "ooty": "ooty",
    "aurangabad": "aurangabad", "nashik": "nashik", "kolhapur": "kolhapur",
    "leh": "leh", "ladakh": "leh", "srinagar": "srinagar", "jammu": "jammu",
    "port blair": "port blair", "andaman": "port blair",
    # International
    "dubai": "dubai", "singapore": "singapore", "bangkok": "bangkok",
    "london": "london", "paris": "paris", "new york": "new york",
    "nyc": "new york", "ny": "new york",
    "la": "los angeles", "sf": "san francisco",
}

KNOWN_CITIES: List[str] = sorted(set(CITY_ALIASES.values()) | {
    "delhi", "mumbai", "bangalore", "hyderabad", "chennai",
    "kolkata", "pune", "ahmedabad", "jaipur", "goa",
    "kochi", "lucknow", "chandigarh", "shimla", "manali",
    "varanasi", "agra", "dehradun", "haridwar", "rishikesh",
    "darjeeling", "puri", "bhubaneswar", "patna", "raipur",
    "coimbatore", "madurai", "visakhapatnam", "rajkot",
    "jodhpur", "udaipur", "mysuru", "ooty", "nashik",
    "leh", "srinagar", "jammu", "port blair",
    "dubai", "singapore", "bangkok", "london", "paris",
    "new york", "los angeles", "san francisco",
})

# ─── Travel Intent Patterns ───────────────────────────────────────────────────

TRAVEL_ROUTE_PATTERNS = [
    r"(?:from\s+)?(\w[\w\s]+?)\s+to\s+(\w[\w\s]+?)(?:\s+(?:on|for|date|trip|flight|train|bus|by|cheap|budget))?(?:\s|$)",
    r"(\w[\w\s]+?)\s*[-–→]\s*(\w[\w\s]+)",
    r"book\s+(?:a\s+)?(?:flight|train|bus)\s+(?:from\s+)?(\w[\w\s]+?)\s+to\s+(\w[\w\s]+)",
]

DATE_PATTERNS = [
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
    r"\b(today|tomorrow|next\s+\w+|this\s+\w+)\b",
    r"\b(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*)\b",
]

FLIGHT_KEYWORDS = ["flight", "fly", "flying", "airline", "airport", "airways",
                   "economy", "business class", "first class", "non.stop"]
TRAIN_KEYWORDS = ["train", "railway", "irctc", "sleeper", "ac coach", "rajdhani",
                  "shatabdi", "express", "passenger", "3ac", "2ac", "1ac"]
BUS_KEYWORDS = ["bus", "coach", "volvo", "redbus", "sleeper bus", "ac bus",
                "overnight bus", "semi sleeper"]
HOTEL_KEYWORDS = ["hotel", "stay", "accommodation", "hostel", "resort",
                  "room", "check in", "checkout", "5 star", "3 star", "4 star"]
CAR_KEYWORDS = ["car", "cab", "taxi", "rent", "rental", "suv", "sedan", "ola", "uber",
                "self drive", "chauffeur"]


# ─── Core Functions ───────────────────────────────────────────────────────────

def normalize_city(raw: str) -> str:
    """Normalize city name: lowercase, strip, replace multiple spaces."""
    return re.sub(r'\s+', ' ', raw.strip().lower())


def resolve_city(raw_city: str) -> Tuple[str, float]:
    """
    Resolve a raw city string to a canonical city name.
    Returns (canonical_name, confidence_score).
    confidence 1.0 = exact match, 0.0 = no match.
    """
    if not raw_city or not raw_city.strip():
        return raw_city, 0.0

    normalized = normalize_city(raw_city)

    # 1. Exact alias match
    if normalized in CITY_ALIASES:
        return CITY_ALIASES[normalized], 1.0

    # 2. Exact known city match
    if normalized in KNOWN_CITIES:
        return normalized, 1.0

    # 3. Fuzzy match against aliases keys
    alias_match = process.extractOne(
        normalized, list(CITY_ALIASES.keys()),
        scorer=fuzz.WRatio, score_cutoff=80
    )
    if alias_match:
        return CITY_ALIASES[alias_match[0]], alias_match[1] / 100.0

    # 4. Fuzzy match against known cities
    city_match = process.extractOne(
        normalized, KNOWN_CITIES,
        scorer=fuzz.WRatio, score_cutoff=75
    )
    if city_match:
        return city_match[0], city_match[1] / 100.0

    # 5. Return cleaned version with low confidence
    return normalized.title(), 0.5


def extract_route(text: str) -> Optional[Tuple[str, str]]:
    """
    Extract origin → destination from user text.
    Returns (origin, destination) or None.
    """
    text_lower = text.lower().strip()

    for pattern in TRAVEL_ROUTE_PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            origin_raw = match.group(1).strip()
            dest_raw = match.group(2).strip()

            # Clean trailing words
            stop_words = {"on", "for", "by", "cheap", "cheapest", "best", "trip", "travel"}
            origin_raw = " ".join(w for w in origin_raw.split() if w not in stop_words)
            dest_raw = " ".join(w for w in dest_raw.split() if w not in stop_words)

            if len(origin_raw) >= 2 and len(dest_raw) >= 2:
                origin, _ = resolve_city(origin_raw)
                dest, _ = resolve_city(dest_raw)
                return origin, dest

    return None


def extract_travel_mode(text: str) -> Optional[str]:
    """Detect travel mode from user text."""
    text_lower = text.lower()

    # Count keyword hits per mode
    scores = {
        "flight": sum(1 for kw in FLIGHT_KEYWORDS if kw in text_lower),
        "train": sum(1 for kw in TRAIN_KEYWORDS if kw in text_lower),
        "bus": sum(1 for kw in BUS_KEYWORDS if kw in text_lower),
        "hotel": sum(1 for kw in HOTEL_KEYWORDS if kw in text_lower),
        "car": sum(1 for kw in CAR_KEYWORDS if kw in text_lower),
    }

    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best
    return None


def extract_budget(text: str) -> Optional[Tuple[Optional[float], Optional[float]]]:
    """
    Extract budget range from text.
    Returns (min_budget, max_budget) or None.
    """
    # "under 5000", "less than 5000", "below 5000"
    under = re.search(r'(?:under|below|less\s+than|max|maximum|within)\s+[₹rs.]?\s*(\d[\d,]*)', text, re.IGNORECASE)
    if under:
        val = float(under.group(1).replace(",", ""))
        return None, val

    # "above 3000", "more than 3000"
    above = re.search(r'(?:above|more\s+than|over|min|minimum|atleast|at\s+least)\s+[₹rs.]?\s*(\d[\d,]*)', text, re.IGNORECASE)
    if above:
        val = float(above.group(1).replace(",", ""))
        return val, None

    # "3000 to 6000" or "3000-6000"
    between = re.search(r'[₹rs.]?\s*(\d[\d,]*)\s*(?:to|-)\s*[₹rs.]?\s*(\d[\d,]*)', text, re.IGNORECASE)
    if between:
        lo = float(between.group(1).replace(",", ""))
        hi = float(between.group(2).replace(",", ""))
        return lo, hi

    return None


def extract_date(text: str) -> Optional[str]:
    """
    Extract a travel date from free text and normalize to YYYY-MM-DD.

    Supports: "19th june", "19 june", "june 19", "tomorrow",
    "next friday", "day after tomorrow", "19/06/2026", etc.

    Uses dateparser with PREFER_DATES_FROM='future' so a bare day/month
    (e.g. "19 june" said in January) resolves to the *next* occurrence
    rather than defaulting to today or a past date. Returns None if no
    date-like text is found — callers must NOT default to "today"
    themselves when this returns a real value.
    """
    if not text or not text.strip():
        return None

    # First, try explicit relative/absolute phrases via regex hints so we
    # only hand dateparser the relevant substring (avoids it grabbing
    # unrelated numbers like budgets or flight numbers).
    candidates = []

    # Relative phrases
    relative_patterns = [
        r"\bday after tomorrow\b",
        r"\btomorrow\b",
        r"\btoday\b",
        r"\bnext\s+(?:mon|tues?|wednes|thurs?|fri|satur|sun)\w*\b",
        r"\bthis\s+(?:mon|tues?|wednes|thurs?|fri|satur|sun)\w*\b",
        r"\bcoming\s+\w+\b",
    ]
    for pat in relative_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            candidates.append(m.group(0))

    # Absolute "19th june", "19 june", "june 19", "19 jun 2026"
    absolute_patterns = [
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*(?:\s+\d{4})?\b",
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?\b",
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    ]
    for pat in absolute_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            candidates.append(m.group(0))

    if not candidates:
        return None

    # Use the longest / most specific candidate match
    raw = max(candidates, key=len)

    try:
        parsed = dateparser.parse(
            raw,
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": datetime.now(),
            },
        )
    except Exception as e:
        logger.warning(f"dateparser failed on '{raw}': {e}")
        parsed = None

    if not parsed:
        return None

    return parsed.strftime("%Y-%m-%d")


def extract_cabin_class(text: str) -> Optional[str]:
    """Extract flight cabin class from text."""
    text_lower = text.lower()
    if "first class" in text_lower:
        return "first"
    if "business" in text_lower:
        return "business"
    if "premium economy" in text_lower or "premium" in text_lower:
        return "premium_economy"
    if "economy" in text_lower:
        return "economy"
    return None


def extract_hotel_stars(text: str) -> Optional[int]:
    """Extract hotel star rating from text."""
    match = re.search(r'(\d)\s*[-]?\s*star', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    if "luxury" in text.lower():
        return 5
    if "budget" in text.lower():
        return 2
    return None


def is_greeting(text: str) -> bool:
    """Check if user message is a greeting."""
    greetings = {"hello", "hi", "hey", "howdy", "hola", "namaste",
                 "good morning", "good evening", "good afternoon",
                 "what's up", "sup", "how are you", "how r u"}
    return normalize_city(text) in greetings or any(
        normalize_city(text).startswith(g) for g in greetings
    )


def is_travel_query(text: str) -> bool:
    """Determine if the user message is a travel-related query."""
    text_lower = text.lower()
    travel_signals = (
        FLIGHT_KEYWORDS + TRAIN_KEYWORDS + BUS_KEYWORDS +
        HOTEL_KEYWORDS + CAR_KEYWORDS +
        ["book", "travel", "trip", "journey", "route", "ticket",
         "depart", "arrive", "destination", "visit", "going to",
         "from", "to", "how to reach", "best way to go"]
    )
    return (
        extract_route(text) is not None or
        any(kw in text_lower for kw in travel_signals)
    )
