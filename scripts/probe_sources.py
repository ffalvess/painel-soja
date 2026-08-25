"""Sonda temporária: confere o físico do painel contra o Notícias Agrícolas.

A matéria do Canal Rural (fonte Safras & Mercado) traz Rio Verde/GO a R$ 138,00
e Rondonópolis/MT a R$ 138,00, enquanto o painel mostra R$ 130,00 e R$ 141,00.
Antes de concluir que são só fontes diferentes, é preciso ver se o painel está
lendo a tabela do Notícias Agrícolas corretamente.

Rodar pelo workflow `probe.yml` e ler os logs. Remover depois.
"""

import re
import sys

sys.path.insert(0, "scripts")

import requests  # noqa: E402

URL = "https://www.noticiasagricolas.com.br/cotacoes/soja"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def main() -> None:
    r = requests.get(URL, headers=HEADERS, timeout=45)
    print("status:", r.status_code, "| bytes:", len(r.content))
    r.raise_for_status()
    bruto = r.text

    # Todas as tabelas, com cabeçalho, para ver qual coluna o coletor lê e se
    # existe mais de uma cotação por praça (balcão x posto, à vista x a prazo).
    tabelas = re.findall(r"(?is)<table.*?</table>", bruto)
    print(f"\n{len(tabelas)} tabela(s) na página")

    for i, t in enumerate(tabelas):
        titulo = ""
        # legenda/caption ou o h2/h3 imediatamente antes da tabela
        m = re.search(r"(?is)<caption[^>]*>(.*?)</caption>", t)
        if m:
            titulo = re.sub(r"<[^>]+>", " ", m.group(1))
        else:
            pos = bruto.find(t)
            antes = bruto[max(0, pos - 1200) : pos]
            hs = re.findall(r"(?is)<h[1-4][^>]*>(.*?)</h[1-4]>", antes)
            if hs:
                titulo = re.sub(r"<[^>]+>", " ", hs[-1])
        titulo = re.sub(r"\s+", " ", titulo).strip()

        linhas = re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", t)
        print(f"\n{'=' * 78}\nTABELA {i}  —  {titulo!r}  ({len(linhas)} linhas)\n{'=' * 78}")
        for linha in linhas[:22]:
            cels = re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", linha)
            cels = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip() for c in cels]
            cels = [c for c in cels if c]
            if cels:
                print("   " + " | ".join(cels))

    print(f"\n{'=' * 78}\nBUSCA DIRETA POR PRAÇA\n{'=' * 78}")
    texto = re.sub(r"<[^>]+>", " ", bruto)
    texto = re.sub(r"[ \t\xa0]+", " ", texto)
    for praca in ("Rio Verde", "Rondon", "Sorriso", "Jata", "Cascavel", "Dourados"):
        for m in re.finditer(praca, texto):
            trecho = texto[m.start() : m.start() + 160].replace("\n", " ")
            print(f"  {praca:12} …{trecho}")


if __name__ == "__main__":
    main()
