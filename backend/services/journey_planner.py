"""
Journey Planner Service.
Builds a complete multi-leg journey plan using the user's CHOSEN travel modes
(gathered adaptively by TripGatherer) — not hardcoded to flights.

Outbound leg:  respects meeting.outbound_mode (flight|train|bus|car|any)
Return leg:    respects meeting.return_mode   (may differ from outbound)
Hotel:         only when meeting.hotel_required is True
Cab:           auto-added after any air/train/bus arrival at destination
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta

from config.settings import settings
from models.travel import (
    JourneyPlan, JourneyLeg, TravelContext, MeetingInfo,
    TravelMode, ServiceType, TravelSearchResult,
)
from services.meeting_planner import meeting_planner
from services.permission_service import permission_service
from utils.time_filter import filter_flights_for_meeting
logger = logging.getLogger(__name__)

# Map string mode names → TravelMode enum
MODE_MAP = {
    "flight": TravelMode.FLIGHT,
    "train":  TravelMode.TRAIN,
    "bus":    TravelMode.BUS,
    "car":    TravelMode.CAR,
    "any":    None,  # default to flight for "any"
}


class JourneyPlannerService:

    async def build_journey(
        self,
        session_id: str,
        meeting: MeetingInfo,
        context: TravelContext,
        travel_search_fn,
    ) -> JourneyPlan:
        journey = JourneyPlan(session_id=session_id, meeting=meeting)

        # Prevent None errors
        allowed = set(
            await permission_service.get_allowed_services(
                context.company_id
            )
        )

        # Validate required fields
        required = {
            "meeting_city": meeting.meeting_city,
            "meeting_date": meeting.meeting_date,
            "origin": context.origin,
        }

        for field, value in required.items():
            if value is None:
                raise ValueError(f"{field} is missing")
        # ── Time window ────────────────────────────────────────────────────────
        window = meeting_planner.compute_travel_window(meeting)
        journey.timeline_summary = meeting_planner.describe_timeline(window)
        context.required_arrival_by = window.get("flight_arrival_by")

        # ── Outbound leg ───────────────────────────────────────────────────────
        out_mode = (
            meeting.outbound_mode
            or context.mode.value if context.mode else None
        )

        if not out_mode:
            raise ValueError("Outbound travel mode is missing.")
        out_leg  = await self._search_outbound(
            session_id, meeting, context, window, travel_search_fn, out_mode, allowed
        )
        if out_leg:
            journey.legs.append(out_leg)

        # ── Cab: station/airport → venue (auto-added for non-car modes) ────────
        if out_mode in ("flight", "train", "bus") and ServiceType.CAR in allowed:
            cab_leg = await self._search_transfer_cab(
                session_id, meeting, context, travel_search_fn
            )
            if cab_leg:
                journey.legs.append(cab_leg)

        # ── Hotel (only if user said yes) ──────────────────────────────────────
        hotel_needed = meeting.hotel_required

        if hotel_needed and ServiceType.HOTEL in allowed and meeting.meeting_city:
            hotel_leg = await self._search_hotel(
                session_id,
                meeting,
                context,
                travel_search_fn,
            )


            if hotel_leg:
                journey.legs.append(hotel_leg)

        # ── Return leg (only if round_trip confirmed) ──────────────────────────
        if meeting.return_required:
            ret_mode  = meeting.return_mode or out_mode
            ret_date  = (meeting.return_date or meeting.meeting_date or
                         datetime.now().strftime("%Y-%m-%d"))
            ret_after = meeting.return_time or window.get("return_departure_after", "14:00")

            ret_legs = await self._plan_return(
                session_id, meeting, context, travel_search_fn,
                ret_mode, ret_date, ret_after, allowed
            )
            journey.legs.extend(ret_legs)

        journey.total_estimated_cost = sum(leg.price or 0 for leg in journey.legs)

        print("=" * 80)
        print("JOURNEY CREATED")
        print("TOTAL LEGS :", len(journey.legs))
        print("TOTAL COST :", journey.total_estimated_cost)

        for leg in journey.legs:
            print(leg)

        print("=" * 80)

        return journey

    # ── Outbound (mode-aware) ─────────────────────────────────────────────────

    async def _search_outbound(
        self, session_id, meeting, context, window,
        search_fn, mode: str, allowed
    ) -> Optional[JourneyLeg]:
        origin      = meeting.current_city or context.origin or context.home_city
        destination = meeting.meeting_city
        date        = meeting.meeting_date

        if not origin or not destination:
            return None

        travel_mode = MODE_MAP.get(mode, TravelMode.FLIGHT)

        # Check company permission
        svc_map = {TravelMode.FLIGHT: ServiceType.FLIGHT,
                   TravelMode.TRAIN:  ServiceType.TRAIN,
                   TravelMode.BUS:    ServiceType.BUS,
                   TravelMode.CAR:    ServiceType.CAR}
        svc = svc_map.get(travel_mode)
        if svc and svc not in allowed:
            logger.warning(f"Outbound {mode} not allowed for company {context.company_id}")
            # Fall back to first allowed transport mode
            for fallback_svc, fallback_mode in [
                (ServiceType.FLIGHT, TravelMode.FLIGHT),
                (ServiceType.TRAIN, TravelMode.TRAIN),
                (ServiceType.BUS, TravelMode.BUS),
                (ServiceType.CAR, TravelMode.CAR),
            ]:
                if fallback_svc in allowed:
                    travel_mode = fallback_mode
                    break
            else:
                return None

        from models.travel import TravelContext as TC
        ctx = TC(**context.dict())
        ctx.origin      = origin
        ctx.destination = destination
        ctx.travel_date = date
        ctx.mode        = travel_mode

        result: TravelSearchResult = await search_fn(session_id, ctx)

        if travel_mode == TravelMode.FLIGHT:
            items = result.flights or []
            if window.get("flight_arrival_by") and items:
                items = meeting_planner.filter_flights_by_arrival(items, window["flight_arrival_by"])
            if not items:
                return None
            best = min(items, key=lambda f: f.price)
            seg  = best.segments[0]
            return JourneyLeg(
                leg_type="flight",
                description=f"✈️ {seg.airline} {seg.flight_number}: {origin} → {destination}",
                from_location=origin, to_location=destination,
                depart_time=self._fmt_time(seg.departure_time),
                arrive_time=self._fmt_time(best.segments[-1].arrival_time),
                duration_minutes=self._parse_dur(best.total_duration),
                price=best.price, currency="INR",
                result_ref=best.dict(), is_mock=best.is_mock,
            )

        elif travel_mode == TravelMode.TRAIN:
            items = result.trains or []

            if window.get("flight_arrival_by"):
                items = meeting_planner.filter_trains_by_arrival(
                    items,
                    window["flight_arrival_by"],
                )

            if not items:
                logger.warning("No train can reach before the meeting.")
                return None
            best     = min(items, key=lambda t: min((c.price for c in t.classes if c.price), default=999999))
            best_cls = min(best.classes, key=lambda c: c.price)
            return JourneyLeg(
                leg_type="train",
                description=f"🚂 {best.train_name} ({best.train_number}): {origin} → {destination}",
                from_location=origin, to_location=destination,
                depart_time=best.departure_time,
                arrive_time=best.arrival_time,
                duration_minutes=self._parse_dur(best.duration),
                price=best_cls.price, currency="INR",
                result_ref=best.dict(), is_mock=best.is_mock,
            )

        elif travel_mode == TravelMode.BUS:
            items = result.buses or []
            if not items:
                return None
            best = min(items, key=lambda b: b.price)
            return JourneyLeg(
                leg_type="bus",
                description=f"🚌 {best.operator} ({best.bus_type}): {origin} → {destination}",
                from_location=origin, to_location=destination,
                depart_time=best.departure_time,
                arrive_time=best.arrival_time,
                duration_minutes=self._parse_dur(best.duration),
                price=best.price, currency="INR",
                result_ref=best.dict(), is_mock=best.is_mock,
            )

        elif travel_mode == TravelMode.CAR:
            items = result.cars or []
            if not items:
                return None
            best = min(items, key=lambda c: c.price_per_day)
            return JourneyLeg(
                leg_type="car",
                description=f"🚗 Self-drive: {origin} → {destination}",
                from_location=origin, to_location=destination,
                price=best.price_per_day, currency="INR",
                result_ref=best.dict(), is_mock=best.is_mock,
            )

        return None

    # ── Transfer cab: terminal → venue ────────────────────────────────────────

    async def _search_transfer_cab(
        self, session_id, meeting, context, search_fn
    ) -> Optional[JourneyLeg]:
        from models.travel import TravelContext as TC, TravelMode
        ctx = TC(**context.dict())
        ctx.destination = meeting.meeting_city
        ctx.mode        = TravelMode.CAR
        ctx.travel_date = meeting.meeting_date

        result = await search_fn(session_id, ctx)
        cars   = result.cars or []
        if not cars:
            return None

        best    = min(cars, key=lambda c: c.price_per_day)
        venue   = meeting.meeting_location or meeting.meeting_city or ""
        outmode = meeting.outbound_mode or "flight"
        origin_label = (
            f"{meeting.meeting_city} Airport"   if outmode == "flight" else
            f"{meeting.meeting_city} Station"   if outmode == "train"  else
            f"{meeting.meeting_city} Bus Stand" if outmode == "bus"    else
            meeting.meeting_city or ""
        )
        return JourneyLeg(
            leg_type="cab",
            description=f"🚗 Transfer: {origin_label} → {venue}",
            from_location=origin_label, to_location=venue,
            duration_minutes=settings.CAB_BUFFER_MINUTES,
            price=round(best.price_per_day * 0.4, 0),   # ~40% of daily rate for transfer
            currency="INR",
            result_ref=best.dict(), is_mock=best.is_mock,
        )

    # ── Hotel near meeting venue ──────────────────────────────────────────────

    async def _search_hotel(
        self, session_id, meeting, context, search_fn
    ) -> Optional[JourneyLeg]:
        from models.travel import TravelContext as TC, TravelMode
        ctx = TC(**context.dict())
        ctx.destination = meeting.meeting_city
        ctx.mode        = TravelMode.HOTEL
        ctx.travel_date = meeting.meeting_date
        ctx.meeting     = meeting

        result = await search_fn(session_id, ctx)
        hotels = result.hotels or []
        if not hotels:
            return None

        hotels_sorted = sorted(
            hotels,
            key=lambda h: (
                h.distance_from_meeting
                if h.distance_from_meeting is not None
                else 999,
                h.price_per_night,
            )
        )
        best = hotels_sorted[0]

        # Compute nights
        checkin  = meeting.meeting_date or datetime.now().strftime("%Y-%m-%d")
        checkout = (meeting.return_date or
                    (datetime.strptime(checkin, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d"))
        try:
            nights = max(1, (datetime.strptime(checkout, "%Y-%m-%d") -
                             datetime.strptime(checkin, "%Y-%m-%d")).days)
        except Exception:
            nights = 1

        return JourneyLeg(
            leg_type="hotel",
            description=f"🏨 {best.name} ({best.stars}★) — {nights} night{'s' if nights>1 else ''}",
            from_location=meeting.meeting_city or "",
            to_location=meeting.meeting_location or meeting.meeting_city or "",
            price=best.price_per_night * nights, currency="INR",
            result_ref=best.dict(), is_mock=best.is_mock,
        )

    # ── Return trip (mode-aware decision tree) ────────────────────────────────

    async def _plan_return(
        self, session_id, meeting, context, search_fn,
        ret_mode: str, ret_date: str, depart_after: str, allowed
    ) -> List[JourneyLeg]:
        legs        = []
        origin_city = meeting.current_city or context.origin or context.home_city
        if not origin_city:
            return []

        travel_mode = MODE_MAP.get(ret_mode, TravelMode.FLIGHT)
        svc_map     = {TravelMode.FLIGHT: ServiceType.FLIGHT,
                       TravelMode.TRAIN:  ServiceType.TRAIN,
                       TravelMode.BUS:    ServiceType.BUS}

        # Try the preferred mode; fall back if not allowed
        modes_to_try = [travel_mode]
        for fallback in [TravelMode.FLIGHT, TravelMode.TRAIN, TravelMode.BUS]:
            if fallback not in modes_to_try:
                modes_to_try.append(fallback)

        for attempt_mode in modes_to_try:
            svc = svc_map.get(attempt_mode)
            if svc and svc not in allowed:
                continue

            from models.travel import TravelContext as TC
            ctx = TC(**context.dict())
            ctx.origin      = meeting.meeting_city
            ctx.destination = origin_city
            ctx.travel_date = ret_date
            ctx.mode        = attempt_mode

            result = await search_fn(session_id, ctx)
            icon   = {"flight": "✈️", "train": "🚂", "bus": "🚌"}.get(
                attempt_mode.value if hasattr(attempt_mode, 'value') else str(attempt_mode), "🚀"
            )

            if attempt_mode == TravelMode.FLIGHT:
                items = result.flights or []
                items = meeting_planner.filter_flights_by_departure(items, depart_after)
                if items:
                    best = min(items, key=lambda f: f.price)
                    seg  = best.segments[0]
                    legs.append(JourneyLeg(
                        leg_type="flight",
                        description=f"✈️ Return: {seg.airline} {seg.flight_number}: {meeting.meeting_city} → {origin_city}",
                        from_location=meeting.meeting_city or "", to_location=origin_city,
                        depart_time=self._fmt_time(seg.departure_time),
                        duration_minutes=self._parse_dur(best.total_duration),
                        price=best.price, currency="INR",
                        result_ref=best.dict(), is_mock=best.is_mock,
                    ))
                    return legs

            elif attempt_mode == TravelMode.TRAIN:
                items = result.trains or []
                if items:
                    best     = min(items, key=lambda t: min((c.price for c in t.classes if c.price), default=999999))
                    best_cls = min(best.classes, key=lambda c: c.price)
                    legs.append(JourneyLeg(
                        leg_type="train",
                        description=f"🚂 Return: {best.train_name}: {meeting.meeting_city} → {origin_city}",
                        from_location=meeting.meeting_city or "", to_location=origin_city,
                        depart_time=best.departure_time,
                        duration_minutes=self._parse_dur(best.duration),
                        price=best_cls.price, currency="INR",
                        result_ref=best.dict(), is_mock=best.is_mock,
                    ))
                    return legs

            elif attempt_mode == TravelMode.BUS:
                items = result.buses or []
                if items:
                    best = min(items, key=lambda b: b.price)
                    legs.append(JourneyLeg(
                        leg_type="bus",
                        description=f"🚌 Return: {best.operator}: {meeting.meeting_city} → {origin_city}",
                        from_location=meeting.meeting_city or "", to_location=origin_city,
                        depart_time=best.departure_time,
                        price=best.price, currency="INR",
                        result_ref=best.dict(), is_mock=best.is_mock,
                    ))
                    return legs

        # Nothing found — suggest hotel instead
        if ServiceType.HOTEL in allowed:
            legs.append(JourneyLeg(
                leg_type="hotel",
                description=f"🏨 No return options found — consider staying another night in {meeting.meeting_city}",
                from_location=meeting.meeting_city or "",
                to_location=meeting.meeting_city or "",
                price=0, currency="INR", is_mock=True,
            ))
        return legs

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_time(raw: str) -> str:
        if not raw:
            return ""
        return raw.split("T")[1][:5] if "T" in raw else raw[:5]

    @staticmethod
    def _parse_dur(duration_str: str) -> Optional[int]:
        import re
        if not duration_str:
            return None
        h = re.search(r"(\d+)h", duration_str)
        m = re.search(r"(\d+)m", duration_str)
        hours = int(h.group(1)) if h else 0
        mins  = int(m.group(1)) if m else 0
        return hours * 60 + mins if (hours or mins) else None


journey_planner = JourneyPlannerService()