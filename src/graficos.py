"""Figuras Plotly reutilizables para app e informe. [FASE 2 / RETO P1-P5]"""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def fig_health_score(df_comparacion: pd.DataFrame) -> go.Figure:
    """Barras agrupadas Antes vs Después por dataset."""
    fig = go.Figure()
    for col, color in [("Health Score Antes", "#EF553B"), ("Health Score Después", "#00CC96")]:
        fig.add_trace(go.Bar(
            name=col.replace("Health Score ", ""),
            x=df_comparacion["Dataset"],
            y=df_comparacion[col],
            marker_color=color,
        ))
    fig.update_layout(
        barmode="group",
        yaxis=dict(range=[0, 105], title="Health Score"),
        xaxis_title="Dataset",
        legend_title="",
    )
    return fig


def fig_nulos_heatmap(auditoria: dict) -> go.Figure:
    """Mapa de calor de % nulos por columna."""
    pcts = auditoria["pct_nulos_por_columna"]
    df = pd.DataFrame({"Columna": list(pcts.keys()), "% Nulos": list(pcts.values())})
    df = df.sort_values("% Nulos", ascending=True)
    fig = px.bar(df, x="% Nulos", y="Columna", orientation="h",
                 color="% Nulos", color_continuous_scale="Blues",
                 labels={"% Nulos": "% Nulos / Disfrazados"})
    fig.update_layout(coloraxis_showscale=False)
    return fig


def fig_p1_fuga(df_skus: pd.DataFrame) -> go.Figure:
    """Top 20 SKUs con mayor fuga de capital. [P1]"""
    if df_skus.empty:
        return go.Figure()
    top = df_skus.nsmallest(20, "Margen_Total")
    fig = px.bar(
        top, x="Margen_Total", y="SKU_ID", orientation="h",
        color="Margen_Total", color_continuous_scale="RdYlGn",
        labels={"Margen_Total": "Margen Total (USD)", "SKU_ID": "SKU"},
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    return fig


def fig_p1_canal(df_canal: pd.DataFrame) -> go.Figure:
    """Margen % por canal de venta. [P1]"""
    if df_canal.empty:
        return go.Figure()
    fig = px.bar(
        df_canal.sort_values("Margen_Pct"),
        x="Canal_Venta", y="Margen_Pct",
        color="Margen_Pct", color_continuous_scale="RdYlGn",
        labels={"Margen_Pct": "Margen %", "Canal_Venta": "Canal"},
    )
    return fig


def fig_p2_correlacion(df_corr: pd.DataFrame) -> go.Figure:
    """Heatmap ciudad × bodega coloreado por correlación. [P2]"""
    if df_corr.empty:
        return go.Figure()
    pivot = df_corr.pivot_table(index="Ciudad", columns="Bodega", values="Correlacion")
    fig = px.imshow(
        pivot, color_continuous_scale="RdYlGn",
        labels={"color": "r Pearson"},
        zmin=-1, zmax=1,
    )
    return fig


def fig_p3_fantasma(por_ciudad: pd.DataFrame) -> go.Figure:
    """Ingresos de SKUs fantasma por ciudad. [P3]"""
    if por_ciudad.empty:
        return go.Figure()
    fig = px.bar(
        por_ciudad, x="Ciudad_Destino", y="Ingreso",
        color="Ingreso", color_continuous_scale="Viridis",
        labels={"Ingreso": "Ingreso USD", "Ciudad_Destino": "Ciudad"},
    )
    return fig


def fig_p4_cuadrante(resumen: pd.DataFrame) -> go.Figure:
    """Scatter NPS vs Margen por categoría. [P4]"""
    if resumen.empty:
        return go.Figure()
    fig = px.scatter(
        resumen, x="Margen_Pct_Prom", y="NPS_Prom",
        text="Categoria", color="Cuadrante",
        color_discrete_map={"Normal": "#00CC96", "⚠ Stock Alto + NPS Negativo": "#EF553B"},
        size="Stock_Prom", size_max=40,
        labels={"Margen_Pct_Prom": "Margen %", "NPS_Prom": "NPS Promedio"},
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_traces(textposition="top center")
    return fig


def fig_p5_riesgo(resumen: pd.DataFrame) -> go.Figure:
    """Scatter días vs tasa soporte con OLS. [P5]"""
    if resumen.empty:
        return go.Figure()
    fig = px.scatter(
        resumen, x="Dias_Prom", y="Tasa_Soporte",
        text="Bodega_Origen", color="Nivel_Riesgo",
        color_discrete_map={"Normal": "#00CC96", "Alto": "#EF553B"},
        labels={"Dias_Prom": "Días Promedio sin Revisión", "Tasa_Soporte": "Tasa Tickets Soporte"},
    )
    if "Tendencia_OLS" in resumen.columns:
        ordenado = resumen.sort_values("Dias_Prom")
        fig.add_trace(go.Scatter(
            x=ordenado["Dias_Prom"], y=ordenado["Tendencia_OLS"],
            mode="lines", name="Tendencia OLS",
            line=dict(dash="dash", color="gray"),
        ))
    fig.update_traces(textposition="top center", selector=dict(mode="markers+text"))
    return fig
