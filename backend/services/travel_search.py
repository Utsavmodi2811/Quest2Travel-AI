"""
Travel Search Orchestration Service.
Coordinates: context → cache → geocoding → API search → filtering → sorting → storage.

Budget/stars/class filters are STRICT: if a user asks for "hotels under ₹5000"
and zero hotels match, we return zero hotels (not silently fall back to
everything). The chat layer / UI is responsible for telling the user
"no results matched your filter" in that case.
"""

import logging
import asyncio
import hashlib
from typing import Optional, List
from datetime import datetime, timedelta

from models.travel import (
    TravelContext, TravelMode, TravelSearchResult,
    FlightResult, HotelResult, TrainResult, BusResult, CarResult, CabinClass,
)
from services.geocoding import geocoding_service
from api_clients.flights import flights_client
from api_clients.travel import hotels_client, trains_client, buses_client, cars_client
from database.connection import get_db
from utils.fallback import MOCK_DISCLAIMER
from config.settings import settings

logger = logging.getLogger(__name__)


class TravelSearchService:

    async def search(self, session_id: str, context: TravelContext) -> TravelSearchResult:
        mode = context.mode
        if mode == TravelMode.FLIGHT:
            return await self._search_flights(session_id, context)
        elif mode == TravelMode.TRAIN:
            return await self._search_trains(session_id, context)
        elif mode == TravelMode.BUS:
            return await self._search_buses(session_id, context)
        elif mode == TravelMode.HOTEL:
            return await self._search_hotels(session_id, context)
        elif mode == TravelMode.CAR:
            return await self._search_cars(session_id, context)
        else:
            return await self._search_all(session_id, context)

    # ── All modes ─────────────────────────────────────────────────────────────

    async def _search_all(self, session_id: str, context: TravelContext) -> TravelSearchResult:
        travel_date = context.travel_date or datetime.now().strftime("%Y-%m-%d")

        flights_task = flights_client.search(
            origin=context.origin or "",
            destination=context.destination or "",
            travel_date=travel_date,
            cabin_class=context.cabin_class.value if context.cabin_class else "economy",
        )
        trains_task = trains_client.search(
            origin=context.origin or "",
            destination=context.destination or "",
            travel_date=travel_date,
        )
        buses_task = buses_client.search(
            origin=context.origin or "",
            destination=context.destination or "",
            travel_date=travel_date,
        )

        flights, trains, buses = await asyncio.gather(
            flights_task, trains_task, buses_task,
            return_exceptions=True,
        )

        if isinstance(flights, Exception):
            logger.warning(f"Flights failed in search_all: {flights}")
            flights = []
        if isinstance(trains, Exception):
            logger.warning(f"Trains failed in search_all: {trains}")
            trains = []
        if isinstance(buses, Exception):
            logger.warning(f"Buses failed in search_all: {buses}")
            buses = []

        flights = self._filter_flights(flights or [], context)
        trains  = self._filter_trains(trains or [], context)
        buses   = self._filter_buses(buses or [], context)

        logger.info(
            f"search_all: found {len(flights)} flights, "
            f"{len(trains)} trains, {len(buses)} buses "
            f"for {context.origin} → {context.destination}"
        )

        all_mock = (
            bool(flights) and all(getattr(f, "is_mock", False) for f in flights) and
            bool(trains)  and all(getattr(t, "is_mock", False) for t in trains)  and
            bool(buses)   and all(getattr(b, "is_mock", False) for b in buses)
        )

        result = TravelSearchResult(
            session_id=session_id,
            search_type=TravelMode.GENERAL,
            origin=context.origin,
            destination=context.destination,
            travel_date=travel_date,
            flights=flights or None,
            trains=trains or None,
            buses=buses or None,
            is_partial_mock=all_mock,
            mock_reason=MOCK_DISCLAIMER if all_mock else None,
        )
        await self._store(result)
        return result

    # ── Flights ───────────────────────────────────────────────────────────────

    async def _search_flights(self, session_id: str, context: TravelContext) -> TravelSearchResult:
        travel_date = context.travel_date or datetime.now().strftime("%Y-%m-%d")
        cabin = context.cabin_class.value if context.cabin_class else "economy"

        # cache_key = self._result_cache_key(
        #     "flights", context.origin, context.destination, travel_date, cabin
        # )

        # cached = await self._read_result_cache(cache_key)

        # if cached is not None:
        #     flights = cached
        #     logger.info(
        #         f"Flight cache HIT: {context.origin}→{context.destination} ({travel_date})"
        #     )
        # else:
        flights = await flights_client.search(
            origin=context.origin or "",
            destination=context.destination or "",
            travel_date=travel_date,
            passengers=context.passengers,
            cabin_class=cabin,
        )

        # if flights and not all(f.is_mock for f in flights):
        #     await self._write_result_cache(cache_key, flights)

        flights = self._filter_flights(flights, context)

        # remove terrible itineraries
        flights = [
            f for f in flights
            if (
                f.stops <= 1
                and (
                    int(f.total_duration.split("h")[0]) <= 8
                )
            )
        ]
        print("Before sorting =", len(flights))

        flights = self._sort_flights(flights)

        print("After sorting =", len(flights))

        logger.info(
            f"Found {len(flights)} flights for "
            f"{context.origin} → {context.destination} on {travel_date}"
        )

        is_mock = bool(flights) and all(f.is_mock for f in flights)
        result = TravelSearchResult(
            session_id=session_id,
            search_type=TravelMode.FLIGHT,
            origin=context.origin,
            destination=context.destination,
            travel_date=travel_date,
            flights=flights,
            is_partial_mock=is_mock,
            mock_reason=MOCK_DISCLAIMER if is_mock else None,
        )
        await self._store(result)
        print("Returning =", len(flights))
        return result

    # ── Trains ────────────────────────────────────────────────────────────────

    async def _search_trains(self, session_id: str, context: TravelContext) -> TravelSearchResult:
        travel_date = context.travel_date or datetime.now().strftime("%Y-%m-%d")

        cache_key = self._result_cache_key("trains", context.origin, context.destination, travel_date)
        cached = await self._read_result_cache(cache_key)
        if cached is not None:
            trains = cached
            logger.info(f"Train cache HIT: {context.origin}→{context.destination} ({travel_date})")
        else:
            trains = await trains_client.search(
                origin=context.origin or "",
                destination=context.destination or "",
                travel_date=travel_date,
            )
            if trains and not all(t.is_mock for t in trains):
                await self._write_result_cache(cache_key, trains)

        trains = self._filter_trains(trains, context)
        trains = self._sort_trains(trains)

        logger.info(f"Found {len(trains)} trains for {context.origin} → {context.destination}")

        is_mock = bool(trains) and all(t.is_mock for t in trains)
        result = TravelSearchResult(
            session_id=session_id,
            search_type=TravelMode.TRAIN,
            origin=context.origin,
            destination=context.destination,
            travel_date=travel_date,
            trains=trains,
            is_partial_mock=is_mock,
            mock_reason=MOCK_DISCLAIMER if is_mock else None,
        )
        await self._store(result)
        return result

    # ── Buses ─────────────────────────────────────────────────────────────────

    async def _search_buses(self, session_id: str, context: TravelContext) -> TravelSearchResult:
        travel_date = context.travel_date or datetime.now().strftime("%Y-%m-%d")
        buses = await buses_client.search(
            origin=context.origin or "",
            destination=context.destination or "",
            travel_date=travel_date,
        )
        buses = self._filter_buses(buses, context)
        buses = sorted(buses, key=lambda b: b.price)

        logger.info(f"Found {len(buses)} buses for {context.origin} → {context.destination}")

        is_mock = bool(buses) and all(b.is_mock for b in buses)
        result = TravelSearchResult(
            session_id=session_id,
            search_type=TravelMode.BUS,
            origin=context.origin,
            destination=context.destination,
            travel_date=travel_date,
            buses=buses,
            is_partial_mock=is_mock,
            mock_reason=MOCK_DISCLAIMER if is_mock else None,
        )
        await self._store(result)
        return result

    # ── Hotels ────────────────────────────────────────────────────────────────

    async def _search_hotels(self, session_id: str, context: TravelContext) -> TravelSearchResult:
        dest_info = await geocoding_service.resolve(context.destination or "")
        check_in  = context.travel_date or datetime.now().strftime("%Y-%m-%d")
        ci        = datetime.strptime(check_in, "%Y-%m-%d")
        check_out = context.return_date or (ci + timedelta(days=1)).strftime("%Y-%m-%d")

        cache_key = self._result_cache_key(
            "hotels", context.destination, None, check_in, check_out
        )
        cached = await self._read_result_cache(cache_key)
        if cached is not None:
            hotels = cached
            logger.info(f"Hotel cache HIT: {context.destination} ({check_in} → {check_out})")
        else:
            hotels = await hotels_client.search(
                destination=context.destination or "",
                check_in=check_in,
                check_out=check_out,
                guests=context.passengers,
                stars=None,  # fetch unfiltered, apply star filter locally below
                latitude=dest_info.latitude if dest_info else None,
                longitude=dest_info.longitude if dest_info else None,
            )
            if hotels and not all(h.is_mock for h in hotels):
                await self._write_result_cache(cache_key, hotels)

        hotels = self._dedupe_hotels(hotels)
        hotels = self._filter_hotels(hotels, context)
        hotels = self._sort_hotels(hotels)

        logger.info(f"Found {len(hotels)} hotels for {context.destination}")

        is_mock = bool(hotels) and all(h.is_mock for h in hotels)
        result = TravelSearchResult(
            session_id=session_id,
            search_type=TravelMode.HOTEL,
            destination=context.destination,
            hotels=hotels,
            is_partial_mock=is_mock,
            mock_reason=MOCK_DISCLAIMER if is_mock else None,
        )
        await self._store(result)
        return result

    # ── Cars ──────────────────────────────────────────────────────────────────

    async def _search_cars(self, session_id: str, context: TravelContext) -> TravelSearchResult:
        location = context.destination or context.origin or ""
        dest_info = await geocoding_service.resolve(location)
        pickup_date = context.travel_date or datetime.now().strftime("%Y-%m-%d")

        cache_key = self._result_cache_key("cars", location, None, pickup_date)
        cached = await self._read_result_cache(cache_key)
        if cached is not None:
            cars = cached
            logger.info(f"Car cache HIT: {location} ({pickup_date})")
        else:
            cars = await cars_client.search(
                location=location,
                pickup_date=pickup_date,
                latitude=dest_info.latitude if dest_info else None,
                longitude=dest_info.longitude if dest_info else None,
            )
            if cars and not all(c.is_mock for c in cars):
                await self._write_result_cache(cache_key, cars)

        cars = self._filter_cars(cars, context)
        cars = sorted(cars, key=lambda c: c.price_per_day)

        logger.info(f"Found {len(cars)} cars for {location}")

        is_mock = bool(cars) and all(c.is_mock for c in cars)
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

    # ── Filters (STRICT — never silently fall back to unfiltered) ──────────────
    #
    # Rule: if the user explicitly asked for a budget/stars/class constraint,
    # we apply it exactly. An empty result list is a valid, honest outcome
    # ("no flights under ₹2000") rather than silently showing everything.

    def _filter_flights(
        self,
        flights: List[FlightResult],
        ctx: TravelContext
    ) -> List[FlightResult]:

        if not flights:
            return []

        r = list(flights)

        # budget filters
        if ctx.max_budget is not None:
            r = [f for f in r if f.price <= ctx.max_budget]

        if ctx.min_budget is not None:
            r = [f for f in r if f.price >= ctx.min_budget]

        # nonstop filter
        if ctx.non_stop_only:
            r = [f for f in r if f.stops == 0]

        # cabin filter
        if ctx.cabin_class:
            r = [f for f in r if f.cabin_class == ctx.cabin_class]

        # remove crazy durations (>8 hours)
        good = []

        for f in r:
            try:
                hours = int(f.total_duration.split("h")[0])
                if hours <= 8:
                    good.append(f)
            except:
                good.append(f)

        return good

    def _filter_trains(self, trains: List[TrainResult], ctx: TravelContext) -> List[TrainResult]:
        if not trains:
            return []
        r = list(trains)
        if ctx.train_class:
            r = [t for t in r if any(
                c.class_code.upper() == ctx.train_class.value.upper()
                for c in t.classes
            )]
        if ctx.max_budget is not None:
            # Train passes the budget filter if its CHEAPEST class is within budget
            def cheapest(t: TrainResult) -> float:
                prices = [c.price for c in t.classes if c.price and c.price > 0]
                return min(prices) if prices else float("inf")
            r = [t for t in r if cheapest(t) <= ctx.max_budget]
        return r

    def _filter_buses(self, buses: List[BusResult], ctx: TravelContext) -> List[BusResult]:
        if not buses:
            return []
        r = list(buses)
        if ctx.max_budget is not None:
            r = [b for b in r if b.price <= ctx.max_budget]
        return r

    def _filter_hotels(self, hotels: List[HotelResult], ctx: TravelContext) -> List[HotelResult]:
        if not hotels:
            return []
        r = list(hotels)
        if ctx.hotel_stars is not None:
            r = [h for h in r if h.stars == ctx.hotel_stars]
        if ctx.max_budget is not None:
            r = [h for h in r if h.price_per_night <= ctx.max_budget]
        if ctx.min_budget is not None:
            r = [h for h in r if h.price_per_night >= ctx.min_budget]
        for amenity in (ctx.amenities or []):
            r = [h for h in r if any(
                amenity.lower() in a.lower() for a in h.amenities
            )]
        return r

    def _filter_cars(self, cars: List[CarResult], ctx: TravelContext) -> List[CarResult]:
        if not cars:
            return []
        r = list(cars)
        if ctx.max_budget is not None:
            r = [c for c in r if c.price_per_day <= ctx.max_budget]
        if ctx.min_budget is not None:
            r = [c for c in r if c.price_per_day >= ctx.min_budget]
        return r

    # ── Sorting ───────────────────────────────────────────────────────────────

    def _sort_flights(self, flights: List[FlightResult]) -> List[FlightResult]:

        # remove duplicates
        unique = {}

        for f in flights:

            first_seg = f.segments[0]

            key = (
                first_seg.flight_number,
                first_seg.departure_time,
                f.stops
            )

            if key not in unique:
                unique[key] = f

            else:
                if f.price < unique[key].price:
                    unique[key] = f

        flights = list(unique.values())

        return sorted(
            flights,
            key=lambda f: (
                f.stops,
                f.price
            )
        )

    def _sort_trains(self, trains: List[TrainResult]) -> List[TrainResult]:
        """Sort by cheapest available class price."""
        def cheapest(t: TrainResult) -> float:
            prices = [c.price for c in t.classes if c.price and c.price > 0]
            return min(prices) if prices else float("inf")
        return sorted(trains, key=cheapest)

    def _sort_hotels(self, hotels: List[HotelResult]) -> List[HotelResult]:
        """Sort by price first, rating as tiebreaker (higher rating wins ties)."""
        return sorted(hotels, key=lambda h: (h.price_per_night, -(h.review_score or 0)))

    # ── Deduplication ────────────────────────────────────────────────────────

    def _dedupe_hotels(self, hotels: List[HotelResult]) -> List[HotelResult]:
        """Remove duplicate hotels (same name + same price) that some
        upstream API responses occasionally repeat across pages."""
        seen = set()
        result = []
        for h in hotels:
            key = (h.name.strip().lower(), round(h.price_per_night, 2))
            if key in seen:
                continue
            seen.add(key)
            result.append(h)
        return result

    # ── Result Cache (30 min TTL, keyed by search params) ───────────────────────

    def _result_cache_key(self, kind: str, a: Optional[str], b: Optional[str], *rest) -> str:
        raw = "|".join([kind, (a or "").lower(), (b or "").lower()] + [str(x) for x in rest if x])
        return "search:" + hashlib.md5(raw.encode()).hexdigest()

    async def _read_result_cache(self, cache_key: str):
        try:
            db = get_db()
            doc = await db.cached_results.find_one({"cache_key": cache_key})
            if not doc or not doc.get("value"):
                return None

            import json
            from models.travel import (
                FlightResult, HotelResult, TrainResult, BusResult, CarResult
            )
            kind = doc.get("kind")
            raw_list = json.loads(doc["value"])

            model_map = {
                "flights": FlightResult, "hotels": HotelResult,
                "trains": TrainResult, "buses": BusResult, "cars": CarResult,
            }
            model = model_map.get(kind)
            if not model:
                return None
            return [model(**item) for item in raw_list]
        except Exception as e:
            logger.debug(f"Result cache read failed ({cache_key}): {e}")
            return None

    async def _write_result_cache(self, cache_key: str, results: List) -> None:
        if not results:
            return  # don't cache empty results — let next call retry the API
        try:
            db = get_db()
            import json
            kind = type(results[0]).__name__.lower().replace("result", "")
            kind_map = {"flight": "flights", "hotel": "hotels", "train": "trains",
                        "bus": "buses", "car": "cars"}
            kind = kind_map.get(kind, kind)

            await db.cached_results.update_one(
                {"cache_key": cache_key},
                {"$set": {
                    "cache_key": cache_key,
                    "kind": kind,
                    "value": json.dumps([r.dict() for r in results], default=str),
                    "expires_at": datetime.utcnow() + timedelta(seconds=settings.TRAVEL_RESULT_CACHE_TTL),
                }},
                upsert=True,
            )
        except Exception as e:
            logger.debug(f"Result cache write failed ({cache_key}): {e}")

    # ── Storage ───────────────────────────────────────────────────────────────

    async def _store(self, result: TravelSearchResult) -> None:
        try:
            db = get_db()
            data = result.dict()
            data = {k: v for k, v in data.items() if v is not None}
            await db.travel_searches.insert_one(data)
        except Exception as e:
            logger.warning(f"Failed to store search results: {e}")


travel_search_service = TravelSearchService()
