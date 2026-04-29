"""
test_io.py — Tests for instance parser, matching serialiser, and CLI I/O.

Covers:
  - Valid parses (comments, metadata, blank lines)
  - Error cases: n negative, n=0, index out of range, wrong triple count
  - Matching write/read round-trip
  - CLI produces correct stats line format
"""

import io
import os
import sys
import tempfile
import pytest

from threedm.instance import load, Instance
from threedm.matching import Matching, write_matching

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _path(name: str) -> str:
    return os.path.join(DATA_DIR, name)


# ---------------------------------------------------------------------------
# Instance parser — valid cases
# ---------------------------------------------------------------------------

class TestParserValid:
    def test_mini1_metadata(self):
        inst = load(_path("mini1.3dm"))
        assert inst.n == 2
        assert inst.m == 3
        assert inst.meta.get("opt") == 2
        assert inst.meta.get("family") == "mini"

    def test_mini2_triples(self):
        inst = load(_path("mini2.3dm"))
        assert len(inst.triples) == inst.m == 5
        # All triples have elements in [0, n)
        for x, y, z in inst.triples:
            assert 0 <= x < inst.n
            assert 0 <= y < inst.n
            assert 0 <= z < inst.n

    def test_empty_instance(self):
        inst = load(_path("empty.3dm"))
        assert inst.m == 0
        assert inst.triples == []

    def test_comment_lines_ignored(self, tmp_path):
        f = tmp_path / "comments.3dm"
        f.write_text(
            "# this is a comment\n"
            "# another comment\n"
            "\n"
            "2 2\n"
            "0 0 0\n"
            "1 1 1\n"
        )
        inst = load(str(f))
        assert inst.n == 2
        assert inst.m == 2

    def test_opt_seed_metadata(self, tmp_path):
        f = tmp_path / "meta.3dm"
        f.write_text(
            "# opt=7\n"
            "# seed=42\n"
            "# family=random\n"
            "1 1\n"
            "0 0 0\n"
        )
        inst = load(str(f))
        assert inst.meta["opt"] == 7
        assert inst.meta["seed"] == 42
        assert inst.meta["family"] == "random"


# ---------------------------------------------------------------------------
# Instance parser — error cases
# ---------------------------------------------------------------------------

class TestParserErrors:
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load("/nonexistent/path/foo.3dm")

    def test_n_zero(self, tmp_path):
        f = tmp_path / "bad.3dm"
        f.write_text("0 0\n")
        with pytest.raises(ValueError, match=r"n must be >= 1"):
            load(str(f))

    def test_n_negative(self, tmp_path):
        f = tmp_path / "bad.3dm"
        f.write_text("-1 0\n")
        with pytest.raises(ValueError, match=r"n must be >= 1"):
            load(str(f))

    def test_m_negative(self, tmp_path):
        f = tmp_path / "bad.3dm"
        f.write_text("3 -1\n")
        with pytest.raises(ValueError, match=r"m must be >= 0"):
            load(str(f))

    def test_x_out_of_range(self, tmp_path):
        f = tmp_path / "bad.3dm"
        f.write_text("2 1\n3 0 0\n")  # x=3 not in [0,2)
        with pytest.raises(ValueError, match=r"out of range"):
            load(str(f))

    def test_y_out_of_range(self, tmp_path):
        f = tmp_path / "bad.3dm"
        f.write_text("2 1\n0 5 0\n")
        with pytest.raises(ValueError, match=r"out of range"):
            load(str(f))

    def test_z_out_of_range(self, tmp_path):
        f = tmp_path / "bad.3dm"
        f.write_text("2 1\n0 0 99\n")
        with pytest.raises(ValueError, match=r"out of range"):
            load(str(f))

    def test_wrong_triple_count(self, tmp_path):
        f = tmp_path / "bad.3dm"
        f.write_text("3 3\n0 0 0\n1 1 1\n")  # declares 3 but provides 2
        with pytest.raises(ValueError, match=r"triple lines"):
            load(str(f))

    def test_empty_file(self, tmp_path):
        f = tmp_path / "bad.3dm"
        f.write_text("")
        with pytest.raises(ValueError):
            load(str(f))

    def test_comments_only(self, tmp_path):
        f = tmp_path / "bad.3dm"
        f.write_text("# only a comment\n")
        with pytest.raises(ValueError):
            load(str(f))


# ---------------------------------------------------------------------------
# Matching serialiser
# ---------------------------------------------------------------------------

class TestMatchingWrite:
    def test_stdout_output(self, capsys):
        m = Matching(indices=[0, 2])
        stats = {
            "time_ms": 1.234,
            "nodes": 42,
            "algo": "brute",
            "n": 3,
            "m": 5,
        }
        write_matching(None, m, stats)
        captured = capsys.readouterr().out
        lines = captured.strip().splitlines()
        assert lines[0] == "2"          # k
        assert lines[1] == "1"          # index 0 -> 1-based
        assert lines[2] == "3"          # index 2 -> 1-based
        assert lines[3].startswith("# stats:")
        assert "algo=brute" in lines[3]
        assert "nodes=42" in lines[3]
        assert "timed_out" not in lines[3]

    def test_file_output(self, tmp_path):
        out_file = str(tmp_path / "solution.out")
        m = Matching(indices=[1])
        stats = {
            "time_ms": 0.5,
            "nodes": 10,
            "algo": "smart",
            "n": 2,
            "m": 3,
        }
        write_matching(out_file, m, stats)
        content = open(out_file).read()
        assert "1\n2\n" in content
        assert "algo=smart" in content

    def test_timed_out_flag(self, capsys):
        m = Matching(indices=[])
        stats = {
            "time_ms": 5000.0,
            "nodes": 99,
            "algo": "smart",
            "n": 10,
            "m": 50,
            "timed_out": 1,
        }
        write_matching(None, m, stats)
        captured = capsys.readouterr().out
        assert "timed_out=1" in captured

    def test_empty_matching(self, capsys):
        m = Matching(indices=[])
        stats = {
            "time_ms": 0.1,
            "nodes": 1,
            "algo": "brute",
            "n": 5,
            "m": 0,
        }
        write_matching(None, m, stats)
        captured = capsys.readouterr().out
        lines = captured.strip().splitlines()
        assert lines[0] == "0"
        assert lines[1].startswith("# stats:")
