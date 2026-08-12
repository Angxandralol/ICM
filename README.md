# Interface Change Monitor - Monitor de Cambios de Interfaces
<div align="center">
  <img src="./presentation/public/logo.png" alt="ConvX Logo" width="180"/>

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.13%2B-blue)
![Node.js](https://img.shields.io/badge/node-v24.0.0-green)
![NPM](https://img.shields.io/badge/npm-v11.3-red)
![PM2](https://img.shields.io/badge/pm2-v6.0-blue)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)


</div>

# ¿Qué es ICM?
![ICM](./docs/icm.png)

El sistema ICM está diseñado para el monitoreo automatizado de cambios en las interfaces de dispositivos dentro de una red. Permite realizar consultas a distintos equipos de red, detectando modificaciones en sus interfaces y generando alertas para su revisión. Sus funcionalidades incluyen:

- **Monitoreo de Cambios**: Escanea dispositivos de red y detecta cambios en las interfaces.
- **Control de usuarios**: Permite administrar operadores y asignarles interfaces con cambios para su revisión y seguimiento.
- **Seguimiento de asignaciones**: Actualiza el estado de las alertas (pendientes, revisadas, redescubiertas).
- **Estadísticas y reportes**: Genera métricas sobre interfaces monitoreadas, cambios detectados y eficiencia en la gestión.

# Índice
- [Documentación](#documentación)
- [Requisitos](#requisitos)
    - [Variables de Entorno](#variables-de-entorno)
- [Instalación](#instalación)
    - [Configuración del Sistema](#configuración-del-sistema)
- [Ejecución](#ejecución)
- [Despliegue con Docker](#despliegue-con-docker)
- [Mantenimiento](#mantenimiento)
    - [Programación de Tareas](#programación-de-tareas)
    - [Logs](#logs)
- [Interfaz de Línea de Comandos](#interfaz-de-línea-de-comandos)
    - [Base de Datos](#base-de-datos)
        - [Inicialización](#inicialización)
    - [Actualizador](#actualizador)
    - [Operaciones](#operaciones)
        - [Crear Usuario](#crear-usuario)
        - [Restablecer Contraseña](#restablecer-contraseña)

--------------------------------------------------------------------------------------------------

# Documentación
Para ver los diagramas de este proyecto, consuta la [documentación]().


# Requisitos
Para ejecutar el proyecto, se requiere tener instalados los siguientes paquetes:
- Python 3.13
- Node.js 24.0
- NPM 11.3
- PM2 6.0

## Variables de Entorno
Para poder ejecutar operaciones con la base de datos, es necesario definir la variable de entorno `URI_POSTGRES` en el archivo variables de entorno de nuestra preferencia `.env.production` o `.env`:
```bash
URI_POSTGRES="postgresql://usuario:contraseña@host:puerto/base_de_datos"
```
> *Nota*: Para ejecutar las **pruebas unitarias** es necesario un archivo `.env.test` con las variables de entorno. Si se desea trabajar en el **entorno de desarrollo**, se debe usar el archivo `.env.development`, que tiene un privilegio de uso antes que el archivo `.env.production` o `.env`. El sistema diferencia el **entorno de desarrollo** entre el **entorno de pruebas**.

Además de esto, para poder ejecutar operaciones con el servidor, es necesario definir la variable de entorno `SECRET_KEY` en el archivo variables de entorno de nuestra preferencia `.env.production` o `.env`:
```bash
SECRET_KEY="clave_secreta"
```

Para generar una clave secreta, puede ejecutar el siguiente comando:
```bash
openssl rand -hex 32
```

También es necesario definir la variable de entorno `HOST_FRONTEND` para definir la URL del frontend que se permitirá acceder a la API:
```bash
HOST_FRONTEND="http://localhost:3000"
```

# Instalación
Este proyecto es un monorepo, por lo que se debe instalar los paquetes para el frontend y el backend del sistema. Este sistema cuenta con un Makefile para facilitar la instalación y la configuración del sistema. Para inicializar el sistema, ejecuta el siguiente comando:
```bash
make setup
```
> *Nota:* Se recomienda instalar el sistema de esta forma ya que cuenta con el plus de la creación de los directorios requeridos. De otra forma, deberá crear los directorios `data/logs`, `data/sources` y `data/sources/devices.csv` manualmente.

También es posible realizar la instalación manualmente siguiendo estos pasos después de tener un entorno virtual activado:
```bash
pip install -e .
cd presentation && npm install
cd presentation && npm run build
pm2 start ecosystem.config.js
```

## Configuración del Sistema
Al iniciar el sistema, este crea automáticamente un archivo llamado `system.json`. Este archivo contiene la configuración del sistema para los permisos de usuarios y alertas de las consultas. Además de esto, en este archivo se debe configurar la información del equipo para conectarse mediante SSH para realizar las consultas SNMP.

*Vista del `system.json` creado por defecto*:
```json
{
    "snmp": { 
        "commands": {
            "ping": "ping",
            "snmp": "snmpwalk"
        }, 
        "credentials": [
            {
                "host": "127.0.0.1",
                "user": "public",
                "password": "public",
                "port": 22
            },
        ]
    },
    "can_assign": {
        "root": true,
        "admin": true,
        "user": false,
        "soport": false
    },
    "can_receive_assignment": {
        "root": false,
        "admin": true,
        "user": true,
        "soport": false
    },
    "view_information_global": {
        "root": true,
        "admin": true,
        "user": false,
        "soport": true
    },
    "notification_changes": {
        "ifName": true,
        "ifDescr": true,
        "ifAlias": true,
        "ifHighSpeed": true,
        "ifOperStatus": false,
        "ifAdminStatus": false
    }
}
```
> *Nota*: El sistema siempre generará automáticamente este archivo si no lo encuentra.


# Ejecución
Una vez instaladas con éxito todas las dependencias del sistema, para levantar el sistema, puede ejecutar la siguiente comando:
```bash
make start
```
o 
```bash
pm2 start ecosystem.config.js
```

O si prefiere, puede levantar los servicios manualmente siguiendo estos pasos:
```bash
fastapi run icm/business/api/app.py
cd presentation && npm run start
```

# Despliegue con Docker
El sistema también puede levantarse completamente con Docker Compose. Se orquestan 4 servicios:
- `postgres`: base de datos PostgreSQL con volumen persistente.
- `backend`: API del sistema (FastAPI/uvicorn).
- `frontend`: interfaz web (Next.js).
- `nginx`: proxy inverso que expone un único puerto (80 por defecto), enrutando `/api/*` hacia el backend y el resto hacia el frontend.

## Requisitos
- Docker y Docker Compose (plugin `docker compose`).

## Configuración
Copia la plantilla de variables de entorno para Docker y ajusta los valores:
```bash
cp .env.docker.example .env.docker
```

Variables disponibles en `.env.docker`:
```bash
POSTGRES_USER=icm_user
POSTGRES_PASSWORD=changeme
POSTGRES_DB=icm_db
SECRET_KEY=changeme
HOST_FRONTEND=http://localhost
NEXT_PUBLIC_API_URL=http://localhost/api
HTTP_PORT=80
```
> *Nota*: `NEXT_PUBLIC_API_URL` y `HOST_FRONTEND` deben apuntar al host/IP público donde estará accesible el sistema (por ejemplo, la IP retornada por `make ip`).

Este archivo `.env.docker` es independiente de `.env`/`.env.production` usados fuera de Docker; el contenedor del backend genera su propio `.env.production` interno a partir de estas variables al iniciar.

Al igual que en la instalación manual, se debe definir el archivo `data/sources/devices.csv` con los equipos a monitorear, y el `system.json` con la configuración de credenciales SNMP (ambos persisten en el host mediante volúmenes).

## Comandos
```bash
make setup     # Prepara directorios/archivos, construye las imágenes y levanta el sistema
make start     # Levanta el sistema (sin reconstruir imágenes)
make stop      # Detiene el sistema
make build     # Reconstruye las imágenes y reinicia el sistema
make updater   # Ejecuta las consultas SNMP dentro del contenedor del backend
make logs      # Sigue los logs de todos los contenedores
make ps        # Muestra el estado de los contenedores
make clean     # Detiene el sistema y elimina los volúmenes (incluye datos de PostgreSQL)
```

# Mantenimiento
El objetivo del sistema es consultar todas las interfaces de los dispositivos en una red y quedarse con la información de cada una de las interfaces para su comparación de información. De esta forma, el sistema detecta cambios en las interfaces para generar los alertas en el sistema. 

Para que el sistema pueda saber qué interfaces debe consultar, se debe definir un archivo `.csv` con la información de las interfaces que se desea monitorear. Este archivo se debe ubicar en el directorio `data/sources`. El archivo no debe tener encabezados y debe contar con las siguiente informaciones separados por comas:
```bash
IP,COMMUNITY
```
> *Nota*: Todos los equipos declarados en este archivo deben estar dentro de la red para su correcta consulta.

Una vez definido el archivo, podrá ordenar al sistema que realize las consultas SNMP ejecutando el siguiente comando:
```bash
make updater
```
o
```bash
python -m icm updater
```
> Para más información sobre el actualizador, consulta la sección [Actualizador](#actualizador).

## Programación de Tareas
Para que el sistema pueda realizar las consultas diaria a los equipos, se debe añadir al `crontab` del equipo de la siguiente forma:
```bash
00 04 * * * cd /home/user/Interface-Change-Monitor && /usr/bin/make updater
```
o
```bash
00 04 * * * /home/user/Interface-Change-Monitor/.venv/bin/python -m icm updater
```

## Actualización de Cambios
Para actualizar el sistema con cambios hechos en la aplicación, puede ejecutar el siguiente comando:
```bash
make build
```

Esto detendrá el sistema y compilará la aplicación de nuevo.

## Logs
El sistema cuenta con un archivo de registro de cada operación realizada por el backend que se encuentra en el directorio `data/logs`.


# Interfaz de Línea de Comandos
El sistema cuenta con una interfaz de línea de comandos para facilitar la ejecución de operaciones en el sistema. Para ver las opciones disponibles, puede ejecutar el siguiente comando:
```bash
python -m icm --help
```

## Base de Datos
### Inicialización
Para inicializar la base de datos, puede ejecutar el siguiente comando:
```bash
python -m icm database start
```

## Actualizador
Para actualizar la información de las interfaces, puede ejecutar el siguiente comando:
```bash
python -m icm updater
```

Esto ejecutará las consultas SNMP, actualizará la información de las interfaces en la base de datos y realizará las comparaciones de información entre las interfaces para generar los cambios.

Si se requiere rehacer las comparaciones de información sin que realice de nuevo las consultas SNMP, puede ejecutar el siguiente comando:
```bash
python -m icm updater --reload
```

## Operaciones
### Crear Usuario
Para crear un nuevo usuario en el sistema, puede ejecutar el siguiente comando:
```bash
python -m icm system --register
```

Este comando permitirá rellenar los campos requeridos para crear un nuevo usuario.

### Restablecer Contraseña
Para restablecer la contraseña de un usuario, puede ejecutar el siguiente comando:
```bash
python -m icm system --restore
```

Este comando solicitará la información del usuario para el restablecimiento de la contraseña.
