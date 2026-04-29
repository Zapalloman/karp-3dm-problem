#!/usr/bin/env bash
# run_benchmarks.sh — Corre los 6 binarios sobre la suite y emite CSV crudo.
#
# Uso:
#   bash tools/run_benchmarks.sh [suite] [time_limit_s]
#
# Argumentos:
#   suite       : small | medium | large (default: small)
#   time_limit  : segundos de límite por corrida (default: 30)
#
# Salida:
#   results/raw/run_YYYYMMDD_HHMMSS.csv
#
# Header CSV exacto (fase 8):
#   lang,algo,family,instance,n,m,opt,k,time_ms,nodes,timed_out,replica
#
# DECISIONES DE IMPLEMENTACIÓN:
#   - R=3 réplicas; se reporta la mediana al final (analyze.py).
#   - El CSV crudo tiene TODAS las réplicas (una fila por réplica).
#   - C++ NO usa --time-limit (bug conocido bajo -O2 con condition_variable).
#     En su lugar se usa `timeout TL ./3dm ...` a nivel bash. Si exit=124,
#     se marca timed_out=1 en el CSV.
#   - Python y Java SÍ usan --time-limit (se implementó correctamente en
#     sus runtimes: Python threading, Java daemon thread).
#   - Brute solo se corre en small/. Para medium y large, solo smart.
#     Excepción: --all-algos para forzar ambos en todos los tamaños.
#   - Si primera réplica timed_out=1 para brute, las restantes también
#     van a timeoutar; se emiten directamente como timed_out=1 sin correr
#     para ahorrar tiempo.
#
# NOTA: el directorio de trabajo debe ser la raíz del repo.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="$REPO_ROOT/tools"
INSTANCES_DIR="$REPO_ROOT/instances"
RESULTS_DIR="$REPO_ROOT/results/raw"

suite="${1:-small}"
timelimit="${2:-30}"
R=3          # réplicas
PROGRESS_N=5 # imprimir progreso cada N instancias

# Timestamp para nombre de salida
ts="$(date +%Y%m%d_%H%M%S)"
out="$RESULTS_DIR/run_${ts}.csv"

mkdir -p "$RESULTS_DIR"

echo "lang,algo,family,instance,n,m,opt,k,time_ms,nodes,timed_out,replica" > "$out"
echo "=== run_benchmarks.sh: suite=$suite time_limit=${timelimit}s R=${R} ===" >&2
echo "Salida: $out" >&2
echo "" >&2

# ---------------------------------------------------------------------------
# Binarios y rutas
# ---------------------------------------------------------------------------

PYTHON_CMD=""
for p in python python3 /usr/bin/python /usr/bin/python3; do
    if command -v "$p" &>/dev/null; then
        PYTHON_CMD="$p"
        break
    fi
done

CPP_BIN="$REPO_ROOT/src/cpp/3dm"

JAVA_CMD=""
for j in java \
    "/home/javier/.vscode/extensions/redhat.java-1.54.0-linux-x64/jre/21.0.10-linux-x86_64/bin/java" \
    "/home/javier/.antigravity/extensions/redhat.java-1.54.0-linux-x64/jre/21.0.10-linux-x86_64/bin/java"; do
    if command -v "$j" &>/dev/null 2>&1 || [[ -x "$j" ]]; then
        JAVA_CMD="$j"
        break
    fi
done

JAVA_CP="$REPO_ROOT/src/java/build"
JAVA_MAIN="com.threedm.Main"

# ---------------------------------------------------------------------------
# Comprobación de binarios disponibles
# ---------------------------------------------------------------------------

PYTHON_OK=0
CPP_OK=0
JAVA_OK=0

if [[ -n "$PYTHON_CMD" ]] && PYTHONPATH="$REPO_ROOT/src/python" "$PYTHON_CMD" -c "import threedm" 2>/dev/null; then
    PYTHON_OK=1
    echo "INFO: Python OK ($PYTHON_CMD)" >&2
else
    echo "WARNING: Python threedm no disponible. Instalar: pip install -e $REPO_ROOT/src/python" >&2
fi

if [[ -x "$CPP_BIN" ]]; then
    CPP_OK=1
    echo "INFO: C++ OK ($CPP_BIN)" >&2
else
    echo "WARNING: C++ binario no encontrado en $CPP_BIN. Compilar: make -C $REPO_ROOT/src/cpp" >&2
fi

if [[ -n "$JAVA_CMD" ]] && [[ -d "$JAVA_CP" ]]; then
    JAVA_OK=1
    echo "INFO: Java OK ($JAVA_CMD -cp $JAVA_CP)" >&2
else
    echo "WARNING: Java no disponible. Compilar: bash $REPO_ROOT/src/java/build.sh" >&2
fi

if [[ $PYTHON_OK -eq 0 && $CPP_OK -eq 0 && $JAVA_OK -eq 0 ]]; then
    echo "ERROR: Ningún binario disponible." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# parse_stats <solution_file>
# Extrae time_ms, nodes, timed_out, k del archivo de solución.
# Imprime: time_ms nodes timed_out k  (separados por espacios)
parse_stats() {
    local solfile="$1"
    local time_ms="NA"
    local nodes="NA"
    local timed_out="0"
    local k="NA"

    [[ -f "$solfile" ]] || { echo "$time_ms $nodes $timed_out $k"; return; }

    # Leer k: primera línea no-comentario, no-vacía
    while IFS= read -r line; do
        local ls="${line#"${line%%[![:space:]]*}"}"
        [[ -z "$ls" || "$ls" == \#* ]] && continue
        k="$ls"
        break
    done < "$solfile"

    # Parsear stats line
    local stats_line
    stats_line=$(grep -m1 '^# stats:' "$solfile" 2>/dev/null || true)
    if [[ -n "$stats_line" ]]; then
        [[ "$stats_line" =~ time_ms=([0-9.]+) ]]  && time_ms="${BASH_REMATCH[1]}"
        [[ "$stats_line" =~ nodes=([0-9]+) ]]      && nodes="${BASH_REMATCH[1]}"
        [[ "$stats_line" =~ timed_out=1 ]]         && timed_out="1"
    fi

    echo "$time_ms $nodes $timed_out $k"
}

# get_opt <instance_file>
get_opt() {
    local opt
    opt=$(grep -m1 '^# opt=' "$1" 2>/dev/null | sed 's/^# opt=//' || true)
    echo "${opt:-NA}"
}

# get_nm <instance_file>  → "n m"
get_nm() {
    while IFS= read -r line; do
        local ls="${line#"${line%%[![:space:]]*}"}"
        [[ -z "$ls" || "$ls" == \#* ]] && continue
        echo "$ls"; return
    done < "$1"
}

# get_family <instance_file>
get_family() {
    local fam
    fam=$(grep -m1 '^# family=' "$1" 2>/dev/null | sed 's/^# family=//' || true)
    # Fallback: parse from path
    if [[ -z "$fam" ]]; then
        fam=$(basename "$(dirname "$1")")
    fi
    echo "$fam"
}

# emit_row <lang> <algo> <family> <instance_name> <n> <m> <opt> <k> <time_ms> <nodes> <timed_out> <replica>
emit_row() {
    echo "$1,$2,$3,$4,$5,$6,$7,$8,$9,${10},${11},${12}" >> "$out"
}

# run_one <lang> <algo> <family> <inst_name> <n> <m> <opt> <inst_path> <replica>
# Corre el solver y emite una fila en el CSV.
run_one() {
    local lang="$1" algo="$2" family="$3" inst_name="$4"
    local n="$5" m="$6" opt="$7" inst="$8" rep="$9"
    local sol_tmp="$10"  # archivo temporal para la solución

    rm -f "$sol_tmp"

    local exit_code=0
    local timed_out_row=0

    case "$lang" in
    python)
        set +e
        timeout "$timelimit" env PYTHONPATH="$REPO_ROOT/src/python" \
            "$PYTHON_CMD" -m threedm \
            "$inst" --algo "$algo" \
            --time-limit "$timelimit" \
            --output "$sol_tmp" 2>/dev/null
        exit_code=$?
        set -e
        ;;
    cpp)
        # C++ NO usa --time-limit (bug bajo -O2). Usamos bash timeout.
        set +e
        timeout "$timelimit" "$CPP_BIN" \
            "$inst" --algo "$algo" \
            --output "$sol_tmp" 2>/dev/null
        exit_code=$?
        set -e
        ;;
    java)
        set +e
        timeout "$((timelimit + 5))" "$JAVA_CMD" -cp "$JAVA_CP" "$JAVA_MAIN" \
            "$inst" --algo "$algo" \
            --time-limit "$timelimit" \
            --output "$sol_tmp" 2>/dev/null
        exit_code=$?
        set -e
        ;;
    esac

    # Detectar timeout: exit 124 = bash timeout; exit 0 = completó
    if [[ $exit_code -eq 124 ]]; then
        timed_out_row=1
        # Sin archivo de salida -> reportar NA para k, nodes; time ≈ timelimit
        emit_row "$lang" "$algo" "$family" "$inst_name" \
            "$n" "$m" "$opt" "NA" "$((timelimit * 1000))" "NA" "1" "$rep"
        return
    fi

    if [[ $exit_code -ne 0 ]]; then
        echo "  WARNING: $lang $algo falló en $inst_name (exit=$exit_code)" >&2
        emit_row "$lang" "$algo" "$family" "$inst_name" \
            "$n" "$m" "$opt" "NA" "NA" "NA" "NA" "$rep"
        return
    fi

    if [[ ! -f "$sol_tmp" ]]; then
        echo "  WARNING: $lang $algo no generó solución para $inst_name" >&2
        emit_row "$lang" "$algo" "$family" "$inst_name" \
            "$n" "$m" "$opt" "NA" "NA" "NA" "NA" "$rep"
        return
    fi

    read -r time_ms nodes timed_out k <<< "$(parse_stats "$sol_tmp")"
    emit_row "$lang" "$algo" "$family" "$inst_name" \
        "$n" "$m" "$opt" "$k" "$time_ms" "$nodes" "$timed_out" "$rep"
}

# ---------------------------------------------------------------------------
# Bucle principal
# ---------------------------------------------------------------------------

total_instances=0
inst_count=0

shopt -s globstar nullglob 2>/dev/null || true
sol_tmp=$(mktemp /tmp/3dm_sol_XXXXXX.txt)
trap 'rm -f "$sol_tmp"' EXIT

# Familias a omitir (separadas por espacio). Ej: SKIP_FAMILIES="hard" bash run_benchmarks.sh medium 60
SKIP_FAMILIES="${SKIP_FAMILIES:-}"

for inst in "$INSTANCES_DIR/$suite"/**/*.3dm; do
    [[ -f "$inst" ]] || continue
    # Verificar si esta instancia pertenece a una familia omitida
    if [[ -n "$SKIP_FAMILIES" ]]; then
        inst_fam=$(grep -m1 '^# family=' "$inst" 2>/dev/null | sed 's/^# family=//' || basename "$(dirname "$inst")")
        skip=0
        for sf in $SKIP_FAMILIES; do
            [[ "$inst_fam" == "$sf" || "$(basename "$(dirname "$inst")")" == "$sf" ]] && skip=1 && break
        done
        [[ $skip -eq 1 ]] && continue
    fi
    ((total_instances++)) || true
done

echo "Instancias encontradas en $suite/: $total_instances" >&2
[[ -n "$SKIP_FAMILIES" ]] && echo "  (SKIP_FAMILIES=$SKIP_FAMILIES)" >&2

for inst in "$INSTANCES_DIR/$suite"/**/*.3dm; do
    [[ -f "$inst" ]] || continue

    inst_name="$(basename "$inst" .3dm)"
    family=$(get_family "$inst")
    nm=$(get_nm "$inst")
    inst_n="${nm%% *}"
    inst_m="${nm##* }"
    opt=$(get_opt "$inst")

    # Omitir si la familia está en SKIP_FAMILIES
    if [[ -n "$SKIP_FAMILIES" ]]; then
        skip=0
        for sf in $SKIP_FAMILIES; do
            [[ "$family" == "$sf" || "$(basename "$(dirname "$inst")")" == "$sf" ]] && skip=1 && break
        done
        [[ $skip -eq 1 ]] && continue
    fi

    ((inst_count++)) || true

    if (( inst_count % PROGRESS_N == 0 )); then
        echo "  Progreso: $inst_count / $total_instances  [último: $inst_name]" >&2
    fi

    # Determinar qué algoritmos correr según suite y familia
    # - Brute: solo en small/ (y en medium si es familia regression o tiny)
    # - En large: solo smart
    algos=("smart")
    if [[ "$suite" == "small" ]]; then
        algos=("brute" "smart")
    fi

    for algo in "${algos[@]}"; do
        # Track si brute timedout en réplica 1 para ahorrar tiempo
        brute_timed_out=0

        for rep in $(seq 1 "$R"); do
            # Si brute ya timedout en rep=1, las siguientes son iguales
            if [[ "$algo" == "brute" && $brute_timed_out -eq 1 && $rep -gt 1 ]]; then
                # Emitir directamente como timed_out=1 para cada lang
                for lang in python cpp java; do
                    [[ "$lang" == "python" && $PYTHON_OK -eq 0 ]] && continue
                    [[ "$lang" == "cpp"    && $CPP_OK -eq 0    ]] && continue
                    [[ "$lang" == "java"   && $JAVA_OK -eq 0   ]] && continue
                    emit_row "$lang" "$algo" "$family" "$inst_name" \
                        "$inst_n" "$inst_m" "$opt" "NA" "$((timelimit * 1000))" "NA" "1" "$rep"
                done
                continue
            fi

            all_timed_out=1

            for lang in python cpp java; do
                [[ "$lang" == "python" && $PYTHON_OK -eq 0 ]] && continue
                [[ "$lang" == "cpp"    && $CPP_OK -eq 0    ]] && continue
                [[ "$lang" == "java"   && $JAVA_OK -eq 0   ]] && continue

                run_one "$lang" "$algo" "$family" "$inst_name" \
                    "$inst_n" "$inst_m" "$opt" "$inst" "$rep" "$sol_tmp"

                # Leer si esta corrida timedout (para brute early-exit logic)
                if [[ $algo == "brute" && $rep -eq 1 ]]; then
                    # Leer última línea del CSV
                    last_row=$(tail -1 "$out")
                    timed_col=$(echo "$last_row" | cut -d',' -f11)
                    if [[ "$timed_col" == "0" || "$timed_col" == "NA" ]]; then
                        all_timed_out=0
                    fi
                fi
            done

            # Si todas las langs timedout en rep=1 con brute, marcar para skip
            if [[ "$algo" == "brute" && $rep -eq 1 && $all_timed_out -eq 1 ]]; then
                brute_timed_out=1
            fi
        done
    done
done

echo "" >&2
echo "=== Benchmarks completados ===" >&2
echo "Instancias: $inst_count  |  CSV: $out" >&2
ROWS=$(wc -l < "$out")
echo "Filas en CSV (incl. header): $ROWS" >&2
