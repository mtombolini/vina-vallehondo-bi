"""Pruebas de calidad que corren en cada carga de la cadena.

Cada prueba declara qué verifica y qué pasa si falla. Las que ``bloquean``
impiden publicar: ``data/published`` conserva la corrida anterior y el
prototipo sigue mostrando esas cifras. Las que ``avisan`` se informan y la
carga sigue. El resultado se publica en ``calidad_ultima_corrida.csv``.
"""

from __future__ import annotations

import pandas as pd

from vina_vallehondo_bi.etl.margins import TOTAL
from vina_vallehondo_bi.etl.processed import ANALYSIS_YEAR

BLOCK = "bloquea"
WARN = "avisa"
FX_RANGE_CLP = (500, 1500)
MARGIN_TOLERANCE_CLP = 0.01
SALES_KEY_FIELDS = ["venta_id", "fecha", "mercado_id", "cliente_id", "producto_id", "cajas", "precio_unitario", "monto_neto"]


def _n(value: float) -> str:
    """Entero con separador de miles chileno."""
    return f"{value:,.0f}".replace(",", ".")


def _dec(value: float, places: int = 2) -> str:
    """Decimal con formato chileno: 2.210,64."""
    return f"{value:,.{places}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _check(prueba: str, capa: str, verifica: str, si_falla: str, ok: bool, detalle: str) -> dict:
    return {
        "prueba": prueba,
        "capa": capa,
        "verifica": verifica,
        "si_falla": si_falla,
        "resultado": "ok" if ok else "falla",
        "detalle": detalle,
    }


def source_checks(staging, processed) -> list[dict]:
    sales = staging["stg_ventas"]
    incomplete = int(sales[SALES_KEY_FIELDS].isna().any(axis=1).sum())
    currencies = sales.dropna(subset=["moneda_id"]).groupby("mercado_id")["moneda_id"].nunique()
    mixed = int(currencies.gt(1).sum())
    costs = processed["costos_productos"]
    priced = processed["ventas"].merge(
        costs[["producto_id", "anada", "costo_caja_clp"]], on=["producto_id", "anada"], how="left"
    )
    uncosted = int(priced["costo_caja_clp"].isna().sum())
    lines = staging["stg_embarques"]
    orphan_lines = int((~lines["venta_id"].isin(sales["venta_id"])).sum())
    return [
        _check(
            "Fuente SQLite: ventas", "staging",
            "Cada registro de ventas tiene venta_id, fecha, mercado, cliente, producto, cajas, precio y monto interpretables.",
            BLOCK, len(sales) > 0 and incomplete == 0,
            f"{_n(len(sales))} registros leídos; {_n(incomplete)} con campos clave vacíos.",
        ),
        _check(
            "Fuente SQLite: moneda por mercado", "staging",
            "Cada mercado informa una sola moneda, para completar las ventas sin moneda.",
            BLOCK, mixed == 0,
            f"{_n(len(currencies))} mercados con moneda informada; {_n(mixed)} con más de una.",
        ),
        _check(
            "Fuente CSV de costos", "processed",
            "Cada producto y añada vendido tiene costo por caja, propio o imputado por tier y añada.",
            BLOCK, uncosted == 0,
            f"{_n(len(costs))} producto-añada ({_n(costs['costo_imputado'].sum())} con costo imputado); "
            f"{_n(uncosted)} ventas sin costo.",
        ),
        _check(
            "Fuente JSON de embarques", "staging",
            "Cada línea de embarque apunta a una venta existente.",
            WARN, orphan_lines == 0,
            f"{_n(orphan_lines)} de {_n(len(lines))} líneas apuntan a ventas inexistentes y se excluyen en processed.",
        ),
    ]


def exchange_checks(staging, processed) -> list[dict]:
    rates = staging["stg_tipo_cambio"]
    fallback = rates.attrs.get("anios_respaldo", [])
    last = rates["fecha"].max()
    low, high = FX_RANGE_CLP
    out_of_range = int((~rates["dolar_observado"].between(low, high)).sum())
    origin = (
        f"Copia de respaldo para {', '.join(map(str, fallback))}"
        if fallback else "Descargado de la API"
    )
    last_text = f"último dato publicado el {last:%d-%m-%Y}" if pd.notna(last) else "sin datos"
    return [
        _check(
            "API mindicador.cl: origen", "staging",
            "El dólar observado se descargó de la API y no de la copia de respaldo.",
            WARN, not fallback,
            f"{origin}; {last_text}.",
        ),
        _check(
            "API mindicador.cl: rango", "staging",
            f"Cada valor del dólar observado está entre {_n(low)} y {_n(high)} CLP.",
            BLOCK, len(rates) > 0 and out_of_range == 0,
            f"{_n(len(rates))} días publicados; {_n(out_of_range)} fuera de rango.",
        ),
    ]


def model_checks(processed, model) -> list[dict]:
    fact = model["fact_venta"]
    keys = {
        "fecha": ("dim_tiempo", "fecha"),
        "fecha_embarque": ("dim_tiempo", "fecha"),
        "mercado_id": ("dim_mercado", "mercado_id"),
        "cliente_id": ("dim_cliente", "cliente_id"),
        "producto_anada_key": ("dim_producto", "producto_anada_key"),
    }
    # La fecha de embarque es opcional; las demás claves no pueden quedar vacías.
    orphans = {
        column: int((~fact[column].dropna().isin(model[dim][key])).sum())
        + (0 if column == "fecha_embarque" else int(fact[column].isna().sum()))
        for column, (dim, key) in keys.items()
    }
    sales = processed["ventas"]
    products = model["dim_producto"]
    out_of_range = {
        "descuento fuera de 0–1": int((~sales["descuento"].between(0, 1)).sum()),
        "precio no positivo": int(sales["precio_unitario"].le(0).sum()),
        "litros por caja no positivos": int(products["litros_por_caja"].le(0).sum()),
        "costo por caja no positivo": int(products["costo_caja_clp"].le(0).sum()),
    }
    outside_year = int(fact["fecha"].dt.year.ne(ANALYSIS_YEAR).sum())
    markets = model["dim_mercado"].set_index("mercado_id")["moneda_facturacion"]
    in_usd = fact["mercado_id"].map(markets).eq("USD")
    without_rate = int((in_usd & fact["ingreso_neto_clp_fecha_venta"].isna()).sum())
    return [
        _check(
            "Unicidad de la clave del hecho", "published",
            "venta_id es único en fact_venta y hay una fila por cada venta limpia.",
            BLOCK, fact["venta_id"].is_unique and len(fact) == len(sales),
            f"{_n(len(fact))} filas en fact_venta y {_n(len(sales))} ventas limpias; "
            f"{_n(fact['venta_id'].duplicated().sum())} venta_id repetidos.",
        ),
        _check(
            "Claves sin huérfanos", "published",
            "Toda clave de fact_venta existe en su dimensión (fecha y fecha de embarque, mercado, cliente y producto-añada).",
            BLOCK, not any(orphans.values()),
            f"{len(keys)} claves revisadas; {_n(sum(orphans.values()))} valores sin dimensión.",
        ),
        _check(
            "Rangos válidos", "processed",
            "Descuento entre 0 y 1, precio mayor que cero y litros y costo por caja mayores que cero.",
            BLOCK, not any(out_of_range.values()),
            f"Descuento entre {sales['descuento'].min():.0%} y {sales['descuento'].max():.0%}; "
            f"{_n(sum(out_of_range.values()))} valores fuera de rango.",
        ),
        _check(
            "Fechas dentro del período", "published",
            f"La fecha de factura de cada venta está en {ANALYSIS_YEAR}.",
            BLOCK, outside_year == 0,
            f"{_n(len(fact) - outside_year)} ventas en {ANALYSIS_YEAR} "
            f"({_n(sales['fecha_imputada'].sum())} reasignadas desde {ANALYSIS_YEAR + 1}); {_n(outside_year)} fuera.",
        ),
        _check(
            "Tipo de cambio de cada venta en USD", "published",
            "Toda venta en USD tiene dólar observado a su fecha de factura para pasar a pesos.",
            BLOCK, without_rate == 0 and markets.notna().all(),
            f"{_n(in_usd.sum())} ventas en USD; {_n(without_rate)} sin tipo de cambio.",
        ),
    ]


def metric_checks(model, metrics) -> list[dict]:
    coverage = metrics["cobertura_margen"].iloc[0]
    exports = int(coverage["ventas_exportacion"])
    with_margin = int(coverage["ventas_exportacion_con_margen_factura"])
    fact = model["fact_venta"].merge(model["dim_mercado"][["mercado_id", "canal"]], on="mercado_id")
    fact = fact.loc[fact["canal"].eq("Exportación")]
    from_model = (fact["ingreso_neto_clp_fecha_venta"].sum() - fact["costo_total_clp"].sum()) / fact["litros"].sum()
    published = metrics["margen_por_mercado"].query(
        "criterio == 'reglas_finanzas' and moneda == 'CLP' and fecha_conversion == 'factura' "
        "and base == 'disponible' and pais == @TOTAL"
    )["margen_por_litro"].iloc[0]
    gap = abs(from_model - published)
    return [
        _check(
            "Cobertura de la métrica", "published",
            "Toda venta de exportación tiene margen en la vista principal (factura, CLP, reglas de Finanzas).",
            BLOCK, exports > 0 and with_margin == exports,
            f"{_n(with_margin)} de {_n(exports)} ventas de exportación con margen.",
        ),
        _check(
            "Métrica cuadra con el modelo", "published",
            "El margen por litro de exportación calculado desde fact_venta es el mismo que publica la métrica.",
            BLOCK, gap < MARGIN_TOLERANCE_CLP,
            f"fact_venta {_dec(from_model)} y métrica {_dec(published)} CLP/L; diferencia {_dec(gap, 4)}.",
        ),
    ]


def build_failure(error: Exception) -> dict:
    """Prueba que registra un error al armar el modelo o la métrica."""
    return _check(
        "Construcción del modelo y la métrica", "published",
        "El modelo y la métrica se pueden calcular con los datos de esta corrida.",
        BLOCK, False, f"{type(error).__name__}: {error}",
    )


def run_checks(staging, processed, model=None, metrics=None) -> pd.DataFrame:
    """Corre las pruebas que aplican a lo que se cargó en esta ejecución."""
    checks = source_checks(staging, processed)
    if "stg_tipo_cambio" in staging:
        checks += exchange_checks(staging, processed)
    if model is not None:
        checks += model_checks(processed, model)
    if model is not None and metrics is not None:
        checks += metric_checks(model, metrics)
    return pd.DataFrame(checks)


def blocking_failures(checks: pd.DataFrame) -> pd.DataFrame:
    return checks.loc[checks["si_falla"].eq(BLOCK) & checks["resultado"].eq("falla")]


def summarize_checks(checks: pd.DataFrame) -> str:
    passed = int(checks["resultado"].eq("ok").sum())
    blocking = int(checks["si_falla"].eq(BLOCK).sum())
    lines = [
        f"Pruebas de calidad: {passed} de {len(checks)} en verde "
        f"(bloquean la carga si fallan: {blocking}; solo avisan: {len(checks) - blocking})."
    ]
    for row in checks.loc[checks["resultado"].eq("falla")].itertuples():
        label = "Falla" if row.si_falla == BLOCK else "Aviso"
        lines.append(f"  {label} · {row.prueba}: {row.detalle}")
    return "\n".join(lines)
