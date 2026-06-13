"""Parser for @goal-N mentions in discussion messages."""

import re

_GOAL_MENTION_RE = re.compile(r"@goal-(\d+)")


def parse_goal_mentions(content: str) -> list[int]:
    """Extract goal IDs from @goal-N mentions in content.

    Example:
        >>> parse_goal_mentions("Please work on @goal-3 and @goal-7")
        [3, 7]
    """
    return [int(m) for m in _GOAL_MENTION_RE.findall(content)]
