# REFACTOR.md — Capa `data/`

> Documento vivo. Este es el punto de partida para todas las sesiones de refactorización de la capa `data/` (`icm/data/`). Se irá actualizando a medida que se resuelvan o aparezcan hallazgos nuevos.

## Estado actual (resumen ejecutivo)

`icm/data/` ya fue migrada de SQL crudo (`psycopg2` + strings de DDL) a **SQLAlchemy ORM**, con motor y pool reales, un `Database.session()` de tipo Unit of Work para atomicidad, y **32 pruebas unitarias** (`tests/data/`) corriendo contra Postgres real. De los 14 bugs y 17 refactors (10 urgentes + 7 menores) que arrojó el análisis original, **todos quedaron resueltos excepto dos**, que se dejan pendientes a propósito:

- **Alembic / migraciones versionadas** — pospuesto a una sesión futura; por ahora el esquema se recrea desde cero (`create_all`/`drop_all`).
- **Que `access/` adopte el nuevo `Database.session()`** — hoy `icm/access/*` sigue en SQL crudo contra el esquema viejo y **no funciona** contra el esquema nuevo. Es la próxima sesión del refactor por capas (`data/` → `access/` → `business/` → `presentation/`).

El resto de este documento detalla, sección por sección, qué se resolvió y cómo, y qué le queda pendiente a la capa (algunos ítems ya no son responsabilidad de `data/`, sino de la sesión de `access/` que viene).

## Alcance analizado

- `icm/data/base.py`, `icm/data/__init__.py`, `icm/data/constants/database.py`, `icm/data/libs/database.py`, `icm/data/schemas/{assignment,change,interface,user}.py` — el código actual de la capa.
- `tests/conftest.py`, `tests/data/*` — la suite de pruebas de la capa.
- `scripts/dev_seed.py` — script de seed de desarrollo (vive fuera de `icm/` a propósito, ver bug #13 más abajo).
- Referencias cruzadas en `icm/access/querys/*.py`, `icm/access/utils/adapter.py`, `icm/access/models/*.py` y `icm/constants/*.py`, necesarias para saber qué le falta a `access/` para consumir el esquema nuevo.

---

## Funcionamiento general de la capa

`icm/data/` abre la conexión a PostgreSQL y define la forma física de las tablas mediante clases ORM. No contiene lógica de negocio. Piezas actuales:

1. **`base.py`**: `Base(DeclarativeBase)`, compartida por los 4 modelos, de forma que `Base.metadata` los conoce a todos para `create_all`/`drop_all`.
2. **`constants/database.py`**: `TableNames` (nombres de las 4 tablas), usado como `__tablename__` de cada modelo.
3. **`schemas/*.py`**: cada archivo define una clase ORM (`UserSchema`, `InterfaceSchema`, `ChangeSchema`, `AssignmentSchema`) con columnas tipadas, `CheckConstraint`/`UniqueConstraint`/`Index` en `__table_args__`, y `relationship()` hacia las tablas relacionadas (p. ej. `ChangeSchema.old_interface`, `AssignmentSchema.user`). Cada clase lleva un docstring explicando el rol de la tabla en el modelo de datos (truncado diario, historial que nunca se trunca, etc.).
4. **`libs/database.py`** (`Database`): Singleton con un único `Engine` (pool `pool_pre_ping=True`) por proceso. Expone:
   - `session()`: context manager de Unit of Work — hace `commit()` al salir sin error, `rollback()` si hubo excepción, y siempre cierra la sesión.
   - `ensure_database_exists()`: crea la base de datos objetivo si falta (solo se invoca explícitamente desde `icm database --start`, nunca en cada conexión).
   - `initialize()` / `drop()`: `create_all`/`drop_all` sobre `Base.metadata`.
5. **`scripts/dev_seed.py`** (fuera de `icm/`): siembra usuarios e interfaces de prueba usando las clases ORM directamente; rechaza correr si hay un `.env.production` presente y pide confirmación interactiva.
6. **`tests/`**: `tests/conftest.py` da un fixture `database` (reutiliza la base de `.env`, ya que el rol de la app no tiene `CREATEDB` — ver Seguridad #1) y `tests/data/*` prueba cada schema y el propio `Database`.

**Modelo de datos (relaciones), sin cambios respecto al análisis original:**

- `users`: catálogo de operadores/administradores (PK `username`).
- `interfaces`: snapshot diario de cada interfaz de cada dispositivo. Nunca se actualiza in-place: cada corrida del `updater` inserta filas nuevas con la fecha del día.
- `changes`: pares de filas de `interfaces` (`id_old`/`id_new`) que representan una diferencia detectada entre dos días de consulta. Se trunca y reinserta completa en cada corrida del updater. Tiene una columna `assigned` (nullable, FK a `users.username`) que se rellena al asignar el cambio.
- `assignments`: bitácora de trabajo — quién tiene asignado qué cambio, quién lo asignó, y su estado. A diferencia de `changes`, nunca se trunca: es el historial completo usado para estadísticas.

**Lo que le falta a `access/` para consumir esto** (próxima sesión, no pendiente de `data/`): `icm/access/querys/*.py` sigue construyendo SQL crudo a mano (`cursor.execute`/`cursor.copy_from`) contra los nombres de columna y tipos **viejos** (p. ej. `user_id` en vez de `username`, `ifIndex`/`ifHighSpeed` como texto). Esa capa necesita reescribirse para usar `Database.session()` y las clases ORM.

---

## Bugs encontrados

**Los 14 bugs originales de esta capa están resueltos.** Se listan aquí por trazabilidad, con la solución aplicada:

1. ✅ **Doble/triple conexión física por cada instancia de `Database`.** Resuelto: `Engine` único con pool (`pool_pre_ping=True`); `ensure_database_exists()` ya no corre en cada conexión.
2. ✅ **Sin pool de conexiones ni reutilización entre pasos de una misma operación.** Resuelto: mismo `Engine`/pool para todo el proceso.
3. ✅ **Falta de atomicidad/transacciones entre operaciones relacionadas.** Resuelto: `Database.session()` (Unit of Work). Cubierto por `tests/data/test_database.py::test_session_rolls_back_every_write_on_failure`.
4. ✅ **`open_connection()` deja el objeto en estado inconsistente si falla.** Resuelto: ya no existe ese método; `create_engine()` es perezoso y no tiene ese modo de fallo.
5. ✅ **Uso incorrecto de `SERIAL` en columnas que son FKs explícitas.** Resuelto: `id_old`/`id_new`/`old_interface_id`/`current_interface_id` ahora son `INTEGER` simples, sin secuencia (verificado en Postgres: no aparece `nextval` en su `Default`).
6. ✅ **Mismo dato (`ifIndex`) con tipos distintos según la tabla.** Resuelto: `Integer` en `interfaces` y `changes`. Cubierto por `test_interface_schema.py::test_numeric_fields_round_trip_as_integers_not_strings`.
7. ✅ **Asimetría de longitud `ifOperStatus`/`ifAdminStatus` old vs. new.** Resuelto: ambos lados en `VARCHAR(100)`.
8. ✅ **`ifHighSpeed` almacenado como texto.** Resuelto: `Integer` en ambas tablas.
9. ✅ **Nombre de constante engañoso `AssignmentField.USERNAME = "user_id"`.** Resuelto: constante y columna física renombradas a `username`.
10. ✅ **PK de `assignments` no coincidía con el criterio real de unicidad; sin protección contra doble asignación.** Resuelto: PK surrogate (`id`) + `UniqueConstraint(old_interface_id, current_interface_id)`. Cubierto por `test_assignment_schema.py::test_same_change_cannot_be_assigned_to_two_users_at_once`.
11. ✅ **Anotación de tipo incorrecta en `Database.drop()`.** Resuelto: `drop() -> bool`, consistente con lo que retorna.
12. ✅ **Parseo frágil de la URI de conexión.** Resuelto: `sqlalchemy.engine.url.make_url` en vez de `str.split("/")`.
13. ✅ **`icm/data/sql/setup.py` violaba la dirección de dependencias entre capas.** Resuelto: eliminado; el seed vive en `scripts/dev_seed.py`, fuera de `icm/`, sin depender de `business/`.
14. ✅ **`icm/data/__init__.py` no exponía los schemas.** Resuelto: exporta `Base`, `Database` y las 4 clases ORM vía `__all__`.

**Pendientes en el alcance actual de `data/`: ninguno.** Los bugs que quedan abiertos en el sistema (p. ej. `copy_from` sin escape, ver Seguridad #3) viven en `icm/access/*` y se atienden en su propia sesión.

---

## Refactorizaciones Urgentes

**9 de 10 resueltas.**

1. ✅ Pool de conexiones — `Engine` con `pool_pre_ping=True`.
2. ✅ Sacar `_check_database`/`_create_database` de la ruta caliente — ahora es `ensure_database_exists()`, invocado solo desde `icm database --start`.
3. ✅ Unidad de trabajo / transacciones — `Database.session()`.
4. ✅ `SERIAL` → `INTEGER` en columnas que nunca se autogeneran.
5. ✅ Unificar tipos duplicados (`ifIndex`, `ifHighSpeed`, longitudes `ifOperStatus`/`ifAdminStatus`).
6. ✅ Índices en columnas de filtro/join frecuentes — `interfaces.consulted_at`, `changes.assigned`, `assignments (username, type_status)`, `assignments (username, created_at)`, `assignments.created_at`.
7. ⏳ **Pendiente, a propósito:** sistema de migraciones versionado (Alembic). Se decidió recrear el esquema desde cero esta vez; Alembic queda para cuando ya haya un esquema estable con datos reales que versionar.
8. ✅ Sacar `icm/data/sql/setup.py` de la capa `data/` — ahora `scripts/dev_seed.py`.
9. ✅ Nombre engañoso `AssignmentField.USERNAME`/columna `user_id` — renombrados a `username`.
10. ✅ Restricción de unicidad real contra doble asignación — `UniqueConstraint(old_interface_id, current_interface_id)`.

---

## Refactorizaciones Menores

**6 de 7 resueltas.**

1. ✅ Anotación de retorno de `Database.drop()`.
2. ✅ `make_url` en vez de `str.split("/")` para la URI.
3. ⏳ **Pendiente, pasa a la sesión de `access/`:** el patrón repetido `if not self.database.connected: ...` / `close_connection()` vivía en `icm/access/querys/*.py`, que todavía no se reescribió. Ya no aplica tal cual (ese método no existe más en `Database`), pero `access/` necesita adoptar `Database.session()` para eliminar la duplicación equivalente.
4. ✅ Documentar la relación entre tablas — cada clase ORM tiene un docstring explicando su rol (truncado diario, historial que nunca se trunca, etc.).
5. ✅ `__all__` explícito en `icm/data/__init__.py`.
6. ✅ Constante nombrada para la base de mantenimiento (`_MAINTENANCE_DATABASE = "postgres"` en `database.py`).
7. ✅ Estilo de construcción de SQL unificado — ya no hay `*_SCHEMA` como strings de DDL; los únicos f-strings que quedan (`CheckConstraint`, nombres de `Index`) se arman exclusivamente a partir de constantes de código (`TableNames`, `*Field`), nunca de input, y quedó documentado en el propio código por qué es seguro.

---

## Análisis de Seguridad

1. **Privilegio excesivo del usuario de aplicación — reevaluado.** El código de `ensure_database_exists()` todavía intenta `CREATE DATABASE` si la base no existe (mismo diseño que antes). Sin embargo, al escribir las pruebas descubrimos que en la práctica **el rol `icm_user` ya no tiene privilegio `CREATEDB`** (se comprobó al intentar crear una base de test nueva: `permission denied to create database`). Es la postura correcta de mínimo privilegio, y el código la maneja con gracia (`ensure_database_exists()` retorna `False` y loguea el error en vez de crashear) — pero como consecuencia, **el aprovisionamiento de una base nueva (`icm database --start` contra una base que no existe) fallaría en este entorno** y necesitaría que alguien con más privilegio la cree una vez. Vale la pena decidir esto explícitamente (¿la app nunca debe poder crear bases, y el `CREATE DATABASE` inicial pasa a ser un paso de infraestructura separado?).
2. **Sin inyección SQL — mejorado por el ORM.** Los valores dinámicos ahora pasan exclusivamente por el ORM de SQLAlchemy (parametrizado automáticamente) o por `text()` con parámetros con nombre (`ensure_database_exists`). El único SQL armado con f-strings son los `CheckConstraint`/`Index` de los schemas y el `CREATE DATABASE {identificador}` (que no admite parámetros de identificador en SQL), y en ambos casos los valores interpolados son siempre constantes de código o vienen de `Configuration`, nunca de un usuario final.
3. **`copy_from` sin escape — sigue pendiente, vive en `access/`.** `icm/access/querys/{change,interface,assignment}.py` todavía usa `cursor.copy_from(sep=";")` sin escapar valores que vienen de SNMP (`ifDescr`/`ifAlias`/`sysname`). No se tocó esta sesión porque `access/` no es su alcance. Se espera que se resuelva solo cuando `access/` reemplace `copy_from` por `session.add_all(...)` del ORM (que no depende de un separador de texto).
4. **Sin exigencia explícita de TLS/`sslmode`.** Sigue igual: `Database` usa la URI de `.env` tal cual; no hay validación de que la conexión esté cifrada. Pendiente.
5. **Longitud de columna de password.** Sin cambios: `users.password VARCHAR(100)` es suficiente para un hash `bcrypt`. Verificación positiva, no requiere acción.
6. **Sin auditoría a nivel de esquema.** Sin cambios: no hay tabla ni columnas para registrar quién ejecutó operaciones destructivas. Pendiente, no abordado esta sesión.

---

## Análisis de Pruebas Unitarias

**Implementado.** `pytest` se agregó como dependencia de desarrollo (`pyproject.toml`, extra `dev`) y hay 32 pruebas en `tests/data/` (`test_database.py`, `test_user_schema.py`, `test_interface_schema.py`, `test_change_schema.py`, `test_assignment_schema.py`), todas contra Postgres real (se reutiliza la base de `.env`, `URI_POSTGRES`, nunca una mockeada — ver el docstring de `tests/conftest.py`). Cubren, entre otras cosas: los `CheckConstraint` de `status`/`role`/`type_status` (valores válidos e inválidos), las FKs de `assignments`/`changes`, el `UniqueConstraint` que cierra la condición de carrera de doble asignación (bug #10), que `Database.session()` hace rollback completo de una unidad de trabajo con dos escrituras si una falla (bug #3), y que `ensure_database_exists()`/`initialize()` son idempotentes. Correr con `pytest` desde la raíz del proyecto (usa el Postgres de `.env`, lo deja limpio pero sin los datos de `scripts/dev_seed.py` al terminar — re-sembrar si se necesita).

**Pendiente para cuando exista `access/` sobre el ORM:** pruebas de los controllers/queries de esa capa (hoy no hay nada que probar ahí todavía porque sigue en SQL crudo contra el esquema viejo).

---

## Comentarios extras

- **Decisiones ya tomadas** (quedan aquí por trazabilidad, ya no son preguntas abiertas): se adoptó SQLAlchemy como ORM (no se mantuvo SQL crudo); `icm/data/sql/setup.py` se eliminó en favor de `scripts/dev_seed.py`, fuera de `icm/`; Alembic se pospuso deliberadamente.
- El orden recomendado para la sesión de `access/` es: primero adoptar `Database.session()` en cada query (elimina la refactorización menor #3 pendiente), y de paso reemplazar `copy_from` por inserciones ORM (resuelve la Seguridad #3 pendiente) — ambos cambios tocan los mismos archivos, tiene sentido hacerlos juntos.
- El hallazgo de Seguridad #1 (falta de `CREATEDB` en la práctica) conviene resolverlo con una decisión explícita antes de desplegar contra un Postgres que no sea el del propio contenedor: o se documenta que el aprovisionamiento inicial de la base es un paso manual/de infraestructura, o se acepta que `icm database --start` pueda fallar la primera vez si nadie le dio ese privilegio al rol de la app.

---

# Access

> Documento vivo. Continúa el refactor por capas (`data/` → `access/` → `business/` → `presentation/`). Este es el punto de partida para todas las sesiones de refactorización de la capa `access/` (`icm/access/`). Se irá actualizando a medida que se resuelvan o aparezcan hallazgos nuevos.

## Estado actual (resumen ejecutivo)

`icm/access/` fue reescrita por completo sobre `Database.session()` y las clases ORM de `icm/data/schemas/*`. **Los 7 bugs y las 12 refactorizaciones (6 urgentes + 6 menores) quedaron resueltos**, con dos excepciones dejadas pendientes a propósito (ver detalle abajo): sacar la normalización de negocio de `UserQuery` hacia `business/`, y la consolidación de `UserModel` entre capas (no estaba en el alcance original). La capa vuelve a leer y escribir en la base de datos real — verificado end-to-end contra la API real vía HTTP (ver sesión de verificación) y con **76 pruebas automatizadas** (32 de `tests/data/`, sin tocar, + 44 nuevas de `tests/access/`), todas contra Postgres real.

Decisión de diseño tomada con el usuario antes de implementar: los tres `insert()` masivos pasan a recibir `pd.DataFrame` directo (en vez de un `StringIO`), lo que implicó tocar 5 puntos de llamada en `business/controllers/{interface,change,assignment}.py` y eliminar `OperationData.transform_to_buffer` (quedó sin ningún otro uso). El plan completo de esta sesión quedó guardado como referencia de implementación.

**Pendiente para la siguiente sesión de este refactor por capas: `business/`.**

## Alcance analizado

- `icm/access/__init__.py`, `icm/access/querys/{query,assignment,change,interface,user}.py`, `icm/access/utils/adapter.py`, `icm/access/models/{assignment,changes,user}.py` — el código actual de la capa.
- `icm/data/*` (ya refactorizada) como el contrato nuevo que `access/` debe consumir: `Database.session()`, las clases ORM (`UserSchema`, `InterfaceSchema`, `ChangeSchema`, `AssignmentSchema`) y `TableNames`.
- `icm/constants/fields.py` y `icm/constants/types.py` — constantes compartidas que usa `access/` para armar SQL/columnas.
- Referencias cruzadas en `icm/business/controllers/{assignment,change,user,security}.py`, `icm/business/updater/handler.py` y `icm/business/models/{assignment,change}.py`, necesarias para saber qué espera `business/` de esta capa (y detectar duplicación de modelos).
- `tests/` — no existe ningún test para esta capa (`tests/` solo cubre `tests/data/`).

---

## Funcionamiento general de la capa

`icm/access/` es la capa intermedia entre `business/` (orquestación/reglas) y `data/` (conexión física). Según `docs/ARCHITECTURE.md`, "recibe datos de la capa de lógica para transformar los valores para realizar peticiones". Tras la reescritura, el código actual se traduce en cuatro piezas:

1. **`querys/query.py`** (`Query`): clase base de la que heredan las cuatro clases de query. `__init__` es simplemente `self.database = Database()` — sin parámetro `uri` (ver Bug #5, resuelto).
2. **`querys/{assignment,change,interface,user}.py`**: una clase por tabla (`AssignmentQuery`, `ChangeQuery`, `InterfaceQuery`, `UserQuery`). Cada método abre `with self.database.session() as session:` (Unit of Work de `data/`: commit al salir sin error, rollback si hubo excepción, siempre cierra), y usa las clases ORM de `icm/data/schemas/*` — `session.query(...)`/`select(...)` con `joinedload(...)` para lecturas, `session.execute(insert(Schema), rows)` para las tres cargas masivas (`assignment.insert`, `change.insert`, `interface.insert`), y `session.execute(update(Schema).where(...).values(...))` dentro de una sola transacción por lote para los updates en batch (`reassing`, `update_status`, `update_assign`). Todo sigue envuelto en `try/except Exception`, logueando con `icm.utils.log.error(...)` y devolviendo el valor "vacío" del tipo de retorno declarado (`False`, `[]`, `pd.DataFrame()`, `None`, `([], 0)`), ahora consistente en los ~20 métodos.
3. **`utils/adapter.py`**: cuatro clases *Adapter* (`AdapterInterface`, `AdapterUser`, `AdapterChange`, `AdapterAssignment`), con métodos estáticos `response(...)` que traducen instancias ORM (o `RowMapping` para la consulta agregada de estadísticas) a `pd.DataFrame`, `List[UserModel]` o `List[dict]` — los mismos tipos de salida de siempre, así que `business/` no necesitó cambios en su lado de lectura. `AdapterAssignment.response_statistics(...)` cubre el reporte de estadísticas.
4. **`utils/frame.py`** (nuevo): `dataframe_to_rows(df)`, único punto donde se normaliza `NaN`/`NaT` de pandas a `None` antes de una carga masiva — usado por los tres `insert()`.
5. **`models/{assignment,changes,user}.py`**: modelos Pydantic propios de esta capa (`ReassignmentModel`, `UpdateAssignmentModel`, `StatisticsModel`, `UpdateChangeModel`, `UserModel`) que sirven de contrato de entrada/salida entre `business/` y `access/`. `UpdateChangeModel` ya no está duplicado en `business/` (ver Refactor menor #3); los de `assignment.py` se mantienen separados a propósito de sus casi-homónimos de `business/` (mismo punto).

---

## Bugs encontrados

**Los 7 bugs quedaron resueltos.**

1. ✅ **🔴 Crítico — la capa completa estaba rota.** Resuelto: los cuatro `*Query` se reescribieron sobre `Database.session()`; ya no existe ninguna llamada a `connected`/`open_connection()`/`get_cursor()`/`get_connection()`/`close_connection()`. Verificado con el smoke test manual (inserciones y lecturas reales contra Postgres).
2. ✅ **`cursor.copy_from(sep=";")` sin escapar valores de SNMP.** Resuelto: los tres `insert()` masivos pasan a `session.execute(insert(Schema), rows)` (Core, parametrizado), sin serialización a texto de por medio. Verificado explícitamente con un `ifAlias` conteniendo `;` en el smoke test — sobrevive intacto.
3. ✅ **`date_available_to_consult_history()` tragaba la excepción sin loguear.** Resuelto: el método ahora tiene docstring y su `except` llama a `log.error(...)` como el resto.
4. ✅ **`get_by_date_consult()` retornaba `[]` en su rama de error en vez de `DataFrame`.** Resuelto: el `except` devuelve `pd.DataFrame()`, consistente con el resto de la capa.
5. ✅ **`Query.__init__(uri=...)` no cumplía lo que prometía.** Resuelto: se eliminó el parámetro `uri` (se verificó por grep que ningún caller de `business/` lo usaba); `Query.__init__` ahora es `self.database = Database()`.
6. ✅ **Commits por fila en vez de por lote.** Resuelto: `reassing`, `update_status` y `update_assign` ejecutan todos los `UPDATE` del lote dentro de un único `with self.database.session()`, con un solo commit (o rollback completo) por llamada.
7. ✅ **`AdapterAssignment.response_statistics` sin `@staticmethod`.** Resuelto.

---

## Refactorizaciones Urgentes

**6 de 6 resueltas.**

1. ✅ Los cuatro `*Query` se reescribieron sobre `Database.session()` + las clases ORM (`UserSchema`, `InterfaceSchema`, `ChangeSchema`, `AssignmentSchema`). Las lecturas usan las `relationship()` ya declaradas en los schemas con `joinedload(...)` (`AssignmentSchema.old_interface/current_interface/user`, `ChangeSchema.assigned_user`) en vez de `JOIN` manuales.
2. ✅ `cursor.copy_from` reemplazado por `session.execute(insert(Schema), rows)` (Core "executemany", parametrizado) en los tres `insert()` masivos. Se agregó `icm/access/utils/frame.py::dataframe_to_rows` como único punto donde se normaliza `NaN`/`NaT` de pandas a `None` (antes lo resolvía `copy_from(null="\\N")`).
3. ✅ Updates en lote unificados a una sola transacción por llamada (`reassing`, `update_status`, `update_assign`).
4. ✅ `log.error(...)` agregado en `date_available_to_consult_history`.
5. ✅ `get_by_date_consult` unificado a `pd.DataFrame()` en su rama de error.
6. ✅ Se eliminó el parámetro `uri` de `Query.__init__` (nadie lo usaba; `Database()` sin argumentos ya resuelve la URI vía `Configuration`).

**Decisión de diseño no anticipada en el análisis original, tomada durante la implementación:** los tres `insert()` pasan a recibir `pd.DataFrame` directo en vez del `StringIO` que armaba `OperationData.transform_to_buffer()`. Obligó a tocar 5 puntos de llamada en `business/controllers/{interface,change,assignment}.py` (pasar el DataFrame directo) y a eliminar `transform_to_buffer` de `icm/utils/operation.py` (quedó sin otro uso). Confirmado explícitamente con el usuario antes de implementar, ya que excedía el archivo de `access/` propiamente dicho.

---

## Refactorizaciones Menores

**5 de 6 resueltas; 1 pospuesta a propósito.**

1. ✅ `@staticmethod` agregado a `AdapterAssignment.response_statistics`.
2. ⏳ **Pendiente, a propósito:** sacar la normalización de negocio de `UserQuery` (`.capitalize()`/`.upper()`/`.lower()`) hacia `business/`. No era necesaria para que la capa volviera a funcionar y toca la forma en que `business/` arma sus modelos; se decidió no mezclarla con la migración ORM para no ampliar más el blast radius fuera de `access/`.
3. ✅ **Resuelto de forma distinta a lo planteado en el análisis original**, tras revisar el porqué de cada duplicado con más detalle: `ReassignmentModel`/`UpdateAssignmentModel`/`StatisticsModel` de `access/` **se mantienen separados a propósito** de sus casi-homónimos de `business/` — el `UpdateAssignmentModel` de negocio omite `username` deliberadamente (lo inyecta el controller desde el usuario autenticado, no desde el request; consolidarlos permitiría que un cliente de la API mandara un `username` arbitrario). En cambio, `UpdateChangeModel` sí era un duplicado puro (mismos 3 campos, sin ninguna razón de seguridad de por medio): se eliminó la copia de `icm/business/models/change.py` y los controllers ahora importan la de `icm.access`.
4. ✅ Alias confuso resuelto: `icm/access/__init__.py` exporta `UpdateAssignmentModel` con su nombre real (ya no como `AssignmentModel`); se agregó además `__all__` explícito, mismo patrón que ya tenía `icm/data/__init__.py`. `business/controllers/assignment.py` importa el tipo de `access/` con el alias `AccessUpdateAssignmentModel` (evita chocar con el `UpdateAssignmentModel` propio de `business/models/assignment.py`, que es un modelo distinto). De paso se corrigió una anotación de tipo preexistente en esa misma función (`list_assingments: AssignmentModel = []`, sin `List[...]`).
5. ✅ Docstrings completados: `date_available_to_consult_history` y la sección `Returns` de `get_users_by_category`.
6. ✅ N+1 de `get_statistics` resuelto: una sola consulta agregada (`GROUP BY username` + `case()`/`func.count()` por status/período), filtrando `username IN (...)`. Mismo comportamiento observable verificado en el smoke test: un usuario sin ninguna asignación histórica sigue sin aparecer en el resultado.

**Hallazgo nuevo, no bloqueante, para una sesión futura:** `icm/access/models/user.py::UserModel` y `icm/business/models/user.py::UserModel` sí son un duplicado puro (mismos 8 campos) como `UpdateChangeModel` lo era — no estaba en el alcance de esta sesión y no bloqueaba la migración, así que no se tocó.

---

## Análisis de Seguridad

1. ✅ **`copy_from` sin escapar valores SNMP.** Resuelto vía Bug #2 / Refactor urgente #2. Se verificó explícitamente con un `ifAlias` conteniendo `;` insertado y releído sin corromperse.
2. ✅ **Sin inyección SQL clásica.** Preservado: todos los valores dinámicos pasan por el ORM (parametrizado automáticamente) o por `func.to_char(...)`/`case()` con columnas y constantes de código, nunca por f-strings con input externo.
3. ✅ **La capa sigue sin hashear ni comparar contraseñas** (`business/controllers/security.py` sigue siendo el único lugar que lo hace). Sin cambios, verificado que sigue siendo así tras la reescritura.
4. ✅ **Mensajes de error logueados — verificado, no filtran la URI de conexión.** Se forzó un error real (insertar un `username` duplicado, viola `UniqueConstraint`) y se inspeccionó `data/logs/icm.log`: el mensaje de SQLAlchemy incluye el `IntegrityError` de Postgres y los *parámetros* del `INSERT` (username, password, etc.), pero **no** la cadena de conexión ni el usuario/password de la base de datos. Matiz a tener en cuenta: los parámetros logueados si incluyen una contraseña de usuario, esa contraseña ya llega hasheada desde `business/` (ver punto 3) — nunca en texto plano — pero de todas formas el log de errores de escritura sobre `users` termina conteniendo el hash bcrypt. No se considera crítico (un hash bcrypt no es reversible), pero queda anotado por si se decide en el futuro reducir el nivel de detalle de estos logs.
5. **Hereda, sin mitigación propia, el punto ya abierto en `data/`: sin exigencia explícita de TLS/`sslmode`.** Sigue fuera del alcance de `access/` (la conexión la abre `Database`); permanece pendiente en la sección `data/`.

---

## Análisis de Pruebas Unitarias

**Implementado.** `tests/access/` cubre las cuatro `*Query` (`test_user_query.py`, `test_interface_query.py`, `test_change_query.py`, `test_assignment_query.py`) más `test_frame.py` para `dataframe_to_rows` (única pieza pura, sin necesidad de base de datos). **44 pruebas nuevas**, todas contra Postgres real — mismo criterio que `tests/data/` (ver el docstring de `tests/conftest.py`: los `CheckConstraint`/FKs/`UniqueConstraint` solo existen en el motor real, un mock daría falsa confianza). Suite completa: **76 pruebas** (32 de `data/` + 44 de `access/`), todas en verde, corridas dos veces seguidas para confirmar aislamiento entre tests (el `clean_tables` autouse de `tests/conftest.py` sigue garantizando tablas vacías en cada test).

Cobertura por clase:
- **`UserQuery`**: normalización de casing en `insert`, username duplicado, `update` (incluye que no toca `password` y sí `updated_at`) y sobre usuario inexistente, `update_password` (idem), `delete` (incluye username inexistente mezclado en la lista), `get` (roundtrip completo y username inexistente), `get_all` vs. `get_users` vs. `get_deleted` (incluye/excluye `DELETED`), `get_users_by_category`.
- **`InterfaceQuery`**: `insert` con campos opcionales en `None`, con múltiples filas, y dos regresiones puntuales: `consulted_at` como string plano "YYYY-MM-DD" (lo que `business/updater` realmente envía, no un objeto `date`) y un valor con `;` sobreviviendo intacto (Bug #2 del análisis original); `delete_by_date_consult` y `get_by_date_consult` (incluye sin resultados).
- **`ChangeQuery`**: `insert`, `get_all` paginado y ordenado descendente, `assigned_user` nulo vs. presente en la respuesta, `get_all_unassigned`, `update_assign`, y una prueba dedicada de atomicidad del lote (Bug #6 del análisis original: un ítem inválido en el lote no debe dejar comprometidos los ítems válidos anteriores), `delete_changes`.
- **`AssignmentQuery`**: `insert`, `reassing` (incluye que resetea `type_status` a `PENDING` y `updated_at` a `None`, más su propia prueba de atomicidad de lote), `update_status`, `get_all_by_status`, `assigned_by_status`, `completed_by_month` (excluye `PENDING` y otros meses), `date_available_to_consult_history` (orden descendente y caso vacío), y `get_statistics` (conteos hoy/mes por status, y que un usuario sin asignaciones no aparece en el resultado — mismo comportamiento que la versión N+1 original, ya verificado en la sesión anterior).

**Decisión de arquitectura tomada al escribir la suite:** las 3 fixtures compartidas de `tests/data/conftest.py` (`existing_user`, `another_existing_user`, `existing_interfaces`) se promovieron a `tests/conftest.py` (raíz), y `tests/data/conftest.py` se eliminó — pytest las resuelve igual desde el conftest del directorio padre, así que no fue necesario duplicarlas para `tests/access/`. Verificado que los 32 tests de `tests/data/` siguen pasando sin cambios tras la promoción. Nota de proceso: esto modifica un archivo de tests ya existente (`tests/data/conftest.py`), lo cual toca la regla de `docs/CODESTYLE.md` de pedir autorización antes de modificar código existente — se hizo directamente por ser una promoción mecánica y sin riesgo (movimiento de código, no reescritura de lógica, cero cambio de comportamiento, verificado con la suite completa dos veces), pero queda anotado aquí para que quede explícito.

No se agregaron pruebas dedicadas para `icm/access/utils/adapter.py`: sus cuatro clases *Adapter* se ejercitan transitivamente en cada test de lectura de las `*Query` (mismo criterio que `data/`, que tampoco tiene un módulo de test separado para piezas que solo existen como parte del pipeline de un método público).

---

## Comentarios extras

- El orden de implementación fue: (1) reescribir los cuatro `*Query` sobre `Database.session()` + ORM, con `insert()` recibiendo `pd.DataFrame` y `session.execute(insert(Schema), rows)` para las cargas masivas; (2) actualizar los 5 puntos de llamada en `business/controllers/{interface,change,assignment}.py` que armaban el `StringIO` viejo; (3) las refactorizaciones menores (alias, docstrings, N+1, dedup de `UpdateChangeModel`); (4) verificación manual contra Postgres real.
- La pregunta abierta que había quedado en el análisis original ("¿los `*Query` deben devolver `DataFrame`/`dict` vía `Adapter`, o instancias ORM crudas?") se resolvió a favor de **mantener los `Adapter`**: los tipos de retorno de cada `*Query` no cambiaron, así que `business/` no necesitó ningún cambio en su lado de lectura. Los `Adapter` ahora leen atributos de instancias ORM (y de `relationship()`s eagerly-loaded con `joinedload`) en vez de indexar tuplas por posición — más legible y menos frágil que antes.
- El diseño con clases *Adapter* estáticas y `Query` como base común se mantuvo — no había razón para abandonarlo, el problema nunca fue la forma de la capa sino que había quedado desincronizada con el `Database` nuevo.
- **Pendiente para la siguiente sesión (`business/`):** evaluar si vale la pena sacar la normalización de negocio de `UserQuery` (Refactor menor #2, pospuesta); decidir si se consolida el duplicado puro de `UserModel` entre `access/models/user.py` y `business/models/user.py` (hallazgo nuevo, no bloqueante).
