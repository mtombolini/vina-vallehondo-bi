# Entrega 2 · Viña Vallehondo · Corrida final (F.2)

Registro de la corrida integrada para F.2 y para la revisión de consistencia de F.3. Se ejecutó desde un clon limpio del repositorio, siguiendo solo los comandos del README, el 15 de noviembre de 2026 entre las 21:48 y las 21:50 (hora de Chile), en macOS con Python 3.12.13.

El clon corresponde al commit `671a27b` de `feature/prototipo-streamlit` (PR #15), que es `main` (`c6183d1`, con la analítica de Vicente) más el tablero en Streamlit. La cadena, las pruebas y los notebooks son idénticos a `main`.

## Comandos y duración

| Paso | Comando | Duración | Resultado |
|---|---|---:|---|
| Clonar | `git clone …/vina-vallehondo-bi.git` | 1 s | OK |
| Instalar | `python3.12 -m venv .venv` y `.venv/bin/pip install -e ".[dev,app]"` | 17 s | OK |
| Pruebas | `.venv/bin/python -m pytest` | 21 s | **77 pasan**, 0 fallan |
| Cadena | `.venv/bin/python -m vina_vallehondo_bi.etl.pipeline` | 7 s | OK, con consulta a la API del dólar |
| Notebook 02 | `jupyter nbconvert --to notebook --execute` | 11 s | OK |
| Notebook 03 | ídem | 10 s | OK, controles de integridad en `OK` |
| Notebook 04 | ídem | 5 s | OK |
| Notebook 05 | ídem | 7 s | OK tras la corrección descrita abajo |

La corrida completa, incluida la instalación, toma cerca de 1 minuto y 20 segundos. La duración de la cadena depende de la respuesta de `mindicador.cl`; sin conexión usa la copia guardada en `data/staging/`.

## Filas por capa

| Capa | Tabla | Filas |
|---|---|---:|
| Staging | `stg_ventas` | 13.968 (695 sin moneda) |
| Staging | `stg_costos_productos` | 81 (1 sin costo) |
| Staging | `stg_embarques` | 10.730 |
| Staging | `stg_tipo_cambio` | 716 |
| Processed | `ventas` | 13.830 |
| Processed | `costos_productos` | 96 |
| Processed | `embarques` | 10.715 |
| Processed | `tipo_cambio` | 685 |
| Published | `margen_por_mercado` | 132 |
| Published | `sensibilidad_reglas_margen` | 44 |
| Published | `caso_descuento_brasil` | 2 |
| Published | `escenarios_mezcla` | 4 |
| Published | `serie_mensual_mercado` | 120 |
| Published | `cobertura_margen` | 1 |
| Published | `descuadres_monto_exportacion` | 527 |

Las filas de tipo de cambio crecen con cada día hábil publicado por la API; el resto es fijo. Dimensiones: 11 mercados, 26 clientes, 7 cepas, 2 monedas y 5 vendedores.

## Cifras clave frente a la analítica de Vicente

Vista principal: reglas de Finanzas, CLP, dólar de factura y base completa, salvo que se indique otra cosa. Referencia: [Analítica de Vicente](analitica-e2-vicente.md).

| Cifra | Documento de Vicente | Corrida final | Estado |
|---|---:|---:|---|
| Margen por litro de exportación | 2.210,64 CLP/L | 2.210,64 CLP/L | Coincide |
| Margen por litro de Brasil | 1.718,61 CLP/L | 1.718,61 CLP/L | Coincide |
| Mediana de los diez mercados | 2.289,02 CLP/L | 2.289,02 CLP/L | Coincide |
| Crecimiento de Brasil en litros | 27,58 % | 27,58 % | Coincide |
| Crecimiento de China, México y Reino Unido | 8,72 %, 1,66 % y 0,06 % | 8,72 %, 1,66 % y 0,06 % | Coincide |
| Exportación, base comparable, factura → embarque | 2.201,88 → 2.150,15 CLP/L | 2.201,88 → 2.150,15 CLP/L | Coincide |
| Cobertura de la base comparable (litros de exportación) | 28,4 % | 28,4 % | Coincide |
| Descuento extra de Brasil a volumen fijo | 788,73 MM CLP | 788,73 MM CLP | Coincide |
| Pérdida de volumen de equilibrio | 23,38 % | 23,38 % | Coincide |
| Un punto de descuento en Brasil | 70,62 MM CLP | 70,62 MM CLP | Coincide |
| Registros fuente con margen a fecha de factura | 10.715 de 13.968 (76,7 %) | 10.715 de 13.968 (76,7 %) | Coincide |
| Ventas nacionales y duplicados fuera | 3.115 y 138 | 3.115 y 138 | Coincide |
| Moneda faltante | 695 registros, 691 ventas únicas | 695 registros, 691 ventas únicas | Coincide |
| Costo imputado en exportación | 1.834 ventas | 1.834 ventas | Coincide |
| Montos de exportación recalculados en la E1 | 527 | 527 | Coincide |

## Tablero

Publicado en Streamlit Community Cloud: <https://vina-vallehondo-g7.streamlit.app/>, desde `feature/prototipo-streamlit`, con Python 3.12. Antes de publicarlo se ejecutó la app con `data/published/` vacía, como queda en la nube, y se recorrieron los filtros de moneda, fecha y definición sin errores. La vista de arranque muestra las respuestas del Anexo 4: Brasil 1.718,61 CLP/L, 570,42 CLP/L bajo la mediana, 27,58 % de crecimiento y, con dólar de embarque sobre las mismas ventas, una baja de 51,73 CLP/L (2,35 %) con 28,4 % de cobertura.

## Problemas encontrados en la corrida

1. **El notebook 05 fallaba desde un clon limpio.** Con IPython 9, `%%capture` revisa la celda como código Python y la ruta `./04_metrica_sensibilidad.ipynb` se lee como un número mal escrito (`TokenError: invalid decimal literal`). Antes no fallaba porque había instalada una versión anterior de IPython. Se corrigió dejando la ruta entre comillas; no cambia ninguna cifra.
2. **Python 3.15 no sirve para instalar.** `scripts/setup.sh` usa `python3`, y con Python 3.15 duckdb no tiene paquete precompilado: intenta compilarlo y la instalación se cae. Con Python 3.12 se instala en unos 17 segundos. Si el `python3` del equipo es 3.15 o superior, crear el ambiente con `python3.12 -m venv .venv`.
3. **La cadena modifica un archivo versionado.** Cada corrida actualiza `data/staging/tipo_cambio_2026.json` con los días nuevos de la API. No subir ese cambio en los PR.

## Para actualizar en el informe

- **B.8 y F.1–F.3:** 77 pruebas, 21 s; cadena completa en 7 s con conexión; los cuatro notebooks de respaldo corren completos en 33 s.
- **Ventas con fecha 2026 y montos ×10:** el notebook 02 informa **82 ventas** reasignadas de 2026 a 2025 y **55** divididas por 10 en toda la fuente. De ellas, **67** y **45** son de exportación, que son las cifras del mensaje de Vicente. Indicar el universo al citar cada número para que el informe no parezca contradecirse.
- **Notebook 02:** su tabla final compara contra el Informe 1 y mantiene cuatro filas en «Revisar» o «Agregar» (rango de descuento de los otros mercados, tratamiento de las ventas 2026, mercado con descuento cercano a 13 % y regla para completar costos). Son diferencias ya conocidas de la E1, pero conviene confirmarlas en F.3.

## Aporte para F.4 · Uso de IA

Borrador; ajustar la columna de revisión a lo que efectivamente se haya revisado.

| Integrante | Herramienta | Uso | Revisión manual |
|---|---|---|---|
| Maximiliano Tombolini | Claude (Claude Code) | Preparar el entorno, ejecutar la corrida final desde un clon limpio, diagnosticar y corregir la falla del notebook 05, ajustar el tema del tablero y redactar este registro. | Comparación de las cifras de la corrida con la analítica de Vicente, revisión del diff de cada cambio antes de subirlo y revisión del tablero publicado con la vista de arranque. |
