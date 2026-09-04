# Guía de contribución

## Regla de trabajo

Cada tarea se realiza en un **workspace de Conductor** y en su propia rama. No se desarrollan cambios directamente en `main`, ni se reutiliza una rama ya asociada a un PR fusionado.

Los archivos de la carpeta `.context/` son locales del workspace, están ignorados por Git y no forman parte de los entregables.

## Crear una rama y workspace

1. En Conductor, crea un workspace desde `origin/main`.
2. Asigna una rama corta, en minúsculas y con guiones: `<tipo>/<descripcion>`.
3. Desarrolla, ejecuta las validaciones y realiza los commits dentro de ese workspace.

Tipos de rama permitidos:

| Tipo | Uso | Ejemplo |
| --- | --- | --- |
| `feature/` | Nueva capacidad de datos, ETL o visualización | `feature/modelo-ventas` |
| `fix/` | Corrección de datos o lógica | `fix/normalizar-fechas` |
| `docs/` | Documentación | `docs/diccionario-datos` |
| `chore/` | Configuración, dependencias o mantenimiento | `chore/configurar-jupyter` |

Si fuera imprescindible trabajar desde terminal, parte siempre de la última `origin/main`:

```bash
git fetch origin
git switch -c feature/descripcion-corta origin/main
```

## Commits

Mantén los commits pequeños y con un propósito único. Usa el formato:

```text
tipo: descripción en infinitivo
```

Ejemplos: `feat: crear modelo de margen`, `fix: normalizar fecha de embarque`, `docs: documentar fuente de costos`.

## Pull requests

1. Sube la rama y abre un PR contra `main`.
2. Completa la plantilla del PR: objetivo, cambios, validaciones y consideraciones de datos.
3. Revisa el diff y confirma que no se incluyan secretos, archivos temporales, salidas de notebooks ni resultados generados.
4. Fusiona solo cuando el PR esté limpio, las verificaciones requeridas pasen y exista aprobación cuando corresponda.

Un PR debe abordar una sola unidad de trabajo. Si el cambio mezcla ETL, modelo de datos y tablero, sepáralo en PRs encadenados cuando sea posible.

## Datos, notebooks y Tableau

- Conserva las fuentes originales sin modificación.
- Usa notebooks para explorar, perfilar y validar hipótesis; pasa la lógica aprobada al paquete `src/`.
- No subas salidas generadas en `data/staging`, `data/processed` o `data/published`.
- Tableau debe conectarse a las tablas publicadas por el ETL, no a las fuentes crudas.

## Validación mínima

Antes de abrir un PR, ejecuta la validación más acotada que cubra tu cambio. Como base:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m vina_vallehondo_bi.etl.pipeline --help
```
