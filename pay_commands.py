"""Generated FSA pay reminder and pay-start announcement block."""

PAY_START_MARKER = "# ---- Pay announcement commands ----"
PAY_END_MARKER = "# ---- End pay announcement commands ----"

PAY_BLOCK = r"""
# ---- Pay announcement commands ----
PAY_REMINDER_CHANNEL_ID = os.getenv("PAY_REMINDER_CHANNEL_ID")
PAY_ALERT_ROLE_ID = os.getenv("PAY_ALERT_ROLE_ID")
PAY_ALERT_ROLE_NAME = os.getenv("PAY_ALERT_ROLE_NAME", "Pay Alert")
FSA_PAY_HOURS_GMT = (1, 4, 7, 13, 16, 19)
FSA_SENT_PAY_EVENTS: set[str] = set()
PAY_ANNOUNCEMENT_HISTORY_LIMIT = 50


def format_pay_clock(value: datetime) -> str:
    hour = value.strftime("%I").lstrip("0") or "12"
    return f"{hour}:{value.strftime('%M %p')}"


def format_pay_zone(pay_time_utc: datetime, timezone_name: str) -> str:
    local_time = pay_time_utc.astimezone(ZoneInfo(timezone_name))
    return f"`{format_pay_clock(local_time)}`"


def get_pay_event_key(pay_time_utc: datetime, event_type: str) -> str:
    return f"{pay_time_utc.strftime('%Y-%m-%d-%H')}-{event_type}"


def get_pay_event_title(event_type: str) -> str:
    return "⏰ FSA PAY REMINDER" if event_type == "reminder" else "💰 PAY IS STARTING NOW!"


async def get_pay_announcement_channel(guild: discord.Guild | None):
    if guild is None:
        return None

    if PAY_REMINDER_CHANNEL_ID:
        try:
            channel_id = int(PAY_REMINDER_CHANNEL_ID)
            channel = guild.get_channel(channel_id) or bot.get_channel(channel_id)
            if channel is None:
                channel = await bot.fetch_channel(channel_id)
            if isinstance(channel, (discord.TextChannel, discord.Thread)):
                return channel
        except (TypeError, ValueError, discord.DiscordException):
            pass

    for channel in guild.text_channels:
        normalized = channel.name.casefold().replace("︱", "-").replace("|", "-")
        if "pay-announcements" in normalized or normalized == "pay-announcement":
            return channel
    return None


def get_pay_alert_role(guild: discord.Guild | None) -> discord.Role | None:
    if guild is None:
        return None

    if PAY_ALERT_ROLE_ID:
        try:
            role = guild.get_role(int(PAY_ALERT_ROLE_ID))
            if role is not None:
                return role
        except (TypeError, ValueError):
            pass

    wanted = PAY_ALERT_ROLE_NAME.casefold().strip()
    return discord.utils.find(lambda role: role.name.casefold().strip() == wanted, guild.roles)


def build_pay_announcement_embed(pay_time_utc: datetime, event_type: str) -> discord.Embed:
    unix_timestamp = int(pay_time_utc.timestamp())

    if event_type == "reminder":
        embed = discord.Embed(
            title=get_pay_event_title(event_type),
            description=(
                "Pay begins in **15 minutes**!\n\n"
                "Please begin making your way to **FSA Base** and prepare for pay.\n\n"
                "> Arrive on time, follow Pay Team instructions, and remain respectful throughout the process."
            ),
            color=discord.Color.gold(),
            timestamp=datetime.now(ZoneInfo("UTC")),
        )
        embed.set_footer(text="FSA Pay Team • Please arrive on time")
    else:
        embed = discord.Embed(
            title=get_pay_event_title(event_type),
            description=(
                "Pay has officially begun!\n\n"
                "Please report to **FSA Base** and follow all instructions provided by the **Pay Team**."
            ),
            color=discord.Color.green(),
            timestamp=datetime.now(ZoneInfo("UTC")),
        )
        embed.set_footer(text="Thank you for your hard work, activity, and dedication to FSA! 💙")

    embed.add_field(name="🌍 GMT", value=format_pay_zone(pay_time_utc, "UTC"), inline=True)
    embed.add_field(name="🇺🇸 Eastern", value=format_pay_zone(pay_time_utc, "America/New_York"), inline=True)
    embed.add_field(name="🇺🇸 Central", value=format_pay_zone(pay_time_utc, "America/Chicago"), inline=True)
    embed.add_field(name="🕒 Your Local Time", value=f"<t:{unix_timestamp}:F>", inline=False)

    if event_type == "reminder":
        embed.add_field(name="⏳ Countdown", value=f"<t:{unix_timestamp}:R>", inline=False)

    return embed


async def pay_event_already_posted(channel, event_type: str, pay_time_utc: datetime) -> bool:
    """Check Discord history so restarts or duplicate bot instances cannot repost an event."""
    expected_title = get_pay_event_title(event_type)
    expected_local_time = f"<t:{int(pay_time_utc.timestamp())}:F>"

    try:
        async for message in channel.history(limit=PAY_ANNOUNCEMENT_HISTORY_LIMIT):
            if bot.user is not None and message.author.id != bot.user.id:
                continue

            for existing_embed in message.embeds:
                if existing_embed.title != expected_title:
                    continue

                for field in existing_embed.fields:
                    if field.name == "🕒 Your Local Time" and expected_local_time in str(field.value):
                        return True
    except (discord.Forbidden, discord.HTTPException) as exc:
        print(
            "Pay duplicate-check warning: could not read announcement history: "
            f"{type(exc).__name__}: {exc}"
        )

    return False


def get_due_pay_event(now_utc: datetime) -> tuple[str, datetime] | None:
    normalized_now = now_utc.replace(second=0, microsecond=0)
    current_minutes = normalized_now.hour * 60 + normalized_now.minute

    for pay_hour in FSA_PAY_HOURS_GMT:
        pay_minutes = pay_hour * 60
        pay_time = normalized_now.replace(hour=pay_hour, minute=0)

        if current_minutes == pay_minutes - 15:
            return "reminder", pay_time

        if current_minutes == pay_minutes:
            return "starting", pay_time

    return None


async def send_pay_announcement(guild: discord.Guild, event_type: str, pay_time_utc: datetime) -> bool:
    channel = await get_pay_announcement_channel(guild)
    if channel is None:
        print(
            "Pay announcement warning: no pay announcement channel was found. "
            "Set PAY_REMINDER_CHANNEL_ID or create #pay-announcements."
        )
        return False

    event_key = get_pay_event_key(pay_time_utc, event_type)
    if await pay_event_already_posted(channel, event_type, pay_time_utc):
        print(f"Pay announcement skipped because {event_key} is already in {channel}.")
        return True

    role = get_pay_alert_role(guild)
    if role is None:
        print(
            f"Pay announcement warning: role '{PAY_ALERT_ROLE_NAME}' was not found. "
            "Set PAY_ALERT_ROLE_ID or create the role."
        )

    content = role.mention if role is not None else f"@{PAY_ALERT_ROLE_NAME}"
    embed = build_pay_announcement_embed(pay_time_utc, event_type)

    await channel.send(
        content=content,
        embed=embed,
        allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=True),
    )
    return True


@tasks.loop(seconds=20)
async def pay_announcement_loop() -> None:
    now_utc = datetime.now(ZoneInfo("UTC"))
    due_event = get_due_pay_event(now_utc)
    if due_event is None:
        return

    event_type, pay_time_utc = due_event
    event_key = get_pay_event_key(pay_time_utc, event_type)
    if event_key in FSA_SENT_PAY_EVENTS:
        return

    sent_to_any_guild = False
    for guild in bot.guilds:
        try:
            sent = await send_pay_announcement(guild, event_type, pay_time_utc)
            sent_to_any_guild = sent_to_any_guild or sent
        except Exception as exc:
            print(f"Pay announcement error in {guild.name}: {type(exc).__name__}: {exc}")

    if sent_to_any_guild:
        FSA_SENT_PAY_EVENTS.add(event_key)

    if len(FSA_SENT_PAY_EVENTS) > 200:
        current_day = now_utc.strftime("%Y-%m-%d")
        today_keys = {key for key in FSA_SENT_PAY_EVENTS if key.startswith(current_day)}
        FSA_SENT_PAY_EVENTS.intersection_update(today_keys)


@bot.listen("on_ready")
async def start_pay_announcement_loop() -> None:
    if not pay_announcement_loop.is_running():
        pay_announcement_loop.start()
        print(
            "Pay announcement loop started with duplicate protection for 15-minute reminders "
            f"and pay-start alerts. Alert role: {PAY_ALERT_ROLE_NAME}"
        )
# ---- End pay announcement commands ----
"""
