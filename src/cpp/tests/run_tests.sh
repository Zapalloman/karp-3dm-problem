#!/usr/bin/env bash
# run_tests.sh — Regression tests for the C++ 3DM solver.
#
# For each .3dm file in tests/data/ that has a "# opt=K" metadata line,
# runs both brute and smart, parses the first output line (k = matching size),
# and checks it equals K.
#
# Exits with non-zero status if any test fails.
#
# Usage: called by "make test" from src/cpp/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="${SCRIPT_DIR}/../3dm"
DATA_DIR="${SCRIPT_DIR}/data"

if [[ ! -x "$BIN" ]]; then
    echo "ERROR: binary not found at $BIN — run 'make' first."
    exit 1
fi

pass=0
fail=0

for f in "$DATA_DIR"/*.3dm; do
    # Extract opt= from file metadata.
    opt_line=$(grep -m1 '^# opt=' "$f" 2>/dev/null || true)
    if [[ -z "$opt_line" ]]; then
        echo "SKIP  $(basename "$f")  (no opt= metadata)"
        continue
    fi
    expected=$(echo "$opt_line" | sed 's/^# opt=//')

    for algo in brute smart; do
        output=$("$BIN" "$f" --algo "$algo")
        # First non-comment, non-blank line is the matching size.
        got=$(echo "$output" | grep -v '^#' | head -1)
        if [[ "$got" == "$expected" ]]; then
            echo "PASS  $(basename "$f")  algo=$algo  opt=$expected"
            ((pass++)) || true
        else
            echo "FAIL  $(basename "$f")  algo=$algo  expected=$expected  got=$got"
            ((fail++)) || true
        fi
    done
done

echo ""
echo "Results: $pass passed, $fail failed."
if [[ "$fail" -ne 0 ]]; then
    exit 1
fi
