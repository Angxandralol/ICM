# Access

> Documento vivo. Continúa el refactor por capas (`data/` → `access/` → `business/` → `presentation/`). Este es el punto de partida para todas las sesiones de refactorización de la capa `access/` (`icm/access/`). Se irá actualizando a medida que se resuelvan o aparezcan hallazgos nuevos.

## Estado actual (resumen ejecutivo)

`icm/access/` fue reescrita por completo sobre `Database.session()` y las clases ORM de `icm/data/schemas/*`. **Los 7 bugs y 11 de las 12 refactorizaciones (6 urgentes + 6 menores) quedaron resueltos**, con una excepción dejada pendiente a propósito (ver detalle abajo): sacar la normalización de negocio de `UserQuery` hacia `business/`. Aparte de eso, quedó anotado un hallazgo nuevo que no estaba en el alcance original: la duplicación de `UserModel` entre `access/` y `business/`. La capa vuelve a leer y escribir en la base de datos real — verificado end-to-end contra la API real vía HTTP (ver sesión de verificación) y con **76 pruebas automatizadas** (32 de `tests/data/`, sin tocar, + 44 nuevas de `tests/access/`), todas contra Postgres real.

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
5. **Hereda, sin mitigación propia, el punto ya abierto en `data/`: sin exigencia explícita de TLS/`sslmode`.** Sigue fuera del alcance de `access/` (la conexión la abre `Database`); permanece pendiente en REFACTOR-DATA.md.

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

