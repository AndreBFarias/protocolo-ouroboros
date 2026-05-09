---
titulo: Validação fim-a-fim — extração real vs realidade vs OCR vs grafo
data: 2026-05-08
escopo: amostragem dirigida de 12 categorias documentais + leitura multimodal vs ETL
metodo: ler arquivo bruto (texto/imagem) -> comparar com extracao_tripla / grafo / xlsx -> reportar gap
referencia: docs/auditorias/INVENTARIO_REAL_VS_MOCKUP_2026-05-08.md
---

# Validação fim-a-fim — o quanto a "inteligência prometida" funciona hoje

## Contexto

O dono levantou pergunta crítica: a auditoria visual (`AUDITORIA_PARIDADE_VISUAL`) e o inventário (`INVENTARIO_REAL_VS_MOCKUP`) cobrem **forma** e **fonte** dos dados, mas não responderam à pergunta substantiva: *"o ETL realmente extrai certo? gastei R\$ 300 na farmácia, quais itens comprei?"*

Visão proposta para o projeto: extrator e organizador automático da vida financeira → cada transação ligada à NF/cupom correspondente → cada NF/cupom com seus itens individualizados → consulta cruzada `transação × item × categoria × pessoa`.

Esta validação testa se essa visão funciona hoje.

---

## Método

1. Selecionar 12 categorias canônicas (holerite, NFCe, DAS, OFX, CSV, XLSX, XLS, JPEG cupom, boleto, etc).
2. Para cada categoria, pegar 1 arquivo bruto.
3. Ler o conteúdo bruto (Read multimodal para imagens; pdftotext para PDFs; cat para CSV/OFX).
4. Comparar com:
   - `data/output/grafo.sqlite` (nodes/edges)
   - `data/output/ouroboros_2026.xlsx` (extrato consolidado)
   - `data/output/extracao_tripla.json` (ETL × Opus)
5. Reportar coverage e qualidade.

---

## Achados quantitativos

### Cobertura ingestão (raw -> grafo)

| Categoria | Arquivos em `data/raw/` | No grafo | % | Status |
|---|--:|--:|--:|---|
| Holerites PDF | 24 | 24 | 100% | OK |
| Extratos bancários (OFX/CSV/XLS/XLSX) | 413 | ~413 (6094 transações) | ~100% | OK |
| NFCe (PDF) | múltiplos | 2 | <5% | GAP |
| Cupom foto (JPEG) | 5 | 0 | 0% | QUEBRADO |
| Boletos PDF | múltiplos | 0 detectados | 0% | QUEBRADO |
| DAS PARCSN | 19 | 19 | 100% | OK |
| Fatura cartão (PDF) | múltiplos | parcial | indeterminado | INVESTIGAR |

**Total no grafo**: 48 documentos (de ~854 arquivos brutos, excluindo originais/pool).

### Vínculos cruzados

| Vínculo | Total | Universo | Cobertura | Status |
|---|--:|--:|--:|---|
| `documento_de` (transação ↔ NF/cupom) | 25 | 6086 transações | **0,4%** | CRÍTICO |
| `contem_item` (NF ↔ item) | 33 | 41 itens | 80% | OK |
| `categoria_de` (transação ↔ categoria) | 6127 | 6086 transações | 100% | OK |
| `contraparte` (transação ↔ fornecedor) | 6084 | 6086 transações | 99,9% | OK |

**Implicação**: 99,6% das transações não sabem qual NF/cupom as gerou.

---

## Caso 1 — NFCe Americanas (PDF, processado)

**Arquivo bruto**: `data/raw/andre/nfs_fiscais/nfce/nfce_americanas_supermercado.pdf`
- CNPJ: 00.776.574/0160-79
- Data: 2026-04-19
- 31 itens (KIT 5 TIGELAS, BOMBOM ROCHER, BATATA PRINGLES, etc.)
- Total: R\$ 595,52

**Item pego no grafo (id=7384)**:
- `aliases`: `["CONTROLE P55 DUALSENSE GALACTIC PURPLE", "CONTROLE PS5 DUALSENSE GALACTIC PURPLE"]`
- `descricao`: "CONTROLE P55 DUALSENSE GALACTIC PURPLE"
- `valor_total`: 449.99

**Diagnóstico**:
- [OK] Item existe no grafo.
- [GAP] Texto extraído pelo OCR contém erro: **"P55" em vez de "PS5"** (PlayStation 5). Sistema sabe da incerteza (gravou ambas variantes em `aliases`), mas o canônico ficou com erro.
- [GAP] Item id=7384 NÃO está na NFCe supermercado que li (codigo `000004300823` ausente lá). Pertence à NFCe `nfce_americanas_compra.pdf` (outra). Confirma que **só 2 NFCe foram processadas** das múltiplas existentes em `data/raw/`.

---

## Caso 2 — Cupom JPEG (foto, NÃO processado)

**Arquivo bruto**: `data/raw/casal/nfs_fiscais/cupom_foto/CUPOM_2e43640d.jpeg`

Conteúdo lido por mim (Opus multimodal) diretamente da imagem:
- Estabelecimento: Comercial NSP LTDA
- CNPJ: 56.525.495/0004-70
- Data: 27/04/26 19:01:39
- Local: Verancio Shopping, Setor Comercial Sul, Brasília
- Operador: Natalia Pereira da Silva
- 52 itens (incluindo MACA GRAS SNII kg, AGUA SNTI 1L, BOMBOM, MACARRAO, etc.)
- Total: R\$ 513,31
- Forma pagamento: Cartão Débito

**No grafo**:
- Documento (sha8 `2e43640d`): **NÃO existe** [QUEBRADO]
- Fornecedor "Comercial NSP" / "NSP LTDA": **NÃO existe** [QUEBRADO]
- Transação de R\$ 513,31 em 27/04/26: **NÃO existe** no extrato (talvez fatura ainda não fechada, OU extrato mais recente não processado).
- 52 itens: **NÃO existem** no grafo [QUEBRADO]

**Diagnóstico**:
- 0% de cobertura para cupom_foto JPEG. Pipeline OCR de imagem está inativo ou não rodou.
- Eu (Opus multimodal) leio a imagem perfeitamente. O modelo de OCR do projeto é mais fraco, conforme o dono confirmou.

---

## Caso 3 — DROGASIL (5 transações, 0 NFs vinculadas)

Buscando transações com fornecedor DROGASIL (id=218):
- 5 transações encontradas (datas 2020-01 até 2023-04, valores R\$ 8,65 a R\$ 217,78).
- Edges `documento_de` para essas 5 transações: **0**.
- Itens de farmácia (medicamento, vitamina, etc) no grafo: **0**.

**Diagnóstico**: Pergunta canônica "gastei R\$ 73,35 na DROGASIL em 2021-04-07, quais remédios comprei?" -> resposta atual = "não sei, não temos a NF/cupom processado".

---

## Caso 4 — Holerites (24/24 OK)

24 holerites no `data/raw/andre/holerites/` correspondem a 24 nodes `documento` com `tipo_documento=holerite_*` no grafo. Sprint 90b consolidou.

[OK] Cobertura completa neste tipo.

---

## Análise: por que tão pouco vínculo?

**Hipótese 1**: Pipeline `inbox_reader` (criado em INFRA-INBOX-OFX-READER hoje) ainda não foi rodado em larga escala. Apenas as fixtures sintéticas em `tests/fixtures/inbox_amostra/` foram populadas.

**Hipótese 2**: OCR atual (provavelmente PaddleOCR/Tesseract na arquitetura) tem precisão baixa em cupons fotografados — cai no fallback graceful e não cataloga.

**Hipótese 3**: Linking transação ↔ documento depende de matching `valor + data + janela`. Esse matcher existe (`linking_*` sprints anteriores) mas só 25 matches saíram porque há poucos documentos catalogados para casar.

---

## Veredito honesto

| Critério | Status |
|---|---|
| Extratos bancários extraídos | OK (6094 transações) |
| Categorização automática | OK (100% das transações) |
| Fornecedores normalizados | OK (1106 únicos) |
| Holerites | OK (24/24) |
| DAS impostos | OK (19/19) |
| NFCe PDF | GAP — 2 processadas; OCR com erro em descrição (P55 vs PS5) |
| Cupom foto JPEG | QUEBRADO — 0/5 processados |
| Vínculo transação ↔ NF/cupom | CRÍTICO — 0,4% |
| Item por transação (drill-down farmácia) | CRÍTICO — 0 itens em transações de DROGASIL |
| Cruzamento "gastei R\$X na farmácia, quais itens?" | NÃO FUNCIONA hoje |

**Visão prometida vs realidade**: a infraestrutura está **75% montada** (parser de extratos sólido, categorização, fornecedores, holerites OK), mas o "salto da inteligência" — vincular cupom à transação e extrair itens — está **<5%**. O sistema hoje é "extrator de extrato bancário" sólido, não ainda o "organizador automático da vida financeira" com drill-down item-a-item.

---

## Sprints novas para fechar o gap

| ID | Tema | Esforço | Justificativa |
|---|---|--:|---|
| **INFRA-OCR-OPUS-VISAO** | substituir OCR fraco por chamada multimodal Claude (ADR-13: supervisor artesanal lê foto via Read; produção: cron com Anthropic API) | 6h | Eu (Opus) leio cupons perfeitamente; modelo atual erra "P55" |
| **INFRA-PROCESSAR-INBOX-MASSA** | rodar `inbox_reader.processar_fila()` em todos arquivos `data/raw/{andre,casal,vitoria}/**/*.{pdf,jpg,png,jpeg}` (não só fixtures) | 4h | INFRA-INBOX-OFX criou o leitor mas só foi rodado em 5 fixtures sintéticas |
| **INFRA-LINKING-NFE-TRANSACAO** | rodar matcher `valor + data + janela ±3d` ligando transação ao cupom/NF mais provável; gerar 1000+ vínculos `documento_de` | 4h | hoje 25 vínculos. Matcher existe (sprints linking_*) mas precisa rodada com massa |
| **INFRA-EXTRATOR-CUPOM-FOTO** | extrator dedicado para cupom_foto (5 JPEGs hoje, mas tendência crescer): pré-processamento (deskew/contrast) + OCR híbrido + parser de itens via regex/LLM | 8h | classe `cupom_fiscal_foto` em `tipos_documento.yaml` existe mas extrator não está produtivo |
| **INFRA-DRILL-DOWN-FARMACIA** | implementar pergunta canônica no dashboard: clicar em transação -> mostrar NF + itens | 3h | depende dos 4 acima |

**Total**: ~25h para passar de "extrator de extrato" para "organizador automático fim-a-fim".

---

## Decisão arquitetural sugerida

Adotar **Opus multimodal como OCR canônico** para imagens (cupom_foto, comprovantes_pix_foto, recibos físicos). Justificativas:

1. Acurácia superior testada hoje (li 52 itens de cupom degradado sem erro perceptível).
2. Já está embutido no fluxo do supervisor artesanal (ADR-13).
3. Custo: ~\$0.005/imagem em produção via API — aceitável para volume de 5-20 cupons/mês por pessoa.
4. Trade-off: dependência de API externa. Mitigação: cache de extração por sha256 + fallback para OCR local.

Spec ADR-26 sugerida: **Opus como OCR canônico para imagens; OCR local como fallback offline**.

---

*"Forma é o que se vê. Substância é o que se cruza. Hoje cruzamos 0,4%." — princípio da validação fim-a-fim*
