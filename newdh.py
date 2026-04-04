import os
import json
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


BASE_URL = "https://www.saha.go.kr/portal/bbs/list.do?ptIdx=9&mId=0103060100"
SAVE_DIR = "data/faq/all"
SAVE_PATH = os.path.join(SAVE_DIR, "faq.json")

CATEGORY_NAME = "faq"

MAX_PAGES = 100
SHORT_SLEEP = 0.2
PAGE_SLEEP = 0.7


def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    prefs = {
        "profile.managed_default_content_settings.images": 2
    }
    options.add_experimental_option("prefs", prefs)

    possible_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Users/dh/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]

    chrome_found = False
    for path in possible_paths:
        if os.path.exists(path):
            options.binary_location = path
            chrome_found = True
            break

    if not chrome_found:
        raise FileNotFoundError("Google Chrome 실행 파일을 찾지 못했습니다.")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver


def safe_text(element):
    try:
        return element.text.strip()
    except Exception:
        return ""


def wait_for_list(driver, timeout=15):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
    )


def wait_for_detail(driver, timeout=15):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".title"))
    )
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".cont_box"))
    )


def get_current_active_page(driver):
    try:
        el = driver.find_element(
            By.XPATH,
            "//div[contains(@class,'box_page')]//span[@title='현재페이지']"
        )
        return int(el.text.strip())
    except Exception:
        return None


def get_total_pages(driver):
    nums = []

    try:
        current_spans = driver.find_elements(
            By.XPATH,
            "//div[contains(@class,'box_page')]//span[@title='현재페이지']"
        )
        for el in current_spans:
            txt = el.text.strip()
            if txt.isdigit():
                nums.append(int(txt))
    except Exception:
        pass

    try:
        page_links = driver.find_elements(
            By.XPATH,
            "//div[contains(@class,'box_page')]//a"
        )
        for el in page_links:
            txt = el.text.strip()
            if txt.isdigit():
                nums.append(int(txt))
    except Exception:
        pass

    return max(nums) if nums else None


def move_to_page(driver, target_page):
    """
    target_page 숫자 링크 직접 클릭.
    현재 화면에 숫자가 없으면 다음페이지 버튼을 눌러 페이지 묶음 이동.
    """
    for _ in range(10):
        try:
            current = get_current_active_page(driver)
            if current == target_page:
                return True

            links = driver.find_elements(
                By.XPATH,
                "//div[contains(@class,'box_page')]//a"
            )

            for link in links:
                txt = link.text.strip()
                onclick = (link.get_attribute("onclick") or "").strip()

                if txt == str(target_page) or f"goPage({target_page})" in onclick:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});",
                        link
                    )
                    time.sleep(SHORT_SLEEP)
                    driver.execute_script("arguments[0].click();", link)

                    WebDriverWait(driver, 10).until(
                        lambda d: get_current_active_page(d) == target_page
                    )
                    wait_for_list(driver, timeout=10)
                    time.sleep(PAGE_SLEEP)
                    return True

            next_btn = None
            for link in links:
                title_attr = (link.get_attribute("title") or "").strip()
                onclick = (link.get_attribute("onclick") or "").strip()
                txt = link.text.strip()

                if "다음페이지" in title_attr:
                    next_btn = link
                    break

                if txt == ">" and "goPage" in onclick:
                    next_btn = link
                    break

            if next_btn is None:
                return False

            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                next_btn
            )
            time.sleep(SHORT_SLEEP)
            driver.execute_script("arguments[0].click();", next_btn)
            wait_for_list(driver, timeout=10)
            time.sleep(PAGE_SLEEP)

        except Exception:
            return False

    return False


def save_json(data):
    os.makedirs(SAVE_DIR, exist_ok=True)
    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_row(row):
    cells = row.find_elements(By.TAG_NAME, "td")
    if len(cells) < 6:
        return None

    link_el = cells[1].find_element(By.TAG_NAME, "a")

    return {
        "list_title": safe_text(link_el),
        "dept": safe_text(cells[2]),
        "date": safe_text(cells[3]),
        "file_flag": safe_text(cells[4]),
        "views": safe_text(cells[5]),
    }


def reopen_list_page(driver, page):
    driver.get(BASE_URL)
    wait_for_list(driver)
    time.sleep(PAGE_SLEEP)

    if page > 1:
        ok = move_to_page(driver, page)
        if not ok:
            raise RuntimeError(f"{page}페이지 재이동 실패")


def build_content(detail_title, detail_content, item_meta):
    """
    최종 content에는 FAQ 본문 중심으로 넣고,
    부가정보는 같이 녹여서 저장.
    """
    parts = []

    if detail_title:
        parts.append(f"[제목]\n{detail_title}")

    if item_meta.get("dept"):
        parts.append(f"[담당부서]\n{item_meta['dept']}")

    if item_meta.get("date"):
        parts.append(f"[작성일]\n{item_meta['date']}")

    if item_meta.get("file_flag"):
        parts.append(f"[첨부여부]\n{item_meta['file_flag']}")

    if item_meta.get("views"):
        parts.append(f"[조회수]\n{item_meta['views']}")

    if detail_content:
        parts.append(f"[본문]\n{detail_content}")

    return "\n\n".join(parts).strip()


def build_search_text(title, content, item_meta):
    parts = [
        CATEGORY_NAME,
        title or "",
        item_meta.get("dept", ""),
        item_meta.get("date", ""),
        item_meta.get("file_flag", ""),
        item_meta.get("views", ""),
        content or "",
    ]
    return " ".join(p.strip() for p in parts if p and p.strip())


def make_record(final_title, current_url, detail_content, item_meta):
    content = build_content(final_title, detail_content, item_meta)
    search_text = build_search_text(final_title, content, item_meta)

    return {
        "category": CATEGORY_NAME,
        "title": final_title or "",
        "url": current_url or "",
        "content": content,
        "search_text": search_text,
    }


def crawl():
    driver = init_driver()
    all_data = []
    seen_urls = set()

    try:
        os.makedirs(SAVE_DIR, exist_ok=True)

        driver.get(BASE_URL)
        wait_for_list(driver)
        time.sleep(PAGE_SLEEP)

        detected_total = get_total_pages(driver)
        print(f"🔎 감지된 페이지 수: {detected_total if detected_total else '자동감지 실패'}")
        print("➡️ 순회 시작")

        for page in range(1, MAX_PAGES + 1):
            try:
                reopen_list_page(driver, page)
            except Exception:
                print(f"\n📌 {page}페이지로 이동 실패 → 마지막 페이지로 판단하고 종료")
                break

            active_page = get_current_active_page(driver)
            print(f"\n📄 {page}페이지 이동 중... (현재 활성 페이지: {active_page})")

            rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            if not rows:
                print("📌 목록 행이 없어 종료합니다.")
                break

            print(f"   → 목록에서 {len(rows)}개 확인")
            page_new_count = 0

            for row_idx in range(len(rows)):
                list_title = ""

                try:
                    reopen_list_page(driver, page)

                    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                    if row_idx >= len(rows):
                        continue

                    row = rows[row_idx]
                    item_meta = parse_row(row)
                    if not item_meta:
                        continue

                    list_title = item_meta["list_title"]

                    link_el = row.find_elements(By.TAG_NAME, "td")[1].find_element(By.TAG_NAME, "a")
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});",
                        link_el
                    )
                    time.sleep(SHORT_SLEEP)
                    driver.execute_script("arguments[0].click();", link_el)

                    wait_for_detail(driver)
                    time.sleep(SHORT_SLEEP)

                    detail_title = safe_text(driver.find_element(By.CSS_SELECTOR, ".title"))
                    detail_content = safe_text(driver.find_element(By.CSS_SELECTOR, ".cont_box"))
                    current_url = driver.current_url.strip()

                    final_title = detail_title or list_title or ""

                    if current_url and current_url in seen_urls:
                        print(f"   ↺ 중복 건너뜀: {final_title}")
                    else:
                        record = make_record(
                            final_title=final_title,
                            current_url=current_url,
                            detail_content=detail_content,
                            item_meta=item_meta,
                        )
                        all_data.append(record)

                        if current_url:
                            seen_urls.add(current_url)

                        page_new_count += 1
                        print(f"   ✔ [{page}-{row_idx + 1}] {final_title}")

                except Exception as e:
                    print(f"   ❌ 상세 수집 실패: {list_title if list_title else '제목미상'} / {e}")
                    continue

            save_json(all_data)
            print(f"   💾 {page}페이지까지 중간저장 완료 (누적 {len(all_data)}건)")

            if detected_total and page >= detected_total:
                print("\n📌 감지된 마지막 페이지까지 완료")
                break

            if page_new_count == 0:
                print("\n📌 이 페이지에서 새 데이터가 없어 종료")
                break

        save_json(all_data)
        print(f"\n✅ 크롤링 완료: 총 {len(all_data)}건 저장")
        print(f"✅ 저장 위치: {SAVE_PATH}")

    finally:
        driver.quit()


if __name__ == "__main__":
    crawl()