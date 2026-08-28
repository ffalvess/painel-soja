"""Sonda temporária: preço do frete rodoviário (rodada 2).

A rodada 1 resolveu a distância — o OSRM público responde e devolveu
Sorriso→Paranaguá 2.147 km, Rio Verde→Paranaguá 1.263 km. Falta o preço.

Descartados na rodada 1: Notícias Agrícolas (404 em /fretes, /frete e
/logistica), SIFRECA/ESALQ (200 mas exige login), dados.gov.br (401, passou a
exigir chave). A busca no CKAN da ANTT por "piso mínimo frete rodoviário" só
trouxe autos de infração — a consulta é que estava ruim.

Agora: consultas melhores no CKAN da ANTT, a calculadora do piso mínimo (que
pode ter API), e o IMEA, que publica frete de Mato Grosso.

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


def get(url, **kw):
    kw.setdefault("timeout", 40)
    return requests.get(url, headers=HEADERS, **kw)


def cab(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def antt_ckan():
    cab("1 — CKAN da ANTT: consultas melhores para o piso mínimo")
    for q in ("piso mínimo", "piso", "tabela de frete", "transporte rodoviário de cargas",
              "ANTT resolução piso mínimo"):
        try:
            r = get("https://dados.antt.gov.br/api/3/action/package_search",
                    params={"q": q, "rows": 6})
            if not r.ok:
                print(f"  {r.status_code}  q={q!r}")
                continue
            d = r.json().get("result", {})
            print(f"\n  q={q!r} -> {d.get('count')} conjunto(s)")
            for p in d.get("results", [])[:6]:
                titulo = p.get("title", "")
                marca = "  <<<" if re.search(r"piso|frete|tabela", titulo, re.I) else ""
                print(f"    · {titulo[:76]}{marca}")
                if marca:
                    for rec in (p.get("resources") or [])[:6]:
                        print(f"        [{rec.get('format')}] {(rec.get('name') or '')[:46]}")
                        print(f"          {(rec.get('url') or '')[:118]}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO q={q!r}: {type(e).__name__}: {str(e)[:80]}")
        time.sleep(1.2)


def antt_piso():
    cab("2 — Calculadora do piso mínimo da ANTT: tem API?")
    for url in (
        "https://piso.antt.gov.br/",
        "https://piso-api.antt.gov.br/",
        "https://piso.antt.gov.br/api/tabelas",
        "https://piso.antt.gov.br/api/v1/tabelas",
        "https://www.gov.br/antt/pt-br/assuntos/transporte-de-cargas/piso-minimo-de-frete",
    ):
        try:
            r = get(url)
            ct = r.headers.get("Content-Type", "")[:40]
            print(f"  {r.status_code}  {len(r.content):>8} B  {ct:<26} {url}")
            if r.ok and "json" in ct:
                print(f"     {r.text[:400]}")
            elif r.ok and "html" in ct:
                txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))
                # links para planilha/norma dentro da página
                for m in re.finditer(r'href="([^"]+\.(?:xlsx|xls|csv|pdf))"', r.text, re.I):
                    print(f"     arquivo: {m.group(1)[:110]}")
                # a página cita valores por eixo?
                v = re.findall(r"R\$\s?\d+[.,]\d+", txt)[:5]
                if v:
                    print(f"     valores no texto: {v}")
                print(f"     {txt[:200]}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO {url[-34:]}: {type(e).__name__}: {str(e)[:70]}")
        time.sleep(1.2)


def imea():
    cab("3 — IMEA: indicador de frete de Mato Grosso")
    for url in (
        "https://www.imea.com.br/imea-site/relatorios-mercado",
        "https://www.imea.com.br/imea-site/indicador-frete",
        "https://publicacoes.imea.com.br/",
    ):
        try:
            r = get(url)
            print(f"  {r.status_code}  {len(r.content):>8} B  {url}")
            if r.ok:
                txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))
                for m in re.finditer(r"[^.]{0,70}frete[^.]{0,70}", txt, re.I):
                    print(f"     …{m.group(0).strip()[:140]}…")
                    break
                for m in list(re.finditer(r'href="([^"]*frete[^"]*)"', r.text, re.I))[:5]:
                    print(f"     link: {m.group(1)[:110]}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO: {type(e).__name__}: {str(e)[:70]}")
        time.sleep(1.2)


def osrm_todas():
    cab("4 — OSRM: todas as praças do painel × dois portos")
    # lon, lat
    pracas = {
        "Sorriso/MT": (-55.7203, -12.5453),
        "Rondonópolis/MT": (-54.6356, -16.4673),
        "Primavera do Leste/MT": (-54.2960, -15.5561),
        "Rio Verde/GO": (-50.9331, -17.7975),
        "Jataí/GO": (-51.7211, -17.8814),
        "Campo Grande/MS": (-54.6464, -20.4697),
        "Maracaju/MS": (-55.1678, -21.6142),
        "São Gabriel do Oeste/MS": (-54.5678, -19.3958),
        "Oeste da Bahia/BA": (-45.0036, -12.1522),  # Luís Eduardo Magalhães
    }
    portos = {
        "Paranaguá/PR": (-48.5225, -25.5163),
        "Santos/SP": (-46.3336, -23.9608),
    }
    print(f"  {'praça':<26}" + "".join(f"{p:>16}" for p in portos))
    for nome, a in pracas.items():
        linha = f"  {nome:<26}"
        for _, b in portos.items():
            url = (f"https://router.project-osrm.org/route/v1/driving/"
                   f"{a[0]},{a[1]};{b[0]},{b[1]}?overview=false")
            try:
                r = get(url)
                km = ((r.json().get("routes") or [{}])[0].get("distance") or 0) / 1000 \
                    if r.ok else None
                linha += f"{km:>13.0f} km" if km else f"{'—':>16}"
            except Exception as e:  # noqa: BLE001
                linha += f"{type(e).__name__[:14]:>16}"
            time.sleep(1.1)
        print(linha)


def main():
    for fn in (antt_ckan, antt_piso, imea, osrm_todas):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            print(f"  {fn.__name__} falhou: {type(e).__name__}: {str(e)[:120]}")


if __name__ == "__main__":
    main()
