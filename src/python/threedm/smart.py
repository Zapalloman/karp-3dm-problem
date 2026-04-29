"""
smart.py — SMART backtracking algorithm for 3-Dimensional Matching.

Implements exactly the pseudocode in docs/ALGORITHMS.md (solveSmart / recur)
with the following improvements over BASE:

  1. Bitmask O(1) conflict test (Python native int, arbitrary precision).
  2. MRV (Minimum Remaining Values): at each step pick the free element
     (any dimension) with the fewest available triples.
  3. Forward checking: implicit via bitmasks (taken triples are excluded
     from availability checks at zero extra cost).
  4. Upper-bound pruning: |chosen| + min(freeX, freeY, freeZ) <= |best|
     → prune.
  5. Branch on the chosen element's available triples + "skip element"
     branch instead of enumerating all m triples.

Discarding: a fourth set of bitmasks (discarded_x/y/z) tracks elements
that have been "given up" in the current branch — they are not free but
also not used by a chosen triple, so they are excluded from MRV.
"""

from __future__ import annotations

from .instance import Instance
from .matching import Matching


def _build_index(n: int, triples: list) -> tuple[list, list, list]:
    """Build inX, inY, inZ: for each element e in 0..n-1, the list of
    triple indices that contain e in that dimension."""
    in_x: list[list[int]] = [[] for _ in range(n)]
    in_y: list[list[int]] = [[] for _ in range(n)]
    in_z: list[list[int]] = [[] for _ in range(n)]
    for i, (x, y, z) in enumerate(triples):
        in_x[x].append(i)
        in_y[y].append(i)
        in_z[z].append(i)
    return in_x, in_y, in_z


def _popcount(v: int) -> int:
    """Return the number of set bits in non-negative integer v."""
    return bin(v).count("1")


def solve_smart(
    inst: Instance,
    aborted_flag: "list[bool] | None" = None,
) -> tuple[Matching, dict]:
    """Run the SMART backtracking algorithm on *inst*.

    Parameters
    ----------
    inst         : parsed Instance
    aborted_flag : single-element list [False]; timer thread sets [0]=True to
                   abort.  Pass None to disable.

    Returns
    -------
    (Matching, stats_dict)
    """
    n = inst.n
    m = inst.m
    triples = inst.triples

    if aborted_flag is None:
        aborted_flag = [False]

    in_x, in_y, in_z = _build_index(n, triples)

    # mask covering all n element bits
    mask_n: int = (1 << n) - 1

    # --- mutable state ---
    chosen: list[int] = []
    best: list[int] = []
    nodes_counter: list[int] = [0]

    # Bitmasks for used elements (chosen triples)
    used_x: list[int] = [0]
    used_y: list[int] = [0]
    used_z: list[int] = [0]

    # Bitmasks for discarded elements (element given up in current branch)
    disc_x: list[int] = [0]
    disc_y: list[int] = [0]
    disc_z: list[int] = [0]

    def triple_available(i: int) -> bool:
        """True if triple i's three elements are all free (not used, not discarded)."""
        x, y, z = triples[i]
        # A triple is available iff its elements are not used by any chosen triple.
        # Discarded elements are still "free" in the sense that bit is 0 in used_*.
        # We only care about used_* here; discarded is separate.
        return (
            not ((used_x[0] >> x) & 1)
            and not ((used_y[0] >> y) & 1)
            and not ((used_z[0] >> z) & 1)
        )

    def recur() -> None:
        if aborted_flag[0]:
            return

        nodes_counter[0] += 1

        # --- 1) Upper-bound pruning ---
        # "free" = not used AND not discarded in current branch
        blocked_x = used_x[0] | disc_x[0]
        blocked_y = used_y[0] | disc_y[0]
        blocked_z = used_z[0] | disc_z[0]

        free_x = _popcount((~blocked_x) & mask_n)
        free_y = _popcount((~blocked_y) & mask_n)
        free_z = _popcount((~blocked_z) & mask_n)
        upper = len(chosen) + min(free_x, free_y, free_z)
        if upper <= len(best):
            return

        # --- 2) MRV: find the free element with fewest available triples ---
        # "free" = not used AND not discarded
        mrv_count = None
        mrv_dim = -1
        mrv_elem = -1

        for e in range(n):
            if not ((blocked_x >> e) & 1):
                cnt = sum(1 for i in in_x[e] if triple_available(i))
                if mrv_count is None or cnt < mrv_count:
                    mrv_count = cnt
                    mrv_dim = 0
                    mrv_elem = e

        for e in range(n):
            if not ((blocked_y >> e) & 1):
                cnt = sum(1 for i in in_y[e] if triple_available(i))
                if mrv_count is None or cnt < mrv_count:
                    mrv_count = cnt
                    mrv_dim = 1
                    mrv_elem = e

        for e in range(n):
            if not ((blocked_z >> e) & 1):
                cnt = sum(1 for i in in_z[e] if triple_available(i))
                if mrv_count is None or cnt < mrv_count:
                    mrv_count = cnt
                    mrv_dim = 2
                    mrv_elem = e

        # No free elements left — current partial is maximal locally
        if mrv_count is None:
            if len(chosen) > len(best):
                best[:] = chosen[:]
            return

        e = mrv_elem
        dim = mrv_dim

        # --- 3) MRV element has 0 available triples: discard it ---
        if mrv_count == 0:
            if dim == 0:
                disc_x[0] |= (1 << e)
                recur()
                disc_x[0] ^= (1 << e)
            elif dim == 1:
                disc_y[0] |= (1 << e)
                recur()
                disc_y[0] ^= (1 << e)
            else:
                disc_z[0] |= (1 << e)
                recur()
                disc_z[0] ^= (1 << e)
            return

        # --- 4) Try each available triple for element (dim, e) ---
        if dim == 0:
            candidates = [i for i in in_x[e] if triple_available(i)]
        elif dim == 1:
            candidates = [i for i in in_y[e] if triple_available(i)]
        else:
            candidates = [i for i in in_z[e] if triple_available(i)]

        for i in candidates:
            if aborted_flag[0]:
                return
            x, y, z = triples[i]
            used_x[0] |= (1 << x)
            used_y[0] |= (1 << y)
            used_z[0] |= (1 << z)
            chosen.append(i)
            recur()
            chosen.pop()
            used_x[0] ^= (1 << x)
            used_y[0] ^= (1 << y)
            used_z[0] ^= (1 << z)

        # --- 5) "Do not match e": discard e in its dimension ---
        if dim == 0:
            disc_x[0] |= (1 << e)
            recur()
            disc_x[0] ^= (1 << e)
        elif dim == 1:
            disc_y[0] |= (1 << e)
            recur()
            disc_y[0] ^= (1 << e)
        else:
            disc_z[0] |= (1 << e)
            recur()
            disc_z[0] ^= (1 << e)

    recur()

    stats = {
        "nodes": nodes_counter[0],
        "timed_out": aborted_flag[0],
    }
    return Matching(indices=best[:]), stats
