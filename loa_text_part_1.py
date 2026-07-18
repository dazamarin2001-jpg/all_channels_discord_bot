PART = r'''

# ---- LOA tracking commands ----
from datetime import timedelta as _loa_timedelta

LOA_TRACKING_CHANNEL_ID = os.getenv("LOA_TRACKING_CHANNEL_ID") or os.getenv("LOA_CHANNEL_ID")
LOA_SHEET_NAME = os.getenv("LOA_SHEET_NAME", "LOA Records")
LOA_REMINDER_DAYS_RAW = os.getenv("LOA_REMINDER_DAYS", "2")
try:
    LOA_REMINDER_DAYS = max(0, int(LOA_REMINDER_DAYS_RAW))
except ValueError:
    LOA_REMINDER_DAYS = 2

LOA_STAFF_ROLE_NAMES = {
    role_name.strip().casefold()
    for role_name in os.getenv(
        "LOA_STAFF_ROLE_NAMES",
        "Founder,Foundation Advisor,Supreme Command,Elite Command,Administrator,Moderator,Chat Moderator,Portal Admin,Badge Admin",
    ).split(",")
    if role_name.strip()
}

LOA_HEADERS = [
    "Record ID",
    "Guild ID",
    "Discord Member ID",
    "Discord Username",
    "Habbo Username",
    "Start Date",
    "End Date",
    "Duration Days",
    "Reason",
    "Portal Notes",
    "Status",
    "Recorded By",
    "Recorded By ID",
    "Role Confirmed",
    "Role Confirmed By",
    "Role Confirmed At",
    "Nickname Confirmed",
    "Nickname Confirmed By",
    "Nickname Confirmed At",
    "Badge Confirmed",
    "Badge Confirmed By",
    "Badge Confirmed At",
    "Reminder Status",
    "Reminder Sent At",
    "Actual Return Date",
    "Completed By",
    "Completed By ID",
    "Role Removed",
    "Role Removed By",
    "Role Removed At",
    "Nickname Removed",
    "Nickname Removed By",
    "Nickname Removed At",
    "Badge Removed",
    "Badge Removed By",
    "Badge Removed At",
    "Tracking Channel ID",
    "Tracking Message ID",
    "Previous End Date",
    "Extension Notes",
    "Last Updated",
    "Overdue Alert Sent",
]

LOA_OPEN_STATUSES = {"Active", "Extended", "Overdue", "Return Pending"}


def _loa_now():
    return datetime.now(ZoneInfo(TIMEZONE))


def _loa_now_text() -> str:
    return _loa_now().strftime("%Y-%m-%d %I:%M %p %Z")


def _loa_today_text() -> str:
    return _loa_now().date().isoformat()


def _loa_parse_date(value: object):
    text = clean_text(value)
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Dates must use YYYY-MM-DD, for example 2026-08-03.") from exc


def _loa_display_date(value: object) -> str:
    text = clean_text(value)
    if not text:
        return "N/A"
    try:
        return _loa_parse_date(text).strftime("%B %d, %Y").replace(" 0", " ")
    except ValueError:
        return text


def _loa_protect(value: object) -> str:
    text = clean_text(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def _loa_column_letter(number: int) -> str:
    letters = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def get_loa_worksheet(spreadsheet=None):
    spreadsheet = spreadsheet or get_spreadsheet()
    sheet = get_or_create_worksheet(spreadsheet, LOA_SHEET_NAME, LOA_HEADERS)
    values = sheet.get_all_values()
    if not values:
        sheet.update(range_name="A1", values=[LOA_HEADERS], value_input_option="USER_ENTERED")
    elif values[0][: len(LOA_HEADERS)] != LOA_HEADERS:
        sheet.update(range_name="A1", values=[LOA_HEADERS], value_input_option="USER_ENTERED")
    return sheet


'''
