#!/usr/bin/env python3
"""Sonda temporária: mapeia os dados PSD em api.fas.usda.gov (header X-Api-Key)."""

import json
import os
import sys

import requests

BASE = "https://api.fas.usda.gov/api/psd"
KEY = os.environ.get("USDA_FAS_KEY", "")
H = {"X-Api-Key": KEY, "Accept": "application/json", "User-Agent": "painel-soja/1.0"}


def sec(t):
    print(f"\n===== {t}")


def api(path):
    r = requests.get(BASE + path, headers=H, timeout=40)
    return r


def main() -> int:  # noqa: C901
    if not KEY:
        print("sem chave")
        return 1

    sec("commodities com 'soybean'")
    r = api("/commodities")
    print("status:", r.status_code)
    soja = []
    if r.ok:
        for c in r.json():
            if "oybean" in c.get("commodityName", ""):
                soja.append(c)
                print("  ", c)

    sec("commodityAttributes")
    r = api("/commodityAttributes")
    print("status:", r.status_code)
    if r.ok:
        for a in r.json():
            print("  ", a)

    sec("countries — BR, US, World")
    r = api("/countries")
    print("status:", r.status_code)
    if r.ok:
        data = r.json()
        print("  total:", len(data), "| chaves:", list(data[0]) if data else None)
        for c in data:
            blob = json.dumps(c, ensure_ascii=False)
            if "Brazil" in blob or "United States" in blob or "World" in blob:
                print("  ", c)

    sec("unitsOfMeasure")
    r = api("/unitsOfMeasure")
    if r.ok:
        print("  ", json.dumps(r.json(), ensure_ascii=False)[:600])

    codigo = soja[0]["commodityCode"] if soja else "2222000"
    for pais in ("BR", "US"):
        sec(f"psd soja {pais} 2026 (código {codigo})")
        r = api(f"/commodity/{codigo}/country/{pais}/year/2026")
        print("status:", r.status_code, "bytes:", len(r.content))
        if r.ok:
            data = r.json()
            print("  registros:", len(data))
            for rec in data[:16]:
                print("   ", rec)

    sec("psd mundo — variantes")
    for path in (
        f"/commodity/{codigo}/world/year/2026",
        f"/commodity/{codigo}/country/R00/year/2026",
        f"/commodity/{codigo}/country/00/year/2026",
        f"/commodity/{codigo}/regions/year/2026",
    ):
        r = api(path)
        corpo = json.dumps(r.json(), ensure_ascii=False)[:280] if r.ok else r.text[:160]
        print(f"  {path} -> {r.status_code} | {' '.join(corpo.split())}")

    sec("anos disponíveis (BR)")
    for ano in (2024, 2025, 2026, 2027):
        r = api(f"/commodity/{codigo}/country/BR/year/{ano}")
        print(f"  {ano}: status={r.status_code} registros={len(r.json()) if r.ok else 0}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
