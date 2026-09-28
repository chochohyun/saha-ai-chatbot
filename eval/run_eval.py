"""
사하구 챗봇 평가 스크립트
- calibrate 모드: 엑셀 기존 답변(기본 RAG)으로 LLM 심사 vs 사람 라벨 일치율 측정
- live 모드: 챗봇 API 직접 호출 → LLM 심사 → 사람 라벨과 비교
"""
import os
import sys
import json
import time
import argparse
import openpyxl
import httpx
from openai import OpenAI
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "..", ".env"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EXCEL_PATH = os.path.join(BASE_DIR, "챗봇_정확도_비교표 복사본.xlsx")
CHATBOT_URL = "http://localhost:8000/api/chat"

# ── LLM-as-a-Judge 프롬프트 ───────────────────────────────────────────────────
JUDGE_SYSTEM = "당신은 공정한 AI 평가 심사위원입니다. 지시사항을 엄격히 따르세요."

JUDGE_PROMPT = """\
당신은 부산광역시 사하구청 AI 민원 챗봇의 답변을 평가합니다.

[질문]
{question}

[챗봇 답변]
{answer}

위 답변이 질문에 대해 정확하고 유용한 정보를 제공했는지 판단하세요.

판단 기준:
- 질문의 핵심 내용에 실질적으로 답했는가?
- 사하구 민원/행정 서비스 정보를 올바르게 안내했는가?
- 틀린 정보나 무관한 내용으로 답하지 않았는가?
- "모르겠다", "안내 어렵다" 등 답변 회피를 정답으로 보지 말 것

반드시 아래 형식으로만 답변하세요 (다른 말 없이):
판정: 정답
이유: (1~2문장)

또는

판정: 오답
이유: (1~2문장)\
"""


def llm_judge(question: str, answer: str) -> dict:
    """LLM-as-a-Judge: 답변 채점 → {"verdict", "correct", "reason"}"""
    resp = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": JUDGE_PROMPT.format(question=question, answer=answer)},
        ],
        temperature=0,
    )
    raw = resp.choices[0].message.content.strip()
    is_correct = raw.startswith("판정: 정답")
    # 이유 추출
    reason = ""
    for line in raw.splitlines():
        if line.startswith("이유:"):
            reason = line.replace("이유:", "").strip()
    return {"verdict": "정답" if is_correct else "오답", "correct": is_correct, "reason": reason, "raw": raw}


def call_chatbot(question: str, timeout: int = 60) -> str:
    """챗봇 API SSE 스트리밍 호출 → 전체 답변 문자열 반환"""
    full = []
    try:
        with httpx.stream(
            "POST", CHATBOT_URL,
            json={"message": question, "history": []},
            timeout=timeout,
        ) as r:
            for line in r.iter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if "delta" in data:
                            full.append(data["delta"])
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        return f"[API 호출 오류: {e}]"
    return "".join(full)


def load_eval_data() -> list[dict]:
    """엑셀에서 평가 데이터 로드 (사람 라벨 있는 50개)"""
    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(min_row=2, max_row=51, values_only=True):
        no, q_type, question, basic_ans, basic_label, hybrid_ans, hybrid_label, note = row
        if not question:
            continue
        if basic_label not in ("✅ 정답", "❌ 오답/모름"):
            continue
        rows.append({
            "no": int(no) if no else len(rows) + 1,
            "type": q_type or "",
            "question": question,
            "basic_answer": basic_ans or "",
            "hybrid_answer": hybrid_ans or "",
            "human_label": basic_label,
            "human_correct": basic_label == "✅ 정답",
        })
    return rows


# ── 실행 모드 ─────────────────────────────────────────────────────────────────

def run_calibrate(rows: list[dict]) -> list[dict]:
    """기존 기본 RAG 답변 → LLM 심사 → 사람 라벨과 비교"""
    results = []
    for i, row in enumerate(rows, 1):
        print(f"  [{i:02d}/{len(rows)}] {row['question'][:40]}")
        judge = llm_judge(row["question"], row["basic_answer"])
        results.append({
            **row,
            "mode": "calibrate",
            "evaluated_answer": row["basic_answer"],
            "judge_verdict": judge["verdict"],
            "judge_correct": judge["correct"],
            "judge_reason": judge["reason"],
            "match": judge["correct"] == row["human_correct"],
        })
        time.sleep(0.3)
    return results


def run_live(rows: list[dict]) -> list[dict]:
    """챗봇 라이브 호출 → LLM 심사 → 사람 라벨과 비교"""
    results = []
    for i, row in enumerate(rows, 1):
        print(f"  [{i:02d}/{len(rows)}] {row['question'][:40]}")
        chatbot_ans = call_chatbot(row["question"])
        judge = llm_judge(row["question"], chatbot_ans)
        results.append({
            **row,
            "mode": "live",
            "evaluated_answer": chatbot_ans,
            "judge_verdict": judge["verdict"],
            "judge_correct": judge["correct"],
            "judge_reason": judge["reason"],
            "match": judge["correct"] == row["human_correct"],
        })
        time.sleep(0.5)
    return results


# ── 보고서 출력 ───────────────────────────────────────────────────────────────

def print_report(results: list[dict], mode: str) -> dict:
    total = len(results)
    agree = sum(1 for r in results if r["match"])
    tp = sum(1 for r in results if r["human_correct"] and r["judge_correct"])
    tn = sum(1 for r in results if not r["human_correct"] and not r["judge_correct"])
    fp = sum(1 for r in results if not r["human_correct"] and r["judge_correct"])
    fn = sum(1 for r in results if r["human_correct"] and not r["judge_correct"])

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    cohen_kappa = compute_kappa(tp, tn, fp, fn, total)

    print(f"\n{'='*55}")
    print(f"  LLM-as-a-Judge 평가 보고서 [{mode}]")
    print(f"{'='*55}")
    print(f"  총 문항        : {total}")
    print(f"  사람-LLM 일치  : {agree}/{total}  ({agree/total*100:.1f}%)")
    print(f"  Cohen's κ      : {cohen_kappa:.3f}  (0.6↑ 신뢰 가능)")
    print()
    print(f"  혼동 행렬")
    print(f"    TP (둘 다 정답)        : {tp:2d}")
    print(f"    TN (둘 다 오답)        : {tn:2d}")
    print(f"    FP (사람=오답, LLM=정답): {fp:2d}  ← LLM이 너무 관대")
    print(f"    FN (사람=정답, LLM=오답): {fn:2d}  ← LLM이 너무 엄격")
    print()
    print(f"  Precision : {precision:.3f}")
    print(f"  Recall    : {recall:.3f}")
    print(f"  F1        : {f1:.3f}")

    disagree = [r for r in results if not r["match"]]
    if disagree:
        print(f"\n  ── 불일치 케이스 ({len(disagree)}개) ──")
        for r in disagree:
            direction = "LLM↑관대" if (not r["human_correct"] and r["judge_correct"]) else "LLM↓엄격"
            print(f"  [{r['no']:02d}] [{direction}] {r['question'][:45]}")
            print(f"       사람={r['human_label']}  LLM={r['judge_verdict']}")
            print(f"       이유: {r['judge_reason']}")
    print(f"{'='*55}\n")

    return {
        "total": total, "agree": agree, "agree_pct": round(agree/total*100, 1),
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "precision": round(precision, 3), "recall": round(recall, 3),
        "f1": round(f1, 3), "cohen_kappa": round(cohen_kappa, 3),
    }


def compute_kappa(tp, tn, fp, fn, total) -> float:
    """Cohen's Kappa 계산"""
    if total == 0:
        return 0.0
    po = (tp + tn) / total
    p_pos = ((tp + fp) / total) * ((tp + fn) / total)
    p_neg = ((fn + tn) / total) * ((fp + tn) / total)
    pe = p_pos + p_neg
    return (po - pe) / (1 - pe) if pe < 1 else 0.0


# ── 엔트리포인트 ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="사하구 챗봇 LLM-as-a-Judge 평가")
    parser.add_argument(
        "--mode",
        choices=["calibrate", "live"],
        default="calibrate",
        help=(
            "calibrate: 엑셀 기존 답변으로 LLM 심사 보정 검증 (API 불필요)\n"
            "live: 챗봇 API 직접 호출 후 LLM 심사 (서버 실행 필요)"
        ),
    )
    parser.add_argument(
        "--output",
        default=os.path.join(BASE_DIR, "results.json"),
        help="결과 JSON 저장 경로",
    )
    args = parser.parse_args()

    print(f"\n[사하구 챗봇 평가] 모드: {args.mode}")
    rows = load_eval_data()
    print(f"평가 데이터 로드: {len(rows)}개\n")

    if args.mode == "calibrate":
        print("기존 기본 RAG 답변으로 LLM 심사 보정 검증 중...")
        results = run_calibrate(rows)
    else:
        print(f"챗봇 API 호출 중 ({CHATBOT_URL})...")
        results = run_live(rows)

    stats = print_report(results, args.mode)

    output = {
        "mode": args.mode,
        "stats": stats,
        "results": [
            {k: v for k, v in r.items() if k != "basic_answer" or args.mode == "calibrate"}
            for r in results
        ],
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"상세 결과 저장: {args.output}")


if __name__ == "__main__":
    main()
