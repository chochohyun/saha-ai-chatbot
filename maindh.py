import os
import re
import json
from openai import OpenAI

# 꼭 FAQ 폴더로 맞춰
DATA_DIR = "data/faq/all"

# 새로 발급한 키로 바꿔
client = OpenAI(api_key="")
                

def load_documents():
    docs = []

    if not os.path.isdir(DATA_DIR):
        raise FileNotFoundError(f"데이터 폴더가 없음: {DATA_DIR}")

    for filename in sorted(os.listdir(DATA_DIR)):
        if filename.endswith(".json"):
            filepath = os.path.join(DATA_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            content = (data.get("content") or "").strip()
            title = (data.get("title") or "").strip()
            url = (data.get("url") or "").strip()

            if title or content:
                docs.append({
                    "title": title,
                    "url": url,
                    "content": content,
                    "filename": filename
                })

    if not docs:
        raise ValueError("문서가 없습니다. 먼저 dh.py를 실행해서 FAQ 데이터를 저장해 주세요.")

    return docs


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

    text = normalize_text(
        " ".join([
            doc.get("title", ""),
            doc.get("content", "")
        ])
    )

    score = 0
    for word in q_words:
        if word in text:
            score += 2

    # 제목 일치 가중치
    title = normalize_text(doc.get("title", ""))
    for word in q_words:
        if word in title:
            score += 3

    return score


def find_related_docs(question, docs, top_k=3):
    scored = []

    for doc in docs:
        score = score_document(question, doc)
        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)

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


def build_context(question, related_docs):
    blocks = []

    for doc in related_docs:
        excerpt = extract_relevant_excerpt(question, doc.get("content", ""))

        block = f"""[제목]
{doc.get("title", "")}

[URL]
{doc.get("url", "")}

[관련 본문 발췌]
{excerpt}
"""
        blocks.append(block)

    return "\n\n".join(blocks)


def ask_chatbot(question, docs):
    related_docs = find_related_docs(question, docs)

    if not related_docs:
        return "현재 저장된 FAQ 데이터에서 질문과 직접 관련된 내용을 찾지 못했습니다."

    context = build_context(question, related_docs)

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": (
                    "너는 사하구청 민원 안내 AI 상담사다. "
                    "반드시 제공된 문서의 발췌 내용만 근거로 답해야 한다. "
                    "문서에 있는 문장만 바탕으로 절차와 방법을 설명해라. "
                    "문서에 없는 내용은 절대 추측하지 말고, "
                    "'현재 저장된 FAQ 문서에서 확인되지 않는다'고 답해라. "
                    "링크만 던지지 말고, 문서에 실제로 있는 내용이 있으면 먼저 요약해서 설명해라."
                )
            },
            {
                "role": "user",
                "content": f"""
다음은 질문과 관련된 사하구청 FAQ 문서 발췌다.

{context}

아래 원칙으로 답해줘.
1. 문서에 실제로 있는 내용을 먼저 요약할 것
2. 절차가 있으면 순서대로 정리할 것
3. 문서에 없는 내용은 없다고 말할 것
4. 마지막 줄에 참고 URL을 적을 것

질문: {question}
"""
            }
        ]
    )

    return response.choices[0].message.content


def main():
    docs = load_documents()
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