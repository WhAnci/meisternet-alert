import asyncio
import csv
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urljoin

import discord
from bot_settings import append_log, get_alert_channel_id, get_alert_role_id
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


BASE_URL = "https://meister.hrdkorea.or.kr"
MAIN_URL = f"{BASE_URL}/main/main.do"
QUESTIONS_URL = (
    f"{BASE_URL}/sub/3/3/7/skillMatchTournament/taskQuestionsList.do"
)
DATA_FILE = os.getenv("DATA_FILE", "data.csv")
MAX_EMBED_COMMENT_LENGTH = 3500


class AlertChannelNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    meister_id: str
    meister_password: str
    meister_passcode: str
    discord_token: str
    discord_channel_id: int
    discord_role_id: Optional[int]
    discord_user_id: Optional[int]
    job_name: str
    interval_seconds: int
    headless: bool
    browser: str
    chrome_driver_path: Optional[str]
    chrome_binary_path: Optional[str]


@dataclass(frozen=True)
class QuestionRow:
    region: str
    count: int
    title: str
    detail_url: str


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} 환경변수가 필요합니다.")
    return value


def optional_int_env(name: str) -> Optional[int]:
    value = os.getenv(name)
    return int(value) if value else None


def load_config() -> Config:
    discord_channel_id = get_alert_channel_id()
    if not discord_channel_id:
        raise AlertChannelNotConfigured("알림 채널이 설정되지 않았습니다. Discord에서 !클컴봇 설정을 먼저 실행하세요.")

    return Config(
        meister_id=required_env("MEISTER_ID"),
        meister_password=required_env("MEISTER_PASSWORD"),
        meister_passcode=required_env("MEISTER_PASSCODE"),
        discord_token=required_env("DISCORD_TOKEN"),
        discord_channel_id=discord_channel_id,
        discord_role_id=get_alert_role_id(),
        discord_user_id=optional_int_env("DISCORD_USER_ID"),
        job_name=os.getenv("MEISTER_JOB_NAME", "클라우드컴퓨팅"),
        interval_seconds=int(os.getenv("CHECK_INTERVAL_SECONDS", "600")),
        headless=os.getenv("SELENIUM_HEADLESS", "true").lower() != "false",
        browser=os.getenv("BROWSER", "chrome").lower(),
        chrome_driver_path=os.getenv("CHROME_DRIVER_PATH") or None,
        chrome_binary_path=os.getenv("CHROME_BINARY_PATH") or None,
    )


def build_driver(config: Config) -> webdriver.Chrome:
    if config.browser == "edge":
        options = EdgeOptions()
        if config.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1600,2000")
        if config.chrome_binary_path:
            options.binary_location = config.chrome_binary_path

        service = (
            EdgeService(config.chrome_driver_path)
            if config.chrome_driver_path
            else EdgeService()
        )
        return webdriver.Edge(service=service, options=options)

    options = Options()
    if config.headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1600,2000")
    if config.chrome_binary_path:
        options.binary_location = config.chrome_binary_path

    service = (
        Service(config.chrome_driver_path)
        if config.chrome_driver_path
        else Service()
    )
    return webdriver.Chrome(service=service, options=options)


def safe_click(driver: webdriver.Chrome, element) -> None:
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    time.sleep(0.2)
    driver.execute_script("arguments[0].click();", element)


def login(driver: webdriver.Chrome, wait: WebDriverWait, config: Config) -> None:
    driver.get(MAIN_URL)

    safe_click(driver, wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "/html/body/div[2]/div[3]/div[1]/div/div/div[1]/ul/li[1]/a")
        )
    ))

    wait.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "/html/body/div[2]/div[4]/div[3]/div[4]/div[2]/fieldset/div/form/dl[1]/dd/input",
            )
        )
    ).send_keys(config.meister_id)

    wait.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "/html/body/div[2]/div[4]/div[3]/div[4]/div[2]/fieldset/div/form/dl[2]/dd[1]/input",
            )
        )
    ).send_keys(config.meister_password)

    login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#loginFrm > a")))
    safe_click(driver, login_button)

    passcode_input = wait.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "/html/body/div[2]/div[4]/div[4]/div/div/div[2]/div[2]/div[1]/input",
            )
        )
    )
    passcode_input.send_keys(config.meister_passcode)

    safe_click(driver, wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="myModal"]/div/div/div[2]/div[2]/div[1]/button')
        )
    ))


def select_job(driver: webdriver.Chrome, wait: WebDriverWait, job_name: str) -> None:
    driver.get(QUESTIONS_URL)

    select_element = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "/html/body/div[2]/div[4]/div[3]/form/div[1]/div/select[2]")
        )
    )
    select = Select(select_element)
    option_texts = [option.text.strip() for option in select.options]
    normalized_job_name = normalize_job_name(job_name)
    matched = next(
        (
            text
            for text in option_texts
            if normalized_job_name in normalize_job_name(text)
        ),
        None,
    )
    if not matched:
        choices = ", ".join(text for text in option_texts if text)[:1000]
        raise RuntimeError(f"직종 '{job_name}'을 찾지 못했습니다. 선택 가능 항목: {choices}")

    select.select_by_visible_text(matched)
    safe_click(driver, wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "/html/body/div[2]/div[4]/div[3]/form/div[1]/div/div/input[2]")
        )
    ))


def extract_count(title: str) -> int:
    match = re.search(r"\[(\d+)\]", title)
    return int(match.group(1)) if match else 0


def extract_question_key(title: str) -> str:
    return re.sub(r"\s*\[\d+\]\s*$", "", title).strip()


def normalize_job_name(value: str) -> str:
    return re.sub(r"\s+", "", value)


def parse_question_rows(driver: webdriver.Chrome, wait: WebDriverWait) -> List[QuestionRow]:
    parsed: List[QuestionRow] = []
    rows = wait.until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "/html/body/div[2]/div[4]/div[3]/form/div[1]/table/tbody/tr")
        )
    )

    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) < 4:
            continue

        title = cells[2].get_attribute("innerText").strip()
        count = extract_count(title)
        if not title or count <= 0:
            continue

        links = cells[2].find_elements(By.TAG_NAME, "a")
        detail_url = ""
        if links:
            href = links[0].get_attribute("href") or ""
            detail_url = urljoin(BASE_URL, href)

        parsed.append(
            QuestionRow(
                region=extract_question_key(title),
                count=count,
                title=title,
                detail_url=detail_url,
            )
        )

    return parsed


def scrape_all_rows(driver: webdriver.Chrome, wait: WebDriverWait) -> List[QuestionRow]:
    result = parse_question_rows(driver, wait)

    while True:
        paging_links = driver.find_elements(By.CSS_SELECTOR, "div.paging a")
        try:
            active = driver.find_element(By.CSS_SELECTOR, "div.paging a.active")
            current_page = int(active.text) if active.text.isdigit() else 1
        except Exception:
            current_page = 1

        next_page = None
        for link in paging_links:
            if link.text.isdigit() and int(link.text) == current_page + 1:
                next_page = link
                break

        if not next_page:
            next_page = next((link for link in paging_links if "다음" in link.text), None)
        if not next_page:
            break

        driver.execute_script("arguments[0].click();", next_page)
        time.sleep(1)
        result.extend(parse_question_rows(driver, wait))

    return result


def load_previous_rows() -> Dict[str, QuestionRow]:
    if not os.path.exists(DATA_FILE):
        return {}

    previous: Dict[str, QuestionRow] = {}
    with open(DATA_FILE, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            region = row["Region"]
            previous[region] = QuestionRow(
                region=region,
                count=int(row["Count"]),
                title=row.get("Title", ""),
                detail_url=row.get("DetailUrl", ""),
            )
    return previous


def save_current_rows(rows: Iterable[QuestionRow]) -> None:
    with open(DATA_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Region", "Count", "Title", "DetailUrl"])
        for row in rows:
            writer.writerow([row.region, row.count, row.title, row.detail_url])


def find_increases(
    previous: Dict[str, QuestionRow], current: List[QuestionRow]
) -> List[Tuple[QuestionRow, int]]:
    if previous and all(row.count == 0 for row in previous.values()):
        print("이전 기준 데이터 형식이 오래되어 현재 크롤링 결과로 기준을 다시 저장합니다.")
        return []

    increases: List[Tuple[QuestionRow, int]] = []
    for row in current:
        old = previous.get(row.region)
        if old and row.count > old.count:
            increases.append((row, old.count))
        elif previous and not old:
            increases.append((row, 0))
    return increases


def collect_zip_links_from_element(element) -> List[str]:
    links: List[str] = []
    for anchor in element.find_elements(By.TAG_NAME, "a"):
        href = anchor.get_attribute("href") or ""
        text = anchor.get_attribute("innerText") or ""
        if ".zip" in href.lower() or ".zip" in text.lower():
            links.append(urljoin(BASE_URL, href))
    return links


def read_new_comments(
    driver: webdriver.Chrome, wait: WebDriverWait, row: QuestionRow, old_count: int
) -> Tuple[str, List[str]]:
    if not row.detail_url:
        return "상세 질의 링크를 찾지 못했습니다. 마이스터넷에서 직접 확인해주세요.", []

    driver.get(row.detail_url)
    try:
        comments = wait.until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "comm_view"))
        )
    except TimeoutException:
        return "상세 페이지에서 질의 내용을 찾지 못했습니다. 마이스터넷에서 직접 확인해주세요.", []

    start = max(old_count, 0)
    end = min(row.count, len(comments))
    if start < end:
        new_comments: List[str] = []
        zip_links: List[str] = []
        seen_links: Set[str] = set()

        for comment in comments[start:end]:
            text = comment.text.strip()
            if text:
                new_comments.append(text)
            for link in collect_zip_links_from_element(comment):
                if link not in seen_links:
                    zip_links.append(link)
                    seen_links.add(link)

        if new_comments:
            return "\n\n---\n\n".join(new_comments), zip_links

    if len(comments) >= row.count and row.count > 0:
        latest_comment = comments[row.count - 1]
        latest = latest_comment.text.strip()
        if latest:
            return latest, collect_zip_links_from_element(latest_comment)

    return f"새 질의 내용을 찾지 못했습니다. 현재 표시된 질의 수: {len(comments)}", []


def split_comment_for_alert(text: str) -> Tuple[str, Optional[str]]:
    cleaned = text.strip() or "내용 없음"
    if len(cleaned) <= MAX_EMBED_COMMENT_LENGTH:
        return cleaned, None

    first = cleaned[:MAX_EMBED_COMMENT_LENGTH].rstrip()
    remaining = cleaned[MAX_EMBED_COMMENT_LENGTH:].strip()
    if len(remaining) > MAX_EMBED_COMMENT_LENGTH:
        remaining = (
            remaining[: MAX_EMBED_COMMENT_LENGTH - 32].rstrip()
            + "\n\n... 내용이 더 있어 일부 생략되었습니다."
        )
    return first, remaining


def escape_code_block(text: str) -> str:
    return text.replace("```", "`\u200b``")


def code_block(text: str) -> str:
    return f"```text\n{escape_code_block(text)}\n```"


def format_alert_links(detail_url: str, zip_links: List[str], limit: int = 5) -> Optional[str]:
    lines: List[str] = []
    if detail_url:
        lines.append(f"[상세 링크]({detail_url})")

    for link in zip_links[:limit]:
        lines.append(f"[다운로드]({link})")

    if len(zip_links) > limit:
        lines.append(f"외 ZIP 첨부파일 {len(zip_links) - limit}개")

    return "\n".join(lines) if lines else None


class OneTimeBot(discord.Client):
    def __init__(
        self,
        config: Config,
        row: QuestionRow,
        old_count: int,
        comment: str,
        zip_links: List[str],
    ):
        intents = discord.Intents.default()
        intents.guilds = True
        super().__init__(intents=intents)
        self.config = config
        self.row = row
        self.old_count = old_count
        self.comment = comment
        self.zip_links = zip_links

    async def on_ready(self) -> None:
        print(f"봇 로그인: {self.user} ({self.user.id})")
        channel = self.get_channel(self.config.discord_channel_id)
        if not channel:
            print("채널을 찾을 수 없습니다.")
            await self.close()
            return

        allowed = discord.AllowedMentions(users=True, roles=True)
        mentions: List[str] = []
        if self.config.discord_role_id:
            mentions.append(f"<@&{self.config.discord_role_id}>")
        if self.config.discord_user_id:
            mentions.append(f"<@!{self.config.discord_user_id}>")

        first_comment, remaining_comment = split_comment_for_alert(self.comment)
        title = f"{self.row.region} 새 질의 알림"
        description = (
            f"질의 수가 **{self.old_count}개 -> {self.row.count}개**로 증가했습니다.\n\n"
            f"{code_block(first_comment)}"
        )

        embed = discord.Embed(title=title, description=description, color=0x1ABC9C)
        alert_links = format_alert_links(self.row.detail_url, self.zip_links)
        if alert_links:
            embed.add_field(name="링크", value=alert_links, inline=False)
        embed.set_footer(text="마이스터넷 질의 게시판 자동 감지")

        await channel.send(
            content=" ".join(mentions) if mentions else None,
            embed=embed,
            allowed_mentions=allowed,
        )

        if remaining_comment:
            continued_embed = discord.Embed(
                title=f"{self.row.region} 질의 내용 계속",
                description=code_block(remaining_comment),
                color=0x1ABC9C,
            )
            continued_embed.set_footer(text="앞 알림의 이어지는 내용입니다.")
            await channel.send(embed=continued_embed)

        await self.close()


async def send_discord_alert(
    config: Config,
    row: QuestionRow,
    old_count: int,
    comment: str,
    zip_links: List[str],
) -> None:
    async with OneTimeBot(config, row, old_count, comment, zip_links) as bot:
        await bot.start(config.discord_token)


def ensure_questions_page(
    driver: webdriver.Chrome, wait: WebDriverWait, config: Config
) -> None:
    try:
        select_job(driver, wait, config.job_name)
    except Exception:
        print("로그인 상태를 확인했습니다. 세션이 만료되었거나 접근이 막혀 재로그인합니다.")
        append_log("세션 만료 또는 접근 실패 감지: 재로그인 시도")
        login(driver, wait, config)
        select_job(driver, wait, config.job_name)


def check_once(
    config: Config,
    driver: webdriver.Chrome,
    wait: WebDriverWait,
    refresh_baseline: bool = False,
) -> None:
    ensure_questions_page(driver, wait, config)
    current_rows = scrape_all_rows(driver, wait)

    if refresh_baseline:
        save_current_rows(current_rows)
        print("앱 시작 기준으로 현재 질의 개수를 새로 저장했습니다.")
        append_log("앱 시작 기준 데이터 갱신")
        return

    previous_rows = load_previous_rows()
    increases = find_increases(previous_rows, current_rows)

    if not previous_rows:
        print("기준 데이터가 없어 현재 데이터를 저장하고 종료합니다.")
        append_log("기준 데이터 생성")
    elif not increases:
        print("값의 변화가 없습니다.")

    for row, old_count in increases:
        print(f"{row.title}의 값이 {old_count}에서 {row.count}로 증가했습니다.")
        append_log(f"새 질의 감지: {row.title} ({old_count} -> {row.count})")
        comment, zip_links = read_new_comments(driver, wait, row, old_count)
        if zip_links:
            print(f"ZIP 첨부파일 {len(zip_links)}개를 찾았습니다.")
            append_log(f"ZIP 첨부파일 감지: {len(zip_links)}개")
        asyncio.run(send_discord_alert(config, row, old_count, comment, zip_links))
        append_log(f"Discord 알림 전송 완료: {row.region}")

    save_current_rows(current_rows)


def main() -> None:
    driver: Optional[webdriver.Chrome] = None
    wait: Optional[WebDriverWait] = None
    refresh_baseline_on_start = True

    while True:
        try:
            config = load_config()
            if driver is None:
                driver = build_driver(config)
                wait = WebDriverWait(driver, 15)
            check_once(config, driver, wait, refresh_baseline_on_start)
            refresh_baseline_on_start = False
        except AlertChannelNotConfigured as exc:
            print(exc)
        except WebDriverException as exc:
            print(f"브라우저 오류가 발생해 다음 주기에 새 브라우저로 재시도합니다: {exc}")
            append_log("브라우저 오류 발생: 다음 주기에 새 브라우저로 재시도")
            if driver:
                driver.quit()
            driver = None
            wait = None
        except Exception as exc:
            print(f"실행 중 오류: {exc}")
            append_log(f"실행 오류: {exc}")

        interval_seconds = int(os.getenv("CHECK_INTERVAL_SECONDS", "600"))
        if interval_seconds <= 0:
            break
        time.sleep(interval_seconds)

    if driver:
        driver.quit()


if __name__ == "__main__":
    main()
