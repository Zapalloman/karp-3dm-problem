#!/usr/bin/env bash
# run_tests.sh — Regression tests for the Java 3DM implementation.
#
# Usage:
#   bash tests/run_tests.sh
#
# Must be run from src/java/ (or adjust JAVA_CMD and DATA_DIR paths).
#
# For each test instance:
#   1. Runs BRUTE and SMART algorithms.
#   2. Checks that the OPT reported in the output matches the # opt=K metadata.
#   3. Reports PASS or FAIL.
#
# Also verifies that mini2 gives nodes=35 (brute) and nodes=7 (smart)
# to ensure parity with Python and C++.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JAVA_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$JAVA_DIR/build"
DATA_DIR="$SCRIPT_DIR/data"

# Find javac/java — look for JDK in common locations
if command -v java &>/dev/null; then
    JAVA_CMD=java
elif [ -x "/home/javier/.vscode/extensions/redhat.java-1.54.0-linux-x64/jre/21.0.10-linux-x86_64/bin/java" ]; then
    JAVA_CMD="/home/javier/.vscode/extensions/redhat.java-1.54.0-linux-x64/jre/21.0.10-linux-x86_64/bin/java"
else
    echo "ERROR: java not found in PATH or common locations."
    exit 1
fi

PASS=0
FAIL=0
TOTAL=0

run_test() {
    local instance="$1"
    local algo="$2"
    local expected_opt="$3"
    local expected_nodes="${4:-}"

    TOTAL=$((TOTAL + 1))
    local name
    name=$(basename "$instance" .3dm)

    local output
    output=$("$JAVA_CMD" -cp "$BUILD_DIR" com.threedm.Main "$instance" --algo "$algo" 2>&1)
    local exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo "FAIL [$name/$algo] exit code $exit_code"
        echo "  output: $output"
        FAIL=$((FAIL + 1))
        return
    fi

    # Extract k (first non-comment line = number of triples in matching)
    local k
    k=$(echo "$output" | grep -v '^#' | head -1)

    if [ "$k" != "$expected_opt" ]; then
        echo "FAIL [$name/$algo] expected OPT=$expected_opt, got k=$k"
        echo "  output: $output"
        FAIL=$((FAIL + 1))
        return
    fi

    # Check node count if specified
    if [ -n "$expected_nodes" ]; then
        local nodes
        nodes=$(echo "$output" | grep '^# stats:' | sed 's/.*nodes=\([0-9]*\).*/\1/')
        if [ "$nodes" != "$expected_nodes" ]; then
            echo "FAIL [$name/$algo] expected nodes=$expected_nodes, got nodes=$nodes"
            echo "  output: $output"
            FAIL=$((FAIL + 1))
            return
        fi
    fi

    echo "PASS [$name/$algo] OPT=$k${expected_nodes:+ nodes=$expected_nodes}"
    PASS=$((PASS + 1))
}

# Check that build/ exists
if [ ! -d "$BUILD_DIR" ]; then
    echo "ERROR: build/ not found. Run 'bash build.sh' first."
    exit 1
fi

echo "=== Java 3DM regression tests ==="
echo ""

# mini1: n=2, m=3, OPT=2
run_test "$DATA_DIR/mini1.3dm" brute 2
run_test "$DATA_DIR/mini1.3dm" smart 2

# mini2: n=3, m=5, OPT=3 — also check node counts for parity with Python/C++
run_test "$DATA_DIR/mini2.3dm" brute 3 35
run_test "$DATA_DIR/mini2.3dm" smart 3 7

# noperf: n=3, m=3, OPT=1
run_test "$DATA_DIR/noperf.3dm" brute 1
run_test "$DATA_DIR/noperf.3dm" smart 1

# dense: n=4, m=16, OPT=4
run_test "$DATA_DIR/dense.3dm" brute 4
run_test "$DATA_DIR/dense.3dm" smart 4

# empty: n=5, m=0, OPT=0
run_test "$DATA_DIR/empty.3dm" brute 0
run_test "$DATA_DIR/empty.3dm" smart 0

echo ""
echo "=== Results: $PASS/$TOTAL PASS, $FAIL FAIL ==="

if [ $FAIL -ne 0 ]; then
    exit 1
fi
