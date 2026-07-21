"""Railway entrypoint for verified, single-message pay announcements.

Apply pay source patches before anything imports pay_commands, then load every
existing runtime patch and start the bot normally.
"""

import pay_ping_reliability_patch  # noqa: F401
import pay_announcement_guard_patch  # noqa: F401
import runtime_patch  # noqa: F401
import rank_sales_totals_patch  # noqa: F401
import pending_balance_patch  # noqa: F401
import trade_pay_request_patch  # noqa: F401
import main  # noqa: F401,E402
