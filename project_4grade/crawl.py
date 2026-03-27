import os
import json
import requests
from bs4 import BeautifulSoup

# =========================
# 기본 설정
# =========================
CATEGORY = "환경/청소"
SUBCATEGORY = "석면관리"

URL_FILE = "urls/asbestos_urls.txt"
SAVE_DIR = "data/environment_cleaning/asbestos"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# =========================
# 유틸 함수
# =========================
def clean_text(text: str) -> str:
    """텍스트 정리"""
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def extract_title(soup: BeautifulSoup) -> str:
    """페이지 제목 추출"""
    if soup.title:
        return soup.title.get_text(strip=True)
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return "제목 없음"


def extract_content(soup: BeautifulSoup) -> str:
    """
    본문 추출
    1차: article / main / section 우선
    2차: body 전체 텍스트
    """
    candidates = [
        soup.find("article"),
        soup.find("main"),
        soup.find("section"),
    ]

    for tag in candidates:
        if tag:
            text = tag.get_text("\n", strip=True)
            text = clean_text(text)
            if len(text) > 100:
                return text

    body = soup.body.get_text("\n", strip=True) if soup.body else soup.get_text("\n", strip=True)
    return clean_text(body)


def crawl_page(url: str) -> dict:
    """페이지 하나 크롤링"""
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    title = extract_title(soup)
    content = extract_content(soup)

    data = {
        "category": CATEGORY,
        "subcategory": SUBCATEGORY,
        "title": title,
        "url": url,
        "department": "",
        "content": content
    }
    return data


def save_json(data: dict, filepath: str) -> None:
    """JSON 저장"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# 실행
# =========================
def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    if not os.path.exists(URL_FILE):
        print(f"URL 파일이 없음: {URL_FILE}")
        return

    with open(URL_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"총 {len(urls)}개 URL 크롤링 시작\n")

    for i, url in enumerate(urls, start=1):
        try:
            data = crawl_page(url)
            filename = f"asbestos_{i:03}.json"
            filepath = os.path.join(SAVE_DIR, filename)
            save_json(data, filepath)

            print(f"[성공] {filename}")
            print(f"제목: {data['title']}")
            print(f"URL: {url}\n")

        except Exception as e:
            print(f"[실패] {url}")
            print(f"에러: {e}\n")

    print("크롤링 완료")


if __name__ == "__main__":
    main()