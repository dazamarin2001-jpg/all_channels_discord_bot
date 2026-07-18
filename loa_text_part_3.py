PART = r'''
            ),
            inline=False,
        )

    embed.add_field(
        name="LOA Discord Role",
        value=_loa_checkmark(record, "Role Confirmed", "Role Confirmed By", "Role Confirmed At"),
        inline=True,
    )
    embed.add_field(
        name="[LOA] Nickname",
        value=_loa_checkmark(record, "Nickname Confirmed", "Nickname Confirmed By", "Nickname Confirmed At"),
        inline=True,
    )
    embed.add_field(
        name="LOA Badge",
        value=_loa_checkmark(record, "Badge Confirmed", "Badge Confirmed By", "Badge Confirmed At"),
        inline=True,
    )

    reminder_status = record.get("Reminder Status") or "Not sent"
    if reminder_status == "Not sent":
        try:
            reminder_date = _loa_parse_date(record.get("End Date")) - _loa_timedelta(days=LOA_REMINDER_DAYS)
            reminder_value = f"Scheduled for {_loa_display_date(reminder_date.isoformat())}"
        except ValueError:
            reminder_value = "Not scheduled"
    else:
        reminder_value = reminder_status
        if record.get("Reminder Sent At"):
            reminder_value += f"\n{record.get('Reminder Sent At')}"
    embed.add_field(name="Return Reminder", value=reminder_value, inline=False)

    if status in {"Return Pending", "Completed"}:
        embed.add_field(name="Actual Return Date", value=_loa_display_date(record.get("Actual Return Date")), inline=False)
        embed.add_field(
            name="LOA Role Removed",
            value=_loa_removed_checkmark(record, "Role Removed", "Role Removed By", "Role Removed At"),
            inline=True,
        )
        embed.add_field(
            name="[LOA] Nickname Removed",
            value=_loa_removed_checkmark(record, "Nickname Removed", "Nickname Removed By", "Nickname Removed At"),
            inline=True,
        )
        embed.add_field(
            name="LOA Badge Removed",
            value=_loa_removed_checkmark(record, "Badge Removed", "Badge Removed By", "Badge Removed At"),
            inline=True,
        )
        if record.get("Completed By"):
            embed.add_field(name="Return Recorded By", value=record.get("Completed By"), inline=True)

    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Recorded By", value=record.get("Recorded By") or "N/A", inline=True)
    embed.set_footer(text=f"Last updated: {record.get('Last Updated') or _loa_now_text()}")
    return embed


async def _loa_staff_allowed(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        return False
    member = interaction.user
    if not isinstance(member, discord.Member):
        try:
            member = await interaction.guild.fetch_member(interaction.user.id)
        except discord.DiscordException:
            return False
    if member.guild_permissions.administrator or member.guild_permissions.manage_messages:
        return True
    return any(role.name.casefold() in LOA_STAFF_ROLE_NAMES for role in member.roles)


async def _loa_require_staff(interaction: discord.Interaction) -> bool:
    if await _loa_staff_allowed(interaction):
        return True
    if interaction.response.is_done():
        await interaction.followup.send("You do not have permission to manage LOA records.", ephemeral=True)
    else:
        await interaction.response.send_message("You do not have permission to manage LOA records.", ephemeral=True)
    return False


async def get_loa_tracking_channel(guild: discord.Guild | None):
    if guild is None or not LOA_TRACKING_CHANNEL_ID:
        return None
    try:
        channel_id = int(LOA_TRACKING_CHANNEL_ID)
    except ValueError:
        return None
    channel = guild.get_channel(channel_id) or bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.DiscordException:
            return None
    if isinstance(channel, (discord.TextChannel, discord.Thread)):
        return channel
    return None


def _loa_active_view_for(record: dict[str, str] | None = None):
    return LOAActiveView(record)


def _loa_return_view_for(record: dict[str, str] | None = None):
    return LOAReturnView(record)


async def _loa_edit_tracking_message(record: dict[str, str], interaction_message=None) -> None:
    status = record.get("Status") or "Active"
    view = None
    if status in {"Active", "Extended", "Overdue"}:
        view = _loa_active_view_for(record)
    elif status == "Return Pending":
        view = _loa_return_view_for(record)

    embed = build_loa_embed(record)
    if interaction_message is not None:
        try:
            await interaction_message.edit(embed=embed, view=view)
            return
        except discord.DiscordException:
            pass

'''
