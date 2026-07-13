#!/usr/bin/env python3
"""Coleta dados de mercado para o Painel Soja.

Roda dentro do GitHub Actions (runner com internet livre). Cada coletor é
independente: se um falhar, a seção correspondente mantém os dados da
execução anterior (lidos de data/data.json) e o erro fica registrado em
`errors` — o painel nunca quebra por causa de uma fonte fora do ar.

Fontes:
  - Yahoo Finance (não oficial): futuros CBOT, Brent, Ibovespa
  - AwesomeAPI: dólar e euro comercial
  - Banco Central (Olinda/PTAX e SGS): PTAX, Selic, CDI, IPCA
  - CEPEA/ESALQ: indicador soja Paranaguá (raspagem best-effort da página pública)
  - Open-Meteo: previsão de chuva em cidades produtoras do Centro-Oeste
  - RSS: Google News, Canal Rural, G1 Agronegócios, Notícias Agrícolas
"""

import datetime as dt
import email.utils
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "data.json"
TIMEOUT = 25
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def get(url: str, **kwargs) -> requests.Response:
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kwargs)
    r.raise_for_status()
    return r


# ---------------------------------------------------------------- cotações

YAHOO_SYMBOLS = [
    ("ZS=F", "Soja CBOT", "¢/bushel"),
    ("ZC=F", "Milho CBOT", "¢/bushel"),
    ("ZM=F", "Farelo de soja", "US$/t curta"),
    ("ZL=F", "Óleo de soja", "¢/lb"),
    ("ZW=F", "Trigo CBOT", "¢/bushel"),
    ("BZ=F", "Petróleo Brent", "US$/barril"),
    ("^BVSP", "Ibovespa", "pontos"),
]


def fetch_yahoo_symbol(symbol: str) -> dict:
    last_err = None
    for host in ("query1", "query2"):
        try:
            r = get(
                f"https://{host}.finance.yahoo.com/v8/finance/chart/{symbol}",
                params={"range": "1mo", "interval": "1d"},
            )
            result = r.json()["chart"]["result"][0]
            meta = result["meta"]
            closes = [
                round(c, 4)
                for c in result["indicators"]["quote"][0]["close"]
                if c is not None
            ]
            price = meta.get("regularMarketPrice")
            if price is None and closes:
                price = closes[-1]
            prev = closes[-2] if len(closes) >= 2 else meta.get("chartPreviousClose")
            change_pct = (
                round((price / prev - 1) * 100, 2) if price and prev else None
            )
            return {
                "price": price,
                "prev_close": prev,
                "change_pct": change_pct,
                "closes": closes,
            }
        except Exception as e:  # noqa: BLE001 - tenta o próximo host
            last_err = e
    raise RuntimeError(f"{symbol}: {last_err}")


def collect_quotes() -> dict:
    items, failed = [], []
    for symbol, name, unit in YAHOO_SYMBOLS:
        try:
            q = fetch_yahoo_symbol(symbol)
            items.append({"symbol": symbol, "name": name, "unit": unit, **q})
        except Exception as e:  # noqa: BLE001
            failed.append(f"{symbol}: {e}")
    if not items:
        raise RuntimeError("; ".join(failed))
    return {"updated_at": now_iso(), "items": items, "failed": failed}


# ---------------------------------------------------------------- câmbio

def collect_fx() -> dict:
    r = get("https://economia.awesomeapi.com.br/json/last/USD-BRL,EUR-BRL")
    data = r.json()

    def pick(key):
        d = data[key]
        return {
            "bid": float(d["bid"]),
            "ask": float(d["ask"]),
            "high": float(d["high"]),
            "low": float(d["low"]),
            "pct_change": float(d["pctChange"]),
        }

    fx = {"updated_at": now_iso(), "usdbrl": pick("USDBRL"), "eurbrl": pick("EURBRL")}

    try:
        end = dt.date.today()
        start = end - dt.timedelta(days=10)
        fmt = "%m-%d-%Y"
        url = (
            "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
            "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
            f"?@dataInicial='{start.strftime(fmt)}'&@dataFinalCotacao='{end.strftime(fmt)}'"
            "&$top=1&$orderby=dataHoraCotacao%20desc&$format=json"
        )
        v = get(url).json()["value"][0]
        fx["ptax"] = {
            "compra": v["cotacaoCompra"],
            "venda": v["cotacaoVenda"],
            "data": v["dataHoraCotacao"][:10],
        }
    except Exception as e:  # noqa: BLE001 - PTAX é complementar
        fx["ptax"] = None
        fx["ptax_error"] = str(e)
    return fx


# ---------------------------------------------------------------- juros/macro

def sgs(codigo: int, ultimos: int = 1) -> list:
    r = get(
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}"
        f"/dados/ultimos/{ultimos}?formato=json"
    )
    return r.json()


def collect_rates() -> dict:
    out = {"updated_at": now_iso()}
    selic = sgs(432)[-1]
    out["selic"] = float(selic["valor"])
    try:
        cdi = sgs(4389)[-1]  # CDI anualizado base 252, % a.a.
        out["cdi"] = float(cdi["valor"])
    except Exception:  # noqa: BLE001
        out["cdi"] = None
    ipca = sgs(433, 12)
    out["ipca_mes"] = {"valor": float(ipca[-1]["valor"]), "data": ipca[-1]["data"]}
    acc = 1.0
    for p in ipca:
        acc *= 1 + float(p["valor"]) / 100
    out["ipca_12m"] = round((acc - 1) * 100, 2)
    return out


# ---------------------------------------------------------------- CEPEA

def collect_cepea() -> dict:
    """Raspagem best-effort da página pública do indicador da soja.

    A CEPEA não tem API gratuita; se o layout da página mudar, esta seção
    simplesmente mantém o valor anterior (ou some do painel).
    """
    r = get("https://www.cepea.esalq.usp.br/br/indicador/soja.aspx")
    text = r.text
    row = re.search(
        r"<td[^>]*>\s*(\d{2}/\d{2}/\d{4})\s*</td>\s*"
        r"<td[^>]*>\s*([\d.]+,\d+)\s*</td>\s*"
        r"<td[^>]*>\s*(-?[\d.]*,?\d+)\s*</td>",
        text,
    )
    if not row:
        raise RuntimeError("padrão da tabela CEPEA não encontrado na página")
    data, valor, var_dia = row.groups()

    def br_float(s: str) -> float:
        return float(s.replace(".", "").replace(",", "."))

    return {
        "updated_at": now_iso(),
        "indicador": {
            "nome": "Indicador Soja CEPEA/ESALQ — Paranaguá (saca 60kg)",
            "data": data,
            "valor": br_float(valor),
            "var_dia_pct": br_float(var_dia),
        },
    }


# ---------------------------------------------------------------- clima

CITIES = [
    ("Sorriso · MT", -12.55, -55.72),
    ("Sinop · MT", -11.86, -55.50),
    ("Rio Verde · GO", -17.79, -50.93),
    ("Dourados · MS", -22.22, -54.81),
]


def collect_weather() -> dict:
    lats = ",".join(str(c[1]) for c in CITIES)
    lons = ",".join(str(c[2]) for c in CITIES)
    r = get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lats,
            "longitude": lons,
            "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
            "forecast_days": 7,
            "timezone": "America/Sao_Paulo",
        },
    )
    payload = r.json()
    if isinstance(payload, dict):
        payload = [payload]
    cities = []
    for (name, _, _), res in zip(CITIES, payload):
        d = res["daily"]
        cities.append(
            {
                "name": name,
                "dates": d["time"],
                "precip": d["precipitation_sum"],
                "tmax": d["temperature_2m_max"],
                "tmin": d["temperature_2m_min"],
            }
        )
    return {"updated_at": now_iso(), "cities": cities}


# ---------------------------------------------------------------- notícias

FEEDS = [
    ("Google News", "https://news.google.com/rss/search?q=soja+OR+%22mercado+de+gr%C3%A3os%22&hl=pt-BR&gl=BR&ceid=BR:pt-419"),
    ("Canal Rural", "https://www.canalrural.com.br/feed/"),
    ("G1 Agronegócios", "https://g1.globo.com/rss/g1/economia/agronegocios/"),
    ("Notícias Agrícolas", "https://www.noticiasagricolas.com.br/rss/noticias"),
]

TAG_RE = re.compile(r"<[^>]+>")


def parse_feed(source: str, url: str) -> list:
    r = get(url)
    root = ET.fromstring(r.content)
    items = []
    for item in root.iter("item"):
        title = html.unescape(TAG_RE.sub("", item.findtext("title") or "")).strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        src = item.findtext("source")
        pub = item.findtext("pubDate")
        published = None
        if pub:
            try:
                published = email.utils.parsedate_to_datetime(pub).isoformat()
            except Exception:  # noqa: BLE001
                pass
        items.append(
            {
                "title": title,
                "link": link,
                "source": (src or source).strip(),
                "published_at": published,
            }
        )
        if len(items) >= 12:
            break
    return items


def collect_news() -> dict:
    items, failed, seen = [], [], set()
    for source, url in FEEDS:
        try:
            for it in parse_feed(source, url):
                key = re.sub(r"\W+", "", it["title"].lower())[:80]
                if key in seen:
                    continue
                seen.add(key)
                items.append(it)
        except Exception as e:  # noqa: BLE001
            failed.append(f"{source}: {e}")
    if not items:
        raise RuntimeError("; ".join(failed))
    items.sort(key=lambda i: i["published_at"] or "", reverse=True)
    return {"updated_at": now_iso(), "items": items[:30], "failed": failed}


# ---------------------------------------------------------------- main

COLLECTORS = {
    "quotes": collect_quotes,
    "fx": collect_fx,
    "rates": collect_rates,
    "cepea": collect_cepea,
    "weather": collect_weather,
    "news": collect_news,
}


def main() -> int:
    old_sections = {}
    if OUT.exists():
        try:
            old_sections = json.loads(OUT.read_text(encoding="utf-8")).get(
                "sections", {}
            )
        except Exception:  # noqa: BLE001
            pass

    sections, errors = {}, []
    for name, collector in COLLECTORS.items():
        try:
            sections[name] = collector()
            print(f"[ok]   {name}")
        except Exception as e:  # noqa: BLE001
            errors.append({"section": name, "error": str(e)})
            sections[name] = old_sections.get(name)
            print(f"[erro] {name}: {e}", file=sys.stderr)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {"generated_at": now_iso(), "sections": sections, "errors": errors},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"gravado {OUT} ({len(errors)} erro(s))")
    # Só falha o job se absolutamente nada funcionou
    return 1 if len(errors) == len(COLLECTORS) else 0


if __name__ == "__main__":
    sys.exit(main())
