import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

ATIVOS = {
    "BTC/EUR":  {"ticker": "BTC-EUR",  "tipo": "Cripto",    "emoji": "BTC"},
    "ETH/EUR":  {"ticker": "ETH-EUR",  "tipo": "Cripto",    "emoji": "ETH"},
    "SOL/EUR":  {"ticker": "SOL-EUR",  "tipo": "Cripto",    "emoji": "SOL"},
    "Ouro":     {"ticker": "GC=F",     "tipo": "Commodity", "emoji": "OURO"},
    "WTI Oil":  {"ticker": "CL=F",     "tipo": "Commodity", "emoji": "OIL"},
    "NVDA":     {"ticker": "NVDA",     "tipo": "Acao",      "emoji": "NVDA"},
}

def calcular_atr(df, periodo=20):
    high = df["High"]
    low = df["Low"]
    close_prev = df["Close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - close_prev).abs(),
        (low - close_prev).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(window=periodo).mean()

def analisar_ativo(nome, info, capital=900.0):
    try:
        df = yf.download(info["ticker"], period="120d", interval="1d", progress=False, auto_adjust=True)
        if df is None or len(df) < 60:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()

        preco = float(df["Close"].iloc[-1])
        max_20 = float(df["High"].iloc[-21:-1].max())
        min_20 = float(df["Low"].iloc[-21:-1].min())
        max_55 = float(df["High"].iloc[-56:-1].max())
        min_10 = float(df["Low"].iloc[-11:-1].min())
        n = float(calcular_atr(df, 20).iloc[-1])

        if np.isnan(n) or n <= 0:
            return None

        risco = capital * 0.01
        tamanho = risco / n
        valor = tamanho * preco

        if preco > max_55:
            sinal = "COMPRA S2 FORTE"
            stop = preco - 2 * n
        elif preco > max_20:
            sinal = "COMPRA S1 NORMAL"
            stop = preco - 2 * n
        else:
            sinal = "NEUTRO"
            stop = None

        dist = ((max_20 - preco) / preco) * 100

        return {
            "nome": nome,
            "ticker": info["ticker"],
            "emoji": info["emoji"],
            "preco": preco,
            "n": n,
            "max_20": max_20,
            "min_10": min_10,
            "sinal": sinal,
            "stop": stop,
            "tamanho": tamanho,
            "valor": valor,
            "risco": risco,
            "dist_pct": dist,
            "capital": capital
        }
    except Exception as e:
        print(f"Erro {nome}: {e}")
        return None

def correr_scanner(capital=900.0):
    sinais = []
    proximos = []
    neutros = []

    for nome, info in ATIVOS.items():
        r = analisar_ativo(nome, info, capital)
        if r is None:
            continue
        if r["sinal"] != "NEUTRO":
            sinais.append(r)
        elif 0 < r["dist_pct"] < 3.0:
            proximos.append(r)
        else:
            neutros.append(r)

    agora = datetime.now(pytz.utc).strftime("%d/%m/%Y %H:%M UTC")
    linhas = [f"TURTLE TRADING SCANNER\nData: {agora}\nCapital: {capital:.0f} euros\n"]

    if sinais:
        linhas.append(f"SINAIS ATIVOS - {len(sinais)} sinal(is)!\n")
        for r in sinais:
            linhas.append(
                f"{r['emoji']} {r['nome']} - {r['sinal']}\n"
                f"Preco: {r['preco']:.4f}\n"
                f"Stop Loss: {r['stop']:.4f}\n"
                f"Comprar: {r['tamanho']:.4f} unidades\n"
                f"Valor: {r['valor']:.2f} euros\n"
                f"Risco: {r['risco']:.2f} euros\n"
            )
    else:
        linhas.append("Sem sinais ativos hoje.\nMercado em consolidacao - aguardar.\n")

    if proximos:
        linhas.append("\nPROXIMOS DO ROMPIMENTO (menos de 3%):\n")
        for r in proximos:
            linhas.append(f"{r['emoji']} {r['nome']} - falta {r['dist_pct']:.1f}% para romper")

    return sinais, proximos, neutros, "\n".join(linhas)
