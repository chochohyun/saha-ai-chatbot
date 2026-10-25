"""
증분 크롤링 모듈 (v2)
────────────────────
• 해시 기준 통일: seed / 정상 실행 모두 _extract_page_hash() 사용 → 오탐 0
• 동적 요소 제거: 조회수·날짜·댓글 수 셀렉터를 추출 전 decompose
• 신규 URL 발견: sitemap.xml → 실패 시 게시판 목록 1페이지 폴백
• reload_callback 지원: 인덱스 재로드를 외부에서 주입

사용법
------
  # 최초 해시 초기화 (네트워크 필요, JSON 갱신 없음)
  python -m backend.incremental_crawl --seed

  # 증분 실행
  python -m backend.incremental_crawl

  # URL 수 제한 (데모용)
  python -m backend.incremental_crawl --limit 10
"""

import argparse
import hashlib
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
CACHE_FILE = os.path.join(DATA_DIR, "embeddings_cache.json")
INCREMENTAL_SAVE_DIR = os.path.join(DATA_DIR, "incremental", "all")
LOG_DIR = os.path.join(BASE_DIR, "..", "logs")
SITEMAP_URL = "https://www.saha.go.kr/sitemap.xml"
os.makedirs(LOG_DIR, exist_ok=True)

# ── 로거 ─────────────────────────────────────────────────────────────────────
logger = logging.getLogger("incremental_crawl")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh = logging.FileHandler(
        os.path.join(LOG_DIR, "incremental_crawl.log"), encoding="utf-8"
    )
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)

sys.path.insert(0, BASE_DIR)
from database import SessionLocal, engine  # noqa: E402
from models import Base, CrawlPageState, CrawlRun  # noqa: E402
from crawler import (  # noqa: E402
    collect_bbs_post_links_from_soup,
    extract_content,
    crawl_page,
    get_soup,
    get_mId_from_url,
    is_bbs_list_url,
    is_bbs_view_url,
)

Base.metadata.create_all(bind=engine)

CRAWL_DELAY_MIN = 1.0
CRAWL_DELAY_MAX = 2.0
CRAWL_UA = "Mozilla/5.0 (SahaRu-IncrementalCrawler/1.0; +https://www.saha.go.kr)"

# 동적 요소 CSS 셀렉터 (조회수·날짜·댓글 등 — 해시 오탐 방지)
DYNAMIC_SELECTORS = [
    "dl.board_info",          # 날짜+조회수 묶음 DL 블록
    ".hit", ".read_cnt", ".readCnt", ".view_cnt", ".viewCnt",
    "dd.date", "span.date", ".reg_date", ".regDate",
    ".write_date", ".writeDate", ".registDate", ".regist_date",
    ".comment_cnt", ".reply_cnt", ".replyCnt",
    ".like_cnt", ".likeCnt", ".vote_cnt",
]

# 공통 노이즈 셀렉터 (네비게이션·헤더·푸터 등)
NOISE_SELECTORS = [
    "header", "footer", "#gnb", "#lnb",
    ".nav", ".footer", ".header", "#footer", "#header",
    ".skipNav", "#skipNav", ".location", ".breadcrumb",
]


# ── 내부 유틸 ─────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def compute_hash(text: str) -> str:
    """SHA-256 해시 (공개 API — 단위 테스트에서도 사용)"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extract_page_hash(url: str) -> tuple[str | None, str | None]:
    """
    URL을 가져와 동적 요소·네비게이션을 제거한 본문 텍스트의 해시를 반환.

    seed와 정상 실행이 모두 이 함수를 사용하므로 해시 기준이 동일하다.
    실패 시 (None, error_message).
    """
    try:
        import requests
        from bs4 import BeautifulSoup

        res = requests.get(url, headers={"User-Agent": CRAWL_UA}, timeout=20)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        # 1) 스크립트·스타일 제거
        for tag in soup.find_all(["script", "style", "noscript"]):
            tag.decompose()

        # 2) 네비게이션·레이아웃 제거
        for sel in NOISE_SELECTORS:
            for el in soup.select(sel):
                el.decompose()

        # 3) 동적 요소 제거 (조회수, 날짜, 댓글 수 등)
        for sel in DYNAMIC_SELECTORS:
            for el in soup.select(sel):
                el.decompose()

        content = extract_content(soup, url)
        return compute_hash(_normalize(content)), None

    except Exception as exc:
        return None, str(exc)


def _get_known_url_entries(limit: int | None = None) -> list[dict]:
    """data/ 디렉토리 JSON 파일에서 (url, filepath, doc) 목록 수집"""
    entries: list[dict] = []
    seen: set[str] = set()

    for root, _, files in os.walk(DATA_DIR):
        for fname in sorted(files):
            if not fname.endswith(".json") or "cache" in fname:
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    raw = json.load(f)
                docs = raw if isinstance(raw, list) else [raw]
                for doc in docs:
                    if not isinstance(doc, dict) or not doc.get("url"):
                        continue
                    url = doc["url"]
                    if url not in seen:
                        seen.add(url)
                        entries.append({"url": url, "filepath": fpath, "doc": doc})
                        if limit and len(entries) >= limit:
                            return entries
            except Exception:
                continue

    return entries


def _update_json_for_url(url: str, filepath: str, doc: dict) -> bool:
    """해당 URL을 재수집하여 JSON 파일 갱신 (기존 청크 교체)"""
    try:
        item = {
            "title": doc.get("title", ""),
            "url": url,
            "mId": doc.get("mId", ""),
            "type": doc.get("type", "page"),
        }
        new_doc = crawl_page(item, doc.get("category", ""))

        with open(filepath, encoding="utf-8") as f:
            raw = json.load(f)

        if isinstance(raw, list):
            for i, d in enumerate(raw):
                if isinstance(d, dict) and d.get("url") == url:
                    raw[i] = new_doc
                    break
        else:
            raw = new_doc

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        return True

    except Exception as exc:
        logger.error("JSON 업데이트 실패 [%s]: %s", url, exc)
        return False


def _invalidate_embeddings_cache() -> None:
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
        logger.info("임베딩 캐시 무효화 → 서버 재시작 또는 /admin/reload-index 호출 필요")


# ── 신규 URL 발견 ─────────────────────────────────────────────────────────────

def _discover_urls_from_sitemap() -> list[str]:
    """
    sitemap.xml에서 URL 목록 반환.
    사하구청이 sitemap을 제공하지 않으면 빈 리스트 반환.
    """
    try:
        import requests
        from xml.etree import ElementTree as ET

        res = requests.get(SITEMAP_URL, headers={"User-Agent": CRAWL_UA}, timeout=15)
        if res.status_code != 200:
            logger.info("sitemap.xml 없음 (HTTP %d)", res.status_code)
            return []

        root = ET.fromstring(res.content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [
            loc.text.strip()
            for loc in root.findall(".//sm:loc", ns)
            if loc.text and loc.text.strip()
        ]
        logger.info("sitemap.xml에서 %d개 URL 수집", len(urls))
        return urls

    except Exception as exc:
        logger.warning("sitemap.xml 파싱 실패: %s", exc)
        return []


def _discover_urls_from_bbs_first_page() -> list[str]:
    """
    게시판 목록 1페이지에서 게시물 URL 수집 (sitemap 없을 때 폴백).
    페이지네이션은 탐색하지 않으므로 빠르게 완료된다.
    """
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

    # 기존 JSON에서 게시판 목록 URL 추출 (페이지 파라미터 제거)
    list_urls: set[str] = set()
    for entry in _get_known_url_entries():
        url = entry["url"]
        if not is_bbs_list_url(url):
            continue
        parsed = urlparse(url)
        query = {k: v for k, v in parse_qs(parsed.query).items()
                 if k not in ("page", "pageIndex")}
        base = urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
        list_urls.add(base)

    urls: list[str] = []
    for list_url in list_urls:
        try:
            soup = get_soup(list_url)
            posts = collect_bbs_post_links_from_soup(soup, list_url)
            urls.extend(p["url"] for p in posts)
            logger.debug("게시판 1페이지 [%s] → %d개", list_url, len(posts))
        except Exception as exc:
            logger.warning("게시판 1페이지 조회 실패 [%s]: %s", list_url, exc)
        time.sleep(random.uniform(0.5, 1.0))

    logger.info("게시판 1페이지 폴백: %d개 URL 수집", len(urls))
    return urls


def _find_truly_new_urls(candidate_urls: list[str], db) -> list[str]:
    """후보 URL 중 crawl_page_states에 없는 URL만 반환"""
    known = {row.url for row in db.query(CrawlPageState.url).all()}
    return [u for u in candidate_urls if u not in known]


def _infer_category(url: str) -> str:
    """mId prefix를 기존 JSON 항목과 대조해 카테고리명 추론"""
    m_id = get_mId_from_url(url)
    if not m_id:
        return "incremental"
    prefix = m_id[:6]
    for entry in _get_known_url_entries():
        if entry["doc"].get("mId", "")[:6] == prefix:
            return entry["doc"].get("category", "incremental")
    return "incremental"


def _crawl_and_save_new_url(url: str) -> str | None:
    """
    sitemap/BBS에서 발견된 신규 URL을 수집하여
    data/incremental/all/incremental_NNNN.json 에 저장.

    Returns:
        저장된 파일 경로, 실패 시 None
    """
    try:
        url_type = (
            "bbs_view" if is_bbs_view_url(url) else
            "bbs_list" if is_bbs_list_url(url) else
            "page"
        )
        category = _infer_category(url)
        item = {"title": "", "url": url, "mId": get_mId_from_url(url), "type": url_type}
        new_doc = crawl_page(item, category)

        os.makedirs(INCREMENTAL_SAVE_DIR, exist_ok=True)
        idx = len([f for f in os.listdir(INCREMENTAL_SAVE_DIR) if f.endswith(".json")])
        filepath = os.path.join(INCREMENTAL_SAVE_DIR, f"incremental_{idx:04d}.json")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(new_doc, f, ensure_ascii=False, indent=2)

        logger.info("[신규 저장] %s → %s", url, filepath)
        return filepath

    except Exception as exc:
        logger.error("[신규 수집 실패] %s: %s", url, exc)
        return None


# ── 공개 함수 ─────────────────────────────────────────────────────────────────

def seed_hashes(limit: int | None = None) -> int:
    """
    알려진 URL을 실제로 가져와 _extract_page_hash()로 해시를 초기화합니다.
    JSON은 갱신하지 않으므로 정상 실행 직후 오탐이 0건입니다.

    주의: 네트워크 필요. --limit N 으로 빠르게 실행 가능.

    Returns:
        초기화된 URL 수
    """
    logger.info("=== 해시 초기화(seed) 시작 ===")
    db = SessionLocal()
    seeded = skipped = failed = 0
    try:
        entries = _get_known_url_entries(limit)
        logger.info("총 %d개 URL 대상", len(entries))

        for entry in entries:
            url = entry["url"]
            if db.query(CrawlPageState).filter(CrawlPageState.url == url).first():
                skipped += 1
                continue

            h, err = _extract_page_hash(url)
            if err:
                logger.warning("[seed 실패] %s → %s", url, err)
                failed += 1
                db.add(CrawlPageState(url=url, status="failed", last_crawled_at=_now()))
            else:
                db.add(CrawlPageState(
                    url=url, content_hash=h,
                    last_crawled_at=_now(), status="seeded",
                ))
                seeded += 1

            db.commit()
            time.sleep(random.uniform(CRAWL_DELAY_MIN, CRAWL_DELAY_MAX))

        logger.info("=== seed 완료: 초기화 %d / 스킵 %d / 실패 %d ===",
                    seeded, skipped, failed)
        return seeded
    finally:
        db.close()


def run_incremental_crawl(
    limit: int | None = None,
    reload_callback: "callable | None" = None,
) -> dict:
    """
    증분 크롤링 메인 함수.

    흐름:
      1) sitemap.xml (없으면 게시판 1페이지) 에서 신규 URL 발견 → 수집·저장
      2) 기존 JSON URL 검사 → 변경 시 JSON 갱신·임베딩 캐시 무효화
      3) 신규/변경 발생 시 reload_callback() 호출 (서버 인덱스 재로드)

    Args:
        limit: 처리할 URL 최대 수 (기존 URL 기준; 데모용)
        reload_callback: 변경 발생 후 호출할 함수 (예: reload_docs_inplace)

    Returns:
        {"checked": int, "new": int, "changed": int, "failed": int}
    """
    started_at = _now()
    logger.info("=== 증분 크롤링 시작 ===")

    db = SessionLocal()
    checked = new_cnt = changed_cnt = failed_cnt = 0
    needs_invalidation = False

    try:
        # ── 1. 신규 URL 발견 (sitemap → BBS 폴백) ────────────────────────────
        candidate_urls = _discover_urls_from_sitemap()
        if not candidate_urls:
            logger.info("sitemap 없음 → 게시판 1페이지 폴백")
            candidate_urls = _discover_urls_from_bbs_first_page()

        new_from_discovery = _find_truly_new_urls(candidate_urls, db)
        if new_from_discovery:
            logger.info("sitemap/BBS에서 발견된 신규 URL: %d건", len(new_from_discovery))

        for url in new_from_discovery:
            checked += 1
            h, err = _extract_page_hash(url)
            if err:
                logger.warning("[신규 해시 실패] %s → %s", url, err)
                failed_cnt += 1
                db.add(CrawlPageState(url=url, status="failed", last_crawled_at=_now()))
                db.commit()
                time.sleep(random.uniform(CRAWL_DELAY_MIN, CRAWL_DELAY_MAX))
                continue

            _crawl_and_save_new_url(url)
            new_cnt += 1
            needs_invalidation = True
            db.add(CrawlPageState(
                url=url, content_hash=h,
                last_crawled_at=_now(), status="new",
            ))
            db.commit()
            time.sleep(random.uniform(CRAWL_DELAY_MIN, CRAWL_DELAY_MAX))

        # ── 2. 기존 JSON URL 변경 감지 ───────────────────────────────────────
        entries = _get_known_url_entries(limit)
        logger.info("기존 URL %d개 검사 시작", len(entries))

        for entry in entries:
            url = entry["url"]
            checked += 1

            h, err = _extract_page_hash(url)
            if err:
                time.sleep(2)
                h, err2 = _extract_page_hash(url)
                if err2:
                    logger.warning("[실패] %s → %s", url, err2)
                    failed_cnt += 1
                    state = db.query(CrawlPageState).filter(
                        CrawlPageState.url == url
                    ).first()
                    if state:
                        state.status = "failed"
                        state.last_crawled_at = _now()
                    else:
                        db.add(CrawlPageState(
                            url=url, status="failed", last_crawled_at=_now()
                        ))
                    db.commit()
                    time.sleep(random.uniform(CRAWL_DELAY_MIN, CRAWL_DELAY_MAX))
                    continue

            state = db.query(CrawlPageState).filter(
                CrawlPageState.url == url
            ).first()

            if state is None:
                logger.info("[신규] %s", url)
                new_cnt += 1
                _update_json_for_url(url, entry["filepath"], entry["doc"])
                needs_invalidation = True
                db.add(CrawlPageState(
                    url=url, content_hash=h,
                    last_crawled_at=_now(), status="new",
                ))

            elif state.content_hash != h:
                logger.info("[변경] %s", url)
                changed_cnt += 1
                _update_json_for_url(url, entry["filepath"], entry["doc"])
                needs_invalidation = True
                state.content_hash = h
                state.last_crawled_at = _now()
                state.status = "changed"

            else:
                state.last_crawled_at = _now()
                state.status = "ok"

            db.commit()
            time.sleep(random.uniform(CRAWL_DELAY_MIN, CRAWL_DELAY_MAX))

        # ── 3. 캐시 무효화 + 인덱스 재로드 ──────────────────────────────────
        if needs_invalidation:
            _invalidate_embeddings_cache()
            if reload_callback:
                try:
                    reload_callback()
                    logger.info("인덱스 재로드 완료 (reload_callback)")
                except Exception as exc:
                    logger.error("인덱스 재로드 실패: %s", exc)

        finished_at = _now()
        db.add(CrawlRun(
            started_at=started_at,
            finished_at=finished_at,
            checked_urls=checked,
            new_count=new_cnt,
            changed_count=changed_cnt,
            failed_count=failed_cnt,
        ))
        db.commit()

        logger.info(
            "=== 증분 크롤링 완료 === 검사:%d 신규:%d 변경:%d 실패:%d",
            checked, new_cnt, changed_cnt, failed_cnt,
        )
        return {"checked": checked, "new": new_cnt,
                "changed": changed_cnt, "failed": failed_cnt}

    finally:
        db.close()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="사하루 증분 크롤러")
    parser.add_argument(
        "--seed",
        action="store_true",
        help="페이지를 실제로 가져와 해시 초기화 (JSON 갱신 없음)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="처리할 URL 최대 수 (데모/테스트용)",
    )
    args = parser.parse_args()

    if args.seed:
        seed_hashes(limit=args.limit)
    else:
        run_incremental_crawl(limit=args.limit)
