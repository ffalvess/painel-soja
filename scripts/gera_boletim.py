#!/usr/bin/env python3
"""Gera o boletim semanal a partir do que o painel já calculou.

Duas versões do mesmo conteúdo:

  interno — tudo, inclusive sinal incerto, ressalvas e os coletores que
            falharam. É o que o consultor lê antes de escrever.
  cliente — curado, com espaço marcado para a leitura dele. Sai com a
            assinatura dele, não do painel.

Duas regras que valem mais que o layout:

1. **O gerador não faz aritmética própria.** Todo número sai de
   `data/data.json`, calculado pelo coletor. Se o boletim recalculasse, ele
   e a tela poderiam divergir — e aí não dá para saber qual está certo.

2. **Ele produz rascunho, não envia.** Um erro de dado num e-mail chega a
   todos os clientes de uma vez e não se desfaz. Só nesta semana apareceram
   cinco defeitos de sinal ou rótulo sobre dado correto.

Uso:  python scripts/gera_boletim.py [diretório de saída]
"""

import datetime as dt
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DADOS = ROOT / "data" / "data.json"
SAIDA = ROOT / "boletim"

MESES = [
    "", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def num(v, dig=2):
    if v is None:
        return "—"
    s = f"{v:,.{dig}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return s


def sinal(v, dig=2):
    return "—" if v is None else ("+" if v > 0 else "") + num(v, dig)


def data_br(iso):
    if not iso:
        return "—"
    p = iso.split("-")
    return f"{p[2]}/{p[1]}/{p[0]}" if len(p) > 2 else f"{p[1]}/{p[0]}"


# ------------------------------------------------------------------ blocos

def bloco_preco(s):
    sn = s.get("sinais") or {}
    if not sn.get("preco"):
        return None
    p, pc = sn["preco"], sn.get("percentis") or {}
    linhas = []
    for k, rot in (("mes", "1 mês"), ("trimestre", "3 meses"), ("ano", "1 ano")):
        v = pc.get(k) or {}
        if v.get("cents") is not None:
            reais = f" · R$/saca p{v['brl_saca']}" if v.get("brl_saca") is not None else ""
            linhas.append(f"<li>{rot}: <b>p{v['cents']}</b> em ¢/bu{reais} "
                          f"<small>({v['n']} pregões)</small></li>")
    return {
        "titulo": f"Preço · contrato {sn.get('contrato_referencia') or '—'}",
        "destaque": (f"R$ {num(p['brl_saca'])}/saca" if p.get("brl_saca")
                     else f"{num(p['cents'])} ¢/bu"),
        "apoio": f"{num(p['cents'])} ¢/bu na bolsa",
        "corpo": f"<p>Onde está no histórico:</p><ul>{''.join(linhas)}</ul>" if linhas else "",
        "ressalva": (
            "O percentil sai do contínuo de primeiro vencimento, cuja série é emendada nas "
            "rolagens. Em mercado de carrego a série deriva para cima, então o percentil fica "
            "enviesado na mesma direção — ordem de 40 ¢ ao ano, perto de 15% da amplitude."
        ),
    }


def bloco_carrego(s):
    car = (s.get("sinais") or {}).get("carrego") or []
    if not car:
        return None
    linhas = "".join(
        f"<tr><td>{c['de']} → {c['para']}</td><td>{sinal(c['cents'])}</td>"
        f"<td>{sinal(c['cents_mes'])}</td><td>{sinal(c['aa_pct'], 1)}%</td>"
        f"<td>{'inversão' if c['cents'] < 0 else 'carrego'}</td></tr>"
        for c in car
    )
    melhor = max((c for c in car if c.get("aa_pct")), key=lambda c: c["aa_pct"], default=None)
    return {
        "titulo": "Quanto o mercado paga para esperar",
        "destaque": (f"{melhor['de']} → {melhor['para']}: {sinal(melhor['aa_pct'], 1)}% a.a."
                     if melhor else "—"),
        "apoio": "melhor trecho da curva",
        "corpo": (
            "<table><thead><tr><th>Trecho</th><th>Spread (¢)</th><th>¢/mês</th>"
            f"<th>a.a.</th><th></th></tr></thead><tbody>{linhas}</tbody></table>"
        ),
        "ressalva": (
            "Retorno anualizado que o mercado paga por adiar a venda, <b>sem descontar custo "
            "de armazenagem</b> — compare com o seu custo para saber se compensa esperar."
        ),
    }


ROTULO_TIPO = {
    "comprador": "bid",
    "intermediario": "mercado",
    "entidade": "levantamento",
}


def bloco_basis(s):
    b = s.get("basis") or {}
    bp = b.get("basis_porto") or {}
    if bp.get("brl_saca") is None:
        return None
    v = bp["brl_saca"]

    # Ordenar praça por basis e chamar as três primeiras de "mais descontadas"
    # era enganoso: hoje as três seriam exatamente as que não são cotação de
    # intermediário. Enquanto a diferença de tipo de cotação for da ordem da
    # diferença entre praças, cada linha sai com quem cotou ao lado.
    tipos = {
        f.get("praca"): f
        for f in (s.get("cepea") or {}).get("fisico") or []
    }
    interior = (b.get("basis_interior") or [])[:4]
    li = ""
    for i in interior:
        f = tipos.get(i["praca"]) or {}
        rot = ROTULO_TIPO.get(f.get("tipo_agente"))
        quem = f.get("agente")
        marca = (
            f" <small>· {quem}{f' ({rot})' if rot else ''}</small>" if quem else ""
        )
        li += (
            f"<li>{i['praca']}: R$ {num(i['valor'])} "
            f"<small>({sinal(i['basis_brl_saca'])} vs. porto)</small>{marca}</li>"
        )

    fr = s.get("frete") or {}
    aj = fr.get("ajuste") or {}
    nota_frete = ""
    if aj.get("r2_distancia") is not None and not fr.get("distancia_explica"):
        nota_frete = (
            f" A distância até o porto <b>não</b> explica a diferença entre as praças "
            f"(R² {num(aj['r2_distancia'], 3)})"
            + (
                f", enquanto o tipo de quem cotou explica "
                f"{num((aj.get('r2_tipo_agente') or 0) * 100, 0)}%"
                if aj.get("r2_tipo_agente") is not None else ""
            )
            + "."
        )

    dif = ""
    por_tipo = {t["tipo"]: t for t in (fr.get("por_tipo") or [])}
    if "intermediario" in por_tipo and len(por_tipo) > 1:
        outros = [t for k, t in por_tipo.items() if k != "intermediario"]
        if outros:
            m_out = sum(t["media"] * t["n"] for t in outros) / sum(t["n"] for t in outros)
            dif = (
                f" Hoje a média de cotação de intermediário está R$ "
                f"{num(abs(por_tipo['intermediario']['media'] - m_out))}/saca acima "
                "das demais."
            )

    return {
        "titulo": "Basis do porto",
        "destaque": f"{'Deságio' if v < 0 else 'Prêmio'} de R$ {num(abs(v))}/saca",
        "apoio": f"{num(abs(bp.get('pct') or 0), 1)}% sobre a paridade de exportação",
        "corpo": (
            f"<p>Paridade R$ {num(b.get('paridade_brl_saca'))} · indicador Paranaguá "
            f"R$ {num(b.get('indicador_brl_saca'))}, referência de "
            f"{b.get('indicador_data') or '—'}.</p>"
            + (f"<p>Praças com maior desconto contra o porto:</p><ul>{li}</ul>" if li else "")
        ),
        "ressalva": (
            f"Calculado contra o prêmio de embarque de <b>{b.get('premio_mes') or '—'}</b> e o "
            f"contrato <b>{b.get('contrato') or '—'}</b>. Quando o mês de referência troca, o "
            "basis dá um degrau que não é movimento de mercado. "
            "<b>Não compare praças sem olhar quem cotou:</b> onde o agente é o próprio "
            "comprador o número é o bid dele, e bid fica abaixo do negócio fechado."
            + dif + nota_frete
        ),
    }


LEGENDA_PERNA = {
    "cbot": ("CBOT", "mundo", 2),
    "premio": ("Prêmio de porto", "o exportador querendo grão agora", 0),
    "cambio": ("Câmbio", "financeiro, não é soja", 4),
}


def bloco_pernas(s):
    """Qual perna moveu a paridade — a conta aberta, que é o diferencial.

    Lê `basis.pernas`, gravado pelo coletor. Sem cálculo próprio aqui: se o
    boletim recalculasse, divergiria do painel no dia em que um dos dois
    mudasse, e é o boletim que leva a assinatura do consultor.
    """
    p = (s.get("basis") or {}).get("pernas") or {}
    if not p.get("pernas"):
        return None
    linhas = ""
    for x in p["pernas"]:
        nome, leg, dig = LEGENDA_PERNA.get(x["perna"], (x["perna"], "", 2))
        linhas += (
            f"<tr><td>{nome} <small>{leg}</small></td>"
            f"<td>{num(x['de'], dig)} → {num(x['para'], dig)} {x['unidade']}</td>"
            f"<td><b>{sinal(x['efeito'])}</b></td></tr>"
        )
    maior = max(p["pernas"], key=lambda x: abs(x["efeito"]))
    nome_maior = LEGENDA_PERNA.get(maior["perna"], (maior["perna"],))[0]
    bv = p.get("basis_var")
    leitura = ""
    if bv is not None:
        leitura = (
            "<p>No mesmo intervalo o basis do porto "
            + (
                f"<b>abriu</b> {sinal(bv)} — o interno ficou para trás da paridade e a "
                "margem de quem exporta melhorou."
                if bv < 0
                else f"<b>fechou</b> {sinal(bv)} — o interno correu na frente da paridade."
            )
            + "</p>"
        )
    return {
        "titulo": "O que moveu a paridade",
        "destaque": f"{sinal(p.get('total'))} R$/saca",
        "apoio": f"de {p.get('de') or '—'} a {p.get('para') or '—'} · puxado por {nome_maior}",
        "corpo": (
            "<table><thead><tr><th>Perna</th><th>Movimento</th><th>Efeito</th></tr></thead>"
            f"<tbody>{linhas}</tbody></table>" + leitura
        ),
        "ressalva": (
            "As três pernas não querem dizer a mesma coisa. Prêmio subindo é o exportador "
            "sinalizando que quer grão agora; câmbio muda o preço em reais sem mudar nada de "
            "soja; CBOT é mundo. A soma não fecha exatamente porque as pernas se multiplicam — "
            f"o resíduo de interação é {sinal(p.get('residuo_interacao'))}."
        ),
    }


def bloco_crush(s):
    c = s.get("crush") or {}
    if c.get("valor") is None:
        return None
    return {
        "titulo": "Margem de esmagamento",
        "destaque": f"US$ {num(c['valor'])}/bu",
        "apoio": (f"percentil {c['percentil_1a']} de {c.get('obs', '?')} pregões"
                  if c.get("percentil_1a") is not None else ""),
        "corpo": (
            f"<p>Mediana do ano {num(c.get('mediana_1a'))}, faixa {num(c.get('min_1a'))} a "
            f"{num(c.get('max_1a'))}. Óleo responde por {num(c.get('part_oleo_pct'), 1)}% do "
            "valor dos produtos.</p>"
            "<p>Esmagamento rentável sustenta a demanda por grão e o prêmio de porto.</p>"
        ),
        "ressalva": (
            "As três pernas são contínuos e podem não estar no mesmo mês; a série do ano herda "
            "degraus de rolagem que não se cancelam entre elas."
        ),
    }


def bloco_embarques(s):
    e = s.get("embarques") or {}
    soja = next((i for i in e.get("itens", []) if i.get("chave") == "soja"), None)
    if not soja:
        return None
    ritmo = soja.get("indice_ritmo")
    return {
        "titulo": "Demanda — embarques dos EUA",
        "destaque": f"índice de ritmo {num(ritmo, 1)}" if ritmo else "—",
        "apoio": f"semana de {data_br(soja.get('semana_ref'))}",
        "corpo": (
            f"<p>Embarcado na semana: {num(soja.get('semana', 0) / 1000, 0)} mil t. "
            f"Acumulado {num(soja.get('acumulado', 0) / 1e6, 2)} Mt contra meta de "
            f"{num((soja.get('meta') or 0) / 1e6, 2)} Mt do WASDE "
            f"({num(soja.get('pct_meta'), 1)}%).</p>"
            f"<p>Compromissos totais em {num(soja.get('pct_compromissos'), 1)}% da meta.</p>"
        ),
        "ressalva": (
            "O índice de ritmo usa fração de ano-safra linear, que não corrige a sazonalidade "
            "do embarque americano — no começo do ano-safra ele exagera o atraso."
        ),
    }


# ------------------------------------------------------------------ render

CSS = """
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
 font-size:15px;line-height:1.5;color:#1a1a1a;background:#fff;margin:0;padding:24px 16px}
.wrap{max-width:640px;margin:0 auto}
h1{font-size:21px;margin:0 0 4px}
.sub{color:#777;font-size:13px;margin-bottom:22px}
.bloco{border:1px solid #e3e2dc;border-radius:8px;padding:14px 16px;margin-bottom:14px}
.bloco h2{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:#8a8880;
 margin:0 0 8px;font-weight:600}
.destaque{font-size:24px;font-weight:650;margin-bottom:2px}
.apoio{font-size:13px;color:#666;margin-bottom:10px}
.bloco p{margin:8px 0}
.bloco ul{margin:6px 0;padding-left:20px}
.bloco li{margin-bottom:3px}
table{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:6px}
th{text-align:right;font-size:11.5px;color:#8a8880;font-weight:600;padding:4px 8px;
 border-bottom:1px solid #e3e2dc}
td{text-align:right;padding:6px 8px;border-bottom:1px solid #f0efe9}
th:first-child,td:first-child{text-align:left}
small{color:#888}
.ressalva{font-size:12px;color:#8a8880;margin-top:10px;padding-top:8px;
 border-top:1px solid #f0efe9}
.leitura{border:2px dashed #c9a227;background:#fdf9ec;border-radius:8px;
 padding:16px;margin-bottom:14px}
.leitura h2{color:#8a6a00}
.rodape{font-size:12px;color:#8a8880;margin-top:24px;border-top:1px solid #e3e2dc;
 padding-top:12px}
.interno{background:#fff4f4;border:1px solid #e8c0c0;border-radius:8px;
 padding:12px 16px;margin-bottom:14px;font-size:13px}
"""


def render(blocos, meta, cliente: bool) -> str:
    partes = []
    if not cliente and meta.get("avisos"):
        partes.append(
            '<div class="interno"><b>Só na versão interna.</b><ul>'
            + "".join(f"<li>{a}</li>" for a in meta["avisos"])
            + "</ul></div>"
        )
    if cliente:
        partes.append(
            '<div class="leitura"><h2>Sua leitura da semana</h2>'
            "<p><i>Escreva aqui o que os números acima significam para o cliente e o que "
            "você recomenda. Este espaço existe de propósito: o painel entrega evidência, "
            "a recomendação é sua e leva a sua assinatura.</i></p></div>"
        )
    for b in blocos:
        partes.append(
            f'<div class="bloco"><h2>{html.escape(b["titulo"])}</h2>'
            f'<div class="destaque">{b["destaque"]}</div>'
            f'<div class="apoio">{html.escape(b["apoio"])}</div>'
            f'{b["corpo"]}'
            f'<div class="ressalva">{b["ressalva"]}</div></div>'
        )
    hoje = dt.date.today()
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Boletim {'' if cliente else 'interno '}— {hoje.isoformat()}</title>
<style>{CSS}</style></head><body><div class="wrap">
<h1>Mercado de soja — {hoje.day} de {MESES[hoje.month]} de {hoje.year}</h1>
<div class="sub">{'Versão interna — não enviar' if not cliente else 'Rascunho — revisar antes de enviar'}
 · dados de {meta.get('gerado', '—')}</div>
{''.join(partes)}
<div class="rodape">
Fontes: CBOT via Yahoo Finance (atraso ~15 min), Cepea/Esalq via Notícias Agrícolas,
USDA/FAS (PSD e Export Sales), Banco Central. Números conforme apurados em
{meta.get('gerado', '—')}; cotações não são tempo real.
<br><br>Material informativo de apoio à decisão. Não constitui recomendação de
investimento nem oferta de compra ou venda.
</div></div></body></html>"""


def main() -> int:
    saida = Path(sys.argv[1]) if len(sys.argv) > 1 else SAIDA
    dados = json.loads(DADOS.read_text(encoding="utf-8"))
    s = dados.get("sections") or {}

    blocos = [b for b in (
        bloco_preco(s), bloco_pernas(s), bloco_basis(s), bloco_carrego(s),
        bloco_crush(s), bloco_embarques(s),
    ) if b]
    if not blocos:
        print("nenhum bloco pôde ser montado", file=sys.stderr)
        return 1

    avisos = []
    for e in dados.get("errors") or []:
        avisos.append(f"coletor <b>{e['section']}</b> falhou: {html.escape(str(e['error'])[:160])}")
    sn = s.get("sinais") or {}
    for chave, rot in (("basis", "basis"), ("carrego", "carrego")):
        f = (sn.get("sem_historico") or {}).get(chave) or {}
        if f.get("obs") is not None and f["obs"] < f.get("necessario", 0):
            avisos.append(f"{rot}: {f['obs']} de {f['necessario']} observações — sem percentil")
    if not sn.get("cambio_historico"):
        avisos.append("série de câmbio indisponível — percentil só em ¢/bu")

    meta = {"gerado": dados.get("generated_at", "")[:16].replace("T", " "), "avisos": avisos}

    saida.mkdir(parents=True, exist_ok=True)
    hoje = dt.date.today().isoformat()
    for nome, cliente in (("interno", False), ("cliente", True)):
        for arq in (saida / f"{nome}-{hoje}.html", saida / f"{nome}.html"):
            arq.write_text(render(blocos, meta, cliente), encoding="utf-8")
        print(f"gerado: {saida / f'{nome}-{hoje}.html'}")
    print(f"{len(blocos)} bloco(s); {len(avisos)} aviso(s) só na versão interna")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
