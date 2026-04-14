import os
import json
from openai import OpenAI

# 새로 발급받은 키로 바꿔 넣기
client = OpenAI(api_key="")
DATA_DIR = "data/여권민원안내/all"

def load_documents():
    docs = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(DATA_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                docs.append(data)
    return docs

def find_related_docs(question, docs):
    # 아주 단순한 방식: 질문 단어가 content/title에 들어가면 관련 문서로 선택
    related = []
    for doc in docs:
        text = (doc.get("title", "") + " " + doc.get("content", "")).lower()
        if any(word in text for word in question.lower().split()):
            related.append(doc)

    # 아무것도 못 찾으면 앞에서 3개 정도만 사용
    if not related:
        related = docs[:3]

    return related[:3]

def build_context(related_docs):
    context_parts = []
    for doc in related_docs:
        context_parts.append(
            f"""[제목]
{doc.get("title", "")}

[URL]
{doc.get("url", "")}

[본문]
{doc.get("content", "")}
"""
        )
    return "\n\n".join(context_parts)

def main():
    docs = load_documents()
    print("사하구청 AI 민원 상담 시작 (종료하려면 exit 입력)\n")

    while True:
        question = input("질문: ").strip()

        if question.lower() == "exit":
            print("상담 종료")
            break

        if not question:
            print("질문을 입력해줘.\n")
            continue

        related_docs = find_related_docs(question, docs)
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
                    "content": f"""
다음은 사하구청 관련 문서들이다.

{context}

위 문서만 바탕으로 아래 질문에 답해줘.
- 질문한 내용에만 답할 것
- 쉬운 말로 설명할 것
- 마지막에 관련 URL이 있으면 함께 안내할 것

질문: {question}
"""
                }
            ]
        )

        print("\n답변:")
        print(response.choices[0].message.content)
        print("\n" + "-" * 50 + "\n")

if __name__ == "__main__":
    main()