# Sprint 44b -- Conferência Artesanal Opus

**Data:** 2026-04-20
**Escopo:** Extrator NFC-e modelo 65 (mini-cupom 80mm com QR SEFAZ)
**Status da implementação:** CONCLUÍDA
**Testes:** 40/40 novos passando (288 total no repo, 0 regressões)
**Lint:** `ruff check` limpo nos arquivos da sprint; 21 avisos pré-existentes de acentuação em arquivos de sprints anteriores permanecem fora de escopo (meta-regra #5).

---

## 1. Tabela de extração por NFC-e

Fixtures sintéticas em `tests/fixtures/nfces/` (texto extraído de NFC-e reais
da Americanas Gama/DF, CPF anonimizado para `000.000.000-00`, chave 44 sintética
com DV SEFAZ válido). PDFs gerados via reportlab em `data/raw/andre/nfs_fiscais/nfce/`
para validação end-to-end.

| NFC-e | Tipo | Nº itens PDF | Nº itens grafo | Recall | Total PDF | Total grafo | Forma pgto | CPF | Chave DV |
|-------|------|--------------|-----------------|--------|-----------|-------------|-------------|-----|----------|
| Compra Americanas (P55) | PDF nativo, 2 itens | 2 | 2 | 100% | R$ 629,98 | R$ 629,98 | PIX ✓ | 000.000.000-00 | válido |
| Supermercado Americanas | PDF nativo, 31 itens densos | 31 | 31 | 100% | R$ 595,52 | R$ 595,52 | PIX ✓ | null (não identificado) | válido |

Meta de aceitação era recall ≥ 90% -- atingido 100% em ambas.

## 2. Grafo após ingestão

Baseline (após Sprint 47c) vs pós-run da 44b:

| Tipo de nó | Antes | Depois | Delta |
|------------|-------|--------|-------|
| `apolice` | 2 | 2 | 0 (já havia) |
| `seguradora` | 1 | 1 | 0 |
| `fornecedor` | 1100 | 1100 | 0 (Americanas já cadastrada pela 47c) |
| `periodo` | 82 | 82 | 0 |
| **`documento`** | 0 | **2** | **+2 (NFC-e 43259 e 43260)** |
| **`item`** | 0 | **33** | **+33 (2 da compra + 31 do supermercado)** |

| Tipo de aresta | Antes | Depois | Delta |
|----------------|-------|--------|-------|
| `emitida_por` | 2 | 2 | 0 |
| `vendida_em` | 2 | 2 | 0 |
| `ocorre_em` | 6088 | 6090 | +2 (documento → periodo) |
| **`fornecido_por`** | 0 | **2** | **+2 (documento → fornecedor)** |
| **`contem_item`** | 0 | **33** | **+33 (documento → item, uma por linha)** |
| **`assegura`** | 0 | **2** | **+2 (apolice → item, criado via heurística do ingestor)** |

**Efeito colateral positivo:** as 2 arestas `assegura` (critério de aceite
pendente da Sprint 47c) foram criadas automaticamente. Quando `./run.sh --tudo`
processou os PDFs em ordem alfabética (`andre/nfs_fiscais/*` antes de
`casal/garantias_estendidas/*`), a NFC-e gerou os itens PRIMEIRO. Depois, ao
re-ingerir as apólices (idempotente), `localizar_item` do ingestor casou por
(descrição fuzzy + CNPJ varejo + janela ±1 dia) e criou a aresta. Triângulo
apolice-item-varejo fechado sem precisar de uma sprint dedicada de linking.

## 3. Matches exatos de `assegura` (query cruzada)

```sql
SELECT a.nome_canonico AS apolice, i.metadata AS item_meta
FROM edge e
JOIN node a ON a.id = e.src_id
JOIN node i ON i.id = e.dst_id
WHERE e.tipo = 'assegura';
```

Resultado:

| Apólice | Item assegurado | Descrição |
|---------|-----------------|-----------|
| 781000129322123 | 000004300823 | CONTROLE P55 DUALSENSE GALACTIC PURPLE |
| 781000129322124 | 000004298119 | BASE DE CARREGAMENTO DO CONTROLE P55 |

Os dois bilhetes MAPFRE agora têm o produto físico concreto amarrado.

## 4. Variantes de forma de pagamento normalizadas

Ordem de prioridade no `normalizar_forma_pagamento` (mais específico primeiro
para evitar que "Cartão" absorva uma linha de débito antes de classificar
como crédito):

| Entrada crua | Canônica |
|--------------|----------|
| `Pagamento Instantâneo (PIX) - Dinâmica 629,98` | PIX |
| `PIX` | PIX |
| `QR Pix 100,00` | PIX |
| `Cartão de Crédito - Visa` | Crédito |
| `Cartão Crédito` | Crédito |
| `Cartão de Débito - Mastercard` | Débito |
| `Dinheiro` | Dinheiro |
| `Espécie` | Dinheiro |
| `Vale Refeição` | Vale |
| `Vale Alimentação Ticket` | Vale |
| `Transferência bancária` | null (não-varejo) |

Variante observada mas ainda não tratada: "Crediário Americanas" (aparece em
parcelamento no próprio varejo). Se surgir em NFC-e real, adicionar ao mapa
como caso canônico dedicado "Crediário" -- não agregar como "Crédito" (é
instrumento de crédito diferente, sem maquininha/bandeira).

## 5. Layouts catalogados em `mappings/layouts_nfce.yaml`

| UF IBGE | Sigla | URL SEFAZ | Emissores conhecidos |
|---------|-------|-----------|----------------------|
| 53 | DF | fazenda.df.gov.br/nfce | Americanas loja 0337 (Gama) |

Outros estados (SP, RJ, MG, etc.) serão adicionados quando NFC-e reais desses
locais atravessarem o pipeline. O extrator canônico cobre o formato-padrão
SEFAZ; layouts específicos entrarão no YAML como overrides.

## 6. Arquivos entregues

| Caminho | Linhas | Propósito |
|---------|--------|-----------|
| `src/utils/chave_nfe.py` | 112 | Validador DV SEFAZ módulo 11 + introspecção (modelo, CNPJ, UF, AAMM, série, número) |
| `src/graph/ingestor_documento.py` | +142 | `upsert_item` e `ingerir_documento_fiscal` compartilhados com Sprint 44 futura |
| `mappings/layouts_nfce.yaml` | 37 | Registry de layouts por SEFAZ |
| `src/extractors/nfce_pdf.py` | 459 | Detector + parser cabeçalho + parser itens + normalizador forma pgto |
| `tests/fixtures/nfces/*.txt` | 2 arquivos | Fixtures anonimizadas |
| `tests/test_nfce_pdf.py` | 315 | 40 testes em 7 classes |
| `src/pipeline.py` | +7 | Registro em `_descobrir_extratores` |

## 7. Decisões de design explicadas

### 7.1. PDF nativo apenas (sem OCR inline)

Spec explícita: foto de cupom térmico é responsabilidade da Sprint 45. Esta
sprint assume texto extraível via pdfplumber. Scan puro de NFC-e fica em
`_classificar/` até que Sprint 45 ou intake evoluído o processe. Fixtures
foram geradas com reportlab para simular o fluxo real de PDF nativo.

### 7.2. Chave 44 como chave canônica do nó `documento`

A chave SEFAZ é globalmente única (inclui UF, AAMM, CNPJ, modelo, série,
número, emissão aleatória, DV). Usá-la como `nome_canonico` garante que
reprocessar uma NFC-e não duplica nó. Itens são chaveados por
`<cnpj_varejo>|<data>|<codigo_produto>` -- o mesmo código vendido em dia
diferente é item diferente (porque a apólice se ancora à compra específica).

### 7.3. Fallback de regex linha-a-linha (não `extract_tables`)

`extract_tables()` do pdfplumber quebra em layout 80mm de algumas SEFAZ.
`RE_LINHA_ITEM` foi escrita flexível o suficiente para absorver variações:
código com letra OCR (`[\d][\dA-Za-z]{5,14}`), `x` opcional entre qtde e
unitário, qtde decimal ou inteira, unidades de 1-4 letras. Itens que
ocupam 2 linhas (continuação da descrição) são reconciliados via
`_e_cabecalho_ou_ruido` -- linhas não-canônicas são anexadas ao item
anterior em vez de perdidas.

### 7.4. Normalização de forma de pagamento com ordem

A string bruta "Cartão de Crédito" prefere matchar "Crédito" antes de
"Cartão" (que seria ambíguo). Tabela `_FORMA_PAGAMENTO_MAPA` é uma tupla
ordenada: PIX → Crédito → Débito → Vale → Dinheiro. Ordem importa.

## 8. Pendências + follow-ups

| Item | Onde | Quando |
|------|------|--------|
| NFC-e escaneadas (pgs 1 e 4 de `notas de garantia e compras.pdf`) | Sprint 45 (OCR cupom) | Quando Sprint 45 rodar |
| DANFE NFe55 -- reuso de `ingestor_documento_fiscal` | Sprint 44 | Próxima janela |
| Crediário Americanas como forma canônica | `_FORMA_PAGAMENTO_MAPA` | Quando surgir em NFC-e real |
| Categorizar prêmio de seguro como categoria dedicada (após cruzamento total) | Sprint 48 ou dedicada | Fase 2 |

## 9. Verificação end-to-end

```bash
.venv/bin/ruff check src/extractors/nfce_pdf.py src/utils/chave_nfe.py \
    src/graph/ingestor_documento.py tests/test_nfce_pdf.py
.venv/bin/pytest tests/test_nfce_pdf.py -v
.venv/bin/pytest -q  # 288 total

./run.sh --tudo

sqlite3 data/output/grafo.sqlite <<SQL
SELECT tipo, COUNT(*) FROM node  WHERE tipo IN ('documento','item')  GROUP BY tipo;
SELECT tipo, COUNT(*) FROM edge  WHERE tipo IN ('contem_item','fornecido_por','assegura')
  GROUP BY tipo;
SQL
```

---

*"Quem despreza o pequeno cupom não merece a grande nota." -- Provérbios 28:20 adaptado*
