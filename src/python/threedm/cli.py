"""
cli.py — Command-line entry point for the 3DM solvers.

Usage:
    python -m threedm <instance.3dm> [--algo brute|smart]
                                     [--time-limit SECONDS]
                                     [--seed N]
                                     [--output PATH]

The --seed flag is accepted for interface uniformity (used only if smart
adds any randomised tie-breaking; currently smart is deterministic).
"""

from __future__ import annotations

import argparse
import sys
import time
import threading

from .instance import load
from .matching import write_matching
from .brute import solve_brute
from .smart import solve_smart


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="threedm",
        description="3-Dimensional Matching solver (Python implementation).",
    )
    parser.add_argument("instance", help="Path to .3dm instance file.")
    parser.add_argument(
        "--algo",
        choices=["brute", "smart"],
        default="smart",
        help="Algorithm to use: brute (BASE) or smart (SMART). Default: smart.",
    )
    parser.add_argument(
        "--time-limit",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Wall-clock time limit in seconds.  Returns best partial solution on timeout.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        metavar="N",
        help="Random seed for tie-breaking (currently unused; kept for CLI uniformity).",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help="Write solution to PATH instead of stdout.",
    )

    args = parser.parse_args()

    # --- Load instance ---
    try:
        inst = load(args.instance)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # --- Set up time-limit flag ---
    aborted_flag: list[bool] = [False]
    timer: threading.Timer | None = None
    if args.time_limit is not None:
        def _abort():
            aborted_flag[0] = True

        timer = threading.Timer(args.time_limit, _abort)
        timer.daemon = True
        timer.start()

    # --- Run solver ---
    t_start = time.perf_counter()
    try:
        if args.algo == "brute":
            matching, algo_stats = solve_brute(inst, aborted_flag=aborted_flag)
        else:
            matching, algo_stats = solve_smart(inst, aborted_flag=aborted_flag)
    finally:
        if timer is not None:
            timer.cancel()

    elapsed_ms = (time.perf_counter() - t_start) * 1000.0

    # --- Build stats dict ---
    stats: dict = {
        "time_ms": elapsed_ms,
        "nodes": algo_stats["nodes"],
        "algo": args.algo,
        "n": inst.n,
        "m": inst.m,
    }
    if algo_stats.get("timed_out"):
        stats["timed_out"] = 1

    # --- Write output ---
    write_matching(args.output, matching, stats)


if __name__ == "__main__":
    main()
