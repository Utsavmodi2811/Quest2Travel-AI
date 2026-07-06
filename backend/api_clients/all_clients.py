"""
All Travel API Clients (unified file).
Flights + Hotels: booking-com15 RapidAPI
Trains: irctc1 RapidAPI
Cars: booking-com15 RapidAPI
Buses: mock only

All use @with_fallback — never crash, always return data.
All locations resolved through india_cities database first.
"""

import httpx
import hashlib
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from config.settings import settings
from models.travel import (
    FlightResult, FlightSegment, CabinClass,
    TrainResult, TrainClassInfo, BusResult, CarResult, HotelResult,
)
from utils.fallback import with_fallback, mock_flights, mock_hotels, mock_trains, mock_buses, mock_cars
from utils.india_cities import get_iata, get_station_code, resolve_city
from database.connection import get_db

logger = logging.getLogger(__name__)

_BOOKING_BASE = "https://booking-com15.p.rapidapi.com/api/v1"
_IRCTC_BASE   = "https://irctc1.p.rapidapi.com/api/v1"


def _bh() -> Dict[str, str]:
    return {"X-RapidAPI-Key": settings.RAPIDAPI_KEY, "X-RapidAPI-Host": settings.BOOKING_COM15_HOST}


def _ih() -> Dict[str, str]:
    return {"X-RapidAPI-Key": settings.RAPIDAPI_KEY, "X-RapidAPI-Host": settings.IRCTC_HOST}


# ── Generic cache ──────────────────────────────────────────────────────────────

async def _cache_get(key: str) -> Optional[str]:
    try:
        doc = await get_db().cached_results.find_one({"cache_key": key})
        if doc and doc.get("value"):
            return doc["value"]
    except Exception:
        pass
    return None


async def _cache_set(key: str, value: str, ttl: int) -> None:
    try:
        await get_db().cached_results.update_one(
            {"cache_key": key},
            {"$set": {"cache_key": key, "value": value,
                      "expires_at": datetime.utcnow() + timedelta(seconds=ttl)}},
            upsert=True,
        )
    except Exception as e:
        logger.debug(f"Cache write failed: {e}")


def _ckey(*parts) -> str:
    return hashlib.md5("|".join(str(p) for p in parts).lower().encode()).hexdigest()


# ── Safe type helpers ─────────────────────────────────────────────────────────

def _str(v) -> str:
    return str(v).strip() if v is not None else ""


def _int(v, default=0) -> int:
    try:
        return int(float(v))
    except Exception:
        return default


def _float(v, default=0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


# ══════════════════════════════════════════════════════════════════════════════
# FLIGHTS
# ══════════════════════════════════════════════════════════════════════════════

_AIRLINE_NAMES = {
    "6E": "IndiGo", "AI": "Air India", "SG": "SpiceJet",
    "UK": "Vistara", "G8": "Go First", "I5": "AirAsia India",
    "QP": "Akasa Air", "9W": "Jet Airways",
}


class FlightsClient:

    async def search(self, origin: str, destination: str, travel_date: str,
                     return_date=None, passengers: int = 1,
                     cabin_class: str = "economy") -> List[FlightResult]:
        return await self._search(origin, destination, travel_date,
                                   return_date, passengers, cabin_class)

    @with_fallback(mock_flights)
    async def _search(self, origin: str, destination: str, travel_date: str,
                      return_date=None, passengers: int = 1,
                      cabin_class: str = "economy") -> List[FlightResult]:
        if not settings.RAPIDAPI_KEY:
            raise ValueError("RAPIDAPI_KEY not set")

        # Resolve IATA codes via india_cities DB first (no API call needed)
        origin_id = await self._get_loc_id(origin)
        dest_id   = await self._get_loc_id(destination)
        if not origin_id or not dest_id:
            raise ValueError(f"Cannot resolve flight locations: {origin}, {destination}")

        cabin_map = {"economy": "ECONOMY", "premium_economy": "PREMIUM_ECONOMY",
                     "business": "BUSINESS", "first": "FIRST"}
        params = {
            "fromId": origin_id, "toId": dest_id,
            "departDate": travel_date, "adults": passengers,
            "cabinClass": cabin_map.get(cabin_class, "ECONOMY"),
            "currency_code": "INR", "sort": "BEST", "page": 1,
        }
        async with httpx.AsyncClient(timeout=settings.API_TIMEOUT) as c:
            r = await c.get(f"{_BOOKING_BASE}/flights/searchFlights", headers=_bh(), params=params)
            r.raise_for_status()
            data = r.json()

        offers = ((data.get("data") or {}).get("flightOffers")
                  or data.get("flightOffers") or [])
        if not offers:
            raise ValueError("No flight offers returned")

        try:
            cab_enum = CabinClass(cabin_class)
        except Exception:
            cab_enum = CabinClass.ECONOMY

        results = []
        for offer in offers[:15]:
            try:
                p = self._parse(offer, cab_enum)
                if p:
                    results.append(p)
            except Exception as e:
                logger.debug(f"Flight parse error: {e}")

        if not results:
            raise ValueError("No parseable flight offers")
        logger.info(f"Flights: {len(results)} results for {origin}→{destination} on {travel_date}")
        return results

    async def _get_loc_id(self, city: str) -> Optional[str]:
        # Use india_cities IATA code as location ID first
        iata = get_iata(city)
        if iata:
            # booking-com15 expects location IDs in their format — cache resolved IDs
            cache_key = "floc:" + _ckey(city)
            cached = await _cache_get(cache_key)
            if cached:
                return cached

        # Search via API
        cache_key = "floc:" + _ckey(city)
        cached = await _cache_get(cache_key)
        if cached:
            return cached

        try:
            async with httpx.AsyncClient(timeout=settings.API_TIMEOUT) as c:
                r = await c.get(f"{_BOOKING_BASE}/flights/searchDestination",
                                headers=_bh(), params={"query": city})
                r.raise_for_status()
                items = r.json().get("data") or []
            for item in items:
                if item.get("type", "").upper() in ("AIRPORT", "CITY"):
                    loc_id = item.get("id", "")
                    if loc_id:
                        await _cache_set(cache_key, loc_id, settings.LOCATION_ID_CACHE_TTL)
                        return loc_id
            if items:
                loc_id = items[0].get("id", "")
                if loc_id:
                    await _cache_set(cache_key, loc_id, settings.LOCATION_ID_CACHE_TTL)
                    return loc_id
        except Exception as e:
            logger.debug(f"Flight location search failed for {city}: {e}")
            # Fall back to IATA code from our DB
            return get_iata(city)

        return get_iata(city)  # last resort from india_cities DB

    def _parse(self, offer: Dict, cab_enum: CabinClass) -> Optional[FlightResult]:
        segs_raw = offer.get("segments") or []
        if not segs_raw:
            return None
        outbound = segs_raw[0]
        legs_raw = outbound.get("legs") or []
        if not legs_raw:
            return None

        segs, total_secs = [], 0
        for leg in legs_raw:
            dep_ap  = leg.get("departureAirport") or {}
            arr_ap  = leg.get("arrivalAirport")   or {}
            fi      = leg.get("flightInfo")       or {}
            carrier = fi.get("carrierInfo")       or {}
            code    = _str(carrier.get("operatingCarrier") or carrier.get("marketingCarrier") or "XX")
            name    = _str(carrier.get("operatingCarrierName") or carrier.get("name")) or _AIRLINE_NAMES.get(code, code)
            leg_sec = _int(leg.get("totalTime"), 0)
            total_secs += leg_sec

            segs.append(FlightSegment(
                flight_number     = f"{code}{fi.get('flightNumber', '')}".strip() or "N/A",
                airline           = name,
                airline_code      = code,
                departure_airport = _str(dep_ap.get("code")),
                departure_city    = _str(dep_ap.get("cityName") or dep_ap.get("city")),
                departure_time    = _str(leg.get("departureTime")),
                arrival_airport   = _str(arr_ap.get("code")),
                arrival_city      = _str(arr_ap.get("cityName") or arr_ap.get("city")),
                arrival_time      = _str(leg.get("arrivalTime")),
                duration          = self._dur(leg_sec),
                aircraft          = leg.get("aircraftType"),
            ))

        price = self._price(offer)
        return FlightResult(
            segments=segs, total_duration=self._dur(total_secs),
            stops=max(0, len(legs_raw) - 1), cabin_class=cab_enum,
            price=price, currency="INR",
            baggage_allowance=self._baggage(offer),
            is_refundable=bool(offer.get("isFlexible")),
            source="booking-com15", is_mock=False,
        )

    def _price(self, offer: Dict) -> float:
        pb = offer.get("priceBreakdown") or {}
        t  = pb.get("total") or {}
        if t.get("units") is not None:
            return _float(t["units"]) + _float(t.get("nanos", 0)) / 1e9
        for tp in offer.get("travellerPrices") or []:
            po = (tp.get("travellerPriceBreakdown") or {}).get("total") or {}
            if po.get("units") is not None:
                return _float(po["units"]) + _float(po.get("nanos", 0)) / 1e9
        return 0.0

    def _baggage(self, offer: Dict) -> str:
        for seg in offer.get("segments") or []:
            for leg in seg.get("legs") or []:
                for bp in leg.get("baggagePolicies") or []:
                    d = bp.get("descriptions") or []
                    if d:
                        return d[0]
        return "15 kg check-in + 7 kg cabin"

    @staticmethod
    def _dur(seconds: int) -> str:
        if not seconds:
            return "N/A"
        h, r = divmod(int(seconds), 3600)
        return f"{h}h {r // 60}m"


# ══════════════════════════════════════════════════════════════════════════════
# HOTELS
# ══════════════════════════════════════════════════════════════════════════════

class HotelsClient:

    async def search(self, destination: str, check_in: str, check_out: str,
                     guests: int = 2, stars: int = None,
                     latitude: float = None, longitude: float = None,
                     meeting_lat: float = None, meeting_lng: float = None) -> List[HotelResult]:
        return await self._search(destination, check_in, check_out, guests,
                                   stars, latitude, longitude, meeting_lat, meeting_lng)

    @with_fallback(mock_hotels)
    async def _search(self, destination: str, check_in: str, check_out: str,
                      guests: int = 2, stars: int = None,
                      latitude: float = None, longitude: float = None,
                      meeting_lat: float = None, meeting_lng: float = None) -> List[HotelResult]:
        if not settings.RAPIDAPI_KEY:
            raise ValueError("RAPIDAPI_KEY not set")

        dest_id = await self._get_dest_id(destination)
        if not dest_id:
            raise ValueError(f"Cannot resolve hotel destination: {destination}")

        params = {
            "dest_id": dest_id, "search_type": "city",
            "arrival_date": check_in, "departure_date": check_out,
            "adults": guests, "room_qty": 1, "page_number": 1,
            "units": "metric", "languagecode": "en-us", "currency_code": "INR",
        }
        async with httpx.AsyncClient(timeout=settings.API_TIMEOUT) as c:
            r = await c.get(f"{_BOOKING_BASE}/hotels/searchHotels", headers=_bh(), params=params)
            r.raise_for_status()
            data = r.json()

        raw = ((data.get("data") or {}).get("hotels")
               or data.get("hotels") or [])
        if not raw:
            raise ValueError("No hotels returned")

        results = []
        for h in raw[:20]:
            try:
                parsed = self._parse(h, destination, meeting_lat, meeting_lng)
                if parsed:
                    results.append(parsed)
            except Exception as e:
                logger.debug(f"Hotel parse error: {e}")

        if not results:
            raise ValueError("No parseable hotels")
        logger.info(f"Hotels: {len(results)} for {destination}")
        return results

    async def _get_dest_id(self, city: str) -> Optional[str]:
        cache_key = "hdest:" + _ckey(city)
        cached = await _cache_get(cache_key)
        if cached:
            return cached
        try:
            async with httpx.AsyncClient(timeout=settings.API_TIMEOUT) as c:
                r = await c.get(f"{_BOOKING_BASE}/hotels/searchDestination",
                                headers=_bh(), params={"query": city})
                r.raise_for_status()
                items = r.json().get("data") or []
            for item in items:
                if (item.get("dest_type") or "").lower() == "city":
                    dest_id = _str(item.get("dest_id") or item.get("id"))
                    if dest_id:
                        await _cache_set(cache_key, dest_id, settings.LOCATION_ID_CACHE_TTL)
                        return dest_id
            if items:
                dest_id = _str(items[0].get("dest_id") or items[0].get("id"))
                if dest_id:
                    await _cache_set(cache_key, dest_id, settings.LOCATION_ID_CACHE_TTL)
                    return dest_id
        except Exception as e:
            logger.error(f"Hotel dest search failed for {city}: {e}")
        return None

    def _parse(self, h: Dict, city_name: str,
               meeting_lat: float = None, meeting_lng: float = None) -> Optional[HotelResult]:
        prop = h.get("property") or h
        name = _str(prop.get("name") or h.get("name")) or "Unnamed Hotel"
        if len(name) > 100:
            name = name[:97] + "..."
        hotel_id = _str(h.get("hotel_id") or prop.get("hotel_id")) or ""
        stars = min(5, max(1, _int(prop.get("accuratePropertyClass") or prop.get("propertyClass") or h.get("class"), 3)))
        score = min(10.0, max(0.0, _float(prop.get("reviewScore") or h.get("review_score"), 0.0)))
        review_count = _int(prop.get("reviewCount") or h.get("review_nr"), 0)
        pb    = prop.get("priceBreakdown") or h.get("priceBreakdown") or {}
        gross = pb.get("grossPrice") or pb.get("total") or {}
        price = _float(gross.get("value") or gross.get("units") or h.get("min_total_price"), 0.0)
        lat   = _float(prop.get("latitude") or h.get("latitude"), None)
        lng   = _float(prop.get("longitude") or h.get("longitude"), None)

        amenities = [_str(f.get("name") or f.get("facilityName"))
                     for f in (prop.get("facilities") or [])
                     if (f.get("name") or f.get("facilityName"))][:8]

        # Distance from meeting venue (Feature 5)
        dist_meeting = None
        if meeting_lat and meeting_lng and lat and lng:
            dist_meeting = self._haversine(lat, lng, meeting_lat, meeting_lng)

        photos = prop.get("photoUrls") or []
        return HotelResult(
            hotel_id=hotel_id or f"bk_{name[:6].lower().replace(' ', '_')}",
            name=name, rating=round(score / 2, 1), stars=stars,
            address=_str(prop.get("address") or h.get("address")) or city_name.title(),
            city=city_name.title(), latitude=lat, longitude=lng,
            price_per_night=price, currency="INR", amenities=amenities,
            distance_from_center=_float(prop.get("distanceToCityCenter") or h.get("distance_to_cc"), 0.0),
            distance_from_meeting=round(dist_meeting, 2) if dist_meeting else None,
            review_score=score, review_count=review_count,
            breakfast_included=bool(prop.get("isBreakfastIncluded") or h.get("breakfast_included")),
            free_cancellation=bool(prop.get("isFreeCancellable") or h.get("is_free_cancellable")),
            image_url=photos[0] if photos and isinstance(photos[0], str) else None,
            source="booking-com15", is_mock=False,
        )

    @staticmethod
    def _haversine(lat1, lon1, lat2, lon2) -> float:
        """Distance in km between two lat/lng points."""
        import math
        R = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi   = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


# ══════════════════════════════════════════════════════════════════════════════
# TRAINS
# ══════════════════════════════════════════════════════════════════════════════

class TrainsClient:

    async def search(self, origin: str, destination: str, travel_date: str,
                     train_class: str = None) -> List[TrainResult]:
        return await self._search(origin, destination, travel_date, train_class)

    @with_fallback(mock_trains)
    async def _search(self, origin: str, destination: str, travel_date: str,
                      train_class: str = None) -> List[TrainResult]:
        if not settings.RAPIDAPI_KEY:
            raise ValueError("RAPIDAPI_KEY not set")

        from_code = await self._get_station(origin)
        to_code   = await self._get_station(destination)
        if not from_code or not to_code:
            raise ValueError(f"Cannot resolve station codes: {origin}, {destination}")

        try:
            dt = datetime.strptime(travel_date, "%Y-%m-%d")
            irctc_date = dt.strftime("%d-%m-%Y")
        except Exception:
            irctc_date = travel_date

        async with httpx.AsyncClient(timeout=settings.API_TIMEOUT) as c:
            r = await c.get(
                f"{_IRCTC_BASE}/railway/trainBetweenStations",
                headers=_ih(),
                params={"fromStationCode": from_code, "toStationCode": to_code, "dateOfJourney": irctc_date},
            )
            print("Train Status:", r.status_code)
            print("Train Response:", r.text[:500])
            r.raise_for_status()
            data = r.json()

        raw = data.get("data") or []
        if not raw:
            raise ValueError(f"No trains between {from_code} and {to_code}")

        results = []
        for t in raw[:12]:
            try:
                parsed = self._parse(t, origin, destination, travel_date)
                if parsed:
                    results.append(parsed)
            except Exception as e:
                logger.debug(f"Train parse error: {e}")

        if not results:
            raise ValueError("No parseable trains")
        logger.info(f"Trains: {len(results)} for {from_code}→{to_code}")
        return results[:10]

    async def _get_station(self, city: str) -> Optional[str]:
        # india_cities DB first — covers all major Indian stations
        code = get_station_code(city)
        if code:
            return code

        cache_key = "stn:" + _ckey(city)
        cached = await _cache_get(cache_key)
        if cached:
            return cached

        try:
            async with httpx.AsyncClient(timeout=settings.API_TIMEOUT) as c:
                r = await c.get(f"{_IRCTC_BASE}/railway/searchStation",
                                headers=_ih(), params={"query": city})
                r.raise_for_status()
                items = r.json().get("data") or []

            if not items:
                return None

            code = self._best_station(items, city)
            if code:
                await _cache_set(cache_key, code, settings.LOCATION_ID_CACHE_TTL)
            return code
        except Exception as e:
            logger.error(f"Station search failed for {city}: {e}")
        return None

    def _best_station(self, items: List[Dict], city: str) -> Optional[str]:
        city_lower = city.strip().lower()
        best_code, best_score = None, -1
        for item in items:
            name = _str(item.get("stationName") or item.get("station_name")).lower()
            code = _str(item.get("stationCode") or item.get("station_code") or item.get("code")).upper()
            if not code:
                continue
            score = 0
            if name == city_lower:         score = 100
            elif any(kw in name for kw in ("central", "junction", "main", "terminus")): score = 50
            elif name.startswith(city_lower): score = 30
            elif city_lower in name:          score = 10
            if score > best_score:
                best_score = score
                best_code = code
        if not best_code and items:
            best_code = _str(items[0].get("stationCode") or items[0].get("code")).upper() or None
        return best_code

    def _parse(self, t: Dict, origin: str, destination: str, travel_date: str) -> Optional[TrainResult]:
        num  = _str(t.get("trainNumber") or t.get("train_number")) or "N/A"
        name = (_str(t.get("trainName") or t.get("train_name")) or f"Train {num}").title()
        from_code = _str(t.get("fromStationCode") or t.get("from_station_code")).upper() or get_station_code(origin) or origin[:4].upper()
        to_code   = _str(t.get("toStationCode")   or t.get("to_station_code")).upper()   or get_station_code(destination) or destination[:4].upper()
        dep = _str(t.get("departureTime") or t.get("departure_time")) or "N/A"
        arr = _str(t.get("arrivalTime")   or t.get("arrival_time"))   or "N/A"
        raw_dur = _str(t.get("duration"))
        if ":" in raw_dur and "h" not in raw_dur:
            p = raw_dur.split(":")
            dur = f"{p[0]}h {p[1]}m" if len(p) >= 2 else raw_dur
        else:
            dur = raw_dur or "N/A"

        ro = t.get("runsOn") or {}
        day_map = {"monday":"Mon","tuesday":"Tue","wednesday":"Wed","thursday":"Thu",
                   "friday":"Fri","saturday":"Sat","sunday":"Sun"}
        runs_on = [v for k, v in day_map.items() if ro.get(k)] or list(day_map.values())

        class_labels = {"1A":"1st AC","2A":"2nd AC","3A":"3rd AC","SL":"Sleeper",
                        "CC":"Chair Car","EC":"Exec Chair","2S":"2nd Sitting"}
        classes = []
        for cls in (t.get("classesAvailable") or t.get("classes") or []):
            code = _str(cls.get("classCode") or cls.get("code")).upper()
            if not code:
                continue
            classes.append(TrainClassInfo(
                class_code=code,
                class_name=class_labels.get(code, code),
                available_seats=_int(cls.get("availableSeats") or cls.get("available_seats"), 0),
                price=_float(cls.get("fare") or cls.get("price"), 0.0),
            ))
        if not classes:
            classes = [
                TrainClassInfo(class_code="SL", class_name="Sleeper", available_seats=0, price=0.0),
                TrainClassInfo(class_code="3A", class_name="3rd AC",  available_seats=0, price=0.0),
            ]

        return TrainResult(
            train_number=num, train_name=name,
            origin_station=f"{origin.title()} ({from_code})", origin_code=from_code,
            destination_station=f"{destination.title()} ({to_code})", destination_code=to_code,
            departure_time=dep, arrival_time=arr, duration=dur, travel_date=travel_date,
            classes=classes, runs_on=runs_on, source="irctc1", is_mock=False,
        )


# ══════════════════════════════════════════════════════════════════════════════
# BUSES (mock only)
# ══════════════════════════════════════════════════════════════════════════════

class BusesClient:
    async def search(self, origin: str, destination: str, travel_date: str = None) -> List[BusResult]:
        return await self._search(origin, destination, travel_date)

    @with_fallback(mock_buses)
    async def _search(self, origin: str, destination: str, travel_date: str = None) -> List[BusResult]:
        raise NotImplementedError("Bus API not available")


# ══════════════════════════════════════════════════════════════════════════════
# CARS
# ══════════════════════════════════════════════════════════════════════════════

class CarsClient:

    async def search(self, location: str, pickup_date: str = None,
                     return_date: str = None,
                     latitude: float = None, longitude: float = None) -> List[CarResult]:
        return await self._search(location, pickup_date, return_date, latitude, longitude)

    @with_fallback(mock_cars)
    async def _search(self, location: str, pickup_date: str = None,
                      return_date: str = None,
                      latitude: float = None, longitude: float = None) -> List[CarResult]:
        if not settings.RAPIDAPI_KEY:
            raise ValueError("RAPIDAPI_KEY not set")

        loc_id = await self._get_loc_id(location)
        if not loc_id:
            raise ValueError(f"Cannot resolve car location: {location}")

        p_date = pickup_date or datetime.now().strftime("%Y-%m-%d")
        r_date = return_date or (datetime.strptime(p_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

        params = {
            "pick_up_place_id": loc_id, "pick_up_date": p_date, "pick_up_time": "10:00",
            "drop_off_place_id": loc_id, "drop_off_date": r_date, "drop_off_time": "10:00",
            "currency_code": "INR", "driver_age": 30,
        }
        async with httpx.AsyncClient(timeout=settings.API_TIMEOUT) as c:
            r = await c.get(f"{_BOOKING_BASE}/cars/searchCarRentals", headers=_bh(), params=params)
            r.raise_for_status()
            data = r.json()

        raw = ((data.get("data") or {}).get("searchResults")
               or data.get("searchResults") or data.get("cars") or [])
        if not raw:
            raise ValueError("No cars returned")

        results = []
        for car in raw[:15]:
            try:
                parsed = self._parse(car, location)
                if parsed:
                    results.append(parsed)
            except Exception as e:
                logger.debug(f"Car parse error: {e}")

        if not results:
            raise ValueError("No parseable cars")
        logger.info(f"Cars: {len(results)} for {location}")
        return sorted(results, key=lambda c: c.price_per_day)[:10]

    async def _get_loc_id(self, location: str) -> Optional[str]:
        cache_key = "carloc:" + _ckey(location)
        cached = await _cache_get(cache_key)
        if cached:
            return cached
        try:
            async with httpx.AsyncClient(timeout=settings.API_TIMEOUT) as c:
                r = await c.get(f"{_BOOKING_BASE}/cars/searchDestination",
                                headers=_bh(), params={"query": location})
                r.raise_for_status()
                items = r.json().get("data") or []
            if items:
                loc_id = _str(items[0].get("id") or items[0].get("dest_id"))
                if loc_id:
                    await _cache_set(cache_key, loc_id, settings.LOCATION_ID_CACHE_TTL)
                    return loc_id
        except Exception as e:
            logger.error(f"Car location search failed for {location}: {e}")
        return None

    def _parse(self, c: Dict, location: str) -> Optional[CarResult]:
        vi       = c.get("vehicle_info") or c.get("vehicleInfo") or c or {}
        supplier = c.get("supplier") or c.get("supplierInfo") or {}
        pricing  = c.get("pricing")  or c.get("price")        or {}
        name     = _str(vi.get("name") or vi.get("vehicle_name") or c.get("name")) or "Vehicle"
        vtype    = _str(vi.get("type") or vi.get("vehicle_type") or c.get("type")).lower() or "sedan"
        seats    = max(1, _int(vi.get("seats") or vi.get("passengerQuantity") or c.get("seats"), 4))
        trans    = _str(vi.get("transmission") or vi.get("gearbox")).lower() or "manual"
        fuel     = _str(vi.get("fuel_policy") or vi.get("fuelType")) or "Petrol"
        price_obj = pricing.get("price") or pricing.get("total") or pricing or {}
        price = _float(price_obj.get("amount") or price_obj.get("value") or price_obj.get("units") or c.get("price"), 0.0)
        vendor = _str(supplier.get("name") or supplier.get("supplier_name") or c.get("supplier_name")) or "RentalCo"
        features = list(vi.get("features") or vi.get("extras") or []) or ["AC", "GPS"]
        return CarResult(
            vehicle_name=name, vehicle_type=vtype, vendor=vendor,
            fuel_type=fuel, seats=seats, transmission=trans,
            pickup_location=location.title(), price_per_day=price, currency="INR",
            features=features[:6], source="booking-com15", is_mock=False,
        )


# ── Singletons ────────────────────────────────────────────────────────────────
flights_client = FlightsClient()
hotels_client  = HotelsClient()
trains_client  = TrainsClient()
buses_client   = BusesClient()
cars_client    = CarsClient()
