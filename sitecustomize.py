"""Small startup compatibility patches for the Discord bot runtime."""

from pathlib import Path


def patch_rank_sale_modal() -> None:
    """Prevent rank-sale submissions from crashing when seller_habbo is absent."""
    bot_path = Path(__file__).with_name("bot.py")
    if not bot_path.exists():
        return

    text = bot_path.read_text(encoding="utf-8")
    unsafe_line = "            seller_habbo = clean_text(self.seller_habbo.value)"
    safe_lines = (
        "            seller_habbo_input = getattr(self, \"seller_habbo\", None)\n"
        "            seller_habbo = clean_text(getattr(seller_habbo_input, \"value\", \"\")) or member_display_name(interaction.user)"
    )

    if unsafe_line not in text:
        return

    bot_path.write_text(text.replace(unsafe_line, safe_lines, 1), encoding="utf-8")
    print("RankSaleModal seller_habbo compatibility patch applied.")


try:
    patch_rank_sale_modal()
except Exception as exc:
    print(f"RankSaleModal compatibility patch warning: {type(exc).__name__}: {exc}")


try:
    import discord

    if not hasattr(discord, "DisordException"):
        discord.DisordException = discord.DiscordException
except Exception:
    pass
