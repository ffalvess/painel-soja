"""Sonda temporária, rodada 2: conteúdo das tabelas de soja.

A rodada 1 fechou as portas da B3: o proxy de ajustes devolve 404, o
arquivos.b3.com.br é SPA, e as páginas de ajuste (inclusive a legada) vêm sem
`<table>` no HTML — tudo renderizado no cliente.

O que sobrou: o Notícias Agrícolas tem 13 tabelas em /cotacoes/soja, e entre os
títulos apareceu uma que a rodada anterior não conhecia —
**'Soja CME - B3 (Pregão Regular)'**. O nome diz CME, o que sugere o SJC
(espelho, base zero por construção), mas pode ter vários vencimentos, e é
justamente o controle negativo de que o plano precisa.

Esta rodada despeja o conteúdo das 13 tabelas para decidir:
  - quantos vencimentos a tabela da B3 traz, e em que unidade
  - se algum lugar publica o SFI (liquidado contra o ESALQ/B3 Paranaguá)
  - se há volume ou contratos em aberto junto do preço

Rodar pelo workflow `probe.yml` e ler os logs. Remover depois.
"""

import re
import time

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}
NA_SOJA = "https://www.noticiasagricolas.com.br/cotacoes/soja"


def get(url, **kw):
    kw.setdefault("timeout", 30)
    return requests.get(url, headers=HEADERS, **kw)


def cab(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def celulas(linha_html):
    return [
        " ".join(re.sub(r"<[^>]+>", " ", c).split())
        for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", linha_html, re.S)
    ]


def tabelas_soja():
    cab("1 — as 13 tabelas de /cotacoes/soja, com conteúdo")
    r = get(NA_SOJA)
    print(f"  HTTP {r.status_code}  {len(r.content)} B\n")
    blocos = re.findall(
        r'<h2>\s*<a[^>]*title="([^"]+)".*?<table[^>]*>(.*?)</table>', r.text, re.S
    )
    print(f"  {len(blocos)} tabela(s) casadas pelo padrão do coletor\n")
    for i, (titulo, tabela) in enumerate(blocos):
        linhas = [c for c in (celulas(ln) for ln in
                              re.findall(r"<tr>(.*?)</tr>", tabela, re.S)) if any(c)]
        marca = ""
        if re.search(r"b3|bmf|cme", titulo, re.I):
            marca = "   <<<<<<"
        print(f"  --- [{i}] {titulo!r}  ({len(linhas)} linhas){marca}")
        for ln in linhas[:14]:
            print(f"        {ln}")
    return r.text


def procura_sfi(page: str):
    cab("2 — o SFI aparece em algum lugar da página?")
    achou = False
    for padrao in (r"SFI", r"Liquida[çc][ãa]o Financeira", r"ESALQ/B3\s*-?\s*Paranagu",
                   r"SJC", r"Pregão Regular"):
        for m in list(re.finditer(padrao, page, re.I))[:2]:
            achou = True
            i = m.start()
            trecho = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page[max(0, i - 160):i + 220]))
            print(f"  {padrao!r}: …{trecho}…")
    if not achou:
        print("  nenhum dos termos aparece")


def b3_ultimas_portas():
    cab("3 — últimas portas da B3 antes de desistir")
    hoje = time.strftime("%y%m%d")
    for nome, url in (
        ("BDI legado (zip do pregão)",
         f"https://www.b3.com.br/pesquisapregao/download?filelist=PR{hoje}.zip"),
        ("cotações market-data",
         "https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/"
         "market-data/cotacoes/cotacoes/"),
        ("UP2DATA aberto",
         "https://arquivos.b3.com.br/bdi/table/DerivativesOpenPosition"),
    ):
        try:
            r = get(url, timeout=25)
            ct = r.headers.get("Content-Type", "")[:36]
            print(f"  {r.status_code}  {len(r.content):>9} B  {ct:<36} {nome}")
            if r.ok and len(r.content) < 3000:
                corpo = re.sub(r"\s+", " ", r.text)[:220]
                print(f"     {corpo}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO {nome}: {type(e).__name__}: {str(e)[:90]}")
        time.sleep(1.2)


def main():
    page = ""
    try:
        page = tabelas_soja()
    except Exception as e:  # noqa: BLE001
        print(f"  tabelas_soja falhou: {type(e).__name__}: {str(e)[:120]}")
    if page:
        try:
            procura_sfi(page)
        except Exception as e:  # noqa: BLE001
            print(f"  procura_sfi falhou: {type(e).__name__}: {str(e)[:120]}")
    try:
        b3_ultimas_portas()
    except Exception as e:  # noqa: BLE001
        print(f"  b3_ultimas_portas falhou: {type(e).__name__}: {str(e)[:120]}")


if __name__ == "__main__":
    main()
