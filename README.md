# Meister Cloud Discord Bot

마이스터넷에서 **클라우드컴퓨팅** 직종의 질의 데이터를 주기적으로 확인하고, 새 질의가 올라오면 Discord 채널로 알림을 보내는 봇입니다.

원본 프로젝트: [eunhuit/Meister-Bot](https://github.com/eunhuit/Meister-Bot)

## 기능

- Selenium으로 마이스터넷 로그인 및 2차 인증 입력
- `MEISTER_JOB_NAME`에 지정한 직종의 질의 게시판 크롤링
- 이전 실행 결과와 비교해 질의 수 증가 감지
- 새 질의 내용을 Discord Embed로 전송
- 봇 알림 메시지에 답장으로 `요약`을 보내면 Gemini API로 한국어 요약
- `!클컴봇 설정` 명령으로 알림 채널과 선택 역할 멘션 설정
- Docker Compose 기반 실행

## Docker 실행

기본 실행 방식은 Docker Compose입니다.

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

- `setup-bot`: Discord `!클컴봇 설정` 명령 처리
- `crawler`: 마이스터넷 질의 크롤링 및 Discord 알림 전송

로그 확인:

```bash
docker compose logs -f
```

중지:

```bash
docker compose down
```

`bot_settings.json`과 `data.csv`는 `bot-data` Docker volume에 저장됩니다.

## 설정

필수 환경변수:

- `MEISTER_ID`: 마이스터넷 ID
- `MEISTER_PASSWORD`: 마이스터넷 비밀번호
- `MEISTER_PASSCODE`: 마이스터넷 2차 인증 입력값
- `DISCORD_TOKEN`: Discord 봇 토큰
- `GEMINI_API_KEY`: Gemini API 키 (`요약` 기능 사용 시 필수)

선택 환경변수:

- `DISCORD_CHANNEL_ID`: 봇 명령 대신 직접 지정할 알림 채널 ID
- `DISCORD_ROLE_ID`: 멘션할 역할 ID
- `DISCORD_USER_ID`: 함께 멘션할 사용자 ID
- `MEISTER_JOB_NAME`: 기본값 `클라우드컴퓨팅`
- `CHECK_INTERVAL_SECONDS`: 확인 주기, 기본값 `600`
- `GEMINI_MODEL`: 사용할 Gemini 모델, 기본값 `gemini-2.0-flash`

## Discord 알림 채널 설정

Discord Developer Portal에서 봇의 **Message Content Intent**를 켜야 `!` 명령어가 동작합니다.

`docker compose up -d --build`로 봇을 실행한 뒤 Discord에서 알림을 받을 채널에 들어가 아래 명령을 실행하세요.

```text
!클컴봇 설정
```

역할 멘션도 함께 지정할 수 있습니다.

```text
!클컴봇 설정 @알림역할
```

역할은 선택 사항입니다. 비워두면 역할 멘션 없이 알림만 전송합니다. 설정이 끝나면 `bot_settings.json`에 채널 ID와 역할 ID가 저장됩니다. 이후 `crawler` 서비스가 이 설정대로 질의 알림을 보냅니다.

`!클컴봇` 계열 명령어는 Discord 서버 관리자만 사용할 수 있습니다. 관리자가 아니면 봇이 응답하지 않습니다.

봇이 보낸 질의 알림 메시지를 Discord에서 **답장**한 뒤 메시지 내용으로 아래처럼 입력하면 됩니다.

```text
요약
```

Gemini API 키가 없거나 API 호출에 실패하면 오류 안내를 답장합니다.

## Discord 명령어

```text
!클컴봇
!클컴봇 도움
```

도움말을 보여줍니다.

```text
!클컴봇 상태
```

현재 알림 채널과 멘션 역할 설정을 보여줍니다.

```text
!클컴봇 최근로그
```

최근 봇 이벤트 로그를 보여줍니다.

```text
!클컴봇 설정해제
```

알림 채널과 멘션 역할 설정을 삭제합니다. 설정을 삭제하면 `crawler`는 다시 설정 대기 상태가 됩니다.

## 한 번만 테스트

`.env`에 아래 값을 넣으면 크롤러가 한 번만 확인하고 종료합니다.

```env
CHECK_INTERVAL_SECONDS=0
```

그다음 크롤러만 실행할 수 있습니다.

```bash
docker compose run --rm crawler
```

첫 실행 시에는 비교 기준이 없으므로 현재 상태를 `data.csv`에 저장만 합니다. 두 번째 실행부터 새 질의 증가를 감지해 Discord 알림을 보냅니다.

## 문제 해결

`Discord 로그인 실패: DISCORD_TOKEN이 잘못되었거나 재발급이 필요합니다.`가 나오면 Discord Developer Portal에서 봇 토큰을 새로 발급해 `.env`의 `DISCORD_TOKEN`을 교체하세요.

`알림 채널이 설정되지 않았습니다. Discord에서 !클컴봇 설정을 먼저 실행하세요.`가 나오면 `setup-bot`이 정상 로그인된 뒤 Discord 채널에서 `!클컴봇 설정`을 실행하면 됩니다. 설정 전까지 `crawler`는 주기적으로 대기합니다.

Rocky Linux에서 `deb.debian.org:80` 접속 실패로 `chromium` 설치가 실패하면 최신 `Dockerfile`을 받은 뒤 다시 빌드하세요. 현재 Dockerfile은 Debian apt 저장소를 HTTPS와 IPv4로 사용하도록 설정되어 있습니다.
