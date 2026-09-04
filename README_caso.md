# Viña Vallehondo (rubro: vino, exportación)

## Contexto del rubro
El vino chileno es uno de los grandes embajadores del pais: Chile esta entre los mayores exportadores de vino del
mundo, y la mayor parte de lo que producen las vinas grandes y medianas se vende afuera. Eso convierte al negocio
en una historia de dos monedas: se produce con costos en pesos, pero se vende en dolares (y a veces euros), asi que
lo que finalmente entra a la caja depende tanto de que tan bien se vendio como de como se movio el tipo de cambio.

Tres rasgos definen al sector y explican por que los datos importan tanto:
- Se cobra en moneda extranjera. Una exportacion facturada en dolares puede verse como un buen negocio y, sin
  embargo, rendir menos en pesos si el peso se aprecia. Mirar solo los dolares (o solo los pesos) engaña: hay que
  mirar las dos monedas y el tipo de cambio del dia.
- El valor esta en la mezcla, no solo en el volumen. No es lo mismo vender mucho vino barato que vender un poco
  menos de vino fino. La premiumizacion (vender mayor proporcion de reservas y gran reservas) sube el precio
  promedio por litro sin tocar los precios de lista. Es una palanca de margen que no se ve si solo se cuentan cajas.
- Cada mercado tiene su propia economia. Un pais puede crecer fuerte en volumen y aun asi dejar poco margen, por
  descuentos, por el mix de productos que compra o por costos de llegar hasta alla. Crecer en el mercado equivocado
  es crecer hacia abajo.

La pregunta de fondo ya no es "cuantas cajas exportamos", sino "cuanto de lo que crecimos es valor real en pesos, y
en que mercados y productos se esta creando o destruyendo margen".

## La empresa
Viña Vallehondo es una productora y exportadora chilena de vino, de tamano mediano. Vende una parte en el mercado
nacional (en pesos) y la mayor parte a exportacion (principalmente en dolares), a distribuidores e importadores en
LatAm, Norteamerica, Europa y Asia. Su catalogo cubre varias cepas y tres niveles de calidad: varietal, reserva y
gran reserva. Cada venta sale de la bodega en cajas, se factura en una moneda y despues se embarca a destino, a
veces semanas despues de la venta.

Durante 2025 la gerencia comercial celebra que las exportaciones en dolares crecieron, pero el area de finanzas
esta inquieta: al convertir a pesos, el resultado no se ve tan bien, y ademas no todos los mercados que crecieron
dejaron el mismo margen. El directorio quiere entender que parte del crecimiento es valor real y donde se esta
ganando o perdiendo plata. Nadie ha cruzado todavia las cuatro fuentes con esa lente. Ahi entran ustedes, un equipo
externo con acceso a los datos de la vina para responder con evidencia.

## Conceptos clave del rubro
- Cepa: la variedad de uva (Cabernet Sauvignon, Merlot, Carménère, Chardonnay, etc.). Define el tipo de vino.
- Varietal, reserva y gran reserva (tiers): niveles de calidad y precio, de menor a mayor. El gran reserva vale
  bastante mas por litro que el varietal.
- Anada: el ano de la cosecha de la uva con que se hizo el vino. Influye en el costo y a veces en el precio.
- Premiumizacion: vender una mayor proporcion de vinos de tier alto, lo que sube el precio promedio por litro sin
  subir los precios de lista.
- Mercado de exportacion: el pais o la zona de destino. Cada uno con su moneda, su logistica y su margen.
- Incoterm (FOB, CIF): las reglas de quien paga que en una exportacion. FOB, el comprador paga el flete desde el
  puerto de origen; CIF, el vendedor incluye flete y seguro hasta el destino.
- Tipo de cambio: cuantos pesos vale un dolar. Si el peso se aprecia (el dolar baja), una misma venta en dolares
  rinde menos pesos.
- Nominal vs real: crecer en dolares es nominal; lo que importa para la empresa es cuanto rinde en pesos, su moneda
  de costos.
- Caja vs litro: el vino se vende en cajas, pero para comparar precios conviene mirar el precio por litro. Una caja
  estandar de 12 botellas de 750 ml son 9 litros; hay formatos distintos.

## Preguntas que la gerencia busca entender
Son las mismas para los tres equipos que trabajan este caso:
1. Las exportaciones crecieron en dolares, pero al convertir a pesos, siguen creciendo o se aplanan? Cuanto del
   resultado es tipo de cambio?
2. El precio promedio por litro que subio, es porque subimos precios o porque vendimos mas proporcion de gran
   reserva (premiumizacion)?
3. Que mercados crecieron en volumen, y de esos, cuales dejaron buen margen y cuales crecieron dejando poco?
4. Para convertir las ventas de exportacion a pesos, que fecha conviene usar, la de la venta o la del embarque? Y
   que es el ingreso neto que hay que comparar contra el costo?

## Fuentes disponibles
La empresa entrega cuatro fuentes:
- `origen_vina.sqlite`: la base comercial, con varias tablas relacionadas: ventas, clientes (distribuidores e
  importadores), mercados, zonas, cepas, monedas y vendedores.
- `origen_costos_productos.csv`: los costos por producto y anada, con la equivalencia de cajas a litros, del area
  de Costos.
- `origen_embarques.json`: los embarques de exportacion, con la fecha de embarque, el incoterm y el puerto de
  destino.
- La API del dolar observado, desde `https://mindicador.cl/api/dolar/2025`.
