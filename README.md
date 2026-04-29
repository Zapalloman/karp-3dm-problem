# Trabajo NP — 3-Dimensional Matching (3DM)

Trabajo grupal del curso de Optimización. Problema #17 de la lista de Karp,
dificultad Alta.


## Estructura rápida

| Carpeta         | Qué hay                                                  |
|-----------------|----------------------------------------------------------|
| `src/`          | Implementaciones Python, C++, Java (1 base + 1 mejorada).|
| `instances/`    | Casos de prueba generados (small/medium/large).          |
| `results/`      | CSV crudos, tablas y gráficos del análisis experimental. |
| `report/`       | Informe escrito final en **LaTeX** (`make -C report`).   |
| `presentation/` | Slides **Beamer** para la exposición de 10 minutos.      |
| `tools/`        | Generador, validador y scripts de benchmark.             |

## Cómo correr (cuando esté implementado)

```bash
# Generar suite de pruebas
python tools/generator.py --suite all --seed 42

# Compilar C++ y Java
make -C src/cpp
javac -d src/java/build src/java/src/*.java

# Correr benchmarks completos
bash tools/run_benchmarks.sh

# Reproducir gráficos del informe
python tools/plot_results.py results/raw/*.csv
```

