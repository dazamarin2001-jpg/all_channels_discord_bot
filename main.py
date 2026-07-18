"""Railway entrypoint that adds generated commands before loading existing commands."""

from pathlib import Path

from loa_commands import LOA_BLOCK, LOA_END_MARKER, LOA_START_MARKER
from pay_commands import PAY_BLOCK, PAY_END_MARKER, PAY_START_MARKER


def remove_marked_block(text: str, start_marker: str, end_marker: str) -> str:
    while start_marker in text:
        start = text.find(start_marker)
        block_start = text.rfind("\n", 0, start)
        if block_start == -1:
            block_start = start
        end = text.find(end_marker, start)
        if end == -1:
            run_marker = "bot.run(TOKEN)"
            run_pos = text.find(run_marker, start)
            if run_pos == -1:
                return text[:block_start].rstrip() + "\n"
            text = text[:block_start].rstrip() + "\n\n" + text[run_pos:]
            continue
        line_end = text.find("\n", end + len(end_marker))
        if line_end == -1:
            line_end = len(text)
        text = text[:block_start].rstrip() + "\n" + text[line_end:].lstrip("\n")
    return text


bot_path = Path("bot.py")
if bot_path.exists():
    bot_text = bot_path.read_text(encoding="utf-8")
    bot_text = remove_marked_block(bot_text, LOA_START_MARKER, LOA_END_MARKER)
    bot_text = remove_marked_block(bot_text, PAY_START_MARKER, PAY_END_MARKER)
    run_marker = "\n\nbot.run(TOKEN)"
    if run_marker in bot_text:
        generated_blocks = LOA_BLOCK.strip() + "\n\n" + PAY_BLOCK.strip()
        bot_text = bot_text.replace(run_marker, "\n\n" + generated_blocks + run_marker, 1)
        bot_path.write_text(bot_text, encoding="utf-8")
        print("LOA tracking and pay announcement commands injected into bot.py.")
    else:
        print("Generated command injector warning: could not find bot.run(TOKEN) marker.")

# Preserve and run every existing donation, cleanup, and trade startup injection.
import legacy_main  # noqa: E402,F401
