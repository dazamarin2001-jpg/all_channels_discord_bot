from pathlib import Path

p = Path("bot.py")
s = p.read_text(encoding="utf-8")

needle = "    q = question.casefold()\n"
insert = "    q = question.casefold()\n    if q.strip() in ('who are you', 'what are you'):\n        return \"I'm **MADBOT**, your helpful FSA Discord bot. I can help with pay timings, FSA staff/info, events team questions, rank-sale logs, and general agency questions.\"\n"

if needle in s and "I'm **MADBOT**, your helpful FSA Discord bot" not in s:
    s = s.replace(needle, insert, 1)

p.write_text(s, encoding="utf-8")
print("Identity answer patch applied.")
