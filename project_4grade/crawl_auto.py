import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://www.saha.go.kr"
START_URL = "https://www.saha.go.kr/portal/contents.do?mId=0405000000"
SAVE_DIR = "data/environment_cleaning/all"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def get_soup(url):
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")


def clean_text(text):
    return "\n".join([line.strip() for line in text.splitlines() if line.strip()])


def is_env_cleaning_link(href: str) -> bool:
    return href.startswith("/portal/contents.do?mId=0405")


def collect_menu_links_from_soup(soup):
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(" ", strip=True)

        if not href or not text:
            continue

        if is_env_cleaning_link(href):
            full_url = urljoin(BASE_URL, href)
            links.append({
                "title": text,
                "url": full_url
            })

    # URL 기준 중복 제거
    unique = []
    seen = set()

    for item in links:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)

    return unique


def collect_first_and_second_level_links(start_url):
    # 1차 링크 수집
    start_soup = get_soup(start_url)
    first_links = collect_menu_links_from_soup(start_soup)

    all_links = []
    seen = set()

    # 1차 링크 저장
    for item in first_links:
        if item["url"] not in seen:
            seen.add(item["url"])
            all_links.append(item)

    # 2차 링크 수집
    for item in first_links:
        try:
            sub_soup = get_soup(item["url"])
            second_links = collect_menu_links_from_soup(sub_soup)

            for sub_item in second_links:
                if sub_item["url"] not in seen:
                    seen.add(sub_item["url"])
                    all_links.append(sub_item)

        except Exception as e:
            print(f"[2차 링크 수집 실패] {item['title']} / {e}")

    return all_links


def extract_content(soup):
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
            text = clean_text(tag.get_text())
            if len(text) > 100:
                return text

    return clean_text(soup.get_text())


def crawl_page(item):
    soup = get_soup(item["url"])
    content = extract_content(soup)

    return {
        "category": "환경/청소",
        "subcategory": item["title"],
        "title": item["title"],
        "url": item["url"],
        "content": content
    }


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    print("1차 + 2차 메뉴 링크 수집 중...\n")
    links = collect_first_and_second_level_links(START_URL)

    print(f"총 {len(links)}개 링크 발견\n")
    for item in links:
        print(f"- {item['title']} -> {item['url']}")
    print()

    for i, item in enumerate(links, start=1):
        try:
            data = crawl_page(item)

            filename = f"env_{i:03}.json"
            filepath = os.path.join(SAVE_DIR, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"[성공] {item['title']}")

        except Exception as e:
            print(f"[실패] {item['title']} / {e}")

    print("\n완료")


if __name__ == "__main__":
    main()