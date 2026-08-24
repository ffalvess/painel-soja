#!/usr/bin/env python3
"""Sonda temporária (rodada 2): fecha as dúvidas restantes das fontes."""

import datetime as dt
import io
import json
import sys
import zipfile
from ftplib import FTP

import requests

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def sec(title):
    print(f"\n===== {title}")


def show(r, snip=800):
    ct = r.headers.get("Content-Type", "?")
    print(f"status={r.status_code} content-type={ct} bytes={len(r.content)}")
    try:
        print("JSON:", json.dumps(r.json(), ensure_ascii=False)[:snip])
    except Exception:
        print("BODY:", " ".join(r.text[:snip].split()))


def main() -> int:  # noqa: C901
    # ---- A. Yahoo: cookie + crumb + cadeia de opções do ZS=F
    sec("yahoo-crumb-options")
    try:
        s = requests.Session()
        s.headers.update(UA)
        s.get("https://fc.yahoo.com", timeout=20)
        crumb = s.get(
            "https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=20
        ).text.strip()
        print("crumb:", repr(crumb[:20]))
        r = s.get(
            "https://query1.finance.yahoo.com/v7/finance/options/ZS=F",
            params={"crumb": crumb},
            timeout=25,
        )
        show(r, 1400)
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    # ---- B. FTP público da CME (arquivos de settlement com volume/OI)
    sec("cme-ftp")
    try:
        ftp = FTP("ftp.cmegroup.com", timeout=40)
        ftp.login()
        for path in ("/", "pub", "pub/settle", "settle"):
            try:
                names = ftp.nlst(path)
                print(f"ls {path!r}: {names[:40]}")
            except Exception as e:  # noqa: BLE001
                print(f"ls {path!r}: EXC {e}")
        # tenta baixar o começo do arquivo de ajustes de agrícolas
        for f in ("pub/settle/stlags", "settle/stlags", "stlags"):
            try:
                buf = io.BytesIO()

                def stop_early(data, buf=buf):
                    buf.write(data)
                    if buf.tell() > 6000:
                        raise EOFError

                try:
                    ftp.retrbinary(f"RETR {f}", stop_early)
                except EOFError:
                    pass
                if buf.tell():
                    print(f"head {f}:")
                    print(buf.getvalue()[:3000].decode("latin-1", "replace"))
                    break
            except Exception as e:  # noqa: BLE001
                print(f"RETR {f}: EXC {e}")
        ftp.close()
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    # ---- C. BMF clássico: resumo por mercadoria (vencimentos, OI)
    for merc in ("SJC", "SOJ", "SFI"):
        sec(f"bmf-pregao-{merc}")
        try:
            r = requests.get(
                "https://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/SistemaPregao1.asp",
                params={
                    "pagetype": "pop",
                    "caminho": "Resumo Estatístico - Sistema Pregão",
                    "Mercadoria": merc,
                },
                headers=UA,
                timeout=30,
            )
            show(r, 1600)
        except Exception as e:  # noqa: BLE001
            print("EXC:", e)

    # ---- D. B3 MDS API de derivativos
    sec("b3-mds-sfi")
    try:
        r = requests.get(
            "https://cotacao.b3.com.br/mds/api/v1/DerivativeQuotation/SFI",
            headers=UA,
            timeout=25,
        )
        show(r, 1400)
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    # ---- E. B3 trades por ticker (curva SFI)
    for tk in ("SFIX26", "SFIU26"):
        sec(f"b3-tickercsv-{tk}")
        try:
            r = requests.get(
                f"https://arquivos.b3.com.br/apinegocios/tickercsv/{tk}/2026-08-21",
                headers=UA,
                timeout=25,
            )
            print(f"status={r.status_code} bytes={len(r.content)}")
            if r.ok and r.content[:2] == b"PK":
                z = zipfile.ZipFile(io.BytesIO(r.content))
                print("zip:", z.namelist())
                print(z.read(z.namelist()[0])[:600].decode("latin-1", "replace"))
            else:
                print("BODY:", " ".join(r.text[:400].split()))
        except Exception as e:  # noqa: BLE001
            print("EXC:", e)

    # ---- F. USDA Crop Progress: conteúdo do zip
    sec("usda-prog-zip")
    try:
        meta = requests.get(
            "https://usda.library.cornell.edu/api/v1/release/findByIdentifier/CropProg?latest=true",
            headers=UA,
            timeout=30,
        ).json()
        files = meta["results"][0]["files"]
        zurl = next(f for f in files if f.endswith(".zip"))
        print("zip url:", zurl)
        z = zipfile.ZipFile(
            io.BytesIO(requests.get(zurl, headers=UA, timeout=60).content)
        )
        print("membros:", z.namelist())
        for name in z.namelist():
            if name.endswith(".csv"):
                text = z.read(name).decode("latin-1", "replace")
                soy = [l for l in text.splitlines() if "oybean" in l]
                print(f"-- {name}: {len(text)} chars, linhas soybean={len(soy)}")
                print("\n".join(text.splitlines()[:6]))
                print("\n".join(soy[:12]))
                break
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    # ---- G. CONAB: rótulos de levantamento das safras recentes de soja
    sec("conab-soja-labels")
    try:
        r = requests.get(
            "https://portaldeinformacoes.conab.gov.br/downloads/arquivos/SerieHistoricaGraos.txt",
            headers=UA,
            timeout=60,
        )
        combos = {}
        for line in r.text.splitlines()[1:]:
            p = [c.strip() for c in line.split(";")]
            if len(p) >= 8 and p[3].startswith("SOJA"):
                combos.setdefault((p[0], p[1], p[3]), 0)
                combos[(p[0], p[1], p[3])] += 1
        keys = sorted(combos)[-12:]
        for k in keys:
            print(k, combos[k])
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    return 0


if __name__ == "__main__":
    sys.exit(main())
