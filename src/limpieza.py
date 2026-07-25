"""Auditoría y limpieza de los tres datasets. [FASE 1]"""
import re
import numpy as np
import pandas as pd

FECHA_CORTE = pd.Timestamp("2026-01-31")

# ---------------------------------------------------------------------------
# Nulos disfrazados que se cuentan como nulos en la auditoría
_NULOS_DISFRAZADOS = {"???", "---", "Ventas_Web"}

# ---------------------------------------------------------------------------
# AUDITORÍA [F1.1]
# ---------------------------------------------------------------------------

def _celdas_nulas_extendidas(df: pd.DataFrame) -> int:
    """Suma de NaN reales + valores disfrazados de nulo."""
    total = df.isna().sum().sum()
    for col in df.select_dtypes(include="object").columns:
        total += df[col].isin(_NULOS_DISFRAZADOS).sum()
    return int(total)


def _valores_imposibles(df: pd.DataFrame, nombre: str) -> int:
    """Cuenta celdas con valores imposibles según el dataset. [F1.1]"""
    count = 0
    if nombre == "inventario":
        if "Stock_Actual" in df.columns:
            count += (df["Stock_Actual"] < 0).sum()
        if "Rating_Producto" in df.columns:
            count += (df["Rating_Producto"] > 5).sum()
    if nombre == "transacciones":
        if "Cantidad_Vendida" in df.columns:
            count += (df["Cantidad_Vendida"] < 0).sum()
        if "Tiempo_Entrega_Real" in df.columns:
            count += (df["Tiempo_Entrega_Real"] == 999).sum()
    if nombre == "feedback":
        if "Rating_Producto" in df.columns:
            count += (df["Rating_Producto"] > 5).sum()
        if "Edad_Cliente" in df.columns:
            count += (df["Edad_Cliente"] > 100).sum()
    return int(count)


def _outliers_iqr(df: pd.DataFrame) -> dict[str, int]:
    """Cuenta outliers IQR por columna numérica."""
    resultado = {}
    for col in df.select_dtypes(include="number").columns:
        serie = df[col].dropna()
        q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        mask = (serie < q1 - 1.5 * iqr) | (serie > q3 + 1.5 * iqr)
        if mask.any():
            resultado[col] = int(mask.sum())
    return resultado


def calcular_health_score(df: pd.DataFrame, nombre: str) -> float:
    """
    Health Score [F1.2]:
      Completitud = 100 × (1 − celdas_nulas / celdas_totales)
      Unicidad    = 100 × (1 − filas_o_ids_duplicados / filas_totales)
      Validez     = 100 × (1 − celdas_con_valor_imposible / celdas_totales)
      Health Score = 0.40·Completitud + 0.20·Unicidad + 0.40·Validez
    Pesos: completitud y validez priorizan porque sesgan KPIs financieros;
    duplicidad es problema de trazabilidad, no de magnitud.
    """
    n_celdas = df.size
    n_filas = len(df)

    completitud = 100 * (1 - _celdas_nulas_extendidas(df) / n_celdas)

    # Unicidad: filas 100% duplicadas OU IDs duplicados (lo que sea mayor)
    dup_exactas = int(df.duplicated().sum())
    id_col = {"inventario": "SKU_ID", "transacciones": "Transaccion_ID", "feedback": "Feedback_ID"}.get(nombre)
    if id_col and id_col in df.columns:
        dup_ids = int(df[id_col].duplicated().sum())
    else:
        dup_ids = 0
    unicidad = 100 * (1 - max(dup_exactas, dup_ids) / n_filas)

    imposibles = _valores_imposibles(df, nombre)
    validez = 100 * (1 - imposibles / n_celdas)

    return round(0.40 * completitud + 0.20 * unicidad + 0.40 * validez, 2)


def auditar(df: pd.DataFrame, nombre: str) -> dict:
    """Auditoría completa de un dataset. [F1.1]"""
    n_celdas = df.size

    # Nulos por columna (reales + disfrazados)
    nulos_por_col = df.isna().sum().to_dict()
    for col in df.select_dtypes(include="object").columns:
        nulos_por_col[col] = int(nulos_por_col[col]) + int(df[col].isin(_NULOS_DISFRAZADOS).sum())
    pct_nulos = {k: round(100 * v / len(df), 2) for k, v in nulos_por_col.items()}

    id_col = {"inventario": "SKU_ID", "transacciones": "Transaccion_ID", "feedback": "Feedback_ID"}.get(nombre)
    ids_dup = int(df[id_col].duplicated().sum()) if id_col and id_col in df.columns else 0

    return {
        "nombre": nombre,
        "filas": len(df),
        "columnas": len(df.columns),
        "celdas_totales": n_celdas,
        "pct_nulos_por_columna": pct_nulos,
        "nulos_totales": _celdas_nulas_extendidas(df),
        "filas_duplicadas_exactas": int(df.duplicated().sum()),
        "ids_duplicados": ids_dup,
        "outliers_por_columna": _outliers_iqr(df),
        "valores_imposibles": _valores_imposibles(df, nombre),
        "health_score": calcular_health_score(df, nombre),
    }


def comparar_salud(antes: dict, despues: dict) -> pd.DataFrame:
    """Tabla Antes vs Después de health score y métricas clave. [F1.3]"""
    rows = []
    for nombre in antes:
        a, d = antes[nombre], despues[nombre]
        rows.append({
            "Dataset": nombre,
            "Health Score Antes": a["health_score"],
            "Health Score Después": d["health_score"],
            "Delta": round(d["health_score"] - a["health_score"], 2),
            "Nulos Antes": a["nulos_totales"],
            "Nulos Después": d["nulos_totales"],
            "Imposibles Antes": a["valores_imposibles"],
            "Imposibles Después": d["valores_imposibles"],
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# UTILIDADES DE LIMPIEZA
# ---------------------------------------------------------------------------

def marcar_outliers_iqr(df: pd.DataFrame, columna: str):
    """Devuelve (serie_bool de outliers, (limite_inferior, limite_superior)). [QA-3]"""
    serie = df[columna].dropna()
    q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
    iqr = q3 - q1
    lim_inf = q1 - 1.5 * iqr
    lim_sup = q3 + 1.5 * iqr
    mask = (df[columna] < lim_inf) | (df[columna] > lim_sup)
    return mask.fillna(False), (round(lim_inf, 4), round(lim_sup, 4))


def _elegir_estadistico(serie: pd.Series) -> tuple[str, float]:
    """Elige media o mediana según simetría. Devuelve (criterio, valor)."""
    s = serie.dropna()
    if len(s) < 2:
        return "mediana", float(s.median())
    std = s.std()
    if std == 0:
        return "mediana", float(s.median())
    asimetria = abs(s.mean() - s.median()) / std
    if asimetria < 0.1:
        return "media", float(s.mean())
    return "mediana", float(s.median())


def _parsear_lead_time(v):
    """'Inmediato'->0 | '25-30 días'->27.5 | '10'->10.0 | otro->NaN"""
    if pd.isna(v):
        return np.nan
    v = str(v).strip()
    if v.lower() == "inmediato":
        return 0.0
    m = re.match(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)", v)
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2
    m2 = re.match(r"^(\d+(?:\.\d+)?)$", v)
    if m2:
        return float(m2.group(1))
    return np.nan


# ---------------------------------------------------------------------------
# LIMPIEZA INVENTARIO [FASE 1 + QA-2]
# ---------------------------------------------------------------------------

_CAT_INVENTARIO = {
    "LAPTOP": "Laptops",
    "Laptops": "Laptops",
    "smart-phone": "Smartphones",
    "Smartphones": "Smartphones",
    "Tablets": "Tablets",
    "Accesorios": "Accesorios",
    "Monitores": "Monitores",
    "???": None,
}

_BODEGA_MAPA = {
    "Norte": "Norte",
    "norte": "Norte",
    "Sur": "Sur",
    "Occidente": "Occidente",
    "ZONA_FRANCA": "ZONA_FRANCA",
    "BOD-EXT-99": "BOD-EXT-99",  # Bodega externa real, no es variante [QA-2]
}


def limpiar_inventario(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Limpia inventario_central_v2. [FASE 1 + QA-2]"""
    df = df.copy()
    log = []

    # Categoria — mapeo canónico explícito [QA-2]
    df["Categoria"] = df["Categoria"].map(_CAT_INVENTARIO)
    df["Categoria"] = df["Categoria"].fillna("Sin Categoria")
    log.append({"columna": "Categoria", "problema": "Variantes y '???'",
                "accion": "Mapeo canónico explícito; '???' → NaN → 'Sin Categoria'",
                "justificacion": "Normalización por diccionario [QA-2]; '???' es nulo disfrazado",
                "filas_afectadas": int((df["Categoria"] == "Sin Categoria").sum())})

    # Stock_Actual — negativos → NaN → imputar mediana
    mask_neg = df["Stock_Actual"] < 0
    df.loc[mask_neg, "Stock_Actual"] = np.nan
    criterio, valor = _elegir_estadistico(df["Stock_Actual"])
    df["Stock_Actual"] = df["Stock_Actual"].fillna(valor)
    log.append({"columna": "Stock_Actual", "problema": "Negativos + nulos",
                "accion": f"Negativos → NaN; imputar {criterio} ({valor:.2f})",
                "justificacion": f"Valores negativos son imposibles en stock. Distribución asimétrica → {criterio}",
                "filas_afectadas": int(mask_neg.sum() + df["Stock_Actual"].isna().sum())})

    # Costo_Unitario_USD — marcar outliers IQR, no imputar [QA-3]
    mask_costo, limites_costo = marcar_outliers_iqr(df, "Costo_Unitario_USD")
    df["Outlier_Costo"] = mask_costo
    log.append({"columna": "Costo_Unitario_USD", "problema": f"Outliers IQR ({mask_costo.sum()} filas)",
                "accion": f"Marcar flag Outlier_Costo. Límites: {limites_costo}",
                "justificacion": "No se eliminan: pueden ser productos legítimos de alto valor [QA-3]",
                "filas_afectadas": int(mask_costo.sum())})

    # Lead_Time_Dias — texto mixto → numérico
    n_nulos_antes = df["Lead_Time_Dias"].isna().sum()
    df["Lead_Time_Dias"] = df["Lead_Time_Dias"].apply(_parsear_lead_time)
    criterio_lt, valor_lt = _elegir_estadistico(df["Lead_Time_Dias"])
    n_nulos_post = df["Lead_Time_Dias"].isna().sum()
    df["Lead_Time_Dias"] = df["Lead_Time_Dias"].fillna(valor_lt)
    log.append({"columna": "Lead_Time_Dias", "problema": "Texto mixto ('25-30 días', 'Inmediato') + nulos",
                "accion": f"Parser explícito → numérico; nulos imputados con {criterio_lt} ({valor_lt:.2f})",
                "justificacion": f"Inmediato→0, rangos→promedio, dígitos→float; {criterio_lt} por distribución",
                "filas_afectadas": int(n_nulos_post + n_nulos_antes)})

    # Bodega_Origen — mapeo canónico [QA-2]
    df["Bodega_Origen"] = df["Bodega_Origen"].map(_BODEGA_MAPA)
    log.append({"columna": "Bodega_Origen", "problema": "Variantes: 'norte', mayúsculas",
                "accion": "Mapeo canónico explícito; BOD-EXT-99 conservada como bodega real",
                "justificacion": "BOD-EXT-99 es bodega externa válida, no variante de otra [QA-2]",
                "filas_afectadas": int(df["Bodega_Origen"].isna().sum())})

    # Ultima_Revision — parse fecha
    df["Ultima_Revision"] = pd.to_datetime(df["Ultima_Revision"], format="%Y-%m-%d")
    log.append({"columna": "Ultima_Revision", "problema": "Tipo object",
                "accion": "pd.to_datetime con formato ISO",
                "justificacion": "100% formato ISO, sin nulos",
                "filas_afectadas": 0})

    return df, log


# ---------------------------------------------------------------------------
# LIMPIEZA TRANSACCIONES [FASE 1 + QA-2 + QA-4]
# ---------------------------------------------------------------------------

_CIUDAD_MAPA = {
    "BOG": "Bogotá",
    "Bogotá": "Bogotá",
    "MED": "Medellín",
    "Medellín": "Medellín",
    "Cali": "Cali",
    "Barranquilla": "Barranquilla",
    "Bucaramanga": "Bucaramanga",
    "Ventas_Web": None,  # valor fugado, no es ciudad [QA-2]
}


def limpiar_transacciones(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Limpia transacciones_logistica_v2. [FASE 1 + QA-2 + QA-4]"""
    df = df.copy()
    log = []

    # Fecha_Venta
    df["Fecha_Venta"] = pd.to_datetime(df["Fecha_Venta"], format="%d/%m/%Y")
    # Flag fechas futuras [QA-4]
    mask_futuro = df["Fecha_Venta"] > FECHA_CORTE
    df["Fecha_Futura"] = mask_futuro
    log.append({"columna": "Fecha_Venta", "problema": f"{mask_futuro.sum()} fechas posteriores a {FECHA_CORTE.date()}",
                "accion": "pd.to_datetime; flag Fecha_Futura; excluir de series de tiempo",
                "justificacion": f"FECHA_CORTE={FECHA_CORTE.date()} es fin del periodo operativo declarado [QA-4]",
                "filas_afectadas": int(mask_futuro.sum())})

    # Cantidad_Vendida — negativos → NaN → mediana
    mask_neg = df["Cantidad_Vendida"] < 0
    df.loc[mask_neg, "Cantidad_Vendida"] = np.nan
    criterio, valor = _elegir_estadistico(df["Cantidad_Vendida"])
    df["Cantidad_Vendida"] = df["Cantidad_Vendida"].fillna(valor)
    log.append({"columna": "Cantidad_Vendida", "problema": f"{mask_neg.sum()} valores negativos",
                "accion": f"Negativos → NaN (no abs(): no confirmadas como devoluciones); imputar {criterio} ({valor:.2f})",
                "justificacion": "Valores negativos son imposibles en cantidad vendida",
                "filas_afectadas": int(mask_neg.sum())})

    # Ciudad_Destino — mapeo canónico [QA-2]
    mask_invalida = df["Ciudad_Destino"] == "Ventas_Web"
    df["Ciudad_Invalida"] = mask_invalida
    df["Ciudad_Destino"] = df["Ciudad_Destino"].map(_CIUDAD_MAPA)
    log.append({"columna": "Ciudad_Destino", "problema": f"'BOG', 'MED', 'Ventas_Web' ({mask_invalida.sum()} filas)",
                "accion": "Mapeo canónico; 'Ventas_Web' → NaN + flag Ciudad_Invalida",
                "justificacion": "'Ventas_Web' es valor fugado de Canal_Venta, no es ciudad [QA-2]",
                "filas_afectadas": int(mask_invalida.sum())})

    # Costo_Envio — imputar mediana por Ciudad_Destino
    n_nulos = df["Costo_Envio"].isna().sum()
    df["Costo_Envio"] = df.groupby("Ciudad_Destino")["Costo_Envio"].transform(
        lambda x: x.fillna(x.median())
    )
    # Si quedan NaN (ciudad NaN), imputar mediana global
    global_med = df["Costo_Envio"].median()
    df["Costo_Envio"] = df["Costo_Envio"].fillna(global_med)
    log.append({"columna": "Costo_Envio", "problema": f"{n_nulos} nulos (8.3%)",
                "accion": "Imputar mediana por Ciudad_Destino; resto con mediana global",
                "justificacion": "El costo de envío varía por ciudad; mediana por ser asimétrico",
                "filas_afectadas": int(n_nulos)})

    # Tiempo_Entrega_Real — centinela 999 → NaN → mediana por ciudad
    mask_999 = df["Tiempo_Entrega_Real"] == 999
    df.loc[mask_999, "Tiempo_Entrega_Real"] = np.nan
    df["Tiempo_Entrega_Real"] = df.groupby("Ciudad_Destino")["Tiempo_Entrega_Real"].transform(
        lambda x: x.fillna(x.median())
    )
    global_med_te = df["Tiempo_Entrega_Real"].median()
    df["Tiempo_Entrega_Real"] = df["Tiempo_Entrega_Real"].fillna(global_med_te)
    log.append({"columna": "Tiempo_Entrega_Real", "problema": f"{mask_999.sum()} valores centinela 999",
                "accion": "999 → NaN; imputar mediana por ciudad vía groupby().transform()",
                "justificacion": "999 es error de sistema (centinela), no outlier real",
                "filas_afectadas": int(mask_999.sum())})

    # Estado_Envio — nulos → "Desconocido"
    n_nulos_estado = df["Estado_Envio"].isna().sum()
    df["Estado_Envio"] = df["Estado_Envio"].fillna("Desconocido")
    log.append({"columna": "Estado_Envio", "problema": f"{n_nulos_estado} nulos (16.8%)",
                "accion": "Nulos → 'Desconocido' (categoría explícita)",
                "justificacion": "Imputar moda perdería información: el nulo puede ser falla de sistema [Decisión Ética]",
                "filas_afectadas": int(n_nulos_estado)})

    return df, log


# ---------------------------------------------------------------------------
# LIMPIEZA FEEDBACK [FASE 1]
# ---------------------------------------------------------------------------

_RECOMIENDA_MAPA = {"SI": True, "NO": False, "Maybe": None}
_TICKET_MAPA = {"Sí": True, "No": False, "1": True, "0": False, 1: True, 0: False}


def limpiar_feedback(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Limpia feedback_clientes_v2. [FASE 1]"""
    df = df.copy()
    log = []

    # Feedback_ID — colisión de llave (500 IDs duplicados con datos distintos) → renumerar
    n_dup_ids = int(df["Feedback_ID"].duplicated().sum())
    df = df.reset_index(drop=True)
    df["Feedback_ID"] = df.index + 1
    log.append({"columna": "Feedback_ID", "problema": f"{n_dup_ids} IDs duplicados con datos distintos (colisión de llave)",
                "accion": "Renumerar secuencialmente; conservar todas las filas",
                "justificacion": "0 filas 100% idénticas → son opiniones distintas [QA-1] política: marcar sobre eliminar",
                "filas_afectadas": n_dup_ids})

    # Rating_Producto — valor 99 (imposible) → NaN → mediana ordinal
    mask_99 = df["Rating_Producto"] > 5
    df.loc[mask_99, "Rating_Producto"] = np.nan
    med_rating = df["Rating_Producto"].median()
    df["Rating_Producto"] = df["Rating_Producto"].fillna(med_rating)
    log.append({"columna": "Rating_Producto", "problema": f"{mask_99.sum()} valores > 5 (ej: 99)",
                "accion": f">5 → NaN; imputar mediana ordinal ({med_rating})",
                "justificacion": "Variable ordinal 1-5; mediana conserva orden sin suponer continuidad [Decisión Ética]",
                "filas_afectadas": int(mask_99.sum())})

    # Comentario_Texto — '---' → NaN
    mask_dash = df["Comentario_Texto"] == "---"
    df.loc[mask_dash, "Comentario_Texto"] = np.nan
    log.append({"columna": "Comentario_Texto", "problema": f"{mask_dash.sum()} valores '---' (nulo disfrazado)",
                "accion": "'---' → NaN",
                "justificacion": "'---' es nulo disfrazado; no imputar texto libre",
                "filas_afectadas": int(mask_dash.sum())})

    # Recomienda_Marca — SI/NO/Maybe → bool/NaN
    df["Recomienda_Marca"] = df["Recomienda_Marca"].map(_RECOMIENDA_MAPA)
    log.append({"columna": "Recomienda_Marca", "problema": "SI/NO/Maybe + nulos",
                "accion": "SI→True, NO→False, Maybe→NaN; nulos conservados",
                "justificacion": "'Maybe' es respuesta ambigua; no imputar booleano [Decisión Ética]",
                "filas_afectadas": int(df["Recomienda_Marca"].isna().sum())})

    # Ticket_Soporte_Abierto — idiomas + tipos → bool
    df["Ticket_Soporte_Abierto"] = df["Ticket_Soporte_Abierto"].map(_TICKET_MAPA)
    log.append({"columna": "Ticket_Soporte_Abierto", "problema": "Mezcla 'Sí','No','1','0'",
                "accion": "Mapeo explícito a booleano",
                "justificacion": "Normalización por diccionario [QA-2]",
                "filas_afectadas": 0})

    # Edad_Cliente — >100 → NaN → mediana
    mask_edad = df["Edad_Cliente"] > 100
    df.loc[mask_edad, "Edad_Cliente"] = np.nan
    criterio_e, valor_e = _elegir_estadistico(df["Edad_Cliente"])
    df["Edad_Cliente"] = df["Edad_Cliente"].fillna(valor_e)
    log.append({"columna": "Edad_Cliente", "problema": f"{mask_edad.sum()} edades > 100 (máx 195)",
                "accion": f">100 → NaN; imputar {criterio_e} ({valor_e:.1f})",
                "justificacion": "Edades biológicamente imposibles; distribución asimétrica → mediana",
                "filas_afectadas": int(mask_edad.sum())})

    # Satisfaccion_NPS — derivar segmento
    df["Segmento_NPS"] = pd.cut(
        df["Satisfaccion_NPS"],
        bins=[-100.1, -0.001, 50, 100],
        labels=["Detractor", "Pasivo", "Promotor"]
    )
    log.append({"columna": "Satisfaccion_NPS", "problema": "Escala continua -100..100 no interpretable directamente",
                "accion": "Derivar Segmento_NPS: Detractor <0, Pasivo 0-50, Promotor >50",
                "justificacion": "Normalización para junta directiva; la escala continua se conserva",
                "filas_afectadas": 0})

    return df, log
