#!/usr/bin/env bash
# reproduce.sh — Script de reproducibilidad para la fase 8.
#
# Ejecuta toda la pipeline desde generación de instancias hasta gráficos.
# Uso desde la raíz del repo:
#   bash tools/reproduce.sh
#
# Parámetros opcionales (exportar antes de invocar o editar los defaults):
#   SEED=42        semilla del generador
#   TL_SMALL=30    time-limit en segundos para small
#   TL_MEDIUM=60   time-limit en segundos para medium
#
# El script asume que los binarios C++ y Java ya están compilados.
# Para compilar: make -C src/cpp && bash src/java/build.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

SEED="${SEED:-42}"
TL_SMALL="${TL_SMALL:-30}"
TL_MEDIUM="${TL_MEDIUM:-60}"

echo "=== Reproducibilidad 3DM ==="
echo "Repo: $REPO_ROOT"
echo "Semilla: $SEED  |  TL small: ${TL_SMALL}s  |  TL medium: ${TL_MEDIUM}s"
echo ""

# 1. Generar instancias
echo "--- Paso 1: Generación de instancias (seed=$SEED) ---"
python tools/generator.py --family all --seed "$SEED" --out instances/
echo ""

# 2. Benchmarks small
echo "--- Paso 2: Benchmarks small (TL=${TL_SMALL}s) ---"
bash tools/run_benchmarks.sh small "$TL_SMALL"
echo ""

# 3. Benchmarks medium
echo "--- Paso 3: Benchmarks medium (TL=${TL_MEDIUM}s) ---"
bash tools/run_benchmarks.sh medium "$TL_MEDIUM"
echo ""

# 4. Análisis
echo "--- Paso 4: Análisis ---"
python tools/analyze.py results/raw/*.csv
echo ""

# 5. Gráficos
echo "--- Paso 5: Gráficos ---"
python tools/plot_results.py results/raw/*.csv
echo ""

echo "=== Pipeline completada ==="
echo "Resultados en:"
echo "  results/raw/       : CSVs crudos"
echo "  results/tables/    : tablas de resumen"
echo "  results/plots/     : gráficos PNG"
