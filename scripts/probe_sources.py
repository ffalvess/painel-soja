"""Sonda temporária: o Yahoo serve histórico de contratos já vencidos?

Decide a arquitetura da comparação temporal da curva (item B2 do plano).

  - SE SERVIR: dá para reconstruir a curva de qualquer data passada juntando
    o fechamento de cada contrato que estava vigente naquele dia. A comparação
    "curva de hoje contra a de 1 ano atrás" existe imediatamente.
  - SE NÃO SERVIR: só resta acumular um retrato por dia em
    `data/curve_history.json`, no mesmo padrão de `basis_history.json`, e a
    comparação anual só existe daqui a um ano.

A diferença entre os dois cenários é grande demais para assumir.

Rodar pelo workflow `probe.yml` e ler os logs. Remover depois.
"""

import datetime as dt
import time

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# A curva de soja de agosto/2025 teria sido esta. Quase toda vencida hoje.
SOJA_2025 = ["ZSU25", "ZSX25", "ZSF26", "ZSH26", "ZSK26", "ZSN26", "ZSQ26"]
# Milho: meses H K N U Z.
MILHO_2025 = ["ZCU25", "ZCZ25", "ZCH26", "ZCK26", "ZCN26"]
# Controle: contratos vivos hoje, que sabemos que funcionam.
VIVOS = ["ZSX26", "ZSF27", "ZCZ26", "ZCH27"]


def chart(symbol: str, rng: str = "2y"):
    """(pontos, primeiro, último, último_fechamento) ou (0, erro)."""
    ultimo = None
    for host in ("query1", "query2"):
        for tentativa in range(2):
            try:
                r = requests.get(
                    f"https://{host}.finance.yahoo.com/v8/finance/chart/{symbol}.CBT",
                    params={"range": rng, "interval": "1d"},
                    headers=HEADERS,
                    timeout=30,
                )
                if r.status_code == 429:
                    ultimo = "429"
                    time.sleep(3 * (tentativa + 1))
                    continue
                r.raise_for_status()
                res = r.json()["chart"]["result"][0]
                ts = res.get("timestamp") or []
                fech = res["indicators"]["quote"][0].get("close") or []
                pares = [(t, c) for t, c in zip(ts, fech) if c is not None]
                if not pares:
                    return 0, "sem fechamentos"
                d = lambda t: dt.datetime.utcfromtimestamp(t).date().isoformat()
                return len(pares), (d(pares[0][0]), d(pares[-1][0]), pares[-1][1])
            except Exception as e:  # noqa: BLE001
                ultimo = str(e)[:70]
    return 0, ultimo


def secao(titulo: str, simbolos: list) -> dict:
    print(f"\n{'=' * 78}\n{titulo}\n{'=' * 78}")
    achados = {}
    for s in simbolos:
        n, info = chart(s)
        if n:
            ini, fim, ult = info
            achados[s] = (n, ini, fim)
            print(f"  {s:8} {n:>4} pregões   {ini} -> {fim}   último {ult}")
        else:
            print(f"  {s:8}    — {info}")
        time.sleep(1.2)  # o Yahoo limita por IP; não vale correr
    return achados


def main() -> None:
    vivos = secao("CONTROLE — contratos vivos (têm que funcionar)", VIVOS)
    soja = secao("SOJA — curva de agosto/2025, quase toda vencida", SOJA_2025)
    milho = secao("MILHO — curva de agosto/2025", MILHO_2025)

    print(f"\n{'=' * 78}\nVEREDITO\n{'=' * 78}")
    if not vivos:
        print("  Nem os contratos vivos responderam — sonda inconclusiva,")
        print("  provavelmente limite de taxa. Repetir mais tarde.")
        return

    vencidos = {**soja, **milho}
    # Um contrato vencido só serve se a série alcançar agosto/2025.
    alvo = "2025-08-31"
    uteis = {s: v for s, v in vencidos.items() if v[1] <= alvo}
    print(f"  contratos vivos que responderam: {len(vivos)}/{len(VIVOS)}")
    print(f"  contratos vencidos que responderam: {len(vencidos)}/{len(SOJA_2025)+len(MILHO_2025)}")
    print(f"  destes, com série alcançando agosto/2025: {len(uteis)}")
    if uteis:
        print("\n  >>> DÁ PARA RECONSTRUIR a curva histórica agora.")
        print("      Buscar cada contrato da curva de então e casar por data.")
        for s, (n, ini, fim) in sorted(uteis.items()):
            print(f"        {s}: {n} pregões desde {ini}")
    else:
        print("\n  >>> NÃO DÁ. Acumular retrato diário em data/curve_history.json,")
        print("      no padrão de basis_history.json. Comparação anual em 1 ano.")


if __name__ == "__main__":
    main()
