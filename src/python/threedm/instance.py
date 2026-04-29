"""
instance.py — Parser and dataclass for 3DM instances.

Format (docs/INSTANCE_FORMAT.md):
    # comment lines (ignored except recognised metadata prefixes)
    n m
    x1 y1 z1
    ...
    xm ym zm

Recognised metadata prefixes in comment lines:
    # opt=K
    # seed=S
    # family=NAME
    # note: free text
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class Instance:
    """Parsed 3DM instance.

    Attributes:
        n      : |X| = |Y| = |Z|  (1-indexed elements are 0..n-1 in code)
        m      : |T|, number of triples
        triples: list of (x, y, z) tuples, indices in [0, n)
        meta   : dict of recognised metadata (opt, seed, family, note)
    """
    n: int
    m: int
    triples: List[Tuple[int, int, int]]
    meta: dict = field(default_factory=dict)


# Recognised metadata keys (value after '=')
_META_KEYS = ("opt", "seed", "family")
# 'note' uses ': ' separator


def _parse_meta_line(line: str) -> Tuple[str, object] | None:
    """Try to extract a (key, value) pair from a comment line.

    Returns None if no recognised prefix is found.
    """
    body = line[1:].strip()  # strip the leading '#'
    for key in _META_KEYS:
        prefix = key + "="
        if body.startswith(prefix):
            raw = body[len(prefix):]
            # cast to int if possible
            if key in ("opt", "seed"):
                try:
                    return key, int(raw)
                except ValueError:
                    return key, raw
            return key, raw
    if body.startswith("note:"):
        return "note", body[5:].strip()
    return None


def load(path: str) -> Instance:
    """Load a .3dm instance from *path*.

    Raises:
        FileNotFoundError : if the file does not exist.
        ValueError        : if the file is malformed (wrong header, bad index,
                            negative n/m, wrong number of triples).
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Instance file not found: {path!r}")

    meta: dict = {}
    data_lines: list[str] = []

    with open(path, "r") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue  # blank line
            if line.startswith("#"):
                result = _parse_meta_line(line)
                if result is not None:
                    key, value = result
                    meta[key] = value
                continue  # comment line
            data_lines.append(line)

    if len(data_lines) == 0:
        raise ValueError("Instance file has no data lines (missing 'n m' header).")

    # Parse header
    header = data_lines[0].split()
    if len(header) != 2:
        raise ValueError(
            f"Header line must have exactly 2 integers (n m), got: {data_lines[0]!r}"
        )
    try:
        n, m = int(header[0]), int(header[1])
    except ValueError as exc:
        raise ValueError(f"Could not parse header integers: {data_lines[0]!r}") from exc

    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}.")
    if m < 0:
        raise ValueError(f"m must be >= 0, got {m}.")

    # Parse triples
    triple_lines = data_lines[1:]
    if len(triple_lines) != m:
        raise ValueError(
            f"Header declares m={m} triples but found {len(triple_lines)} triple lines."
        )

    triples: list[tuple[int, int, int]] = []
    for idx, tline in enumerate(triple_lines, start=1):
        parts = tline.split()
        if len(parts) != 3:
            raise ValueError(
                f"Triple line {idx} must have exactly 3 integers, got: {tline!r}"
            )
        try:
            x, y, z = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError as exc:
            raise ValueError(
                f"Could not parse integers in triple line {idx}: {tline!r}"
            ) from exc
        if not (0 <= x < n):
            raise ValueError(
                f"Triple {idx}: x={x} out of range [0, {n})."
            )
        if not (0 <= y < n):
            raise ValueError(
                f"Triple {idx}: y={y} out of range [0, {n})."
            )
        if not (0 <= z < n):
            raise ValueError(
                f"Triple {idx}: z={z} out of range [0, {n})."
            )
        triples.append((x, y, z))

    return Instance(n=n, m=m, triples=triples, meta=meta)
