# Meister Cloud Slack Bot

마이스터넷에서 **클라우드컴퓨팅** 직종의 질의 데이터를 주기적으로 확인하고, 새 질의가 올라오면 Slack 채널로 알림을 보내는 봇입니다.

원본 프로젝트: [eunhuit/Meister-Bot](https://github.com/eunhuit/Meister-Bot)

## 기능

- Selenium으로 마이스터넷 로그인 및 2차 인증 입력
- `MEISTER_JOB_NAME`에 지정한 직종의 질의 게시판 크롤링
- 이전 실행 결과와 비교해 질의 수 증가 감지
- 새 질의 내용, 상세 링크, ZIP 첨부 링크를 Slack으로 전송
- `/클컴봇 설정` 명령으로 알림 채널과 선택 멘션 설정
- Docker Compose 기반 실행

## Slack 앱 준비

Socket Mode로 실행하므로 외부 공개 URL이 필요 없습니다.

필요 토큰:

- `SLACK_BOT_TOKEN`: Bot User OAuth Token, `xoxb-`로 시작
- `SLACK_APP_TOKEN`: App-Level Token, `xapp-`로 시작, Socket Mode용

권장 Bot Token Scopes:

- `chat:write`
- `commands`
- `channels:history`
- `groups:history`
- `users:read`

Slack 앱에서 **Socket Mode**를 켜세요. 메시지 이벤트 구독은 필요 없습니다.
Slack 앱의 **Slash Commands**에서 `/클컴봇` 명령어를 추가하세요. Request URL은 Socket Mode에서 실제로 호출되지 않지만 Slack 설정상 필수라면 `https://example.com/slack/commands`처럼 임시 URL을 넣어도 됩니다.
역할/유저 그룹 멘션을 저장하려면 Slash Command 설정의 **Escape channels, users, and links sent to your app** 옵션을 켜두세요.

## Docker 실행

```bash
cp .env.example .env
vi .env
docker compose up -d --build
```

Windows PowerShell에서는:

```powershell
copy .env.example .env
notepad .env
docker compose up -d --build
```

Compose는 두 서비스를 실행합니다.

- `setup-bot`: Slack `/클컴봇` 명령 처리
- `crawler`: 마이스터넷 질의 크롤링 및 Slack 알림 전송

로그 확인:

```bash
docker compose logs -f
```

중지:

```bash
docker compose down
```

`bot_settings.json`, `data.csv`, `bot_events.log`는 `bot-data` Docker volume에 저장됩니다.

## 설정

필수 환경변수:

- `MEISTER_ID`: 마이스터넷 ID
- `MEISTER_PASSWORD`: 마이스터넷 비밀번호
- `MEISTER_PASSCODE`: 마이스터넷 2차 인증 입력값
- `SLACK_BOT_TOKEN`: Slack Bot User OAuth Token
- `SLACK_APP_TOKEN`: Slack Socket Mode App-Level Token

선택 환경변수:

- `SLACK_ADMIN_USER_IDS`: 명령어를 허용할 Slack 사용자 ID 목록, 쉼표 구분. 비워두면 Slack 워크스페이스 관리자/소유자만 허용합니다.
- `SLACK_CHANNEL_ID`: 봇 명령 대신 직접 지정할 알림 채널 ID
- `SLACK_MENTION`: 알림 때 함께 보낼 멘션 문자열
- `MEISTER_JOB_NAME`: 기본값 `클라우드컴퓨팅`
- `CHECK_INTERVAL_SECONDS`: 확인 주기, 기본값 `600`

## Slack 명령어

`/클컴봇` 계열 명령어는 관리자만 사용할 수 있습니다. 권한이 없으면 봇이 응답하지 않습니다.

```text
/클컴봇
/클컴봇 도움
```

도움말을 보여줍니다.

```text
/클컴봇 설정
```

현재 채널을 알림 채널로 설정합니다.

```text
/클컴봇 설정 @그룹
```

현재 채널을 알림 채널로 설정하고, 알림 때 해당 멘션을 함께 보냅니다.

```text
/클컴봇 상태
```

현재 알림 채널과 멘션 설정을 보여줍니다.

```text
/클컴봇 최근로그
```

최근 봇 이벤트 로그를 보여줍니다.

```text
/클컴봇 설정해제
```

알림 채널과 멘션 설정을 삭제합니다. 설정을 삭제하면 `crawler`는 다시 설정 대기 상태가 됩니다.

## 한 번만 테스트

`.env`에 아래 값을 넣으면 크롤러가 한 번만 확인하고 종료합니다.

```env
CHECK_INTERVAL_SECONDS=0
```

그다음 크롤러만 실행할 수 있습니다.

```bash
docker compose run --rm crawler
```

첫 실행 시에는 비교 기준이 없으므로 현재 상태를 `data.csv`에 저장만 합니다. 두 번째 실행부터 새 질의 증가를 감지해 Slack 알림을 보냅니다.

## 문제 해결

`SLACK_BOT_TOKEN에 실제 Slack Bot User OAuth Token을 넣어주세요.`가 나오면 `.env`의 `SLACK_BOT_TOKEN`을 확인하세요.

`SLACK_APP_TOKEN에 실제 Slack App-Level Token을 넣어주세요.`가 나오면 Socket Mode용 `xapp-` 토큰을 확인하세요.

`알림 채널이 설정되지 않았습니다. Slack에서 /클컴봇 설정을 먼저 실행하세요.`가 나오면 Slack 채널에서 `/클컴봇 설정`을 실행하면 됩니다.

Rocky Linux에서 `deb.debian.org:80` 접속 실패로 `chromium` 설치가 실패하면 최신 `Dockerfile`을 받은 뒤 다시 빌드하세요. 현재 Dockerfile은 Debian apt 저장소를 HTTPS와 IPv4로 사용하도록 설정되어 있습니다.
