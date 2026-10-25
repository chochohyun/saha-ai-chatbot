from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class CrawlPageState(Base):
    """URL별 본문 해시 및 마지막 수집 상태"""
    __tablename__ = "crawl_page_states"

    url = Column(Text, primary_key=True)
    content_hash = Column(String, nullable=True)
    last_crawled_at = Column(DateTime, nullable=True)
    # 'seeded' | 'new' | 'changed' | 'ok' | 'failed'
    status = Column(String, nullable=True)


class CrawlRun(Base):
    """증분 크롤링 실행 이력"""
    __tablename__ = "crawl_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime)
    finished_at = Column(DateTime, nullable=True)
    checked_urls = Column(Integer, default=0)
    new_count = Column(Integer, default=0)
    changed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=True)                      # 첫 질문 기반 자동 생성 제목
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id"), nullable=False, index=True)
    sender = Column(String, nullable=False)           # "user" | "bot"
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)       # RAG 출처, 담당부서, 링크 등 JSON 문자열
    feedback = Column(String, nullable=True)          # "like" | "dislike" | null
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")
