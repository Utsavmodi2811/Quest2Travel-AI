"""
Conversation memory manager.
Maintains travel context across multiple turns — the core of the
follow-up query system (Delhi→Mumbai, only flights, business class, under 6000).
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from database.connection import get_db
from models.travel import Session, Message, TravelContext, TravelMode, MessageRole
from utils.nlu import (
    extract_route, extract_travel_mode, extract_budget,
    extract_date, extract_cabin_class, extract_hotel_stars,
    resolve_city,
)

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Manages per-session travel context and message history.
    Core logic: parse each user message and merge NEW information
    into existing context — only reset when a new route is detected.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id

    # ── Session ──────────────────────────────────────────────────────────────

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

    # ── Messages ─────────────────────────────────────────────────────────────

    async def add_message(self, role: MessageRole, content: str,
                          travel_intent: Optional[TravelMode] = None,
                          metadata: Dict[str, Any] = None) -> Message:
        db = get_db()
        message = Message(
            session_id=self.session_id,
            role=role,
            content=content,
            travel_intent=travel_intent,
            metadata=metadata or {},
        )
        await db.messages.insert_one(message.dict())

        await db.sessions.update_one(
            {"session_id": self.session_id},
            {"$inc": {"message_count": 1}, "$set": {"updated_at": datetime.utcnow()}},
        )
        return message

    async def get_messages(self, limit: int = 20) -> List[Message]:
        db = get_db()
        cursor = db.messages.find(
            {"session_id": self.session_id},
            sort=[("created_at", 1)],
            limit=limit,
        )
        messages = []
        async for doc in cursor:
            doc.pop("_id", None)
            messages.append(Message(**doc))
        return messages

    async def get_conversation_history_for_gemini(self) -> List[Dict]:
        """Format message history for Gemini API."""
        messages = await self.get_messages(limit=15)
        history = []
        for msg in messages:
            if msg.role == MessageRole.USER:
                history.append({"role": "user", "parts": [{"text": msg.content}]})
            elif msg.role == MessageRole.ASSISTANT:
                history.append({"role": "model", "parts": [{"text": msg.content}]})
        return history

    # ── Context Management ────────────────────────────────────────────────────

    async def get_context(self) -> TravelContext:
        session = await self.get_or_create_session()
        return session.travel_context

    async def update_context_from_message(self, user_message: str) -> TravelContext:
        """
        Core memory logic: parse the new message and merge it into context.

        Reset rules:
          1. A NEW route (origin+destination) that differs from the existing
             one → full context reset (Mumbai→Delhi becomes Ahmedabad→Goa).
          2. A destination-ONLY query ("Hotels in Delhi") while an origin is
             still set from a previous route → clear origin AND any stale
             route-specific fields (cabin class, non-stop, train class),
             since those don't apply to a plain destination search.
          3. Everything else (budget, date, stars, mode refinement) is
             additive on top of the existing context.
        """
        session = await self.get_or_create_session()
        ctx = session.travel_context

        route = extract_route(user_message)
        destination_only = self._extract_destination_only(user_message)
        # Special handling for destination-only car/hotel searches
        if destination_only is None:
            mode_hint = extract_travel_mode(user_message)

            if mode_hint in ["car", "hotel"]:
                import re

                match = re.search(
                    r"(?:in|at|near)\s+([a-zA-Z\s]+?)(?:\s+(?:under|for|on|with|tomorrow|today|next)|\s*$|[,.!?])",
                    user_message,
                    re.IGNORECASE,
                )

                if match:
                    destination_only = match.group(1).strip()
        if route:
            new_origin, new_dest = route
            origin_resolved, _ = resolve_city(new_origin)
            dest_resolved, _ = resolve_city(new_dest)

            route_changed = (
                (ctx.origin and ctx.origin != origin_resolved) or
                (ctx.destination and ctx.destination != dest_resolved)
            )
            if route_changed:
                logger.info(
                    f"Context reset: {ctx.origin}→{ctx.destination} "
                    f"=> {origin_resolved}→{dest_resolved}"
                )
                ctx = TravelContext()

            ctx.origin = origin_resolved
            ctx.destination = dest_resolved

        elif destination_only:
            dest_resolved, _ = resolve_city(destination_only)
            if ctx.destination and ctx.destination != dest_resolved:
                logger.info(
                    f"Context reset (destination-only): "
                    f"{ctx.origin}→{ctx.destination} => {dest_resolved}"
                )
                ctx = TravelContext()
            elif ctx.origin:
                # Same destination, but an origin is leaking in from an
                # earlier route search — clear it, this is now a
                # destination-only query (e.g. hotel/car search).
                logger.info(f"Clearing stale origin '{ctx.origin}' for destination-only query")
                ctx.origin = None
                ctx.cabin_class = None
                ctx.non_stop_only = False
                ctx.train_class = None

            ctx.destination = dest_resolved

        # Travel mode (additive — can refine)
        mode = extract_travel_mode(user_message)

        if mode:
            new_mode = TravelMode(mode)

            if ctx.mode != new_mode:
                ctx.last_search_results = None
                ctx.max_budget = None
                ctx.min_budget = None
                ctx.hotel_stars = None
                ctx.cabin_class = None  
            ctx.mode = new_mode
            ctx.active_filter = new_mode

        # Budget
        budget = extract_budget(user_message)
        if budget:
            ctx.min_budget, ctx.max_budget = budget

        # Date (never default to "today" here — extract_date returns None
        # if no date phrase was found, and we simply don't touch ctx.travel_date
        # in that case, preserving whatever was set in a previous turn)
        date = extract_date(user_message)
        if date:
            ctx.travel_date = date

        # Cabin class
        cabin = extract_cabin_class(user_message)
        if cabin:
            from models.travel import CabinClass
            ctx.cabin_class = CabinClass(cabin)

        # Hotel stars
        stars = extract_hotel_stars(user_message)
        if stars:
            ctx.hotel_stars = stars
            if ctx.mode is None:
                ctx.mode = TravelMode.HOTEL

        # Non-stop filter
        if "non.stop" in user_message.lower() or "nonstop" in user_message.lower() or "direct" in user_message.lower():
            ctx.non_stop_only = True

        # Save updated context
        session.travel_context = ctx
        await self.save_session(session)


        return ctx

    async def store_search_results(self, results_dict: Dict[str, Any]) -> None:
        session = await self.get_or_create_session()
        session.travel_context.last_search_results = results_dict
        await self.save_session(session)

    async def clear_context(self) -> None:
        session = await self.get_or_create_session()
        session.travel_context = TravelContext()
        await self.save_session(session)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _extract_destination_only(self, text: str) -> Optional[str]:
        """
        Detect destination-only queries.

        Examples:
        - Hotels in Mumbai
        - 5-star hotels in Goa
        - Car rental in Delhi
        - Self drive car in Pune
        - Cab in Ahmedabad tomorrow
        """

        import re as _re

        patterns = [

            # Hotels
            r"(?:hotels?|stay|accommodation)\s+(?:in|at|near)\s+([a-zA-Z\s]+?)"
            r"(?:\s+(?:under|for|on|with|tomorrow|today|next)|\s*$|[,.!?])",

            # Cars
            r"(?:cars?|car rental|rent a car|rental car|self drive|cab|taxi)"
            r"\s+(?:in|at|near)\s+([a-zA-Z\s]+?)"
            r"(?:\s+(?:under|for|on|with|tomorrow|today|next)|\s*$|[,.!?])",
        ]

        for pattern in patterns:
            match = _re.search(pattern, text, _re.IGNORECASE)

            if match:
                city = match.group(1).strip()

                if 2 <= len(city) <= 40:
                    return city.title()

        return None
