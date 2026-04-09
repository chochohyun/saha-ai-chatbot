import os
import re
import csv
import json
import time
import zipfile
import requests
import pandas as pd

from pypdf import PdfReader
from bs4 import BeautifulSoup
from collections import deque
from urllib.parse import (
    urljoin,
    urlparse,
    parse_qs,
    urlencode,
    urlunparse,
    unquote
)
import xml.etree.ElementTree as ET


BASE_URL = "https://www.saha.go.kr"
START_URL = "https://www.saha.go.kr/portal/contents.do?mId=0104000000"
ROOT_SAVE_DIR = "data"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

REQUEST_DELAY = 0.2


def get_soup(url):
    res = requests.get(url, headers=HEADERS, timeout=20)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")


def clean_text(text):
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w가-힣\s-]", "", text)
    text = re.sub(r"[\s-]+", "_", text)
    return text[:60] if text else "category"


def sanitize_filename(name: str) -> str:
    name = unquote(name).strip()
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return name[:200] if name else "file"


def get_mId_from_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return query.get("mId", [""])[0]


def get_bIdx_from_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return query.get("bIdx", [""])[0]


def get_ptIdx_from_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return query.get("ptIdx", [""])[0]


def set_query_param(url: str, key: str, value: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query[key] = [str(value)]

    new_query = urlencode(query, doseq=True)
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))


def get_menu_prefix(m_id: str, level: int = 4) -> str:
    return m_id[:level] if m_id else ""


def normalize_url(href: str) -> str:
    return urljoin(BASE_URL, href.strip())


def is_same_menu_link(url: str, menu_prefix: str) -> bool:
    m_id = get_mId_from_url(url)
    return bool(m_id) and m_id.startswith(menu_prefix)


def is_bbs_list_url(url: str) -> bool:
    return "/bbs/list.do" in url


def is_bbs_view_url(url: str) -> bool:
    return "/bbs/view.do" in url


def extract_best_title(soup):
    candidates = []

    selectors = [
        "h1", "h2", "h3",
        ".sub_title", ".title", ".tit", ".con_title", ".contit",
        ".page-title", ".page_title", ".contents_title",
        ".location .current", ".breadcrumb .current", "title"
    ]

    for selector in selectors:
        for tag in soup.select(selector):
            text = tag.get_text(" ", strip=True)
            if text:
                candidates.append(text)

    bad_values = {"주메뉴", "서브메뉴", "콘텐츠", "내용", "본문", "상세", "목록"}

    for text in candidates:
        if text and text not in bad_values and len(text) >= 2:
            return text

    return "unknown"


def extract_menu_name_from_page(soup, current_mId: str):
    if not current_mId:
        return ""

    for a in soup.find_all("a", href=True):
        href = normalize_url(a["href"])
        m_id = get_mId_from_url(href)
        text = a.get_text(" ", strip=True)

        if m_id == current_mId and text and text not in {"주메뉴", "서브메뉴"}:
            return text

    return ""


def extract_category_name(start_url):
    soup = get_soup(start_url)
    start_mId = get_mId_from_url(start_url)

    menu_name = extract_menu_name_from_page(soup, start_mId)
    if menu_name:
        return menu_name

    title = extract_best_title(soup)
    if title and title != "unknown":
        return title

    return start_mId or "category"


def collect_menu_links_from_soup(soup, menu_prefix):
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href:
            continue

        full_url = normalize_url(href)

        if not is_same_menu_link(full_url, menu_prefix):
            continue

        text = a.get_text(" ", strip=True)
        if not text:
            text = get_mId_from_url(full_url) or "untitled"

        links.append({
            "title": text,
            "url": full_url,
            "mId": get_mId_from_url(full_url),
            "type": "bbs_list" if is_bbs_list_url(full_url) else (
                "bbs_view" if is_bbs_view_url(full_url) else "page"
            )
        })

    unique = []
    seen = set()

    for item in links:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)

    return unique


def parse_board_view_onclick(onclick: str):
    if not onclick or "boardView(" not in onclick:
        return None

    match = re.search(r"boardView\s*\((.*?)\)", onclick)
    if not match:
        return None

    args_text = match.group(1)
    args = re.findall(r"'(.*?)'", args_text)

    if len(args) < 6:
        return None

    b_idx = args[3].strip()
    pt_idx = args[4].strip()
    m_id = args[5].strip()

    if not b_idx or not pt_idx or not m_id:
        return None

    view_url = (
        f"{BASE_URL}/portal/bbs/view.do"
        f"?mId={m_id}&bIdx={b_idx}&ptIdx={pt_idx}"
    )

    return {
        "url": view_url,
        "bIdx": b_idx,
        "ptIdx": pt_idx,
        "mId": m_id
    }


def parse_onclick_download_url(onclick: str):
    if not onclick:
        return ""

    # fn_egov_downFile('FILE_000000000170230','0')
    m = re.search(
        r"""fn_egov_downFile\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]+)['"]\s*\)""",
        onclick
    )
    if m:
        atch_file_id = m.group(1).strip()
        file_sn = m.group(2).strip()

        # 전자정부 계열 다운로드 경로 후보들
        candidates = [
            f"{BASE_URL}/common/file/down.do?atchFileId={atch_file_id}&fileSn={file_sn}",
            f"{BASE_URL}/cmm/fms/FileDown.do?atchFileId={atch_file_id}&fileSn={file_sn}",
            f"{BASE_URL}/portal/cmm/fms/FileDown.do?atchFileId={atch_file_id}&fileSn={file_sn}",
            f"{BASE_URL}/portal/common/file/down.do?atchFileId={atch_file_id}&fileSn={file_sn}",
        ]
        return candidates[0]

    m = re.search(r"""location\.href\s*=\s*['"]([^'"]+)['"]""", onclick, re.IGNORECASE)
    if m:
        return urljoin(BASE_URL, m.group(1))

    m = re.search(r"""window\.open\s*\(\s*['"]([^'"]+)['"]""", onclick, re.IGNORECASE)
    if m:
        return urljoin(BASE_URL, m.group(1))

    m = re.search(r"""['"]([^'"]*(?:download|filedown|attach|file)[^'"]*)['"]""", onclick, re.IGNORECASE)
    if m:
        return urljoin(BASE_URL, m.group(1))

    return ""


def collect_bbs_post_links_from_soup(soup, list_url):
    collected = []
    seen = set()

    base_m_id = get_mId_from_url(list_url)
    base_pt_idx = get_ptIdx_from_url(list_url)

    for a in soup.find_all("a"):
        text = a.get_text(" ", strip=True)
        onclick = a.get("onclick", "").strip()

        parsed = parse_board_view_onclick(onclick)
        if not parsed:
            continue

        if parsed["mId"] != base_m_id:
            continue

        if parsed["ptIdx"] != base_pt_idx:
            continue

        post_url = parsed["url"]

        if post_url not in seen:
            seen.add(post_url)
            collected.append({
                "title": text or parsed["bIdx"] or "post",
                "url": post_url,
                "mId": parsed["mId"],
                "type": "bbs_view"
            })

    return collected


def collect_bbs_post_links(list_url):
    collected = []
    seen = set()
    page = 1

    while True:
        page_urls = [
            set_query_param(list_url, "page", page),
            set_query_param(list_url, "pageIndex", page),
        ]

        page_found_this_round = 0
        round_items = []

        for paged_url in page_urls:
            try:
                soup = get_soup(paged_url)
            except Exception:
                continue

            items = collect_bbs_post_links_from_soup(soup, list_url)

            if len(items) > page_found_this_round:
                page_found_this_round = len(items)
                round_items = items

        for item in round_items:
            if item["url"] not in seen:
                seen.add(item["url"])
                collected.append(item)

        print(f"[게시판 탐색] {list_url} / page={page} -> 게시글 {len(round_items)}개 발견")

        if len(round_items) == 0:
            break

        page += 1
        time.sleep(REQUEST_DELAY)

    return collected


def get_filename_from_response(response, fallback_url=""):
    cd = response.headers.get("Content-Disposition", "")
    filename = None

    m = re.search(r"filename\*\s*=\s*UTF-8''([^;]+)", cd, re.IGNORECASE)
    if m:
        filename = unquote(m.group(1))

    if not filename:
        m = re.search(r'filename\s*=\s*"([^"]+)"', cd, re.IGNORECASE)
        if m:
            filename = m.group(1)

    if not filename:
        m = re.search(r'filename\s*=\s*([^;]+)', cd, re.IGNORECASE)
        if m:
            filename = m.group(1).strip()

    if not filename:
        path = urlparse(fallback_url).path
        filename = os.path.basename(path) or "downloaded_file"

    return sanitize_filename(filename)


def collect_attachment_links(soup):
    files = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(" ", strip=True)
        onclick = a.get("onclick", "").strip()

        full_url = urljoin(BASE_URL, href) if href else ""
        onclick_url = parse_onclick_download_url(onclick)
        final_url = onclick_url or full_url

        low_url = final_url.lower()
        low_text = text.lower()
        low_onclick = onclick.lower()

        is_candidate = False

        if any(ext in low_text for ext in [".xlsx", ".xls", ".csv", ".pdf", ".hwp", ".hwpx", ".jpg", ".jpeg", ".png"]):
            is_candidate = True

        if "fn_egov_downfile" in low_onclick:
            is_candidate = True

        if any(ext in low_url for ext in [".xlsx", ".xls", ".csv", ".pdf", ".hwp", ".hwpx", ".jpg", ".jpeg", ".png"]):
            is_candidate = True

        if any(keyword in low_url for keyword in ["down.do", "download", "filedown", "attach", "file"]):
            is_candidate = True

        if not is_candidate:
            continue

        key = final_url or onclick or text
        if key in seen:
            continue
        seen.add(key)

        files.append({
            "name": text or "attachment",
            "url": final_url,
            "onclick": onclick
        })

    return files


def try_download_from_candidates(url_candidates, save_dir, fallback_name="attachment"):
    os.makedirs(save_dir, exist_ok=True)

    last_error = None

    for candidate_url in url_candidates:
        try:
            res = requests.get(candidate_url, headers=HEADERS, timeout=60)
            res.raise_for_status()

            filename = get_filename_from_response(res, candidate_url)
            if not filename or filename == "downloaded_file":
                filename = sanitize_filename(fallback_name)

            filepath = os.path.join(save_dir, filename)

            if not os.path.exists(filepath):
                with open(filepath, "wb") as f:
                    f.write(res.content)

            return filepath, filename, candidate_url

        except Exception as e:
            last_error = e

    raise last_error if last_error else Exception("다운로드 실패")


def build_download_candidates(file_info):
    url = file_info.get("url", "")
    onclick = file_info.get("onclick", "")

    candidates = []

    if url:
        candidates.append(url)

    # fn_egov_downFile는 여러 다운로드 경로 후보 시도
    m = re.search(
        r"""fn_egov_downFile\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]+)['"]\s*\)""",
        onclick
    )
    if m:
        atch_file_id = m.group(1).strip()
        file_sn = m.group(2).strip()

        extra = [
            f"{BASE_URL}/common/file/down.do?atchFileId={atch_file_id}&fileSn={file_sn}",
            f"{BASE_URL}/cmm/fms/FileDown.do?atchFileId={atch_file_id}&fileSn={file_sn}",
            f"{BASE_URL}/portal/cmm/fms/FileDown.do?atchFileId={atch_file_id}&fileSn={file_sn}",
            f"{BASE_URL}/portal/common/file/down.do?atchFileId={atch_file_id}&fileSn={file_sn}",
        ]

        for x in extra:
            if x not in candidates:
                candidates.append(x)

    return candidates


def download_attachment(file_info, save_dir):
    candidates = build_download_candidates(file_info)
    return try_download_from_candidates(
        candidates,
        save_dir,
        fallback_name=file_info.get("name", "attachment")
    )


def extract_csv_text(filepath):
    lines = []
    encodings = ["utf-8-sig", "cp949", "euc-kr", "utf-8"]

    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc, newline="") as f:
                reader = csv.reader(f)
                for row in reader:
                    line = " | ".join(str(cell).strip() for cell in row if str(cell).strip())
                    if line:
                        lines.append(line)
            return "\n".join(lines)
        except Exception:
            continue

    return ""


def extract_excel_text(filepath):
    texts = []

    try:
        excel_file = pd.ExcelFile(filepath)

        for sheet_name in excel_file.sheet_names:
            try:
                df = pd.read_excel(filepath, sheet_name=sheet_name, dtype=str)
                df = df.fillna("")

                texts.append(f"[시트명] {sheet_name}")

                for row in df.values.tolist():
                    row_text = " | ".join(str(cell).strip() for cell in row if str(cell).strip())
                    if row_text:
                        texts.append(row_text)

            except Exception as e:
                texts.append(f"[시트 읽기 실패] {sheet_name} / {e}")

    except Exception as e:
        return f"[엑셀 읽기 실패] {e}"

    return "\n".join(texts)


def extract_pdf_text(filepath):
    texts = []

    try:
        reader = PdfReader(filepath)

        for i, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
                page_text = page_text.strip()
                if page_text:
                    texts.append(f"[PDF {i}페이지]\n{page_text}")
            except Exception as e:
                texts.append(f"[PDF {i}페이지 추출 실패] {e}")

    except Exception as e:
        return f"[PDF 읽기 실패] {e}"

    return "\n\n".join(texts)


def extract_hwpx_text(filepath):
    texts = []

    try:
        with zipfile.ZipFile(filepath, "r") as z:
            xml_files = [name for name in z.namelist() if name.endswith(".xml")]

            for xml_name in xml_files:
                try:
                    with z.open(xml_name) as f:
                        tree = ET.parse(f)
                        root = tree.getroot()

                        for elem in root.iter():
                            if elem.text and elem.text.strip():
                                texts.append(elem.text.strip())

                except Exception:
                    continue

    except Exception as e:
        return f"[HWPX 읽기 실패] {e}"

    return "\n".join(texts)


def extract_hwp_text(filepath):
    return "[HWP 추출 미지원 또는 실패 가능성 높음] 파일은 저장했지만 텍스트 추출은 별도 처리 필요"


def extract_attachment_text(filepath):
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".csv":
        return extract_csv_text(filepath)

    if ext in [".xlsx", ".xls"]:
        return extract_excel_text(filepath)

    if ext == ".pdf":
        return extract_pdf_text(filepath)

    if ext == ".hwpx":
        return extract_hwpx_text(filepath)

    if ext == ".hwp":
        return extract_hwp_text(filepath)

    return ""


def extract_content(soup, url=""):
    # 게시판 상세 페이지 우선 처리
    if "/bbs/view.do" in url:
        selectors = [
            ".board_view",
            ".bbs--view",
            ".view_cont",
            ".view_content",
            ".con_view",
            "#content"
        ]

        for selector in selectors:
            tag = soup.select_one(selector)
            if tag:
                text = clean_text(tag.get_text(" ", strip=False))
                if len(text) > 100:
                    return text

    # 일반 페이지
    candidates = [
        soup.find("div", id="content"),
        soup.find("div", class_="content"),
        soup.find("div", class_="contents"),
        soup.find("div", class_="sub_contents"),
        soup.find("main"),
        soup.find("article"),
        soup.find("section"),
    ]

    for tag in candidates:
        if tag:
            text = clean_text(tag.get_text(" ", strip=False))
            if len(text) > 100:
                return text

    return clean_text(soup.get_text(" ", strip=False))


def crawl_page(item, category_name):
    soup = get_soup(item["url"])
    page_title = extract_best_title(soup)
    content = extract_content(soup, item["url"])

    attachments = []
    post_id = get_bIdx_from_url(item["url"]) or get_mId_from_url(item["url"]) or "page"
    attach_save_dir = os.path.join(ROOT_SAVE_DIR, slugify(category_name), "attachments", post_id)

    file_links = collect_attachment_links(soup)

    for file_info in file_links:
        try:
            saved_path, real_filename, actual_url = download_attachment(file_info, attach_save_dir)
            file_text = extract_attachment_text(saved_path)

            attachments.append({
                "name": real_filename,
                "url": actual_url,
                "saved_path": saved_path,
                "content": file_text
            })

        except Exception as e:
            attachments.append({
                "name": file_info.get("name", "attachment"),
                "url": file_info.get("url", ""),
                "error": str(e)
            })

    attachment_texts = []
    for att in attachments:
        if att.get("content"):
            attachment_texts.append(att["content"])

    search_text = "\n\n".join([
        content or "",
        "\n\n".join(attachment_texts)
    ]).strip()

    return {
        "category": category_name,
        "subcategory": item["title"],
        "title": page_title if page_title and page_title != "unknown" else item["title"],
        "url": item["url"],
        "mId": item["mId"],
        "type": item.get("type", "page"),
        "content": content,
        "attachments": attachments,
        "search_text": search_text
    }


def collect_all_links(start_url, menu_prefix):
    discovered_links = []
    discovered_urls = set()
    visited_pages = set()

    queue = deque([{
        "title": "start",
        "url": start_url,
        "mId": get_mId_from_url(start_url),
        "type": "page"
    }])

    while queue:
        current = queue.popleft()
        current_url = current["url"]

        if current_url in visited_pages:
            continue

        visited_pages.add(current_url)

        try:
            soup = get_soup(current_url)
        except Exception as e:
            print(f"[탐색 실패] {current_url} / {e}")
            continue

        if current_url not in discovered_urls:
            discovered_urls.add(current_url)
            if current_url != start_url:
                discovered_links.append(current)

        page_links = collect_menu_links_from_soup(soup, menu_prefix)
        print(f"[탐색] {current_url} -> {len(page_links)}개 링크 발견")

        for item in page_links:
            if item["url"] not in discovered_urls:
                discovered_urls.add(item["url"])
                discovered_links.append(item)
            if item["url"] not in visited_pages:
                queue.append(item)

        if is_bbs_list_url(current_url):
            post_links = collect_bbs_post_links(current_url)

            for post in post_links:
                if post["url"] not in discovered_urls:
                    discovered_urls.add(post["url"])
                    discovered_links.append(post)
                if post["url"] not in visited_pages:
                    queue.append(post)

        time.sleep(REQUEST_DELAY)

    unique = []
    seen = set()

    for item in discovered_links:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)

    return unique


def save_json(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    start_mId = get_mId_from_url(START_URL)
    if not start_mId:
        raise ValueError("START_URL에서 mId를 찾을 수 없습니다.")

    menu_prefix = get_menu_prefix(start_mId, level=4)
    category_name = extract_category_name(START_URL)
    category_slug = slugify(category_name)

    save_dir = os.path.join(ROOT_SAVE_DIR, category_slug, "all")
    os.makedirs(save_dir, exist_ok=True)

    print(f"시작 URL: {START_URL}")
    print(f"시작 mId: {start_mId}")
    print(f"메뉴 prefix: {menu_prefix}")
    print(f"카테고리명: {category_name}")
    print(f"저장 폴더: {save_dir}\n")

    print("하위 링크 + 게시판 글 + 첨부파일 전체 탐색 중...\n")
    links = collect_all_links(START_URL, menu_prefix)

    print(f"\n총 {len(links)}개 링크 발견\n")
    for item in links:
        print(f"- [{item.get('type', 'page')}] {item['title']} -> {item['url']}")
    print()

    failed = []

    start_item = {
        "title": category_name,
        "url": START_URL,
        "mId": start_mId,
        "type": "page"
    }

    try:
        start_data = crawl_page(start_item, category_name)
        save_json(start_data, os.path.join(save_dir, f"{category_slug}_000.json"))
        print(f"[성공] {category_name} (start)")
    except Exception as e:
        failed.append({"title": category_name, "url": START_URL, "error": str(e)})
        print(f"[실패] {category_name} (start) / {e}")

    for i, item in enumerate(links, start=1):
        try:
            data = crawl_page(item, category_name)
            filename = f"{category_slug}_{i:03}.json"
            filepath = os.path.join(save_dir, filename)
            save_json(data, filepath)
            print(f"[성공] {item['title']}")
        except Exception as e:
            failed.append({"title": item["title"], "url": item["url"], "error": str(e)})
            print(f"[실패] {item['title']} / {e}")

    if failed:
        failed_path = os.path.join(save_dir, f"{category_slug}_failed.json")
        save_json(failed, failed_path)
        print(f"\n실패 로그 저장: {failed_path}")

    print("\n완료")


if __name__ == "__main__":
    main()