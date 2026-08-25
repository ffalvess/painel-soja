# 🌱 Painel Soja

Painel matinal do mercado de soja para o Centro-Oeste: cotações CBOT (com a
curva de vencimentos e volume por contrato), calls × puts em Chicago, câmbio,
juros, indicador CEPEA, andamento da safra nos EUA (USDA) e no Brasil (CONAB),
previsão de chuva nas regiões produtoras e notícias com link — tudo em uma
página estática, atualizada automaticamente.

**Como funciona:** um GitHub Action (`.github/workflows/update-data.yml`) roda
de hora em hora, executa `scripts/update_data.py`, que busca os dados nas
fontes gratuitas e grava `data/data.json`. O `index.html` (GitHub Pages) só lê
esse JSON — não há servidor, banco de dados nem custo.

## Ativar (uma vez)

0. **Chave do USDA:** em *Settings → Secrets and variables → Actions*, crie o
   secret `USDA_FAS_KEY` com uma chave gratuita de https://api.fas.usda.gov.
   Sem ela, só a seção de oferta e demanda fica indisponível; o resto do
   painel funciona normalmente.
1. **GitHub Pages:** em *Settings → Pages → Build and deployment*, escolha
   *Deploy from a branch*, branch `main`, pasta `/ (root)` e salve.
   O site ficará em `https://SEU-USUARIO.github.io/painel-soja/`.
2. **Primeira carga de dados:** em *Actions → Atualizar dados de mercado →
   Run workflow*. Depois disso o robô roda sozinho a cada hora.

## Fontes de dados (todas gratuitas)

| Dado | Fonte | Observação |
|---|---|---|
| Soja, milho, farelo, óleo, trigo (CBOT), Brent, Ibovespa | Yahoo Finance (não oficial) | Atraso ~15 min; é a fonte mais frágil — se falhar, o painel mantém o último valor. Guarda três séries por símbolo (intradiário 1 h em 5 dias, diária em 1 ano, semanal em 5 anos) para o detalhe clicável |
| Curva de vencimentos da soja (preço, variação, volume e **posições em aberto** por contrato) | Yahoo Finance — `/v7/finance/quote` com cookie + crumb | Próximos 7 vencimentos; o `openInterest` só vem por esse endpoint |
| Volume de calls × puts de soja na CBOT | CME Group — FTP público (`ftp.cmegroup.com`, `daily_volume.xlsx`) | Dado do pregão anterior; a CME bloqueia o site/API para o Actions, mas o FTP é aberto. OI de opções por call/put não existe nesse arquivo |
| Safra EUA (floração, formação de vagens, condição boa/excelente) | USDA/NASS Crop Progress, via API da biblioteca Cornell | Semanal (segundas), sem chave |
| Safra Brasil (área, produção, produtividade) | CONAB — série histórica de grãos | Atualizada nos levantamentos mensais |
| Dólar e euro comercial | AwesomeAPI, com fallback Yahoo/PTAX | A AwesomeAPI limita os IPs do Actions (429) |
| PTAX, Selic, CDI, IPCA | Banco Central (Olinda e SGS) | Fontes oficiais, estáveis |
| Indicadores CEPEA (Paranaguá e Paraná), prêmio de porto e balcão nas praças | Cepea/Esalq, via Notícias Agrícolas | O site do CEPEA passou a exigir verificação da Cloudflare e responde 403 a robôs; o Notícias Agrícolas republica citando a fonte |
| Chuva 7 dias e acumulado de 30 dias (Sorriso, Sinop, Rio Verde, Dourados) | Open-Meteo (`past_days=31`) | Sem chave; o acumulado indica se a janela de plantio abre |
| Notícias | Google News RSS, Canal Rural, G1 Agronegócios, Notícias Agrícolas | Links diretos para as matérias |
| Embarques e vendas semanais dos EUA (complexo soja e milho) | USDA/FAS Export Sales (ESR) — `api.fas.usda.gov/api/esr`, header `X-Api-Key` | Mesma chave do PSD. Publicado às quintas com ~1 semana de defasagem. **Atenção:** no ESR o `marketYear` N é a safra N-1/N; no PSD é a safra N/N+1 |
| Oferta e demanda da soja (mundo, Brasil, EUA) | USDA/FAS PSD — `api.fas.usda.gov`, header `X-Api-Key` | Exige o secret `USDA_FAS_KEY`; código da commodity e atributos descobertos em tempo de execução |
| Basis (paridade de exportação vs. indicador; interior vs. porto) | Derivado das seções acima | Casa o mês de embarque do prêmio com o contrato CBOT correspondente; a série é acumulada em `data/basis_history.json` |

## Páginas

- `index.html` — painel do dia: câmbio, mercado físico, cotações, curva de
  vencimentos, opções, safra, embarques semanais, clima e notícias. Os cartões de cotação são
  clicáveis e abrem a série de 1 dia a 5 anos, com as variações acumuladas
  em dia, semana, mês, trimestre, ano e 5 anos.
- `modelo.html` — decomposição do preço em paridade de exportação + basis
  (calculada a cada hora) e a especificação do modelo de direção de preço
  em 4–8 semanas. Linkada no cabeçalho do painel.

## Documentação

`docs/Painel-Soja-Documentacao.docx` — documento completo: guia de uso e
interpretação de cada seção, fontes, mecanismo de atualização, arquitetura,
algoritmos, limitações, aplicação comercial, próximos passos e glossário.

## Ajustes comuns

- **Frequência:** mude o `cron` em `.github/workflows/update-data.yml`
  (ex.: `*/30 * * * *` para 30 min).
- **Cidades do clima:** edite a lista `CITIES` em `scripts/update_data.py`.
- **Feeds de notícias:** edite a lista `FEEDS` no mesmo arquivo.
- **Contratos cotados:** edite `YAHOO_SYMBOLS`.

## Limitações conhecidas

- O **índice de ritmo** dos embarques usa fração de ano-safra linear, que não
  corrige a sazonalidade do embarque americano (concentrado de outubro a
  fevereiro). No começo do ano-safra ele exagera o atraso. A correção exige
  perfil sazonal histórico.
- A **faixa esperada pelo mercado** para os embarques semanais, citada pelas
  matérias ("dentro do esperado"), vem de pesquisa com analistas e não é
  publicada de forma estruturada — o painel não a exibe.
- Cotações não são em tempo real (atraso das fontes + atualização horária).
- O cron do GitHub pode atrasar alguns minutos em horário de pico.
- De **opções** só há volume, não posições em aberto: a CME bloqueia
  site e API para IPs de nuvem, e o arquivo público do FTP traz apenas
  volume por produto. O OI que o painel mostra é o dos **futuros**, por
  vencimento (via Yahoo).
- Estoque final do Brasil pelo USDA não bate com o da CONAB: as duas
  instituições usam definições diferentes de estoque de passagem.
- Não há fonte gratuita e estruturada com o **percentual plantado por
  semana no Brasil**: a CONAB publica em painel Power BI (o portal é uma
  SPA sem API aberta), a AgRural divulga em release e o USDA/FAS exige
  chave de API. O painel mostra a fase do calendário e a chuva acumulada,
  que é o gatilho prático do plantio.
- Derivativos de soja da B3 (futuro SFI e opções) ficaram de fora: o boletim
  legado (`www2.bmf.com.br`) foi desligado no servidor e não há API pública
  gratuita; a liquidez desses contratos também é muito baixa.
- A série histórica do basis é construída daqui para a frente: não há
  arquivo gratuito do indicador para reconstruir o passado.
- A densidade risco-neutra (Breeden-Litzenberger) não está implementada —
  exige a cadeia de opções por strike, que nenhuma fonte gratuita expõe.
- Uso pessoal/informativo; não redistribua os dados comercialmente.
