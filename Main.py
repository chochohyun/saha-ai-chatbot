import os
import re
import json
import numpy as np
from openai import OpenAI

client = OpenAI(api_key="")

DATA_DIR = "data/다대레포츠광장_인조잔디족구장a/all"
EMBEDDINGS_CACHE = "data/다대레포츠광장_인조잔디족구장a/embeddings_cache.json"
EMBED_MODEL = "text-embedding-3-small"


def load_documents():
    docs = []
    for filename in sorted(os.listdir(DATA_DIR)):
        if filename.endswith(".json") and filename != "embeddings_cache.json":
            filepath = os.path.join(DATA_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                docs.append(json.load(f))
    return docs


def doc_to_text(doc):
    """임베딩용 텍스트 구성 (title + content 위주)"""
    parts = [
        doc.get("title", ""),
        doc.get("content", ""),
        doc.get("search_text", ""),
    ]
    text = " ".join(p for p in parts if p).strip()
    return re.sub(r"\s+", " ", text)[:8000]


def get_embedding(text):
    text = re.sub(r"\s+", " ", text).strip()
    res = client.embeddings.create(input=[text], model=EMBED_MODEL)
    return res.data[0].embedding


def build_embeddings_cache(docs):
    """전체 문서 임베딩 생성 후 캐시 파일에 저장"""
    print("임베딩 생성 중 (최초 1회만 실행됨)...")
    cache = []
    for i, doc in enumerate(docs):
        embedding = get_embedding(doc_to_text(doc))
        cache.append({"index": i, "embedding": embedding})
        print(f"  [{i+1}/{len(docs)}] {doc.get('title', '')[:40]}")

    with open(EMBEDDINGS_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f)
    print("캐시 저장 완료\n")
    return cache


def load_embeddings_cache(docs):
    """캐시 있으면 로드, 없으면 생성"""
    if os.path.exists(EMBEDDINGS_CACHE):
        with open(EMBEDDINGS_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    return build_embeddings_cache(docs)


def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def find_related_docs(question, docs, cache, top_k=3):
    # 문서가 적을 때는 전부 반환 (임베딩 검색보다 정확)
    if len(docs) <= 10:
        return docs

    q_vec = get_embedding(question)
    scored = sorted(
        [(cosine_similarity(q_vec, entry["embedding"]), entry["index"]) for entry in cache],
        reverse=True
    )
    return [docs[idx] for _, idx in scored[:top_k]]


def build_context(related_docs):
    parts = []
    for doc in related_docs:
        parts.append(
            f"[제목] {doc.get('title', '')}\n"
            f"[URL] {doc.get('url', '')}\n"
            f"[본문]\n{doc.get('content', '')}"
        )
    return "\n\n".join(parts)


def main():
    docs = load_documents()
    cache = load_embeddings_cache(docs)
    print("사하구청 AI 민원 상담 시작 (종료하려면 exit 입력)\n")

    while True:
        question = input("질문: ").strip()

        if question.lower() == "exit":
            print("상담 종료")
            break
        if not question:
            continue

        related_docs = find_related_docs(question, docs, cache)
        context = build_context(related_docs)

        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "너는 사하구청 민원 안내 AI 상담사다. "
                        "반드시 제공된 문서 정보만 바탕으로 답하고, "
                        "질문한 내용에만 간단하고 직접적으로 답해. "
                        "모르면 모른다고 말하고, 추측하지 마."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"다음은 사하구청 관련 문서들이다.\n\n{context}\n\n"
                        f"위 문서만 바탕으로 아래 질문에 답해줘.\n"
                        f"- 질문한 내용에만 답할 것\n"
                        f"- 쉬운 말로 설명할 것\n"
                        f"- 관련 URL이 있으면 함께 안내할 것\n\n"
                        f"질문: {question}"
                    )
                }
            ]
        )

        print("\n답변:")
        print(response.choices[0].message.content)
        print("\n" + "-" * 50 + "\n")


if __name__ == "__main__":
    main()
