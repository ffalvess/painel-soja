"""Sonda temporária: o Yahoo serve histórico de contratos já vencidos?

Decide a arquitetura da comparação temporal da curva (item B2 do plano):
reconstruir a curva histórica agora, ou acumular um retrato por dia durante
um ano.

A primeira tentativa tomou 429 em tudo, inclusive nos contratos vivos de
controle — 16 símbolos com repetição em dois hosts foi rajada demais. Esta
versão:

  - reusa `fetch_yahoo_series` do próprio coletor, que roda de hora em hora
    sem tomar bloqueio (mesmos cabeçalhos, mesma alternância de host)
  - testa 4 símbolos em vez de 16 — o mínimo para decidir
  - espaça 8 s entre chamadas

Rodar pelo workflow `probe.yml` e ler os logs. Remover depois.
"""

import datetime as dt
import sys
import time

sys.path.insert(0, "scripts")

from update_data import fetch_yahoo_series  # noqa: E402

# O mínimo que decide a questão:
ALVOS = [
    ("ZSX26.CBT", "vivo", "controle — se este falhar, a sonda é inconclusiva"),
    ("ZSX25.CBT", "vencido", "novembro/25, vencido há ~9 meses"),
    ("ZSN26.CBT", "vencido", "julho/26, vencido há ~6 semanas"),
    ("ZCZ25.CBT", "vencido", "dezembro/25 do milho"),
]


def main() -> None:
    achados = {}
    print(f"{'=' * 78}\nHISTÓRICO POR CONTRATO (via fetch_yahoo_series do coletor)\n{'=' * 78}")
    for i, (symbol, tipo, nota) in enumerate(ALVOS):
        if i:
            time.sleep(8)
        try:
            serie, _meta = fetch_yahoo_series(symbol, "2y", "1d")
            ts, cs = serie["t"], serie["c"]
            if not ts:
                print(f"  {symbol:12} {tipo:8} respondeu vazio")
                continue
            d = lambda t: dt.datetime.utcfromtimestamp(t).date().isoformat()
            achados[symbol] = (len(ts), d(ts[0]), d(ts[-1]))
            print(f"  {symbol:12} {tipo:8} {len(ts):>4} pregões  {d(ts[0])} -> {d(ts[-1])}"
                  f"  último {cs[-1]}   ({nota})")
        except Exception as e:  # noqa: BLE001
            print(f"  {symbol:12} {tipo:8} FALHOU: {str(e)[:90]}")

    print(f"\n{'=' * 78}\nVEREDITO\n{'=' * 78}")
    if "ZSX26.CBT" not in achados:
        print("  O contrato vivo de controle não respondeu.")
        print("  INCONCLUSIVO — limite de taxa, não resposta do Yahoo. Repetir mais tarde,")
        print("  de preferência longe do minuto 0, quando o coletor horário roda.")
        return

    vencidos = {s: v for s, v in achados.items() if s != "ZSX26.CBT"}
    if not vencidos:
        print("  Vivo responde, vencidos não.")
        print("  >>> NÃO DÁ para reconstruir. Acumular retrato diário em")
        print("      data/curve_history.json, padrão do basis_history.json.")
        return

    print(f"  Vivo respondeu, e {len(vencidos)} de 3 vencidos também:")
    for s, (n, ini, fim) in sorted(vencidos.items()):
        print(f"    {s}: {n} pregões, {ini} -> {fim}")
    print("\n  >>> DÁ PARA RECONSTRUIR a curva histórica.")
    print("      Para cada data passada, buscar os contratos que estavam vigentes")
    print("      naquele dia e casar pelo fechamento. Sem esperar acumular.")


if __name__ == "__main__":
    main()
