PART = r'''
                f"✅ LOA extended to {_loa_display_date(new_end.isoformat())}. The permanent log was updated.",
                ephemeral=True,
            )
        except ValueError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
        except Exception as exc:
            print(f"LOA extension error: {type(exc).__name__}: {exc}")
            await interaction.followup.send(f"Could not extend the LOA: {type(exc).__name__}: {exc}", ephemeral=True)


class LOAReturnConfirmView(discord.ui.View):
    def __init__(self, record_message_id: int):
        super().__init__(timeout=60)
        self.record_message_id = record_message_id

    @discord.ui.button(label="Confirm Return", emoji="✅", style=discord.ButtonStyle.danger)
    async def confirm_return(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await _loa_require_staff(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        record = await asyncio.to_thread(_loa_find_by_message, self.record_message_id)
        if record is None:
            await interaction.followup.send("This LOA record was not found.", ephemeral=True)
            return
        if record.get("Status") not in {"Active", "Extended", "Overdue"}:
            await interaction.followup.send("This LOA is not currently active.", ephemeral=True)
            return
        source_message = None
        try:
            channel_id = int(record.get("Tracking Channel ID") or "0")
            channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
            source_message = await channel.fetch_message(int(record.get("Tracking Message ID") or "0"))
        except (ValueError, discord.DiscordException):
            source_message = None
        await _loa_mark_return(record, interaction, source_message)
        await interaction.followup.send(
            "✅ Return recorded. Manually remove the role, nickname tag, and badge, then confirm each removal on the permanent log.",
            ephemeral=True,
        )
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(content="Return action cancelled.", view=None)
        self.stop()


class LOAActiveView(discord.ui.View):
    def __init__(self, record: dict[str, str] | None = None):
        super().__init__(timeout=None)
        if record is not None:
            if record.get("Role Confirmed") == "Yes":
                self.remove_item(self.confirm_role)
            if record.get("Nickname Confirmed") == "Yes":
                self.remove_item(self.confirm_nickname)
            if record.get("Badge Confirmed") == "Yes":
                self.remove_item(self.confirm_badge)

    @discord.ui.button(label="Confirm LOA Role", emoji="🎭", style=discord.ButtonStyle.primary, custom_id="loa:confirm_role", row=0)
    async def confirm_role(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await _loa_confirm_field(interaction, "Role Confirmed", "Role Confirmed By", "Role Confirmed At", "LOA Discord role")

    @discord.ui.button(label="Confirm Nickname Added", emoji="✏️", style=discord.ButtonStyle.primary, custom_id="loa:confirm_nickname", row=0)
    async def confirm_nickname(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await _loa_confirm_field(interaction, "Nickname Confirmed", "Nickname Confirmed By", "Nickname Confirmed At", "[LOA] nickname")

    @discord.ui.button(label="Confirm LOA Badge", emoji="🏅", style=discord.ButtonStyle.primary, custom_id="loa:confirm_badge", row=0)
    async def confirm_badge(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await _loa_confirm_field(interaction, "Badge Confirmed", "Badge Confirmed By", "Badge Confirmed At", "LOA badge")

    @discord.ui.button(label="Extend LOA", emoji="📅", style=discord.ButtonStyle.secondary, custom_id="loa:extend", row=1)
    async def extend_loa(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await _loa_require_staff(interaction):
            return
        if interaction.message is None:
            await interaction.response.send_message("I could not identify the LOA record.", ephemeral=True)
            return
        await interaction.response.send_modal(LOAExtendModal(interaction.message.id))

    @discord.ui.button(label="Member Returned", emoji="🏠", style=discord.ButtonStyle.success, custom_id="loa:return", row=1)
    async def member_returned(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await _loa_require_staff(interaction):
            return
        if interaction.message is None:
            await interaction.response.send_message("I could not identify the LOA record.", ephemeral=True)
            return
        await interaction.response.send_message(
            "Are you sure the member has returned? This begins the manual removal confirmation process.",
            view=LOAReturnConfirmView(interaction.message.id),
            ephemeral=True,
        )


class LOAReturnView(discord.ui.View):
    def __init__(self, record: dict[str, str] | None = None):
        super().__init__(timeout=None)
        if record is not None:
            if record.get("Role Removed") == "Yes":
                self.remove_item(self.confirm_role_removed)
            if record.get("Nickname Removed") == "Yes":
                self.remove_item(self.confirm_nickname_removed)
            if record.get("Badge Removed") == "Yes":
                self.remove_item(self.confirm_badge_removed)

    async def _confirm_removed(self, interaction: discord.Interaction, field: str, by_field: str, at_field: str, label: str) -> None:
        if not await _loa_require_staff(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        if interaction.message is None:
            await interaction.followup.send("I could not identify the LOA record.", ephemeral=True)
            return
        record = await asyncio.to_thread(_loa_find_by_message, interaction.message.id)
        if record is None:
            await interaction.followup.send("This LOA record was not found.", ephemeral=True)
            return
        if record.get(field) == "Yes":
            await interaction.followup.send(f"{label} was already confirmed.", ephemeral=True)
            return
        record[field] = "Yes"
        record[by_field] = member_display_name(interaction.user)
        record[at_field] = _loa_now_text()
        _loa_finish_if_ready(record)
        await asyncio.to_thread(_loa_update_record, record)
        await _loa_edit_tracking_message(record, interaction.message)
        if record.get("Status") == "Completed":
'''
