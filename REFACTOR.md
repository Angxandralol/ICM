# REFACTOR.md — Refactor por capas

> Documento vivo. Índice general del refactor del backend, capa por capa, siguiendo el orden `data/` → `access/` → `business/` → `presentation/`. El detalle de cada capa (funcionamiento general, bugs encontrados, refactorizaciones urgentes/menores, análisis de seguridad, análisis de pruebas unitarias y comentarios extra) vive en su propio documento — ver "Índice de capas" abajo. Este archivo solo mantiene el resumen ejecutivo de "Estado general" y se actualiza a medida que se resuelven hallazgos o aparecen nuevos en cualquiera de las capas.

## Índice de capas

- [REFACTOR-DATA.md](REFACTOR-DATA.md) — capa `data/`.
- [REFACTOR-ACCESS.md](REFACTOR-ACCESS.md) — capa `access/`.
- [REFACTOR-BUSINESS.md](REFACTOR-BUSINESS.md) — capa `business/`.

## Estado general

- ✅ **`data/`** — migrada a SQLAlchemy ORM. 14/14 bugs y 16/17 refactorizaciones resueltos (queda pendiente, a propósito, un sistema de migraciones versionado con Alembic). 32 pruebas en `tests/data/`. Detalle en REFACTOR-DATA.md.
- ✅ **`access/`** — migrada a SQLAlchemy ORM sobre el `data/` ya migrado. 7/7 bugs y 11/12 refactorizaciones resueltos (queda pendiente, a propósito, sacar la normalización de negocio de `UserQuery` hacia `business/`). 44 pruebas nuevas en `tests/access/`. Detalle en REFACTOR-ACCESS.md.
- ⏳ **`business/`** — `api/`, `controllers/`, `cli/` y `models/` refactorizados (`ResponseCode` reemplazado por `BusinessError` + exception handler global), verificados (`/verify`) y con **123 pruebas nuevas** en `tests/business/`. 8/13 bugs (los 5 críticos: los 3 originales + 2 encontrados al escribir las pruebas, ambos ya resueltos) y 2/7 refactors urgentes resueltos; `updater/libs/{ping,snmp,ssh,host}.py` queda pendiente a propósito para una sub-sesión dedicada (concentra el resto de los hallazgos urgentes/seguridad, y sus pruebas). Detalle en REFACTOR-BUSINESS.md.
- ⏳ **`presentation/`** — pendiente, sin sesión programada todavía.

**Próximo paso concreto:** la sub-sesión de `updater/libs/{ping,snmp,ssh,host}.py` (dentro de `business/`) — es lo único que queda pendiente de todo lo que ya se empezó a trabajar. `presentation/` sigue sin ninguna sesión programada.
