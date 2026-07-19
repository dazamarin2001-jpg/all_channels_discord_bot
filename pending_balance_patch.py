"""Patch trade and sales-summary logic to calculate durable pending balances.

Pending balances are derived from gross sales/donations minus completed Trade Out
entries in Summary Log. This prevents a totals-sheet rebuild from restoring money
that was already traded to Finance.
"""

from pathlib import Path


path = Path("legacy_main.py")
if not path.exists():
    print("Pending balance patch warning: legacy_main.py was not found.")
else:
    text = path.read_text(encoding="utf-8")
    marker = "PENDING_BALANCE_PATCH_VERSION = 1"

    if marker not in text:
        constants_anchor = (
            'DONATIONS_RECEIVED_HEADER = globals().get("DONATIONS_RECEIVED_HEADER", "Donations Received")\n'
        )
        constants_replacement = constants_anchor + (
            'PENDING_BALANCE_PATCH_VERSION = 1\n'
            'PENDING_SALES_HEADER = "Pending Sales Balance"\n'
            'PENDING_DONATIONS_HEADER = "Pending Donations Balance"\n'
            'TOTAL_TRADED_HEADER = "Total Traded Out"\n'
            'PENDING_FUNDS_HEADER = "Pending Funds"\n'
        )
        if constants_anchor in text:
            text = text.replace(constants_anchor, constants_replacement, 1)
        else:
            print("Pending balance patch warning: trade constants anchor was not found.")

        functions_start = text.find("def read_trade_account_balance(")
        functions_end = text.find("def append_trade_to_summary_log(", functions_start)
        if functions_start != -1 and functions_end != -1:
            new_functions = r'''def _find_header_index(header: list[str], *names: str) -> int | None:
    normalized = [norm(value) for value in header]
    for name in names:
        wanted = norm(name)
        if wanted in normalized:
            return normalized.index(wanted)
    return None


def _gross_sales_by_account(spreadsheet) -> dict[str, float]:
    worksheet = get_rank_sales_worksheet()
    values = worksheet.get_all_values()
    if not values:
        return {}

    header = values[0]
    account_index = _find_header_index(header, "Discord Username", "Discord Seller", "Logged By")
    amount_index = _find_header_index(header, "Amount", "Amount Sold")
    if account_index is None or amount_index is None:
        return {}

    totals: dict[str, float] = {}
    for row in values[1:]:
        padded = list(row) + [""] * len(header)
        account_key = norm(padded[account_index])
        if not account_key:
            continue
        totals[account_key] = totals.get(account_key, 0.0) + (amount_to_credits(padded[amount_index]) or 0.0)
    return totals


def _gross_donations_by_account(spreadsheet) -> dict[str, float]:
    if "get_donations_worksheet" not in globals():
        return {}

    worksheet = get_donations_worksheet(spreadsheet)
    values = worksheet.get_all_values()
    if not values:
        return {}

    header = values[0]
    account_index = _find_header_index(header, "Logged By", "Discord Username", "Account")
    amount_index = _find_header_index(header, "Amount", "Donation Amount")
    if account_index is None or amount_index is None:
        return {}

    totals: dict[str, float] = {}
    for row in values[1:]:
        padded = list(row) + [""] * len(header)
        account_key = norm(padded[account_index])
        if not account_key:
            continue
        totals[account_key] = totals.get(account_key, 0.0) + (amount_to_credits(padded[amount_index]) or 0.0)
    return totals


def _completed_trade_outs_by_account(spreadsheet) -> dict[tuple[str, str], float]:
    worksheet = get_trade_summary_worksheet(spreadsheet)
    values = worksheet.get_all_values()
    totals: dict[tuple[str, str], float] = {}

    for row in values[1:] if len(values) > 1 else []:
        padded = list(row) + [""] * len(TRADE_SUMMARY_HEADERS)
        account_key = norm(padded[0])
        category_key = norm(padded[1])
        action = norm(padded[2])
        status = norm(padded[5])
        if not account_key or category_key not in {"sale", "donation"}:
            continue
        if action != "trade out" or status != "completed":
            continue
        amount = amount_to_credits(padded[3]) or 0.0
        key = (account_key, category_key)
        totals[key] = totals.get(key, 0.0) + abs(amount)

    return totals


def refresh_pending_balances(spreadsheet=None):
    spreadsheet = spreadsheet or get_spreadsheet()
    totals_sheet = ensure_donations_received_column_for_trades(get_rank_seller_totals_worksheet(spreadsheet))
    values = totals_sheet.get_all_values()
    if not values:
        return totals_sheet

    gross_sales = _gross_sales_by_account(spreadsheet)
    gross_donations = _gross_donations_by_account(spreadsheet)
    traded_out = _completed_trade_outs_by_account(spreadsheet)

    pending_rows = [[
        PENDING_SALES_HEADER,
        PENDING_DONATIONS_HEADER,
        TOTAL_TRADED_HEADER,
        PENDING_FUNDS_HEADER,
    ]]

    for row in values[1:]:
        padded = list(row) + [""] * 11
        account_key = norm(padded[0])

        fallback_sales = amount_to_credits(padded[3]) or 0.0
        fallback_donations = amount_to_credits(padded[6]) or 0.0
        sales_total = gross_sales.get(account_key, fallback_sales)
        donations_total = gross_donations.get(account_key, fallback_donations)

        sales_traded = traded_out.get((account_key, "sale"), 0.0)
        donations_traded = traded_out.get((account_key, "donation"), 0.0)
        pending_sales = max(0.0, sales_total - sales_traded)
        pending_donations = max(0.0, donations_total - donations_traded)
        total_traded = sales_traded + donations_traded
        pending_funds = pending_sales + pending_donations

        pending_rows.append([
            format_credits(pending_sales),
            format_credits(pending_donations),
            format_credits(total_traded),
            format_credits(pending_funds),
        ])

    totals_sheet.update(range_name="H1", values=pending_rows, value_input_option="USER_ENTERED")
    apply_sales_sheet_style(totals_sheet, 11)
    return totals_sheet


def read_trade_account_balance(spreadsheet, account: str, category: str) -> tuple[object, int, str, float]:
    totals_sheet = refresh_pending_balances(spreadsheet)
    values = totals_sheet.get_all_values()
    target_account = norm(account)
    category_key = category.casefold()
    balance_index = 8 if category_key == "donation" else 7
    balance_col = "I" if category_key == "donation" else "H"

    for index, row in enumerate(values[1:] if len(values) > 1 else [], start=2):
        padded = list(row) + [""] * 11
        if norm(padded[0]) != target_account:
            continue
        current_balance = amount_to_credits(padded[balance_index]) or 0.0
        return totals_sheet, index, balance_col, current_balance

    raise RuntimeError(f"No Rank Seller Totals row was found for {account}. Log a sale or donation first, then try /trade again.")


def apply_trade_to_sales_summary(account: str, category: str, amount: float) -> tuple[str, str, str]:
    spreadsheet = get_spreadsheet()
    _totals_sheet, _row_index, balance_col, current_balance = read_trade_account_balance(spreadsheet, account, category)

    if current_balance < amount:
        raise RuntimeError(f"{account} only has {format_credits(current_balance)} available in {category} funds.")

    new_balance = current_balance - amount
    return balance_col, format_credits(current_balance), format_credits(new_balance)


'''
            text = text[:functions_start] + new_functions + text[functions_end:]
        else:
            print("Pending balance patch warning: trade balance function block was not found.")

        summary_start = text.find("async def sale_summary_with_donations(")
        summary_end = text.find("\n\ntry:\n    sale_group.remove_command", summary_start)
        if summary_start != -1 and summary_end != -1:
            new_summary = r'''async def sale_summary_with_donations(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        worksheet = await asyncio.to_thread(refresh_pending_balances)
        values = await asyncio.to_thread(worksheet.get_all_values)
        rows = values[1:] if len(values) > 1 else []
        if not rows:
            await interaction.followup.send("No rank seller totals have been synced yet.", ephemeral=True)
            return

        parsed_rows = []
        for row in rows:
            padded = list(row) + [""] * 11
            discord_username = clean_text(padded[0])
            sales_count = clean_text(padded[2]) or "0"
            gross_sales = clean_text(padded[3]) or "0c"
            gross_donations = clean_text(padded[6]) or "0c"
            pending_sales = clean_text(padded[7]) or "0c"
            pending_donations = clean_text(padded[8]) or "0c"
            total_traded = clean_text(padded[9]) or "0c"
            pending_funds = clean_text(padded[10]) or "0c"
            if not discord_username:
                continue
            current_funds = amount_to_credits(pending_funds) or 0.0
            try:
                sort_sales = int(float(sales_count))
            except ValueError:
                sort_sales = 0
            parsed_rows.append((
                current_funds,
                sort_sales,
                discord_username,
                sales_count,
                gross_sales,
                gross_donations,
                pending_sales,
                pending_donations,
                total_traded,
                pending_funds,
            ))

        parsed_rows.sort(key=lambda item: (item[0], item[1]), reverse=True)
        lines = []
        for rank_number, item in enumerate(parsed_rows[:10], start=1):
            (
                _current_funds,
                _sort_sales,
                discord_username,
                sales_count,
                gross_sales,
                gross_donations,
                pending_sales,
                pending_donations,
                total_traded,
                pending_funds,
            ) = item
            sale_word = "sale" if str(sales_count).strip() == "1" else "sales"
            lines.append(
                f"{rank_number}.  **{discord_username}**\n"
                f"— Sales: {sales_count} {sale_word} — Gross: {gross_sales}\n"
                f"— Donations Received: {gross_donations}\n"
                f"— Traded Out: {total_traded}\n"
                f"— Pending Sales: {pending_sales} — Pending Donations: {pending_donations}\n"
                f"— **Pending Funds: {pending_funds}**"
            )

        if not lines:
            await interaction.followup.send("No Discord usernames found in Rank Seller Totals.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Rank Seller Pending Balances",
            description="\n\n".join(lines),
            color=discord.Color.purple(),
            timestamp=datetime.now(ZoneInfo(TIMEZONE)),
        )
        embed.set_footer(text="Gross sales + donations minus completed trades in Summary Log")
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as exc:
        print(f"Rank sales summary error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(f"Could not load sales summary: {type(exc).__name__}: {exc}", ephemeral=True)
'''
            text = text[:summary_start] + new_summary + text[summary_end:]
        else:
            print("Pending balance patch warning: sale summary function was not found.")

        old_trade_flow = '''            _balance_col, old_balance, new_balance = await asyncio.to_thread(apply_trade_to_sales_summary, account, category, amount_value)
            await asyncio.to_thread(
                append_trade_to_summary_log,
                [account, category, "Trade Out", negative_change, traded_to, "Completed"],
            )'''
        new_trade_flow = old_trade_flow + '''
            await asyncio.to_thread(refresh_pending_balances)'''
        if old_trade_flow in text:
            text = text.replace(old_trade_flow, new_trade_flow, 1)
        else:
            print("Pending balance patch warning: trade submission flow was not found.")

        path.write_text(text, encoding="utf-8")
        print("Pending sales and donation balance patch applied.")
    else:
        print("Pending sales and donation balance patch already applied.")
