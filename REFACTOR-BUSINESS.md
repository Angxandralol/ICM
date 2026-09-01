# Business — Pendiente

> Todo lo que falta en `icm/business/`. Un ítem se elimina de este archivo en cuanto se corrige. Numeración heredada de `REFACTOR.md` para mantener referencias cruzadas.

## Bugs

- **Bug #6** — `controllers/assignment.py::reassign`/`update_status_assignment` (y `access/querys/assignment.py`): los `UPDATE` no verifican rowcount; una reasignación a un dueño incorrecto puede dejar `assignments`/`changes` inconsistentes sin lanzar error.

## Refactorizaciones Urgentes

- Implementar el modo `modern` (PySNMP) en `updater/libs/{ping,snmp}.py` — ya existen `PingClient`/`SnmpClient` (interfaz) y `get_ping_client()`/`get_snmp_client()` (factory) listos para la segunda implementación; el modo `legacy` actual sigue dependiendo de un parser de texto frágil ante variaciones de formato de `snmpwalk`.
- Loguear el traceback (no solo `str(error)`) y separar errores de programación de errores de negocio esperados en los `except Exception` de `controllers/`.


## Refactorizaciones Menores

- `controllers/user.py::update_user` arma un `UserModel` completo con `password=""` solo para descartarlo — requiere cambiar la firma de `UserQuery.update` en `access/`.
- Dejar de sombrear `error` (`except Exception as error: error = str(error)...`) en los `except` de `controllers/`.

## Seguridad

- `paramiko.AutoAddPolicy()` sin verificación de host key — `updater/libs/ssh.py`.
- `UserCLI.restore_password` genera la contraseña temporal con el módulo `random` (`Configuration.generate_default_password()`, en `icm/utils/config.py`) — no criptográficamente seguro, usar `secrets`.
- Tokens JWT de 9 horas sin mecanismo de revocación ni refresh token.

## Pruebas Unitarias

- `updater/` (`handler.py` + `libs/`) sin pruebas — necesita mocks de `multiprocessing`/SSH/SNMP.
