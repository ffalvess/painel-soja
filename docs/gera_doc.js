const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  PageBreak, LevelFormat, convertInchesToTwip,
} = require("docx");
const fs = require("fs");
const novas = require("./secoes_novas.js");

const VERDE = "2E6B3E";
const CINZA = "5A5A55";
const TINTA = "1A1A1A";
const LARGURA = 9360; // 6.5" em DXA

/* ---------------------------------------------------------------- helpers */

const P = (texto, opts = {}) =>
  new Paragraph({
    spacing: { after: opts.after ?? 120, line: 276 },
    alignment: opts.align,
    indent: opts.indent,
    border: opts.border,
    children: [new TextRun({ text: texto, size: opts.size ?? 21,
      color: opts.color ?? TINTA, bold: opts.bold, italics: opts.italics,
      font: opts.font })],
  });

/* parágrafo com trechos em negrito: partes = ["normal", ["negrito"], "normal"] */
const PR = (partes, opts = {}) =>
  new Paragraph({
    spacing: { after: opts.after ?? 120, line: 276 },
    children: partes.map((p) =>
      Array.isArray(p)
        ? new TextRun({ text: p[0], bold: true, size: 21, color: TINTA })
        : new TextRun({ text: p, size: 21, color: TINTA })),
  });

const H1 = (texto) =>
  new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 160 },
    children: [new TextRun({ text: texto, size: 30, bold: true, color: VERDE })],
  });

const H2 = (texto) =>
  new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 240, after: 110 },
    children: [new TextRun({ text: texto, size: 24, bold: true, color: TINTA })],
  });

const H3 = (texto) =>
  new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 180, after: 90 },
    children: [new TextRun({ text: texto, size: 21, bold: true, color: CINZA })],
  });

const LI = (texto, nivel = 0) =>
  new Paragraph({
    numbering: { reference: "balas", level: nivel },
    spacing: { after: 70, line: 276 },
    children: [new TextRun({ text: texto, size: 21, color: TINTA })],
  });

/* item de lista com o começo em negrito, separado por " — " */
const LIB = (chave, resto, nivel = 0) =>
  new Paragraph({
    numbering: { reference: "balas", level: nivel },
    spacing: { after: 70, line: 276 },
    children: [
      new TextRun({ text: chave, bold: true, size: 21, color: TINTA }),
      new TextRun({ text: " — " + resto, size: 21, color: TINTA }),
    ],
  });

const cel = (texto, { larg, cab = false, bold = false, span } = {}) =>
  new TableCell({
    width: { size: larg, type: WidthType.DXA },
    columnSpan: span,
    shading: cab
      ? { type: ShadingType.CLEAR, fill: "EDF2ED", color: "auto" }
      : undefined,
    margins: { top: 80, bottom: 80, left: 110, right: 110 },
    children: [
      new Paragraph({
        spacing: { after: 0, line: 264 },
        children: [new TextRun({
          text: texto, size: 19, bold: cab || bold,
          color: cab ? VERDE : TINTA,
        })],
      }),
    ],
  });

const tabela = (colunas, linhas) => {
  // a última coluna absorve a sobra do arredondamento, para a soma bater com
  // a largura da tabela — o Word desalinha a grade se não bater
  const larguras = colunas.map((c) => Math.round(LARGURA * c.p));
  larguras[larguras.length - 1] +=
    LARGURA - larguras.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: LARGURA, type: WidthType.DXA },
    columnWidths: larguras,
    borders: {
      top: { style: BorderStyle.SINGLE, size: 2, color: "D5D5CE" },
      bottom: { style: BorderStyle.SINGLE, size: 2, color: "D5D5CE" },
      left: { style: BorderStyle.SINGLE, size: 2, color: "D5D5CE" },
      right: { style: BorderStyle.SINGLE, size: 2, color: "D5D5CE" },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: "E6E6E0" },
      insideVertical: { style: BorderStyle.SINGLE, size: 2, color: "E6E6E0" },
    },
    rows: [
      new TableRow({
        tableHeader: true,
        children: colunas.map((c, i) => cel(c.t, { larg: larguras[i], cab: true })),
      }),
      ...linhas.map((l) =>
        new TableRow({
          children: l.map((t, i) => cel(String(t), { larg: larguras[i] })),
        })),
    ],
  });
};

const ESPACO = () => new Paragraph({ spacing: { after: 100 }, children: [] });

const REGRA = () =>
  new Paragraph({
    spacing: { before: 60, after: 200 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: VERDE } },
    children: [],
  });


/* bloco de fórmula / pseudocódigo, com fundo claro e fonte monoespaçada */
const BLOCO = (linhas, fundo) => linhas.map((l, i) =>
  new Paragraph({
    spacing: { before: i === 0 ? 100 : 0, after: i === linhas.length - 1 ? 140 : 0, line: 240 },
    shading: { type: ShadingType.CLEAR, fill: fundo, color: "auto" },
    indent: { left: 220, right: 220 },
    children: [new TextRun({ text: l || " ", font: "Consolas", size: 18, color: TINTA })],
  }));
const FORMULA = (linhas) => BLOCO(linhas, "F1F5F1");
const COD = (linhas) => BLOCO(linhas, "F4F4F1");

/* ---------------------------------------------------------------- conteúdo */

const capa = [
  new Paragraph({ spacing: { before: 2600, after: 0 }, children: [
    new TextRun({ text: "PAINEL SOJA", size: 56, bold: true, color: VERDE })] }),
  new Paragraph({ spacing: { after: 260 }, children: [
    new TextRun({ text: "Documentação técnica e guia de uso", size: 28, color: CINZA })] }),
  REGRA(),
  PR([["Painel de mercado da soja para o Centro-Oeste"],
    ": cotações de Chicago, curva de vencimentos, mercado físico brasileiro, " +
    "balanço de oferta e demanda, andamento de safra, clima nas regiões produtoras e notícias — " +
    "atualizado automaticamente, sem servidor e sem custo de operação."], { after: 200 }),
  ESPACO(),
  tabela(
    [{ t: "Item", p: 0.3 }, { t: "Detalhe", p: 0.7 }],
    [
      ["Endereço", "https://ffalvess.github.io/painel-soja/"],
      ["Repositório", "github.com/ffalvess/painel-soja"],
      ["Páginas", "index.html (painel) e modelo.html (basis e modelo)"],
      ["Atualização", "Automática, de hora em hora"],
      ["Fontes ativas", "11 seções de dados, todas gratuitas"],
      ["Custo de operação", "Zero — GitHub Pages e Actions no plano gratuito"],
      ["Versão do documento", new Date().toLocaleDateString("pt-BR")],
    ]),
  new Paragraph({ children: [new PageBreak()] }),
];

const sumario = [
  H1("Conteúdo"),
  ...[
    "1. Visão geral",
    "2. Público-alvo",
    "3. Como usar: acesso e navegação",
    "4. Interpretação das informações",
    "5. Fontes utilizadas",
    "6. Mecanismo de atualização",
    "7. Arquitetura e linguagens",
    "8. Algoritmos e cálculos",
    "9. Limitações conhecidas",
    "10. Aplicação comercial",
    "11. Estratégias de spread e arbitragem de base",
    "12. Gráficos sugeridos para vendedores e originadores",
    "13. Fontes de dados adicionais sugeridas",
    "14. Casos de uso pontuais para expansão",
    "15. Próximos passos sugeridos",
    "16. Glossário",
  ].map((t) => P(t, { after: 80 })),
  new Paragraph({ children: [new PageBreak()] }),
];

const visao = [
  H1("1. Visão geral"),
  P("O Painel Soja reúne, numa única página, as variáveis que formam o preço recebido " +
    "pelo produtor de soja no Centro-Oeste. A premissa central é que o produtor não recebe " +
    "em centavos de dólar por bushel: ele recebe em reais por saca de 60 kg, e esse preço " +
    "é o resultado de três camadas — o futuro em Chicago, a taxa de câmbio e o basis " +
    "(prêmio de porto e desconto de interior)."),
  P("O sistema é composto por um coletor em Python que roda de hora em hora no GitHub " +
    "Actions e grava um arquivo JSON, e por duas páginas estáticas que leem esse arquivo. " +
    "Não há servidor, banco de dados nem custo recorrente."),
  H2("Princípio de projeto: falha isolada"),
  P("Cada fonte de dados é coletada de forma independente. Se uma delas sai do ar, a seção " +
    "correspondente mantém o último valor conhecido, o erro fica registrado no arquivo de " +
    "dados e o restante do painel continua funcionando normalmente. O painel nunca quebra " +
    "por causa de uma fonte indisponível — uma decisão importante, porque várias das fontes " +
    "são páginas públicas sem contrato de disponibilidade."),
  H2("O que o painel não é"),
  P("Não é uma ferramenta de execução nem de recomendação. Não há sinal de compra ou venda, " +
    "não há previsão de preço em produção e os dados têm atraso de pelo menos 15 minutos. " +
    "É um instrumento de leitura de mercado e apoio à decisão."),
];

const publico = [
  H1("2. Público-alvo"),
  H2("Usuário primário"),
  LIB("Produtor rural e gestor de fazenda no Centro-Oeste",
    "acompanha o preço de balcão na própria praça, compara com o porto e decide o " +
    "momento de vender. A régua de variações (dia, semana, mês, trimestre, ano) responde " +
    "à pergunta prática “o preço está bom em relação a quando?”."),
  LIB("Originador e mesa de comercialização",
    "usa a decomposição de paridade e basis para avaliar onde está a margem entre " +
    "originar no interior e embarcar no porto, e o prêmio por mês de embarque para " +
    "programar logística."),
  H2("Usuário secundário"),
  LIB("Consultor e assessor de comercialização agrícola",
    "material de apoio em reuniões com produtores: uma página com o quadro completo, " +
    "atualizada, com fonte identificada em cada número."),
  LIB("Analista de risco e estruturador",
    "curva de vencimentos com posições em aberto, fluxo de opções e balanço de oferta " +
    "e demanda para dimensionar hedge e estruturas."),
  LIB("Estudante e pesquisador de agronegócio",
    "o repositório é público e o código é legível: serve como exemplo de coleta e " +
    "tratamento de dados agrícolas reais."),
  H2("Pré-requisito de leitura"),
  P("O painel assume familiaridade com conceitos básicos de mercado futuro (contrato, " +
    "vencimento, basis). O glossário na seção 16 cobre os termos usados. Não é necessário " +
    "nenhum conhecimento técnico de programação para usar."),
];

const uso = [
  H1("3. Como usar: acesso e navegação"),
  H2("Endereço"),
  PR([["https://ffalvess.github.io/painel-soja/"],
    " — abre direto no navegador, em qualquer dispositivo. Não há login, cadastro nem " +
    "instalação. A página é responsiva e se adapta a celular e tablet; tabelas largas " +
    "rolam horizontalmente dentro do próprio quadro."]),
  P("O painel se ajusta automaticamente ao tema claro ou escuro do sistema operacional."),
  H2("As duas páginas"),
  tabela(
    [{ t: "Página", p: 0.22 }, { t: "Endereço", p: 0.3 }, { t: "Para quê", p: 0.48 }],
    [
      ["Painel", "/painel-soja/", "Leitura diária do mercado: preços, físico, safra, clima, notícias"],
      ["Modelo e basis", "/painel-soja/modelo.html", "Decomposição do preço, série do basis e especificação do modelo"],
    ]),
  ESPACO(),
  P("A navegação entre as duas é feita pelo botão no cabeçalho: “Modelo e basis →” no " +
    "painel, e “← Painel Soja” na página do modelo."),
  H2("Detalhe das cotações"),
  P("Os cartões da seção “Grãos, energia e bolsa” são clicáveis. Ao clicar, abre-se uma " +
    "janela com:"),
  LI("seletor de período: 1 dia, 1 semana, 1 mês, 3 meses, 1 ano e 5 anos;"),
  LI("gráfico com leitura ponto a ponto — passe o mouse ou o dedo sobre a linha para ver a data e o valor;"),
  LI("régua de variações acumuladas em dia, semana, mês, trimestre, ano e 5 anos."),
  P("A janela fecha com a tecla Esc, com o × no canto ou clicando fora dela. A troca de " +
    "período é instantânea porque todas as séries já vêm carregadas — não há nova consulta " +
    "à internet a cada clique.", { after: 160 }),
  H2("Frequência de leitura sugerida"),
  LIB("Diária, pela manhã", "preço de fechamento de Chicago, câmbio, indicador do dia e notícias."),
  LIB("Semanal", "andamento da safra nos EUA (o USDA publica às segundas) e prêmio de porto."),
  LIB("Mensal", "balanço de oferta e demanda do USDA, que muda a cada revisão do WASDE, e os levantamentos da CONAB."),
];

const interpretacao = [
  H1("4. Interpretação das informações"),
  P("Esta seção explica o que cada bloco significa e, principalmente, o que ele não " +
    "significa — as leituras equivocadas mais comuns estão sinalizadas."),

  H2("4.1 Câmbio e macro"),
  P("Dólar e euro comerciais, PTAX de fechamento, Selic, CDI e IPCA. O dólar é a variável " +
    "de maior impacto imediato no preço em reais: uma alta de 1% no câmbio, com Chicago " +
    "parado, eleva o preço em reais em aproximadamente 1%."),
  PR([["Atenção: "], "o dólar comercial é a cotação de mercado em tempo quase real; a PTAX é " +
    "o fechamento oficial do Banco Central do dia anterior. Contratos indexados costumam " +
    "usar a PTAX, não o comercial."]),

  H2("4.2 Mercado físico"),
  P("Três blocos complementares:"),
  LIB("Indicadores CEPEA/ESALQ", "referência de preço em Paranaguá e no Paraná, em R$ por " +
    "saca de 60 kg. É o número que o mercado brasileiro cita como “o preço da soja”."),
  LIB("Balcão nas praças produtoras", "preço efetivamente pago ao produtor em onze praças, " +
    "de Sorriso a Luís Eduardo Magalhães, mais os portos de Paranaguá e Santos."),
  LIB("Prêmio de porto de Paranaguá", "quanto o mercado paga acima do futuro de Chicago " +
    "para embarque em cada mês, em US$ por bushel."),
  P("A diferença entre praças é essencialmente frete e poder de barganha local. Um leque de " +
    "R$ 12 por saca entre Rondonópolis e Rio Verde não é erro: é o custo de tirar a soja " +
    "do interior."),
  PR([["Leitura importante: "], "prêmio de porto positivo e alto com Chicago fraco significa " +
    "que o produtor brasileiro está sendo relativamente bem pago apesar de um quadro " +
    "global baixista. O prêmio é onde aparece a disputa por origem — por exemplo, a China " +
    "comprando Brasil em vez dos Estados Unidos. Isso não aparece no preço de Chicago."]),

  H2("4.3 Grãos, energia e bolsa"),
  P("Soja, milho, farelo, óleo e trigo em Chicago, mais Brent e Ibovespa como contexto " +
    "macro. Farelo e óleo importam porque definem a margem de esmagamento, que é quem " +
    "puxa a demanda industrial pelo grão. O Brent entra pela ligação com biodiesel, que " +
    "sustenta a demanda de óleo de soja."),
  P("No cartão da soja aparece a conversão aproximada para R$ por saca, calculada apenas " +
    "com Chicago e câmbio — sem prêmio nem frete. É referência rápida, não preço de venda."),

  H2("4.4 Curva de vencimentos"),
  P("Preço, variação, equivalência em reais por saca, volume do dia e posições em aberto " +
    "para os próximos sete vencimentos da soja em Chicago."),
  H3("Como ler a inclinação"),
  LIB("Curva ascendente (contango)", "o mercado paga para você carregar estoque. Só existe " +
    "quando não falta produto no disponível. Indica oferta confortável."),
  LIB("Curva descendente (backwardation)", "quem precisa do grão agora paga mais que quem " +
    "aceita esperar. Sinal de aperto imediato de oferta."),
  P("A inclinação não é uniforme e é justamente aí que está a informação. Um trecho pagando " +
    "carrego cheio logo após a colheita americana, seguido de achatamento nos meses em que " +
    "a safra brasileira chega ao mercado, mostra que o mercado já precificou a oferta " +
    "sul-americana. A queda no último vencimento do ciclo é estrutural — ali a curva " +
    "atravessa para o ano-safra seguinte — e não deve ser lida como sinal."),
  H3("Posições em aberto"),
  P("“Em aberto” é quanto ainda está posicionado no contrato, não o giro do dia. A " +
    "concentração em um vencimento indica onde está o interesse real do mercado — " +
    "tipicamente o contrato da safra nova. É um dado de futuros, não de opções."),

  H2("4.5 Opções de soja em Chicago"),
  P("Volume de calls e puts negociados no pregão anterior e a razão put/call."),
  PR([["Este é o bloco mais fácil de interpretar errado. "],
    "Volume de opções não indica direção. Toda call negociada tem um comprador e um " +
    "vendedor, e vender call contra estoque físico — prática comum entre produtores para " +
    "financiar hedge — é operação baixista. Um volume alto de calls pode significar tanto " +
    "aposta na alta quanto o seu oposto exato."]),
  P("Três limitações adicionais: é o giro de um único pregão, não posição acumulada; não se " +
    "sabe se as operações abriram ou fecharam posição, porque a CME não publica posições em " +
    "aberto de opções por produto de forma gratuita; e não há a distribuição por preço de " +
    "exercício, sem a qual comprar proteção barata e vender opcionalidade cara ficam " +
    "indistinguíveis no mesmo número."),
  P("A leitura direcional correta exige a densidade risco-neutra, descrita na seção 8. " +
    "Enquanto ela não estiver disponível, este bloco é descritivo."),

  H2("4.6 Safra"),
  H3("Estados Unidos — USDA Crop Progress"),
  P("Percentual da área de soja que já atingiu cada estágio, nos dezoito estados que " +
    "respondem por 96% da área plantada americana. A barra mostra o estágio atual e o " +
    "traço vertical marca a média das cinco safras anteriores na mesma época, de modo que " +
    "se lê de imediato se a lavoura está adiantada ou atrasada."),
  P("A condição da lavoura aparece como faixa colorida de “muito ruim” a “excelente”. O " +
    "número que o mercado acompanha é a soma de “boa” e “excelente”, comparada com a " +
    "semana anterior e com o ano passado. Uma queda de vários pontos percentuais contra o " +
    "ano anterior costuma anteceder revisão de produtividade."),
  H3("Brasil — CONAB e calendário"),
  P("Área, produção e produtividade da safra corrente com variação sobre a anterior, mais " +
    "a fase do calendário agrícola e a chuva acumulada em trinta dias por praça."),
  PR([["Por que chuva acumulada: "], "não existe fonte gratuita e estruturada com o " +
    "percentual plantado por semana no Brasil. A umidade do solo é o gatilho prático da " +
    "semeadura — sem chuva o produtor não planta, mesmo dentro da janela do calendário. " +
    "É a melhor aproximação automatizável do andamento do plantio."]),
  H3("Mundo — balanço de oferta e demanda"),
  P("Produção, consumo, exportação, estoque final e relação estoque/uso para mundo, Brasil " +
    "e Estados Unidos, direto do USDA."),
  PR([["A relação estoque/uso é o indicador de folga mais importante do painel. "],
    "Quanto maior, mais confortável a oferta e menor a chance de disparada de preço; " +
    "quanto menor, mais sensível o mercado a qualquer quebra de safra. Note que para " +
    "mundo o cálculo usa apenas o consumo, porque no agregado global a exportação é " +
    "transferência entre países; para Brasil e Estados Unidos a exportação entra no uso."]),

  H2("4.7 Chuva nos próximos sete dias"),
  P("Previsão de precipitação diária em Sorriso, Sinop, Rio Verde e Dourados, com total " +
    "acumulado e faixa de temperatura. Relevante em duas janelas: no plantio, definindo " +
    "quando a semeadura começa; e no enchimento de grãos, quando a falta de chuva vira " +
    "quebra de produtividade."),

  H2("4.8 Notícias"),
  P("Manchetes com link direto das redações citadas, ordenadas por horário de publicação. " +
    "Serve para dar contexto ao que os números mostram — uma alta de prêmio geralmente tem " +
    "uma notícia por trás."),

  H2("4.9 Página Modelo e basis"),
  H3("Decomposição do preço"),
  P("A cadeia completa, do pregão de Chicago ao balcão do produtor: futuro do contrato " +
    "correspondente ao embarque, mais o prêmio de porto, multiplicado pelo câmbio, " +
    "resultando na paridade de exportação; a diferença entre a paridade e o indicador do " +
    "porto é o basis do porto; a diferença entre o porto e a praça é o basis do interior."),
  P("É a resposta visual à pergunta “de onde veio o preço que eu recebo”. Se o preço caiu, " +
    "a cadeia mostra se a culpa foi de Chicago, do câmbio ou do basis — cada um exige uma " +
    "reação diferente."),
  H3("Cenário e sanity check"),
  P("O balanço mundial ao vivo, usado como teste de coerência para qualquer modelo " +
    "preditivo: com oferta ampla e estoque/uso confortável, o resultado esperado é viés " +
    "neutro a baixista com cauda de alta condicionada a clima e demanda chinesa. Um modelo " +
    "que devolva alta convicta nesse cenário está quebrado, e isso deve ser verificado " +
    "antes de olhar qualquer métrica de acurácia."),
];

const fontes = [
  H1("5. Fontes utilizadas"),
  P("Todas as fontes são gratuitas e de acesso público. A coluna de observação registra as " +
    "restrições reais encontradas em produção."),
  tabela(
    [{ t: "Dado", p: 0.27 }, { t: "Fonte", p: 0.27 }, { t: "Observação", p: 0.46 }],
    [
      ["Futuros CBOT, Brent, Ibovespa", "Yahoo Finance (não oficial)",
        "Atraso de ~15 min. É a fonte mais frágil do conjunto; se falhar, o painel mantém o último valor"],
      ["Curva de vencimentos com posições em aberto", "Yahoo Finance, endpoint /v7/finance/quote",
        "Exige cookie e crumb obtidos a cada execução. É o único caminho gratuito que devolve open interest por contrato"],
      ["Séries históricas de 1 dia a 5 anos", "Yahoo Finance, endpoint /v8/finance/chart",
        "Três granularidades por símbolo: 1 h em 5 dias, diária em 1 ano, semanal em 5 anos"],
      ["Volume de calls e puts", "CME Group, FTP público",
        "Arquivo daily_volume.xlsx, do pregão anterior. O site e a API da CME bloqueiam IPs de nuvem; o FTP é aberto"],
      ["Indicadores CEPEA, prêmio de porto e balcão", "Cepea/Esalq, via Notícias Agrícolas",
        "O site do CEPEA passou a exigir verificação da Cloudflare e responde 403 a acesso automatizado. O Notícias Agrícolas republica citando a fonte"],
      ["Oferta e demanda mundial", "USDA/FAS, API PSD",
        "Requer chave gratuita, guardada como secret do repositório. Atualiza a cada revisão do WASDE"],
      ["Andamento da safra nos EUA", "USDA/NASS Crop Progress, via biblioteca Cornell",
        "Publicação semanal, às segundas-feiras. Sem necessidade de chave"],
      ["Safra brasileira", "CONAB, série histórica de grãos",
        "Arquivo público atualizado nos levantamentos mensais"],
      ["Dólar e euro comerciais", "AwesomeAPI, com alternativa no Yahoo",
        "A AwesomeAPI limita os IPs do GitHub Actions; há troca automática de fonte quando isso ocorre"],
      ["PTAX, Selic, CDI, IPCA", "Banco Central do Brasil (Olinda e SGS)",
        "Fontes oficiais, as mais estáveis do conjunto"],
      ["Chuva e temperatura", "Open-Meteo",
        "Sem chave. Previsão de 7 dias e histórico de 31 dias"],
      ["Notícias", "Google News, Canal Rural, G1 Agronegócios",
        "Leitura de RSS com remoção de duplicatas por título"],
    ]),
  ESPACO(),
  H2("Nota sobre atribuição"),
  P("Os indicadores de preço físico são produzidos pelo CEPEA/ESALQ e obtidos por meio do " +
    "Notícias Agrícolas, que os republica citando a fonte. A atribuição aparece no rodapé " +
    "das duas páginas. Qualquer uso além do informativo deve observar as condições de " +
    "licenciamento de cada produtor de dados — ver seção 10."),
];

const atualizacao = [
  H1("6. Mecanismo de atualização"),
  H2("Fluxo"),
  LIB("Gatilho", "o GitHub Actions dispara o processo de hora em hora, por agendamento cron, " +
    "e também sob comando manual."),
  LIB("Coleta", "um script Python percorre as onze fontes de forma independente e monta a " +
    "estrutura de dados."),
  LIB("Derivação", "com todas as seções coletadas, calcula-se o basis, que depende de " +
    "câmbio, Chicago e mercado físico simultaneamente."),
  LIB("Gravação", "o resultado é escrito em data/data.json e a observação diária do basis é " +
    "acrescentada a data/basis_history.json."),
  LIB("Publicação", "o próprio robô faz commit dos arquivos e o GitHub Pages serve a versão " +
    "nova em segundos."),
  LIB("Leitura", "as páginas buscam o JSON ao abrir e o recarregam a cada dez minutos com a " +
    "aba aberta."),
  H2("Tolerância a falhas"),
  P("Se uma fonte falha, a seção herda o valor da execução anterior e o erro é registrado " +
    "numa lista dentro do próprio arquivo de dados. O painel exibe um aviso discreto no " +
    "rodapé informando quais fontes estavam indisponíveis na última atualização. O processo " +
    "só é considerado com falha se absolutamente todas as fontes falharem."),
  H2("Latência real"),
  tabela(
    [{ t: "Dado", p: 0.4 }, { t: "Defasagem típica", p: 0.6 }],
    [
      ["Cotações de Chicago", "15 minutos da bolsa, mais até 1 hora do ciclo de atualização"],
      ["Câmbio", "Quase tempo real, mais o ciclo de atualização"],
      ["Indicador CEPEA", "Um dia útil (o indicador do dia sai no fim da tarde)"],
      ["Volume de opções", "Um pregão"],
      ["Crop Progress", "Semanal, divulgado às segundas"],
      ["Oferta e demanda", "Mensal, a cada WASDE"],
      ["Safra CONAB", "Mensal, a cada levantamento"],
    ]),
  ESPACO(),
  P("O agendamento do GitHub pode atrasar alguns minutos em horários de pico, e em raras " +
    "ocasiões a plataforma não aloca máquina e a execução é cancelada — nesses casos a " +
    "execução seguinte normaliza o quadro."),
];

const arquitetura = [
  H1("7. Arquitetura e linguagens"),
  H2("Visão geral"),
  P("A arquitetura é deliberadamente simples: um processo de coleta que gera um arquivo, e " +
    "páginas estáticas que leem esse arquivo. Não há servidor de aplicação, banco de dados, " +
    "framework de front-end nem etapa de compilação. Isso mantém o custo em zero e reduz a " +
    "superfície de manutenção."),
  H2("Linguagens e tecnologias"),
  tabela(
    [{ t: "Camada", p: 0.24 }, { t: "Tecnologia", p: 0.3 }, { t: "Papel", p: 0.46 }],
    [
      ["Coleta", "Python 3.12", "Script único de ~1.280 linhas, um coletor por fonte"],
      ["Bibliotecas Python", "requests, openpyxl", "HTTP e leitura da planilha de volume da CME"],
      ["Biblioteca padrão", "ftplib, zipfile, csv, xml.etree, re", "FTP da CME, pacote do USDA, RSS e extração de tabelas"],
      ["Formato de dados", "JSON", "Contrato único entre coleta e apresentação (~93 KB)"],
      ["Estrutura das páginas", "HTML5", "Duas páginas independentes, sem dependências externas"],
      ["Apresentação", "CSS3", "Variáveis de tema, grid e flexbox; tema claro e escuro automáticos"],
      ["Interatividade", "JavaScript (ES2020), sem framework", "Renderização, modal de detalhe e fatiamento das séries"],
      ["Gráficos", "SVG gerado em JavaScript", "Linhas, áreas, barras e leitura ponto a ponto, sem biblioteca de terceiros"],
      ["Automação", "GitHub Actions (YAML)", "Agendamento, execução e commit automático"],
      ["Hospedagem", "GitHub Pages", "Servidor estático com HTTPS"],
      ["Versionamento", "Git", "Histórico completo; o próprio dado é versionado"],
    ]),
  ESPACO(),
  H2("Por que sem framework"),
  P("O volume de dados é pequeno e a interface é estável. React ou similar acrescentaria " +
    "etapa de compilação, dependências a atualizar e centenas de kilobytes de download, sem " +
    "benefício proporcional. A página inteira, com estilos e scripts, cabe em um arquivo " +
    "legível e carrega instantaneamente."),
  H2("Estrutura do repositório"),
  tabela(
    [{ t: "Caminho", p: 0.34 }, { t: "Conteúdo", p: 0.66 }],
    [
      ["index.html", "Painel principal: estilos, marcação e lógica de apresentação"],
      ["modelo.html", "Página de basis e especificação do modelo"],
      ["scripts/update_data.py", "Coletor de todas as fontes e cálculos derivados"],
      [".github/workflows/update-data.yml", "Agendamento e execução horária"],
      ["data/data.json", "Fotografia mais recente de todas as seções"],
      ["data/basis_history.json", "Série acumulada do basis, uma observação por dia"],
      ["README.md", "Documentação de operação e fontes"],
    ]),
  ESPACO(),
  H2("Segurança"),
  P("A única credencial do sistema é a chave da API do USDA, guardada como secret do " +
    "repositório e injetada como variável de ambiente na execução. Ela não aparece no " +
    "código, nos arquivos de dados nem nos registros de execução. O repositório é público; " +
    "nenhum outro dado sensível trafega pelo sistema."),
];

const limitacoes = [
  H1("9. Limitações conhecidas"),
  H2("9.1 Qualidade e defasagem dos dados"),
  LIB("Não é tempo real", "atraso de ao menos 15 minutos nas bolsas, somado ao ciclo de " +
    "atualização de até uma hora. Não serve para execução de ordens."),
  LIB("Yahoo Finance não é fonte oficial", "é a dependência mais frágil do sistema. Não há " +
    "contrato de disponibilidade e o formato pode mudar sem aviso."),
  LIB("Indicador CEPEA por intermediário", "o acesso direto foi bloqueado por verificação " +
    "anti-robô. A leitura é feita no Notícias Agrícolas, que republica citando a fonte — " +
    "se aquele site mudar de layout, a seção para de atualizar."),
  H2("9.2 Lacunas de cobertura"),
  LIB("Opções sem posições em aberto", "a CME não publica open interest de opções por " +
    "produto de forma gratuita. O painel mostra apenas volume; o open interest exibido é " +
    "o dos futuros."),
  LIB("Sem cadeia de opções por preço de exercício", "impede a densidade risco-neutra e " +
    "qualquer leitura direcional consistente do mercado de opções."),
  LIB("Sem percentual plantado no Brasil", "a CONAB publica em painel Power BI sem API " +
    "aberta, a AgRural divulga em comunicado de imprensa e o USDA não cobre progresso " +
    "semanal para o Brasil. O painel usa calendário e chuva acumulada como aproximação."),
  LIB("Sem derivativos da B3", "o boletim legado da BM&F foi desativado no servidor de " +
    "origem e não há API pública gratuita. A liquidez desses contratos também é muito baixa."),
  LIB("Série do basis começa agora", "não existe arquivo gratuito do indicador para " +
    "reconstruir o histórico. A série útil ao modelo se forma a partir de sua criação."),
  LIB("Um feed RSS indisponível", "o Notícias Agrícolas alterou o endereço do feed; as " +
    "outras três fontes de notícia cobrem a seção normalmente."),
  H2("9.3 Divergências metodológicas"),
  P("O estoque final do Brasil segundo o USDA não coincide com o da CONAB — as duas " +
    "instituições usam definições diferentes de estoque de passagem. O painel exibe as duas " +
    "e sinaliza a divergência em vez de escolher uma e apresentá-la como consenso."),
  P("A paridade de exportação é simplificada: não desconta frete rodoviário até o navio, " +
    "taxas portuárias nem custo de originação. O nível do basis absorve esses componentes. " +
    "Para o propósito de modelagem isso não é problema, porque o que se modela é a variação " +
    "do basis, não o seu nível absoluto."),
  H2("9.4 Limitações de infraestrutura"),
  LIB("Agendamento não garantido", "o cron do GitHub pode atrasar em horários de pico e, " +
    "ocasionalmente, não alocar máquina — a execução seguinte normaliza."),
  LIB("Sem alertas", "o painel é consultado ativamente; não há notificação por preço, " +
    "e-mail ou mensagem."),
  LIB("Sem autenticação", "a página é pública. Não há perfis, preferências salvas nem " +
    "trilha de auditoria."),
  LIB("Crescimento do histórico", "cada execução grava um arquivo de aproximadamente 93 KB. " +
    "O histórico do repositório cresce continuamente e pode exigir limpeza periódica."),
];

const comercial = [
  H1("10. Aplicação comercial"),
  H2("10.1 Usos diretos"),
  LIB("Apoio à decisão de venda", "o produtor compara o preço de balcão da sua praça com o " +
    "porto e com o histórico de doze meses antes de fechar lote."),
  LIB("Análise de margem de originação", "a decomposição em paridade e basis mostra onde " +
    "está a margem entre comprar no interior e embarcar, por praça e por mês de embarque."),
  LIB("Material de relacionamento", "consultores e cooperativas podem usar o painel em " +
    "reuniões com associados: quadro completo, atualizado e com fonte identificada."),
  LIB("Insumo para estruturação", "curva com posições em aberto e balanço de oferta e " +
    "demanda para dimensionar hedge; com a densidade risco-neutra implementada, passa a " +
    "servir para precificar collar, fence e acumulador."),
  H2("10.2 Restrições de licenciamento"),
  P("Este é o ponto crítico para qualquer uso comercial. O painel foi construído sobre " +
    "fontes gratuitas cujos termos permitem consulta, mas não necessariamente " +
    "redistribuição comercial:"),
  tabela(
    [{ t: "Fonte", p: 0.28 }, { t: "Situação para uso comercial", p: 0.72 }],
    [
      ["CEPEA/ESALQ", "Os indicadores são propriedade intelectual do CEPEA. A redistribuição comercial requer autorização e provavelmente contrato"],
      ["CME Group", "Dados de mercado têm licenciamento próprio. O uso de dados atrasados para fins internos costuma ser aceito; a redistribuição, não"],
      ["Yahoo Finance", "Não é fonte licenciável — é um endpoint não oficial. Inadequado como base de produto comercial"],
      ["USDA e Banco Central", "Dados públicos governamentais, sem restrição relevante de redistribuição"],
      ["CONAB", "Dados públicos, sem restrição relevante"],
      ["Open-Meteo", "Licença aberta; uso comercial permitido conforme os termos do serviço"],
      ["Notícias (RSS)", "Manchete e link são uso aceito; reprodução integral do texto, não"],
    ]),
  ESPACO(),
  PR([["Conclusão prática: "], "na forma atual o painel é adequado para uso interno e " +
    "informativo. Para virar produto comercial, as fontes de preço precisam ser " +
    "substituídas por feeds licenciados — o que também resolve, de uma vez, a fragilidade " +
    "técnica e a lacuna da cadeia de opções."]),
  H2("10.3 Caminhos de evolução comercial"),
  LIB("Camada de serviço para cooperativas", "painel personalizado por praça e por " +
    "cooperativa, com o preço de balcão da própria organização ao lado das referências " +
    "de mercado."),
  LIB("Relatório recorrente automatizado", "geração diária ou semanal de um documento com o " +
    "quadro do mercado, distribuído por e-mail a produtores associados."),
  LIB("Módulo de estruturação", "com feed de opções licenciado, a densidade risco-neutra " +
    "permite precificar e comparar estruturas de proteção para o cliente produtor."),
  LIB("Alertas por praça", "notificação quando o basis da praça atinge percentil histórico " +
    "favorável — o produto natural depois que a série do basis acumular histórico."),
  H2("10.4 Custo de operação"),
  P("Na configuração atual o custo é zero: GitHub Pages e Actions no plano gratuito atendem " +
    "com folga o volume necessário. Uma versão comercial teria como principais custos os " +
    "feeds de dados licenciados e, eventualmente, hospedagem própria caso passe a existir " +
    "autenticação ou personalização por usuário."),
];

const proximos = [
  H1("15. Próximos passos sugeridos"),
  P("Em ordem aproximada de relação entre benefício e esforço."),
  H2("Curto prazo"),
  LIB("Corrigir o feed de notícias do Notícias Agrícolas",
    "localizar o novo endereço do RSS e restaurar a quarta fonte da seção. Esforço baixo."),
  LIB("Estender o detalhe clicável a câmbio e juros",
    "a mecânica de séries e modal já existe; falta apenas coletar o histórico dessas " +
    "seções. Esforço baixo, ganho imediato de utilidade."),
  LIB("Comparação sobreposta entre ativos",
    "soja contra milho, ou soja contra dólar, normalizados em base 100, para leitura de " +
    "relação de troca. Esforço baixo."),
  H2("Médio prazo"),
  LIB("Feed de opções com preços de exercício",
    "é o desbloqueio de maior valor do projeto. Habilita a densidade risco-neutra e toda " +
    "a leitura direcional do mercado de opções. Requer Barchart, CME DataMine ou acesso " +
    "via corretora."),
  LIB("Alertas configuráveis",
    "notificação quando preço, basis ou prêmio cruzam um limite definido pelo usuário. " +
    "Exige um canal de envio e alguma forma de preferência por usuário."),
  LIB("Progresso de plantio no Brasil",
    "extração do boletim mensal da CONAB em PDF, ou assinatura de fonte privada como " +
    "AgRural ou Pátria Agronegócios."),
  LIB("Testes automatizados dos extratores",
    "os coletores que leem páginas HTML são frágeis por natureza. Testes sobre amostras " +
    "salvas detectariam mudanças de layout antes que a seção pare silenciosamente."),
  H2("Longo prazo"),
  LIB("Implementação do modelo de direção",
    "depende de acumular histórico de basis e de montar o conjunto de variáveis " +
    "explicativas semanais. A especificação e o protocolo de validação já estão definidos."),
  LIB("Modelagem separada do basis",
    "o basis é estacionário e sazonal, portanto mais previsível que o preço absoluto. " +
    "É a linha de pesquisa com maior chance de gerar resultado aplicável."),
  LIB("Banco de dados de série temporal",
    "substituir o histórico versionado em Git por armazenamento apropriado quando o " +
    "volume justificar."),
  LIB("Aplicativo instalável",
    "transformar o painel em aplicação web progressiva, com funcionamento offline e " +
    "ícone na tela inicial do celular."),
];

const glossario = [
  H1("16. Glossário"),
  tabela(
    [{ t: "Termo", p: 0.24 }, { t: "Significado", p: 0.76 }],
    [
      ["Basis", "Diferença entre o preço físico em um local e o preço do futuro de referência. Reúne frete, qualidade, prazo e condições locais de oferta e demanda"],
      ["Bushel", "Unidade de volume usada em Chicago. Para soja equivale a 27,2155 kg; uma saca de 60 kg tem 2,2046 bushels"],
      ["Contango", "Curva de futuros ascendente: vencimentos distantes valem mais que os próximos. Indica oferta confortável"],
      ["Backwardation", "Curva descendente: o disponível vale mais que o futuro. Indica aperto de oferta"],
      ["Carrego", "Custo de manter estoque — armazenagem, juros e seguro. O contango remunera esse custo"],
      ["Paridade de exportação", "Preço em reais por saca que Chicago e o câmbio explicam, antes do basis"],
      ["Prêmio de porto", "Quanto o mercado paga acima do futuro para embarque em um porto e mês específicos"],
      ["Posição em aberto", "Número de contratos ainda em vigor, não liquidados. Mede posicionamento, não giro"],
      ["Volume", "Número de contratos negociados no período. Mede atividade, não direção"],
      ["Call / Put", "Opção de compra / opção de venda"],
      ["Razão put/call", "Volume de puts dividido pelo de calls. Indicador de fluxo, não de direção"],
      ["Estoque/uso", "Estoque final dividido pelo consumo. Principal medida de folga de oferta"],
      ["WASDE", "Relatório mensal do USDA com as estimativas de oferta e demanda mundiais"],
      ["Crop Progress", "Levantamento semanal do USDA sobre estágio e condição das lavouras americanas"],
      ["Densidade risco-neutra", "Distribuição de probabilidade implícita nos preços das opções"],
      ["Walk-forward", "Validação que treina no passado e testa no futuro, avançando no tempo"],
      ["Purga e embargo", "Remoção de observações que causariam vazamento de informação entre treino e teste"],
      ["AUC", "Medida de qualidade de um classificador. 0,5 equivale a acerto aleatório"],
    ]),
  ESPACO(),
  REGRA(),
  P("Documento gerado a partir do estado do repositório em " +
    new Date().toLocaleDateString("pt-BR") + ". O painel evolui continuamente; o README do " +
    "repositório é a referência sempre atualizada sobre fontes e operação.",
    { size: 18, color: CINZA, italics: true }),
  P("Conteúdo informativo. Não constitui recomendação de negociação.",
    { size: 18, color: CINZA, italics: true }),
];

const NOV = novas({ P, PR, H1, H2, H3, LI, LIB, tabela, ESPACO, FORMULA, COD });

/* ---------------------------------------------------------------- documento */

const doc = new Document({
  creator: "Painel Soja",
  title: "Painel Soja — Documentação técnica e guia de uso",
  description: "Documentação do painel de mercado da soja",
  numbering: {
    config: [{
      reference: "balas",
      levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 360, hanging: 220 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 220 } } } },
      ],
    }],
  },
  styles: {
    default: {
      document: { run: { font: "Calibri", size: 21, color: TINTA } },
    },
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    children: [
      ...capa, ...sumario, ...visao, ...publico, ...uso, ...interpretacao,
      ...fontes, ...atualizacao, ...arquitetura, ...NOV.algoritmos,
      ...limitacoes, ...comercial, ...NOV.estrategias, ...NOV.graficos,
      ...NOV.fontesNovas, ...NOV.casosUso, ...proximos, ...glossario,
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(process.argv[2] || "Painel-Soja-Documentacao.docx", buf);
  console.log("gerado:", process.argv[2]);
});
