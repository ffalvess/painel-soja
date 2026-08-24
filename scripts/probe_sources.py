#!/usr/bin/env python3
"""Sonda temporária (rodada 4): subdirs do FTP CME, daily_volume.xlsx,
e páginas BMF com redirect manual (Location vem em latin-1)."""

import io
import sys
from ftplib import FTP

import requests

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def sec(t):
    print(f"\n===== {t}")


def ftp_op(fn):
    ftp = FTP("ftp.cmegroup.com", timeout=45)
    ftp.login()
    try:
        return fn(ftp)
    finally:
        try:
            ftp.close()
        except Exception:  # noqa: BLE001
            pass


def bmf_get(url: str, max_hops: int = 4) -> requests.Response:
    """GET seguindo redirects na mão — o Location vem em latin-1 cru."""
    for _ in range(max_hops):
        r = requests.get(url, headers=UA, timeout=40, allow_redirects=False)
        loc = r.headers.get("Location")
        if r.status_code in (301, 302, 303, 307) and loc:
            if loc.startswith("/"):
                loc = "https://www2.bmf.com.br" + loc
            url = loc
            continue
        return r
    return r


def main() -> int:  # noqa: C901
    for d in ("settle/TCF", "settle/east"):
        sec(f"cme-ftp-ls-{d}")
        try:
            print(ftp_op(lambda f, d=d: f.nlst(d))[:50])
        except Exception as e:  # noqa: BLE001
            print("EXC:", e)

    sec("cme-daily-volume-xlsx")
    try:
        buf = io.BytesIO()
        ftp_op(lambda f: f.retrbinary("RETR daily_volume/daily_volume.xlsx", buf.write))
        print("bytes:", buf.tell())
        try:
            from openpyxl import load_workbook

            wb = load_workbook(buf, read_only=True)
            for ws in wb.worksheets[:2]:
                print(f"-- aba {ws.title}")
                for i, row in enumerate(ws.iter_rows(values_only=True)):
                    print([str(c)[:30] if c is not None else "" for c in row[:10]])
                    if i > 25:
                        break
        except ImportError:
            print("(openpyxl indisponível)")
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    # BMF Resumo Estatístico com URL pré-codificada em latin-1
    base = (
        "https://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/SistemaPregao1.asp"
        "?pagetype=pop&caminho=Resumo%20Estat%EDstico%20-%20Sistema%20Preg%E3o"
    )
    for merc in ("SOJ", "SFI"):
        sec(f"bmf-pregao-{merc}")
        try:
            r = bmf_get(base + f"&Mercadoria={merc}")
            r.encoding = "latin-1"
            text = " ".join(r.text.split())
            print(f"status={r.status_code} bytes={len(r.content)}")
            up = text.upper()
            for kw in ("FUTURO", "OPÇÕES", "OPCOES", "VENCTO", "ABERTO"):
                print(f"contém {kw}: {kw in up}")
            i = up.find("VENCTO")
            print("TRECHO:", text[max(0, i - 800): i + 5000] if i >= 0 else text[:3000])
        except Exception as e:  # noqa: BLE001
            print("EXC:", e)

    sec("bmf-ajustes-soja")
    try:
        r = requests.get(
            "https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/lum-ajustes-do-pregao-ptBR.asp",
            headers=UA,
            timeout=40,
        )
        r.encoding = "latin-1"
        text = " ".join(r.text.split())
        up = text.upper()
        i = up.find("SOJ")
        print(f"status={r.status_code} bytes={len(r.content)} idx_soja={i}")
        print("TRECHO:", text[max(0, i - 300): i + 2500] if i >= 0 else text[:1500])
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    return 0


if __name__ == "__main__":
    sys.exit(main())
