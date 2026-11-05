# 06 - Predicción de Churn (ML)

![Ruta del Master Training con énfasis en lo construido hasta el Ejercicio 06](../assets/06%20-%20arquitetura.gif?v=20260928)

> _Resaltado, lo que ya construiste en la ruta hasta este punto; en gris, lo que todavía viene._

Ahora vamos a entrenar un modelo que estima la probabilidad de que cada cliente cancele y convertir eso en una **tabla de scores** lista para usar. Este es el ejercicio puente: el score que generes aquí alimenta los dashboards, los agentes y la app de retención de los próximos módulos.

**Requisitos previos:**
- [Ej. 1 - SQL con IA](<../01 - SQL con IA/README.md>)
- [Ej. 5 - Dashboards con IA](<../05 - Dashboards con IA/README.md>) (para el Desafío)

## Objetivo
A partir de la tabla de features `dbacademy.churn.feature_churn` (comportamiento de uso, atraso de pago, satisfacción), vamos a entrenar un modelo de clasificación, registrarlo en Unity Catalog y calcular el score de todos los clientes. Al final tendrás, en tu schema:
- **`modelo_churn`**: el modelo gobernado, registrado en Unity Catalog
- **`churn_scores`**: la tabla de scores con `prob_churn`, `nivel_riesgo` (Alto/Medio/Bajo) y el `factor_principal` detrás del riesgo

> No escribimos ML a mano celda por celda: el notebook ya trae el flujo listo y explicado. El foco es generar el activo (modelo + scores), no programar el entrenamiento.

---

## Paso 1: Ejecutar el notebook
1. Importa el notebook: **Workspace → Tres puntitos arriba → Import → URL**, y pega lo siguiente:
```
https://github.com/douglassrsilva/master-training-spanish/blob/main/06%20-%20Predicci%C3%B3n%20de%20Churn%20%28ML%29/notebook_modelo_churn.py
```
2. Después de hacer clic en **Import**, serás redirigido al notebook
3. En el menú desplegable de la barra superior, junto a Run all, selecciona el cluster `dbacademy_workshop_cluster`
4. Ejecuta las celdas en orden hasta la primera celda de código debajo de **Paso 1 — Configura tu schema**, que muestra el widget
5. En el widget **Tu schema**, selecciona el schema que creaste en el Ej. 1
6. Haz clic en **Run all**

En unos ~2 minutos el notebook instala las bibliotecas, entrena, registra el modelo y guarda la tabla de scores.

## Paso 2: Revisar el resultado
Al final del notebook, verifica:
- **AUC (prueba): ≈ 0,97**: el modelo separa bien a quienes cancelan de quienes se quedan
- Distribución de riesgo (`churn_scores`):

  | Nivel de riesgo | Clientes | Prob. promedio |
  |-----------------|----------|----------------|
  | Alto            | ~492     | ~0,82          |
  | Medio           | ~133     | ~0,36          |
  | Bajo            | ~1.375   | ~0,06          |

- Factor principal de cada cliente en riesgo: *Insatisfacción (CSAT)*, *Bajo uso*, *Morosidad* o *Detractor (NPS)*, la "explicación de negocio" que va a aparecer en la app

Luego, revisa los objetos creados en tu schema:
1. En el menú lateral izquierdo, ve a **Catalog → `dbacademy` → `<tu_schema>`**
2. En **Models**, abre el `modelo_churn`
3. En **Tables**, abre la tabla `churn_scores`

## 🎯 Desafío
Vuelve a tu dashboard `Análisis de Churn <tu_schema>` y genera un nuevo análisis: usando las tablas `dbacademy.<tu_schema>.churn_scores` y `dbacademy.churn.dim_cliente`, crea indicadores y visualizaciones relevantes sobre la predicción de churn.

Así, el mismo dashboard pasa a tener una pestaña de **retrospectiva** (el churn que ocurrió, del Ej. 5) y otra de **predicción** (quién está en riesgo ahora).

## Explore
Acabas de crear el corazón de la operación de retención: un score de riesgo por cliente, con el motivo detrás. En los próximos módulos, este activo cobra vida: los agentes responden sobre riesgo, y los dashboards y la app priorizan a quién atender primero. Registrado en Unity Catalog, el `modelo_churn` queda listo para publicarse como endpoint de serving (con guardrail de PII) cuando quieras consultarlo en tiempo real.
