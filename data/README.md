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
| `stg_tipo_cambio` | API Mindicador | Día hábil, años 2024 a 2026 |

Staging solo tipa fechas, números y booleanos; lo que no se puede interpretar queda nulo. No elimina duplicados, no imputa valores ni corrige inconsistencias: esas reglas pertenecen a `processed/`. `fila_origen` permite volver al registro de la fuente.

## Tablas de processed

El mismo comando limpia staging y escribe en `processed/` las tablas `ventas`, `mercados`, `clientes`, `cepas`, `monedas`, `vendedores`, `costos_productos`, `embarques` y `tipo_cambio`. Cada corrección deja una columna indicadora en la fila afectada:

| Tabla | Regla | Indicador |
| --- | --- | --- |
| `ventas` | Moneda nula: se usa la moneda con que factura el mercado | `moneda_imputada` |
| `ventas` | Pedidos sobre 220 cajas: están en botellas (se dividen por 12) o multiplicados por 10 (cajas y monto se dividen por 10) | `ajuste_cajas` |
| `ventas` | Monto que difiere más de 0,5% de cajas × precio × (1 − descuento): se recalcula | `monto_recalculado` |
| `ventas` | Fecha fuera de 2025: se usa la fecha de la venta válida anterior según `venta_id` | `fecha_imputada` |
| `ventas` | `venta_id` repetido: se conserva el primer registro | — |
| `ventas` | Cajas negativas: se conservan como devolución | `es_devolucion` |
| `mercados` | Zona inexistente: se asigna la zona más frecuente del mercado en ventas | — |
| `clientes` | RUT normalizado a `12345678-K` | — |
| `costos_productos` | Cepa según el maestro de cepas; costos nulos y añadas faltantes se completan con el costo del tier y la añada | `costo_imputado` |
| `embarques` | Se descartan líneas sin venta; la fecha es creíble solo en la primera línea, con el mismo mercado de la venta y entre 0 y 60 días después | `fecha_embarque_confiable` |
| `tipo_cambio` | Serie en días corridos desde 2025; los días sin publicación usan el último valor publicado | `publicado` |
