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

Lee las cuatro fuentes (SQLite, CSV, JSON y API), las tipa en `data/staging/` y las limpia en `data/processed/`. Demora cerca de 30 segundos, casi todo en las tres consultas a la API.

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
Ingesta a staging y limpieza a processed listas.
```

Las filas de `stg_tipo_cambio` y `tipo_cambio` crecen con cada día hábil que publica la API; el resto de las cifras es fijo. Las reglas de cada capa están en [data/README.md](data/README.md).

La respuesta de la API queda guardada en `data/staging/tipo_cambio_<año>.json`. Si una ejecución posterior no logra conectarse, usa esa copia y lo avisa. Sin conexión y sin copia previa, `--omitir-tipo-cambio` ejecuta la cadena solo con las fuentes locales.

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

Deben pasar los 73 tests en pocos segundos. Uno de ellos ejecuta la ingesta y la limpieza sobre las fuentes reales.

## Flujo de trabajo

```text
Fuentes originales → staging (tipado) → processed (limpieza) → Notebooks de análisis y modelo
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
├── src/vina_vallehondo_bi/etl/   # parsers, staging, processed y pipeline
├── tableau/
└── tests/
```
