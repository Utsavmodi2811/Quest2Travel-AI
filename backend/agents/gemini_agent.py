"""
Gemini AI Agent.
Handles: greetings, general conversation, travel guidance, and a SHORT
summary of search results — never an enumeration.

IMPORTANT: The frontend already renders flight/hotel/train/car cards with
full details. Gemini's job is ONLY to summarize, e.g.:
  "10 flights found. Cheapest fare starts at ₹7,355. See cards below."
NEVER list every flight/hotel/train/car — that is what the cards are for.
"""

import logging
from typing import Optional, List, Dict, Any

from config.settings import settings
from models.travel import TravelContext, TravelMode

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Quest2Travel, a friendly and knowledgeable AI travel assistant for India and international travel.

You help users:
- Search and compare flights, trains, buses, hotels, and car rentals
- Plan trips and suggest itineraries
- Answer travel questions (visa, weather, best time to visit, tips)

CRITICAL RULE ABOUT SEARCH RESULTS:
The user interface already displays full result cards (flight numbers, times,
hotel names, prices, amenities, etc.) directly below your message. You must
NEVER repeat, list, or enumerate individual results in your text reply.

When search results are provided to you, reply with ONLY a one or two
sentence summary in this style:
  Flights: "10 flights found from Mumbai to Delhi. Cheapest fare starts at ₹7,355. See cards below."
  Hotels:  "12 hotels found in Goa. Cheapest stay is ₹851/night. See cards below."
  Trains:  "8 trains found between Ahmedabad and Bangalore. Fares start at ₹480."
  Cars:    "6 cars available in Pune, starting at ₹799/day."
  Buses:   "5 buses found, starting at ₹480."

If a filter was applied (budget, class, stars) and it returned ZERO results,
say so plainly and suggest loosening the filter — do not invent results.
  Example: "No flights found under ₹3,000 for this route. Try raising your budget or removing the filter."

If results are marked is_mock=true, casually note: "(showing sample results — live data temporarily unavailable)"
appended to your one-line summary — do not make a big deal of it.

Other rules:
- Be conversational and concise. Use ₹ for Indian currency.
- Remember travel context (origin, destination, class, budget) throughout the conversation.
- Never invent flight numbers, prices, or hotel names — only reference counts/cheapest price from what's given.
- For general questions (history, culture, weather, "what can you do"), answer normally and helpfully —
  the no-enumeration rule applies ONLY when travel search results are attached to this turn.
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
                logger.info("Gemini agent initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
        else:
            logger.warning("GEMINI_API_KEY not set. Using rule-based fallback responses.")

    async def chat(
        self,
        user_message: str,
        history: List[Dict],
        travel_context: Optional[TravelContext] = None,
        travel_results: Optional[Dict] = None,
    ) -> str:
        if not self._configured or not self._model:
            return self._rule_based_response(user_message, travel_context, travel_results)

        try:
            parts = [user_message]

            if travel_context and (travel_context.origin or travel_context.destination):
                parts.append(f"\n[Context: {self._fmt_context(travel_context)}]")

            # IMPORTANT: distinguish "no search ran this turn" (travel_results
            # is None) from "a search ran and found zero matches" (an empty
            # dict {} — e.g. a budget filter that matched nothing). Both are
            # falsy in Python, so we must check explicitly with `is not None`.
            if travel_results is not None:
                summary_stats = self._summarize_results(travel_results)
                parts.append(f"\n[Search result stats — summarize ONLY, do not list items:\n{summary_stats}\n]")

            full_prompt = "\n".join(parts)

            chat_history = history[:-1] if history else []
            chat = self._model.start_chat(history=chat_history)
            response = await chat.send_message_async(full_prompt)
            return response.text

        except Exception as e:
            logger.error(f"Gemini API error: {type(e).__name__}: {e}")
            return self._rule_based_response(user_message, travel_context, travel_results)

    async def generate_suggestions(self, context: TravelContext) -> List[str]:
        if context.origin and context.destination:
            suggestions = []
            if context.mode != TravelMode.FLIGHT:
                suggestions.append("Show me flights")
            if context.mode != TravelMode.TRAIN:
                suggestions.append("Show trains")
            if context.mode != TravelMode.HOTEL:
                suggestions.append(f"Hotels in {context.destination}")
            if not context.max_budget:
                suggestions.append("Under ₹5,000")
            if context.mode == TravelMode.FLIGHT and not context.cabin_class:
                suggestions.append("Business class only")
            return suggestions[:3]
        return [
            "Delhi to Mumbai flights tomorrow",
            "Hotels in Goa under ₹5000",
            "Train from Ahmedabad to Bangalore",
        ]

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _summarize_results(self, results: Dict) -> str:
        """
        Reduce full results to COUNTS + CHEAPEST PRICE only.
        This is deliberately lossy — Gemini never sees individual
        flight numbers / hotel names, so it cannot enumerate them.
        """
        lines = []
        if results.get("is_mock"):
            lines.append("is_mock=true (mention sample-data note briefly)")

        if results.get("flights"):
            prices = [f["price_inr"] for f in results["flights"] if f.get("price_inr")]
            cheapest = min(prices) if prices else None
            lines.append(f"flights_count={len(results['flights'])} cheapest_price_inr={cheapest}")

        if results.get("hotels"):
            prices = [h["price"] for h in results["hotels"] if h.get("price")]
            cheapest = min(prices) if prices else None
            lines.append(f"hotels_count={len(results['hotels'])} cheapest_price_per_night_inr={cheapest}")

        if results.get("trains"):
            all_prices = []
            for t in results["trains"]:
                for c in t.get("classes", []):
                    if c.get("price"):
                        all_prices.append(c["price"])
            cheapest = min(all_prices) if all_prices else None
            lines.append(f"trains_count={len(results['trains'])} cheapest_class_price_inr={cheapest}")

        if results.get("buses"):
            prices = [b["price"] for b in results["buses"] if b.get("price")]
            cheapest = min(prices) if prices else None
            lines.append(f"buses_count={len(results['buses'])} cheapest_price_inr={cheapest}")

        if results.get("cars"):
            prices = [c["price_day"] for c in results["cars"] if c.get("price_day")]
            cheapest = min(prices) if prices else None
            lines.append(f"cars_count={len(results['cars'])} cheapest_price_per_day_inr={cheapest}")

        if not any(results.get(k) for k in ("flights", "hotels", "trains", "buses", "cars")):
            lines.append("zero_results=true (filter likely too strict — tell user plainly, suggest loosening it)")

        return "\n".join(lines) if lines else "no_results"

    def _fmt_context(self, ctx: TravelContext) -> str:
        parts = []
        if ctx.origin:      parts.append(f"From={ctx.origin}")
        if ctx.destination: parts.append(f"To={ctx.destination}")
        if ctx.travel_date: parts.append(f"Date={ctx.travel_date}")
        if ctx.mode:        parts.append(f"Mode={ctx.mode.value}")
        if ctx.cabin_class: parts.append(f"Class={ctx.cabin_class.value}")
        if ctx.hotel_stars: parts.append(f"Stars={ctx.hotel_stars}")
        if ctx.max_budget:  parts.append(f"MaxBudget=₹{ctx.max_budget:,.0f}")
        return " | ".join(parts) if parts else "none"

    def _rule_based_response(
        self,
        message: str,
        context: Optional[TravelContext],
        results: Optional[Dict],
    ) -> str:
        """
        Fallback used when Gemini is not configured or fails.
        Mirrors the same no-enumeration rule: counts + cheapest price only.
        """
        msg = message.lower().strip()

        if any(w in msg for w in ["hello", "hi", "hey", "namaste", "good morning", "good evening"]):
            return (
                "👋 Hello! I'm **Quest2Travel**, your AI travel assistant.\n\n"
                "I can help you:\n"
                "✈️ Search flights\n🚂 Find trains\n🚌 Book buses\n"
                "🏨 Find hotels\n🚗 Rent cars\n🗺️ Plan trips\n\n"
                "Just tell me where you'd like to go! E.g. *Delhi to Mumbai tomorrow*"
            )

        if any(w in msg for w in ["what can you do", "help", "how do you work"]):
            return (
                "I'm your complete travel assistant! Here's what I can do:\n\n"
                "🔍 **Search** — flights, trains, buses, hotels, car rentals\n"
                "🧠 **Remember** — I keep your route, budget & preferences through the conversation\n"
                "✏️ **Understand typos** — 'Delhii to Mumabi' works fine!\n"
                "🔄 **Follow-ups** — say 'only flights', 'business class', 'under ₹6000'\n\n"
                "Try: *Ahmedabad to Bangalore flights*"
            )

        # IMPORTANT: `results is not None` (not `if results:`) — an empty
        # dict {} means a search legitimately ran and found zero matches
        # (e.g. a too-strict budget filter), which is different from no
        # search having run at all. Plain truthiness would treat {} as
        # "no results provided" and skip straight to the generic prompt,
        # hiding the fact that the user's filter excluded everything.
        if results is not None:
            mock_note = " (showing sample results — live data temporarily unavailable)" if results.get("is_mock") else ""

            if results.get("flights"):
                prices = [f["price_inr"] for f in results["flights"] if f.get("price_inr")]
                cheapest = f"₹{min(prices):,.0f}" if prices else "N/A"
                return f"{len(results['flights'])} flights found. Cheapest fare starts at {cheapest}. See cards below.{mock_note}"

            if results.get("hotels"):
                prices = [h["price"] for h in results["hotels"] if h.get("price")]
                cheapest = f"₹{min(prices):,.0f}" if prices else "N/A"
                return f"{len(results['hotels'])} hotels found. Cheapest stay is {cheapest}/night. See cards below.{mock_note}"

            if results.get("trains"):
                all_prices = [c["price"] for t in results["trains"] for c in t.get("classes", []) if c.get("price")]
                cheapest = f"₹{min(all_prices):,.0f}" if all_prices else "N/A"
                return f"{len(results['trains'])} trains found. Fares start at {cheapest}. See cards below.{mock_note}"

            if results.get("buses"):
                prices = [b["price"] for b in results["buses"] if b.get("price")]
                cheapest = f"₹{min(prices):,.0f}" if prices else "N/A"
                return f"{len(results['buses'])} buses found, starting at {cheapest}. See cards below.{mock_note}"

            if results.get("cars"):
                prices = [c["price_day"] for c in results["cars"] if c.get("price_day")]
                cheapest = f"₹{min(prices):,.0f}" if prices else "N/A"
                return f"{len(results['cars'])} cars available, starting at {cheapest}/day. See cards below.{mock_note}"

            # No category had results — zero matches (e.g. a too-strict filter)
            return (
                "No results matched your filters for this search. "
                "Try raising your budget, removing a filter, or broadening the search."
            )

        if context and (context.origin or context.destination):
            loc = (
                f"{context.origin} to {context.destination}"
                if context.origin and context.destination
                else (context.destination or context.origin)
            )
            return f"Searching for travel options for **{loc}**... Results are shown below! 👇"

        return (
            "I'm here to help with your travel plans! "
            "Tell me your route — for example: *Delhi to Mumbai flights tomorrow*"
        )


gemini_agent = GeminiAgent()
