import os
import json
import re
import numpy as np
from rank_bm25 import BM25Okapi
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

# uvicorn backend.main:app --reload
 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "..", ".env"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()   

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(BASE_DIR, "..", "data")
EMBED_MODEL = "text-embedding-3-small"

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
                except:
                    continue
    return docs

def get_embedding(text):
    text = re.sub(r"\s+", " ", text).strip()[:3000]
    res = client.embeddings.create(input=[text], model=EMBED_MODEL)
    return res.data[0].embedding

def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

CACHE_FILE = os.path.join(BASE_DIR, "..", "data", "embeddings_cache.json")

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


def find_related_docs(question, docs, doc_embeddings, bm25, top_k=5):
    # 벡터 점수
    q_emb = np.array(get_embedding(question))
    matrix = np.array(doc_embeddings)
    vector_scores = matrix @ q_emb / (np.linalg.norm(matrix, axis=1) * np.linalg.norm(q_emb))

    # BM25 점수
    bm25_scores = np.array(bm25.get_scores(question.split()))

    # 정규화 후 합산 (0~1 사이로 맞추기)
    vector_norm = (vector_scores - vector_scores.min()) / (vector_scores.max() - vector_scores.min() + 1e-9)
    bm25_norm = (bm25_scores - bm25_scores.min()) / (bm25_scores.max() - bm25_scores.min() + 1e-9)

    # 하이브리드 점수 (벡터 70% + BM25 30%)
    hybrid_scores = 0.7 * vector_norm + 0.3 * bm25_norm

    top_indices = np.argsort(hybrid_scores)[::-1][:top_k]
    return [docs[i] for i in top_indices]


docs = load_documents()
print(f"문서 {len(docs)}개 로드 완료")
doc_embeddings = load_doc_embeddings(docs)
bm25 = build_bm25(docs)
print("BM25 인덱스 생성 완료")

class ChatRequest(BaseModel):
    message: str
    history: list = []

@app.post("/chat")
async def chat(req: ChatRequest):
    related = find_related_docs(req.message, docs, doc_embeddings, bm25)
    context = "\n\n".join([
        f"[제목] {d.get('title','')}\n[URL] {d.get('url','')}\n[본문] {d.get('content','')[:1000]}"
        for d in related
    ])
    messages = [
        {"role": "system", "content": f"""당신은 부산광역시 사하구청의 공식 AI 민원 안내 서비스입니다.

답변 규칙:
1. 아래 제공된 [참고 문서]를 우선적으로 활용하여 친절하고 명확하게 답변하세요.
2. 참고 문서에 관련 내용이 부족하더라도, 일반적인 행정 지식을 바탕으로 최대한 도움이 되는 답변을 제공하세요.
3. 참고 문서에서 관련 내용을 찾은 경우, 답변 마지막에 출처 URL을 "📎 출처: {{url}}" 형식으로 표기하세요.
4. 사하구 민원과 전혀 무관한 질문(예: 요리, 연예인 등)인 경우에만:
   - "죄송합니다. 해당 내용은 제가 안내드리기 어렵습니다." 라고 안내하세요.
   - 사하구청 대표전화: 051-220-4000 을 안내하세요.
5. 존댓말을 사용하고, 목록이나 단계가 있을 경우 번호를 붙여 정리하세요.

[참고 문서]
{context}"""}
    ]
    for h in req.history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": req.message})

    async def generate():
        stream = client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield f"data: {json.dumps({'delta': delta})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )