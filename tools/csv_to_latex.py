#!/usr/bin/env python3
"""Convert CSVs in results/tables/ to .tex files in report/tablas/."""
import csv
import os

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, "..")
TABLE_DIR = os.path.join(ROOT, "results", "tables")
OUT_DIR = os.path.join(ROOT, "report", "tablas")
os.makedirs(OUT_DIR, exist_ok=True)


def _escape(s):
    return str(s).replace("_", r"\_").replace("%", r"\%").replace("&", r"\&")


def write_table(rows, headers, out_path, caption, label):
    col_n = len(headers)
    col_spec = "l" * col_n
    with open(out_path, "w") as f:
        f.write("\\begin{table}[htbp]\n")
        f.write("\\centering\n")
        f.write(f"\\caption{{{caption}}}\n")
        f.write(f"\\label{{{label}}}\n")
        f.write(f"\\begin{{tabular}}{{{col_spec}}}\n")
        f.write("\\toprule\n")
        f.write(" & ".join(_escape(h) for h in headers) + " \\\\\n")
        f.write("\\midrule\n")
        for row in rows:
            f.write(" & ".join(_escape(v) for v in row) + " \\\\\n")
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")


# --- summary_by_n.csv ---
rows_n = []
with open(os.path.join(TABLE_DIR, "summary_by_n.csv")) as fh:
    reader = csv.DictReader(fh)
    for row in reader:
        rows_n.append([row["lang"], row["algo"], row["n"],
                       row["time_ms_median"], row["n_instances"]])

write_table(
    rows_n,
    ["Lenguaje", "Algoritmo", "n", "Tiempo mediana (ms)", "Instancias"],
    os.path.join(OUT_DIR, "summary_by_n.tex"),
    "Tiempo de ejecuci\\'on mediano por tama\\~no de instancia (\\textit{small suite})",
    "tab:summary_by_n",
)

# --- summary_by_family.csv ---
rows_f = []
with open(os.path.join(TABLE_DIR, "summary_by_family.csv")) as fh:
    reader = csv.DictReader(fh)
    for row in reader:
        rows_f.append([row["lang"], row["algo"], row["family"],
                       row["time_ms_median"], row["n_instances"]])

write_table(
    rows_f,
    ["Lenguaje", "Algoritmo", "Familia", "Tiempo mediana (ms)", "Instancias"],
    os.path.join(OUT_DIR, "summary_by_family.tex"),
    "Tiempo de ejecuci\\'on mediano por familia de instancia",
    "tab:summary_by_family",
)

# --- correctness.csv (solo regression instances) ---
rows_c = []
REGRESSION = {"mini1", "mini2", "noperf", "dense", "empty"}
with open(os.path.join(TABLE_DIR, "correctness.csv")) as fh:
    reader = csv.DictReader(fh)
    for row in reader:
        if row["instance"] in REGRESSION:
            rows_c.append([
                row["instance"],
                row["n"], row["m"], row["opt"],
                row["all_agree"],
                row.get("python_smart_k", ""),
                row.get("cpp_smart_k", ""),
                row.get("java_smart_k", ""),
            ])

write_table(
    rows_c,
    ["Instancia", "n", "m", "OPT esperado", "Acuerdo", "Py-smart", "C++-smart", "Java-smart"],
    os.path.join(OUT_DIR, "correctness.tex"),
    "Verificaci\\'on de correctitud --- instancias de regresi\\'on",
    "tab:correctness",
)

print("Tables written to", OUT_DIR)
