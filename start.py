"""Compatibility Railway entrypoint.

Apply the existing runtime patches, then use main.py so generated LOA, pay,
donation, cleanup, and trade commands are injected before the bot starts.
"""

import runtime_patch  # noqa: F401
import rank_sales_totals_patch  # noqa: F401
import main  # noqa: F401,E402
