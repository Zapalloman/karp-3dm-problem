#!/usr/bin/env python3
"""
analyze.py — Analiza los CSVs crudos de run_benchmarks.sh y produce tablas.

Uso:
    python tools/analyze.py results/raw/*.csv [--out results/tables]

Salida en results/tables/:
    summary_by_family.csv   : tiempo mediana por (lang, algo, family)
    summary_by_n.csv        : escalabilidad: tiempo vs n por (lang, algo)
    correctness.csv         : por instancia, coinciden los 6 k? (bool)
"""

import argparse
import sys
from pathlib import Path
import csv
from collections import defaultdict
import statistics
import math


def load_csvs(paths):
    """Lee uno o varios CSV crudos y retorna lista de dicts."""
    rows = []
    for p in paths:
        with open(p, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    return rows


def parse_num(val, default=None):
    """Convierte string a float; retorna default si es NA o vacío."""
    if val in ("NA", "", None):
        return default
    try:
        return float(val)
    except ValueError:
        return default


def parse_int(val, default=None):
    """Convierte string a int; retorna default si es NA o vacío."""
    if val in ("NA", "", None):
        return default
    try:
        return int(val)
    except ValueError:
        return default


def compute_median_rows(rows):
    """
    Agrega por mediana sobre réplicas.
    Retorna lista de dicts con columnas: lang,algo,family,instance,n,m,opt,
    k_median,time_ms_median,nodes_median,timed_out_any.
    """
    # Agrupar por (lang, algo, family, instance)
    groups = defaultdict(list)
    meta = {}  # guarda n, m, opt para cada grupo
    for row in rows:
        key = (row["lang"], row["algo"], row["family"], row["instance"])
        groups[key].append(row)
        if key not in meta:
            meta[key] = {
                "n": parse_int(row.get("n")),
                "m": parse_int(row.get("m")),
                "opt": parse_int(row.get("opt")),
            }

    result = []
    for key, reps in groups.items():
        lang, algo, family, instance = key
        times = [parse_num(r["time_ms"]) for r in reps if parse_num(r["time_ms"]) is not None]
        nodes_list = [parse_num(r["nodes"]) for r in reps if parse_num(r["nodes"]) is not None]
        ks = [parse_int(r["k"]) for r in reps if parse_int(r["k"]) is not None]
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
            "k_median": statistics.median(ks) if ks else None,
            "time_ms_median": statistics.median(times) if times else None,
            "nodes_median": statistics.median(nodes_list) if nodes_list else None,
            "timed_out_any": 1 if timed_any else 0,
            "n_replicas": len(reps),
        })
    return result


def write_summary_by_family(agg_rows, out_dir):
    """
    summary_by_family.csv: mediana de tiempo_ms por (lang, algo, family).
    """
    groups = defaultdict(list)
    for r in agg_rows:
        key = (r["lang"], r["algo"], r["family"])
        if r["time_ms_median"] is not None:
            groups[key].append(r["time_ms_median"])

    out_path = out_dir / "summary_by_family.csv"
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["lang", "algo", "family", "time_ms_median", "n_instances"])
        for key in sorted(groups):
            lang, algo, family = key
            times = groups[key]
            w.writerow([lang, algo, family,
                        f"{statistics.median(times):.3f}",
                        len(times)])
    print(f"  -> {out_path}  ({len(groups)} filas)")
    return out_path


def write_summary_by_n(agg_rows, out_dir):
    """
    summary_by_n.csv: escalabilidad: tiempo vs n por (lang, algo).
    Agrega instancias del mismo n tomando mediana de time_ms_median.
    """
    groups = defaultdict(list)
    for r in agg_rows:
        key = (r["lang"], r["algo"], r["n"])
        if r["time_ms_median"] is not None and r["n"] is not None:
            groups[key].append(r["time_ms_median"])

    out_path = out_dir / "summary_by_n.csv"
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["lang", "algo", "n", "time_ms_median", "n_instances"])
        for key in sorted(groups, key=lambda k: (k[0], k[1], k[2] or 0)):
            lang, algo, n = key
            times = groups[key]
            w.writerow([lang, algo, n,
                        f"{statistics.median(times):.3f}",
                        len(times)])
    print(f"  -> {out_path}  ({len(groups)} filas)")
    return out_path


def write_correctness(agg_rows, out_dir):
    """
    correctness.csv: por instancia, ¿coinciden los 6 k?
    Una discrepancia = bug (no timeout).
    """
    # Agrupar por (family, instance) -> dict de {lang_algo: k_median}
    inst_groups = defaultdict(dict)
    for r in agg_rows:
        inst_key = (r["family"], r["instance"])
        la_key = f"{r['lang']}_{r['algo']}"
        inst_groups[inst_key][la_key] = {
            "k": r["k_median"],
            "timed_out": r["timed_out_any"],
            "n": r["n"],
            "m": r["m"],
            "opt": r["opt"],
        }

    out_path = out_dir / "correctness.csv"
    discrepancies = 0
    total = 0

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["family", "instance", "n", "m", "opt",
                    "all_agree", "discrepancy_reason",
                    "python_brute_k", "python_smart_k",
                    "cpp_brute_k", "cpp_smart_k",
                    "java_brute_k", "java_smart_k"])

        for (family, instance) in sorted(inst_groups.keys()):
            info = inst_groups[(family, instance)]
            n = None
            m = None
            opt = None
            for d in info.values():
                if d["n"] is not None:
                    n = d["n"]
                    m = d["m"]
                    opt = d["opt"]
                    break

            ks = {}
            for key in ["python_brute", "python_smart", "cpp_brute", "cpp_smart",
                        "java_brute", "java_smart"]:
                d = info.get(key, {})
                ks[key] = d.get("k")

            # Check agreement: ignore None (timed_out or missing)
            valid_ks = [v for v in ks.values() if v is not None]
            unique_ks = set(valid_ks)

            # Which are timed out?
            timed_out_keys = [k for k, d in info.items() if d.get("timed_out")]

            all_agree = True
            reason = ""
            if len(unique_ks) > 1:
                # Check if disagreement is only due to timeouts
                non_timeout_ks = {
                    k: v for k, v in ks.items()
                    if v is not None and k not in timed_out_keys
                }
                non_timeout_unique = set(non_timeout_ks.values())
                if len(non_timeout_unique) > 1:
                    all_agree = False
                    reason = f"BUG: non-timeout ks differ: {non_timeout_unique}"
                    discrepancies += 1
                else:
                    reason = f"timeout on: {timed_out_keys}"
            elif len(unique_ks) == 0:
                reason = "all timed out or missing"

            total += 1
            w.writerow([
                family, instance, n, m, opt,
                "YES" if all_agree else "NO",
                reason,
                ks.get("python_brute", "NA"),
                ks.get("python_smart", "NA"),
                ks.get("cpp_brute", "NA"),
                ks.get("cpp_smart", "NA"),
                ks.get("java_brute", "NA"),
                ks.get("java_smart", "NA"),
            ])

    print(f"  -> {out_path}  ({total} instancias, {discrepancies} discrepancias BUG)")
    if discrepancies > 0:
        print("  *** ADVERTENCIA: hay discrepancias que no son por timeout. "
              "Posible bug en alguna implementación. ***")
    return out_path, discrepancies


def main():
    parser = argparse.ArgumentParser(description="Analiza CSVs de benchmarks 3DM")
    parser.add_argument("csvs", nargs="+", help="Archivos CSV crudos")
    parser.add_argument("--out", default="results/tables",
                        help="Directorio de salida (default: results/tables)")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Cargando {len(args.csvs)} CSV(s)...")
    rows = load_csvs(args.csvs)
    print(f"  Filas cargadas: {len(rows)}")

    print("Calculando medianas por réplica...")
    agg = compute_median_rows(rows)
    print(f"  Filas agregadas (por instancia×solver): {len(agg)}")

    print("Generando tablas...")
    write_summary_by_family(agg, out_dir)
    write_summary_by_n(agg, out_dir)
    _, discrepancies = write_correctness(agg, out_dir)

    print("\nAnálisis completado.")
    if discrepancies > 0:
        print(f"ACCION REQUERIDA: {discrepancies} discrepancias de bug encontradas.")
        print("Revisar correctness.csv y las implementaciones afectadas.")
        sys.exit(2)
    else:
        print("Correctness OK: todas las discrepancias son por timeout.")
        sys.exit(0)


if __name__ == "__main__":
    main()
