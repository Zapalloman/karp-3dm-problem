# tools/

Scripts de soporte que **no** son parte del algoritmo (no entran en la
prohibición de "librerías que resuelvan el problema").



| Script                  | Qué hace                                               |
|-------------------------|--------------------------------------------------------|
| `generator.py`          | Genera instancias `.3dm` por familia.                  |
| `validator.py`          | Verifica que un matching es válido para una instancia. |
| `run_benchmarks.sh`     | Corre los 6 binarios sobre la suite, emite CSV crudo.  |
| `analyze.py`            |Agrega CSVs crudos en tablas resumen.                  |
| `plot_results.py`       |Genera los gráficos del informe.                       |
| `reproduce.sh`          |Pipeline end-to-end para reproducir todos los datos.   |

---

## generator.py

Genera instancias 3DM en formato `.3dm` según familia.

### CLI

```bash
python tools/generator.py [--family random|structured|hard|regression|all]
                          [--n N] [--m M | --density D]
                          [--seed S] [--out DIR]
```

### Opciones

| Flag | Default | Descripción |
|------|---------|-------------|
| `--family` | `all` | Familia a generar. |
| `--n N` | — | Tamaño n (requerido para random/structured/hard). |
| `--m M` | — | Número exacto de tripletas (random). |
| `--density D` | 4 | Densidad m/n (random; ignorado si `--m` está dado). |
| `--seed S` | 0 | Semilla del generador. |
| `--out DIR` | `instances/` | Directorio de salida. |

### Familias

- **`regression`**: Las 5 instancias mínimas bit-idénticas a
  `src/python/tests/data/` (`mini1`, `mini2`, `noperf`, `dense`, `empty`).
  Llevan `# opt=K` obligatorio.

- **`random`**: Tripletas muestreadas uniformemente sin repetición.
  Nombre de archivo: `random_n<n>_m<m>_s<seed>.3dm`.

- **`structured`**: Instancias con OPT=n garantizado. Se construye un
  matching perfecto base `{(i, pi(i), sigma(i))}` y se añaden tripletas
  ruido. Header lleva `# opt=n`.

- **`hard`**: Instancias derivadas de fórmulas 3-SAT al umbral de
  satisfacibilidad (ratio cláusulas/vars ≈ 4.27), traducidas a 3DM con la
  reducción de §3.2 de `docs/03_complexity_analysis.md` (gadgets de
  variable, cláusula y garbage).

- **`all`**: Genera la suite completa en `instances/{small,medium,large}/`.

### Ejemplos

```bash
# Suite completa
python tools/generator.py --family all --out instances/

# Solo regresión
python tools/generator.py --family regression --out instances/small/regression

# Una instancia random específica
python tools/generator.py --family random --n 50 --density 4 --seed 7 --out /tmp/test

# Reproducibilidad: ambas corridas producen el mismo archivo
python tools/generator.py --family random --n 20 --density 4 --seed 42 --out /tmp/a
python tools/generator.py --family random --n 20 --density 4 --seed 42 --out /tmp/b
diff /tmp/a/*.3dm /tmp/b/*.3dm  # sin diferencias
```

### Determinismo

`generator.py` usa `random.Random(seed)` por instancia, nunca el global
`random.seed()`. Generar dos veces con la misma semilla produce archivos
byte-idénticos.

---

## validator.py

Verifica que una solución es válida para una instancia.

### CLI

```bash
python tools/validator.py <instance.3dm> <solution.txt>
```

### Checks

1. `parse_instance` — el archivo `.3dm` es legible y bien formado.
2. `parse_solution` — el archivo de solución es legible y bien formado.
3. `indices_valid` — todos los índices están en `[1, m]` (1-based).
4. `indices_distinct` — no hay índices duplicados.
5. `no_collision_X` — las tripletas del matching no comparten `x`.
6. `no_collision_Y` — ídem para `y`.
7. `no_collision_Z` — ídem para `z`.
8. `opt_check` — si la instancia tiene `# opt=K`, verifica `k <= K`.

### Salida

```
PASS parse_instance: n=3 m=5
PASS parse_solution: k=3
PASS indices_valid: todos los 3 índices en [1,5]
PASS indices_distinct: 3 índices son todos distintos
PASS no_collision_X: ninguna colisión en dimensión X
PASS no_collision_Y: ninguna colisión en dimensión Y
PASS no_collision_Z: ninguna colisión en dimensión Z
PASS opt_check: k=3 <= opt=3
```

### Exit codes

| Código | Significado |
|--------|-------------|
| 0 | Todos los checks pasan. |
| 1 | Al menos un check falla. |
| 2 | Error de parsing (archivo no encontrado o mal formado). |

### Ejemplo

```bash
# Generar una solución con la implementación Python
PYTHONPATH=src/python python -m threedm instances/small/regression/mini2.3dm \
    --algo smart --output /tmp/sol.txt

# Validarla
python tools/validator.py instances/small/regression/mini2.3dm /tmp/sol.txt
echo "Exit: $?"
```

---

## run_benchmarks.sh

Corre los 6 binarios (Python/C++/Java × brute/smart) sobre una suite de
instancias y emite un CSV crudo con los resultados.

### CLI

```bash
bash tools/run_benchmarks.sh [suite] [time_limit_s]
```

| Argumento | Default | Descripción |
|-----------|---------|-------------|
| `suite` | `small` | Subcarpeta de `instances/` a usar. |
| `time_limit_s` | `30` | Segundos de límite por corrida. |

### Salida

Archivo `results/raw/run_YYYYMMDD_HHMMSS.csv` con header:

```
lang,algo,instance,n,m,opt,k,time_ms,nodes,timed_out
```

### Pre-requisitos

Antes de correr, compilar/instalar los binarios:

```bash
# Python
pip install -e src/python/

# C++
make -C src/cpp

# Java
bash src/java/build.sh
```

### Ejemplo

```bash
# Suite pequeña con límite de 60 segundos
bash tools/run_benchmarks.sh small 60

# Suite mediana
bash tools/run_benchmarks.sh medium 120
```

---

## reproduce.sh

Pipeline end-to-end:

```bash
bash tools/reproduce.sh
```

1. Regenera la suite de instancias.
2. Corre los benchmarks.
3. Genera las tablas y gráficos.
4. Compila el informe LaTeX.
