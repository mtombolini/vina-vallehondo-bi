"""Capa semántica del margen bruto del producto para Viña Vallehondo."""

from pathlib import Path

import pandas as pd

from vina_vallehondo_bi.etl.processed import ANALYSIS_YEAR

METRIC_NAME = "Margen bruto del producto por litro"
BRAZIL = "Brasil"
TOTAL = "Total exportación"
SEGMENTS = {BRAZIL: "Recomendación de revisión", "China": "Hipótesis de mezcla"}
RULES = {
    "e1": ("neto_e1_usd", "costo_e1_clp"),
    "solo_monto_facturado": ("neto_facturado_usd", "costo_e1_clp"),
    "solo_sin_reversa": ("neto_e1_usd", "costo_sin_reversa_clp"),
    "reglas_finanzas": ("neto_facturado_usd", "costo_sin_reversa_clp"),
}
DATES = {"factura": "dolar_factura", "embarque": "dolar_embarque"}


def export_lines(staging, processed):
    """Una línea por venta de exportación de 2025, con los insumos de ambos criterios."""
    markets = processed["mercados"]
    markets = markets.loc[markets["canal"].eq("Exportación"), ["mercado_id", "pais"]]
    sales = processed["ventas"]
    sales = sales.loc[sales["fecha"].dt.year.eq(ANALYSIS_YEAR)]
    sales = sales.merge(markets, on="mercado_id", validate="many_to_one")
    currencies = processed["monedas"].set_index("moneda_id")["moneda"]
    if not sales["moneda_id"].map(currencies).eq("USD").all():
        raise ValueError("Se esperaba moneda de facturación USD en las exportaciones.")

    original = staging["stg_ventas"][["fila_origen", "monto_neto"]].rename(
        columns={"monto_neto": "neto_fuente_usd"}
    )
    lines = sales.merge(original, on="fila_origen", how="left", validate="one_to_one")
    costs = processed["costos_productos"][
        ["producto_id", "anada", "producto", "tier", "litros_por_caja", "costo_caja_clp", "costo_imputado"]
    ]
    lines = lines.merge(costs, on=["producto_id", "anada"], how="left", validate="many_to_one")

    shipments = processed["embarques"]
    shipments = (
        shipments.loc[shipments["fecha_embarque_confiable"]]
        .sort_values(["fecha_embarque", "embarque_orden", "linea_orden"])
        .drop_duplicates("venta_id")
    )
    lines = lines.merge(
        shipments[["venta_id", "fecha_embarque"]], on="venta_id", how="left", validate="one_to_one"
    )
    rates = processed["tipo_cambio"].set_index("fecha")["dolar_observado"]
    for role, date in [("factura", "fecha"), ("embarque", "fecha_embarque")]:
        lines[f"dolar_{role}"] = lines[date].map(rates.where(rates.gt(0)))
    lines["semestre"] = lines["fecha"].dt.month.sub(1).floordiv(6).add(1)
    lines["litros"] = lines["cajas"] * lines["litros_por_caja"]
    if lines["litros"].isna().any():
        raise ValueError("Hay ventas sin cajas o equivalencia a litros. No se puede medir la cobertura.")
    lines["bruto_usd"] = lines["cajas"] * lines["precio_unitario"]
    lines["neto_e1_usd"] = lines["monto_neto"]
    # El ajuste de escala del registro se conserva. El recálculo por descuadre es otra regla.
    lines["neto_facturado_usd"] = lines["neto_fuente_usd"].mask(
        lines["ajuste_cajas"].eq("dividido_por_10"), lines["neto_fuente_usd"] / 10
    )
    lines["costo_e1_clp"] = lines["cajas"] * lines["costo_caja_clp"]
    # El costo original ya se reconoció en la venta. El descarte resta ingreso y volumen.
    lines["costo_sin_reversa_clp"] = lines["cajas"].clip(lower=0) * lines["costo_caja_clp"]
    return lines


def _sum_by_market(lines, columns):
    by_market = lines.groupby("pais", sort=True)[columns].sum(min_count=1)
    by_market.loc[TOTAL] = lines[columns].sum(min_count=1)
    return by_market


def _volume(lines):
    fields = {"cajas": "cajas_totales", "litros": "litros_totales"}
    volume = _sum_by_market(lines, list(fields)).rename(columns=fields)
    for semester in (1, 2):
        semester_lines = lines.loc[lines["semestre"].eq(semester)]
        volume = volume.join(_sum_by_market(semester_lines, list(fields)).add_suffix(f"_s{semester}"))
    for unit in fields:
        first = volume[f"{unit}_s1"]
        volume[f"crecimiento_{unit}_pct"] = (volume[f"{unit}_s2"].div(first.where(first.gt(0))) - 1) * 100
    return volume


def _valued_lines(lines, rule, currency, conversion, population):
    net, cost = RULES[rule]
    fx = lines[DATES[conversion]]
    eligible = fx.notna() & lines[net].notna() & lines[cost].notna()
    if population == "comparable":
        eligible &= lines[["dolar_factura", "dolar_embarque"]].notna().all(axis=1)
    fields = ["pais", "fecha", "tier", "litros", "cajas", "bruto_usd", "descuento"]
    valued = lines.loc[eligible, fields].copy()
    if currency == "CLP":
        valued["ingreso_neto"] = lines.loc[eligible, net] * fx[eligible]
        valued["costo_producto"] = lines.loc[eligible, cost]
        valued["ingreso_bruto"] = valued["bruto_usd"] * fx[eligible]
    else:
        valued["ingreso_neto"] = lines.loc[eligible, net]
        valued["costo_producto"] = lines.loc[eligible, cost] / fx[eligible]
        valued["ingreso_bruto"] = valued["bruto_usd"]
    valued["descuento_comercial"] = valued["ingreso_bruto"] * valued["descuento"]
    valued["margen_total"] = valued["ingreso_neto"] - valued["costo_producto"]
    valued["ventas_con_margen"] = 1
    return valued


def _aggregate(lines, volume, rule, currency, conversion, population):
    valued = _valued_lines(lines, rule, currency, conversion, population)
    totals = _sum_by_market(
        valued, ["litros", "cajas", "ingreso_neto", "costo_producto", "ingreso_bruto",
                 "margen_total", "descuento_comercial", "ventas_con_margen"]
    ).rename(columns={"litros": "litros_con_margen", "cajas": "cajas_con_margen"})
    result = volume.join(totals)
    covered = ["litros_con_margen", "cajas_con_margen", "ventas_con_margen"]
    result[covered] = result[covered].fillna(0)
    for unit, field in [("litros", "margen_por_litro"), ("cajas", "margen_por_caja")]:
        denominator = result[f"{unit}_con_margen"]
        result[field] = result["margen_total"].div(denominator.where(denominator.gt(0)))
    result["cobertura_litros_pct"] = result["litros_con_margen"].div(result["litros_totales"].where(result["litros_totales"].gt(0))) * 100
    gross = result["ingreso_bruto"]
    valid_gross = gross.where(gross.gt(0))
    result["descuento_implicito_pct"] = (1 - result["ingreso_neto"].div(valid_gross)) * 100
    result["descuento_comercial_pct"] = result["descuento_comercial"].div(valid_gross) * 100
    markets = result.drop(index=TOTAL)["margen_por_litro"]
    median = markets.median()
    result["mediana_margen_por_litro"] = median
    result["ranking"] = markets.rank(ascending=False, method="min").astype("Int64")
    result["clase_margen"] = pd.Series(pd.NA, index=result.index, dtype="string")
    result.loc[markets.dropna().index, "clase_margen"] = markets.dropna().ge(median).map(
        {True: "Buen margen", False: "Margen bajo"}
    )
    result["estado_decision"] = result.index.map(lambda market: SEGMENTS.get(market, "Seguimiento"))
    result.loc[TOTAL, "estado_decision"] = pd.NA
    result = result.reset_index()
    for position, (name, value) in enumerate(
        [("criterio", rule), ("moneda", currency), ("fecha_conversion", conversion), ("base", population)]
    ):
        result.insert(position, name, value)
    return result


def _business_case(metrics):
    rows = []
    selected = metrics.loc[
        metrics["moneda"].eq("CLP") & metrics["fecha_conversion"].eq("factura") & metrics["base"].eq("disponible")
    ]
    for rule in ("e1", "reglas_finanzas"):
        frame = selected.loc[selected["criterio"].eq(rule)].set_index("pais")
        br = frame.loc[BRAZIL]
        others = frame.drop(index=[BRAZIL, TOTAL])
        normal_rate = 1 - others["ingreso_neto"].sum() / others["ingreso_bruto"].sum()
        # Escenario comparable con E1: igual precio de lista, mezcla y volumen.
        current_rate = br["descuento_implicito_pct"] / 100
        extra = br["ingreso_bruto"] * (current_rate - normal_rate)
        commercial_rate = br["descuento_comercial_pct"] / 100
        others_commercial_rate = others["descuento_comercial"].sum() / others["ingreso_bruto"].sum()
        commercial_extra = br["ingreso_bruto"] * (commercial_rate - others_commercial_rate)
        gap = (br["mediana_margen_por_litro"] - br["margen_por_litro"]) * br["litros_con_margen"]
        normal_margin = br["margen_total"] + extra
        rows.append({
            "criterio": rule,
            "margen_brasil_clp": br["margen_total"],
            "margen_brasil_clp_litro": br["margen_por_litro"],
            "brecha_mediana_clp": gap,
            "descuento_implicito_brasil_pct": current_rate * 100,
            "descuento_implicito_resto_pct": normal_rate * 100,
            "descuento_extra_clp": extra,
            "proporcion_brecha_pct": extra / gap * 100,
            "margen_con_descuento_resto_clp_litro": normal_margin / br["litros_con_margen"],
            "perdida_volumen_equilibrio_pct": (1 - br["margen_total"] / normal_margin) * 100,
            "un_punto_descuento_clp": br["ingreso_bruto"] * 0.01,
            "descuento_comercial_brasil_pct": commercial_rate * 100,
            "descuento_comercial_resto_pct": others_commercial_rate * 100,
            "escenario_descuento_comercial_clp": commercial_extra,
            "perdida_volumen_equilibrio_comercial_pct": (
                1 - br["margen_total"] / (br["margen_total"] + commercial_extra)
            ) * 100,
        })
    return pd.DataFrame(rows)


def _mix_scenarios(lines):
    valued = _valued_lines(lines, "reglas_finanzas", "CLP", "factura", "disponible")
    tiers = valued.groupby(["pais", "tier"])[["litros", "margen_total"]].sum()
    rows = []
    for market in (BRAZIL, "China"):
        if market not in tiers.index.get_level_values("pais"):
            continue
        market_tiers = tiers.loc[market]
        total_liters = market_tiers["litros"].sum()
        tier_liters = market_tiers["litros"]
        unit_margin = market_tiers["margen_total"].div(tier_liters.where(tier_liters.gt(0)))
        if total_liters <= 0 or tier_liters.get("Varietal", 0) < total_liters * 0.01:
            continue
        for target in ("Reserva", "Gran Reserva"):
            if pd.isna(unit_margin.get(target)):
                continue
            delta = unit_margin[target] - unit_margin["Varietal"]
            rows.append({
                "pais": market, "origen": "Varietal", "destino": target, "puntos_porcentuales": 1,
                "litros_reasignados": total_liters * 0.01,
                "participacion_varietal_pct": market_tiers.loc["Varietal", "litros"] / total_liters * 100,
                "margen_origen_clp_litro": unit_margin["Varietal"],
                "margen_destino_clp_litro": unit_margin[target],
                "variacion_margen_clp": total_liters * 0.01 * delta,
            })
    return pd.DataFrame(rows)


def _market_series(lines):
    valued = _valued_lines(lines, "reglas_finanzas", "CLP", "factura", "disponible")
    valued["mes_factura"] = valued["fecha"].dt.to_period("M").astype(str)
    series = valued.groupby(["pais", "mes_factura"], as_index=False)[
        ["litros", "cajas", "ingreso_bruto", "ingreso_neto", "costo_producto", "margen_total"]
    ].sum()
    series["margen_clp_litro"] = series["margen_total"].div(series["litros"].where(series["litros"].gt(0)))
    return series


def build_margin_tables(staging, processed):
    """Calcula las tablas para informe y tablero sobre la misma definición."""
    lines = export_lines(staging, processed)
    volume = _volume(lines)
    public_rules = ("e1", "reglas_finanzas")
    metrics = pd.concat([
        _aggregate(lines, volume, rule, currency, conversion, population)
        for rule in public_rules
        for currency in ("CLP", "USD")
        for conversion, population in [("factura", "disponible"), ("factura", "comparable"),
                                       ("embarque", "comparable")]
    ], ignore_index=True)
    audit = pd.concat([
        _aggregate(lines, volume, rule, "CLP", "factura", "disponible") for rule in RULES
    ], ignore_index=True)
    sales = processed["ventas"]
    baseline = metrics.loc[
        metrics["criterio"].eq("reglas_finanzas")
        & metrics["moneda"].eq("CLP")
        & metrics["fecha_conversion"].eq("factura")
        & metrics["base"].eq("disponible")
        & metrics["pais"].eq(TOTAL)
    ].iloc[0]
    source_rows = len(staging["stg_ventas"])
    quality = pd.DataFrame([{
        "registros_fuente": source_rows,
        "ventas_unicas": len(sales),
        "registros_duplicados": source_rows - len(sales),
        "ventas_nacionales": int(sales["mercado_id"].isin(
            processed["mercados"].loc[processed["mercados"]["canal"].eq("Nacional"), "mercado_id"]
        ).sum()),
        "ventas_exportacion": len(lines),
        "ventas_exportacion_con_margen_factura": int(baseline["ventas_con_margen"]),
        "cobertura_registros_fuente_pct": baseline["ventas_con_margen"] / source_rows * 100,
        "montos_recalculados_e1_total": int(sales["monto_recalculado"].sum()),
        "montos_recalculados_e1_exportacion": int(lines["monto_recalculado"].sum()),
        "mermas_total": int(sales["es_devolucion"].sum()),
        "mermas_exportacion": int(lines["es_devolucion"].sum()),
        "moneda_faltante_fuente": int(staging["stg_ventas"]["moneda_id"].isna().sum()),
        "moneda_imputada_unicas": int(sales["moneda_imputada"].sum()),
        "moneda_imputada_exportacion": int(lines["moneda_imputada"].sum()),
        "costos_imputados_exportacion": int(lines["costo_imputado"].sum()),
        "ventas_embarque_confiable": int(lines["fecha_embarque"].notna().sum()),
    }])
    inconsistent = lines.loc[lines["monto_recalculado"], [
        "venta_id", "fila_origen", "pais", "neto_fuente_usd", "neto_facturado_usd", "neto_e1_usd", "ajuste_cajas"
    ]]
    return {
        "margen_por_mercado": metrics,
        "sensibilidad_reglas_margen": audit,
        "caso_descuento_brasil": _business_case(metrics),
        "escenarios_mezcla": _mix_scenarios(lines),
        "serie_mensual_mercado": _market_series(lines),
        "cobertura_margen": quality,
        "descuadres_monto_exportacion": inconsistent,
    }


def publish_margin_tables(project_root: Path, staging, processed):
    tables = build_margin_tables(staging, processed)
    destination = project_root / "data/published"
    destination.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(destination / f"{name}.csv", index=False)
    return tables
