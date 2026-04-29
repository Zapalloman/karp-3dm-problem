#!/usr/bin/env python3
"""
plot_results.py — Genera los 5 gráficos del análisis experimental 3DM.

Uso:
    python tools/plot_results.py results/raw/*.csv [--out results/plots]

Gráficos generados:
    scaling_lang.png        : tiempo vs n por (lang × algo), familia random, log-log
    brute_vs_smart.png      : speedup (time_brute / time_smart) por n, una línea por lang
    lang_comparison_bar.png : barras agrupadas por lang × algo para n fijo
    nodes_explored.png      : nodos explorados por algoritmo (escala log)
    timeouts_heatmap.png    : % de timeouts por (lang × algo × n)
"""

import argparse
import sys
from pathlib import Path
import csv
from collections import defaultdict
import statistics
import math

import matplotlib
matplotlib.use("Agg")  # no GUI
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


# ---------------------------------------------------------------------------
# Paleta de colores consistente
# ---------------------------------------------------------------------------
LANG_COLORS = {
    "python": "#3776ab",   # azul Python
    "cpp":    "#f34b7d",   # rosa/rojo C++
    "java":   "#b07219",   # marrón Java
}
ALGO_MARKERS = {
    "brute": "o",
    "smart": "s",
}
ALGO_LS = {
    "brute": "--",
    "smart": "-",
}
LANG_LABELS = {"python": "Python", "cpp": "C++", "java": "Java"}
ALGO_LABELS = {"brute": "BRUTE", "smart": "SMART"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_csvs(paths):
    rows = []
    for p in paths:
        with open(p, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    return rows


def pf(val, default=None):
    if val in ("NA", "", None):
        return default
    try:
        return float(val)
    except ValueError:
        return default


def pi(val, default=None):
    if val in ("NA", "", None):
        return default
    try:
        return int(val)
    except ValueError:
        return default


def aggregate(rows):
    """Agrega CSV crudo por mediana sobre réplicas. Retorna lista de dicts."""
    groups = defaultdict(list)
    meta = {}
    for row in rows:
        key = (row["lang"], row["algo"], row["family"], row["instance"])
        groups[key].append(row)
        if key not in meta:
            meta[key] = {
                "n": pi(row.get("n")),
                "m": pi(row.get("m")),
                "opt": pi(row.get("opt")),
            }

    result = []
    for key, reps in groups.items():
        lang, algo, family, instance = key
        times = [pf(r["time_ms"]) for r in reps if pf(r["time_ms"]) is not None]
        nodes_list = [pf(r["nodes"]) for r in reps if pf(r["nodes"]) is not None]
        ks = [pi(r["k"]) for r in reps if pi(r["k"]) is not None]
        timed_any = any(r.get("timed_out") == "1" for r in reps)

        info = meta[key]
        result.append({
            "lang": lang,
            "algo": algo,
            "family": family,
            "instance": instance,
            "n": info["n"],
            "m": info["m"],
            "opt": info["opt"],
            "k": statistics.median(ks) if ks else None,
            "time_ms": statistics.median(times) if times else None,
            "nodes": statistics.median(nodes_list) if nodes_list else None,
            "timed_out": 1 if timed_any else 0,
        })
    return result


def save_fig(fig, path, dpi=150):
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {path}")


# ---------------------------------------------------------------------------
# Plot 1: scaling_lang.png
# tiempo vs n, por (lang × algo), familia random, log-log
# ---------------------------------------------------------------------------
def plot_scaling_lang(agg, out_dir):
    # Filtrar: solo familia random, agrupar por (lang, algo, n)
    data = defaultdict(list)
    for r in agg:
        if r["family"] != "random":
            continue
        if r["time_ms"] is None or r["n"] is None:
            continue
        key = (r["lang"], r["algo"], r["n"])
        data[key].append(r["time_ms"])

    # Para cada (lang, algo): {n -> mediana de time_ms}
    curves = defaultdict(dict)
    for (lang, algo, n), times in data.items():
        curves[(lang, algo)][n] = statistics.median(times)

    if not curves:
        print("  WARNING: No hay datos para scaling_lang.png")
        return

    fig, ax = plt.subplots(figsize=(9, 6))

    for (lang, algo), n_dict in sorted(curves.items()):
        ns = sorted(n_dict.keys())
        ts = [n_dict[n] for n in ns]
        color = LANG_COLORS.get(lang, "gray")
        ls = ALGO_LS.get(algo, "-")
        marker = ALGO_MARKERS.get(algo, "o")
        label = f"{LANG_LABELS.get(lang, lang)} {ALGO_LABELS.get(algo, algo)}"
        ax.plot(ns, ts, ls=ls, marker=marker, color=color, label=label,
                linewidth=1.8, markersize=6)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("n (tamaño del problema)", fontsize=12)
    ax.set_ylabel("Tiempo [ms] (mediana)", fontsize=12)
    ax.set_title("Escalabilidad: tiempo vs n (familia random)", fontsize=13)
    ax.legend(fontsize=9, ncol=2)
    ax.grid(True, which="both", alpha=0.3)

    save_fig(fig, out_dir / "scaling_lang.png")


# ---------------------------------------------------------------------------
# Plot 2: brute_vs_smart.png
# speedup (time_brute / time_smart) por n, una línea por lenguaje
# ---------------------------------------------------------------------------
def plot_brute_vs_smart(agg, out_dir):
    # Para cada (lang, family, instance): obtener time_brute y time_smart
    by_instance = defaultdict(dict)
    for r in agg:
        if r["time_ms"] is None or r["n"] is None:
            continue
        key = (r["lang"], r["family"], r["instance"], r["n"])
        by_instance[key][r["algo"]] = r["time_ms"]

    # Calcular speedup por (lang, n)
    speedups = defaultdict(list)
    for (lang, family, instance, n), algos in by_instance.items():
        if "brute" in algos and "smart" in algos and algos["smart"] > 0:
            speedup = algos["brute"] / algos["smart"]
            speedups[(lang, n)].append(speedup)

    if not speedups:
        print("  WARNING: No hay datos para brute_vs_smart.png")
        return

    # Para cada (lang, n): mediana de speedups
    curves = defaultdict(dict)
    for (lang, n), slist in speedups.items():
        curves[lang][n] = statistics.median(slist)

    fig, ax = plt.subplots(figsize=(9, 6))

    for lang, n_dict in sorted(curves.items()):
        ns = sorted(n_dict.keys())
        ss = [n_dict[n] for n in ns]
        color = LANG_COLORS.get(lang, "gray")
        label = LANG_LABELS.get(lang, lang)
        ax.plot(ns, ss, marker="o", color=color, label=label,
                linewidth=1.8, markersize=6)

    ax.set_xlabel("n (tamaño del problema)", fontsize=12)
    ax.set_ylabel("Speedup BRUTE / SMART (mediana)", fontsize=12)
    ax.set_title("Speedup: BRUTE vs SMART por lenguaje", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.axhline(1, color="gray", linestyle=":", linewidth=1)

    if any(s > 10 for nd in curves.values() for s in nd.values()):
        ax.set_yscale("log")

    save_fig(fig, out_dir / "brute_vs_smart.png")


# ---------------------------------------------------------------------------
# Plot 3: lang_comparison_bar.png
# Para un n fijo, barras agrupadas por lang × algo
# ---------------------------------------------------------------------------
def plot_lang_comparison_bar(agg, out_dir):
    # Encontrar el n con más datos, preferir n cercano a 20 o 30
    n_counts = defaultdict(int)
    for r in agg:
        if r["n"] is not None and r["time_ms"] is not None:
            n_counts[r["n"]] += 1

    if not n_counts:
        print("  WARNING: No hay datos para lang_comparison_bar.png")
        return

    # Preferir n=20 si existe, luego 10, luego el más frecuente
    preferred = [20, 10, 30, 50]
    target_n = None
    for pn in preferred:
        if pn in n_counts and n_counts[pn] > 0:
            target_n = pn
            break
    if target_n is None:
        target_n = max(n_counts, key=n_counts.get)

    # Obtener datos para n=target_n
    # Para cada (lang, algo): mediana de time_ms sobre instancias con ese n
    data = defaultdict(list)
    for r in agg:
        if r["n"] != target_n or r["time_ms"] is None:
            continue
        data[(r["lang"], r["algo"])].append(r["time_ms"])

    if not data:
        print(f"  WARNING: No hay datos para n={target_n} en lang_comparison_bar.png")
        return

    langs = ["python", "cpp", "java"]
    algos = ["brute", "smart"]
    x = np.arange(len(langs))
    width = 0.35

    fig, ax = plt.subplots(figsize=(9, 6))

    for i, algo in enumerate(algos):
        times = []
        for lang in langs:
            t = data.get((lang, algo))
            times.append(statistics.median(t) if t else 0)
        offset = (i - 0.5) * width
        bars = ax.bar(x + offset, times, width,
                      label=ALGO_LABELS.get(algo, algo),
                      alpha=0.85,
                      color=[LANG_COLORS.get(l, "gray") for l in langs],
                      edgecolor="black", linewidth=0.5,
                      hatch="///" if algo == "brute" else "")
        # Valores encima de barras
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h,
                        f"{h:.1f}", ha="center", va="bottom", fontsize=7)

    ax.set_yscale("log")
    ax.set_xlabel("Lenguaje", fontsize=12)
    ax.set_ylabel("Tiempo [ms] (mediana, log)", fontsize=12)
    ax.set_title(f"Comparación de lenguajes (n={target_n})", fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels([LANG_LABELS.get(l, l) for l in langs], fontsize=11)
    ax.legend(fontsize=10)
    ax.grid(True, axis="y", alpha=0.3)

    save_fig(fig, out_dir / "lang_comparison_bar.png")


# ---------------------------------------------------------------------------
# Plot 4: nodes_explored.png
# nodos explorados por algoritmo (escala log)
# ---------------------------------------------------------------------------
def plot_nodes_explored(agg, out_dir):
    data = defaultdict(list)
    for r in agg:
        if r["nodes"] is None or r["n"] is None:
            continue
        key = (r["lang"], r["algo"], r["n"])
        data[key].append(r["nodes"])

    curves = defaultdict(dict)
    for (lang, algo, n), ns in data.items():
        curves[(lang, algo)][n] = statistics.median(ns)

    if not curves:
        print("  WARNING: No hay datos para nodes_explored.png")
        return

    fig, ax = plt.subplots(figsize=(9, 6))

    for (lang, algo), n_dict in sorted(curves.items()):
        ns = sorted(n_dict.keys())
        nds = [n_dict[n] for n in ns]
        color = LANG_COLORS.get(lang, "gray")
        ls = ALGO_LS.get(algo, "-")
        marker = ALGO_MARKERS.get(algo, "o")
        label = f"{LANG_LABELS.get(lang, lang)} {ALGO_LABELS.get(algo, algo)}"
        ax.plot(ns, nds, ls=ls, marker=marker, color=color, label=label,
                linewidth=1.8, markersize=6)

    ax.set_yscale("log")
    ax.set_xlabel("n (tamaño del problema)", fontsize=12)
    ax.set_ylabel("Nodos explorados (mediana, log)", fontsize=12)
    ax.set_title("Nodos explorados por algoritmo", fontsize=13)
    ax.legend(fontsize=9, ncol=2)
    ax.grid(True, which="both", alpha=0.3)

    save_fig(fig, out_dir / "nodes_explored.png")


# ---------------------------------------------------------------------------
# Plot 5: timeouts_heatmap.png
# % de timeouts por (lang × algo × n)
# ---------------------------------------------------------------------------
def plot_timeouts_heatmap(agg, out_dir):
    # Por (lang, algo, n): contar instancias y timeouts
    counts = defaultdict(lambda: {"total": 0, "timed_out": 0})
    for r in agg:
        if r["n"] is None:
            continue
        key = (r["lang"], r["algo"], r["n"])
        counts[key]["total"] += 1
        if r["timed_out"]:
            counts[key]["timed_out"] += 1

    if not counts:
        print("  WARNING: No hay datos para timeouts_heatmap.png")
        return

    # Construir matriz: filas = (lang, algo), columnas = n
    lang_algos = sorted(set((k[0], k[1]) for k in counts))
    ns = sorted(set(k[2] for k in counts))

    matrix = np.full((len(lang_algos), len(ns)), np.nan)
    for i, (lang, algo) in enumerate(lang_algos):
        for j, n in enumerate(ns):
            key = (lang, algo, n)
            if key in counts and counts[key]["total"] > 0:
                pct = 100.0 * counts[key]["timed_out"] / counts[key]["total"]
                matrix[i, j] = pct

    fig, ax = plt.subplots(figsize=(max(8, len(ns) * 0.8), max(4, len(lang_algos) * 0.6)))

    cmap = matplotlib.cm.YlOrRd
    cmap.set_bad("lightgray")
    im = ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=0, vmax=100)
    plt.colorbar(im, ax=ax, label="% timeouts")

    ax.set_xticks(range(len(ns)))
    ax.set_xticklabels([str(n) for n in ns], rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(lang_algos)))
    ax.set_yticklabels(
        [f"{LANG_LABELS.get(la[0], la[0])} {ALGO_LABELS.get(la[1], la[1])}"
         for la in lang_algos],
        fontsize=9)

    # Anotar valores en celdas
    for i in range(len(lang_algos)):
        for j in range(len(ns)):
            val = matrix[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.0f}%", ha="center", va="center",
                        fontsize=7, color="black" if val < 70 else "white")

    ax.set_title("Porcentaje de timeouts por (solver × n)", fontsize=12)
    ax.set_xlabel("n", fontsize=11)

    save_fig(fig, out_dir / "timeouts_heatmap.png")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Genera gráficos de benchmarks 3DM")
    parser.add_argument("csvs", nargs="+", help="Archivos CSV crudos")
    parser.add_argument("--out", default="results/plots",
                        help="Directorio de salida (default: results/plots)")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Cargando {len(args.csvs)} CSV(s)...")
    rows = load_csvs(args.csvs)
    print(f"  Filas: {len(rows)}")

    print("Calculando medianas...")
    agg = aggregate(rows)
    print(f"  Agregadas: {len(agg)} combinaciones")

    print("Generando gráficos...")
    plot_scaling_lang(agg, out_dir)
    plot_brute_vs_smart(agg, out_dir)
    plot_lang_comparison_bar(agg, out_dir)
    plot_nodes_explored(agg, out_dir)
    plot_timeouts_heatmap(agg, out_dir)

    print("\nGráficos completados.")


if __name__ == "__main__":
    main()
