PART = r'''
def setup_loa_sheet_layout() -> None:
    sheet = get_loa_worksheet()
    apply_sales_sheet_style(sheet, len(LOA_HEADERS))


def _loa_record_from_row(row: list[object], row_number: int) -> dict[str, str]:
    padded = [clean_text(value) for value in row] + [""] * len(LOA_HEADERS)
    record = {header: padded[index] for index, header in enumerate(LOA_HEADERS)}
    record["_row"] = str(row_number)
    return record


def _loa_all_records() -> list[dict[str, str]]:
    sheet = get_loa_worksheet()
    values = sheet.get_all_values()
    records = []
    for row_number, row in enumerate(values[1:], start=2):
        if any(clean_text(cell) for cell in row):
            records.append(_loa_record_from_row(row, row_number))
    return records


def _loa_append_record(record: dict[str, str]) -> dict[str, str]:
    sheet = get_loa_worksheet()
    row = [_loa_protect(record.get(header, "")) for header in LOA_HEADERS]
    sheet.append_row(row, value_input_option="USER_ENTERED")
    values = sheet.get_all_values()
    record["_row"] = str(len(values))
    apply_sales_sheet_style(sheet, len(LOA_HEADERS))
    return record


def _loa_update_record(record: dict[str, str]) -> dict[str, str]:
    row_number = int(record["_row"])
    record["Last Updated"] = _loa_now_text()
    row = [_loa_protect(record.get(header, "")) for header in LOA_HEADERS]
    end_column = _loa_column_letter(len(LOA_HEADERS))
    sheet = get_loa_worksheet()
    sheet.update(
        range_name=f"A{row_number}:{end_column}{row_number}",
        values=[row],
        value_input_option="USER_ENTERED",
    )
    apply_sales_sheet_style(sheet, len(LOA_HEADERS))
    return record


def _loa_find_by_message(message_id: int | str) -> dict[str, str] | None:
    wanted = str(message_id)
    for record in reversed(_loa_all_records()):
        if record.get("Tracking Message ID") == wanted:
            return record
    return None


def _loa_find_latest_for_member(member_id: int | str, open_only: bool = False) -> dict[str, str] | None:
    wanted = str(member_id)
    for record in reversed(_loa_all_records()):
        if record.get("Discord Member ID") != wanted:
            continue
        if open_only and record.get("Status") not in LOA_OPEN_STATUSES:
            continue
        return record
    return None


def _loa_checkmark(record: dict[str, str], field: str, by_field: str, at_field: str) -> str:
    if record.get(field) == "Yes":
        by_value = record.get(by_field) or "Unknown staff member"
        at_value = record.get(at_field) or "Unknown time"
        return f"✅ Confirmed by **{by_value}**\n{at_value}"
    return "⏳ Waiting for confirmation"


def _loa_removed_checkmark(record: dict[str, str], field: str, by_field: str, at_field: str) -> str:
    if record.get(field) == "Yes":
        by_value = record.get(by_field) or "Unknown staff member"
        at_value = record.get(at_field) or "Unknown time"
        return f"✅ Confirmed by **{by_value}**\n{at_value}"
    return "⏳ Waiting for confirmation"


def _loa_status_style(status: str):
    if status == "Completed":
        return "✅ COMPLETED LEAVE OF ABSENCE", discord.Color.green()
    if status == "Return Pending":
        return "🟡 RETURN PROCESS IN PROGRESS", discord.Color.gold()
    if status == "Overdue":
        return "🔴 OVERDUE LEAVE OF ABSENCE", discord.Color.red()
    if status == "Extended":
        return "🔵 EXTENDED LEAVE OF ABSENCE", discord.Color.blue()
    return "🟢 ACTIVE LEAVE OF ABSENCE", discord.Color.green()


def build_loa_embed(record: dict[str, str]) -> discord.Embed:
    status = record.get("Status") or "Active"
    title, color = _loa_status_style(status)
    member_id = record.get("Discord Member ID")
    member_value = f"<@{member_id}>" if member_id else record.get("Discord Username", "Unknown")
    start_date = _loa_display_date(record.get("Start Date"))
    end_date = _loa_display_date(record.get("End Date"))

    embed = discord.Embed(
        title=title,
        description="Permanent Discord copy of an approved portal LOA record.",
        color=color,
        timestamp=_loa_now(),
    )
    embed.add_field(name="Member", value=member_value, inline=True)
    embed.add_field(name="Habbo Username", value=record.get("Habbo Username") or "N/A", inline=True)
    embed.add_field(name="Record ID", value=f"`{record.get('Record ID') or 'N/A'}`", inline=True)
    embed.add_field(name="LOA Period", value=f"{start_date} — {end_date}", inline=False)
    embed.add_field(name="Duration", value=f"{record.get('Duration Days') or '0'} day(s)", inline=True)
    embed.add_field(name="Portal Status", value="✅ Approved", inline=True)
    embed.add_field(name="Reason", value=record.get("Reason") or "N/A", inline=False)
    if record.get("Portal Notes") and record.get("Portal Notes") != "N/A":
        embed.add_field(name="Portal Notes", value=record.get("Portal Notes"), inline=False)

    if record.get("Previous End Date"):
        embed.add_field(
            name="Extension",
            value=(
                f"Previous end: {_loa_display_date(record.get('Previous End Date'))}\n"
                f"New end: {end_date}\n"
                f"Notes: {record.get('Extension Notes') or 'N/A'}"
'''
