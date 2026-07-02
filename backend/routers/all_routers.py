"""
All FastAPI routers.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging

from models.travel import ChatRequest, ChatResponse, FilterRequest, Company, ServiceType
from services.chat import chat_service
from services.permission_service import permission_service
from memory.conversation import ConversationMemory
from database.connection import get_db

logger = logging.getLogger(__name__)

# ── Chat ──────────────────────────────────────────────────────────────────────
chat_router = APIRouter(prefix="/api/chat", tags=["Chat"])


@chat_router.post("", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    try:
        return await chat_service.process(request)
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process message")


@chat_router.get("/{session_id}/history")
async def get_history(session_id: str, limit: int = Query(50, ge=1, le=200)):
    memory = ConversationMemory(session_id)
    msgs   = await memory.get_messages(limit=limit)
    return [
        {"message_id": m.message_id, "role": m.role.value,
         "content": m.content, "created_at": m.created_at.isoformat(),
         "travel_intent": m.travel_intent.value if m.travel_intent else None}
        for m in msgs
    ]


@chat_router.get("/{session_id}/context")
async def get_context(session_id: str):
    memory = ConversationMemory(session_id)
    ctx    = await memory.get_context()
    return ctx.dict()


@chat_router.delete("/{session_id}/context")
async def clear_context(session_id: str):
    memory = ConversationMemory(session_id)
    await memory.clear_context()
    return {"status": "cleared", "session_id": session_id}


# ── Sessions ──────────────────────────────────────────────────────────────────
sessions_router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


@sessions_router.get("")
async def list_sessions(limit: int = Query(20, ge=1, le=100)):
    db = get_db()
    results = []
    async for doc in db.sessions.find(
        {}, projection={"session_id":1,"created_at":1,"updated_at":1,
                         "message_count":1,"travel_context":1},
        sort=[("updated_at", -1)], limit=limit,
    ):
        doc.pop("_id", None)
        results.append(doc)
    return results


@sessions_router.delete("/{session_id}")
async def delete_session(session_id: str):
    db = get_db()
    await db.sessions.delete_one({"session_id": session_id})
    await db.messages.delete_many({"session_id": session_id})
    await db.travel_searches.delete_many({"session_id": session_id})
    return {"status": "deleted"}


# ── Travel ────────────────────────────────────────────────────────────────────
travel_router = APIRouter(prefix="/api/travel", tags=["Travel"])


@travel_router.get("/{session_id}/searches")
async def get_searches(session_id: str, limit: int = Query(10, ge=1, le=50)):
    db = get_db()
    results = []
    async for doc in db.travel_searches.find(
        {"session_id": session_id}, sort=[("created_at", -1)], limit=limit,
    ):
        doc.pop("_id", None)
        results.append(doc)
    return results


@travel_router.post("/filter")
async def apply_filters(request: dict):
    """Re-run search with updated filters on existing session."""
    from services.travel_search import travel_search_service
    from models.travel import TravelMode, CabinClass

    session_id = request.get("session_id", "")
    filters    = request.get("filters", {})
    mode       = request.get("search_type", "general")

    memory  = ConversationMemory(session_id)
    context = await memory.get_context()

    if filters.get("max_budget"):   context.max_budget  = float(filters["max_budget"])
    if filters.get("min_budget"):   context.min_budget  = float(filters["min_budget"])
    if filters.get("cabin_class"):
        try: context.cabin_class = CabinClass(filters["cabin_class"])
        except Exception: pass
    if filters.get("hotel_stars"):  context.hotel_stars = int(filters["hotel_stars"])
    if filters.get("non_stop"):     context.non_stop_only = bool(filters["non_stop"])
    try:  context.mode = TravelMode(mode)
    except Exception: pass

    result = await travel_search_service.search(session_id, context)
    return result.dict()


# ── Company Admin ─────────────────────────────────────────────────────────────
company_router = APIRouter(prefix="/api/company", tags=["Company"])


@company_router.get("")
async def list_companies():
    db = get_db()
    results = []
    async for doc in db.companies.find({}, sort=[("name", 1)]):
        doc.pop("_id", None)
        results.append(doc)
    return results


@company_router.post("")
async def create_company(company: Company):
    await permission_service.upsert_company(company)
    return {"status": "created", "company_id": company.company_id}


@company_router.put("/{company_id}/services")
async def update_services(company_id: str, services: List[str]):
    """Update allowed services for a company."""
    try:
        service_list = [ServiceType(s) for s in services]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid service: {e}")

    db = get_db()
    await db.companies.update_one(
        {"company_id": company_id},
        {"$set": {"allowed_services": services}},
    )
    return {"status": "updated", "allowed_services": services}


@company_router.get("/{company_id}")
async def get_company(company_id: str):
    company = await permission_service.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company.dict()
