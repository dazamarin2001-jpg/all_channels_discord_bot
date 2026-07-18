PART = r'''
                except discord.DiscordException:
                    pass
            await interaction.followup.send(f"Could not add the LOA record: {type(exc).__name__}: {exc}", ephemeral=True)


leave_group = app_commands.Group(name="leave", description="Track approved portal LOA records in Discord.")


@leave_group.command(name="add", description="Copy an approved portal LOA into the Discord tracker.")
@app_commands.describe(member="Member whose approved LOA should be tracked")
@app_commands.check(_loa_staff_allowed)
async def leave_add(interaction: discord.Interaction, member: discord.Member) -> None:
    if not SPREADSHEET_ID or not GOOGLE_CREDENTIALS_JSON:
        await interaction.response.send_message(
            "LOA tracking needs SPREADSHEET_ID and GOOGLE_CREDENTIALS_JSON in Railway Variables.",
            ephemeral=True,
        )
        return
    if not LOA_TRACKING_CHANNEL_ID:
        await interaction.response.send_message("Add LOA_TRACKING_CHANNEL_ID in Railway Variables first.", ephemeral=True)
        return
    await interaction.response.send_modal(LOAAddModal(member))


@leave_group.command(name="active", description="Show all active LOA records.")
@app_commands.check(_loa_staff_allowed)
async def leave_active(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        records = await asyncio.to_thread(_loa_all_records)
        active_records = [record for record in records if record.get("Status") in LOA_OPEN_STATUSES]
        if not active_records:
            await interaction.followup.send("There are no open LOA records.", ephemeral=True)
            return
        active_records.sort(key=lambda record: record.get("End Date") or "9999-12-31")
        lines = []
        today = _loa_now().date()
        for record in active_records[:20]:
            try:
                days_left = (_loa_parse_date(record.get("End Date")) - today).days
                timing = f"{days_left} day(s) remaining" if days_left >= 0 else f"{abs(days_left)} day(s) overdue"
            except ValueError:
                timing = "Invalid end date"
            lines.append(
                f"• <@{record.get('Discord Member ID')}> — **{record.get('Habbo Username') or 'N/A'}**\n"
                f"  {_loa_display_date(record.get('Start Date'))} → {_loa_display_date(record.get('End Date'))} · {timing} · {record.get('Status')}"
            )
        embed = discord.Embed(
            title="Active LOA Records",
            description="\n\n".join(lines),
            color=discord.Color.blue(),
            timestamp=_loa_now(),
        )
        if len(active_records) > 20:
            embed.set_footer(text=f"Showing 20 of {len(active_records)} open records")
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as exc:
        print(f"LOA active list error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(f"Could not load LOA records: {type(exc).__name__}: {exc}", ephemeral=True)


@leave_group.command(name="view", description="View a member's latest LOA record.")
@app_commands.describe(member="Member whose LOA record should be displayed")
@app_commands.check(_loa_staff_allowed)
async def leave_view(interaction: discord.Interaction, member: discord.Member) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    record = await asyncio.to_thread(_loa_find_latest_for_member, member.id, False)
    if record is None:
        await interaction.followup.send(f"No LOA record was found for {member.mention}.", ephemeral=True)
        return
    await interaction.followup.send(embed=build_loa_embed(record), ephemeral=True)


@leave_group.command(name="extend", description="Extend an open LOA record.")
@app_commands.describe(member="Member whose LOA should be extended")
@app_commands.check(_loa_staff_allowed)
async def leave_extend(interaction: discord.Interaction, member: discord.Member) -> None:
    record = await asyncio.to_thread(_loa_find_latest_for_member, member.id, True)
    if record is None:
        await interaction.response.send_message(f"No open LOA was found for {member.mention}.", ephemeral=True)
        return
    try:
        message_id = int(record.get("Tracking Message ID") or "0")
    except ValueError:
        message_id = 0
    if not message_id:
        await interaction.response.send_message("The tracking message ID is missing for this record.", ephemeral=True)
        return
    await interaction.response.send_modal(LOAExtendModal(message_id))


@leave_group.command(name="return", description="Begin the return process for an open LOA.")
@app_commands.describe(member="Member who has returned from LOA")
@app_commands.check(_loa_staff_allowed)
async def leave_return(interaction: discord.Interaction, member: discord.Member) -> None:
    record = await asyncio.to_thread(_loa_find_latest_for_member, member.id, True)
    if record is None:
        await interaction.response.send_message(f"No open LOA was found for {member.mention}.", ephemeral=True)
        return
    try:
        message_id = int(record.get("Tracking Message ID") or "0")
    except ValueError:
        message_id = 0
    if not message_id:
        await interaction.response.send_message("The tracking message ID is missing for this record.", ephemeral=True)
        return
    await interaction.response.send_message(
        "Are you sure the member has returned? This begins the manual removal confirmation process.",
        view=LOAReturnConfirmView(message_id),
        ephemeral=True,
    )


@leave_group.command(name="overdue", description="Show LOA records whose end date has passed.")
@app_commands.check(_loa_staff_allowed)
async def leave_overdue(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    records = await asyncio.to_thread(_loa_all_records)
    today = _loa_now().date()
    overdue_records = []
    for record in records:
        if record.get("Status") not in {"Active", "Extended", "Overdue"}:
            continue
        try:
            end_date = _loa_parse_date(record.get("End Date"))
'''
