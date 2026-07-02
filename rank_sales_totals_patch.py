from pathlib import Path

p = Path("bot.py")
s = p.read_text(encoding="utf-8")


def rep(old: str, new: str) -> None:
    global s
    if old in s:
        s = s.replace(old, new)

# Add a separate seller totals sheet name.
rep(
    'RANK_SALES_SHEET_NAME = os.getenv("RANK_SALES_SHEET_NAME", "Rank Sales")\n',
    'RANK_SALES_SHEET_NAME = os.getenv("RANK_SALES_SHEET_NAME", "Rank Sales")\n'
    'RANK_SALES_TOTALS_SHEET_NAME = os.getenv("RANK_SALES_TOTALS_SHEET_NAME", "Rank Seller Totals")\n',
)

# Add headers for the seller totals sheet.
if "RANK_SALES_TOTALS_HEADERS" not in s:
    rep(
        'RANK_SALES_HEADERS = [\n    "Discord Username",\n    "Habbo Username",\n    "Buyer",\n    "Rank Sold",\n    "Amount",\n    "Proof / Notes",\n    "Timestamp",\n]\n',
        'RANK_SALES_HEADERS = [\n    "Discord Username",\n    "Habbo Username",\n    "Buyer",\n    "Rank Sold",\n    "Amount",\n    "Proof / Notes",\n    "Timestamp",\n]\n\n'
        'RANK_SALES_TOTALS_HEADERS = [\n    "Discord Username",\n    "Habbo Username",\n    "Total Sales",\n    "Total Amount Sold",\n    "Last Sale",\n    "Last Rank Sold",\n]\n',
    )

# After each sale is added, rebuild seller totals and add them to the Discord log embed.
rep(
    '            await asyncio.to_thread(append_rank_sale_to_sheet, row)\n\n            embed = discord.Embed(',
    '            await asyncio.to_thread(append_rank_sale_to_sheet, row)\n\n'
    '            seller_summary = None\n'
    '            try:\n'
    '                totals = await asyncio.to_thread(sync_rank_seller_totals)\n'
    '                seller_summary = find_seller_summary(totals, row[0], row[1])\n'
    '            except Exception as totals_exc:\n'
    '                print(f"Rank seller totals warning: {type(totals_exc).__name__}: {totals_exc}")\n\n'
    '            embed = discord.Embed(',
)

rep(
    '            embed.add_field(name="Amount", value=amount, inline=True)\n            embed.add_field(name="Proof / Notes", value=proof, inline=False)',
    '            embed.add_field(name="Amount", value=amount, inline=True)\n'
    '            if seller_summary:\n'
    '                embed.add_field(name="Seller Total Sales", value=str(seller_summary["total_sales"]), inline=True)\n'
    '                embed.add_field(name="Seller Total Amount Sold", value=format_total_credits(seller_summary), inline=True)\n'
    '            else:\n'
    '                embed.add_field(name="Seller Totals", value="Sale logged. Totals could not sync yet.", inline=False)\n'
    '            embed.add_field(name="Proof / Notes", value=proof, inline=False)',
)

# Helper functions for rebuilding totals from the Rank Sales sheet.
helper_code = r'''


def get_rank_sales_totals_worksheet():
    if not GOOGLE_CREDENTIALS_JSON:
        raise RuntimeError("GOOGLE_CREDENTIALS_JSON is missing in Railway Variables.")
    if not SPREADSHEET_ID:
        raise RuntimeError("SPREADSHEET_ID is missing in Railway Variables.")

    credentials_info = json.loads(GOOGLE_CREDENTIALS_JSON)
    credentials = Credentials.from_service_account_info(credentials_info, scopes=GOOGLE_SCOPES)
    sheets_client = gspread.authorize(credentials)
    spreadsheet = sheets_client.open_by_key(SPREADSHEET_ID)

    try:
        worksheet = spreadsheet.worksheet(RANK_SALES_TOTALS_SHEET_NAME)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=RANK_SALES_TOTALS_SHEET_NAME, rows=1000, cols=len(RANK_SALES_TOTALS_HEADERS))

    return worksheet


def amount_to_credits(amount: str) -> float | None:
    text = str(amount or "").strip().lower().replace(",", "")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    value = float(match.group(0))
    if "gb" in text or "gold bar" in text or "goldbar" in text:
        return value * 50
    return value


def normalize_seller_key(discord_username: str, habbo_username: str) -> str:
    discord_username = str(discord_username or "").strip()
    habbo_username = str(habbo_username or "").strip()
    return (discord_username or habbo_username).casefold()


def format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def format_total_credits(summary: dict) -> str:
    if not summary.get("has_credit_total"):
        return "N/A"
    return f"{format_number(float(summary.get('total_credits', 0)))}c"


def calculate_rank_seller_totals(values: list[list[str]]) -> list[dict]:
    totals = {}

    for row in values[1:]:
        if not any(str(cell).strip() for cell in row):
            continue

        padded = list(row) + [""] * len(RANK_SALES_HEADERS)
        discord_username = str(padded[0]).strip()
        habbo_username = str(padded[1]).strip()
        rank_sold = str(padded[3]).strip()
        amount = str(padded[4]).strip()
        timestamp = str(padded[6]).strip()

        seller_key = normalize_seller_key(discord_username, habbo_username)
        if not seller_key:
            continue

        if seller_key not in totals:
            totals[seller_key] = {
                "seller_key": seller_key,
                "discord_username": discord_username,
                "habbo_username": habbo_username,
                "total_sales": 0,
                "total_credits": 0.0,
                "has_credit_total": False,
                "last_sale": "",
                "last_rank_sold": "",
            }

        entry = totals[seller_key]
        entry["discord_username"] = discord_username or entry["discord_username"]
        entry["habbo_username"] = habbo_username or entry["habbo_username"]
        entry["total_sales"] += 1

        credits = amount_to_credits(amount)
        if credits is not None:
            entry["total_credits"] += credits
            entry["has_credit_total"] = True

        entry["last_sale"] = timestamp
        entry["last_rank_sold"] = rank_sold

    return sorted(
        totals.values(),
        key=lambda item: (
            float(item["total_credits"]) if item["has_credit_total"] else -1.0,
            int(item["total_sales"]),
            str(item["discord_username"]).casefold(),
        ),
        reverse=True,
    )


def apply_rank_sales_totals_sheet_style(worksheet) -> None:
    try:
        worksheet.format("A1:F1", {
            "backgroundColor": {"red": 0.10, "green": 0.06, "blue": 0.22},
            "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True, "fontSize": 11},
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE",
        })
        worksheet.format("A2:F1000", {
            "backgroundColor": {"red": 0.96, "green": 0.94, "blue": 1.0},
            "textFormat": {"foregroundColor": {"red": 0.08, "green": 0.08, "blue": 0.12}},
            "verticalAlignment": "MIDDLE",
        })
        worksheet.format("A:F", {"horizontalAlignment": "CENTER"})
        try:
            worksheet.freeze(rows=1)
        except Exception:
            pass
        try:
            worksheet.columns_auto_resize(0, 6)
        except Exception:
            pass
    except Exception as exc:
        print(f"Rank seller totals sheet style warning: {type(exc).__name__}: {exc}")


def sync_rank_seller_totals() -> list[dict]:
    sales_worksheet = get_rank_sales_worksheet()
    values = sales_worksheet.get_all_values()

    if not values:
        values = [RANK_SALES_HEADERS]
        sales_worksheet.update(range_name="A1", values=values, value_input_option="USER_ENTERED")
        apply_rank_sales_sheet_style(sales_worksheet)

    totals = calculate_rank_seller_totals(values)
    total_rows = [RANK_SALES_TOTALS_HEADERS]
    for item in totals:
        total_rows.append([
            item["discord_username"],
            item["habbo_username"],
            item["total_sales"],
            format_total_credits(item),
            item["last_sale"],
            item["last_rank_sold"],
        ])

    totals_worksheet = get_rank_sales_totals_worksheet()
    totals_worksheet.clear()
    totals_worksheet.update(range_name="A1", values=total_rows, value_input_option="USER_ENTERED")
    apply_rank_sales_totals_sheet_style(totals_worksheet)
    return totals


def find_seller_summary(totals: list[dict], discord_username: str, habbo_username: str) -> dict | None:
    seller_key = normalize_seller_key(discord_username, habbo_username)
    for item in totals:
        if item["seller_key"] == seller_key:
            return item
    return None
'''

if "def sync_rank_seller_totals" not in s:
    rep(
        '    except Exception as exc:\n        print(f"Rank sales sheet style warning: {type(exc).__name__}: {exc}")\n\n\ndef setup_rank_sales_sheet_layout() -> None:',
        '    except Exception as exc:\n        print(f"Rank sales sheet style warning: {type(exc).__name__}: {exc}")'
        + helper_code +
        '\n\ndef setup_rank_sales_sheet_layout() -> None:',
    )

# Rebuild the totals sheet when the setup command is used.
rep(
    '    apply_rank_sales_sheet_style(worksheet)\n\n\ndef append_rank_sale_to_sheet(row: list[str]) -> None:',
    '    apply_rank_sales_sheet_style(worksheet)\n    sync_rank_seller_totals()\n\n\ndef append_rank_sale_to_sheet(row: list[str]) -> None:',
)

summary_command = r'''

@bot.tree.command(name="rank-sales-summary", description="Show the top rank sellers based on logged sales.")
@app_commands.describe(limit="How many sellers to show, from 1 to 25")
async def rank_sales_summary(interaction: discord.Interaction, limit: int = 10) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return

    if not await member_can_log_sales(interaction):
        await interaction.response.send_message("You do not have permission to view rank sales.", ephemeral=True)
        return

    if not SPREADSHEET_ID or not GOOGLE_CREDENTIALS_JSON:
        await interaction.response.send_message(
            "Rank sales logging is not configured yet. Add SPREADSHEET_ID and GOOGLE_CREDENTIALS_JSON in Railway Variables.",
            ephemeral=True,
        )
        return

    limit = max(1, min(int(limit), 25))
    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        totals = await asyncio.to_thread(sync_rank_seller_totals)
    except Exception as exc:
        print(f"Rank sales summary error: {type(exc).__name__}: {exc}")
        await interaction.followup.send(f"Could not load rank sales summary: {type(exc).__name__}: {exc}", ephemeral=True)
        return

    if not totals:
        await interaction.followup.send("No rank sales have been logged yet.", ephemeral=True)
        return

    lines = []
    for index, item in enumerate(totals[:limit], start=1):
        seller = item["habbo_username"] or item["discord_username"] or "Unknown Seller"
        lines.append(f"**{index}. {seller}** — {item['total_sales']} sales — {format_total_credits(item)} total")

    embed = discord.Embed(
        title="Rank Seller Totals",
        description="\n".join(lines),
        color=discord.Color.purple(),
        timestamp=datetime.now(ZoneInfo(TIMEZONE)),
    )
    embed.set_footer(text=f"Synced from the {RANK_SALES_TOTALS_SHEET_NAME} sheet")
    await interaction.followup.send(embed=embed, ephemeral=True)
'''

if "rank-sales-summary" not in s:
    rep(
        '\n\n@bot.tree.command(name="setup-rank-sales-sheet", description="Clean and style the rank sales Google Sheet.")',
        summary_command + '\n\n@bot.tree.command(name="setup-rank-sales-sheet", description="Clean and style the rank sales Google Sheet.")',
    )

rep(
    'Rank Sales sheet cleaned and styled. Columns are now: Discord Username, Habbo Username, Buyer, Rank Sold, Amount, Proof / Notes, Timestamp.',
    'Rank Sales sheet cleaned and styled. Rank Seller Totals was also rebuilt from all logged sales.',
)

p.write_text(s, encoding="utf-8")
print("Rank sales totals patch applied.")
