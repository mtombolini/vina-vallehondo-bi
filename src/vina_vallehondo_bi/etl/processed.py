"""Limpieza de las tablas de staging hacia la capa ``data/processed``.

Aplica las reglas de calidad validadas en el perfilado. Cada corrección deja
una columna indicadora en la fila afectada, de modo que el modelo pueda
incluirla, excluirla o auditarla contra staging mediante ``fila_origen``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROCESSED_DIRECTORY = Path("data/processed")
ANALYSIS_YEAR = 2025
# Mayor pedido observado en registros consistentes; sobre este valor las cajas vienen multiplicadas por 10.
MAX_CASES_PER_SALE = 220
BOTTLES_PER_CASE = 12
AMOUNT_TOLERANCE = 0.005
# Plazo máximo entre venta y embarque para considerar creíble la fecha de embarque.
MAX_DAYS_TO_SHIPMENT = 60


def _expected_amount(sales: pd.DataFrame) -> pd.Series:
    return sales["cajas"].astype("float64") * sales["precio_unitario"] * (1 - sales["descuento"])


def clean_sales(sales: pd.DataFrame) -> pd.DataFrame:
    """Corrige y deduplica las ventas; deja una fila por ``venta_id``.

    Reglas, en orden:

    1. Moneda nula: se completa con la moneda con que factura el mercado.
    2. Cajas en botellas: sobre ``MAX_CASES_PER_SALE`` y con un monto muy
       inferior al esperado, las cajas se dividen por 12.
    3. Cajas x10: en el resto de los pedidos sobre ``MAX_CASES_PER_SALE``,
       cajas y monto se dividen por 10.
    4. Monto inconsistente: si difiere del esperado, se recalcula como
       cajas x precio x (1 - descuento).
    5. Fecha fuera de ``ANALYSIS_YEAR``: ``venta_id`` es correlativo con la
       fecha, por lo que se usa la fecha de la venta válida anterior.
    6. Duplicados: se conserva el primer registro de cada ``venta_id``.
    """
    clean = sales.sort_values("fila_origen").drop(columns=["zona_origen", "mes_origen"]).reset_index(drop=True)

    market_currency = clean.dropna(subset=["moneda_id"]).groupby("mercado_id")["moneda_id"].agg(lambda s: s.mode().iloc[0])
    clean["moneda_imputada"] = clean["moneda_id"].isna()
    clean["moneda_id"] = clean["moneda_id"].fillna(clean["mercado_id"].map(market_currency)).astype("Int64")

    ratio = clean["monto_neto"] / _expected_amount(clean)
    oversized = clean["cajas"].abs() > MAX_CASES_PER_SALE
    in_bottles = oversized & (ratio < 0.5) & (clean["cajas"] % BOTTLES_PER_CASE == 0)
    times_ten = oversized & ~in_bottles & (clean["cajas"] % 10 == 0)
    clean["ajuste_cajas"] = "ninguno"
    clean.loc[in_bottles, "ajuste_cajas"] = "botellas_a_cajas"
    clean.loc[times_ten, "ajuste_cajas"] = "dividido_por_10"
    clean.loc[in_bottles, "cajas"] = clean.loc[in_bottles, "cajas"] // BOTTLES_PER_CASE
    clean.loc[times_ten, "cajas"] = clean.loc[times_ten, "cajas"] // 10
    clean.loc[times_ten, "monto_neto"] = clean.loc[times_ten, "monto_neto"] / 10

    expected = _expected_amount(clean)
    clean["monto_recalculado"] = (clean["monto_neto"] / expected - 1).abs() > AMOUNT_TOLERANCE
    clean.loc[clean["monto_recalculado"], "monto_neto"] = expected[clean["monto_recalculado"]].round(2)

    clean = clean.sort_values(["venta_id", "fila_origen"]).reset_index(drop=True)
    clean["fecha_imputada"] = clean["fecha"].dt.year != ANALYSIS_YEAR
    valid_dates = clean["fecha"].mask(clean["fecha_imputada"])
    clean["fecha"] = valid_dates.ffill().bfill()

    clean["es_devolucion"] = (clean["cajas"] < 0).astype(bool)
    return clean.drop_duplicates("venta_id", keep="first").reset_index(drop=True)


def clean_markets(markets: pd.DataFrame, zones: pd.DataFrame, sales: pd.DataFrame) -> pd.DataFrame:
    """Une mercados con su zona.

    Si un mercado apunta a una zona inexistente, se le asigna la zona más
    frecuente con que la fuente de ventas registra ese mercado.
    """
    clean = markets.merge(zones, on="zona_id", how="left")
    orphans = clean["zona"].isna()
    if orphans.any():
        usual_zone = sales.groupby("mercado_id")["zona_origen"].agg(lambda s: s.mode().iloc[0])
        clean.loc[orphans, "zona"] = clean.loc[orphans, "mercado_id"].map(usual_zone)
        clean.loc[orphans, "zona_id"] = clean.loc[orphans, "zona"].map(zones.set_index("zona")["zona_id"])
    return clean[["mercado_id", "pais", "zona_id", "zona", "canal"]]


def clean_customers(customers: pd.DataFrame) -> pd.DataFrame:
    """Normaliza el RUT al formato ``12345678-K``."""
    clean = customers.copy()
    digits = clean["rut"].str.upper().str.replace(r"[^0-9K]", "", regex=True)
    clean["rut"] = digits.str[:-1] + "-" + digits.str[-1]
    return clean


def clean_costs(costs: pd.DataFrame, varieties: pd.DataFrame) -> pd.DataFrame:
    """Unifica la cepa y completa los costos faltantes.

    La cepa se toma del nombre del producto, que usa la grafía del maestro de
    cepas. El costo depende solo del tier y la añada, así que los costos nulos
    y las añadas faltantes de un producto se completan con el de su tier.
    """
    names = sorted(varieties["cepa"], key=len, reverse=True)
    products = costs.drop_duplicates("producto_id")[["producto_id", "producto", "tier", "formato", "litros_por_caja"]]
    products["cepa"] = products["producto"].map(
        lambda product: next((name for name in names if product.startswith(name)), None)
    )
    vintages = costs[["anada"]].drop_duplicates()
    tier_cost = costs.dropna(subset=["costo_caja_clp"]).groupby(["tier", "anada"], as_index=False)["costo_caja_clp"].first()

    clean = products.merge(vintages, how="cross")
    clean = clean.merge(costs[["producto_id", "anada", "costo_caja_clp", "activo"]], on=["producto_id", "anada"], how="left")
    clean = clean.merge(tier_cost, on=["tier", "anada"], how="left", suffixes=("", "_tier"))
    clean["costo_imputado"] = clean["costo_caja_clp"].isna() & clean["costo_caja_clp_tier"].notna()
    clean["costo_caja_clp"] = clean["costo_caja_clp"].fillna(clean["costo_caja_clp_tier"])
    columns = ["producto_id", "producto", "cepa", "tier", "formato", "litros_por_caja", "anada", "costo_caja_clp", "costo_imputado", "activo"]
    return clean[columns].sort_values(["producto_id", "anada"]).reset_index(drop=True)


def clean_shipments(shipments: pd.DataFrame, clean_sales_table: pd.DataFrame) -> pd.DataFrame:
    """Descarta líneas sin venta asociada y marca las fechas de embarque creíbles.

    Una fecha de embarque es confiable cuando la venta es la primera línea del
    embarque, este va al mercado de la venta y ocurre entre 0 y
    ``MAX_DAYS_TO_SHIPMENT`` días después de ella. Las demás líneas apuntan a
    ventas de otros mercados o fechas y solo coinciden por azar.
    """
    sales = clean_sales_table[["venta_id", "fecha", "mercado_id"]].rename(
        columns={"fecha": "fecha_venta", "mercado_id": "mercado_id_venta"}
    )
    clean = shipments.merge(sales, on="venta_id", how="inner")
    clean["dias_desde_venta"] = (clean["fecha_embarque"] - clean["fecha_venta"]).dt.days.astype("Int64")
    clean["fecha_embarque_confiable"] = (
        (clean["linea_orden"] == 1)
        & (clean["mercado_id"] == clean["mercado_id_venta"])
        & clean["dias_desde_venta"].between(0, MAX_DAYS_TO_SHIPMENT)
    )
    return clean.drop(columns=["fecha_venta", "mercado_id_venta"]).reset_index(drop=True)


def clean_exchange_rate(rates: pd.DataFrame) -> pd.DataFrame:
    """Completa la serie a días corridos desde ``ANALYSIS_YEAR``.

    Los días sin publicación (fines de semana y feriados) usan el último valor
    publicado, que es el dólar observado vigente ese día.
    """
    calendar = pd.DataFrame({"fecha": pd.date_range(rates["fecha"].min(), rates["fecha"].max(), freq="D")})
    clean = calendar.merge(rates, on="fecha", how="left")
    clean["publicado"] = clean["dolar_observado"].notna()
    clean["dolar_observado"] = clean["dolar_observado"].ffill()
    return clean[clean["fecha"] >= pd.Timestamp(ANALYSIS_YEAR, 1, 1)].reset_index(drop=True)


def run_processing(project_root: Path, staging: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Limpia las tablas de staging y escribe una tabla Parquet por cada una en processed."""
    sales = clean_sales(staging["stg_ventas"])
    tables = {
        "ventas": sales,
        "mercados": clean_markets(staging["stg_mercados"], staging["stg_zonas"], staging["stg_ventas"]),
        "clientes": clean_customers(staging["stg_clientes"]),
        "cepas": staging["stg_cepas"],
        "monedas": staging["stg_monedas"],
        "vendedores": staging["stg_vendedores"],
        "costos_productos": clean_costs(staging["stg_costos_productos"], staging["stg_cepas"]),
        "embarques": clean_shipments(staging["stg_embarques"], sales),
    }
    if "stg_tipo_cambio" in staging:
        tables["tipo_cambio"] = clean_exchange_rate(staging["stg_tipo_cambio"])

    processed = project_root / PROCESSED_DIRECTORY
    processed.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_parquet(processed / f"{name}.parquet", index=False)
    return tables
