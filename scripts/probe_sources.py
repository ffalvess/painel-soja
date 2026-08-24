#!/usr/bin/env python3
"""Sonda temporária: mapeia a API PSD do USDA/FAS.

Lê a chave de USDA_FAS_KEY (secret do Actions). Nunca imprime a chave.
"""

import json
import os
import sys

import requests

BASE = "https://apps.fas.usda.gov/OpenData/api/psd"
KEY = os.environ.get("USDA_FAS_KEY", "")


def sec(t):
    print(f"\n===== {t}")


def api(path, **params):
    """Tenta os dois esquemas de autenticação documentados pela FAS."""
    tentativas = [
        ({"API_KEY": KEY, "Accept": "application/json"}, params),
        ({"Accept": "application/json"}, {**params, "api_key": KEY}),
    ]
    for headers, qs in tentativas:
        r = requests.get(BASE + path, headers=headers, params=qs, timeout=40)
        if r.ok:
            return r
        ultimo = r
    return ultimo


def main() -> int:  # noqa: C901
    if not KEY:
        print("USDA_FAS_KEY não definida — cadastre o secret no repositório.")
        return 1
    print(f"chave presente ({len(KEY)} caracteres)")

    sec("commodities-soja")
    try:
        r = api("/commodities")
        print("status:", r.status_code, "bytes:", len(r.content))
        if r.ok:
            data = r.json()
            soja = [c for c in data if "oybean" in json.dumps(c)]
            for c in soja[:12]:
                print("  ", c)
    except Exception as e:  # noqa: BLE001
        print("EXC:", type(e).__name__, str(e)[:200])

    sec("countries-BR-US-World")
    try:
        r = api("/countries")
        print("status:", r.status_code)
        if r.ok:
            data = r.json()
            print("  total:", len(data), "| exemplo:", data[0] if data else None)
            for c in data:
                blob = json.dumps(c, ensure_ascii=False)
                if any(k in blob for k in ('"BR"', '"US"', "World", "Brazil")):
                    print("  ", c)
    except Exception as e:  # noqa: BLE001
        print("EXC:", type(e).__name__, str(e)[:200])

    sec("commodityAttributes")
    try:
        r = api("/commodityAttributes")
        print("status:", r.status_code)
        if r.ok:
            for a in r.json():
                print("  ", a)
    except Exception as e:  # noqa: BLE001
        print("EXC:", type(e).__name__, str(e)[:200])

    sec("regions")
    try:
        r = api("/regions")
        print("status:", r.status_code)
        if r.ok:
            print("  ", json.dumps(r.json(), ensure_ascii=False)[:800])
    except Exception as e:  # noqa: BLE001
        print("EXC:", type(e).__name__, str(e)[:200])

    for pais in ("BR", "US"):
        sec(f"psd-soja-{pais}-2026")
        try:
            r = api(f"/commodity/2222000/country/{pais}/year/2026")
            print("status:", r.status_code, "bytes:", len(r.content))
            if r.ok:
                data = r.json()
                print("  registros:", len(data))
                for rec in data[:14]:
                    print("   ", rec)
        except Exception as e:  # noqa: BLE001
            print("EXC:", type(e).__name__, str(e)[:200])

    sec("psd-mundo-variantes")
    for path in (
        "/commodity/2222000/world/year/2026",
        "/commodity/2222000/country/R00/year/2026",
        "/commodity/2222000/country/00/year/2026",
        "/commodity/2222000/country/WD/year/2026",
        "/commodity/2222000/country/W00/year/2026",
    ):
        try:
            r = api(path)
            body = r.text[:200] if not r.ok else json.dumps(r.json(), ensure_ascii=False)[:300]
            print(f"  {path} -> {r.status_code} | {body}")
        except Exception as e:  # noqa: BLE001
            print(f"  {path} -> EXC {type(e).__name__}")

    sec("psd-anos-disponiveis")
    for ano in (2025, 2026, 2027):
        try:
            r = api(f"/commodity/2222000/country/BR/year/{ano}")
            n = len(r.json()) if r.ok else 0
            print(f"  {ano}: status={r.status_code} registros={n}")
        except Exception as e:  # noqa: BLE001
            print(f"  {ano}: EXC {type(e).__name__}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
