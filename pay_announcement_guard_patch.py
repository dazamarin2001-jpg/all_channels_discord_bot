"""Ensure scheduled pay announcements ping only the configured Pay Alert role.

This runs after pay_ping_reliability_patch.py and before main.py imports
PAY_BLOCK. It removes any duplicate announcement that did not verify the
Pay Alert role mention and never falls back to @everyone.
"""

from pathlib import Path


path = Path("pay_commands.py")
if not path.exists():
    print("Pay announcement guard patch warning: pay_commands.py was not found.")
else:
    text = path.read_text(encoding="utf-8")
    marker = "PAY_ANNOUNCEMENT_GUARD_PATCH_VERSION = 2"

    if marker not in text:
        old_duplicate_check = '''                for field in existing_embed.fields:
                    if field.name == "🕒 Your Local Time" and expected_local_time in str(field.value):
                        return True'''

        version1_duplicate_check = '''                for field in existing_embed.fields:
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

        strict_duplicate_check = '''                for field in existing_embed.fields:
                    if field.name != "🕒 Your Local Time" or expected_local_time not in str(field.value):
                        continue

                    role = get_pay_alert_role(channel.guild)
                    if role is not None and any(
                        mentioned.id == role.id for mentioned in message.role_mentions
                    ):
                        return True

                    try:
                        await message.delete()
                        print(
                            "Pay announcement existed without a verified Pay Alert ping; "
                            "removed it before sending one corrected replacement."
                        )
                    except (discord.Forbidden, discord.HTTPException) as exc:
                        print(
                            "Pay announcement existed without a verified Pay Alert ping, but "
                            f"it could not be removed: {type(exc).__name__}: {exc}. Skipping a "
                            "new message to avoid channel clutter."
                        )
                        return True
                    return False'''

        if version1_duplicate_check in text:
            text = text.replace(version1_duplicate_check, strict_duplicate_check, 1)
        elif old_duplicate_check in text:
            text = text.replace(old_duplicate_check, strict_duplicate_check, 1)
        elif strict_duplicate_check not in text:
            print("Pay announcement guard patch warning: duplicate-check block was not found.")

        helper_start = text.find("async def send_pay_message_with_role_ping(")
        helper_end = text.find("async def send_pay_announcement(", helper_start)

        strict_helper = r'''async def send_pay_message_with_role_ping(
    channel,
    guild: discord.Guild,
    role: discord.Role | None,
    *,
    embed: discord.Embed | None = None,
    content_prefix: str | None = None,
) -> bool:
    # Send one visible message only when the Pay Alert role can be pinged.
    if role is None:
        print(
            "Pay announcement not sent because the configured Pay Alert role "
            "could not be found."
        )
        return False

    bot_member = guild.me
    permissions = channel.permissions_for(bot_member) if bot_member is not None else None
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
        if not can_manage_role:
            print(
                "Pay announcement not sent because Pay Alert is not mentionable and "
                "the bot cannot temporarily edit that role."
            )
            return False

        try:
            role_for_send = await role.edit(
                mentionable=True,
                reason="Temporarily allow the scheduled FSA Pay Alert ping.",
            )
            temporarily_made_mentionable = True
            print(
                "Pay Alert role temporarily made mentionable: "
                f"name={role.name!r}, id={role.id}, channel={channel}"
            )
        except discord.DiscordException as exc:
            print(
                "Pay announcement not sent because Pay Alert could not be made "
                f"mentionable: {type(exc).__name__}: {exc}"
            )
            return False

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
        "Pay Alert role ping was not verified. Removing the unverified announcement "
        "without sending a fallback ping."
    )
    try:
        await sent_message.delete()
    except (discord.Forbidden, discord.HTTPException) as exc:
        print(
            "Could not remove the unverified announcement: "
            f"{type(exc).__name__}: {exc}"
        )
    return False


'''

        if helper_start != -1 and helper_end != -1:
            text = text[:helper_start] + strict_helper + text[helper_end:]
        else:
            print("Pay announcement guard patch warning: reliable send helper was not found.")

        old_send_result = '''    ping_expected = await send_pay_message_with_role_ping(
        channel,
        guild,
        role,
        embed=embed,
    )
    print(
        f"Pay announcement sent: event={event_key}, channel={channel}, "
        f"role_ping_expected={ping_expected}"
    )
    return True'''

        strict_send_result = '''    ping_verified = await send_pay_message_with_role_ping(
        channel,
        guild,
        role,
        embed=embed,
    )
    print(
        f"Pay announcement result: event={event_key}, channel={channel}, "
        f"pay_alert_ping_verified={ping_verified}"
    )
    return ping_verified'''

        if old_send_result in text:
            text = text.replace(old_send_result, strict_send_result, 1)
        elif strict_send_result not in text:
            print("Pay announcement guard patch warning: send-result block was not found.")

        constants_anchor = "PAY_PING_RELIABILITY_PATCH_VERSION = 1\n"
        if marker not in text:
            if constants_anchor in text:
                text = text.replace(constants_anchor, constants_anchor + marker + "\n", 1)
            else:
                print("Pay announcement guard patch warning: reliability marker was not found.")

        path.write_text(text, encoding="utf-8")
        print("Pay announcement Pay-Alert-only guard version 2 applied.")
    else:
        print("Pay announcement Pay-Alert-only guard version 2 already applied.")
