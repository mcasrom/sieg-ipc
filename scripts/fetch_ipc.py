#!/usr/bin/env python3
"""
fetch_ipc.py
SIEG Monitor IPC · Inflación y Precios España

Descarga datos del IPC desde API INE.
Almacena en DuckDB + Parquet.

Cron: mensual dia 15 a las 09:00
0 9 15 * * cd ~/sieg-ipc && source venv/bin/activate && python3 scripts/fetch_ipc.py >> logs/pipeline.log 2>&1 && git add data/exports/ && git commit -m "auto: IPC $(date +%Y-%m)" && git push origin main

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

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

# Series IPC del INE — códigos verificados
SERIES_IPC = {
    "IPC General":              ("IPC251856", "#ef4444"),
    "Alimentos y bebidas":      ("IPC251862", "#eab308"),
    "Bebidas y tabaco":         ("IPC251867", "#84cc16"),
    "Vestido y calzado":        ("IPC251872", "#06b6d4"),
    "Vivienda y energía":       ("IPC251877", "#3b82f6"),
    "Muebles y hogar":          ("IPC251882", "#8b5cf6"),
    "Sanidad":                  ("IPC251887", "#14b8a6"),
    "Transporte":               ("IPC251892", "#f59e0b"),
    "Restaurantes y hoteles":   ("IPC251845", "#ec4899"),
    "Otros bienes y servicios": ("IPC251850", "#f97316"),
}

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")
    print(line)

def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ipc_series (
            cod         VARCHAR,
            nombre      VARCHAR,
            categoria   VARCHAR,
            color       VARCHAR,
            PRIMARY KEY (cod)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ipc_datos (
            cod         VARCHAR,
            categoria   VARCHAR,
            anyo        INTEGER,
            periodo     INTEGER,
            fecha       DATE,
            valor       DOUBLE,
            ingestion_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (cod, anyo, periodo)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ipc_ultimo (
            categoria   VARCHAR PRIMARY KEY,
            cod         VARCHAR,
            valor       DOUBLE,
            anyo        INTEGER,
            periodo     INTEGER,
            fecha       DATE,
            variacion   DOUBLE,
            color       VARCHAR,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    log("DB inicializada OK")

def fetch_serie(conn, categoria, cod, color, nult=999):
    url = f"https://servicios.ine.es/wstempus/js/ES/DATOS_SERIE/{cod}?nult={nult}"
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "SIEG-IPC/1.0"})
        r.raise_for_status()
        data = r.json()

        nombre = data.get("Nombre", categoria)

        # Guardar metadatos
        conn.execute("""
            INSERT OR REPLACE INTO ipc_series (cod, nombre, categoria, color)
            VALUES (?, ?, ?, ?)
        """, (cod, nombre[:200], categoria, color))

        # Guardar datos
        insertados = 0
        valores = data.get("Data", [])
        # Solo últimos 36 meses (desde 2023)
        # Ordenar por año/periodo descendente y tomar últimos 36
        valores = sorted(valores, key=lambda x: (x["Anyo"], x["FK_Periodo"]), reverse=True)[:36]
        valores = sorted(valores, key=lambda x: (x["Anyo"], x["FK_Periodo"]))  # volver a orden ascendente
        for v in valores:
            if v.get("Secreto", False):
                continue
            anyo    = v["Anyo"]
            periodo = v["FK_Periodo"]
            valor   = v["Valor"]
            # Calcular fecha aproximada
            mes = periodo if periodo <= 12 else 1
            try:
                fecha = date(anyo, mes, 1)
            except:
                fecha = date(anyo, 1, 1)

            conn.execute("""
                INSERT OR IGNORE INTO ipc_datos
                (cod, categoria, anyo, periodo, fecha, valor)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cod, categoria, anyo, periodo, str(fecha), valor))
            insertados += 1

        # Calcular último valor y variación
        if len(valores) >= 2:
            ultimo    = valores[-1]
            penultimo = valores[-2]
            variacion = ultimo["Valor"] - penultimo["Valor"] if penultimo["Valor"] else 0
            mes_u = ultimo["FK_Periodo"] if ultimo["FK_Periodo"] <= 12 else 1
            try:
                fecha_u = date(ultimo["Anyo"], mes_u, 1)
            except:
                fecha_u = date(ultimo["Anyo"], 1, 1)

            conn.execute("""
                INSERT OR REPLACE INTO ipc_ultimo
                (categoria, cod, valor, anyo, periodo, fecha, variacion, color)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (categoria, cod, ultimo["Valor"], ultimo["Anyo"],
                  ultimo["FK_Periodo"], str(fecha_u), round(variacion, 2), color))

        log(f"[INE] {categoria}: {insertados} datos · último: {valores[-1]['Valor'] if valores else 'N/A'}%")
        return insertados

    except Exception as e:
        log(f"[INE] Error {categoria}: {e}")
        return 0

def exportar_parquet(conn):
    import pandas as pd
    exp_dir = os.path.join(BASE_DIR, "data", "exports")
    os.makedirs(exp_dir, exist_ok=True)

    exportaciones = {
        "ipc_ultimo":  "SELECT * FROM ipc_ultimo ORDER BY valor DESC",
        "ipc_datos":   "SELECT * FROM ipc_datos ORDER BY cod, fecha DESC",
        "ipc_general": "SELECT * FROM ipc_datos WHERE categoria = 'IPC General' ORDER BY fecha",
        "ipc_series":  "SELECT * FROM ipc_series",
    }

    for nombre, query in exportaciones.items():
        try:
            df = conn.execute(query).df()
            df.to_parquet(os.path.join(exp_dir, f"{nombre}.parquet"), index=False)
            log(f"[PARQUET] {nombre}: {len(df)} filas")
        except Exception as e:
            log(f"[PARQUET] Error {nombre}: {e}")

def main():
    log("=" * 50)
    log("SIEG Monitor IPC — Inicio ingesta")

    conn = duckdb.connect(DB_PATH)
    init_db(conn)

    total = 0
    for categoria, (cod, color) in SERIES_IPC.items():
        total += fetch_serie(conn, categoria, cod, color)

    n = conn.execute("SELECT COUNT(*) FROM ipc_datos").fetchone()[0]
    log(f"BD: {n} registros IPC")

    exportar_parquet(conn)
    conn.close()

    log(f"Ingesta IPC completada — {total} registros")
    log("=" * 50)

if __name__ == "__main__":
    main()
