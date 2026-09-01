# Capa `data/`

> Documento vivo. Este es el punto de partida para todas las sesiones de refactorización de la capa `data/` (`icm/data/`). Se irá actualizando a medida que se resuelvan o aparezcan hallazgos nuevos.

## Estado actual (resumen ejecutivo)

`icm/data/` ya fue migrada de SQL crudo (`psycopg2` + strings de DDL) a **SQLAlchemy ORM**, con motor y pool reales, un `Database.session()` de tipo Unit of Work para atomicidad, y **32 pruebas unitarias** (`tests/data/`) corriendo contra Postgres real. De los 14 bugs y 17 refactors (10 urgentes + 7 menores) que arrojó el análisis original, **todos quedaron resueltos excepto uno**, que se deja pendiente a propósito:

- **Alembic / migraciones versionadas** — pospuesto a una sesión futura; por ahora el esquema se recrea desde cero (`create_all`/`drop_all`).

El otro ítem que en su momento quedó pendiente — que `access/` adoptara el nuevo `Database.session()` — ya se completó en la sesión siguiente de este refactor por capas; ver REFACTOR-ACCESS.md.

El resto de este documento detalla, sección por sección, qué se resolvió y cómo, y qué le quedó pendiente a la capa en su momento (algunos ítems que en ese entonces no eran responsabilidad de `data/` ya se resolvieron después, en la sesión de `access/` — quedan marcados donde corresponde).

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

**Lo que le faltaba a `access/` para consumir esto** (resuelto en la sesión siguiente, nunca fue pendiente de `data/`): en su momento, `icm/access/querys/*.py` seguía construyendo SQL crudo a mano (`cursor.execute`/`cursor.copy_from`) contra los nombres de columna y tipos **viejos** (p. ej. `user_id` en vez de `username`, `ifIndex`/`ifHighSpeed` como texto). Esa capa se reescribió por completo sobre `Database.session()` y las clases ORM — ver REFACTOR-ACCESS.md.

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

**Pendientes en el alcance actual de `data/`: ninguno.** El bug relacionado que en su momento seguía abierto en el sistema (`copy_from` sin escape en `icm/access/*`, ver Seguridad #3 de esta sección) ya se resolvió en la sesión de `access/`.

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

**7 de 7 resueltas.**

1. ✅ Anotación de retorno de `Database.drop()`.
2. ✅ `make_url` en vez de `str.split("/")` para la URI.
3. ✅ **Resuelto en la sesión de `access/`:** el patrón repetido `if not self.database.connected: ...` / `close_connection()` vivía en `icm/access/querys/*.py`. Esa capa adoptó `Database.session()`, eliminando la duplicación equivalente.
4. ✅ Documentar la relación entre tablas — cada clase ORM tiene un docstring explicando su rol (truncado diario, historial que nunca se trunca, etc.).
5. ✅ `__all__` explícito en `icm/data/__init__.py`.
6. ✅ Constante nombrada para la base de mantenimiento (`_MAINTENANCE_DATABASE = "postgres"` en `database.py`).
7. ✅ Estilo de construcción de SQL unificado — ya no hay `*_SCHEMA` como strings de DDL; los únicos f-strings que quedan (`CheckConstraint`, nombres de `Index`) se arman exclusivamente a partir de constantes de código (`TableNames`, `*Field`), nunca de input, y quedó documentado en el propio código por qué es seguro.

---

## Análisis de Seguridad

1. **Privilegio excesivo del usuario de aplicación — reevaluado.** El código de `ensure_database_exists()` todavía intenta `CREATE DATABASE` si la base no existe (mismo diseño que antes). Sin embargo, al escribir las pruebas descubrimos que en la práctica **el rol `icm_user` ya no tiene privilegio `CREATEDB`** (se comprobó al intentar crear una base de test nueva: `permission denied to create database`). Es la postura correcta de mínimo privilegio, y el código la maneja con gracia (`ensure_database_exists()` retorna `False` y loguea el error en vez de crashear) — pero como consecuencia, **el aprovisionamiento de una base nueva (`icm database --start` contra una base que no existe) fallaría en este entorno** y necesitaría que alguien con más privilegio la cree una vez. Vale la pena decidir esto explícitamente (¿la app nunca debe poder crear bases, y el `CREATE DATABASE` inicial pasa a ser un paso de infraestructura separado?).
2. **Sin inyección SQL — mejorado por el ORM.** Los valores dinámicos ahora pasan exclusivamente por el ORM de SQLAlchemy (parametrizado automáticamente) o por `text()` con parámetros con nombre (`ensure_database_exists`). El único SQL armado con f-strings son los `CheckConstraint`/`Index` de los schemas y el `CREATE DATABASE {identificador}` (que no admite parámetros de identificador en SQL), y en ambos casos los valores interpolados son siempre constantes de código o vienen de `Configuration`, nunca de un usuario final.
3. ✅ **`copy_from` sin escape — resuelto en la sesión de `access/`.** `icm/access/querys/{change,interface,assignment}.py` usaba `cursor.copy_from(sep=";")` sin escapar valores que vienen de SNMP (`ifDescr`/`ifAlias`/`sysname`); no se tocó en esta sesión porque `access/` no era su alcance. Se resolvió reemplazando `copy_from` por `session.execute(insert(Schema), rows)` del ORM (parametrizado, no depende de un separador de texto) — verificado explícitamente con un valor conteniendo `;` sobreviviendo intacto.
4. **Sin exigencia explícita de TLS/`sslmode`.** Sigue igual: `Database` usa la URI de `.env` tal cual; no hay validación de que la conexión esté cifrada. Pendiente.
5. **Longitud de columna de password.** Sin cambios: `users.password VARCHAR(100)` es suficiente para un hash `bcrypt`. Verificación positiva, no requiere acción.
6. **Sin auditoría a nivel de esquema.** Sin cambios: no hay tabla ni columnas para registrar quién ejecutó operaciones destructivas. Pendiente, no abordado esta sesión.

---

## Análisis de Pruebas Unitarias

**Implementado.** `pytest` se agregó como dependencia de desarrollo (`pyproject.toml`, extra `dev`) y hay 32 pruebas en `tests/data/` (`test_database.py`, `test_user_schema.py`, `test_interface_schema.py`, `test_change_schema.py`, `test_assignment_schema.py`), todas contra Postgres real (se reutiliza la base de `.env`, `URI_POSTGRES`, nunca una mockeada — ver el docstring de `tests/conftest.py`). Cubren, entre otras cosas: los `CheckConstraint` de `status`/`role`/`type_status` (valores válidos e inválidos), las FKs de `assignments`/`changes`, el `UniqueConstraint` que cierra la condición de carrera de doble asignación (bug #10), que `Database.session()` hace rollback completo de una unidad de trabajo con dos escrituras si una falla (bug #3), y que `ensure_database_exists()`/`initialize()` son idempotentes. Correr con `pytest` desde la raíz del proyecto (usa el Postgres de `.env`, lo deja limpio pero sin los datos de `scripts/dev_seed.py` al terminar — re-sembrar si se necesita).

**Ya no pendiente:** las pruebas de los controllers/queries de `access/` se escribieron en su propia sesión — 44 pruebas nuevas en `tests/access/`, mismo criterio (Postgres real, nunca mocks). Ver REFACTOR-ACCESS.md.

---

## Comentarios extras

- **Decisiones ya tomadas** (quedan aquí por trazabilidad, ya no son preguntas abiertas): se adoptó SQLAlchemy como ORM (no se mantuvo SQL crudo); `icm/data/sql/setup.py` se eliminó en favor de `scripts/dev_seed.py`, fuera de `icm/`; Alembic se pospuso deliberadamente.
- **El orden recomendado para la sesión de `access/` se siguió tal cual:** adoptar `Database.session()` en cada query y reemplazar `copy_from` por inserciones ORM se hicieron juntos, en la misma sesión, porque tocaban los mismos archivos — resolvió de una vez la refactorización menor #3 y la Seguridad #3 de esta sección. Ver REFACTOR-ACCESS.md para el detalle.
- El hallazgo de Seguridad #1 (falta de `CREATEDB` en la práctica) sigue sin una decisión explícita tomada — conviene resolverlo antes de desplegar contra un Postgres que no sea el del propio contenedor: o se documenta que el aprovisionamiento inicial de la base es un paso manual/de infraestructura, o se acepta que `icm database --start` pueda fallar la primera vez si nadie le dio ese privilegio al rol de la app.

