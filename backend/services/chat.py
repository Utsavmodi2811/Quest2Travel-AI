"""
Chat Service — Master orchestrator.

New flow:
  User Message
    → Conversation Memory (context update + profile gathering)
    → Intent Detection
    → Permission Check
    → Meeting Planner (if meeting intent)
    → Journey Planner (multi-leg)  OR  Travel Search (simple)
    → Gemini Response Generator
    → Structured Response
"""

import logging
import uuid
from typing import Optional

from models.travel import (
    ChatRequest, ChatResponse, MessageRole, TravelMode,
    IntentType, ServiceType, JourneyPlan,
)
from memory.conversation import ConversationMemory
from agents.gemini_agent import gemini_agent
from services.travel_search import travel_search_service
from services.meeting_planner import meeting_planner
from services.journey_planner import journey_planner
from services.permission_service import permission_service
from utils.nlu import detect_intent, is_travel_query

logger = logging.getLogger(__name__)


class ChatService:

    async def process(self, request: ChatRequest) -> ChatResponse:
        session_id = request.session_id or str(uuid.uuid4())
        memory     = ConversationMemory(session_id)

        # ── 1. Update context from message ────────────────────────────────────
        context = await memory.update_context_from_message(
            request.message,
            user_id=request.user_id,
            company_id=request.company_id,
        )

        # Load allowed services for this company
        if context.company_id:
            context.allowed_services = await permission_service.get_allowed_services(
                context.company_id
            )

        # ── 2. Store user message ─────────────────────────────────────────────
        await memory.add_message(
            role=MessageRole.USER,
            content=request.message,
            travel_intent=context.mode,
        )

        # ── 3. Check if we need profile info first ─────────────────────────────
        # Feature 9: gather all info upfront
        profile_question = memory.needs_profile_info(context)
        if profile_question and not is_travel_query(request.message):
            assistant_msg = await memory.add_message(
                role=MessageRole.ASSISTANT,
                content=profile_question,
            )
            return ChatResponse(
                session_id=session_id,
                message_id=assistant_msg.message_id,
                reply=profile_question,
                intent_type=IntentType.GENERAL_CHAT,
                suggestions=["I'm in Delhi", "I'm in Mumbai", "I'm in Bangalore"],
            )

        # Mark profile complete once we have a home city
        if context.home_city and not context.profile_complete:
            context.profile_complete = True
            session = await memory.get_or_create_session()
            session.travel_context.profile_complete = True
            await memory.save_session(session)

        # ── 4. Detect intent ──────────────────────────────────────────────────
        intent_type = detect_intent(request.message)

        # ── 5. Permission check ───────────────────────────────────────────────
        permission_denied = False
        denied_service    = None

        if context.mode:
            service_map = {
                TravelMode.FLIGHT: ServiceType.FLIGHT,
                TravelMode.HOTEL:  ServiceType.HOTEL,
                TravelMode.TRAIN:  ServiceType.TRAIN,
                TravelMode.CAR:    ServiceType.CAR,
                TravelMode.BUS:    ServiceType.BUS,
            }
            svc = service_map.get(context.mode)
            if svc:
                allowed, deny_msg = await permission_service.is_allowed(
                    context.company_id, svc
                )
                if not allowed:
                    permission_denied = True
                    denied_service    = context.mode.value
                    history = await memory.get_conversation_history_for_gemini()
                    reply   = await gemini_agent.chat(
                        user_message=request.message,
                        history=history,
                        travel_context=context,
                        permission_denied=True,
                        denied_service=denied_service,
                    )
                    assistant_msg = await memory.add_message(
                        role=MessageRole.ASSISTANT,
                        content=reply,
                    )
                    return ChatResponse(
                        session_id=session_id,
                        message_id=assistant_msg.message_id,
                        reply=reply,
                        intent_type=intent_type,
                        travel_context=context,
                        permission_denied=True,
                        denied_service=denied_service,
                    )

        # ── 6. Meeting / Journey planning ─────────────────────────────────────
        journey_result: Optional[JourneyPlan] = None
        travel_results = None
        travel_results_dict = None

        if intent_type == IntentType.MEETING_PLAN and context.meeting:
            try:
                journey_result = await journey_planner.build_journey(
                    session_id=session_id,
                    meeting=context.meeting,
                    context=context,
                    travel_search_fn=travel_search_service.search,
                )
                await memory.store_journey_plan(journey_result)

                # Collect all sub-results for card display
                # Build a composite TravelSearchResult from journey legs
                travel_results_dict = self._journey_to_results_dict(journey_result)

                # Also run a plain flight search so cards show individual options
                if context.origin and context.meeting.meeting_city:
                    context.destination = context.meeting.meeting_city
                    context.travel_date = context.meeting.meeting_date
                    context.mode        = TravelMode.FLIGHT
                    if ServiceType.FLIGHT in context.allowed_services:
                        flight_search = await travel_search_service.search(session_id, context)
                        travel_results = flight_search

            except Exception as e:
                logger.error(f"Journey planning failed: {e}", exc_info=True)
                intent_type = IntentType.TRAVEL_SEARCH  # fall back to plain search

        # ── 7. Plain travel search ─────────────────────────────────────────────
        if intent_type != IntentType.MEETING_PLAN and is_travel_query(request.message):
            if context.destination or context.mode:
                try:
                    travel_results = await travel_search_service.search(session_id, context)
                    travel_results_dict = self._results_to_dict(travel_results)
                    await memory.store_search_results(travel_results_dict)
                    logger.info(
                        f"Search done: session={session_id} mode={context.mode} "
                        f"{context.origin}→{context.destination}"
                    )
                except Exception as e:
                    logger.error(f"Travel search failed: {e}", exc_info=True)

        # ── 8. Gemini response ────────────────────────────────────────────────
        history = await memory.get_conversation_history_for_gemini()
        reply   = await gemini_agent.chat(
            user_message=request.message,
            history=history,
            travel_context=context,
            travel_results=travel_results_dict,
            journey_plan=journey_result,
            intent_type=intent_type,
        )

        suggestions = await gemini_agent.generate_suggestions(context, intent_type)

        # ── 9. Store assistant message ────────────────────────────────────────
        assistant_msg = await memory.add_message(
            role=MessageRole.ASSISTANT,
            content=reply,
            travel_intent=context.mode,
            metadata={"has_results": travel_results is not None},
        )

        return ChatResponse(
            session_id=session_id,
            message_id=assistant_msg.message_id,
            reply=reply,
            intent_type=intent_type,
            travel_results=travel_results,
            journey_plan=journey_result,
            travel_context=context,
            suggestions=suggestions,
            is_travel_query=(travel_results is not None or journey_result is not None),
        )

    # ── Result dict builders ──────────────────────────────────────────────────

    def _results_to_dict(self, results) -> dict:
        if not results:
            return {}
        d = {
            "search_type": results.search_type.value,
            "origin":      results.origin,
            "destination": results.destination,
            "is_mock":     results.is_partial_mock,
        }
        if results.flights:
            d["flights"] = [
                {"airline": f.segments[0].airline if f.segments else "",
                 "flight":  f.segments[0].flight_number if f.segments else "",
                 "departure": f.segments[0].departure_time if f.segments else "",
                 "arrival":   f.segments[-1].arrival_time if f.segments else "",
                 "duration": f.total_duration, "stops": f.stops,
                 "class": f.cabin_class.value, "price_inr": f.price, "is_mock": f.is_mock}
                for f in results.flights[:5]
            ]
        if results.hotels:
            d["hotels"] = [
                {"name": h.name, "stars": h.stars, "rating": h.review_score,
                 "price": h.price_per_night, "breakfast": h.breakfast_included,
                 "dist_meeting": h.distance_from_meeting, "is_mock": h.is_mock}
                for h in results.hotels[:5]
            ]
        if results.trains:
            d["trains"] = [
                {"number": t.train_number, "name": t.train_name,
                 "departure": t.departure_time, "arrival": t.arrival_time,
                 "duration": t.duration,
                 "classes": [{"code": c.class_code, "price": c.price, "seats": c.available_seats}
                             for c in t.classes[:4]],
                 "is_mock": t.is_mock}
                for t in results.trains[:5]
            ]
        if results.buses:
            d["buses"] = [
                {"operator": b.operator, "type": b.bus_type,
                 "departure": b.departure_time, "arrival": b.arrival_time,
                 "price": b.price, "seats": b.available_seats, "is_mock": b.is_mock}
                for b in results.buses[:5]
            ]
        if results.cars:
            d["cars"] = [
                {"name": c.vehicle_name, "type": c.vehicle_type, "vendor": c.vendor,
                 "price_day": c.price_per_day, "seats": c.seats, "is_mock": c.is_mock}
                for c in results.cars[:5]
            ]
        return d

    def _journey_to_results_dict(self, journey: JourneyPlan) -> dict:
        """Convert journey legs to the format Gemini expects."""
        d = {"search_type": "journey", "is_mock": False}
        for leg in journey.legs:
            ref = leg.result_ref
            if not ref:
                continue
            if leg.leg_type == "flight":
                d.setdefault("flights", []).append({
                    "airline": ref.get("segments", [{}])[0].get("airline", "") if ref.get("segments") else "",
                    "price_inr": ref.get("price", 0),
                    "stops": ref.get("stops", 0),
                    "is_mock": ref.get("is_mock", False),
                })
            elif leg.leg_type == "hotel":
                d.setdefault("hotels", []).append({
                    "name": ref.get("name", ""), "stars": ref.get("stars", 3),
                    "price": ref.get("price_per_night", 0),
                    "dist_meeting": ref.get("distance_from_meeting"),
                    "is_mock": ref.get("is_mock", False),
                })
            elif leg.leg_type == "train":
                d.setdefault("trains", []).append({
                    "name": ref.get("train_name", ""),
                    "number": ref.get("train_number", ""),
                    "classes": ref.get("classes", []),
                    "is_mock": ref.get("is_mock", False),
                })
            elif leg.leg_type == "cab":
                d.setdefault("cars", []).append({
                    "name": ref.get("vehicle_name", "Cab"),
                    "price_day": leg.price or 0,
                    "is_mock": ref.get("is_mock", False),
                })
        return d


chat_service = ChatService()
