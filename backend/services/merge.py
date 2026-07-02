"""
Enterprise Travel Search Service

Responsibilities
----------------
Context
    ↓
Cache
    ↓
Geocoding
    ↓
Travel Provider APIs
    ↓
Filtering
    ↓
Ranking
    ↓
Storage
"""

import asyncio
import hashlib
import json
import logging

from datetime import datetime, timedelta
from typing import List, Optional

from config.settings import settings
from database.connection import get_db

from models.travel import (
    TravelContext,
    TravelMode,
    TravelSearchResult,
    FlightResult,
    HotelResult,
    TrainResult,
    BusResult,
    CarResult,
)

from api_clients.all_clients import (
    flights_client,
    hotels_client,
    trains_client,
    buses_client,
    cars_client,
)

from utils.fallback import MOCK_DISCLAIMER
from utils.india_cities import get_city_coords

logger = logging.getLogger(__name__)


class TravelSearchService:

    """
    Master Travel Search Orchestrator

    Responsible for

    • Flights
    • Hotels
    • Trains
    • Bus
    • Cars

    Also responsible for

    • Cache
    • Filters
    • Ranking
    • Storage
    """

    async def search(
        self,
        session_id: str,
        context: TravelContext,
    ) -> TravelSearchResult:

        mode = context.mode

        if mode == TravelMode.FLIGHT:
            return await self._flights(session_id, context)

        elif mode == TravelMode.TRAIN:
            return await self._trains(session_id, context)

        elif mode == TravelMode.BUS:
            return await self._buses(session_id, context)

        elif mode == TravelMode.HOTEL:
            return await self._hotels(session_id, context)

        elif mode == TravelMode.CAR:
            return await self._cars(session_id, context)

        else:
            return await self._all(session_id, context)

    # ==========================================================
    # Search Everything
    # ==========================================================

    async def _all(
        self,
        session_id: str,
        ctx: TravelContext,
    ) -> TravelSearchResult:

        logger.info(
            "Searching all travel modes %s → %s",
            ctx.origin,
            ctx.destination,
        )

        travel_date = (
            ctx.travel_date
            or datetime.now().strftime("%Y-%m-%d")
        )

        cabin = (
            ctx.cabin_class.value
            if ctx.cabin_class
            else "economy"
        )

        tasks = [

            flights_client.search(
                ctx.origin or "",
                ctx.destination or "",
                travel_date,
                cabin_class=cabin,
                passengers=ctx.passengers,
            ),

            trains_client.search(
                ctx.origin or "",
                ctx.destination or "",
                travel_date,
            ),

            buses_client.search(
                ctx.origin or "",
                ctx.destination or "",
                travel_date,
            ),

        ]

        flights, trains, buses = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        if isinstance(flights, Exception):
            logger.exception(flights)
            flights = []

        if isinstance(trains, Exception):
            logger.exception(trains)
            trains = []

        if isinstance(buses, Exception):
            logger.exception(buses)
            buses = []

        flights = self._filter_flights(
            flights or [],
            ctx,
        )

        trains = self._filter_trains(
            trains or [],
            ctx,
        )

        buses = self._filter_buses(
            buses or [],
            ctx,
        )

        #
        # Enterprise Ranking
        #

        flights = self._sort_flights(flights)

        trains = self._sort_trains(trains)

        buses = sorted(
            buses,
            key=lambda x: x.price,
        )

        flights = flights[:10]
        trains = trains[:10]
        buses = buses[:10]

        logger.info(
            "Results | Flights=%d Trains=%d Buses=%d",
            len(flights),
            len(trains),
            len(buses),
        )

        all_mock = (

            bool(flights)
            and all(f.is_mock for f in flights)

            and

            bool(trains)
            and all(t.is_mock for t in trains)

            and

            bool(buses)
            and all(b.is_mock for b in buses)

        )

        result = TravelSearchResult(

            session_id=session_id,

            search_type=TravelMode.GENERAL,

            origin=ctx.origin,

            destination=ctx.destination,

            travel_date=travel_date,

            flights=flights or None,

            trains=trains or None,

            buses=buses or None,

            is_partial_mock=all_mock,

            mock_reason=(
                MOCK_DISCLAIMER
                if all_mock
                else None
            ),
        )

        await self._store(result)

        return result

# ==========================================================
# Flights
# ==========================================================

async def _flights(
    self,
    session_id: str,
    ctx: TravelContext,
) -> TravelSearchResult:

    travel_date = (
        ctx.travel_date
        or datetime.now().strftime("%Y-%m-%d")
    )

    cabin = (
        ctx.cabin_class.value
        if ctx.cabin_class
        else "economy"
    )

    cache_key = self._ckey(
        "flights",
        ctx.origin,
        ctx.destination,
        travel_date,
        cabin,
        ctx.passengers,
    )

    logger.info(
        "Flight Search %s → %s (%s)",
        ctx.origin,
        ctx.destination,
        travel_date,
    )

    flights = await self._read_cache(
        cache_key,
        "flights",
    )

    if flights is None:

        logger.info("Flight cache MISS")

        flights = await flights_client.search(

            origin=ctx.origin or "",

            destination=ctx.destination or "",

            travel_date=travel_date,

            passengers=ctx.passengers,

            cabin_class=cabin,

        )

        await self._write_cache(
            cache_key,
            flights,
        )

    else:

        logger.info("Flight cache HIT")

    ####################################################
    # Apply User Filters
    ####################################################

    flights = self._filter_flights(
        flights,
        ctx,
    )

    ####################################################
    # Meeting Planner Filters
    ####################################################

    if ctx.required_arrival_by and flights:

        try:

            from services.meeting_planner import meeting_planner

            flights = meeting_planner.filter_flights_by_arrival(

                flights,

                ctx.required_arrival_by,

            )

        except Exception as e:

            logger.warning(
                f"Arrival filter failed: {e}"
            )

    if ctx.required_departure_after and flights:

        try:

            from services.meeting_planner import meeting_planner

            flights = meeting_planner.filter_flights_by_departure(

                flights,

                ctx.required_departure_after,

            )

        except Exception as e:

            logger.warning(
                f"Departure filter failed: {e}"
            )

    ####################################################
    # Remove Bad Itineraries
    ####################################################

    cleaned = []

    for flight in flights:

        try:

            duration = flight.total_duration.lower()

            if "h" in duration:

                hours = int(duration.split("h")[0])

                if hours > 8:
                    continue

            if flight.stops > 1:
                continue

        except Exception:

            pass

        cleaned.append(flight)

    flights = cleaned

    ####################################################
    # Remove Duplicate Flights
    ####################################################

    unique = {}

    for flight in flights:

        if not flight.segments:
            continue

        first = flight.segments[0]

        key = (

            first.flight_number,

            first.departure_time,

            flight.stops,

        )

        if key not in unique:

            unique[key] = flight

        else:

            if flight.price < unique[key].price:

                unique[key] = flight

    flights = list(unique.values())

    ####################################################
    # Enterprise Ranking
    ####################################################

    flights = sorted(

        flights,

        key=lambda f: (

            f.stops,

            f.price,

        ),

    )

    flights = flights[:10]

    ####################################################
    # Logging
    ####################################################

    logger.info(

        "Flight Search Complete | %d flights",

        len(flights),

    )

    ####################################################
    # Mock Detection
    ####################################################

    is_mock = (

        bool(flights)

        and all(

            flight.is_mock

            for flight in flights

        )

    )

    ####################################################
    # Build Result
    ####################################################

    result = TravelSearchResult(

        session_id=session_id,

        search_type=TravelMode.FLIGHT,

        origin=ctx.origin,

        destination=ctx.destination,

        travel_date=travel_date,

        flights=flights,

        is_partial_mock=is_mock,

        mock_reason=(
            MOCK_DISCLAIMER
            if is_mock
            else None
        ),

    )

    await self._store(result)

    return result

# ==========================================================
# Trains
# ==========================================================

async def _trains(
    self,
    session_id: str,
    ctx: TravelContext,
) -> TravelSearchResult:

    travel_date = (
        ctx.travel_date
        or datetime.now().strftime("%Y-%m-%d")
    )

    cache_key = self._ckey(
        "trains",
        ctx.origin,
        ctx.destination,
        travel_date,
    )

    trains = await self._read_cache(
        cache_key,
        "trains",
    )

    if trains is None:

        logger.info("Train cache MISS")

        trains = await trains_client.search(
            ctx.origin or "",
            ctx.destination or "",
            travel_date,
        )

        await self._write_cache(
            cache_key,
            trains,
        )

    else:

        logger.info("Train cache HIT")

    trains = self._filter_trains(
        trains,
        ctx,
    )

    trains = self._sort_trains(trains)

    trains = trains[:10]

    logger.info(
        "Train Search Complete | %d trains",
        len(trains),
    )

    is_mock = (
        bool(trains)
        and all(t.is_mock for t in trains)
    )

    result = TravelSearchResult(
        session_id=session_id,
        search_type=TravelMode.TRAIN,
        origin=ctx.origin,
        destination=ctx.destination,
        travel_date=travel_date,
        trains=trains,
        is_partial_mock=is_mock,
        mock_reason=MOCK_DISCLAIMER if is_mock else None,
    )

    await self._store(result)

    return result

# ==========================================================
# Buses
# ==========================================================

async def _buses(
    self,
    session_id: str,
    ctx: TravelContext,
) -> TravelSearchResult:

    travel_date = (
        ctx.travel_date
        or datetime.now().strftime("%Y-%m-%d")
    )

    buses = await buses_client.search(
        ctx.origin or "",
        ctx.destination or "",
        travel_date,
    )

    buses = self._filter_buses(
        buses,
        ctx,
    )

    buses = sorted(
        buses,
        key=lambda b: b.price,
    )

    buses = buses[:10]

    logger.info(
        "Bus Search Complete | %d buses",
        len(buses),
    )

    is_mock = (
        bool(buses)
        and all(b.is_mock for b in buses)
    )

    result = TravelSearchResult(
        session_id=session_id,
        search_type=TravelMode.BUS,
        origin=ctx.origin,
        destination=ctx.destination,
        travel_date=travel_date,
        buses=buses,
        is_partial_mock=is_mock,
        mock_reason=MOCK_DISCLAIMER if is_mock else None,
    )

    await self._store(result)

    return result
# ==========================================================
# Hotels
# ==========================================================

async def _hotels(
    self,
    session_id: str,
    ctx: TravelContext,
) -> TravelSearchResult:

    check_in = (
        ctx.travel_date
        or datetime.now().strftime("%Y-%m-%d")
    )

    checkin_date = datetime.strptime(
        check_in,
        "%Y-%m-%d",
    )

    check_out = (
        ctx.return_date
        or (
            checkin_date +
            timedelta(days=1)
        ).strftime("%Y-%m-%d")
    )

    destination = ctx.destination or ""

    coords = get_city_coords(destination)

    latitude = longitude = None

    if coords:

        latitude, longitude = coords

    meeting_lat = None
    meeting_lng = None

    if ctx.meeting:

        meeting_lat = ctx.meeting.meeting_lat
        meeting_lng = ctx.meeting.meeting_lng

    cache_key = self._ckey(
        "hotels",
        destination,
        check_in,
        check_out,
    )

    hotels = await self._read_cache(
        cache_key,
        "hotels",
    )

    if hotels is None:

        logger.info("Hotel cache MISS")

        hotels = await hotels_client.search(

            destination=destination,

            check_in=check_in,

            check_out=check_out,

            guests=ctx.passengers,

            latitude=latitude,

            longitude=longitude,

            meeting_lat=meeting_lat,

            meeting_lng=meeting_lng,

        )

        await self._write_cache(
            cache_key,
            hotels,
        )

    else:

        logger.info("Hotel cache HIT")

    hotels = self._dedupe(hotels)

    hotels = self._filter_hotels(
        hotels,
        ctx,
    )

    hotels = sorted(

        hotels,

        key=lambda hotel: (

            hotel.distance_from_meeting
            if hotel.distance_from_meeting is not None
            else 999,

            hotel.price_per_night,

            -(hotel.review_score or 0),

        ),

    )

    hotels = hotels[:10]

    logger.info(
        "Hotel Search Complete | %d hotels",
        len(hotels),
    )

    is_mock = (
        bool(hotels)
        and all(h.is_mock for h in hotels)
    )

    result = TravelSearchResult(

        session_id=session_id,

        search_type=TravelMode.HOTEL,

        destination=destination,

        hotels=hotels,

        is_partial_mock=is_mock,

        mock_reason=(
            MOCK_DISCLAIMER
            if is_mock
            else None
        ),

    )

    await self._store(result)

    return result

# ==========================================================
# Cars
# ==========================================================

async def _cars(
    self,
    session_id: str,
    ctx: TravelContext,
) -> TravelSearchResult:

    location = ctx.destination or ctx.origin or ""

    travel_date = (
        ctx.travel_date
        or datetime.now().strftime("%Y-%m-%d")
    )

    coords = get_city_coords(location)

    latitude = longitude = None

    if coords:
        latitude, longitude = coords

    cache_key = self._ckey(
        "cars",
        location,
        travel_date,
    )

    cars = await self._read_cache(
        cache_key,
        "cars",
    )

    if cars is None:

        logger.info("Car cache MISS")

        cars = await cars_client.search(
            location=location,
            pickup_date=travel_date,
            latitude=latitude,
            longitude=longitude,
        )

        await self._write_cache(
            cache_key,
            cars,
        )

    else:

        logger.info("Car cache HIT")

    cars = self._filter_cars(
        cars,
        ctx,
    )

    cars = sorted(
        cars,
        key=lambda x: x.price_per_day,
    )

    cars = cars[:10]

    is_mock = (
        bool(cars)
        and all(c.is_mock for c in cars)
    )

    result = TravelSearchResult(
        session_id=session_id,
        search_type=TravelMode.CAR,
        destination=location,
        cars=cars,
        is_partial_mock=is_mock,
        mock_reason=MOCK_DISCLAIMER if is_mock else None,
    )

    await self._store(result)

    return result

# ==========================================================
# Filters
# ==========================================================

def _filter_flights(self, flights, ctx):

    if ctx.max_budget is not None:
        flights = [f for f in flights if f.price <= ctx.max_budget]

    if ctx.min_budget is not None:
        flights = [f for f in flights if f.price >= ctx.min_budget]

    if ctx.non_stop_only:
        flights = [f for f in flights if f.stops == 0]

    if ctx.cabin_class:
        flights = [
            f
            for f in flights
            if f.cabin_class == ctx.cabin_class
        ]

    return flights


def _filter_trains(self, trains, ctx):

    if ctx.train_class:

        trains = [

            t

            for t in trains

            if any(

                c.class_code.upper()
                == ctx.train_class.value.upper()

                for c in t.classes

            )

        ]

    if ctx.max_budget is not None:

        trains = [

            t

            for t in trains

            if min(

                (
                    c.price
                    for c in t.classes
                    if c.price
                ),

                default=999999,

            ) <= ctx.max_budget

        ]

    return trains


def _filter_buses(self, buses, ctx):

    if ctx.max_budget is not None:

        buses = [

            b

            for b in buses

            if b.price <= ctx.max_budget

        ]

    return buses


def _filter_hotels(self, hotels, ctx):

    if ctx.hotel_stars is not None:

        hotels = [

            h

            for h in hotels

            if h.stars == ctx.hotel_stars

        ]

    if ctx.max_budget is not None:

        hotels = [

            h

            for h in hotels

            if h.price_per_night <= ctx.max_budget

        ]

    if ctx.min_budget is not None:

        hotels = [

            h

            for h in hotels

            if h.price_per_night >= ctx.min_budget

        ]

    for amenity in ctx.amenities:

        hotels = [

            h

            for h in hotels

            if any(

                amenity.lower() in a.lower()

                for a in h.amenities

            )

        ]

    return hotels


def _filter_cars(self, cars, ctx):

    if ctx.max_budget is not None:

        cars = [

            c

            for c in cars

            if c.price_per_day <= ctx.max_budget

        ]

    return cars

# ==========================================================
# Sorting
# ==========================================================

def _sort_flights(self, flights):

    unique = {}

    for f in flights:

        if not f.segments:
            continue

        first = f.segments[0]

        key = (

            first.flight_number,

            first.departure_time,

            f.stops,

        )

        if key not in unique:

            unique[key] = f

        elif f.price < unique[key].price:

            unique[key] = f

    flights = list(unique.values())

    return sorted(

        flights,

        key=lambda x: (

            x.stops,

            x.price,

        ),

    )


def _sort_trains(self, trains):

    return sorted(

        trains,

        key=lambda t: min(

            (

                c.price

                for c in t.classes

                if c.price

            ),

            default=999999,

        ),

    )

def _dedupe(self, hotels):

    seen = set()

    result = []

    for hotel in hotels:

        key = (

            hotel.name.lower().strip(),

            round(hotel.price_per_night, 2),

        )

        if key in seen:
            continue

        seen.add(key)

        result.append(hotel)

    return result

# ==========================================================
# Cache
# ==========================================================

def _ckey(self, *parts):

    raw = "|".join(

        str(x or "").lower()

        for x in parts

    )

    return "search:" + hashlib.md5(raw.encode()).hexdigest()


async def _read_cache(self, key, kind):

    try:

        db = get_db()

        doc = await db.cached_results.find_one(
            {"cache_key": key}
        )

        if not doc:
            return None

        model_map = {

            "flights": FlightResult,

            "hotels": HotelResult,

            "trains": TrainResult,

            "buses": BusResult,

            "cars": CarResult,

        }

        model = model_map[kind]

        return [

            model(**x)

            for x in json.loads(doc["value"])

        ]

    except Exception:

        return None


async def _write_cache(
    self,
    key,
    results,
):

    if not results:
        return

    try:

        db = get_db()

        await db.cached_results.update_one(

            {"cache_key": key},

            {

                "$set": {

                    "cache_key": key,

                    "value": json.dumps(

                        [

                            r.dict()

                            for r in results

                        ],

                        default=str,

                    ),

                    "expires_at": datetime.utcnow()
                    + timedelta(
                        seconds=settings.TRAVEL_RESULT_CACHE_TTL
                    ),

                }

            },

            upsert=True,

        )

    except Exception as e:

        logger.debug(e)


# ==========================================================
# Storage
# ==========================================================

async def _store(
    self,
    result: TravelSearchResult,
):

    try:

        db = get_db()

        await db.travel_searches.insert_one(

            {

                k: v

                for k, v in result.dict().items()

                if v is not None

            }

        )

    except Exception as e:

        logger.warning(e)


travel_search_service = TravelSearchService()