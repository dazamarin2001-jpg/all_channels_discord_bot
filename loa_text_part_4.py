PART = r'''
    try:
        channel_id = int(record.get("Tracking Channel ID") or "0")
        message_id = int(record.get("Tracking Message ID") or "0")
    except ValueError:
        channel_id = message_id = 0
    if not channel_id:
        return

    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.DiscordException:
            return

    if message_id:
        try:
            message = await channel.fetch_message(message_id)
            await message.edit(embed=embed, view=view)
            return
        except discord.NotFound:
            pass
        except discord.DiscordException:
            return

    try:
        replacement = await channel.send(embed=embed, view=view)
        record["Tracking Message ID"] = str(replacement.id)
        record["Tracking Channel ID"] = str(replacement.channel.id)
        await asyncio.to_thread(_loa_update_record, record)
    except discord.DiscordException:
        return


async def _loa_confirm_field(interaction: discord.Interaction, field: str, by_field: str, at_field: str, label: str) -> None:
    if not await _loa_require_staff(interaction):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    if interaction.message is None:
        await interaction.followup.send("I could not identify the LOA tracking message.", ephemeral=True)
        return
    record = await asyncio.to_thread(_loa_find_by_message, interaction.message.id)
    if record is None:
        await interaction.followup.send("This LOA record was not found in Google Sheets.", ephemeral=True)
        return
    if record.get(field) == "Yes":
        await interaction.followup.send(f"{label} was already confirmed.", ephemeral=True)
        return
    record[field] = "Yes"
    record[by_field] = member_display_name(interaction.user)
    record[at_field] = _loa_now_text()
    await asyncio.to_thread(_loa_update_record, record)
    await _loa_edit_tracking_message(record, interaction.message)
    await interaction.followup.send(f"✅ {label} confirmed and the permanent log was updated.", ephemeral=True)


async def _loa_mark_return(
    record: dict[str, str],
    interaction: discord.Interaction,
    tracking_message=None,
) -> None:
    record["Status"] = "Return Pending"
    record["Actual Return Date"] = _loa_today_text()
    record["Completed By"] = member_display_name(interaction.user)
    record["Completed By ID"] = str(interaction.user.id)
    record["Role Removed"] = "No"
    record["Nickname Removed"] = "No"
    record["Badge Removed"] = "No"
    await asyncio.to_thread(_loa_update_record, record)
    await _loa_edit_tracking_message(record, tracking_message)


def _loa_finish_if_ready(record: dict[str, str]) -> None:
    if all(record.get(field) == "Yes" for field in ("Role Removed", "Nickname Removed", "Badge Removed")):
        record["Status"] = "Completed"


class LOAExtendModal(discord.ui.Modal, title="Extend LOA"):
    new_end_date = discord.ui.TextInput(
        label="New End Date",
        placeholder="YYYY-MM-DD",
        required=True,
        max_length=10,
    )
    notes = discord.ui.TextInput(
        label="Extension Notes",
        placeholder="Optional portal notes or reason",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
    )

    def __init__(self, record_message_id: int):
        super().__init__()
        self.record_message_id = record_message_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await _loa_require_staff(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            new_end = _loa_parse_date(self.new_end_date.value)
            record = await asyncio.to_thread(_loa_find_by_message, self.record_message_id)
            if record is None:
                await interaction.followup.send("This LOA record was not found.", ephemeral=True)
                return
            start_date = _loa_parse_date(record.get("Start Date"))
            current_end = _loa_parse_date(record.get("End Date"))
            if new_end <= current_end:
                await interaction.followup.send("The new end date must be after the current end date.", ephemeral=True)
                return
            if new_end < start_date:
                await interaction.followup.send("The end date cannot be before the start date.", ephemeral=True)
                return
            record["Previous End Date"] = record.get("End Date")
            record["End Date"] = new_end.isoformat()
            record["Duration Days"] = str((new_end - start_date).days + 1)
            record["Extension Notes"] = _loa_protect(self.notes.value) or "N/A"
            record["Status"] = "Extended"
            record["Reminder Status"] = "Not sent"
            record["Reminder Sent At"] = ""
            record["Overdue Alert Sent"] = "No"
            await asyncio.to_thread(_loa_update_record, record)
            await _loa_edit_tracking_message(record)
            await interaction.followup.send(
'''
