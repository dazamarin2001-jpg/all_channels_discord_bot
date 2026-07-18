PART = r'''
        except ValueError:
            continue
        if end_date < today:
            overdue_records.append((end_date, record))
    if not overdue_records:
        await interaction.followup.send("There are no overdue LOA records.", ephemeral=True)
        return
    overdue_records.sort(key=lambda item: item[0])
    lines = []
    for end_date, record in overdue_records[:20]:
        overdue_days = (today - end_date).days
        lines.append(
            f"• <@{record.get('Discord Member ID')}> — **{record.get('Habbo Username') or 'N/A'}**\n"
            f"  Expected return: {_loa_display_date(end_date.isoformat())} · {overdue_days} day(s) overdue"
        )
    embed = discord.Embed(title="Overdue LOA Records", description="\n\n".join(lines), color=discord.Color.red(), timestamp=_loa_now())
    await interaction.followup.send(embed=embed, ephemeral=True)


@leave_group.command(name="setup", description="Create and style the LOA Records sheet tab.")
@app_commands.checks.has_permissions(administrator=True)
async def leave_setup(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await asyncio.to_thread(setup_loa_sheet_layout)
        await interaction.followup.send("✅ The LOA Records sheet tab is ready.", ephemeral=True)
    except Exception as exc:
        print(f"LOA sheet setup error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(f"Could not set up the LOA sheet: {type(exc).__name__}: {exc}", ephemeral=True)


bot.tree.add_command(leave_group)


@tasks.loop(hours=24)
async def loa_daily_monitor() -> None:
    records = await asyncio.to_thread(_loa_all_records)
    today = _loa_now().date()
    for record in records:
        if record.get("Status") not in {"Active", "Extended", "Overdue"}:
            continue
        try:
            end_date = _loa_parse_date(record.get("End Date"))
        except ValueError:
            continue

        changed = False
        if end_date < today and record.get("Status") != "Overdue":
            record["Status"] = "Overdue"
            changed = True

        reminder_date = end_date - _loa_timedelta(days=LOA_REMINDER_DAYS)
        if today >= reminder_date and today <= end_date and record.get("Reminder Status") in {"", "Not sent"}:
            member_id = record.get("Discord Member ID")
            dm_sent = False
            if member_id:
                try:
                    user = bot.get_user(int(member_id)) or await bot.fetch_user(int(member_id))
                    await user.send(
                        "⏰ **Your Leave of Absence Ends Soon**\n\n"
                        f"Your approved FSA LOA is scheduled to end on **{_loa_display_date(record.get('End Date'))}**.\n\n"
                        "Please contact the appropriate FSA staff member if you need an extension or cannot return as scheduled."
                    )
                    dm_sent = True
                except (ValueError, discord.DiscordException):
                    dm_sent = False
            record["Reminder Status"] = "✅ Member DM sent" if dm_sent else "⚠️ DM unavailable; staff alert sent"
            record["Reminder Sent At"] = _loa_now_text()
            changed = True
            try:
                channel_id = int(record.get("Tracking Channel ID") or "0")
                channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
                await channel.send(
                    "⏰ **LOA Ending Soon**\n"
                    f"<@{record.get('Discord Member ID')}> (**{record.get('Habbo Username') or 'N/A'}**) is scheduled to return on "
                    f"**{_loa_display_date(record.get('End Date'))}**."
                )
            except (ValueError, discord.DiscordException):
                pass

        if end_date < today and record.get("Overdue Alert Sent") != "Yes":
            record["Overdue Alert Sent"] = "Yes"
            changed = True
            try:
                channel_id = int(record.get("Tracking Channel ID") or "0")
                channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
                overdue_days = (today - end_date).days
                await channel.send(
                    "⚠️ **LOA Overdue**\n"
                    f"<@{record.get('Discord Member ID')}> (**{record.get('Habbo Username') or 'N/A'}**) was expected back on "
                    f"**{_loa_display_date(record.get('End Date'))}** and is now **{overdue_days} day(s) overdue**."
                )
            except (ValueError, discord.DiscordException):
                pass

        if changed:
            await asyncio.to_thread(_loa_update_record, record)
            await _loa_edit_tracking_message(record)


@loa_daily_monitor.before_loop
async def before_loa_daily_monitor() -> None:
    await bot.wait_until_ready()


_loa_startup_complete = False


@bot.listen("on_ready")
async def loa_startup() -> None:
    global _loa_startup_complete
    if not _loa_startup_complete:
        bot.add_view(LOAActiveView())
        bot.add_view(LOAReturnView())
        _loa_startup_complete = True
    if not loa_daily_monitor.is_running():
        loa_daily_monitor.start()
# ---- End LOA tracking commands ----
'''
