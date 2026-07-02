from pathlib import Path

p = Path("bot.py")
s = p.read_text(encoding="utf-8")

role_ping_code = r'''

# ROLE_PING_BY_MESSAGE_ENABLED
def can_use_role_ping(member) -> bool:
    if getattr(getattr(member, "guild_permissions", None), "administrator", False):
        return True
    allowed = {"chat moderator", "administrator", "moderator", "founder", "foundation team", "foundation advisor", "leadership"}
    return any(str(getattr(role, "name", "")).casefold() in allowed for role in getattr(member, "roles", []))


def norm(value):
    return " ".join(str(value or "").casefold().replace("@", "").replace("-", " ").replace("_", " ").split())


def find_role_for_ping(message, text):
    if message.role_mentions:
        return message.role_mentions[0]
    wanted = norm(text)
    if wanted.startswith("ping "):
        wanted = wanted[5:].strip()
    checks = [wanted]
    if wanted.endswith("s"):
        checks.append(wanted[:-1])
    for role in getattr(message.guild, "roles", []):
        role_name = norm(role.name)
        for check in checks:
            if check == role_name or check.startswith(role_name + " "):
                return role
    return None


async def try_role_ping_message(message) -> bool:
    if message.guild is None or bot.user is None or bot.user not in message.mentions:
        return False
    text = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
    if not text.casefold().startswith("ping "):
        return False
    if not can_use_role_ping(message.author):
        await message.reply("You do not have permission to use MADBOT role ping.", mention_author=False)
        return True
    role = find_role_for_ping(message, text)
    if role is None:
        await message.reply("I could not find that server role. Try `@MADBOT ping @RoleName message`.", mention_author=False)
        return True
    note = text.split(" ", 2)[2].strip() if len(text.split(" ", 2)) >= 3 else ""
    await message.channel.send(f"{role.mention} {note}".strip())
    return True
'''

start = s.find("\n# ROLE_PING_BY_MESSAGE_ENABLED")
event = s.find("\n\n@bot.event\nasync def on_message", start if start != -1 else 0)
if start != -1 and event != -1:
    s = s[:start] + role_ping_code + s[event:]
elif "ROLE_PING_BY_MESSAGE_ENABLED" not in s and event != -1:
    s = s[:event] + role_ping_code + s[event:]

hook = "    if await try_role_ping_message(message):\n        await bot.process_commands(message)\n        return\n"
if hook not in s:
    s = s.replace("    if message.author.bot:\n        return\n", "    if message.author.bot:\n        return\n" + hook, 1)

p.write_text(s, encoding="utf-8")
print("Role ping patch applied.")
