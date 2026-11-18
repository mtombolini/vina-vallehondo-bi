# Entrega 2 · Viña Vallehondo · Corrida final (F.2)

Registro de la corrida integrada para F.2 y para la revisión de consistencia de F.3. Se ejecutó desde un clon limpio del repositorio, siguiendo solo los comandos del README, el 18 de noviembre de 2026 entre las 15:38 y las 15:41 (hora de Chile), en macOS con Python 3.12.13, sobre `main` en el commit `b578ab3`. Esa versión incluye el modelo estrella y las pruebas de calidad dentro de la cadena (PR #17), el rediseño del prototipo tras la prueba de uso (PR #21), los títulos y figuras de hallazgos de los cuadernos (PR #22) y las cifras del escenario de descuento con los decimales del informe (PR #23). La etiqueta `E2` apunta al commit que integra este registro, con el mismo código.

## Comandos y duración

| Paso | Comando | Duración | Resultado |
|---|---|---:|---|
| Clonar | `git clone …/vina-vallehondo-bi.git` | 5 s | OK |
| Instalar | `python3.12 -m venv .venv` y `.venv/bin/pip install -e ".[dev,app]"` | 27 s | OK |
| Pruebas automáticas | `.venv/bin/python -m pytest` | 32 s | **86 pasan**, 0 fallan |
| Cadena | `.venv/bin/python -m vina_vallehondo_bi.etl.pipeline` | 33 s | OK, publica; 11 de 11 pruebas que bloquean en verde |
| Notebooks 02 a 05 | `jupyter nbconvert --to notebook --execute` | 13, 34, 5 y 4 s | OK |

La API de `mindicador.cl` no respondió durante esta corrida (error de conexión de su lado). La cadena esperó el plazo, usó las copias versionadas de 2024 a 2026 (con datos hasta el 17-11-2026), lo avisó y publicó con las mismas cifras; por eso tardó 33 s. Con la API disponible tarda unos 3 s, como en la corrida del 17-11-2026 sobre `9c1b79e`.

## Pruebas de calidad dentro de la cadena (B.5)

Corren en cada carga, antes de publicar (`etl/quality.py`). El resultado queda en `data/published/calidad_ultima_corrida.csv`.

| Prueba | Qué verifica | Si falla | Última corrida |
|---|---|---|---|
| Fuente SQLite: ventas | Cada registro tiene venta_id, fecha, mercado, cliente, producto, cajas, precio y monto | Bloquea | ✓ 13.968 registros, 0 con campos clave vacíos |
| Fuente SQLite: moneda por mercado | Cada mercado informa una sola moneda | Bloquea | ✓ 11 mercados, 0 con más de una |
| Fuente CSV de costos | Cada producto y añada vendido tiene costo, propio o imputado | Bloquea | ✓ 0 ventas sin costo (16 costos imputados) |
| Fuente JSON de embarques | Cada línea apunta a una venta existente | Avisa | ⚠ 15 de 10.730 líneas sin venta; se excluyen en processed |
| API mindicador.cl: origen | El dólar viene de la API y no de la copia de respaldo | Avisa | ⚠ Copia de respaldo para 2024, 2025 y 2026 |
| API mindicador.cl: rango | Cada valor está entre 500 y 1.500 CLP | Bloquea | ✓ 717 días, 0 fuera de rango |
| Unicidad de la clave del hecho | venta_id único y una fila por venta limpia | Bloquea | ✓ 13.830 filas, 0 repetidas |
| Claves sin huérfanos | Toda clave de fact_venta existe en su dimensión | Bloquea | ✓ 5 claves, 0 huérfanas |
| Rangos válidos | Descuento entre 0 y 1; precio, litros y costo por caja mayores que cero | Bloquea | ✓ Descuento entre 0 % y 18 % |
| Fechas dentro del período | Fecha de factura en 2025 | Bloquea | ✓ 13.830 en 2025 (82 reasignadas desde 2026) |
| Tipo de cambio de cada venta en USD | Toda venta en USD tiene dólar a su fecha de factura | Bloquea | ✓ 10.715 ventas, 0 sin tipo de cambio |
| Cobertura de la métrica | Toda venta de exportación tiene margen en la vista principal | Bloquea | ✓ 10.715 de 10.715 |
| Métrica cuadra con el modelo | El margen calculado desde fact_venta es el mismo publicado | Bloquea | ✓ 2.210,64 CLP/L en ambos |

## Filas por capa

| Capa | Tabla | Filas |
|---|---|---:|
| Staging | `stg_ventas` | 13.968 (695 sin moneda) |
| Staging | `stg_costos_productos` | 81 (1 sin costo) |
| Staging | `stg_embarques` | 10.730 |
| Staging | `stg_tipo_cambio` | 717 |
| Processed | `ventas` | 13.830 |
| Processed | `costos_productos` | 96 |
| Processed | `embarques` | 10.715 |
| Processed | `tipo_cambio` | 686 |
| Published | `fact_venta` (Parquet y CSV) | 13.830 |
| Published | `dim_tiempo`, `dim_mercado`, `dim_cliente`, `dim_producto` | 408, 11, 26 y 96 |
| Published | `margen_por_mercado` | 132 |
| Published | `sensibilidad_reglas_margen` | 44 |
| Published | `caso_descuento_brasil` | 2 |
| Published | `escenarios_mezcla` | 4 |
| Published | `serie_mensual_mercado` | 120 |
| Published | `cobertura_margen` | 1 |
| Published | `descuadres_monto_exportacion` | 527 |

Las filas de tipo de cambio crecen con cada día hábil publicado por la API; el resto es fijo.

## Cifras clave frente al informe

Vista principal: reglas de Finanzas, CLP, dólar de factura y base completa, salvo que se indique otra cosa. Referencia: [Analítica de Vicente](analitica-e2-vicente.md) y secciones C.9, E.2–E.4 y F.1 del informe.

| Cifra | Informe | Corrida final | Estado |
|---|---:|---:|---|
| Margen por litro de exportación | 2.210,64 CLP/L | 2.210,64 CLP/L | Coincide |
| Margen por litro de Brasil | 1.718,61 CLP/L | 1.718,61 CLP/L | Coincide |
| Mediana de los diez mercados | 2.289,02 CLP/L | 2.289,02 CLP/L | Coincide |
| Crecimiento de Brasil en litros | 27,58 % | 27,58 % | Coincide |
| Exportación, base comparable, factura → embarque | 2.201,88 → 2.150,15 CLP/L | 2.201,88 → 2.150,15 CLP/L | Coincide |
| Cobertura de la base comparable (litros de exportación) | 28,4 % | 28,4 % | Coincide |
| Escenario de descuento comercial de Brasil | 783,81 MM CLP | 783,81 MM CLP | Coincide |
| Pérdida de volumen de equilibrio (escenario comercial) | 23,27 % | 23,27 % | Coincide |
| Escenario implícito, solo para conciliar con la E1 | 788,73 MM CLP | 788,73 MM CLP | Coincide |
| Registros fuente con margen a fecha de factura | 10.715 de 13.968 (76,7 %) | 10.715 de 13.968 (76,7 %) | Coincide |

## Tablero

Publicado en <https://vina-vallehondo-g7.streamlit.app/>. La rama que usa Streamlit Community Cloud queda en el mismo commit que `main`. El prototipo lee solo `data/published/`, muestra el escenario comercial (783,81 MM CLP y 23,27 %) y, si la corrida usó la copia del dólar, avisa con los años afectados y la fecha del último dato. El pie indica la fecha de la corrida, el origen del tipo de cambio y las pruebas en verde. Después de la prueba de uso se rediseñó (PR #21): respuesta escrita arriba, «mercado típico (mediana de los 10 mercados)», tarjetas sin texto cortado, serie mensual del mercado destacado y detalle por cliente, producto y factura desde `fact_venta`, con descarga a Excel.

## Problemas encontrados y cómo se resolvieron

1. **El notebook 05 fallaba desde un clon limpio.** Con IPython 9, `%%capture` leía la ruta `./04_metrica_sensibilidad.ipynb` como un número mal escrito. Se corrigió dejando la ruta entre comillas (PR #16), sin efecto en las cifras.
2. **El modelo solo existía en el notebook 03 y la cadena no tenía pruebas propias.** Se llevaron `fact_venta` y sus dimensiones a `etl/model.py` y se agregaron 13 pruebas en cada carga (PR #17). El margen calculado desde el modelo coincide con el publicado.
3. **El tablero mostraba el escenario implícito (788,73 MM CLP)** mientras el informe usa el comercial (783,81 MM CLP). Se alineó en el PR #17.
4. **La API de mindicador.cl falla de forma intermitente.** La cadena usa la copia versionada, lo registra y el prototipo lo avisa. La copia de 2026 se actualizó hasta el 17-11-2026.
5. **Python 3.15 no sirve para instalar**, porque duckdb no tiene paquete precompilado. Usar Python 3.12 (`python3.12 -m venv .venv`).

## Aporte para F.4 · Uso de IA

Borrador; ajustar la columna de revisión a lo que efectivamente se haya revisado.

| Integrante | Herramienta | Uso | Revisión manual |
|---|---|---|---|
| Maximiliano Tombolini | Claude (Claude Code) y Claude en Word | Preparar el entorno, ejecutar la corrida final desde un clon limpio, implementar el modelo estrella y las pruebas de calidad en la cadena, corregir el notebook 05, ajustar el prototipo y redactar B y F.2. Claude en Word se usó para insertar y ajustar los textos en el informe. | Comparación de las cifras de la corrida con el informe, revisión del diff y de la revisión de código de cada cambio antes de integrarlo, y prueba del tablero publicado. |
