# Entrega 2 · Viña Vallehondo · Analítica de Vicente

Material para incorporar al Informe 2 del Grupo 7. Cifras de exportación de 2025, por semestre de factura. La vista principal usa pesos chilenos, dólar observado a fecha de factura y las reglas de Finanzas aplicables al extracto. MM CLP significa millones de pesos. Los textos y las cifras provienen de la corrida sobre el extracto con la caché versionada del dólar.

## A · Registro de mejora

La tabla corta y A.1 van primero en el cuerpo. Pasar el detalle al Anexo 1 si las dos tablas juntas exceden una página. Las referencias indican la sección de destino. Completar las páginas con el Word final y verificar las filas que requieren evidencia del resto del equipo.

| Origen | Observación o requisito | Qué hicimos o qué queda por confirmar | Dónde |
|---|---|---|---|
| Informe 1 | Explicar cajas y litros como medidas distintas. | Se distinguió la unidad comercial de la unidad de análisis y se verificó la equivalencia de ambos formatos y su efecto sobre el resultado. | Mandato y C.9 |
| Informe 1 y P1 | Mostrar el resultado con monto facturado y sin reversar mermas. | Se aisló el efecto de cada regla y se compararon ambos ajustes con la E1. Se identificaron los 527 montos de exportación que habían sido recalculados. | C.7–C.9 |
| Informe 1 | Diagrama legible con claves y medidas. | Registrar la incorporación de PK, FK y medidas al verificar el diagrama de Catalina. | C.1 |
| Enunciado E2 | Identificar autor y fecha de cada supuesto y declarar uso de IA con verificación manual. | La plantilla ya trae nombres y fechas para los supuestos históricos. Confirmar los supuestos nuevos y las declaraciones de cada integrante. | Anexo 3 y F.4 |
| P1 | El resultado apareció después de la portada y se usaron siete láminas. | Verificar en P2 que la primera lámina abra con cifra, recomendación, valor, costo y cambio respecto de P1, dentro del máximo de seis láminas. | Presentación 2 |
| P1 | Un solo gráfico, bajo contraste y faltó descomponer la brecha y mostrar el equilibrio. | Se recalcularon los insumos de ambas figuras. Registrar el cambio de diseño y las figuras incorporadas por Catalina y Benjamín. | E.1 y D.2 |
| Anexo 7 del enunciado E2 | Elegir moneda y fecha, mostrar equivalencia y cobertura y distinguir recomendación de hipótesis. | Se calcularon las combinaciones por mercado, la cobertura en litros y los escenarios de descuento y mezcla. Verificar su uso en la pantalla final. | C.9, D.2 y E.4 |
| Revisión interna | Conteo de pruebas, duración y monedas faltantes tenían más de un valor. | Se distinguieron 695 registros de origen y 691 ventas únicas sin moneda. Actualizar pruebas y duración con la corrida integrada de Maximiliano. | B.8, F.1–F.3 |

### A.1 · Número de la E1 y número de hoy

| Cifra | E1 | E2 | Cambio | Motivo |
|---|---:|---:|---:|---|
| Margen por litro de exportación | 2.201,93 CLP/L | 2.210,64 CLP/L | +8,71 CLP/L | Ingreso facturado +321,65 MM CLP y costo reconocido +222,72 MM CLP. |
| Margen por litro de Brasil | 1.705,27 CLP/L | 1.718,61 CLP/L | +13,33 CLP/L | Ingreso facturado +37,59 MM CLP y costo reconocido +17,54 MM CLP. |
| Mediana de los diez mercados | 2.266,15 CLP/L | 2.289,02 CLP/L | +22,88 CLP/L | Se vuelve a calcular con el margen de cada mercado bajo el criterio E2. |
| Brecha de Brasil frente a la mediana | 843,47 MM CLP | 857,82 MM CLP | +14,35 MM CLP | La mediana subió más que el margen por litro de Brasil. |
| Escenario de descuento implícito adicional, a volumen fijo | 783,83 MM CLP (92,93 % de la brecha) | 788,73 MM CLP (91,95 % de la brecha) | +4,91 MM CLP | Al conservar los montos facturados cambian las tasas implícitas de Brasil y de los otros mercados. |
| Pérdida de volumen de equilibrio en ese escenario | 23,41 % | 23,38 % | −0,03 pp | Se recalculó con el margen inicial y el margen del escenario. |
| Registros fuente con margen de exportación a fecha de factura | 76,7 % | 76,7 % | 0,0 pp | El cambio afecta ingresos y costo, y conserva las 10.715 ventas de exportación. |

Las cifras E1 se presentan con dos decimales para conciliar los cambios. El PDF las reportó redondeadas. Las diferencias se calcularon antes de redondear.

## Mandato acordado · Cajas y litros

En la entrevista del 4 de septiembre, la contraparte explicó que las ventas se comercializan en cajas y que Operaciones trabaja con litros por cepa y nivel de calidad [V]. También señaló que la equivalencia puede variar según el formato [V]. En el extracto recibido, los dos formatos registrados, 12 botellas de 750 ml y 6 botellas de 1,5 L, equivalen a 9 L por caja [M]. El grupo eligió los litros netos para comparar mercados y mantuvo las cajas netas como medida comercial. El crecimiento es la variación entre el segundo y el primer semestre de 2025, asignados por fecha de factura. La referencia de buen margen es la mediana de los diez mercados bajo la configuración de cálculo que se muestra.

## C.7 y C.8 · Definición y alternativas

El **margen bruto del producto por litro** es la suma del ingreso neto facturado menos la suma del costo del producto, dividida por los litros netos de las mismas líneas. Se calcula por mercado de exportación, antes de flete, seguro y comisiones. El extracto permite incorporar las mermas y los ajustes identificados en las ventas. Falta el detalle separado de notas de crédito y la conciliación con contabilidad que pidió la contraparte para decidir la renovación.

El ingreso conserva el monto neto registrado, luego de normalizar la escala en los casos identificados como multiplicados por diez. Las diferencias con cajas × precio × (1 − descuento) quedan identificadas por venta. Las mermas reducen ingreso y volumen, y el costo reconocido en la venta original se conserva. El costo unitario corresponde al producto y la añada, con imputación por nivel y añada donde falta.

Finanzas confirmó el dólar observado de **factura** como referencia contable el 11 de noviembre [V]. En CLP se convierte el ingreso en USD por línea. En USD se conserva el ingreso en su moneda de facturación y se divide el costo en CLP por el tipo de cambio de esa misma línea. La fecha de **embarque** permite medir sensibilidad en el subconjunto con fecha confiable y dólar disponible para ambos momentos. La fecha de factura sigue determinando el semestre y el año de análisis en las dos vistas. La fecha efectiva de cobro no viene en el extracto.

La definición está implementada en `src/vina_vallehondo_bi/etl/margins.py`. Los CSV de una misma corrida son la referencia para el informe y el tablero.

## C.9 · Resultados

### Efecto de las dos reglas de Finanzas

| Cifra en CLP/L, dólar de factura | E1 | Solo monto facturado | Solo sin reversa de mermas | Ambos ajustes |
|---|---:|---:|---:|---:|
| Total exportación | 2.201,93 | 2.230,24 | 2.182,32 | 2.210,64 |
| Brasil | 1.705,27 | 1.730,27 | 1.693,61 | 1.718,61 |
| Mediana de mercados | 2.266,15 | 2.299,94 | 2.255,22 | 2.289,02 |

En exportación, conservar el monto facturado suma 28,31 CLP/L y eliminar la reversa de costo resta 19,60 CLP/L. El efecto conjunto es de +8,71 CLP/L. De las 691 ventas únicas con monto recalculado en la E1, 527 son de exportación. Hay 110 líneas de merma en total y 85 en exportación. Brasil permanece último y los diez mercados conservan su clase de margen. México pasa del tercer al segundo lugar y Reino Unido pasa del segundo al tercero.

### Cajas y litros

Brasil pasó de **73.422 a 93.673 cajas netas** entre semestres, equivalentes a **660.798 y 843.057 litros**. Ambas medidas dan un crecimiento de **27,58 %**. El margen corregido de Brasil es **1.718,61 CLP/L**, equivalente a **15.467,47 CLP/caja** con los valores sin redondear. Los 9 L por caja multiplican el margen unitario por el mismo factor en todos los mercados, de modo que su orden y su posición frente a la mediana se conservan.

### Moneda, fecha y cobertura

| Dólar de referencia y base de ventas, reglas de Finanzas | Exportación CLP/L | Brasil CLP/L | Exportación USD/L | Brasil USD/L | Cobertura exportación en litros |
|---|---:|---:|---:|---:|---:|
| Factura, base completa | 2.210,64 | 1.718,61 | 2,3234 | 1,8080 | 100,0 % |
| Factura, base comparable | 2.201,88 | 1.632,25 | 2,3132 | 1,7187 | 28,4 % |
| Embarque, base comparable | 2.150,15 | 1.588,95 | 2,2842 | 1,6911 | 28,4 % |

Sobre las mismas 3.064 ventas, usar el dólar de embarque reduce el margen en **51,73 CLP/L (2,35 %)**. Brasil sigue último. Estados Unidos y Japón, y Canadá y Países Bajos, intercambian puestos dentro de sus grupos de margen. Ningún mercado cambia de clase en CLP. Comparar directamente la vista de factura completa con la de embarque incorporaría también un cambio de cobertura.

## E.4 · Mercados con recomendación y con hipótesis

| Mercado | Estado | Qué indican los datos y qué falta |
|---|---|---|
| Brasil | Recomendación de revisar las condiciones antes de renovarlas | Creció 27,58 % y dejó 570,42 CLP/L bajo la mediana. Se puede evaluar una reducción gradual o condicionada a volumen y margen. El volumen que se perdería y el margen final con flete, comisiones y notas de crédito requieren validación. La serie mensual muestra el comportamiento durante 2025, un año en que el descuento ya estaba vigente. |
| China | Hipótesis de mezcla | Creció 8,72 %, dejó 2.190,73 CLP/L y el 41,68 % de sus litros fue varietal. Medir si los clientes comprarían más reserva al margen observado antes de cambiar la oferta. |
| Demás mercados | Seguimiento | La comparación semestral y el margen sirven para monitoreo. Para interpretar caídas como pérdida de mercado se requiere una base interanual comparable. |

**Un punto porcentual de descuento en Brasil** equivale a **70,62 MM CLP** de margen bruto del producto si se mantienen el precio de lista, los costos, la mezcla y el volumen de 2025. El cálculo aplica 1 % a un bruto de 7.061,71 MM CLP. Es el efecto directo antes de cambios en demanda. En el escenario comparable con E1, igualar el descuento implícito del resto representa hasta 788,73 MM CLP a volumen fijo. El margen modelado se iguala al actual si Brasil pierde cerca de 23,38 % del volumen, con margen unitario del escenario constante y sin reubicar los litros perdidos. Para usar este umbral en la renovación se requiere conciliación con Finanzas.

**Un punto porcentual de mezcla** corresponde a reasignar el 1 % de los litros netos del mercado de un nivel a otro. Se usa el margen observado por litro de cada nivel, con volumen total constante y precios, costos y descuentos por nivel fijos.

| Mercado | Litros reasignados | Varietal → Reserva | Varietal → Gran Reserva |
|---|---:|---:|---:|
| Brasil | 15.038,55 | +14,97 MM CLP | +38,84 MM CLP |
| China | 10.465,65 | +12,59 MM CLP | +32,67 MM CLP |

El **descuento comercial ponderado** de Brasil es 13,76 % y el del resto 2,66 %, calculados desde el campo de descuento. El **descuento implícito** se obtiene como 1 − monto neto / bruto. Bajo el criterio E2 es 13,23 % para Brasil y 2,06 % para el resto. El escenario de 788,73 MM CLP usa la tasa implícita para reproducir el enfoque de E1 y puede recoger otros descuadres del monto neto. Presentarlo como escenario de margen, sujeto a conciliación. Para la decisión comercial, igualar la tasa declarada del resto, conservando los demás ajustes de factura, da **783,81 MM CLP** a volumen fijo y un equilibrio de **23,27 %** de caída de volumen. El valor de un punto de descuento usa directamente el bruto.

## F.1 y F.3 · Cobertura y consistencia

En factura entran **10.715 de 13.968 registros (76,7 %)**, igual que en la E1. Quedan fuera **3.115 ventas nacionales (22,3 %)** y **138 duplicados (1,0 %)**. Con la definición principal se calcula margen para el **100 % de los 11.360.529 litros netos de exportación**. La alternativa por embarque cubre **3.224.898 L (28,4 %)** de exportación. En Brasil cubre **28,1 %**. Las 3.064 ventas comparables representan el 28,6 % de las ventas de exportación. Se imputó el costo de 1.834 ventas de exportación (17,1 %) y la moneda de 556. En toda la fuente había 695 registros sin moneda, equivalentes a 691 ventas únicas después de deduplicar.

| Regla | Definición para el informe |
|---|---|
| Período | Exportación 2025. S2 vs. S1 por factura, también cuando se cambia la fecha de conversión. |
| Vara de buen margen | Mediana de los diez mercados de la misma combinación de reglas, moneda, fecha y base. Principal: 2.289,02 CLP/L. |
| Fecha oficial y sensibilidad | Dólar observado de factura para la cifra oficial. Factura y embarque sobre el mismo subconjunto para medir sensibilidad. |
| Volumen | Cajas netas. Litros netos según el formato, 9 L por caja en ambos formatos del extracto. |
| Ingreso y costo | Monto facturado normalizado por escala y costo de producto por añada. Merma con ingreso y volumen negativos y sin reversa de costo. La E1 queda como comparación histórica. |
| Descuento | Tasa comercial ponderada para describir lo otorgado. Tasa implícita para el escenario comparable con la E1. |
| Alcance de margen | Margen bruto del producto, antes de flete, seguro y comisiones. Conciliación de notas de crédito pendiente. |

Revisar en el Word que C.6–C.8, E.2–E.5 y los supuestos 8, 11, 14, 15, 19 y 20 del Anexo 3 no mezclen reglas ni valores de la E1 con la vista principal. Para F.4, dejar constancia del uso de ChatGPT/Codex para apoyar implementación, cálculos y redacción, y completar la columna de revisión manual con las comprobaciones que Vicente efectivamente haga.

### Anexo 3 · Supuestos analíticos nuevos para validar con el grupo

| Supuesto | Justificación | Efecto si cambia |
|---|---|---|
| Conservar el ajuste de escala de los montos ×10 junto con sus cajas. | El extracto registra el mismo factor en ambas variables. Los descuadres posteriores quedan para conciliación. | Usar el importe sin normalizar inflaría el ingreso de esas ventas. |
| Mantener el costo de las mermas en la venta original. | Finanzas indicó que la caja descartada no vuelve a inventario. Se evita acreditar costo o volver a reconocerlo en la línea negativa. | Una regla de reversa cambia el costo de exportación en 222,72 MM CLP. |
| Medir la sensibilidad del dólar sobre ventas comparables. | Usar las mismas líneas aísla el efecto de la fecha elegida. | Comparar bases de cobertura distintas mezcla selección de ventas con tipo de cambio. |
| Simular el cambio de un punto de mezcla con márgenes unitarios históricos. | Permite estimar el orden de magnitud con el extracto. | Cambios en precio, descuento, costo o demanda por nivel modifican el valor del escenario. |

Responsable propuesto de las decisiones analíticas: Vicente San Juan. Registrar la fecha en que el equipo confirme cada regla.

## Anexo 4 · Respuestas esperadas de la prueba de uso

Antes de iniciar, dejar seleccionados CLP, factura y reglas de Finanzas. Para la pregunta 3, la pantalla debe mostrar la comparación sobre el subconjunto común o permitir ver ambos valores de ese subconjunto.

| Pregunta | Respuesta esperada |
|---|---|
| ¿Qué mercado deja menos margen por litro y cuánto menos que un mercado típico? | **Brasil, 1.718,61 CLP/L**, **570,42 CLP/L** bajo la mediana de **2.289,02 CLP/L**. |
| ¿Cuánto creció Brasil en litros y qué otros mercados crecieron? | **27,58 %**. También crecieron China (**8,72 %**), México (**1,66 %**) y Reino Unido (**0,06 %**). |
| Si se usa el dólar de embarque, ¿cambia el mercado que deja menos margen? ¿Cuánto baja el margen de exportación? | **Brasil sigue último**. En la base común, exportación pasa de **2.201,88 a 2.150,15 CLP/L**, una caída de **51,73 CLP/L (2,35 %)**. Cobertura: **28,4 %** de los litros de exportación. |
| Pregunta de reserva · ¿Brasil es una recomendación o una hipótesis? | **Recomendación de revisar el descuento antes de renovarlo**. La respuesta del volumen a una reducción y el margen final conciliado son asuntos por validar. |

## Entrega de datos para el tablero

La vista de arranque usa `criterio=reglas_finanzas`, `moneda=CLP`, `fecha_conversion=factura` y `base=disponible`. Para el cambio de fecha se usa `base=comparable` en ambos casos. En la tarjeta de Brasil, `cobertura_litros_pct` debe salir de la fila de Brasil. El total exportación tiene su propia fila y cobertura. Los litros S1/S2 y el crecimiento siempre describen la base completa por factura. El margen y los litros cubiertos responden a la selección de cálculo. Los 10 mercados y el total tienen 12 combinaciones publicadas.
