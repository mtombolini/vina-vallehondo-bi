# Capas de datos

| Capa | Propósito | Versionada |
| --- | --- | --- |
| Fuentes originales en la raíz | Entrega original, sin modificación | Sí |
| `staging/` | Datos leídos y normalizados de forma mínima | No |
| `processed/` | Datos limpios y con reglas de negocio aplicadas | No |
| `published/` | Tablas analíticas para Tableau | No |

Las salidas generadas se excluyen de Git. El ETL debe poder recrearlas desde las fuentes originales y la configuración versionada.

## Tablas de staging

`python -m vina_vallehondo_bi.etl.pipeline` escribe una tabla Parquet por fuente en `staging/`:

| Tabla | Origen | Granularidad |
| --- | --- | --- |
| `stg_ventas` | `origen_vina.sqlite` | Una fila por registro de `ventas`, incluidos los repetidos |
| `stg_zonas`, `stg_mercados`, `stg_cepas`, `stg_monedas`, `stg_vendedores`, `stg_clientes` | `origen_vina.sqlite` | Copia de cada dimensión |
| `stg_costos_productos` | `origen_costos_productos.csv` | Producto y añada |
| `stg_embarques` | `origen_embarques.json` | Línea de embarque (`embarque_orden`, `linea_orden`) |
| `stg_tipo_cambio` | API Mindicador | Día hábil, años 2025 y 2026 |

Staging solo tipa fechas, números y booleanos; lo que no se puede interpretar queda nulo. No elimina duplicados, no imputa valores ni corrige inconsistencias: esas reglas pertenecen a `processed/`. `fila_origen` permite volver al registro de la fuente.
