from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


# ── 세션 ────────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    """POST /api/sessions 요청 바디 (선택적 초기 제목)"""
    title: Optional[str] = None


class SessionResponse(BaseModel):
    """세션 단건 응답"""
    session_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── 메시지 ──────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    """메시지 단건 응답"""
    message_id: int
    session_id: str
    sender: str                    # "user" | "bot"
    content: str
    metadata_json: Optional[str]   # JSON 문자열 그대로 반환
    feedback: Optional[str]        # "like" | "dislike" | null
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 피드백 ──────────────────────────────────────────────────────────────────

class FeedbackUpdate(BaseModel):
    """POST /api/messages/{message_id}/feedback 요청 바디"""
    feedback: str                  # "like" | "dislike"


# ── 채팅 (기존 /chat 엔드포인트 확장용) ─────────────────────────────────────

class ChatRequest(BaseModel):
    """POST /api/chat 요청 바디 (session_id 추가)"""
    message: str
    history: list = []
    session_id: Optional[str] = None   # 없으면 새 세션 자동 생성
