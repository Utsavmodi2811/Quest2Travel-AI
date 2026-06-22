"""
Flights API Client — booking-com15 via RapidAPI.

Flow (2 endpoints only):
  1. Search Flight Location  →  resolve city name to airport/location ID
  2. Search Flights          →  search with those IDs

Fallback: mock_flights() when API key missing or calls fail.
"""

import httpx
import hashlib
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from config.settings import settings
from models.travel import FlightResult, FlightSegment, CabinClass
from utils.fallback import with_fallback, mock_flights
from database.connection import get_db

logger = logging.getLogger(__name__)

# booking-com15 base URL
_BASE = "https://booking-com15.p.rapidapi.com/api/v1/flights"


def _headers() -> Dict[str, str]:
    return {
        "X-RapidAPI-Key":  settings.RAPIDAPI_KEY,
        "X-RapidAPI-Host": settings.BOOKING_COM15_HOST,
    }


# ── Location ID cache helpers ──────────────────────────────────────────────────

def _loc_cache_key(query: str) -> str:
    return "flight_loc:" + hashlib.md5(query.strip().lower().encode()).hexdigest()


async def _get_cached_location_id(query: str) -> Optional[str]:
    try:
        db = get_db()
        doc = await db.cached_results.find_one({"cache_key": _loc_cache_key(query)})
        if doc and doc.get("value"):
            return doc["value"]
    except Exception:
        pass
    return None


async def _cache_location_id(query: str, loc_id: str) -> None:
    try:
        db = get_db()
        await db.cached_results.update_one(
            {"cache_key": _loc_cache_key(query)},
            {"$set": {
                "cache_key": _loc_cache_key(query),
                "value": loc_id,
                "expires_at": datetime.utcnow() + timedelta(seconds=settings.LOCATION_ID_CACHE_TTL),
            }},
            upsert=True,
        )
    except Exception as e:
        logger.debug(f"Flight loc cache write failed: {e}")


# ── Main client ────────────────────────────────────────────────────────────────

class FlightsClient:

    async def search(
        self,
        origin: str,
        destination: str,
        travel_date: str,
        return_date: Optional[str] = None,
        passengers: int = 1,
        cabin_class: str = "economy",
    ) -> List[FlightResult]:
        return await self._search_with_fallback(
            origin, destination, travel_date, return_date, passengers, cabin_class
        )

    @with_fallback(mock_flights)
    async def _search_with_fallback(
        self,
        origin: str,
        destination: str,
        travel_date: str,
        return_date: Optional[str] = None,
        passengers: int = 1,
        cabin_class: str = "economy",
    ) -> List[FlightResult]:
        if not settings.RAPIDAPI_KEY:
            raise ValueError("RAPIDAPI_KEY not configured — using mock data")

        # Step 1: resolve both city names to location IDs
        origin_id = await self._get_location_id(origin)
        dest_id   = await self._get_location_id(destination)

        if not origin_id or not dest_id:
            missing = []
            if not origin_id:
                missing.append(f"origin='{origin}'")
            if not dest_id:
                missing.append(f"destination='{destination}'")
            logger.warning(f"Airport resolution failed for: {', '.join(missing)}")
            raise ValueError(
                f"Could not resolve location IDs for '{origin}' or '{destination}'"
            )

        # Step 2: search flights
        return await self._search_flights(
            origin_id, dest_id, travel_date, passengers, cabin_class
        )

    # ── Step 1: Search Flight Location ────────────────────────────────────────

    async def _get_location_id(self, city: str) -> Optional[str]:
        """
        Endpoint: GET /api/v1/flights/searchDestination
        Param: query=<city name>
        Returns the first matching airport/city ID.
        Caches result for 7 days.
        """
        cached = await _get_cached_location_id(city)
        if cached:
            logger.debug(f"Flight location cache hit: {city} → {cached}")
            return cached

        try:
            timeout = httpx.Timeout(
                connect=10,
                read=30,
                write=10,
                pool=10
            )

            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(
                    f"{_BASE}/searchDestination",
                    headers=_headers(),
                    params={"query": city},
                )
                resp.raise_for_status()
                data = resp.json()
                print("\n========== FLIGHT API RESPONSE ==========")
                print(data)
                print("========================================")

            # Response: {"status": true, "data": [{"id": "...", "name": "...", ...}]}
            items = data.get("data") or []
            if not items:
                logger.warning(f"No flight location found for: {city}")
                return None

            # Pick the first airport (type=AIRPORT) if available, else first result
            loc_id = None
            for item in items:
                if item.get("type", "").upper() in ("AIRPORT", "CITY"):
                    loc_id = item.get("id")
                    break
            if not loc_id:
                loc_id = items[0].get("id")

            if loc_id:
                await _cache_location_id(city, loc_id)
                logger.info(f"Resolved flight location: {city} → {loc_id}")

            return loc_id

        except Exception as e:
            logger.error(f"Search Flight Location failed for '{city}': {e}")
            return None

    # ── Step 2: Search Flights ────────────────────────────────────────────────

    async def _search_flights(
        self,
        from_id: str,
        to_id: str,
        date: str,
        adults: int,
        cabin_class: str,
    ) -> List[FlightResult]:
        """
        Endpoint: GET /api/v1/flights/searchFlights
        Required params: fromId, toId, departDate, adults, cabinClass, currency, sort
        """
        cabin_map = {
            "economy":         "ECONOMY",
            "premium_economy": "PREMIUM_ECONOMY",
            "business":        "BUSINESS",
            "first":           "FIRST",
        }

        params: Dict[str, Any] = {
            "fromId":      from_id,
            "toId":        to_id,
            "departDate":  date,
            "adults":      adults,
            "cabinClass":  cabin_map.get(cabin_class, "ECONOMY"),
            "currency_code": "INR",
            "sort":        "BEST",
            "page":        1,
        }

        timeout = httpx.Timeout(
            connect=10,
            read=30,
            write=10,
            pool=10
        )

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(
                f"{_BASE}/searchFlights",
                headers=_headers(),
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        # Response shape: {"status": true, "data": {"flightOffers": [...], ...}}
        # Schema can drift between API versions — try multiple known shapes.
        offers = (
            (data.get("data") or {}).get("flightOffers")
            or data.get("flightOffers")
            or (data.get("data") or {}).get("offers")
            or []
        )

        if not offers:
            logger.warning(f"booking-com15 returned 0 flight offers for {from_id}→{to_id} on {date}")
            raise ValueError("No flight offers returned by booking-com15")

        results = []
        seen = set()
        try:
            cab_enum = CabinClass(cabin_class)
        except Exception:
            cab_enum = CabinClass.ECONOMY
        

        for offer in offers[:15]:
            try:
                parsed = self._parse_offer(offer, cab_enum)

                if parsed:

                    # unique key
                    first_seg = parsed.segments[0]

                    key = (
                        first_seg.flight_number,
                        first_seg.departure_time,
                        parsed.segments[-1].arrival_time
                    )

                    if key in seen:
                        continue

                    seen.add(key)
                    results.append(parsed)

            except Exception as e:
                logger.debug(f"Failed to parse flight offer: {e}")

        if not results:
            logger.warning(f"All {len(offers)} flight offers failed to parse for {from_id}→{to_id}")
            raise ValueError("No parseable flight offers in response")

        logger.info(f"Parsed {len(results)} flights for {from_id} → {to_id} ({date})")
        return results

    def _parse_offer(self, offer: Dict, cab_enum: CabinClass) -> Optional[FlightResult]:
        """
        booking-com15 offer structure:
        {
          "segments": [{
            "legs": [{
              "departureAirport": {"code": "DEL", "city": "Delhi", ...},
              "arrivalAirport":   {"code": "BOM", "city": "Mumbai", ...},
              "departureTime":    "2024-06-15T06:15:00",
              "arrivalTime":      "2024-06-15T08:20:00",
              "flightInfo": {"flightNumber": 123, "carrierInfo": {"operatingCarrier": "6E"}},
              "totalTime":  6300,
            }]
          }],
          "priceBreakdown": {"total": {"units": 4299, "nanos": 0}},
          "travellerPrices": [...],
          "isFlexible": false,
        }

        NOTE on "stops": one "segment" = one directional leg of the
        itinerary (e.g. outbound). Each segment can have multiple "legs"
        if it has layovers (DEL→BLR→BOM = 2 legs in 1 segment = 1 stop).
        Stops = (number of legs in the outbound segment) - 1, NOT
        (total segments - 1) — multi-segment offers (round trips) would
        otherwise be miscounted as having stops.
        """
        segments_raw = offer.get("segments") or []
        if not segments_raw:
            return None

        # We render only the OUTBOUND segment (first one) as the itinerary;
        # this matches what the FlightResult/FlightSegment model expects
        # (a single directional list of segments/legs).
        outbound = segments_raw[0]
        legs_raw = outbound.get("legs") or []
        if not legs_raw:
            return None

        segments: List[FlightSegment] = []
        

        for leg in legs_raw:
            dep_ap  = leg.get("departureAirport") or {}
            arr_ap  = leg.get("arrivalAirport")   or {}
            fi      = leg.get("flightInfo")       or {}
            carrier = fi.get("carrierInfo")       or {}

            airline_code = (
                carrier.get("operatingCarrier")
                or carrier.get("marketingCarrier")
                or carrier.get("operating")
                or "XX"
            )
            # Real airline NAME comes from carrierInfo / a dedicated field,
            # never from the airport's city name (that was the old bug —
            # it caused "Delhi" to show up as the airline).
            airline_name = (
                carrier.get("operatingCarrierName")
                or carrier.get("marketingCarrierName")
                or carrier.get("name")
                or self._airline_code_to_name(airline_code)
                or "Unknown Airline"
            )

            flight_num = f"{airline_code}{fi.get('flightNumber', '')}".strip()

            leg_secs = leg.get("totalTime", 0) or 0
            dur_str = self._fmt_duration(leg_secs)

            segments.append(FlightSegment(
                flight_number     = flight_num or "N/A",
                airline           = airline_name,
                airline_code      = airline_code,
                departure_airport = dep_ap.get("code", "") or "",
                departure_city    = dep_ap.get("cityName") or dep_ap.get("city") or "",
                departure_time    = leg.get("departureTime", "") or "",
                arrival_airport   = arr_ap.get("code", "") or "",
                arrival_city      = arr_ap.get("cityName") or arr_ap.get("city") or "",
                arrival_time      = leg.get("arrivalTime", "") or "",
                duration          = dur_str,
                aircraft          = leg.get("aircraftType"),
            ))
        from datetime import datetime

        try:
            departure_dt = datetime.fromisoformat(
                segments[0].departure_time
            )

            arrival_dt = datetime.fromisoformat(
                segments[-1].arrival_time
            )

            total_seconds = int(
                (arrival_dt - departure_dt).total_seconds()
            )

        except Exception:
            total_seconds = 0


        if not segments:
            return None

        price = self._extract_price(offer)

        # Correct stop count: legs within the outbound segment minus 1.
        # A direct flight has exactly 1 leg → 0 stops.
        stops = max(0, len(legs_raw) - 1)

        return FlightResult(
            segments          = segments,
            total_duration    = self._fmt_duration(total_seconds),
            stops             = stops,
            cabin_class       = cab_enum,
            price             = price,
            currency          = "INR",
            baggage_allowance = self._extract_baggage(offer),
            is_refundable=False,
            source            = "booking-com15",
            is_mock           = False,
        )

    # Minimal IATA code → name map for when the API omits a human name.
    # Used only as a last-resort fallback; never overrides a real API value.
    _AIRLINE_NAMES = {
        "6E": "IndiGo",
        "AI": "Air India",
        "SG": "SpiceJet",
        "UK": "Vistara",
        "QP": "Akasa Air",
        "IX": "Air India Express",
        "I5": "AirAsia India",
        "G8": "Go First",
    }

    def _airline_code_to_name(self, code: str) -> str:
        if not code:
            return "Unknown Airline"

        return self._AIRLINE_NAMES.get(
            code.upper(),
            f"Airline {code}"
        )

    def _extract_price(self, offer: Dict) -> float:
        """
        Extract price from priceBreakdown or travellerPrices.
        Returns 0.0 (never a random number) if the schema doesn't match —
        callers/UI should treat price=0 as "price unavailable", not as a
        real fare. Faking a price is worse than admitting we don't have one.
        """
        pb = offer.get("priceBreakdown") or {}
        total = pb.get("total") or {}
        if total.get("units") is not None:
            nanos = total.get("nanos", 0) or 0
            return float(total["units"]) + nanos / 1e9

        for tp in offer.get("travellerPrices") or []:
            price_obj = (tp.get("travellerPriceBreakdown") or {}).get("total") or {}
            if price_obj.get("units") is not None:
                nanos = price_obj.get("nanos", 0) or 0
                return float(price_obj["units"]) + nanos / 1e9

        logger.warning("Flight offer had no parseable price field — defaulting to 0.0")
        return 0.0

    def _extract_baggage(self, offer: Dict) -> Optional[str]:

        segments = offer.get("segments") or []

        if not segments:
            return None

        seg = segments[0]

        checked = seg.get("travellerCheckedLuggage") or []
        cabin = seg.get("travellerCabinLuggage") or []

        check_kg = None
        cabin_kg = None

        if checked:
            allowance = checked[0].get("luggageAllowance", {})
            weight_lb = (
                allowance.get("maxWeightPerPiece")
                or allowance.get("maxTotalWeight")
            )

            if weight_lb:
                check_kg = round(float(weight_lb) * 0.453592)

        if cabin:
            allowance = cabin[0].get("luggageAllowance", {})
            weight_lb = allowance.get("maxWeightPerPiece")

            if weight_lb:
                cabin_kg = round(float(weight_lb) * 0.453592)

        parts = []

        if check_kg:
            parts.append(f"{check_kg} kg check-in")

        if cabin_kg:
            parts.append(f"{cabin_kg} kg cabin")

        return " + ".join(parts) if parts else None

    @staticmethod
    def _fmt_duration(seconds: int) -> str:
        if not seconds:
            return "N/A"
        h, rem = divmod(int(seconds), 3600)
        m = rem // 60
        return f"{h}h {m}m"


flights_client = FlightsClient()
