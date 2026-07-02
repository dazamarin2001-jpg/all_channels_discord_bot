from pathlib import Path

p = Path("bot.py")
s = p.read_text(encoding="utf-8")


def rep(old: str, new: str) -> None:
    global s
    if old in s:
        s = s.replace(old, new)

# Exact Railway variable only. No channel-name fallback.
if "UPDATE_LOG_CHANNEL_ID" not in s:
    rep(
        'TIMEZONE = os.getenv("TIMEZONE", "America/Chicago")\n',
        'TIMEZONE = os.getenv("TIMEZONE", "America/Chicago")\n'
        'UPDATE_LOG_CHANNEL_ID = os.getenv("UPDATE_LOG_CHANNEL_ID")\n',
    )
else:
    rep(
        'UPDATE_LOG_CHANNEL_ID = os.getenv("UPDATE_LOG_CHANNEL_ID") or os.getenv("BOT_UPDATE_CHANNEL_ID")\n',
        'UPDATE_LOG_CHANNEL_ID = os.getenv("UPDATE_LOG_CHANNEL_ID")\n',
    )

auto_update_code = r'''


async def post_rank_sale_update_log_once() -> None:
    if getattr(bot, "_rank_sale_update_log_sent_once", False):
        return
    bot._rank_sale_update_log_sent_once = True

    if not UPDATE_LOG_CHANNEL_ID:
        print("UPDATE_LOG_CHANNEL_ID is not set; automatic update-log notification skipped.")
        return

    try:
        channel_id = int(UPDATE_LOG_CHANNEL_ID)
    except ValueError:
        print("UPDATE_LOG_CHANNEL_ID must be a Discord channel ID number; automatic update-log notification skipped.")
        return

    try:
        channel = bot.get_channel(channel_id)
        if channel is None:
            channel = await bot.fetch_channel(channel_id)
    except discord.Forbidden as exc:
        print(f"Could not access UPDATE_LOG_CHANNEL_ID={channel_id}: {type(exc).__name__}: {exc}")
        return
    except discord.DiscordException as exc:
        print(f"Could not fetch UPDATE_LOG_CHANNEL_ID={channel_id}: {type(exc).__name__}: {exc}")
        return

    if not hasattr(channel, "send"):
        print(f"UPDATE_LOG_CHANNEL_ID={channel_id} is not a sendable channel; automatic update-log notification skipped.")
        return

    embed = discord.Embed(
        title="MADBOT Update — Rank Sales Update",
        description="The rank sales update is live on the latest deployment.",
        color=discord.Color.blurple(),
        timestamp=datetime.now(ZoneInfo(TIMEZONE)),
    )
    embed.add_field(
        name="Added",
        value="• /rank-sale Discord form\n• Google Sheets logging\n• Rank-sales channel log",
        inline=False,
    )
    embed.add_field(
        name="Changed / Fixed",
        value="• Rank sale logging now runs on the latest deployment\n• Update-log notification posts automatically on startup",
        inline=False,
    )
    embed.set_footer(text="MADBOT automatic deployment log")

    try:
        message = await channel.send(
            content="Rank Sale Update Pushed — /rank-sale is live and running on the latest deployment.",
            embed=embed,
        )
        print(f"Automatic update-log notification posted to {channel.id}: {message.jump_url}")
    except discord.Forbidden as exc:
        print(f"Bot cannot send to UPDATE_LOG_CHANNEL_ID={channel_id}: {type(exc).__name__}: {exc}")
    except discord.DiscordException as exc:
        print(f"Could not send automatic update-log notification: {type(exc).__name__}: {exc}")
'''

if "async def post_rank_sale_update_log_once" not in s:
    s = s.replace("\n\nbot.run(TOKEN)", auto_update_code + "\n\nbot.run(TOKEN)")

if "await post_rank_sale_update_log_once()" not in s:
    rep(
        '    if not stat_loop.is_running():\n        stat_loop.start()',
        '    if not stat_loop.is_running():\n        stat_loop.start()\n    await post_rank_sale_update_log_once()',
    )

p.write_text(s, encoding="utf-8")
print("Bot updates patch applied.")
