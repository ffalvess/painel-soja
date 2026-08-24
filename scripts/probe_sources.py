#!/usr/bin/env python3
"""Sonda temporária (rodada 7): endpoints do portal da CONAB (progresso de
safra) e fontes alternativas ao CEPEA para o preço físico no Brasil."""

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


def sec(t):
    print(f"\n===== {t}")


def show(r, snip=700):
    print(f"status={r.status_code} ct={r.headers.get('Content-Type','?')} bytes={len(r.content)}")
    try:
        print("JSON:", json.dumps(r.json(), ensure_ascii=False)[:snip])
    except Exception:
        print("BODY:", " ".join(r.text[:snip].split()))


def main() -> int:  # noqa: C901
    # ---------- A. CONAB: achar a API por trás do portal ----------
    sec("conab-spa-scripts")
    scripts = []
    try:
        r = requests.get(
            "https://portaldeinformacoes.conab.gov.br/progresso-de-safra.html",
            headers=UA, timeout=40,
        )
        print(f"status={r.status_code} bytes={len(r.content)}")
        scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', r.text)
        print("scripts:", scripts[:30])
        refs = sorted(set(re.findall(r'["\']([^"\']*(?:downloads/arquivos|/api/|\.txt|\.json)[^"\']*)["\']', r.text)))
        print("refs no html:", refs[:30])
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    base = "https://portaldeinformacoes.conab.gov.br/"
    for src in scripts[:12]:
        url = src if src.startswith("http") else base + src.lstrip("./")
        sec(f"conab-js {src[:60]}")
        try:
            r = requests.get(url, headers=UA, timeout=40)
            hits = sorted(set(re.findall(
                r'["\']([^"\']*(?:downloads/arquivos/[\w.-]+|/api/[\w./-]+)[^"\']*)["\']', r.text)))
            print(f"status={r.status_code} bytes={len(r.content)} | achados: {hits[:40]}")
        except Exception as e:  # noqa: BLE001
            print("EXC:", e)

    sec("conab-arquivos-candidatos")
    for f in (
        "ProgressoSafraSerie.txt", "ProgressoSafraBrasil.txt",
        "ProgressoDeSafra.txt", "progresso_safra.txt",
        "SerieHistoricaGraos.txt",
    ):
        try:
            r = requests.get(base + "downloads/arquivos/" + f, headers=UA, timeout=40)
            print(f"{f}: status={r.status_code} bytes={len(r.content)}")
        except Exception as e:  # noqa: BLE001
            print(f"{f}: EXC {e}")

    # ---------- B. Alternativas ao CEPEA ----------
    sec("imea-site")
    for url in (
        "https://www.imea.com.br/imea-site/indicador-preco",
        "https://api.imea.com.br/api/v1/indicadores",
        "https://www.imea.com.br/imea-site/api/indicadores",
    ):
        try:
            show(requests.get(url, headers=UA, timeout=30), 500)
        except Exception as e:  # noqa: BLE001
            print(f"{url}: EXC {type(e).__name__} {e}")

    sec("noticias-agricolas-cepea")
    for url in (
        "https://www.noticiasagricolas.com.br/cotacoes/soja/soja-cepea-esalq-paranagua",
        "https://www.noticiasagricolas.com.br/cotacoes/soja",
    ):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            text = " ".join(r.text.split())
            print(f"{url} -> status={r.status_code} bytes={len(r.content)}")
            i = text.upper().find("PARANAGU")
            print("   trecho:", text[max(0, i - 400): i + 1200] if i >= 0 else text[:600])
        except Exception as e:  # noqa: BLE001
            print("EXC:", e)

    sec("cepea-via-http-simples")
    # a proteção é da Cloudflare; testa se o host antigo sem www responde
    for url in (
        "http://cepea.esalq.usp.br/br/indicador/soja.aspx",
        "https://www.cepea.esalq.usp.br/br/indicador/soja.aspx",
    ):
        try:
            r = requests.get(url, headers=UA, timeout=30, allow_redirects=True)
            print(f"{url} -> {r.status_code} ({len(r.content)} bytes) final={r.url}")
        except Exception as e:  # noqa: BLE001
            print(f"{url}: EXC {e}")

    # ---------- C. OI de todos os vencimentos ----------
    sec("yahoo-oi-curva")
    try:
        s = requests.Session()
        s.headers.update(UA)
        s.get("https://fc.yahoo.com", timeout=20)
        crumb = s.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=20).text.strip()
        syms = "ZSU26.CBT,ZSX26.CBT,ZSF27.CBT,ZSH27.CBT,ZSK27.CBT,ZSN27.CBT,ZSQ27.CBT"
        r = s.get(
            "https://query1.finance.yahoo.com/v7/finance/quote",
            params={"symbols": syms, "crumb": crumb}, timeout=25,
        )
        total = 0
        for q in r.json()["quoteResponse"]["result"]:
            oi = q.get("openInterest")
            total += oi or 0
            print(f"  {q['symbol']:12} preço={q.get('regularMarketPrice')} "
                  f"vol={q.get('regularMarketVolume')} OI={oi} exp={q.get('expireIsoDate','')[:10]}")
        print("  soma OI:", total)
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    return 0


if __name__ == "__main__":
    sys.exit(main())
