"""
matching.py — Dataclass and serialiser for 3DM solutions.

Output format (docs/INSTANCE_FORMAT.md):
    k
    i1
    i2
    ...
    ik
    # stats: time_ms=<float> nodes=<int> algo=<brute|smart> n=<n> m=<m> [timed_out=1]

Indices are 1-based (as specified by INSTANCE_FORMAT.md).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import List


@dataclass
class Matching:
    """A 3DM solution.

    Attributes:
        indices: 0-based indices into Instance.triples for chosen triples.
                 Serialised as 1-based in the output file.
        size   : |M| = len(indices)  (kept for convenience)
    """
    indices: List[int]

    @property
    def size(self) -> int:
        return len(self.indices)


def write_matching(
    dest: "str | None",
    matching: Matching,
    stats: dict,
) -> None:
    """Write a matching + stats to *dest* (file path) or stdout if None.

    *stats* must contain at minimum:
        time_ms : float
        nodes   : int
        algo    : str  ('brute' or 'smart')
        n       : int
        m       : int
    Optional:
        timed_out : int  (1 if time limit was hit)
    """
    lines: list[str] = []
    lines.append(str(matching.size))
    for idx in matching.indices:
        lines.append(str(idx + 1))  # convert to 1-based

    # Build stats line
    stats_parts = [
        f"time_ms={stats['time_ms']:.3f}",
        f"nodes={stats['nodes']}",
        f"algo={stats['algo']}",
        f"n={stats['n']}",
        f"m={stats['m']}",
    ]
    if stats.get("timed_out"):
        stats_parts.append("timed_out=1")
    lines.append("# stats: " + " ".join(stats_parts))

    output = "\n".join(lines) + "\n"

    if dest is None:
        sys.stdout.write(output)
    else:
        with open(dest, "w") as fh:
            fh.write(output)
