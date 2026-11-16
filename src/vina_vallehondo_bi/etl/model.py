"""Modelo estrella de ventas: ``fact_venta`` y sus dimensiones.

Lleva a la cadena el diseño del cuaderno 03. El grano es una fila por
``venta_id``. Las medidas siguen las reglas de Finanzas de la E2 (C.7): el
ingreso es el monto neto registrado, con el ajuste de escala de las ventas
divididas por 10, y las mermas restan litros e ingreso sin revertir costo.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PUBLISHED_DIRECTORY = Path("data/published")

HEMISPHERE_BY_COUNTRY = {
    "Chile": "Sur",
    "Brasil": "Sur",
    "México": "Norte",
    "Estados Unidos": "Norte",
    "Canadá": "Norte",
    "Reino Unido": "Norte",
    "Alemania": "Norte",
    "Países Bajos": "Norte",
    "China": "Norte",
    "Japón": "Norte",
    "Corea del Sur": "Norte",
}
SOUTHERN_SEASON = {
    12: "Verano", 1: "Verano", 2: "Verano",
    3: "Otoño", 4: "Otoño", 5: "Otoño",
    6: "Invierno", 7: "Invierno", 8: "Invierno",
    9: "Primavera", 10: "Primavera", 11: "Primavera",
}
FACT_COLUMNS = [
    "venta_id", "fecha", "mercado_id", "cliente_id", "producto_anada_key", "fecha_embarque",
    "cajas", "litros", "monto_bruto", "monto_descuento", "ingreso_neto_moneda_original",
    "monto_bruto_clp", "monto_descuento_clp",
    "ingreso_neto_clp_fecha_venta", "ingreso_neto_clp_fecha_embarque", "costo_total_clp",
]


def market_currency(staging: dict[str, pd.DataFrame]) -> pd.Series:
    """Código de la moneda informada por cada mercado en la fuente."""
    sales = staging["stg_ventas"].dropna(subset=["moneda_id"])
    codes = staging["stg_monedas"].set_index("moneda_id")["moneda"].str.upper()
    return sales.groupby("mercado_id")["moneda_id"].first().map(codes)


def reliable_shipment_dates(shipments: pd.DataFrame) -> pd.DataFrame:
    """Primera fecha de embarque confiable de cada venta."""
    return (
        shipments.loc[shipments["fecha_embarque_confiable"]]
        .sort_values(["fecha_embarque", "embarque_orden", "linea_orden"])
        .drop_duplicates("venta_id")[["venta_id", "fecha_embarque"]]
    )


def build_dimensions(staging, processed) -> dict[str, pd.DataFrame]:
    markets = processed["mercados"][["mercado_id", "pais", "zona", "canal"]].copy()
    markets["hemisferio"] = markets["pais"].map(HEMISPHERE_BY_COUNTRY)
    markets["moneda_facturacion"] = markets["mercado_id"].map(market_currency(staging))

    customers = processed["clientes"][["cliente_id", "nombre", "tipo"]].drop_duplicates("cliente_id")

    wine_type = staging["stg_cepas"][["cepa", "tipo"]].drop_duplicates("cepa")
    products = (
        processed["costos_productos"][
            ["producto_id", "anada", "producto", "cepa", "tier", "formato", "litros_por_caja", "costo_caja_clp"]
        ]
        .sort_values(["producto_id", "anada"])
        .reset_index(drop=True)
        .merge(wine_type, on="cepa", how="left", validate="many_to_one")
    )
    products.insert(0, "producto_anada_key", np.arange(1, len(products) + 1))
    products = products[
        ["producto_anada_key", "producto_id", "anada", "producto", "cepa", "tipo",
         "tier", "formato", "litros_por_caja", "costo_caja_clp"]
    ]

    shipped = reliable_shipment_dates(processed["embarques"])["fecha_embarque"]
    dates = pd.concat([processed["ventas"]["fecha"], shipped]).dropna()
    calendar = pd.DataFrame({"fecha": pd.date_range(dates.min().normalize(), dates.max().normalize(), freq="D")})
    calendar["anio"] = calendar["fecha"].dt.year
    calendar["mes"] = calendar["fecha"].dt.month
    calendar["trimestre"] = "T" + calendar["fecha"].dt.quarter.astype(str)
    calendar["semestre"] = "S" + calendar["mes"].sub(1).floordiv(6).add(1).astype(str)
    calendar["estacion_hemisferio_sur"] = calendar["mes"].map(SOUTHERN_SEASON)

    return {
        "dim_tiempo": calendar,
        "dim_mercado": markets.reset_index(drop=True),
        "dim_cliente": customers.reset_index(drop=True),
        "dim_producto": products,
    }


def build_fact(staging, processed, dimensions) -> pd.DataFrame:
    products = dimensions["dim_producto"][
        ["producto_id", "anada", "producto_anada_key", "litros_por_caja", "costo_caja_clp"]
    ]
    currency = dimensions["dim_mercado"][["mercado_id", "moneda_facturacion"]]
    registered = staging["stg_ventas"][["fila_origen", "monto_neto"]].rename(columns={"monto_neto": "neto_registrado"})
    fact = (
        processed["ventas"]
        .merge(registered, on="fila_origen", how="left", validate="one_to_one")
        .merge(products, on=["producto_id", "anada"], how="left", validate="many_to_one")
        .merge(reliable_shipment_dates(processed["embarques"]), on="venta_id", how="left", validate="one_to_one")
        .merge(currency, on="mercado_id", how="left", validate="many_to_one")
    )
    rates = processed["tipo_cambio"].set_index("fecha")["dolar_observado"]
    rates = rates.where(rates.gt(0))
    in_clp = fact["moneda_facturacion"].eq("CLP")
    # El CLP se convierte a sí mismo; el USD con el dólar observado de cada fecha.
    sale_rate = fact["fecha"].map(rates).mask(in_clp, 1.0)
    shipment_rate = fact["fecha_embarque"].map(rates).mask(in_clp & fact["fecha_embarque"].notna(), 1.0)

    # Monto registrado; en las ventas con cajas x10 también se divide el monto.
    net = fact["neto_registrado"].mask(fact["ajuste_cajas"].eq("dividido_por_10"), fact["neto_registrado"] / 10)
    fact["litros"] = fact["cajas"] * fact["litros_por_caja"]
    fact["monto_bruto"] = fact["cajas"] * fact["precio_unitario"]
    fact["ingreso_neto_moneda_original"] = net
    fact["monto_descuento"] = fact["monto_bruto"] - net
    fact["monto_bruto_clp"] = fact["monto_bruto"] * sale_rate
    fact["ingreso_neto_clp_fecha_venta"] = net * sale_rate
    fact["monto_descuento_clp"] = fact["monto_bruto_clp"] - fact["ingreso_neto_clp_fecha_venta"]
    fact["ingreso_neto_clp_fecha_embarque"] = net * shipment_rate
    # La caja descartada no vuelve a inventario: la merma no revierte costo.
    fact["costo_total_clp"] = fact["cajas"].clip(lower=0) * fact["costo_caja_clp"]
    return fact[FACT_COLUMNS].reset_index(drop=True)


def build_model(staging, processed) -> dict[str, pd.DataFrame]:
    """Construye el modelo estrella desde staging y processed."""
    dimensions = build_dimensions(staging, processed)
    return {"fact_venta": build_fact(staging, processed, dimensions), **dimensions}


def publish_model(project_root: Path, model: dict[str, pd.DataFrame]) -> None:
    destination = project_root / PUBLISHED_DIRECTORY
    destination.mkdir(parents=True, exist_ok=True)
    for name, table in model.items():
        table.to_parquet(destination / f"{name}.parquet", index=False)
