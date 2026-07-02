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

update_log_code = r'''


def load_release_notes() -> dict:
    default_notes = {
        "title": "MADBOT Update",
        "summary": "A new bot update was deployed.",
        "added": [],
        "changed": [],
        "commands_added": [],
    }
    try:
        with open("release_notes.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            default_notes.update(data)
    except Exception as exc:
        print(f"Release notes warning: {type(exc).__name__}: {exc}")
    return default_notes


def list_field(items, empty_text="No items listed.") -> str:
    if not items:
        return empty_text
    lines = []
    for item in items:
        if isinstance(item, dict):
            name = str(item.get("name", "")).strip()
            desc = str(item.get("description", "")).strip()
            lines.append(f"• `{name}` — {desc}" if name and desc else f"• {name or desc}")
        else:
            lines.append(f"• {str(item).strip()}")
    return "\n".join(line for line in lines if line.strip())[:1024]


async def post_rank_sale_update_log_once() -> None:
    if getattr(bot, "_deployment_update_log_sent_once", False):
        return
    bot._deployment_update_log_sent_once = True

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

    notes = load_release_notes()
    title = str(notes.get("title") or "MADBOT Update")[:120]
    summary = str(notes.get("summary") or "A new bot update was deployed.")[:300]

    embed = discord.Embed(
        title=f"MADBOT Update — {title}",
        description=summary,
        color=discord.Color.blurple(),
        timestamp=datetime.now(ZoneInfo(TIMEZONE)),
    )
    embed.add_field(name="Added", value=list_field(notes.get("added", [])), inline=False)
    if notes.get("commands_added"):
        embed.add_field(name="Commands Added", value=list_field(notes.get("commands_added", [])), inline=False)
    if notes.get("changed"):
        embed.add_field(name="Changed / Fixed", value=list_field(notes.get("changed", [])), inline=False)
    embed.set_footer(text="MADBOT automatic update log")

    try:
        message = await channel.send(content=f"MADBOT Update — {title}", embed=embed)
        print(f"Automatic update log posted to {channel.id}: {message.jump_url}")
    except discord.Forbidden as exc:
        print(f"Bot cannot send to UPDATE_LOG_CHANNEL_ID={channel_id}: {type(exc).__name__}: {exc}")
    except discord.DiscordException as exc:
        print(f"Could not send automatic update log: {type(exc).__name__}: {exc}")
'''

if "def load_release_notes" not in s:
    s = s.replace("\n\nbot.run(TOKEN)", update_log_code + "\n\nbot.run(TOKEN)")

if "await post_rank_sale_update_log_once()" not in s:
    rep(
        '    if not stat_loop.is_running():\n        stat_loop.start()',
        '    if not stat_loop.is_running():\n        stat_loop.start()\n    await post_rank_sale_update_log_once()',
    )

p.write_text(s, encoding="utf-8")
print("Bot updates patch applied.")
