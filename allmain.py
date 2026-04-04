import os
import re
import json
import numpy as np
from openai import OpenAI

client = OpenAI(api_key="")

MODEL_NAME = "gpt-4.1"
EMBED_MODEL = "text-embedding-3-small"

# 여기 폴더들만 추가하면 됨
DATA_DIRS = [
    "data/여권민원안내/all",
    "data/faq/all",
]

EMBEDDINGS_CACHE = "data/integrated_embeddings_cache.json"


def normalize_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def ensure_doc_schema(doc: dict, source_path: str = "") -> dict:
    """
    어떤 JSON이 와도 아래 구조로 맞춤
    {
      "category": "",
      "title": "",
      "url": "",
      "content": "",
      "search_text": ""
    }
    """
    category = str(doc.get("category", "") or "").strip()
    title = str(doc.get("title", "") or "").strip()
    url = str(doc.get("url", "") or "").strip()
    content = str(doc.get("content", "") or "").strip()
    search_text = str(doc.get("search_text", "") or "").strip()

    # 과거 FAQ 형식 호환
    if not title and "list_title" in doc:
        title = str(doc.get("list_title", "") or "").strip()

    # category 없으면 파일 경로 기반으로 유추
    if not category:
        lower_path = source_path.lower()
        if "faq" in lower_path:
            category = "faq"
        else:
            category = "document"

    # search_text 없으면 자동 생성
    if not search_text:
        extra_parts = []

        # 예전 FAQ 메타가 남아있는 경우도 검색에 활용
        for key in ["dept", "date", "file_flag", "views"]:
            if doc.get(key):
                extra_parts.append(str(doc.get(key)))

        search_text = " ".join(
            p for p in [
                category,
                title,
                content,
                *extra_parts,
            ] if p and str(p).strip()
        )

    return {
        "category": category,
        "title": title,
        "url": url,
        "content": content,
        "search_text": search_text,
    }


def load_json_file(filepath: str) -> list:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    docs = []

    # 리스트 형태
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                docs.append(ensure_doc_schema(item, filepath))

    # 단일 객체 형태
    elif isinstance(data, dict):
        docs.append(ensure_doc_schema(data, filepath))

    return docs


def load_documents():
    docs = []
    seen = set()

    for data_dir in DATA_DIRS:
        if not os.path.exists(data_dir):
            print(f"[건너뜀] 폴더 없음: {data_dir}")
            continue

        for filename in sorted(os.listdir(data_dir)):
            if not filename.endswith(".json"):
                continue

            # 임베딩 캐시류 제외
            if "embedding" in filename.lower():
                continue

            filepath = os.path.join(data_dir, filename)

            try:
                file_docs = load_json_file(filepath)

                for doc in file_docs:
                    # 중복 제거: url 우선, 없으면 title+content 일부
                    dedup_key = doc["url"] or f'{doc["title"]}::{doc["content"][:200]}'
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)
                    docs.append(doc)

            except Exception as e:
                print(f"[로드 실패] {filepath}: {e}")

    return docs


def doc_to_text(doc):
    parts = [
        doc.get("category", ""),
        doc.get("title", ""),
        doc.get("content", ""),
        doc.get("search_text", ""),
    ]
    text = " ".join(p for p in parts if p).strip()
    return normalize_text(text)[:8000]


def get_embedding(text):
    text = normalize_text(text)
    res = client.embeddings.create(input=[text], model=EMBED_MODEL)
    return res.data[0].embedding


def build_embeddings_cache(docs):
    print("임베딩 생성 중 (최초 1회만 실행됨)...")
    cache = []

    for i, doc in enumerate(docs):
        embedding = get_embedding(doc_to_text(doc))
        cache.append({
            "index": i,
            "embedding": embedding
        })
        print(f"  [{i+1}/{len(docs)}] {doc.get('title', '')[:50]}")

    os.makedirs(os.path.dirname(EMBEDDINGS_CACHE), exist_ok=True)
    with open(EMBEDDINGS_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f)

    print("캐시 저장 완료\n")
    return cache


def load_embeddings_cache(docs):
    if os.path.exists(EMBEDDINGS_CACHE):
        try:
            with open(EMBEDDINGS_CACHE, "r", encoding="utf-8") as f:
                cache = json.load(f)

            # 문서 수가 바뀌면 재생성
            if len(cache) != len(docs):
                print("문서 수가 변경되어 임베딩 캐시를 다시 생성합니다.")
                return build_embeddings_cache(docs)

            return cache

        except Exception:
            print("기존 캐시를 읽지 못해 다시 생성합니다.")
            return build_embeddings_cache(docs)

    return build_embeddings_cache(docs)


def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def keyword_score(question: str, doc: dict) -> int:
    q_words = tokenize(question)
    if not q_words:
        return 0

    category = normalize_for_match(doc.get("category", ""))
    title = normalize_for_match(doc.get("title", ""))
    content = normalize_for_match(doc.get("content", ""))
    search_text = normalize_for_match(doc.get("search_text", ""))

    combined = f"{category} {title} {content} {search_text}"

    score = 0
    for word in q_words:
        if word in combined:
            score += 2
        if word in title:
            score += 3
        if word in category:
            score += 1

    return score


def normalize_for_match(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^0-9a-zA-Z가-힣\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(text: str):
    text = normalize_for_match(text)
    return [w for w in text.split() if len(w) >= 2]


def find_related_docs(question, docs, cache, top_k=3):
    # 문서가 적으면 키워드 방식이 더 간단
    if len(docs) <= 10:
        scored = [(keyword_score(question, doc), doc) for doc in docs]
        scored.sort(key=lambda x: x[0], reverse=True)
        picked = [doc for score, doc in scored if score > 0][:top_k]
        return picked if picked else docs[:top_k]

    # 문서가 많으면 임베딩 + 키워드 보정
    q_vec = get_embedding(question)

    scored = []
    for entry in cache:
        idx = entry["index"]
        doc = docs[idx]
        sim = cosine_similarity(q_vec, entry["embedding"])
        key_bonus = keyword_score(question, doc) * 0.02
        final_score = sim + key_bonus
        scored.append((final_score, idx))

    scored.sort(reverse=True)
    return [docs[idx] for _, idx in scored[:top_k]]


def extract_relevant_excerpt(question: str, content: str, max_len: int = 1500) -> str:
    if not content:
        return ""

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    q_words = tokenize(question)

    if not lines:
        return content[:max_len]

    scored_lines = []
    for line in lines:
        normalized = normalize_for_match(line)
        score = sum(1 for word in q_words if word in normalized)
        if score > 0:
            scored_lines.append((score, line))

    scored_lines.sort(key=lambda x: x[0], reverse=True)

    if not scored_lines:
        return content[:max_len]

    excerpt = "\n".join(line for _, line in scored_lines[:8])
    return excerpt[:max_len]


def build_context(question, related_docs):
    context_parts = []

    for doc in related_docs:
        excerpt = extract_relevant_excerpt(question, doc.get("content", ""))

        context_parts.append(
            f"""[카테고리]
{doc.get("category", "")}

[제목]
{doc.get("title", "")}

[URL]
{doc.get("url", "")}

[관련 본문 발췌]
{excerpt}
"""
        )

    return "\n\n".join(context_parts)


def ask_chatbot(question: str, docs: list, cache: list) -> str:
    related_docs = find_related_docs(question, docs, cache, top_k=3)

    if not related_docs:
        return "현재 저장된 문서에서 관련 내용을 찾지 못했습니다."

    context = build_context(question, related_docs)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "너는 사하구청 민원 안내 AI 상담사다. "
                    "반드시 제공된 문서 내용만 근거로 답해야 한다. "
                    "문서에 없는 내용을 추측해서 말하지 마라. "
                    "질문에 맞는 내용을 간단하고 직접적으로 설명하라. "
                    "절차나 방법이 보이면 순서대로 정리하라. "
                    "문서에 없는 정보는 '현재 저장된 문서에서 확인되지 않는다'고 답하라. "
                    "답변 마지막에 참고 URL을 함께 안내하라."
                )
            },
            {
                "role": "user",
                "content": f"""
다음은 질문과 관련된 사하구청 문서들이다.

{context}

위 문서만 바탕으로 아래 질문에 답해줘.
- 질문한 내용에만 답할 것
- 쉬운 말로 설명할 것
- 문서에 없는 내용은 추측하지 말 것
- 마지막에 참고 URL을 적을 것

질문: {question}
"""
            }
        ]
    )

    return response.choices[0].message.content


def main():
    docs = load_documents()

    if not docs:
        print("불러온 문서가 없습니다.")
        print("먼저 크롤러를 실행해서 JSON 파일을 생성해 주세요.")
        return

    print(f"불러온 문서 수: {len(docs)}")
    cache = load_embeddings_cache(docs)

    print("사하구청 AI 민원 상담 시작 (종료하려면 exit 입력)\n")

    while True:
        try:
            question = input("질문: ").strip()
        except KeyboardInterrupt:
            print("\n상담 종료")
            break

        if question.lower() == "exit":
            print("상담 종료")
            break

        if not question:
            print("질문을 입력해줘.\n")
            continue

        try:
            answer = ask_chatbot(question, docs, cache)
            print("\n답변:")
            print(answer)
            print("\n" + "-" * 50 + "\n")
        except Exception as e:
            print(f"\n오류 발생: {e}\n")


if __name__ == "__main__":
    main()