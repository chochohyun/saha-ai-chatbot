import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import ChatSession, ChatMessage
from schemas import (
    SessionCreate,
    SessionResponse,
    MessageResponse,
    FeedbackUpdate,
)

router = APIRouter(prefix="/api", tags=["chat-history"])


# ── 세션 ────────────────────────────────────────────────────────────────────

@router.post("/sessions", response_model=SessionResponse, status_code=201)
def create_session(body: SessionCreate, db: Session = Depends(get_db)):
    """새 대화 세션 생성"""
    session = ChatSession(
        session_id=str(uuid.uuid4()),
        title=body.title,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions(db: Session = Depends(get_db)):
    """저장된 모든 세션 목록 (최신순) — 사이드바 '최근 문의 내역'용"""
    return (
        db.query(ChatSession)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )


# ── 메시지 ──────────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
def get_messages(session_id: str, db: Session = Depends(get_db)):
    """특정 세션의 전체 대화 히스토리 (시간순)"""
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )


# ── 피드백 ──────────────────────────────────────────────────────────────────

@router.post("/messages/{message_id}/feedback", response_model=MessageResponse)
def update_feedback(
    message_id: int,
    body: FeedbackUpdate,
    db: Session = Depends(get_db),
):
    """챗봇 메시지 피드백(like/dislike) 업데이트"""
    if body.feedback not in ("like", "dislike"):
        raise HTTPException(status_code=422, detail="feedback 값은 'like' 또는 'dislike'여야 합니다.")

    message = db.query(ChatMessage).filter(ChatMessage.message_id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="메시지를 찾을 수 없습니다.")
    if message.sender != "bot":
        raise HTTPException(status_code=400, detail="사용자 메시지에는 피드백을 남길 수 없습니다.")

    message.feedback = body.feedback
    db.commit()
    db.refresh(message)
    return message


# ── 내부 헬퍼 (main.py의 /api/chat 엔드포인트에서 호출) ───────────────────

def get_or_create_session(session_id: str | None, first_message: str, db: Session) -> ChatSession:
    """
    session_id가 있으면 해당 세션 반환, 없으면 새 세션 생성.
    새 세션인 경우 첫 메시지 앞 30자를 제목으로 사용.
    """
    if session_id:
        session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if session:
            session.updated_at = datetime.utcnow()
            db.commit()
            return session

    # 새 세션 생성
    title = first_message[:30] + ("..." if len(first_message) > 30 else "")
    session = ChatSession(
        session_id=str(uuid.uuid4()),
        title=title,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def save_message(
    session_id: str,
    sender: str,
    content: str,
    db: Session,
    metadata_json: str | None = None,
) -> ChatMessage:
    """메시지 저장 후 message_id 반환"""
    msg = ChatMessage(
        session_id=session_id,
        sender=sender,
        content=content,
        metadata_json=metadata_json,
        created_at=datetime.utcnow(),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg
