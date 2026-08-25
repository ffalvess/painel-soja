"""Sonda temporária: qual contrato está por trás dos contínuos do Yahoo.

Objetivo: confirmar se `ZC=F` rolou de setembro para dezembro/26 — o que
explicaria o salto de 491,50 para 523,25 (+6,46%) no dia 25/08/2026.

O `/v8/chart` não exige crumb e cota contrato individual: se o ZCU26 estiver
perto de 480 e o ZCZ26 bater com o ZC=F, a rolagem está confirmada sem precisar
do endpoint autenticado. O `/v7/quote` (com crumb) vem depois, como bônus, para
pegar `underlyingSymbol` — mas o Yahoo devolve 429 com frequência para IPs do
Actions, então a sonda não pode depender dele.

Rodar pelo workflow `probe.yml` e ler os logs. Remover depois.
"""

import json
import time

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

CONTINUOS = ["ZC=F", "ZS=F", "ZW=F", "ZM=F", "ZL=F"]
CONTRATOS = [
    "ZCU26.CBT",
    "ZCZ26.CBT",
    "ZCH27.CBT",
    "ZCK27.CBT",
    "ZSX26.CBT",
    "ZSF27.CBT",
]


def chart(symbol: str) -> dict:
    """meta do /v8/chart — sem crumb, sem autenticação."""
    ultimo = None
    for host in ("query1", "query2"):
        try:
            r = requests.get(
                f"https://{host}.finance.yahoo.com/v8/finance/chart/{symbol}",
                params={"range": "5d", "interval": "1d"},
                headers=HEADERS,
                timeout=30,
            )
            r.raise_for_status()
            return r.json()["chart"]["result"][0]["meta"]
        except Exception as e:  # noqa: BLE001
            ultimo = e
    raise RuntimeError(f"{symbol}: {ultimo}")


def secao_chart() -> dict:
    print(f"{'=' * 78}\n/v8/chart — meta por símbolo (sem crumb)\n{'=' * 78}")
    precos = {}
    for symbol in CONTINUOS + CONTRATOS:
        try:
            m = chart(symbol)
        except Exception as e:  # noqa: BLE001
            print(f"\n{symbol}: FALHOU — {e}")
            continue
        precos[symbol] = m.get("regularMarketPrice")
        print(f"\n{symbol}")
        for campo in (
            "symbol",
            "shortName",
            "longName",
            "instrumentType",
            "regularMarketPrice",
            "chartPreviousClose",
            "previousClose",
            "regularMarketVolume",
            "regularMarketTime",
        ):
            if campo in m:
                print(f"  {campo:24} {m[campo]}")
        # campos que eu não previ podem trazer o contrato
        extras = set(m) - {
            "symbol",
            "shortName",
            "longName",
            "instrumentType",
            "regularMarketPrice",
            "chartPreviousClose",
            "previousClose",
            "regularMarketVolume",
            "regularMarketTime",
            "currency",
            "exchangeName",
            "fullExchangeName",
            "exchangeTimezoneName",
            "timezone",
            "gmtoffset",
            "firstTradeDate",
            "hasPrePostMarketData",
            "priceHint",
            "currentTradingPeriod",
            "tradingPeriods",
            "dataGranularity",
            "range",
            "validRanges",
            "regularMarketDayHigh",
            "regularMarketDayLow",
            "fiftyTwoWeekHigh",
            "fiftyTwoWeekLow",
            "scale",
            "sourceInterval",
            "exchangeDataDelayedBy",
        }
        for campo in sorted(extras):
            print(f"  [extra] {campo:17} {m[campo]}")
    return precos


def veredito(precos: dict) -> None:
    print(f"\n{'=' * 78}\nVEREDITO\n{'=' * 78}")
    zc = precos.get("ZC=F")
    if zc is None:
        print("  ZC=F não respondeu — inconclusivo")
        return
    print(f"  ZC=F = {zc}")
    for symbol in ("ZCU26.CBT", "ZCZ26.CBT", "ZCH27.CBT"):
        p = precos.get(symbol)
        if p is None:
            print(f"  {symbol}: sem resposta")
            continue
        dif = zc - p
        marca = "  <<< É ESTE" if abs(dif) < 0.51 else ""
        print(f"  {symbol} = {p:8.2f}   ZC=F - contrato = {dif:+7.2f}{marca}")
    u, z = precos.get("ZCU26.CBT"), precos.get("ZCZ26.CBT")
    if u and z:
        print(f"\n  spread set->dez = {z - u:+.2f} c/bu")
        print("  (o degrau observado na serie do painel foi +31,75)")


def secao_quote() -> None:
    """Bônus: /v7/quote traz underlyingSymbol, mas costuma dar 429."""
    print(f"\n{'=' * 78}\n/v7/quote — underlyingSymbol (exige crumb)\n{'=' * 78}")
    for tentativa in range(1, 5):
        try:
            s = requests.Session()
            s.headers.update(HEADERS)
            s.get("https://fc.yahoo.com", timeout=30)
            crumb = s.get(
                "https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=30
            ).text.strip()
            if not crumb or "<" in crumb or " " in crumb:
                raise RuntimeError(f"crumb inválido: {crumb!r}")
            r = s.get(
                "https://query1.finance.yahoo.com/v7/finance/quote",
                params={"symbols": ",".join(CONTINUOS + CONTRATOS), "crumb": crumb},
                timeout=30,
            )
            r.raise_for_status()
            for q in r.json()["quoteResponse"]["result"]:
                print(f"\n{q['symbol']}")
                for campo in (
                    "underlyingSymbol",
                    "shortName",
                    "contractSymbol",
                    "headSymbolAsString",
                    "regularMarketPrice",
                    "regularMarketPreviousClose",
                    "regularMarketChangePercent",
                    "openInterest",
                    "expireIsoDate",
                ):
                    if campo in q:
                        print(f"  {campo:28} {q[campo]}")
            bruto = next(
                (q for q in r.json()["quoteResponse"]["result"] if q["symbol"] == "ZC=F"),
                None,
            )
            if bruto:
                print("\nPAYLOAD CRU — ZC=F")
                print(json.dumps(bruto, indent=2, ensure_ascii=False, sort_keys=True))
            return
        except Exception as e:  # noqa: BLE001
            espera = 2**tentativa
            print(f"  tentativa {tentativa} falhou ({e}); espera {espera}s")
            time.sleep(espera)
    print("  /v7/quote indisponível — o veredito do /v8/chart acima é o que vale")


if __name__ == "__main__":
    veredito(secao_chart())
    secao_quote()
