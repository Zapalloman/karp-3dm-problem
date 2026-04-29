# 3DM C++ Implementation

C++17 implementation of the two 3-Dimensional Matching solvers:
- `brute` — BASE backtracking (docs/ALGORITHMS.md § solveBrute)
- `smart` — SMART backtracking with MRV + bitmask forward-checking + upper-bound pruning

## Build

Requires g++ (GCC) with C++17 support. Tested with GCC 15.2.1 (2026-02-09).

```
cd src/cpp
make          # produces ./3dm
make test     # runs regression tests (10 cases, all must pass)
make clean    # remove objects and binary
```

## Compiler environment (for Phase 8 benchmarks)

| Field           | Value                             |
|-----------------|-----------------------------------|
| Compiler        | g++ (GCC) 15.2.1 20260209         |
| Standard        | C++17 (-std=c++17)                |
| Optimisation    | -O2                               |
| Platform        | Linux (x86-64)                    |
| Flags           | -Wall -Wextra -pedantic           |
| Threading       | std::thread / pthreads (-lpthread)|

## Usage

```
./3dm <instance.3dm> [--algo brute|smart] [--time-limit <s>] [--seed <int>] [--output <path>]
```

- `--algo`: `brute` (BASE) or `smart` (SMART). Default: `smart`.
- `--time-limit`: wall-clock seconds. Returns best partial solution on timeout; appends `timed_out=1` to stats.
- `--seed`: accepted for CLI uniformity; currently unused (solver is deterministic).
- `--output`: write solution to file; default is stdout.

## Output format

```
k
i1
...
ik
# stats: time_ms=<float> nodes=<int> algo=<brute|smart> n=<n> m=<m> [timed_out=1]
```

Indices are 1-based. See docs/INSTANCE_FORMAT.md for the full contract.

## Source layout

```
include/
  bitmask.hpp    Bitmask: uint64_t (n<=64) or vector<uint64_t> (n>64), runtime dispatch
  instance.hpp   Instance struct + from_file() declaration
  matching.hpp   Matching struct + write_matching() declaration
  brute.hpp      solve_brute() declaration
  smart.hpp      solve_smart() declaration
src/
  instance.cpp   Parser: tolerant to '#' comments, reads opt/seed/family/note metadata
  matching.cpp   Output writer
  brute.cpp      BASE algorithm: recur(i) over triple indices 0..m-1
  smart.cpp      SMART algorithm: MRV + forward-check + bound
  main.cpp       CLI (manual argv parsing, no Boost)
tests/
  data/*.3dm     Regression instances (same files as src/python/tests/data/)
  run_tests.sh   Runs both algos on all instances, checks vs opt= metadata
```

## Design notes

- No `using namespace std` in any header.
- No external libraries beyond the C++17 stdlib.
- `nodes++` is the first statement in `recur()` (before aborted check), matching the Python implementation exactly so node counts are comparable.
- XOR (`^=`) used to undo bit-setting on backtrack (equivalent to AND-NOT since one bit at a time is set).
- Time-limit uses `std::thread` sleeping `limit_ms` milliseconds, then sets `std::atomic<bool> aborted = true`. Recursion checks at each call entry.
