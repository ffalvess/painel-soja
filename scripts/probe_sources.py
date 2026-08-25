#!/usr/bin/env python3
"""Sonda temporária: mapeia o serviço ESR (Export Sales) da API do USDA/FAS.

Precisa confirmar: códigos das commodities, forma da resposta, nomes dos
campos, unidade dos valores e a convenção de marketYear na virada do
ano-safra. Nunca imprime a chave.
"""

import json
import os
import sys

import requests

BASE = "https://api.fas.usda.gov/api"
KEY = os.environ.get("USDA_FAS_KEY", "")
H = {"X-Api-Key": KEY, "Accept": "application/json", "User-Agent": "painel-soja/1.0"}


def sec(t):
    print(f"\n===== {t}")


def api(path, servico="esr"):
    return requests.get(f"{BASE}/{servico}{path}", headers=H, timeout=45)


def main() -> int:  # noqa: C901
    if not KEY:
        print("sem chave")
        return 1

    sec("esr/commodities")
    r = api("/commodities")
    print("status:", r.status_code, "bytes:", len(r.content))
    alvos = {}
    if r.ok:
        dados = r.json()
        print("total:", len(dados), "| chaves:", list(dados[0]) if dados else None)
        for c in dados:
            nome = json.dumps(c, ensure_ascii=False).lower()
            if any(k in nome for k in ("soybean", "corn")):
                print("  ", c)
                alvos[c.get("commodityName", "?")] = c.get("commodityCode")

    sec("esr/countries (amostra + China)")
    r = api("/countries")
    print("status:", r.status_code)
    if r.ok:
        d = r.json()
        print("total:", len(d), "| chaves:", list(d[0]) if d else None)
        for c in d:
            if "china" in json.dumps(c, ensure_ascii=False).lower():
                print("  ", c)

    sec("esr/unitsOfMeasure")
    r = api("/unitsOfMeasure")
    print("status:", r.status_code)
    if r.ok:
        print("  ", json.dumps(r.json(), ensure_ascii=False)[:500])

    # usa o código da soja em grão para explorar a série
    codigo = None
    for nome, cod in alvos.items():
        if "soybean" in nome.lower() and not any(
            x in nome.lower() for x in ("meal", "oil", "cake")
        ):
            codigo = cod
            print(f"\ncódigo escolhido para a soja em grão: {cod} ({nome})")
            break
    codigo = codigo or "801"

    sec("esr/exports — variantes de caminho")
    for path in (
        f"/exports/commodityCode/{codigo}/allCountries/marketYear/2026",
        f"/exports/commodityCode/{codigo}/allCountries/marketYear/2025",
        f"/exports/commodityCode/{codigo}/countryCode/1220/marketYear/2026",
    ):
        r = api(path)
        print(f"\n  {path}")
        print(f"  -> {r.status_code} ({len(r.content)} bytes)")
        if r.ok:
            d = r.json()
            print("  registros:", len(d))
            if d:
                print("  campos:", list(d[0]))
                for rec in d[:3]:
                    print("   ", json.dumps(rec, ensure_ascii=False))
                # maior data e soma da última semana
                datas = sorted({x.get("weekEndingDate") for x in d if x.get("weekEndingDate")})
                if datas:
                    ult = datas[-1]
                    linhas = [x for x in d if x.get("weekEndingDate") == ult]
                    soma = sum(x.get("weeklyExports") or 0 for x in linhas)
                    acum = sum(x.get("accumulatedExports") or 0 for x in linhas)
                    pend = sum(x.get("outstandingSales") or 0 for x in linhas)
                    print(f"  primeira semana: {datas[0]} | última: {ult} ({len(datas)} semanas)")
                    print(f"  SOMA última semana: embarques={soma:,.0f} "
                          f"acumulado={acum:,.0f} em_aberto={pend:,.0f}")
                    print("  >>> confronto de unidade: a meta do WASDE para soja EUA é "
                          "45,18 Mt = 45.180.000 t")

    sec("esr/exports — anos disponíveis")
    for ano in (2024, 2025, 2026, 2027):
        r = api(f"/exports/commodityCode/{codigo}/allCountries/marketYear/{ano}")
        n = len(r.json()) if r.ok else 0
        datas = []
        if r.ok and n:
            datas = sorted({x.get("weekEndingDate") for x in r.json()})
        print(f"  {ano}: status={r.status_code} registros={n}"
              + (f" | {datas[0]} .. {datas[-1]}" if datas else ""))

    sec("esr/datareleasedates")
    for p in ("/datareleasedates", "/exports/datareleasedates"):
        r = api(p)
        print(f"  {p} -> {r.status_code} | {r.text[:200] if r.ok else ''}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
