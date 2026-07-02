from pathlib import Path

p = Path("bot.py")
s = p.read_text(encoding="utf-8")

role_ping_code = r'''

# ROLE_PING_BY_MESSAGE_ENABLED
def can_use_role_ping(member) -> bool:
    if getattr(getattr(member, "guild_permissions", None), "administrator", False):
        return True
    allowed = {"chat moderator", "administrator", "moderator", "founder", "foundation team", "foundation advisor", "leadership", "high rank"}
    return any(str(getattr(role, "name", "")).casefold() in allowed for role in getattr(member, "roles", []))


def find_role_for_ping(message, text):
    if message.role_mentions:
        return message.role_mentions[0]
    cleaned = text.casefold().replace("@", "").strip()
    if cleaned.startswith("ping "):
        cleaned = cleaned[5:].strip()
    role_name = cleaned.split(" ", 1)[0].strip()
    for role in getattr(message.guild, "roles", []):
        if role.name.casefold().replace(" ", "-") == role_name.replace(" ", "-"):
            return role
    return None


async def try_role_ping_message(message) -> bool:
    if message.guild is None or bot.user is None or bot.user not in message.mentions:
        return False
    text = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
    if not text.casefold().startswith("ping "):
        return False
    if not can_use_role_ping(message.author):
        await message.reply("You do not have permission to ping roles with MADBOT.", mention_author=False)
        return True
    role = find_role_for_ping(message, text)
    if role is None:
        await message.reply("I could not find that role. Try `@MADBOT ping @RoleName message`.", mention_author=False)
        return True
    note = text.split(" ", 2)[2].strip() if len(text.split(" ", 2)) >= 3 else ""
    content = f"{role.mention} {note}".strip()
    await message.channel.send(content, allowed_mentions=discord.AllowedMentions(roles=True, users=False, everyone=False))
    return True
'''

if "ROLE_PING_BY_MESSAGE_ENABLED" not in s:
    s = s.replace("\n\n@bot.event\nasync def on_message", role_ping_code + "\n\n@bot.event\nasync def on_message")
    s = s.replace(
        "    if message.author.bot:\n        return\n",
        "    if message.author.bot:\n        return\n    if await try_role_ping_message(message):\n        await bot.process_commands(message)\n        return\n",
        1,
    )

p.write_text(s, encoding="utf-8")
print("Role ping patch applied.")
