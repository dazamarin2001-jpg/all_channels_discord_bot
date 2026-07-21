"""Keep scheduled pay announcements to one visible message and verify the ping.

This runs after pay_ping_reliability_patch.py and before main.py imports
PAY_BLOCK. It replaces an unpinged duplicate instead of posting beside it, and
it verifies the role mention returned by Discord. If the Pay Alert mention is
not present, the bot removes that message and sends one @everyone replacement.
"""

from pathlib import Path


path = Path("pay_commands.py")
if not path.exists():
    print("Pay announcement guard patch warning: pay_commands.py was not found.")
else:
    text = path.read_text(encoding="utf-8")
    marker = "PAY_ANNOUNCEMENT_GUARD_PATCH_VERSION = 1"

    if marker not in text:
        constants_anchor = "PAY_PING_RELIABILITY_PATCH_VERSION = 1\n"
        if constants_anchor in text:
            text = text.replace(constants_anchor, constants_anchor + marker + "\n", 1)
        else:
            print("Pay announcement guard patch warning: reliability marker was not found.")

        old_duplicate_check = '''                for field in existing_embed.fields:
                    if field.name == "🕒 Your Local Time" and expected_local_time in str(field.value):
                        return True'''
        guarded_duplicate_check = '''                for field in existing_embed.fields:
                    if field.name != "🕒 Your Local Time" or expected_local_time not in str(field.value):
                        continue

                    role = get_pay_alert_role(channel.guild)
                    if message.mention_everyone:
                        return True
                    if role is not None and any(
                        mentioned.id == role.id for mentioned in message.role_mentions
                    ):
                        return True

                    try:
                        await message.delete()
                        print(
                            "Pay announcement existed without a verified ping; removed it "
                            "before sending one corrected replacement."
                        )
                    except (discord.Forbidden, discord.HTTPException) as exc:
                        print(
                            "Pay announcement existed without a verified ping, but it could "
                            f"not be removed: {type(exc).__name__}: {exc}. Skipping a new "
                            "message to avoid channel clutter."
                        )
                        return True
                    return False'''

        if old_duplicate_check in text:
            text = text.replace(old_duplicate_check, guarded_duplicate_check, 1)
        elif guarded_duplicate_check not in text:
            print("Pay announcement guard patch warning: duplicate-check block was not found.")

        helper_start = text.find("async def send_pay_message_with_role_ping(")
        helper_end = text.find("async def send_pay_announcement(", helper_start)

        guarded_helper = r'''async def send_pay_message_with_role_ping(
    channel,
    guild: discord.Guild,
    role: discord.Role | None,
    *,
    embed: discord.Embed | None = None,
    content_prefix: str | None = None,
) -> bool:
    """Send one visible message, verify its ping, and safely replace it if needed."""
    bot_member = guild.me
    permissions = channel.permissions_for(bot_member) if bot_member is not None else None

    async def send_everyone_replacement() -> bool:
        content_parts = []
        if content_prefix:
            content_parts.append(content_prefix)
        content_parts.append("@everyone")
        sent = await channel.send(
            content="\n".join(content_parts),
            embed=embed,
            allowed_mentions=discord.AllowedMentions(
                everyone=True,
                users=False,
                roles=False,
                replied_user=False,
            ),
        )
        verified = bool(sent.mention_everyone)
        print(
            "Pay @everyone fallback sent: "
            f"channel={channel}, verified={verified}, "
            f"bot_can_mention_everyone={bool(permissions and permissions.mention_everyone)}"
        )
        return verified

    if role is None or not role.members:
        reason = "role not found" if role is None else "role has no members"
        print(f"Pay Alert unavailable ({reason}); using @everyone in the announcement.")
        return await send_everyone_replacement()

    can_mention_without_edit = bool(
        role.mentionable
        or (permissions is not None and permissions.mention_everyone)
    )
    role_for_send = role
    temporarily_made_mentionable = False

    if not can_mention_without_edit:
        can_manage_role = bool(
            bot_member is not None
            and bot_member.guild_permissions.manage_roles
            and role < bot_member.top_role
            and not role.managed
        )
        if can_manage_role:
            try:
                role_for_send = await role.edit(
                    mentionable=True,
                    reason="Temporarily allow the scheduled FSA pay alert ping.",
                )
                temporarily_made_mentionable = True
                print(
                    "Pay Alert role temporarily made mentionable: "
                    f"name={role.name!r}, id={role.id}, channel={channel}"
                )
            except discord.DiscordException as exc:
                print(
                    "Could not temporarily make Pay Alert mentionable: "
                    f"{type(exc).__name__}: {exc}. Using @everyone instead."
                )
                return await send_everyone_replacement()
        else:
            print(
                "Pay Alert cannot be mentioned and cannot be edited; using @everyone instead."
            )
            return await send_everyone_replacement()

    content_parts = []
    if content_prefix:
        content_parts.append(content_prefix)
    content_parts.append(role_for_send.mention)

    try:
        sent_message = await channel.send(
            content="\n".join(content_parts),
            embed=embed,
            allowed_mentions=get_pay_allowed_mentions(role_for_send),
        )
    finally:
        if temporarily_made_mentionable:
            try:
                await role_for_send.edit(
                    mentionable=False,
                    reason="Restore Pay Alert role after scheduled FSA pay ping.",
                )
            except discord.DiscordException as exc:
                print(
                    "Could not restore Pay Alert mentionable setting: "
                    f"{type(exc).__name__}: {exc}"
                )

    role_ping_verified = any(
        mentioned.id == role.id for mentioned in sent_message.role_mentions
    )
    if role_ping_verified:
        print(
            "Pay Alert role ping verified in the sent announcement: "
            f"role={role.name!r}, id={role.id}, channel={channel}"
        )
        return True

    print(
        "Pay Alert role ping was not verified. Removing that announcement before "
        "sending one @everyone replacement."
    )
    try:
        await sent_message.delete()
    except (discord.Forbidden, discord.HTTPException) as exc:
        print(
            "Could not remove the unverified announcement: "
            f"{type(exc).__name__}: {exc}. Not sending a second message."
        )
        return False

    return await send_everyone_replacement()


'''

        if helper_start != -1 and helper_end != -1:
            text = text[:helper_start] + guarded_helper + text[helper_end:]
        else:
            print("Pay announcement guard patch warning: reliable send helper was not found.")

        path.write_text(text, encoding="utf-8")
        print("Pay announcement one-message verification guard applied.")
    else:
        print("Pay announcement one-message verification guard already applied.")
