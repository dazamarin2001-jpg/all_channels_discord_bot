"""Assemble the generated LOA and unified transaction command block."""

from loa_text_part_1 import PART as PART_1
from loa_text_part_2 import PART as PART_2
from loa_text_part_3 import PART as PART_3
from loa_text_part_4 import PART as PART_4
from loa_text_part_5 import PART as PART_5
from loa_text_part_6 import PART as PART_6
from loa_text_part_7 import PART as PART_7
from loa_text_part_8 import PART as PART_8
from transaction_commands import TRANSACTION_BLOCK

LOA_START_MARKER = "# ---- LOA tracking commands ----"
LOA_END_MARKER = "# ---- End LOA tracking commands ----"

_raw_loa_block = PART_1 + PART_2 + PART_3 + PART_4 + PART_5 + PART_6 + PART_7 + PART_8
if LOA_END_MARKER not in _raw_loa_block:
    raise RuntimeError("Could not find the LOA end marker while adding transaction commands.")

_transaction_block = TRANSACTION_BLOCK

_old_log_permission = '''    if not await member_can_log_sales(interaction):
        await interaction.response.send_message(
            "You do not have permission to log transactions.",
            ephemeral=True,
        )
        return False'''
_new_log_permission = '''    member = interaction.user
    if not isinstance(member, discord.Member):
        try:
            member = await interaction.guild.fetch_member(interaction.user.id)
        except discord.DiscordException:
            await interaction.response.send_message(
                "I could not verify your server roles.",
                ephemeral=True,
            )
            return False

    has_chat_moderation = any(
        re.sub(r"[^a-z0-9]", "", role.name.casefold())
        in {"chatmoderation", "chatmoderator"}
        for role in member.roles
    )
    has_existing_sales_access = await member_can_log_sales(interaction)
    if not (
        member.guild_permissions.administrator
        or has_chat_moderation
        or has_existing_sales_access
    ):
        await interaction.response.send_message(
            "Only members with the @Chat Moderation role can log transactions.",
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return False'''

_old_check_role = '''    has_chat_moderation = any(
        role.name.casefold() == "chat moderation"
        for role in member.roles
    )'''
_new_check_role = '''    has_chat_moderation = any(
        re.sub(r"[^a-z0-9]", "", role.name.casefold())
        in {"chatmoderation", "chatmoderator"}
        for role in member.roles
    )'''

if _old_log_permission in _transaction_block:
    _transaction_block = _transaction_block.replace(
        _old_log_permission,
        _new_log_permission,
        1,
    )

if _old_check_role in _transaction_block:
    _transaction_block = _transaction_block.replace(
        _old_check_role,
        _new_check_role,
        1,
    )

# Keep the transaction block inside the LOA markers so main.py removes and
# regenerates both blocks cleanly on every Railway restart.
LOA_BLOCK = _raw_loa_block.replace(
    LOA_END_MARKER,
    _transaction_block.strip() + "\n" + LOA_END_MARKER,
    1,
)
