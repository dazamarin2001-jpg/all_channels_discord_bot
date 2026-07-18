PART = r'''
            await interaction.followup.send("✅ Final removal confirmed. The LOA is now completed and the permanent log is read-only.", ephemeral=True)
        else:
            await interaction.followup.send(f"✅ {label} confirmed and the permanent log was updated.", ephemeral=True)

    @discord.ui.button(label="Confirm Role Removed", emoji="🎭", style=discord.ButtonStyle.danger, custom_id="loa:role_removed", row=0)
    async def confirm_role_removed(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._confirm_removed(interaction, "Role Removed", "Role Removed By", "Role Removed At", "LOA role removal")

    @discord.ui.button(label="Confirm Nickname Removed", emoji="✏️", style=discord.ButtonStyle.danger, custom_id="loa:nickname_removed", row=0)
    async def confirm_nickname_removed(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._confirm_removed(interaction, "Nickname Removed", "Nickname Removed By", "Nickname Removed At", "[LOA] nickname removal")

    @discord.ui.button(label="Confirm Badge Removed", emoji="🏅", style=discord.ButtonStyle.danger, custom_id="loa:badge_removed", row=0)
    async def confirm_badge_removed(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._confirm_removed(interaction, "Badge Removed", "Badge Removed By", "Badge Removed At", "LOA badge removal")


class LOAAddModal(discord.ui.Modal, title="Add Approved LOA Record"):
    habbo_username = discord.ui.TextInput(
        label="Habbo Username",
        placeholder="Example: HabboUsername",
        required=True,
        max_length=80,
    )
    start_date = discord.ui.TextInput(
        label="Start Date",
        placeholder="YYYY-MM-DD",
        required=True,
        max_length=10,
    )
    end_date = discord.ui.TextInput(
        label="End Date",
        placeholder="YYYY-MM-DD",
        required=True,
        max_length=10,
    )
    reason = discord.ui.TextInput(
        label="Reason",
        placeholder="Copy the approved reason from the portal",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000,
    )
    portal_notes = discord.ui.TextInput(
        label="Portal Notes",
        placeholder="Optional notes from the portal",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
    )

    def __init__(self, member: discord.Member):
        super().__init__()
        self.member = member

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await _loa_require_staff(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        tracking_message = None
        try:
            start_date = _loa_parse_date(self.start_date.value)
            end_date = _loa_parse_date(self.end_date.value)
            if end_date < start_date:
                await interaction.followup.send("The end date cannot be before the start date.", ephemeral=True)
                return
            existing = await asyncio.to_thread(_loa_find_latest_for_member, self.member.id, True)
            if existing is not None:
                await interaction.followup.send(
                    f"{self.member.mention} already has an open LOA record (`{existing.get('Record ID')}`).",
                    ephemeral=True,
                )
                return
            channel = await get_loa_tracking_channel(interaction.guild)
            if channel is None:
                await interaction.followup.send(
                    "The LOA tracking channel is not configured. Add LOA_TRACKING_CHANNEL_ID in Railway Variables.",
                    ephemeral=True,
                )
                return
            now = _loa_now()
            record_id = f"LOA-{now.strftime('%Y%m%d%H%M')}-{str(self.member.id)[-6:]}"
            record = {header: "" for header in LOA_HEADERS}
            record.update(
                {
                    "Record ID": record_id,
                    "Guild ID": str(interaction.guild.id),
                    "Discord Member ID": str(self.member.id),
                    "Discord Username": member_display_name(self.member),
                    "Habbo Username": _loa_protect(self.habbo_username.value),
                    "Start Date": start_date.isoformat(),
                    "End Date": end_date.isoformat(),
                    "Duration Days": str((end_date - start_date).days + 1),
                    "Reason": _loa_protect(self.reason.value),
                    "Portal Notes": _loa_protect(self.portal_notes.value) or "N/A",
                    "Status": "Active",
                    "Recorded By": member_display_name(interaction.user),
                    "Recorded By ID": str(interaction.user.id),
                    "Role Confirmed": "No",
                    "Nickname Confirmed": "No",
                    "Badge Confirmed": "No",
                    "Reminder Status": "Not sent",
                    "Role Removed": "No",
                    "Nickname Removed": "No",
                    "Badge Removed": "No",
                    "Overdue Alert Sent": "No",
                    "Last Updated": _loa_now_text(),
                }
            )
            tracking_message = await channel.send(embed=build_loa_embed(record), view=_loa_active_view_for(record))
            record["Tracking Channel ID"] = str(tracking_message.channel.id)
            record["Tracking Message ID"] = str(tracking_message.id)
            await asyncio.to_thread(_loa_append_record, record)
            await tracking_message.edit(embed=build_loa_embed(record), view=_loa_active_view_for(record))
            await interaction.followup.send(
                f"✅ LOA record added to {channel.mention}. Assign the role, nickname, and badge manually, then use the confirmation buttons.",
                ephemeral=True,
            )
        except ValueError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
        except Exception as exc:
            print(f"LOA add error: {type(exc).__name__}: {exc}")
            if tracking_message is not None:
                try:
                    await tracking_message.delete()
'''
