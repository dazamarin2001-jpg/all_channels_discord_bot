"""Compatibility Railway entrypoint.

Apply the existing runtime patches, then use main.py so generated LOA, pay,
donation, cleanup, trade, pending-balance, and reliable pay-ping commands are
injected before the bot starts.
"""

import runtime_patch  # noqa: F401
import rank_sales_totals_patch  # noqa: F401
import pending_balance_patch  # noqa: F401
import trade_pay_request_patch  # noqa: F401
import pay_ping_reliability_patch  # noqa: F401
import pay_announcement_guard_patch  # noqa: F401
import main  # noqa: F401,E402
