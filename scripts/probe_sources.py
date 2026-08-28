"""Sonda temporária: dados para a análise de oportunidade (bloco A do plano).

Duas perguntas que o WebSearch não respondeu:

  A2 — quantos produtores de soja existem, e de que tamanho? O IBGE tem o
       número no Censo Agropecuário 2017, mas via API SIDRA, que a rede
       daqui bloqueia. A tabela é descoberta pelo nome no catálogo, não
       chutada por ID — mesma disciplina do USDA e do Pink Sheet.

  A1 — os concorrentes publicam preço? A busca só devolveu páginas de
       produto sem valor. Confirmar se é "sob consulta" mesmo, porque isso
       muda o que dá para afirmar no documento.

Rodar pelo workflow `probe.yml` e ler os logs. Remover depois.
"""

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
}

CATALOGO = "https://servicodados.ibge.gov.br/api/v3/agregados"
SIDRA = "https://servicodados.ibge.gov.br/api/v3/agregados"

# Páginas de produto dos concorrentes — só para ver se o preço é público.
CONCORRENTES = [
    ("SAFRAS pacote análises", "https://safras.com.br/produto/plataforma-safras-pacote-analises/"),
    ("StoneX grãos premium", "https://loja.stonex.com/products/graos-premium-relatorios-de-mercado"),
    ("StoneX loja grãos", "https://loja.stonex.com/collections/graos"),
]


def get(url, **kw):
    kw.setdefault("timeout", 90)
    return requests.get(url, headers=HEADERS, **kw)


def acha_tabelas():
    """Catálogo do IBGE, filtrado pelo Censo Agropecuário."""
    print(f"{'=' * 78}\nA2 — catálogo IBGE: tabelas do Censo Agropecuário\n{'=' * 78}")
    r = get(CATALOGO)
    print(f"  status {r.status_code}, {len(r.content):,} B")
    r.raise_for_status()
    pesquisas = r.json()

    alvos = []
    for p in pesquisas:
        nome = (p.get("nome") or "").lower()
        if "censo agropecu" not in nome:
            continue
        for ag in p.get("agregados") or []:
            n = (ag.get("nome") or "")
            if re.search(r"lavoura tempor|soja|grupos de área|condição do produtor", n, re.I):
                alvos.append((p.get("id"), ag.get("id"), n))

    print(f"  {len(alvos)} tabela(s) candidata(s):")
    for _, tid, n in alvos[:25]:
        print(f"    {tid:>6}  {n[:110]}")
    return alvos


def metadados(tid):
    """Variáveis e classificações da tabela — para montar a consulta certa."""
    r = get(f"{SIDRA}/{tid}/metadados")
    if not r.ok:
        print(f"    metadados {tid}: {r.status_code}")
        return None
    m = r.json()
    print(f"\n  --- tabela {tid}: {m.get('nome','')[:100]}")
    print(f"      período: {(m.get('periodicidade') or {}).get('inicio')} "
          f"a {(m.get('periodicidade') or {}).get('fim')}")
    for v in (m.get("variaveis") or [])[:6]:
        print(f"      var {v['id']}: {v['nome'][:80]} ({v.get('unidade','')})")
    for c in (m.get("classificacoes") or [])[:6]:
        cats = c.get("categorias") or []
        soja = [k for k in cats if "soja" in (k.get("nome") or "").lower()]
        print(f"      classif {c['id']}: {c['nome'][:60]} — {len(cats)} categorias"
              + (f"  [SOJA: {[(k['id'], k['nome'][:40]) for k in soja][:3]}]" if soja else ""))
        if re.search(r"grupos de área|área total", c.get("nome") or "", re.I):
            print(f"        faixas: {[k['nome'][:26] for k in cats[:12]]}")
    return m


def preco_publico():
    print(f"\n{'=' * 78}\nA1 — preço dos concorrentes é público?\n{'=' * 78}")
    for rot, url in CONCORRENTES:
        try:
            r = get(url, timeout=45)
            txt = re.sub(r"<[^>]+>", " ", r.text)
            txt = re.sub(r"\s+", " ", txt)
            # procura padrões de preço em reais
            precos = re.findall(r"R\$\s?[\d.]+,\d{2}", txt)[:8]
            sob = bool(re.search(r"sob consulta|solicite|fale com|consulte", txt, re.I))
            print(f"  {r.status_code}  {rot}")
            print(f"       preços na página: {precos or 'nenhum'}")
            print(f"       menciona 'sob consulta/fale com': {'sim' if sob else 'não'}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO  {rot}: {str(e)[:90]}")
        time.sleep(2)


def main():
    try:
        alvos = acha_tabelas()
    except Exception as e:  # noqa: BLE001
        print(f"  catálogo falhou: {str(e)[:140]}")
        alvos = []

    for _, tid, _ in alvos[:4]:
        try:
            metadados(tid)
        except Exception as e:  # noqa: BLE001
            print(f"    erro em {tid}: {str(e)[:90]}")
        time.sleep(1)

    preco_publico()

    print(f"\n{'=' * 78}\nPRÓXIMO PASSO\n{'=' * 78}")
    print("  Com o id da tabela, da variável e da classificação de grupos de área,")
    print("  monta-se a consulta de valores. Sem isso o número de produtores de")
    print("  soja por faixa de tamanho fica sem fonte — e vai para o documento")
    print("  como lacuna assumida, não como estimativa inventada.")


if __name__ == "__main__":
    main()
