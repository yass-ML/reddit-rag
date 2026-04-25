"""Reddit-facing text cleanup before chunking and storage.

Removes obvious empty/deleted markers and invisible noise. Does not reflow
paragraphs into a single line, strip URL punctuation, or remove Markdown
blockquotes or quoted phrases.
"""

from __future__ import annotations

import re

# Zero-width space, word joiner, BOM — common copy/paste / editor noise.
_REMOVABLE_INVISIBLE = str.maketrans("", "", "\u200b\u2060\ufeff")

# Collapse runs of three or more newlines to two (one blank line between blocks).
_NEWLINE_RUN = re.compile(r"\n{3,}")


def clean_reddit_text(text: str) -> str:
    """Return cleaned Reddit body/selftext suitable for chunking.

    - Strips leading/trailing whitespace from the whole string.
    - Maps a body that is only ``[deleted]`` or ``[removed]`` (after strip) to
      ``""``. Longer text that merely *contains* those tokens is unchanged.
    - Removes U+200B, U+2060, and U+FEFF anywhere in the string.
    - Collapses three or more consecutive newlines to two newlines.
    - Does not alter URL characters (including trailing ``)`` or ``]``),
      straight double quotes, ``>`` quote markers, or spaces inside lines
      except via the rules above.
    """
    text = text.translate(_REMOVABLE_INVISIBLE).strip()
    if not text:
        return ""
    if text in ("[deleted]", "[removed]"):
        return ""
    text = _NEWLINE_RUN.sub("\n\n", text)
    return text.strip()
