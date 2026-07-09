import re
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from utils.nlu import(extract_hotel_stars,resolve_city,)
from models.travel import MeetingInfo, TravelContext, TravelMode
from utils.nlu import extract_time
logger = logging.getLogger(__name__)


# ── Gathering State ────────────────────────────────────────────────────────────

@dataclass
class GatheringState:
    """
    Tracks every piece of trip information we need.
    Stored inside TravelContext.gathering_state (as a dict).
    """
    # Required for any trip
    origin: Optional[str]       = None   # where traveller starts from
    destination: Optional[str]  = None   # meeting city
    travel_date: Optional[str]  = None   # outbound date (YYYY-MM-DD)
    meeting_time: Optional[str] = None   # when meeting starts (HH:MM)

    # Outbound travel
    outbound_mode: Optional[str] = None  # "flight"|"train"|"bus"|"car"|"any"
    outbound_class: Optional[str]= None  # "economy"|"business"|"sleeper"|"3ac" etc.

    # Trip type
    trip_type: Optional[str]    = None   # "one_way"|"round_trip"

    # Return (only if round_trip)
    return_date: Optional[str]  = None
    return_time: Optional[str]  = None   # when they want to leave venue
    return_mode: Optional[str]  = None   # may differ from outbound

    # Accommodation
    hotel_needed: Optional[bool]= None   # True/False/None (undecided)
    hotel_checkin: Optional[str]= None   # YYYY-MM-DD
    hotel_checkout: Optional[str]= None  # YYYY-MM-DD
    hotel_stars: Optional[int]  = None   # 3/4/5

    # Extra preferences (all optional)
    budget_max: Optional[float] = None
    passengers: int             = 1
    special_requirements: str   = ""

    # Internal flags
    asked_outbound_mode: bool   = False
    asked_trip_type: bool       = False
    asked_return_date: bool     = False
    asked_return_mode: bool     = False
    asked_hotel: bool           = False
    asked_hotel_dates: bool     = False
    asked_preferences: bool     = False

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GatheringState":
        valid = {k for k in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in valid})

    def is_complete(self) -> bool:
        if not all([
            self.origin,
            self.destination,
            self.travel_date,
            self.meeting_time,
            self.outbound_mode,
            self.trip_type
        ]):
            return False

        if self.trip_type == "round_trip":
            if not self.return_date:
                return False

            if not self.return_time:
                return False

            if not self.return_mode:
                return False

        # REPLACE THIS PART
        if self.hotel_needed is None:
            return False

        if self.hotel_needed:
            if not self.hotel_checkin:
                return False
            if not self.hotel_checkout:
                return False

        return True


# ── Question templates ─────────────────────────────────────────────────────────

OUTBOUND_MODE_QUESTION = (
    "How would you prefer to travel from **{origin}** to **{destination}**?\n"
    "Options: ✈️ Flight  🚂 Train  🚌 Bus  🚗 Self-drive  (or type your preference)"
)

TRIP_TYPE_QUESTION = (
    "Is this a **one-way** trip or do you need a **return** journey back to {origin}?"
)

RETURN_DATE_QUESTION = (
    "What date and approximate time would you like to return to **{origin}**?\n"
    "*(e.g. 'same day after 6 PM', 'next day morning', '25th June evening')*"
)

RETURN_MODE_QUESTION = (
    "How would you like to travel back from **{destination}** to **{origin}**?\n"
    "Options: ✈️ Flight  🚂 Train  🚌 Bus  (same as outbound / your choice)"
)

HOTEL_QUESTION = (
    "Will you need **accommodation** in {destination}?"
)

HOTEL_DATES_QUESTION = (
    "For how many nights? Or tell me your check-in and check-out dates."
)

PREFERENCES_QUESTION = (
    "Any other preferences for this trip?\n"
    "*(e.g. budget limit, travel class, hotel rating, number of travellers)*\n"
    "Or say **'plan my trip'** to proceed with defaults."
)


class TripGatherer:
    """
    Stateful information gatherer for business trip planning.
    Called each turn; updates GatheringState and returns the next question,
    or None when gathering is complete.
    """

    # ── Main entry ────────────────────────────────────────────────────────────

    def update_from_message(
        self,
        state: GatheringState,
        message: str,
        context: TravelContext,
    ) -> GatheringState:
        """
        Parse the user's latest message and fill in any newly provided info.
        Also copies over anything already known from TravelContext.
        """
        print("=" * 60)
        print("MESSAGE:", message)
        print("CONTEXT DESTINATION:", context.destination)
        print("MEETING CITY:", context.meeting.meeting_city if context.meeting else None)
        print("TRAVEL DATE:", context.travel_date)
        print("=" * 60)
        msg = message.strip().lower()
        print("CONTEXT ORIGIN      :", context.origin)
        print("CONTEXT DESTINATION :", context.destination)
        print("STATE ORIGIN        :", state.origin)
        print("STATE DESTINATION   :", state.destination)
        city, conf = resolve_city(message)

        if conf >= 0.9:

            # User explicitly tells us where they are
            if any(
                x in msg
                for x in [
                    "i'm in",
                    "i am in",
                    "currently in",
                    "travelling from",
                    "traveling from",
                    "from "
                ]
            ):
                state.origin = city

            # Only if the bot is currently asking for origin
            elif (
                state.origin is None
                and state.destination is not None
                and len(message.strip().split()) <= 2
            ):
                state.origin = city

        # Sync from context (NLU already parsed routes, dates, etc.)
        if (
            context.origin
            and not state.origin
            and context.origin != context.destination
        ):
            state.origin = context.origin



        # Meeting parser already found destination
        if (
            context.meeting
            and context.meeting.meeting_city
            and not state.destination
        ):
            print("SETTING DESTINATION FROM MEETING =", context.meeting.meeting_city)
            state.destination = context.meeting.meeting_city

        if context.destination:
            state.destination = context.destination
        # If we already know the destination from the meeting,
        # don't treat it as the origin.
        if (
            state.origin == state.destination
            and context.meeting
            and context.meeting.current_city is None
        ):
            state.origin = None
        # Sync from context (NLU already parsed routes, dates, etc.)
        # If meeting parser already found the meeting city,
        # use it as the destination.

        print("=" * 80)
        print("AFTER SYNC")
        print("state.origin      =", state.origin)
        print("state.destination =", state.destination)
        print("context.origin    =", context.origin)
        print("context.destination =", context.destination)
        print("=" * 80)

        if context.travel_date:
            state.travel_date = context.travel_date

        if context.meeting and context.meeting.meeting_time:
            state.meeting_time = context.meeting.meeting_time
        if context.travel_date and not state.travel_date:
            state.travel_date = context.travel_date
        if context.meeting and context.meeting.meeting_time and not state.meeting_time:
            state.meeting_time = context.meeting.meeting_time
        # ----------------------------
        # Parse meeting time from reply
        # ----------------------------
        print("="*60)
        print("RAW MESSAGE:", message)

        meeting_time = extract_time(message)

        print("PARSED TIME:", meeting_time)
        print("="*60)

        if meeting_time:
            state.meeting_time = meeting_time

            if context.meeting:
                context.meeting.meeting_time = meeting_time

        print("STATE TIME:", state.meeting_time)
        # Sync destination from meeting
        if (
            context.meeting
            and context.meeting.meeting_city
            and not state.destination
        ):
            state.destination = context.meeting.meeting_city
        # if context.home_city and not state.origin:
        #     state.origin = context.home_city
        if context.max_budget and not state.budget_max:
            state.budget_max = context.max_budget
        if context.passengers and context.passengers > 1:
            state.passengers = context.passengers

        # ── Outbound mode ──────────────────────────────────────────────────────
        if not state.outbound_mode:
            mode = self._parse_travel_mode(msg)

            print("=" * 50)
            print("MESSAGE:", msg)
            print("PARSED MODE:", mode)

            if mode:
                state.outbound_mode = mode
                print("OUTBOUND MODE SAVED:", state.outbound_mode)

                cls = self._parse_class(msg, mode)
                if cls:
                    state.outbound_class = cls

        # ── Trip type ──────────────────────────────────────────────────────────
        if not state.trip_type:

            print("MESSAGE RECEIVED:", msg)

            if any(
                w in msg
                for w in [
                    "one way",
                    "one-way",
                    "oneway",
                    "no return",
                    "won't return",
                    "not returning",
                    "single",
                ]
            ):
                print("Detected ONE WAY")
                state.trip_type = "one_way"

            elif any(
                w in msg
                for w in [
                    "round trip",
                    "round-trip",
                    "both ways",
                    "return trip",
                    "two way",
                    "two-way",
                ]
            ):
                print("Detected ROUND TRIP")
                state.trip_type = "round_trip"

            print("TRIP TYPE =", state.trip_type)

        # ── Return details ─────────────────────────────────────────────────────
        if state.trip_type == "round_trip":
            # Return date
            if not state.return_date:
                rd = self._parse_return_date(msg, state.travel_date)
                if rd:
                    state.return_date = rd
                    # "same day" → hotel probably not needed
                    if (
                        ("same day" in msg or "same-day" in msg)
                        and state.travel_date
                    ):
                        state.return_date = state.travel_date
                        state.hotel_needed = False

            # Return time
            if not state.return_time:
                rt = self._parse_return_time(msg)
                if rt:
                    state.return_time = rt

            # Return mode
            # Return mode
            if state.trip_type == "round_trip" and not state.return_mode:

                # Same as outbound
                if (
                    any(
                        w in msg
                        for w in [
                            "same mode",
                            "same as outbound",
                            "same as going",
                            "same flight",
                            "same train",
                            "same bus",
                        ]
                    )
                    and state.outbound_mode
                ):
                    state.return_mode = state.outbound_mode

                else:
                    rm = self._parse_travel_mode(msg)

                    if rm:
                        state.return_mode = rm
        print("=" * 50)
        print("RETURN STATE")
        print("return_date :", state.return_date)
        print("return_time :", state.return_time)
        print("return_mode :", state.return_mode)
        print("=" * 50)
        # ── Hotel ──────────────────────────────────────────────────────────────

        if state.hotel_needed is None and state.asked_hotel:

            if any(x in msg for x in [
                "yes",
                "yeah",
                "yep",
                "need",
                "book"
            ]):
                state.hotel_needed = True

            elif any(x in msg for x in [
                "no",
                "nope",
                "nah",
                "don't",
                "dont",
                "not",
                "not needed",
                "no hotel"
            ]):
                # Only treat as hotel confirmation if we actually asked
                if state.asked_hotel:
                    state.hotel_needed = False
            elif any(w in msg for w in ["no hotel", "no accommodation", "not staying",
                                          "won't stay", "no stay", "no thanks",
                                          "not needed", "nope", "no need"]):
                if state.asked_hotel:
                    state.hotel_needed = False

        # ── Hotel dates ────────────────────────────────────────────────────────
        if state.hotel_needed and not state.hotel_checkout:
            # "2 nights", "two nights"
            nights_m = re.search(r"(\d+|one|two|three|four|five)\s+night", msg)
            if nights_m:
                n_map = {"one":1,"two":2,"three":3,"four":4,"five":5}
                raw = nights_m.group(1)
                nights = int(raw) if raw.isdigit() else n_map.get(raw, 1)
                if state.travel_date:
                    checkin  = state.travel_date
                    checkout = (datetime.strptime(checkin, "%Y-%m-%d") + timedelta(days=nights)).strftime("%Y-%m-%d")
                    state.hotel_checkin  = checkin
                    state.hotel_checkout = checkout

            # Explicit checkout from return date
            if not state.hotel_checkout and state.return_date:
                state.hotel_checkin  = state.travel_date or state.return_date
                state.hotel_checkout = state.return_date

        # ── Hotel stars ────────────────────────────────────────────────────────
        if not state.hotel_stars:
             
            stars = extract_hotel_stars(message)
            if stars:
                state.hotel_stars = stars

        # ── Budget ─────────────────────────────────────────────────────────────
        if not state.budget_max:
            from utils.nlu import extract_budget
            budget = extract_budget(message)
            if budget and budget[1]:
                state.budget_max = budget[1]
        # If the user answered the preferences question,
        # don't ask it again.
        if state.asked_preferences:
            if (
                state.budget_max
                or state.outbound_class
                or state.hotel_stars
                or any(
                    w in msg
                    for w in [
                        "plan my trip",
                        "proceed",
                        "go ahead",
                        "continue",
                        "default",
                        "no preference",
                        "nothing else",
                    ]
                )
            ):
                state.asked_preferences = True

        # ── "Plan my trip" / skip preferences ──────────────────────────────────
        if any(w in msg for w in ["plan my trip", "proceed", "go ahead", "plan it",
                                    "that's all", "thats all", "nothing else",
                                    "no other", "start planning", "book it"]):
            state.asked_preferences = True
        print("=" * 60)
        print("FINAL STATE")
        print("Origin      :", state.origin)
        print("Destination :", state.destination)
        print("Meeting Time:", state.meeting_time)
        print("=" * 60)
        return state
    def should_ask_hotel(self, state: GatheringState) -> bool:
        """
        Decide whether the hotel question should be asked.
        """

        # Already decided
        if state.hotel_needed is not None:
            return False

        # One-way trips usually need accommodation
        if state.trip_type != "round_trip":
            return True

        # Missing dates -> ask user later
        if not state.travel_date or not state.return_date:
            return False

        # Same-day return
        if state.travel_date == state.return_date:
            state.hotel_needed = False
            return False

        return True
    def next_question(self, state: GatheringState) -> Optional[str]:
        """
        Returns the next question to ask the user, or None if gathering is done.
        Questions are asked in priority order — only one at a time.
        """
        # Origin (should already be set from NLU/profile, but ask if missing)
        # Destination
        if not state.destination:
            return "What is your destination city for this business trip?"

        # Date
        if not state.travel_date:
            return "What date is your outbound journey?"

        # Meeting time
        if not state.meeting_time:
            return (
                "What time is your meeting? "
                "(e.g. 10 AM, 1 PM)"
            )

        # Origin
        if not state.origin:
            return "Which city are you currently in / travelling from?"
        # Outbound travel mode
        if not state.outbound_mode:
            state.asked_outbound_mode = True
            return OUTBOUND_MODE_QUESTION.format(
                origin=state.origin, destination=state.destination
            )

        # Trip type
        if not state.trip_type:
            state.asked_trip_type = True
            return TRIP_TYPE_QUESTION.format(origin=state.origin)

        # Return details (only for round trips)
        if state.trip_type == "round_trip":

            if not state.return_date:
                state.asked_return_date = True
                return RETURN_DATE_QUESTION.format(origin=state.origin)

            # NEW
            if not state.return_time:
                return (
                    f"What time would you like to return from "
                    f"{state.destination} to {state.origin}?"
                )

            if not state.return_mode:
                state.asked_return_mode = True
                return RETURN_MODE_QUESTION.format(
                    origin=state.origin,
                    destination=state.destination,
                )

        # Hotel
        if self.should_ask_hotel(state):
            state.asked_hotel = True
            return HOTEL_QUESTION.format(
                destination=state.destination
            )

        if state.hotel_needed and not state.hotel_checkout:
            state.asked_hotel_dates = True
            return HOTEL_DATES_QUESTION

        # Optional preferences (ask once, not blocking)
        # Optional preferences (ask once only if something is still missing)
        needs_preferences = (
            not state.outbound_class
            or (state.hotel_needed and not state.hotel_stars)
            or not state.budget_max
        )

        if not state.asked_preferences and needs_preferences:
            state.asked_preferences = True

            extras = []
            if not state.outbound_class:
                extras.append("travel class")
            if state.hotel_needed and not state.hotel_stars:
                extras.append("hotel rating")
            if not state.budget_max:
                extras.append("budget")

            return (
                f"Almost ready! Any preferences for **{', '.join(extras)}**? "
                f"Or say **'plan my trip'** to continue with defaults."
            )

        return None  # All information gathered

    def apply_to_context(self, state: GatheringState, context: TravelContext) -> TravelContext:
        """
        Write gathered state back into TravelContext so journey_planner can use it.
        """
        from models.travel import CabinClass, TrainClass

        if state.origin:       context.origin      = state.origin
        if state.destination:  context.destination = state.destination
        if state.travel_date:  context.travel_date = state.travel_date
        if state.return_date:  context.return_date = state.return_date
        if state.budget_max:   context.max_budget  = state.budget_max
        if state.hotel_stars:  context.hotel_stars = state.hotel_stars
        if state.passengers:   context.passengers  = state.passengers

        # Map outbound mode to TravelMode
        mode_map = {
            "flight": TravelMode.FLIGHT,
            "train":  TravelMode.TRAIN,
            "bus":    TravelMode.BUS,
            "car":    TravelMode.CAR,
        }
        if state.outbound_mode and state.outbound_mode in mode_map:
            context.mode = mode_map[state.outbound_mode]

        # Map class preference
        if state.outbound_class:
            cabin_map = {"economy": "economy", "business": "business",
                          "first": "first", "premium": "premium_economy",
                          "premium economy": "premium_economy"}
            train_map = {"sleeper": "sleeper", "3ac": "3ac", "2ac": "2ac",
                          "1ac": "1ac", "chair car": "cc"}
            cls_lower = state.outbound_class.lower()
            if cls_lower in cabin_map:
                try:
                    context.cabin_class = CabinClass(cabin_map[cls_lower])
                except Exception:
                    pass
            elif cls_lower in train_map:
                try:
                    context.train_class = TrainClass(train_map[cls_lower])
                except Exception:
                    pass

        # Update meeting info
        if context.meeting:
            if state.return_date:
                context.meeting.return_required = True
                context.meeting.return_time     = state.return_time
            if state.hotel_needed is not None:
                context.meeting.hotel_required  = state.hotel_needed
            if state.meeting_time:
                context.meeting.meeting_time    = state.meeting_time

        return context

    def summarize_gathered(self, state: GatheringState) -> str:
        """
        Human-readable summary of what has been gathered.
        Used by Gemini/rule-based agent to confirm before building plan.
        """
        lines = ["📋 **Trip Summary — here's what I have:**\n"]

        lines.append(f"🗺️  **Route:** {state.origin} → {state.destination}")
        if state.travel_date:
            lines.append(f"📅  **Outbound:** {state.travel_date}" +
                          (f" at {state.meeting_time}" if state.meeting_time else ""))
        if state.outbound_mode:
            emoji = {"flight":"✈️","train":"🚂","bus":"🚌","car":"🚗"}.get(state.outbound_mode,"🚀")
            cls_str = f" ({state.outbound_class})" if state.outbound_class else ""
            lines.append(f"{emoji}  **Outbound mode:** {state.outbound_mode.title()}{cls_str}")
        if state.outbound_class:
            lines.append(f"💺  **Travel class:** {state.outbound_class.title()}")

        if state.trip_type == "round_trip":
            lines.append(f"🔄  **Trip type:** Round trip")
            if state.return_date:
                rt = f" after {state.return_time}" if state.return_time else ""
                lines.append(f"📅  **Return:** {state.return_date}{rt}")
            if state.return_mode:
                emoji2 = {"flight":"✈️","train":"🚂","bus":"🚌"}.get(state.return_mode,"🚀")
                lines.append(f"{emoji2}  **Return mode:** {state.return_mode.title()}")
        else:
            lines.append(f"➡️  **Trip type:** One-way")

        if state.hotel_needed:
            nights_str = ""
            if state.hotel_checkin and state.hotel_checkout:
                from datetime import datetime as dt
                try:
                    n = (dt.strptime(state.hotel_checkout, "%Y-%m-%d") -
                         dt.strptime(state.hotel_checkin, "%Y-%m-%d")).days
                    nights_str = f" ({n} night{'s' if n>1 else ''})"
                except Exception:
                    pass
            stars_str = f" — {state.hotel_stars}★ preferred" if state.hotel_stars else ""
            lines.append(f"🏨  **Hotel:** Yes{nights_str}{stars_str}")
        elif state.hotel_needed is False:
            lines.append("🏨  **Hotel:** Not required")

        if state.budget_max:
            lines.append(f"💰  **Budget:** up to ₹{state.budget_max:,.0f}")
        if state.hotel_stars:
            lines.append(f"🏨  **Preferred hotel:** {state.hotel_stars}★")
        if state.passengers > 1:
            lines.append(f"👥  **Travellers:** {state.passengers}")

        lines.append("\n*Building your journey plan now…*")
        return "\n".join(lines)

    # ── Parsers ───────────────────────────────────────────────────────────────

    def _parse_travel_mode(self, msg: str):

        msg = msg.lower().strip()

        flight = [
            "flight",
            "fly",
            "plane",
            "air",
            "airways"
        ]

        train = [
            "train",
            "rail",
            "railway",
            "irctc",
            "rajdhani",
            "shatabdi",
            "vande bharat"
        ]

        bus = [
            "bus",
            "coach",
            "volvo",
            "redbus"
        ]

        car = [
            "car",
            "cab",
            "drive",
            "taxi",
            "uber",
            "ola"
        ]

        if any(x in msg for x in flight):
            return "flight"

        if any(x in msg for x in train):
            return "train"

        if any(x in msg for x in bus):
            return "bus"

        if any(x in msg for x in car):
            return "car"

        if any(x in msg for x in [
            "any",
            "cheapest",
            "fastest",
            "best",
            "no preference"
        ]):
            return "any"

        return None

    def _parse_class(self, msg: str, mode: str) -> Optional[str]:
        if mode == "flight":
            if "business" in msg:    return "business"
            if "first class" in msg: return "first"
            if "premium" in msg:     return "premium economy"
            if "economy" in msg:     return "economy"
        elif mode == "train":
            if "1ac" in msg or "first ac" in msg: return "1ac"
            if "2ac" in msg or "second ac" in msg: return "2ac"
            if "3ac" in msg or "third ac" in msg:  return "3ac"
            if "sleeper" in msg:                   return "sleeper"
            if "chair" in msg:                     return "chair car"
        return None

    def _parse_return_date(self, msg: str, travel_date: Optional[str]) -> Optional[str]:
        from utils.nlu import extract_date
        # "same day" → same as travel date
        if "same day" in msg or "same-day" in msg:
            return travel_date
        # "next day" → travel_date + 1
        if "next day" in msg or "following day" in msg:
            if travel_date:
                return (datetime.strptime(travel_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        # Try general date extraction
        return extract_date(msg)

    def _parse_return_time(self, msg: str) -> Optional[str]:
        from utils.nlu import extract_time
        # Look for "after 6 PM", "around 7", "evening", "morning" etc.
        t = extract_time(msg)
        if t:
            return t
        if "evening"  in msg: return "18:00"
        if "morning"  in msg: return "09:00"
        if "afternoon"in msg: return "14:00"
        if "night"    in msg: return "21:00"
        return None


trip_gatherer = TripGatherer()