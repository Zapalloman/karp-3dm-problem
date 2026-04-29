"""
test_smart.py — Regression tests for the SMART backtracking algorithm.

Each test loads a .3dm fixture and asserts:
  1. The matching size equals expected OPT.
  2. The matching is conflict-free.
  3. brute and smart return the same size (correctness cross-check).
"""

import os
import pytest

from threedm.instance import load
from threedm.brute import solve_brute
from threedm.smart import solve_smart

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _path(name: str) -> str:
    return os.path.join(DATA_DIR, name)


def _run(filename: str, expected_opt: int) -> None:
    inst = load(_path(filename))

    brute_m, _ = solve_brute(inst)
    smart_m, smart_stats = solve_smart(inst)

    # Both algorithms must agree on OPT
    assert smart_m.size == expected_opt, (
        f"smart on {filename}: expected OPT={expected_opt}, got {smart_m.size}"
    )
    assert brute_m.size == smart_m.size, (
        f"brute/smart disagree on {filename}: "
        f"brute={brute_m.size} smart={smart_m.size}"
    )

    # nodes must be positive
    assert smart_stats["nodes"] > 0

    # Conflict-free check
    used_x, used_y, used_z = set(), set(), set()
    for idx in smart_m.indices:
        assert 0 <= idx < inst.m
        x, y, z = inst.triples[idx]
        assert x not in used_x, f"x={x} reused in smart solution"
        assert y not in used_y, f"y={y} reused in smart solution"
        assert z not in used_z, f"z={z} reused in smart solution"
        used_x.add(x)
        used_y.add(y)
        used_z.add(z)


def test_mini1():
    _run("mini1.3dm", expected_opt=2)


def test_mini2():
    _run("mini2.3dm", expected_opt=3)


def test_noperf():
    _run("noperf.3dm", expected_opt=1)


def test_dense():
    _run("dense.3dm", expected_opt=4)


def test_empty():
    _run("empty.3dm", expected_opt=0)
