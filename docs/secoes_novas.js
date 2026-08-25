/* Seções reescritas e novas do documento. Exporta funções que recebem os
   helpers de formatação e devolvem os parágrafos. */

module.exports = ({ P, PR, H1, H2, H3, LI, LIB, tabela, ESPACO, FORMULA, COD }) => {

/* ============================================================ ALGORITMOS */
const algoritmos = [
  H1("8. Algoritmos e cálculos"),
  P("Esta seção descreve os algoritmos em detalhe suficiente para reimplementar o " +
    "sistema, e registra as decisões numéricas e os casos de borda que custaram a ser " +
    "descobertos."),

  H2("8.1 Orquestração do coletor"),
  P("O coletor é um registro de funções independentes, executadas em duas ondas. A " +
    "primeira onda reúne os coletores autônomos, que só dependem da internet. A segunda " +
    "reúne os derivados, que dependem do resultado da primeira — hoje apenas o basis, que " +
    "precisa simultaneamente de câmbio, de Chicago e do mercado físico."),
  ...COD([
    "anterior ← ler(data.json).seções     # estado da execução passada",
    "seções, erros ← {}, []",
    "",
    "para nome, coletor em COLETORES:      # onda 1: independentes",
    "    tente:  seções[nome] ← coletor()",
    "    exceto e:",
    "        erros ← erros + (nome, e)",
    "        seções[nome] ← anterior[nome]   # herda o último valor bom",
    "",
    "para nome, derivar em DERIVADOS:      # onda 2: dependem da onda 1",
    "    tente:  seções[nome] ← derivar(seções)",
    "    exceto e:  mesmo tratamento",
    "",
    "gravar(data.json, {gerado_em, seções, erros})",
    "sair com erro apenas se |erros| = |COLETORES| + |DERIVADOS|",
  ]),
  P("A consequência prática desse desenho é que uma fonte fora do ar degrada exatamente " +
    "uma seção, e o painel mostra o valor anterior com um aviso — em vez de mostrar um " +
    "espaço vazio ou, pior, quebrar a página inteira."),

  H2("8.2 Conversões de unidade"),
  P("Metade dos erros possíveis neste domínio é de unidade. As constantes exatas:"),
  tabela(
    [{ t: "Conversão", p: 0.42 }, { t: "Fator", p: 0.2 }, { t: "Origem", p: 0.38 }],
    [
      ["1 bushel de soja", "27,2155 kg", "60 libras-peso, padrão CBOT para soja e trigo"],
      ["1 bushel de milho", "25,4012 kg", "56 libras — diferente da soja, atenção ao expandir"],
      ["1 saca", "60 kg", "Padrão brasileiro"],
      ["bushels por saca (soja)", "2,204623", "60 ÷ 27,2155"],
      ["1 short ton (farelo)", "907,185 kg", "2.000 libras — não é tonelada métrica"],
      ["Cotação da soja", "centavos de dólar por bushel", "Dividir por 100 para dólares"],
      ["Cotação do farelo", "dólares por short ton", "Já em dólares"],
      ["Cotação do óleo", "centavos de dólar por libra", "Dividir por 100"],
    ]),
  ESPACO(),
  P("As duas direções da conversão principal:"),
  ...FORMULA([
    "R$/saca  =  (¢/bushel ÷ 100) × 2,204623 × câmbio",
    "¢/bushel =  (R$/saca ÷ câmbio) ÷ 2,204623 × 100",
  ]),
  PR([["Lição aprendida em produção: "], "o prêmio de porto do Notícias Agrícolas é cotado " +
    "em dólares por bushel, não em centavos. Tratar +1,50 como 1,5 ¢/bu em vez de 150 ¢/bu " +
    "subestimava a paridade em cerca de R$ 17 por saca e produzia um basis residual de +11%, " +
    "implausível para um indicador que é essencialmente paridade menos custo portuário. " +
    "A regra que ficou: ler a unidade do cabeçalho da tabela, nunca inferir pela ordem de " +
    "grandeza do número."]),

  H2("8.3 Paridade de exportação e decomposição do basis"),
  P("É o cálculo central do sistema. A paridade de exportação responde a “quanto do preço " +
    "brasileiro é explicado por Chicago e pelo câmbio”, e o resíduo é o basis."),
  ...FORMULA([
    "paridade   = ((futuro_do_embarque + prêmio) ÷ 100) × 2,204623 × câmbio",
    "basis_porto    = indicador_Paranaguá − paridade",
    "basis_interior = preço_da_praça − indicador_Paranaguá",
  ]),
  H3("Casamento de vencimento — o passo que a maioria pula"),
  P("O prêmio é cotado por mês de embarque e precifica contra o contrato de Chicago vigente " +
    "naquele embarque. Usar o primeiro vencimento da curva, que é o reflexo automático, " +
    "produz erro de vários reais por saca sempre que o embarque e o primeiro vencimento " +
    "não coincidem."),
  ...COD([
    "alvo ← (ano, mês) extraído do rótulo do prêmio   # 'Agosto/26' → (2026, 8)",
    "para contrato em curva_ordenada_por_vencimento:",
    "    se (ano, mês) do contrato ≥ alvo:",
    "        futuro_do_embarque ← preço do contrato",
    "        parar",
  ]),
  P("Exemplo real: embarque de agosto com a curva começando em setembro seleciona set/26, " +
    "não nov/26. A diferença entre os dois contratos era de 8,5 ¢/bu — cerca de R$ 0,95 por " +
    "saca que iriam parar no basis como ruído."),
  H3("O que a paridade simplificada não inclui"),
  P("Frete rodoviário até o costado do navio, taxas portuárias, custo de originação, " +
    "margem do trading e ICMS. Todos esses componentes ficam absorvidos no nível do basis " +
    "do porto — que hoje roda perto de −1%, coerente com “paridade FOB menos custo " +
    "portuário”. Para modelagem isso não é problema: o que se modela é a variação do basis, " +
    "não o seu nível absoluto, e esses componentes são aproximadamente constantes no " +
    "horizonte de semanas."),

  H2("8.4 Seleção dos contratos da curva"),
  P("A soja negocia em sete meses de vencimento e o milho em cinco, com códigos herdados " +
    "do pregão viva-voz. Os calendários são diferentes porque cada grão segue o seu ciclo: " +
    "a soja acompanha o esmagamento, o milho a colheita americana."),
  P("Soja:"),
  tabela(
    [{ t: "Código", p: 0.14 }, { t: "Mês", p: 0.2 }, { t: "Papel no ciclo", p: 0.66 }],
    [
      ["F", "janeiro", "Safra velha americana, auge da exportação dos EUA"],
      ["H", "março", "Chegada da safra brasileira ao mercado"],
      ["K", "maio", "Safra sul-americana plenamente disponível"],
      ["N", "julho", "Contrato de referência da safra velha"],
      ["Q", "agosto", "Transição — ponte entre safra velha e nova"],
      ["U", "setembro", "Início da colheita americana"],
      ["X", "novembro", "Safra nova americana, o contrato mais líquido do ano"],
    ]),
  ESPACO(),
  P("Milho:"),
  tabela(
    [{ t: "Código", p: 0.14 }, { t: "Mês", p: 0.2 }, { t: "Papel no ciclo", p: 0.66 }],
    [
      ["H", "março", "Safra velha americana, escoamento do estoque de inverno"],
      ["K", "maio", "Referência da safra velha, antes do plantio americano definir a nova"],
      ["N", "julho", "Polinização nos EUA — o contrato mais sensível a clima do ano"],
      ["U", "setembro", "Transição, início da colheita americana; liquidez baixa"],
      ["Z", "dezembro", "Safra nova americana, o contrato de referência do milho"],
    ]),
  ESPACO(),
  P("O algoritmo gera os próximos sete vencimentos a partir do mês corrente, com uma regra " +
    "de corte: passado o dia 15, o contrato do mês corrente é descartado, porque está " +
    "próximo demais do vencimento e a liquidez migrou. O símbolo é montado como o prefixo " +
    "da commodity, o código do mês, o ano com dois dígitos e o sufixo da bolsa."),
  P("As duas curvas são buscadas numa requisição só. O endpoint que devolve posições em " +
    "aberto exige cookie e crumb, e o Yahoo limita por IP — os IPs do GitHub Actions batem " +
    "no limite com facilidade, então o par de autenticação é obtido uma vez por execução e " +
    "reaproveitado entre os coletores."),
  P("Cada contrato guarda também o spread para o vencimento anterior. Positivo é carrego: " +
    "o mercado paga para estocar. Negativo é inversão: o mercado quer o grão agora. Além " +
    "de ser a base da decisão de armazenagem, é esse número que explica o degrau descrito " +
    "a seguir."),

  H2("8.5 Contínuos e contratos: a armadilha da emenda"),
  P("Os cartões de cotação usam símbolos terminados em “=F” — ZS=F, ZC=F, ZW=F, ZM=F, " +
    "ZL=F, BZ=F. Nenhum deles é um contrato. São séries contínuas: apontam para o " +
    "vencimento ativo e trocam de contrato sozinhas quando ele se aproxima do vencimento."),
  P("O problema é como a troca aparece na série histórica. O Yahoo emenda o contrato novo " +
    "no lugar do velho sem retroajustar os preços anteriores. Como vencimentos diferentes " +
    "negociam a preços diferentes, no dia da rolagem a série dá um degrau que não " +
    "corresponde a nenhum movimento de mercado."),
  P("O caso que motivou a correção: em 25 de agosto de 2026 o ZC=F passou de setembro para " +
    "dezembro de 2026. O fechamento anterior era 491,50 ¢/bu e o novo, 523,25 — um salto de " +
    "31,75 ¢, que o painel exibia como alta de 6,46% num único dia. Três sinais mostravam " +
    "que era emenda, não mercado:"),
  tabela(
    [{ t: "Sinal", p: 0.34 }, { t: "O que mostrava", p: 0.66 }],
    [
      ["Magnitude", "6,46% num dia excede o percentil 99 do próprio milho no último ano (5,44%), contra mediana diária de 0,75%"],
      ["Intradiário", "Nenhum salto: a sessão inteira negociou entre 513 e 523, ou seja, abriu já no patamar novo"],
      ["Spread", "+31,75 ¢ é exatamente o carrego setembro→dezembro do milho, cerca de 10 a 11 ¢ por mês"],
    ]),
  ESPACO(),
  P("A correção tem três partes. A variação do dia passou a vir do endpoint de cotação, " +
    "que compara o contrato com o fechamento dele mesmo e por isso é imune à emenda. O " +
    "campo que nomeia o contrato por trás do contínuo passou a ser gravado, e o painel " +
    "exibe o vencimento ao lado do nome em cada cartão — “Milho CBOT · dez/26”. E a curva " +
    "de vencimentos, que antes só existia para a soja, passou a cobrir o milho: com " +
    "setembro e dezembro visíveis lado a lado, o degrau deixa de ser uma alta fantasma e " +
    "vira o que sempre foi, um spread de calendário."),
  P("O que continua em aberto: as variações de mais de um dia (semana, mês, trimestre, ano, " +
    "cinco anos) ainda saem da série emendada e ainda carregam os degraus das rolagens " +
    "passadas. Retroajustar exige saber a data de cada rolagem, e nenhuma fonte gratuita " +
    "publica esse histórico. O painel passou a acumular esse registro por conta própria, " +
    "um por dia, no mesmo modelo da série do basis — daqui a alguns meses o retroajuste " +
    "fica possível. Enquanto isso, a ressalva aparece no rodapé do gráfico."),
  P("Vale lembrar que o milho não usa o mesmo fator de conversão da soja: o bushel de milho " +
    "pesa 56 libras contra 60 da soja, como registra a tabela de conversões da seção 8.2. " +
    "Converter milho em reais por saca com a constante da soja subestima o valor em cerca " +
    "de 7%."),

  H2("8.6 Séries temporais e variações multi-horizonte"),
  H3("Três granularidades"),
  P("Cada símbolo guarda três séries, escolhidas para cobrir todos os períodos do painel " +
    "com o menor volume de dados possível:"),
  tabela(
    [{ t: "Série", p: 0.2 }, { t: "Janela e passo", p: 0.26 }, { t: "Períodos que atende", p: 0.54 }],
    [
      ["Intradiária", "5 dias, passo de 1 h", "1 dia e 1 semana"],
      ["Diária", "1 ano, fechamentos", "1 mês, 3 meses e 1 ano"],
      ["Semanal", "5 anos, fechamentos", "5 anos, e horizontes que a diária não alcança"],
    ]),
  ESPACO(),
  H3("Cálculo da variação"),
  P("Para cada horizonte o algoritmo calcula a data-alvo, escolhe a série que a cobre e " +
    "localiza o último fechamento em ou antes dela:"),
  ...COD([
    "para cada horizonte h em {7, 30, 91, 365, 1826} dias:",
    "    alvo ← timestamp_do_último_ponto − h × 86400",
    "    para base em (série_diária, série_semanal):     # ordem importa",
    "        se base.primeiro_timestamp ≤ alvo:          # a série cobre o alvo?",
    "            ref ← último fechamento de base com t ≤ alvo",
    "            variação[h] ← (preço_atual ÷ ref − 1) × 100",
    "            parar",
    "    # se nenhuma base cobre, o horizonte é omitido",
  ]),
  PR([["A regra de omissão é deliberada. "], "A série diária de um ano começa alguns dias " +
    "depois da marca de 365 dias; comparar contra o primeiro ponto disponível devolveria " +
    "um número plausível e errado. Preferimos não mostrar o horizonte a mostrar uma " +
    "variação de 358 dias rotulada como “ano”. Por isso a busca cai para a série semanal, " +
    "que alcança cinco anos, antes de desistir."]),
  P("A busca do fechamento de referência é linear com interrupção antecipada — as séries " +
    "estão ordenadas e têm no máximo algumas centenas de pontos, então o custo é " +
    "irrelevante. Com séries longas, busca binária seria o caminho."),

  H2("8.7 Renderização dos gráficos no navegador"),
  P("Todos os gráficos são SVG gerado em JavaScript, sem biblioteca. A escolha do SVG em " +
    "vez de canvas se justifica por três motivos: os elementos são inspecionáveis e " +
    "acessíveis, escalam sem perda em qualquer densidade de tela, e o volume de pontos " +
    "(algumas centenas) está muito abaixo do limite em que o canvas passaria a compensar."),
  H3("Mapeamento de coordenadas"),
  ...FORMULA([
    "x(i) = margem_esq + i × (largura − margens) ÷ (n − 1)",
    "y(v) = topo + (máx − v) × (altura − margens) ÷ (máx − mín)",
  ]),
  P("A escala é linear e ajustada ao mínimo e máximo da janela exibida, não a zero. Para " +
    "séries de preço de commodity isso é o correto: começar o eixo em zero comprimiria " +
    "toda a variação relevante numa faixa ilegível."),
  H3("Leitura ponto a ponto"),
  P("O evento de ponteiro devolve a coordenada em pixels da tela; ela é convertida para o " +
    "sistema do SVG usando a caixa delimitadora do elemento, e o índice do ponto mais " +
    "próximo sai da inversão da função x. O tratamento é o mesmo para mouse e toque, " +
    "porque o código escuta eventos de ponteiro genéricos."),
  H3("Fatiamento sem rede"),
  P("Trocar de período não dispara requisição: a página seleciona a série apropriada, filtra " +
    "os pontos com timestamp dentro da janela e redesenha. Isso torna a interação " +
    "instantânea e mantém o painel funcional mesmo se a conexão cair depois da carga."),

  H2("8.8 Balanço de oferta e demanda"),
  H3("Descoberta dinâmica em vez de identificadores fixos"),
  P("O catálogo do USDA tem linhas separadas para grão, farelo e óleo, com códigos numéricos " +
    "próximos e nomes parecidos. O algoritmo descobre o código da commodity e os " +
    "identificadores dos atributos pelo nome, em tempo de execução:"),
  ...COD([
    "commodities ← API('/commodities')",
    "código ← primeiro c em commodities tal que",
    "         'soybean' ∈ minúsculas(c.nome) e 'oilseed' ∈ minúsculas(c.nome)",
    "nomes ← {a.id: a.nome  para a em API('/commodityAttributes')}",
    "registros ← API(f'/commodity/{código}/world/year/{ano}')",
    "valores ← {nomes[r.attributeId]: r.value ÷ 1000  para r em registros",
    "           se r.unitId = 8}          # unitId 8 = milhares de toneladas",
  ]),
  PR([["Por que isso importa: "], "durante o desenvolvimento, uma versão que pegava o " +
    "primeiro resultado contendo “soybean” selecionou o código do farelo e reportou " +
    "produção brasileira de 50 Mt em vez de 186 Mt. Fixar identificadores numéricos é a " +
    "forma mais comum de publicar farelo achando que é grão."]),
  H3("Relação estoque/uso"),
  P("A definição de uso muda conforme o escopo, e essa é a sutileza mais fácil de errar:"),
  ...FORMULA([
    "país:  estoque_uso = estoque_final ÷ (consumo_interno + exportações)",
    "mundo: estoque_uso = estoque_final ÷ consumo_interno",
  ]),
  P("No agregado mundial a exportação é transferência entre países: somá-la ao uso conta o " +
    "mesmo grão duas vezes e achata artificialmente o indicador. A primeira versão do " +
    "coletor cometia esse erro e devolvia 19,6% onde o correto era 28,1% — diferença que " +
    "muda completamente a leitura de folga de oferta."),
  H3("Escolha do ano-safra"),
  P("O ano-safra corrente vira em setembro. Antes disso, a consulta pelo ano civil pode " +
    "devolver conjunto vazio; o algoritmo tenta o ano corrente e, se não houver registros, " +
    "recua um ano. O mês da estimativa vem no próprio registro e identifica a rodada do " +
    "WASDE a que os números pertencem."),

  H2("8.9 Extração de dados semiestruturados"),
  P("Quatro fontes não oferecem API e exigem extração. Em todas, a estratégia é ancorar em " +
    "rótulos textuais em vez de posições fixas, porque posição quebra a cada mudança de " +
    "layout e rótulo geralmente sobrevive."),
  H3("USDA Crop Progress"),
  P("A publicação vem num pacote compactado cujo arquivo principal reúne todas as culturas " +
    "num único CSV, com o identificador da tabela na primeira coluna e o tipo de linha na " +
    "segunda — título, cabeçalho, unidade, dado, rodapé. O algoritmo agrupa por " +
    "identificador, isola as tabelas cujo título menciona soja, e de cada uma extrai a " +
    "linha-resumo dos dezoito estados. Os estágios são então ordenados pelo calendário " +
    "agrícola — plantio, emergência, floração, formação de vagens, queda de folhas, " +
    "colheita — e não pela ordem em que aparecem no arquivo."),
  PR([["Detalhe de codificação: "], "os títulos usam travessão em codificação Windows-1252. " +
    "Decodificar como Latin-1 produz um caractere inválido no meio do rótulo, que vazava " +
    "para a interface como “Blooming \\x96”. A leitura correta é cp1252."]),
  H3("Planilha de volume da CME"),
  P("A aba de volume por produto é lida pelo nome das colunas, localizadas na linha de " +
    "cabeçalho, e as linhas de interesse são encontradas pela descrição exata do produto. " +
    "A data do pregão vem de uma linha de texto livre no topo, extraída por expressão " +
    "regular."),
  H3("Tabelas de cotação em HTML"),
  P("Cada bloco de cotação do Notícias Agrícolas é um título seguido de uma tabela. A " +
    "extração casa os dois numa única expressão regular com captura do título, e depois " +
    "quebra a tabela em linhas e células, removendo marcação e normalizando entidades HTML. " +
    "O resultado é um dicionário de título para matriz de células, do qual cada coletor " +
    "pega o que precisa."),
  H3("Feeds RSS"),
  P("Os feeds são lidos com o parser XML da biblioteca padrão. A remoção de duplicatas usa " +
    "uma chave derivada do título — minúsculas, sem pontuação, truncada — porque a mesma " +
    "matéria costuma aparecer em mais de um feed com pequenas variações de pontuação. A " +
    "ordenação final é por data de publicação decrescente."),

  H2("8.10 Robustez de rede"),
  tabela(
    [{ t: "Fonte", p: 0.26 }, { t: "Estratégia", p: 0.74 }],
    [
      ["Yahoo Finance", "Dois hosts alternativos por requisição; o segundo é tentado se o primeiro falhar"],
      ["Yahoo /v7/quote", "Cookie e crumb renovados a cada execução; se falhar, cai para o endpoint de gráfico, que não traz posições em aberto"],
      ["AwesomeAPI", "Troca automática para o Yahoo quando devolve limite de requisições excedido"],
      ["FTP da CME", "Até três tentativas com conexão nova a cada uma — o servidor derruba sessões com frequência"],
      ["Todas", "Tempo limite de 25 segundos e verificação de status HTTP antes de processar"],
    ]),
  ESPACO(),

  H2("8.11 Modelo de direção de preço (especificado, não implementado)"),
  P("A especificação está documentada na página do modelo e é reproduzida aqui com o " +
    "protocolo de validação detalhado."),
  tabela(
    [{ t: "Item", p: 0.24 }, { t: "Escolha e justificativa", p: 0.76 }],
    [
      ["Alvo", "Sinal do retorno em 4 a 8 semanas — classificação binária. Prever nível de preço com esta amostra é ilusão"],
      ["Algoritmo", "Gradient boosting em árvores. Cerca de 1.800 observações semanais desde 1990 é pouco para qualquer coisa mais flexível"],
      ["Validação", "Walk-forward expandindo, com purga e embargo de 8 semanas"],
      ["Métrica", "Taxa de acerto direcional e resultado financeiro de uma regra de hedge — não R², que é irrelevante para decisão binária"],
      ["Expectativa", "AUC entre 0,55 e 0,58. Acima disso, procurar vazamento antes de comemorar"],
      ["Descartado", "Redes recorrentes e transformers: razão sinal-ruído baixa e amostra curta levam à memorização de 2012 e 2020"],
    ]),
  ESPACO(),
  H3("Protocolo de validação"),
  ...COD([
    "para cada dobra k = 1..K:",
    "    treino ← observações de t₀ até fim_treino(k)      # janela expande",
    "    teste  ← observações de início_teste(k) até fim_teste(k)",
    "",
    "    # PURGA: remove do treino tudo cujo alvo invade o teste",
    "    treino ← treino \\ {i : i + horizonte ≥ início_teste(k)}",
    "",
    "    # EMBARGO: descarta as 8 semanas após o teste da próxima dobra",
    "    próximo_treino_começa_em ← fim_teste(k) + 8 semanas",
    "",
    "    ajustar(treino); avaliar(teste)",
  ]),
  P("Sem purga, uma observação cujo alvo de oito semanas se sobrepõe ao período de teste " +
    "carrega informação do futuro para dentro do treino. Sem embargo, a autocorrelação " +
    "residual entre o fim de um teste e o início do treino seguinte tem o mesmo efeito " +
    "atenuado. Ambos inflam a taxa de acerto em alguns pontos — o suficiente para um modelo " +
    "inútil parecer promissor."),
  H3("Variáveis explicativas candidatas"),
  LI("Preço: retornos defasados, distância de médias móveis, volatilidade realizada."),
  LI("Curva: inclinação dos spreads de calendário, posição relativa ao carrego cheio."),
  LI("Basis: nível e variação do basis do porto e das praças, desvio da sazonalidade."),
  LI("Fundamentos: relação estoque/uso mundial e por origem, revisões mês a mês do WASDE."),
  LI("Câmbio: nível e variação do real, diferencial de juros."),
  LI("Clima: chuva acumulada e desvio da normal nas regiões produtoras, em ambos os hemisférios."),
  LI("Posicionamento: posição líquida de fundos, quando a fonte estiver integrada."),

  H2("8.12 Densidade risco-neutra (bloqueado por falta de dados)"),
  P("O resultado de Breeden e Litzenberger (1978) diz que os preços das opções, lidos ao " +
    "longo dos preços de exercício, contêm a distribuição de probabilidade inteira que o " +
    "mercado atribui ao preço futuro. Não é preciso estimar nada — só extrair."),
  H3("Derivação em três passos"),
  ...FORMULA([
    "C(K) = e^(−rT) ∫ₖ^∞ (S − K) q(S) dS         preço da opção de compra",
    "∂C/∂K  = −e^(−rT) · P(S > K)                 probabilidade acumulada",
    "∂²C/∂K² =  e^(−rT) · q(K)                    densidade",
  ]),
  P("A primeira derivada já é útil por si: a inclinação da curva de preços das calls " +
    "informa a probabilidade risco-neutra de o preço superar cada exercício."),
  H3("A intuição da borboleta"),
  P("Comprar uma call em K−h, vender duas em K e comprar uma em K+h custa exatamente a " +
    "diferença segunda dos preços, e paga um triângulo que só rende se o preço terminar " +
    "perto de K. Apertando h, a estrutura vira uma aposta que só paga se o preço cair " +
    "naquele ponto — e o preço dela é, por definição, a probabilidade descontada de cair " +
    "ali. Breeden-Litzenberger é essa observação formalizada."),
  H3("Pipeline de implementação"),
  ...COD([
    "1. coletar C(K) para todos os exercícios de um vencimento (preço médio)",
    "2. converter para volatilidade implícita — suavizar em preço é instável",
    "3. ajustar curva suave na variância implícita total (spline cúbico ou SVI)",
    "4. reamostrar numa grade fina de K e converter de volta para preços",
    "5. impor convexidade: C decrescente e convexo em K",
    "6. diferença segunda numérica → multiplicar por e^(rT)",
    "7. colar caudas paramétricas além do último exercício listado",
    "8. normalizar para integrar a 1",
  ]),
  P("Os passos 2 e 3 não são opcionais: a segunda derivada amplifica ruído a ponto de " +
    "produzir densidades negativas quando aplicada a preços cotados crus. O passo 7 " +
    "importa porque a cauda é justamente o que interessa ao dimensionar um fence."),
  PR([["Ressalva conceitual: "], "a densidade extraída é risco-neutra, não real. Ela embute " +
    "o prêmio de risco — o mercado atribui probabilidade maior a quedas do que a " +
    "frequência histórica justificaria, porque protege-se paga. Leia como preço de cada " +
    "cenário, nunca como previsão."]),
  P("Restrição adicional: as opções de soja na CME são americanas, e o resultado é " +
    "derivado para europeias. O prêmio de exercício antecipado é pequeno em opções sobre " +
    "futuros, mas não nulo nas muito dentro do dinheiro."),
];

/* =============================================== ESTRATÉGIAS DE TRADING */
const estrategias = [
  H1("11. Estratégias de spread e arbitragem de base"),
  P("Esta seção é a continuação natural do painel: as técnicas que consomem exatamente os " +
    "dados já coletados. Nenhuma delas é recomendação — são estruturas padrão do mercado " +
    "de grãos, descritas com a mecânica e os riscos."),

  H2("11.1 Spread de calendário"),
  P("Comprar um vencimento e vender outro da mesma commodity. O resultado depende apenas da " +
    "mudança na diferença entre os dois, o que elimina boa parte do risco de nível de preço " +
    "e isola a leitura de oferta e demanda no tempo."),
  H3("O carrego cheio como régua"),
  P("O custo de carregar estoque por um mês é a soma de armazenagem, juros sobre o capital " +
    "parado e seguro:"),
  ...FORMULA([
    "carrego_cheio (¢/bu/mês) = armazenagem + (preço × taxa_juros ÷ 12) + seguro",
    "aproveitamento = spread_observado ÷ carrego_cheio × 100",
  ]),
  P("A interpretação é direta e é a base de quase toda decisão de armazenagem:"),
  tabela(
    [{ t: "Aproveitamento", p: 0.22 }, { t: "Leitura de mercado", p: 0.4 }, { t: "Implicação prática", p: 0.38 }],
    [
      ["Acima de 100%", "Insustentável — abre arbitragem de armazenagem", "Armazenar e vender futuro trava lucro"],
      ["70% a 100%", "Oferta ampla, mercado quer que você estoque", "Armazenagem se paga; vender à vista é caro"],
      ["40% a 70%", "Oferta confortável mas não abundante", "Decisão depende do custo real de cada um"],
      ["Abaixo de 40%", "Mercado não quer estoque — quer o grão agora", "Vender à vista tende a ser melhor"],
      ["Negativo (invertido)", "Aperto de oferta no disponível", "Vender à vista; carregar destrói valor"],
    ]),
  ESPACO(),
  P("Na curva atual, o trecho de novembro para janeiro paga 7,0 ¢/bu por mês, enquanto o " +
    "trecho de maio para julho paga 1,9 ¢/bu. A leitura é que o mercado remunera bem quem " +
    "carrega no pós-colheita americana, mas não remunera quem pretende carregar até depois " +
    "da chegada da safra brasileira."),
  H3("Spread de safra velha contra safra nova"),
  P("O spread entre o último contrato da safra velha e o primeiro da nova é o termômetro " +
    "mais direto da expectativa de transição. Um spread apertado ou invertido indica que o " +
    "mercado teme não chegar à nova safra com estoque suficiente; um spread largo indica " +
    "sobra confortável. No painel, é o trecho entre julho e agosto — hoje invertido em " +
    "9,1 ¢/bu por mês, o que é estrutural da passagem de ciclo e não deve ser lido como " +
    "sinal de aperto."),
  H3("Riscos"),
  LI("O spread exige margem nas duas pernas e pode consumir caixa mesmo quando a tese está correta."),
  LI("Perto do vencimento, a perna curta pode sofrer squeeze de entrega, com movimento que não reflete fundamento."),
  LI("Liquidez cai rapidamente nos vencimentos distantes — o painel já mostra posições em aberto por contrato, e é o dado a consultar antes de montar."),

  H2("11.2 Arbitragem de base"),
  P("Operar basis é separar a decisão de “quando fixar o preço” da decisão de “quando " +
    "entregar o físico”. Quem tem grão armazenado e vende futuro está comprado em basis: " +
    "ganha se o basis subir, independentemente do que Chicago fizer."),
  ...FORMULA([
    "resultado_da_operação  =  basis_no_encerramento − basis_na_montagem",
    "(o movimento do preço absoluto se cancela entre físico e futuro)",
  ]),
  H3("Quando a estrutura é favorável"),
  P("A combinação clássica é basis historicamente baixo somado a carrego alto. O produtor " +
    "que armazena, vende futuro e espera o basis normalizar captura duas coisas ao mesmo " +
    "tempo: o carrego pago pela curva e a recuperação do basis. Se o carrego pago pelo " +
    "mercado supera o custo real de armazenagem do produtor, a parcela de carrego já é " +
    "lucro travado no momento da montagem."),
  H3("Convergência"),
  P("Perto do vencimento, o basis do local de entrega converge para próximo de zero, porque " +
    "físico e futuro passam a ser substitutos. Longe do ponto de entrega — que é o caso de " +
    "toda praça brasileira em relação a Chicago — a convergência é parcial e o basis " +
    "residual reflete permanentemente frete e logística. É por isso que o basis brasileiro " +
    "não tende a zero, e sim a um patamar sazonal."),
  H3("O que falta no painel para operar isso bem"),
  P("Falta histórico. A decisão “o basis está baixo” exige a distribuição do basis para " +
    "aquela praça e aquela semana do ano. A série começou a ser acumulada e é justamente o " +
    "insumo que a seção 12 propõe transformar em gráfico sazonal."),

  H2("11.3 Spreads entre commodities"),
  H3("Margem de esmagamento"),
  P("Compra de soja contra venda de farelo e óleo, na proporção do rendimento industrial. " +
    "Um bushel rende aproximadamente 44 libras de farelo e 11 libras de óleo:"),
  ...FORMULA([
    "margem (US$/bu) = 0,022 × farelo(US$/short ton)",
    "                + 0,11  × óleo(¢/lb)",
    "                − soja(¢/bu) ÷ 100",
  ]),
  P("Com os preços atuais do painel — soja 1.225,5 ¢/bu, farelo 328,5 US$/t curta e óleo " +
    "67,33 ¢/lb — a margem é de aproximadamente US$ 2,38 por bushel. O painel já coleta as " +
    "três pernas; falta apenas o cálculo e, principalmente, o histórico para saber em que " +
    "percentil esse valor está. Margem alta puxa a demanda da indústria pelo grão e " +
    "sustenta o basis nas praças próximas a esmagadoras."),
  H3("Relação soja/milho"),
  P("A razão entre os preços dos dois contratos de novembro e dezembro orienta a decisão de " +
    "área nos Estados Unidos, e por tabela a expectativa de oferta da safra seguinte. Hoje " +
    "a relação está em 2,38. A regra prática de mercado situa o ponto de indiferença perto " +
    "de 2,4: acima disso a soja atrai área, abaixo o milho atrai. Para o produtor " +
    "brasileiro, a mesma relação informa a decisão de safrinha e de barter."),

  H2("11.4 Arbitragem geográfica"),
  P("O painel mostra onze praças simultaneamente. Sempre que a diferença entre duas praças " +
    "supera o custo de frete entre elas, existe arbitragem física — na prática capturada " +
    "por quem tem logística, mas informativa para todos, porque indica para onde o grão " +
    "vai fluir e onde o basis tende a ceder."),
  P("Hoje o leque entre Rondonópolis e Rio Verde é de R$ 13 por saca. Saber se isso é " +
    "oportunidade ou apenas frete exige o custo de transporte da rota — dado que a seção 13 " +
    "propõe integrar a partir do índice de frete da ESALQ-LOG."),

  H2("11.5 Estruturas com opções"),
  P("Listadas por completude; todas dependem da cadeia de opções por exercício, ainda " +
    "bloqueada."),
  LIB("Collar", "compra de put e venda de call, calibradas para custo próximo de zero. " +
    "Estabelece piso abrindo mão do que estiver acima do teto."),
  LIB("Fence", "variação do collar com três exercícios, que preserva parte da alta."),
  LIB("Acumulador", "venda escalonada com gatilhos, atraente quando a densidade indica " +
    "baixa probabilidade de rompimento do teto — e perigoso exatamente quando ela indica o contrário."),
  LIB("Venda coberta de call", "produtor com físico vende call para gerar receita. É " +
    "operação de viés baixista a neutro, e responde por parte do volume de calls que o " +
    "painel reporta."),
];

/* ================================================= GRÁFICOS SUGERIDOS */
const graficos = [
  H1("12. Gráficos sugeridos para vendedores e originadores"),
  P("Propostas ordenadas por relação entre utilidade e esforço. A coluna de dados indica " +
    "o que já existe e o que falta."),

  H2("12.1 Basis sazonal"),
  P("Basis médio por semana do ano, com faixa de mínimo e máximo históricos, e o ano " +
    "corrente sobreposto em destaque."),
  PR([["É o gráfico mais valioso da lista. "], "Responde à pergunta central do produtor — " +
    "“o basis está bom para vender agora?” — que nenhum número isolado responde. Um basis " +
    "de −R$ 1,50 pode ser excelente ou péssimo dependendo da época do ano."]),
  P("Dados: a série já está sendo acumulada. Exige alguns ciclos de safra para ter faixa " +
    "histórica confiável; com um ano já é possível mostrar a curva do ano corrente."),

  H2("12.2 Aproveitamento do carrego"),
  P("Barras horizontais, uma por spread da curva, mostrando quanto do carrego cheio o " +
    "mercado está pagando, com faixas coloridas de referência."),
  P("Transforma a curva de vencimentos numa decisão direta de armazenagem, em vez de exigir " +
    "que o usuário faça a conta mentalmente. Dados: preços já coletados; falta parametrizar " +
    "custo de armazenagem e taxa de juros, que idealmente o usuário informa."),

  H2("12.3 Termômetro de percentil"),
  P("Faixa horizontal mostrando onde o preço atual em reais por saca se situa na " +
    "distribuição dos últimos cinco anos, com marcações de quartil e a mediana."),
  P("Responde “está bom?” de forma imediata e visual. Deve ser feito em reais por saca, não " +
    "em centavos por bushel, porque é a moeda da decisão do produtor — e porque o câmbio " +
    "pode deixar o preço em reais em máxima histórica enquanto Chicago está em mínima."),
  P("Dados: a série de cinco anos já é coletada; falta apenas convertê-la para reais com o " +
    "câmbio histórico, que precisa ser adicionado à coleta."),

  H2("12.4 Mapa de calor de praças por mês"),
  P("Matriz com praças nas linhas e meses nas colunas, colorida pelo basis. Revela de uma " +
    "vez o padrão sazonal de cada praça e onde estão as melhores janelas de originação."),
  P("Público principal: originadores, que decidem onde comprar. Dados: exige o histórico " +
    "por praça, que a coleta atual já registra diariamente."),

  H2("12.5 Margem de esmagamento com histórico"),
  P("Linha da margem calculada pela fórmula da seção 11.3, com faixa de percentis. " +
    "Indicador antecedente da demanda industrial pelo grão."),
  P("Dados: as três pernas já são coletadas em série de cinco anos — este gráfico pode ser " +
    "construído imediatamente, inclusive com histórico completo."),

  H2("12.6 Decomposição comparada no tempo"),
  P("A cascata de paridade e basis que a página do modelo já mostra, com duas datas lado a " +
    "lado, atribuindo a variação do preço a cada componente."),
  P("Responde “por que o preço caiu?” separando culpa entre Chicago, câmbio e basis — e " +
    "cada uma dessas causas pede uma reação diferente do vendedor. Dados: a série do basis, " +
    "acumulando."),

  H2("12.7 Relação de troca"),
  P("Soja contra milho e soja contra os principais insumos, normalizados, para decisão de " +
    "área e de barter. Dados de preço de insumo exigem fonte nova."),

  H2("12.8 Chuva acumulada contra a normal climatológica"),
  P("O painel já mostra o acumulado de trinta dias em valor absoluto. Compará-lo com a " +
    "média histórica da mesma época transforma um número solto em sinal: 40 mm pode ser " +
    "excelente em agosto e catastrófico em dezembro."),
  P("Dados: a Open-Meteo tem API de reanálise histórica gratuita, o que permite calcular a " +
    "normal de trinta anos para cada praça."),

  H2("12.9 Volatilidade implícita e realizada"),
  P("Duas linhas sobrepostas. Quando a implícita está abaixo da realizada, proteção está " +
    "relativamente barata; o inverso favorece quem vende prêmio. Depende da cadeia de " +
    "opções."),
];

/* ====================================================== FONTES ADICIONAIS */
const fontesNovas = [
  H1("13. Fontes de dados adicionais sugeridas"),
  P("Avaliadas por relevância, custo e dificuldade de integração. As gratuitas aparecem " +
    "primeiro porque podem ser integradas imediatamente."),

  H2("13.1 Gratuitas, de alto impacto"),
  tabela(
    [{ t: "Fonte", p: 0.24 }, { t: "O que traz", p: 0.42 }, { t: "Observação", p: 0.34 }],
    [
      ["USDA FAS — Export Sales", "Vendas semanais de exportação dos EUA por destino, incluindo China",
        "Usa a mesma chave de API que o painel já possui. Ganho imediato"],
      ["CFTC — Commitments of Traders", "Posição líquida semanal de fundos e comerciais em soja",
        "Gratuito. É a variável de posicionamento que falta ao modelo"],
      ["Comex Stat / Secex", "Exportação brasileira por produto, porto e destino",
        "API pública do governo. Permite acompanhar o ritmo de embarque"],
      ["ANTAQ", "Movimentação portuária e estatística aquaviária",
        "Dados públicos. Complementa a leitura de gargalo logístico"],
      ["INMET", "Estações meteorológicas brasileiras, dados observados",
        "Complementa a Open-Meteo com medição de superfície"],
      ["Open-Meteo Archive", "Reanálise histórica de clima desde 1940",
        "Gratuita. Habilita a comparação com a normal climatológica"],
      ["NASA / Copernicus", "Índices de vegetação por satélite (NDVI, EVI)",
        "Gratuito. Sinal antecedente de produtividade, mas exige processamento"],
      ["BCB — Focus", "Expectativas de mercado para câmbio, juros e inflação",
        "API pública do Banco Central, mesma família das já usadas"],
    ]),
  ESPACO(),
  PR([["Prioridade sugerida: "], "Export Sales e Commitments of Traders. O primeiro porque " +
    "usa a chave que já existe e mede a demanda efetiva semana a semana; o segundo porque " +
    "posicionamento de fundos é uma das variáveis explicativas mais citadas na literatura " +
    "de retorno de commodities, e é gratuito."]),

  H2("13.2 Físico brasileiro"),
  tabela(
    [{ t: "Fonte", p: 0.24 }, { t: "O que traz", p: 0.42 }, { t: "Custo", p: 0.34 }],
    [
      ["IMEA", "Indicadores e progresso de safra de Mato Grosso", "Gratuito no portal, mas em PDF — exige extração"],
      ["Deral / SEAB-PR", "Preços e progresso de safra do Paraná", "Gratuito, planilhas públicas semanais"],
      ["ESALQ-LOG", "Índice de frete rodoviário de grãos por rota", "Gratuito com registro. Desbloqueia a arbitragem geográfica"],
      ["CEPEA direto", "Todos os indicadores, sem intermediário", "Licenciamento pago — resolve a fragilidade atual"],
      ["Safras & Mercado, StoneX, AgRural", "Estimativas privadas de safra e progresso de plantio", "Assinatura paga"],
    ]),
  ESPACO(),

  H2("13.3 Mercado e derivativos"),
  tabela(
    [{ t: "Fonte", p: 0.24 }, { t: "O que desbloqueia", p: 0.42 }, { t: "Custo", p: 0.34 }],
    [
      ["Barchart", "Cadeia de opções por exercício, dados de futuros confiáveis", "Assinatura, faixa acessível. Desbloqueia a densidade risco-neutra"],
      ["CME DataMine", "Dados oficiais da bolsa, incluindo posições em aberto de opções", "Pago, por conjunto de dados"],
      ["B3 UP2DATA", "Derivativos brasileiros, incluindo o contrato de soja", "Gratuito mediante cadastro — vale testar"],
      ["Refinitiv / Bloomberg", "Cobertura completa de mercado", "Custo elevado, adequado apenas a operação profissional"],
    ]),
  ESPACO(),
  P("Do ponto de vista de retorno sobre esforço, uma assinatura do Barchart resolve " +
    "simultaneamente a fragilidade do Yahoo Finance e a lacuna da cadeia de opções — as " +
    "duas maiores limitações técnicas do sistema."),
];

/* ==================================================== CASOS DE USO */
const casosUso = [
  H1("14. Casos de uso pontuais para expansão"),
  P("Funcionalidades estreitas, cada uma resolvendo um problema específico de um usuário " +
    "específico. São propostas de produto, não de infraestrutura — deliberadamente pequenas " +
    "para poderem ser construídas e descartadas rápido."),

  H2("14.1 Semáforo de venda"),
  LIB("Problema", "o produtor olha para dez números e não conclui nada."),
  LIB("Solução", "um indicador único, verde, amarelo ou vermelho, combinando três " +
    "componentes: percentil do preço em reais nos últimos cinco anos, percentil do basis " +
    "para aquela praça e semana, e aproveitamento do carrego."),
  LIB("Entrega", "um bloco no topo do painel com o veredito e as três razões explícitas — " +
    "nunca só o veredito, para que o usuário possa discordar com base no raciocínio."),
  LIB("Depende de", "histórico de basis e de preço em reais."),

  H2("14.2 Calculadora de trava"),
  LIB("Problema", "“quanto da minha safra eu já deveria ter vendido?”"),
  LIB("Solução", "o usuário informa custo de produção por saca, área e volume já vendido; a " +
    "ferramenta mostra a margem travada, a margem em risco e quanto o preço pode cair antes " +
    "de a safra virar prejuízo."),
  LIB("Entrega", "formulário simples com resultado gráfico, sem cadastro — os dados ficam " +
    "no próprio navegador."),
  LIB("Depende de", "nada além do que já existe. É o caso de uso mais barato da lista."),

  H2("14.3 Alerta de basis por praça"),
  LIB("Problema", "o produtor não fica olhando o painel o dia inteiro e perde a janela."),
  LIB("Solução", "o usuário escolhe a praça e um limite — em reais por saca ou em percentil " +
    "histórico — e recebe aviso quando é atingido."),
  LIB("Entrega", "notificação por e-mail, Telegram ou WhatsApp, disparada pelo mesmo processo " +
    "horário que já roda."),
  LIB("Depende de", "canal de envio e alguma forma de armazenar preferências."),

  H2("14.4 Ficha diária do produtor"),
  LIB("Problema", "o produtor quer o resumo no celular, não uma página para navegar."),
  LIB("Solução", "uma imagem ou PDF de uma página, gerado automaticamente toda manhã, com " +
    "preço da praça, basis, variações e a manchete do dia."),
  LIB("Entrega", "arquivo publicado num endereço fixo e enviado por mensagem, pronto para " +
    "encaminhar em grupo."),
  LIB("Depende de", "geração de imagem no processo automatizado."),

  H2("14.5 Painel por praça"),
  LIB("Problema", "o produtor de Sorriso não quer ver onze praças."),
  LIB("Solução", "o endereço aceita um parâmetro de praça e o painel se reorganiza em torno " +
    "dela: preço local em destaque, basis contra o porto, e as demais praças como referência."),
  LIB("Entrega", "endereços do tipo /painel-soja/?praca=sorriso, compartilháveis e " +
    "salváveis como favorito."),
  LIB("Depende de", "nada — é reorganização da interface existente."),

  H2("14.6 Simulador de armazenagem"),
  LIB("Problema", "“vendo agora ou guardo?”"),
  LIB("Solução", "compara vender à vista hoje contra armazenar e vender no contrato futuro, " +
    "descontando custo de armazenagem, juros e perda técnica, e mostra o resultado nas duas " +
    "pontas."),
  LIB("Entrega", "tabela comparativa por vencimento, com o ponto de indiferença destacado."),
  LIB("Depende de", "curva já coletada e parâmetros de custo informados pelo usuário."),

  H2("14.7 Comparador de ofertas"),
  LIB("Problema", "o produtor recebe ofertas de três compradores e não sabe qual é boa."),
  LIB("Solução", "o usuário registra as ofertas e a ferramenta as posiciona contra o " +
    "indicador da praça, o porto e a paridade, mostrando o basis implícito de cada uma."),
  LIB("Entrega", "entrada rápida no navegador, sem cadastro."),
  LIB("Depende de", "nada além do que já existe."),

  H2("14.8 Boletim semanal para cooperativa"),
  LIB("Problema", "a cooperativa quer comunicar mercado aos associados sem ter analista."),
  LIB("Solução", "documento semanal gerado automaticamente com o quadro do mercado, a " +
    "posição da praça da cooperativa e os destaques da semana."),
  LIB("Entrega", "documento pronto para distribuição, com marca da cooperativa."),
  LIB("Depende de", "geração de documento no processo automatizado — a mesma mecânica " +
    "usada para produzir este arquivo."),

  H2("14.9 Registro de vendas e preço médio"),
  LIB("Problema", "o produtor não sabe se está vendendo melhor ou pior que o mercado."),
  LIB("Solução", "registro simples de cada venda — data, volume, preço — e comparação do " +
    "preço médio realizado com a média do período e com estratégias de referência, como " +
    "vender tudo na colheita ou vender em parcelas iguais."),
  LIB("Entrega", "histórico pessoal guardado no navegador, com gráfico comparativo."),
  LIB("Depende de", "série de preços, já coletada."),
];

return { algoritmos, estrategias, graficos, fontesNovas, casosUso };
};
