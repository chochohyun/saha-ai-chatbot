import os
import json
import re
import numpy as np
from rank_bm25 import BM25Okapi
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


def find_related_docs(question, docs, doc_embeddings, bm25, top_k=3):
    # 벡터 점수
    q_emb = np.array(get_embedding(question))
    matrix = np.array(doc_embeddings)
    vector_scores = matrix @ q_emb / (np.linalg.norm(matrix, axis=1) * np.linalg.norm(q_emb))

    # BM25 점수
    bm25_scores = np.array(bm25.get_scores(question.split()))

    # 정규화 후 합산 (0~1 사이로 맞추기)
    vector_norm = (vector_scores - vector_scores.min()) / (vector_scores.max() - vector_scores.min() + 1e-9)
    bm25_norm = (bm25_scores - bm25_scores.min()) / (bm25_scores.max() - bm25_scores.min() + 1e-9)

    # 하이브리드 점수 (벡터 60% + BM25 40%)
    hybrid_scores = 0.6 * vector_norm + 0.4 * bm25_norm

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
        {"role": "system", "content": f"당신은 사하구청 민원 안내 AI입니다. 아래 문서만 참고해서 친절하게 답변하세요. 모르면 사하구청에 직접 문의하라고 안내하세요.\n\n{context}"}
    ]
    for h in req.history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": req.message})

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages
    )
    return {"answer": response.choices[0].message.content}