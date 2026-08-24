#!/usr/bin/env python3
"""Sonda temporária: descobre a qual serviço do USDA a chave pertence e qual
esquema de autenticação ela usa. Nunca imprime a chave."""

import json
import os
import sys

import requests

KEY = os.environ.get("USDA_FAS_KEY", "")
UA = {"User-Agent": "painel-soja/1.0", "Accept": "application/json"}


def sec(t):
    print(f"\n===== {t}")


def tenta(nome, url, headers=None, params=None):
    try:
        r = requests.get(
            url, headers={**UA, **(headers or {})}, params=params or {}, timeout=40
        )
        corpo = " ".join(r.text[:220].split())
        print(f"  [{r.status_code}] {nome}  {corpo}")
        return r
    except Exception as e:  # noqa: BLE001
        print(f"  [EXC] {nome}  {type(e).__name__}: {str(e)[:120]}")
        return None


def main() -> int:  # noqa: C901
    if not KEY:
        print("USDA_FAS_KEY não definida")
        return 1
    print(f"chave presente ({len(KEY)} caracteres)")

    # ---------- 1. NASS Quick Stats (o e-mail de confirmação tem esse formato)
    sec("NASS Quick Stats")
    r = tenta(
        "quickstats api_GET soja",
        "https://quickstats.nass.usda.gov/api/api_GET/",
        params={
            "key": KEY,
            "commodity_desc": "SOYBEANS",
            "year": "2026",
            "agg_level_desc": "NATIONAL",
            "statisticcat_desc": "PRODUCTION",
            "format": "JSON",
        },
    )
    if r is not None and r.ok:
        try:
            data = r.json().get("data", [])
            print(f"  registros: {len(data)}")
            for d in data[:4]:
                print("   ", {k: d[k] for k in list(d)[:12]})
        except Exception as e:  # noqa: BLE001
            print("  json:", e)

    tenta(
        "quickstats param_values (fonte viva?)",
        "https://quickstats.nass.usda.gov/api/get_param_values/",
        params={"key": KEY, "param": "source_desc"},
    )

    # ---------- 2. FAS: variações de host, caminho e header
    sec("FAS PSD — combinações")
    bases = [
        "https://apps.fas.usda.gov/OpenData/api/psd",
        "https://api.fas.usda.gov/api/psd",
        "https://apps.fas.usda.gov/PSDOnlineApi/api/psd",
    ]
    auths = [
        ("header API_KEY", {"API_KEY": KEY}, {}),
        ("header X-Api-Key", {"X-Api-Key": KEY}, {}),
        ("header api_key", {"api_key": KEY}, {}),
        ("query api_key", {}, {"api_key": KEY}),
        ("query API_KEY", {}, {"API_KEY": KEY}),
    ]
    for base in bases:
        for nome, h, p in auths:
            tenta(f"{base.split('//')[1][:38]}… /commodities · {nome}",
                  base + "/commodities", h, p)

    # ---------- 3. FAS: outros serviços da mesma chave
    sec("FAS — outros endpoints")
    for nome, url in (
        ("esr commodities", "https://apps.fas.usda.gov/OpenData/api/esr/commodities"),
        ("esr countries", "https://apps.fas.usda.gov/OpenData/api/esr/countries"),
        ("gats hs6", "https://apps.fas.usda.gov/OpenData/api/gats/commodities"),
    ):
        tenta(nome, url, {"API_KEY": KEY})

    # ---------- 4. ERS (outra API do USDA que emite chaves nesse formato)
    sec("ERS Data API")
    tenta(
        "ers arms",
        "https://api.ers.usda.gov/data/arms/surveys",
        params={"api_key": KEY},
    )

    # ---------- 5. api.data.gov (chave federal genérica)
    sec("api.data.gov")
    tenta(
        "nass via api.data.gov",
        "https://api.nal.usda.gov/fdc/v1/foods/search",
        params={"api_key": KEY, "query": "soybean", "pageSize": 1},
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
