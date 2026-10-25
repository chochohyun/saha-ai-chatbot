"""
증분 크롤링 단위 테스트

실행:
  cd /Users/juchohyun/saha-ai-chatbot
  python -m pytest tests/test_incremental.py -v
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from incremental_crawl import compute_hash, _normalize


# ── 픽스처: 인메모리 SQLite DB ────────────────────────────────────────────────

@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    """테스트 전용 인메모리 SQLite DB를 생성하고 incremental_crawl 모듈에 주입"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base
    import incremental_crawl

    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    TestSession = sessionmaker(bind=test_engine)

    monkeypatch.setattr(incremental_crawl, "engine", test_engine)
    monkeypatch.setattr(incremental_crawl, "SessionLocal", TestSession)

    return TestSession


# ── 기존 해시 비교 단위 테스트 ────────────────────────────────────────────────

def _detect_status(stored_hash: str | None, new_hash: str) -> str:
    if stored_hash is None:
        return "new"
    if stored_hash != new_hash:
        return "changed"
    return "ok"


def test_new_url():
    """저장된 해시 없음 → 신규"""
    assert _detect_status(None, compute_hash("내용")) == "new"


def test_changed_url():
    """해시 불일치 → 변경"""
    assert _detect_status(compute_hash("이전"), compute_hash("바뀜")) == "changed"


def test_unchanged_url():
    """해시 일치 → 스킵(ok)"""
    h = compute_hash("동일 내용")
    assert _detect_status(h, h) == "ok"


def test_hash_deterministic():
    text = "사하구청 복지서비스 안내"
    assert compute_hash(text) == compute_hash(text)


def test_hash_sensitivity():
    assert compute_hash("내용A") != compute_hash("내용 A")


def test_normalize_collapses_whitespace():
    assert _normalize("  사하구청\n\n  민원  안내  ") == "사하구청 민원 안내"


# ── 신규 테스트 1: seed 직후 run → 신규 0 / 변경 0 ──────────────────────────

@patch("incremental_crawl._extract_page_hash")
@patch("incremental_crawl._discover_urls_from_sitemap", return_value=[])
@patch("incremental_crawl._discover_urls_from_bbs_first_page", return_value=[])
def test_seed_then_run_zero_false_positives(
    _mock_bbs, _mock_sitemap, mock_hash, monkeypatch, temp_db
):
    """
    seed 직후 정상 실행 시 신규 0건 / 변경 0건 이어야 한다.
    _extract_page_hash 가 동일 해시를 반환하면 오탐 없음.
    """
    import incremental_crawl

    TEST_URL = "https://www.saha.go.kr/portal/test"
    FIXED_HASH = "abc123def456abc123def456abc123def456abc123def456abc123def456abc12"
    mock_hash.return_value = (FIXED_HASH, None)

    fake_entries = [{
        "url": TEST_URL,
        "filepath": "/fake/path.json",
        "doc": {"url": TEST_URL, "content": "테스트 내용", "category": "test", "mId": "0104"},
    }]
    monkeypatch.setattr(incremental_crawl, "_get_known_url_entries",
                        lambda limit=None: fake_entries)
    # _update_json_for_url 는 호출되지 않아야 하지만, 혹시 호출돼도 파일 I/O 막기
    monkeypatch.setattr(incremental_crawl, "_update_json_for_url",
                        lambda url, fp, doc: True)
    monkeypatch.setattr(incremental_crawl, "_invalidate_embeddings_cache",
                        lambda: None)

    # Step 1: seed — 해시 저장 (JSON 갱신 없음)
    seeded = incremental_crawl.seed_hashes()
    assert seeded == 1

    # Step 2: 정상 실행 — 동일 해시이므로 신규/변경 0건
    result = incremental_crawl.run_incremental_crawl()
    assert result["new"] == 0, f"신규가 0건 이어야 하는데 {result['new']}건"
    assert result["changed"] == 0, f"변경이 0건 이어야 하는데 {result['changed']}건"


# ── 신규 테스트 2: sitemap URL 발견 ──────────────────────────────────────────

def test_sitemap_url_discovery():
    """
    sitemap.xml 응답이 있을 때 URL 목록을 정확히 파싱해야 한다.
    """
    from incremental_crawl import _discover_urls_from_sitemap

    sitemap_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://www.saha.go.kr/portal/contents.do?mId=0104010100</loc></url>
      <url><loc>https://www.saha.go.kr/portal/contents.do?mId=0104020100</loc></url>
      <url><loc>  https://www.saha.go.kr/portal/contents.do?mId=0104030100  </loc></url>
    </urlset>"""

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = sitemap_xml

    with patch("requests.get", return_value=mock_resp):
        urls = _discover_urls_from_sitemap()

    assert len(urls) == 3
    assert "https://www.saha.go.kr/portal/contents.do?mId=0104010100" in urls
    # 양쪽 공백이 strip 되어야 함
    assert "https://www.saha.go.kr/portal/contents.do?mId=0104030100" in urls


def test_sitemap_unavailable_returns_empty():
    """sitemap.xml 이 404 면 빈 리스트를 반환해야 한다."""
    from incremental_crawl import _discover_urls_from_sitemap

    mock_resp = MagicMock()
    mock_resp.status_code = 404

    with patch("requests.get", return_value=mock_resp):
        urls = _discover_urls_from_sitemap()

    assert urls == []


# ── 시연 헬퍼: 해시 1개 변조 ─────────────────────────────────────────────────

def tamper_hash(url: str, fake_hash: str = "0" * 64) -> bool:
    """
    시연 시나리오용: 특정 URL의 저장 해시를 임의 값으로 변조한다.

    사용 예:
        python -c "
        import sys; sys.path.insert(0,'backend')
        from tests.test_incremental import tamper_hash
        tamper_hash('https://www.saha.go.kr/portal/contents.do?mId=0104010100')
        "
    """
    try:
        from database import SessionLocal
        from models import CrawlPageState

        db = SessionLocal()
        state = db.query(CrawlPageState).filter(CrawlPageState.url == url).first()
        if not state:
            print(f"[tamper] URL이 DB에 없습니다: {url}")
            return False
        state.content_hash = fake_hash
        db.commit()
        print(f"[tamper] 해시 변조 완료: {url} → {fake_hash[:16]}…")
        return True
    except Exception as e:
        print(f"[tamper] 실패: {e}")
        return False
    finally:
        db.close()
