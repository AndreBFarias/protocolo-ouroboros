---
id: INFRA-DAS-EXTRAIR-COMPOSICAO
titulo: Estender extrator DAS PARCSN para capturar decomposição principal/multa/juros + composição por tributo + código de barras
status: concluída  <!-- noqa: accent -->
concluida_em: 2026-05-12  <!-- noqa: accent -->
prioridade: P1
data_criacao: 2026-05-12
fase: VALIDACAO_ARTESANAL
depende_de: []
esforco_estimado_horas: 3
origem: docs/auditorias/VALIDACAO_ARTESANAL_DAS_2026-05-12.md -- ETL extrai apenas total e metadados mas omite decomposicao, composicao por tributo e codigo de barras. Campos canonicos do bloco das_parcsn no schema estendido nao sao preenchidos.  <!-- noqa: accent -->
---

# Sprint INFRA-DAS-EXTRAIR-COMPOSICAO

## Contexto

Validação artesanal DAS PARCSN 2026-05-12 confirmou que aritmética interna bate centavo-a-centavo em ambas amostras (fev/2025 R$ 324,31 e mar/2026 R$ 363,49). Mas `_montar_documento` em `src/extractors/das_parcsn_pdf.py` (linha 140) captura apenas:

- `tipo_documento, cnpj_emitente, razao_social, data_emissao, vencimento, periodo_apuracao, numero, parcela_atual, parcela_total, total`.

**Não captura**:

- `principal`, `multa`, `juros` (totais da decomposição)
- `codigo_barras` (linha digitável 47 dígitos com espaços)
- `composicao_por_tributo`: lista de `{codigo, denominacao, principal, multa, juros, total, periodo}` (6 tributos por mês: COFINS, CSLL, INSS, IRPJ, ISS, PIS)
- `quantidade_meses_diversos`: quando `periodo_apuracao == "diversos"`, parsear N meses internos (ex: DAS mar/2026 cobre 06/2024 + 07/2024)

Esses campos são **obrigatórios** no bloco condicional `das_parcsn` do schema (`mappings/schema_opus_ocr.json`) estendido pela Sprint INFRA-OPUS-SCHEMA-EXTENDIDO.

## Objetivo

1. Estender `_montar_documento` em `src/extractors/das_parcsn_pdf.py` para capturar os 4 campos novos.
2. Aplicar regex robustas para a tabela de composição (cabeçalho "Código Denominação Principal Multa Juros Total" + N linhas).
3. Aplicar regex para a linha digitável (47 dígitos com espaços, formato `XXXXX X XXXXX X XXXXX X XXXXX X`).
4. Quando `periodo_apuracao == "diversos"`, identificar N meses (substring date YYYY/MM nos detalhes da composição).
5. Atualizar `_ingerir_holerite_no_grafo` (não é o nome certo — usar o ingestor de DAS) para persistir os novos campos em metadata.
6. Mínimo 8 testes em `tests/test_das_parcsn_pdf.py`:
   - Parse positivo amostra 1 (fev/2025)
   - Parse positivo amostra 2 (mar/2026, com periodo `diversos`)
   - Aritmética `principal + multa + juros = total` para cada amostra
   - Composição por tributo: 6 entradas em amostra 1, 12 em amostra 2 (2 meses × 6 tributos)
   - Código de barras com 47 dígitos
   - Cross-check soma composição = total

## Validação ANTES (padrão (k))

```bash
# Confirma que extrator atual não captura
.venv/bin/python -c "
from src.extractors.das_parcsn_pdf import ExtratorDASPARCSNPDF
from pathlib import Path
r = ExtratorDASPARCSNPDF(Path('data/raw/andre/impostos/das_parcsn/DAS_PARCSN_2025-02-28_2b8e0045.pdf')).extrair_das(Path('data/raw/andre/impostos/das_parcsn/DAS_PARCSN_2025-02-28_2b8e0045.pdf'))
d = r['documento']
assert 'principal' not in d, 'extrator ja captura principal'
assert 'codigo_barras' not in d, 'ja captura codigo_barras'
print('OK: gaps confirmados, extrator nao captura decomposicao')
"
```

## Não-objetivos

- NÃO corrigir o drift de `razao_social` (responsabilidade da Sprint AUDIT2-SPRINT107-RETROATIVA já no backlog).
- NÃO renomear `chave_44` para `numero_documento` ainda (sub-sprint de schema cleanup).
- NÃO mexer em outros tipos de DARF (DAS-MEI, DAS-NFC-e, etc) nesta sprint.
- NÃO tentar OCR fallback — DAS é PDF estruturado, pdfplumber resolve.

## Critério de aceitação (gate (z))

1. `_montar_documento` retorna dict com 14+ campos (era 10).
2. Aritmética validada: `principal + multa + juros == total` para ambas amostras.
3. Soma composição por tributo == total.
4. Schema estendido valida resultado: `jsonschema.validate(doc_dict, schema)` com `tipo_documento=das_parcsn`.
5. Pytest baseline cresce ≥ +8.
6. `make lint` exit 0. `make smoke` 10/10.
7. Re-rodar validação artesanal DAS → APROVADO (sem ressalvas de decomposição).

## Referência

- Auditoria geradora: `docs/auditorias/VALIDACAO_ARTESANAL_DAS_2026-05-12.md`
- Extrator: `src/extractors/das_parcsn_pdf.py::_montar_documento` (linha 140) + `ExtratorDASPARCSNPDF` (linha 202)
- Schema: `mappings/schema_opus_ocr.json` bloco `das_parcsn`
- Sprint irmã: AUDIT2-SPRINT107-RETROATIVA (corrige fornecedor canônico)

*"DAS sem decomposicao eh boleto opaco; com decomposicao eh telescópio fiscal." -- princípio INFRA-DAS-EXTRAIR-COMPOSICAO*
