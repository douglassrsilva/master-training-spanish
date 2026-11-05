# 00 - Setup y teardown: Base compartida + Habilitación de la clase

![Ruta del Master Training con lo construido hasta el Ej. 00 resaltado](../assets/00%20-%20arquitetura.gif?v=20260928)

> _Resaltado, lo que ya construiste en la ruta hasta este punto; en gris, lo que todavía viene._

Un único notebook, que ejecuta una sola vez el **administrador de cuenta**, hace todo: prepara la clase (grupo, permisos, cómputo), carga la base compartida de churn y verifica que cada participante (y el workspace) esté listo. Es **idempotente**.

***El entrenamiento debe ejecutarse en el workspace corporativo, y no en Databricks Free Edition.***

!!! tip "Líderes de datos: mira el Setup guiado"
    Videos cortos sobre la dinámica del entrenamiento, la preparación del entorno y el envío de evidencias: **[Setup guiado](<Setup guiado/README.md>)**.

## Contenido

| Carpeta | Qué contiene |
|---------|--------------|
| `data/` | CSV de origen (dataset fijo, 1 por tabla). El setup los lee desde aquí. |
| `notebooks/` | `00_setup.py` (prepara la clase, carga los datos y verifica todo) y `00_teardown.py` (elimina los recursos al término del workshop) |

## Qué hace el Setup
> El setup es idempotente, así que puede ejecutarse varias veces

1. Crea el grupo `dbacademy_workshop` y agrega a los participantes
2. Crea el catálogo `dbacademy`
3. Crea los recursos de cómputo:
    - SQL Warehouse `dbacademy_workshop_wh`
    - Cluster multiuso `dbacademy_workshop_cluster`
4. Otorga los permisos al grupo:
    - `USE CATALOG` + `CREATE SCHEMA` en el catálogo
    - `USE SCHEMA` + `EXECUTE` en el schema `system.ai` (modelo del model service del Ej. 9)
    - `CAN_MANAGE` en el warehouse
    - `CAN_ATTACH_TO` en el cluster
5. Carga la base compartida en `dbacademy.churn` como solo lectura para los participantes:
    - Dimensiones `dim_cliente`, `dim_plan`, `dim_fecha` y hechos `hecho_suscripcion`, `hecho_uso`, `hecho_facturacion`, `hecho_ticket_soporte`
    - `feature_churn`: tabla analítica por cliente
    - Comentarios + claves en todas las tablas
    - Volumen `kb_volume` con la base de conocimiento (FAQ, Política de Retención, Playbook de CS)
    - Otorga a la clase `USE SCHEMA` + `SELECT` en el schema `churn` y `READ VOLUME` en `kb_volume`
6. Verifica:
    - Permisos por participante
    - Funcionalidades de IA usadas en los Ej. 4/6/7
7. Genera un informe final de preparación del workspace


## Pasos
> Es necesario ser administrador de cuenta para ejecutar el setup

1. **Clona el repositorio como Git folder.** En el workspace, ve a **Workspace → Create → Git folder** y pega la URL `https://github.com/douglassrsilva/master-training-spanish`. Autentícate con tu credencial de GitHub.
    - El repositorio es privado (GitHub EMU), por eso los CSV no se leen desde una URL pública de GitHub: el setup los toma de la carpeta `data/` del propio Git folder, porque el notebook se ejecuta desde su carpeta dentro del workspace.
    - Si necesitas leer los CSV desde otra ubicación, define `CSV_OVERRIDE` en la celda de configuración del notebook (URL o ruta absoluta).
2. Abre `00 - Setup y teardown/notebooks/00_setup.py` desde el Git folder (no lo importes por URL).
3. Ejecuta las dos primeras celdas para mostrar los widgets.
4. Selecciona a los participantes del entrenamiento. No es necesario cambiar los demás parámetros.
5. Haz clic en **Run all**.
    - Si obtienes el error `RuntimeError: Catálogo 'dbacademy' no puede crearse automáticamente` en la celda 11, crea el catálogo `dbacademy` manualmente con **Catalog → Create a catalog** y vuelve a ejecutar las celdas desde la 11.
6. Todas las celdas deben terminar con éxito.

> Si vas a participar en un entrenamiento con el equipo de Databricks, envía la evidencia de finalización del Setup a tu equipo de cuenta.

## Desmontaje (después del workshop)
> Es necesario ser administrador de cuenta para ejecutar el desmontaje

> ATENCIÓN: Antes de ejecutar el teardown, los endpoints de los agentes Supervisor deben eliminarse manualmente: Workspace > "Agents" > pasa el mouse sobre el agente > en la esquina derecha selecciona los 3 puntos > "Delete"

El notebook `00_teardown.py` revierte lo que creó el Setup. Es **idempotente** (los recursos que ya no existen se ignoran, por lo que es seguro volver a ejecutarlo).

### Qué hace el Desmontaje
Cada interruptor es `true`/`false`. Los valores por defecto eliminan los recursos **específicos del workshop**:

1. Elimina el grupo `dbacademy_workshop` (lo que también revoca todos los permisos otorgados a él)
2. Elimina el SQL Warehouse `dbacademy_workshop_wh`
3. Elimina el cluster multiuso `dbacademy_workshop_cluster`
4. **ELIMINAR CATÁLOGO** viene **desactivado** (`false`): el catálogo `dbacademy` pertenece al administrador y contiene tanto la base compartida `dbacademy.churn` (tablas + volumen `kb_volume`) como el schema personal `dbacademy.<username>` de cada participante. Actívalo (`true`) solo si el Setup creó el catálogo y el workshop terminó por completo, porque el `DROP CATALOG ... CASCADE` borra todo eso.

### Pasos
1. Clona el repositorio como Git folder (igual que en el Setup) y abre `00 - Setup y teardown/notebooks/00_teardown.py`.
2. Ejecuta las dos primeras celdas para mostrar los widgets.
3. Ajusta los interruptores según lo que quieras eliminar.
4. Haz clic en **Run all**.
5. Revisa el resultado en la sección **3. Informe final** (`✅ Desmontaje concluido`).
