import datetime
import os
import random

import discord
from discord.ext import commands

from bot_settings import set_alert_settings


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
    await ctx.reply("사용법: `!클컴봇 설정 [@역할]`")


@cloud_bot.command(name="설정")
async def setup(ctx: commands.Context, role: discord.Role = None):
    set_alert_settings(ctx.channel.id, role.id if role else None)

    lines = [f"알림 채널: {ctx.channel.mention}"]
    if role:
        lines.append(f"멘션 역할: {role.mention}")
    else:
        lines.append("멘션 역할: 없음")

    await ctx.reply("\n".join(lines))


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
