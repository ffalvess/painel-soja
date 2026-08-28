"""Sonda temporária: dados para a análise de oportunidade (bloco A).

Segunda rodada. A primeira errou o filtro do IBGE — casou tabelas de
agrotóxico de 2006 porque a expressão pegava "condição do produtor" nas
classificações, não no nome da tabela. Agora filtra pelo nome da tabela e
exige período 2017.

Também descobre a que corresponde cada preço da StoneX (R$ 3.060 / 5.814 /
10.404), que a primeira rodada achou mas não soube interpretar.

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
API = "https://servicodados.ibge.gov.br/api/v3/agregados"


def get(url, **kw):
    kw.setdefault("timeout", 90)
    return requests.get(url, headers=HEADERS, **kw)


def tabelas_2017():
    """Tabelas do Censo 2017 cujo NOME fala de lavoura temporária ou soja."""
    print(f"{'=' * 78}\nA2 — tabelas do Censo Agropecuário 2017\n{'=' * 78}")
    r = get(API)
    r.raise_for_status()
    achados = []
    for p in r.json():
        nome_p = (p.get("nome") or "")
        if "censo agropecu" not in nome_p.lower():
            continue
        for ag in p.get("agregados") or []:
            nome = ag.get("nome") or ""
            # o nome da TABELA, não das classificações
            if re.search(r"lavoura tempor|soja", nome, re.I):
                achados.append((ag.get("id"), nome, nome_p))
    print(f"  {len(achados)} tabela(s):")
    for tid, nome, pesq in achados[:20]:
        print(f"    {tid:>6}  {nome[:100]}")
        print(f"            ({pesq[:70]})")
    return achados


def detalha(tid):
    r = get(f"{API}/{tid}/metadados")
    if not r.ok:
        print(f"    {tid}: metadados {r.status_code}")
        return
    m = r.json()
    per = m.get("periodicidade") or {}
    if str(per.get("fim")) != "2017":
        print(f"    {tid}: período termina em {per.get('fim')} — ignorando")
        return
    print(f"\n  === tabela {tid} — {m.get('nome','')[:95]}")
    print(f"      período {per.get('inicio')}–{per.get('fim')}")
    for v in (m.get("variaveis") or [])[:8]:
        print(f"      var {v['id']}: {v['nome'][:75]} ({v.get('unidade','')})")
    for c in (m.get("classificacoes") or []):
        cats = c.get("categorias") or []
        nome_c = c.get("nome") or ""
        soja = [k for k in cats if re.fullmatch(r"\s*soja.*", (k.get("nome") or ""), re.I)]
        area = re.search(r"grupos de área|área total", nome_c, re.I)
        marca = ""
        if soja:
            marca = f"  <<< SOJA em {[(k['id'], k['nome'][:30]) for k in soja][:2]}"
        if area:
            marca = f"  <<< FAIXAS DE ÁREA ({len(cats)})"
        print(f"      classif {c['id']}: {nome_c[:55]} — {len(cats)} cat.{marca}")
        if area:
            for k in cats[:14]:
                print(f"          {k['id']:>8}  {k['nome'][:44]}")


def stonex():
    """A que corresponde cada preço? Extrai o contexto em volta dos valores."""
    print(f"\n{'=' * 78}\nA1 — o que a StoneX vende por R$ 3.060 / 5.814 / 10.404\n{'=' * 78}")
    for url in (
        "https://loja.stonex.com/products/graos-premium-relatorios-de-mercado",
        "https://loja.stonex.com/collections/graos",
    ):
        try:
            r = get(url, timeout=45)
            txt = re.sub(r"<[^>]+>", " ", r.text)
            txt = re.sub(r"\s+", " ", txt)
            print(f"\n  {r.status_code}  {url.rsplit('/', 1)[-1]}")
            for m in re.finditer(r"R\$\s?[\d.]+,\d{2}", txt):
                ini = max(0, m.start() - 140)
                print(f"     …{txt[ini:m.end() + 60]}…")
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO: {str(e)[:90]}")
        time.sleep(2)


def main():
    try:
        for tid, _, _ in tabelas_2017()[:8]:
            detalha(tid)
            time.sleep(0.6)
    except Exception as e:  # noqa: BLE001
        print(f"  IBGE falhou: {str(e)[:140]}")
    stonex()


if __name__ == "__main__":
    main()
