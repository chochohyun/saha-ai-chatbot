import os
import json
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


START_URL = "https://www.saha.go.kr/portal/bbs/list.do?ptIdx=9&mId=0103060100"
SAVE_DIR = "data/faq/all"


def clean_text(text: str) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1400,2200")
    driver = webdriver.Chrome(options=options)
    return driver


def extract_main_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    selectors = [
        ".bbs--view",
        ".bbs-view",
        ".board_view",
        ".view_con",
        ".conBox",
        ".contents",
        ".content",
        "#contents",
        "#content",
        ".cont",
    ]

    for selector in selectors:
        el = soup.select_one(selector)
        if el:
            text = clean_text(el.get_text("\n", strip=True))
            if len(text) > 30:
                return text

    return clean_text(soup.get_text("\n", strip=True))


def collect_detail_links(driver):
    driver.get(START_URL)
    wait = WebDriverWait(driver, 10)

    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table tbody tr")))

    links = []
    seen = set()

    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

    for idx in range(len(rows)):
        # 뒤로 갔다 오면 element가 stale 되니까 매번 다시 잡음
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        row = rows[idx]

        anchors = row.find_elements(By.TAG_NAME, "a")
        target = None

        for a in anchors:
            title = a.text.strip()
            if title and len(title) >= 4:
                target = a
                break

        if target is None:
            continue

        title = target.text.strip()

        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", target)

            wait.until(lambda d: "view.do" in d.current_url or d.current_url != START_URL)
            current_url = driver.current_url

            if "view.do" in current_url and current_url not in seen:
                seen.add(current_url)
                links.append({
                    "title": title,
                    "url": current_url
                })

            driver.back()
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table tbody tr")))
            time.sleep(0.5)

        except Exception as e:
            print(f"[링크 수집 실패] {title} / {e}")
            try:
                driver.get(START_URL)
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "table tbody tr")))
            except Exception:
                pass

    return links


def crawl_detail(driver, item):
    wait = WebDriverWait(driver, 10)
    driver.get(item["url"])
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(0.5)

    html = driver.page_source
    content = extract_main_text(html)

    return {
        "title": item["title"],
        "url": driver.current_url,
        "content": content
    }


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)
    driver = setup_driver()

    try:
        print("기존 FAQ 데이터 삭제 후 새로 수집 시작...\n")
        for filename in os.listdir(SAVE_DIR):
            if filename.endswith(".json"):
                os.remove(os.path.join(SAVE_DIR, filename))

        print("FAQ 상세 링크 수집 중...\n")
        links = collect_detail_links(driver)
        print(f"총 {len(links)}개 수집\n")

        for i, item in enumerate(links):
            try:
                data = crawl_detail(driver, item)
                filepath = os.path.join(SAVE_DIR, f"faq_{i:03}.json")
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"[성공] {item['title']}")
            except Exception as e:
                print(f"[상세 수집 실패] {item['title']} / {e}")

    finally:
        driver.quit()

    print("\n완료")


if __name__ == "__main__":
    main()