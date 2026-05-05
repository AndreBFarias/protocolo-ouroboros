// Dados sintéticos para a fila do Inbox.
const INBOX_FILA = [
  { sha8:'a3f9c1e2', filename:'extrato_nubank_cc_2026-03.pdf', tipo:'pdf',  tamanho:'182 KB', status:'extraido',   data:'2026-04-29 14:32', tipoArquivo:'extrato_cc' },
  { sha8:'b7d2a04f', filename:'fatura_c6_cartao_2026-03.pdf', tipo:'pdf',   tamanho:'241 KB', status:'extraido',   data:'2026-04-29 14:31', tipoArquivo:'fatura_cartao' },
  { sha8:'c1e8b302', filename:'recibo_farmacia_drogasil.jpg', tipo:'img',   tamanho:'87 KB',  status:'aguardando', data:'2026-04-29 14:28', tipoArquivo:'recibo' },
  { sha8:'d4b6f192', filename:'nota_consulta_cardio.pdf',     tipo:'pdf',   tamanho:'95 KB',  status:'aguardando', data:'2026-04-29 14:25', tipoArquivo:'nota_servico' },
  { sha8:'e0a7c843', filename:'extrato_itau_cc_2026-03.ofx',  tipo:'ofx',   tamanho:'12 KB',  status:'extraido',   data:'2026-04-29 13:50', tipoArquivo:'extrato_cc' },
  { sha8:'f29b1c75', filename:'cupom_padaria.png',            tipo:'img',   tamanho:'54 KB',  status:'falhou',     data:'2026-04-29 13:42', tipoArquivo:'cupom_fiscal', erro:'OCR não conseguiu ler valor total' },
  { sha8:'a8c4d91e', filename:'extrato_nubank_cc_2026-03.pdf',tipo:'pdf',   tamanho:'182 KB', status:'duplicado',  data:'2026-04-29 13:30', tipoArquivo:'extrato_cc' },
  { sha8:'b2e6f48d', filename:'energia_neoenergia_marco.pdf', tipo:'pdf',   tamanho:'104 KB', status:'extraido',   data:'2026-04-29 12:15', tipoArquivo:'fatura_concessionaria' },
  { sha8:'c7d3a128', filename:'inss_2025.csv',                tipo:'csv',   tamanho:'4 KB',   status:'extraido',   data:'2026-04-29 11:08', tipoArquivo:'tabela' },
  { sha8:'d9e5b047', filename:'recibo_dentista.jpg',          tipo:'img',   tamanho:'112 KB', status:'aguardando', data:'2026-04-29 10:54', tipoArquivo:'recibo_medico' },
  { sha8:'e1f8c360', filename:'fatura_santander_cartao.xlsx', tipo:'xlsx',  tamanho:'31 KB',  status:'extraido',   data:'2026-04-29 09:40', tipoArquivo:'fatura_cartao' },
  { sha8:'f5a9d271', filename:'comprovante_aluguel_03.pdf',   tipo:'pdf',   tamanho:'78 KB',  status:'extraido',   data:'2026-04-29 09:12', tipoArquivo:'comprovante' },
];

const INBOX_TIPOS_SUPORTADOS = ['PDF', 'PNG', 'JPG', 'CSV', 'XLSX', 'OFX', 'JSON', 'TXT', 'HTML'];

// Sidecar JSON sintético (mostrado no drawer)
const INBOX_SIDECAR = {
  sha256: 'a3f9c1e2b7d4a8c5e9f1b2d3c4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3',
  sha8: 'a3f9c1e2',
  filename: 'extrato_nubank_cc_2026-03.pdf',
  tipo_arquivo: 'extrato_cc',
  extrator: 'nubank_cc',
  versao_extrator: '2.4.1',
  registrado_em: '2026-04-29T14:32:11-03:00',
  resultado: {
    status: 'ok',
    confianca: 0.94,
    transacoes: 47,
    periodo: { inicio: '2026-03-01', fim: '2026-03-31' },
    saldo_inicial: 'R$ 3.218,40',
    saldo_final: 'R$ 4.102,15',
    campos_baixa_confianca: ['fornecedor[12]', 'fornecedor[31]'],
  },
  caminho_processado: 'data/inbox/.processed/2026-03/a3f9c1e2.pdf',
};
