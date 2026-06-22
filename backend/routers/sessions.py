"""
Sessions Router — /api/sessions
Travel Router — /api/travel
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging

from database.connection import get_db
from models.travel import FilterRequest, TravelMode

logger = logging.getLogger(__name__)

# ── Sessions ──────────────────────────────────────────────────────────────────
sessions_router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


@sessions_router.get("")
async def list_sessions(limit: int = Query(20, ge=1, le=100)):
    """List recent sessions (for sidebar chat history)."""
    db = get_db()
    sessions = []
    cursor = db.sessions.find(
        {},
        projection={"session_id": 1, "created_at": 1, "updated_at": 1,
                    "message_count": 1, "travel_context": 1},
        sort=[("updated_at", -1)],
        limit=limit,
    )
    async for doc in cursor:
        doc.pop("_id", None)
        sessions.append(doc)
    return sessions


@sessions_router.get("/{session_id}")
async def get_session(session_id: str):
    """Get a specific session."""
    db = get_db()
    doc = await db.sessions.find_one({"session_id": session_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    doc.pop("_id", None)
    return doc


@sessions_router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and all its messages."""
    db = get_db()
    await db.sessions.delete_one({"session_id": session_id})
    await db.messages.delete_many({"session_id": session_id})
    await db.travel_searches.delete_many({"session_id": session_id})
    return {"status": "deleted", "session_id": session_id}


# ── Travel ────────────────────────────────────────────────────────────────────
travel_router = APIRouter(prefix="/api/travel", tags=["Travel"])


@travel_router.get("/{session_id}/searches")
async def get_travel_searches(
    session_id: str,
    search_type: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
):
    """Get travel search history for a session."""
    db = get_db()
    query = {"session_id": session_id}
    if search_type:
        query["search_type"] = search_type
    cursor = db.travel_searches.find(
        query,
        sort=[("created_at", -1)],
        limit=limit,
    )
    results = []
    async for doc in cursor:
        doc.pop("_id", None)
        results.append(doc)
    return results


@travel_router.post("/filter")
async def apply_filters(request: FilterRequest):
    """
    Apply filters to the last search results of a session.
    This is called when user says 'under 5000' or 'only business class'.
    """
    from memory.conversation import ConversationMemory
    from services.travel_search import travel_search_service

    memory = ConversationMemory(request.session_id)
    context = await memory.get_context()

    # Merge filters into context
    f = request.filters
    if "max_budget" in f:
        context.max_budget = f["max_budget"]
    if "min_budget" in f:
        context.min_budget = f["min_budget"]
    if "cabin_class" in f:
        from models.travel import CabinClass
        context.cabin_class = CabinClass(f["cabin_class"])
    if "hotel_stars" in f:
        context.hotel_stars = f["hotel_stars"]
    if "non_stop" in f:
        context.non_stop_only = f["non_stop"]
    if "mode" in f:
        context.mode = TravelMode(f["mode"])

    # Re-run search with updated filters
    result = await travel_search_service.search(request.session_id, context)
    return result.dict()
