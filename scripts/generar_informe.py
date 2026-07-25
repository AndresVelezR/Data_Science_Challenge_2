"""Genera docs/Informe_Hallazgos.pdf con ReportLab. [E2]

Uso:
    python scripts/generar_informe.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.carga import cargar_crudos
from src.limpieza import (
    auditar,
    comparar_salud,
    limpiar_feedback,
    limpiar_inventario,
    limpiar_transacciones,
)
from src.integracion import agregar_variables_derivadas, construir_maestro
from src.analisis import (
    p1_fuga_capital,
    p2_crisis_logistica,
    p3_venta_invisible,
    p4_diagnostico_fidelidad,
    p5_riesgo_operativo,
)
from src.graficos import (
    fig_p1_fuga,
    fig_p2_correlacion,
    fig_p3_fantasma,
    fig_p4_cuadrante,
    fig_p5_riesgo,
)

# ---------------------------------------------------------------------------
# Directorios de salida
# ---------------------------------------------------------------------------
DOCS_IMG = ROOT / "docs" / "img"
DOCS_IMG.mkdir(parents=True, exist_ok=True)
PDF_SALIDA = ROOT / "docs" / "Informe_Hallazgos.pdf"


def _exportar_fig(fig, nombre: str) -> Path:
    """Exporta figura Plotly a PNG con kaleido."""
    ruta = DOCS_IMG / nombre
    fig.write_image(str(ruta), width=900, height=500)
    return ruta


def _tabla_rl(data: list[list], col_widths=None) -> Table:
    """Genera tabla ReportLab con estilo corporativo."""
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3D7A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def main():
    print("Cargando datos y ejecutando pipeline...")
    crudos = cargar_crudos()
    inv_l, _ = limpiar_inventario(crudos["inventario"])
    trx_l, _ = limpiar_transacciones(crudos["transacciones"])
    fb_l, _ = limpiar_feedback(crudos["feedback"])

    audit_antes = {n: auditar(crudos[n], n) for n in ["inventario", "transacciones", "feedback"]}
    audit_despues = {
        "inventario": auditar(inv_l, "inventario"),
        "transacciones": auditar(trx_l, "transacciones"),
        "feedback": auditar(fb_l, "feedback"),
    }
    df_comp = comparar_salud(audit_antes, audit_despues)

    maestro = construir_maestro(inv_l, trx_l, fb_l)
    maestro = agregar_variables_derivadas(maestro, inv_l)

    _, c1 = p1_fuga_capital(maestro)
    df2, c2 = p2_crisis_logistica(maestro)
    df3, c3 = p3_venta_invisible(maestro)
    df4, c4 = p4_diagnostico_fidelidad(maestro)
    df5, c5 = p5_riesgo_operativo(maestro)

    print("Exportando figuras...")
    df1, _ = p1_fuga_capital(maestro)
    img_p1 = _exportar_fig(fig_p1_fuga(df1), "p1_fuga.png")
    img_p2 = _exportar_fig(fig_p2_correlacion(df2), "p2_correlacion.png")
    img_p3 = _exportar_fig(fig_p3_fantasma(pd.DataFrame(c3.get("por_ciudad", []))), "p3_fantasma.png")
    img_p4 = _exportar_fig(fig_p4_cuadrante(df4), "p4_cuadrante.png")
    img_p5 = _exportar_fig(fig_p5_riesgo(df5), "p5_riesgo.png")

    print("Generando PDF...")
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle("titulo", parent=estilos["Title"], fontSize=22, spaceAfter=6, textColor=colors.HexColor("#1F3D7A"))
    h1 = ParagraphStyle("h1", parent=estilos["Heading1"], fontSize=14, spaceAfter=4, textColor=colors.HexColor("#1F3D7A"))
    h2 = ParagraphStyle("h2", parent=estilos["Heading2"], fontSize=11, spaceAfter=3)
    cuerpo = ParagraphStyle("cuerpo", parent=estilos["Normal"], fontSize=9, leading=14, spaceAfter=6)
    pie = ParagraphStyle("pie", parent=estilos["Normal"], fontSize=7, textColor=colors.grey)

    doc = SimpleDocTemplate(str(PDF_SALIDA), pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2.5*cm, bottomMargin=2.5*cm)
    story = []

    # ---- PORTADA ----
    story += [
        Spacer(1, 3*cm),
        Paragraph("TechLogistics S.A.S.", titulo),
        Paragraph("Informe de Hallazgos Operacionales", estilos["Heading1"]),
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1F3D7A")),
        Spacer(1, 0.5*cm),
        Paragraph("Autor: Andrés Vélez R.", cuerpo),
        Paragraph("Curso: Ciencia de Datos", cuerpo),
        Paragraph("Fecha: Julio 2026", cuerpo),
        PageBreak(),
    ]

    # ---- RESUMEN EJECUTIVO ----
    story += [
        Paragraph("Resumen Ejecutivo", h1),
        HRFlowable(width="100%", thickness=1, color=colors.lightgrey),
        Spacer(1, 0.3*cm),
        Paragraph(
            f"TechLogistics opera con una fuga de capital de <b>${abs(c1.get('perdida_total_usd', 0)):,.0f} USD</b> "
            f"acumulada en {c1.get('n_skus_negativos', 0)} SKUs con margen negativo, "
            f"equivalente al {c1.get('pct_del_ingreso', 0):.1f}% del ingreso bruto. "
            "Esta pérdida no es marginal: supera el umbral de corrección urgente y apunta a una falla "
            "estructural de fijación de precios o de gestión de costos de envío.",
            cuerpo
        ),
        Paragraph(
            f"Paralelamente, el {c3.get('pct_ingreso_total', 0):.1f}% del ingreso "
            f"(${c3.get('ingreso_fantasma_usd', 0):,.0f} USD) proviene de SKUs que no existen en el catálogo ERP. "
            "La hipótesis más probable es un catálogo desactualizado —productos nuevos que se venden antes de ser "
            "registrados— lo que genera ingresos invisibles para el sistema contable y dificulta la planificación de inventario.",
            cuerpo
        ),
        Paragraph(
            f"En logística, la zona {c2.get('zona_intervenir', 'N/A')} muestra la correlación más negativa "
            f"entre tiempo de entrega y satisfacción del cliente (r = {c2.get('correlacion_peor', 0):.3f}). "
            "Intervenir esta ruta tiene impacto directo en el NPS y en la tasa de tickets de soporte.",
            cuerpo
        ),
        PageBreak(),
    ]

    # ---- ESTADO DE LOS DATOS ----
    story += [
        Paragraph("Estado de los Datos — Health Score [F1.2]", h1),
        HRFlowable(width="100%", thickness=1, color=colors.lightgrey),
        Spacer(1, 0.3*cm),
    ]
    hs_data = [["Dataset", "Health Score Antes", "Health Score Después", "Delta"]]
    for _, row in df_comp.iterrows():
        hs_data.append([row["Dataset"], f"{row['Health Score Antes']:.1f}", f"{row['Health Score Después']:.1f}", f"+{row['Delta']:.2f}"])
    story.append(_tabla_rl(hs_data, [4*cm, 3.5*cm, 3.5*cm, 2.5*cm]))
    story += [
        Spacer(1, 0.3*cm),
        Paragraph(
            "La limpieza aplicó mapeos canónicos explícitos (nunca transformaciones automáticas de texto), "
            "imputación con mediana para distribuciones asimétricas, y conservó todas las filas con flags "
            "en lugar de eliminarlas —política de 'marcar sobre eliminar' para preservar trazabilidad.",
            cuerpo
        ),
        PageBreak(),
    ]

    # ---- HALLAZGOS P1–P5 ----
    hallazgos = [
        ("P1 — Fuga de Capital", img_p1,
         f"<b>{c1.get('n_skus_negativos',0)} SKUs</b> acumulan pérdidas por <b>${abs(c1.get('perdida_total_usd',0)):,.0f} USD</b>. "
         f"Tipo de falla: {c1.get('tipo_falla','N/A')}. Canal más afectado: {c1.get('canal_peor','N/A')}.",
         "[P1]"),
        ("P2 — Crisis Logística", img_p2,
         f"Zona crítica: <b>{c2.get('zona_intervenir','N/A')}</b> (r={c2.get('correlacion_peor',0):.3f}, p={c2.get('p_valor_peor',0):.4f}). "
         f"{c2.get('grupos_significativos',0)} de {c2.get('n_grupos_analizados',0)} rutas muestran correlación negativa significativa.",
         "[P2]"),
        ("P3 — Venta Invisible", img_p3,
         f"<b>${c3.get('ingreso_fantasma_usd',0):,.0f} USD</b> ({c3.get('pct_ingreso_total',0):.1f}% del ingreso total) "
         f"provienen de {c3.get('n_transacciones_fantasma',0)} transacciones de SKUs no catalogados.",
         "[P3]"),
        ("P4 — Diagnóstico de Fidelidad", img_p4,
         f"Categorías en cuadrante crítico (stock alto + NPS negativo): <b>{', '.join(c4.get('categorias_problema',[]) or ['ninguna'])}</b>. "
         f"Causa probable: {c4.get('causa_dominante','N/A')}.",
         "[P4]"),
        ("P5 — Riesgo Operativo", img_p5,
         f"Bodegas de alto riesgo: <b>{', '.join(c5.get('bodegas_a_ciegas',[]) or ['ninguna'])}</b>. "
         f"Tendencia OLS: pendiente {c5.get('pendiente_ols',0):.6f}. {c5.get('interpretacion','')}",
         "[P5]"),
    ]

    for ttl, img_path, texto, tag in hallazgos:
        story.append(Paragraph(ttl, h1))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
        story.append(Spacer(1, 0.2*cm))
        if img_path.exists():
            story.append(Image(str(img_path), width=15*cm, height=8*cm))
        story.append(Paragraph(texto, cuerpo))
        story.append(Paragraph(f"Tag de trazabilidad: {tag}", pie))
        story.append(Spacer(1, 0.5*cm))

    story.append(PageBreak())

    # ---- PLAN DE ACCIÓN ----
    story += [
        Paragraph("Plan de Acción — Recomendaciones Priorizadas", h1),
        HRFlowable(width="100%", thickness=1, color=colors.lightgrey),
        Spacer(1, 0.3*cm),
        Paragraph("<b>1. [ALTA complejidad] Auditoría de precios en SKUs con margen negativo</b>", h2),
        Paragraph(
            f"Revisar la estructura de costos de los {c1.get('n_skus_negativos',0)} SKUs deficitarios. "
            f"Impacto estimado: recuperar hasta ${abs(c1.get('perdida_total_usd',0)):,.0f} USD anuales. "
            "Plazo: 60 días.",
            cuerpo
        ),
        Paragraph("<b>2. [MEDIA complejidad] Sincronización ERP-Catálogo para SKUs fantasma</b>", h2),
        Paragraph(
            f"Implementar un proceso de registro acelerado para productos nuevos. "
            f"Actualmente el {c3.get('pct_ingreso_total',0):.1f}% del ingreso es invisible al ERP. "
            "Impacto: trazabilidad contable completa. Plazo: 30 días.",
            cuerpo
        ),
        Paragraph(f"<b>3. [BAJA complejidad] Intervención logística en {c2.get('zona_intervenir','la ruta crítica')}</b>", h2),
        Paragraph(
            f"Renegociar SLA con el proveedor logístico de esta ruta o reasignar la bodega de origen. "
            f"Correlación entrega-NPS de {c2.get('correlacion_peor',0):.3f} indica que mejorar 1 día de entrega "
            "tiene impacto medible en la satisfacción. Plazo: 15 días.",
            cuerpo
        ),
    ]

    doc.build(story)
    print(f"\n✅ Informe generado en: {PDF_SALIDA}")
    print("\n⚠️  Reemplaza docs/img/*.png por capturas reales del dashboard desplegado")
    print("   si quieres cumplir literalmente el requisito de 4 capturas de pantalla.")


if __name__ == "__main__":
    main()
