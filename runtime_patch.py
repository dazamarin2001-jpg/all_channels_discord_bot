from pathlib import Path

p = Path("bot.py")
s = p.read_text(encoding="utf-8")

# Extra imports for AI mention replies and website reading.
s = s.replace(
    "import json\nimport os\nfrom datetime import datetime",
    "import json\nimport os\nimport re\nimport time\nimport urllib.request\nfrom datetime import datetime",
)
s = s.replace(
    "from google.oauth2.service_account import Credentials\n",
    "from google.oauth2.service_account import Credentials\n\ntry:\n    from openai import OpenAI\nexcept Exception:\n    OpenAI = None\n",
)

# Environment variables.
s = s.replace(
    'TIMEZONE = os.getenv("TIMEZONE", "America/Chicago")\n',
    'TIMEZONE = os.getenv("TIMEZONE", "America/Chicago")\n'
    'OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")\n'
    'AI_MODEL = os.getenv("AI_MODEL", "gpt-5.5")\n'
    'AI_WEBSITE_URLS_RAW = os.getenv("AI_WEBSITE_URLS") or os.getenv("WEBSITE_URL") or os.getenv("HELP_WEBSITE_URL") or ""\n'
    'AI_WEBSITE_URLS = [url.strip() for url in AI_WEBSITE_URLS_RAW.split(",") if url.strip()]\n'
    'AI_SITE_CACHE_SECONDS = int(os.getenv("AI_SITE_CACHE_SECONDS", "600"))\n',
)

# Message content intent for mention replies.
s = s.replace(
    "intents.members = True\nbot = commands.Bot(command_prefix=\"!\", intents=intents)",
    "intents.members = True\nintents.message_content = True\nbot = commands.Bot(command_prefix=\"!\", intents=intents)",
)

# Rank Sales sheet layout improvements.
s = s.replace(
    'RANK_SALES_HEADERS = [\n    "Timestamp",\n    "Discord Seller",\n    "Seller Habbo",\n    "Buyer",\n    "Rank Sold",\n    "Amount",\n    "Proof / Notes",\n]',
    'RANK_SALES_HEADERS = [\n    "Discord Username",\n    "Habbo Username",\n    "Buyer",\n    "Rank Sold",\n    "Amount",\n    "Proof / Notes",\n    "Timestamp",\n]',
)

seller_block = '''    seller_habbo = discord.ui.TextInput(
        label="Seller Habbo Username",
        placeholder="Example: Dazamarin",
        required=True,
        max_length=80,
    )
'''
s = s.replace(seller_block, "")
s = s.replace(
    "            seller_habbo = str(self.seller_habbo.value).strip()",
    "            seller_habbo = interaction.user.display_name",
)
s = s.replace(
    '            row = [\n                timestamp,\n                str(interaction.user),\n                seller_habbo,\n                buyer,\n                rank,\n                amount,\n                proof,\n            ]',
    '            row = [\n                str(interaction.user),\n                seller_habbo,\n                buyer,\n                rank,\n                amount,\n                proof,\n                timestamp,\n            ]',
)
s = s.replace('embed.add_field(name="Discord Seller", value=interaction.user.mention, inline=True)', 'embed.add_field(name="Discord Username", value=interaction.user.mention, inline=True)')
s = s.replace('embed.add_field(name="Seller Habbo", value=seller_habbo, inline=True)', 'embed.add_field(name="Habbo Username", value=seller_habbo, inline=True)')

s = s.replace(
    '''        if has_old_private_columns:
            cleaned.append([
                padded[0],  # Timestamp
                padded[1],  # Discord Seller
                padded[3],  # Seller Habbo
                padded[4],  # Buyer
                padded[5],  # Rank Sold
                padded[6],  # Amount
                padded[7],  # Proof / Notes
            ])
        else:
            cleaned.append(padded[:len(RANK_SALES_HEADERS)])''',
    '''        if has_old_private_columns:
            cleaned.append([padded[1], padded[3], padded[4], padded[5], padded[6], padded[7], padded[0]])
        else:
            if old_header and old_header[0] == "timestamp":
                cleaned.append([padded[1], padded[2], padded[3], padded[4], padded[5], padded[6], padded[0]])
            else:
                cleaned.append(padded[:len(RANK_SALES_HEADERS)])''',
)

s = s.replace('worksheet.format("G:G", {"wrapStrategy": "WRAP", "horizontalAlignment": "LEFT"})', 'worksheet.format("F:F", {"wrapStrategy": "WRAP", "horizontalAlignment": "LEFT"})')
s = s.replace(
    '            worksheet.columns_auto_resize(0, 7)',
    '            worksheet.spreadsheet.batch_update({"requests":[{"updateDimensionProperties":{"range":{"sheetId":worksheet.id,"dimension":"COLUMNS","startIndex":i,"endIndex":i+1},"properties":{"pixelSize":w},"fields":"pixelSize"}} for i,w in enumerate([190,180,150,170,110,350,180])]})',
)
s = s.replace('                        "startIndex": 6,\n                        "endIndex": 7,', '                        "startIndex": 5,\n                        "endIndex": 6,')
s = s.replace(
    '    worksheet.append_row(row, value_input_option="USER_ENTERED")\n    apply_rank_sales_sheet_style(worksheet)',
    '    worksheet.append_row(row, value_input_option="USER_ENTERED")',
)

# Allow only Chat Moderator to restyle the sheet.
s = s.replace(
    '\n@bot.tree.command(name="setup-rank-sales-sheet", description="Clean and style the rank sales Google Sheet.")\n@app_commands.checks.has_permissions(administrator=True)\nasync def setup_rank_sales_sheet(interaction: discord.Interaction) -> None:\n    await interaction.response.defer(ephemeral=True, thinking=True)',
    '\n@bot.tree.command(name="setup-rank-sales-sheet", description="Clean and style the rank sales Google Sheet.")\nasync def setup_rank_sales_sheet(interaction: discord.Interaction) -> None:\n    if not any(getattr(r, "name", "") == "Chat Moderator" for r in getattr(interaction.user, "roles", [])):\n        await interaction.response.send_message("Only Chat Moderator can use this command.", ephemeral=True)\n        return\n    await interaction.response.defer(ephemeral=True, thinking=True)',
)
s = s.replace(
    'Rank Sales sheet cleaned and styled. Columns are now: Timestamp, Discord Seller, Seller Habbo, Buyer, Rank Sold, Amount, Proof / Notes.',
    'Rank Sales sheet cleaned and styled. Columns are now: Discord Username, Habbo Username, Buyer, Rank Sold, Amount, Proof / Notes, Timestamp.',
)

# AI mention replies. Users can type: @BotName question
ai_code = r'''

AI_SITE_CACHE = {"expires": 0.0, "text": ""}
AI_CLIENT = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY and OpenAI is not None else None


def clean_website_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\\1>", " ", html)
    html = re.sub(r"(?is)<br\\s*/?>", "\n", html)
    html = re.sub(r"(?is)</p>|</div>|</li>|</h[1-6]>", "\n", html)
    text = re.sub(r"(?is)<[^>]+>", " ", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def fetch_one_website(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 MADBOT Discord helper"})
    with urllib.request.urlopen(request, timeout=10) as response:
        raw = response.read(700000)
    return clean_website_text(raw.decode("utf-8", errors="ignore"))[:12000]


def get_ai_website_context() -> str:
    if not AI_WEBSITE_URLS:
        return ""

    now = time.time()
    if AI_SITE_CACHE["text"] and AI_SITE_CACHE["expires"] > now:
        return AI_SITE_CACHE["text"]

    parts = []
    for url in AI_WEBSITE_URLS[:5]:
        try:
            parts.append(f"SOURCE: {url}\n{fetch_one_website(url)}")
        except Exception as exc:
            parts.append(f"SOURCE: {url}\nCould not read this page: {type(exc).__name__}")

    AI_SITE_CACHE["text"] = "\n\n---\n\n".join(parts)[:50000]
    AI_SITE_CACHE["expires"] = now + AI_SITE_CACHE_SECONDS
    return AI_SITE_CACHE["text"]


def build_ai_answer(question: str, author_name: str, guild_name: str) -> str:
    if AI_CLIENT is None:
        return "AI is not set up yet. Add OPENAI_API_KEY in Railway Variables, then redeploy me."

    website_context = get_ai_website_context()
    website_note = (
        "Use the website context first when it answers the question. Include a short Source line when website context was used. "
        "If the website context does not answer it, answer as a normal helpful assistant."
        if website_context else
        "No website context is configured, so answer as a normal helpful assistant."
    )

    instructions = (
        "You are MADBOT, a helpful Discord bot for a Habbo agency server. "
        "Answer clearly and keep replies Discord-friendly. "
        "For agency rules, ranks, procedures, and server info, prefer website context. "
        "For general questions, answer normally. "
        "Do not reveal secrets, tokens, private keys, or credentials. "
        "Do not help with malware, credential theft, cheating tools, bypassing bans, or harmful exploitation. "
        + website_note
    )

    user_input = (
        f"Discord server: {guild_name}\n"
        f"Question from: {author_name}\n\n"
        f"Website context:\n{website_context or 'None'}\n\n"
        f"User question:\n{question}"
    )

    response = AI_CLIENT.responses.create(
        model=AI_MODEL,
        instructions=instructions,
        input=user_input,
    )
    answer = getattr(response, "output_text", "") or "I could not generate an answer."
    return answer[:1900]


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return

    if bot.user is None or bot.user not in message.mentions:
        await bot.process_commands(message)
        return

    question = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
    if not question:
        await message.reply("Ask me a question after mentioning me. Example: `@MADBOT how do I log a rank sale?`", mention_author=False)
        return

    try:
        async with message.channel.typing():
            answer = await asyncio.to_thread(
                build_ai_answer,
                question,
                getattr(message.author, "display_name", str(message.author)),
                message.guild.name if message.guild else "Direct Message",
            )
        await message.reply(answer, mention_author=False)
    except Exception as exc:
        print(f"AI reply error: {type(exc).__name__}: {exc}")
        await message.reply(f"AI error: {type(exc).__name__}: {exc}", mention_author=False)

    await bot.process_commands(message)
'''

if "AI_SITE_CACHE =" not in s:
    s = s.replace("\n\nbot.run(TOKEN)", ai_code + "\n\nbot.run(TOKEN)")

p.write_text(s, encoding="utf-8")
print("Runtime patch applied.")
