"""
brute.py — BASE backtracking algorithm for 3-Dimensional Matching.

Implements exactly the pseudocode in docs/ALGORITHMS.md (solveBrute / recur).
No heuristics, no pruning beyond feasibility.  Complexity O(2^m).

The solver returns a Matching and a stats dict.  The stats dict carries
  nodes    : int   — number of recursive calls (including leaf calls)
  timed_out: bool  — True if the time-limit flag was set before completion
"""

from __future__ import annotations

from .instance import Instance
from .matching import Matching


def solve_brute(
    inst: Instance,
    aborted_flag: "list[bool] | None" = None,
) -> tuple[Matching, dict]:
    """Run the BASE backtracking algorithm on *inst*.

    Parameters
    ----------
    inst         : parsed Instance
    aborted_flag : a single-element list [False] shared with a Timer thread;
                   when the Timer fires it sets aborted_flag[0] = True and
                   the recursion exits early returning the best partial solution.
                   Pass None to disable time-limiting.

    Returns
    -------
    (Matching, stats_dict)
    """
    n = inst.n
    m = inst.m
    triples = inst.triples

    # Mutable state (Python closures cannot rebind names, use lists)
    chosen: list[int] = []
    best: list[int] = []
    nodes_counter: list[int] = [0]

    # Bitmasks — Python ints support arbitrary precision
    used_x: list[int] = [0]
    used_y: list[int] = [0]
    used_z: list[int] = [0]

    # aborted_flag is a mutable container so the timer thread can set it
    if aborted_flag is None:
        aborted_flag = [False]

    def recur(i: int) -> None:
        # Check time-limit flag first
        if aborted_flag[0]:
            return

        nodes_counter[0] += 1

        # Base case: exhausted all triples
        if i == m:
            if len(chosen) > len(best):
                best[:] = chosen[:]
            return

        # Branch 1: take triple i if available
        x, y, z = triples[i]
        if not ((used_x[0] >> x) & 1) and \
           not ((used_y[0] >> y) & 1) and \
           not ((used_z[0] >> z) & 1):
            used_x[0] |= (1 << x)
            used_y[0] |= (1 << y)
            used_z[0] |= (1 << z)
            chosen.append(i)
            recur(i + 1)
            chosen.pop()
            used_x[0] ^= (1 << x)
            used_y[0] ^= (1 << y)
            used_z[0] ^= (1 << z)

        # Branch 2: skip triple i
        recur(i + 1)

    recur(0)

    stats = {
        "nodes": nodes_counter[0],
        "timed_out": aborted_flag[0],
    }
    return Matching(indices=best[:]), stats
