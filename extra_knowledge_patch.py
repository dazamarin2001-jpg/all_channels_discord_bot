from pathlib import Path

p = Path("bot.py")
s = p.read_text(encoding="utf-8")

needle = "    q = question.casefold()\n"
insert = '''    q = question.casefold()\n    if "foundation" in q and any(word in q for word in ("team", "member", "members", "who", "list")):\n        return "The Foundation Team members are **Eskimo**, **BeccaMneme**, **missbluegerlx2**, and **srafin**."\n'''

if needle in s and "The Foundation Team members are" not in s:
    s = s.replace(needle, insert, 1)

p.write_text(s, encoding="utf-8")
print("Extra knowledge patch applied.")
