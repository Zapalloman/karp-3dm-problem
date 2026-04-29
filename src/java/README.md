# 3DM — Java Implementation

Java 17+ implementation of two algorithms for 3-Dimensional Matching (Karp #17):
- **BRUTE**: plain backtracking, O(2^m).
- **SMART**: backtracking with MRV + bitmask forward-checking + upper-bound pruning.

## Environment

- **JDK**: OpenJDK 21.0.10 (Temurin-21.0.10+7, 64-bit), Linux x86-64.
- **Standard library only** — no external dependencies.

## Build

```bash
bash build.sh
```

Compiles all sources to `build/` using `-Xlint:all -Werror`.

## Run

```bash
java -cp build com.threedm.Main <instance.3dm> [--algo brute|smart] \
     [--time-limit SECONDS] [--seed N] [--output PATH]
```

Defaults: `--algo smart`.  If `--output` is omitted, output goes to stdout.

## Tests

```bash
bash tests/run_tests.sh
```

Runs both algorithms on 5 regression instances and checks OPT values.
Also verifies node counts for mini2 (35 for brute, 7 for smart) to ensure
parity with the Python and C++ implementations.

## Output format

```
k
i1
i2
...
ik
# stats: time_ms=<float> nodes=<int> algo=<brute|smart> n=<n> m=<m> [timed_out=1]
```

Triple indices are 1-based in the output (0-based internally).

## Design decisions (Phase 6)

1. **Bitmask**: `Bitmask.java` uses a single `long` for n<=64 and `long[]`
   for n>64. Runtime branch on `large` flag — no templates/generics.
   `Long.bitCount()` provides the POPCNT instruction on x86.

2. **Time-limit**: a daemon `Thread` sleeps `limitMs` milliseconds then sets
   `AtomicBoolean aborted = true`.  The solver checks this flag at the start
   of every recursive call.  Main thread interrupts the watcher after the
   solver returns.

3. **`nodes++` is FIRST** in `recur()`, before the abort check, so the root
   node is always counted.  Identical to Python and C++ for comparable metrics.

4. **MRV**: three separate loops over X, Y, Z elements (not interleaved).
   Tie-breaking by ascending element index (deterministic, no randomness).

5. **Discarded bitmask (SMART)**: `discX/Y/Z` separate from `usedX/Y/Z`.
   `freeCountCombined()` computes `popcount(~(used|disc) & maskN)` in one pass.

6. **Static mrvDim/mrvElem/mrvCount** in `Smart.pickMrv`: avoids object
   allocation on the hot recursive path. Safe because the recursion is
   single-threaded.

7. **Indices**: 0-based internally, 1-based in serialised output.
