# Databricks notebook source
# MAGIC %md
# MAGIC # Ejercicio 6 — Modelo de churn
# MAGIC Entrena un modelo que estima la **probabilidad de churn** de cada cliente, lo registra en Unity Catalog y guarda una **tabla de scores** lista para los dashboards y la app.
# MAGIC
# MAGIC **Fuente:** `dbacademy.churn.feature_churn` (features de comportamiento).
# MAGIC **Crea en tu schema:** `modelo_churn` (el modelo) y `churn_scores` (la tabla de scores).
# MAGIC
# MAGIC Adjunta el cluster `dbacademy_workshop_cluster` y ejecuta las celdas en orden.

# COMMAND ----------

# MAGIC %pip install scikit-learn mlflow

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 1 — Configura tu schema
# MAGIC Selecciona tu schema personal en el widget de abajo.

# COMMAND ----------

dbutils.widgets.text("schema", "", "Tu schema")
SCHEMA = dbutils.widgets.get("schema")
SCHEMA_FQN = f"dbacademy.{SCHEMA}"
MODEL  = f"{SCHEMA_FQN}.modelo_churn"
SCORES = f"{SCHEMA_FQN}.churn_scores"
print("Modelo  ->", MODEL)
print("Scores  ->", SCORES)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 2 — Entrenar el modelo
# MAGIC Un `GradientBoostingClassifier` sobre las features de comportamiento. Variable objetivo = `churn_flag`.

# COMMAND ----------

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

df = spark.table("dbacademy.churn.feature_churn").toPandas()
y = df["churn_flag"].astype(int)
X = df.drop(columns=["id_cliente", "churn_flag"])

cat = ["segmento", "nombre_plan"]
num = [c for c in X.columns if c not in cat]

pre = ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
    ("num", "passthrough", num),
])
pipe = Pipeline([("pre", pre), ("clf", GradientBoostingClassifier(random_state=42))])

Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
pipe.fit(Xtr, ytr)
auc = roc_auc_score(yte, pipe.predict_proba(Xte)[:, 1])
print(f"AUC (prueba): {auc:.3f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 3 — Registrar en Unity Catalog
# MAGIC Registramos un modelo **pyfunc** que devuelve la **probabilidad** de churn.

# COMMAND ----------

import mlflow

class ChurnProb(mlflow.pyfunc.PythonModel):
    def __init__(self, model):
        self.model = model
    def predict(self, context, model_input):
        return self.model.predict_proba(model_input)[:, 1]

mlflow.set_registry_uri("databricks-uc")
signature = mlflow.models.infer_signature(X, pipe.predict_proba(X)[:, 1])

with mlflow.start_run(run_name="modelo_churn"):
    mlflow.log_metric("auc", auc)
    mlflow.pyfunc.log_model(
        artifact_path="model",
        python_model=ChurnProb(pipe),
        signature=signature,
        input_example=X.head(3),
        registered_model_name=MODEL,
    )
print("Modelo registrado:", MODEL)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Paso 4 — Generar la tabla de scores
# MAGIC Calculamos el score de todos los clientes y los clasificamos por **nivel de riesgo** + la **señal principal** detrás del riesgo. Esta tabla alimenta los dashboards y la app.

# COMMAND ----------

scores = df[["id_cliente", "segmento", "nombre_plan", "precio_mensual"]].copy()
scores["prob_churn"] = pipe.predict_proba(X)[:, 1]

# nivel de riesgo (umbrales fijos, interpretables)
def nivel(p):
    return "Alto" if p >= 0.50 else ("Medio" if p >= 0.25 else "Bajo")
scores["nivel_riesgo"] = scores["prob_churn"].apply(nivel)

# señal principal: el factor de riesgo que más se destaca (z-score orientado al riesgo)
z = (X[num] - X[num].mean()) / X[num].std(ddof=0)
senales = pd.DataFrame({
    "Bajo uso":              -z["uso_promedio"],
    "Morosidad":              z["pct_facturas_atraso"],
    "Insatisfacción (CSAT)": -z["csat_promedio"],
    "Detractor (NPS)":       -z["nps_promedio"],
})
scores["factor_principal"] = senales.idxmax(axis=1)
scores["prob_churn"] = scores["prob_churn"].astype(float).round(4)

spark.createDataFrame(scores).write.mode("overwrite").saveAsTable(SCORES)
print("Tabla de scores guardada:", SCORES)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Revisa el resultado

# COMMAND ----------

print(f"AUC (prueba): {auc:.3f}")

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC     nivel_riesgo,
# MAGIC     COUNT(*) AS clientes,
# MAGIC     ROUND(AVG(prob_churn), 3) AS prob_promedio
# MAGIC FROM dbacademy.${schema}.churn_scores
# MAGIC GROUP BY nivel_riesgo
# MAGIC ORDER BY prob_promedio DESC


# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC     *
# MAGIC FROM dbacademy.${schema}.churn_scores
# MAGIC ORDER BY prob_churn DESC
# MAGIC LIMIT 10
