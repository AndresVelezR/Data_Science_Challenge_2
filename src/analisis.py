"""Cálculos de las cinco preguntas gerenciales. [RETO P1-P5]"""
import numpy as np
import pandas as pd
from scipy import stats


def _filtrar_serie_tiempo(df: pd.DataFrame) -> pd.DataFrame:
    """Excluye fechas futuras de análisis temporales. [QA-4]"""
    if "Fecha_Futura" in df.columns:
        return df[~df["Fecha_Futura"]].copy()
    return df.copy()


# ---------------------------------------------------------------------------
# P1 — Fuga de capital [P1]
# ---------------------------------------------------------------------------

def p1_fuga_capital(maestro: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """SKUs con Margen_Utilidad < 0. Contraste Online vs otros canales. [P1]"""
    df = _filtrar_serie_tiempo(maestro)
    if df.empty or "Margen_Utilidad" not in df.columns:
        return pd.DataFrame(), {"error": "Sin datos suficientes"}

    # Agregar por SKU
    por_sku = df.groupby("SKU_ID", dropna=False).agg(
        Categoria=("Categoria", "first"),
        Canal_Venta=("Canal_Venta", lambda x: x.mode().iloc[0] if len(x) > 0 else "Desconocido"),
        Ingreso_Total=("Ingreso_Bruto", "sum"),
        Margen_Total=("Margen_Utilidad", "sum"),
        Transacciones=("Transaccion_ID", "count"),
    ).reset_index()
    por_sku["Margen_Pct"] = np.where(
        por_sku["Ingreso_Total"] != 0,
        por_sku["Margen_Total"] / por_sku["Ingreso_Total"] * 100,
        np.nan
    )

    skus_negativos = por_sku[por_sku["Margen_Total"] < 0].sort_values("Margen_Total")

    # Contraste por canal
    canal_resumen = df.groupby("Canal_Venta").agg(
        Margen_Total=("Margen_Utilidad", "sum"),
        Ingreso_Total=("Ingreso_Bruto", "sum"),
        Transacciones=("Transaccion_ID", "count"),
    ).reset_index()
    canal_resumen["Margen_Pct"] = np.where(
        canal_resumen["Ingreso_Total"] != 0,
        canal_resumen["Margen_Total"] / canal_resumen["Ingreso_Total"] * 100,
        np.nan
    )

    perdida_total = float(skus_negativos["Margen_Total"].sum())
    ingreso_total = float(df["Ingreso_Bruto"].sum())
    pct_perdida = abs(perdida_total) / ingreso_total * 100 if ingreso_total != 0 else 0

    conclusiones = {
        "n_skus_negativos": len(skus_negativos),
        "perdida_total_usd": round(perdida_total, 2),
        "pct_del_ingreso": round(pct_perdida, 2),
        "canal_peor": canal_resumen.nsmallest(1, "Margen_Pct")["Canal_Venta"].iloc[0] if len(canal_resumen) > 0 else "N/A",
        "tipo_falla": "pérdida por volumen" if skus_negativos["Transacciones"].mean() > 10 else "falla de precios",
        "tabla_canal": canal_resumen.to_dict("records"),
    }

    return skus_negativos, conclusiones


# ---------------------------------------------------------------------------
# P2 — Crisis logística [P2]
# ---------------------------------------------------------------------------

def p2_crisis_logistica(maestro: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Correlación Pearson Tiempo_Entrega_Real vs NPS_Prom por ciudad × bodega. [P2]
    Filtra grupos con n < 30.
    """
    df = maestro.dropna(subset=["Tiempo_Entrega_Real", "NPS_Prom", "Ciudad_Destino", "Bodega_Origen"]).copy()

    if len(df) < 30:
        return pd.DataFrame(), {"error": "Datos insuficientes para correlación significativa"}

    filas = []
    for (ciudad, bodega), grupo in df.groupby(["Ciudad_Destino", "Bodega_Origen"]):
        n = len(grupo)
        if n < 30:
            continue
        r, pval = stats.pearsonr(grupo["Tiempo_Entrega_Real"], grupo["NPS_Prom"])
        filas.append({
            "Ciudad": ciudad,
            "Bodega": bodega,
            "Correlacion": round(r, 4),
            "P_Valor": round(pval, 4),
            "N": n,
            "Significativa": pval < 0.05,
        })

    if not filas:
        return pd.DataFrame(), {"error": "Ningún grupo tiene n >= 30"}

    resultado = pd.DataFrame(filas).sort_values("Correlacion")

    peor = resultado.iloc[0]
    conclusiones = {
        "zona_intervenir": f"{peor['Ciudad']} × {peor['Bodega']}",
        "correlacion_peor": peor["Correlacion"],
        "p_valor_peor": peor["P_Valor"],
        "n_grupos_analizados": len(resultado),
        "grupos_significativos": int(resultado["Significativa"].sum()),
    }

    return resultado, conclusiones


# ---------------------------------------------------------------------------
# P3 — Venta invisible (SKU fantasma) [P3]
# ---------------------------------------------------------------------------

def p3_venta_invisible(maestro: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Ingresos de SKUs fantasma en USD y % del total. Desglose por ciudad y canal. [P3]"""
    df = _filtrar_serie_tiempo(maestro)
    if df.empty or "Es_SKU_Fantasma" not in df.columns:
        return pd.DataFrame(), {"error": "Sin datos"}

    fantasmas = df[df["Es_SKU_Fantasma"]]
    ingreso_total = float(df["Ingreso_Bruto"].sum())
    ingreso_fantasma = float(fantasmas["Ingreso_Bruto"].sum())
    pct = ingreso_fantasma / ingreso_total * 100 if ingreso_total != 0 else 0

    por_ciudad = fantasmas.groupby("Ciudad_Destino", dropna=False).agg(
        Ingreso=("Ingreso_Bruto", "sum"),
        Transacciones=("Transaccion_ID", "count"),
    ).reset_index().sort_values("Ingreso", ascending=False)

    por_canal = fantasmas.groupby("Canal_Venta", dropna=False).agg(
        Ingreso=("Ingreso_Bruto", "sum"),
        Transacciones=("Transaccion_ID", "count"),
    ).reset_index().sort_values("Ingreso", ascending=False)

    conclusiones = {
        "ingreso_fantasma_usd": round(ingreso_fantasma, 2),
        "pct_ingreso_total": round(pct, 2),
        "n_skus_fantasma": int(df["SKU_ID"][df["Es_SKU_Fantasma"]].nunique()),
        "n_transacciones_fantasma": len(fantasmas),
        "hipotesis": "Catálogo desactualizado (productos nuevos no registrados en ERP), no error de digitación",
        "por_ciudad": por_ciudad.to_dict("records"),
        "por_canal": por_canal.to_dict("records"),
    }

    return pd.concat([por_ciudad.assign(dimension="Ciudad"), por_canal.assign(dimension="Canal")]), conclusiones


# ---------------------------------------------------------------------------
# P4 — Diagnóstico de fidelidad [P4]
# ---------------------------------------------------------------------------

def p4_diagnostico_fidelidad(maestro: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Por categoría: Stock, NPS y Margen. Cuadrante stock alto + NPS negativo. [P4]"""
    cols_req = {"Categoria", "Stock_Actual", "NPS_Prom", "Margen_Pct", "Rating_Producto_Prom"}
    df = maestro.dropna(subset=list(cols_req - {"Rating_Producto_Prom"}))

    if df.empty:
        return pd.DataFrame(), {"error": "Sin datos suficientes"}

    resumen = df.groupby("Categoria", dropna=False).agg(
        Stock_Prom=("Stock_Actual", "mean"),
        NPS_Prom=("NPS_Prom", "mean"),
        Margen_Pct_Prom=("Margen_Pct", "mean"),
        Rating_Prom=("Rating_Producto_Prom", "mean"),
        N=("Transaccion_ID", "count"),
    ).reset_index()

    # Cuadrante: stock > mediana Y NPS < 0
    med_stock = resumen["Stock_Prom"].median()
    resumen["Cuadrante"] = "Normal"
    mask = (resumen["Stock_Prom"] > med_stock) & (resumen["NPS_Prom"] < 0)
    resumen.loc[mask, "Cuadrante"] = "⚠ Stock Alto + NPS Negativo"

    # Causa: si Rating_Prom alto pero Margen bajo → sobrecosto; si Rating bajo → calidad
    resumen["Causa_Probable"] = np.where(
        resumen["Rating_Prom"] >= 3.5,
        "Sobrecosto (calidad aceptable, margen bajo)",
        "Calidad deficiente (rating bajo)"
    )

    peor = resumen[mask].nsmallest(1, "NPS_Prom")
    conclusiones = {
        "categorias_problema": resumen[mask]["Categoria"].tolist(),
        "n_categorias_problema": int(mask.sum()),
        "categoria_peor_nps": peor["Categoria"].iloc[0] if len(peor) > 0 else "N/A",
        "causa_dominante": peor["Causa_Probable"].iloc[0] if len(peor) > 0 else "N/A",
    }

    return resumen, conclusiones


# ---------------------------------------------------------------------------
# P5 — Riesgo operativo [P5]
# ---------------------------------------------------------------------------

def p5_riesgo_operativo(maestro: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Por bodega: Dias_Desde_Revision vs tasa de soporte. Scatter + OLS numpy. [P5]"""
    cols_req = {"Bodega_Origen", "Dias_Desde_Revision", "Tuvo_Ticket_Soporte"}
    df = maestro.dropna(subset=list(cols_req))

    if len(df) < 2:
        return pd.DataFrame(), {"error": "Sin datos suficientes"}

    df = df.copy()
    df["Tuvo_Ticket_Soporte"] = df["Tuvo_Ticket_Soporte"].astype(float)
    resumen = df.groupby("Bodega_Origen").agg(
        Dias_Prom=("Dias_Desde_Revision", "mean"),
        Tasa_Soporte=("Tuvo_Ticket_Soporte", "mean"),
        N=("Transaccion_ID", "count"),
    ).reset_index()
    resumen["Dias_Prom"] = resumen["Dias_Prom"].astype(float)
    resumen["Tasa_Soporte"] = resumen["Tasa_Soporte"].astype(float)

    # Línea de tendencia OLS con numpy.polyfit (sin statsmodels) [nota del plan]
    if len(resumen) >= 2:
        coef = np.polyfit(resumen["Dias_Prom"], resumen["Tasa_Soporte"], 1)
        resumen["Tendencia_OLS"] = np.polyval(coef, resumen["Dias_Prom"])
        pendiente = round(float(coef[0]), 6)
    else:
        pendiente = 0.0

    # Bodegas "a ciegas": dias > mediana Y tasa_soporte > mediana
    med_dias = resumen["Dias_Prom"].median()
    med_tasa = resumen["Tasa_Soporte"].median()
    mask_riesgo = (resumen["Dias_Prom"] > med_dias) & (resumen["Tasa_Soporte"] > med_tasa)
    resumen["Nivel_Riesgo"] = np.where(mask_riesgo, "Alto", "Normal")

    conclusiones = {
        "bodegas_a_ciegas": resumen[mask_riesgo]["Bodega_Origen"].tolist(),
        "pendiente_ols": pendiente,
        "interpretacion": (
            "Correlación positiva: más días sin revisión → más tickets de soporte"
            if pendiente > 0 else "Sin correlación clara entre antigüedad y tickets"
        ),
    }

    return resumen, conclusiones
