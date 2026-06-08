import os
import re

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from bot_settings import (
    append_log,
    clear_alert_settings,
    get_alert_channel_id,
    get_alert_mention,
    read_recent_logs,
    set_alert_settings,
)


SLASH_COMMAND = os.getenv("SLACK_SLASH_COMMAND", "/클컴봇")


def is_admin(client, user_id: str) -> bool:
    admin_ids = {
        user.strip()
        for user in os.getenv("SLACK_ADMIN_USER_IDS", "").split(",")
        if user.strip()
    }
    if admin_ids:
        return user_id in admin_ids

    try:
        profile = client.users_info(user=user_id)["user"]
        return bool(profile.get("is_admin") or profile.get("is_owner"))
    except Exception:
        return False


def help_blocks():
    command = SLASH_COMMAND
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*클컴봇 명령어*\n마이스터넷 클라우드컴퓨팅 질의 알림을 설정하고 확인합니다.",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*설정*\n"
                    f"`{command} 설정` - 현재 채널을 알림 채널로 설정\n"
                    f"`{command} 설정 @그룹` - 알림 때 멘션할 대상도 함께 저장\n\n"
                    "*관리*\n"
                    f"`{command} 상태` - 현재 설정 확인\n"
                    f"`{command} 최근로그` - 최근 이벤트 로그 확인\n"
                    f"`{command} 설정해제` - 알림 설정 삭제\n\n"
                    "*도움*\n"
                    f"`{command}`, `{command} 도움`"
                ),
            },
        },
    ]


def extract_mention(text: str) -> str | None:
    match = re.search(r"(<(?:@|!subteam\^)[^>]+>)", text)
    return match.group(1) if match else None


def command_response(command: str, user_id: str, channel_id: str, client, respond):
    if not is_admin(client, user_id):
        return

    if command in ("", "도움"):
        respond(blocks=help_blocks(), text="클컴봇 도움말", response_type="ephemeral")
        return

    if command.startswith("설정해제"):
        clear_alert_settings()
        append_log(f"Slack 알림 설정 삭제: user={user_id}")
        respond("알림 채널과 멘션 설정을 삭제했습니다.", response_type="ephemeral")
        return

    if command.startswith("상태"):
        alert_channel = get_alert_channel_id()
        mention = get_alert_mention()
        channel_text = f"<#{alert_channel}>" if alert_channel else "설정되지 않음"
        mention_text = mention or "없음"
        respond(
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text": "*클컴봇 상태*"}},
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*알림 채널*\n{channel_text}"},
                        {"type": "mrkdwn", "text": f"*멘션 대상*\n{mention_text}"},
                    ],
                },
            ],
            text="클컴봇 상태",
            response_type="ephemeral",
        )
        return

    if command.startswith("최근로그"):
        logs = read_recent_logs(10)
        body = "\n".join(logs)[-2800:] if logs else "아직 기록된 로그가 없습니다."
        respond(
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*클컴봇 최근로그*\n```{body}```"},
                }
            ],
            text="클컴봇 최근로그",
            response_type="ephemeral",
        )
        return

    if command.startswith("설정"):
        mention = extract_mention(command)
        set_alert_settings(channel_id, mention)
        append_log(f"Slack 알림 설정 변경: channel={channel_id}, mention={mention or 'none'}, user={user_id}")
        mention_text = mention or "없음"
        respond(f"알림 채널: <#{channel_id}>\n멘션 대상: {mention_text}", response_type="ephemeral")
        return

    respond(blocks=help_blocks(), text="클컴봇 도움말", response_type="ephemeral")


def register_handlers(app: App) -> None:
    @app.command(SLASH_COMMAND)
    def handle_cloud_bot_command(ack, body, client, respond):
        ack()
        command = (body.get("text") or "").strip()
        user_id = body.get("user_id")
        channel_id = body.get("channel_id")
        if not user_id or not channel_id:
            return
        command_response(command, user_id, channel_id, client, respond)


def main():
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")
    if not bot_token or bot_token == "xoxb-your-slack-bot-token":
        print("SLACK_BOT_TOKEN에 실제 Slack Bot User OAuth Token을 넣어주세요.")
        return
    if not app_token or app_token == "xapp-your-slack-app-token":
        print("SLACK_APP_TOKEN에 실제 Slack App-Level Token을 넣어주세요.")
        return

    app = App(token=bot_token)
    register_handlers(app)
    append_log("Slack 설정 봇 시작")
    SocketModeHandler(app, app_token).start()


if __name__ == "__main__":
    main()
