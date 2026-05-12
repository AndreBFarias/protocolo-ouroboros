---
titulo: Validação artesanal CUPOM_2e43640d.jpeg — ETL × Opus multimodal
data: 2026-05-12
auditor: supervisor Opus 4.7 (multimodal interativo)
escopo: Sprint INFRA-VALIDACAO-ARTESANAL-CUPOM amostra 1/2
status_final: REPROVADO_CLASSE_A
---

# Validação artesanal CUPOM_2e43640d.jpeg

## TL;DR

**REPROVADO classe A.** O cache `data/output/opus_ocr_cache/2e43640d…json` é **sintético** (52 itens fabricados a partir de 4 amostras visíveis + extrapolação para somar R$ 513,31). O extrator `ExtratorCupomTermicoFoto.extrair_cupom` apenas devolve o cache — não realiza OCR fresco quando cache existe. Resultado: ETL e cache "concordam 100%" mas ambos divergem do cupom real.

Cabeçalho confere (CNPJ + razão + data + operador + total + qtd_itens), itens NÃO conferem.

## Setup

| Item | Valor |
|---|---|
| Arquivo | `data/raw/casal/nfs_fiscais/cupom_foto/CUPOM_2e43640d.jpeg` |
| Cache existente | `data/output/opus_ocr_cache/2e43640dde52352439716cb7854af244effa3cc0f9d2c9d7f2aa31454b37f73e.json` |
| Origem do cache | Sprint INFRA-OCR-OPUS-VISAO (commit `0efe0ef`), 2026-05-08 |
| Extrator ETL | `src/extractors/cupom_termico_foto.py::ExtratorCupomTermicoFoto::extrair_cupom` |

## Captura ETL (executada nesta sessão)

```python
from src.extractors.cupom_termico_foto import ExtratorCupomTermicoFoto
from pathlib import Path
caminho = Path("data/raw/casal/nfs_fiscais/cupom_foto/CUPOM_2e43640d.jpeg")
resultado = ExtratorCupomTermicoFoto(caminho).extrair_cupom(caminho)
```

Log do extrator:

```
INFO cupom CUPOM_2e43640d.jpeg upgrade via Opus: 52 itens, total=513.31
```

Resultado:
- `documento.total = 513.31`
- `documento.cnpj_emitente = "56.525.495/0004-70"`
- `len(itens) = 52`
- `confidence = 95.0`
- `recall = 1.0`

**Achado crítico do log**: "`upgrade via Opus`" indica que o extrator **delegou para o cache Opus existente** em vez de rodar OCR fresco. ETL e cache são literalmente o mesmo objeto.

## Captura Opus multimodal (supervisor, eu)

Lendo o JPEG via `Read` tool (Opus 4.7 multimodal, modo artesanal ADR-13):

### Cabeçalho

| Campo | Valor lido visualmente |
|---|---|
| `razao_social` | COMERCIAL NSP LTDA |
| `cnpj` | 56.525.495/0004-70 |
| `endereco` | Verancio Shopping, Setor Comercial Sul, Quadra 08, Bloco E-60, Sala 240 - Brasília |
| `data_emissao` | 27/04/26 (2026-04-27) |
| `horario` | 19:01:39 |
| `operador` | NATALIA PEREIRA DA SILVA |
| `qtd_itens_total` | 52 |
| `total` (Valor a Pagar) | R$ 513,13 ou R$ 513,31 — imagem com resolução baixa, dígitos 1 vs 3 ambíguos |
| `forma_pagamento` | Cartão Débito |

### Itens (primeiras 15 linhas legíveis no cupom REAL)

Texto bruto do cupom (resolução limitada — leitura de boa fé):

```
001 7891571486032 LOCAO RSA FRG CONG TUN     14.39    14.39
002 74861 FILE PEITO FRG CONG kg 1,1346     16.49    18.77
003 1686 SACOLA RENOVAVEL DF 30X50 3 TUN     0.15     0.45
004 89148064 SACOLA RENOVAVEL DF 30X50 3 TUN 0.15     0.45
005 7891900360032 LOCAO RSA FRG CONG TUN    16.99    16.99
006 ?911401571487709 LOCAO RSA FRG CONG TUN 16.99    16.99
007 ?34951861688 MISTURA REFRIG 500ml ...    8.79    17.51
008 ?156000080078 LOCAO RSA FRG CONG TUN    16.99    16.99
009 7896041061188 CAFE 2100 GOZA TUN        10.99    10.99
010 78960748561514 CAFE 2900 FOLHA M TUN    21.99    21.99
011 7965810081092 BANHA CONGELADO TUN        9.99    19.99
012 3271 CEBOLA kg               0.310Kg 7.99 / 2.43
013 1207 PERA kg                 0.265Kg 12.99 / 3.44
014 2925 KIWI kg                 0.566Kg 39.89 / 22.31
015 1841 NACA kg PERSONI ...     0.524Kg 19.90 / 10.43
```

Padrão dominante: **carnes congeladas + frutas a granel + sacolas**, não o "supermercado canônico" do cache.

## Diff campo-a-campo

### Cabeçalho

| Campo | ETL/Cache | Opus multimodal | Classe | Veredito |
|---|---|---|---|---|
| `razao_social` | Comercial NSP LTDA | COMERCIAL NSP LTDA | D (cosmética) | OK |
| `cnpj` | 56.525.495/0004-70 | 56.525.495/0004-70 | A | OK |
| `data_emissao` | 2026-04-27 | 2026-04-27 | A | OK |
| `horario` | 19:01:39 | 19:01:39 | C | OK |
| `operador` | Natalia Pereira da Silva | NATALIA PEREIRA DA SILVA | D | OK |
| `total` | 513.31 | 513,13 ou 513,31 (ambíguo) | A | OK (assumindo 513,31) |
| `qtd_itens` | 52 | 52 | A | OK |
| `forma_pagamento` | debito | Cartão Débito | C | OK |

### Itens (15 amostras primárias)

| # | Cache item.descricao | Cupom real (lido visualmente) | Classe | Veredito |
|---|---|---|---|---|
| 1 | "MACA GRAS SNII kg" — 8.16 | "LOCAO RSA FRG CONG TUN" — 14.39 | A | **ERRO** |
| 2 | "AGUA SNTI 1L" — 3.75 | "FILE PEITO FRG CONG kg" — 18.77 | A | **ERRO** |
| 3 | "BOMBOM SORTIDO" — 15.74 | "SACOLA RENOVAVEL DF 30X50" — 0.45 | A | **ERRO** |
| 4 | "MACARRAO ESPAGUETE 500G" — 9.14 | "SACOLA RENOVAVEL DF 30X50" — 0.45 | A | **ERRO** |
| 5 | "ARROZ TIPO 1 5KG" — 24.06 | "LOCAO RSA FRG CONG TUN" — 16.99 | A | **ERRO** |
| ... | ... | (padrão se mantém) | A | **ERRO** |

Pelo menos **5 dos primeiros 5 itens divergem 100%** entre cache e cupom real.

## Causa-raiz (auditoria do cache)

O próprio cache admite o caráter sintético em `_observacao`:

> "Cache canônico pré-populado pela Sprint INFRA-OCR-OPUS-VISAO. 52 itens conforme docs/auditorias/VALIDACAO_END2END_2026-05-08.md caso 2. Itens com valor_total foram balanceados para somar R$ 513,31 (total declarado pelo cupom). **Descrições baseadas nas amostras visíveis (MACA, AGUA SNTI, BOMBOM, MACARRAO) extrapoladas com itens canônicos de supermercado plausíveis para cobrir os 52**."

Ou seja: **trabalho de placeholder declarado**, executado pela Sprint INFRA-OCR-OPUS-VISAO. Ninguém promoveu ele a gabarito real ainda. A spec INFRA-VALIDACAO-ARTESANAL-CUPOM (que estou executando agora) deveria ter sido o passo onde substituiríamos o cache sintético por leitura artesanal real. **Esta é a entrega que falta**.

## Veredito

**REPROVADO classe A**. Não por bug no extrator (ele segue ADR-13 corretamente — lê cache Opus quando disponível), mas porque o cache não é gabarito real e o extrator não tem como saber. Toda a "validação 4-way ETL × Opus × Grafo × Humano" é circular enquanto o cache for sintético.

## Sprint-filha gerada

`docs/sprints/backlog/sprint_INFRA_substituir_cache_opus_sintetico_cupom_2e43640d.md`

Escopo: substituir o cache sintético `2e43640d…json` (e os 3 outros caches `6554d704`, `67a3104a`, `bc3c42aa`) por **gabaritos reais** lidos artesanalmente pelo supervisor (eu) via `Read` multimodal. Os caches sintéticos eram placeholders da Sprint INFRA-OCR-OPUS-VISAO; o trabalho era promovê-los a gabaritos reais antes de declarar validação artesanal.

## Recomendações

1. **Re-rotular o cache atual** com flag `extraido_via: "opus_supervisor_artesanal_sintetico_placeholder"` (em vez de `opus_supervisor_artesanal` que sugere gabarito real). Confiança deve baixar para 0.5.
2. **Promover 4 amostras de cupom a gabaritos reais** (esta sprint-filha).
3. **Re-rodar validação artesanal** depois — então ETL × Opus real terá significado.
4. **Auditar os outros 3 caches sintéticos** (`6554d704`, `67a3104a`, `bc3c42aa`) — provavelmente todos têm a mesma natureza.

## Reabertura do contrato

Esta validação artesanal **não fecha** a Sprint INFRA-VALIDACAO-ARTESANAL-CUPOM nem habilita Onda 6 a prosseguir com Validação HOLERITE/DAS/NFCe presumindo cache OK. As validações dos outros tipos podem prosseguir em paralelo **se** os caches deles forem gabaritos reais, não sintéticos. **Auditar antes**.

---

*"Cache sintético é placeholder honesto que vira mentira silenciosa quando consumido como gabarito." — princípio descoberto na validação artesanal CUPOM 2026-05-12*
