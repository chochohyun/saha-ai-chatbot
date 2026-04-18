import os
import json
import re
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

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
                        docs.append(json.load(f))
                except:
                    continue
    return docs

def get_embedding(text):
    text = re.sub(r"\s+", " ", text).strip()[:8000]
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
        text = (doc.get("title", "") + " " + doc.get("content", ""))[:8000]
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

def find_related_docs(question, docs, doc_embeddings, top_k=3):
    q_emb = np.array(get_embedding(question))
    matrix = np.array(doc_embeddings)
    scores = matrix @ q_emb / (np.linalg.norm(matrix, axis=1) * np.linalg.norm(q_emb))
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [docs[i] for i in top_indices]

docs = load_documents()
print(f"문서 {len(docs)}개 로드 완료")
doc_embeddings = load_doc_embeddings(docs)

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(req: ChatRequest):
    related = find_related_docs(req.message, docs, doc_embeddings)
    context = "\n\n".join([
        f"[제목] {d.get('title','')}\n[URL] {d.get('url','')}\n[본문] {d.get('content','')[:1000]}"
        for d in related
    ])
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": f"당신은 사하구청 민원 안내 AI입니다. 아래 문서만 참고해서 답변하세요.\n\n{context}"},
            {"role": "user", "content": req.message}
        ]
    )
    return {"answer": response.choices[0].message.content}
