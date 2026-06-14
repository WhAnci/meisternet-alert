import csv
import os

import discord
from discord.ext import commands

from bot_settings import (
    append_log,
    clear_alert_settings,
    get_alert_channel_id,
    get_alert_role_id,
    read_recent_logs,
    set_alert_settings,
)


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
DATA_FILE = os.getenv("DATA_FILE", "data.csv")


@bot.event
async def on_ready():
    print(f"봇 로그인: {bot.user} ({bot.user.id})")
    append_log(f"설정 봇 로그인: {bot.user}")


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.RoleNotFound) and ctx.command == setup:
        await ctx.reply("멘션 역할은 Discord 역할만 사용할 수 있습니다. 예: `!클컴봇 설정 @알림역할`")
        return

    raise error


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.CommandNotFound):
        return

    raise error


def is_admin(ctx: commands.Context) -> bool:
    return bool(ctx.guild and ctx.author.guild_permissions.administrator)


def read_question_counts() -> list[tuple[str, int]]:
    if not os.path.exists(DATA_FILE):
        return []

    counts: list[tuple[str, int]] = []
    with open(DATA_FILE, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            region = row.get("Region", "").strip()
            count = row.get("Count", "").strip()
            if region and count.isdigit():
                counts.append((region, int(count)))
    return counts


@bot.group(name="클컴봇", invoke_without_command=True)
async def cloud_bot(ctx: commands.Context):
    if not is_admin(ctx):
        return
    await send_help(ctx)


async def send_help(ctx: commands.Context):
    embed = discord.Embed(
        title="클컴봇 명령어",
        description=(
            "마이스터넷 클라우드컴퓨팅 질의 알림을 설정하고 확인합니다.\n"
            "처음 사용할 때는 알림을 받을 채널에서 `!클컴봇 설정`을 실행하세요."
        ),
        color=0x1ABC9C,
    )
    embed.set_author(name="클라우드컴퓨팅 질의 알림 봇")
    embed.add_field(
        name="설정",
        value=(
            "`!클컴봇 설정`\n"
            "현재 채널을 알림 채널로 설정합니다.\n\n"
            "`!클컴봇 설정 @역할`\n"
            "알림 채널을 설정하고 새 질의 알림 때 역할을 멘션합니다."
        ),
        inline=False,
    )
    embed.add_field(
        name="관리",
        value=(
            "`!클컴봇 상태`\n"
            "현재 알림 채널과 멘션 역할을 확인합니다.\n\n"
            "`!클컴봇 질의수`\n"
            "현재 저장된 지역별 질의 수를 확인합니다.\n\n"
            "`!클컴봇 최근로그`\n"
            "최근 봇 이벤트 로그를 확인합니다.\n\n"
            "`!클컴봇 설정해제`\n"
            "알림 채널과 역할 설정을 삭제합니다."
        ),
        inline=True,
    )
    embed.add_field(
        name="도움",
        value=(
            "`!클컴봇`\n"
            "도움말을 보여줍니다.\n\n"
            "`!클컴봇 도움`\n"
            "도움말을 보여줍니다."
        ),
        inline=True,
    )
    embed.add_field(
        name="알림 내용",
        value="새 질의 내용, 상세 링크, ZIP 첨부 링크가 있으면 함께 전송합니다.",
        inline=False,
    )
    embed.set_footer(text="명령어가 반응하지 않으면 Discord Developer Portal에서 Message Content Intent를 켜주세요.")
    await ctx.reply(embed=embed)


@cloud_bot.command(name="도움")
async def help_command(ctx: commands.Context):
    if not is_admin(ctx):
        return
    await send_help(ctx)


@cloud_bot.command(name="설정")
async def setup(ctx: commands.Context, role: discord.Role = None):
    if not is_admin(ctx):
        return

    set_alert_settings(ctx.channel.id, role.id if role else None)
    append_log(
        f"알림 설정 변경: channel={ctx.channel.id}, role={role.id if role else 'none'}, user={ctx.author}"
    )

    lines = [f"알림 채널: {ctx.channel.mention}"]
    if role:
        lines.append(f"멘션 역할: {role.mention}")
    else:
        lines.append("멘션 역할: 없음")

    await ctx.reply("\n".join(lines))


@cloud_bot.command(name="상태")
async def status(ctx: commands.Context):
    if not is_admin(ctx):
        return

    channel_id = get_alert_channel_id()
    role_id = get_alert_role_id()

    embed = discord.Embed(title="클컴봇 상태", color=0x1ABC9C)
    if channel_id:
        channel = bot.get_channel(channel_id)
        channel_text = channel.mention if channel else f"`{channel_id}` (채널을 찾을 수 없음)"
    else:
        channel_text = "설정되지 않음"

    if role_id:
        role = ctx.guild.get_role(role_id) if ctx.guild else None
        role_text = role.mention if role else f"`{role_id}` (역할을 찾을 수 없음)"
    else:
        role_text = "없음"

    embed.add_field(name="알림 채널", value=channel_text, inline=False)
    embed.add_field(name="멘션 역할", value=role_text, inline=False)
    await ctx.reply(embed=embed)


@cloud_bot.command(name="설정해제")
async def clear_setup(ctx: commands.Context):
    if not is_admin(ctx):
        return

    clear_alert_settings()
    append_log(f"알림 설정 삭제: user={ctx.author}")
    await ctx.reply("알림 채널과 멘션 역할 설정을 삭제했습니다.")


@cloud_bot.command(name="최근로그")
async def recent_logs(ctx: commands.Context):
    if not is_admin(ctx):
        return

    logs = read_recent_logs(10)
    embed = discord.Embed(title="클컴봇 최근로그", color=0x1ABC9C)
    if logs:
        embed.description = "```text\n" + "\n".join(logs)[-3900:] + "\n```"
    else:
        embed.description = "아직 기록된 로그가 없습니다."
    await ctx.reply(embed=embed)


@cloud_bot.command(name="질의수")
async def question_counts(ctx: commands.Context):
    if not is_admin(ctx):
        return

    counts = read_question_counts()
    embed = discord.Embed(title="현재 질의 수", color=0x1ABC9C)
    if not counts:
        embed.description = "아직 저장된 질의 수가 없습니다. 크롤러가 한 번 실행된 뒤 다시 확인해주세요."
    else:
        total = sum(count for _, count in counts)
        embed.description = "\n".join(
            f"**{region}**: {count}개" for region, count in counts
        )
        embed.set_footer(text=f"총 {total}개")
    await ctx.reply(embed=embed)


def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token or token == "your-discord-bot-token":
        print("DISCORD_TOKEN에 실제 Discord 봇 토큰을 넣어주세요.")
        return

    try:
        bot.run(token)
    except discord.LoginFailure:
        print("Discord 로그인 실패: DISCORD_TOKEN이 잘못되었거나 재발급이 필요합니다.")


if __name__ == "__main__":
    main()
