"""
Chat Router — /api/chat
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import logging
from fastapi import Depends

from security.dependencies import get_current_user
from models.user import User
from models.travel import ChatRequest, ChatResponse, Message
from services.chat import chat_service
from memory.conversation import ConversationMemory
from database.connection import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Send a user message and receive an AI response.
    """

    try:

        # Inject authenticated user information
        request.user_id = current_user.user_id
        request.company_id = current_user.company_id

        response = await chat_service.process(request)

        return response

    except Exception as e:

        logger.error(
            f"Chat processing error: {e}",
            exc_info=True,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to process message",
        )


@router.get("/{session_id}/history", response_model=List[dict])
async def get_history(
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
):
    """Get conversation history for a session."""
    try:
        memory = ConversationMemory(session_id)
        messages = await memory.get_messages(limit=limit)
        return [
            {
                "message_id": m.message_id,
                "role": m.role.value,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
                "travel_intent": m.travel_intent.value if m.travel_intent else None,
            }
            for m in messages
        ]
    except Exception as e:
        logger.error(f"History fetch error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch history")


@router.get("/{session_id}/context")
async def get_context(session_id: str):
    """Get the current travel context for a session."""
    memory = ConversationMemory(session_id)
    ctx = await memory.get_context()
    return ctx.dict()


@router.delete("/{session_id}/context")
async def clear_context(session_id: str):
    """Clear travel context (start fresh search) for a session."""
    memory = ConversationMemory(session_id)
    await memory.clear_context()
    return {"status": "cleared", "session_id": session_id}
