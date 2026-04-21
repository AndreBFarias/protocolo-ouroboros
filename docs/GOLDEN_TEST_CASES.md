# Golden Test Cases — dados reais do Andre para validar sprints

**Última atualização:** 2026-04-21

Este documento registra casos reais que o Andre deixou preparados no ambiente para usar como teste de aceitação ao executar as sprints. Cada caso tem: entrada, saída esperada, sprint que deve fazer passar.

---

## GTC-01 — Boleto de natação (C6 March / Itaú April)

### Entrada

**Arquivos na inbox** (`~/Desenvolvimento/protocolo-ouroboros/inbox/`):

- `natacao_andre.pdf` (230.172 bytes)
- `natacao_andre2.pdf` (230.317 bytes)

Muito provavelmente são boletos de mensalidade do Sesc/natação, dois meses consecutivos. Precisam de OCR ou extração PDF para confirmar valor/data/emissor.

**Transações correspondentes no XLSX** (`data/output/ouroboros_2026.xlsx`, aba `extrato`):

| Linha | Data | Valor | Local | Categoria | Banco | Forma | Observação |
|---|---|---|---|---|---|---|---|
| 5948 | 2026-03-19 | 103,93 | SESC - Serviço SOCIAL DO Comércio ADMINI | Natação | **C6** | — | duplicada (linha 5954 idem) |
| 5954 | 2026-03-19 | 103,93 | SESC - Serviço SOCIAL DO Comércio ADMINI | Natação | **C6** | — | par da 5948 |
| 6056 | 2026-04-10 | 101,60 | PAG BBoleto Sesc - Serviço SOCIAL DO COM | Natação | Itaú | **Boleto** | forma explícita |
| 6036 | 2026-04-04 | 108,99 | Sesc | Natação | Nubank | Crédito | valor diferente, talvez outro item |

### Saída esperada após Sprints 70 + 74 + 17

1. **Sprint 70:** `natacao_andre.pdf` e `natacao_andre2.pdf` detectados como `boleto`, movidos para `data/raw/andre/boletos/`, copiados para `data/raw/originais/{hash}.pdf`.

2. **Sprint 74 (matching heurístico):**
   - Extrator de boleto extrai: emissor (Sesc/Serviço Social do Comércio), valor, data de vencimento, código de barras.
   - Matcher acha transação candidata com score >= 0.8:
     - `natacao_andre.pdf` (valor 103,93 provável) → linha 5948 (C6 19/03) com edge `confirma`.
     - `natacao_andre2.pdf` (valor 101,60 provável) → linha 6056 (Itaú 10/04) com edge `confirma` (forma_pagamento=Boleto já sinaliza).
   - Caso o valor não bater exato (ex: boleto tem juros), fica como proposta em `docs/propostas/linking/`.

3. **Sprint 74 (modal):** clicar em linha do extrato "Natação 103,93 C6 19/03" abre modal com:
   - Detalhes da transação
   - Preview inline do `natacao_andre.pdf`
   - Badge verde "confirmada" (ADR-20, estado da transação)

4. **Sprint 71 (sync rico):** nota gerada em `~/Controle de Bordo/Pessoal/Casal/Financeiro/Documentos/2026-03/boleto-sesc-natacao.md` com:
   ```yaml
   tipo: documento
   tipo_documento: boleto
   valor: 103.93
   data: 2026-03-19
   fornecedor: "[[Sesc]]"
   transacao_ids: [5948, 5954]
   arquivo_original: "[[_Attachments/natacao_andre.pdf]]"
   ```

### Como o executor da Sprint 74 deve usar

1. Ler este documento antes de começar.
2. Rodar o matcher e esperar `auto >= 2` para essas 2 linhas (ou `propostas >= 2` se score < 0.8).
3. Abrir modal no dashboard (aba Extrato) clicando na linha 5948 e confirmar visualmente que o PDF aparece.
4. Reportar veredicto: SUCESSO se o casamento aconteceu; FALHA com log literal se não.

---

## GTC-02 — Notas de garantia e compras (PDF 5MB)

### Entrada

`~/Desenvolvimento/protocolo-ouroboros/inbox/notas de garantia e compras.pdf` (5.012.948 bytes)

PDF grande, possivelmente multi-documento (várias notas em um só arquivo).

### Saída esperada

- **Sprint 70:** detecta como `cupom_garantia` ou `multidoc` (se heterogêneo).
- **Sprint 47b** (já existe na fase GAMA, backlog): extrator de garantia processa. Se multi-doc, invoca heterogeneity detector (Sprint 41d, já concluída).
- **Sprint 74:** vincula garantias às compras correspondentes no extrato.

---

## GTC-03 — Extrato dos débitos (PDF 1.3MB)

### Entrada

`~/Desenvolvimento/protocolo-ouroboros/inbox/extrato dos debitos.pdf` (1.374.632 bytes)

Provável extrato bancário (Itaú ou C6).

### Saída esperada

- **Sprint 70:** detecta como `pdf_itau` ou `pdf_c6` via `intake/registry.py`.
- Extrator correspondente (`src/extractors/itau_pdf.py` ou `c6_cc.py`) processa.
- Deduplicação com extratos já importados (podem haver meses sobrepostos).

---

## Protocolo de uso deste documento

Ao iniciar qualquer sprint que toque inbox / documentos / vinculação:

1. Verificar se tem GTC aplicável aqui.
2. Rodar a sprint.
3. Se GTC passa automaticamente, SUCESSO.
4. Se GTC falha, adicionar ao relatório final o que não passou e POR QUE (log literal).
5. Nunca inventar caso de teste quando tem GTC real disponível.

Novos GTCs podem ser adicionados conforme o Andre for alimentando a inbox com casos reais. Cada entrada deve ter: entrada, saída esperada, sprint alvo.

---

*"Teste real vale por dez testes sintéticos." — princípio"*
