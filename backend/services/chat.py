"""
Chat Service — Master orchestrator.

Full pipeline:
  User Message
    → Conversation Memory (context update)
    → Intent Detection
    → Permission Check
    → [MEETING] Adaptive Trip Gatherer (ask questions until complete)
    → [MEETING] Journey Planner (only when gathering_complete)
    → [TRAVEL]  Travel Search (plain route searches)
    → Gemini Response
    → Structured Response
"""

import logging
import uuid
from typing import Optional
import traceback
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
from services.trip_gatherer import TripGatherer, GatheringState
from utils.nlu import detect_intent, is_travel_query
from models.travel import MeetingInfo
logger = logging.getLogger(__name__)

_gatherer = TripGatherer()


class ChatService:

    async def process(self, request: ChatRequest) -> ChatResponse:
        session_id = request.session_id or str(uuid.uuid4())
        memory     = ConversationMemory(session_id)

        # ── 1. Update context ─────────────────────────────────────────────────
        context = await memory.update_context_from_message(
            request.message,
            user_id=request.user_id,
            company_id=request.company_id,
        )
        meeting_in_progress = (
            context.meeting
            and context.meeting.gathering_state
            and not context.meeting.gathering_complete
        )
        print("=" * 50)
        print("NEW MESSAGE:", request.message)
        print("Meeting:", context.meeting)
        print("Origin:", context.origin)
        print("Mode:", context.mode)
        print("=" * 50)

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

        # ── 3. Profile gathering (ask city once if missing) ───────────────────
        profile_question = memory.needs_profile_info(context)

        meeting_in_progress = (
            context.meeting
            and context.meeting.gathering_state
            and not context.meeting.gathering_complete
        )

        if (
            not meeting_in_progress
            and profile_question
            and not is_travel_query(request.message)
        ):
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

        # User has just completed their profile.
        # Don't continue into travel search.
        if (
            not meeting_in_progress
            and context.profile_complete
            and request.message.strip().lower() == context.home_city.lower()
        ):
            assistant_msg = await memory.add_message(
                role=MessageRole.ASSISTANT,
                content=f"Great! I'll remember that you're based in {context.home_city}. How can I help you today?",
            )

            return ChatResponse(
                session_id=session_id,
                message_id=assistant_msg.message_id,
                reply=f"Great! I'll remember that you're based in {context.home_city}. How can I help you today?",
                intent_type=IntentType.GENERAL_CHAT,
                travel_context=context,
                suggestions=[
                    "I have a meeting tomorrow",
                    "Book a flight",
                    "Find hotels",
                    "Plan a trip",
                ],
            )

        if (
            not meeting_in_progress
            and context.home_city
            and not context.profile_complete
        ):
            context.profile_complete = True

            session = await memory.get_or_create_session()
            session.travel_context = context
            await memory.save_session(session)

            assistant_msg = await memory.add_message(
                role=MessageRole.ASSISTANT,
                content=(
                    f"Great! I'll remember that you're in {context.home_city}. "
                    "How can I help you today?"
                ),
            )

            return ChatResponse(
                session_id=session_id,
                message_id=assistant_msg.message_id,
                reply=f"Great! I'll remember that you're in {context.home_city}. How can I help you today?",
                intent_type=IntentType.GENERAL_CHAT,
                travel_context=context,
                suggestions=[
                    "I have a meeting tomorrow",
                    "Book a flight",
                    "Find hotels",
                    "Plan a trip",
                ],
            )

        # ── 4. Intent detection ───────────────────────────────────────────────
        if (
            context.meeting
            and context.meeting.gathering_complete is False
        ):

            intent_type = IntentType.MEETING_PLAN

        else:

            # Continue gathering if a meeting is already in progress
            if (
                context.meeting
                and context.meeting.gathering_state
                and not context.meeting.gathering_complete
            ):
                intent_type = IntentType.MEETING_PLAN
            else:
                intent_type = detect_intent(request.message)
        logger.info(
            "Intent=%s | Message=%s",
            intent_type,
            request.message,
        )
        # ── 5. Permission check ───────────────────────────────────────────────
        permission_denied = False
        denied_service    = None

        if context.mode:
            svc_map = {
                TravelMode.FLIGHT: ServiceType.FLIGHT,
                TravelMode.HOTEL:  ServiceType.HOTEL,
                TravelMode.TRAIN:  ServiceType.TRAIN,
                TravelMode.CAR:    ServiceType.CAR,
                TravelMode.BUS:    ServiceType.BUS,
            }
            svc = svc_map.get(context.mode)
            if svc:
                allowed, _ = await permission_service.is_allowed(context.company_id, svc)
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
                        role=MessageRole.ASSISTANT, content=reply,
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

        # ── 6. Meeting / Journey planning (adaptive gathering) ─────────────────
        journey_result: Optional[JourneyPlan] = None
        travel_results      = None
        travel_results_dict = None
        logger.info(
            "Meeting exists=%s",
            context.meeting is not None,
        )

        # Create meeting context if this is the first meeting message
        if intent_type == IntentType.MEETING_PLAN and context.meeting is None:
            context.meeting = MeetingInfo()# or your meeting model

        if intent_type == IntentType.MEETING_PLAN:
            meeting = context.meeting

            # Load or create GatheringState from persisted dict
            gs_dict = meeting.gathering_state or {}
            state   = GatheringState.from_dict(gs_dict) if gs_dict else GatheringState()
            print("=" * 60)
            print("BEFORE update_from_message")
            print("Origin      :", state.origin)
            print("Destination :", state.destination)
            print("Home city   :", context.home_city)
            print("Ctx origin  :", context.origin)
            print("Meeting city:", context.meeting.meeting_city if context.meeting else None)
            # Update state with what NLU / context already knows
            state = _gatherer.update_from_message(state, request.message, context)
            print("=" * 60)
            print("AFTER update_from_message")
            print("Origin      :", state.origin)
            print("Destination :", state.destination)
            print("=" * 60)
            print("=" * 80)
            print("STATE AFTER UPDATE")
            print("Origin      :", state.origin)
            print("Destination :", state.destination)
            print("Context Home:", context.home_city)
            print("Context Orig:", context.origin)
            print("Context Dest:", context.destination)
            print("=" * 80)
            # Keep TravelContext synchronized with GatheringState
            context.origin = state.origin
            context.destination = state.destination

            if state.outbound_mode:
                context.mode = TravelMode(state.outbound_mode)

            if state.travel_date:
                context.travel_date = state.travel_date
            context.mode = state.outbound_mode or context.mode
            context.travel_date = state.travel_date
            if not meeting.meeting_city and state.destination:
                meeting.meeting_city = state.destination
            meeting.current_city = state.origin

            if state.travel_date:
                meeting.meeting_date = state.travel_date

            if state.meeting_time:
                meeting.meeting_time = state.meeting_time
            meeting.gathering_state = state.to_dict()
            context.meeting = meeting

            session = await memory.get_or_create_session()
            session.travel_context = context
            await memory.save_session(session)
            print(state.to_dict())
            print("RETURN DATE :", state.return_date)
            print("RETURN TIME :", state.return_time)
            print("HOTEL       :", state.hotel_needed)
            print("COMPLETE    :", state.is_complete())
            logger.info("=" * 60)
            logger.info("Gathering State Updated")
            logger.info(state.to_dict())
            logger.info("=" * 60)
            # Check if gathering is complete
            print("CHECKING COMPLETENESS")
            if not state.is_complete():
                print("=" * 80)
                print("BEFORE next_question")
                print(state.to_dict())
                print("=" * 80)
                # Ask the next question
                question = _gatherer.next_question(state)

                # Safety check: if somehow no question is available,
                # don't continue planning yet.
                if not question:
                    logger.warning(
                        "TripGatherer returned no question although gathering is incomplete."
                    )
                    question = (
                        "I need a little more information before I can plan your trip."
                    )

                # Persist updated state
                meeting.gathering_state = state.to_dict()
                context.meeting = meeting

                session = await memory.get_or_create_session()
                session.travel_context = context
                await memory.save_session(session)

                assistant_msg = await memory.add_message(
                    role=MessageRole.ASSISTANT,
                    content=question,
                    metadata={"gathering": True},
                )

                suggestions = self._gathering_suggestions(state)
                print("=" * 50)
                print("STATE")
                print(state.to_dict())
                print("QUESTION :", question)
                print("SUGGESTIONS :", suggestions)
                print("=" * 50)
                return ChatResponse(
                    session_id=session_id,
                    message_id=assistant_msg.message_id,
                    reply=question,
                    intent_type=intent_type,
                    travel_context=context,
                    suggestions=suggestions,
                )

            # Only reach here when gathering is actually complete   
            logger.info(
                "Gathering status -> complete=%s, state_complete=%s, state=%s",
                meeting.gathering_complete,
                state.is_complete(),
                state.to_dict(),
            )
            if state.is_complete():
                # Apply gathered state back to context
                meeting.gathering_complete = True
                context = _gatherer.apply_to_context(state, context)
                meeting.gathering_state    = state.to_dict()
                context.meeting            = meeting

                # Show confirmation summary before building plan
                summary = _gatherer.summarize_gathered(state)

                # Update meeting fields from state
                if state.outbound_mode:
                    meeting.outbound_mode = state.outbound_mode
                if state.return_mode:
                    meeting.return_mode = state.return_mode
                if state.return_date:
                    meeting.return_required = True
                    meeting.return_date     = state.return_date
                    meeting.return_time     = state.return_time
                if state.hotel_needed is not None:
                    meeting.hotel_required = state.hotel_needed
                if state.outbound_class:
                    meeting.outbound_class = state.outbound_class
                print("=" * 80)
                print("MEETING CITY :", meeting.meeting_city)
                print("MEETING DATE :", meeting.meeting_date)
                print("RETURN DATE  :", meeting.return_date)
                print("RETURN TIME  :", meeting.return_time)
                print("ORIGIN       :", context.origin)
                print("DESTINATION  :", context.destination)
                print("MODE         :", context.mode)
                print("=" * 80)
                # Build the journey plan
                try:
                    journey_result = await journey_planner.build_journey(
                        session_id=session_id,
                        meeting=meeting,
                        context=context,
                        travel_search_fn=travel_search_service.search,
                    )
                    await memory.store_journey_plan(journey_result)
                    travel_results_dict = self._journey_to_results_dict(journey_result)

                    # Also run outbound travel search for full card display
                    if context.origin and meeting.meeting_city:
                        context.destination = meeting.meeting_city
                        if not context.travel_date:
                            context.travel_date = meeting.meeting_date
                        try:
                            travel_results = await travel_search_service.search(
                                session_id, context
                            )
                            window = meeting_planner.compute_travel_window(meeting)

                            if (
                                context.mode == TravelMode.FLIGHT
                                and travel_results.flights
                                and window.get("flight_arrival_by")
                            ):
                                travel_results.flights = meeting_planner.filter_flights_by_arrival(
                                    travel_results.flights,
                                    window["flight_arrival_by"],
                                )
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
                            logger.exception(e)
                            raise

                    reply = summary
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    logger.exception(e)
                    raise
                    intent_type = IntentType.TRAVEL_SEARCH

                # Persist final context
                session = await memory.get_or_create_session()
                session.travel_context = context
                await memory.save_session(session)

                history = await memory.get_conversation_history_for_gemini()
                if journey_result:
                    ai_reply = await gemini_agent.chat(
                        user_message=request.message,
                        history=history,
                        travel_context=context,
                        travel_results=travel_results_dict,
                        journey_plan=journey_result,
                        intent_type=intent_type,
                    )
                    # Prepend summary then AI commentary
                    full_reply = f"{summary}\n\n{ai_reply}" if ai_reply and ai_reply != summary else summary
                else:
                    full_reply = reply

                if context.meeting and not context.meeting.gathering_complete:
                    suggestions = self._gathering_suggestions(state)
                else:
                    if (
                        context.meeting
                        and context.meeting.gathering_state
                        and not context.meeting.gathering_complete
                    ):
                        state = GatheringState.from_dict(context.meeting.gathering_state)
                        suggestions = self._gathering_suggestions(state)
                    else:
                        suggestions = await gemini_agent.generate_suggestions(
                            context,
                            intent_type,
                        )
                assistant_msg = await memory.add_message(
                    role=MessageRole.ASSISTANT,
                    content=full_reply,
                    travel_intent=context.mode,
                    metadata={"has_results": journey_result is not None},
                )
                print("=" * 60)
                print("TRAVEL RESULTS")
                print(travel_results)
                print("=" * 60)
                return ChatResponse(
                    session_id=session_id,
                    message_id=assistant_msg.message_id,
                    reply=full_reply,
                    intent_type=intent_type,
                    travel_results=travel_results,
                    journey_plan=journey_result,
                    travel_context=context,
                    suggestions=suggestions,
                    is_travel_query=True,
                )

        # ── 7. Plain travel search / filter refinement ────────────────────────
        print("=" * 60)
        print("SHOULD SEARCH CHECK")
        print("Message      :", request.message)
        print("Intent       :", intent_type)
        print("Origin       :", context.origin)
        print("Destination  :", context.destination)
        print("Mode         :", context.mode)
        print("Travel Query :", is_travel_query(request.message))
        print("=" * 60)
        should_search = (
            intent_type != IntentType.MEETING_PLAN
            and (
                is_travel_query(request.message)
                or intent_type == IntentType.FILTER_REFINE
            )
            and context.origin
            and context.destination
            and context.mode
        )
        logger.info(
            "should_search=%s origin=%s destination=%s mode=%s intent=%s",
            should_search,
            context.origin,
            context.destination,
            context.mode,
            intent_type,
        )
        if should_search:
            try:
                travel_results = await travel_search_service.search(session_id, context)
                travel_results_dict = self._results_to_dict(travel_results)
                await memory.store_search_results(travel_results_dict)
                logger.info(
                    f"Search done: session={session_id} mode={context.mode} "
                    f"{context.origin}→{context.destination}"
                )
            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.exception(e)
                raise

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

    # ── Suggestion helpers ────────────────────────────────────────────────────

    def _gathering_suggestions(self, state):
        print("INSIDE _gathering_suggestions")
        print(state.to_dict())

        if not state.origin:
            return [
                "Ahmedabad",
                "Mumbai",
                "Delhi",
                "Bangalore",
            ]

        if not state.destination:

            cities = [
                "Delhi",
                "Mumbai",
                "Bangalore",
                "Hyderabad",
                "Ahmedabad",
                "Pune",
                "Chennai",
                "Goa",
            ]

            if state.origin:
                cities = [
                    c for c in cities
                    if c.lower() != state.origin.lower()
                ]

            return cities[:4]
        if not state.meeting_time:
            return [
                "9 AM",
                "10 AM",
                "1 PM",
                "3 PM",
            ]
        if not state.outbound_mode:
            return [
                "Flight",
                "Train",
                "Bus",
                "Car",
            ]

        if not state.trip_type:
            return [
                "One-way",
                "Round trip",
            ]

        if state.trip_type == "round_trip" and not state.return_date:
            return [
                "Same day",
                "Tomorrow evening",
                "Next day",
            ]

        if (
            state.trip_type == "round_trip"
            and state.return_date
            and not state.return_time
        ):
            return [
                "4 PM",
                "6 PM",
                "8 PM",
                "10 PM",
            ]

        if state.trip_type == "round_trip" and not state.return_mode:
            return [
                f"Same as {state.outbound_mode.title()}",
                "Flight",
                "Train",
                "Bus",
                "Car",
            ]

        if _gatherer.should_ask_hotel(state):

            return [

                "Yes",

                "No"

            ]

        if state.hotel_needed and not state.hotel_checkout:
            return [
                "1 Night",
                "2 Nights",
                "3 Nights",
            ]

        return [
            "Economy",
            "Business",
            "₹5000 Budget",
            "₹10000 Budget",
            "Plan my trip",
        ]

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
                 "class": f.cabin_class.value, "price_inr": f.price,
                 "is_mock": f.is_mock}
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
                 "classes": [{"code": c.class_code, "price": c.price,
                              "seats": c.available_seats} for c in t.classes[:4]],
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
        d = {"search_type": "journey", "is_mock": False}
        for leg in journey.legs:
            ref = leg.result_ref
            if not ref:
                continue
            if leg.leg_type == "flight":
                segs = ref.get("segments", [])
                d.setdefault("flights", []).append({
                    "airline":   segs[0].get("airline", "") if segs else "",
                    "price_inr": ref.get("price", 0),
                    "stops":     ref.get("stops", 0),
                    "is_mock":   ref.get("is_mock", False),
                })
            elif leg.leg_type == "train":
                d.setdefault("trains", []).append({
                    "name":    ref.get("train_name", ""),
                    "number":  ref.get("train_number", ""),
                    "classes": ref.get("classes", []),
                    "is_mock": ref.get("is_mock", False),
                })
            elif leg.leg_type == "hotel":
                d.setdefault("hotels", []).append({
                    "name":           ref.get("name", ""),
                    "stars":          ref.get("stars", 3),
                    "price":          ref.get("price_per_night", 0),
                    "dist_meeting":   ref.get("distance_from_meeting"),
                    "is_mock":        ref.get("is_mock", False),
                })
            elif leg.leg_type in ("cab", "car"):
                d.setdefault("cars", []).append({
                    "name":      ref.get("vehicle_name", "Cab"),
                    "price_day": leg.price or 0,
                    "is_mock":   ref.get("is_mock", False),
                })
        return d


chat_service = ChatService()