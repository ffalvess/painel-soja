"""Sonda temporária: extrai os números da matéria do Canal Rural.

Objetivo: conferir a consistência do painel (indicador CEPEA, prêmio de porto,
praças do físico, câmbio, CBOT) contra uma fonte independente.

Rodar pelo workflow `probe.yml` e ler os logs. Remover depois.
"""

import html
import re

import requests

URL = (
    "https://www.canalrural.com.br/agricultura/projeto-soja-brasil/"
    "negocios-da-soja-melhoram-mas-distancia-entre-compradores-e-vendedores-"
    "limita-negocios/"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def limpa(bruto: str) -> str:
    """HTML -> texto corrido, preservando quebras de parágrafo e tabelas."""
    s = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", bruto)
    s = re.sub(r"(?i)</(p|div|h[1-6]|li|tr|br)\s*>", "\n", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</t[dh]\s*>", " | ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\xa0]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def main() -> None:
    r = requests.get(URL, headers=HEADERS, timeout=45)
    print("status:", r.status_code, "| bytes:", len(r.content))
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"

    texto = limpa(r.text)

    # data de publicação
    for pat in (
        r'"datePublished"\s*:\s*"([^"]+)"',
        r'"dateModified"\s*:\s*"([^"]+)"',
        r'property="article:published_time"\s+content="([^"]+)"',
    ):
        m = re.search(pat, r.text)
        if m:
            print("data:", pat.split('"')[1], "=", m.group(1))

    print(f"\n{'=' * 78}\nTEXTO (linhas com número)\n{'=' * 78}")
    for linha in texto.split("\n"):
        linha = linha.strip()
        if len(linha) < 3:
            continue
        if re.search(r"\d", linha):
            print(" ", linha[:300])

    print(f"\n{'=' * 78}\nTEXTO COMPLETO (primeiros 9000 caracteres)\n{'=' * 78}")
    print(texto[:9000])


if __name__ == "__main__":
    main()
