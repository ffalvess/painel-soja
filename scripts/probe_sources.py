#!/usr/bin/env python3
"""Sonda temporária (rodada 9): onde vive a API do portal da CONAB e quais
fontes publicam o progresso de plantio/colheita no Brasil."""

import re
import sys

import requests

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def sec(t):
    print(f"\n===== {t}")


def main() -> int:  # noqa: C901
    sec("conab-js-urls-absolutas")
    for js in ("main-AVLRI5XU.js", "scripts-Y6FOZT2A.js"):
        try:
            t = requests.get(
                "https://portaldeinformacoes.conab.gov.br/" + js, headers=UA, timeout=45
            ).text
            urls = sorted(set(re.findall(r'https?://[\w.-]+(?:/[\w./?=&%-]*)?', t)))
            urls = [u for u in urls if "w3.org" not in u and "schema" not in u]
            print(f"-- {js}: {len(urls)} urls")
            for u in urls[:40]:
                print("   ", u)
        except Exception as e:  # noqa: BLE001
            print("EXC:", e)

    sec("conab-hosts-api")
    for url in (
        "https://portaldeinformacoes.conab.gov.br/download",
        "https://portaldeinformacoes.conab.gov.br/publico/paginado",
        "https://api.conab.gov.br/api/v1/publico/paginado",
        "https://portaldeinformacoes.conab.gov.br/backend/api/v1/publico/paginado",
    ):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            ct = r.headers.get("Content-Type", "?")
            print(f"{url} -> {r.status_code} ({len(r.content)}b) {ct}")
            if "json" in ct:
                print("   ", r.text[:600])
        except Exception as e:  # noqa: BLE001
            print(f"{url}: EXC {type(e).__name__}")

    # ---------- progresso de plantio no Brasil ----------
    sec("br-progresso-fontes")
    fontes = [
        ("deral-pr-boletim",
         "https://www.agricultura.pr.gov.br/deral/BoletimSemanal"),
        ("deral-pr-plantio",
         "https://www.agricultura.pr.gov.br/system/files/publico/safras/plantio_colheita.xls"),
        ("imea-home", "https://www.imea.com.br/imea-site/"),
        ("imea-relatorios", "https://www.imea.com.br/imea-site/relatorios-mercado"),
        ("conab-boletim-graos",
         "https://www.conab.gov.br/info-agro/safras/graos/boletim-da-safra-de-graos"),
        ("na-plantio",
         "https://www.noticiasagricolas.com.br/noticias/plantio"),
        ("usda-fas-brasil",
         "https://apps.fas.usda.gov/psdonline/api/download/commodity?commodityCode=2222000"),
    ]
    for nome, url in fontes:
        try:
            r = requests.get(url, headers=UA, timeout=35)
            txt = " ".join(r.text.split())
            print(f"\n{nome}: {r.status_code} ({len(r.content)}b) ct={r.headers.get('Content-Type','?')}")
            for kw in ("plantio", "Plantio", "PLANTIO", "colheita", "semeadura"):
                i = txt.find(kw)
                if i > 0:
                    print(f"   contém {kw!r}: ...{txt[max(0,i-150):i+300]}...")
                    break
        except Exception as e:  # noqa: BLE001
            print(f"{nome}: EXC {type(e).__name__} {str(e)[:120]}")

    sec("psd-usda-online")
    # PSD Online: estimativas oficiais do USDA para a safra brasileira
    for url in (
        "https://apps.fas.usda.gov/psdonline/app/index.html",
        "https://apps.fas.usda.gov/psdonline/api/psd/commodity/2222000/country/BR/year/2026",
        "https://apps.fas.usda.gov/OpenData/api/psd/commodity/2222000/country/BR/year/2026",
    ):
        try:
            r = requests.get(url, headers=UA, timeout=35)
            print(f"{url} -> {r.status_code} ({len(r.content)}b)")
            if "json" in r.headers.get("Content-Type", ""):
                print("   ", r.text[:500])
        except Exception as e:  # noqa: BLE001
            print(f"{url}: EXC {type(e).__name__}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
