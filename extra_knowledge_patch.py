from pathlib import Path

p = Path("bot.py")
s = p.read_text(encoding="utf-8")

needle = "    q = question.casefold()\n"
insert = '''    q = question.casefold()\n    if "foundation" in q and any(word in q for word in ("team", "member", "members", "who", "list")):\n        return "The Foundation Team members are **Eskimo**, **BeccaMneme**, **missbluegerlx2**, and **srafin**."\n'''

if needle in s and "The Foundation Team members are" not in s:
    s = s.replace(needle, insert, 1)

role_access = r'''

# ROLE_BASED_COMMAND_ACCESS_ENABLED
RESTRICTED_COMMANDS = {"rank-sale", "rank-sales-summary", "setup-rank-sales-sheet", "setup_hierarchy", "build_server", "delete_old_layout", "setup_welcome", "setup_logs", "setup_tickets", "ticketpanel", "bot-update", "bot-update-channel"}
ALLOWED_COMMAND_ROLES = {"chat moderator", "founder", "foundation team", "foundation advisor", "administrator", "moderator", "staff", "leadership", "high rank", "sales"}
try:
    ALLOWED_COMMAND_ROLES.update(str(name).casefold() for name in STAFF_ROLE_NAMES)
except Exception:
    pass


def user_can_use_restricted_command(user) -> bool:
    if getattr(getattr(user, "guild_permissions", None), "administrator", False):
        return True
    for role in getattr(user, "roles", []):
        if str(getattr(role, "name", "")).casefold() in ALLOWED_COMMAND_ROLES:
            return True
        if SALES_ROLE_ID and str(getattr(role, "id", "")) == str(SALES_ROLE_ID):
            return True
    return False


async def role_command_check(interaction):
    command_name = str(getattr(getattr(interaction, "command", None), "name", "")).casefold()
    if command_name not in RESTRICTED_COMMANDS:
        return True
    if user_can_use_restricted_command(interaction.user):
        return True
    msg = "You do not have permission to use this command."
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)
    return False


bot.tree.interaction_check = role_command_check
print("Role-based command access enabled. Chat Moderator can use restricted commands.")
'''

if "ROLE_BASED_COMMAND_ACCESS_ENABLED" not in s:
    s = s.replace("\n\nbot.run(TOKEN)", role_access + "\n\nbot.run(TOKEN)")

p.write_text(s, encoding="utf-8")
print("Extra knowledge patch applied.")
