---
concluida_em: 2026-04-20
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 44b
  title: "Extrator NFC-e modelo 65 (mini-cupom com QR SEFAZ)"
  touches:
    - path: src/extractors/nfce_pdf.py
      reason: "extrai cabeçalho (CNPJ emissor, chave 44 dígitos, número/série NFC-e, data/hora, total, forma de pagamento) e itens do mini-cupom NFC-e (modelo 65)"
    - path: mappings/layouts_nfce.yaml
      reason: "registra variações conhecidas de layout NFC-e por SEFAZ estadual e por emissor"
    - path: src/pipeline.py
      reason: "registra ExtratorNfcePDF em _descobrir_extratores"
    - path: tests/fixtures/nfces/
      reason: "fixtures sintéticas e amostras anonimizadas (inclui o NFC-e da Americanas pgs 1 e 4 de inbox/notas de garantia e compras.pdf)"
  n_to_n_pairs:
    - [src/extractors/nfce_pdf.py, src/graph/ingestor_documento.py]
  forbidden:
    - src/extractors/danfe_pdf.py  # NFe modelo 55 é Sprint 44; NÃO duplicar parser nem misturar layouts
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_nfce_pdf.py -x -q"
      timeout: 60
  acceptance_criteria:
    - "Extrai >= 2 NFC-e de fornecedores diferentes (Americanas + 1 outro) com >= 90% dos itens recuperados"
    - "Chave 44 dígitos validada (dígito verificador correto), modelo == 65"
    - "Forma de pagamento extraída (PIX, Crédito, Débito, Dinheiro)"
    - "Documento de cupom térmico fotografado entra como NFC-e quando tem QR SEFAZ + 'Documento Auxiliar da Nota Fiscal de Consumidor Eletrônica'"
    - "Layout sem destinatário não causa erro (NFC-e quase nunca tem destinatário)"
    - "Grafo recebe 1 Documento + N Itens + 1 Fornecedor + arestas via src/graph/ingestor_documento.py (compartilhado com Sprint 44)"
    - "Acentuação PT-BR correta, zero emojis, zero menções a IA"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 44b -- Extrator NFC-e modelo 65

**Status:** CONCLUÍDA
**Data:** 2026-04-19 (criada após descoberta na Conferência Artesanal Opus da Sprint 41 -- amostra `inbox/notas de garantia e compras.pdf` pg 1 e pg 4)
**Prioridade:** ALTA
**Tipo:** Feature
**Dependências:** Sprint 41 (intake roteia NFC-e para pasta correta), Sprint 42 (grafo), Sprint 44 (compartilha `src/graph/ingestor_documento.py`)
**Desbloqueia:** Sprint 48 (linking documento↔transação)
**Issue:** --
**ADR:** ADR-14 (grafo extensível), ADR-15 (intake multiformato)

---

## Como Executar

- `.venv/bin/pytest tests/test_nfce_pdf.py -v`
- `./run.sh --tudo` -- extrator roda no pipeline e popula grafo

### O que NÃO fazer

- NÃO reusar parser da Sprint 44 (DANFE NFe55) -- layout é fundamentalmente diferente: mini-cupom 80mm, sem destinatário formal, sem tabela ICMS por item, totais condensados, QR SEFAZ obrigatório.
- NÃO tentar OCR neste extrator -- assume PDF nativo. Foto fotografada que vier como imagem é roteada pelo intake (Sprint 41) para o caminho de OCR (Sprint 45 cobre cupom térmico foto), e só DEPOIS chega aqui se o resultado do OCR estiver em formato NFC-e equivalente.
- NÃO normalizar produto neste extrator -- entity resolution é Sprint 49.

---

## Problema

NFC-e (Nota Fiscal Eletrônica de Consumidor, modelo fiscal 65) é a versão simplificada da NFe usada em varejo direto ao consumidor (supermercados, magazines, lojas físicas com checkout fiscal). Em vez do A4 estruturado do DANFE NFe55, é um **mini-cupom 80mm** que parece um cupom térmico, mas é DOCUMENTO FISCAL com chave 44 dígitos validável e QR SEFAZ.

A amostra real `inbox/notas de garantia e compras.pdf` tem 2 NFC-e (pg 1 e pg 4) ao lado de 2 cupons de garantia estendida. O DANFE da Sprint 44 não dá conta -- não tem destinatário formal (consumidor identificado só por CPF opcional), não tem tabela de tributos por item, e o QR SEFAZ é o que garante autenticidade. A regex tentando casar os dois layouts num só extrator vira inviável.

**Diferenças concretas observadas (NFC-e Americanas vs DANFE NFe55):**

| Campo | NFe modelo 55 (Sprint 44) | NFC-e modelo 65 (esta sprint) |
|-------|---------------------------|-------------------------------|
| Cabeçalho | "DANFE" + "DOCUMENTO AUXILIAR DA NOTA FISCAL ELETRÔNICA" | "Documento Auxiliar da Nota Fiscal de Consumidor Eletrônica" |
| Destinatário | Bloco "DESTINATÁRIO/REMETENTE" obrigatório | Linha única "CONSUMIDOR CPF: ..." opcional, no rodapé |
| Itens | Tabela com NCM, CFOP, ICMS por linha | Tabela enxuta: CÓDIGO, DESCRIÇÃO, QTDE × UN, VL UNIT, VL TOTAL R$ |
| Tributos | Bloco completo (BC ICMS, ICMS, IPI, PIS, COFINS) | "Trib aprox: R$ X.XX Fed R$ Y.YY Est R$ 0.00 Mun Fonte: IBPT" no rodapé |
| Pagamento | Não aparece (cobrança via boleto/transferência separada) | "VALOR PAGO R$ ..." + "FORMA DE PAGAMENTO" (PIX, Crédito, Débito, Dinheiro) |
| QR | Opcional, código de barras DANFE | QR SEFAZ obrigatório no rodapé, URL `fazenda.{uf}.gov.br/nfce/...` |
| Largura | A4 (210mm) | 80mm (formato cupom térmico) |
| Modelo na chave 44 | dígitos 21-22 == "55" | dígitos 21-22 == "65" |

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Ingestor de documento (a ser criado pela 44) | `src/graph/ingestor_documento.py` | Insere Documento + Itens + Fornecedor + arestas no grafo. **Reusar; NÃO duplicar.** |
| Validador chave 44 | `src/extractors/danfe_pdf.py` (Sprint 44) | Algoritmo SEFAZ de dígito verificador. Extrair para `src/utils/chave_nfe.py` se ainda não estiver. |
| pdfplumber | lib | Extração de texto. NFC-e PDF nativo costuma ser bem-comportado; layout fixo. |
| Regex CNPJ | `src/transform/irpf_tagger.py:_REGEX_CNPJ` | Reusar (mas considerar Armadilha #20 -- glyphs corrompidos). |

---

## Implementação

### Fase 1: detector específico de NFC-e

`_e_nfce(texto: str) -> bool`:
- Casa pelo menos 2 de 3:
  - `r"Documento\s+Auxiliar\s+da\s+Nota\s+Fiscal\s+de\s+Consumidor"`
  - `r"NFC-?e\s*N[ºo°]"`
  - `r"fazenda\.\w+\.gov\.br/nfce"` (URL do QR SEFAZ)
- Se chave 44 presente, valida que dígitos 21-22 == "65".

### Fase 2: parser do cabeçalho NFC-e

`_parse_cabecalho_nfce(texto: str) -> dict`:
- CNPJ emissor (Armadilha #20: usar `CNP[J\)]:?\s*([\d./\-]+)`)
- Razão social (linha imediatamente acima ou abaixo do CNPJ, dependendo do layout)
- Endereço da loja (multilinha)
- Chave 44 dígitos (mesma regex do DANFE NFe55, com tolerância a espaços)
- NFC-e nº e série
- Data/hora de emissão
- CPF do consumidor (opcional): `r"CONSUMIDOR\s+CPF[:\s]+([\d.\-]+)"`
- Total: `r"VALOR\s+TOTAL\s*R\$?\s*([\d.,]+)"`
- Forma de pagamento: `r"FORMA\s+DE\s+PAGAMENTO\s*[\r\n]+([A-Za-zÁ-ú ()-]+)"` ou via tabela `extract_tables`

### Fase 3: parser dos itens NFC-e

`_parse_itens_nfce(pagina) -> list[dict]`:

Layout típico:
```
CÓDIGO    DESCRIÇÃO            QTDE UN VL.UNIT  VL.TOTAL R$
000004300823 CONTROLE P55 ...   1 PCE x 449,99    449,99
000004298119 BASE DE CARREG... 1 PCE x 179,99    179,99
QTD. TOTAL DE ITENS                                      2
VALOR TOTAL R$                                       629,98
```

Estratégia: `page.extract_tables()` primeiro. Se vazio, fallback regex linha-a-linha:
```python
ITEM_RE = re.compile(
    r"^(?P<codigo>\d{6,15})\s+"
    r"(?P<descricao>.+?)\s+"
    r"(?P<qtde>[\d.,]+)\s+"
    r"(?P<unidade>[A-Z]{1,4})\s+"
    r"x?\s*(?P<valor_unit>[\d.,]+)\s+"
    r"(?P<valor_total>[\d.,]+)$"
)
```

A linha "QTD. TOTAL DE ITENS" serve como sentinela de fim da tabela.

### Fase 4: ingestão no grafo

Reusa `src/graph/ingestor_documento.py` da Sprint 44. Tipo do documento: `"nfce_modelo_65"`. Adiciona campo `metadata.forma_pagamento` no nó Documento (útil para Sprint 48 -- linking confere se débito bancário casa com PIX/cartão da NFC-e).

### Fase 5: registro no pipeline

```python
try:
    from src.extractors.nfce_pdf import ExtratorNfcePDF
    extratores.append(ExtratorNfcePDF)
except ImportError as e:
    logger.warning("Extrator nfce_pdf indisponível: %s", e)
```

### Fase 6: testes

Fixtures em `tests/fixtures/nfces/`:
- `nfce_americanas_compra.pdf` (anonimizada -- pg 1 do PDF da inbox, com 2 itens, total R$ 629,98, pagamento PIX)
- `nfce_americanas_supermercado.pdf` (anonimizada -- pg 4 do PDF da inbox, ~30 itens, layout denso)
- (futuro: NFC-e de outro fornecedor, outro estado, quando aparecer na inbox)

Testes:
- `test_e_nfce_aceita_americanas_pg1`
- `test_e_nfce_rejeita_danfe_modelo55`
- `test_chave_44_modelo_65_valida`
- `test_parse_2_itens_compra_americanas`
- `test_parse_30_itens_supermercado_americanas`
- `test_forma_pagamento_pix_extraida`
- `test_cpf_consumidor_extraido_quando_presente`
- `test_glyph_tolerante_cnpj_corrompido` (Armadilha #20 -- usa fixture com `CNP)` em vez de `CNPJ`)

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A44b-1 | NFC-e e DANFE têm chave 44 idêntica em forma -- só o modelo (dígitos 21-22) distingue | Sempre validar `chave[20:22]` para decidir extrator quando ambíguo |
| A44b-2 | Layout 80mm quebra `extract_tables()` em algumas SEFAZ estaduais | Fallback regex linha-a-linha; ITEM_RE flexível para colunas concatenadas |
| A44b-3 | "Trib aprox" não é o total da nota -- é só estimativa fiscal | Usar EXCLUSIVAMENTE `VALOR TOTAL R$` ou `VALOR A PAGAR R$` |
| A44b-4 | Forma de pagamento "Pagamento Instantâneo (PIX) - Dinâmico" tem variantes longas | Normalizar via lookup: `{"PIX": ["Pagamento Instantâneo", "PIX Dinâmico"], "Crédito": [...], ...}` |
| A44b-5 | NFC-e de cupom térmico fotografado chega via OCR (Sprint 45), não como PDF nativo | Esta sprint só processa PDF nativo; foto vai pro pipeline de OCR e só converge aqui se o produto OCR for re-emitido como NFC-e equivalente |
| A20 (cross) | Glyphs corrompidos em PDF nativo (`CNP)` em vez de `CNPJ`) | Usar classes tolerantes em toda regex de detecção e cabeçalho. Ver ARMADILHAS.md #20 |

Referência: `docs/ARMADILHAS.md`

## Evidências Obrigatórias

- [ ] `make lint` passa sem erros
- [ ] `.venv/bin/pytest tests/test_nfce_pdf.py -v` passa com cobertura >= 75%
- [ ] 2+ NFC-e de fixtures processadas sem warnings
- [ ] Grafo após processamento tem nodes Documento (tipo `nfce_modelo_65`) + Fornecedor + Items
- [ ] Recall de itens >= 90% em amostra validada pelo supervisor (a meta é menor que a 44 porque layout 80mm é mais ruidoso)

## Verificação end-to-end

```bash
make lint
.venv/bin/pytest tests/test_nfce_pdf.py -v
cp tests/fixtures/nfces/*.pdf data/raw/andre/nfs_fiscais/
./run.sh --tudo
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM node WHERE tipo='item' AND JSON_EXTRACT(metadata, '$.documento_tipo')='nfce_modelo_65';"
# esperado: >= soma de itens das fixtures NFC-e
```

## Conferência Artesanal Opus

**Arquivos originais a ler:**

- Cada NFC-e em `tests/fixtures/nfces/*.pdf` e em `data/raw/andre/nfs_fiscais/*.pdf` cujo cabeçalho casa "Consumidor Eletrônica"
- Render visual via `pdfplumber.Page.to_image(resolution=120)` salvo em `/tmp/sprint44b_pages/` para cruzar OCR vs texto nativo

**Outputs a comparar:**

- `sqlite3 data/output/grafo.sqlite "SELECT n.nome_canonico, n.metadata FROM node n WHERE n.tipo='item' AND JSON_EXTRACT(n.metadata, '$.documento_id')=<doc_id>;"`
- `sqlite3 data/output/grafo.sqlite "SELECT JSON_EXTRACT(metadata,'$.forma_pagamento'), JSON_EXTRACT(metadata,'$.total') FROM node WHERE tipo='documento' AND JSON_EXTRACT(metadata,'$.tipo_documento')='nfce_modelo_65';"`

**Checklist:**

1. Para cada NFC-e: o número de itens visível no PDF bate com o número de nodes `item` no grafo?
2. Total visível no PDF == `metadata.total` no grafo?
3. CPF do consumidor (quando presente) extraído corretamente?
4. Forma de pagamento normalizada (PIX/Crédito/Débito/Dinheiro), não a string crua?
5. Chave 44: modelo 65 confirmado? Dígito verificador OK?
6. Layout novo apareceu? Registrar variação em `mappings/layouts_nfce.yaml` e propor ajuste regex.

**Relatório esperado em `docs/propostas/sprint_44b_conferencia.md`:**

- Tabela: NFC-e | nº itens PDF | nº itens grafo | recall | total bate? | forma pgto OK? | observação
- Layouts novos para `mappings/layouts_nfce.yaml` (com diff)
- Propostas de ajuste regex (cada uma como arquivo próprio em `docs/propostas/regra/`)

**Critério de aprovação:** 2 NFC-e de fornecedores distintos com recall >= 90% cada e total da nota batendo 100%.

---

*"Quem despreza o pequeno cupom não merece a grande nota." -- adaptação livre de Provérbios 28:20*
