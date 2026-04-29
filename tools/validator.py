#!/usr/bin/env python3
"""
validator.py — Validador de soluciones 3DM.

Uso:
    python tools/validator.py <instance.3dm> <solution.txt>

Verifica:
    1. Parseo: los archivos son legibles y tienen el formato correcto.
    2. Índices válidos: cada índice está en [1, m] (1-based).
    3. Índices distintos: no hay duplicados en la solución.
    4. Sin colisiones en X: dos tripletas del matching no comparten x.
    5. Sin colisiones en Y: ídem para y.
    6. Sin colisiones en Z: ídem para z.
    7. Opt check: si la instancia tiene # opt=K, verifica k <= K.

Formato de salida:
    PASS <check>
    FAIL <check>: <detalle>

Exit codes:
    0  — todos los checks pasan.
    1  — al menos un check falla.
    2  — error de parsing (archivo no encontrado o malformado).

No usa librerías que resuelvan 3DM; sólo parsing manual + chequeos de conjuntos.
"""

from __future__ import annotations

import sys
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Parser de instancia .3dm
# ---------------------------------------------------------------------------

class InstanceParseError(Exception):
    pass


def parse_instance(path: str) -> Tuple[int, int, List[Tuple[int, int, int]], Dict]:
    """Lee un archivo .3dm y retorna (n, m, triples, meta).

    meta puede contener 'opt', 'seed', 'family' si están en comentarios.
    Lanza InstanceParseError en caso de formato inválido.
    """
    try:
        with open(path, "r") as fh:
            raw = fh.read()
    except FileNotFoundError:
        raise InstanceParseError(f"Archivo no encontrado: {path}")

    meta: Dict = {}
    header_found = False
    n = m = 0
    triples: List[Tuple[int, int, int]] = []

    for lineno, line in enumerate(raw.splitlines(), start=1):
        line_stripped = line.strip()

        # Comentarios / metadatos
        if line_stripped.startswith("#"):
            content = line_stripped[1:].strip()
            # Parsear prefijos de metadato conocidos
            for key in ("opt", "seed", "family"):
                if content.startswith(f"{key}="):
                    try:
                        val = content[len(key) + 1:].split()[0]
                        meta[key] = int(val) if key in ("opt", "seed") else val
                    except (ValueError, IndexError):
                        pass
            # "# n=N  m=M  seed=S" (formato del generador)
            if content.startswith("n="):
                parts = content.split()
                for part in parts:
                    if "=" in part:
                        k_meta, v_meta = part.split("=", 1)
                        if k_meta in ("opt", "seed"):
                            try:
                                meta[k_meta] = int(v_meta)
                            except ValueError:
                                pass
            continue

        # Líneas en blanco
        if not line_stripped:
            continue

        # Primera línea no-comentario: encabezado "n m"
        if not header_found:
            parts = line_stripped.split()
            if len(parts) != 2:
                raise InstanceParseError(
                    f"Línea {lineno}: se esperaba 'n m', se encontró '{line_stripped}'"
                )
            try:
                n, m = int(parts[0]), int(parts[1])
            except ValueError:
                raise InstanceParseError(
                    f"Línea {lineno}: n y m deben ser enteros, se encontró '{line_stripped}'"
                )
            if n < 1:
                raise InstanceParseError(f"n debe ser >= 1, se encontró n={n}")
            if m < 0:
                raise InstanceParseError(f"m debe ser >= 0, se encontró m={m}")
            header_found = True
            continue

        # Tripletas
        parts = line_stripped.split()
        if len(parts) != 3:
            raise InstanceParseError(
                f"Línea {lineno}: se esperaba 'x y z', se encontró '{line_stripped}'"
            )
        try:
            x, y, z = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            raise InstanceParseError(
                f"Línea {lineno}: x, y, z deben ser enteros, se encontró '{line_stripped}'"
            )
        if not (0 <= x < n and 0 <= y < n and 0 <= z < n):
            raise InstanceParseError(
                f"Línea {lineno}: elementos ({x},{y},{z}) fuera de rango [0,{n})"
            )
        triples.append((x, y, z))

    if not header_found:
        raise InstanceParseError("Archivo vacío o sin encabezado n m")
    if len(triples) != m:
        raise InstanceParseError(
            f"Se declararon m={m} tripletas pero se encontraron {len(triples)}"
        )

    return n, m, triples, meta


# ---------------------------------------------------------------------------
# Parser de solución
# ---------------------------------------------------------------------------

class SolutionParseError(Exception):
    pass


def parse_solution(path: str) -> Tuple[int, List[int], Dict]:
    """Lee un archivo de solución y retorna (k, indices_1based, stats).

    Formato esperado (docs/INSTANCE_FORMAT.md):
        k
        i1
        i2
        ...
        ik
        # stats: time_ms=... nodes=... algo=... ...

    indices_1based son los índices tal como aparecen en el archivo (1-based).
    stats es un dict con los campos de la línea # stats.
    """
    try:
        with open(path, "r") as fh:
            raw = fh.read()
    except FileNotFoundError:
        raise SolutionParseError(f"Archivo no encontrado: {path}")

    lines = [ln.strip() for ln in raw.splitlines()]
    # Filtrar líneas vacías y de stats (preservar orden)
    data_lines = []
    stats: Dict = {}
    for line in lines:
        if not line:
            continue
        if line.startswith("# stats:"):
            # Parsear stats
            content = line[len("# stats:"):].strip()
            for part in content.split():
                if "=" in part:
                    k_s, v_s = part.split("=", 1)
                    stats[k_s] = v_s
            continue
        if line.startswith("#"):
            continue
        data_lines.append(line)

    if not data_lines:
        raise SolutionParseError("Solución vacía (sin línea k ni índices)")

    try:
        k = int(data_lines[0])
    except ValueError:
        raise SolutionParseError(
            f"Primera línea debe ser k (entero), se encontró '{data_lines[0]}'"
        )

    if k < 0:
        raise SolutionParseError(f"k debe ser >= 0, se encontró k={k}")

    if len(data_lines) - 1 != k:
        raise SolutionParseError(
            f"k={k} pero se encontraron {len(data_lines)-1} índices"
        )

    indices: List[int] = []
    for i, line in enumerate(data_lines[1:], start=1):
        try:
            idx = int(line)
        except ValueError:
            raise SolutionParseError(f"Índice {i}: se esperaba entero, se encontró '{line}'")
        indices.append(idx)

    return k, indices, stats


# ---------------------------------------------------------------------------
# Validación
# ---------------------------------------------------------------------------

def validate(instance_path: str, solution_path: str) -> bool:
    """Ejecuta todos los checks y retorna True si todos pasan."""
    all_pass = True

    # --- CHECK 0: Parseo de instancia ---
    try:
        n, m, triples, meta = parse_instance(instance_path)
        print(f"PASS parse_instance: n={n} m={m}")
    except InstanceParseError as e:
        print(f"FAIL parse_instance: {e}")
        return False

    # --- CHECK 1: Parseo de solución ---
    try:
        k, indices, stats = parse_solution(solution_path)
        print(f"PASS parse_solution: k={k}")
    except SolutionParseError as e:
        print(f"FAIL parse_solution: {e}")
        return False

    # --- CHECK 2: Índices válidos (1-based, en [1, m]) ---
    invalid = [idx for idx in indices if not (1 <= idx <= m)]
    if invalid:
        print(f"FAIL indices_valid: índices fuera de [1,{m}]: {invalid[:5]}")
        all_pass = False
    else:
        print(f"PASS indices_valid: todos los {k} índices en [1,{m}]")

    # --- CHECK 3: Índices distintos ---
    if len(set(indices)) != len(indices):
        # Encontrar duplicados
        seen: set = set()
        dups = []
        for idx in indices:
            if idx in seen:
                dups.append(idx)
            seen.add(idx)
        print(f"FAIL indices_distinct: índices duplicados: {dups[:5]}")
        all_pass = False
    else:
        print(f"PASS indices_distinct: {k} índices son todos distintos")

    # --- CHECK 4-6: Sin colisiones en X, Y, Z ---
    used_x: set = set()
    used_y: set = set()
    used_z: set = set()
    collision_x: list = []
    collision_y: list = []
    collision_z: list = []

    for idx in indices:
        if 1 <= idx <= m:  # Solo si el índice es válido
            x, y, z = triples[idx - 1]
            if x in used_x:
                collision_x.append((idx, x))
            used_x.add(x)
            if y in used_y:
                collision_y.append((idx, y))
            used_y.add(y)
            if z in used_z:
                collision_z.append((idx, z))
            used_z.add(z)

    if collision_x:
        print(f"FAIL no_collision_X: colisiones en X: {collision_x[:3]}")
        all_pass = False
    else:
        print(f"PASS no_collision_X: ninguna colisión en dimensión X")

    if collision_y:
        print(f"FAIL no_collision_Y: colisiones en Y: {collision_y[:3]}")
        all_pass = False
    else:
        print(f"PASS no_collision_Y: ninguna colisión en dimensión Y")

    if collision_z:
        print(f"FAIL no_collision_Z: colisiones en Z: {collision_z[:3]}")
        all_pass = False
    else:
        print(f"PASS no_collision_Z: ninguna colisión en dimensión Z")

    # --- CHECK 7: Opt check ---
    if "opt" in meta:
        opt_known = meta["opt"]
        if k <= opt_known:
            print(f"PASS opt_check: k={k} <= opt={opt_known}")
        else:
            print(f"FAIL opt_check: k={k} > opt={opt_known} (solución dice ser mayor que el óptimo conocido)")
            all_pass = False
    else:
        print(f"PASS opt_check: no hay # opt= en la instancia (skipped)")

    return all_pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) != 3:
        print(
            "Uso: python tools/validator.py <instance.3dm> <solution.txt>",
            file=sys.stderr,
        )
        sys.exit(2)

    instance_path = sys.argv[1]
    solution_path = sys.argv[2]

    ok = validate(instance_path, solution_path)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
