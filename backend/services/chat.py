"""
Main Chat Service.
Orchestrates: Memory → NLU → Travel Search → Gemini → Response.
"""

import logging
import uuid
from typing import Optional

from models.travel import ChatRequest, ChatResponse, MessageRole, TravelMode
from memory.conversation import ConversationMemory
from agents.gemini_agent import gemini_agent
from services.travel_search import travel_search_service
from utils.nlu import is_travel_query, is_greeting

logger = logging.getLogger(__name__)


class ChatService:

    async def process(self, request: ChatRequest) -> ChatResponse:
        # ── Session ───────────────────────────────────────────────────────────
        session_id = request.session_id or str(uuid.uuid4())
        memory = ConversationMemory(session_id)

        # ── Ensure session exists ─────────────────────────────────────────────
        await memory.get_or_create_session()

        # ── Update travel context from this message ───────────────────────────
        context = await memory.update_context_from_message(request.message)
        print("\n========== CONTEXT ==========")
        print("mode =", context.mode)
        print("origin =", context.origin)
        print("destination =", context.destination)
        print("=============================\n")

        # ── Store user message ────────────────────────────────────────────────
        await memory.add_message(
            role=MessageRole.USER,
            content=request.message,
            travel_intent=context.mode,
        )

        # ── Decide whether to run a travel search ─────────────────────────────
        needs_travel_search = (
            is_travel_query(request.message)
            and context.destination is not None
            and context.mode is not None
        )
        print("needs_travel_search =", needs_travel_search)

        travel_results     = None
        travel_results_dict = None

        # ── Travel Search ─────────────────────────────────────────────────────
        if needs_travel_search:
            try:
                travel_results = await travel_search_service.search(session_id, context)
                # Always build a results dict, even if every category came
                # back empty after filtering (e.g. "hotels under ₹500" with
                # no matches) — Gemini needs to know it was a *real* search
                # that legitimately found zero results, not "no search ran".
                travel_results_dict = self._results_to_dict(travel_results)
                await memory.store_search_results(travel_results_dict)
                logger.info(
                    f"Search complete for session={session_id}: "
                    f"mode={context.mode}, origin={context.origin}, "
                    f"destination={context.destination}"
                )
            except Exception as e:
                logger.error(f"Travel search failed for session={session_id}: {e}", exc_info=True)

        # ── Conversation history for Gemini ───────────────────────────────────
        history = await memory.get_conversation_history_for_gemini()

        # ── AI Response ───────────────────────────────────────────────────────
        reply = await gemini_agent.chat(
            user_message=request.message,
            history=history,
            travel_context=context,
            travel_results=travel_results_dict,
        )

        # ── Suggestions ───────────────────────────────────────────────────────
        suggestions = await gemini_agent.generate_suggestions(context)

        # ── Store assistant message ───────────────────────────────────────────
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
            travel_results=travel_results,
            travel_context=context,
            suggestions=suggestions,
            is_travel_query=needs_travel_search,
        )

    def _results_to_dict(self, results) -> dict:
        if not results:
            return {}
        d: dict = {
            "search_type": results.search_type.value,
            "origin":      results.origin,
            "destination": results.destination,
            "is_mock":     results.is_partial_mock,
        }
        if results.flights:
            d["flights"] = [
                {
                    "airline":     f.segments[0].airline if f.segments else "",
                    "flight":      f.segments[0].flight_number if f.segments else "",
                    "departure":   f.segments[0].departure_time if f.segments else "",
                    "arrival":     f.segments[-1].arrival_time if f.segments else "",
                    "duration":    f.total_duration,
                    "stops":       f.stops,
                    "class":       f.cabin_class.value,
                    "price_inr":   f.price,
                    "refundable":  f.is_refundable,
                    "is_mock":     f.is_mock,
                }
                for f in results.flights[:5]
            ]
        if results.trains:
            d["trains"] = [
                {
                    "number":    t.train_number,
                    "name":      t.train_name,
                    "departure": t.departure_time,
                    "arrival":   t.arrival_time,
                    "duration":  t.duration,
                    "classes":   [{"code": c.class_code, "price": c.price, "seats": c.available_seats}
                                  for c in t.classes[:4]],
                    "is_mock":   t.is_mock,
                }
                for t in results.trains[:5]
            ]
        if results.buses:
            d["buses"] = [
                {
                    "operator":  b.operator,
                    "type":      b.bus_type,
                    "departure": b.departure_time,
                    "arrival":   b.arrival_time,
                    "duration":  b.duration,
                    "price":     b.price,
                    "seats":     b.available_seats,
                    "is_mock":   b.is_mock,
                }
                for b in results.buses[:5]
            ]
        if results.hotels:
            d["hotels"] = [
                {
                    "name":       h.name,
                    "stars":      h.stars,
                    "rating":     h.review_score,
                    "price":      h.price_per_night,
                    "breakfast":  h.breakfast_included,
                    "cancel":     h.free_cancellation,
                    "is_mock":    h.is_mock,
                }
                for h in results.hotels[:5]
            ]
        if results.cars:
            d["cars"] = [
                {
                    "name":      c.vehicle_name,
                    "type":      c.vehicle_type,
                    "vendor":    c.vendor,
                    "price_day": c.price_per_day,
                    "seats":     c.seats,
                    "is_mock":   c.is_mock,
                }
                for c in results.cars[:5]
            ]
        return d


chat_service = ChatService()
