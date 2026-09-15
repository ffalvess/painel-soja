"""Sonda temporária: o SFI está no Boletim Diário de Mercado?

Contexto. A rodada anterior concluiu que a B3 não expõe ajuste por vencimento.
Estava certa sobre os endpoints testados e **incompleta**: desde 10/12/2025 os
preços de ajuste migraram para o Boletim Diário de Mercado, nos capítulos de
Cotações. Os proxies antigos dão 404 porque o dado mudou de lugar.

Um resultado de busca expôs um endereço de arquivo por data:

    https://arquivos.b3.com.br/bdi/download/bdi/2026-01-15/BDI_03-1_20260115.pdf

Alvo: o **SFI**, futuro de soja liquidado contra o Indicador ESALQ/B3
Paranaguá. Não confundir com o **SJC**, minicontrato espelhado na CME, cuja
base com Chicago é zero por construção — esse o painel já coleta.

O que estabelecer:
  1. o padrão de URL responde? 404 e 403 dizem coisas diferentes
  2. existe índice de capítulos, ou é preciso varrer?
  3. qual capítulo traz derivativo agropecuário?
  4. existe variante CSV (ou zip)?
  5. o ajuste vem com volume e contratos em aberto?

Pegada: poucas requisições, espaçadas, timeout curto e teto de bytes — boletim
em PDF é grande, e o timeout do requests conta entre bytes, não no total.

Rodar pelo workflow `probe.yml` e ler os logs. Remover depois.
"""

import datetime as dt
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
RAIZ = "https://arquivos.b3.com.br/bdi/download/bdi"
TETO = 6 * 1024 * 1024
ALVOS = ("SFI", "SJC", "CCM", "BGI", "SOJA", "Soja")


def baixa(url, timeout=20):
    """Devolve (status, corpo|None, motivo). Para no teto: PDF de boletim é grande."""
    try:
        with requests.get(url, headers=HEADERS, timeout=timeout, stream=True) as r:
            if not r.ok:
                return r.status_code, None, ""
            buf = bytearray()
            for pedaco in r.iter_content(65536):
                buf += pedaco
                if len(buf) > TETO:
                    return r.status_code, bytes(buf), "cortado no teto"
            return r.status_code, bytes(buf), ""
    except Exception as e:  # noqa: BLE001
        return None, None, f"{type(e).__name__}: {str(e)[:70]}"


def cab(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def pregao_recente(dias_atras=1):
    """Último dia útil, ignorando fim de semana (feriado não é tratado)."""
    d = dt.date.today() - dt.timedelta(days=dias_atras)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def procura_alvos(corpo: bytes):
    """Os códigos aparecem no conteúdo? PDF comprime texto, então é indicativo."""
    achados = []
    for alvo in ALVOS:
        if alvo.encode("latin-1", "ignore") in corpo:
            achados.append(alvo)
    return achados


def url_capitulo(data: dt.date, cap: str, ext: str = "pdf"):
    return f"{RAIZ}/{data:%Y-%m-%d}/BDI_{cap}_{data:%Y%m%d}.{ext}"


def passo1_padrao():
    cab("1 — o padrão de URL responde? (404 x 403 dizem coisas diferentes)")
    casos = [
        ("data conhecida do exemplo", dt.date(2026, 1, 15), "03-1", "pdf"),
        ("pregão recente", pregao_recente(1), "03-1", "pdf"),
        ("pregão de 3 dias atrás", pregao_recente(3), "03-1", "pdf"),
    ]
    vivos = []
    for nome, data, cap, ext in casos:
        url = url_capitulo(data, cap, ext)
        st, corpo, motivo = baixa(url)
        tam = len(corpo) if corpo else 0
        marca = ""
        if st == 200 and tam:
            vivos.append((data, cap))
            marca = "   <<< RESPONDE"
        elif st == 403:
            marca = "   <<< 403: endereço certo, acesso fechado"
        print(f"  {str(st):>5}  {tam:>9} B  {motivo:<24} {nome}{marca}")
        print(f"         {url}")
        time.sleep(1.5)
    return vivos


def passo2_indice(data: dt.date):
    cab(f"2 — existe índice de capítulos para {data:%Y-%m-%d}?")
    for nome, url in (
        ("diretório da data", f"{RAIZ}/{data:%Y-%m-%d}/"),
        ("index.json", f"{RAIZ}/{data:%Y-%m-%d}/index.json"),
        ("bdi.json", f"{RAIZ}/{data:%Y-%m-%d}/bdi.json"),
    ):
        st, corpo, motivo = baixa(url, timeout=15)
        print(f"  {str(st):>5}  {len(corpo) if corpo else 0:>8} B  {motivo:<22} {nome}")
        if corpo and len(corpo) < 4000:
            print(f"         {re.sub(rb'[^ -~]', b'.', corpo[:300]).decode()}")
        time.sleep(1.2)


def passo3_capitulos(data: dt.date):
    cab(f"3 — qual capítulo traz derivativo agropecuário? ({data:%Y-%m-%d})")
    # numeração curta: o exemplo era 03-1, então varrer a vizinhança
    caps = ["01-1", "02-1", "03-1", "03-2", "04-1", "05-1", "06-1"]
    for cap in caps:
        st, corpo, motivo = baixa(url_capitulo(data, cap))
        tam = len(corpo) if corpo else 0
        achados = procura_alvos(corpo) if corpo else []
        marca = f"   <<< {achados}" if achados else ""
        print(f"  BDI_{cap}: {str(st):>5}  {tam:>9} B  {motivo:<18}{marca}")
        time.sleep(1.4)


def passo4_csv(data: dt.date):
    cab(f"4 — existe variante CSV ou zip? ({data:%Y-%m-%d})")
    for ext in ("csv", "zip", "txt"):
        st, corpo, motivo = baixa(url_capitulo(data, "03-1", ext), timeout=15)
        tam = len(corpo) if corpo else 0
        marca = "   <<< EXISTE" if st == 200 and tam else ""
        print(f"  .{ext:<4} {str(st):>5}  {tam:>9} B  {motivo:<20}{marca}")
        if corpo and tam:
            print(f"         {re.sub(rb'[^ -~]', b'.', corpo[:260]).decode()}")
        time.sleep(1.3)


def main():
    vivos = []
    try:
        vivos = passo1_padrao()
    except Exception as e:  # noqa: BLE001
        print(f"  passo1 falhou: {type(e).__name__}: {str(e)[:110]}")

    data = vivos[0][0] if vivos else pregao_recente(1)
    print(f"\n  -> seguindo com {data:%Y-%m-%d}"
          f"{' (nenhum endereço respondeu no passo 1)' if not vivos else ''}")

    for fn in (passo2_indice, passo3_capitulos, passo4_csv):
        try:
            fn(data)
        except Exception as e:  # noqa: BLE001
            print(f"  {fn.__name__} falhou: {type(e).__name__}: {str(e)[:110]}")


if __name__ == "__main__":
    main()
