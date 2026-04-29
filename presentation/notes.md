# Guion de la presentacion — 3-Dimensional Matching (10 minutos)

Tono: explicativo y directo. No leer las notas textualmente; usarlas para ensayar.

---

## Slide 1 — Portada (~30 s)

- Buenos dias/tardes. Somos Javier Farias, Uriel Navarrete y Vicente Abarca.
- Presentamos el Trabajo Grupal de Optimizacion: el Problema 17 de Karp, conocido como 3-Dimensional Matching o 3DM.
- Este es uno de los 21 problemas NP-completos originales de Karp del 72, con bonificacion por dificultad Alta en el curso.

---

## Slide 2 — Problema (~1 min)

- El problema generaliza el matching bipartito clasico: en vez de emparejar pares (x, y), emparejamos tripletas (x, y, z) de tres conjuntos disjuntos.
- La pregunta de decision es si existe un matching perfecto de tamano n; nosotros implementamos la version de optimizacion, que maximiza cuantas tripletas se pueden incluir sin repetir elementos.
- En el ejemplo del diagrama: con n=3 y 5 tripletas, el optimo es el matching azul que cubre todos los elementos exactamente una vez.

---

## Slide 3 — Modelo matematico (~2 min)

- Tenemos una variable binaria s_t por tripleta: 1 si la incluimos en el matching, 0 si no.
- Maximizamos la suma de las s_t, es decir, el tamano del matching.
- Las restricciones dicen: cada elemento de X, Y y Z puede aparecer a lo sumo en una tripleta del matching.
- Resultado clave: la relajacion LP de este modelo no siempre da soluciones enteras, hay gap entre el optimo LP y el ILP. Esto justifica que no podemos usar un simple redondeo y necesitamos backtracking exacto.

---

## Slide 4 — Complejidad (~1 min)

- 3DM esta en NP: dado un conjunto de tripletas propuesto, verificar si es un matching valido toma tiempo O(n) con bitmasks.
- Para la NP-dificultad, Karp mostro en 1972 una reduccion polinomial desde 3-SAT. Los gadgets codifican las variables y clausulas de la formula como tripletas; si la formula es satisfacible, existe un matching perfecto, y viceversa.
- La version de optimizacion, max-3DM, es ademas APX-dificil: no tiene esquema de aproximacion polinomial salvo que P=NP. El mejor algoritmo de aproximacion conocido llega al 66%.

---

## Slide 5 — Implementacion (~3 min)

- Implementamos dos algoritmos en tres lenguajes: Python 3.11, C++17 y Java 17, con la misma logica en los seis.
- BRUTE es backtracking simple que explora el arbol binario de inclusion/exclusion de las m tripletas.
- SMART agrega cuatro mejoras: bitmasks para verificar conflictos en O(1), una cota superior basada en min(freeX, freeY, freeZ) que poda ramas sin esperanza, la heuristica MRV para elegir el elemento mas restringido primero, y forward checking implicito al activar bits.
- La decision tecnica mas importante: usar enteros de 64 bits para los bitmasks, lo que permite el conteo de elementos libres con la instruccion POPCNT del hardware.
- Los tres lenguajes usan exactamente la misma logica, lo que verifica el determinismo: misma semilla produce el mismo numero de nodos explorados en los tres.

---

## Slide 6 — Resultados (~2 min)

- El grafico muestra el speedup de SMART sobre BRUTE segun n: el beneficio crece exponencialmente con el tamano.
- Para n=20, m=80, BRUTE hace timeout en 30 segundos mientras SMART resuelve en menos de 1 ms: speedup mayor a 60.000 veces.
- Entre lenguajes, para una instancia representativa de n=30 m=120: C++ tarda 18 ms, Java 52 ms (3 veces mas lento), y Python 1150 ms (63 veces mas lento que C++).
- Lo mas importante: los tres lenguajes exploran exactamente 37.854 nodos, confirmando que la logica es identica. La diferencia es puramente de velocidad de ejecucion.

---

## Slide 7 — Conclusiones (~1 min)

- El aprendizaje principal: un modelo ILP bien formulado guia el disenio del algoritmo. Las restricciones del modelo se traducen directamente en las podas de SMART.
- Las limitaciones son claras: instancias con n mayor a 50 son intractables para todos nuestros solvers, y no usamos paralelismo.
- Como trabajo futuro, las direcciones mas prometedoras son: implementar el algoritmo de aproximacion de Cygan para instancias grandes, explorar la parametrizacion FPT del problema, y usar paralelismo de trabajo-robo en las ramas del backtracking.

---

## Resumen de tiempos

| Slide | Tema            | Tiempo estimado |
|-------|-----------------|-----------------|
| 1     | Portada         | 30 s            |
| 2     | Problema        | 1 min           |
| 3     | Modelo ILP      | 2 min           |
| 4     | Complejidad     | 1 min           |
| 5     | Implementacion  | 3 min           |
| 6     | Resultados      | 2 min           |
| 7     | Conclusiones    | 1 min           |
| **Total** |             | **~10 min 30 s** |

---

*Total de palabras aproximado: ~820 palabras. Leer a ritmo natural = ~9-10 minutos.*
