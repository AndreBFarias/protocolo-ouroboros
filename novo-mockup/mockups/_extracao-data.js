// Dados sintéticos para Extração Tripla (substitui _validacao-data.js).
// Vários arquivos de tipos diferentes (PDF, CSV, imagem, XLSX, OFX, HTML).
// Cada arquivo tem 3 extrações: ETL determinística, Claude Opus agentic, User.
// User começa pré-preenchido com o CONSENSO (campos onde ETL == Opus).
// Onde diverge, fica vazio e flagueado para o humano resolver.

const EXTRACAO_TIPOS_LABEL = {
  pdf:   { rotulo: 'PDF',   icon: 'docs',     cor: 'var(--accent-red)'    },
  csv:   { rotulo: 'CSV',   icon: 'table',    cor: 'var(--accent-green)'  },
  xlsx:  { rotulo: 'XLSX',  icon: 'table',    cor: 'var(--accent-green)'  },
  imagem:{ rotulo: 'IMG',   icon: 'eye',      cor: 'var(--accent-pink)'   },
  ofx:   { rotulo: 'OFX',   icon: 'financas', cor: 'var(--accent-cyan)'   },
  html:  { rotulo: 'HTML',  icon: 'docs',     cor: 'var(--accent-orange)' },
};

// === ARQUIVOS ===
// Cada arquivo: { id, sha8, filename, tipo_arquivo, formato, data_processado, bytes, paginas, fonte_etl }
// formato é o que aparece no badge da lista (pdf/csv/imagem/xlsx/ofx/html).
// tipo_arquivo é a categoria semântica (extrato_cc, fatura_cartao, etc).

const EXTRACAO_ARQUIVOS = [
  {
    id: 'A1', sha8: 'a3f9c1e2',
    filename: 'extrato_nubank_cc_2026-03.pdf',
    tipo_arquivo: 'extrato_cc',
    formato: 'pdf',
    data_processado: '2026-03-31 14:32',
    bytes: 184_320,
    paginas: 4,
    fonte_etl: 'nubank_cc v2.1.0',
    status_humano: 'pendente',
  },
  {
    id: 'A2', sha8: 'b7d2a04f',
    filename: 'fatura_c6_cartao_2026-03.pdf',
    tipo_arquivo: 'fatura_cartao',
    formato: 'pdf',
    data_processado: '2026-03-31 14:35',
    bytes: 92_416,
    paginas: 6,
    fonte_etl: 'c6_cartao v1.8.2',
    status_humano: 'em_revisao',
  },
  {
    id: 'A3', sha8: 'c1e8b302',
    filename: 'recibo_farmacia_drogasil.jpg',
    tipo_arquivo: 'recibo_medico',
    formato: 'imagem',
    data_processado: '2026-03-30 09:14',
    bytes: 412_800,
    paginas: 1,
    fonte_etl: 'ocr_tesseract v5.3',
    status_humano: 'pendente',
  },
  {
    id: 'A4', sha8: 'b2e6f48d',
    filename: 'energia_neoenergia_marco.pdf',
    tipo_arquivo: 'fatura_concessionaria',
    formato: 'pdf',
    data_processado: '2026-03-12 18:01',
    bytes: 156_700,
    paginas: 2,
    fonte_etl: 'concessionaria_energia v1.4.0',
    status_humano: 'aprovado',
  },
  {
    id: 'A5', sha8: 'e1f8c360',
    filename: 'fatura_santander_cartao.xlsx',
    tipo_arquivo: 'fatura_cartao',
    formato: 'xlsx',
    data_processado: '2026-03-25 11:22',
    bytes: 28_900,
    paginas: 1,
    fonte_etl: 'xlsx_genérico v0.9',
    status_humano: 'pendente',
  },
  {
    id: 'A6', sha8: 'a8c4d91e',
    filename: 'cupom_padaria_termico.png',
    tipo_arquivo: 'cupom_fiscal',
    formato: 'imagem',
    data_processado: '2026-03-12 19:45',
    bytes: 89_200,
    paginas: 1,
    fonte_etl: 'ocr_tesseract v5.3',
    status_humano: 'pendente',
  },
  {
    id: 'A7', sha8: 'f1d92a30',
    filename: 'extrato_itau_2026-03.ofx',
    tipo_arquivo: 'extrato_cc',
    formato: 'ofx',
    data_processado: '2026-03-31 14:30',
    bytes: 12_400,
    paginas: null,
    fonte_etl: 'ofx_parser v3.1',
    status_humano: 'aprovado',
  },
  {
    id: 'A8', sha8: 'd4b6f192',
    filename: 'nota_consulta_cardio.pdf',
    tipo_arquivo: 'nota_servico',
    formato: 'pdf',
    data_processado: '2026-03-20 16:08',
    bytes: 220_500,
    paginas: 1,
    fonte_etl: 'nfse_genérico v1.2',
    status_humano: 'pendente',
  },
  {
    id: 'A9', sha8: '4c8b1e07',
    filename: 'transacoes_xp_2026-03.csv',
    tipo_arquivo: 'extrato_corretora',
    formato: 'csv',
    data_processado: '2026-03-31 14:28',
    bytes: 8_240,
    paginas: null,
    fonte_etl: 'csv_xp_invest v1.0',
    status_humano: 'pendente',
  },
  {
    id: 'A10', sha8: '7a3e9b45',
    filename: 'extrato_caixa_internetbanking.html',
    tipo_arquivo: 'extrato_cc',
    formato: 'html',
    data_processado: '2026-03-31 14:33',
    bytes: 64_800,
    paginas: null,
    fonte_etl: 'html_caixa v0.7',
    status_humano: 'em_revisao',
  },
];

// === EXTRAÇÕES ===
// Para cada arquivo, ETL extraiu N campos, Opus extraiu N campos.
// User é DERIVADO: campo onde ETL == Opus → preenchido com esse valor (status: consenso_auto).
//                  campo onde ETL != Opus → vazio (status: divergente, aguarda humano).
//                  campo só em ETL → vazio com hint (status: apenas_etl)
//                  campo só em Opus → vazio com hint (status: apenas_opus)
//
// Estrutura: { campo, etl, opus, conf_opus, fonte_pagina }

const EXTRACAO_DADOS = {
  A1: {
    campos: [
      { campo: 'banco',           etl: 'Nubank',        opus: 'Nubank',        conf: 0.99 },
      { campo: 'titular',         etl: 'XXXXX XXXXX',   opus: 'XXXXX XXXXX',   conf: 0.97 },
      { campo: 'agencia',         etl: '0001',          opus: '0001',          conf: 0.99 },
      { campo: 'conta',           etl: 'XXXXXXXX-X',    opus: 'XXXXXXXX-X',    conf: 0.99 },
      { campo: 'periodo_inicio',  etl: '2026-03-01',    opus: '2026-03-01',    conf: 1.00 },
      { campo: 'periodo_fim',     etl: '2026-03-31',    opus: '2026-03-31',    conf: 1.00 },
      { campo: 'saldo_inicial',   etl: 'R$ 3.218,40',   opus: 'R$ 3.218,40',   conf: 0.98 },
      { campo: 'saldo_final',     etl: 'R$ 4.102,15',   opus: 'R$ 4.102,15',   conf: 0.98 },
      { campo: 'creditos_total',  etl: 'R$ 5.840,00',   opus: 'R$ 5.840,00',   conf: 0.96 },
      { campo: 'debitos_total',   etl: 'R$ 4.956,25',   opus: 'R$ 4.956,25',   conf: 0.96 },
      { campo: 'lancamentos_qtd', etl: 47,              opus: 47,              conf: 1.00 },
    ],
  },
  A2: {
    campos: [
      { campo: 'banco',           etl: 'C6 Bank',                 opus: 'C6 Bank',                 conf: 0.99 },
      { campo: 'bandeira',        etl: 'Mastercard',              opus: 'Mastercard',              conf: 0.98 },
      { campo: 'ultimos_4',       etl: '••42',                    opus: '••42',                    conf: 1.00 },
      { campo: 'data_emissao',    etl: '2026-03-22',              opus: '2026-03-22',              conf: 1.00 },
      { campo: 'data_vencimento', etl: '2026-04-08',              opus: '2026-04-08',              conf: 1.00 },
      { campo: 'total_fatura',    etl: 'R$ 2.847,90',             opus: 'R$ 2.874,90',             conf: 0.71, obs: 'OCR confundiu "47" com "74" na 4a posição' },
      { campo: 'pagamento_minimo',etl: 'R$ 569,58',               opus: 'R$ 574,98',               conf: 0.68, obs: 'mesmo dígito ambíguo do total' },
      { campo: 'lancamentos_qtd', etl: 18,                        opus: 18,                        conf: 1.00 },
      { campo: 'parcelamento',    etl: 'sem juros — 3x R$ 124,30',opus: 'sem juros — 3x R$ 124,30',conf: 0.95 },
      { campo: 'limite_total',    etl: 'R$ 8.500,00',             opus: 'R$ 8.500,00',             conf: 0.99 },
    ],
  },
  A3: {
    campos: [
      { campo: 'fornecedor',      etl: 'DROGASIL S.A.',           opus: 'Drogasil',                 conf: 0.62, obs: 'razão social vs. nome fantasia' },
      { campo: 'cnpj',            etl: 'XX.XXX.XXX/XXXX-XX',      opus: 'XX.XXX.XXX/XXXX-XX',       conf: 0.93 },
      { campo: 'data_compra',     etl: '2026-03-18',              opus: '2026-03-18',               conf: 0.95 },
      { campo: 'valor_total',     etl: 'R$ 87,40',                opus: 'R$ 87,40',                 conf: 0.93 },
      { campo: 'forma_pagamento', etl: 'CARTÃO CRÉDITO',          opus: 'cartão de crédito',        conf: 0.81, obs: 'caixa-alta vs sentence-case' },
      { campo: 'itens_qtd',       etl: 3,                         opus: 3,                          conf: 0.88 },
      { campo: 'medicamento',     etl: '',                        opus: 'Dipirona 500mg + Loratadina', conf: 0.55, obs: 'ETL não extrai itens; Opus inferiu da imagem' },
    ],
  },
  A4: {
    campos: [
      { campo: 'concessionaria',  etl: 'Neoenergia Coelba',       opus: 'Neoenergia Coelba',        conf: 0.99 },
      { campo: 'cliente',         etl: 'XXXXX XXXXX',             opus: 'XXXXX XXXXX',              conf: 0.96 },
      { campo: 'instalacao',      etl: 'XXXXXXXXX',               opus: 'XXXXXXXXX',                conf: 0.99 },
      { campo: 'mes_referencia',  etl: '2026-03',                 opus: '2026-03',                  conf: 1.00 },
      { campo: 'data_vencimento', etl: '2026-04-10',              opus: '2026-04-10',               conf: 1.00 },
      { campo: 'kwh_consumido',   etl: '318',                     opus: '318',                      conf: 1.00 },
      { campo: 'valor_total',     etl: 'R$ 287,15',               opus: 'R$ 287,15',                conf: 0.99 },
      { campo: 'leitura_anterior',etl: '2026-02-09',              opus: '2026-02-09',               conf: 0.97 },
      { campo: 'leitura_atual',   etl: '2026-03-09',              opus: '2026-03-09',               conf: 0.97 },
    ],
  },
  A5: {
    campos: [
      { campo: 'banco',           etl: 'Santander',               opus: 'Santander',                conf: 0.98 },
      { campo: 'bandeira',        etl: 'Visa',                    opus: 'Visa',                     conf: 0.97 },
      { campo: 'data_vencimento', etl: '2026-04-12',              opus: '2026-04-12',               conf: 1.00 },
      { campo: 'total_fatura',    etl: 'R$ 1.230,00',             opus: 'R$ 1.250,00',              conf: 0.55, obs: 'XLSX usou ponto como milhar; ETL leu como decimal' },
      { campo: 'lancamentos_qtd', etl: 11,                        opus: 11,                         conf: 1.00 },
      { campo: 'mes_referencia',  etl: '',                        opus: '2026-03',                  conf: 0.78, obs: 'campo não está numa célula nomeada — Opus inferiu do contexto' },
    ],
  },
  A6: {
    campos: [
      { campo: 'fornecedor',      etl: '',                        opus: 'Padaria São José',         conf: 0.45, obs: 'papel térmico desbotado; ETL falhou' },
      { campo: 'data_compra',     etl: '2026-03-12',              opus: '2026-03-12',               conf: 0.82 },
      { campo: 'valor_total',     etl: '',                        opus: 'R$ 23,80',                 conf: 0.40 },
      { campo: 'forma_pagamento', etl: '',                        opus: 'PIX',                      conf: 0.51 },
      { campo: 'itens_qtd',       etl: '',                        opus: 4,                          conf: 0.38 },
    ],
  },
  A7: {
    campos: [
      { campo: 'banco',           etl: 'Itaú',                    opus: 'Itaú Unibanco',            conf: 0.92, obs: 'OFX traz "Itaú", Opus normalizou para razão social' },
      { campo: 'agencia',         etl: 'XXXX',                    opus: 'XXXX',                     conf: 1.00 },
      { campo: 'conta',           etl: 'XXXXX-X',                 opus: 'XXXXX-X',                  conf: 1.00 },
      { campo: 'periodo_inicio',  etl: '2026-03-01',              opus: '2026-03-01',               conf: 1.00 },
      { campo: 'periodo_fim',     etl: '2026-03-31',              opus: '2026-03-31',               conf: 1.00 },
      { campo: 'saldo_final',     etl: 'R$ 8.421,70',             opus: 'R$ 8.421,70',              conf: 1.00 },
      { campo: 'lancamentos_qtd', etl: 62,                        opus: 62,                         conf: 1.00 },
      { campo: 'moeda',           etl: 'BRL',                     opus: 'BRL',                      conf: 1.00 },
    ],
  },
  A8: {
    campos: [
      { campo: 'prestador',       etl: 'Clínica Cardio Centro',   opus: 'Clínica Cardio Centro Ltda', conf: 0.85, obs: 'Ltda vs sem sufixo' },
      { campo: 'cnpj_prestador',  etl: 'XX.XXX.XXX/XXXX-XX',      opus: 'XX.XXX.XXX/XXXX-XX',       conf: 0.96 },
      { campo: 'tomador',         etl: 'XXXXX XXXXX',             opus: 'XXXXX XXXXX',              conf: 0.97 },
      { campo: 'cpf_tomador',     etl: 'XXX.XXX.XXX-XX',          opus: 'XXX.XXX.XXX-XX',           conf: 0.98 },
      { campo: 'numero_nota',     etl: 'NFS-e 0004271',           opus: 'NFS-e 0004271',            conf: 0.99 },
      { campo: 'data_emissao',    etl: '2026-03-20',              opus: '2026-03-20',               conf: 1.00 },
      { campo: 'descricao',       etl: 'Consulta cardiológica',   opus: 'Consulta cardiológica',    conf: 0.96 },
      { campo: 'valor_servico',   etl: 'R$ 450,00',               opus: 'R$ 450,00',                conf: 1.00 },
      { campo: 'iss_retido',      etl: 'R$ 0,00',                 opus: 'R$ 0,00',                  conf: 0.99 },
      { campo: 'codigo_servico',  etl: '',                        opus: '08.01.01',                 conf: 0.61, obs: 'item da LC 116 — Opus inferiu da descrição' },
    ],
  },
  A9: {
    campos: [
      { campo: 'corretora',       etl: 'XP Investimentos',        opus: 'XP Investimentos',         conf: 0.99 },
      { campo: 'periodo',         etl: '2026-03',                 opus: '2026-03',                  conf: 1.00 },
      { campo: 'operacoes_qtd',   etl: 23,                        opus: 23,                         conf: 1.00 },
      { campo: 'compras_total',   etl: 'R$ 12.480,00',            opus: 'R$ 12.480,00',             conf: 1.00 },
      { campo: 'vendas_total',    etl: 'R$ 8.250,00',             opus: 'R$ 8.250,00',              conf: 1.00 },
      { campo: 'taxas_total',     etl: 'R$ 18,40',                opus: 'R$ 18,40',                 conf: 0.99 },
      { campo: 'irrf_retido',     etl: 'R$ 12,38',                opus: 'R$ 12,38',                 conf: 0.99 },
      { campo: 'lucro_prejuizo',  etl: '',                        opus: '+ R$ 340,15',              conf: 0.72, obs: 'CSV não traz P&L; Opus calculou de operações' },
    ],
  },
  A10: {
    campos: [
      { campo: 'banco',           etl: 'Caixa',                   opus: 'Caixa Econômica Federal',  conf: 0.94, obs: 'HTML traz "Caixa", razão social completa só no rodapé' },
      { campo: 'agencia',         etl: 'XXXX',                    opus: 'XXXX',                     conf: 0.99 },
      { campo: 'conta',           etl: 'XXX XXXXX-X',             opus: 'XXX XXXXX-X',              conf: 0.99 },
      { campo: 'operacao',        etl: '013',                     opus: '013',                      conf: 1.00 },
      { campo: 'periodo_inicio',  etl: '2026-03-01',              opus: '2026-03-01',               conf: 1.00 },
      { campo: 'periodo_fim',     etl: '2026-03-31',              opus: '2026-03-31',               conf: 1.00 },
      { campo: 'saldo_final',     etl: 'R$ 1.842,30',             opus: 'R$ 1.842,30',              conf: 0.97 },
      { campo: 'lancamentos_qtd', etl: 28,                        opus: 29,                         conf: 0.74, obs: 'HTML pulou linha de tarifa em fonte cinza-claro' },
      { campo: 'tarifas_total',   etl: 'R$ 12,90',                opus: 'R$ 19,80',                 conf: 0.66, obs: 'consequência da linha pulada' },
    ],
  },
};

// === STATUS por campo ===
// derivado de etl/opus: ok | divergente | apenas_etl | apenas_opus | apenas_humano
function statusCampo(c) {
  const eVazio = (v) => v === '' || v === null || v === undefined;
  const etlVazio = eVazio(c.etl);
  const opusVazio = eVazio(c.opus);
  if (etlVazio && opusVazio) return 'apenas_humano';
  if (etlVazio) return 'apenas_opus';
  if (opusVazio) return 'apenas_etl';
  return String(c.etl) === String(c.opus) ? 'ok' : 'divergente';
}

// === CONSENSO inicial para tabela User ===
// se ok → preenche com valor
// caso contrário → vazio (humano resolve)
function valorConsenso(c) {
  return statusCampo(c) === 'ok' ? c.etl : '';
}

// === Estatísticas por arquivo (paridade) ===
function estatisticasArquivo(arqId) {
  const dados = EXTRACAO_DADOS[arqId];
  if (!dados) return { total: 0, ok: 0, divergente: 0, apenas: 0, paridade: 0 };
  const total = dados.campos.length;
  let ok = 0, divergente = 0, apenas = 0;
  for (const c of dados.campos) {
    const s = statusCampo(c);
    if (s === 'ok') ok++;
    else if (s === 'divergente') divergente++;
    else apenas++;
  }
  return { total, ok, divergente, apenas, paridade: total ? ok / total : 0 };
}

// === Agrupamento por formato ===
function arquivosPorFormato() {
  const grupos = {};
  for (const a of EXTRACAO_ARQUIVOS) {
    if (!grupos[a.formato]) grupos[a.formato] = [];
    grupos[a.formato].push(a);
  }
  return grupos;
}

// === Helper: bytes humano ===
function bytesHumano(b) {
  if (b == null) return '—';
  if (b < 1024) return b + ' B';
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB';
  return (b / 1024 / 1024).toFixed(2) + ' MB';
}

// === Default selecionado ===
const EXTRACAO_DEFAULT = 'A2'; // fatura_c6_cartao — tem divergência clara
