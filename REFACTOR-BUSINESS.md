# Business — Pendiente

> Todo lo que falta en `icm/business/`. Un ítem se elimina de este archivo en cuanto se corrige. Numeración heredada de `REFACTOR.md` para mantener referencias cruzadas.

## Bugs

- **Bug #2** — `updater/libs/ping.py` y `updater/libs/snmp.py`: `host`/`community`/comando se interpolan sin escapar en `exec_command()` (comandos de shell remotos) → riesgo de inyección de comandos.
- **Bug #6** — `controllers/assignment.py::reassign`/`update_status_assignment` (y `access/querys/assignment.py`): los `UPDATE` no verifican rowcount; una reasignación a un dueño incorrecto puede dejar `assignments`/`changes` inconsistentes sin lanzar error.
- **Bug #8** — `updater/libs/snmp.py::get_sysname`: si el comando remoto falla sin excepción, falta el `return` explícito → devuelve `None` en vez de `""`.
- **Bug #9** — `updater/libs/ssh.py::_ssh_jump`: si un salto SSH intermedio falla, los clientes ya conectados no se cierran ni se limpian de `self._client` → fuga de conexiones en cada reintento.
- **Bug #11** — `updater/libs/host.py::get_info_interfaces`: si falla la consulta SNMP de un campo puntual, la columna no se agrega (en vez de quedar `NaN`) → puede romper la validación de header al concatenar dispositivos.

## Refactorizaciones Urgentes

- Sanitizar la interpolación de comandos SSH remotos en `updater/libs/{ping,snmp}.py` (ver Bug #2), o migrar a una librería SNMP nativa (pysnmp).
- Agregar timeouts de red en `SSHClient.connect()`/`exec_command()` — `updater/libs/{ssh,ping,snmp}.py`.
- Reemplazar el parser de texto de `SnmpHandler._transform_response*` (frágil ante valores con `=`/`.`) por una librería SNMP estructurada.
- Reducir los 8 round-trips SSH+SNMP secuenciales por dispositivo (`host.py`/`snmp.py`) a una consulta bulk multi-OID.
- Loguear el traceback (no solo `str(error)`) y separar errores de programación de errores de negocio esperados en los `except Exception` de `controllers/`.
- Reemplazar `paramiko.AutoAddPolicy()` en `updater/libs/ssh.py::_ssh_jump` por verificación de host key.

## Refactorizaciones Menores

- `controllers/user.py::update_user` arma un `UserModel` completo con `password=""` solo para descartarlo — requiere cambiar la firma de `UserQuery.update` en `access/`.
- Dejar de sombrear `error` (`except Exception as error: error = str(error)...`) en los `except` de `controllers/` y `updater/`.

## Seguridad

- Inyección de comandos SSH en `updater/libs/{ping,snmp}.py` (Bug #2).
- `paramiko.AutoAddPolicy()` sin verificación de host key — `updater/libs/ssh.py`.
- `UserCLI.restore_password` genera la contraseña temporal con el módulo `random` (`Configuration.generate_default_password()`, en `icm/utils/config.py`) — no criptográficamente seguro, usar `secrets`.
- Tokens JWT de 9 horas sin mecanismo de revocación ni refresh token.

## Pruebas Unitarias

- `updater/` (`handler.py` + `libs/`) sin pruebas — necesita mocks de `multiprocessing`/SSH/SNMP.
