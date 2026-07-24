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

# Keep the transaction block inside the LOA markers so main.py removes and
# regenerates both blocks cleanly on every Railway restart.
LOA_BLOCK = _raw_loa_block.replace(
    LOA_END_MARKER,
    TRANSACTION_BLOCK.strip() + "\n" + LOA_END_MARKER,
    1,
)
