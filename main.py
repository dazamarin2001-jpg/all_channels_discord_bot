"""Railway entrypoint for the Discord bot.

Keep startup simple: import bot.py and let it register commands and run the bot.
Do not rewrite bot.py at runtime; runtime patching caused RankSaleModal fields
to get removed while on_submit still referenced them.
"""

import bot
