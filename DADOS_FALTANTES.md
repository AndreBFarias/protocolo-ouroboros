# Dados Faltantes

Checklist de arquivos que precisam ser adicionados ao projeto para completar o histórico financeiro.

---

### André

- [ ] Nubank cartão: históricos de 2024 e 2025 (CSVs, formato `date,title,amount`)
- [ ] C6 conta corrente: históricos de 2024 e 2025 (XLSX)
- [ ] C6 cartão: históricos de 2024 e 2025 (XLS, formato `Fatura-CPF-*.xls`)
- [ ] Itaú extrato CC: históricos de 2024 e 2025 (PDFs protegidos, senha via `senhas.yaml`)
- [ ] Santander cartão: identificar quais meses cobrem os 4 PDFs existentes (nomes numéricos sem data)
- [ ] Contracheques G4F: todos os meses (XLSX ou PDF)
- [ ] Contracheques Infobase: todos os meses (XLSX ou PDF)

### Vitória

- [ ] Nubank PJ cartão: setembro/2025 (falta entre agosto e outubro)
- [ ] Nubank PF CC: meses anteriores a outubro/2024
- [ ] Comprovantes de bolsa NEES/UFAL: todos os meses

### Contas Fixas

- [ ] Neoenergia (energia): contas de todos os meses disponíveis (PDF ou screenshot)
- [ ] CAESB (água): contas de todos os meses (PDF). Extrator de água ainda não implementado (sprint futura)

### Documentos para Integração (~/Controle de Bordo/)

- [ ] Contratos de trabalho (F2F, Paim, IBPAD)
- [ ] Currículos atualizados
- [ ] Documentos pessoais (CPF, RG, CTPS)
- [ ] Registrato BCB (André e Vitória)
- [ ] CCS bancário (André e Vitória)
- [ ] Serasa/dívidas (André e Vitória)
- [ ] Diplomas/certificados (graduação, pós, cursos)
- [ ] Seguro de vida
- [ ] Comprovante de renda

---

### Formato Esperado

| Banco/Fonte | Formato Aceito | Observação |
|---|---|---|
| Itaú CC | PDF (extrato mensal) | Protegido por senha via `senhas.yaml` |
| Nubank cartão | CSV (`date,title,amount`) | Exportar pelo app ou site |
| Nubank CC | CSV (`Data,Valor,Identificador,Descrição`) | Formato diferente do cartão |
| C6 CC | XLSX | Exportar pelo app |
| C6 cartão | XLS (`Fatura-CPF-*.xls`) | Exportar pelo app |
| Santander cartão | PDF (fatura mensal) | Sem senha |
| Neoenergia | PDF ou screenshot (imagem) | OCR via Tesseract |
| CAESB | PDF | Extrator ainda não implementado |
| Contracheques | XLSX ou PDF | Qualquer formato legível |

---

### Onde Colocar

Arquivos brutos devem ser colocados em um dos dois locais:

1. **`inbox/`** -- Jogar qualquer arquivo aqui sem organizar. O pipeline identifica e processa automaticamente.

2. **`data/raw/{pessoa}/{banco_tipo}/`** -- Organizado por pessoa e fonte. Exemplos:
   - `data/raw/andre/itau_cc/extrato_2024_01.pdf`
   - `data/raw/andre/nubank_cartao/nubank-2024-01.csv`
   - `data/raw/vitoria/nubank_pj_cartao/nubank-2025-08.csv`
   - `data/raw/contas/neoenergia/conta_2025_03.pdf`

O pipeline varre ambos os diretórios. Não é necessário renomear os arquivos -- a identificação é feita pelo conteúdo.

---

<!-- "Aquele que tem um porquê para viver pode suportar quase qualquer como." -- Friedrich Nietzsche -->
