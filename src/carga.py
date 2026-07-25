"""Lectura de los CSV originales sin modificarlos. [F1.0]"""
from pathlib import Path
import pandas as pd
import streamlit as st

_DATA_RAW = Path(__file__).parent.parent / "data" / "raw"


@st.cache_data
def cargar_crudos() -> dict[str, pd.DataFrame]:
    """Lee los 3 CSV de data/raw/ SIN modificarlos. [F1.0]"""
    return {
        "inventario": pd.read_csv(_DATA_RAW / "inventario_central_v2.csv"),
        "transacciones": pd.read_csv(_DATA_RAW / "transacciones_logistica_v2.csv"),
        "feedback": pd.read_csv(_DATA_RAW / "feedback_clientes_v2.csv"),
    }
