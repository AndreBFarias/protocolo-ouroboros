# Dados Faltantes

Checklist do que falta para cobrir a janela **jan/2025 -> 16/04/2026**
(acompanhamento alvo definido em 16/04/2026).

Legenda:
- [x] já no projeto e cobre a janela
- [~] parcial (indica os meses que faltam)
- [ ] ausente

---

### André

- [~] **Itaú CC** (PDF, senha via `senhas.yaml`): só
  `itau_extrato_012026.pdf`. Faltam **jan-dez/2025 e fev-abr/2026**
  (15 meses).
- [ ] **Itaú cartão**: pasta não existe. Faltam 16 meses.
- [ ] **Santander CC** (OFX): nenhum arquivo. Faltam 16 meses.
- [~] **Santander cartão** (PDF): 4 faturas com vencimento
  10/jan/26, 10/fev/26, 10/mar/26, 10/abr/26 (faturas de **dez/2025
  a mar/2026**). Faltam **jan-nov/2025 + abr/2026** (12 meses).
- [x] **C6 CC** (OFX): `data/raw/andre/c6_cc/c6_cc_andre_2022-06_2026-04.ofx`
  cobre jun/2022 a 14/04/2026 (892 transações). XLSX antigo movido
  para `legacy/`. Janela coberta.
- [~] **C6 cartão** (XLS): 3 faturas (`Fatura-CPF-janeiro/
  fevereiro/marco-andre.xls`) -- presumivelmente 2026. Faltam
  abr/2026 (se já fechou) e todo 2025 (12 meses).
- [~] **Nubank CC** (OFX/CSV): arquivos em `data/raw/andre/nubank_cc/`:
  - `nubank_cc_andre_17759427-5_2022-03_2025-07.{csv,ofx}` -- conta
    antiga (virou nova em jul/2025).
  - `nubank_cc_andre_73551559-3_2019-10_2026-03.{csv,ofx}` -- conta
    ativa atual.
  Falta **05/03/2026 -> 16/04/2026** da conta ativa.
- [ ] **Nubank cartão** (CSV formato `date,title,amount`): os 4
  CSVs no projeto (`Nubank_2026-08-09` a `Nubank_2026-11-09`) são
  **projeções de parcelas futuras** (parcelas 7/10 a 10/10 de uma
  compra Amazon), não extratos históricos. Faltam **todas as
  faturas reais de jan/2025 a abr/2026** (16 meses).

### Vitória

- [x] **Nubank PF CC** (CSV, `Data,Valor,Identificador,Descrição`):
  48 CSVs cobrindo out/2024 -> abr/2026. Janela coberta.
- [x] **Nubank PJ CC**: `cc_pj_vitoria.csv` (571 transações, de
  05/01/2024 a 01/04/2026). Janela coberta.
- [~] **Nubank PJ cartão** (CSV): 13 faturas jun/2025 -> mai/2026.
  Pendente conhecido: **setembro/2025**.
- [ ] **Nubank PF cartão**: pasta não existe. Faltam 16 meses.
- [ ] **Comprovantes de bolsa NEES/UFAL**: todos os meses.

### Contas Fixas

- [ ] Neoenergia (energia): PDF ou screenshot. Extrator via OCR
  Tesseract já implementado.
- [ ] CAESB (água): PDF. Extrator ainda não implementado.

### Contracheques

- [ ] G4F: todos os meses (XLSX ou PDF).
- [ ] Infobase: todos os meses (XLSX ou PDF).

### Documentos para Integração (`~/Controle de Bordo/`)

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
| Nubank CC | CSV (`Data,Valor,Identificador,Descrição`) ou OFX | Formato diferente do cartão |
| C6 CC | OFX (preferido) ou XLSX | Exportar pelo app (OFX vem em ZIP com senha) |
| C6 cartão | XLS (`Fatura-CPF-*.xls`) | Exportar pelo app |
| Santander CC | OFX | Internet banking desktop |
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
