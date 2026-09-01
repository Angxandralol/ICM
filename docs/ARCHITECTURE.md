# Arquitectura (capas)

El backend se encuentra completamente contenido dentro de la carpeta `icm/`. Siendo las subdivisiones un intento por seguir el estilo arquitectónico en capas:

- `access`: La capa que intermedia que recibe datos de la capa de lógica para transformar los valores para realizar peticiones. Tiene los querys, modelos, etc...
- `business`: La capa orquestadora de procesos, endpoints y lógica de negocio.
- `constants`: Capa abierta que almacena todas las constantes necesarias por las distintas capas.
- `data`: La capa que interactúa con la base de datos directamente. Tiene las estructuras, esquemas y es quien abre las conexiones a la base de datos.
- `utils`: Capa abierta con distintas herramientas útiles para el sistema.

Además de eso, el código completo de la página web (frontend) se encuentra en `presentation/`.
