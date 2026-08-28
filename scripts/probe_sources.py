"""Sonda temporária: frete rodoviário de grãos.

A lacuna: o basis do interior embute frete até o porto, e sem medir frete não
dá para separar "o comprador sumiu" de "o frete subiu" — nem dizer quanto dos
R$ 12,40 entre Rondonópolis e Rio Verde é logística.

Candidatas, da mais desejável para a menos:

  1. Notícias Agrícolas — já é fonte do painel e a estrutura de tabela é
     conhecida. Se publicar frete por rota, resolve.
  2. SIFRECA/ESALQ — a referência do setor. Pode exigir cadastro.
  3. ANTT dados abertos (CKAN) — piso mínimo de frete é norma publicada,
     R$/km por eixos. Dá o piso legal, não o praticado.
  4. OSRM público — distância rodoviária praça→porto, que multiplica o piso.
  5. ANP — diesel, que não é frete mas explica a variação.

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

# lon,lat — o OSRM pede nessa ordem, ao contrário do resto do mundo
PONTOS = {
    "Sorriso/MT": (-55.7203, -12.5453),
    "Rondonópolis/MT": (-54.6356, -16.4673),
    "Rio Verde/GO": (-50.9331, -17.7975),
    "Paranaguá/PR": (-48.5225, -25.5163),
    "Santos/SP": (-46.3336, -23.9608),
}


def get(url, **kw):
    kw.setdefault("timeout", 45)
    return requests.get(url, headers=HEADERS, **kw)


def cab(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def noticias_agricolas():
    cab("1 — Notícias Agrícolas: existe página de frete?")
    for url in (
        "https://www.noticiasagricolas.com.br/cotacoes/fretes",
        "https://www.noticiasagricolas.com.br/cotacoes/frete",
        "https://www.noticiasagricolas.com.br/cotacoes/logistica",
    ):
        try:
            r = get(url)
            print(f"  {r.status_code}  {url.rsplit('/', 1)[-1]}  {len(r.content)} B")
            if not r.ok:
                continue
            # título e as primeiras linhas de cada tabela
            tabelas = re.findall(r"<table[^>]*>(.*?)</table>", r.text, re.S)
            print(f"     {len(tabelas)} tabela(s)")
            for i, t in enumerate(tabelas[:4]):
                linhas = re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)[:3]
                for ln in linhas:
                    cels = [re.sub(r"<[^>]+>", " ", c) for c in
                            re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", ln, re.S)]
                    cels = [re.sub(r"\s+", " ", c).strip() for c in cels]
                    if any(cels):
                        print(f"     t{i}: {cels[:6]}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO {url[-28:]}: {type(e).__name__}: {str(e)[:80]}")
        time.sleep(1.5)


def sifreca():
    cab("2 — SIFRECA/ESALQ: aberto ou exige cadastro?")
    for url in (
        "https://sifreca.esalq.usp.br/",
        "https://sifreca.esalq.usp.br/mercado/graos",
        "https://esalqlog.esalq.usp.br/sifreca/",
    ):
        try:
            r = get(url)
            txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))
            trava = re.search(r"(login|cadastr|assinante|senha|associado)", txt, re.I)
            print(f"  {r.status_code}  {url}  {len(r.content)} B"
                  f"  {'TRAVA: ' + trava.group(1) if trava else 'sem trava aparente'}")
            if r.ok:
                print(f"     {txt[:260]}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO: {type(e).__name__}: {str(e)[:80]}")
        time.sleep(1.5)


def antt():
    cab("3 — ANTT dados abertos: piso mínimo de frete")
    try:
        r = get("https://dados.antt.gov.br/api/3/action/package_search",
                params={"q": "piso mínimo frete rodoviário", "rows": 8})
        print(f"  {r.status_code}  CKAN")
        if r.ok:
            d = r.json().get("result", {})
            print(f"  {d.get('count')} conjunto(s)")
            for p in d.get("results", [])[:6]:
                print(f"    · {p.get('title', '')[:80]}")
                print(f"      id={p.get('name')}  atualizado={p.get('metadata_modified', '')[:10]}")
                for rec in (p.get("resources") or [])[:4]:
                    print(f"        [{rec.get('format')}] {(rec.get('name') or '')[:50]}")
                    print(f"          {(rec.get('url') or '')[:120]}")
    except Exception as e:  # noqa: BLE001
        print(f"  ERRO: {type(e).__name__}: {str(e)[:110]}")


def osrm():
    cab("4 — OSRM público: distância rodoviária praça → porto")
    rotas = [("Sorriso/MT", "Paranaguá/PR"), ("Rondonópolis/MT", "Santos/SP"),
             ("Rio Verde/GO", "Paranaguá/PR"), ("Rio Verde/GO", "Santos/SP")]
    for orig, dest in rotas:
        a, b = PONTOS[orig], PONTOS[dest]
        url = (f"https://router.project-osrm.org/route/v1/driving/"
               f"{a[0]},{a[1]};{b[0]},{b[1]}?overview=false")
        try:
            r = get(url)
            if r.ok:
                rt = (r.json().get("routes") or [{}])[0]
                km = (rt.get("distance") or 0) / 1000
                h = (rt.get("duration") or 0) / 3600
                print(f"  {r.status_code}  {orig:>18} → {dest:<14} {km:7.0f} km  {h:5.1f} h")
            else:
                print(f"  {r.status_code}  {orig} → {dest}  {r.text[:90]}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO {orig}→{dest}: {type(e).__name__}: {str(e)[:70]}")
        time.sleep(1.2)


def anp():
    cab("5 — ANP: série de preço do diesel")
    alvos = [
        ("CKAN", "https://dados.gov.br/api/3/action/package_search",
         {"q": "preços combustíveis revenda", "rows": 5}),
    ]
    for nome, url, params in alvos:
        try:
            r = get(url, params=params)
            print(f"  {r.status_code}  {nome}")
            if r.ok:
                d = r.json().get("result", {})
                print(f"  {d.get('count')} conjunto(s)")
                for p in d.get("results", [])[:5]:
                    print(f"    · {p.get('title', '')[:78]}")
                    for rec in (p.get("resources") or [])[:3]:
                        print(f"        [{rec.get('format')}] {(rec.get('url') or '')[:110]}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO {nome}: {type(e).__name__}: {str(e)[:90]}")


def main():
    for fn in (noticias_agricolas, sifreca, antt, osrm, anp):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            print(f"  {fn.__name__} falhou: {type(e).__name__}: {str(e)[:120]}")


if __name__ == "__main__":
    main()
