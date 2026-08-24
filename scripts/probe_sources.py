#!/usr/bin/env python3
"""Sonda temporária: qual a unidade do prêmio de porto no Notícias Agrícolas."""

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


def main() -> int:
    r = requests.get(
        "https://www.noticiasagricolas.com.br/cotacoes/soja", headers=UA, timeout=40
    )
    html = r.text
    print("status:", r.status_code)

    for alvo in ("Prêmio Soja Paranaguá", "Soja - Bolsa de Chicago"):
        print(f"\n===== bloco: {alvo}")
        i = html.find(alvo)
        if i < 0:
            # o título pode vir com entidades HTML
            i = html.find("mio Soja Paranagu")
        if i < 0:
            print("  não encontrado")
            continue
        trecho = html[max(0, i - 700): i + 2600]
        # cabeçalhos da tabela costumam carregar a unidade
        print("  THs:", re.findall(r"<th[^>]*>(.*?)</th>", trecho, re.S)[:8])
        print("  texto:", " ".join(re.sub(r"<[^>]+>", " ", trecho).split())[:900])

    print("\n===== página dedicada do prêmio")
    for slug in (
        "/cotacoes/soja/soja-premio-paranagua-pr",
        "/cotacoes/soja/premio-soja-paranagua",
        "/cotacoes/soja/soja-premio-de-exportacao-paranagua",
    ):
        try:
            rr = requests.get(
                "https://www.noticiasagricolas.com.br" + slug, headers=UA, timeout=30
            )
            print(f"  {slug} -> {rr.status_code}")
            if rr.ok:
                txt = " ".join(re.sub(r"<[^>]+>", " ", rr.text).split())
                for chave in ("centavos", "cents", "US$", "bushel", "unidade"):
                    j = txt.find(chave)
                    if j > 0:
                        print(f"     {chave!r}: ...{txt[max(0,j-160):j+200]}...")
                        break
        except Exception as e:  # noqa: BLE001
            print(f"  {slug} -> EXC {type(e).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
