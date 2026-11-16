# Viña Vallehondo BI

Proyecto inicial de Business Intelligence para Viña Vallehondo, orientado a integrar ventas, costos, embarques y tipo de cambio para analizar el desempeño de las exportaciones.

## Objetivo

Determinar cuánto del crecimiento de las exportaciones corresponde a valor real en pesos y en qué mercados, productos y niveles de calidad se crea o se deteriora el margen.

El análisis buscará responder, entre otras, estas preguntas:

- ¿Las exportaciones que crecieron en dólares también crecieron al convertirlas a pesos chilenos?
- ¿La variación del precio por litro responde a precio, mix o premiumización?
- ¿Qué mercados crecen en volumen con un margen atractivo y cuáles no?
- ¿Qué fecha debe utilizarse para convertir ventas de exportación: venta o embarque?

## Stack

- **Cadena de datos:** Python con pandas; salidas en Parquet.
- **BI y visualización:** Tableau.
- **Datos de origen:** SQLite, CSV y JSON.
- **Tipo de cambio:** API de dólar observado de Mindicador (`https://mindicador.cl/api/dolar/2025`).

## Fuentes incluidas

| Archivo | Descripción |
| --- | --- |
| `origen_vina.sqlite` | Base comercial: ventas, clientes, mercados, zonas, cepas, monedas y vendedores. |
| `origen_costos_productos.csv` | Costos por producto y añada, junto con la equivalencia de cajas a litros. |
| `origen_embarques.json` | Embarques de exportación, fechas, incoterms, puertos de destino y líneas asociadas a ventas. |
| `README_caso.md` | Contexto de negocio, definiciones y preguntas entregadas para el caso. |

## Consideraciones iniciales de calidad de datos

- Las fechas de ventas y embarques están en más de un formato; deberán normalizarse antes de relacionar las fuentes.
- Los campos numéricos incluyen formatos distintos de miles y decimales, valores de texto y nulos.
- El archivo de costos contiene encabezados repetidos y valores heterogéneos para campos como cepa y estado activo.
- Existen registros posteriores a 2025. Se conservarán en la capa de preparación, pero el análisis inicial se enfocará en 2025 salvo que se acuerde otra ventana temporal.

## Reproducción

Todo corre desde un clon limpio del repositorio, con un comando para instalar y otro para ejecutar la cadena de datos.

### Requisitos

- Python 3.9 o superior.
- Conexión a internet en la primera ejecución, para consultar el dólar observado en `mindicador.cl`.

### Instalar

```bash
git clone https://github.com/mtombolini/vina-vallehondo-bi.git
cd vina-vallehondo-bi
bash scripts/setup.sh
```

El script crea el ambiente virtual `.venv` e instala el paquete con sus dependencias. Demora entre 1 y 3 minutos según la conexión. En Windows, los comandos equivalentes son `python -m venv .venv` y `.venv\Scripts\pip install -e ".[dev]"`, y en los pasos siguientes `.venv\Scripts\python` reemplaza a `.venv/bin/python`.

### Correr la cadena de datos

```bash
.venv/bin/python -m vina_vallehondo_bi.etl.pipeline
```

Lee las cuatro fuentes (SQLite, CSV, JSON y API), las tipa en `data/staging/`, las limpia en `data/processed/`, arma el modelo estrella y la métrica de margen, corre las pruebas de calidad y publica en `data/published/`. Con la API respondiendo demora menos de 10 segundos; si la API no responde, espera hasta 30 segundos por año antes de usar la copia guardada.

Al terminar se espera ver este resumen:

```text
stg_ventas: 13968 filas (nulos: moneda_id=695)
stg_zonas: 5 filas
stg_mercados: 11 filas
stg_cepas: 7 filas
stg_monedas: 2 filas
stg_vendedores: 5 filas
stg_clientes: 26 filas
stg_costos_productos: 81 filas (nulos: costo_caja_clp=1)
stg_embarques: 10730 filas
stg_tipo_cambio: 692 filas

ventas: 13830 filas
mercados: 11 filas
clientes: 26 filas
cepas: 7 filas
monedas: 2 filas
vendedores: 5 filas
costos_productos: 96 filas
embarques: 10715 filas
tipo_cambio: 651 filas

Pruebas de calidad: 12 de 13 en verde (bloquean la carga si fallan: 11; solo avisan: 2).
  Aviso · Fuente JSON de embarques: 15 de 10.730 líneas apuntan a ventas inexistentes y se excluyen en processed.

fact_venta: 13830 filas (nulos: fecha_embarque=10766, ingreso_neto_clp_fecha_embarque=10766)
dim_tiempo: 408 filas
dim_mercado: 11 filas
dim_cliente: 26 filas
dim_producto: 96 filas
margen_por_mercado: 132 filas (nulos: ranking=12, clase_margen=12, estado_decision=12)
sensibilidad_reglas_margen: 44 filas (nulos: ranking=4, clase_margen=4, estado_decision=4)
caso_descuento_brasil: 2 filas
escenarios_mezcla: 4 filas
serie_mensual_mercado: 120 filas
cobertura_margen: 1 filas
descuadres_monto_exportacion: 527 filas
Modelo y métricas de margen publicados en data/published.
Ingesta a staging y limpieza a processed listas.
```

Las filas de `stg_tipo_cambio` y `tipo_cambio` crecen con cada día hábil que publica la API; el resto de las cifras es fijo. Las reglas de cada capa están en [data/README.md](data/README.md).

La respuesta de la API queda guardada en `data/staging/tipo_cambio_<año>.json`. Si una ejecución posterior no logra conectarse, usa esa copia, lo avisa en la salida y lo registra en `data/published/corrida.json`; el prototipo muestra entonces un aviso de tipo de cambio de respaldo con la fecha del último dato. Sin conexión y sin copia previa, la cadena se detiene. `--omitir-tipo-cambio` ejecuta solo con las fuentes locales: prueba las fuentes, pero no arma el modelo ni publica métricas.

#### Pruebas de calidad en cada carga

Antes de publicar, la cadena corre 13 pruebas (`etl/quality.py`): una o más por fuente, las del modelo (clave única del hecho, claves sin huérfanos, rangos, fechas dentro de 2025, tipo de cambio de cada venta en USD) y las que protegen la métrica (cobertura y cuadratura entre `fact_venta` y el margen publicado). Las que bloquean impiden publicar: `data/published/` conserva la corrida anterior y el comando termina con código 1. Las que avisan se informan y la carga sigue. El resultado de cada prueba queda en `data/published/calidad_ultima_corrida.csv`.

### Abrir el prototipo

```bash
.venv/bin/pip install -e ".[app]"
.venv/bin/streamlit run app.py
```

Se abre en el navegador en `http://localhost:8501`. El tablero lee solo los CSV de `data/published/`; si la carpeta está vacía, corre la cadena al iniciar, y el botón «Volver a correr la cadena», al final de la pantalla, la ejecuta de nuevo y recarga las cifras. En Windows: `.venv\Scripts\streamlit run app.py`.

Versión publicada: <https://vina-vallehondo-g7.streamlit.app/>. Abre sin instalar nada; si Streamlit la dejó en reposo por inactividad, el botón para reactivarla la carga en unos segundos.

### Reproducir las cifras del informe

Los notebooks usan el mismo código del pipeline y se pueden ejecutar completos desde la terminal:

```bash
.venv/bin/jupyter nbconvert --to notebook --execute --inplace notebooks/02_hallazgos_mandato.ipynb
.venv/bin/jupyter nbconvert --to notebook --execute --inplace notebooks/03_modelado_estrella.ipynb
.venv/bin/jupyter nbconvert --to notebook --execute --inplace notebooks/04_metrica_sensibilidad.ipynb
.venv/bin/jupyter nbconvert --to notebook --execute --inplace notebooks/05_evidencia_recomendacion.ipynb
```

Cada uno demora menos de 30 segundos. El 05 ejecuta internamente el 04, así que sus cifras son siempre las de la ficha de la métrica. También se pueden abrir con `.venv/bin/jupyter lab` y usar *Run All*.

| Notebook | Qué respalda |
| --- | --- |
| `02_hallazgos_mandato.ipynb` | Cifras medidas del mandato y de la bitácora de supuestos; termina con una tabla que compara cada cifra del informe con la calculada. |
| `03_modelado_estrella.ipynb` | Modelo estrella (`fact_venta` y sus dimensiones) con la conversión a pesos; termina con los controles de integridad en `OK`. Requiere el tipo de cambio. |
| `04_metrica_sensibilidad.ipynb` | Ficha de la métrica (Sección D): margen bruto por litro por mercado con el dólar a fecha de factura (A) y a fecha de embarque (B), sensibilidad A vs B y cruce crecimiento × margen. |
| `05_evidencia_recomendacion.ipynb` | Sección E: visualizaciones, caso de negocio en pesos, recomendación y cobertura de datos, todo dentro del cuaderno. |

### Verificar

```bash
.venv/bin/python -m pytest
```

Deben pasar los 83 tests en menos de un minuto. Incluyen la ingesta, la limpieza, el modelo, las pruebas de calidad y la conciliación de las métricas sobre las fuentes reales.

## Flujo de trabajo

```text
Fuentes originales → staging (tipado) → processed (limpieza) → published (modelo, métricas y pruebas) → prototipo
                                             ↳ Notebooks de análisis
```

El ETL versionado en `src/vina_vallehondo_bi/etl/` es la única fuente de las transformaciones; los notebooks lo importan para analizar y modelar. Revisa [CONTRIBUTING.md](CONTRIBUTING.md) para el flujo de ramas, workspaces y PRs.

## Estructura actual

```text
.
├── README.md
├── README_caso.md
├── CONTRIBUTING.md
├── config/
├── data/                  # capas staging, processed y published (salidas no versionadas)
├── notebooks/             # perfilado, hallazgos, modelo estrella, métrica y evidencia
├── origen_costos_productos.csv
├── origen_embarques.json
├── origen_vina.sqlite
├── scripts/setup.sh
├── src/vina_vallehondo_bi/etl/   # parsers, staging, processed, model, margins, quality y pipeline
├── tableau/
└── tests/
```

### Analítica E2 para el informe y el tablero

El mismo comando del pipeline publica en `data/published/` el modelo estrella y los CSV de margen cuando carga el tipo de cambio y pasan las pruebas que bloquean. La opción `--omitir-tipo-cambio` mantiene la ejecución de preparación sin publicar métricas de moneda. El modelo está en `etl/model.py` y la métrica en `etl/margins.py`.

| Salida | Contenido |
| --- | --- |
| `margen_por_mercado.csv` | Diez mercados y total por criterio, moneda, fecha y base. Incluye litros y cajas por semestre, crecimiento, margen, mediana, ranking, clase, descuento y cobertura. |
| `sensibilidad_reglas_margen.csv` | E1, solo monto facturado, solo sin reversa de merma y ambas reglas. CLP, factura y base completa. |
| `caso_descuento_brasil.csv` | Brecha frente a la mediana, escenarios de descuento implícito y comercial, equilibrio de volumen y valor de un punto de descuento. |
| `escenarios_mezcla.csv` | Valor en CLP de reasignar un punto porcentual de litros entre niveles de vino, para Brasil y China. |
| `serie_mensual_mercado.csv` | Volumen y margen de producto por mes de factura para la vista principal. |
| `cobertura_margen.csv` | Universo y conteos de auditoría. |
| `descuadres_monto_exportacion.csv` | Identificadores y montos de las ventas de exportación recalculadas en la E1 para conciliación. |
| `fact_venta.parquet` | Una fila por venta: claves de fecha, fecha de embarque, mercado, cliente y producto-añada; cajas, litros, montos en moneda original y en CLP y costo, con las reglas de Finanzas de la E2. |
| `dim_tiempo`, `dim_mercado`, `dim_cliente`, `dim_producto` (`.parquet`) | Dimensiones del modelo estrella, con el diseño del cuaderno 03. |
| `calidad_ultima_corrida.csv` | Resultado de cada prueba de calidad de la última ejecución: qué verifica, si bloquea o avisa, resultado y detalle. |
| `corrida.json` | Fecha de la corrida publicada, origen del tipo de cambio (API o copia de respaldo) y resumen de las pruebas, para el pie del prototipo. |

La vista principal usa `reglas_finanzas / CLP / factura / disponible`. Para medir el efecto de fecha, comparar `factura` y `embarque` con `base=comparable`. La cobertura se calcula sobre los litros netos del mercado o del total, según la fila. El margen en USD convierte el costo de CLP a USD por línea con el tipo de cambio seleccionado. El crecimiento siempre usa los dos semestres completos según factura.

El escenario del descuento implícito conserva la comparación de la E1. El informe y el prototipo usan el escenario comercial (`escenario_descuento_comercial_clp` y `perdida_volumen_equilibrio_comercial_pct`). El margen publicado es de producto, antes de flete, seguro y comisiones, y queda sujeto a conciliación de notas de crédito. El material para el Word y las respuestas de la prueba de uso están en [Analítica de Vicente](docs/analitica-e2-vicente.md).
