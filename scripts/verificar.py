"""Verificación extremo a extremo del pipeline. [Bloque 8]

Corre con:
    python scripts/verificar.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from src.carga import cargar_crudos
from src.limpieza import limpiar_inventario, limpiar_transacciones, limpiar_feedback
from src.integracion import agregar_variables_derivadas, construir_maestro, verificar_trazabilidad
from src.analisis import (
    p1_fuga_capital,
    p2_crisis_logistica,
    p3_venta_invisible,
    p4_diagnostico_fidelidad,
    p5_riesgo_operativo,
)

VERDE = "\033[92m✅"
ROJO = "\033[91m❌"
RESET = "\033[0m"


def check(condicion: bool, mensaje: str):
    icono = VERDE if condicion else ROJO
    print(f"{icono} {mensaje}{RESET}")
    return condicion


def main():
    print("\n=== Verificación del pipeline TechLogistics ===\n")
    errores = 0

    # ---- 1. Carga ----
    crudos = cargar_crudos()
    shapes_originales = {k: v.shape for k, v in crudos.items()}

    ok = check(shapes_originales["inventario"] == (2500, 8), "Inventario: 2500 filas × 8 columnas")
    errores += not ok
    ok = check(shapes_originales["transacciones"] == (10000, 10), "Transacciones: 10000 filas × 10 columnas")
    errores += not ok
    ok = check(shapes_originales["feedback"] == (4500, 9), "Feedback: 4500 filas × 9 columnas")
    errores += not ok

    # ---- 2. Limpieza ----
    inv_l, _ = limpiar_inventario(crudos["inventario"])
    trx_l, _ = limpiar_transacciones(crudos["transacciones"])
    fb_l, _ = limpiar_feedback(crudos["feedback"])

    ok = check((inv_l["Stock_Actual"] < 0).sum() == 0, "Stock_Actual: 0 negativos post-limpieza")
    errores += not ok
    ok = check((trx_l["Cantidad_Vendida"] < 0).sum() == 0, "Cantidad_Vendida: 0 negativos post-limpieza")
    errores += not ok
    ok = check((fb_l["Rating_Producto"] > 5).sum() == 0, "Rating_Producto: 0 valores > 5 post-limpieza")
    errores += not ok
    ok = check((fb_l["Edad_Cliente"] > 100).sum() == 0, "Edad_Cliente: 0 valores > 100 post-limpieza")
    errores += not ok
    ok = check((trx_l["Tiempo_Entrega_Real"] == 999).sum() == 0, "Tiempo_Entrega_Real: 0 centinelas 999 post-limpieza")
    errores += not ok

    # ---- 3. QA-2: ciudades ----
    ciudades = trx_l["Ciudad_Destino"].dropna().unique()
    ok = check(len(ciudades) == 5, f"Ciudad_Destino: exactamente 5 categorías [QA-2] — encontradas: {sorted(ciudades)}")
    errores += not ok

    # ---- 4. Fan-out: 10,000 filas ----
    maestro_base = construir_maestro(inv_l, trx_l, fb_l)
    ok = check(len(maestro_base) == 10_000, f"Maestro: {len(maestro_base)} filas (debe ser 10,000) [F2.1]")
    errores += not ok

    maestro = agregar_variables_derivadas(maestro_base, inv_l)

    # ---- 5. Trazabilidad ----
    traz = verificar_trazabilidad(crudos["transacciones"], maestro)
    ok = check(traz["filas_ok"], f"Trazabilidad: {traz['filas_crudo']} → {traz['filas_maestro']} filas [QA-1]")
    errores += not ok
    print(f"   Info: {traz['explicacion']}")

    # ---- 6. P1–P5 sobre dataset completo ----
    for fn in [p1_fuga_capital, p2_crisis_logistica, p3_venta_invisible, p4_diagnostico_fidelidad, p5_riesgo_operativo]:
        try:
            fn(maestro)
            ok = check(True, f"{fn.__name__} ejecuta sin error (dataset completo)")
        except Exception as e:
            ok = check(False, f"{fn.__name__} lanzó excepción: {e}")
            errores += 1

    # ---- 6b. P1–P5 sobre subconjunto de 1 ciudad ----
    sub_ciudad = maestro[maestro["Ciudad_Destino"] == "Bogotá"].copy()
    for fn in [p1_fuga_capital, p2_crisis_logistica, p3_venta_invisible, p4_diagnostico_fidelidad, p5_riesgo_operativo]:
        try:
            fn(sub_ciudad)
            ok = check(True, f"{fn.__name__} ejecuta sin error (1 ciudad)")
        except Exception as e:
            ok = check(False, f"{fn.__name__} lanzó excepción con 1 ciudad: {e}")
            errores += 1

    # ---- 7. Filtro 0 filas ----
    df_vacio = maestro.iloc[0:0].copy()
    for fn in [p1_fuga_capital, p3_venta_invisible, p4_diagnostico_fidelidad, p5_riesgo_operativo]:
        try:
            res_df, res_dict = fn(df_vacio)
            ok = check("error" in res_dict or res_df.empty, f"{fn.__name__}: retorno controlado con 0 filas")
            errores += not ok
        except Exception as e:
            ok = check(False, f"{fn.__name__} lanzó excepción con 0 filas: {e}")
            errores += 1

    # p2 con 0 filas
    try:
        res_df, res_dict = p2_crisis_logistica(df_vacio)
        ok = check("error" in res_dict or res_df.empty, "p2_crisis_logistica: retorno controlado con 0 filas")
        errores += not ok
    except Exception as e:
        ok = check(False, f"p2_crisis_logistica lanzó excepción con 0 filas: {e}")
        errores += 1

    # ---- Resumen ----
    print(f"\n{'='*50}")
    if errores == 0:
        print(f"{VERDE} Todos los checks pasaron.{RESET}")
    else:
        print(f"{ROJO} {errores} check(s) fallaron.{RESET}")
    print()
    return errores


if __name__ == "__main__":
    sys.exit(main())
