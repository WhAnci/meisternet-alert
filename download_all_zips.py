import argparse
import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Iterable, List, Set
from urllib.parse import parse_qs, unquote, urlparse

import requests
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from main import (
    Config,
    QuestionRow,
    build_driver,
    collect_zip_links_from_element,
    ensure_questions_page,
    optional_int_env,
    required_env,
    scrape_all_rows,
)


DEFAULT_DOWNLOAD_DIR = r"C:\Users\competitor\Documents\tmp\worldskills-tmp"
REQUEST_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class ZipAttachment:
    row: QuestionRow
    url: str
    uploaded_at: str


def load_env_file(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


def load_download_config() -> Config:
    return Config(
        meister_id=required_env("MEISTER_ID"),
        meister_password=required_env("MEISTER_PASSWORD"),
        meister_passcode=required_env("MEISTER_PASSCODE"),
        discord_token=os.getenv("DISCORD_TOKEN", ""),
        discord_channel_id=0,
        discord_role_id=None,
        discord_user_id=optional_int_env("DISCORD_USER_ID"),
        job_name=os.getenv("MEISTER_JOB_NAME", "클라우드컴퓨팅"),
        interval_seconds=0,
        headless=os.getenv("SELENIUM_HEADLESS", "true").lower() != "false",
        browser=os.getenv("BROWSER", "chrome").lower(),
        chrome_driver_path=os.getenv("CHROME_DRIVER_PATH") or None,
        chrome_binary_path=os.getenv("CHROME_BINARY_PATH") or None,
    )


def safe_filename(value: str) -> str:
    filename = unquote(value).split("?")[0].split("#")[0]
    filename = filename.rsplit("/", 1)[-1].strip() or "download.zip"
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)
    return filename if filename.lower().endswith(".zip") else f"{filename}.zip"


def task_directory_name(row: QuestionRow) -> str:
    return safe_filename(row.region).removesuffix(".zip")


def filename_timestamp(value: str) -> str:
    normalized_match = re.search(r"(\d{8})_(\d{6})", value)
    if normalized_match:
        date, time = normalized_match.groups()
        return f"{date}_{time}"

    match = re.search(
        r"(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})",
        value,
    )
    if not match:
        match = re.search(r"(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", value)
    if not match:
        return "unknown_time"
    year, month, day, hour, minute, second = match.groups()[:6]
    return f"{year}{month}{day}_{hour}{minute}{second}"


def unique_path(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    index = 2
    while True:
        candidate = directory / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def extract_comment_timestamp(comment) -> str:
    timestamps = comment.find_elements(By.CSS_SELECTOR, "span.point01")
    if not timestamps:
        return ""
    return timestamps[0].get_attribute("innerText").strip()


def timestamp_from_download_url(url: str) -> str:
    parsed = urlparse(url)
    file_rename = parse_qs(parsed.query).get("fileRename", [""])[0]
    return filename_timestamp(file_rename)


def is_inside_comment(anchor) -> bool:
    return bool(
        anchor.find_elements(
            By.XPATH,
            "./ancestor::*[contains(concat(' ', normalize-space(@class), ' '), ' comm_view ')]",
        )
    )


def collect_original_zip_attachments(driver, row: QuestionRow) -> List[ZipAttachment]:
    found: List[ZipAttachment] = []
    for anchor in driver.find_elements(By.TAG_NAME, "a"):
        if is_inside_comment(anchor):
            continue

        href = anchor.get_attribute("href") or ""
        text = anchor.get_attribute("innerText") or ""
        if ".zip" not in href.lower() and ".zip" not in text.lower():
            continue

        found.append(
            ZipAttachment(
                row=row,
                url=urlparse(href).geturl(),
                uploaded_at=timestamp_from_download_url(href),
            )
        )
    return found


def open_detail_page(driver, wait: WebDriverWait, config: Config, row: QuestionRow) -> bool:
    for attempt in range(2):
        try:
            driver.get(row.detail_url)
            wait.until(lambda current_driver: current_driver.find_elements(By.CLASS_NAME, "comm_view"))
            return True
        except UnexpectedAlertPresentException:
            try:
                driver.switch_to.alert.accept()
            except Exception:
                pass
        except TimeoutException:
            if attempt == 1:
                return False

        print(f"[RETRY] {row.region}: 세션 확인 후 상세 페이지 재시도")
        ensure_questions_page(driver, wait, config)

    return False


def collect_all_zip_attachments(
    driver, wait: WebDriverWait, config: Config, rows: Iterable[QuestionRow]
) -> List[ZipAttachment]:
    found: List[ZipAttachment] = []
    seen_links: Set[str] = set()

    for row in rows:
        if not row.detail_url:
            print(f"[SKIP] {row.region}: 상세 링크 없음")
            continue

        if not open_detail_page(driver, wait, config, row):
            print(f"[SKIP] {row.region}: 질의 댓글 영역을 찾지 못함")
            continue
        row_count = 0
        for attachment in collect_original_zip_attachments(driver, row):
            if attachment.url in seen_links:
                continue
            seen_links.add(attachment.url)
            found.append(attachment)
            row_count += 1
        comments = driver.find_elements(By.CLASS_NAME, "comm_view")

        for comment in comments:
            uploaded_at = extract_comment_timestamp(comment)
            for link in collect_zip_links_from_element(comment):
                if link in seen_links:
                    continue
                seen_links.add(link)
                found.append(ZipAttachment(row=row, url=link, uploaded_at=uploaded_at))
                row_count += 1

        print(f"[SCAN] {row.region}: ZIP {row_count}개")

    return found


def make_session_from_driver(driver) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": driver.execute_script("return navigator.userAgent;"),
            "Referer": driver.current_url,
        }
    )
    for cookie in driver.get_cookies():
        session.cookies.set(
            cookie["name"],
            cookie["value"],
            domain=cookie.get("domain"),
            path=cookie.get("path", "/"),
        )
    return session


def download_zip(session: requests.Session, attachment: ZipAttachment, directory: Path) -> Path:
    url = attachment.url
    response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    content_disposition = response.headers.get("Content-Disposition", "")
    filename_match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', content_disposition)
    if filename_match:
        filename = safe_filename(filename_match.group(1))
    else:
        filename = safe_filename(urlparse(url).path)

    filename = f"{filename_timestamp(attachment.uploaded_at)}__{filename}"
    path = unique_path(directory, filename)
    path.write_bytes(response.content)
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="마이스터넷 클라우드컴퓨팅 과제의 모든 ZIP 파일을 다운로드합니다."
    )
    parser.add_argument(
        "--download-dir",
        default=DEFAULT_DOWNLOAD_DIR,
        help=f"ZIP 파일 저장 디렉터리. 기본값: {DEFAULT_DOWNLOAD_DIR}",
    )
    return parser.parse_args()


def main() -> None:
    load_env_file()
    args = parse_args()
    download_dir = Path(args.download_dir)
    download_dir.mkdir(parents=True, exist_ok=True)

    config = load_download_config()
    driver = build_driver(config)
    wait = WebDriverWait(driver, 15)

    try:
        ensure_questions_page(driver, wait, config)
        rows = scrape_all_rows(driver, wait)
        print(f"[INFO] 과제 {len(rows)}개 조회 완료")
        for row in rows:
            (download_dir / task_directory_name(row)).mkdir(parents=True, exist_ok=True)

        zip_attachments = collect_all_zip_attachments(driver, wait, config, rows)
        print(f"[INFO] ZIP 링크 {len(zip_attachments)}개 발견")

        session = make_session_from_driver(driver)
        for index, attachment in enumerate(zip_attachments, start=1):
            task_dir = download_dir / task_directory_name(attachment.row)
            task_dir.mkdir(parents=True, exist_ok=True)
            path = download_zip(session, attachment, task_dir)
            print(f"[{index}/{len(zip_attachments)}] {attachment.row.region}: {path}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
