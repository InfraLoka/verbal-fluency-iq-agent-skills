# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Evidence ranked by contribution, not by position in the text (G-043).

Each analyser scores every sentence (or transition) with a ``contribution``
value in the metric's own units. Reviewers see the sentences that pushed the
metric up the most (``rank: "strongest"``) and the ones that held it down the
most (``rank: "weakest"``), so evidence explains the score instead of quoting
whatever came first.
"""

from typing import Any

EVIDENCE_PER_SIDE = 2


def rank_evidence(
    items: list[dict[str, Any]], per_side: int = EVIDENCE_PER_SIDE
) -> list[dict[str, Any]]:
    """Strongest ``per_side`` items (descending), then weakest (ascending).

    Every item must carry a numeric ``contribution``. Ties keep text order. An
    item appears at most once, so short texts return fewer than 2 x per_side.
    """
    positions = range(len(items))
    strongest = sorted(positions, key=lambda i: (-items[i]["contribution"], i))[
        :per_side
    ]
    weakest = [
        i
        for i in sorted(positions, key=lambda i: (items[i]["contribution"], i))
        if i not in strongest
    ][:per_side]
    return [{**items[i], "rank": "strongest"} for i in strongest] + [
        {**items[i], "rank": "weakest"} for i in weakest
    ]
