# TechLogistics S.A.S. — Dashboard Operacional de Datos

## Problema de negocio

TechLogistics S.A.S. opera la distribución de tecnología en Colombia. La compañía enfrenta tres retos simultáneos que están erosionando su rentabilidad:

1. **Fuga de capital silenciosa**: SKUs con margen negativo que generan volumen pero destruyen utilidad.
2. **Crisis logística invisible**: rutas donde el incumplimiento de tiempos de entrega destruye la satisfacción del cliente (NPS).
3. **Catálogo desactualizado**: el 17.5% de las ventas corresponde a SKUs que no existen en el inventario registrado, representando ingresos que el ERP no puede rastrear.

Este proyecto construye una fuente única de verdad integrando inventario, transacciones y feedback de clientes, y expone hallazgos accionables a través de un dashboard interactivo.

---

## Guía de instalación reproducible

```bash
# 1. Clonar el repositorio
git clone git@github.com:AndresVelezR/Data_Science_Challenge_2.git
cd Data_Science_Challenge_2

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate   # Linux / Mac
# .venv\Scripts\activate    # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar API key de Groq (opcional, la app funciona sin ella)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edita .streamlit/secrets.toml y agrega tu GROQ_API_KEY

# 5. Lanzar el dashboard
streamlit run app.py
```

### Configurar GROQ_API_KEY

| Entorno | Método |
|---|---|
| **Local** | Crea `.streamlit/secrets.toml` copiando el `.example`, o exporta `export GROQ_API_KEY=gsk_...` |
| **Streamlit Cloud** | Ve a tu app → Settings → Secrets → agrega `GROQ_API_KEY = "gsk_..."` |

**App desplegada:** <URL_STREAMLIT_CLOUD>

---

## Matriz de trazabilidad de requisitos [3.3]

| Requisito (fuente) | Tag | Dónde está implementado |
|---|---|---|
| Fase 1 · Health Score antes/después | `[F1.2]` | `src/limpieza.py::calcular_health_score` · app → pestaña Auditoría |
| Fase 1 · % nulidad por columna | `[F1.1]` | `src/limpieza.py::auditar` · pestaña Auditoría |
| Fase 1 · Decisión ética media/mediana/moda | `[F1.4]` | `src/limpieza.py::_elegir_estadistico` + `log_decisiones` · reporte descargable |
| Fase 2 · Merge estratégico (SSOT) | `[F2.2]` | `src/integracion.py::construir_maestro` |
| Fase 2 · Dilema SKU fantasma | `[F2.3]` | `src/integracion.py` · pestaña Operaciones (P3) |
| Fase 2 · ≥3 variables derivadas | `[F2.4]` | `src/integracion.py::agregar_variables_derivadas` (6 variables) |
| Fase 3 · IA Groq (Llama-3) | `[F3]` | `src/ia.py` · pestaña Insights de IA |
| Pregunta 1 · Fuga de capital | `[P1]` | `src/analisis.py::p1_fuga_capital` · pestaña Operaciones |
| Pregunta 2 · Crisis logística | `[P2]` | `src/analisis.py::p2_crisis_logistica` · pestaña Cliente |
| Pregunta 3 · Venta invisible | `[P3]` | `src/analisis.py::p3_venta_invisible` · pestaña Operaciones |
| Pregunta 4 · Diagnóstico de fidelidad | `[P4]` | `src/analisis.py::p4_diagnostico_fidelidad` · pestaña Cliente |
| Pregunta 5 · Riesgo operativo | `[P5]` | `src/analisis.py::p5_riesgo_operativo` · pestaña Cliente |
| QA · Trazabilidad de ingresos | `[QA-1]` | `src/integracion.py::verificar_trazabilidad` · pestaña Auditoría |
| QA · Normalización categórica | `[QA-2]` | `src/limpieza.py` mapeos `_CAT_INVENTARIO`, `_BODEGA_MAPA`, `_CIUDAD_MAPA` · sidebar |
| QA · Outliers de costo IQR | `[QA-3]` | `src/limpieza.py::marcar_outliers_iqr` · toggle sidebar + expander Auditoría |
| QA · Fechas futuras | `[QA-4]` | `src/limpieza.py` flag `Fecha_Futura` · pestaña Auditoría |
| Entregable · Reporte de limpieza descargable | `[E1]` | pestaña Auditoría · `st.download_button` |
| Entregable · Informe PDF | `[E2]` | `scripts/generar_informe.py` → `docs/Informe_Hallazgos.pdf` |
| Entregable · Gestión de secretos | `[E3]` | `src/ia.py::obtener_api_key` · `.streamlit/secrets.toml.example` |

---

## Discrepancias detectadas en el diccionario de datos

El diccionario oficial (`Lecture_02_dictionary.pdf`) contiene las siguientes discrepancias respecto a los CSV reales:

| Diccionario dice | CSV real contiene | Impacto |
|---|---|---|
| `Tiempo_Entrega` | `Tiempo_Entrega_Real` | Nombre distinto — el código usa el nombre real |
| `Ticket_Soporte` | `Ticket_Soporte_Abierto` | Nombre distinto — el código usa el nombre real |
| *(no mencionado)* | `Canal_Venta` | Columna presente en datos pero ausente en el diccionario |

Estas discrepancias sugieren que el diccionario corresponde a una versión anterior del esquema de datos.

---

## Fórmula del Health Score [F1.2]

```
Completitud = 100 × (1 − celdas_nulas / celdas_totales)
Unicidad    = 100 × (1 − filas_o_ids_duplicados / filas_totales)
Validez     = 100 × (1 − celdas_con_valor_imposible / celdas_totales)
Health Score = 0.40·Completitud + 0.20·Unicidad + 0.40·Validez
```

Los pesos priorizan completitud (40%) y validez (40%) porque son las dimensiones que sesgan los KPIs financieros. La unicidad recibe el 20% restante porque aquí es un problema de trazabilidad, no de magnitud.

---

*Autor: Andrés Vélez R. — Ciencia de Datos — 2026*
