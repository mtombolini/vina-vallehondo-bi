# Guía de contribución

## Regla de trabajo

Cada tarea se desarrolla en su propia rama. No se realizan cambios directamente en `main`, ni se reutiliza una rama ya asociada a un PR fusionado.

Puedes usar el editor, IDE, terminal o asistente de IA que prefieras. Quien abre el PR es responsable de entender los cambios, validarlos y cumplir esta guía.

## Crear una rama

1. Actualiza las referencias remotas y crea la rama desde `origin/main`.
2. Usa un nombre corto, en minúsculas y con guiones: `<tipo>/<descripcion>`.
3. Desarrolla, ejecuta las validaciones y realiza los commits en esa rama.

Tipos de rama permitidos:

| Tipo | Uso | Ejemplo |
| --- | --- | --- |
| `feature/` | Nueva capacidad de datos, ETL o visualización | `feature/modelo-ventas` |
| `fix/` | Corrección de datos o lógica | `fix/normalizar-fechas` |
| `docs/` | Documentación | `docs/diccionario-datos` |
| `chore/` | Configuración, dependencias o mantenimiento | `chore/configurar-jupyter` |

Desde terminal:

```bash
git fetch origin
git switch -c feature/descripcion-corta origin/main
```

Desde un IDE, crea la rama con el mismo nombre y asegúrate de que su base sea la última `origin/main`. Si usas Conductor, crea un workspace desde esa misma base. Es una alternativa de trabajo, no un requisito del proyecto.

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

## Uso de asistentes de IA

El uso de asistentes de IA es opcional. Si se utilizan, quien contribuye debe revisar el código, preservar información sensible y ejecutar las mismas validaciones que aplicaría a un cambio escrito manualmente. No se deben subir credenciales, datos privados ni resultados generados sin revisión.

## Validación mínima

Antes de abrir un PR, ejecuta la validación más acotada que cubra tu cambio. Como base:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m vina_vallehondo_bi.etl.pipeline --help
```
