#!/usr/bin/env python3
"""
fetch_eurostat.py
SIEG Monitor IPC · Módulo de Veracidad

Descarga HICP (IPC armonizado) de Eurostat para España
y compara con datos oficiales del INE.

Detecta divergencias significativas entre ambas fuentes.

Autor : M. Castillo · mybloggingnotes@gmail.com
© 2026 M. Castillo
"""

import os
import requests
import duckdb
from datetime import datetime, date

BASE_DIR = os.path.expanduser("~/sieg-ipc")
DB_PATH  = os.path.join(BASE_DIR, "data", "processed", "ipc.duckdb")
LOG_PATH = os.path.join(BASE_DIR, "logs", "pipeline.log")

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [EUROSTAT] {msg}"
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")
    print(line)

def init_tabla(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ipc_eurostat (
            periodo     VARCHAR PRIMARY KEY,
            anyo        INTEGER,
            mes         INTEGER,
            fecha       DATE,
            hicp_es     DOUBLE,
            ingestion_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ipc_veracidad (
            fecha       DATE PRIMARY KEY,
            ine_valor   DOUBLE,
            eurostat_valor DOUBLE,
            divergencia DOUBLE,
            alerta      BOOLEAN,
            nivel       VARCHAR,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

def fetch_hicp_eurostat(conn):
    """Descarga HICP España desde Eurostat."""
    url = (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
        "prc_hicp_manr?geo=ES&coicop=CP00&sinceTimePeriod=2023-01&format=JSON"
    )
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "SIEG-IPC/1.0"})
        r.raise_for_status()
        data = r.json()

        # Extraer valores
        valores = data.get("value", {})
        dimensiones = data.get("dimension", {})
        periodos = dimensiones.get("time", {}).get("category", {}).get("index", {})
        periodos_inv = {v: k for k, v in periodos.items()}

        insertados = 0
        for idx_str, valor in valores.items():
            idx = int(idx_str)
            periodo = periodos_inv.get(idx)
            if not periodo:
                continue

            try:
                anyo = int(periodo[:4])
                mes  = int(periodo[5:7])
                fecha = date(anyo, mes, 1)
            except:
                continue

            conn.execute("""
                INSERT OR REPLACE INTO ipc_eurostat
                (periodo, anyo, mes, fecha, hicp_es)
                VALUES (?, ?, ?, ?, ?)
            """, (periodo, anyo, mes, str(fecha), valor))
            insertados += 1

        log(f"Eurostat HICP España: {insertados} registros")
        return insertados

    except Exception as e:
        log(f"Error Eurostat: {e}")
        return 0

def calcular_veracidad(conn):
    """Cruza INE vs Eurostat y detecta divergencias."""
    try:
        # IPC General INE
        df_ine = conn.execute("""
            SELECT fecha, valor FROM ipc_datos
            WHERE categoria = 'IPC General' AND fecha >= '2023-01-01'
            ORDER BY fecha
        """).df()

        # HICP Eurostat
        df_eur = conn.execute("""
            SELECT fecha, hicp_es FROM ipc_eurostat
            ORDER BY fecha
        """).df()

        if df_ine.empty or df_eur.empty:
            log("Sin datos suficientes para comparar")
            return

        # Merge por fecha
        import pandas as pd
        df_ine["fecha"] = pd.to_datetime(df_ine["fecha"])
        df_eur["fecha"] = pd.to_datetime(df_eur["fecha"])

        df_merge = df_ine.merge(df_eur, on="fecha", how="inner")
        df_merge["divergencia"] = (df_merge["valor"] - df_merge["hicp_es"]).round(2)

        # Clasificar nivel de alerta
        def nivel_alerta(div):
            abs_div = abs(div)
            if abs_div >= 1.0:
                return "ALTA"
            elif abs_div >= 0.5:
                return "MEDIA"
            elif abs_div >= 0.2:
                return "BAJA"
            return "OK"

        insertados = 0
        for _, row in df_merge.iterrows():
            div   = row["divergencia"]
            nivel = nivel_alerta(div)
            alerta = abs(div) >= 0.2

            conn.execute("""
                INSERT OR REPLACE INTO ipc_veracidad
                (fecha, ine_valor, eurostat_valor, divergencia, alerta, nivel)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(row["fecha"].date()), row["valor"],
                  row["hicp_es"], div, alerta, nivel))
            insertados += 1

        alertas = df_merge[abs(df_merge["divergencia"]) >= 0.2]
        log(f"Veracidad calculada: {insertados} comparaciones · {len(alertas)} alertas divergencia")

    except Exception as e:
        log(f"Error veracidad: {e}")

def exportar_parquet(conn):
    import pandas as pd
    exp_dir = os.path.join(BASE_DIR, "data", "exports")

    tablas = {
        "ipc_eurostat":  "SELECT * FROM ipc_eurostat ORDER BY fecha DESC",
        "ipc_veracidad": "SELECT * FROM ipc_veracidad ORDER BY fecha DESC",
    }
    for nombre, query in tablas.items():
        try:
            df = conn.execute(query).df()
            df.to_parquet(os.path.join(exp_dir, f"{nombre}.parquet"), index=False)
            log(f"Parquet {nombre}: {len(df)} filas")
        except Exception as e:
            log(f"Error parquet {nombre}: {e}")

def main():
    log("=" * 40)
    log("Módulo veracidad IPC — Inicio")

    conn = duckdb.connect(DB_PATH)
    init_tabla(conn)
    fetch_hicp_eurostat(conn)
    calcular_veracidad(conn)
    exportar_parquet(conn)
    conn.close()

    log("Módulo veracidad completado")
    log("=" * 40)

if __name__ == "__main__":
    main()
