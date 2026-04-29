# Entorno de benchmarks — Fase 8

## Hardware

| Campo        | Valor                           |
|--------------|---------------------------------|
| CPU          | AMD Ryzen 7 5800X 8-Core Processor |
| Nucleos fisicos | 8 (16 hilos, SMT habilitado) |
| RAM          | 15.5 GiB (15,893 MB)           |
| Kernel       | Linux 6.19.14-arch1-1           |
| OS           | Arch Linux                      |

## Software

| Herramienta | Version                                           |
|-------------|---------------------------------------------------|
| Python      | Python 3.14.4                                     |
| g++         | g++ (GCC) 15.2.1 20260209                         |
| Java        | openjdk version "21.0.10" 2026-01-20 LTS (Temurin-21.0.10+7, 64-bit) |
| bash        | GNU bash 5.2+                                     |

## Flags de compilacion C++

Extraidos de `src/cpp/Makefile`:

```
CXX      = g++
CXXFLAGS = -O2 -std=c++17 -Wall -Wextra -pedantic -Iinclude
LDFLAGS  = -lpthread
```

Binario: `src/cpp/3dm` (ELF 64-bit LSB pie executable, x86-64).

## Configuracion Java

- JVM: OpenJDK 64-Bit Server VM Temurin-21.0.10+7 (mixed mode, sharing)
- Classpath: `src/java/build/`
- Main: `com.threedm.Main`
- No flags JVM adicionales (default heap sizing, JIT activado)

## Decisiones de implementacion

- **C++ y --time-limit**: Se detecto un bug bajo -O2 donde el flag
  `--time-limit` causa que el proceso retorne inmediatamente con
  `timed_out=1` en lugar de correr hasta el limite. El bug se debe
  a interaccion entre la optimizacion del compilador y `std::condition_variable`
  (confirmado: funciona con -O0). Workaround: el script de benchmarks usa
  `timeout TL_s ./3dm ...` a nivel bash para C++, sin pasar `--time-limit`.
  Python y Java no tienen este problema y usan `--time-limit` directamente.

- **Brute en medium/large**: Segun la nota de la Fase 7, el algoritmo brute
  agota el time-limit en practicamente todas las instancias medium/hard y large.
  El script corre brute solo en `small/`; para medium y large, solo smart.

- **Replicas**: R=3 replicas por (lang, algo, instance). El CSV crudo
  contiene todas las replicas. Las tablas y graficos usan la mediana.
  Optimizacion: si la primera replica del brute en una instancia timedout
  para todos los lenguajes, las restantes se registran directamente como
  timed_out=1 sin correr (el resultado seria identico).

- **Instancias hard (medium/)**: Las instancias de la familia hard tienen
  n >= 102 (derivadas de reduccion SAT->3DM). Confirmado que todas hacen
  timeout en 60s incluso con el algoritmo smart. Se registran como
  timed_out=1 sin correr para ahorrar tiempo de ejecucion (decision
  documentada en results/discussion.md).

- **Instancias large (n=100, n=150)**: Probada manualmente la instancia
  large/random/random_n100_m200_s0. El algoritmo smart C++ excedio 5 minutos
  sin completar. Todas las instancias large se omiten de los benchmarks.

- **Java JVM**: Se usa la JRE incluida en la extension VS Code
  (`redhat.java` 1.54.0), Temurin-21.0.10. No existe `java`
  en el PATH del sistema; el script lo localiza automaticamente.

## Fechas de ejecucion

| Archivo CSV | Suite | Timestamp |
|-------------|-------|-----------|
| run_20260429_024225.csv | small (brute+smart) | 2026-04-29 02:42 |
| run_20260429_024823.csv | medium/random n30 (smart) | 2026-04-29 02:48 |
| run_20260429_025211.csv | medium/random n50 s0,s1 (smart) | 2026-04-29 02:52 |
| run_missing_20260429_031020.csv | medium/structured + remaining random + hard | 2026-04-29 03:10 |

Las corridas se fechan por el timestamp del archivo CSV en `results/raw/`.
