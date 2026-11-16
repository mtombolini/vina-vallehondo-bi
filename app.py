"""Prototipo E2 · Viña Vallehondo · Grupo 7.

Una pantalla, una pregunta. Lee solo los CSV que publica la cadena en
data/published/, así que se actualiza al volver a correr el pipeline:

    python -m vina_vallehondo_bi.etl.pipeline
    streamlit run app.py

Si data/published/ está vacía (por ejemplo, en Streamlit Community Cloud,
donde las capas no se versionan), la app corre la cadena al iniciar.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent
PUBLISHED = RAIZ / "data" / "published"
TABLAS = ("margen_por_mercado.csv", "caso_descuento_brasil.csv", "escenarios_mezcla.csv")
FOCO = "Brasil"
TOTAL = "Total exportación"

# Textos del pie que no salen de los datos. Ajustar con B.7 (acuerdo de servicio).
DUENO_DATO = "Gerencia de Finanzas (por confirmar en B.7)"
CERTIFICACION = "Finanzas confirmó el dólar observado de factura como referencia contable (11-nov-2026)"

ETIQUETA_CRITERIO = {"reglas_finanzas": "Finanzas", "e1": "Nuestra (E1)"}
ETIQUETA_FECHA = {"factura": "Factura (oficial)", "embarque": "Embarque (sensibilidad)"}


# ---------------------------------------------------------------- utilidades
def num(x: float, dec: int = 2) -> str:
    """Número con formato chileno: 1.718,61."""
    texto = f"{x:,.{dec}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_data(show_spinner=False)
def leer(nombre: str, marca: float) -> pd.DataFrame:
    # `marca` es la fecha de modificación del archivo: si la cadena vuelve a
    # correr, cambia y se invalida la caché.
    return pd.read_csv(PUBLISHED / nombre)


def correr_cadena() -> subprocess.CompletedProcess:
    """Ejecuta el mismo comando del README y deja las tablas en data/published/."""
    entorno = {**os.environ, "PYTHONPATH": str(RAIZ / "src")}
    return subprocess.run(
        [sys.executable, "-m", "vina_vallehondo_bi.etl.pipeline", "--project-root", str(RAIZ)],
        cwd=RAIZ, env=entorno, capture_output=True, text=True, timeout=300,
    )


def cargar(nombre: str) -> pd.DataFrame:
    ruta = PUBLISHED / nombre
    if not ruta.exists():
        st.error(
            f"No existe `data/published/{nombre}`. Corre primero la cadena: "
            "`python -m vina_vallehondo_bi.etl.pipeline`."
        )
        st.stop()
    return leer(nombre, ruta.stat().st_mtime)


# ---------------------------------------------------------------- datos
st.set_page_config(page_title="Viña Vallehondo · Margen por mercado", layout="wide")

if not all((PUBLISHED / t).exists() for t in TABLAS):
    with st.spinner("Corriendo la cadena de datos por primera vez (unos segundos)…"):
        resultado = correr_cadena()
    if resultado.returncode != 0:
        st.error("La cadena falló. Detalle:")
        st.code(resultado.stderr[-3000:] or resultado.stdout[-3000:])
        st.stop()

margen = cargar("margen_por_mercado.csv")
caso = cargar("caso_descuento_brasil.csv")
mezcla = cargar("escenarios_mezcla.csv")
ultima_corrida = datetime.fromtimestamp(
    (PUBLISHED / "margen_por_mercado.csv").stat().st_mtime, ZoneInfo("America/Santiago")
)

# ---------------------------------------------------------------- 1. título y filtros
st.title("¿Qué mercados de exportación crecieron en volumen y cuáles crecieron dejando poco margen?")
st.caption(
    "Exportación 2025 · 2.º semestre vs. 1.er semestre, por fecha de factura · "
    "Margen bruto del producto por litro, antes de flete, seguro y comisiones  \n"
    "**Para quién:** gerente comercial y encargados de mercado, mensual tras el cierre · "
    "gerencia general y Finanzas, trimestral y antes de cada renovación de condiciones comerciales"
)

f1, f2, f3, f4, f5 = st.columns([1, 1.3, 1.1, 1.1, 1.2])
moneda = f1.radio("Moneda", ["CLP", "USD"], horizontal=True)
fecha = f2.radio(
    "Fecha del dólar", ["factura", "embarque"], format_func=ETIQUETA_FECHA.get, horizontal=True
)
criterio = f3.radio(
    "Definición", ["reglas_finanzas", "e1"], format_func=ETIQUETA_CRITERIO.get, horizontal=True
)
# El dólar de embarque solo existe para un subconjunto de ventas: en ese caso
# la comparación se hace siempre sobre las mismas ventas.
mismas_ventas = f4.toggle(
    "Mismas ventas",
    value=(fecha == "embarque"),
    disabled=(fecha == "embarque"),
    help="Usa solo las ventas que tienen dólar de factura y de embarque, para que "
    "cambiar la fecha no cambie también qué ventas entran.",
)
base = "comparable" if (fecha == "embarque" or mismas_ventas) else "disponible"
paises = sorted(p for p in margen["pais"].unique() if p != TOTAL)
destacado = f5.selectbox("Mercado a destacar", paises, index=paises.index(FOCO))

sel = margen[
    (margen["criterio"] == criterio)
    & (margen["moneda"] == moneda)
    & (margen["fecha_conversion"] == fecha)
    & (margen["base"] == base)
]
if sel.empty:
    st.warning("La cadena no publicó esta combinación de filtros.")
    st.stop()

mercados = sel[sel["pais"] != TOTAL].copy()
total = sel[sel["pais"] == TOTAL].iloc[0]
foco = sel[sel["pais"] == destacado].iloc[0]
mediana = float(foco["mediana_margen_por_litro"])
unidad = f"{moneda}/L"
dec = 2 if moneda == "CLP" else 4

# ---------------------------------------------------------------- 2. cifra clave y secundarias
k1, k2, k3, k4 = st.columns([1.4, 1, 1, 1])
k1.metric(
    f"Margen por litro de {destacado}",
    f"{num(foco['margen_por_litro'], dec)} {unidad}",
    delta=f"{num(foco['margen_por_litro'] - mediana, dec)} {unidad} vs. mediana ({num(mediana, dec)})",
    delta_color="off",
    delta_arrow="off",
    border=True,
    help="La mediana de los diez mercados es la vara de buen margen, con los mismos filtros.",
)
k2.metric(
    "Cobertura (% de los litros con margen)",
    f"{num(foco['cobertura_litros_pct'], 1)} %",
    delta=f"Exportación total: {num(total['cobertura_litros_pct'], 1)} %",
    delta_color="off",
    delta_arrow="off",
    help="Porcentaje de los litros netos con margen calculado bajo esta combinación.",
)
k3.metric(
    f"Crecimiento de {destacado} en litros",
    f"{num(foco['crecimiento_litros_pct'], 2)} %",
    delta=f"{num(foco['litros_s1'], 0)} → {num(foco['litros_s2'], 0)} L · "
    f"{num(foco['litros_totales'] / foco['cajas_totales'], 0)} L por caja",
    delta_color="off",
    delta_arrow="off",
    help="Siempre sobre todas las ventas por fecha de factura.",
)
fila_caso = caso[caso["criterio"] == criterio].iloc[0]
k4.metric(
    f"Costo del descuento extra de {FOCO}",
    f"{num(fila_caso['descuento_extra_clp'] / 1e6, 2)} MM CLP",
    delta=f"Cada punto de descuento: {num(fila_caso['un_punto_descuento_clp'] / 1e6, 2)} MM CLP",
    delta_color="off",
    delta_arrow="off",
    help=(
        f"Igualar el descuento implícito de {FOCO} al del resto, a volumen fijo: "
        f"{num(fila_caso['proporcion_brecha_pct'], 1)} % de la brecha frente a la mediana. "
        f"El margen se iguala si {FOCO} pierde {num(fila_caso['perdida_volumen_equilibrio_pct'], 1)} % "
        "del volumen. En CLP con dólar de factura: no cambia con los filtros de moneda y fecha."
    ),
)
st.info(
    "**Margen bruto del producto:** no descuenta flete, comisiones ni notas de crédito, que no vienen "
    "en el extracto. Finanzas pidió margen neto de esos costos para decidir la renovación, así que "
    f"{FOCO} queda como recomendación de *revisar* el descuento, condicionada a esa conciliación. "
    "El dólar oficial es el de factura (cuadra con contabilidad); embarque es solo sensibilidad.",
    icon="ℹ️",
)
if base == "comparable":
    otra = margen[
        (margen["criterio"] == criterio) & (margen["moneda"] == moneda) & (margen["base"] == "comparable")
        & (margen["pais"] == TOTAL)
    ].set_index("fecha_conversion")["margen_por_litro"]
    if {"factura", "embarque"} <= set(otra.index):
        cambio = otra["embarque"] - otra["factura"]
        st.caption(
            f"Sobre las mismas ventas, exportación total: {num(otra['factura'], dec)} {unidad} con dólar de factura "
            f"y {num(otra['embarque'], dec)} {unidad} con dólar de embarque "
            f"({num(cambio, dec)} {unidad}, {num(cambio / otra['factura'] * 100, 2)} %)."
        )

# ---------------------------------------------------------------- 3. gráfico que explica la cifra
ultimo = mercados.loc[mercados["margen_por_litro"].idxmin(), "pais"]
bajo_mediana = int((mercados["margen_por_litro"] < mediana).sum())
st.subheader(
    f"{ultimo} deja el menor margen por litro de los {len(mercados)} mercados; "
    f"{bajo_mediana} quedan bajo la mediana"
)
mercados["grupo"] = mercados["pais"].where(mercados["pais"] == destacado, "Otros mercados")
mercados["etiqueta"] = mercados["margen_por_litro"].map(lambda v: num(v, dec))
mercados["etiqueta_barra"] = [
    f"{num(m, dec)} {unidad} · {num(l / 1e3, 0)} mil L ({'+' if c >= 0 else ''}{num(c, 1)} %)"
    for m, l, c in zip(mercados["margen_por_litro"], mercados["litros_s2"], mercados["crecimiento_litros_pct"])
]
orden = mercados.sort_values("margen_por_litro", ascending=False)["pais"].tolist()
eje_y = alt.Y("pais:N", sort=orden, title=None, scale=alt.Scale(paddingInner=0.12))
x_max = float(mercados["margen_por_litro"].max())
eje_x = alt.X(
    "margen_por_litro:Q",
    title=f"Margen bruto por litro ({unidad})",
    scale=alt.Scale(domain=[0, x_max * 1.12], nice=False),
    axis=alt.Axis(labelExpr="replace(datum.label, ',', '.')", tickCount=6),
)
barras = alt.Chart(mercados).mark_bar().encode(
    y=eje_y,
    x=eje_x,
    color=alt.Color(
        "grupo:N",
        scale=alt.Scale(domain=[destacado, "Otros mercados"], range=["#1f4e79", "#c3ccd5"]),
        legend=None,
    ),
    tooltip=[
        alt.Tooltip("pais:N", title="Mercado"),
        alt.Tooltip("etiqueta:N", title=f"Margen ({unidad})"),
        alt.Tooltip("crecimiento_litros_pct:Q", title="Crecimiento litros (%)", format=".2f"),
        alt.Tooltip("cobertura_litros_pct:Q", title="Cobertura (%)", format=".1f"),
    ],
)
# Etiquetas al final de cada barra (solo el margen) y, aparte, una columna con el volumen.
textos = alt.Chart(mercados).mark_text(align="left", dx=8, fontWeight="bold").encode(
    y=eje_y,
    x=alt.value(0),
    text="etiqueta:N",
    color=alt.condition(alt.datum.pais == destacado, alt.value("white"), alt.value("#222")),
)
mercados["etiqueta_volumen"] = [
    f"{num(l / 1e3, 0)} mil L ({'+' if c >= 0 else ''}{num(c, 1)} %)"
    for l, c in zip(mercados["litros_s2"], mercados["crecimiento_litros_pct"])
]
volumen = (
    alt.Chart(mercados)
    .mark_text(align="left", color="#333")
    .encode(y=alt.Y("pais:N", sort=orden, axis=None, scale=alt.Scale(paddingInner=0.12)),
            x=alt.value(0), text="etiqueta_volumen:N")
    .properties(width=170, title="Litros 2.º sem. (crec.)")
)
linea = alt.Chart(pd.DataFrame({"m": [mediana]})).mark_rule(strokeDash=[5, 4], color="#333").encode(x="m:Q")
texto_linea = (
    alt.Chart(pd.DataFrame({"m": [mediana], "t": [f"Mediana {num(mediana, dec)}"]}))
    .mark_text(align="left", dx=4, dy=-8, color="#333", fontWeight="bold")
    .encode(x="m:Q", y=alt.value(0), text="t:N")
)
grafico, _ = st.columns([3, 1])  # más angosto que la página completa
grafico.altair_chart(
    alt.hconcat((barras + textos + linea + texto_linea).properties(height=440, width=620), volumen.properties(height=440), spacing=12)
    .configure_view(stroke=None)
    .configure_title(fontSize=12, anchor="start", color="#555"),
)

# ---------------------------------------------------------------- 4. corte por mercado
st.subheader("Qué hacer con cada mercado")
c1, c2, c3 = st.columns(3)
for col, estado, nota in [
    (c1, "Recomendación de revisión", "Revisar las condiciones antes de renovarlas."),
    (c2, "Hipótesis de mezcla", "Medir si comprarían más reserva antes de cambiar la oferta."),
    (c3, "Seguimiento", "Monitorear; sin base interanual para leer caídas."),
]:
    filas = mercados[mercados["estado_decision"] == estado].sort_values("crecimiento_litros_pct", ascending=False)
    col.markdown(f"**{estado}** · {nota}")
    if estado == "Seguimiento":
        col.markdown(", ".join(filas["pais"]) + ".")
        continue
    col.markdown(
        "\n".join(
            f"- **{r.pais}:** {'+' if r.crecimiento_litros_pct >= 0 else ''}{num(r.crecimiento_litros_pct, 1)} % en litros, "
            f"{num(r.margen_por_litro, dec)} {unidad}"
            for r in filas.itertuples()
        )
    )
# Anexo 7: "¿Cuánto vale cada punto de mezcla, en pesos?"
st.markdown("**Cuánto vale un punto de mezcla** (pasar el 1 % de los litros del mercado desde Varietal, en MM CLP de margen)")
tabla_mezcla = mezcla.pivot(index="pais", columns="destino", values="variacion_margen_clp") / 1e6
st.dataframe(
    pd.DataFrame(
        {
            "Mercado": tabla_mezcla.index,
            "Litros reasignados": mezcla.groupby("pais")["litros_reasignados"].first().map(lambda v: num(v, 0)).values,
            "Varietal → Reserva": tabla_mezcla["Reserva"].map(lambda v: f"+{num(v, 2)} MM CLP").values,
            "Varietal → Gran Reserva": tabla_mezcla["Gran Reserva"].map(lambda v: f"+{num(v, 2)} MM CLP").values,
        }
    ),
    hide_index=True,
)
st.caption(
    "Con el margen observado por litro de cada nivel en 2025, volumen total constante y precios, costos "
    f"y descuentos por nivel fijos. Un punto de descuento en {FOCO} vale "
    f"{num(fila_caso['un_punto_descuento_clp'] / 1e6, 2)} MM CLP."
)

# ---------------------------------------------------------------- 5. tabla de detalle
st.subheader("Detalle por mercado")
detalle = sel.assign(dif=sel["margen_por_litro"] - sel["mediana_margen_por_litro"]).sort_values(
    "margen_por_litro", ascending=False
)
detalle = pd.concat([detalle[detalle["pais"] != TOTAL], detalle[detalle["pais"] == TOTAL]])
tabla = pd.DataFrame(
    {
        "Mercado": detalle["pais"],
        "Litros 1.er sem.": detalle["litros_s1"].map(lambda v: num(v, 0)),
        "Litros 2.º sem.": detalle["litros_s2"].map(lambda v: num(v, 0)),
        "Crecimiento (%)": detalle["crecimiento_litros_pct"].map(lambda v: num(v, 2)),
        f"Margen ({unidad})": detalle["margen_por_litro"].map(lambda v: num(v, dec)),
        f"Vs. mediana ({unidad})": detalle["dif"].map(lambda v: num(v, dec)),
        "Cobertura (%)": detalle["cobertura_litros_pct"].map(lambda v: num(v, 1)),
        "Clase": detalle["clase_margen"].fillna("—"),
        "Estado": detalle["estado_decision"].fillna("—"),
    }
)
st.dataframe(tabla, hide_index=True, width="stretch", height=(len(tabla) + 1) * 35 + 3)
exportar = detalle[
    ["pais", "litros_s1", "litros_s2", "crecimiento_litros_pct", "cajas_s1", "cajas_s2", "margen_por_litro",
     "margen_por_caja", "mediana_margen_por_litro", "dif", "cobertura_litros_pct", "clase_margen", "estado_decision"]
].assign(criterio=ETIQUETA_CRITERIO[criterio], moneda=moneda, fecha_dolar=fecha, base=base)
st.download_button(
    "Descargar detalle para Excel (CSV)",
    # Separador ; y coma decimal para que Excel en español lo abra en columnas.
    exportar.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
    file_name=f"margen_por_mercado_{criterio}_{moneda}_{fecha}_{base}.csv",
    mime="text/csv",
)

# ---------------------------------------------------------------- 6. pie
litros_caja = total["litros_totales"] / total["cajas_totales"]
st.divider()
st.caption(
    f"**Fuente:** cadena vina-vallehondo-bi (ERP SQLite, costos CSV, embarques JSON y dólar observado de mindicador.cl), "
    f"archivo `data/published/margen_por_mercado.csv` · **Última corrida:** {ultima_corrida:%d-%m-%Y %H:%M} · "
    f"**Dueño del dato:** {DUENO_DATO} · **Definición certificada:** {CERTIFICACION} · "
    f"**Litros por caja:** {num(litros_caja, 1)} L (12 × 750 ml y 6 × 1,5 L) · "
    f"**Definición vigente:** {ETIQUETA_CRITERIO[criterio]}, {moneda}, dólar de {fecha}, "
    f"{'mismas ventas' if base == 'comparable' else 'todas las ventas'}."
)

if st.button("Volver a correr la cadena", help="Ejecuta el pipeline y recarga las cifras con la nueva corrida."):
    with st.spinner("Corriendo la cadena…"):
        resultado = correr_cadena()
    if resultado.returncode == 0:
        st.cache_data.clear()
        st.rerun()
    st.error("La cadena falló; se siguen mostrando las cifras de la corrida anterior.")
    st.code(resultado.stderr[-3000:] or resultado.stdout[-3000:])
