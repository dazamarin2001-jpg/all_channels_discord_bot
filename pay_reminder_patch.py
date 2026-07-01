from pathlib import Path

p = Path("bot.py")
s = p.read_text(encoding="utf-8")

s = s.replace(
    'AI_SITE_CACHE_SECONDS = int(os.getenv("AI_SITE_CACHE_SECONDS", "600"))\n',
    'AI_SITE_CACHE_SECONDS = int(os.getenv("AI_SITE_CACHE_SECONDS", "600"))\nPAY_REMINDER_CHANNEL_ID = os.getenv("PAY_REMINDER_CHANNEL_ID")\n',
)

code = r'''

SENT_PAY_REMINDERS = set()


def pay_reminder_due(now_utc: datetime):
    if now_utc.minute != 30:
        return None
    now_utc = now_utc.replace(second=0, microsecond=0)
    for hour in PAY_HOURS_GMT:
        if now_utc.hour == hour - 1:
            return now_utc.replace(hour=hour, minute=0)
    return None


@tasks.loop(minutes=1)
async def pay_reminder_loop() -> None:
    if not PAY_REMINDER_CHANNEL_ID:
        return
    now_utc = datetime.now(ZoneInfo("UTC"))
    pay_time = pay_reminder_due(now_utc)
    if pay_time is None:
        return
    key = pay_time.strftime("%Y-%m-%d-%H")
    if key in SENT_PAY_REMINDERS:
        return
    SENT_PAY_REMINDERS.add(key)
    channel = bot.get_channel(int(PAY_REMINDER_CHANNEL_ID)) or await bot.fetch_channel(int(PAY_REMINDER_CHANNEL_ID))
    eastern = pay_time.astimezone(ZoneInfo("America/New_York"))
    central = pay_time.astimezone(ZoneInfo("America/Chicago"))
    await channel.send(
        f"⏰ **Pay is in 30 minutes!**\n"
        f"Next pay: **{format_time(pay_time, 'GMT')}** "
        f"(**{format_time(eastern, 'Eastern')}** / **{format_time(central, 'Central')}**)."
    )


@bot.listen("on_ready")
async def start_pay_reminder_loop() -> None:
    if PAY_REMINDER_CHANNEL_ID and not pay_reminder_loop.is_running():
        pay_reminder_loop.start()
        print("Pay reminder loop started.")

'''

if "pay_reminder_loop" not in s:
    s = s.replace("\n\n@bot.event\nasync def on_message", code + "\n@bot.event\nasync def on_message")

p.write_text(s, encoding="utf-8")
print("Pay reminder patch applied.")
