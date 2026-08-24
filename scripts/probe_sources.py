#!/usr/bin/env python3
"""Sonda temporária (rodada 6): CEPEA alternativo, open interest por
vencimento e progresso de safra do Brasil."""

import json
import sys
from ftplib import FTP

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


def show(r, snip=900):
    print(f"status={r.status_code} ct={r.headers.get('Content-Type','?')} bytes={len(r.content)}")
    try:
        print("JSON:", json.dumps(r.json(), ensure_ascii=False)[:snip])
    except Exception:
        print("BODY:", " ".join(r.text[:snip].split()))


def main() -> int:  # noqa: C901
    # ---------- A. CEPEA: caminhos alternativos ----------
    cepea = [
        ("widget-92",
         "https://www.cepea.esalq.usp.br/br/widgetproduto.js.php"
         "?fonte=arial&tamanho=10&largura=400px&corfundo=dbd6b2&cortexto=333333"
         "&corlinha=ede9ce&id_indicador[]=92"),
        ("widget-multi",
         "https://www.cepea.esalq.usp.br/br/widgetproduto.js.php"
         "?id_indicador[]=91&id_indicador[]=92&id_indicador[]=93&id_indicador[]=94"),
        ("widget-page", "https://www.cepea.esalq.usp.br/br/widget.aspx"),
        ("org-direct", "https://cepea.org.br/br/indicador/soja.aspx"),
        ("esalq-direct", "https://www.cepea.esalq.usp.br/br/indicador/soja.aspx"),
        ("consulta-bd", "https://www.cepea.esalq.usp.br/br/consultas-ao-banco-de-dados-do-site.aspx"),
        ("xls-soja", "https://www.cepea.esalq.usp.br/br/indicador/series/soja.aspx?id=92"),
    ]
    for name, url in cepea:
        sec(f"cepea-{name}")
        try:
            show(requests.get(url, headers=UA, timeout=30), 1200)
        except Exception as e:  # noqa: BLE001
            print("EXC:", type(e).__name__, e)

    # ---------- B. Open interest por vencimento ----------
    sec("yahoo-quote-oi")
    try:
        s = requests.Session()
        s.headers.update(UA)
        s.get("https://fc.yahoo.com", timeout=20)
        crumb = s.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=20).text.strip()
        r = s.get(
            "https://query1.finance.yahoo.com/v7/finance/quote",
            params={"symbols": "ZSX26.CBT,ZSF27.CBT,ZS=F", "crumb": crumb},
            timeout=25,
        )
        print("status:", r.status_code)
        for q in r.json().get("quoteResponse", {}).get("result", []):
            keys = {k: v for k, v in q.items() if "pen" in k.lower() or "nterest" in k.lower()}
            print(q.get("symbol"), "| campos de OI:", keys or "NENHUM")
            print("   todos os campos:", sorted(q.keys())[:60])
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    sec("cme-ftp-dirs")
    for d in ("pub", "webmthly", "delivery_reports", "grs", "fprf", "daily_volume"):
        try:
            ftp = FTP("ftp.cmegroup.com", timeout=45)
            ftp.login()
            names = ftp.nlst(d)
            ftp.close()
            print(f"{d}: {len(names)} itens ->", names[:12])
        except Exception as e:  # noqa: BLE001
            print(f"{d}: EXC {e}")

    # ---------- C. CONAB: progresso de safra ----------
    base = "https://portaldeinformacoes.conab.gov.br/downloads/arquivos/"
    for fname in (
        "ProgressoSafra.txt",
        "ProgressodeSafra.txt",
        "SerieHistoricaProgressoSafra.txt",
        "ProgressoSafraGraos.txt",
        "CalendarioAgricola.txt",
        "SerieHistoricaCustoProducao.txt",
    ):
        sec(f"conab-{fname}")
        try:
            r = requests.get(base + fname, headers=UA, timeout=45)
            print(f"status={r.status_code} bytes={len(r.content)}")
            if r.ok:
                print("HEAD:", "\n".join(r.text.splitlines()[:5]))
        except Exception as e:  # noqa: BLE001
            print("EXC:", e)

    sec("conab-paginas")
    for url in (
        "https://portaldeinformacoes.conab.gov.br/progresso-de-safra.html",
        "https://portaldeinformacoes.conab.gov.br/safra-serie-historica.html",
    ):
        try:
            r = requests.get(url, headers=UA, timeout=40)
            text = " ".join(r.text.split())
            print(f"{url} -> status={r.status_code} bytes={len(r.content)}")
            import re

            for m in set(re.findall(r"[\w./-]*(?:arquivos|api|json)[\w./?=&-]*", text))[:0] or []:
                pass
            hits = sorted(set(re.findall(r"['\"]([^'\"]*(?:downloads/arquivos|/api/)[^'\"]*)['\"]", text)))
            print("   refs:", hits[:20])
        except Exception as e:  # noqa: BLE001
            print("EXC:", e)

    return 0


if __name__ == "__main__":
    sys.exit(main())
