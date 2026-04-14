import os
import json
import re
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = "data"
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

def find_related_docs(question, docs, top_k=3):
    q_emb = get_embedding(question)
    scored = []
    for doc in docs:
        text = (doc.get("title", "") + " " + doc.get("content", ""))[:8000]
        d_emb = get_embedding(text)
        score = cosine_similarity(q_emb, d_emb)
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]

docs = load_documents()
print(f"문서 {len(docs)}개 로드 완료")

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(req: ChatRequest):
    related = find_related_docs(req.message, docs)
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
