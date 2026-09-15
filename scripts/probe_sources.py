"""Sonda temporária, rodada 2: o SFI está dentro do Boletim Diário?

A rodada 1 estabeleceu metade do critério:

  - o endereço `arquivos.b3.com.br/bdi/download/bdi/{data}/BDI_{cap}_{data}.pdf`
    responde 200 sem autenticação, e **não só para a data do exemplo**:
    2026-09-14 e 2026-09-11 vieram com ~98 KB cada
  - não há índice JSON (`index.json`, `bdi.json` dão 500); o diretório da data
    devolve o HTML da SPA
  - o capítulo **02-1** passou de 6 MiB e foi o único em que um código alvo
    apareceu nos bytes crus: `BGI`. É o candidato a capítulo de agropecuário
  - não existe variante `.csv`/`.zip`/`.txt` — testado no capítulo 03-1

O que **não** está estabelecido, e é o que decide o gráfico: o boletim traz o
**SFI por vencimento, com preço de ajuste**? Achar `BGI` e não achar `SFI` nos
bytes crus não prova nada — PDF comprime os fluxos de texto, então ausência ali
não é ausência no documento. Só abrindo o arquivo.

Esta rodada:
  A. o que é cada capítulo? (título da primeira página dos pequenos)
  B. baixar o 02-1 inteiro e **extrair o texto**: SFI aparece? com vencimento,
     ajuste, volume e contratos em aberto?
  C. a SPA do /bdi/ chama alguma API que liste capítulos ou sirva CSV?
  D. variantes de extensão no 02-1 — a rodada 1 só testou no capítulo errado

Pegada: um download grande e algumas requisições pequenas. Teto de bytes e
timeout curto continuam valendo — o timeout do requests conta entre bytes.

Rodar pelo workflow `probe.yml` e ler os logs. Remover depois.
"""

import datetime as dt
import io
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
TETO_GRANDE = 80 * 1024 * 1024
TETO_PEQUENO = 4 * 1024 * 1024

# O que procurar no texto extraído. SFI é o alvo; os outros situam a página.
ALVOS = {
    "SFI": r"\bSFI\b",
    "SJC": r"\bSJC\b",
    "soja financeiro": r"[Ss]oja.{0,40}[Ff]inanceir",
    "BGI": r"\bBGI\b",
    "CCM": r"\bCCM\b",
    "ICF (café)": r"\bICF\b",
}


def baixa(url, timeout=25, teto=TETO_PEQUENO):
    """(status, corpo|None, motivo). Para no teto: boletim em PDF é grande."""
    t0 = time.time()
    try:
        with requests.get(url, headers=HEADERS, timeout=timeout, stream=True) as r:
            if not r.ok:
                return r.status_code, None, ""
            buf = bytearray()
            for pedaco in r.iter_content(131072):
                buf += pedaco
                if len(buf) > teto:
                    return r.status_code, bytes(buf), f"cortado no teto ({time.time()-t0:.0f}s)"
            return r.status_code, bytes(buf), f"{time.time()-t0:.0f}s"
    except Exception as e:  # noqa: BLE001
        return None, None, f"{type(e).__name__}: {str(e)[:70]}"


def cab(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}", flush=True)


def pregao_recente(dias_atras=1):
    """Último dia útil, ignorando fim de semana (feriado não é tratado)."""
    d = dt.date.today() - dt.timedelta(days=dias_atras)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def url_capitulo(data: dt.date, cap: str, ext: str = "pdf"):
    return f"{RAIZ}/{data:%Y-%m-%d}/BDI_{cap}_{data:%Y%m%d}.{ext}"


def paginas(corpo: bytes, limite=None):
    """Gera (n, texto) por página. pypdf falha em página solta sem derrubar tudo."""
    from pypdf import PdfReader

    leitor = PdfReader(io.BytesIO(corpo), strict=False)
    total = len(leitor.pages)
    print(f"  {total} páginas", flush=True)
    for n in range(total if limite is None else min(total, limite)):
        try:
            yield n + 1, leitor.pages[n].extract_text() or ""
        except Exception as e:  # noqa: BLE001
            print(f"    página {n+1} falhou: {type(e).__name__}", flush=True)


def passoG_soja(data: dt.date):
    """'soja' aparece 120x no 02-1 e 'futuro' zero. O que são essas linhas?

    A decisão sobre o gráfico depende disso, então é para olhar, não supor.
    """
    cab(f"G — as 120 ocorrências de 'soja' no 02-1, uma a uma ({data:%Y-%m-%d})")
    st, corpo, motivo = baixa(url_capitulo(data, "02-1"), timeout=40, teto=TETO_GRANDE)
    print(f"  BDI_02-1: {st}  {len(corpo) if corpo else 0} B  {motivo}", flush=True)
    if not corpo:
        return
    vistas, mostradas = set(), 0
    for n, txt in paginas(corpo):
        for linha in txt.splitlines():
            if "soja" not in linha.lower():
                continue
            chave = linha.strip()[:60]
            if chave in vistas:
                continue
            vistas.add(chave)
            mostradas += 1
            if mostradas <= 30:
                print(f"    pág {n:>3} | {linha.strip()[:120]}", flush=True)
    print(f"\n  linhas distintas com 'soja': {len(vistas)}", flush=True)


def passoE_extracao(data: dt.date):
    """A extração no 02-1 produziu texto mesmo? Zero achado só vale se sim."""
    cab(f"E — a extração do 02-1 produziu texto? ({data:%Y-%m-%d})")
    st, corpo, motivo = baixa(url_capitulo(data, "02-1"), timeout=40, teto=TETO_GRANDE)
    print(f"  BDI_02-1: {st}  {len(corpo) if corpo else 0} B  {motivo}", flush=True)
    if not corpo:
        return
    amostra = {1, 50, 200, 450, 700, 880}
    total_chars = 0
    vazias = 0
    palavras = {"soja": 0, "ajuste": 0, "futuro": 0, "vencimento": 0, "milho": 0,
                "boi": 0, "agropecu": 0}
    for n, txt in paginas(corpo):
        total_chars += len(txt)
        if not txt.strip():
            vazias += 1
        baixo = txt.lower()
        for p in palavras:
            palavras[p] += baixo.count(p)
        if n in amostra:
            print(f"\n  --- página {n} ({len(txt)} chars) ---", flush=True)
            for x in [l for l in txt.splitlines() if l.strip()][:10]:
                print(f"    | {x[:110]}", flush=True)
    print(f"\n  total extraído: {total_chars} chars; páginas vazias: {vazias}", flush=True)
    print(f"  palavras (minúsculas): {palavras}", flush=True)


def passoF_capitulos(data: dt.date):
    """Enumerar de verdade, em vez de chutar vizinhança de numeração."""
    cab(f"F — quais capítulos existem? ({data:%Y-%m-%d})")
    for i in range(1, 10):
        for j in (1, 2, 3):
            cap = f"{i:02d}-{j}"
            st, corpo, motivo = baixa(url_capitulo(data, cap), timeout=20, teto=3 * 1024 * 1024)
            tam = len(corpo) if corpo else 0
            if st != 200 or not tam:
                print(f"  BDI_{cap}: {st}", flush=True)
                continue
            titulo = ""
            if "teto" not in motivo:
                try:
                    from pypdf import PdfReader

                    leitor = PdfReader(io.BytesIO(corpo), strict=False)
                    npg = len(leitor.pages)
                    linhas = [x.strip() for x in
                              (leitor.pages[0].extract_text() or "").splitlines() if x.strip()]
                    titulo = f"{npg} pág | " + " / ".join(linhas[:3])[:150]
                except Exception as e:  # noqa: BLE001
                    titulo = f"(pypdf: {type(e).__name__})"
            else:
                titulo = "(grande, cortado no teto)"
            print(f"  BDI_{cap}: 200  {tam:>9} B  {titulo}", flush=True)
            time.sleep(0.8)


def passoA_titulos(data: dt.date):
    cab(f"A — o que é cada capítulo? ({data:%Y-%m-%d})")
    for cap in ("03-1", "04-1"):
        st, corpo, motivo = baixa(url_capitulo(data, cap))
        print(f"\n  BDI_{cap}: {st}  {len(corpo) if corpo else 0} B  {motivo}", flush=True)
        if not corpo:
            continue
        for n, txt in paginas(corpo, limite=1):
            linhas = [x.strip() for x in txt.splitlines() if x.strip()][:12]
            for x in linhas:
                print(f"    | {x[:100]}", flush=True)


def passoB_agro(data: dt.date):
    cab(f"B — o 02-1 traz o SFI, com ajuste por vencimento? ({data:%Y-%m-%d})")
    st, corpo, motivo = baixa(url_capitulo(data, "02-1"), timeout=40, teto=TETO_GRANDE)
    print(f"  BDI_02-1: {st}  {len(corpo) if corpo else 0} B  {motivo}", flush=True)
    if not corpo:
        print("  sem corpo — nada a extrair", flush=True)
        return

    achados = {k: [] for k in ALVOS}
    contexto_sfi = []
    t0 = time.time()
    for n, txt in paginas(corpo):
        for nome, padrao in ALVOS.items():
            if re.search(padrao, txt):
                achados[nome].append(n)
                # a primeira página com SFI vale o texto inteiro: é onde se vê
                # se vêm vencimento, ajuste, volume e contratos em aberto
                if nome == "SFI" and not contexto_sfi:
                    contexto_sfi = [n, txt]
        if time.time() - t0 > 240:
            print(f"  ... parando na página {n} (240s)", flush=True)
            break

    print("\n  ocorrências por código:", flush=True)
    for nome, pgs in achados.items():
        onde = f"{len(pgs)} pág, ex.: {pgs[:6]}" if pgs else "nenhuma"
        marca = "   <<<" if pgs and nome == "SFI" else ""
        print(f"    {nome:<18} {onde}{marca}", flush=True)

    if contexto_sfi:
        n, txt = contexto_sfi
        print(f"\n  --- página {n}, texto integral (é aqui que se lê o ajuste) ---",
              flush=True)
        for x in txt.splitlines()[:90]:
            if x.strip():
                print(f"    | {x[:120]}", flush=True)


def passoC_spa():
    cab("C — a SPA do /bdi/ chama alguma API de capítulos ou CSV?")
    st, corpo, motivo = baixa("https://arquivos.b3.com.br/bdi/", timeout=15)
    print(f"  /bdi/  {st}  {len(corpo) if corpo else 0} B  {motivo}", flush=True)
    if not corpo:
        return
    html = corpo.decode("utf-8", "ignore")
    scripts = re.findall(r'src="([^"]+\.js)"', html)
    print(f"  scripts: {scripts[:6]}", flush=True)
    for s in scripts[:3]:
        url = s if s.startswith("http") else f"https://arquivos.b3.com.br{s}"
        st, js, motivo = baixa(url, timeout=20)
        print(f"\n  {url.rsplit('/', 1)[-1]}: {st}  {len(js) if js else 0} B  {motivo}",
              flush=True)
        if not js:
            continue
        txt = js.decode("utf-8", "ignore")
        # endereços e nomes de rota que valham sondagem depois
        pistas = set()
        for padrao in (r'["\'`](/[a-zA-Z0-9_\-/{}.$]{4,60})["\'`]',
                       r'https://[a-z0-9.\-]*b3\.com\.br[a-zA-Z0-9_\-/{}.$]{0,60}'):
            for m in re.findall(padrao, txt):
                if re.search(r"bdi|api|download|csv|json|capitulo|chapter|arquiv", m, re.I):
                    pistas.add(m[:90])
        for p in sorted(pistas)[:25]:
            print(f"    | {p}", flush=True)
        time.sleep(1.0)


def passoD_extensoes(data: dt.date):
    cab(f"D — variantes de extensão no capítulo 02-1 ({data:%Y-%m-%d})")
    for ext in ("csv", "zip", "xml", "txt"):
        st, corpo, motivo = baixa(url_capitulo(data, "02-1", ext), timeout=15)
        tam = len(corpo) if corpo else 0
        marca = "   <<< EXISTE" if st == 200 and tam else ""
        print(f"  .{ext:<4} {str(st):>5}  {tam:>9} B  {motivo:<20}{marca}", flush=True)
        if corpo and tam:
            print(f"         {re.sub(rb'[^ -~]', b'.', corpo[:260]).decode()}", flush=True)
        time.sleep(1.2)


def main():
    data = pregao_recente(1)
    print(f"  pregão de referência: {data:%Y-%m-%d}", flush=True)
    for fn in (passoG_soja,):
        try:
            fn(data)
        except Exception as e:  # noqa: BLE001
            print(f"  {fn.__name__} falhou: {type(e).__name__}: {str(e)[:140]}", flush=True)


if __name__ == "__main__":
    main()
