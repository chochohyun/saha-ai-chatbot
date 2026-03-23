from openai import OpenAI

# 새로 발급받은 키로 바꿔 넣기
client = OpenAI(api_key="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")

# 문서 불러오기
docs = {
    "전입신고": open("docs/move.txt", encoding="utf-8").read(),
    "대형폐기물": open("docs/trash.txt", encoding="utf-8").read()
}

print("사하구청 AI 민원 상담 시작 (종료하려면 exit 입력)\n")

while True:
    # 질문 받기
    question = input("질문: ").strip()

    # 종료
    if question.lower() == "exit":
        print("상담을 종료합니다.")
        break

    # 빈 입력 방지
    if not question:
        print("질문을 입력해줘.\n")
        continue

    # 간단한 검색
    selected_doc = ""
    for key in docs:
        if key in question:
            selected_doc = docs[key]
            break

    # 아무것도 못 찾았을 때 전체 문서 사용
    if selected_doc == "":
        selected_doc = "\n\n".join(docs.values())

    # AI에게 질문
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": (
                    "너는 사하구청 민원 안내 AI 상담사다. "
                    "반드시 제공된 정보만 바탕으로 답하고, "
                    "사용자가 질문한 내용에만 간단하고 직접적으로 답해. "
                    "문서 전체를 요약하지 말고, 질문과 관련된 부분만 설명해."
                )
            },
            {
                "role": "user",
                "content": f"""
다음은 전입신고 관련 안내문이다.

{selected_doc}

위 정보만 바탕으로 아래 질문에 답해줘.
- 질문한 내용에만 답할 것
- 불필요하게 전체 내용을 전부 설명하지 말 것
- 모르면 모른다고 할 것

질문: {question}
"""
            }
        ]
    )

    print("\n답변:")
    print(response.choices[0].message.content)
    print("\n" + "-" * 50 + "\n")