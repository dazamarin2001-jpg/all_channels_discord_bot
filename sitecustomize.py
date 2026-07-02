"""Startup hook for Discord bot deployment/update logging.

Python automatically imports this module on startup when it is on sys.path.
It wraps the bot's on_ready event so deployments/restarts can be posted to the
exact Discord update-log channel configured with UPDATE_LOG_CHANNEL_ID.
"""

from __future__ import annotations

import functools
import os
from datetime import datetime, timezone


def _patch_discord_bot_event() -> None:
    try:
        import discord
        from discord.ext import commands
    except Exception as exc:  # pragma: no cover - startup safety
        print(f"Update log hook skipped: could not import discord.py: {type(exc).__name__}: {exc}")
        return

    if getattr(commands.Bot, "_update_log_event_patched", False):
        return

    original_event = commands.Bot.event

    async def send_update_log(bot: commands.Bot) -> None:
        channel_id_value = os.getenv("UPDATE_LOG_CHANNEL_ID") or os.getenv("BOT_UPDATE_LOG_CHANNEL_ID")
        if not channel_id_value:
            print("UPDATE_LOG_CHANNEL_ID is not set; skipping Discord update log message.")
            return

        try:
            channel_id = int(channel_id_value)
        except ValueError:
            print("UPDATE_LOG_CHANNEL_ID must be a Discord channel ID number; skipping update log message.")
            return

        channel = bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await bot.fetch_channel(channel_id)
            except discord.DiscordException as exc:
                print(f"Could not fetch UPDATE_LOG_CHANNEL_ID={channel_id}: {type(exc).__name__}: {exc}")
                return

        if not hasattr(channel, "send"):
            print(f"UPDATE_LOG_CHANNEL_ID={channel_id} is not a sendable Discord channel.")
            return

        started_at = datetime.now(timezone.utc)
        bot_name = str(bot.user) if bot.user else "Unknown bot"
        bot_id = bot.user.id if bot.user else "unknown"

        content = "✅ **Rank Sale Update Pushed** — `/rank-sale` is live and running on the latest deployment."
        embed = discord.Embed(
            title="Rank Sale Update Pushed",
            description="The `/rank-sale` logging update is now live after the latest Railway/GitHub deployment.",
            color=discord.Color.green(),
            timestamp=started_at,
        )
        embed.add_field(name="Bot", value=f"{bot_name} (`{bot_id}`)", inline=False)
        embed.add_field(
            name="What's included",
            value=(
                "• `/rank-sale` opens a Discord form.\n"
                "• Logs Seller Habbo, Buyer, Rank Sold, Amount, and Proof/Notes.\n"
                "• Saves rank sales to Google Sheets.\n"
                "• Posts the rank sale log into the configured rank-sales channel."
            ),
            inline=False,
        )
        embed.add_field(name="Required channel variable", value="`RANK_SALES_CHANNEL_ID`", inline=True)
        embed.add_field(name="Update log variable", value="`UPDATE_LOG_CHANNEL_ID`", inline=True)
        embed.set_footer(text="Automatic startup update log")

        try:
            await channel.send(content=content, embed=embed)
            print(f"Posted rank sale update log to #{getattr(channel, 'name', channel.id)} ({channel.id}).")
        except discord.Forbidden as exc:
            try:
                await channel.send(content=content)
                print(f"Posted plain-text rank sale update log to #{getattr(channel, 'name', channel.id)} ({channel.id}).")
            except discord.DiscordException:
                print(f"Bot cannot send to UPDATE_LOG_CHANNEL_ID={channel_id}: {type(exc).__name__}: {exc}")
        except discord.DiscordException as exc:
            print(f"Could not send update log message: {type(exc).__name__}: {exc}")

    def patched_event(self: commands.Bot, coro):
        if getattr(coro, "__name__", "") != "on_ready":
            return original_event(self, coro)

        @functools.wraps(coro)
        async def wrapped_on_ready(*args, **kwargs):
            await coro(*args, **kwargs)
            if getattr(self, "_sent_update_log_once", False):
                return
            self._sent_update_log_once = True
            try:
                await send_update_log(self)
            except Exception as exc:  # pragma: no cover - never crash bot on logging
                print(f"Unexpected update log error: {type(exc).__name__}: {exc}")

        return original_event(self, wrapped_on_ready)

    commands.Bot.event = patched_event
    commands.Bot._update_log_event_patched = True


_patch_discord_bot_event()
