"""
Hotels, Trains, Buses, Cars API Clients.

Hotels  → booking-com15 RapidAPI  (2 endpoints: searchDestination + searchHotels)
Trains  → irctc1 RapidAPI         (2 endpoints: SearchStation + TrainsBetweenStations V3)
Cars    → booking-com15 RapidAPI  (2 endpoints: searchDestination + searchCarRentals)
Buses   → mock only (no public API available)

All clients fall back to rich mock data automatically on any failure.
"""

import httpx
import hashlib
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from config.settings import settings
from models.travel import (
    HotelResult, TrainResult, TrainClass_Info,
    BusResult, CarResult,
)
from utils.fallback import with_fallback, mock_hotels, mock_trains, mock_buses, mock_cars
from database.connection import get_db

logger = logging.getLogger(__name__)

# Base URLs
_BOOKING_BASE = "https://booking-com15.p.rapidapi.com/api/v1"
_IRCTC_BASE = "https://irctc1.p.rapidapi.com"


def _booking_headers() -> Dict[str, str]:
    return {
        "X-RapidAPI-Key":  settings.RAPIDAPI_KEY,
        "X-RapidAPI-Host": settings.BOOKING_COM15_HOST,
    }


def _irctc_headers() -> Dict[str, str]:
    return {
        "X-RapidAPI-Key":  settings.RAPIDAPI_KEY,
        "X-RapidAPI-Host": settings.IRCTC_HOST,
    }


# ── Generic cache helpers ─────────────────────────────────────────────────────

async def _read_cache(key: str) -> Optional[str]:
    try:
        doc = await get_db().cached_results.find_one({"cache_key": key})
        if doc and doc.get("value"):
            return doc["value"]
    except Exception:
        pass
    return None


async def _write_cache(key: str, value: str, ttl: int) -> None:
    try:
        await get_db().cached_results.update_one(
            {"cache_key": key},
            {"$set": {
                "cache_key": key,
                "value": value,
                "expires_at": datetime.utcnow() + timedelta(seconds=ttl),
            }},
            upsert=True,
        )
    except Exception as e:
        logger.debug(f"Cache write failed ({key}): {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# HOTELS CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class HotelsClient:

    async def search(
        self,
        destination: str,
        check_in: str,
        check_out: str,
        guests: int = 2,
        stars: Optional[int] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> List[HotelResult]:
        return await self._search_with_fallback(
            destination,
            check_in,
            check_out,
            guests,
            stars,
            latitude,
            longitude,
        )

    @with_fallback(mock_hotels)
    async def _search_with_fallback(
        self,
        destination: str,
        check_in: str,
        check_out: str,
        guests: int = 2,
        stars: Optional[int] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> List[HotelResult]:

        if not settings.RAPIDAPI_KEY:
            raise ValueError("RAPIDAPI_KEY not configured — using mock data")

        result = await self._get_destination_id(destination)

        if not result:
            raise ValueError(
                f"Could not resolve hotel destination ID for '{destination}'"
            )

        dest_id, search_type = result

        return await self._search_hotels(
            dest_id,
            search_type,
            destination,
            check_in,
            check_out,
            guests,
            stars,
        )

    # ─────────────────────────────────────────────────────────────
    # STEP 1: searchDestination
    # ─────────────────────────────────────────────────────────────

    async def _get_destination_id(self, city: str):
        """
        Returns:
            (dest_id, search_type)
        """

        cache_key = (
            "hotel_dest:"
            + hashlib.md5(city.strip().lower().encode()).hexdigest()
        )

        cached = await _read_cache(cache_key)
        if cached:
            logger.debug(f"Hotel destination cache hit: {city}")
            return tuple(cached)

        try:
            async with httpx.AsyncClient(
                timeout=settings.API_TIMEOUT
            ) as client:

                resp = await client.get(
                    f"{_BOOKING_BASE}/hotels/searchDestination",
                    headers=_booking_headers(),
                    params={"query": city},
                )

                resp.raise_for_status()
                data = resp.json()
                print("\n========== HOTEL RESPONSE ==========")
                print(data)
                print("====================================")

            items = data.get("data") or []

            if not items:
                logger.warning(f"No destination found for {city}")
                return None

            dest_id = None
            search_type = "CITY"

            # Prefer CITY
            for item in items:
                if (item.get("dest_type") or "").lower() == "city":
                    dest_id = str(item.get("dest_id") or item.get("id", ""))

                    search_type = (
                        item.get("search_type")
                        or item.get("dest_type")
                        or "CITY"
                    )

                    break

            # Fallback to first result
            if not dest_id:
                first = items[0]

                dest_id = str(
                    first.get("dest_id") or first.get("id", "")
                )

                search_type = (
                    first.get("search_type")
                    or first.get("dest_type")
                    or "CITY"
                )

            if dest_id:
                value = (dest_id, search_type)

                await _write_cache(
                    cache_key,
                    value,
                    settings.LOCATION_ID_CACHE_TTL,
                )

                logger.info(
                    f"Resolved hotel destination: {city} → "
                    f"{dest_id} ({search_type})"
                )

                return value

            return None

        except Exception as e:
            logger.exception(
                f"searchDestination failed for '{city}': {e}"
            )
            raise

    # ─────────────────────────────────────────────────────────────
    # STEP 2: searchHotels
    # ─────────────────────────────────────────────────────────────

    async def _search_hotels(
        self,
        dest_id: str,
        search_type: str,
        city_name: str,
        check_in: str,
        check_out: str,
        guests: int = 2,
        stars: Optional[int] = None,
    ) -> List[HotelResult]:

        params = {
            "dest_id": dest_id,
            "search_type": search_type,
            "arrival_date": check_in,
            "departure_date": check_out,
            "adults": guests,
            "room_qty": 1,
            "page_number": 1,
            "units": "metric",
            "temperature_unit": "c",
            "languagecode": "en-us",
            "currency_code": "INR",
        }

        async with httpx.AsyncClient(
            timeout=settings.API_TIMEOUT
        ) as client:

            resp = await client.get(
                f"{_BOOKING_BASE}/hotels/searchHotels",
                headers=_booking_headers(),
                params=params,
            )

            resp.raise_for_status()

            data = resp.json()

            print("\n================ HOTEL API RESPONSE ================")
            print(data)
            print("====================================================")

        hotels_raw = (
            (data.get("data") or {}).get("hotels")
            or (data.get("data") or {}).get("results")
            or data.get("hotels")
            or []
        )

        if not hotels_raw:
            logger.warning(
                f"No hotels returned for {city_name}"
            )
            return []

        hotels_raw = sorted(
            hotels_raw,
            key=lambda x: (
                float(x.get("property", {}).get("propertyClass", 0)),
                float(x.get("property", {}).get("reviewScore", 0))
            ),
            reverse=True,
        )

        results: List[HotelResult] = []

        for h in hotels_raw[:20]:

            try:
                hotel = self._parse_hotel(
                    h,
                    city_name,
                )

                if stars and hotel.stars:
                    if hotel.stars != stars:
                        continue

                results.append(hotel)

            except Exception as e:
                logger.exception(
                    f"Failed to parse hotel: {e}"
                )

        return results

    # ─────────────────────────────────────────────────────────────
    # Parse Hotel
    # ─────────────────────────────────────────────────────────────

    def _parse_hotel(
        self,
        h: dict,
        city_name: str,
    ) -> HotelResult:

        prop = h.get("property", {})

        name = (
            prop.get("name")
            or h.get("hotel_name")
            or h.get("name")
            or "Unknown Hotel"
        )

        review_score_raw = float(
            prop.get("reviewScore")
            or h.get("reviewScore")
            or 0
        )

        price = float(
            prop.get("priceBreakdown", {})
            .get("grossPrice", {})
            .get("value")
            or h.get("price", 0)
            or 0
        )

        star_raw = (
            prop.get("propertyClass")
            or prop.get("starRating")
            or h.get("stars")
            or 3
        )

        return HotelResult(
            hotel_id=f"hotel_{name[:10].replace(' ', '_')}",
            name=name,
            rating=review_score_raw,
            review_score=review_score_raw,
            stars=max(1, min(5, int(float(star_raw or 3)))),
            address=city_name.title(),
            city=city_name.title(),
            price_per_night=price,
            currency="INR",
            source="booking-com15",
            is_mock=False,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINS CLIENT  (IRCTC1 RapidAPI)
# ═══════════════════════════════════════════════════════════════════════════════

class TrainsClient:
    STATIC_STATIONS = {
        "ahmedabad": "ADI",
        "mumbai": "MMCT",
        "delhi": "NDLS",
        "bangalore": "SBC",
        "pune": "PUNE",
        "surat": "ST",
        "rajkot": "RJT",
        "chennai": "MAS",
        "hyderabad": "HYB"
    }
    async def search(
        self,
        origin: str,
        destination: str,
        travel_date: str,
        train_class: Optional[str] = None,
    ) -> List[TrainResult]:
        return await self._search_with_fallback(
            origin, destination, travel_date, train_class
        )

    @with_fallback(mock_trains)
    async def _search_with_fallback(
        self,
        origin: str,
        destination: str,
        travel_date: str = None,
        *args,
        **kwargs
    ) -> List[TrainResult]:
        if not settings.RAPIDAPI_KEY:
            raise ValueError("RAPIDAPI_KEY not configured — using mock data")

        # Step 1: Resolve station codes for both cities
        origin_code = await self._get_station_code(origin)
        dest_code   = await self._get_station_code(destination)

        if not origin_code or not dest_code:
            raise ValueError(
                f"Could not resolve station codes for '{origin}' or '{destination}'"
            )

        # Step 2: Trains Between Stations V3
        return await self._trains_between_stations(
            origin_code, dest_code, origin, destination, travel_date
        )

    # ── Step 1: SearchStation ─────────────────────────────────────────────────

    async def _get_station_code(self, city: str) -> Optional[str]:
        """
        Endpoint: GET /api/v1/railway/searchStation
        Param: query=<city name>
        Returns station code (e.g. "NDLS" for New Delhi).
        Cached 7 days.

        Many Indian cities have multiple stations (Delhi: NDLS, DLI, NZM,
        ANVT; Mumbai: CSTM, BCT, BDTS...). Picking items[0] blindly is the
        bug that caused "wrong station for city" — instead we score all
        candidates and prefer the one whose name most closely matches the
        city query (favoring "Central"/"Junction"/"Main" terminals, which
        are nearly always the primary station for that city).
        """
        city_lower = city.strip().lower()

        if city_lower in self.STATIC_STATIONS:
            logger.info(
                f"Using static station code: {city} → {self.STATIC_STATIONS[city_lower]}"
            )
            return self.STATIC_STATIONS[city_lower]
        cache_key = "station:" + hashlib.md5(city.strip().lower().encode()).hexdigest()
        cached = await _read_cache(cache_key)
        if cached:
            logger.debug(f"Station cache hit: {city} → {cached}")
            return cached

        try:
            async with httpx.AsyncClient(timeout=settings.API_TIMEOUT) as client:
                resp = await client.get(
                    f"{_IRCTC_BASE}/railway/searchStation",
                    headers=_irctc_headers(),
                    params={"query": city},
                )
                resp.raise_for_status()
                data = resp.json()
                print("\n========== TRAIN API RESPONSE ==========")
                print(data)
                print("========================================\n")

            # Response: {"status": true, "data": [{"stationCode": "NDLS", "stationName": "...", ...}]}
            items = data.get("data") or []
            if not items:
                logger.warning(f"No station found for: {city}")
                return None

            code = self._pick_best_station(items, city)

            if code:
                await _write_cache(cache_key, code, settings.LOCATION_ID_CACHE_TTL)
                logger.info(f"Resolved station: {city} → {code} (from {len(items)} candidates)")

            return code or None

        except Exception as e:
            logger.error(f"SearchStation failed for '{city}': {e}")
            return None

    def _pick_best_station(self, items: List[Dict], city: str) -> Optional[str]:
        """
        Score station candidates and return the best match's code.
        Preference order:
          1. Station name exactly equals the city name
          2. Station name contains "central"/"junction"/"main"/"terminus"
          3. Station name starts with the city name
          4. First result (last resort)
        """
        city_lower = city.strip().lower()
        if city_lower in self.STATIC_STATIONS:
            return self.STATIC_STATIONS[city_lower]
        best_code = None
        best_score = -1

        for item in items:
            name = (item.get("stationName") or item.get("station_name") or "").lower()
            code = (
                item.get("stationCode")
                or item.get("station_code")
                or item.get("code")
                or ""
            ).upper()
            if not code:
                continue

            score = 0
            if name == city_lower:
                score = 100
            elif any(kw in name for kw in ("central", "junction", "main", "terminus")):
                score = 50
            elif name.startswith(city_lower):
                score = 30
            elif city_lower in name:
                score = 10

            if score > best_score:
                best_score = score
                best_code = code

        # Fallback: first item with any code at all
        if not best_code:
            for item in items:
                code = (
                    item.get("stationCode")
                    or item.get("station_code")
                    or item.get("code")
                    or ""
                ).upper()
                if code:
                    return code

        return best_code

    # ── Safe type conversion helpers (trains) ───────────────────────────────
    @staticmethod
    def _safe_str_train(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _safe_int_train(value: Any, default: int = 0) -> int:
        if value is None:
            return default
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_float_train(value: Any, default: float = 0.0) -> float:
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    # ── Step 2: TrainsBetweenStations V3 ──────────────────────────────────────

    async def _trains_between_stations(
        self,
        from_code: str,
        to_code: str,
        origin_name: str,
        dest_name: str,
        travel_date: str,
    ) -> List[TrainResult]:
        """
        Endpoint: GET /api/v1/railway/trainBetweenStations
        Params: fromStationCode, toStationCode, dateOfJourney (DD-MM-YYYY)
        """
        # IRCTC API expects DD-MM-YYYY. travel_date should already be
        # normalised to YYYY-MM-DD by extract_date()'s dateparser pipeline —
        # if it isn't (invalid format slipped through), log it loudly rather
        # than silently sending a malformed date that returns 0 trains with
        # no indication why.
        irctc_date = datetime.strptime(
            travel_date,
            "%Y-%m-%d"
        ).strftime("%d-%m-%Y")
        async with httpx.AsyncClient(timeout=settings.API_TIMEOUT) as client:
            resp = await client.get(
                f"{_IRCTC_BASE}/api/v3/trainBetweenStations",
                headers=_irctc_headers(),
                params={
                    "fromStationCode": from_code,
                    "toStationCode":   to_code,
                    "dateOfJourney":   irctc_date,
                },
            )

            resp.raise_for_status()
            data = resp.json()
            print("\n========== TRAINS BETWEEN STATIONS ==========")
            print(data)
            print("=============================================\n")
            if not data.get("data"):
                logger.warning(
                    f"IRCTC1 returned 0 trains between {from_code} and {to_code} on {irctc_date}"
                )
                raise ValueError(
                    f"No trains returned between {from_code} and {to_code}"
                )

        # Response: {"status": true, "data": [{"trainNumber": "12951", "trainName": "...", ...}]}
        trains_raw = data.get("data") or []
        if not trains_raw:
            logger.warning(f"IRCTC1 returned 0 trains between {from_code} and {to_code} on {irctc_date}")
            raise ValueError(
                f"No trains returned between {from_code} and {to_code}"
            )

        results = []

        for t in trains_raw:

            train_type = t.get("train_type")
            if train_type in ["PASS", "PASSENGER"]:
                continue

            # skip wrong terminals (Panvel, Bandra, etc.)
            from_station_name = (
                t.get("from_station_name", "")
            ).upper()

            to_station_name = (
                t.get("to_station_name", "")
            ).upper()


            try:
                parsed = self._parse_train(
                    t,
                    origin_name,
                    dest_name,
                    travel_date
                )

                if parsed:
                    results.append(parsed)

            except Exception as e:
                logger.debug(f"Failed to parse train: {e}")

        if not results:
            logger.warning(f"All {len(trains_raw)} trains failed to parse for {from_code}→{to_code}")
            raise ValueError("No parseable trains in response")

        logger.info(f"Parsed {len(results)} trains for {from_code} → {to_code} ({irctc_date})")
        results.sort(
            key=lambda x: (
                x.classes[0].price
                if x.classes else 99999
            )
        )
        print("travel_date =", travel_date)

        return results[:10]  # cap to top 10

    def _parse_train(
        self,
        t: Dict,
        origin_name: str,
        dest_name: str,
        travel_date: str,
    ) -> Optional[TrainResult]:

        # Train number and name
        train_num = self._safe_str_train(
            t.get("train_number")
            or t.get("trainNumber")
        )

        train_name_raw = self._safe_str_train(
            t.get("train_name")
            or t.get("trainName")
        )

        train_name = (
            train_name_raw.title()
            if train_name_raw
            else f"Train {train_num or 'Unknown'}"
        )

        remove_words = [
            "New Delhi - ",
            "Hazrat Nizamuddin - ",
            "Delhi Hazrat Nizamuddin - ",
            "Delhi Sarai Rohilla - ",
            "Mumbai Central - ",
            "Mumbai Csmt - ",
            "Mumbai Bandra T - ",
            "Bandra T - "
        ]

        for word in remove_words:
            train_name = train_name.replace(word, "")

        train_name = " ".join(train_name.split())

        # Station codes
        from_code = origin_name[:3].upper()
        to_code = dest_name[:3].upper()

        # Station names
        origin_station = origin_name.title()
        destination_station = dest_name.title()

        # Departure and arrival times
        dep_time = (
            t.get("from_std")
            or t.get("departureTime")
            or ""
        )

        arr_time = (
            t.get("to_std")
            or t.get("arrivalTime")
            or ""
        )

        # Duration
        # Duration
        raw_dur = str(t.get("duration") or "")

        parts = raw_dur.split(":")

        if len(parts) >= 2:
            h = parts[0]
            m = parts[1]
            dur = f"{h}h {m.zfill(2)}m"
        else:
            dur = raw_dur or "N/A"
        run_days = t.get("run_days", [])

        if isinstance(run_days, list):
            runs_on = run_days
        else:
            runs_on = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

        if not runs_on:
            runs_on = day_map[1:] + [day_map[0]]  # Mon-Sun

        # Classes
        # Classes
        class_codes = t.get("class_type", [])

        if isinstance(class_codes, str):
            class_codes = [
                c.strip()
                for c in class_codes.split(",")
                if c.strip()
            ]

        class_price = {
            "SL": 480,
            "CC": 680,
            "3A": 1285,
            "2A": 1840,
            "1A": 3155
        }

        class_labels = {
            "SL": "Sleeper",
            "CC": "Chair Car",
            "3A": "3rd AC",
            "2A": "2nd AC",
            "1A": "1st AC"
        }

        classes = []

        for code in class_codes:
            classes.append(
                TrainClass_Info(
                    class_code=code,
                    class_name=class_labels.get(code, code),
                    available_seats=20,
                    price=class_price.get(code, 1000)
                )
            )

        # Fallback if API returned no classes
        if not classes:
            classes = [
                TrainClass_Info(
                    class_code="SL",
                    class_name="Sleeper",
                    available_seats=0,
                    price=0
                ),
                TrainClass_Info(
                    class_code="3A",
                    class_name="3rd AC",
                    available_seats=0,
                    price=0
                )
            ]

        return TrainResult(
            train_number=train_num or "N/A",
            train_name=train_name,

            origin_station=origin_station,
            origin_code=from_code,

            destination_station=destination_station,
            destination_code=to_code,

            departure_time=dep_time or "N/A",
            arrival_time=arr_time or "N/A",

            duration=dur,
            travel_date=travel_date,

            classes=classes,
            runs_on=runs_on,

            source="irctc1",
            is_mock=False,
        )

# ═══════════════════════════════════════════════════════════════════════════════
# BUSES CLIENT  (mock only — no public API)
# ═══════════════════════════════════════════════════════════════════════════════

class BusesClient:

    async def search(
        self,
        origin: str,
        destination: str,
        travel_date: str = None,
    ) -> List[BusResult]:
        return await self._search_with_fallback(origin, destination, travel_date)

    @with_fallback(mock_buses)
    async def _search_with_fallback(
        self,
        origin: str,
        destination: str,
        travel_date: str = None,
    ) -> List[BusResult]:
        # No public bus API — always fall through to mock
        raise NotImplementedError("Bus API not available — using mock data")


# ═══════════════════════════════════════════════════════════════════════════════
# CARS CLIENT  (booking-com15 RapidAPI)
# ═══════════════════════════════════════════════════════════════════════════════

class CarsClient:

    async def search(
        self,
        location: str,
        pickup_date: str = None,
        return_date: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> List[CarResult]:
        return await self._search_with_fallback(
            location, pickup_date, return_date, latitude, longitude
        )

    @with_fallback(mock_cars)
    async def _search_with_fallback(
        self,
        location: str,
        pickup_date: str = None,
        return_date: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> List[CarResult]:
        if not settings.RAPIDAPI_KEY:
            raise ValueError("RAPIDAPI_KEY not configured — using mock data")

        # Step 1: Search Car Location → get pick-up location ID
        lat_lon = await self._get_car_coordinates(location)

        if not lat_lon:
            raise ValueError(
                f"Could not resolve coordinates for '{location}'"
            )

        lat, lon = lat_lon

        return await self._search_car_rentals(
            lat,
            lon,
            location,
            pickup_date,
            return_date,
        )

    # ── Step 1: Search Car Location ───────────────────────────────────────────

    async def _get_car_coordinates(
        self,
        location: str
    ) -> Optional[tuple[float, float]]:
        """
        Endpoint:
            GET /api/v1/cars/searchDestination

        Returns:
            (latitude, longitude)
        """

        cache_key = (
            "car_coord:"
            + hashlib.md5(location.strip().lower().encode()).hexdigest()
        )

        cached = await _read_cache(cache_key)
        if cached:
            return tuple(cached)

        try:
            async with httpx.AsyncClient(timeout=settings.API_TIMEOUT) as client:
                resp = await client.get(
                    f"{_BOOKING_BASE}/cars/searchDestination",
                    headers=_booking_headers(),
                    params={"query": location},
                )
                resp.raise_for_status()
                data = resp.json()
                print("\n========== CAR API RESPONSE ==========")
                print(data)
                print("======================================")

            items = data.get("data") or []

            if not items:
                logger.warning(f"No car destination found for {location}")
                return None

            item = items[0]

            coord = item.get("coordinates", {})

            lat = (
                coord.get("latitude")
                or item.get("latitude")
                or item.get("lat")
            )

            lon = (
                coord.get("longitude")
                or item.get("longitude")
                or item.get("lng")
                or item.get("lon")
            )

            if lat is None or lon is None:
                logger.warning(f"No coordinates found for {location}")
                return None

            coords = (float(lat), float(lon))

            await _write_cache(
                cache_key,
                coords,
                settings.LOCATION_ID_CACHE_TTL,
            )

            logger.info(f"Resolved {location} -> {coords}")

            return coords

        except Exception as e:
            logger.error(f"Search destination failed for {location}: {e}")
            return None
    
    # ── Step 2: Search Car Rentals ────────────────────────────────────────────

    async def _search_car_rentals(
        self,
        lat: float,
        lon: float,
        location_name: str,
        pickup_date: Optional[str],
        return_date: Optional[str],
    ) -> List[CarResult]:

        from datetime import timedelta as td

        p_date = pickup_date or datetime.now().strftime("%Y-%m-%d")

        r_date = return_date or (
            datetime.strptime(p_date, "%Y-%m-%d") + td(days=1)
        ).strftime("%Y-%m-%d")

        params: Dict[str, Any] = {
            "pick_up_latitude": lat,
            "pick_up_longitude": lon,

            "drop_off_latitude": lat,
            "drop_off_longitude": lon,

            "pick_up_date": p_date,
            "drop_off_date": r_date,

            "pick_up_time": "10:00",
            "drop_off_time": "10:00",

            "driver_age": 30,
            "currency_code": "INR",
        }

        async with httpx.AsyncClient(timeout=settings.API_TIMEOUT) as client:
            resp = await client.get(
                f"{_BOOKING_BASE}/cars/searchCarRentals",
                headers=_booking_headers(),
                params=params,
            )

            resp.raise_for_status()
            data = resp.json()

        print("\n========== CAR API RESPONSE ==========")
        print(data)
        print("======================================")

        cars_raw = (
            (data.get("data") or {}).get("search_results")
            or (data.get("data") or {}).get("searchResults")
            or (data.get("data") or {}).get("cars")
            or data.get("search_results")
            or data.get("searchResults")
            or data.get("cars")
            or []
        )

        if not cars_raw:
            logger.warning(
                f"booking-com15 returned 0 cars for ({lat}, {lon})"
            )
            raise ValueError("No cars returned")

        results = []

        for c in cars_raw[:10]:
            try:
                parsed = self._parse_car(c, location_name)

                if parsed:
                    results.append(parsed)

            except Exception as e:
                logger.exception(f"Failed parsing car: {e}")

        if not results:
            raise ValueError("No parseable cars returned")

        logger.info(
            f"Parsed {len(results)} cars for {location_name}"
        )

        return sorted(
            results,
            key=lambda x: x.price_per_day
        )[:10]

    # ── Safe type conversion helpers (cars) ─────────────────────────────────
    @staticmethod
    def _safe_str_car(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _safe_int_car(value: Any, default: int = 0) -> int:
        if value is None:
            return default
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_float_car(value: Any, default: float = 0.0) -> float:
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _parse_car(
        self,
        c: Dict,
        location_name: str,
    ) -> Optional[CarResult]:

        vi = (
            c.get("vehicle_info")
            or c.get("vehicleInfo")
            or {}
        )

        supplier = (
            c.get("supplier")
            or c.get("supplierInfo")
            or c.get("supplier_info")
            or {}
        )

        pricing = (
            c.get("pricing")
            or c.get("pricing_info")
            or c.get("price")
            or {}
        )

        # Vehicle name
        name = self._safe_str_car(
            vi.get("name")
            or vi.get("vehicle_name")
            or vi.get("v_name")
            or c.get("name")
        ) or "Vehicle"

        # Type
        vtype = self._safe_str_car(
            vi.get("type")
            or vi.get("vehicle_type")
            or vi.get("category")
            or c.get("type")
        ).lower()

        if not vtype:
            vtype = "sedan"

        # Seats
        seats = self._safe_int_car(
            vi.get("seats")
            or vi.get("passengerQuantity")
            or c.get("seats"),
            default=4,
        )

        if seats <= 0:
            seats = 4

        # Transmission
        trans = self._safe_str_car(
            vi.get("transmission")
            or vi.get("gearbox")
        ).lower()

        if not trans:
            trans = "manual"

        # Fuel
        fuel = self._safe_str_car(
            vi.get("fuel_policy")
            or vi.get("fuelType")
        )

        if not fuel:
            fuel = "Petrol"

        # Price
        price_obj = (
            pricing.get("price")
            or pricing.get("total_price")
            or pricing.get("total")
            or {}
        )

        price = self._safe_float_car(
            price_obj.get("amount")
            or price_obj.get("value")
            or price_obj.get("units")
            or pricing.get("amount")
            or c.get("price"),
            default=0.0,
        )
        if price <= 0:
            return None 
        print(pricing)

        # Supplier
        vendor = self._safe_str_car(
            supplier.get("name")
            or supplier.get("supplier_name")
            or supplier.get("vendor_name")
            or c.get("supplier_name")
        )

        if not vendor:
            vendor = "RentalCo"

        # Features
        features = list(
            vi.get("features")
            or vi.get("extras")
            or []
        )

        if not features:
            features = ["AC", "GPS"]

        return CarResult(
            vehicle_name=name,
            vehicle_type=vtype,
            vendor=vendor,
            fuel_type=fuel,
            seats=seats,
            transmission=trans,
            pickup_location=location_name.title(),
            price_per_day=price,
            currency="INR",
            features=features[:6],
            source="booking-com15",
            is_mock=False,
        )


# ── Singletons ─────────────────────────────────────────────────────────────────
hotels_client = HotelsClient()
trains_client = TrainsClient()
buses_client  = BusesClient()
cars_client   = CarsClient()
