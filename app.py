"""Dashboard TechLogistics S.A.S. — UI Streamlit. [Checklist 3.1]"""
import pandas as pd
import streamlit as st

from src.carga import cargar_crudos
from src.limpieza import (
    FECHA_CORTE,
    auditar,
    comparar_salud,
    limpiar_feedback,
    limpiar_inventario,
    limpiar_transacciones,
    marcar_outliers_iqr,
)
from src.integracion import (
    agregar_variables_derivadas,
    construir_maestro,
    verificar_trazabilidad,
)
from src.analisis import (
    p1_fuga_capital,
    p2_crisis_logistica,
    p3_venta_invisible,
    p4_diagnostico_fidelidad,
    p5_riesgo_operativo,
)
from src.graficos import (
    fig_health_score,
    fig_nulos_heatmap,
    fig_p1_canal,
    fig_p1_fuga,
    fig_p2_correlacion,
    fig_p3_fantasma,
    fig_p4_cuadrante,
    fig_p5_riesgo,
)
from src.ia import mostrar_seccion_ia

st.set_page_config(
    page_title="TechLogistics · Dashboard Operacional",
    page_icon="📦",
    layout="wide",
)


# ---------------------------------------------------------------------------
# CARGA Y LIMPIEZA (con caché)
# ---------------------------------------------------------------------------

@st.cache_data
def pipeline_limpieza():
    crudos = cargar_crudos()
    inv_l, log_inv = limpiar_inventario(crudos["inventario"])
    trx_l, log_trx = limpiar_transacciones(crudos["transacciones"])
    fb_l, log_fb = limpiar_feedback(crudos["feedback"])

    audit_antes = {
        "inventario": auditar(crudos["inventario"], "inventario"),
        "transacciones": auditar(crudos["transacciones"], "transacciones"),
        "feedback": auditar(crudos["feedback"], "feedback"),
    }
    audit_despues = {
        "inventario": auditar(inv_l, "inventario"),
        "transacciones": auditar(trx_l, "transacciones"),
        "feedback": auditar(fb_l, "feedback"),
    }

    maestro_base = construir_maestro(inv_l, trx_l, fb_l)
    maestro_base = agregar_variables_derivadas(maestro_base, inv_l)

    trazabilidad = verificar_trazabilidad(crudos["transacciones"], maestro_base)
    log_total = log_inv + log_trx + log_fb

    return (
        crudos, inv_l, trx_l, fb_l,
        audit_antes, audit_despues,
        maestro_base, trazabilidad, log_total,
    )


(crudos, inv_l, trx_l, fb_l,
 audit_antes, audit_despues,
 maestro_base, trazabilidad, log_total) = pipeline_limpieza()

# ---------------------------------------------------------------------------
# SIDEBAR [3.1-a]
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("⚙️ Filtros")

    fecha_min = maestro_base["Fecha_Venta"].min().date()
    fecha_max_default = FECHA_CORTE.date()
    rango_fechas = st.date_input(
        "Rango de fechas",
        value=(fecha_min, fecha_max_default),
        min_value=fecha_min,
        max_value=maestro_base["Fecha_Venta"].max().date(),
    )

    opciones_cat = sorted(maestro_base["Categoria"].dropna().unique())
    categorias = st.multiselect("Categoría", opciones_cat, default=opciones_cat)

    opciones_bod = sorted(maestro_base["Bodega_Origen"].dropna().unique())
    bodegas = st.multiselect("Bodega Origen", opciones_bod, default=opciones_bod)

    # QA-2: debe mostrar exactamente 5 ciudades
    opciones_ciudad = sorted(maestro_base["Ciudad_Destino"].dropna().unique())
    ciudades = st.multiselect("Ciudad Destino", opciones_ciudad, default=opciones_ciudad)

    opciones_canal = sorted(maestro_base["Canal_Venta"].dropna().unique())
    canales = st.multiselect("Canal de Venta", opciones_canal, default=opciones_canal)

    excluir_outliers = st.toggle("Excluir outliers de costo (IQR)", value=True)
    incluir_fantasmas = st.toggle("Incluir SKUs fantasma en el margen", value=True)

    if st.button("🔄 Refrescar Análisis"):
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------------------------------
# APLICAR FILTROS
# ---------------------------------------------------------------------------

def aplicar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if len(rango_fechas) == 2:
        f0 = pd.Timestamp(rango_fechas[0])
        f1 = pd.Timestamp(rango_fechas[1])
        df = df[(df["Fecha_Venta"] >= f0) & (df["Fecha_Venta"] <= f1)]
    if categorias:
        df = df[df["Categoria"].isin(categorias)]
    if bodegas:
        df = df[df["Bodega_Origen"].isin(bodegas)]
    if ciudades:
        df = df[df["Ciudad_Destino"].isin(ciudades)]
    if canales:
        df = df[df["Canal_Venta"].isin(canales)]
    if excluir_outliers and "Outlier_Costo" in df.columns:
        df = df[~df["Outlier_Costo"].astype(bool)]
    if not incluir_fantasmas and "Es_SKU_Fantasma" in df.columns:
        df = df[~df["Es_SKU_Fantasma"]]
    return df


maestro = aplicar_filtros(maestro_base)

if maestro.empty:
    st.warning("⚠️ Los filtros actuales no devuelven datos. Ajusta los filtros del sidebar.")
    st.stop()

# ---------------------------------------------------------------------------
# PESTAÑAS [3.1-c]
# ---------------------------------------------------------------------------

tab_auditoria, tab_operaciones, tab_cliente, tab_ia = st.tabs([
    "🔍 Auditoría",
    "📦 Operaciones",
    "👤 Cliente",
    "🤖 Insights de IA",
])

# ======================== PESTAÑA 1: AUDITORÍA ========================

with tab_auditoria:
    st.header("🔍 Auditoría de Calidad de Datos")
    st.write(
        "Esta sección muestra el estado de los datos antes y después de la limpieza. "
        "El Health Score resume la calidad en una sola cifra ponderada. "
        "Un evaluador puede rastrear cada decisión de limpieza en el reporte descargable."
    )

    df_comp = comparar_salud(audit_antes, audit_despues)
    st.subheader("Health Score Antes vs Después [F1.2]")
    cols = st.columns(3)
    for i, row in df_comp.iterrows():
        cols[i].metric(
            row["Dataset"].capitalize(),
            f"{row['Health Score Después']:.1f}",
            delta=f"+{row['Delta']:.2f}",
        )
    st.caption("[F1.2] Health Score = 0.40·Completitud + 0.20·Unicidad + 0.40·Validez — pesos priorizan completitud y validez porque son las que sesgan los KPIs financieros")
    st.plotly_chart(fig_health_score(df_comp), width="stretch")

    st.subheader("Porcentaje de Nulos por Columna [F1.1]")
    dataset_sel = st.selectbox("Dataset", ["inventario", "transacciones", "feedback"])
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Antes**")
        st.plotly_chart(fig_nulos_heatmap(audit_antes[dataset_sel]), width="stretch")
    with col_b:
        st.write("**Después**")
        st.plotly_chart(fig_nulos_heatmap(audit_despues[dataset_sel]), width="stretch")

    st.subheader("Duplicados [F1.1]")
    for nombre, aud in audit_antes.items():
        st.write(f"**{nombre}** — Filas exactamente duplicadas: `{aud['filas_duplicadas_exactas']}` | IDs duplicados: `{aud['ids_duplicados']}`")

    fechas_futuras = int(maestro_base["Fecha_Futura"].sum()) if "Fecha_Futura" in maestro_base.columns else 0
    st.info(f"[QA-4] Fechas futuras detectadas (posteriores a {FECHA_CORTE.date()}): **{fechas_futuras}** transacciones — excluidas de series de tiempo.")

    # Trazabilidad de ingresos [QA-1]
    st.subheader("Trazabilidad de Ingresos [QA-1]")
    if trazabilidad["filas_ok"]:
        st.success(f"✅ Filas: {trazabilidad['filas_crudo']:,} → {trazabilidad['filas_maestro']:,} (sin fan-out por merge)")
    else:
        st.error(f"❌ Fan-out detectado: {trazabilidad['filas_crudo']:,} → {trazabilidad['filas_maestro']:,}")
    st.write(f"Ingreso bruto crudo: **${trazabilidad['ingreso_crudo']:,.2f}** USD")
    st.write(f"Ingreso bruto maestro: **${trazabilidad['ingreso_maestro']:,.2f}** USD")
    st.write(f"Delta: **${trazabilidad['delta_usd']:,.2f}** USD — {trazabilidad['explicacion']}")

    # Outliers IQR [QA-3]
    with st.expander("Ver registros excluidos por IQR de costo [QA-3]"):
        mask_outlier, limites = marcar_outliers_iqr(inv_l, "Costo_Unitario_USD")
        df_outliers = inv_l[mask_outlier]
        st.write(f"Límites IQR: {limites} | Registros excluibles: **{len(df_outliers)}**")
        st.dataframe(df_outliers[["SKU_ID", "Categoria", "Costo_Unitario_USD", "Bodega_Origen"]])

    # Reporte descargable [E1]
    st.subheader("Reporte de Limpieza Descargable [E1]")
    df_log = pd.DataFrame(log_total)
    st.download_button(
        label="⬇️ Descargar reporte de limpieza (CSV)",
        data=df_log.to_csv(index=False).encode("utf-8"),
        file_name="reporte_limpieza.csv",
        mime="text/csv",
    )

# ======================== PESTAÑA 2: OPERACIONES ========================

with tab_operaciones:
    st.header("📦 Operaciones y Rentabilidad")
    st.write(
        "Aquí se responden las preguntas P1 y P3: ¿cuánto dinero se está perdiendo y dónde? "
        "¿Cuántas ventas corresponden a productos que no aparecen en el catálogo? "
        "Estos hallazgos tienen impacto directo en el margen de la compañía."
    )

    if maestro.empty:
        st.warning("Sin datos con los filtros actuales.")
    else:
        # P1 — Fuga de capital
        st.subheader("[P1] Fuga de Capital — SKUs con Margen Negativo")
        df_p1, c1 = p1_fuga_capital(maestro)
        if "error" in c1:
            st.warning(c1["error"])
        else:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("SKUs en pérdida", c1["n_skus_negativos"])
            m2.metric("Pérdida total", f"${c1['perdida_total_usd']:,.0f} USD")
            m3.metric("% del ingreso", f"{c1['pct_del_ingreso']:.1f}%")
            m4.metric("Canal más afectado", c1["canal_peor"])
            st.caption(f"[P1] Fuga de capital — Tipo de falla identificada: **{c1['tipo_falla']}**")
            col_l, col_r = st.columns(2)
            with col_l:
                st.plotly_chart(fig_p1_fuga(df_p1), width="stretch")
                st.caption("[P1] Top 20 SKUs con mayor pérdida acumulada")
            with col_r:
                df_canal = pd.DataFrame(c1["tabla_canal"])
                st.plotly_chart(fig_p1_canal(df_canal), width="stretch")
                st.caption("[P1] Margen % por canal de venta — contrasta Online vs otros")

        # P3 — Venta invisible
        st.subheader("[P3] Venta Invisible — SKUs Fantasma")
        df_p3, c3 = p3_venta_invisible(maestro)
        if "error" in c3:
            st.warning(c3["error"])
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric("Ingreso de SKUs fantasma", f"${c3['ingreso_fantasma_usd']:,.0f} USD")
            m2.metric("% del ingreso total", f"{c3['pct_ingreso_total']:.1f}%")
            m3.metric("Transacciones fantasma", c3["n_transacciones_fantasma"])
            st.caption(f"[P3] Hipótesis: {c3['hipotesis']}")
            por_ciudad_p3 = pd.DataFrame(c3["por_ciudad"])
            if not por_ciudad_p3.empty:
                st.plotly_chart(fig_p3_fantasma(por_ciudad_p3), width="stretch")
                st.caption("[P3] Distribución de ingresos de SKUs fantasma por ciudad destino")

# ======================== PESTAÑA 3: CLIENTE ========================

with tab_cliente:
    st.header("👤 Experiencia de Cliente y Riesgo Operativo")
    st.write(
        "Esta sección responde P2, P4 y P5: ¿qué rutas logísticas destruyen la satisfacción del cliente? "
        "¿Qué categorías tienen el stock más alto pero el NPS más bajo? "
        "¿Qué bodegas operan 'a ciegas' y generan más quejas?"
    )

    if maestro.empty:
        st.warning("Sin datos con los filtros actuales.")
    else:
        # P2 — Crisis logística
        st.subheader("[P2] Crisis Logística — Correlación Entrega vs NPS")
        df_p2, c2 = p2_crisis_logistica(maestro)
        if "error" in c2:
            st.warning(c2["error"])
        elif df_p2.empty:
            st.warning("Datos insuficientes para calcular correlaciones significativas (se requieren grupos con n ≥ 30).")
        else:
            m1, m2 = st.columns(2)
            m1.metric("Zona a intervenir", c2["zona_intervenir"])
            m2.metric("Correlación más negativa", f"{c2['correlacion_peor']:.4f}")
            st.caption(f"[P2] Correlación Pearson Tiempo_Entrega_Real vs NPS_Prom — {c2['grupos_significativos']} grupos estadísticamente significativos (p<0.05)")
            st.plotly_chart(fig_p2_correlacion(df_p2), width="stretch")
            st.dataframe(df_p2.sort_values("Correlacion"), width="stretch")

        # P4 — Diagnóstico de fidelidad
        st.subheader("[P4] Diagnóstico de Fidelidad — Stock vs NPS vs Margen")
        df_p4, c4 = p4_diagnostico_fidelidad(maestro)
        if "error" in c4:
            st.warning(c4["error"])
        elif df_p4.empty:
            st.warning("Sin datos suficientes para este análisis.")
        else:
            m1, m2 = st.columns(2)
            m1.metric("Categorías en cuadrante crítico", c4["n_categorias_problema"])
            m2.metric("Causa probable dominante", c4["causa_dominante"])
            st.caption("[P4] Cuadrante crítico: stock por encima de la mediana Y NPS negativo")
            st.plotly_chart(fig_p4_cuadrante(df_p4), width="stretch")

        # P5 — Riesgo operativo
        st.subheader("[P5] Riesgo Operativo — Bodegas 'A Ciegas'")
        df_p5, c5 = p5_riesgo_operativo(maestro)
        if "error" in c5:
            st.warning(c5["error"])
        elif df_p5.empty:
            st.warning("Sin datos suficientes para este análisis.")
        else:
            st.write(f"**{c5['interpretacion']}**")
            if c5["bodegas_a_ciegas"]:
                st.error(f"[P5] Bodegas de alto riesgo: {', '.join(c5['bodegas_a_ciegas'])}")
            st.caption("[P5] Scatter: días promedio sin revisión vs tasa de tickets de soporte. Línea = tendencia OLS (numpy.polyfit)")
            st.plotly_chart(fig_p5_riesgo(df_p5), width="stretch")

# ======================== PESTAÑA 4: IA ========================

with tab_ia:
    conclusiones_analisis = {}
    if not maestro.empty:
        try:
            _, c1 = p1_fuga_capital(maestro)
            _, c3 = p3_venta_invisible(maestro)
            _, c2 = p2_crisis_logistica(maestro)
            _, c4 = p4_diagnostico_fidelidad(maestro)
            _, c5 = p5_riesgo_operativo(maestro)
            conclusiones_analisis = {"P1": c1, "P2": c2, "P3": c3, "P4": c4, "P5": c5}
        except Exception:
            pass
    mostrar_seccion_ia(maestro, conclusiones_analisis)
