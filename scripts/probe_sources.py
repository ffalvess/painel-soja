#!/usr/bin/env python3
"""Sonda temporária: testa endpoints candidatos para as novas seções do painel.

Roda no runner do Actions (internet livre) e imprime status + trecho da
resposta de cada URL, para decidir quais fontes usar nos coletores.
"""

import datetime as dt
import json
import sys

import requests

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def last_business_day(offset: int = 1) -> dt.date:
    d = dt.date.today() - dt.timedelta(days=offset)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


BD = last_business_day()
BD2 = last_business_day(2) if BD != last_business_day(2) else BD - dt.timedelta(days=1)
YMD = BD.strftime("%Y%m%d")
MDY = BD.strftime("%m/%d/%Y")
DMY = BD.strftime("%d/%m/%Y")
ISO = BD.isoformat()

CANDIDATES = [
    # --- CME: ids de produto (futuros e opções de soja)
    ("cme-product-slate",
     "https://www.cmegroup.com/CmeWS/mvc/ProductSlate/V2/List?pageNumber=1&pageSize=25&searchString=soybean",
     1800),
    # --- CME: ajustes de futuros por vencimento (settle, volume, OI)
    ("cme-settlements-fut",
     f"https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/320/FUT?tradeDate={MDY}&strategy=DEFAULT&pageSize=50",
     1200),
    # --- CME: volume/OI detalhado
    ("cme-voi-fut", f"https://www.cmegroup.com/CmeWS/mvc/Volume/Details/F/320/{YMD}/P", 900),
    ("cme-voi-opt-320", f"https://www.cmegroup.com/CmeWS/mvc/Volume/Details/O/320/{YMD}/P", 900),
    ("cme-voi-opt-321", f"https://www.cmegroup.com/CmeWS/mvc/Volume/Details/O/321/{YMD}/P", 900),
    # --- Yahoo: contrato individual (curva) e cadeia de opções
    ("yahoo-zsx26", "https://query1.finance.yahoo.com/v8/finance/chart/ZSX26.CBT?range=5d&interval=1d", 1500),
    ("yahoo-options-zs", "https://query1.finance.yahoo.com/v7/finance/options/ZS%3DF", 900),
    # --- B3 / BMF clássico: resumo estatístico por mercadoria (futuros e opções)
    ("bmf-pregao-sfi",
     "http://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/SistemaPregao1.asp"
     f"?pagetype=pop&caminho=Resumo%20Estat%EDstico%20-%20Sistema%20Preg%E3o&Data={DMY.replace('/', '%2F')}&Mercadoria=SFI",
     1200),
    ("bmf-ajustes",
     "https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/lum-ajustes-do-pregao-ptBR.asp",
     900),
    # --- B3 arquivos públicos
    ("b3-tickercsv", f"https://arquivos.b3.com.br/apinegocios/tickercsv/{ISO}", 400),
    ("b3-lending", f"https://arquivos.b3.com.br/api/download/requestname?fileName=DerivativesOpenPositionFile_{YMD}_1.csv", 600),
    # --- CONAB
    ("conab-serie-graos", "https://portaldeinformacoes.conab.gov.br/downloads/arquivos/SerieHistoricaGraos.txt", 900),
    ("conab-ckan", "https://dadosabertos.conab.gov.br/api/3/action/package_search?q=safra+graos&rows=5", 1500),
    # --- USDA
    ("usda-wasde-json", "https://www.usda.gov/oce/commodity/wasde/latest.json", 700),
    ("usda-esmis-cropprog", "https://usda.library.cornell.edu/api/v1/release/findByIdentifier/CropProg?latest=true", 1500),
    ("usda-nass-nokey", "https://quickstats.nass.usda.gov/api/api_GET/?key=TEST&commodity_desc=SOYBEANS&year=2026&format=JSON", 500),
]


def main() -> int:
    print(f"data de referência: {BD} ({YMD})")
    for name, url, snip in CANDIDATES:
        print(f"\n===== {name}\nGET {url}")
        try:
            r = requests.get(url, headers=UA, timeout=30)
            ct = r.headers.get("Content-Type", "?")
            body = r.text
            print(f"status={r.status_code} content-type={ct} bytes={len(r.content)}")
            try:
                parsed = r.json()
                body = json.dumps(parsed, ensure_ascii=False)[:snip]
                print("JSON:", body)
            except Exception:
                print("BODY:", " ".join(body[:snip].split()))
        except Exception as e:  # noqa: BLE001
            print(f"EXC: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
