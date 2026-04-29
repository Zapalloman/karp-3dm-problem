"""
threedm — 3-Dimensional Matching solver (Python implementation).

Exposes two solvers:
  - brute: backtracking BASE (no heuristics)
  - smart: backtracking with MRV + bitmask + bound pruning
"""

from .instance import Instance, load
from .matching import Matching, write_matching
from .brute import solve_brute
from .smart import solve_smart

__all__ = [
    "Instance",
    "load",
    "Matching",
    "write_matching",
    "solve_brute",
    "solve_smart",
]
