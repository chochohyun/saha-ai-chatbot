# 사하루 — 사하구청 AI 민원 챗봇

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)
![OpenAI](https://img.shields.io/badge/GPT--4.1-OpenAI-412991?logo=openai&logoColor=white)

> 부산광역시 사하구청 민원 정보를 자연어로 안내하는 RAG 기반 AI 챗봇

---

## 프로젝트 소개

사하구청 홈페이지에는 복지, 세무, 여권, 환경 등 수백 개의 민원 안내 페이지가 흩어져 있습니다.
원하는 정보를 찾으려면 여러 메뉴를 탐색해야 하고, 검색 결과도 정확하지 않은 경우가 많습니다.

**사하루**는 이 문제를 해결하기 위해 만든 AI 민원 안내 서비스입니다.
구청 웹사이트 전체를 크롤링해 문서 데이터베이스를 구성하고,
사용자의 질문에 가장 관련 있는 문서를 검색해 GPT-4.1이 자연어로 답변합니다.

단순 키워드 매칭이 아닌 **하이브리드 RAG** 방식을 사용합니다.
BM25(키워드 검색)과 벡터 임베딩(의미 검색)을 결합해 두 방식의 장점을 모두 취합니다.
데이터는 매일 새벽 자동으로 갱신되어, 구청 홈페이지가 바뀌어도 챗봇이 최신 정보를 유지합니다.

---

## 동작 흐름

```
사하구청 웹사이트
      │
      ▼
  crawler.py          ← 최초 1회 전수 수집
  incremental_crawl.py ← 이후 변경·신규 페이지만 자동 감지 (매일 01:00 KST)
      │
      ▼
  data/ (JSON)        ← 카테고리별 문서 저장 (16개 분류, 약 277개 문서)
      │
      ▼
  RAG Pipeline
  ├─ Retriever  : BM25 + 벡터 임베딩 하이브리드 검색
  ├─ Reranker   : Cross-encoder 기반 정밀 재랭킹 (선택)
  └─ Generator  : GPT-4.1 스트리밍 답변 생성
      │
      ▼
  FastAPI (SSE)       ← 실시간 스트리밍 응답
      │
      ▼
  Next.js 챗봇 UI     ← 사용자 대화
```

---

## 주요 기능

| 기능 | 설명 |
|---|---|
| 하이브리드 RAG | BM25 + 벡터 임베딩 결합으로 키워드·의미 검색을 동시에 수행 |
| 증분 크롤링 | 전수 수집 이후 변경·신규 페이지만 자동 재수집 (해시 비교) |
| 실시간 스트리밍 | SSE 방식으로 답변이 타이핑되며 출력 |
| 대화 세션 | 대화 이력 저장·조회, 이전 맥락 유지 |
| 피드백 시스템 | 답변별 좋아요/싫어요, 관리자 통계 확인 |
| 다크모드·글자 크기 | 사용자 환경설정 localStorage 저장 |

---

## 기술 스택

| 영역 | 스택 |
|---|---|
| 백엔드 | Python 3.11, FastAPI, SQLAlchemy, SQLite |
| AI / 검색 | OpenAI GPT-4.1, text-embedding-3-small, BM25Okapi |
| 프론트엔드 | Next.js 16 (App Router), TypeScript, Tailwind CSS |
| 스케줄링 | APScheduler (KST 기준 매일 01:00) |
| 크롤링 | requests, BeautifulSoup4 |

---

## 프로젝트 구조

```
saha-ai-chatbot/
├── backend/
│   ├── main.py               # 앱 진입점 — API 라우트, RAG 파이프라인, 스케줄러 시작
│   ├── crawler.py            # 사하구청 전수 크롤러
│   ├── incremental_crawl.py  # 증분 크롤링 — 변경/신규 페이지 감지·재수집
│   ├── scheduler.py          # APScheduler 설정 (매일 01:00 KST)
│   ├── database.py           # SQLAlchemy 엔진 및 세션
│   ├── models.py             # DB 테이블 (세션, 메시지, 크롤링 상태, 실행 이력)
│   ├── schemas.py            # Pydantic 스키마
│   ├── rag/
│   │   ├── pipeline.py       # 파이프라인 오케스트레이터 (검색 → 재랭킹 → 생성)
│   │   ├── retriever.py      # 하이브리드 검색기 (BM25 + 벡터)
│   │   ├── reranker.py       # Cross-encoder 재랭킹
│   │   ├── generator.py      # GPT-4.1 스트리밍 답변 생성
│   │   ├── query_processor.py# 쿼리 전처리·확장
│   │   └── config.py         # 파이프라인 설정
│   └── routers/
│       └── chat_history.py   # 대화 세션 CRUD API
│
├── frontend/
│   └── app/
│       ├── page.tsx          # 메인 페이지 — 상태 관리, API 연동, SSE 처리
│       ├── layout.tsx        # 루트 레이아웃
│       ├── types.ts          # 공용 TypeScript 타입
│       └── components/
│           ├── ChatSidebar.tsx       # 사이드바 (새 대화, 최근 문의, 콜센터)
│           ├── WelcomeSection.tsx    # 웰컴 화면 (카테고리 카드 + 예시 질문 칩)
│           ├── ChatHeader.tsx        # 헤더 (다크모드, 글자 크기, 모바일 메뉴)
│           ├── ChatInput.tsx         # 입력창 (텍스트 + 음성 입력)
│           ├── ChatMessageList.tsx   # 메시지 목록
│           ├── ChatMessageItem.tsx   # 개별 메시지 (마크다운, 출처, 피드백)
│           └── FeedbackAdminModal.tsx# 관리자 피드백 통계 모달
│
├── data/                     # 크롤링 결과 (16개 카테고리, 약 277개 JSON 문서)
├── tests/
│   └── test_incremental.py   # 증분 크롤링 단위 테스트 (9개)
├── eval/
│   └── run_eval.py           # RAG 정확도 평가 스크립트
├── logs/
│   └── incremental_crawl.log # 증분 크롤링 실행 로그
└── requirements.txt
```

---

## 시작하기

### 사전 준비

- Python 3.11+
- Node.js 18+
- OpenAI API Key

### 환경 변수

프로젝트 루트에 `.env` 파일을 만듭니다.

```env
OPENAI_API_KEY=sk-...
ADMIN_API_KEY=your-secret-key    # 관리자 엔드포인트 보호 (선택)
```

### 백엔드

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

uvicorn backend.main:app --reload
# → http://localhost:8000
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## 데이터 수집

### 최초 전수 크롤링

```bash
python backend/crawler.py
```

### 증분 크롤링

최초 1회 전수 수집 이후, 변경·신규 페이지만 재수집합니다.

```bash
# 기준 해시 초기화 (최초 1회, 실제 페이지 fetch 필요)
python -m backend.incremental_crawl --seed

# 이후 증분 실행 (변경된 페이지만 재수집)
python -m backend.incremental_crawl

# 일부만 빠르게 테스트
python -m backend.incremental_crawl --limit 10
```

**증분 크롤링 동작 방식**

1. sitemap.xml 조회 → 없으면 게시판 목록 1페이지에서 신규 URL 탐색
2. 페이지 본문을 정규화(동적 요소·네비게이션 제거)한 뒤 SHA-256 해시 계산
3. 저장된 해시와 비교 → 없으면 "신규", 다르면 "변경", 같으면 스킵
4. 신규·변경 문서만 파싱·임베딩해 인메모리 인덱스에 반영
5. 서버가 실행 중이라면 재시작 없이 인덱스를 즉시 교체

스케줄러가 매일 새벽 01:00 KST에 자동으로 위 과정을 실행합니다.

**수동 인덱스 재로드**

```bash
curl -X POST http://localhost:8000/admin/reload-index \
  -H "X-Admin-Key: your-secret-key"
```

**크롤링 실행 이력 조회**

```bash
curl "http://localhost:8000/admin/crawl-runs?limit=5" \
  -H "X-Admin-Key: your-secret-key"
```

---

## API

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/api/chat` | 채팅 전송 (SSE 스트리밍) |
| `GET` | `/api/sessions` | 대화 세션 목록 |
| `GET` | `/api/sessions/{id}/messages` | 세션 메시지 이력 |
| `POST` | `/api/messages/{id}/feedback` | 피드백 저장 |
| `GET` | `/admin/crawl-runs` | 크롤링 실행 이력 (인증 필요) |
| `POST` | `/admin/reload-index` | 인메모리 인덱스 재로드 (인증 필요) |

---

## 테스트

```bash
python -m pytest tests/test_incremental.py -v
```

---

## 알려진 한계

- 본문 해시 기반 변경 감지라 동적 요소를 제거해도 오탐이 완전히 없어지지 않을 수 있습니다.
- 신규 URL은 해시 계산 + 본문 수집으로 HTTP 요청이 2회 발생합니다.
- 임베딩 캐시가 없을 때 `/admin/reload-index` 호출 시 OpenAI API 재호출로 수 분 소요될 수 있습니다.
- APScheduler는 단일 uvicorn 워커 기준이며, 다중 워커 환경에서는 시스템 cron 사용을 권장합니다.
