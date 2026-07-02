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


def build_command_update_fields() -> list[tuple[str, str]]:
    commands = []
    try:
        commands = list(bot.tree.get_commands())
    except Exception:
        commands = []

    if not commands:
        return [("Commands", "No slash commands were found on this deployment.")]

    lines = []
    for command in sorted(commands, key=lambda item: item.name):
        name = getattr(command, "name", "unknown")
        description = getattr(command, "description", "No description.") or "No description."
        lines.append(f"• `/{name}` — {description}")

    fields = []
    current = ""
    field_number = 1
    for line in lines:
        if len(current) + len(line) + 1 > 1000:
            title = "Commands Added / Updated" if field_number == 1 else f"Commands Added / Updated {field_number}"
            fields.append((title, current.strip()))
            field_number += 1
            current = ""
        current += line + "\n"

    if current.strip():
        title = "Commands Added / Updated" if field_number == 1 else f"Commands Added / Updated {field_number}"
        fields.append((title, current.strip()))

    return fields


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

    if not hasattr(channel, "send"):
        print(f"UPDATE_LOG_CHANNEL_ID={channel_id} is not a sendable channel; automatic update-log notification skipped.")
        return

    embed = discord.Embed(
        title="MADBOT Deployment Update",
        description="A new bot update was deployed. Below are the commands currently live on this deployment.",
        color=discord.Color.blurple(),
        timestamp=datetime.now(ZoneInfo(TIMEZONE)),
    )

    for name, value in build_command_update_fields():
        embed.add_field(name=name, value=value, inline=False)

    embed.add_field(
        name="Update Log Status",
        value="Automatic update-log posting is active and using the configured update-log channel.",
        inline=False,
    )
    embed.set_footer(text="MADBOT automatic deployment log")

    try:
        message = await channel.send(
            content="MADBOT Deployment Update — new bot changes are live.",
            embed=embed,
        )
        print(f"Automatic deployment update posted to {channel.id}: {message.jump_url}")
    except discord.Forbidden as exc:
        print(f"Bot cannot send to UPDATE_LOG_CHANNEL_ID={channel_id}: {type(exc).__name__}: {exc}")
    except discord.DiscordException as exc:
        print(f"Could not send automatic deployment update: {type(exc).__name__}: {exc}")
'''

if "async def post_rank_sale_update_log_once" not in s and "async def post_deployment_update_log_once" not in s:
    s = s.replace("\n\nbot.run(TOKEN)", auto_update_code + "\n\nbot.run(TOKEN)")

if "await post_rank_sale_update_log_once()" not in s:
    rep(
        '    if not stat_loop.is_running():\n        stat_loop.start()',
        '    if not stat_loop.is_running():\n        stat_loop.start()\n    await post_rank_sale_update_log_once()',
    )

# Refresh older already-patched bot.py deployments to use a generic deployment update instead of a hard-coded rank-sales message.
rep('title="MADBOT Update — Rank Sales Update"', 'title="MADBOT Deployment Update"')
rep('description="The rank sales update is live on the latest deployment."', 'description="A new bot update was deployed. Below are the commands currently live on this deployment."')
rep('content="Rank Sale Update Pushed — /rank-sale is live and running on the latest deployment."', 'content="MADBOT Deployment Update — new bot changes are live."')
rep('print(f"Automatic update-log notification posted to {channel.id}: {message.jump_url}")', 'print(f"Automatic deployment update posted to {channel.id}: {message.jump_url}")')

p.write_text(s, encoding="utf-8")
print("Bot updates patch applied.")
