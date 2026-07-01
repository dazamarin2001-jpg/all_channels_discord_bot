from pathlib import Path

p = Path("bot.py")
s = p.read_text(encoding="utf-8")


def rep(old: str, new: str) -> None:
    global s
    if old in s:
        s = s.replace(old, new)

# Imports and environment for AI mention replies.
rep(
    "import json\nimport os\nfrom datetime import datetime",
    "import json\nimport os\nimport re\nimport time\nimport urllib.request\nfrom datetime import datetime",
)
rep(
    "from google.oauth2.service_account import Credentials\n",
    "from google.oauth2.service_account import Credentials\n\ntry:\n    from openai import OpenAI\nexcept Exception:\n    OpenAI = None\n",
)
rep(
    'TIMEZONE = os.getenv("TIMEZONE", "America/Chicago")\n',
    'TIMEZONE = os.getenv("TIMEZONE", "America/Chicago")\n'
    'OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")\n'
    'AI_MODEL = os.getenv("AI_MODEL", "gpt-5.5")\n'
    'AI_WEBSITE_URLS_RAW = os.getenv("AI_WEBSITE_URLS") or os.getenv("WEBSITE_URL") or os.getenv("HELP_WEBSITE_URL") or "https://fsa-habbo.com/"\n'
    'AI_WEBSITE_URLS = [url.strip() for url in AI_WEBSITE_URLS_RAW.split(",") if url.strip()]\n'
    'AI_SITE_CACHE_SECONDS = int(os.getenv("AI_SITE_CACHE_SECONDS", "600"))\n',
)
rep(
    'intents.members = True\nbot = commands.Bot(command_prefix="!", intents=intents)',
    'intents.members = True\nintents.message_content = True\nbot = commands.Bot(command_prefix="!", intents=intents)',
)

# Rank Sales sheet fixes.
rep(
    'RANK_SALES_HEADERS = [\n    "Timestamp",\n    "Discord Seller",\n    "Seller Habbo",\n    "Buyer",\n    "Rank Sold",\n    "Amount",\n    "Proof / Notes",\n]',
    'RANK_SALES_HEADERS = [\n    "Discord Username",\n    "Habbo Username",\n    "Buyer",\n    "Rank Sold",\n    "Amount",\n    "Proof / Notes",\n    "Timestamp",\n]',
)
rep('''    seller_habbo = discord.ui.TextInput(
        label="Seller Habbo Username",
        placeholder="Example: Dazamarin",
        required=True,
        max_length=80,
    )
''', '')
rep('            seller_habbo = str(self.seller_habbo.value).strip()', '            seller_habbo = interaction.user.display_name')
rep(
    '''            row = [
                timestamp,
                str(interaction.user),
                seller_habbo,
                buyer,
                rank,
                amount,
                proof,
            ]''',
    '''            row = [
                str(interaction.user),
                seller_habbo,
                buyer,
                rank,
                amount,
                proof,
                timestamp,
            ]''',
)
rep('embed.add_field(name="Discord Seller", value=interaction.user.mention, inline=True)', 'embed.add_field(name="Discord Username", value=interaction.user.mention, inline=True)')
rep('embed.add_field(name="Seller Habbo", value=seller_habbo, inline=True)', 'embed.add_field(name="Habbo Username", value=seller_habbo, inline=True)')
rep(
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
rep('worksheet.format("G:G", {"wrapStrategy": "WRAP", "horizontalAlignment": "LEFT"})', 'worksheet.format("F:F", {"wrapStrategy": "WRAP", "horizontalAlignment": "LEFT"})')
rep(
    '            worksheet.columns_auto_resize(0, 7)',
    '            worksheet.spreadsheet.batch_update({"requests":[{"updateDimensionProperties":{"range":{"sheetId":worksheet.id,"dimension":"COLUMNS","startIndex":i,"endIndex":i+1},"properties":{"pixelSize":w},"fields":"pixelSize"}} for i,w in enumerate([190,180,150,170,110,350,180])]})',
)
rep('                        "startIndex": 6,\n                        "endIndex": 7,', '                        "startIndex": 5,\n                        "endIndex": 6,')
rep('    worksheet.append_row(row, value_input_option="USER_ENTERED")\n    apply_rank_sales_sheet_style(worksheet)', '    worksheet.append_row(row, value_input_option="USER_ENTERED")')
rep(
    '\n@bot.tree.command(name="setup-rank-sales-sheet", description="Clean and style the rank sales Google Sheet.")\n@app_commands.checks.has_permissions(administrator=True)\nasync def setup_rank_sales_sheet(interaction: discord.Interaction) -> None:\n    await interaction.response.defer(ephemeral=True, thinking=True)',
    '\n@bot.tree.command(name="setup-rank-sales-sheet", description="Clean and style the rank sales Google Sheet.")\nasync def setup_rank_sales_sheet(interaction: discord.Interaction) -> None:\n    if not any(getattr(r, "name", "") == "Chat Moderator" for r in getattr(interaction.user, "roles", [])):\n        await interaction.response.send_message("Only Chat Moderator can use this command.", ephemeral=True)\n        return\n    await interaction.response.defer(ephemeral=True, thinking=True)',
)
rep('Rank Sales sheet cleaned and styled. Columns are now: Timestamp, Discord Seller, Seller Habbo, Buyer, Rank Sold, Amount, Proof / Notes.', 'Rank Sales sheet cleaned and styled. Columns are now: Discord Username, Habbo Username, Buyer, Rank Sold, Amount, Proof / Notes, Timestamp.')

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
    parts = []
    for url in AI_WEBSITE_URLS[:5]:
        try:
            parts.append(fetch_one_website(url))
        except Exception:
            pass
    parts.append("FSA known info: Pay timings are 1:00 AM, 4:00 AM, 7:00 AM, 1:00 PM, 4:00 PM, and 7:00 PM GMT.")
    parts.append("FSA known info: The Foundation Team members are Eskimo, BeccaMneme, missbluegerlx2, and srafin.")
    parts.append("FSA Events Team: The Events Team is responsible for entertainment in the Federal Habbo Agency. They plan and host games to keep the community active and engaged. The Events Team has two branches: Hosts and Planners. Hosts are responsible for hosting games in FSA; some games are hosted in base and others in external rooms related to FSA. Planners create ideas for activities and events such as celebratory events, competitions, and more. Planners may build event rooms if they choose, but it is not required. Events Leadership Team: Events Overseer is vacant, Events Director iC is vacant, Hosting Assistant 2iC is vacant, and Planning Assistant 2iC is vacant.")
    return "\n\n---\n\n".join(parts)[:50000]


def build_ai_answer(question: str, author_name: str, guild_name: str) -> str:
    q = question.casefold()
    if "pay" in q and any(word in q for word in ("time", "timing", "timings", "schedule", "when")):
        return "Pay timings are **1:00 AM, 4:00 AM, 7:00 AM, 1:00 PM, 4:00 PM, and 7:00 PM GMT**."
    if "foundation" in q and any(word in q for word in ("team", "member", "members", "who", "list")):
        return "The Foundation Team members are **Eskimo**, **BeccaMneme**, **missbluegerlx2**, and **srafin**."
    if "events" in q and any(word in q for word in ("team", "branch", "branches", "host", "planner", "leadership", "overseer", "director", "assistant")):
        return "The **Events Team** is responsible for entertainment in FSA. They plan and host games to keep the community active and engaged.\n\n**Branches:**\n• **Hosts** — host games in FSA. Some games are hosted in base, while others can be hosted in external FSA-related rooms.\n• **Planners** — create ideas for activities and events, including celebratory events, competitions, and more. They may build event rooms if they choose, but it is not required.\n\n**Events Leadership Team:**\n• Events Overseer — **VACANT**\n• Events Director iC — **VACANT**\n• Hosting Assistant 2iC — **VACANT**\n• Planning Assistant 2iC — **VACANT**"
    if AI_CLIENT is None:
        return "AI is not set up yet. Add OPENAI_API_KEY in Railway Variables, then redeploy me."

    context = get_ai_website_context()
    instructions = (
        "You are MADBOT, a helpful Discord bot for a Habbo agency server. "
        "Use the FSA context first when it answers the question. "
        "If the context does not answer it, answer normally. "
        "Never include source links or a Source line. Keep answers clear and Discord-friendly."
    )
    user_input = f"Discord server: {guild_name}\nQuestion from: {author_name}\n\nFSA context:\n{context or 'None'}\n\nUser question:\n{question}"
    response = AI_CLIENT.responses.create(model=AI_MODEL, instructions=instructions, input=user_input)
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
        await message.reply("Ask me a question after mentioning me. Example: `@MADBOT who is in the Events Team?`", mention_author=False)
        return
    try:
        async with message.channel.typing():
            answer = await asyncio.to_thread(build_ai_answer, question, getattr(message.author, "display_name", str(message.author)), message.guild.name if message.guild else "Direct Message")
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
