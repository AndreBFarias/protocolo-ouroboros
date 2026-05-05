// Dados sintéticos para o Revisor (Apuração de Transações).
// Lista de transações na visão "extrato_cc · Nubank · 2026-03"
const REVISOR_TRANSACOES = [
  { id: 1, data:'2026-03-01', desc:'PIX RECEBIDO - SALARIO ACME', valor: +9800.00,  estado:'apurado',         conf:1.00 },
  { id: 2, data:'2026-03-02', desc:'PAG ALUGUEL IMOB SILVA',     valor: -2400.00,  estado:'apurado',         conf:0.99 },
  { id: 3, data:'2026-03-04', desc:'AMAZON MARKETPLACE',         valor: -187.40,   estado:'apurado',         conf:0.96 },
  { id: 4, data:'2026-03-05', desc:'IFD*RESTAURANTE',            valor: -68.90,    estado:'rascunho',        conf:0.82 },
  { id: 5, data:'2026-03-07', desc:'TRANSF DOC 4823',            valor: -1500.00,  estado:'divergente',      conf:0.55, divergencia: 'OFX e Opus discordam sobre fornecedor' },
  { id: 6, data:'2026-03-09', desc:'POSTO IPIRANGA 0345',        valor: -210.00,   estado:'apurado',         conf:0.94 },
  { id: 7, data:'2026-03-12', desc:'DROGASIL 1238',              valor: -87.40,    estado:'apurado',         conf:0.91 },
  { id: 8, data:'2026-03-14', desc:'PIX ENVIADO MARIA SANTOS',   valor: -350.00,   estado:'rascunho',        conf:0.74 },
  { id: 9, data:'2026-03-15', desc:'C6 BANK FATURA',             valor: -2847.90,  estado:'divergente',      conf:0.71, divergencia:'Opus leu 2.874,90 — auditoria abriu' },
  { id:10, data:'2026-03-18', desc:'PIX RECEBIDO JOAO BATISTA',  valor: +500.00,   estado:'apurado',         conf:0.98 },
  { id:11, data:'2026-03-22', desc:'NETFLIX.COM',                valor: -55.90,    estado:'apurado',         conf:0.99 },
  { id:12, data:'2026-03-24', desc:'UBER *TRIP',                 valor: -23.80,    estado:'rascunho',        conf:0.86 },
  { id:13, data:'2026-03-25', desc:'SAQUE 24H BB',               valor: -200.00,   estado:'apurado',         conf:0.93 },
  { id:14, data:'2026-03-28', desc:'TARIFA MENSALIDADE',         valor: -29.90,    estado:'apurado',         conf:1.00 },
  { id:15, data:'2026-03-30', desc:'NUBANK RENDIMENTO',          valor: +18.42,    estado:'apurado',         conf:1.00 },
];

// 4-way para a transação selecionada (id 9: divergente fatura C6).
const REVISOR_4WAY = {
  id: 9,
  contexto: { sha8: 'b7d2a04f', conta: 'Nubank · CC ••42', mes: '2026-03' },
  ofx: {
    label: 'OFX',
    src: 'banco · imutável',
    icon: 'bank',
    fields: {
      data:        '2026-03-15',
      descricao:   'C6 BANK FATURA',
      valor:       'R$ 2.847,90',
      tipo:        'DEBIT',
      memo:        'PAGAMENTO FATURA C6',
      identificador: 'FITID:20260315-001874',
    }
  },
  rascunho: {
    label: 'Rascunho ETL',
    src: 'extracao_cartao_v3.py',
    icon: 'cog',
    fields: {
      data:        '2026-03-15',
      descricao:   'C6 BANK FATURA',
      valor:       'R$ 2.847,90',
      categoria:   '(vazio)',
      fornecedor:  '(vazio)',
      eh_pessoal:  '(vazio)',
      observacao:  '(vazio)',
    }
  },
  opus: {
    label: 'Opus',
    src: 'agentic · IRPF-skill v0.4',
    icon: 'sparkle',
    fields: {
      data:        '2026-03-15',
      descricao:   'Pagamento da fatura do cartão C6 (mar/26)',
      valor:       'R$ 2.847,90',
      categoria:   'Cartão de crédito · pagamento',
      fornecedor:  'Banco C6 S.A.',
      eh_pessoal:  'pessoal',
      observacao:  'Diverge do total da fatura (R$ 2.874,90 segundo extração da fatura sha8 b7d2a04f). Provável falha de OCR no extrato bancário (47/74 confundidos).',
      conf:        '0.71',
    }
  },
  humano: {
    label: 'Humano',
    src: 'aguardando você',
    icon: 'user',
    fields: {
      data:        '2026-03-15',
      descricao:   '',
      valor:       'R$ 2.847,90',
      categoria:   '',
      fornecedor:  '',
      eh_pessoal:  '',
      observacao:  '',
    }
  }
};

// Tabs para o painel inferior
const REVISOR_TABS = ['Detalhes', 'Auditoria do Opus', 'Histórico de revisões', 'Hints catalogados'];
