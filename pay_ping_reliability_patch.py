"""Patch scheduled pay announcements so the Pay Alert role reliably notifies members.

If the role is not mentionable and the bot lacks Mention Everyone in the pay channel,
the bot temporarily makes the role mentionable while sending, then restores it.
"""

from pathlib import Path


path = Path("pay_commands.py")
if not path.exists():
    print("Pay ping reliability patch warning: pay_commands.py was not found.")
else:
    text = path.read_text(encoding="utf-8")
    marker = "PAY_PING_RELIABILITY_PATCH_VERSION = 1"

    if marker not in text:
        constants_anchor = "PAY_ANNOUNCEMENT_HISTORY_LIMIT = 50\n"
        if constants_anchor in text:
            text = text.replace(
                constants_anchor,
                constants_anchor + marker + "\n",
                1,
            )
        else:
            print("Pay ping reliability patch warning: constants anchor was not found.")

        function_start = text.find("async def send_pay_announcement(")
        function_end = text.find(
            '@bot.tree.command(name="test-pay-ping"',
            function_start,
        )

        if function_start != -1 and function_end != -1:
            replacement = r'''async def send_pay_message_with_role_ping(
    channel,
    guild: discord.Guild,
    role: discord.Role | None,
    *,
    embed: discord.Embed | None = None,
    content_prefix: str | None = None,
) -> bool:
    # Send a message and make a best effort to produce a real role notification.
    if role is None:
        await channel.send(
            content=content_prefix,
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none(),
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
    ping_expected = can_mention_without_edit

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
                ping_expected = True
                print(
                    "Pay alert role temporarily made mentionable for scheduled ping: "
                    f"name={role.name!r}, id={role.id}, channel={channel}"
                )
            except discord.DiscordException as exc:
                print(
                    "Pay announcement warning: could not temporarily make the role "
                    f"mentionable: {type(exc).__name__}: {exc}"
                )
        else:
            print(
                "Pay announcement warning: the Pay Alert role is not mentionable, "
                "the bot lacks Mention Everyone in this channel, and the bot cannot "
                "edit the role. Move the bot role above Pay Alert or grant Manage Roles."
            )

    content_parts = []
    if content_prefix:
        content_parts.append(content_prefix)
    content_parts.append(role_for_send.mention)
    content = "\n".join(content_parts)

    try:
        await channel.send(
            content=content,
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
                print(
                    "Pay alert role mentionable setting restored after scheduled ping: "
                    f"name={role.name!r}, id={role.id}"
                )
            except discord.DiscordException as exc:
                print(
                    "Pay announcement warning: could not restore the Pay Alert role's "
                    f"mentionable setting: {type(exc).__name__}: {exc}"
                )

    return ping_expected


async def send_pay_announcement(guild: discord.Guild, event_type: str, pay_time_utc: datetime) -> bool:
    channel = await get_pay_announcement_channel(guild)
    if channel is None:
        print(
            "Pay announcement warning: no pay announcement channel was found. "
            "Set PAY_REMINDER_CHANNEL_ID or create #pay-announcements."
        )
        return False

    event_key = get_pay_event_key(pay_time_utc, event_type)
    if await pay_event_already_posted(channel, event_type, pay_time_utc):
        print(f"Pay announcement skipped because {event_key} is already in {channel}.")
        return True

    role = get_pay_alert_role(guild)
    if role is None:
        print(
            f"Pay announcement warning: role '{PAY_ALERT_ROLE_NAME}' was not found. "
            "Set PAY_ALERT_ROLE_ID to the numeric Discord role ID."
        )
    else:
        bot_member = guild.me
        permissions = channel.permissions_for(bot_member) if bot_member is not None else None
        print(
            "Pay announcement role resolved: "
            f"name={role.name!r}, id={role.id}, mentionable={role.mentionable}, "
            f"bot_can_mention_roles={bool(permissions and permissions.mention_everyone)}, "
            f"channel={channel}"
        )

    embed = build_pay_announcement_embed(pay_time_utc, event_type)
    ping_expected = await send_pay_message_with_role_ping(
        channel,
        guild,
        role,
        embed=embed,
    )
    print(
        f"Pay announcement sent: event={event_key}, channel={channel}, "
        f"role_ping_expected={ping_expected}"
    )
    return True


'''
            text = text[:function_start] + replacement + text[function_end:]
        else:
            print("Pay ping reliability patch warning: send function block was not found.")

        path.write_text(text, encoding="utf-8")
        print("Pay ping reliability patch applied.")
    else:
        print("Pay ping reliability patch already applied.")