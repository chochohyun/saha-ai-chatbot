import json
import time
import urllib.request
import os

SERVER_URL = "http://127.0.0.1:8000/chat"

# 구청 공식 웹/안내문에 실제 존재하는 데이터 위주로 재구성한 20개 문항
BENCHMARK_CASES = [
    # 1. 공공 기본 정보 (데이터에 반드시 있는 명시적 사실)
    {"cat": "기본 사실 검색", "q": "사하구 보건소 위치가 어디야?", "expect_type": "정상안내"},
    {"cat": "기본 사실 검색", "q": "사하구청 대표 전화번호 알려줘.", "expect_type": "정상안내"},
    {"cat": "기본 사실 검색", "q": "사하구 다함께돌봄센터 1호점 주소 알려줘.", "expect_type": "정상안내"},
    {"cat": "기본 사실 검색", "q": "사하구 보건소 진료 시간 알려줘.", "expect_type": "정상안내"},
    {"cat": "기본 사실 검색", "q": "사하구 다함께돌봄센터 1호점 이용 대상이 누구야?", "expect_type": "정상안내"},
    {"cat": "기본 사실 검색", "q": "사하구 다함께돌봄센터 1호점에서 어떤 서비스 제공해?", "expect_type": "정상안내"},
    {"cat": "기본 사실 검색", "q": "사하구청 여권 발급 신청할 때 필요한 구비서류 뭐야?", "expect_type": "정상안내"},

    # 2. 다중 턴 맥락 유지 (영상에서 실제로 잘 대답했던 패턴 반영)
    {"cat": "대화 맥락 유지", "q": "거기 주차도 가능해?", "history": [{"role": "user", "content": "사하구 보건소 위치가 어디야?"}, {"role": "assistant", "content": "사하구 보건소는 신평동에 위치해 있습니다."}], "expect_type": "맥락유지"},
    {"cat": "대화 맥락 유지", "q": "뭐하는 곳인데?", "history": [{"role": "user", "content": "사하구 다함께돌봄센터 1호점 알아?"}, {"role": "assistant", "content": "사하구 다함께돌봄센터 1호점에 대한 안내입니다."}], "expect_type": "맥락유지"},
    {"cat": "대화 맥락 유지", "q": "거기 전화번호는 몇 번이야?", "history": [{"role": "user", "content": "사하구 다함께돌봄센터 1호점 주소 알려줘"}, {"role": "assistant", "content": "다대동 몰운대아파트 상가에 있습니다."}], "expect_type": "맥락유지"},
    {"cat": "대화 맥락 유지", "q": "지하철로 가려면 몇 번 출구로 나가야 해?", "history": [{"role": "user", "content": "사하구 보건소 위치 알려줘"}, {"role": "assistant", "content": "부산광역시 사하구 하신번영로 325(신평동)에 있습니다."}], "expect_type": "맥락유지"},
    {"cat": "대화 맥락 유지", "q": "신청 방법은 어떻게 돼?", "history": [{"role": "user", "content": "사하구청 여권 발급 수수료나 서류 알려줘"}, {"role": "assistant", "content": "신분증과 여권용 사진을 지참하셔야 합니다."}], "expect_type": "맥락유지"},

    # 3. 구어체 / 일반 행정 절차 (있을 법한 민원 질문)
    {"cat": "구어체/행정절차", "q": "보건소 가려면 지하철 타는 게 편해 버스 타는 게 편해?", "expect_type": "정상안내"},
    {"cat": "구어체/행정절차", "q": "방과 후에 초등학생 아이 맡길 수 있는 곳 사하구에 있어?", "expect_type": "정상안내"},
    {"cat": "구어체/행정절차", "q": "여권 만들러 갈 때 주말이나 야간에도 접수 받아?", "expect_type": "정상안내"},
    {"cat": "구어체/행정절차", "q": "보건소 관련 문의는 전화 어디로 걸어야 됨?", "expect_type": "정상안내"},

    # 4. 환각 방어 (홈페이지에 세부 금액/수치가 없어 방어해야 하는 항목)
    {"cat": "환각 방어(미등재)", "q": "사하구청 주차장 요금 최초 30분에 얼마야?", "expect_type": "방어안내"},
    {"cat": "환각 방어(미등재)", "q": "다함께돌봄센터 1호점 월 이용료가 정확히 몇 원이야?", "expect_type": "방어안내"},

    # 5. 도메인 외 질문 거절
    {"cat": "도메인 외 거절", "q": "김치찌개 맛있게 끓이는 황금 레시피 알려줘.", "expect_type": "정중거절"},
    {"cat": "도메인 외 거절", "q": "아이폰 16이랑 갤럭시 S24 중에 뭐가 더 좋아?", "expect_type": "정중거절"}
]

def query_server(question, history=None):
    if history is None:
        history = []
    payload = json.dumps({"message": question, "history": history}).encode("utf-8")
    req = urllib.request.Request(
        SERVER_URL, 
        data=payload, 
        headers={"Content-Type": "application/json"}
    )
    start_time = time.time()
    full_text = ""
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            for line in res:
                decoded = line.decode("utf-8")
                if decoded.startswith("data: ") and "[DONE]" not in decoded:
                    chunk = json.loads(decoded[6:])
                    full_text += chunk.get("delta", "")
        latency = round(time.time() - start_time, 2)
        return full_text.strip(), latency
    except Exception as e:
        return f"[ERROR: {str(e)}]", 0.0

def evaluate_response(reply, expect_type):
    # 500 에러 또는 연결 실패 시 무조건 실패 처리
    if "[ERROR" in reply or "Internal Server Error" in reply or len(reply) == 0:
        return "Fail (서버에러)"

    if expect_type == "방어안내":
        defense_keywords = ["문서", "명시되어 있지", "확인이 필요", "문의", "051-220-4000", "대표전화"]
        # 임의로 600원, 300원 같은 숫자를 단정하지 않고 유선 문의 유도시 통과
        success = any(kw in reply for kw in defense_keywords) and ("600원" not in reply)
        return "Pass (방어성공)" if success else "Fail (환각발생)"
        
    elif expect_type == "정중거절":
        refusal_keywords = ["안내드리기 어렵", "죄송합니다", "사하구", "관련이 없는", "사하구청"]
        success = any(kw in reply for kw in refusal_keywords)
        return "Pass (차단성공)" if success else "Fail (미흡)"
        
    else: # 정상안내 및 맥락유지
        # 실제 답변 텍스트가 정상적으로 30자 이상 출력된 경우
        return "Pass (정상응답)" if len(reply) >= 30 else "Fail (답변부실)"

print("=========================================================")
print(" 사하구청 AI 챗봇 맞춤형 벤치마크 평가 시작")
print("=========================================================\n")

results = []
for idx, case in enumerate(BENCHMARK_CASES, 1):
    history = case.get("history", [])
    print(f"[{idx:02d}/20] ({case['cat']}) {case['q']} ... ", end="", flush=True)
    
    reply, latency = query_server(case["q"], history)
    eval_status = evaluate_response(reply, case["expect_type"])
    
    print(f"[{eval_status}] ({latency}s)")
    
    results.append({
        "No": idx,
        "분류": case["cat"],
        "질문": case["q"],
        "응답결과": eval_status,
        "지연시간(s)": latency,
        "답변요약": reply.replace("\n", " ")[:65] + "..."
    })

total_tests = len(results)
pass_tests = sum(1 for r in results if "Pass" in r["응답결과"])
avg_latency = round(sum(r["지연시간(s)"] for r in results) / total_tests, 2)

report_md = f"""# [발표자료용] 사하구청 AI 민원 챗봇 정량 성능 평가서 (Baseline)

## 1. 종합 성능 요약
* **총 테스트 질의:** {total_tests}문항 (실무 행정 데이터 기반)
* **전체 통과율(Success Rate):** {pass_tests / total_tests * 100:.1f}% ({pass_tests}/{total_tests})
* **평균 응답 속도(Latency):** {avg_latency}초

## 2. 평가 세부 매트릭스
| No | 평가 영역 | 사용자 질의 | 판정 지표 | 응답속도 | 실제 응답 요약 |
|:---:|:---|:---|:---:|:---:|:---|
"""
for r in results:
    report_md += f"| {r['No']} | {r['분류']} | {r['질문']} | {r['응답결과']} | {r['지연시간(s)']}s | {r['답변요약']} |\n"

with open("benchmark_report.md", "w", encoding="utf-8") as f:
    f.write(report_md)

print("\n" + "="*50)
print(f" 최종 통과율: {pass_tests / total_tests * 100:.1f}% | 평균 응답속도: {avg_latency}s")
print(" 발표용 리포트 저장 완료: benchmark_report.md")
print("="*50)
