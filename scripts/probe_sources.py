"""Sonda temporária: contagem de produtores de soja (bloco A2).

Terceira rodada. A segunda listou as 36 tabelas certas mas detalhou só as 8
primeiras, que por ordem de ID eram todas de 2006 — a tabela que interessa,
a 6965 ("Número de estabelecimentos agropecuários com lavoura temporária"),
estava na lista e nunca foi aberta. Agora vai direto pelo ID.

Fluxo: metadados -> descobre variável de contagem, categoria SOJA e a
classificação de faixa de área -> monta a consulta de valores sozinha.
Nada de ID chutado: tudo sai dos metadados em tempo de execução.

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
API = "https://servicodados.ibge.gov.br/api/v3/agregados"
ALVOS = [6965]

# A rodada anterior pediu N1|N3 com todas as faixas e ficou 17 min baixando —
# o `timeout` do requests é entre bytes, então um corpo gigante não estoura.
# Só Brasil, e um teto explícito de tamanho.
LOCALIDADES = "N3[all]"
TETO_BYTES = 8 * 1024 * 1024


def get(url, **kw):
    kw.setdefault("timeout", 90)
    return requests.get(url, **kw, headers=HEADERS)


def get_limitado(url):
    """Baixa em stream e desiste se passar do teto — sonda não pode travar."""
    with requests.get(url, headers=HEADERS, timeout=90, stream=True) as r:
        if not r.ok:
            return r.status_code, None
        buf = bytearray()
        for pedaco in r.iter_content(65536):
            buf += pedaco
            if len(buf) > TETO_BYTES:
                print(f"  >{TETO_BYTES // 1024} KiB — abortando o download")
                return r.status_code, None
        return r.status_code, bytes(buf)


def acha_cat(classificacoes, padrao):
    """Devolve (id_classificacao, id_categoria, nome) da 1a categoria que casa."""
    for c in classificacoes:
        for k in c.get("categorias") or []:
            if re.search(padrao, (k.get("nome") or ""), re.I):
                return c["id"], k["id"], k["nome"]
    return None, None, None


def metadados(tid):
    r = get(f"{API}/{tid}/metadados")
    if not r.ok:
        print(f"  {tid}: metadados HTTP {r.status_code}")
        return None
    m = r.json()
    per = m.get("periodicidade") or {}
    print(f"\n{'=' * 78}\ntabela {tid} — {(m.get('nome') or '')[:110]}")
    print(f"  período {per.get('inicio')}–{per.get('fim')}")
    if str(per.get("fim")) != "2017":
        print("  não é 2017 — ignorando")
        return None
    for v in m.get("variaveis") or []:
        print(f"  var {v['id']}: {v['nome'][:80]} ({v.get('unidade', '')})")
    for c in m.get("classificacoes") or []:
        cats = c.get("categorias") or []
        print(f"  classif {c['id']}: {(c.get('nome') or '')[:60]} — {len(cats)} cat.")
        soja = [k for k in cats if re.search(r"\bsoja\b", k.get("nome") or "", re.I)]
        faixa = re.search(r"grupos de área|área total|classes de área", c.get("nome") or "", re.I)
        for k in soja[:3]:
            print(f"      SOJA -> {k['id']}  {k['nome'][:60]}")
        if faixa:
            for k in cats:
                print(f"      faixa  {k['id']:>8}  {(k.get('nome') or '')[:50]}")
    return m


def valores(tid, m):
    """Monta e executa a consulta de valores a partir dos metadados."""
    variaveis = m.get("variaveis") or []
    classif = m.get("classificacoes") or []

    contagem = next(
        (v for v in variaveis if re.search(r"n[úu]mero de estabelecimentos", v["nome"], re.I)),
        None,
    )
    if not contagem:
        print("  sem variável de contagem de estabelecimentos — pulando valores")
        return
    c_soja, k_soja, nome_soja = acha_cat(classif, r"^\s*soja\b")
    faixa = next(
        (c for c in classif
         if re.search(r"grupos de área|área total|classes de área", c.get("nome") or "", re.I)),
        None,
    )

    partes = []
    if c_soja:
        partes.append(f"{c_soja}[{k_soja}]")
    if faixa:
        partes.append(f"{faixa['id']}[all]")
    q = f"{API}/{tid}/periodos/2017/variaveis/{contagem['id']}?localidades={LOCALIDADES}"
    if partes:
        q += "&classificacao=" + "|".join(partes)

    print(f"\n  var usada: {contagem['id']} — {contagem['nome'][:70]}")
    print(f"  soja: {c_soja}[{k_soja}] {nome_soja}")
    print(f"  faixa: {faixa['id'] if faixa else '—'} {(faixa or {}).get('nome', '')[:50]}")
    print(f"  GET {q[:180]}")

    status, corpo = get_limitado(q)
    print(f"  HTTP {status}  {len(corpo) if corpo else 0} B")
    if not corpo:
        return
    dados = json.loads(corpo)
    # v3 devolve [{variavel, resultados:[{classificacoes, series:[{localidade, serie}]}]}]
    for v in dados:
        for res in v.get("resultados") or []:
            rot = " / ".join(
                str(list((c.get("categoria") or {}).values())[0])[:34]
                for c in res.get("classificacoes") or []
            )
            # só as UFs que interessam ao Centro-Oeste + as duas grandes do Sul
            uf = ("Mato Grosso", "Mato Grosso do Sul", "Goiás", "Distrito Federal",
                  "Paraná", "Rio Grande do Sul")
            linhas = []
            for s in res.get("series") or []:
                loc = (s.get("localidade") or {}).get("nome", "?")
                if loc not in uf:
                    continue
                val = list((s.get("serie") or {}).values())
                linhas.append(f"{loc}={val[0] if val else '?'}")
            if linhas:
                print(f"    [{rot}]  " + "  ".join(linhas))


def main():
    for tid in ALVOS:
        try:
            m = metadados(tid)
            if m:
                valores(tid, m)
        except Exception as e:  # noqa: BLE001
            print(f"  {tid} falhou: {type(e).__name__}: {str(e)[:140]}")
        time.sleep(1.5)


if __name__ == "__main__":
    main()
