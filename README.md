# 🌱 Painel Soja

Painel matinal do mercado de soja para o Centro-Oeste: cotações CBOT, câmbio,
juros, indicador CEPEA, previsão de chuva nas regiões produtoras e notícias
com link — tudo em uma página estática, atualizada automaticamente.

**Como funciona:** um GitHub Action (`.github/workflows/update-data.yml`) roda
de hora em hora, executa `scripts/update_data.py`, que busca os dados nas
fontes gratuitas e grava `data/data.json`. O `index.html` (GitHub Pages) só lê
esse JSON — não há servidor, banco de dados nem custo.

## Ativar (uma vez)

1. **GitHub Pages:** em *Settings → Pages → Build and deployment*, escolha
   *Deploy from a branch*, branch `main`, pasta `/ (root)` e salve.
   O site ficará em `https://SEU-USUARIO.github.io/painel-soja/`.
2. **Primeira carga de dados:** em *Actions → Atualizar dados de mercado →
   Run workflow*. Depois disso o robô roda sozinho a cada hora.

## Fontes de dados (todas gratuitas)

| Dado | Fonte | Observação |
|---|---|---|
| Soja, milho, farelo, óleo, trigo (CBOT), Brent, Ibovespa | Yahoo Finance (não oficial) | Atraso ~15 min; é a fonte mais frágil — se falhar, o painel mantém o último valor |
| Dólar e euro comercial | AwesomeAPI | Quase em tempo real |
| PTAX, Selic, CDI, IPCA | Banco Central (Olinda e SGS) | Fontes oficiais, estáveis |
| Indicador soja Paranaguá | CEPEA/ESALQ (raspagem da página pública) | Sem API gratuita; se o site mudar, a seção some sem quebrar o resto |
| Chuva 7 dias (Sorriso, Sinop, Rio Verde, Dourados) | Open-Meteo | Sem chave |
| Notícias | Google News RSS, Canal Rural, G1 Agronegócios, Notícias Agrícolas | Links diretos para as matérias |

## Ajustes comuns

- **Frequência:** mude o `cron` em `.github/workflows/update-data.yml`
  (ex.: `*/30 * * * *` para 30 min).
- **Cidades do clima:** edite a lista `CITIES` em `scripts/update_data.py`.
- **Feeds de notícias:** edite a lista `FEEDS` no mesmo arquivo.
- **Contratos cotados:** edite `YAHOO_SYMBOLS`.

## Limitações conhecidas

- Cotações não são em tempo real (atraso das fontes + atualização horária).
- O cron do GitHub pode atrasar alguns minutos em horário de pico.
- Uso pessoal/informativo; não redistribua os dados comercialmente.
