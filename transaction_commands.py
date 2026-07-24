"""Generated unified FSA transaction commands injected into bot.py at startup."""

TRANSACTION_START_MARKER = "# ---- Unified transaction commands ----"
TRANSACTION_END_MARKER = "# ---- End unified transaction commands ----"

TRANSACTION_BLOCK = r'''
# ---- Unified transaction commands ----
TRANSACTION_SPREADSHEET_ID = os.getenv(
    "TRANSACTION_SPREADSHEET_ID",
    "1FQhLeS_6AV5WFyXHIbSOczihkLOxgQN4B4X1pe2y1Y8",
)
TRANSACTION_SHEET_NAME = os.getenv("TRANSACTION_SHEET_NAME", "Transaction Log")
TRANSACTION_HEADERS = [
    "Log Type",
    "Rank Seller",
    "Purchaser / Recipient",
    "Rank / Item / Service",
    "Credits Received",
    "Traded to FSA Founder?",
    "Proof / Notes",
    "Date & Time",
]

# Use the supplied unified workbook for every Google Sheets feature in this bot.
SPREADSHEET_ID = TRANSACTION_SPREADSHEET_ID


def ensure_transaction_layout(spreadsheet=None):
    spreadsheet = spreadsheet or get_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet(TRANSACTION_SHEET_NAME)
    except gspread.WorksheetNotFound as exc:
        raise RuntimeError(
            f'Could not find the "{TRANSACTION_SHEET_NAME}" tab in the configured Google Sheet.'
        ) from exc

    header_values = worksheet.get("A4:H4")
    current_headers = header_values[0] if header_values else []
    current_headers = list(current_headers) + [""] * (len(TRANSACTION_HEADERS) - len(current_headers))
    current_headers = current_headers[:len(TRANSACTION_HEADERS)]

    if not any(clean_text(value) for value in current_headers):
        worksheet.update(
            range_name="A4:H4",
            values=[TRANSACTION_HEADERS],
            value_input_option="USER_ENTERED",
        )
    elif current_headers != TRANSACTION_HEADERS:
        raise RuntimeError(
            "The Transaction Log headers do not match the bot. Expected: "
            + " | ".join(TRANSACTION_HEADERS)
        )

    # Make the summary formulas continue working after the original 200 template rows.
    try:
        summary = spreadsheet.worksheet("Summary")
        summary.update(
            range_name="B4:B8",
            values=[
                ["=COUNTIF('Transaction Log'!A5:A,\"<>\")"],
                ["=COUNTIF('Transaction Log'!A5:A,\"Sale\")"],
                ["=COUNTIF('Transaction Log'!A5:A,\"Donation\")"],
                ["=COUNTIF('Transaction Log'!A5:A,\"Trade\")"],
                ["=SUM('Transaction Log'!E5:E)"],
            ],
            value_input_option="USER_ENTERED",
        )
    except gspread.WorksheetNotFound:
        print('Transaction summary warning: the "Summary" tab was not found.')
    except Exception as exc:
        print(f"Transaction summary warning: {type(exc).__name__}: {exc}")

    return worksheet


def append_transaction_to_sheet(row: list[object]) -> int:
    spreadsheet = get_spreadsheet()
    worksheet = ensure_transaction_layout(spreadsheet)

    # The template header is in row 4. Column A identifies the next transaction row.
    first_column = worksheet.col_values(1)
    next_row = max(5, len(first_column) + 1)
    worksheet.update(
        range_name=f"A{next_row}:H{next_row}",
        values=[row],
        value_input_option="USER_ENTERED",
    )
    return next_row


class TransactionModal(discord.ui.Modal):
    def __init__(self, log_type: str, transferred: str):
        super().__init__(title=f"Log {log_type}")
        self.log_type = log_type
        self.transferred = transferred

        self.rank_seller = discord.ui.TextInput(
            label="Rank Seller Habbo Username",
            placeholder="Example: Dazamarin",
            required=True,
            max_length=80,
        )
        self.recipient = discord.ui.TextInput(
            label="Purchaser / Recipient",
            placeholder="Habbo username of the other person",
            required=True,
            max_length=80,
        )
        self.item_service = discord.ui.TextInput(
            label="Rank / Item / Service",
            placeholder="What was sold, donated, or traded?",
            required=True,
            max_length=150,
        )
        self.credits = discord.ui.TextInput(
            label="Credits Received",
            placeholder="Examples: 50c, 100c, 1 GB",
            required=True,
            max_length=60,
        )
        self.proof_notes = discord.ui.TextInput(
            label="Proof / Notes",
            placeholder="Paste a proof link and/or add notes",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
        )

        self.add_item(self.rank_seller)
        self.add_item(self.recipient)
        self.add_item(self.item_service)
        self.add_item(self.credits)
        self.add_item(self.proof_notes)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            rank_seller = clean_text(self.rank_seller.value)
            recipient = clean_text(self.recipient.value)
            item_service = clean_text(self.item_service.value)
            credits_text = clean_text(self.credits.value)
            proof_notes = clean_text(self.proof_notes.value) or "N/A"
            credits_value = amount_to_credits(credits_text)

            if credits_value is None or credits_value < 0:
                raise ValueError(
                    "Credits Received must contain a valid number, such as 50c, 100c, or 1 GB."
                )

            now = datetime.now(ZoneInfo(TIMEZONE))
            date_time = now.strftime("%m/%d/%Y %I:%M %p")
            row = [
                self.log_type,
                rank_seller,
                recipient,
                item_service,
                credits_value,
                self.transferred,
                proof_notes,
                date_time,
            ]
            sheet_row = await asyncio.to_thread(append_transaction_to_sheet, row)

            color_by_type = {
                "Sale": discord.Color.green(),
                "Donation": discord.Color.purple(),
                "Trade": discord.Color.gold(),
            }
            embed = discord.Embed(
                title=f"{self.log_type} Logged",
                color=color_by_type.get(self.log_type, discord.Color.blurple()),
                timestamp=now,
            )
            embed.add_field(name="Submitted By", value=interaction.user.mention, inline=True)
            embed.add_field(name="Rank Seller", value=rank_seller, inline=True)
            embed.add_field(name="Purchaser / Recipient", value=recipient, inline=True)
            embed.add_field(name="Rank / Item / Service", value=item_service, inline=False)
            embed.add_field(name="Credits Received", value=credits_text, inline=True)
            embed.add_field(name="Traded to FSA Founder?", value=self.transferred, inline=True)
            embed.add_field(name="Proof / Notes", value=proof_notes, inline=False)
            embed.set_footer(text=f"Saved to Transaction Log row {sheet_row}")

            log_channel = await get_rank_sales_channel(interaction.guild)
            if log_channel is None:
                raise RuntimeError(
                    "RANK_SALES_CHANNEL_ID is missing, invalid, or the bot cannot access the sale-log channel."
                )
            await log_channel.send(embed=embed)
            await interaction.followup.send(
                f"{self.log_type} logged successfully in Google Sheets and the sale-log channel.",
                ephemeral=True,
            )
        except Exception as exc:
            print(f"Transaction logging error: {type(exc).__name__}: {exc}")
            await interaction.followup.send(
                f"Could not log the transaction: {type(exc).__name__}: {exc}",
                ephemeral=True,
            )


async def can_log_transaction(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        await interaction.response.send_message("Use this command in a server.", ephemeral=True)
        return False
    if not await member_can_log_sales(interaction):
        await interaction.response.send_message(
            "You do not have permission to log transactions.",
            ephemeral=True,
        )
        return False
    if not GOOGLE_CREDENTIALS_JSON:
        await interaction.response.send_message(
            "Google Sheets is not configured. GOOGLE_CREDENTIALS_JSON is missing in Railway.",
            ephemeral=True,
        )
        return False
    return True


transaction_group = app_commands.Group(
    name="transaction",
    description="Log FSA sales, donations, and trades.",
)


@transaction_group.command(name="log", description="Open the unified transaction logging form.")
@app_commands.describe(
    log_type="Choose whether this is a sale, donation, or trade",
    transferred="Was it traded to the FSA Founder?",
)
@app_commands.choices(
    log_type=[
        app_commands.Choice(name="Sale", value="Sale"),
        app_commands.Choice(name="Donation", value="Donation"),
        app_commands.Choice(name="Trade", value="Trade"),
    ],
    transferred=[
        app_commands.Choice(name="Yes", value="Yes"),
        app_commands.Choice(name="No", value="No"),
        app_commands.Choice(name="N/A", value="N/A"),
    ],
)
async def transaction_log(
    interaction: discord.Interaction,
    log_type: app_commands.Choice[str],
    transferred: app_commands.Choice[str],
) -> None:
    if not await can_log_transaction(interaction):
        return
    await interaction.response.send_modal(TransactionModal(log_type.value, transferred.value))


@transaction_group.command(name="check-sheet", description="Check the transaction spreadsheet connection.")
@app_commands.checks.has_permissions(administrator=True)
async def transaction_check_sheet(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        spreadsheet = await asyncio.to_thread(get_spreadsheet)
        worksheet = await asyncio.to_thread(ensure_transaction_layout, spreadsheet)
        await interaction.followup.send(
            f'Connected successfully to "{spreadsheet.title}" → "{worksheet.title}".',
            ephemeral=True,
        )
    except Exception as exc:
        await interaction.followup.send(
            f"Spreadsheet connection failed: {type(exc).__name__}: {exc}",
            ephemeral=True,
        )


sale_transaction_group = app_commands.Group(name="sale", description="FSA sale tools.")


@sale_transaction_group.command(name="log", description="Open the sale logging form.")
@app_commands.describe(transferred="Was it traded to the FSA Founder?")
@app_commands.choices(
    transferred=[
        app_commands.Choice(name="Yes", value="Yes"),
        app_commands.Choice(name="No", value="No"),
        app_commands.Choice(name="N/A", value="N/A"),
    ]
)
async def transaction_sale_log(
    interaction: discord.Interaction,
    transferred: app_commands.Choice[str],
) -> None:
    if not await can_log_transaction(interaction):
        return
    await interaction.response.send_modal(TransactionModal("Sale", transferred.value))


# Delay command replacement until bot.run(), after legacy_main has injected its
# donation and trade commands. This guarantees only the unified log system is synced.
_original_transaction_bot_run = bot.run


def _run_with_unified_transactions(*args, **kwargs):
    for command_name in (
        "sale",
        "setup-rank-sales-sheet",
        "donate",
        "setup-donations-sheet",
        "trade",
        "transaction",
    ):
        bot.tree.remove_command(command_name)

    bot.tree.add_command(transaction_group)
    bot.tree.add_command(sale_transaction_group)
    return _original_transaction_bot_run(*args, **kwargs)


bot.run = _run_with_unified_transactions
# ---- End unified transaction commands ----
'''
