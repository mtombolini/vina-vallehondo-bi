# Capas de datos

| Capa | Propósito | Versionada |
| --- | --- | --- |
| Fuentes originales en la raíz | Entrega original, sin modificación | Sí |
| `staging/` | Datos leídos y normalizados de forma mínima | No |
| `processed/` | Datos limpios y con reglas de negocio aplicadas | No |
| `published/` | Tablas analíticas para Tableau | No |

Las salidas generadas se excluyen de Git. El ETL debe poder recrearlas desde las fuentes originales y la configuración versionada.
