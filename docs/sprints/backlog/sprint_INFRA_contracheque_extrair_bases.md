---
id: INFRA-CONTRACHEQUE-EXTRAIR-BASES
titulo: Estender _parse_g4f e _parse_infobase para capturar bases fiscais (base_inss, base_irrf, FGTS, dependentes, CNPJ empresa, dados bancários)
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-12
fase: VALIDACAO_ARTESANAL
depende_de: []
esforco_estimado_horas: 3
origem: docs/auditorias/VALIDACAO_ARTESANAL_HOLERITE_2026-05-12.md -- ETL captura apenas 5 campos classe A (bruto, INSS, IRRF, VR/VA, liquido) mas omite bases fiscais visiveis no PDF de ambos empregadores. Impacto direto em pacote IRPF.  <!-- noqa: accent -->
---

# Sprint INFRA-CONTRACHEQUE-EXTRAIR-BASES -- capturar bases fiscais omitidas

## Contexto

Validação artesanal HOLERITE 2026-05-12 (G4F + Infobase fev/2026) confirmou que `_parse_g4f` e `_parse_infobase` em `src/extractors/contracheque_pdf.py` extraem corretamente os 5 campos críticos classe A (bruto, INSS, IRRF, VR/VA, líquido). Aritmética bate centavo-a-centavo nos 2 casos.

Mas os PDFs contêm metadata fiscal importante que o ETL **ignora**:

**G4F**:
- `base_inss`: 8.475,55
- `base_irrf`: 8.657,25
- `base_fgts`: 8.657,25
- `fgts_mes`: 692,58
- `dependentes_ir`: 0
- `dependentes_salfam`: 0
- `cnpj_empresa`: 07.094.346/0002-26
- `razao_social`: G4F SOLUCOES CORPORATIVAS LTDA
- `cargo`: ANALISTA DE BUSINESS INTELLIGENCE
- `data_admissao`: 08/05/2025
- `data_pagamento`: 06/03/2026
- `banco_credito`: Santander 33, Ag 2327, CC 71018701-1

**Infobase**:
- `base_inss`: 8.475,55
- `base_irrf`: 10.000,00
- `base_fgts`: 9.011,93
- `fgts_mes`: 800,00
- `cnpj_empresa`: 02.800.463/0001-63
- `razao_social`: INFOBASE CONSULTORIA E INFORMATICA LTDA
- `cargo`: ANALISTA DE DADOS
- `data_admissao`: 02/06/2025

Impacto IRPF: alto. `base_inss` e `base_irrf` são campos canônicos do informe de rendimentos anual.

## Objetivo

1. Estender `_parse_g4f` em `src/extractors/contracheque_pdf.py` (linha 132) para capturar:
   - `base_inss`, `base_irrf`, `base_fgts`, `fgts_mes`, `dependentes_ir`, `dependentes_salfam`
   - `cnpj_empresa`, `razao_social`, `cargo`, `data_admissao`, `data_pagamento`, `cpf_colaborador`
   - `banco_credito` (banco_numero + agencia + conta)
2. Estender `_parse_infobase` (linha 191) com os mesmos campos.
3. Validar via regex contra texto bruto de ambos PDFs.
4. Cross-check aritmético adicional: `base_inss * aliquota_inss = inss` (sanidade quando alíquota aparece).
5. Estender `_ingerir_holerite_no_grafo` (linha 282) para persistir os novos campos em `metadata` do node `documento`.
6. Pelo menos 6 testes novos em `tests/test_contracheque.py` (parse positivo + regex base_inss + retrocompat).

## Validação ANTES

```bash
.venv/bin/python -c "
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location('cp', 'src/extractors/contracheque_pdf.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
texto_g4f = m._extrair_texto(Path('data/raw/andre/holerites/HOLERITE_2026-02_G4F_6381.pdf'))
# Confirma os textos das bases estão no PDF
print('base_inss' in texto_g4f.lower() or 'Base de cálculo INSS' in texto_g4f)
print('FGTS do mês' in texto_g4f)
print('Banco: 33' in texto_g4f)
"
```

## Não-objetivos

- **NÃO** mudar os 5 campos críticos já extraídos.
- **NÃO** quebrar retrocompat com extratores que consomem o dict atual.
- **NÃO** persistir CPF do colaborador em log INFO (mascarar).
- **NÃO** processar holerites de outras empresas além de G4F + Infobase (sub-sprint futura).

## Critério de aceitação

1. `_parse_g4f` e `_parse_infobase` retornam dicionário com 14+ campos (era 8).
2. 6 testes novos pelo menos. Pytest baseline cresce ≥ +6.
3. Cross-check aritmético opcional: `abs(base_inss * (inss/base_inss) - inss) < 0.01`.
4. Grafo persiste novos campos em `metadata`.
5. Validação artesanal HOLERITE re-rodada vira APROVADO (sem ressalvas de bases).
6. `make lint` exit 0. `make smoke` 10/10.

## Referência

- Auditoria que gerou: `docs/auditorias/VALIDACAO_ARTESANAL_HOLERITE_2026-05-12.md`
- Extrator: `src/extractors/contracheque_pdf.py::_parse_g4f` (linha 132), `_parse_infobase` (linha 191)
- ADR-08 (extratores documentais)

*"Holerite eh contrato fiscal entre 3 partes (empregado, empregador, Receita); extrator que se contenta com liquido lambe a casca do contrato e ignora o conteudo." -- principio INFRA-CONTRACHEQUE-EXTRAIR-BASES*
