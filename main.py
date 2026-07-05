"""Railway entrypoint for the Discord bot.

This keeps startup safe while adding the cleanup command if bot.py does not
already contain it. It does not touch the rank sale modal.
"""

from pathlib import Path


CLEANUP_BLOCK = '''
# ---- Cleanup crew commands ----
CLEANUP_CHANNELS_FILE = os.getenv("CLEANUP_CHANNELS_FILE", "cleanup_channels.json")
EXTRA_CLEANUP_CHANNEL_IDS: set[int] = set()


def get_static_cleanup_channel_ids() -> set[int]:
    ids: set[int] = set()
    raw_values = [
        os.getenv("AUTO_CLEAN_CHANNEL_ID"),
        os.getenv("AUTO_CLEAN_CHANNEL_IDS"),
        RANK_SALES_CHANNEL_ID,
        globals().get("DONATION_CHANNEL_ID"),
    ]
    for raw_value in raw_values:
        if not raw_value:
            continue
        for piece in str(raw_value).replace(";", ",").split(","):
            piece = piece.strip()
            if not piece:
                continue
            try:
                ids.add(int(piece))
            except ValueError:
                pass
    return ids


def load_extra_cleanup_channel_ids_from_file() -> set[int]:
    EXTRA_CLEANUP_CHANNEL_IDS.clear()
    if not os.path.exists(CLEANUP_CHANNELS_FILE):
        return set(EXTRA_CLEANUP_CHANNEL_IDS)
    try:
        with open(CLEANUP_CHANNELS_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        for entry in data.get("channels", []):
            try:
                EXTRA_CLEANUP_CHANNEL_IDS.add(int(entry.get("channel_id")))
            except (TypeError, ValueError):
                continue
    except Exception as exc:
        print(f"Cleanup channel file warning: {type(exc).__name__}: {exc}")
    return set(EXTRA_CLEANUP_CHANNEL_IDS)


def save_extra_cleanup_channels_to_file() -> None:
    payload = {"channels": [{"channel_id": str(channel_id)} for channel_id in sorted(EXTRA_CLEANUP_CHANNEL_IDS)]}
    with open(CLEANUP_CHANNELS_FILE, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def get_all_cleanup_channel_ids() -> set[int]:
    return set(EXTRA_CLEANUP_CHANNEL_IDS) | get_static_cleanup_channel_ids()


def add_cleanup_channel(channel_id: int) -> None:
    load_extra_cleanup_channel_ids_from_file()
    EXTRA_CLEANUP_CHANNEL_IDS.add(channel_id)
    save_extra_cleanup_channels_to_file()


def remove_cleanup_channel(channel_id: int) -> bool:
    load_extra_cleanup_channel_ids_from_file()
    existed = channel_id in EXTRA_CLEANUP_CHANNEL_IDS
    EXTRA_CLEANUP_CHANNEL_IDS.discard(channel_id)
    save_extra_cleanup_channels_to_file()
    return existed


def is_cleanup_log_message(candidate: discord.Message) -> bool:
    # Keep bot/webhook embeds, such as sale logs, donation logs, and ticket embeds.
    return bool(candidate.embeds) and (candidate.author.bot or candidate.webhook_id is not None)


async def cleanup_existing_non_logs_in_channel(channel, history_limit: int | None = None) -> int:
    if history_limit is None:
        history_limit_raw = os.getenv("AUTO_CLEAN_HISTORY_LIMIT", "500")
        try:
            history_limit = max(1, min(int(history_limit_raw), 2000))
        except ValueError:
            history_limit = 500

    deleted = 0
    async for message in channel.history(limit=history_limit):
        if getattr(message, "pinned", False):
            continue
        if is_cleanup_log_message(message):
            continue
        try:
            await message.delete()
            deleted += 1
            await asyncio.sleep(0.25)
        except (discord.NotFound, discord.Forbidden):
            continue
        except discord.HTTPException as exc:
            print(f"Cleanup failed on old message: {type(exc).__name__}: {exc}")
            await asyncio.sleep(1)
    return deleted


async def can_manage_cleanup(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        return False
    member = interaction.user
    if not isinstance(member, discord.Member):
        member = await interaction.guild.fetch_member(interaction.user.id)
    return member.guild_permissions.administrator or member.guild_permissions.manage_messages


cleanup_group = app_commands.Group(name="cleanup", description="Clean-up crew channel tools.")


@cleanup_group.command(name="enable", description="Enable clean-up crew in this channel or another channel.")
@app_commands.describe(channel="Channel to clean. Leave empty to use this channel.")
@app_commands.check(can_manage_cleanup)
async def cleanup_enable(interaction: discord.Interaction, channel: discord.TextChannel | None = None) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return

    target = channel or interaction.channel
    if not isinstance(target, (discord.TextChannel, discord.Thread)):
        await interaction.response.send_message("Use this in a text channel or pick a text channel.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await asyncio.to_thread(add_cleanup_channel, target.id)
        deleted = await cleanup_existing_non_logs_in_channel(target)
        await interaction.followup.send(
            f"🧹 Clean-up crew enabled in {target.mention}. I also removed {deleted} old non-log message(s).",
            ephemeral=True,
        )
    except Exception as exc:
        print(f"Cleanup enable error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(f"Could not enable cleanup: {type(exc).__name__}: {exc}", ephemeral=True)


@cleanup_group.command(name="disable", description="Disable clean-up crew in this channel or another channel.")
@app_commands.describe(channel="Channel to stop cleaning. Leave empty to use this channel.")
@app_commands.check(can_manage_cleanup)
async def cleanup_disable(interaction: discord.Interaction, channel: discord.TextChannel | None = None) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return

    target = channel or interaction.channel
    if not isinstance(target, (discord.TextChannel, discord.Thread)):
        await interaction.response.send_message("Use this in a text channel or pick a text channel.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        removed = await asyncio.to_thread(remove_cleanup_channel, target.id)
        if target.id in get_static_cleanup_channel_ids():
            await interaction.followup.send(
                f"{target.mention} is still cleaned because it is set in Railway Variables. Remove it from the variable to fully disable it.",
                ephemeral=True,
            )
        elif removed:
            await interaction.followup.send(f"🧹 Clean-up crew disabled in {target.mention}.", ephemeral=True)
        else:
            await interaction.followup.send(f"Clean-up crew was not enabled in {target.mention}.", ephemeral=True)
    except Exception as exc:
        print(f"Cleanup disable error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(f"Could not disable cleanup: {type(exc).__name__}: {exc}", ephemeral=True)


@cleanup_group.command(name="list", description="List channels where clean-up crew is enabled.")
@app_commands.check(can_manage_cleanup)
async def cleanup_list(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await asyncio.to_thread(load_extra_cleanup_channel_ids_from_file)
        ids = sorted(get_all_cleanup_channel_ids())
        if not ids:
            await interaction.followup.send("No cleanup channels are enabled yet.", ephemeral=True)
            return

        lines = []
        for channel_id in ids[:25]:
            channel = interaction.guild.get_channel(channel_id)
            lines.append(channel.mention if channel else f"`{channel_id}`")
        await interaction.followup.send("🧹 Clean-up crew is enabled in:\n" + "\n".join(lines), ephemeral=True)
    except Exception as exc:
        print(f"Cleanup list error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(f"Could not list cleanup channels: {type(exc).__name__}: {exc}", ephemeral=True)


@bot.listen("on_message")
async def auto_cleanup_on_message(message: discord.Message) -> None:
    if message.guild is None:
        return

    await asyncio.to_thread(load_extra_cleanup_channel_ids_from_file)
    if message.channel.id not in get_all_cleanup_channel_ids():
        return
    if getattr(message, "pinned", False):
        return
    if is_cleanup_log_message(message):
        return

    warning = None
    if not message.author.bot and message.webhook_id is None:
        try:
            warning = await message.channel.send(
                "🧹 **Clean-up crew is here!** This channel is for logs only. Non-log messages will be swept away in **10 seconds**."
            )
        except discord.HTTPException:
            warning = None

    await asyncio.sleep(10)
    try:
        current_message = await message.channel.fetch_message(message.id)
        if is_cleanup_log_message(current_message) or getattr(current_message, "pinned", False):
            return
        await current_message.delete()
        if warning is not None:
            try:
                await warning.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
    except (discord.NotFound, discord.Forbidden):
        pass
    except discord.HTTPException as exc:
        print(f"Auto cleanup failed: {type(exc).__name__}: {exc}")


_cleanup_startup_done = False


@bot.listen("on_ready")
async def clean_existing_cleanup_channel_messages() -> None:
    global _cleanup_startup_done
    if _cleanup_startup_done:
        return
    _cleanup_startup_done = True

    await asyncio.to_thread(load_extra_cleanup_channel_ids_from_file)
    for cleanup_channel_id in get_all_cleanup_channel_ids():
        channel = bot.get_channel(cleanup_channel_id)
        if channel is None:
            try:
                channel = await bot.fetch_channel(cleanup_channel_id)
            except discord.HTTPException:
                continue
        if not hasattr(channel, "history"):
            continue
        deleted = await cleanup_existing_non_logs_in_channel(channel)
        if deleted:
            print(f"Startup cleanup deleted {deleted} old non-log message(s) from channel {cleanup_channel_id}.")


bot.tree.add_command(cleanup_group)
# ---- End cleanup crew commands ----
'''


path = Path("bot.py")
if path.exists():
    text = path.read_text(encoding="utf-8")
    if "cleanup_group = app_commands.Group" not in text:
        marker = "\n\nbot.run(TOKEN)"
        if marker in text:
            text = text.replace(marker, "\n\n" + CLEANUP_BLOCK.strip() + marker, 1)
            path.write_text(text, encoding="utf-8")
            print("Cleanup crew commands injected into bot.py.")
        else:
            print("Cleanup command warning: could not find bot.run(TOKEN) marker.")

import bot
