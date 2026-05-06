// Metas — financeiras + operacionais
const METAS_FINANCEIRAS = [
  { id:'reserva',    nome:'Reserva de emergência',     tipo:'reserva',  alvo:60000,  atual:42800, mensalidade:2500, deadline:'2026-12-31', cor:'var(--accent-cyan)',   nota:'6 meses de despesa' },
  { id:'aposenta',   nome:'Aposentadoria · 2055',      tipo:'longo',    alvo:1800000, atual:215400, mensalidade:3200, deadline:'2055-01-01', cor:'var(--accent-purple)', nota:'projeção real, IPCA + 4%' },
  { id:'viagem',     nome:'Japão · outubro/2026',      tipo:'curto',    alvo:18000,  atual:12450, mensalidade:1100, deadline:'2026-10-15', cor:'var(--accent-pink)',   nota:'2 pessoas · 14 dias' },
  { id:'imovel',     nome:'Entrada apartamento',       tipo:'longo',    alvo:120000, atual:38900, mensalidade:1800, deadline:'2028-06-30', cor:'var(--accent-orange)', nota:'~20% sobre 600k' },
  { id:'mestrado',   nome:'Mestrado · UFSC',           tipo:'curto',    alvo:8400,   atual:8400,  mensalidade:0,    deadline:'2026-03-01', cor:'var(--d7-graduado)',   nota:'ATINGIDA · 02/2026', concluida:true },
];

const METAS_OPERACIONAIS = [
  { id:'cob_pipeline', nome:'Cobertura D7 média ≥ 80%',   atual:0.69, alvo:0.80, formato:'pct', cor:'var(--accent-purple)', nota:'14 skills · cobertura observável', sparkline:[0.51,0.56,0.60,0.64,0.66,0.69,0.71,0.69] },
  { id:'paridade',     nome:'Paridade ETL × Opus ≥ 90%', atual:0.76, alvo:0.90, formato:'pct', cor:'var(--accent-pink)',   nota:'sprint VALIDAÇÃO-CSV-01',          sparkline:[0.62,0.65,0.68,0.71,0.73,0.74,0.76,0.76] },
  { id:'completude',   nome:'Completude por tipo ≥ 95%',  atual:0.88, alvo:0.95, formato:'pct', cor:'var(--accent-cyan)',   nota:'439 arquivos · 7 tipos',           sparkline:[0.79,0.81,0.83,0.85,0.86,0.87,0.88,0.88] },
  { id:'inbox_zero',   nome:'Inbox-zero diário',          atual:23,   alvo:0,    formato:'inv', cor:'var(--accent-yellow)', nota:'arquivos parados há > 24h',        sparkline:[8,12,15,17,19,21,22,23] },
  { id:'testes',       nome:'Suite verde · 2.066 testes', atual:1,    alvo:1,    formato:'bin', cor:'var(--d7-graduado)',  nota:'CI passou em todos os PRs (28d)', sparkline:[1,1,1,0,1,1,1,1], concluida:true },
];

// Aporte mensal histórico (12 meses)
const METAS_APORTE_12M = [
  { mes:'mai/25', total:7200 }, { mes:'jun/25', total:7400 }, { mes:'jul/25', total:7100 },
  { mes:'ago/25', total:8900 }, { mes:'set/25', total:7200 }, { mes:'out/25', total:7800 },
  { mes:'nov/25', total:9100 }, { mes:'dez/25', total:11400 }, { mes:'jan/26', total:7600 },
  { mes:'fev/26', total:7700 }, { mes:'mar/26', total:8200 }, { mes:'abr/26', total:8600 },
];

const METAS_LOG = [
  { ts:'2026-04-30', tipo:'aporte', meta:'reserva',    valor:'R$ 2.500',  detalhe:'depósito mensal automático' },
  { ts:'2026-04-30', tipo:'aporte', meta:'aposenta',   valor:'R$ 3.200',  detalhe:'IVVB11 · 12 cotas' },
  { ts:'2026-04-25', tipo:'aporte', meta:'viagem',     valor:'R$ 1.100',  detalhe:'CDB Inter 110% CDI' },
  { ts:'2026-04-20', tipo:'milestone', meta:'cob_pipeline', valor:'+2pp', detalhe:'fatura_servico graduou parcialmente' },
  { ts:'2026-04-12', tipo:'milestone', meta:'paridade', valor:'76%',      detalhe:'fatura_cartao GRADUOU' },
  { ts:'2026-03-01', tipo:'concluida', meta:'mestrado', valor:'R$ 8.400', detalhe:'matrícula paga · meta atingida' },
];
