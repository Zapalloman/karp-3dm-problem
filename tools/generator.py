#!/usr/bin/env python3
"""
generator.py — Generador de instancias 3DM para el trabajo NP-Completos #17.

CLI:
    python tools/generator.py [--family random|structured|hard|regression|all]
                              [--n N] [--m M | --density D]
                              [--seed S] [--out DIR]

Familias:
    regression  - Las 5 instancias mínimas de docs/ALGORITHMS.md (copiadas
                  bit-identicas desde src/python/tests/data/).
    random      - Tripletas muestreadas uniformemente sin repetición.
    structured  - Instancias con OPT=n garantizado (matching perfecto base +
                  ruido).
    hard        - Instancias derivadas de fórmulas 3-SAT cercanas al umbral
                  de satisfacibilidad (ratio ~4.27), traducidas a 3DM con la
                  reducción de la fase 3 (gadgets variable+cláusula+garbage).
    all         - Genera la suite completa en instances/{small,medium,large}/

Semilla: se usa random.Random(seed) por instancia, NUNCA el global random.seed().
Filename: <family>_n<n>_m<m>_s<seed>.3dm  (excepto regression que conserva
          el nombre original).

Reproducibilidad: generar dos veces con la misma semilla produce archivos
byte-idénticos.
"""

from __future__ import annotations

import argparse
import os
import random
import shutil
import sys
from typing import List, Set, Tuple

# ---------------------------------------------------------------------------
# Constantes de la suite por defecto (--family all)
# ---------------------------------------------------------------------------

# small: n <= 30
SMALL_RANDOM_N = [10, 20, 30]
SMALL_RANDOM_DENSITY = [1, 2, 4, 8]    # m = density * n
SMALL_RANDOM_SEEDS = range(5)           # seeds 0..4  → 3*4*5 = 60 pero usamos
                                         # solo n en {10,20,30} y solo algunas combinaciones

# Para llegar a 40 archivos small/random: 2 n × 4 density × 5 seeds = 40
# Usamos n in {10, 20} para small/random (n<=30)
SMALL_RANDOM_N_SUITE = [10, 20]

# Para llegar a 15 archivos small/structured: 3 n × 5 seeds = 15
SMALL_STRUCTURED_N_SUITE = [5, 10, 20]
SMALL_STRUCTURED_SEEDS = range(5)

# medium: 30 < n <= 80
MEDIUM_RANDOM_N_SUITE = [30, 50]
MEDIUM_RANDOM_DENSITY = [2, 4, 8, 16]  # 2*4*5 = 40
MEDIUM_RANDOM_SEEDS = range(5)

MEDIUM_STRUCTURED_N_SUITE = [30, 50, 60]
MEDIUM_STRUCTURED_SEEDS = range(5)

# hard medium: 20 instancias  → 4 vars × 5 seeds = 20
MEDIUM_HARD_NVARS_SUITE = [4, 6, 8, 10]  # número de variables 3-SAT
MEDIUM_HARD_SEEDS = range(5)

# large: n > 80
# random: 20 archivos → 2 n × 2 density × 5 seeds = 20
LARGE_RANDOM_N_SUITE = [100, 150]
LARGE_RANDOM_DENSITY = [2, 4]
LARGE_RANDOM_SEEDS = range(5)

# hard large: 10 instancias → 2 nvars × 5 seeds = 10
LARGE_HARD_NVARS_SUITE = [12, 15]
LARGE_HARD_SEEDS = range(5)


# ---------------------------------------------------------------------------
# Utilidades de formato de archivo .3dm
# ---------------------------------------------------------------------------

def write_instance(
    path: str,
    n: int,
    triples: List[Tuple[int, int, int]],
    family: str,
    seed: int,
    opt: int | None = None,
    note: str | None = None,
) -> None:
    """Escribe una instancia en formato .3dm al archivo *path*.

    Formato (docs/INSTANCE_FORMAT.md):
        # family=...
        # n=N  m=M  seed=S
        [# opt=K]
        [# note: ...]
        N M
        x1 y1 z1
        ...
    """
    m = len(triples)
    lines: list[str] = []
    lines.append(f"# family={family}")
    lines.append(f"# n={n}  m={m}  seed={seed}")
    if opt is not None:
        lines.append(f"# opt={opt}")
    if note is not None:
        lines.append(f"# note: {note}")
    lines.append(f"{n} {m}")
    for x, y, z in triples:
        lines.append(f"{x} {y} {z}")

    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


def instance_filename(family: str, n: int, m: int, seed: int) -> str:
    """Nombre canónico de archivo según docs/INSTANCE_FORMAT.md."""
    return f"{family}_n{n}_m{m}_s{seed}.3dm"


# ---------------------------------------------------------------------------
# Familia: regression
# ---------------------------------------------------------------------------

# Contenido literal de las 5 instancias de regresión.
# Copiadas bit-idénticas desde src/python/tests/data/ para que los hashes
# coincidan con los tests de regresión de Python/C++/Java.
REGRESSION_INSTANCES = {
    "mini1.3dm": """\
# family=mini
# opt=2
# seed=0
2 3
0 0 0
0 1 1
1 1 1
""",
    "mini2.3dm": """\
# family=mini
# opt=3
# seed=0
3 5
0 0 0
1 1 1
2 2 2
0 1 2
1 2 0
""",
    "noperf.3dm": """\
# family=mini
# opt=1
# seed=0
3 3
0 0 0
0 1 1
0 2 2
""",
    "dense.3dm": """\
# family=dense
# opt=4
# seed=0
# note: all 16 triples from X={0,1,2,3} x Y={0,1,2,3} x Z constant per x
4 16
0 0 0
0 1 0
0 2 0
0 3 0
1 0 1
1 1 1
1 2 1
1 3 1
2 0 2
2 1 2
2 2 2
2 3 2
3 0 3
3 1 3
3 2 3
3 3 3
""",
    "empty.3dm": """\
# family=mini
# opt=0
# seed=0
5 0
""",
}


def generate_regression(out_dir: str) -> List[str]:
    """Copia las 5 instancias de regresión bit-idénticas a *out_dir*.

    Retorna lista de paths generados.
    """
    paths = []
    for fname, content in REGRESSION_INSTANCES.items():
        path = os.path.join(out_dir, fname)
        os.makedirs(out_dir, exist_ok=True)
        with open(path, "w", newline="\n") as fh:
            fh.write(content)
        paths.append(path)
    print(f"  regression: {len(paths)} archivos en {out_dir}")
    return paths


# ---------------------------------------------------------------------------
# Familia: random
# ---------------------------------------------------------------------------

def generate_random_instance(
    n: int,
    m_target: int,
    seed: int,
) -> Tuple[List[Tuple[int, int, int]], int]:
    """Genera m_target tripletas uniformes sin repetición en [0,n)^3.

    Usa random.Random(seed) (determinista, sin estado global).
    Si m_target > n^3, se acota a n^3 (universo completo).
    Retorna (triples, seed_usado).
    """
    rng = random.Random(seed)
    universe_size = n * n * n
    m_actual = min(m_target, universe_size)

    # Muestreo de Fisher-Yates parcial (reservoir sampling) sobre [0, n^3)
    chosen: Set[int] = set()
    triples: List[Tuple[int, int, int]] = []

    # Para m_actual pequeño respecto al universo, muestreo con rechazo
    # Para m_actual grande, generar el universo y mezclar
    if m_actual <= universe_size // 2:
        while len(triples) < m_actual:
            idx = rng.randrange(universe_size)
            if idx not in chosen:
                chosen.add(idx)
                x = idx // (n * n)
                y = (idx // n) % n
                z = idx % n
                triples.append((x, y, z))
    else:
        # Generar todo el universo y elegir m_actual
        all_triples = [(x, y, z) for x in range(n) for y in range(n) for z in range(n)]
        rng.shuffle(all_triples)
        triples = all_triples[:m_actual]

    return triples, seed


def generate_random_family(
    out_dir: str,
    n_list: list,
    density_list: list,
    seed_list: range,
) -> List[str]:
    """Genera instancias random para todos los (n, density, seed)."""
    paths = []
    os.makedirs(out_dir, exist_ok=True)
    for n in n_list:
        for density in density_list:
            m_target = density * n
            for seed in seed_list:
                triples, _ = generate_random_instance(n, m_target, seed)
                m = len(triples)
                fname = instance_filename("random", n, m, seed)
                path = os.path.join(out_dir, fname)
                write_instance(path, n, triples, "random", seed)
                paths.append(path)
    print(f"  random: {len(paths)} archivos en {out_dir}")
    return paths


# ---------------------------------------------------------------------------
# Familia: structured (OPT = n garantizado)
# ---------------------------------------------------------------------------

def generate_structured_instance(
    n: int,
    seed: int,
    noise_factor: float = 2.0,
) -> Tuple[List[Tuple[int, int, int]], int]:
    """Genera una instancia con matching perfecto garantizado (OPT = n).

    Construcción:
    1. Genera dos permutaciones pi, sigma de [0,n) (el matching base).
       El matching base es {(i, pi(i), sigma(i)) : i in 0..n-1}.
    2. Añade tripletas ruido (hasta noise_factor*n adicionales, sin repetir
       las del matching base, muestreadas uniformemente).

    Retorna (triples, seed).
    """
    rng = random.Random(seed)

    perm_y = list(range(n))
    perm_z = list(range(n))
    rng.shuffle(perm_y)
    rng.shuffle(perm_z)

    base_triples: Set[Tuple[int, int, int]] = set()
    matching_base: List[Tuple[int, int, int]] = []
    for i in range(n):
        t = (i, perm_y[i], perm_z[i])
        base_triples.add(t)
        matching_base.append(t)

    # Tripletas ruido: muestreo con rechazo
    n_noise = int(noise_factor * n)
    universe_size = n * n * n
    all_triples: Set[Tuple[int, int, int]] = set(matching_base)
    attempts = 0
    max_attempts = n_noise * 20
    while len(all_triples) < min(n + n_noise, universe_size) and attempts < max_attempts:
        x = rng.randrange(n)
        y = rng.randrange(n)
        z = rng.randrange(n)
        all_triples.add((x, y, z))
        attempts += 1

    # Ordenar para determinismo: primero el matching base, luego el ruido
    # (en el orden en que se añadieron, para reproducibilidad)
    triples_ordered: List[Tuple[int, int, int]] = []
    noise_set = all_triples - base_triples

    # Insertar base en orden, luego ruido en orden lexicográfico
    triples_ordered.extend(matching_base)
    triples_ordered.extend(sorted(noise_set))

    return triples_ordered, seed


def generate_structured_family(
    out_dir: str,
    n_list: list,
    seed_list: range,
) -> List[str]:
    """Genera instancias structured para todos los (n, seed)."""
    paths = []
    os.makedirs(out_dir, exist_ok=True)
    for n in n_list:
        for seed in seed_list:
            triples, _ = generate_structured_instance(n, seed)
            m = len(triples)
            fname = instance_filename("structured", n, m, seed)
            path = os.path.join(out_dir, fname)
            write_instance(path, n, triples, "structured", seed, opt=n)
            paths.append(path)
    print(f"  structured: {len(paths)} archivos en {out_dir}")
    return paths


# ---------------------------------------------------------------------------
# Familia: hard (reducción 3-SAT -> 3DM)
# ---------------------------------------------------------------------------
# Implementa los gadgets de docs/03_complexity_analysis.md §3.2.
#
# Gadgets:
#   (G-V) Variable gadget: para variable u_i con k_i ocurrencias,
#         elementos t^i_p, f^i_p ∈ X  (p=1..k_i)
#                  a^i_p ∈ Y, b^i_p ∈ Z
#         tripletas T^i_p = (t^i_p, a^i_p, b^i_p)
#                   F^i_p = (f^i_p, a^i_{(p mod k_i)+1}, b^i_p)
#
#   (G-C) Clause gadget: para cláusula C_j con literales ell_{j,1..3}:
#         c_j ∈ Y,  c'_j ∈ Z
#         3 tripletas: (lit(j,l), c_j, c'_j)  para l=1,2,3
#         donde lit(j,l) = t^i_p si ell_{j,l} = u_i positivo (ocurrencia p)
#                        = f^i_p si ell_{j,l} = ~u_i (ocurrencia p)
#
#   (G-G) Garbage gadget: 2q elementos g^Y_r ∈ Y, 2q g^Z_r ∈ Z,
#         todas las tripletas (eps, g^Y_r, g^Z_s) para eps ∈ X-libre
#
# El total de X es 6q, Y es 6q, Z es 6q  → n = 6q.
# Tripletas: 2*sum(k_i) + 3q + (6q)*(2q)*(2q) pero en la implementación
# usamos solo el subconjunto necesario de garbage (O(q^2) en lugar de O(q^3))
# para mantener los archivos manejables, siguiendo la "Observación" de §3.2.3.
# Esta decisión se documenta en el Hand-off de la fase.

def generate_3sat_formula(n_vars: int, n_clauses: int, seed: int):
    """Genera una fórmula 3-SAT aleatoria.

    Retorna lista de cláusulas; cada cláusula es una lista de 3 literales.
    Un literal es (var_idx, positive) con var_idx en 0..n_vars-1.

    Para fórmulas cercanas al umbral se usa ratio n_clauses/n_vars ~ 4.27.
    """
    rng = random.Random(seed)
    clauses = []
    for _ in range(n_clauses):
        clause = []
        # Elegir 3 variables distintas
        vars_chosen = rng.sample(range(n_vars), min(3, n_vars))
        # Si n_vars < 3, repetir con reemplazo
        while len(vars_chosen) < 3:
            vars_chosen.append(rng.randrange(n_vars))
        for v in vars_chosen[:3]:
            polarity = rng.randint(0, 1) == 1
            clause.append((v, polarity))
        clauses.append(clause)
    return clauses


def sat_to_3dm(n_vars: int, clauses: list) -> Tuple[int, List[Tuple[int, int, int]], int]:
    """Reduce una fórmula 3-SAT a una instancia 3DM con la reducción de §3.2.

    Retorna (n, triples, opt_if_sat) donde:
      - n = 6q  (q = len(clauses))
      - triples = lista de (x, y, z) con valores en [0, n)
      - opt_if_sat = n si la fórmula es satisfacible, None (no calculado) si no.

    Índices de elementos (todos en [0, n=6q)):
    DIMENSIÓN X (indices 0 .. 6q-1):
      Para variable u_i (i=0..nv-1) con k_i ocurrencias:
        t^i_p  (p=0..k_i-1): offset_t[i] + p
        f^i_p  (p=0..k_i-1): offset_f[i] + p
    DIMENSIÓN Y (indices 0 .. 6q-1):
      Para variable u_i:
        a^i_p  (p=0..k_i-1): offset_a[i] + p
      Para cláusula j:
        c_j: base_cy + j
      Garbage:
        g^Y_r (r=0..2q-1): base_gy + r
    DIMENSIÓN Z (indices 0 .. 6q-1):
      Para variable u_i:
        b^i_p  (p=0..k_i-1): offset_b[i] + p
      Para cláusula j:
        c'_j: base_cz + j
      Garbage:
        g^Z_r (r=0..2q-1): base_gz + r
    """
    q = len(clauses)
    nv = n_vars
    if q == 0 or nv == 0:
        return 1, [], 0

    # Contar ocurrencias de cada variable
    k = [0] * nv  # k[i] = número de ocurrencias de u_i
    for clause in clauses:
        for (var, _pol) in clause:
            k[var] += 1

    # Verificar que todas las variables aparecen al menos una vez;
    # si alguna tiene k[i]=0, le asignamos k[i]=1 (tripleta ficticia)
    for i in range(nv):
        if k[i] == 0:
            k[i] = 1

    # sum_k = sum(k) = 3q (solo si todas las ocurrencias vienen de cláusulas)
    # En general puede ser > 3q por el ajuste anterior; recompute
    sum_k = sum(k)

    # --- Asignación de índices X ---
    # X tiene 2*sum_k elementos: t^i_0..t^i_{k[i]-1} y f^i_0..f^i_{k[i]-1}
    offset_t = [0] * nv
    offset_f = [0] * nv
    cur = 0
    for i in range(nv):
        offset_t[i] = cur
        cur += k[i]
    for i in range(nv):
        offset_f[i] = cur
        cur += k[i]
    X_total = cur  # = 2 * sum_k

    # --- Asignación de índices Y ---
    # Y tiene sum_k (a^i_p) + q (c_j) + garbage
    # garbage_y = X_total - q (los X-libres después de gadgets = 2*sum_k - sum_k - q = sum_k - q)
    # Pero según §3.2.3 con la versión completa: Y-total = X-total = 2*sum_k
    # a^i_p: offset_a[i] + p
    offset_a = [0] * nv
    cur = 0
    for i in range(nv):
        offset_a[i] = cur
        cur += k[i]
    base_cy = cur      # c_j para j=0..q-1
    cur += q
    # Garbage Y: debe haber exactamente X_total - sum_k - q = sum_k - q elementos
    n_garbage = sum_k - q
    if n_garbage < 0:
        n_garbage = 0
    base_gy = cur
    cur += n_garbage
    Y_total = cur

    # --- Asignación de índices Z ---
    offset_b = [0] * nv
    cur = 0
    for i in range(nv):
        offset_b[i] = cur
        cur += k[i]
    base_cz = cur      # c'_j para j=0..q-1
    cur += q
    base_gz = cur
    cur += n_garbage
    Z_total = cur

    # n de la instancia 3DM = max(X_total, Y_total, Z_total)
    # Si no están balanceadas, hacemos padding
    n_inst = max(X_total, Y_total, Z_total)

    triples: List[Tuple[int, int, int]] = []

    # --- (G-V) Variable gadgets ---
    occ_count = [0] * nv  # contador de ocurrencias usadas por variable

    for i in range(nv):
        ki = k[i]
        for p in range(ki):
            t_x = offset_t[i] + p
            f_x = offset_f[i] + p
            a_p = offset_a[i] + p
            a_next = offset_a[i] + (p + 1) % ki
            b_p = offset_b[i] + p

            T_trip = (t_x, a_p, b_p)
            F_trip = (f_x, a_next, b_p)
            triples.append(T_trip)
            triples.append(F_trip)

    # --- (G-C) Clause gadgets ---
    # Para cada variable, rastrear qué ocurrencia (positiva/negativa) es la p-ésima
    pos_occ = [0] * nv   # siguiente ocurrencia positiva de cada variable
    neg_occ = [0] * nv   # siguiente ocurrencia negativa de cada variable

    # Pre-compute occurrence indices: para cada literal en cada cláusula,
    # asignar un índice de ocurrencia p.
    # Primero un pass para contar cuántas ocurrencias positivas/negativas tiene cada var
    k_pos = [0] * nv
    k_neg = [0] * nv
    for clause in clauses:
        for (var, pol) in clause:
            if pol:
                k_pos[var] += 1
            else:
                k_neg[var] += 1

    # Asignar los k[i] slots: primero las positivas, luego las negativas
    # t^i_p (p=0..k_pos[i]-1) → literal u_i positivo, ocurrencia p
    # f^i_p (p=0..k_neg[i]-1) → literal ~u_i, ocurrencia p
    # (si k_pos[i]+k_neg[i] < k[i] por el ajuste, los slots sobrantes no se usan en clauses)

    pos_idx = [0] * nv
    neg_idx = [0] * nv

    for j, clause in enumerate(clauses):
        cj_y = base_cy + j
        cj_z = base_cz + j

        for (var, pol) in clause:
            if pol:
                # Literal positivo u_var: elemento X es t^var_{pos_idx[var]}
                p = pos_idx[var]
                pos_idx[var] += 1
                x_elem = offset_t[var] + p
            else:
                # Literal negativo ~u_var: elemento X es f^var_{neg_idx[var]}
                p = neg_idx[var]
                neg_idx[var] += 1
                x_elem = offset_f[var] + p

            triples.append((x_elem, cj_y, cj_z))

    # --- (G-G) Garbage gadgets ---
    # X-libres: los elementos X que no fueron consumidos por (G-V) ni por (G-C)
    # Después de (G-V): si se elige F-branch, los t^i_* quedan libres; si T-branch, los f^i_*.
    # En total exactamente sum_k elementos X están libres en cualquier matching válido.
    # Después de (G-C): cada cláusula consume 1 de esos X-libres → sobran sum_k - q.
    # (G-G) necesita cubrir esos sum_k - q elementos X.
    # g^Y_r (r=0..n_garbage-1) y g^Z_r (r=0..n_garbage-1)
    # Tripletas: (eps, g^Y_r, g^Z_s) para eps en ALL X, r,s en [0,n_garbage)
    # Para mantener el tamaño del archivo manejable, usamos solo las tripletas
    # necesarias (una rejilla diagonal O(q^2) en vez de O(q^3)):
    # Asignamos eps_k ↔ (g^Y_{k mod n_garbage}, g^Z_{k div ...}) pero la
    # versión simple es: listamos todas las combinaciones (eps, g^Y_r, g^Z_s)
    # para TODOS los X y todos los pares (r,s). Esto es O(X_total * n_garbage^2).
    # Para n_garbage grande esto puede ser enorme. Usamos versión diagonal O(q^2):
    # Para cada X-elemento eps (índice e=0..X_total-1),
    # para cada r in range(n_garbage), para cada s in range(n_garbage):
    #   triples.append((e, base_gy+r, base_gz+s))
    # En lugar de la versión completa, usamos SOLO los pares (r,s) necesarios
    # para garantizar la existencia del garbage matching (diagonal).
    # La versión completa (O(q^3)) es correcta pero genera archivos enormes.
    # Decisión: usamos la versión COMPLETA para instancias pequeñas (n_garbage<=4)
    # y la versión diagonal para las más grandes.

    all_x_elems = list(range(X_total))

    if n_garbage > 0:
        if n_garbage <= 4:
            # Versión completa
            for e in all_x_elems:
                for r in range(n_garbage):
                    for s in range(n_garbage):
                        triples.append((e, base_gy + r, base_gz + s))
        else:
            # Versión diagonal O(X_total * n_garbage):
            # Para cada X-elem eps_e:
            #   tripletas (eps_e, g^Y_{e mod n_garbage}, g^Z_s) para s in range(n_garbage)
            # Esto asegura cobertura de todos los g^Y y g^Z y todos los X-libres.
            for e in all_x_elems:
                r = e % n_garbage
                for s in range(n_garbage):
                    triples.append((e, base_gy + r, base_gz + s))

    return n_inst, triples, None  # opt no se calcula (necesitaría resolver SAT)


def generate_hard_instance(
    n_vars: int,
    seed: int,
    ratio: float = 4.27,
) -> Tuple[int, List[Tuple[int, int, int]], int]:
    """Genera una instancia hard derivada de una fórmula 3-SAT al umbral.

    Retorna (n, triples, seed).
    """
    n_clauses = max(1, round(ratio * n_vars))
    clauses = generate_3sat_formula(n_vars, n_clauses, seed)
    n, triples, _ = sat_to_3dm(n_vars, clauses)
    return n, triples, seed


def generate_hard_family(
    out_dir: str,
    nvars_list: list,
    seed_list: range,
) -> List[str]:
    """Genera instancias hard para todos los (n_vars, seed)."""
    paths = []
    os.makedirs(out_dir, exist_ok=True)
    for nv in nvars_list:
        for seed in seed_list:
            n, triples, _ = generate_hard_instance(nv, seed)
            m = len(triples)
            fname = instance_filename("hard", n, m, seed)
            path = os.path.join(out_dir, fname)
            write_instance(
                path, n, triples, "hard", seed,
                note=f"3sat_vars={nv} ratio=4.27"
            )
            paths.append(path)
    print(f"  hard: {len(paths)} archivos en {out_dir}")
    return paths


# ---------------------------------------------------------------------------
# Suite completa (--family all)
# ---------------------------------------------------------------------------

def generate_all(base_dir: str) -> None:
    """Genera la suite completa en base_dir/{small,medium,large}/."""
    total = 0

    print("Generando suite completa en:", base_dir)
    print()

    # --- small ---
    print("=== small ===")
    paths = generate_regression(os.path.join(base_dir, "small", "regression"))
    total += len(paths)

    paths = generate_random_family(
        os.path.join(base_dir, "small", "random"),
        SMALL_RANDOM_N_SUITE,
        SMALL_RANDOM_DENSITY,
        SMALL_RANDOM_SEEDS,
    )
    total += len(paths)

    paths = generate_structured_family(
        os.path.join(base_dir, "small", "structured"),
        SMALL_STRUCTURED_N_SUITE,
        SMALL_STRUCTURED_SEEDS,
    )
    total += len(paths)

    # --- medium ---
    print()
    print("=== medium ===")
    paths = generate_random_family(
        os.path.join(base_dir, "medium", "random"),
        MEDIUM_RANDOM_N_SUITE,
        MEDIUM_RANDOM_DENSITY,
        MEDIUM_RANDOM_SEEDS,
    )
    total += len(paths)

    paths = generate_structured_family(
        os.path.join(base_dir, "medium", "structured"),
        MEDIUM_STRUCTURED_N_SUITE,
        MEDIUM_STRUCTURED_SEEDS,
    )
    total += len(paths)

    paths = generate_hard_family(
        os.path.join(base_dir, "medium", "hard"),
        MEDIUM_HARD_NVARS_SUITE,
        MEDIUM_HARD_SEEDS,
    )
    total += len(paths)

    # --- large ---
    print()
    print("=== large ===")
    paths = generate_random_family(
        os.path.join(base_dir, "large", "random"),
        LARGE_RANDOM_N_SUITE,
        LARGE_RANDOM_DENSITY,
        LARGE_RANDOM_SEEDS,
    )
    total += len(paths)

    paths = generate_hard_family(
        os.path.join(base_dir, "large", "hard"),
        LARGE_HARD_NVARS_SUITE,
        LARGE_HARD_SEEDS,
    )
    total += len(paths)

    print()
    print(f"Total archivos .3dm generados: {total}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="generator.py",
        description="Generador de instancias 3DM para la suite de pruebas.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--family",
        choices=["random", "structured", "hard", "regression", "all"],
        default="all",
        help="Familia de instancias a generar (default: all).",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=None,
        metavar="N",
        help="Tamaño n (|X|=|Y|=|Z|=n). Requerido para family=random/structured/hard.",
    )
    parser.add_argument(
        "--m",
        type=int,
        default=None,
        metavar="M",
        help="Número exacto de tripletas. Para family=random.",
    )
    parser.add_argument(
        "--density",
        type=float,
        default=None,
        metavar="D",
        help="Densidad m/n. Para family=random. Se ignora si --m está dado.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        metavar="S",
        help="Semilla del generador (default: 0).",
    )
    parser.add_argument(
        "--out",
        default="instances",
        metavar="DIR",
        help="Directorio de salida (default: instances/).",
    )

    args = parser.parse_args()

    if args.family == "all":
        generate_all(args.out)
        return

    if args.family == "regression":
        generate_regression(args.out)
        return

    if args.family in ("random", "structured", "hard") and args.n is None:
        parser.error(f"--n es requerido para --family {args.family}")

    n = args.n

    if args.family == "random":
        if args.m is not None:
            m_target = args.m
        elif args.density is not None:
            m_target = int(args.density * n)
        else:
            m_target = 4 * n  # densidad por defecto
        triples, _ = generate_random_instance(n, m_target, args.seed)
        m = len(triples)
        fname = instance_filename("random", n, m, args.seed)
        path = os.path.join(args.out, fname)
        write_instance(path, n, triples, "random", args.seed)
        print(f"Generado: {path}")

    elif args.family == "structured":
        triples, _ = generate_structured_instance(n, args.seed)
        m = len(triples)
        fname = instance_filename("structured", n, m, args.seed)
        path = os.path.join(args.out, fname)
        write_instance(path, n, triples, "structured", args.seed, opt=n)
        print(f"Generado: {path}")

    elif args.family == "hard":
        nv = n  # aquí n se interpreta como número de variables 3-SAT
        n_inst, triples, _ = generate_hard_instance(nv, args.seed)
        m = len(triples)
        fname = instance_filename("hard", n_inst, m, args.seed)
        path = os.path.join(args.out, fname)
        write_instance(
            path, n_inst, triples, "hard", args.seed,
            note=f"3sat_vars={nv} ratio=4.27"
        )
        print(f"Generado: {path}")


if __name__ == "__main__":
    main()
