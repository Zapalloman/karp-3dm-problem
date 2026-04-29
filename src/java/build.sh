#!/usr/bin/env bash
# build.sh — Compile the Java 3DM implementation.
#
# Usage:
#   bash build.sh
#
# Output: class files in src/java/build/
#
# Requires: JDK 17+ (tested with OpenJDK 21.0.10).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Locate javac: prefer system PATH, then known VSCode JRE location.
if command -v javac &>/dev/null; then
    JAVAC_CMD=javac
elif [ -x "/home/javier/.vscode/extensions/redhat.java-1.54.0-linux-x64/jre/21.0.10-linux-x86_64/bin/javac" ]; then
    JAVAC_CMD="/home/javier/.vscode/extensions/redhat.java-1.54.0-linux-x64/jre/21.0.10-linux-x86_64/bin/javac"
else
    echo "ERROR: javac not found. Install JDK 17+ and ensure it is on PATH."
    exit 1
fi

mkdir -p build

# Collect all .java sources
SOURCES=$(find src -name '*.java')

# Compile with strict warnings
# -Xlint:all enables all lint checks; -Werror treats warnings as errors.
$JAVAC_CMD -Xlint:all -Werror -d build $SOURCES

echo "Compiled successfully → build/"
echo "Run with: java -cp build com.threedm.Main <instance.3dm> [--algo brute|smart]"
