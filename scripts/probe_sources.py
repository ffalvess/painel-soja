#!/usr/bin/env python3
"""Sonda temporária (rodada 5): colunas do xlsx da CME e BMF via http.client."""

import http.client
import io
import sys
from ftplib import FTP


def sec(t):
    print(f"\n===== {t}")


def main() -> int:  # noqa: C901
    sec("cme-xlsx-soybean")
    try:
        ftp = FTP("ftp.cmegroup.com", timeout=45)
        ftp.login()
        buf = io.BytesIO()
        ftp.retrbinary("RETR daily_volume/daily_volume.xlsx", buf.write)
        ftp.close()
        from openpyxl import load_workbook

        wb = load_workbook(buf, read_only=True)
        ws = next(w for w in wb.worksheets if "by Product" in w.title)
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            cells = ["" if c is None else str(c).replace("\n", " ") for c in row]
            if i < 4:
                print("HDR", i, cells)
            elif any("SOYBEAN" in c for c in cells):
                print("SOY", cells)
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    # BMF via http.client cru (sem o tratamento de URL do requests)
    paths = [
        ("soj-com-caminho",
         "/pages/portal/bmfbovespa/boletim1/SistemaPregao1.asp?pagetype=pop"
         "&caminho=Resumo%20Estat%EDstico%20-%20Sistema%20Preg%E3o&Mercadoria=SOJ"),
        ("soj-sem-caminho",
         "/pages/portal/bmfbovespa/boletim1/SistemaPregao1.asp?pagetype=pop&Mercadoria=SOJ"),
        ("sfi-sem-caminho",
         "/pages/portal/bmfbovespa/boletim1/SistemaPregao1.asp?pagetype=pop&Mercadoria=SFI"),
    ]
    for name, path in paths:
        sec(f"bmf-{name}")
        try:
            conn = http.client.HTTPSConnection("www2.bmf.com.br", timeout=45)
            conn.request(
                "GET",
                path,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "Host": "www2.bmf.com.br",
                    "Accept": "*/*",
                },
            )
            resp = conn.getresponse()
            body = resp.read()
            conn.close()
            print(f"status={resp.status} bytes={len(body)}")
            loc = resp.getheader("Location")
            if loc:
                print("location:", loc)
            text = " ".join(body.decode("latin-1", "replace").split())
            up = text.upper()
            i = up.find("VENCTO")
            j = up.find("ABERTO")
            print(f"idx VENCTO={i} ABERTO={j}")
            print("TRECHO:", text[max(0, i - 1000): i + 4500] if i >= 0 else text[:2500])
        except Exception as e:  # noqa: BLE001
            print("EXC:", type(e).__name__, e)

    return 0


if __name__ == "__main__":
    sys.exit(main())
