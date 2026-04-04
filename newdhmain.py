import os
os.environ["PYTHONIOENCODING"] = "utf-8"

import re
import json
from openai import OpenAI

client = OpenAI(api_key="")
MODEL_NAME = "gpt-4.1"
DATA_PATH = "data/faq/all/faq.json"


def load_data():
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"FAQ 파일이 없습니다: {DATA_PATH}\n"
            "먼저 python3 dhtwo.py 를 실행해서 faq.json을 생성해 주세요."
        )

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        raise ValueError("faq.json 파일은 있지만 내용이 비어 있습니다.")

    if not isinstance(data, list):
        raise ValueError("faq.json 형식이 잘못되었습니다. 리스트 형태여야 합니다.")

    return data


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^0-9a-zA-Z가-힣\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(text: str):
    text = normalize_text(text)
    return [w for w in text.split() if len(w) >= 2]


def score_document(question: str, doc: dict) -> int:
    q_words = tokenize(question)
    if not q_words:
        return 0

    title = normalize_text(doc.get("title", ""))
    content = normalize_text(doc.get("content", ""))
    search_text = normalize_text(doc.get("search_text", ""))
    category = normalize_text(doc.get("category", ""))

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


def find_related_docs(question: str, docs: list, top_k: int = 3):
    scored = []
    for doc in docs:
        score = score_document(question, doc)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        return docs[:top_k]

    return [doc for score, doc in scored[:top_k]]


def extract_relevant_excerpt(question: str, content: str, max_len: int = 1200) -> str:
    if not content:
        return ""

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    q_words = tokenize(question)

    scored_lines = []
    for line in lines:
        normalized = normalize_text(line)
        score = 0
        for word in q_words:
            if word in normalized:
                score += 1
        if score > 0:
            scored_lines.append((score, line))

    scored_lines.sort(key=lambda x: x[0], reverse=True)

    if not scored_lines:
        return content[:max_len]

    excerpt = "\n".join([line for _, line in scored_lines[:8]])
    return excerpt[:max_len]


def build_context(question: str, related_docs: list) -> str:
    blocks = []

    for doc in related_docs:
        excerpt = extract_relevant_excerpt(question, doc.get("content", ""))

        block = f"""[카테고리]
{doc.get("category", "")}

[제목]
{doc.get("title", "")}

[URL]
{doc.get("url", "")}

[관련 본문 발췌]
{excerpt}
"""
        blocks.append(block)

    return "\n\n".join(blocks)


def ask_chatbot(question: str, docs: list) -> str:
    related_docs = find_related_docs(question, docs)

    if not related_docs:
        return "현재 저장된 FAQ 데이터에서 질문과 직접 관련된 내용을 찾지 못했습니다."

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
                    "마지막 줄에 참고 URL을 적어라."
                ),
            },
            {
                "role": "user",
                "content": f"""
다음은 질문과 관련된 사하구청 문서 발췌다.

{context}

질문: {question}
"""
            },
        ],
    )

    return response.choices[0].message.content


def main():
    docs = load_data()
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
            answer = ask_chatbot(question, docs)
            print("\n답변:")
            print(answer)
            print("\n" + "-" * 50 + "\n")
        except Exception as e:
            print(f"\n오류 발생: {e}\n")


if __name__ == "__main__":
    main()