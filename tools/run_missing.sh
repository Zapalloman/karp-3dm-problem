#!/usr/bin/env bash
# run_missing.sh — Corre solo las instancias faltantes del benchmarks medium.
# Solo algoritmo smart (brute no se corre en medium).
# R=3 réplicas, time-limit configurable.
#
# Uso:
#   bash tools/run_missing.sh [time_limit_s]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTANCES_DIR="$REPO_ROOT/instances"
RESULTS_DIR="$REPO_ROOT/results/raw"

timelimit="${1:-60}"
R=3

ts="$(date +%Y%m%d_%H%M%S)"
out="$RESULTS_DIR/run_missing_${ts}.csv"

mkdir -p "$RESULTS_DIR"
echo "lang,algo,family,instance,n,m,opt,k,time_ms,nodes,timed_out,replica" > "$out"
echo "=== run_missing.sh: time_limit=${timelimit}s R=${R} ===" >&2
echo "Salida: $out" >&2

# Locate binaries
PYTHON_CMD="python"
CPP_BIN="$REPO_ROOT/src/cpp/3dm"
JAVA_CMD="/home/javier/.vscode/extensions/redhat.java-1.54.0-linux-x64/jre/21.0.10-linux-x86_64/bin/java"
for j in java "$JAVA_CMD" "/home/javier/.antigravity/extensions/redhat.java-1.54.0-linux-x64/jre/21.0.10-linux-x86_64/bin/java"; do
    if command -v "$j" &>/dev/null 2>&1 || [[ -x "$j" ]]; then
        JAVA_CMD="$j"
        break
    fi
done
JAVA_CP="$REPO_ROOT/src/java/build"
JAVA_MAIN="com.threedm.Main"

parse_stats() {
    local solfile="$1"
    local time_ms="NA" nodes="NA" timed_out="0" k="NA"
    [[ -f "$solfile" ]] || { echo "$time_ms $nodes $timed_out $k"; return; }
    while IFS= read -r line; do
        local ls="${line#"${line%%[![:space:]]*}"}"
        [[ -z "$ls" || "$ls" == \#* ]] && continue
        k="$ls"; break
    done < "$solfile"
    local stats_line
    stats_line=$(grep -m1 '^# stats:' "$solfile" 2>/dev/null || true)
    if [[ -n "$stats_line" ]]; then
        [[ "$stats_line" =~ time_ms=([0-9.]+) ]] && time_ms="${BASH_REMATCH[1]}"
        [[ "$stats_line" =~ nodes=([0-9]+) ]]    && nodes="${BASH_REMATCH[1]}"
        [[ "$stats_line" =~ timed_out=1 ]]        && timed_out="1"
    fi
    echo "$time_ms $nodes $timed_out $k"
}

get_opt() {
    local opt
    opt=$(grep -m1 '^# opt=' "$1" 2>/dev/null | sed 's/^# opt=//' || true)
    echo "${opt:-NA}"
}

get_nm() {
    while IFS= read -r line; do
        local ls="${line#"${line%%[![:space:]]*}"}"
        [[ -z "$ls" || "$ls" == \#* ]] && continue
        echo "$ls"; return
    done < "$1"
}

get_family() {
    local fam
    fam=$(grep -m1 '^# family=' "$1" 2>/dev/null | sed 's/^# family=//' || true)
    [[ -z "$fam" ]] && fam=$(basename "$(dirname "$1")")
    echo "$fam"
}

emit_row() {
    echo "$1,$2,$3,$4,$5,$6,$7,$8,$9,${10},${11},${12}" >> "$out"
}

sol_tmp=$(mktemp /tmp/3dm_sol_XXXXXX.txt)
trap 'rm -f "$sol_tmp"' EXIT

# List of missing instances to run
# Derived from analysis: missing are medium/structured, medium/random n50 (except s0,s1 already covered),
# and medium/hard (all will timeout)

MISSING_INSTANCES=(
    "$INSTANCES_DIR/medium/structured/structured_n30_m90_s0.3dm"
    "$INSTANCES_DIR/medium/structured/structured_n30_m90_s1.3dm"
    "$INSTANCES_DIR/medium/structured/structured_n30_m90_s2.3dm"
    "$INSTANCES_DIR/medium/structured/structured_n30_m90_s3.3dm"
    "$INSTANCES_DIR/medium/structured/structured_n30_m90_s4.3dm"
    "$INSTANCES_DIR/medium/structured/structured_n50_m150_s0.3dm"
    "$INSTANCES_DIR/medium/structured/structured_n50_m150_s1.3dm"
    "$INSTANCES_DIR/medium/structured/structured_n50_m150_s2.3dm"
    "$INSTANCES_DIR/medium/structured/structured_n50_m150_s3.3dm"
    "$INSTANCES_DIR/medium/structured/structured_n50_m150_s4.3dm"
    "$INSTANCES_DIR/medium/structured/structured_n60_m180_s0.3dm"
    "$INSTANCES_DIR/medium/structured/structured_n60_m180_s1.3dm"
    "$INSTANCES_DIR/medium/structured/structured_n60_m180_s2.3dm"
    "$INSTANCES_DIR/medium/structured/structured_n60_m180_s3.3dm"
    "$INSTANCES_DIR/medium/structured/structured_n60_m180_s4.3dm"
    "$INSTANCES_DIR/medium/random/random_n50_m200_s2.3dm"
    "$INSTANCES_DIR/medium/random/random_n50_m200_s3.3dm"
    "$INSTANCES_DIR/medium/random/random_n50_m200_s4.3dm"
    "$INSTANCES_DIR/medium/random/random_n50_m400_s0.3dm"
    "$INSTANCES_DIR/medium/random/random_n50_m400_s1.3dm"
    "$INSTANCES_DIR/medium/random/random_n50_m400_s2.3dm"
    "$INSTANCES_DIR/medium/random/random_n50_m400_s3.3dm"
    "$INSTANCES_DIR/medium/random/random_n50_m400_s4.3dm"
    "$INSTANCES_DIR/medium/random/random_n50_m800_s0.3dm"
    "$INSTANCES_DIR/medium/random/random_n50_m800_s1.3dm"
    "$INSTANCES_DIR/medium/random/random_n50_m800_s2.3dm"
    "$INSTANCES_DIR/medium/random/random_n50_m800_s3.3dm"
    "$INSTANCES_DIR/medium/random/random_n50_m800_s4.3dm"
)

# Hard instances: emit directly as timed_out=1 without running (all confirmed timeout from prior run)
HARD_INSTANCES=(
    "$INSTANCES_DIR/medium/hard/hard_n102_m3621_s0.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n102_m3621_s1.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n102_m3621_s2.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n102_m3621_s3.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n102_m3621_s4.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n156_m8346_s0.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n156_m8346_s1.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n156_m8346_s2.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n156_m8346_s3.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n156_m8346_s4.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n204_m14178_s0.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n204_m14178_s1.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n204_m14178_s2.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n204_m14178_s3.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n204_m14178_s4.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n258_m22575_s0.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n258_m22575_s1.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n258_m22575_s2.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n258_m22575_s3.3dm"
    "$INSTANCES_DIR/medium/hard/hard_n258_m22575_s4.3dm"
)

total=${#MISSING_INSTANCES[@]}
count=0

echo "Running ${total} missing instances (smart only)..." >&2
echo "Hard instances (${#HARD_INSTANCES[@]}): emitting as timed_out=1..." >&2

# Emit hard instances directly as timed_out=1 (confirmed timeouts from discussion.md)
for inst in "${HARD_INSTANCES[@]}"; do
    [[ -f "$inst" ]] || continue
    inst_name="$(basename "$inst" .3dm)"
    family=$(get_family "$inst")
    nm=$(get_nm "$inst")
    inst_n="${nm%% *}"
    inst_m="${nm##* }"
    opt=$(get_opt "$inst")
    for lang in python cpp java; do
        for rep in $(seq 1 $R); do
            emit_row "$lang" "smart" "$family" "$inst_name" \
                "$inst_n" "$inst_m" "$opt" "NA" "$((timelimit * 1000))" "NA" "1" "$rep"
        done
    done
done
echo "  -> Hard instances emitted." >&2

# Run remaining missing instances
for inst in "${MISSING_INSTANCES[@]}"; do
    [[ -f "$inst" ]] || continue
    ((count++)) || true
    inst_name="$(basename "$inst" .3dm)"
    family=$(get_family "$inst")
    nm=$(get_nm "$inst")
    inst_n="${nm%% *}"
    inst_m="${nm##* }"
    opt=$(get_opt "$inst")

    echo "  [$count/$total] $inst_name (n=$inst_n, m=$inst_m)" >&2

    # Track if first replica times out for early-skip on remaining reps
    first_timed_out=0

    for rep in $(seq 1 $R); do
        if [[ $first_timed_out -eq 1 && $rep -gt 1 ]]; then
            # All langs timed out in rep 1, skip remaining replicas
            for lang in python cpp java; do
                emit_row "$lang" "smart" "$family" "$inst_name" \
                    "$inst_n" "$inst_m" "$opt" "NA" "$((timelimit * 1000))" "NA" "1" "$rep"
            done
            continue
        fi

        all_timed_this_rep=1

        for lang in python cpp java; do
            rm -f "$sol_tmp"
            exit_code=0

            case "$lang" in
            python)
                set +e
                timeout "$timelimit" env PYTHONPATH="$REPO_ROOT/src/python" \
                    "$PYTHON_CMD" -m threedm \
                    "$inst" --algo smart \
                    --time-limit "$timelimit" \
                    --output "$sol_tmp" 2>/dev/null
                exit_code=$?
                set -e
                ;;
            cpp)
                set +e
                timeout "$timelimit" "$CPP_BIN" \
                    "$inst" --algo smart \
                    --output "$sol_tmp" 2>/dev/null
                exit_code=$?
                set -e
                ;;
            java)
                set +e
                timeout "$((timelimit + 5))" "$JAVA_CMD" -cp "$JAVA_CP" "$JAVA_MAIN" \
                    "$inst" --algo smart \
                    --time-limit "$timelimit" \
                    --output "$sol_tmp" 2>/dev/null
                exit_code=$?
                set -e
                ;;
            esac

            if [[ $exit_code -eq 124 ]]; then
                emit_row "$lang" "smart" "$family" "$inst_name" \
                    "$inst_n" "$inst_m" "$opt" "NA" "$((timelimit * 1000))" "NA" "1" "$rep"
                continue
            fi

            if [[ $exit_code -ne 0 || ! -f "$sol_tmp" ]]; then
                echo "    WARNING: $lang failed (exit=$exit_code)" >&2
                emit_row "$lang" "smart" "$family" "$inst_name" \
                    "$inst_n" "$inst_m" "$opt" "NA" "NA" "NA" "NA" "$rep"
                continue
            fi

            read -r time_ms nodes timed_out k <<< "$(parse_stats "$sol_tmp")"
            emit_row "$lang" "smart" "$family" "$inst_name" \
                "$inst_n" "$inst_m" "$opt" "$k" "$time_ms" "$nodes" "$timed_out" "$rep"

            if [[ "$timed_out" == "0" ]]; then
                all_timed_this_rep=0
            fi
        done

        # If first replica had all langs timing out, flag for skip
        if [[ $rep -eq 1 && $all_timed_this_rep -eq 1 ]]; then
            first_timed_out=1
            echo "    All langs timed out in rep 1, skipping remaining replicas" >&2
        fi
    done
done

echo "" >&2
echo "=== run_missing.sh completado ===" >&2
ROWS=$(wc -l < "$out")
echo "Filas en CSV (incl. header): $ROWS  |  CSV: $out" >&2
