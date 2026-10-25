# 사하루 — 사하구청 AI 민원 챗봇

부산광역시 사하구청 공식 민원 정보를 자연어로 안내하는 AI 챗봇입니다.
구청 웹사이트에서 수집한 실제 데이터를 기반으로 하이브리드 RAG(검색증강생성) 방식으로 답변합니다.

---

## 주요 기능

- **하이브리드 검색** — BM25(키워드) + 벡터 임베딩(의미) 결합으로 관련 문서 검색
- **증분 크롤링** — 최초 1회 전수 수집 후, 변경·신규 페이지만 자동 감지·재수집 (매일 새벽 1시)
- **대화 세션 관리** — 대화 이력 저장·조회, 이전 문맥 유지
- **피드백 시스템** — 답변별 좋아요/싫어요, 관리자 통계 확인
- **SSE 스트리밍** — 챗GPT처럼 답변이 실시간으로 타이핑되며 출력
- **다크모드 / 글자 크기** — 사용자 환경 설정 localStorage 저장

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
├── backend/                  # FastAPI 백엔드
│   ├── main.py               # 앱 진입점. API 라우트, RAG 파이프라인 초기화, 스케줄러 시작
│   ├── crawler.py            # 사하구청 웹사이트 크롤러 (전수 수집)
│   ├── incremental_crawl.py  # 증분 크롤링 — 변경/신규 페이지 감지 및 재수집
│   ├── scheduler.py          # APScheduler 설정 (매일 01:00 KST 증분 크롤링 실행)
│   ├── database.py           # SQLAlchemy 엔진 및 세션 설정
│   ├── models.py             # DB 테이블 정의 (세션, 메시지, 크롤링 상태, 실행 이력)
│   ├── schemas.py            # Pydantic 스키마
│   ├── rag/                  # 모듈형 RAG 파이프라인
│   │   ├── pipeline.py       # 파이프라인 오케스트레이터 (검색 → 재랭킹 → 생성)
│   │   ├── retriever.py      # 하이브리드 검색기 (BM25 + 벡터 임베딩)
│   │   ├── reranker.py       # Cross-encoder 재랭킹 (선택적)
│   │   ├── generator.py      # GPT-4.1 기반 답변 생성 (스트리밍)
│   │   ├── query_processor.py# 쿼리 전처리 및 확장
│   │   └── config.py         # 파이프라인 설정값
│   └── routers/
│       └── chat_history.py   # 대화 세션 CRUD API (/api/sessions, /api/messages)
│
├── frontend/                 # Next.js 프론트엔드
│   └── app/
│       ├── page.tsx          # 메인 페이지 — 상태 관리, API 연동, SSE 스트리밍
│       ├── layout.tsx        # 루트 레이아웃 (폰트, 전역 스타일)
│       ├── types.ts          # 공용 TypeScript 타입 정의
│       └── components/
│           ├── ChatSidebar.tsx       # 사이드바 (새 대화, 최근 문의 내역, 콜센터)
│           ├── WelcomeSection.tsx    # 웰컴 화면 (카드 6개 + 예시 질문 칩)
│           ├── ChatHeader.tsx        # 헤더 (다크모드, 글자크기, 모바일 메뉴)
│           ├── ChatInput.tsx         # 입력창 (텍스트, 음성 입력)
│           ├── ChatMessageList.tsx   # 메시지 목록 스크롤 영역
│           ├── ChatMessageItem.tsx   # 개별 메시지 (마크다운, 출처, 피드백)
│           └── FeedbackAdminModal.tsx# 관리자 전용 피드백 통계 모달
│
├── data/                     # 크롤링된 민원 데이터 (JSON, 카테고리별 디렉토리)
│   ├── faq/                  # 자주 묻는 질문
│   ├── 여권민원안내/          # 여권 발급 안내
│   ├── 세무민원안내/          # 세금 관련 민원
│   ├── 아동/                 # 아동 복지 서비스
│   ├── 노인복지/              # 노인 복지 서비스
│   ├── 장애인/               # 장애인 복지 서비스
│   ├── 복지정책/              # 일반 복지 정책
│   ├── 1인가구/               # 1인가구 지원
│   ├── 여성가족/              # 여성·가족 서비스
│   ├── environment_cleaning/ # 환경·청소 민원
│   └── ...                   # 총 16개 카테고리, 약 277개 문서
│
├── tests/
│   └── test_incremental.py   # 증분 크롤링 단위 테스트 (9개)
├── eval/
│   └── run_eval.py           # RAG 정확도 평가 스크립트
├── logs/
│   └── incremental_crawl.log # 증분 크롤링 실행 로그
└── requirements.txt          # Python 의존성 목록
```

---

## 시작하기

### 사전 준비

- Python 3.11+
- Node.js 18+
- OpenAI API Key

### 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다.

```
OPENAI_API_KEY=sk-...
ADMIN_API_KEY=your-secret-admin-key   # 관리자 엔드포인트 보호 (선택)
```

### 백엔드 실행

```bash
# 1. 가상환경 생성 및 패키지 설치
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. 서버 실행
uvicorn backend.main:app --reload
# → http://localhost:8000
```

### 프론트엔드 실행

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

### 증분 크롤링 (변경·신규 페이지만 재수집)

```bash
# 1. 최초 1회 해시 초기화 (페이지를 실제로 가져와 기준 해시 저장)
python -m backend.incremental_crawl --seed

# 실행 확인 (오탐 0건 검증)
python -m backend.incremental_crawl --limit 10

# 2. 이후 증분 실행 (변경된 페이지만 재수집)
python -m backend.incremental_crawl
```

#### 동작 방식

1. **신규 URL 발견** — sitemap.xml 조회 → 없으면 기존 게시판 목록 1페이지에서 탐색
2. **변경 감지** — 페이지 본문을 정규화(동적 요소·네비 제거)한 뒤 SHA-256 해시 비교
3. **재수집 판단** — 해시가 없으면 "신규", 다르면 "변경", 같으면 스킵
4. **인덱스 재로드** — 변경이 있으면 임베딩 캐시 무효화 후 서버 재시작 없이 인메모리 인덱스 교체
5. **자동 스케줄** — APScheduler가 매일 새벽 01:00 KST에 자동 실행

#### 수동 인덱스 재로드 (서버 실행 중)

```bash
curl -X POST http://localhost:8000/admin/reload-index \
  -H "X-Admin-Key: your-secret-admin-key"
```

### 실행 이력 조회

```bash
curl "http://localhost:8000/admin/crawl-runs?limit=5" \
  -H "X-Admin-Key: your-secret-admin-key"
```

```json
[
  {
    "id": 3,
    "started_at": "2026-10-25T01:00:00+00:00",
    "checked_urls": 277,
    "new_count": 2,
    "changed_count": 1,
    "failed_count": 0,
    "duration_sec": 312.4
  }
]
```

---

## 테스트

```bash
python -m pytest tests/test_incremental.py -v
```

| 테스트 | 내용 |
|---|---|
| `test_new_url` | 해시 없음 → 신규 판정 |
| `test_changed_url` | 해시 불일치 → 변경 판정 |
| `test_unchanged_url` | 해시 일치 → 스킵 |
| `test_seed_then_run_zero_false_positives` | seed 직후 실행 시 오탐 0건 |
| `test_sitemap_url_discovery` | sitemap.xml 파싱 정확성 |
| `test_sitemap_unavailable_returns_empty` | sitemap 없을 때 빈 리스트 반환 |

---

## API 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| `POST` | `/api/chat` | 채팅 메시지 전송 (SSE 스트리밍) |
| `GET` | `/api/sessions` | 대화 세션 목록 |
| `GET` | `/api/sessions/{id}/messages` | 특정 세션 메시지 이력 |
| `POST` | `/api/messages/{id}/feedback` | 메시지 피드백 저장 |
| `GET` | `/admin/crawl-runs` | 증분 크롤링 실행 이력 (인증 필요) |
| `POST` | `/admin/reload-index` | 서버 재시작 없이 인덱스 재로드 (인증 필요) |

---

## 알려진 한계

- 본문 해시 기반 변경 감지이므로 동적 요소(조회수 등)를 제거해도 오탐이 완전히 사라지지 않을 수 있습니다.
- 증분 크롤링 시 신규 URL은 해시 계산 + 본문 수집으로 HTTP 요청이 2회 발생합니다.
- `/admin/reload-index` 호출 시 임베딩 캐시가 없으면 OpenAI API 재호출로 수 분 소요될 수 있습니다.
- APScheduler는 단일 uvicorn 워커 기준입니다. 다중 워커 환경에서는 시스템 cron 사용을 권장합니다.
