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

## Flujo de trabajo

```text
Fuentes originales → Notebook de perfilado → ETL versionado → data/published → Tableau
```

Los notebooks se usan para exploración y validación. Las transformaciones que alimenten el tablero deben implementarse en el ETL para que sean reproducibles. Revisa [CONTRIBUTING.md](CONTRIBUTING.md) para el flujo de ramas, workspaces y PRs.

## Estructura actual

```text
.
├── README.md
├── README_caso.md
├── CONTRIBUTING.md
├── config/
├── data/
├── notebooks/
├── origen_costos_productos.csv
├── origen_embarques.json
├── src/
├── tableau/
├── tests/
└── origen_vina.sqlite
```
