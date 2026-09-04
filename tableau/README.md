# Conexión con Tableau

Tableau debe consumir la capa `data/published/`, nunca las fuentes originales. El ETL publicará tablas analíticas en CSV, un formato simple de actualizar y conectar desde Tableau.

Flujo esperado:

1. Ejecutar el ETL para regenerar las tablas publicadas.
2. En Tableau, conectar a **Archivo de texto** y seleccionar la tabla publicada correspondiente.
3. Crear un extracto de Tableau si se requiere mejor rendimiento.
4. Versionar aquí los archivos de definición de fuente (`.tds`) y libros (`.twb`) que no contengan credenciales; no versionar extractos (`.hyper`) generados.

Las primeras tablas candidatas son `fact_ventas`, `fact_embarques`, `dim_producto`, `dim_mercado` y una tabla de tipo de cambio. Sus nombres y granularidad se definirán al diseñar el modelo.
