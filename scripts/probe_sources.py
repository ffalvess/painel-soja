#!/usr/bin/env python3
"""Sonda temporária (rodada 3): CME FTP com conexão nova por operação,
páginas BMF em latin-1 e linhas de dados das tabelas de soja do USDA."""

import io
import json
import sys
import urllib.request
import zipfile
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


def main() -> int:  # noqa: C901
    # ---- CME FTP, uma conexão por operação
    sec("cme-ftp-ls-settle")
    try:
        print(ftp_op(lambda f: f.nlst("settle"))[:60])
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    sec("cme-ftp-ls-daily_volume")
    try:
        print(ftp_op(lambda f: f.nlst("daily_volume"))[:60])
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    sec("cme-ftp-retr-stlags")
    try:
        buf = io.BytesIO()

        def grab(f):
            def cb(data):
                buf.write(data)
                if buf.tell() > 20000:
                    raise EOFError

            try:
                f.retrbinary("RETR settle/stlags", cb)
            except EOFError:
                pass
            return buf

        ftp_op(grab)
        text = buf.getvalue().decode("latin-1", "replace")
        print(f"bytes lidos: {buf.tell()}")
        print(text[:6000])
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    sec("cme-ftp-urllib-stlags")
    try:
        with urllib.request.urlopen("ftp://ftp.cmegroup.com/settle/stlags", timeout=60) as f:
            head = f.read(6000)
        print(head.decode("latin-1", "replace"))
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    # ---- BMF clássico em latin-1
    for merc in ("SOJ", "SFI"):
        sec(f"bmf-pregao-{merc}")
        try:
            r = requests.get(
                "https://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/SistemaPregao1.asp",
                params={"pagetype": "pop", "caminho": "Resumo Estatístico - Sistema Pregão", "Mercadoria": merc},
                headers=UA,
                timeout=40,
            )
            r.encoding = "latin-1"
            text = " ".join(r.text.split())
            print(f"status={r.status_code} bytes={len(r.content)}")
            i = text.upper().find("VENCTO")
            print("TRECHO:", text[max(0, i - 500): i + 4000] if i >= 0 else text[:2500])
        except Exception as e:  # noqa: BLE001
            print("EXC:", e)

    sec("bmf-pregao-index")
    try:
        r = requests.get(
            "https://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/SistemaPregao1.asp",
            params={"pagetype": "pop", "caminho": "Resumo Estatístico - Sistema Pregão"},
            headers=UA,
            timeout=40,
        )
        r.encoding = "latin-1"
        text = r.text
        print(f"status={r.status_code} bytes={len(r.content)}")
        import re

        opts = re.findall(r"Mercadoria=([A-Z0-9]{2,4})[^>]*>([^<]{2,60})<", text)
        seen = []
        for code, label in opts:
            if code not in [c for c, _ in seen]:
                seen.append((code, label.strip()))
        print("mercadorias:", seen[:80])
        if not seen:
            print("BODY:", " ".join(text[:2500].split()))
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    # ---- USDA: linhas completas das tabelas de soja
    sec("usda-soy-tables")
    try:
        meta = requests.get(
            "https://usda.library.cornell.edu/api/v1/release/findByIdentifier/CropProg?latest=true",
            headers=UA,
            timeout=30,
        ).json()
        zurl = next(f for f in meta["results"][0]["files"] if f.endswith(".zip"))
        z = zipfile.ZipFile(io.BytesIO(requests.get(zurl, headers=UA, timeout=60).content))
        text = z.read("prog_all_tables.csv").decode("latin-1", "replace")
        lines = text.splitlines()
        soy_ids = set()
        for ln in lines:
            parts = next(iter([ln.split(",", 2)]))
            if len(parts) >= 3 and parts[1] == '"t"' and "oybean" in parts[2]:
                soy_ids.add(parts[0])
        print("tabelas de soja:", sorted(soy_ids))
        for tid in sorted(soy_ids):
            print(f"--- tabela {tid} ---")
            for ln in lines:
                if ln.split(",", 1)[0] == tid:
                    print(ln)
    except Exception as e:  # noqa: BLE001
        print("EXC:", e)

    return 0


if __name__ == "__main__":
    sys.exit(main())
