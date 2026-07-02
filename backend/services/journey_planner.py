"""
Journey Planner Service.
Feature 3-6: Builds a complete multi-leg journey plan from a meeting request.

Flow:
  Meeting Info
    → Time Window Computation
    → Outbound Flight Search (filtered by arrival deadline)
    → Airport Cab Search (automatic - Feature 4)
    → Hotel Search near meeting venue (Feature 5)
    → Return Trip Planning (Feature 6 decision tree)
    → JourneyPlan assembly
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta

from models.travel import (
    JourneyPlan, JourneyLeg, TravelContext, MeetingInfo,
    TravelMode, ServiceType, TravelSearchResult,
)
from services.meeting_planner import meeting_planner
from services.permission_service import permission_service

logger = logging.getLogger(__name__)


class JourneyPlannerService:

    async def build_journey(
        self,
        session_id: str,
        meeting: MeetingInfo,
        context: TravelContext,
        travel_search_fn,   # callable: async (session_id, context) -> TravelSearchResult
    ) -> JourneyPlan:
        """
        Main entry point. Builds the full journey plan for a meeting request.
        Uses travel_search_fn to call the existing travel search service.
        """
        journey = JourneyPlan(session_id=session_id, meeting=meeting)
        company_id = context.company_id
        allowed = context.allowed_services

        # ── Step 1: Compute time window ────────────────────────────────────────
        window = meeting_planner.compute_travel_window(meeting)
        journey.timeline_summary = meeting_planner.describe_timeline(window)

        # Set time constraints on context so flight search uses them
        context.required_arrival_by = window.get("flight_arrival_by")
        context.required_departure_after = None  # outbound leg

        # ── Step 2: Outbound flight ────────────────────────────────────────────
        if ServiceType.FLIGHT in allowed:
            outbound = await self._search_outbound_flight(
                session_id, meeting, context, window, travel_search_fn
            )
            if outbound:
                journey.legs.append(outbound)

        # ── Step 3: Airport → Venue cab (automatic, Feature 4) ────────────────
        if ServiceType.CAR in allowed and meeting.meeting_city:
            cab_leg = await self._search_airport_cab(
                session_id, meeting, context, travel_search_fn
            )
            if cab_leg:
                journey.legs.append(cab_leg)

        # ── Step 4: Hotel near meeting venue (Feature 5) ──────────────────────
        hotel_needed = (
            meeting.hotel_required
            or meeting.meeting_duration_hours >= 8
            or not meeting.return_required
        )
        if hotel_needed and ServiceType.HOTEL in allowed and meeting.meeting_city:
            hotel_leg = await self._search_nearby_hotel(
                session_id, meeting, context, travel_search_fn
            )
            if hotel_leg:
                journey.legs.append(hotel_leg)

        # ── Step 5: Return trip (Feature 6 decision tree) ─────────────────────
        if meeting.return_required and window.get("return_departure_after"):
            return_legs = await self._plan_return_trip(
                session_id, meeting, context, window, travel_search_fn, allowed
            )
            journey.legs.extend(return_legs)

        # ── Step 6: Compute total cost ─────────────────────────────────────────
        journey.total_estimated_cost = sum(
            leg.price or 0 for leg in journey.legs
        )

        return journey

    # ── Outbound flight ────────────────────────────────────────────────────────

    async def _search_outbound_flight(
        self, session_id: str, meeting: MeetingInfo,
        context: TravelContext, window: dict, search_fn
    ) -> Optional[JourneyLeg]:
        from models.travel import TravelContext as TC, TravelMode
        ctx = TC(**context.dict())
        ctx.origin      = meeting.current_city or context.origin or context.home_city
        ctx.destination = meeting.meeting_city
        ctx.travel_date = meeting.meeting_date
        ctx.mode        = TravelMode.FLIGHT

        if not ctx.origin or not ctx.destination:
            return None

        result: TravelSearchResult = await search_fn(session_id, ctx)
        flights = result.flights or []

        # Apply time-intelligence filter (Feature 2)
        if window.get("flight_arrival_by") and flights:
            flights = meeting_planner.filter_flights_by_arrival(
                flights, window["flight_arrival_by"]
            )

        if not flights:
            logger.warning("No flights satisfy the time constraint for meeting")
            return None

        # Pick cheapest qualifying flight
        best = min(flights, key=lambda f: f.price)
        seg = best.segments[0]

        return JourneyLeg(
            leg_type="flight",
            description=f"✈️ {seg.airline} {seg.flight_number}: {ctx.origin} → {ctx.destination}",
            from_location=ctx.origin or "",
            to_location=ctx.destination or "",
            depart_time=seg.departure_time if "T" not in seg.departure_time
                        else seg.departure_time.split("T")[1][:5],
            arrive_time=best.segments[-1].arrival_time if "T" not in best.segments[-1].arrival_time
                        else best.segments[-1].arrival_time.split("T")[1][:5],
            duration_minutes=self._parse_duration(best.total_duration),
            price=best.price,
            currency="INR",
            result_ref=best.dict(),
            is_mock=best.is_mock,
        )

    # ── Airport → Venue cab (Feature 4) ───────────────────────────────────────

    async def _search_airport_cab(
        self, session_id: str, meeting: MeetingInfo,
        context: TravelContext, search_fn
    ) -> Optional[JourneyLeg]:
        from models.travel import TravelContext as TC, TravelMode
        ctx = TC(**context.dict())
        ctx.destination = meeting.meeting_city
        ctx.mode        = TravelMode.CAR
        ctx.travel_date = meeting.meeting_date

        result: TravelSearchResult = await search_fn(session_id, ctx)
        cars = result.cars or []
        if not cars:
            return None

        best = min(cars, key=lambda c: c.price_per_day)
        airport_name = f"{meeting.meeting_city} Airport"
        venue = meeting.meeting_location or meeting.meeting_city or ""

        return JourneyLeg(
            leg_type="cab",
            description=f"🚗 Cab: {airport_name} → {venue}",
            from_location=airport_name,
            to_location=venue,
            duration_minutes=settings.CAB_BUFFER_MINUTES,
            price=best.price_per_day * 0.5,   # estimate: half-day rate for airport transfer
            currency="INR",
            result_ref=best.dict(),
            is_mock=best.is_mock,
        )

    # ── Hotel near meeting venue (Feature 5) ──────────────────────────────────

    async def _search_nearby_hotel(
        self, session_id: str, meeting: MeetingInfo,
        context: TravelContext, search_fn
    ) -> Optional[JourneyLeg]:
        from models.travel import TravelContext as TC, TravelMode
        ctx = TC(**context.dict())
        ctx.destination = meeting.meeting_city
        ctx.mode        = TravelMode.HOTEL
        ctx.travel_date = meeting.meeting_date
        # Preserve meeting lat/lng for proximity search
        ctx.meeting = meeting

        result: TravelSearchResult = await search_fn(session_id, ctx)
        hotels = result.hotels or []
        if not hotels:
            return None

        # Prefer hotels closest to meeting venue, then cheapest
        hotels_sorted = sorted(
            hotels,
            key=lambda h: (
                h.distance_from_meeting or h.distance_from_center or 999,
                h.price_per_night,
            )
        )
        best = hotels_sorted[0]
        nights = max(1, int(meeting.meeting_duration_hours / 24) + 1) if meeting.hotel_required else 1

        return JourneyLeg(
            leg_type="hotel",
            description=f"🏨 {best.name} ({best.stars}★) — {nights} night(s)",
            from_location=meeting.meeting_city or "",
            to_location=meeting.meeting_location or meeting.meeting_city or "",
            price=best.price_per_night * nights,
            currency="INR",
            result_ref=best.dict(),
            is_mock=best.is_mock,
        )

    # ── Return trip decision tree (Feature 6) ─────────────────────────────────

    async def _plan_return_trip(
        self, session_id: str, meeting: MeetingInfo,
        context: TravelContext, window: dict,
        search_fn, allowed: list
    ) -> List[JourneyLeg]:
        legs = []
        origin_city = meeting.current_city or context.origin or context.home_city
        if not origin_city:
            return []

        return_date = meeting.meeting_date   # same-day return default
        depart_after = window.get("return_departure_after", "14:00")

        # Decision tree: Flight → Train → Hotel (Feature 6)

        # Try return flight
        if ServiceType.FLIGHT in allowed:
            from models.travel import TravelContext as TC, TravelMode
            ctx = TC(**context.dict())
            ctx.origin      = meeting.meeting_city
            ctx.destination = origin_city
            ctx.travel_date = return_date
            ctx.mode        = TravelMode.FLIGHT

            result = await search_fn(session_id, ctx)
            flights = result.flights or []
            flights = meeting_planner.filter_flights_by_departure(flights, depart_after)

            if flights:
                best = min(flights, key=lambda f: f.price)
                seg = best.segments[0]
                legs.append(JourneyLeg(
                    leg_type="flight",
                    description=f"✈️ Return: {seg.airline} {seg.flight_number}: {meeting.meeting_city} → {origin_city}",
                    from_location=meeting.meeting_city or "",
                    to_location=origin_city,
                    depart_time=seg.departure_time if "T" not in seg.departure_time
                                else seg.departure_time.split("T")[1][:5],
                    duration_minutes=self._parse_duration(best.total_duration),
                    price=best.price, currency="INR",
                    result_ref=best.dict(), is_mock=best.is_mock,
                ))
                return legs

        # No return flight → try train
        if ServiceType.TRAIN in allowed:
            from models.travel import TravelContext as TC, TravelMode
            ctx = TC(**context.dict())
            ctx.origin      = meeting.meeting_city
            ctx.destination = origin_city
            ctx.travel_date = return_date
            ctx.mode        = TravelMode.TRAIN

            result = await search_fn(session_id, ctx)
            trains = result.trains or []

            if trains:
                best = min(trains, key=lambda t: min(
                    (c.price for c in t.classes if c.price), default=999999
                ))
                cheapest_cls = min(best.classes, key=lambda c: c.price)
                legs.append(JourneyLeg(
                    leg_type="train",
                    description=f"🚂 Return: {best.train_name} ({best.train_number}): {meeting.meeting_city} → {origin_city}",
                    from_location=meeting.meeting_city or "",
                    to_location=origin_city,
                    depart_time=best.departure_time,
                    duration_minutes=self._parse_duration(best.duration),
                    price=cheapest_cls.price, currency="INR",
                    result_ref=best.dict(), is_mock=best.is_mock,
                ))
                return legs

        # No flight or train → suggest stay another night
        if ServiceType.HOTEL in allowed:
            legs.append(JourneyLeg(
                leg_type="hotel",
                description=f"🏨 No return options found. Suggest staying another night in {meeting.meeting_city}.",
                from_location=meeting.meeting_city or "",
                to_location=meeting.meeting_city or "",
                price=0, currency="INR",
                is_mock=True,
            ))

        return legs

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_duration(duration_str: str) -> Optional[int]:
        """Parse '2h 30m' → 150 (minutes)."""
        if not duration_str:
            return None
        import re
        h = re.search(r"(\d+)h", duration_str)
        m = re.search(r"(\d+)m", duration_str)
        hours = int(h.group(1)) if h else 0
        mins  = int(m.group(1)) if m else 0
        return hours * 60 + mins if (hours or mins) else None


from config.settings import settings
journey_planner = JourneyPlannerService()
