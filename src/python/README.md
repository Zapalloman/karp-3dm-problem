# threedm — Python implementation

Python 3.11+ implementation of the 3-Dimensional Matching solver.
Two algorithms: `brute` (BASE backtracking) and `smart` (MRV + bitmask + bound).

## Requirements

- Python 3.11+
- No external runtime dependencies (only stdlib).
- `pytest` for running the test suite.

```bash
pip install pytest
```

## Running the solver

```bash
# from repo root
python -m threedm path/to/instance.3dm --algo smart
python -m threedm path/to/instance.3dm --algo brute
python -m threedm path/to/instance.3dm --algo smart --time-limit 10
python -m threedm path/to/instance.3dm --algo smart --output solution.out
```

The working directory must be `src/python/` (or `src/python/` must be on
PYTHONPATH) so that the `threedm` package is importable.  From the repo root:

```bash
cd src/python && python -m threedm tests/data/mini2.3dm --algo smart
# or
PYTHONPATH=src/python python -m threedm src/python/tests/data/mini2.3dm --algo smart
```

## Running tests

```bash
# from repo root
python -m pytest src/python/tests -q

# or from src/python/
cd src/python
pytest tests -q
```

## Output format

```
k
i1
i2
...
ik
# stats: time_ms=<float> nodes=<int> algo=<brute|smart> n=<n> m=<m> [timed_out=1]
```

Indices are 1-based.  See `docs/INSTANCE_FORMAT.md` for the full spec.
