"""Cliente Groq para recomendaciones estratégicas. [FASE 3]"""
import os
import json
import streamlit as st
import pandas as pd


def obtener_api_key() -> str | None:
    """Lee la key de .env local o de st.secrets en Cloud. Devuelve None si no existe."""
    key = os.getenv("GROQ_API_KEY")
    if key:
        return key
    try:
        return st.secrets.get("GROQ_API_KEY", None)
    except Exception:
        return None


def _resumen_datos(maestro: pd.DataFrame, conclusiones: dict) -> str:
    """Construye un resumen estadístico compacto para enviar a la IA."""
    cols_num = maestro.select_dtypes(include="number").columns.tolist()
    describe_dict = maestro[cols_num].describe().round(2).to_dict()
    return json.dumps({
        "estadisticas": describe_dict,
        "conclusiones_p1_p5": {k: {ck: cv for ck, cv in v.items() if not isinstance(cv, list)} for k, v in conclusiones.items()},
        "n_filas": len(maestro),
    }, ensure_ascii=False, default=str)


def generar_recomendaciones(resumen_filtrado: str, modelo: str, api_key: str) -> str:
    """Llama a Groq y devuelve el texto de recomendación. [F3]"""
    from groq import Groq
    cliente = Groq(api_key=api_key)

    system_prompt = (
        "Eres un consultor senior de operaciones y rentabilidad. "
        "Tu audiencia es la junta directiva de TechLogistics S.A.S., una empresa de logística de tecnología. "
        "Redacta exactamente tres párrafos sin jerga técnica ni menciones a código o modelos de datos. "
        "Cada párrafo debe citar al menos una cifra concreta del resumen estadístico que recibes. "
        "El tono es ejecutivo, directo y orientado a decisiones."
    )

    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Aquí está el resumen de indicadores operacionales:\n\n{resumen_filtrado}"},
        ],
        temperature=0.5,
        max_tokens=800,
    )
    return respuesta.choices[0].message.content


def mostrar_seccion_ia(maestro: pd.DataFrame, conclusiones: dict):
    """Renderiza la pestaña completa de IA. [F3]"""
    st.header("🤖 Insights de IA — Recomendación Estratégica")
    st.write(
        "El módulo de inteligencia artificial analiza los indicadores filtrados y genera tres recomendaciones "
        "ejecutivas priorizadas para la junta directiva. Solo se envían estadísticos agregados, nunca datos personales."
    )

    api_key = obtener_api_key()

    if not api_key:
        st.info(
            "**¿Cómo activar el módulo de IA?**\n\n"
            "- **Local:** crea un archivo `.env` en la raíz del proyecto con `GROQ_API_KEY=gsk_...`\n"
            "- **Streamlit Cloud:** ve a Settings → Secrets y agrega `GROQ_API_KEY = \"gsk_...\"`"
        )
        return

    MODELOS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "openai/gpt-oss-120b",
    ]
    modelo = st.selectbox(
        "Modelo de IA",
        MODELOS,
        help="llama-3.3-70b-versatile cumple el requisito del enunciado (Llama-3). [F3]",
    )

    if st.button("Generar recomendación estratégica"):
        if maestro.empty:
            st.warning("Aplica filtros que contengan datos antes de generar recomendaciones.")
            return

        resumen = _resumen_datos(maestro, conclusiones)
        with st.spinner("Consultando IA... esto tarda unos segundos"):
            try:
                texto = generar_recomendaciones(resumen, modelo, api_key)
                st.success("Recomendación generada")
                st.write(texto)
                st.caption(f"[F3] Generado con modelo {modelo} vía Groq API · Solo estadísticos agregados enviados (sin datos personales)")
            except Exception as e:
                msg = str(e)
                if "decommissioned" in msg.lower() or "not found" in msg.lower():
                    st.error(
                        f"El modelo `{modelo}` ya no está disponible en Groq. "
                        f"Prueba con `{MODELOS[1]}` u otro de la lista."
                    )
                else:
                    st.error(f"Error al llamar a la IA: {msg}")
