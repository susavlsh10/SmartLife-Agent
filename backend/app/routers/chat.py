import uuid
from fastapi import APIRouter, HTTPException, status, Header, Depends
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models import ChatMessage, ChatResponse, ChatHistoryItem
from app.auth import verify_token, get_user_by_id
from app.database import get_db
from app.db_models import ChatHistory

router = APIRouter()


def get_current_user_id(
    authorization: Optional[str] = Header(None), db: Session = Depends(get_db)
) -> str:
    """Extract and verify user ID from authorization token"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    payload = verify_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Verify user exists
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user_id


@router.post("", response_model=ChatResponse)
async def send_message(
    message: ChatMessage,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Send a chat message and get AI response"""
    from app.agent.gemini_client import get_gemini_response

    try:
        # Get response from Gemini
        response_text = await get_gemini_response(message.message)
        print(response_text)
        # Save to database
        chat_entry = ChatHistory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            message=message.message,
            response=response_text,
        )
        db.add(chat_entry)
        db.commit()

        return ChatResponse(response=response_text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        )


@router.get("/history", response_model=List[ChatHistoryItem])
async def get_history(
    user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    """Get chat history for the current user"""
    chat_entries = (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == user_id)
        .order_by(ChatHistory.timestamp.asc())
        .all()
    )

    return [
        ChatHistoryItem(
            id=entry.id,
            message=entry.message,
            response=entry.response,
            timestamp=entry.timestamp.isoformat() if entry.timestamp else "",
        )
        for entry in chat_entries
    ]

