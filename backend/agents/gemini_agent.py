"""
Gemini AI Agent.
Knows about: meetings, journey plans, company restrictions, time constraints.
NEVER enumerates result cards — only summarizes counts + cheapest price.
"""

import logging
from typing import Optional, List, Dict, Any

from config.settings import settings
from models.travel import TravelContext, TravelMode, JourneyPlan, MeetingInfo, IntentType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Quest2Travel, an intelligent corporate travel assistant for India.
 
You help users plan complete business journeys — flights, trains, buses, hotels, cab transfers, and return trips.
 
INFORMATION GATHERING RULES:
When a user mentions a meeting or business trip, you gather ALL necessary information
by asking ONE question at a time. Never ask multiple questions at once.
After each answer, ask the next most important missing question.
Questions to ask (in order of priority, skip if already known):
  1. Outbound travel mode (flight / train / bus / car / any)
  2. One-way or round trip?
  3. If round trip: return date and preferred time
  4. If round trip: return travel mode (may differ from outbound)
  5. Hotel needed? (yes/no)
  6. If hotel: how many nights / check-out date
  7. Any other preferences (class, budget, hotel rating) — optional
 
RESULT SUMMARY RULES (when cards are shown below your message):
- NEVER list individual flight numbers, hotel names, or train schedules — the UI cards do that.
- Summarize in ONE sentence per category:
    "Found 8 flights. Cheapest ₹4,299. See cards below."
    "6 hotels near your venue. Closest 0.8 km, from ₹4,200/night."
- For journey plans, present the full timeline clearly step by step.
- If zero results after filtering, say so and suggest loosening the filter.
- Always acknowledge company subscription limits if a service is restricted.
 
OTHER RULES:
- Use ₹ for Indian prices. Be concise and professional.
- Remember all trip details within a conversation — never ask for them again.
- When user says "plan my trip" or all info is gathered, confirm with a summary then build the plan.
"""


class GeminiAgent:
    def __init__(self):
        self._model = None
        self._configured = False
        if settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self._model = genai.GenerativeModel(
                    model_name=settings.GEMINI_MODEL,
                    system_instruction=SYSTEM_PROMPT,
                )
                self._configured = True
                logger.info("Gemini initialized")
            except Exception as e:
                logger.error(f"Gemini init failed: {e}")
        else:
            logger.warning("GEMINI_API_KEY not set — using rule-based responses")

    async def chat(
        self,
        user_message: str,
        history: List[Dict],
        travel_context: Optional[TravelContext] = None,
        travel_results: Optional[Dict] = None,
        journey_plan: Optional[JourneyPlan] = None,
        intent_type: Optional[IntentType] = None,
        permission_denied: bool = False,
        denied_service: Optional[str] = None,
    ) -> str:
        if not self._configured or not self._model:
            return self._rule_based(
                user_message, travel_context, travel_results,
                journey_plan, permission_denied, denied_service,
            )
        try:
            parts = [user_message]
            if travel_context:
                parts.append(f"\n[Context: {self._fmt_ctx(travel_context)}]")
            if permission_denied and denied_service:
                parts.append(f"\n[PERMISSION DENIED: company does not allow {denied_service}]")
            if journey_plan:
                parts.append(f"\n[Journey plan:\n{journey_plan.timeline_summary}\n"
                             f"Total estimated cost: ₹{journey_plan.total_estimated_cost:,.0f}\n"
                             f"Legs: {len(journey_plan.legs)}\n"
                             f"Present the timeline clearly to the user.]")
            if travel_results is not None:
                parts.append(
                    "\nTravel results are already displayed as cards."
                    "\nDo NOT summarize search results."
                    "\nDo NOT mention number of flights/trains/hotels."
                    "\nOnly answer the user's question or give useful travel advice."
                )

            chat = self._model.start_chat(history=history[:-1] if history else [])
            response = await chat.send_message_async("\n".join(parts))
            return response.text
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return self._rule_based(
                user_message, travel_context, travel_results,
                journey_plan, permission_denied, denied_service,
            )

    async def generate_suggestions(
        self,
        context: TravelContext,
        intent_type: Optional[IntentType] = None,
    ) -> List[str]:
        if intent_type == IntentType.MEETING_PLAN:
            return [
                "Show hotel options near venue",
                "Find return flights",
                "What's the cab cost from airport?",
            ]
        if context.origin and context.destination:
            sugg = []
            if context.mode != TravelMode.FLIGHT:
                sugg.append("Show flights")
            if context.mode != TravelMode.TRAIN:
                sugg.append("Show trains")
            if context.mode != TravelMode.HOTEL:
                sugg.append(f"Hotels in {context.destination}")
            if not context.max_budget:
                sugg.append("Under ₹5,000")
            return sugg[:3]
        return [
            "Delhi to Mumbai flights tomorrow",
            "Hotels in Goa under ₹5000",
            "Train from Ahmedabad to Bangalore",
        ]

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _fmt_ctx(self, ctx: TravelContext) -> str:
        parts = []
        if ctx.home_city:     parts.append(f"Home={ctx.home_city}")
        if ctx.origin:        parts.append(f"From={ctx.origin}")
        if ctx.destination:   parts.append(f"To={ctx.destination}")
        if ctx.travel_date:   parts.append(f"Date={ctx.travel_date}")
        if ctx.mode:          parts.append(f"Mode={ctx.mode.value}")
        if ctx.cabin_class:   parts.append(f"Class={ctx.cabin_class.value}")
        if ctx.hotel_stars:   parts.append(f"Stars={ctx.hotel_stars}★")
        if ctx.max_budget:    parts.append(f"MaxBudget=₹{ctx.max_budget:,.0f}")
        if ctx.company_id:    parts.append(f"Company={ctx.company_id}")
        if ctx.required_arrival_by: parts.append(f"MustArriveBy={ctx.required_arrival_by}")
        m = ctx.meeting
        if m and m.meeting_time:
            parts.append(f"Meeting={m.meeting_time} at {m.meeting_location or m.meeting_city}")
        return " | ".join(parts) if parts else "none"

    def _summarize(self, results: Dict) -> str:
        lines = []
        if results.get("is_mock"):
            lines.append("is_mock=true")
        for key, label in [("flights","flights"), ("hotels","hotels"),
                            ("trains","trains"),  ("buses","buses"), ("cars","cars")]:
            items = results.get(key, [])
            if not items:
                continue
            if key == "flights":
                prices = [f["price_inr"] for f in items if f.get("price_inr")]
                cheapest = min(prices) if prices else None
                lines.append(f"flights_count={len(items)} cheapest_inr={cheapest}")
            elif key == "hotels":
                prices = [h["price"] for h in items if h.get("price")]
                cheapest = min(prices) if prices else None
                lines.append(f"hotels_count={len(items)} cheapest_per_night_inr={cheapest}")
            elif key == "trains":
                all_p = [c["price"] for t in items for c in t.get("classes",[]) if c.get("price")]
                cheapest = min(all_p) if all_p else None
                lines.append(f"trains_count={len(items)} cheapest_class_inr={cheapest}")
            elif key == "buses":
                prices = [b["price"] for b in items if b.get("price")]
                cheapest = min(prices) if prices else None
                lines.append(f"buses_count={len(items)} cheapest_inr={cheapest}")
            elif key == "cars":
                prices = [c["price_day"] for c in items if c.get("price_day")]
                cheapest = min(prices) if prices else None
                lines.append(f"cars_count={len(items)} cheapest_per_day_inr={cheapest}")
        if not any(results.get(k) for k in ("flights","hotels","trains","buses","cars")):
            lines.append("zero_results=true — filter too strict, tell user and suggest loosening")
        return "\n".join(lines) if lines else "no_results"

    def _rule_based(
        self,
        message: str,
        ctx: Optional[TravelContext],
        results: Optional[Dict],
        journey: Optional[JourneyPlan],
        permission_denied: bool,
        denied_service: Optional[str],
    ) -> str:
        msg = message.lower().strip()

        # Permission denied
        if permission_denied and denied_service:
            company = ctx.company_id if ctx else "your company"
            allowed = ", ".join(s.value for s in ctx.allowed_services) if ctx else "some services"
            return (
                f"Sorry, **{company}** subscription does not include "
                f"**{denied_service.capitalize()}** booking. "
                f"Available services: {allowed}. "
                f"Please contact your travel administrator to upgrade."
            )

        # Journey plan
        if journey and journey.legs:
            total = journey.total_estimated_cost
            lines = [journey.timeline_summary or "**Journey Plan Ready**", ""]
            for i, leg in enumerate(journey.legs, 1):
                price_str = f" — ₹{leg.price:,.0f}" if leg.price else ""
                lines.append(f"{i}. {leg.description}{price_str}")
            if total > 0:
                lines.append(f"\n💰 **Total estimated cost: ₹{total:,.0f}**")
            lines.append("\nSee cards below for full details and alternatives.")
            return "\n".join(lines)

        # Greeting
        if any(w in msg for w in ["hello", "hi", "hey", "namaste", "good morning", "good evening"]):
            home = ctx.home_city if ctx else None
            home_str = f" I see you're based in **{home}**." if home else ""
            return (
                f"👋 Hello! I'm **Quest2Travel**, your AI travel assistant.{home_str}\n\n"
                "I can help you:\n"
                "✈️ Book flights  🚂 Find trains  🚌 Book buses\n"
                "🏨 Find hotels  🚗 Rent cars  📋 Plan complete meeting journeys\n\n"
                "Try: *I have a meeting tomorrow at 11 AM at Taj Hotel Mumbai. I'm in Delhi.*"
            )

        # Help
        if any(w in msg for w in ["what can you do", "help", "how"]):
            return (
                "I'm your complete business travel assistant:\n\n"
                "📋 **Meeting Planner** — Tell me your meeting details and I'll plan the entire journey:\n"
                "   flight + airport cab + hotel near venue + return trip\n\n"
                "🔍 **Travel Search** — Search any combination of flights, trains, buses, hotels, cars\n\n"
                "🧠 **Smart Memory** — I remember your city, preferences, and budget throughout\n\n"
                "🏢 **Company Policy** — Automatically checks your company's travel policy\n\n"
                "Try: *Meeting at 11 AM tomorrow at Taj Mumbai, I'm in Delhi. Need return same day.*"
            )

        # Search results
        if results is not None:
            mock_note = " *(sample results — live data temporarily unavailable)*" if results.get("is_mock") else ""

            if results.get("flights"):
                prices = [f["price_inr"] for f in results["flights"] if f.get("price_inr")]
                cheapest = f"₹{min(prices):,.0f}" if prices else "N/A"
                return f"Found **{len(results['flights'])} flights**. Cheapest fare is {cheapest}. See cards below.{mock_note}"

            if results.get("hotels"):
                prices = [h["price"] for h in results["hotels"] if h.get("price")]
                cheapest = f"₹{min(prices):,.0f}" if prices else "N/A"
                meeting_note = " (sorted by proximity to your venue)" if ctx and ctx.meeting else ""
                return f"Found **{len(results['hotels'])} hotels**. Starting at {cheapest}/night{meeting_note}. See cards below.{mock_note}"

            if results.get("trains"):
                return (
                    f"Found **{len(results['trains'])} trains**."
                    f" Cheapest class from {cheapest}. "
                    "See cards below."
                )

            if results.get("buses"):
                prices = [b["price"] for b in results["buses"] if b.get("price")]
                cheapest = f"₹{min(prices):,.0f}" if prices else "N/A"
                return f"Found **{len(results['buses'])} buses**, starting at {cheapest}. See cards below.{mock_note}"

            if results.get("cars"):
                prices = [c["price_day"] for c in results["cars"] if c.get("price_day")]
                cheapest = f"₹{min(prices):,.0f}" if prices else "N/A"
                return f"Found **{len(results['cars'])} cars**, starting at {cheapest}/day. See cards below.{mock_note}"

            # Zero results
            return (
                "No results matched your current filters. "
                "Try raising your budget, removing the cabin class filter, or choosing different dates."
            )

        # Travel context without results yet
        if ctx and (ctx.origin or ctx.destination or ctx.meeting):
            if ctx.meeting and ctx.meeting.meeting_time:
                m = ctx.meeting
                return (
                    f"Got it! Planning your trip for the **{m.meeting_time}** meeting"
                    f"{' at ' + m.meeting_location if m.meeting_location else ''}"
                    f"{' in ' + m.meeting_city if m.meeting_city else ''}. "
                    "Let me ask a few quick questions to understand your travel preferences."
                )
            loc = f"{ctx.origin} to {ctx.destination}" if ctx.origin and ctx.destination else (ctx.destination or ctx.origin)
            return f"Searching for travel options for **{loc}**… Results shown below! 👇"

        return (
            "I'm here to help with your travel plans! "
            "Tell me your meeting details or route — e.g. *Delhi to Mumbai flights tomorrow*"
        )


gemini_agent = GeminiAgent()
