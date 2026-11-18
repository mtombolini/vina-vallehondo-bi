"""Prototipo E2 · Viña Vallehondo · Grupo 7.

Una pantalla, una pregunta. Lee solo lo que publica la cadena en
data/published/, así que se actualiza al volver a correr el pipeline:

    python -m vina_vallehondo_bi.etl.pipeline
    streamlit run app.py

Si data/published/ está vacía (por ejemplo, en Streamlit Community Cloud,
donde las capas no se versionan), la app corre la cadena al iniciar.

Rediseño después de la prueba de uso (16-11-2026) y de la respuesta de la
contraparte (11-11-2026): respuesta escrita arriba, un solo gráfico con
margen, crecimiento y qué hacer por mercado, serie mensual 2025, brecha de
Brasil descompuesta, comparación factura/embarque explícita, detalle por
cliente, producto y factura, descarga a Excel y glosario.
"""

from __future__ import annotations

import io
import json
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
TABLAS = (
    "margen_por_mercado.csv",
    "caso_descuento_brasil.csv",
    "escenarios_mezcla.csv",
    "serie_mensual_mercado.csv",
    "fact_venta.parquet",
)
FOCO = "Brasil"  # mercado del caso de descuento (caso_descuento_brasil.csv)
TOTAL = "Total exportación"

# Textos del pie que no salen de los datos. El dueño es el mismo cargo de B.7 y E.7 del informe.
DUENO_DATO = "Jefatura de Control de Gestión, Gerencia de Finanzas"
CERTIFICACION = "Finanzas confirmó el dólar observado de factura como referencia contable (11-nov-2026)"

ETIQUETA_CRITERIO = {"reglas_finanzas": "Finanzas", "e1": "Nuestra (E1)"}
ESTADO_CORTO = {
    "Recomendación de revisión": "Revisar descuento · recomendación",
    "Hipótesis de mezcla": "Validar más Reserva · hipótesis",
    "Seguimiento": "Seguimiento",
}
AZUL, GRIS, GRIS_OSCURO = "#1f4e79", "#b8c2cc", "#4a5560"


# ---------------------------------------------------------------- utilidades
def num(x: float, dec: int = 2) -> str:
    """Número con formato chileno: 1.718,61."""
    texto = f"{x:,.{dec}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def signo(x: float, dec: int = 1) -> str:
    return f"{'+' if x >= 0 else '−'}{num(abs(x), dec)}"


@st.cache_data(show_spinner=False)
def leer(nombre: str, marca: float) -> pd.DataFrame:
    # `marca` es la fecha de modificación del archivo: si la cadena vuelve a
    # correr, cambia y se invalida la caché.
    ruta = PUBLISHED / nombre
    return pd.read_parquet(ruta) if ruta.suffix == ".parquet" else pd.read_csv(ruta)


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


def a_excel(hojas: dict[str, pd.DataFrame]) -> tuple[bytes, str, str]:
    """Devuelve un .xlsx (o un CSV para Excel si falta openpyxl)."""
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as libro:
            for nombre, tabla in hojas.items():
                tabla.to_excel(libro, sheet_name=nombre[:31], index=False)
        return (buffer.getvalue(), "xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except ImportError:
        primera = next(iter(hojas.values()))
        return (primera.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"), "csv", "text/csv")


def tarjeta(col, titulo: str, valor: str, detalle: str, destacada: bool = False) -> None:
    """Tarjeta de cifra con texto que se ajusta en vez de cortarse."""
    clase = "tarjeta destacada" if destacada else "tarjeta"
    col.markdown(
        f'<div class="{clase}"><div class="t-titulo">{titulo}</div>'
        f'<div class="t-valor">{valor}</div><div class="t-detalle">{detalle}</div></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- datos
st.set_page_config(page_title="Viña Vallehondo · Margen por mercado", layout="wide")
st.markdown(
    """
    <style>
      .tarjeta {border: 1px solid #d5dbe1; border-radius: 8px; padding: 12px 14px; height: 100%;}
      .tarjeta.destacada {border: 2px solid #1f4e79; background: #f3f7fb;}
      .t-titulo {font-size: 0.9rem; color: #333; font-weight: 600; line-height: 1.25;}
      .t-valor {font-size: 1.9rem; font-weight: 700; color: #111; margin: 4px 0 2px 0; line-height: 1.15;}
      .tarjeta.destacada .t-valor {color: #1f4e79; font-size: 2.2rem;}
      .t-detalle {font-size: 0.85rem; color: #444; line-height: 1.35;}
      .respuesta {border-left: 6px solid #1f4e79; background: #f3f7fb; padding: 12px 16px;
                  border-radius: 4px; font-size: 1.05rem; line-height: 1.5; color: #111;}
    </style>
    """,
    unsafe_allow_html=True,
)

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
serie = cargar("serie_mensual_mercado.csv")
hechos = cargar("fact_venta.parquet")
dim_mercado = cargar("dim_mercado.parquet")
dim_cliente = cargar("dim_cliente.parquet")
dim_producto = cargar("dim_producto.parquet")

ultima_corrida = datetime.fromtimestamp(
    (PUBLISHED / "margen_por_mercado.csv").stat().st_mtime, ZoneInfo("America/Santiago")
)
# La cadena deja en corrida.json qué tipo de cambio usó y cómo salieron las pruebas.
ruta_corrida = PUBLISHED / "corrida.json"
corrida = json.loads(ruta_corrida.read_text(encoding="utf-8")) if ruta_corrida.exists() else None
dolar_respaldo = False
if corrida:
    ultima_corrida = datetime.fromisoformat(corrida["fecha_corrida"]).astimezone(ZoneInfo("America/Santiago"))
    dolar_hasta = datetime.fromisoformat(corrida["tipo_cambio"]["ultimo_dato"])
    anios_respaldo = ", ".join(map(str, corrida["tipo_cambio"]["anios_respaldo"]))
    dolar_respaldo = corrida["tipo_cambio"]["fuente"] == "respaldo"

# ---------------------------------------------------------------- 1. encabezado
st.title("¿Qué mercados de exportación crecieron en volumen y cuáles crecieron dejando poco margen?")
st.markdown(
    "**Para qué sirve:** decidir si se renueva, se ajusta o se condiciona el descuento especial de "
    f"{FOCO}, y en qué mercados poner foco. **Cómo se usa:** la respuesta está escrita en el recuadro "
    "azul; no hay que ingresar datos. Los controles solo cambian la moneda, el tipo de cambio, la "
    "definición de margen o el mercado que se destaca."
)
st.caption(
    "Exportación 2025 · 2.º semestre vs. 1.er semestre, por fecha de factura · "
    "Para: gerente comercial y encargados de mercado (mensual, tras el cierre); gerencia general y "
    "Finanzas (trimestral y antes de cada renovación) · "
    f"**Datos al {ultima_corrida:%d-%m-%Y %H:%M}** (última corrida de la cadena)"
)
if corrida and dolar_respaldo:
    st.warning(
        f"**Tipo de cambio de respaldo.** La API del dólar observado no respondió para {anios_respaldo} "
        "en la última corrida y se usó la copia guardada en el repositorio. "
        f"Último dato disponible: {dolar_hasta:%d-%m-%Y}.",
        icon="⚠️",
    )

# ---------------------------------------------------------------- 2. controles
c1, c2, c3, c4 = st.columns([0.8, 1.6, 1.1, 1])
moneda = c1.radio("Moneda", ["CLP", "USD"], horizontal=True,
                  help="Comercial mira dólares y Finanzas pesos; el tipo de cambio es el mismo en ambos.")
vista = c2.radio(
    "Tipo de cambio",
    ["factura", "comparar"],
    format_func={"factura": "Fecha de factura (oficial)",
                 "comparar": "Comparar con fecha de embarque"}.get,
    horizontal=True,
    help="La fecha de embarque confiable existe solo para parte de las ventas. Al comparar, factura y "
         "embarque se calculan sobre esas mismas ventas, para que solo cambie el dólar.",
)
criterio = c3.radio("Definición de margen", ["reglas_finanzas", "e1"],
                    format_func=ETIQUETA_CRITERIO.get, horizontal=True,
                    help="Finanzas: monto facturado y mermas sin reversar el costo (vigente). "
                         "Nuestra (E1): definición de la Entrega 1, como alternativa.")
paises = sorted(p for p in margen["pais"].unique() if p != TOTAL)
destacado = c4.selectbox("Mercado a destacar", paises, index=paises.index(FOCO))

comparar = vista == "comparar"
fecha, base = ("embarque", "comparable") if comparar else ("factura", "disponible")


def seleccion(fecha_: str, base_: str) -> pd.DataFrame:
    return margen[(margen["criterio"] == criterio) & (margen["moneda"] == moneda)
                  & (margen["fecha_conversion"] == fecha_) & (margen["base"] == base_)]


sel = seleccion(fecha, base)
if sel.empty:
    st.warning("La cadena no publicó esta combinación de filtros.")
    st.stop()
mercados = sel[sel["pais"] != TOTAL].copy()
total = sel[sel["pais"] == TOTAL].iloc[0]
foco = sel[sel["pais"] == destacado].iloc[0]
mediana = float(foco["mediana_margen_por_litro"])
unidad = f"{moneda}/L"
dec = 2 if moneda == "CLP" else 4
ultimo = mercados.loc[mercados["margen_por_litro"].idxmin()]
mas_crece = mercados.loc[mercados["crecimiento_litros_pct"].idxmax()]
crecieron = mercados[mercados["crecimiento_litros_pct"] > 0].sort_values("crecimiento_litros_pct", ascending=False)
if comparar:
    sel_fact = seleccion("factura", "comparable")
    total_fact = sel_fact[sel_fact["pais"] == TOTAL].iloc[0]
    foco_fact = sel_fact[sel_fact["pais"] == destacado].iloc[0]
    ultimo_fact = sel_fact[sel_fact["pais"] != TOTAL].set_index("pais")["margen_por_litro"].idxmin()

# ---------------------------------------------------------------- 3. respuesta
recom = mercados[mercados["estado_decision"] == "Recomendación de revisión"]["pais"].tolist()
hipo = mercados[mercados["estado_decision"] == "Hipótesis de mezcla"]
n_seguimiento = int((mercados["estado_decision"] == "Seguimiento").sum())
if comparar:
    cambio = total["margen_por_litro"] - total_fact["margen_por_litro"]
    texto = (
        f"<b>Con el dólar de embarque, {ultimo['pais']} "
        f"{'sigue siendo' if ultimo['pais'] == ultimo_fact else 'pasa a ser'} el mercado que menos margen deja</b> "
        f"({num(ultimo['margen_por_litro'], dec)} {unidad}). Sobre las mismas ventas "
        f"({num(total['cobertura_litros_pct'], 1)} % de los litros de exportación, las que tienen fecha de "
        f"embarque confiable), el margen de toda la exportación pasa de {num(total_fact['margen_por_litro'], dec)} "
        f"con dólar de factura a {num(total['margen_por_litro'], dec)} {unidad} con dólar de embarque "
        f"({signo(cambio, dec)} {unidad}, {signo(cambio / total_fact['margen_por_litro'] * 100, 2)} %). "
        "La cifra oficial sigue siendo la de factura."
    )
else:
    otros = ", ".join(f"{r.pais} ({signo(r.crecimiento_litros_pct)} %)" for r in crecieron.itertuples()
                      if r.pais != mas_crece["pais"])
    mismo = ultimo["pais"] == mas_crece["pais"]
    texto = (
        f"<b>{ultimo['pais']} es el mercado que menos margen deja"
        f"{' y, a la vez, el que más creció' if mismo else ''}</b>: "
        f"{num(ultimo['margen_por_litro'], dec)} {unidad}, {num(mediana - ultimo['margen_por_litro'], dec)} "
        f"bajo un mercado típico (la mediana de los 10 mercados, {num(mediana, dec)}), "
        f"{'con ' + signo(ultimo['crecimiento_litros_pct']) + ' % en litros' if mismo else ''}. "
        f"También crecieron {otros}. "
        + (f"<b>Qué hacer:</b> revisar el descuento de {', '.join(recom)} antes de renovarlo (recomendación). "
           if recom else "")
        + "".join(
            f"{r.pais} creció {signo(r.crecimiento_litros_pct)} % con margen bajo la mediana y "
            f"{num(r.margen_por_litro, dec)} {unidad}: vender más Reserva es una hipótesis por validar. "
            for r in hipo.itertuples())
        + f"Los otros {n_seguimiento} mercados quedan en seguimiento."
    )
st.markdown(f'<div class="respuesta">{texto}</div>', unsafe_allow_html=True)
st.write("")

# ---------------------------------------------------------------- 4. cifras
fila_caso = caso[caso["criterio"] == criterio].iloc[0]
k1, k2, k3, k4 = st.columns([1.35, 1, 1, 1.1])
if comparar:
    dif = foco["margen_por_litro"] - foco_fact["margen_por_litro"]
    tarjeta(k1, f"Margen por litro de {destacado} · dólar de embarque",
            f"{num(foco['margen_por_litro'], dec)} {unidad}",
            f"Con dólar de factura, mismas ventas: {num(foco_fact['margen_por_litro'], dec)} "
            f"({signo(dif, dec)}). Mercado típico (mediana): {num(mediana, dec)}.", destacada=True)
else:
    tarjeta(k1, f"Margen por litro de {destacado}",
            f"{num(foco['margen_por_litro'], dec)} {unidad}",
            f"{signo(foco['margen_por_litro'] - mediana, dec)} {unidad} frente a un mercado típico "
            f"(mediana de los 10 mercados: {num(mediana, dec)})", destacada=True)
tarjeta(k2, f"Crecimiento de {destacado} en litros",
        f"{signo(foco['crecimiento_litros_pct'], 2)} %",
        f"{num(foco['litros_s1'], 0)} L en el 1.er sem. → {num(foco['litros_s2'], 0)} L en el 2.º · "
        f"{num(foco['litros_totales'] / foco['cajas_totales'], 0)} L por caja")
tarjeta(k3, "Litros con margen calculado (cobertura)",
        f"{num(foco['cobertura_litros_pct'], 1)} %",
        f"De {destacado}. Toda la exportación: {num(total['cobertura_litros_pct'], 1)} %"
        + (" (ventas con fecha de embarque)" if comparar else ""))
tarjeta(k4, f"Costo del descuento extra de {FOCO}",
        f"{num(fila_caso['escenario_descuento_comercial_clp'] / 1e6, 2)} MM CLP",
        f"Margen al año si su descuento ({num(fila_caso['descuento_comercial_brasil_pct'], 2)} %) fuera el "
        f"del resto ({num(fila_caso['descuento_comercial_resto_pct'], 2)} %). Cada punto de descuento: "
        f"{num(fila_caso['un_punto_descuento_clp'] / 1e6, 2)} MM CLP")
st.write("")

# ---------------------------------------------------------------- 5. gráfico principal
orden = mercados.sort_values("margen_por_litro", ascending=False)["pais"].tolist()
mercados["es_destacado"] = mercados["pais"].eq(destacado)
mercados["etq_margen"] = mercados["margen_por_litro"].map(lambda v: num(v, dec))
mercados["etq_crec"] = mercados["crecimiento_litros_pct"].map(lambda v: f"{signo(v)} %")
mercados["que_hacer"] = mercados["estado_decision"].map(ESTADO_CORTO)
mismo_titulo = ultimo["pais"] == mas_crece["pais"]
st.subheader(
    f"{ultimo['pais']} es el que más creció y el que menos margen deja por litro" if mismo_titulo and not comparar
    else f"{ultimo['pais']} deja el menor margen por litro de los {len(mercados)} mercados"
)
st.caption(
    "Cada fila es un mercado: a la izquierda su margen por litro (la línea punteada es la mediana, el "
    "mercado típico), al centro cuánto cambiaron sus litros del 1.er al 2.º semestre y a la derecha qué "
    "hacer con él." + (" Vista: dólar de embarque, mismas ventas." if comparar else "")
)
alto = 36 * len(mercados)
y = alt.Y("pais:N", sort=orden, title=None, scale=alt.Scale(paddingInner=0.2))
color = alt.condition(alt.datum.es_destacado, alt.value(AZUL), alt.value(GRIS))
x_max = float(mercados["margen_por_litro"].max())
x_margen = alt.X("margen_por_litro:Q", title=f"Margen bruto por litro ({unidad})",
                 scale=alt.Scale(domain=[0, x_max * 1.08], nice=False),
                 axis=alt.Axis(labelExpr="replace(datum.label, ',', '.')", tickCount=5))
barras = alt.Chart(mercados).mark_bar().encode(
    y=y, x=x_margen, color=color,
    tooltip=[alt.Tooltip("pais:N", title="Mercado"), alt.Tooltip("etq_margen:N", title=f"Margen ({unidad})"),
             alt.Tooltip("etq_crec:N", title="Crecimiento litros")],
)
etq = alt.Chart(mercados).mark_text(align="left", dx=8, fontWeight="bold").encode(
    y=y, x=alt.value(0), text="etq_margen:N",
    color=alt.condition(alt.datum.es_destacado, alt.value("white"), alt.value("#111")),
)
linea = alt.Chart(pd.DataFrame({"m": [mediana]})).mark_rule(strokeDash=[5, 4], color="#111").encode(x="m:Q")
etq_linea = (alt.Chart(pd.DataFrame({"m": [mediana], "t": [f"Mediana {num(mediana, dec)}"]}))
             .mark_text(align="center", dy=-8, color="#111", fontWeight="bold")
             .encode(x="m:Q", y=alt.value(0), text="t:N"))
panel_margen = (barras + etq + linea + etq_linea).properties(
    width=430, height=alto, title="Margen por litro")

c_max = float(mercados["crecimiento_litros_pct"].abs().max()) * 1.45
x_crec = alt.X("crecimiento_litros_pct:Q", title="Variación de litros, 2.º vs. 1.er semestre (%)",
               scale=alt.Scale(domain=[-c_max, c_max], nice=False),
               axis=alt.Axis(labelExpr="replace(datum.label, '.', ',')", tickCount=5))
y_sin = alt.Y("pais:N", sort=orden, axis=None, scale=alt.Scale(paddingInner=0.2))
crec = alt.Chart(mercados).mark_bar().encode(y=y_sin, x=x_crec, color=color)
cero = alt.Chart(pd.DataFrame({"c": [0]})).mark_rule(color="#111").encode(x="c:Q")
etq_pos = (alt.Chart(mercados).transform_filter(alt.datum.crecimiento_litros_pct >= 0)
           .mark_text(fontWeight="bold", color="#111", align="left", dx=4)
           .encode(y=y_sin, x="crecimiento_litros_pct:Q", text="etq_crec:N"))
etq_neg = (alt.Chart(mercados).transform_filter(alt.datum.crecimiento_litros_pct < 0)
           .mark_text(fontWeight="bold", color="#111", align="right", dx=-4)
           .encode(y=y_sin, x="crecimiento_litros_pct:Q", text="etq_crec:N"))
etq_crec = etq_pos + etq_neg
panel_crec = (crec + cero + etq_crec).properties(width=260, height=alto, title="Crecimiento en litros")

que_base = alt.Chart(mercados).encode(y=y_sin, x=alt.value(0), text="que_hacer:N")
panel_que = (
    que_base.transform_filter(alt.datum.estado_decision == "Seguimiento")
    .mark_text(align="left", fontSize=13, color=GRIS_OSCURO)
    + que_base.transform_filter(alt.datum.estado_decision != "Seguimiento")
    .mark_text(align="left", fontSize=13, color=AZUL, fontWeight="bold")
).properties(width=230, height=alto, title="Qué hacer")
st.altair_chart(
    alt.hconcat(panel_margen, panel_crec, panel_que, spacing=18)
    .configure_view(stroke=None)
    .configure_title(fontSize=13, anchor="start", color="#111")
    .configure_axis(labelFontSize=12, titleFontSize=11, labelColor="#111", titleColor="#333"),
)

# ---------------------------------------------------------------- 6. tiempo y decisión
izq, der = st.columns([1.15, 1])

# Serie mensual: CLP, dólar de factura y reglas de Finanzas (lo que publica la cadena).
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
serie = serie.assign(mes=pd.to_datetime(serie["mes_factura"] + "-01"))
serie = serie.assign(mes_txt=serie["mes"].dt.month.map(lambda m: MESES[m - 1]))
propio = serie[serie["pais"] == destacado][["mes", "mes_txt", "litros", "margen_clp_litro"]].assign(serie=destacado)
resto = (serie[serie["pais"] != destacado].groupby(["mes", "mes_txt"], as_index=False)[["litros", "margen_total"]].sum())
resto = resto.assign(margen_clp_litro=resto["margen_total"] / resto["litros"],
                     serie="Resto de la exportación")[["mes", "mes_txt", "litros", "margen_clp_litro", "serie"]]
meses_bajo = int((propio.set_index("mes")["margen_clp_litro"]
                  < resto.set_index("mes")["margen_clp_litro"]).sum())
s1 = propio[propio["mes"].dt.month <= 6]["litros"].sum()
s2 = propio[propio["mes"].dt.month > 6]["litros"].sum()
with izq:
    st.subheader(
        f"{destacado} vendió {'más' if s2 > s1 else 'menos'} en el 2.º semestre"
        + (f" y su margen por litro quedó bajo el resto en {meses_bajo} de 12 meses" if meses_bajo else "")
    )
    st.caption(
        "Mes a mes en 2025, en CLP con dólar de factura y definición de Finanzas. El descuento de "
        f"{FOCO} estuvo vigente todo 2025, así que no hay un «antes del descuento» en los datos "
        "(faltan las ventas de 2024)."
    )
    ambas = pd.concat([propio, resto])
    x_mes = alt.X("mes_txt:O", title=None, sort=MESES, axis=alt.Axis(labelAngle=0))
    colores = alt.Scale(domain=[destacado, "Resto de la exportación"], range=[AZUL, GRIS_OSCURO])
    lineas = (alt.Chart(ambas).mark_line(point=True).encode(
        x=x_mes, y=alt.Y("margen_clp_litro:Q", title="Margen (CLP/L)", scale=alt.Scale(zero=True),
                         axis=alt.Axis(labelExpr="replace(datum.label, ',', '.')")),
        color=alt.Color("serie:N", scale=colores, legend=alt.Legend(orient="top", title=None)),
        strokeDash=alt.StrokeDash("serie:N", scale=alt.Scale(domain=[destacado, "Resto de la exportación"],
                                                             range=[[1, 0], [5, 3]]), legend=None),
        tooltip=[alt.Tooltip("serie:N"), alt.Tooltip("mes_txt:O", title="Mes"),
                 alt.Tooltip("margen_clp_litro:Q", format=",.0f")],
    ).properties(height=170, title="Margen por litro"))
    volumen = (alt.Chart(propio).mark_bar(color=AZUL, size=22).encode(
        x=x_mes, y=alt.Y("litros:Q", title=f"Litros de {destacado}",
                         axis=alt.Axis(labelExpr="replace(datum.label, ',', '.')")),
        tooltip=[alt.Tooltip("mes_txt:O", title="Mes"), alt.Tooltip("litros:Q", format=",.0f")],
    ).properties(height=120, title=f"Volumen de {destacado}"))
    st.altair_chart(alt.vconcat(lineas, volumen, spacing=8).configure_view(stroke=None)
                    .configure_title(fontSize=13, anchor="start", color="#111"), width="stretch")

with der:
    brecha = fila_caso["brecha_mediana_clp"] / 1e6
    por_desc = fila_caso["escenario_descuento_comercial_clp"] / 1e6
    st.subheader(f"El descuento explica {num(por_desc / brecha * 100, 1)} % de lo que {FOCO} deja de ganar")
    st.caption(
        f"Margen que {FOCO} deja de ganar al año frente a un mercado típico, en MM CLP (CLP, dólar de "
        "factura). El costo del descuento supone volumen fijo."
    )
    partes = pd.DataFrame({
        "parte": [f"Descuento extra ({num(fila_caso['descuento_comercial_brasil_pct'], 1)} % vs. "
                  f"{num(fila_caso['descuento_comercial_resto_pct'], 1)} %)", "Otros factores (mezcla, precio, costo)"],
        "valor": [por_desc, brecha - por_desc], "orden": [0, 1],
    })
    partes["etq"] = partes["valor"].map(lambda v: f"{num(v, 2)} MM")
    barra = alt.Chart(partes).mark_bar(height=38).encode(
        x=alt.X("sum(valor):Q", title=f"Brecha total frente a un mercado típico: {num(brecha, 2)} MM CLP",
                axis=alt.Axis(labels=False, ticks=False, grid=False)),
        color=alt.Color("parte:N", scale=alt.Scale(domain=partes["parte"].tolist(), range=[AZUL, GRIS]),
                        legend=alt.Legend(orient="top", title=None, labelLimit=400, direction="vertical")),
        order="orden:Q",
    )
    etq_barra = alt.Chart(partes).mark_text(color="#111", fontWeight="bold", dx=-6, dy=-28, align="right").encode(
        x=alt.X("sum(valor):Q", stack="zero"), text="etq:N", order="orden:Q",
        detail="parte:N",
    )
    st.altair_chart((barra + etq_barra).properties(height=120).configure_view(stroke=None)
                    .configure_legend(labelFontSize=12, labelColor="#111"), width="stretch")
    st.markdown(
        f"- **Punto de equilibrio:** si el descuento de {FOCO} bajara al del resto, su margen total se "
        f"mantiene mientras el volumen no caiga más de **{num(fila_caso['perdida_volumen_equilibrio_comercial_pct'], 2)} %**.\n"
        f"- **Un punto de descuento** en {FOCO} vale **{num(fila_caso['un_punto_descuento_clp'] / 1e6, 2)} MM CLP** "
        "de margen al año.\n"
        "- **Un punto de mezcla** (pasar el 1 % de los litros de Varietal a un nivel superior):\n"
        + "".join(
            f"  - {p}: Reserva **+{num(g.set_index('destino').loc['Reserva', 'variacion_margen_clp'] / 1e6, 1)} MM**, "
            f"Gran Reserva **+{num(g.set_index('destino').loc['Gran Reserva', 'variacion_margen_clp'] / 1e6, 1)} MM CLP**\n"
            for p, g in mezcla.groupby("pais"))
    )
    st.info(
        "**Falta para decidir:** el margen es bruto del producto (ingreso facturado menos costo del vino). "
        "No descuenta flete, comisiones ni notas de crédito, que no vienen en los datos y que Finanzas pidió "
        f"para la renovación. Por eso {FOCO} es una recomendación de *revisar*, sujeta a esa conciliación.",
        icon="ℹ️",
    )


# ---------------------------------------------------------------- 7. detalle
@st.cache_data(show_spinner=False)
def ventas_exportacion(moneda_: str, fecha_: str, marca: float) -> pd.DataFrame:
    """Margen por venta con la definición de Finanzas, en la moneda y fecha elegidas."""
    v = hechos.merge(dim_mercado[["mercado_id", "pais", "canal"]], on="mercado_id")
    v = v[v["canal"] == "Exportación"].copy()
    ingreso_clp = v["ingreso_neto_clp_fecha_venta" if fecha_ == "factura" else "ingreso_neto_clp_fecha_embarque"]
    if fecha_ == "embarque":
        v, ingreso_clp = v[ingreso_clp.notna()], ingreso_clp[ingreso_clp.notna()]
    if moneda_ == "CLP":
        v["ingreso"], v["costo"] = ingreso_clp, v["costo_total_clp"]
    else:
        tipo_cambio = ingreso_clp / v["ingreso_neto_moneda_original"]
        v["ingreso"], v["costo"] = v["ingreso_neto_moneda_original"], v["costo_total_clp"] / tipo_cambio
    v["margen"] = v["ingreso"] - v["costo"]
    v = v.merge(dim_cliente[["cliente_id", "nombre", "tipo"]].rename(columns={"nombre": "cliente", "tipo": "tipo_cliente"}),
                on="cliente_id", how="left")
    v = v.merge(dim_producto[["producto_anada_key", "producto", "anada", "tier"]], on="producto_anada_key", how="left")
    return v


st.subheader("Detalle para revisar cualquier cifra")
ventas = ventas_exportacion(moneda, "embarque" if comparar else "factura",
                            (PUBLISHED / "fact_venta.parquet").stat().st_mtime)
ventas_mercado = ventas[ventas["pais"] == destacado]
cuadra = abs(ventas_mercado["margen"].sum() / ventas_mercado["litros"].sum() - foco["margen_por_litro"]) < 1e-6 \
    if criterio == "reglas_finanzas" else None
st.caption(
    f"Baja de mercado a cliente, producto o factura para entender un número extraño, y descarga a Excel. "
    f"El detalle por venta usa la definición de Finanzas ({moneda}, dólar de "
    f"{'embarque, mismas ventas' if comparar else 'factura'})."
    + (f" ✓ La suma de las ventas de {destacado} da {num(foco['margen_por_litro'], dec)} {unidad}, la misma "
       "cifra de arriba." if cuadra else "")
    + (" Con la definición «Nuestra (E1)» el detalle sigue mostrando la de Finanzas." if criterio == "e1" else "")
)


def resumen(grupo: list[str], datos: pd.DataFrame) -> pd.DataFrame:
    r = datos.groupby(grupo, as_index=False)[["cajas", "litros", "ingreso", "costo", "margen"]].sum()
    r["margen_por_litro"] = r["margen"] / r["litros"]
    return r.sort_values("margen_por_litro")


def mostrar(tabla: pd.DataFrame, nombres: dict[str, str]) -> pd.DataFrame:
    """Muestra la tabla con formato chileno y devuelve la versión numérica para Excel."""
    t = tabla[list(nombres)].rename(columns=nombres)
    vista_t = t.copy()
    for col in t.columns:
        if col in ("Venta", "Añada"):
            vista_t[col] = t[col].astype("string")
        elif pd.api.types.is_datetime64_any_dtype(t[col]):
            vista_t[col] = t[col].dt.strftime("%d-%m-%Y")
        elif pd.api.types.is_numeric_dtype(t[col]):
            d = dec if "por litro" in col or "mediana" in col else (
                2 if "%" in col else (0 if moneda == "CLP" or col in ("Cajas", "Litros") or "Litros" in col else 2))
            vista_t[col] = t[col].map(lambda v: "" if pd.isna(v) else num(v, d))
        else:
            vista_t[col] = t[col].fillna("—")
    st.dataframe(vista_t, hide_index=True, width="stretch", height=min(36 * (len(t) + 1) + 3, 420))
    return t


cols_valor = {"cajas": "Cajas", "litros": "Litros", "ingreso": f"Ingreso neto ({moneda})",
              "costo": f"Costo ({moneda})", "margen": f"Margen ({moneda})",
              "margen_por_litro": f"Margen por litro ({unidad})"}
t_merc, t_cli, t_prod, t_fac = st.tabs(["Por mercado", f"Por cliente · {destacado}",
                                       f"Por producto · {destacado}", f"Por factura · {destacado}"])
with t_merc:
    detalle = sel.assign(vs_mediana=sel["margen_por_litro"] - sel["mediana_margen_por_litro"])
    detalle = pd.concat([detalle[detalle["pais"] != TOTAL].sort_values("margen_por_litro", ascending=False),
                         detalle[detalle["pais"] == TOTAL]])
    hoja_mercado = mostrar(detalle, {
        "pais": "Mercado", "litros_s1": "Litros 1.er sem.", "litros_s2": "Litros 2.º sem.",
        "crecimiento_litros_pct": "Crecimiento (%)", "margen_por_litro": f"Margen por litro ({unidad})",
        "vs_mediana": f"Vs. mediana ({unidad})", "descuento_comercial_pct": "Descuento (%)",
        "cobertura_litros_pct": "Cobertura (%)", "estado_decision": "Qué hacer"})
with t_cli:
    hoja_cliente = mostrar(resumen(["cliente", "tipo_cliente"], ventas_mercado),
                           {"cliente": "Cliente", "tipo_cliente": "Tipo", **cols_valor})
with t_prod:
    hoja_producto = mostrar(resumen(["producto", "tier", "anada"], ventas_mercado),
                            {"producto": "Producto", "tier": "Nivel", "anada": "Añada", **cols_valor})
with t_fac:
    hoja_factura = mostrar(
        ventas_mercado.assign(margen_por_litro=ventas_mercado["margen"] / ventas_mercado["litros"])
        .sort_values("fecha"),
        {"venta_id": "Venta", "fecha": "Fecha factura", "cliente": "Cliente", "producto": "Producto",
         "anada": "Añada", **cols_valor})
contenido, extension, tipo_mime = a_excel({
    "Por mercado": hoja_mercado, f"Clientes {destacado}": hoja_cliente,
    f"Productos {destacado}": hoja_producto, f"Facturas {destacado}": hoja_factura,
})
st.download_button(
    "Descargar a Excel (mercados, clientes, productos y facturas)", contenido,
    file_name=f"vallehondo_margen_{destacado}_{moneda}_{'embarque' if comparar else 'factura'}.{extension}",
    mime=tipo_mime,
)

# ---------------------------------------------------------------- 8. glosario
with st.expander("Cómo leer esta pantalla (vocabulario)"):
    st.markdown(
        "- **Margen bruto por litro:** ingreso neto facturado menos el costo del vino, dividido por los "
        "litros vendidos. Es antes de flete, seguro, comisiones y notas de crédito.\n"
        "- **Mercado típico (mediana):** el valor del medio cuando se ordenan los 10 mercados por margen; "
        "cinco quedan sobre y cinco bajo. No es el promedio, para que un mercado extremo no la mueva.\n"
        "- **Crecimiento:** variación de litros entre el 2.º y el 1.er semestre de 2025, por fecha de factura.\n"
        "- **Cobertura:** porcentaje de los litros que tienen margen calculado con los controles elegidos.\n"
        "- **Fecha de factura vs. embarque:** día cuyo dólar se usa para pasar a pesos. La de factura es la "
        "oficial (cuadra con contabilidad). La de embarque solo existe para parte de las ventas; por eso, al "
        "comparar, las dos se calculan sobre esas mismas ventas y el total cambia.\n"
        "- **Recomendación vs. hipótesis:** recomendación es lo que los datos ya permiten proponer (revisar "
        "el descuento de Brasil); hipótesis es una idea que hay que validar antes de actuar (que China compre "
        "más Reserva).\n"
        "- **Punto de descuento / punto de mezcla:** cuánto margen al año cambia al mover 1 punto el "
        "descuento, o al pasar el 1 % de los litros de Varietal a un nivel superior."
    )

# ---------------------------------------------------------------- 9. pie
litros_caja = total["litros_totales"] / total["cajas_totales"]
st.divider()
st.caption(
    f"**Fuente:** cadena vina-vallehondo-bi (ERP SQLite, costos CSV, embarques JSON y dólar observado de "
    f"mindicador.cl), tablas de `data/published/` · **Última corrida:** {ultima_corrida:%d-%m-%Y %H:%M} · "
    f"**Dueño del dato:** {DUENO_DATO} · **Definición certificada:** {CERTIFICACION} · "
    f"**Litros por caja:** {num(litros_caja, 1)} L (12 × 750 ml y 6 × 1,5 L) · "
    + (
        f"**Tipo de cambio:** dólar observado de la API"
        f"{f' (copia de respaldo para {anios_respaldo})' if dolar_respaldo else ''}, "
        f"último dato {dolar_hasta:%d-%m-%Y} · **Pruebas de calidad:** {corrida['pruebas']['en_verde']} de "
        f"{corrida['pruebas']['total']} en verde ({corrida['pruebas']['avisos']} avisos) · "
        if corrida else ""
    )
    + f"**Vista:** {ETIQUETA_CRITERIO[criterio]}, {moneda}, dólar de "
    f"{'embarque sobre las mismas ventas' if comparar else 'factura, todas las ventas'}."
)

if st.button("Volver a correr la cadena", help="Ejecuta el pipeline y recarga las cifras con la nueva corrida."):
    with st.spinner("Corriendo la cadena…"):
        resultado = correr_cadena()
    if resultado.returncode == 0:
        st.cache_data.clear()
        st.rerun()
    st.error("La cadena falló; se siguen mostrando las cifras de la corrida anterior.")
    st.code(resultado.stderr[-3000:] or resultado.stdout[-3000:])
