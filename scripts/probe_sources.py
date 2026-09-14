"""Sonda temporária: ajuste diário da B3 por vencimento.

Alvo: o contrato **SFI** (Futuro de Soja com Liquidação Financeira, referenciado
ao Indicador ESALQ/B3 Paranaguá). Não confundir com o **SJC**, que é
minicontrato liquidado contra a CME — a base do SJC com Chicago é zero por
construção, e é justamente o SJC que a tabela "BRASIL (B3)" do Notícias
Agrícolas publica (`Soja (NOV 26) 27,28` contra CBOT NOV26 convertido 27,2878).

O boletim legado `www2.bmf.com.br` está desligado. Ordem de tentativa:

  1. sistemaswebb3-derivativos — proxy JSON da SPA de Ajustes do Pregão,
     parâmetros em base64
  2. arquivos.b3.com.br — arquivos diários públicos
  3. página de Ajustes do Pregão em HTML
  4. Notícias Agrícolas — página do SFI com mais de um vencimento

Procurar em cada uma: código, vencimento, ajuste, **volume e contratos em
aberto**. Sem volume não dá para separar preço negociado de ajuste carimbado.

Rodar pelo workflow `probe.yml` e ler os logs. Remover depois.
"""

import base64
import json
import re
import time

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "application/json, text/html;q=0.9,*/*;q=0.8",
}


def get(url, **kw):
    kw.setdefault("timeout", 30)
    return requests.get(url, headers=HEADERS, **kw)


def cab(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def amostra(txt, n=400):
    return re.sub(r"\s+", " ", txt)[:n]


def b64(obj):
    return base64.b64encode(json.dumps(obj).encode()).decode()


def proxy_derivativos():
    cab("1 — sistemaswebb3-derivativos: proxy JSON dos ajustes do pregão")
    hoje = time.strftime("%d/%m/%Y")
    # a SPA manda {"language":"pt-br"} ou {"dateValue":"dd/mm/aaaa",...} em base64
    tentativas = [
        ("DerivativeAdjustments sem data",
         f"https://sistemaswebb3-derivativos.b3.com.br/DerivativeAdjustmentsProxy/"
         f"DerivativeAdjustments/GetDerivativeAdjustments/{b64({'language': 'pt-br'})}"),
        ("DerivativeAdjustments com data",
         f"https://sistemaswebb3-derivativos.b3.com.br/DerivativeAdjustmentsProxy/"
         f"DerivativeAdjustments/GetDerivativeAdjustments/"
         f"{b64({'dateValue': hoje, 'language': 'pt-br'})}"),
        ("DerivativeQuotation por mercadoria",
         f"https://sistemaswebb3-derivativos.b3.com.br/DerivativeQuotationProxy/"
         f"DerivativeQuotation/GetQuotation/"
         f"{b64({'commodity': 'SFI', 'language': 'pt-br'})}"),
    ]
    for nome, url in tentativas:
        try:
            r = get(url)
            ct = r.headers.get("Content-Type", "")[:40]
            print(f"\n  {r.status_code}  {len(r.content):>8} B  {ct}  — {nome}")
            if not r.ok:
                print(f"     {amostra(r.text, 200)}")
                continue
            try:
                d = r.json()
            except Exception:  # noqa: BLE001
                print(f"     não é JSON: {amostra(r.text, 220)}")
                continue
            print(f"     chaves: {list(d)[:8] if isinstance(d, dict) else type(d).__name__}")
            bruto = json.dumps(d, ensure_ascii=False)
            print(f"     amostra: {bruto[:500]}")
            for alvo in ("SFI", "SJC", "CCM", "SOJA", "Soja"):
                if alvo in bruto:
                    i = bruto.index(alvo)
                    print(f"     <<< achou {alvo!r}: …{bruto[max(0, i - 120):i + 260]}…")
                    break
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO {nome}: {type(e).__name__}: {str(e)[:110]}")
        time.sleep(1.5)


def arquivos_b3():
    cab("2 — arquivos.b3.com.br: arquivos diários de derivativos")
    for nome, url in (
        ("índice de tabelas", "https://arquivos.b3.com.br/tabelas"),
        ("API de tabelas", "https://arquivos.b3.com.br/api/tables"),
        ("listagem de arquivos", "https://arquivos.b3.com.br/api/download/requestname?fileName=BDRatio"),
    ):
        try:
            r = get(url)
            print(f"  {r.status_code}  {len(r.content):>8} B  {nome}")
            if r.ok:
                print(f"     {amostra(r.text, 300)}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO {nome}: {type(e).__name__}: {str(e)[:100]}")
        time.sleep(1.2)


def pagina_ajustes():
    cab("3 — b3.com.br: página de ajustes em HTML e o boletim legado")
    for nome, url in (
        ("ajustes do pregão (atual)",
         "https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/"
         "market-data/consultas/mercado-de-derivativos/ajustes-do-pregao/"),
        ("boletim legado (esperado morto)",
         "https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/"
         "lum-ajustes-do-pregao-ptBR.asp"),
    ):
        try:
            r = get(url)
            txt = re.sub(r"<[^>]+>", " ", r.text)
            tem_tabela = "<table" in r.text.lower()
            print(f"  {r.status_code}  {len(r.content):>8} B  tabela={tem_tabela}  — {nome}")
            if r.ok:
                for alvo in ("SFI", "SJC", "Soja", "SOJA"):
                    if alvo in r.text:
                        i = r.text.index(alvo)
                        print(f"     <<< {alvo!r} no HTML: …{amostra(r.text[max(0, i - 150):i + 250])}…")
                        break
                else:
                    print(f"     {amostra(txt, 240)}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO {nome}: {type(e).__name__}: {str(e)[:100]}")
        time.sleep(1.5)


def noticias_agricolas():
    cab("4 — Notícias Agrícolas: existe página do SFI com vários vencimentos?")
    for url in (
        "https://www.noticiasagricolas.com.br/cotacoes/soja/soja-bmf",
        "https://www.noticiasagricolas.com.br/cotacoes/soja/soja-b3",
        "https://www.noticiasagricolas.com.br/cotacoes/bolsas/b3",
        "https://www.noticiasagricolas.com.br/cotacoes/soja",
    ):
        try:
            r = get(url)
            print(f"\n  {r.status_code}  {len(r.content):>8} B  {url.rsplit('/', 1)[-1]}")
            if not r.ok:
                continue
            # títulos de todas as tabelas, para achar qualquer coisa de B3
            titulos = re.findall(r'<h2>\s*<a[^>]*title="([^"]+)"', r.text)
            achou = [t for t in titulos if re.search(r"b3|bmf|bolsa", t, re.I)]
            print(f"     {len(titulos)} tabela(s); com B3/BMF no título: {achou}")
            # a tabela BRASIL (B3), para registrar quantos vencimentos traz
            m = re.search(r'title="BRASIL \(B3\)".*?<table[^>]*>(.*?)</table>', r.text, re.S)
            if m:
                linhas = re.findall(r"<tr>(.*?)</tr>", m.group(1), re.S)
                for ln in linhas[:8]:
                    cels = [" ".join(re.sub(r"<[^>]+>", " ", c).split())
                            for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", ln, re.S)]
                    if any(cels):
                        print(f"       {cels}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO: {type(e).__name__}: {str(e)[:100]}")
        time.sleep(1.5)


def main():
    for fn in (proxy_derivativos, arquivos_b3, pagina_ajustes, noticias_agricolas):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            print(f"  {fn.__name__} falhou: {type(e).__name__}: {str(e)[:130]}")


if __name__ == "__main__":
    main()
