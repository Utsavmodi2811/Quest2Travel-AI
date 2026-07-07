"""
Conversation Memory Manager.
Maintains travel context, user profile, and meeting info across turns.

Key behaviour:
  - Profile gathering: on first contact, bot collects home city + preferences
    ONCE and stores them in context.profile_complete = True.
  - Context reset: new route or destination-only clears stale fields.
  - Meeting context: fully preserves meeting + journey plan between turns.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from database.connection import get_db
from models.travel import (
    Session, Message, TravelContext, TravelMode, MessageRole,
    MeetingInfo, ServiceType,
)
from utils.nlu import (
    extract_route,
    extract_travel_mode,
    extract_budget,
    extract_date,
    extract_cabin_class,
    extract_hotel_stars,
    extract_meeting_info,
    extract_destination_only,
    resolve_city,
    is_greeting,
)

logger = logging.getLogger(__name__)


class ConversationMemory:

    def __init__(self, session_id: str):
        self.session_id = session_id

    # ── Session ───────────────────────────────────────────────────────────────

    async def get_or_create_session(self) -> Session:
        db = get_db()
        doc = await db.sessions.find_one({"session_id": self.session_id})
        if doc:
            doc.pop("_id", None)
            return Session(**doc)
        session = Session(session_id=self.session_id)
        await db.sessions.insert_one(session.dict())
        return session

    async def save_session(self, session: Session) -> None:
        db = get_db()
        session.updated_at = datetime.utcnow()
        await db.sessions.update_one(
            {"session_id": self.session_id},
            {"$set": session.dict()},
            upsert=True,
        )

    # ── Messages ──────────────────────────────────────────────────────────────

    async def add_message(
        self,
        role: MessageRole,
        content: str,
        travel_intent: Optional[TravelMode] = None,
        metadata: Dict[str, Any] = None,
    ) -> Message:
        db = get_db()
        msg = Message(
            session_id=self.session_id,
            role=role,
            content=content,
            travel_intent=travel_intent,
            metadata=metadata or {},
        )
        await db.messages.insert_one(msg.dict())
        await db.sessions.update_one(
            {"session_id": self.session_id},
            {"$inc": {"message_count": 1}, "$set": {"updated_at": datetime.utcnow()}},
        )
        return msg

    async def get_messages(self, limit: int = 20) -> List[Message]:
        db = get_db()
        cursor = db.messages.find(
            {"session_id": self.session_id},
            sort=[("created_at", 1)],
            limit=limit,
        )
        msgs = []
        async for doc in cursor:
            doc.pop("_id", None)
            msgs.append(Message(**doc))
        return msgs

    async def get_conversation_history_for_gemini(self) -> List[Dict]:
        messages = await self.get_messages(limit=15)
        history = []
        for msg in messages:
            if msg.role == MessageRole.USER:
                history.append({"role": "user",  "parts": [{"text": msg.content}]})
            elif msg.role == MessageRole.ASSISTANT:
                history.append({"role": "model", "parts": [{"text": msg.content}]})
        return history

    # ── Context Update ────────────────────────────────────────────────────────

    async def update_context_from_message(
        self, user_message: str, user_id: str = None, company_id: str = None
    ) -> TravelContext:
        session = await self.get_or_create_session()
        ctx = session.travel_context

        # Set user/company if provided
        if user_id:    ctx.user_id    = user_id
        if company_id: ctx.company_id = company_id

        # ── Meeting extraction (Feature 1) ─────────────────────────────────────
        meeting_info = extract_meeting_info(user_message)

        if meeting_info:
            if ctx.meeting:
                meeting_info = self._merge_meeting(ctx.meeting, meeting_info)

            ctx.meeting = meeting_info

        if meeting_info:
            # Merge with existing meeting context
            if ctx.meeting:
                meeting_info = self._merge_meeting(ctx.meeting, meeting_info)
            # Fill meeting city from existing destination if not extracted
            if not meeting_info.meeting_city and ctx.destination:
                meeting_info.meeting_city = ctx.destination
            # Fill current city from home_city if not set
            if not meeting_info.current_city and ctx.home_city:
                meeting_info.current_city = ctx.home_city
            elif not meeting_info.current_city and ctx.origin:
                meeting_info.current_city = ctx.origin
            ctx.meeting = meeting_info
            # Set route from meeting info
            if meeting_info.current_city:
                ctx.origin, _ = resolve_city(meeting_info.current_city)
            if meeting_info.meeting_city:
                ctx.destination, _ = resolve_city(meeting_info.meeting_city)
        print("=" * 60)
        print("USER MESSAGE:", user_message)
        # ── Route extraction ───────────────────────────────────────────────────
        route = extract_route(user_message)
        print("EXTRACTED ROUTE:", route)
        dest_only = extract_destination_only(user_message) if not route else None
        print("DEST ONLY:", dest_only)
        print("=" * 60)
        if route:
            new_origin, new_dest = route
            route_changed = (
                (ctx.origin and ctx.origin != new_origin) or
                (ctx.destination and ctx.destination != new_dest)
            )
            if route_changed:
                logger.info(f"Context reset: {ctx.origin}→{ctx.destination} => {new_origin}→{new_dest}")
                old_meeting = ctx.meeting
                old_company = ctx.company_id
                old_user    = ctx.user_id
                old_home    = ctx.home_city
                old_allowed = ctx.allowed_services
                old_pref_cabin = ctx.preferred_cabin
                old_pref_stars = ctx.preferred_hotel_stars
                old_profile = ctx.profile_complete
                ctx = TravelContext()
                ctx.company_id          = old_company
                ctx.user_id             = old_user
                ctx.home_city           = old_home
                ctx.allowed_services    = old_allowed
                ctx.preferred_cabin     = old_pref_cabin
                ctx.preferred_hotel_stars = old_pref_stars
                ctx.profile_complete    = old_profile
            ctx.origin, _      = resolve_city(new_origin)
            ctx.destination, _ = resolve_city(new_dest)

        elif dest_only:
            city, _ = resolve_city(dest_only)
            if ctx.destination and ctx.destination != city:
                # Destination changed — clear route-specific fields
                ctx.origin = None
                ctx.cabin_class = None
                ctx.non_stop_only = False
            elif ctx.origin:
                ctx.origin = None  # clear stale origin for dest-only search
            ctx.destination = city

        # ── Profile fields (collected once, Feature 8) ─────────────────────────
        # Home city: extract from "I am in Delhi" / "I am currently in Pune"
        import re

        home_match = re.search(
            r"(?:i(?:'m| am)(?: currently)?|currently)\s+(?:in|at|from)\s+([A-Za-z][a-zA-Z\s]{1,25})",
            user_message,
            re.IGNORECASE,
        )
        # If the user simply typed a city name like "Ahmedabad"
        if (
            not home_match
            and len(user_message.strip().split()) <= 3
        ):
            city, conf = resolve_city(user_message.strip())

            if conf >= 0.80:
                ctx.home_city = city
                ctx.origin = city
                ctx.profile_complete = True

        # NEW: if the whole message is just a city name
        # If the message is just a city name (Ahmedabad, Delhi, Mumbai)
        # don't try to resolve greetings like "Hi"
        # if (
        #     not home_match
        #     and not is_greeting(user_message)
        #     and len(user_message.strip().split()) <= 3
        # ):
        #     city, conf = resolve_city(user_message.strip())

        #     if conf >= 0.95:
        #         home_match = True
        #         home_city = city

        if home_match:
            home_city, conf = resolve_city(home_match.group(1).strip())

            if conf >= 0.80:
                ctx.home_city = home_city
                ctx.origin = home_city
                ctx.profile_complete = True

        # ── Additive filters ──────────────────────────────────────────────────
        mode = extract_travel_mode(user_message)
        # Don't overwrite mode while gathering
        if not (
            ctx.meeting
            and ctx.meeting.gathering_state
            and not ctx.meeting.gathering_complete
        ):
            mode = extract_travel_mode(user_message)
        else:
            mode = None
        if mode:
            ctx.mode          = TravelMode(mode)
            ctx.active_filter = TravelMode(mode)

        budget = extract_budget(user_message)
        if budget:
            ctx.min_budget, ctx.max_budget = budget

        date = extract_date(user_message)
        if date:
            ctx.travel_date = date

        cabin = extract_cabin_class(user_message)
        if cabin:
            from models.travel import CabinClass
            ctx.cabin_class = CabinClass(cabin)
            ctx.preferred_cabin = CabinClass(cabin)

        stars = extract_hotel_stars(user_message)
        if stars:
            ctx.hotel_stars = stars
            ctx.preferred_hotel_stars = stars
            if not ctx.mode:
                ctx.mode = TravelMode.HOTEL

        if re.search(r"\bnon.?stop\b|\bdirect\b", user_message, re.IGNORECASE):
            ctx.non_stop_only = True

        # Passenger count
        pax = re.search(r"(\d+)\s+(?:passengers?|people|persons?|travell?ers?)", user_message, re.IGNORECASE)
        if pax:
            ctx.passengers = int(pax.group(1))

        if ctx.home_city :
            ctx.profile_complete = True
        if ctx.home_city and not ctx.origin:
            ctx.origin = ctx.home_city        
            
        session.travel_context = ctx
        await self.save_session(session)
        return ctx

    async def get_context(self) -> TravelContext:
        session = await self.get_or_create_session()
        return session.travel_context

    async def store_search_results(self, results_dict: Dict[str, Any]) -> None:
        session = await self.get_or_create_session()
        session.travel_context.last_search_results = results_dict
        await self.save_session(session)

    async def store_journey_plan(self, journey) -> None:
        session = await self.get_or_create_session()
        session.travel_context.journey_plan = journey
        await self.save_session(session)

    async def clear_context(self) -> None:
        session = await self.get_or_create_session()
        # Keep profile/company data across a context clear
        old = session.travel_context
        session.travel_context = TravelContext(
            company_id=old.company_id,
            user_id=old.user_id,
            home_city=old.home_city,
            allowed_services=old.allowed_services,
            preferred_cabin=old.preferred_cabin,
            preferred_hotel_stars=old.preferred_hotel_stars,
            profile_complete=old.profile_complete,
        )
        await self.save_session(session)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _merge_meeting(self, existing: MeetingInfo, new: MeetingInfo) -> MeetingInfo:
        """Merge new meeting details into existing, only overwriting non-None values."""
        data = existing.dict()
        for k, v in new.dict().items():
            if v is not None:
                data[k] = v
        return MeetingInfo(**data)

    def needs_profile_info(self, ctx: TravelContext) -> Optional[str]:
        """
        Returns a question to ask the user if critical profile info is missing.
        Feature 9: collect all info upfront so bot doesn't ask repeatedly.
        Returns None if profile is complete enough to proceed.
        """
        print("=" * 50)
        print("PROFILE COMPLETE :", ctx.profile_complete)
        print("HOME CITY        :", ctx.home_city)
        print("ORIGIN           :", ctx.origin)
        print("=" * 50)
        if ctx.profile_complete:
            return None
        if not ctx.home_city and not ctx.origin:
            return (
                "Before I help plan your journey, could you tell me: "
                "**which city are you currently in?** "
                "(I'll remember this for the entire conversation.)"
            )
        return None
