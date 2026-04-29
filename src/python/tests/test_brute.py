"""
test_brute.py — Regression tests for the BASE backtracking algorithm.

Each test loads a .3dm fixture from tests/data/ and asserts that the
returned matching size matches the expected OPT stored in the file's
metadata.
"""

import os
import pytest

from threedm.instance import load
from threedm.brute import solve_brute

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _path(name: str) -> str:
    return os.path.join(DATA_DIR, name)


def _run(filename: str, expected_opt: int) -> None:
    inst = load(_path(filename))
    matching, stats = solve_brute(inst)
    assert matching.size == expected_opt, (
        f"brute on {filename}: expected OPT={expected_opt}, got {matching.size}"
    )
    # nodes must be positive (at least one call)
    assert stats["nodes"] > 0
    # indices must be valid (0-based, in range)
    for idx in matching.indices:
        assert 0 <= idx < inst.m
    # chosen triples must not conflict
    used_x, used_y, used_z = set(), set(), set()
    for idx in matching.indices:
        x, y, z = inst.triples[idx]
        assert x not in used_x, f"x={x} reused in brute solution"
        assert y not in used_y, f"y={y} reused in brute solution"
        assert z not in used_z, f"z={z} reused in brute solution"
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
