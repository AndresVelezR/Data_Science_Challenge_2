# PLAN DE EJECUCIÓN — Challenge 02 · TechLogistics S.A.S.
## Instrucciones para Claude Code

> **Rol:** Eres el implementador. Este documento es el plan completo y ya está decidido.
> **Autonomía:** Ejecuta todo de principio a fin sin pedir confirmación. No preguntes por permisos
> de escritura, de commits ni de decisiones de diseño: todas están tomadas abajo.
> **Filosofía:** Solución más simple que cumpla el requisito. **Prohibida la sobreingeniería**
> (nada de clases abstractas, factories, ORM, tests unitarios exhaustivos, logging estructurado,
> Docker, CI/CD, ni configuración YAML). Funciones puras en módulos planos. Punto.

---

## 0. CONTEXTO DEL ENTORNO

| Ítem | Valor |
|---|---|
| Directorio de trabajo | `/home/andres/Documents/Universidad/ciencia_datos/challenge2` |
| SO | Kali Linux |
| Repositorio remoto | `git@github.com:AndresVelezR/Data_Science_Challenge_2.git` |
| Deploy | Streamlit Community Cloud (conectado al repo de GitHub) |
| Secreto de IA | `GROQ_API_KEY`, ya configurado por el usuario en **Settings → Secrets** de la app en Streamlit Cloud |
| Estado actual del dir | `data/` (3 CSV), `guides/` (3 PDF), `Untitled.ipynb` |

**Nota crítica de deploy:** el código debe funcionar **idéntico en local y en Streamlit Cloud sin
modificarse**. Usa siempre este patrón para el secreto (nunca hardcodear):

```python
import os
import streamlit as st

def obtener_api_key():
    """Lee la key de .env local o de st.secrets en Cloud. Devuelve None si no existe."""
    key = os.getenv("GROQ_API_KEY")
    if key:
        return key
    try:
        return st.secrets.get("GROQ_API_KEY", None)
    except Exception:
        return None
```

Rutas: usa siempre rutas relativas a la raíz del repo construidas con `pathlib.Path(__file__).parent`,
nunca rutas absolutas de `/home/andres/...` (romperían el deploy).

---

## 1. REGLAS DE GIT (OBLIGATORIAS)

1. **Conventional Commits** en cada paso. Formato: `tipo(alcance): descripción en español`.
   Tipos permitidos: `feat`, `fix`, `docs`, `refactor`, `chore`, `style`, `data`.
   Ejemplos: `feat(limpieza): normaliza categorías y bodegas del inventario`,
   `docs(readme): agrega matriz de trazabilidad de requisitos`.
2. **PROHIBIDO** incluir en el mensaje de commit, en el cuerpo, o en el footer:
   - `Co-Authored-By: Claude ...`
   - `🤖 Generated with Claude Code`
   - Cualquier mención a Claude, Anthropic, IA generativa o asistentes.
   Los commits deben verse escritos íntegramente por un humano.
3. **Haz commits sin pedir autorización**, uno por cada bloque numerado de la sección 4 (Roadmap).
4. Al terminar todo: `git push -u origin main` (o `master` si ya existe esa rama).
5. `.gitignore` debe incluir: `.venv/`, `__pycache__/`, `*.pyc`, `.env`, `.streamlit/secrets.toml`,
   `.ipynb_checkpoints/`, `data/processed/*.csv` (los procesados se regeneran).

---

## 2. ESTRUCTURA FINAL DEL WORKSPACE

Reorganiza así (mueve lo existente, no dupliques):

```
challenge2/
├── app.py                        # UI de Streamlit ÚNICAMENTE (sin lógica de limpieza)
├── src/
│   ├── __init__.py
│   ├── carga.py                  # lectura de CSV + caché
│   ├── limpieza.py               # [FASE 1] auditoría + limpieza por dataset
│   ├── integracion.py            # [FASE 2] merge + variables derivadas
│   ├── analisis.py               # [RETO] cálculos de P1..P5
│   ├── graficos.py               # figuras Plotly reutilizables (app + informe)
│   └── ia.py                     # [FASE 3] cliente Groq
├── data/
│   ├── raw/                      # INMUTABLE: los 3 CSV originales van aquí
│   └── processed/                # salidas generadas (gitignored)
├── notebooks/
│   └── 01_auditoria_exploratoria.ipynb    # renombrar/absorber Untitled.ipynb
├── docs/
│   ├── guides/                   # los 3 PDF del enunciado (mover desde guides/)
│   ├── img/                      # figuras exportadas para el informe
│   └── Informe_Hallazgos.pdf     # entregable generado
├── scripts/
│   └── generar_informe.py        # genera docs/Informe_Hallazgos.pdf
├── .streamlit/
│   └── secrets.toml.example      # plantilla, SIN la key real
├── requirements.txt
├── README.md
└── .gitignore
```

`requirements.txt` — usa rangos `>=`, **no pines exactos** (evita conflictos en Streamlit Cloud):

```
streamlit>=1.40
pandas>=2.2
numpy>=1.26
plotly>=5.24
scipy>=1.14
groq>=0.11
reportlab>=4.2
kaleido>=0.2.1
```

---

## 3. HALLAZGOS YA VERIFICADOS SOBRE LOS DATOS

**No pierdas tiempo redescubriendo esto: ya fue auditado contra los archivos reales.**
Úsalo para escribir la limpieza directamente. Aun así, el módulo de auditoría debe **calcular**
estas métricas en tiempo de ejecución (no hardcodearlas), porque el dashboard las muestra.

### 3.1 `inventario_central_v2.csv` — 2,500 filas × 8 columnas
| Columna | Hallazgo | Acción decidida |
|---|---|---|
| `SKU_ID` | 0 duplicados. Llave primaria válida | ninguna |
| `Categoria` | 8 valores para 5 categorías reales: `LAPTOP`/`Laptops`, `smart-phone`/`Smartphones`, más `'???'` (nulo disfrazado) | mapeo canónico explícito; `'???'` → `NaN` → `"Sin Categoria"` |
| `Stock_Actual` | 100 nulos + **60 valores negativos** (mín −50) | negativos → `NaN`, luego imputar **mediana** |
| `Costo_Unitario_USD` | 0 nulos. Rango **$0.05 → $850,000** (media 1,105 vs mediana 755: asimetría brutal) | **no eliminar**: marcar con flag IQR (ver QA-3) |
| `Punto_Reorden` | limpio (100–299) | ninguna |
| `Lead_Time_Dias` | **tipo texto mixto**: `'25-30 días'`(454), `'Inmediato'`(433), `'10'`, `'5'`, `'3'` + **403 nulos** | parser a numérico: `Inmediato`→0, rango→promedio, dígito→float; nulos → mediana |
| `Bodega_Origen` | 6 valores: `Norte`, `norte`, `Sur`, `Occidente`, `ZONA_FRANCA`, `BOD-EXT-99` | mapeo canónico. **OJO:** `BOD-EXT-99` NO es variante de otra, es bodega externa real |
| `Ultima_Revision` | **100% formato ISO** `YYYY-MM-DD`, sin nulos. Rango 2024-03-04 → 2026-01-31 | `pd.to_datetime` directo |

### 3.2 `transacciones_logistica_v2.csv` — 10,000 filas × 10 columnas
| Columna | Hallazgo | Acción decidida |
|---|---|---|
| `Transaccion_ID` | 0 duplicados | llave primaria válida |
| `SKU_ID` | **480 SKUs huérfanos = 1,751 filas (17.5%)** sin match en inventario | **NO eliminar.** Left join + flag `Es_SKU_Fantasma` |
| `Fecha_Venta` | **100% formato `DD/MM/YYYY`** (no hay mezcla real). Rango 2024-09-23 → 2026-02-04 | `pd.to_datetime(..., format='%d/%m/%Y')` |
| `Cantidad_Vendida` | **100 valores negativos** (mín −5) | → `NaN` (no `abs()`: no está confirmado que sean devoluciones) → imputar mediana |
| `Precio_Venta_Final` | limpio | ninguna |
| `Costo_Envio` | **834 nulos (8.3%)** | imputar mediana por `Ciudad_Destino` |
| `Tiempo_Entrega_Real` | **50 filas con valor exactamente 999** (centinela de error, no outlier real) | 999 → `NaN` → imputar mediana **por ciudad** vía `groupby().transform()` |
| `Estado_Envio` | **1,683 nulos (16.8%)**. Valores: Entregado, Perdido, Retrasado, Devuelto, En Camino | nulos → `"Desconocido"` (categoría explícita, no imputar moda: perdería información) |
| `Ciudad_Destino` | 8 valores: `BOG`/`Bogotá`, `MED`/`Medellín`, `Cali`, `Barranquilla`, `Bucaramanga`, y **`Ventas_Web`** (¡no es ciudad! es valor fugado de `Canal_Venta`) | mapeo canónico; `Ventas_Web` → `NaN` + flag `Ciudad_Invalida` |
| `Canal_Venta` | limpio: App, Físico, Online, WhatsApp | ninguna |

> ⚠️ El **diccionario de datos** menciona `Tiempo_Entrega` y `Ticket_Soporte`; los nombres reales
> en los CSV son `Tiempo_Entrega_Real` y `Ticket_Soporte_Abierto`. Además `Canal_Venta` existe en
> los datos pero no en el diccionario. **Documenta esta discrepancia en el README** — es hallazgo
> de auditoría válido y suma en "Transparencia".

### 3.3 `feedback_clientes_v2.csv` — 4,500 filas × 9 columnas
| Columna | Hallazgo | Acción decidida |
|---|---|---|
| `Feedback_ID` | **500 IDs duplicados PERO con datos distintos** (distinto `Transaccion_ID`, edad, NPS) → es **colisión de llave**, no fila repetida | **NO usar `drop_duplicates()` ciego.** Renumerar IDs; conservar las filas |
| — | 0 filas 100% idénticas (`df.duplicated().sum() == 0`) | reportar ambos números por separado en la auditoría |
| `Transaccion_ID` | 0 huérfanos (todos existen en transacciones) **pero 877 IDs repetidos** → varias opiniones por venta | **riesgo de fan-out**: agregar feedback al grano de transacción ANTES del merge |
| — | Cobertura: solo **3,623 de 10,000 ventas** (36.2%) tienen feedback | los `NaN` post-merge son legítimos, no imputar |
| `Rating_Producto` | escala 1–5 pero contiene **valor 99** | `>5` → `NaN` → imputar **mediana** (variable ordinal) |
| `Rating_Logistica` | limpio (1–5) | ninguna |
| `Comentario_Texto` | 657 `NaN` **+ 631 con el literal `'---'`** (nulo disfrazado) | `'---'` → `NaN` |
| `Recomienda_Marca` | 1,119 nulos + valores `SI`/`NO`/`Maybe` | `SI`→True, `NO`→False, `Maybe`→`NaN` |
| `Ticket_Soporte_Abierto` | 4 valores mezclando idiomas y tipos: `'Sí'`, `'No'`, `'1'`, `'0'` | mapear a booleano |
| `Edad_Cliente` | **23 filas > 110** (máx 195) | `>100` → `NaN` → imputar mediana |
| `Satisfaccion_NPS` | continuo −99.8 → 99.9 | conservar numérico + derivar `Segmento_NPS` (ver 4.3) |

---

## 4. ROADMAP DE IMPLEMENTACIÓN

> Cada bloque = un commit. Cada función y cada sección de la UI debe llevar un **tag de
> trazabilidad** en comentario/docstring y en el texto visible, con el formato `[F1.1]`, `[P3]`,
> `[QA-2]`, etc. Así el evaluador identifica de inmediato qué requisito se cumplió dónde.

### Bloque 0 — `chore: estructura inicial del proyecto`
- Crear el árbol de la sección 2. Mover los 3 CSV a `data/raw/`, los 3 PDF a `docs/guides/`,
  el notebook a `notebooks/01_auditoria_exploratoria.ipynb`.
- Crear `.gitignore`, `requirements.txt`, `.streamlit/secrets.toml.example`.
- `git init` si no existe; añadir remote; primer commit.

---

### Bloque 1 — `feat(auditoria): calcula health score y metricas de calidad` → **[FASE 1]**

**`src/carga.py`**
```python
@st.cache_data
def cargar_crudos() -> dict[str, pd.DataFrame]:
    """Lee los 3 CSV de data/raw/ SIN modificarlos. [F1.0]"""
```

**`src/limpieza.py`** — funciones de auditoría:

- `auditar(df, nombre) -> dict` **[F1.1]** devuelve:
  - `pct_nulos_por_columna` (incluye **nulos disfrazados**: `'???'`, `'---'`, `'Ventas_Web'`)
  - `filas_duplicadas_exactas` y `ids_duplicados` (por separado — son fallas distintas)
  - `outliers_por_columna` (regla IQR: `< Q1 − 1.5·IQR` o `> Q3 + 1.5·IQR`)
  - `valores_imposibles` (negativos en stock/cantidad, rating>5, edad>100, tiempo==999)
  - `health_score`

- **Definición del Health Score [F1.2]** — usa exactamente esta fórmula (documéntala en el README
  y como tooltip en la app; el evaluador debe ver que no es arbitraria):

  ```
  Completitud = 100 × (1 − celdas_nulas / celdas_totales)
  Unicidad    = 100 × (1 − filas_o_ids_duplicados / filas_totales)
  Validez     = 100 × (1 − celdas_con_valor_imposible / celdas_totales)
  Health Score = 0.40·Completitud + 0.20·Unicidad + 0.40·Validez
  ```
  Los pesos priorizan completitud y validez porque son las que sesgan los KPIs financieros;
  la duplicidad aquí es un problema de trazabilidad, no de magnitud.

- `comparar_salud(antes, despues) -> pd.DataFrame` **[F1.3]** tabla Antes vs Después.

---

### Bloque 2 — `feat(limpieza): normaliza y depura los tres datasets` → **[FASE 1 + QA-2]**

Tres funciones, una por dataset: `limpiar_inventario(df)`, `limpiar_transacciones(df)`,
`limpiar_feedback(df)`. Cada una devuelve `(df_limpio, log_decisiones)` donde `log_decisiones`
es una lista de dicts `{columna, problema, accion, justificacion, filas_afectadas}` → esto
alimenta el **reporte de limpieza descargable** exigido en los entregables.

**Principios de implementación obligatorios:**

1. **Valores imposibles → `NaN` ANTES de imputar.** Nunca al revés: imputar con estadísticos
   contaminados por valores fuera de rango es un error metodológico crítico.
2. **Mapeo canónico explícito con diccionario**, nunca `.str.lower()` automático **[QA-2]**.
   Razón: `BOD-EXT-99` y `Ventas_Web` no se arreglan con transformaciones de texto; requieren
   juicio caso por caso.
3. **Justificación de media vs mediana vs moda [Decisión Ética]** — regla a aplicar y documentar:
   - Distribución **simétrica** (|media − mediana| / std < 0.1) → **media**
   - Distribución **asimétrica o con outliers** → **mediana** (robusta)
   - Variable **categórica u ordinal** → **moda / mediana ordinal**
   - Nulo que **significa algo** (`Estado_Envio`) → categoría explícita `"Desconocido"`, no imputar
   Calcula el criterio en código (no lo asumas) y guarda la justificación en `log_decisiones`.
4. **Nada se elimina salvo justificación explícita.** En este dataset, **no se elimina ninguna fila**:
   ni SKUs fantasma (se marcan), ni feedback con ID colisionado (se renumera). Documenta que la
   política fue "marcar sobre eliminar" para preservar trazabilidad de ingresos **[QA-1]**.

**`Lead_Time_Dias` — parser explícito:**
```python
def _parsear_lead_time(v):
    """'Inmediato'->0 | '25-30 días'->27.5 | '10'->10.0 | otro->NaN"""
```

**Validación temporal [QA-4] — fechas futuras:**
Define `FECHA_CORTE = pd.Timestamp("2026-01-31")` (fin del periodo operativo declarado; coincide
con el máximo de `Ultima_Revision`). Hay **75 transacciones posteriores** (máx 2026-02-04).
Acción: marcarlas con flag `Fecha_Futura` y **excluirlas de las series de tiempo**, conservándolas
en el dataset con su flag. La app muestra el conteo. *No uses `datetime.now()`*: la fecha de
ejecución real ya superó el periodo y el filtro no detectaría nada.

**Filtro IQR de costos [QA-3]:**
Función `marcar_outliers_iqr(df, columna) -> (serie_bool, limites)`. Se **marca**, no se borra.
La app expone un toggle "Excluir outliers de costo de los KPIs" (default: **activado**) y una
sección expandible **"Ver registros excluidos"** con la tabla completa.

---

### Bloque 3 — `feat(integracion): construye la fuente unica de verdad` → **[FASE 2]**

**Arquitectura de dos capas — el orden importa:**

```python
# PASO 1 [F2.1]: agregar feedback AL GRANO DE TRANSACCIÓN para evitar fan-out.
# Sin esto, las 877 transacciones con >1 feedback duplicarían filas e INFLARÍAN el margen total.
fb_agg = fb.groupby("Transaccion_ID").agg(
    Rating_Producto_Prom=("Rating_Producto", "mean"),
    Rating_Logistica_Prom=("Rating_Logistica", "mean"),
    NPS_Prom=("Satisfaccion_NPS", "mean"),
    Tuvo_Ticket_Soporte=("Ticket_Soporte_Abierto", "any"),
    N_Feedbacks=("Feedback_ID", "count"),
).reset_index()

# PASO 2 [F2.2]: merge en cadena. Grano final = 1 fila por VENTA. Nunca inner join.
maestro = (trx
    .merge(inv, on="SKU_ID", how="left", indicator="_origen_inv")
    .merge(fb_agg, on="Transaccion_ID", how="left"))
maestro["Es_SKU_Fantasma"] = maestro["_origen_inv"] == "left_only"
```

**Dilema del SKU Fantasma — decisión a implementar y justificar [F2.3]:**
Los 480 SKUs huérfanos aparecen en 1,751 ventas (17.5%) con **volumen y precios normales**, no en
patrón de dígitos transpuestos ni concentrados en un canal → la hipótesis defendible es
**catálogo desactualizado (productos nuevos no registrados en el ERP)**, no error de digitación
ni fraude. Por tanto: **conservar las ventas, marcarlas, y calcular el margen en dos escenarios**
(`margen_conservador` = solo SKUs catalogados; `margen_total` = todos, con costo imputado por
mediana de la categoría o global). Mostrar ambos en el dashboard: es la evidencia que exige P3.

**Trazabilidad de ingresos [QA-1]:** implementa una aserción visible en la pestaña de Auditoría:
```
ingreso_bruto_crudo (desde data/raw) == ingreso_bruto_maestro ± 0.01
```
Si no cuadra, la app lo muestra en rojo. Esto satisface el criterio "la suma total de ingresos
post-limpieza debe ser trazable hasta el archivo original".

**Variables derivadas — mínimo 3, implementa las 5 [F2.4]:**
| Variable | Fórmula | Para qué pregunta |
|---|---|---|
| `Ingreso_Bruto` | `Cantidad_Vendida × Precio_Venta_Final` | P1, P3 |
| `Margen_Utilidad` | `Ingreso_Bruto − (Cantidad_Vendida × Costo_Unitario_USD) − Costo_Envio` | P1 |
| `Margen_Pct` | `Margen_Utilidad / Ingreso_Bruto × 100` | P1 |
| `Brecha_Entrega` | `Tiempo_Entrega_Real − Lead_Time_Dias` (>0 = incumplimiento) | P2, P5 |
| `Dias_Desde_Revision` | `(FECHA_CORTE − Ultima_Revision).dt.days` | P5 |
| `Segmento_NPS` | Detractor `< 0` · Pasivo `0–50` · Promotor `> 50` | P2, P4 |

*(La normalización del NPS exigida por el enunciado se cumple con `Segmento_NPS`: la escala
continua −100..100 no es interpretable por sí sola para la junta directiva.)*

`Ratio_Soporte_por_Categoria` se calcula agregado en `analisis.py` (grano categoría, no venta).

---

### Bloque 4 — `feat(analisis): resuelve las cinco preguntas gerenciales` → **[RETO P1–P5]**

`src/analisis.py`: una función por pregunta, cada una devuelve `(df_resultado, dict_conclusiones)`.
Los `dict_conclusiones` alimentan tanto la UI como el prompt de la IA.

- **`p1_fuga_capital(maestro)`** — SKUs con `Margen_Utilidad < 0` agregados por SKU. Cruzar con
  `Canal_Venta` para contrastar Online vs resto. Cuantificar: pérdida total USD, % del ingreso,
  nº de SKUs afectados. Concluir "pérdida por volumen" vs "falla de precios".
- **`p2_crisis_logistica(maestro)`** — correlación de Pearson entre `Tiempo_Entrega_Real` y
  `NPS_Prom` **por cada combinación ciudad × bodega**. Devolver ranking ordenado por correlación
  más negativa, con `n` y `p-valor` (`scipy.stats.pearsonr`). Filtrar grupos con `n < 30` (una
  correlación con 5 datos no es evidencia). Identificar la zona a intervenir.
- **`p3_venta_invisible(maestro)`** — `Ingreso_Bruto` de `Es_SKU_Fantasma == True`, en USD y como
  % del ingreso total. Desglose por ciudad y canal.
- **`p4_diagnostico_fidelidad(maestro)`** — por `Categoria`: `Stock_Actual` promedio vs
  `NPS_Prom` promedio vs `Margen_Pct` promedio. Marcar cuadrante "stock alto + NPS negativo".
  Resolver la paradoja comparando `Rating_Producto_Prom` (→ calidad) contra `Margen_Pct`
  (→ sobrecosto): el que se desvíe explica la causa.
- **`p5_riesgo_operativo(maestro)`** — por `Bodega_Origen`: `Dias_Desde_Revision` promedio vs
  tasa de `Tuvo_Ticket_Soporte`. Scatter + línea de tendencia OLS. Identificar bodegas "a ciegas".

> ⚠️ Si usas `trendline="ols"` en Plotly Express, `statsmodels` debe estar en `requirements.txt`.
> Para evitar esa dependencia extra, calcula la recta con `numpy.polyfit` y agrégala como traza.
> **Prefiere `numpy.polyfit`** (menos dependencias = menos riesgo de deploy).

---

### Bloque 5 — `feat(ui): dashboard streamlit con pestanas y filtros` → **[Checklist 3.1]**

**`app.py` — solo UI.** Toda la lógica vive en `src/`.

**Sidebar [3.1-a]:**
- `st.date_input` rango de fechas (default: min–`FECHA_CORTE`)
- `st.multiselect` de `Categoria`, `Bodega_Origen`, `Ciudad_Destino`, `Canal_Venta`
- `st.toggle` "Excluir outliers de costo (IQR)" — default `True` **[QA-3]**
- `st.toggle` "Incluir SKUs fantasma en el margen" — default `True` **[F2.3]**
- `st.button("🔄 Refrescar Análisis")` → `st.cache_data.clear()` + `st.rerun()`

> **[QA-2] Criterio de aceptación:** el multiselect de ciudad debe mostrar exactamente
> **5 opciones** (Bogotá, Medellín, Cali, Barranquilla, Bucaramanga). Si aparecen `BOG` o `MED`,
> la normalización falló.

**Cuatro pestañas con `st.tabs` [3.1-c]:**

1. **🔍 Auditoría** — Health Score antes/después por dataset (`st.metric` con delta), tabla de
   nulos por columna, duplicados exactos vs IDs colisionados, conteo de outliers, expander
   "Ver registros excluidos" **[QA-3]**, aserción de trazabilidad de ingresos **[QA-1]**,
   y `st.download_button` con el **reporte de limpieza en CSV** (desde `log_decisiones`).
2. **📦 Operaciones** — P1 (fuga de capital) y P3 (venta invisible).
3. **👤 Cliente** — P2 (crisis logística), P4 (fidelidad) y P5 (riesgo operativo).
4. **🤖 Insights de IA** — módulo Groq.

**Reglas de UI:**
- Cada gráfico y cada KPI lleva un `st.caption` con su tag: *"[P1] Fuga de capital…"*.
- Usa `width="stretch"` en lugar de `use_container_width` (deprecado).
- Cada pestaña abre con 2–3 líneas de texto explicando **qué se está viendo y por qué importa**,
  redactadas para alguien no técnico. El dashboard debe enseñar, no solo mostrar.
- Maneja el caso "filtros dejan 0 filas" y "un solo grupo": muestra `st.warning` y `return`,
  **nunca dejes que reviente**. Aplica esto también antes de cualquier `pearsonr`.

---

### Bloque 6 — `feat(ia): integra modulo de recomendacion estrategica con groq` → **[FASE 3]**

`src/ia.py`:
- Cliente Groq inicializado con `obtener_api_key()`. Si no hay key: `st.info` explicando cómo
  configurarla, **sin romper la app**.
- `st.selectbox` de modelo con: `llama-3.3-70b-versatile` (default, cumple el requisito "Llama-3"),
  `llama-3.1-8b-instant`, `openai/gpt-oss-120b`. Si Groq devuelve *model decommissioned*,
  captura la excepción y muestra un mensaje claro con el siguiente modelo sugerido.
- `generar_recomendaciones(resumen_filtrado: dict) -> str`:
  - **Entrada = exclusivamente el resumen estadístico de los datos ya filtrados por el usuario**
    (`df.describe()` + los `dict_conclusiones` de P1–P5). Nunca envíes el DataFrame completo.
  - System prompt: *consultor senior de operaciones y rentabilidad dirigiéndose a una junta
    directiva; exactamente tres párrafos; sin jerga técnica ni mención de código; cada párrafo
    debe citar una cifra concreta del resumen.*
  - `try/except` alrededor de la llamada, con `st.spinner` mientras corre.
- Botón `st.button("Generar recomendación estratégica")` — dispara solo bajo demanda **[3.1-d]**.

---

### Bloque 7 — `docs: genera informe de hallazgos y readme` → **[Entregables 3.2 y 3.3]**

**`scripts/generar_informe.py`** — genera `docs/Informe_Hallazgos.pdf` con **reportlab**:
- Exporta las figuras clave llamando a las **mismas funciones de `src/graficos.py`** que usa la
  app (`fig.write_image()` con kaleido) → `docs/img/`. Así las gráficas del PDF son literalmente
  las de la app, no reconstrucciones.
- Estructura del PDF **[3.2]**:
  1. Portada (título, autor: Andrés Vélez R., curso, docente, fecha)
  2. Resumen ejecutivo — **narrativa de negocio, cero código**: por qué la empresa pierde dinero
  3. Estado de los datos: Health Score antes/después + decisiones éticas de limpieza
  4. Hallazgos P1–P5, cada uno con su figura + cifra + interpretación
  5. **Plan de acción: 3 recomendaciones tácticas numeradas y priorizadas** (Baja / Media / Alta
     complejidad), cada una con impacto estimado en USD o en puntos de NPS
- Al final, imprime en consola: *"Reemplaza `docs/img/*.png` por capturas reales del dashboard
  desplegado si quieres cumplir literalmente el requisito de 4 capturas de pantalla"*.

**`README.md` [3.3]:**
- Descripción del problema de negocio (no del código)
- Guía de instalación reproducible: clonar → `venv` → `pip install -r requirements.txt` →
  `streamlit run app.py`; y cómo configurar `GROQ_API_KEY` en local (`.env`) y en Cloud (Secrets)
- Enlace a la app desplegada (deja el placeholder `<URL_STREAMLIT_CLOUD>`)
- **Matriz de trazabilidad de requisitos** — tabla obligatoria, es lo que pidió el usuario:

  | Requisito (fuente) | Tag | Dónde está implementado |
  |---|---|---|
  | Fase 1 · Health Score antes/después | `[F1.2]` | `src/limpieza.py::calcular_health_score` · app → pestaña Auditoría |
  | Fase 1 · % nulidad por columna | `[F1.1]` | `src/limpieza.py::auditar` · pestaña Auditoría |
  | Fase 1 · Decisión ética media/mediana/moda | `[F1.4]` | `log_decisiones` · reporte descargable |
  | Fase 2 · Merge estratégico (SSOT) | `[F2.2]` | `src/integracion.py::construir_maestro` |
  | Fase 2 · Dilema SKU fantasma | `[F2.3]` | `src/integracion.py` · pestaña Operaciones |
  | Fase 2 · ≥3 variables derivadas | `[F2.4]` | `src/integracion.py::agregar_variables_derivadas` |
  | Fase 3 · IA Groq (Llama-3) | `[F3]` | `src/ia.py` · pestaña Insights de IA |
  | Pregunta 1 · Fuga de capital | `[P1]` | `src/analisis.py::p1_fuga_capital` |
  | Pregunta 2 · Crisis logística | `[P2]` | `src/analisis.py::p2_crisis_logistica` |
  | Pregunta 3 · Venta invisible | `[P3]` | `src/analisis.py::p3_venta_invisible` |
  | Pregunta 4 · Diagnóstico de fidelidad | `[P4]` | `src/analisis.py::p4_diagnostico_fidelidad` |
  | Pregunta 5 · Riesgo operativo | `[P5]` | `src/analisis.py::p5_riesgo_operativo` |
  | QA · Trazabilidad de ingresos | `[QA-1]` | pestaña Auditoría (aserción visible) |
  | QA · Normalización categórica | `[QA-2]` | `src/limpieza.py` mapeos · sidebar |
  | QA · Outliers de costo IQR | `[QA-3]` | `src/limpieza.py::marcar_outliers_iqr` · toggle sidebar |
  | QA · Fechas futuras | `[QA-4]` | `src/limpieza.py` flag `Fecha_Futura` |
  | Entregable · Reporte de limpieza descargable | `[E1]` | pestaña Auditoría · `st.download_button` |
  | Entregable · Informe PDF | `[E2]` | `docs/Informe_Hallazgos.pdf` |
  | Entregable · Gestión de secretos | `[E3]` | `src/ia.py::obtener_api_key` |

- Sección **"Discrepancias detectadas en el diccionario de datos"** con lo del punto 3.2.

---

### Bloque 8 — `test: valida el pipeline extremo a extremo`

Un solo archivo `scripts/verificar.py` (no pytest, no suite formal — evita sobreingeniería).
Debe correr sin errores e imprimir ✅/❌ por cada check:

1. Los 3 CSV cargan y `data/raw/` no fue modificado (compara hash o `shape`).
2. Post-limpieza: 0 negativos en `Stock_Actual`/`Cantidad_Vendida`, 0 ratings >5,
   0 edades >100, 0 valores 999 en `Tiempo_Entrega_Real`.
3. `Ciudad_Destino` limpia tiene exactamente 5 categorías **[QA-2]**.
4. `len(maestro) == 10_000` (el merge NO duplicó filas → sin fan-out) **[F2.1]**.
5. Trazabilidad: `ingreso_crudo == ingreso_maestro` con tolerancia 0.01 **[QA-1]**.
6. P1–P5 se ejecutan sobre el maestro completo **y** sobre un subconjunto de 1 sola ciudad
   (caso borde de grupo único) sin lanzar excepción.
7. Filtro que deja 0 filas: cada función de análisis retorna vacío controlado, no excepción.

Corre `python scripts/verificar.py` antes del commit final. Si algo falla, arréglalo.

---

### Bloque 9 — `chore: publica el proyecto en el repositorio remoto`
- Verifica que `.streamlit/secrets.toml` **no** esté trackeado.
- `git push -u origin main`.
- Imprime al usuario: URL del repo, comando local de ejecución, y el recordatorio de que
  `GROQ_API_KEY` debe estar en Settings → Secrets de Streamlit Cloud.

---

## 5. RESTRICCIONES FINALES

- ❌ No crear clases si una función basta. No abstraer "por si acaso".
- ❌ No usar `use_container_width` (deprecado) → `width="stretch"`.
- ❌ No pasar paletas cualitativas de Plotly (ej. `"Plotly"`) a parámetros de escala continua:
  no son colorscales válidas y revientan en deploy. Usa `"Viridis"`, `"RdYlGn"`, `"Blues"`.
- ❌ No dejar rutas absolutas ni la API key en el código.
- ❌ No mencionar Claude ni IA generativa en commits, código, README o el PDF.
- ✅ Todo el texto visible al usuario en **español**.
- ✅ PEP8 y manejo de excepciones donde el dato puede fallar (I/O, API, grupos vacíos).
- ✅ Cada bloque = un commit conventional, hecho sin pedir autorización.

**Al terminar, imprime un resumen de qué se implementó, en qué archivo, y con qué tag.**
