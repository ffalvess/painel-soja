#!/usr/bin/env python3
"""Sonda temporária (rodada 8): caça a API de progresso de safra da CONAB e
valida a extração dos indicadores CEPEA na página do Notícias Agrícolas."""

import json
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
CONAB = "https://portaldeinformacoes.conab.gov.br/"


def sec(t):
    print(f"\n===== {t}")


def main() -> int:  # noqa: C901
    # ---------- A. contexto de "api" no bundle da CONAB ----------
    sec("conab-js-contexto-api")
    try:
        js = requests.get(CONAB + "main-AVLRI5XU.js", headers=UA, timeout=40).text
        for m in re.finditer(r"api", js):
            frag = js[max(0, m.start() - 120): m.start() + 160]
            if any(k in frag for k in ("http", "url", "URL", "endpoint", "/v1")):
                print("...", " ".join(frag.split()), "\n")
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    sec("conab-js-rotas")
    try:
        js = requests.get(CONAB + "main-AVLRI5XU.js", headers=UA, timeout=40).text
        rotas = sorted(set(re.findall(r'path\s*:\s*"([^"]{2,60})"', js)))
        print("rotas:", rotas[:40])
        paths = sorted(set(re.findall(r'"(/[a-z0-9][\w./-]{3,60})"', js)))
        print("paths:", paths[:60])
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    sec("conab-api-candidatos")
    cands = [
        "api/v1/progresso-safra", "api/v1/progressoSafra", "api/v1/progresso",
        "api/v1/safra/progresso", "api/v1/graos/progresso-safra",
        "api/v1/", "api/", "api/v1/produtos", "api/v1/safras",
        "downloads/arquivos/ProgressoSafraSemanal.txt",
        "downloads/arquivos/SerieHistoricaProgresso.txt",
        "downloads/arquivos/AcompanhamentoSafraBrasileira.txt",
    ]
    for c in cands:
        try:
            r = requests.get(CONAB + c, headers=UA, timeout=30)
            body = " ".join(r.text[:220].split()) if r.text else ""
            print(f"{c}: {r.status_code} ({len(r.content)}b) {body[:160]}")
        except Exception as e:  # noqa: BLE001
            print(f"{c}: EXC {type(e).__name__}")

    # ---------- B. Notícias Agrícolas: tabelas de indicadores da soja ----------
    sec("na-soja-tabelas")
    try:
        r = requests.get(
            "https://www.noticiasagricolas.com.br/cotacoes/soja", headers=UA, timeout=40
        )
        print("status:", r.status_code, "bytes:", len(r.content))
        html = r.text
        blocos = re.findall(
            r'<h2>\s*<a[^>]*title="([^"]+)".*?<table[^>]*>(.*?)</table>',
            html, re.S,
        )
        print("blocos encontrados:", len(blocos))
        for titulo, tabela in blocos:
            linhas = re.findall(r"<tr>(.*?)</tr>", tabela, re.S)
            dados = []
            for ln in linhas:
                celulas = [
                    " ".join(re.sub(r"<[^>]+>", "", c).split())
                    for c in re.findall(r"<td[^>]*>(.*?)</td>", ln, re.S)
                ]
                if celulas:
                    dados.append(celulas)
            print(f"  - {titulo!r}: {dados}")
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    sec("na-pagina-historico")
    try:
        r = requests.get(
            "https://www.noticiasagricolas.com.br/cotacoes/soja/"
            "soja-indicador-cepea-esalq-porto-paranagua",
            headers=UA, timeout=40,
        )
        print("status:", r.status_code, "bytes:", len(r.content))
        linhas = re.findall(r"<tr>(.*?)</tr>", r.text, re.S)[:12]
        for ln in linhas:
            celulas = [
                " ".join(re.sub(r"<[^>]+>", "", c).split())
                for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", ln, re.S)
            ]
            if celulas:
                print("   ", celulas)
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    return 0


if __name__ == "__main__":
    sys.exit(main())
