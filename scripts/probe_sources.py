"""Sonda temporária: extrai os números da matéria do Canal Rural.

A URL direta devolve 403 para o IP do Actions (proteção anti-robô). O feed RSS
do mesmo site é lido pelo coletor sem problema, então a sonda tenta várias
rotas até uma responder.

Rodar pelo workflow `probe.yml` e ler os logs. Remover depois.
"""

import html
import re
import xml.etree.ElementTree as ET

import requests

SLUG = (
    "negocios-da-soja-melhoram-mas-distancia-entre-compradores-e-vendedores-"
    "limita-negocios"
)
BASE = "https://www.canalrural.com.br/agricultura/projeto-soja-brasil/"
URL = BASE + SLUG + "/"

NAVEGADOR = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.4 Safari/605.1.15"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/",
    "Upgrade-Insecure-Requests": "1",
}


def limpa(bruto: str) -> str:
    s = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", bruto)
    s = re.sub(r"(?i)</(p|div|h[1-6]|li|tr)\s*>", "\n", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</t[dh]\s*>", " | ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\xa0]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


def mostra(rotulo: str, texto: str) -> None:
    print(f"\n{'=' * 78}\n{rotulo} — {len(texto)} caracteres\n{'=' * 78}")
    print(texto[:12000])


def tenta_direto() -> str:
    """A página em si, com cabeçalhos de navegador."""
    for url in (URL, URL + "amp/", BASE + SLUG + "/amp/", URL + "?amp=1"):
        try:
            r = requests.get(url, headers=NAVEGADOR, timeout=45, allow_redirects=True)
            print(f"  {r.status_code}  {url}")
            if r.ok and len(r.content) > 3000:
                r.encoding = r.apparent_encoding or "utf-8"
                return limpa(r.text)
        except Exception as e:  # noqa: BLE001
            print(f"  ERRO  {url}: {e}")
    return ""


def tenta_rss() -> str:
    """O feed do site — o coletor já o lê sem tomar 403."""
    try:
        r = requests.get(
            "https://www.canalrural.com.br/feed/", headers=NAVEGADOR, timeout=45
        )
        print(f"  feed: {r.status_code}, {len(r.content)} bytes")
        r.raise_for_status()
        root = ET.fromstring(r.content)
        achou = ""
        print("  itens no feed:")
        for item in root.iter("item"):
            link = (item.findtext("link") or "").strip()
            titulo = (item.findtext("title") or "").strip()
            print(f"    - {titulo[:90]}")
            if SLUG in link:
                partes = [titulo, item.findtext("pubDate") or ""]
                for tag in ("description", "{http://purl.org/rss/1.0/modules/content/}encoded"):
                    v = item.findtext(tag)
                    if v:
                        partes.append(limpa(v))
                achou = "\n".join(partes)
        return achou
    except Exception as e:  # noqa: BLE001
        print(f"  ERRO no feed: {e}")
        return ""


def main() -> None:
    print("=== 1. página direta ===")
    texto = tenta_direto()
    if texto:
        mostra("PÁGINA", texto)
        return

    print("\n=== 2. feed RSS ===")
    texto = tenta_rss()
    if texto:
        mostra("ITEM DO FEED", texto)
        return

    print("\nNenhuma rota funcionou.")


if __name__ == "__main__":
    main()
