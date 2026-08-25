"""Sonda temporária: qual contrato está por trás dos contínuos do Yahoo.

Objetivo: confirmar se `ZC=F` rolou de setembro para dezembro/26 — o que
explicaria o salto de 491,50 para 523,25 (+6,46%) no dia 25/08/2026.

Rodar pelo workflow `probe.yml` e ler os logs. Remover depois.
"""

import json

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

ALVOS = [
    "ZC=F",
    "ZCU26.CBT",
    "ZCZ26.CBT",
    "ZCH27.CBT",
    "ZS=F",
    "ZSX26.CBT",
    "ZW=F",
    "ZM=F",
    "ZL=F",
    "BZ=F",
]

CAMPOS = [
    "symbol",
    "underlyingSymbol",
    "shortName",
    "regularMarketPrice",
    "regularMarketPreviousClose",
    "regularMarketChangePercent",
    "regularMarketVolume",
    "openInterest",
    "expireIsoDate",
    "contractSymbol",
    "headSymbolAsString",
]


def main() -> None:
    s = requests.Session()
    s.headers.update(HEADERS)
    s.get("https://fc.yahoo.com", timeout=30)
    crumb = s.get(
        "https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=30
    ).text.strip()
    print(f"crumb: {crumb!r}")

    r = s.get(
        "https://query1.finance.yahoo.com/v7/finance/quote",
        params={"symbols": ",".join(ALVOS), "crumb": crumb},
        timeout=30,
    )
    print("status:", r.status_code)
    r.raise_for_status()
    resultado = r.json()["quoteResponse"]["result"]

    print(f"\n{'=' * 78}\nCAMPOS SELECIONADOS\n{'=' * 78}")
    for q in resultado:
        print()
        for campo in CAMPOS:
            if campo in q:
                print(f"  {campo:32} {q[campo]}")

    faltando = set(ALVOS) - {q["symbol"] for q in resultado}
    if faltando:
        print("\nsímbolos sem resposta:", sorted(faltando))

    # Payload cru do milho, para não perder nenhum campo útil que eu não
    # tenha antecipado na lista acima.
    print(f"\n{'=' * 78}\nPAYLOAD CRU — ZC=F\n{'=' * 78}")
    for q in resultado:
        if q["symbol"] == "ZC=F":
            print(json.dumps(q, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
