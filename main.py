"""Railway entrypoint that adds generated commands before loading existing commands."""

from pathlib import Path

from loa_commands import LOA_BLOCK, LOA_END_MARKER, LOA_START_MARKER
from pay_commands import PAY_BLOCK, PAY_END_MARKER, PAY_START_MARKER

TEST_PING_START_MARKER = "# ---- Pay test alias commands ----"
TEST_PING_END_MARKER = "# ---- End pay test alias commands ----"

TEST_PING_BLOCK = r"""
# ---- Pay test alias commands ----
pay_test_group = app_commands.Group(name="test", description="Bot test tools.")


@pay_test_group.command(name="ping", description="Test the configured Pay Alert role mention.")
async def test_pay_ping_alias(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message(
            "This command can only be used inside a server.",
            ephemeral=True,
        )
        return

    member = interaction.user
    if not isinstance(member, discord.Member):
        try:
            member = await guild.fetch_member(interaction.user.id)
        except discord.DiscordException:
            await interaction.response.send_message(
                "I could not verify your server roles.",
                ephemeral=True,
            )
            return

    has_chat_moderator = any(
        normalize_pay_role_name(role.name) == "chatmoderator"
        for role in member.roles
    )
    if not has_chat_moderator:
        await interaction.response.send_message(
            "Only members with the Chat Moderator role can use this command.",
            ephemeral=True,
        )
        return

    callback = getattr(test_pay_ping, "callback", test_pay_ping)
    await callback(interaction)


bot.tree.add_command(pay_test_group)
# ---- End pay test alias commands ----
"""


def remove_marked_block(text: str, start_marker: str, end_marker: str) -> str:
    while start_marker in text:
        start = text.find(start_marker)
        block_start = text.rfind("\n", 0, start)
        if block_start == -1:
            block_start = start
        end = text.find(end_marker, start)
        if end == -1:
            run_marker = "bot.run(TOKEN)"
            run_pos = text.find(run_marker, start)
            if run_pos == -1:
                return text[:block_start].rstrip() + "\n"
            text = text[:block_start].rstrip() + "\n\n" + text[run_pos:]
            continue
        line_end = text.find("\n", end + len(end_marker))
        if line_end == -1:
            line_end = len(text)
        text = text[:block_start].rstrip() + "\n" + text[line_end:].lstrip("\n")
    return text


def patch_legacy_cleanup_permission_handling() -> None:
    """Make startup cleanup skip channels the bot cannot read."""
    legacy_path = Path("legacy_main.py")
    if not legacy_path.exists():
        return

    legacy_text = legacy_path.read_text(encoding="utf-8")
    unsafe_call = "        deleted = await cleanup_existing_non_logs_in_channel(channel)"
    safe_call = """        try:
            deleted = await cleanup_existing_non_logs_in_channel(channel)
        except discord.Forbidden:
            print(
                f\"Startup cleanup skipped channel {cleanup_channel_id}: \"
                \"missing View Channel or Read Message History permission.\"
            )
            continue
        except discord.HTTPException as exc:
            print(
                f\"Startup cleanup skipped channel {cleanup_channel_id}: \"
                f\"{type(exc).__name__}: {exc}\"
            )
            continue"""

    if safe_call in legacy_text:
        return
    if unsafe_call not in legacy_text:
        print("Cleanup permission patch warning: startup cleanup call was not found.")
        return

    legacy_path.write_text(legacy_text.replace(unsafe_call, safe_call, 1), encoding="utf-8")
    print("Cleanup permission handling patched for inaccessible channels.")


def patch_trade_modal_label() -> None:
    """Add Pay Request to the category label shown in the /trade modal."""
    legacy_path = Path("legacy_main.py")
    if not legacy_path.exists():
        return

    legacy_text = legacy_path.read_text(encoding="utf-8")
    old_label = '        label="Donation/Sale",'
    new_label = '        label="Donation/Sale/Pay Request",'

    if new_label in legacy_text:
        return
    if old_label not in legacy_text:
        print("Trade modal label patch warning: Donation/Sale label was not found.")
        return

    legacy_path.write_text(legacy_text.replace(old_label, new_label, 1), encoding="utf-8")
    print("Trade modal label patched to include Pay Request.")


bot_path = Path("bot.py")
if bot_path.exists():
    bot_text = bot_path.read_text(encoding="utf-8")
    bot_text = remove_marked_block(bot_text, LOA_START_MARKER, LOA_END_MARKER)
    bot_text = remove_marked_block(bot_text, PAY_START_MARKER, PAY_END_MARKER)
    bot_text = remove_marked_block(bot_text, TEST_PING_START_MARKER, TEST_PING_END_MARKER)
    run_marker = "\n\nbot.run(TOKEN)"
    if run_marker in bot_text:
        generated_blocks = (
            LOA_BLOCK.strip()
            + "\n\n"
            + PAY_BLOCK.strip()
            + "\n\n"
            + TEST_PING_BLOCK.strip()
        )
        bot_text = bot_text.replace(run_marker, "\n\n" + generated_blocks + run_marker, 1)
        bot_path.write_text(bot_text, encoding="utf-8")
        print("LOA tracking, pay announcements, and pay test commands injected into bot.py.")
    else:
        print("Generated command injector warning: could not find bot.run(TOKEN) marker.")

patch_legacy_cleanup_permission_handling()
patch_trade_modal_label()

# Preserve and run every existing donation, cleanup, and trade startup injection.
import legacy_main  # noqa: E402,F401
