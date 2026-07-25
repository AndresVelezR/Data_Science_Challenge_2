"""Merge de datasets y variables derivadas — SSOT. [FASE 2]"""
import numpy as np
import pandas as pd
from src.limpieza import FECHA_CORTE


def _agregar_feedback(fb: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega feedback al grano de transacción para evitar fan-out. [F2.1]
    Sin esto, las transacciones con >1 feedback duplicarían filas e inflarían el margen total.
    """
    return fb.groupby("Transaccion_ID").agg(
        Rating_Producto_Prom=("Rating_Producto", "mean"),
        Rating_Logistica_Prom=("Rating_Logistica", "mean"),
        NPS_Prom=("Satisfaccion_NPS", "mean"),
        Tuvo_Ticket_Soporte=("Ticket_Soporte_Abierto", lambda x: bool(x.any())),
        N_Feedbacks=("Feedback_ID", "count"),
    ).reset_index()


def construir_maestro(inv: pd.DataFrame, trx: pd.DataFrame, fb: pd.DataFrame) -> pd.DataFrame:
    """
    Merge en cadena. Grano final = 1 fila por VENTA. [F2.2]
    Nunca inner join para preservar trazabilidad de ingresos.
    """
    fb_agg = _agregar_feedback(fb)

    maestro = (
        trx
        .merge(inv, on="SKU_ID", how="left", suffixes=("", "_inv"), indicator="_origen_inv")
        .merge(fb_agg, on="Transaccion_ID", how="left")
    )

    # Flag SKU fantasma [F2.3]
    maestro["Es_SKU_Fantasma"] = maestro["_origen_inv"] == "left_only"
    maestro = maestro.drop(columns=["_origen_inv"])

    return maestro


def agregar_variables_derivadas(maestro: pd.DataFrame, inv: pd.DataFrame) -> pd.DataFrame:
    """
    Variables derivadas mínimo 3, implementadas 6. [F2.4]
    Para SKUs fantasma, Costo_Unitario_USD se imputa por mediana de categoría o global,
    permitiendo calcular margen en dos escenarios [F2.3].
    """
    df = maestro.copy()

    # Imputar costo para SKUs fantasma por mediana de categoría
    mediana_costo_cat = inv.groupby("Categoria")["Costo_Unitario_USD"].median()
    mediana_costo_global = inv["Costo_Unitario_USD"].median()

    def _costo_imputado(row):
        if pd.notna(row.get("Costo_Unitario_USD")):
            return row["Costo_Unitario_USD"]
        cat = row.get("Categoria")
        if cat and cat in mediana_costo_cat.index:
            return mediana_costo_cat[cat]
        return mediana_costo_global

    if "Costo_Unitario_USD" in df.columns:
        df["Costo_Unitario_USD_Imputado"] = df.apply(_costo_imputado, axis=1)
    else:
        df["Costo_Unitario_USD_Imputado"] = mediana_costo_global

    # Ingreso_Bruto [F2.4]
    df["Ingreso_Bruto"] = df["Cantidad_Vendida"] * df["Precio_Venta_Final"]

    # Margen_Utilidad y Margen_Pct [F2.4]
    df["Margen_Utilidad"] = (
        df["Ingreso_Bruto"]
        - df["Cantidad_Vendida"] * df["Costo_Unitario_USD_Imputado"]
        - df["Costo_Envio"]
    )
    mask_ingreso = df["Ingreso_Bruto"] != 0
    df["Margen_Pct"] = np.where(
        mask_ingreso,
        df["Margen_Utilidad"] / df["Ingreso_Bruto"] * 100,
        np.nan
    )

    # Margen conservador (solo SKUs catalogados) vs total [F2.3]
    df["Margen_Utilidad_Conservador"] = np.where(
        ~df["Es_SKU_Fantasma"],
        df["Cantidad_Vendida"] * (df["Precio_Venta_Final"] - df.get("Costo_Unitario_USD", np.nan)) - df["Costo_Envio"],
        np.nan
    )

    # Brecha_Entrega [F2.4]
    df["Brecha_Entrega"] = df["Tiempo_Entrega_Real"] - df["Lead_Time_Dias"]

    # Dias_Desde_Revision [F2.4]
    if "Ultima_Revision" in df.columns:
        df["Dias_Desde_Revision"] = (FECHA_CORTE - df["Ultima_Revision"]).dt.days

    # Segmento_NPS [F2.4] — en feedback ya viene, acá lo recalculamos a nivel maestro
    if "NPS_Prom" in df.columns:
        df["Segmento_NPS"] = pd.cut(
            df["NPS_Prom"],
            bins=[-100.1, -0.001, 50, 100],
            labels=["Detractor", "Pasivo", "Promotor"]
        )

    return df


def verificar_trazabilidad(df_crudo_trx: pd.DataFrame, maestro: pd.DataFrame) -> dict:
    """
    Aserción de trazabilidad. [QA-1]
    Verifica dos propiedades:
    1. Filas: el merge no duplicó ni eliminó filas (sin fan-out).
    2. Delta de ingresos: calculado y explicado (puede diferir por imputación de negativos).
    La propiedad crítica es la de filas, no la igualdad de montos (la limpieza cambia valores legítimamente).
    """
    filas_ok = len(maestro) == len(df_crudo_trx)
    # Ingreso crudo con valores positivos (negativos son imposibles, no revenue real)
    ingreso_crudo = (df_crudo_trx["Cantidad_Vendida"].clip(lower=0) * df_crudo_trx["Precio_Venta_Final"]).sum()
    ingreso_maestro = maestro["Ingreso_Bruto"].sum()
    delta = ingreso_maestro - ingreso_crudo
    n_negativos = int((df_crudo_trx["Cantidad_Vendida"] < 0).sum())
    return {
        "filas_ok": filas_ok,
        "filas_crudo": len(df_crudo_trx),
        "filas_maestro": len(maestro),
        "ingreso_crudo": round(float(ingreso_crudo), 2),
        "ingreso_maestro": round(float(ingreso_maestro), 2),
        "delta_usd": round(float(delta), 2),
        "explicacion": f"Delta de ${delta:,.0f} USD explicado por imputación de {n_negativos} cantidades negativas con mediana.",
    }
