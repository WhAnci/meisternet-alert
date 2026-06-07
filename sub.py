import datetime
import os
import random

import discord
from discord.ext import commands

from bot_settings import clear_alert_settings, get_alert_channel_id, get_alert_role_id, set_alert_settings


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
start_time = datetime.datetime.utcnow()
regions = ["광주", "충남", "전남", "대전", "서울", "충북"]


@bot.event
async def on_ready():
    print(f"봇 로그인: {bot.user} ({bot.user.id})")


@bot.group(name="클컴봇", invoke_without_command=True)
async def cloud_bot(ctx: commands.Context):
    await send_help(ctx)


async def send_help(ctx: commands.Context):
    embed = discord.Embed(
        title="클컴봇 도움",
        description="클라우드컴퓨팅 질의 알림 봇 명령어입니다.",
        color=0x1ABC9C,
    )
    embed.add_field(
        name="!클컴봇 설정 [@역할]",
        value="현재 채널을 알림 채널로 설정합니다. 역할은 선택 사항입니다.",
        inline=False,
    )
    embed.add_field(
        name="!클컴봇 상태",
        value="현재 알림 채널과 멘션 역할 설정을 확인합니다.",
        inline=False,
    )
    embed.add_field(
        name="!클컴봇 설정해제",
        value="알림 채널과 역할 설정을 삭제합니다.",
        inline=False,
    )
    embed.add_field(
        name="!클컴봇 도움",
        value="이 도움말을 보여줍니다.",
        inline=False,
    )
    await ctx.reply(embed=embed)


@cloud_bot.command(name="도움")
async def help_command(ctx: commands.Context):
    await send_help(ctx)


@cloud_bot.command(name="설정")
async def setup(ctx: commands.Context, role: discord.Role = None):
    set_alert_settings(ctx.channel.id, role.id if role else None)

    lines = [f"알림 채널: {ctx.channel.mention}"]
    if role:
        lines.append(f"멘션 역할: {role.mention}")
    else:
        lines.append("멘션 역할: 없음")

    await ctx.reply("\n".join(lines))


@cloud_bot.command(name="상태")
async def status(ctx: commands.Context):
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
    clear_alert_settings()
    await ctx.reply("알림 채널과 멘션 역할 설정을 삭제했습니다.")


@bot.command(name="안녕")
async def hi(ctx: commands.Context):
    await ctx.reply(f"안녕하세요, {ctx.author.mention}!")


@bot.command(name="1과제")
async def task1(ctx: commands.Context):
    await ctx.reply(f"1과제 뽑힌 지역은 **{random.choice(regions)}** 입니다!")


@bot.command(name="2과제")
async def task2(ctx: commands.Context):
    await ctx.reply(f"2과제 뽑힌 지역은 **{random.choice(regions)}** 입니다!")


@bot.command(name="3과제")
async def task3(ctx: commands.Context):
    await ctx.reply(f"3과제 뽑힌 지역은 **{random.choice(regions)}** 입니다!")


@bot.command(name="업타임")
async def uptime(ctx: commands.Context):
    now = datetime.datetime.utcnow()
    delta = now - start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    await ctx.reply(f"봇 업타임: {hours}시간 {minutes}분 {seconds}초")


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
