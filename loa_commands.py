"""Assemble the generated LOA command block."""

from loa_text_part_1 import PART as PART_1
from loa_text_part_2 import PART as PART_2
from loa_text_part_3 import PART as PART_3
from loa_text_part_4 import PART as PART_4
from loa_text_part_5 import PART as PART_5
from loa_text_part_6 import PART as PART_6
from loa_text_part_7 import PART as PART_7
from loa_text_part_8 import PART as PART_8

LOA_START_MARKER = "# ---- LOA tracking commands ----"
LOA_END_MARKER = "# ---- End LOA tracking commands ----"
LOA_BLOCK = PART_1 + PART_2 + PART_3 + PART_4 + PART_5 + PART_6 + PART_7 + PART_8
