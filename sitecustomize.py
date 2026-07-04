"""Small startup compatibility patch for the Discord bot runtime."""

try:
    import discord

    if not hasattr(discord, "DisordException"):
        discord.DisordException = discord.DiscordException
except Exception:
    pass
