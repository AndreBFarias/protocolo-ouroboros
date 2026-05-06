// Skills D7 — dataset
// Cobertura observável: skills graduam por consistência, não bloqueiam pipeline.
// Estados: graduado (≥90% por 7 dias), calibracao (50-89%), regredindo (caiu >10pp), pendente (<50%, novo)

const SKILLS_D7 = [
  { id:'fatura_cartao', nome:'fatura_cartao', escopo:'documento', d7:'graduado',   cobertura:0.96, runs7d:142, sucesso7d:0.97, sparkD7:[0.78,0.82,0.85,0.88,0.91,0.94,0.96], graduadoEm:'2026-04-12', proximaCalibracao:null, owner:'opus', divergencias7d:4 },
  { id:'extrato_cc',     nome:'extrato_cc',     escopo:'documento', d7:'graduado',   cobertura:0.94, runs7d:98,  sucesso7d:0.95, sparkD7:[0.80,0.83,0.86,0.89,0.91,0.93,0.94], graduadoEm:'2026-04-08', proximaCalibracao:null, owner:'opus', divergencias7d:6 },
  { id:'comprovante_pix', nome:'comprovante_pix', escopo:'transacao', d7:'graduado', cobertura:0.92, runs7d:67,  sucesso7d:0.93, sparkD7:[0.85,0.86,0.88,0.90,0.91,0.92,0.92], graduadoEm:'2026-04-19', proximaCalibracao:null, owner:'etl', divergencias7d:2 },
  { id:'boleto_pdf',     nome:'boleto_pdf',     escopo:'documento', d7:'calibracao', cobertura:0.78, runs7d:54,  sucesso7d:0.81, sparkD7:[0.62,0.66,0.71,0.74,0.76,0.77,0.78], graduadoEm:null, proximaCalibracao:'2026-05-04', owner:'opus', divergencias7d:11 },
  { id:'nota_fiscal',    nome:'nota_fiscal',    escopo:'documento', d7:'calibracao', cobertura:0.71, runs7d:39,  sucesso7d:0.74, sparkD7:[0.55,0.58,0.62,0.65,0.68,0.70,0.71], graduadoEm:null, proximaCalibracao:'2026-05-06', owner:'opus', divergencias7d:9 },
  { id:'extrato_invest', nome:'extrato_invest', escopo:'documento', d7:'calibracao', cobertura:0.68, runs7d:21,  sucesso7d:0.72, sparkD7:[0.50,0.55,0.58,0.62,0.64,0.66,0.68], graduadoEm:null, proximaCalibracao:'2026-05-08', owner:'opus', divergencias7d:6 },
  { id:'recibo_medico',  nome:'recibo_medico',  escopo:'documento', d7:'regredindo', cobertura:0.41, runs7d:18,  sucesso7d:0.44, sparkD7:[0.72,0.68,0.61,0.55,0.49,0.44,0.41], graduadoEm:'2026-03-15', proximaCalibracao:'2026-05-02', owner:'opus', divergencias7d:14, regrediuEm:'2026-04-24', motivoRegressao:'Layouts novos da Hapvida não cobertos por hint' },
  { id:'cupom_fiscal',   nome:'cupom_fiscal',   escopo:'transacao', d7:'regredindo', cobertura:0.52, runs7d:31,  sucesso7d:0.55, sparkD7:[0.74,0.71,0.66,0.61,0.57,0.54,0.52], graduadoEm:'2026-02-28', proximaCalibracao:'2026-05-03', owner:'etl', divergencias7d:18, regrediuEm:'2026-04-22', motivoRegressao:'OCR ruim em cupons térmicos desbotados' },
  { id:'irpf_dirf',      nome:'irpf_dirf',      escopo:'transacao', d7:'pendente', cobertura:0.18, runs7d:4,   sucesso7d:0.25, sparkD7:[0.10,0.12,0.14,0.15,0.16,0.17,0.18], graduadoEm:null, proximaCalibracao:'2026-05-12', owner:'opus', divergencias7d:3 },
  { id:'darf_pdf',       nome:'darf_pdf',       escopo:'documento', d7:'pendente', cobertura:0.22, runs7d:7,   sucesso7d:0.29, sparkD7:[0.15,0.16,0.18,0.19,0.20,0.21,0.22], graduadoEm:null, proximaCalibracao:'2026-05-10', owner:'opus', divergencias7d:5 },
  { id:'contracheque',   nome:'contracheque',   escopo:'documento', d7:'graduado', cobertura:0.91, runs7d:14,  sucesso7d:0.93, sparkD7:[0.82,0.84,0.86,0.88,0.89,0.90,0.91], graduadoEm:'2026-04-26', proximaCalibracao:null, owner:'etl', divergencias7d:1 },
  { id:'fatura_servico', nome:'fatura_servico', escopo:'documento', d7:'calibracao', cobertura:0.83, runs7d:47, sucesso7d:0.85, sparkD7:[0.70,0.74,0.77,0.79,0.81,0.82,0.83], graduadoEm:null, proximaCalibracao:'2026-05-07', owner:'opus', divergencias7d:7 },
  { id:'transferencia',  nome:'transferencia',  escopo:'transacao', d7:'graduado', cobertura:0.97, runs7d:203, sucesso7d:0.98, sparkD7:[0.93,0.94,0.95,0.96,0.96,0.97,0.97], graduadoEm:'2026-03-20', proximaCalibracao:null, owner:'etl', divergencias7d:5 },
  { id:'rendimento_app', nome:'rendimento_app', escopo:'transacao', d7:'pendente', cobertura:0.34, runs7d:9,   sucesso7d:0.40, sparkD7:[0.20,0.22,0.25,0.28,0.30,0.32,0.34], graduadoEm:null, proximaCalibracao:'2026-05-09', owner:'opus', divergencias7d:4 },
];

// Eventos — graduação, regressão, calibração, run-batch
const SKILLS_EVENTOS = [
  { ts:'2026-05-01 14:32', tipo:'run', skill:'fatura_cartao', detalhe:'12 docs · 100% sucesso · paridade 96%' },
  { ts:'2026-05-01 13:18', tipo:'run', skill:'extrato_cc', detalhe:'8 docs · 7 sucesso · 1 divergência total_periodo' },
  { ts:'2026-05-01 11:42', tipo:'regressao', skill:'recibo_medico', detalhe:'D7 cruzou 50% · entra em calibração obrigatória' },
  { ts:'2026-04-30 18:00', tipo:'calibracao', skill:'boleto_pdf', detalhe:'Hint adicionado: layouts boletos Itaú PJ' },
  { ts:'2026-04-30 16:24', tipo:'graduacao', skill:'contracheque', detalhe:'7 dias ≥ 90% · GRADUADO' },
  { ts:'2026-04-30 14:11', tipo:'run', skill:'cupom_fiscal', detalhe:'4 docs · 2 sucesso · 2 OCR baixa qualidade' },
  { ts:'2026-04-29 22:08', tipo:'regressao', skill:'cupom_fiscal', detalhe:'D7 cruzou 60% · alerta humano' },
  { ts:'2026-04-29 17:45', tipo:'run', skill:'transferencia', detalhe:'45 transações · 100% paridade ETL' },
  { ts:'2026-04-29 10:30', tipo:'calibracao', skill:'nota_fiscal', detalhe:'Re-processada: cobertura 68% → 71%' },
  { ts:'2026-04-28 20:15', tipo:'run', skill:'fatura_cartao', detalhe:'9 docs · 100% · paridade 95%' },
  { ts:'2026-04-28 14:00', tipo:'graduacao', skill:'comprovante_pix', detalhe:'7 dias ≥ 90% · GRADUADO' },
  { ts:'2026-04-27 16:12', tipo:'run', skill:'extrato_invest', detalhe:'3 docs · 2 sucesso · 1 layout novo BTG' },
];

// Distribuição agregada (para donut)
const SKILLS_DISTRIBUICAO = (() => {
  const dist = { graduado:0, calibracao:0, regredindo:0, pendente:0 };
  SKILLS_D7.forEach(s => dist[s.d7]++);
  return dist;
})();

// Histórico semanal de cobertura média (pra gráfico de área)
const SKILLS_HISTORICO_8SEM = [
  { sem:'S-7', media:0.51, graduados:3, regredindo:0 },
  { sem:'S-6', media:0.56, graduados:4, regredindo:1 },
  { sem:'S-5', media:0.60, graduados:5, regredindo:1 },
  { sem:'S-4', media:0.64, graduados:5, regredindo:0 },
  { sem:'S-3', media:0.66, graduados:6, regredindo:1 },
  { sem:'S-2', media:0.69, graduados:5, regredindo:2 },
  { sem:'S-1', media:0.71, graduados:5, regredindo:2 },
  { sem:'S0',  media:0.69, graduados:5, regredindo:2 },
];
