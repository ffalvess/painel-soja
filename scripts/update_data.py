#!/usr/bin/env python3
"""Coleta dados de mercado para o Painel Soja.

Roda dentro do GitHub Actions (runner com internet livre). Cada coletor é
independente: se um falhar, a seção correspondente mantém os dados da
execução anterior (lidos de data/data.json) e o erro fica registrado em
`errors` — o painel nunca quebra por causa de uma fonte fora do ar.

Fontes:
  - Yahoo Finance (não oficial): futuros CBOT (inclusive curva de
    vencimentos), Brent, Ibovespa e câmbio de fallback
  - AwesomeAPI: dólar e euro comercial (limita IPs do Actions; há fallback)
  - Banco Central (Olinda/PTAX e SGS): PTAX, Selic, CDI, IPCA
  - CEPEA/ESALQ: indicador soja Paranaguá (raspagem best-effort da página pública)
  - USDA/NASS Crop Progress (via API da biblioteca Cornell): safra dos EUA
  - CONAB (série histórica de grãos): safra do Brasil
  - CME Group (FTP público ftp.cmegroup.com): volume de calls/puts de soja
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


def fetch_yahoo_symbol(symbol: str, range_: str = "1mo") -> dict:
    last_err = None
    for host in ("query1", "query2"):
        try:
            r = get(
                f"https://{host}.finance.yahoo.com/v8/finance/chart/{symbol}",
                params={"range": range_, "interval": "1d"},
            )
            result = r.json()["chart"]["result"][0]
            meta = result["meta"]
            quote = result["indicators"]["quote"][0]
            closes = [round(c, 4) for c in quote.get("close") or [] if c is not None]
            price = meta.get("regularMarketPrice")
            if price is None and closes:
                price = closes[-1]
            prev = closes[-2] if len(closes) >= 2 else meta.get("chartPreviousClose")
            change_pct = (
                round((price / prev - 1) * 100, 2) if price and prev else None
            )
            volume = meta.get("regularMarketVolume")
            if volume is None:
                vols = [v for v in quote.get("volume") or [] if v]
                volume = vols[-1] if vols else None
            return {
                "price": price,
                "prev_close": prev,
                "change_pct": change_pct,
                "closes": closes,
                "volume": volume,
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
    fx = {"updated_at": now_iso()}
    try:
        data = get(
            "https://economia.awesomeapi.com.br/json/last/USD-BRL,EUR-BRL"
        ).json()

        def pick(key):
            d = data[key]
            return {
                "bid": float(d["bid"]),
                "ask": float(d["ask"]),
                "high": float(d["high"]),
                "low": float(d["low"]),
                "pct_change": float(d["pctChange"]),
            }

        fx["usdbrl"] = pick("USDBRL")
        fx["eurbrl"] = pick("EURBRL")
        fx["source"] = "AwesomeAPI"
    except Exception as e:  # noqa: BLE001 - a AwesomeAPI limita IPs do Actions (429)
        # Fallback: Yahoo Finance para dólar/euro comerciais
        fx["awesomeapi_error"] = str(e)
        for key, symbol in (("usdbrl", "BRL=X"), ("eurbrl", "EURBRL=X")):
            q = fetch_yahoo_symbol(symbol)
            fx[key] = {
                "bid": q["price"],
                "ask": None,
                "high": None,
                "low": None,
                "pct_change": q["change_pct"],
            }
        fx["source"] = "Yahoo Finance"

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


# ---------------------------------------------------------------- safra

SOY_ACTIVITIES = {
    "planted": "Plantio",
    "emerged": "Emergência",
    "blooming": "Floração",
    "setting pods": "Formação de vagens",
    "dropping leaves": "Queda de folhas",
    "harvested": "Colheita",
}


def collect_safra_us() -> dict:
    """Crop Progress semanal do USDA/NASS via API da biblioteca Cornell.

    O zip da publicação traz `prog_all_tables.csv` com todas as tabelas;
    filtramos as de soja e extraímos a linha-resumo "18 States".
    """
    import csv
    import io
    import zipfile

    meta = get(
        "https://usda.library.cornell.edu/api/v1/release/findByIdentifier/CropProg",
        params={"latest": "true"},
    ).json()
    release = meta["results"][0]
    zip_url = next(f for f in release["files"] if f.endswith(".zip"))
    z = zipfile.ZipFile(io.BytesIO(get(zip_url).content))
    text = z.read("prog_all_tables.csv").decode("cp1252", "replace")

    tables = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) >= 2:
            tables.setdefault(row[0], []).append(row[1:])

    def num(s):
        s = (s or "").strip()
        if s in ("", "-"):
            return 0
        try:
            return int(s)
        except ValueError:
            return None

    out = {
        "released": release["release_datetime"][:10],
        "week_ending": None,
        "progress": [],
        "condition": None,
    }
    for rows in tables.values():
        titles = [r[1] for r in rows if r[0] == "t" and len(r) > 1]
        title = next(
            (t for t in titles if "Soybean" in t and not t.startswith("Crop Progress")),
            None,
        )
        if not title:
            continue
        m = re.search(r"Week Ending ([A-Z][a-z]+ \d+, \d{4})", title)
        if m:
            out["week_ending"] = m.group(1)
        data = {
            r[1]: [num(c) for c in r[2:]]
            for r in rows
            if r[0] == "d" and len(r) > 2 and r[1]
        }
        if "Condition" in title:
            cur = data.get("18 States")
            if cur and len(cur) >= 5:
                cond = {
                    "dist": dict(zip(("vp", "p", "f", "g", "e"), cur)),
                    "gex": cur[3] + cur[4],
                }
                for label, key in (
                    ("Previous week", "gex_prev_week"),
                    ("Previous year", "gex_prev_year"),
                ):
                    v = data.get(label)
                    if v and len(v) >= 5:
                        cond[key] = v[3] + v[4]
                out["condition"] = cond
        else:
            # Colunas: mesma semana do ano passado, semana anterior,
            # semana atual, média de 5 anos
            cur = data.get("18 States")
            if cur and len(cur) >= 4:
                activity = title.replace("Soybeans", "").split("Selected")[0]
                activity = re.sub(r"[^A-Za-z ]", " ", activity).strip()
                label = SOY_ACTIVITIES.get(activity.lower(), activity)
                out["progress"].append(
                    {
                        "label": label,
                        "prev_year": cur[0],
                        "prev_week": cur[1],
                        "current": cur[2],
                        "avg_5y": cur[3],
                    }
                )
    if not out["progress"] and not out["condition"]:
        raise RuntimeError("nenhuma tabela de soja encontrada no Crop Progress")
    return out


def collect_safra_br() -> dict:
    """Série histórica de grãos da CONAB (área, produção e produtividade)."""
    r = get(
        "https://portaldeinformacoes.conab.gov.br/downloads/arquivos/"
        "SerieHistoricaGraos.txt"
    )
    por_safra = {}
    for line in r.text.splitlines()[1:]:
        p = [c.strip() for c in line.split(";")]
        if len(p) < 8 or p[3] != "SOJA":
            continue
        agg = por_safra.setdefault(p[0], {"area": 0.0, "prod": 0.0})
        try:
            agg["area"] += float(p[5])
            agg["prod"] += float(p[6])
        except ValueError:
            continue
    if not por_safra:
        raise RuntimeError("nenhuma linha de SOJA na série da CONAB")
    safras = sorted(por_safra)
    atual, anterior = safras[-1], (safras[-2] if len(safras) > 1 else None)

    def fmt(safra):
        a = por_safra[safra]
        return {
            "safra": safra,
            "area_mil_ha": round(a["area"], 1),
            "producao_mil_t": round(a["prod"], 1),
            "produtividade_kg_ha": round(a["prod"] / a["area"] * 1000, 1)
            if a["area"]
            else None,
        }

    out = {"atual": fmt(atual), "anterior": fmt(anterior) if anterior else None}
    if anterior:
        prev = por_safra[anterior]
        cur = por_safra[atual]
        if prev["prod"]:
            out["var_producao_pct"] = round((cur["prod"] / prev["prod"] - 1) * 100, 1)
        if prev["area"]:
            out["var_area_pct"] = round((cur["area"] / prev["area"] - 1) * 100, 1)
    return out


def collect_safra() -> dict:
    out = {"updated_at": now_iso(), "failed": []}
    for key, fn in (("us", collect_safra_us), ("br", collect_safra_br)):
        try:
            out[key] = fn()
        except Exception as e:  # noqa: BLE001
            out[key] = None
            out["failed"].append(f"{key}: {e}")
    if out["us"] is None and out["br"] is None:
        raise RuntimeError("; ".join(out["failed"]))
    return out


# ---------------------------------------------------------------- curva CBOT

# Meses de vencimento da soja na CBOT (código, mês, rótulo pt-BR)
SOY_MONTHS = [
    ("F", 1, "jan"),
    ("H", 3, "mar"),
    ("K", 5, "mai"),
    ("N", 7, "jul"),
    ("Q", 8, "ago"),
    ("U", 9, "set"),
    ("X", 11, "nov"),
]


def soy_contracts(n: int = 7) -> list:
    """Próximos n vencimentos de soja na CBOT a partir do mês corrente."""
    today = dt.date.today()
    # o contrato vence por volta do dia 15; depois disso pula para o próximo
    cutoff = (today.year, today.month + (1 if today.day > 15 else 0))
    out = []
    for year in range(today.year, today.year + 3):
        for code, month, label in SOY_MONTHS:
            if (year, month) < cutoff:
                continue
            out.append(
                {
                    "symbol": f"ZS{code}{year % 100:02d}.CBT",
                    "label": f"{label}/{year % 100:02d}",
                }
            )
            if len(out) >= n:
                return out
    return out


def collect_curve() -> dict:
    contracts, failed = [], []
    for c in soy_contracts():
        try:
            q = fetch_yahoo_symbol(c["symbol"], range_="5d")
            contracts.append(
                {
                    "symbol": c["symbol"],
                    "label": c["label"],
                    "price": q["price"],
                    "change_pct": q["change_pct"],
                    "volume": q.get("volume"),
                }
            )
        except Exception as e:  # noqa: BLE001
            failed.append(f"{c['symbol']}: {e}")
    if not contracts:
        raise RuntimeError("; ".join(failed))
    return {
        "updated_at": now_iso(),
        "unit": "¢/bushel",
        "contracts": contracts,
        "failed": failed,
    }


# ---------------------------------------------------------------- opções CBOT

def collect_options() -> dict:
    """Volume diário de calls e puts de soja na CBOT.

    Fonte: relatório público `daily_volume.xlsx` no FTP da CME
    (ftp.cmegroup.com), atualizado a cada pregão. O site/API da CME bloqueia
    os IPs do GitHub Actions, mas o FTP é aberto. O arquivo traz volume por
    produto (calls e puts separados); posições em aberto só existem
    agregadas por grupo, então não são publicadas por produto.
    """
    import io
    from ftplib import FTP

    from openpyxl import load_workbook

    buf, last_err = None, None
    for _ in range(3):
        try:
            ftp = FTP("ftp.cmegroup.com", timeout=60)
            ftp.login()
            buf = io.BytesIO()
            ftp.retrbinary("RETR daily_volume/daily_volume.xlsx", buf.write)
            ftp.close()
            break
        except Exception as e:  # noqa: BLE001 - o FTP da CME derruba conexões às vezes
            last_err = e
            buf = None
    if buf is None:
        raise RuntimeError(f"FTP da CME: {last_err}")

    wb = load_workbook(buf, read_only=True)
    ws = next(w for w in wb.worksheets if "by Product" in w.title)
    trade_date = None
    vol_idx = None
    wanted = {"SOYBEAN FUTURE": "futures", "SOYBEAN CALL": "calls", "SOYBEAN PUT": "puts"}
    out = {}
    for row in ws.iter_rows(values_only=True):
        cells = ["" if c is None else str(c) for c in row]
        if cells and cells[0].startswith("Trade Date"):
            m = re.search(r"(\d{2})/(\d{2})/(\d{4})", cells[0])
            if m:
                trade_date = f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
        if "Product Description" in cells:
            vol_idx = next(
                i for i, c in enumerate(cells) if c.replace("\n", " ").strip() == "Total Volume"
            )
            desc_idx = cells.index("Product Description")
            continue
        if vol_idx is None or len(cells) <= vol_idx:
            continue
        key = wanted.get(cells[desc_idx].strip())
        if key:
            try:
                out[key] = {"volume": int(float(cells[vol_idx]))}
            except ValueError:
                continue
    if "calls" not in out or "puts" not in out:
        raise RuntimeError("linhas SOYBEAN CALL/PUT não encontradas no daily_volume.xlsx")
    cbot = out
    if cbot["calls"]["volume"]:
        cbot["put_call_volume"] = round(
            cbot["puts"]["volume"] / cbot["calls"]["volume"], 2
        )
    return {"updated_at": now_iso(), "trade_date": trade_date, "cbot": cbot}


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
    "safra": collect_safra,
    "curve": collect_curve,
    "options": collect_options,
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
