import os
import sys
import json
import re
import threading
import numpy as np
from rank_bm25 import BM25Okapi
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# uvicorn backend.main:app --reload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, "..", ".env"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

from contextlib import asynccontextmanager
from scheduler import start_scheduler, stop_scheduler

_scheduler = None


def _crawl_and_reload():
    """스케줄러 실행 함수: 증분 크롤링 완료 후 변경 발생 시 인덱스 재로드"""
    from incremental_crawl import run_incremental_crawl
    run_incremental_crawl(reload_callback=reload_docs_inplace)


@asynccontextmanager
async def lifespan(app):
    global _scheduler
    _scheduler = start_scheduler(_crawl_and_reload)
    yield
    stop_scheduler(_scheduler)

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from database import engine, get_db
from models import Base
import models  # noqa: F401
Base.metadata.create_all(bind=engine)

from routers.chat_history import router as history_router, get_or_create_session, save_message
app.include_router(history_router)

# ── Modular RAG 파이프라인 초기화 ────────────────────────────────────────────
from rag import ModularRAGPipeline, PipelineConfig

DATA_DIR = os.path.join(BASE_DIR, "..", "data")
EMBED_MODEL = "text-embedding-3-small"
CACHE_FILE = os.path.join(BASE_DIR, "..", "data", "embeddings_cache.json")


def load_documents():
    docs = []
    for root, _, files in os.walk(DATA_DIR):
        for filename in sorted(files):
            if filename.endswith(".json") and "cache" not in filename:
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        docs.extend([d for d in data if isinstance(d, dict)])
                    elif isinstance(data, dict):
                        docs.append(data)
                except Exception:
                    continue
    return docs


def get_embedding(text: str) -> list[float]:
    text = re.sub(r"\s+", " ", text).strip()[:3000]
    res = client.embeddings.create(input=[text], model=EMBED_MODEL)
    return res.data[0].embedding

async def get_embedding_async(text: str) -> list[float]:
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_embedding, text)


def build_doc_embeddings(docs):
    print("문서 임베딩 생성 중 (최초 1회)...")
    embeddings = []
    for i, doc in enumerate(docs):
        text = (doc.get("title", "") + " " + doc.get("content", ""))[:3000]
        embeddings.append(get_embedding(text))
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(docs)} 완료")
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(embeddings, f)
    print("임베딩 캐시 저장 완료")
    return embeddings


def load_doc_embeddings(docs):
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cached = json.load(f)
        if len(cached) == len(docs):
            print("임베딩 캐시 로드 완료")
            return cached
    return build_doc_embeddings(docs)


def build_bm25(docs):
    tokenized = [
        (d.get("title", "") + " " + d.get("content", "")).split()
        for d in docs
    ]
    return BM25Okapi(tokenized)


# 서버 시작 시 1회 로드
docs = load_documents()
print(f"문서 {len(docs)}개 로드 완료")
doc_embeddings = load_doc_embeddings(docs)
bm25 = build_bm25(docs)
print("BM25 인덱스 생성 완료")

# 파이프라인 설정 — use_reranker=True/False 로 즉시 전환 가능
pipeline = ModularRAGPipeline(
    config=PipelineConfig(
        use_reranker=False,
        top_k_retrieve=10,
        top_k_final=3,
    ),
    docs=docs,
    doc_embeddings=doc_embeddings,
    bm25=bm25,
    openai_client=client,
    embed_fn=get_embedding_async,
)


# ── 관리자 인증 ───────────────────────────────────────────────────────────────

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")


def _require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    """
    X-Admin-Key 헤더로 관리자 인증.
    ADMIN_API_KEY 환경변수 미설정 시 인증 없이 허용 (개발 모드).
    프로덕션에서는 반드시 .env 에 ADMIN_API_KEY=<강한 랜덤 문자열> 설정.
    """
    if ADMIN_API_KEY and x_admin_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="관리자 인증 실패: X-Admin-Key 헤더를 확인하세요.",
        )


# ── 인메모리 인덱스 재로드 ─────────────────────────────────────────────────────

_reload_lock = threading.Lock()


def reload_docs_inplace() -> int:
    """
    서버 재시작 없이 JSON 파일 변경 사항을 메모리 인덱스에 반영.

    • APScheduler 백그라운드 스레드에서 자동 호출 (증분 크롤링 후 변경 발생 시)
    • POST /admin/reload-index 엔드포인트로 수동 호출 가능
    • _reload_lock 으로 동시 재로드 방지 (GIL + threading.Lock)
    • 임베딩 캐시가 없으면 OpenAI API로 재생성하므로 다소 시간이 걸림

    Returns:
        재로드된 문서 수
    """
    global docs, doc_embeddings, bm25, pipeline

    with _reload_lock:
        new_docs = load_documents()
        new_embeddings = load_doc_embeddings(new_docs)
        new_bm25 = build_bm25(new_docs)
        new_pipeline = ModularRAGPipeline(
            config=PipelineConfig(
                use_reranker=False,
                top_k_retrieve=10,
                top_k_final=3,
            ),
            docs=new_docs,
            doc_embeddings=new_embeddings,
            bm25=new_bm25,
            openai_client=client,
            embed_fn=get_embedding_async,
        )
        # 글로벌 교체: Python GIL 덕분에 개별 대입은 원자적
        docs = new_docs
        doc_embeddings = new_embeddings
        bm25 = new_bm25
        pipeline = new_pipeline

    print(f"[reload] 인덱스 재로드 완료: 문서 {len(docs)}개")
    return len(docs)


# ── API ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: list = []
    session_id: str | None = None


@app.post("/api/chat")
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    # ── 1. 세션 확보 및 사용자 메시지 저장 ───────────────────────────────
    session = get_or_create_session(req.session_id, req.message, db)
    save_message(session.session_id, "user", req.message, db)

    # ── 2~3. Modular RAG 파이프라인 실행 (검색 + 재랭킹) ─────────────────
    stream, rag_metadata, timings = await pipeline.run_stream(
        question=req.message,
        history=req.history,
        session_id=session.session_id,
    )
    print(f"[timings] {timings}")

    # ── 4. 스트리밍 응답 + DB 저장 ────────────────────────────────────────
    async def generate():
        full_response = []
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                full_response.append(delta)
                yield f"data: {json.dumps({'delta': delta, 'session_id': session.session_id})}\n\n"

        bot_content = "".join(full_response)
        saved_msg = save_message(session.session_id, "bot", bot_content, db, rag_metadata)
        yield f"data: {json.dumps({'done': True, 'session_id': session.session_id, 'message_id': saved_msg.message_id})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── 관리자 엔드포인트 ─────────────────────────────────────────────────────────

@app.get("/admin/crawl-runs")
def get_crawl_runs(
    limit: int = 20,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    """최근 증분 크롤링 실행 이력 반환 (관리자 인증 필요)"""
    from models import CrawlRun
    runs = (
        db.query(CrawlRun)
        .order_by(CrawlRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "checked_urls": r.checked_urls,
            "new_count": r.new_count,
            "changed_count": r.changed_count,
            "failed_count": r.failed_count,
            "duration_sec": (
                round((r.finished_at - r.started_at).total_seconds(), 1)
                if r.finished_at and r.started_at else None
            ),
        }
        for r in runs
    ]


@app.post("/admin/reload-index")
async def reload_index(_: None = Depends(_require_admin)):
    """
    서버 재시작 없이 JSON 파일 변경 사항을 메모리 인덱스에 즉시 반영.
    임베딩 캐시가 없으면 재생성하므로 수십 초~수 분 소요될 수 있음.
    """
    import asyncio
    loop = asyncio.get_event_loop()
    doc_count = await loop.run_in_executor(None, reload_docs_inplace)
    return {"status": "ok", "docs_loaded": doc_count}
