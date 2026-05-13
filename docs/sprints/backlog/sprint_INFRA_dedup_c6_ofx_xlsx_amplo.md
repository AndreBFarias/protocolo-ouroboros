---
id: INFRA-DEDUP-C6-OFX-XLSX-AMPLO
titulo: Eliminar duplicação sistemática C6 OFX x XLSX (253 pares, ~43% das linhas C6/pessoa_a)
status: backlog
concluida_em: null
prioridade: P0
data_criacao: 2026-05-12
fase: VALIDACAO_ARTESANAL
depende_de: [INFRA-DEDUP-LANCAMENTO-DUPLICADO-G4F]
esforco_estimado_horas: 3
origem: |
  Sprint INFRA-DEDUP-LANCAMENTO-DUPLICADO-G4F detectou que o par
  R$ 6.381,14 / 2026-03-06 e parte de 253 pares no C6/pessoa_a sao
  ingestão dupla OFX + XLSX, não duplicação isolada.
  Ver docs/auditorias/DUPLICACAO_C6_OFX_XLSX_2026-05-12.md
---

# Sprint INFRA-DEDUP-C6-OFX-XLSX-AMPLO -- eliminar ingestão dupla OFX x XLSX

## Contexto

Auditoria `DUPLICACAO_C6_OFX_XLSX_2026-05-12.md` provou que:

- `src/extractors/ofx_parser.py` e `src/extractors/c6_cc.py` ingerem **as
  mesmas transações** dos arquivos `BANCARIO_C6_OFX_*.ofx` e
  `BANCARIO_C6_CC_*.xlsx`.
- `src/transform/deduplicator.py::deduplicar_por_hash_fuzzy` usa chave
  `(data, valor, local)`. O `local` derivado da descrição é
  **estruturalmente diferente** em OFX e XLSX -- OFX traz prefixo
  bancário (`"RECEBIMENTO SALARIO -"`, `"DEBITO DE CARTAO -"`,
  `"PGTO FAT CARTAO C6 -"`), XLSX traz apenas o sufixo.
- 253 pares `(data, valor)` colidem; 197 (~78%) casam após normalizar
  removendo o prefixo antes do primeiro ` - `.
- Impacto: 510 linhas (~43%) de C6/pessoa_a são duplicações silenciosas.

## Objetivo

Eliminar ingestão dupla **sem alterar pares legítimos** (transferências
reais entre contas com mesma data/valor).

## Opções arquiteturais (decidir antes de codar)

1. **(recomendada) Eliminar uma fonte**: rotear
   `BANCARIO_C6_OFX_*.ofx` para `data/raw/_arquivado/` (parte do `legacy/`)
   e usar apenas `BANCARIO_C6_CC_*.xlsx`. XLSX historicamente é mais
   confiável para C6 e já produz formas de pagamento corretas em mais
   casos.
2. **Fingerprint normalizado no dedup nível-2**: adicionar normalização de
   `local` (remover prefixos bancários conhecidos OU regra geral "sufixo
   após primeiro ` - `") na chave do `deduplicar_por_hash_fuzzy`.
3. **Precedência por `banco_origem`/`arquivo_origem`**: quando
   `(data, valor, sufixo_normalizado)` colide, preservar uma fonte
   canônica (decisão por banco).

## Validação ANTES (grep obrigatório -- padrão `(k)`)

```bash
.venv/bin/python scripts/investigar_dedup_c6_ofx_xlsx.py
# Esperado pre-fix: ~253 pares, ~197 casam apos normalizar
```

```bash
rg -n 'extrair_local|deduplicar_por_hash_fuzzy' src/transform/ src/extractors/
```

## Não-objetivos (escopo fechado -- padrão `(t)`)

- NÃO ampliar para Itaú, Santander, Nubank nesta sprint.
- NÃO fazer UPDATE retroativo no grafo SQLite (próximo `make run`
  reescreve tudo).
- NÃO alterar `forma_pagamento` heurísticas dos extratores (sprint
  separada se necessário).
- NÃO promover esta sprint para sprint estrutural sem aprovação do dono.

## Critério de aceitação

1. Diagnóstico aplicado: opção 1, 2 ou 3 escolhida e implementada.
2. Após `make run`, novo `investigar_dedup_c6_ofx_xlsx.py` reporta **≤
   30 pares** (margem para legítimos como transferências reais do casal
   mesmo valor/data).
3. Pares preservados são legítimos (verificação amostral manual de 3
   pares).
4. Pacote IRPF reflete apenas 1 salário G4F por mês após `make run`
   pós-fix.
5. Teste regressivo em `tests/test_dedup_lancamento.py` ampliado.

## Proof-of-work (padrão `(u)`)

```bash
make run  # ou run incremental por banco
.venv/bin/python scripts/investigar_dedup_c6_ofx_xlsx.py
.venv/bin/python -c "
import pandas as pd
df = pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato')
df['data'] = pd.to_datetime(df['data'], errors='coerce').dt.strftime('%Y-%m-%d')
dup = df[(df['data']=='2026-03-06') & (df['valor']==6381.14) & (df['quem']=='pessoa_a')]
print(dup[['data','valor','forma_pagamento','local','identificador']])
# Esperado pos-fix: 1 linha
"
```

## Referência

- Auditoria: `docs/auditorias/DUPLICACAO_C6_OFX_XLSX_2026-05-12.md`
- Spec mãe: `docs/sprints/concluidos/sprint_INFRA_dedup_lancamento_duplicado_g4f.md`
- Script: `scripts/investigar_dedup_c6_ofx_xlsx.py`
- Teste: `tests/test_dedup_lancamento.py`

*"A duplicacao sistematica e mais perigosa que a fraude isolada: passa
despercebida por se vestir de normalidade." -- principio
INFRA-DEDUP-C6-OFX-XLSX-AMPLO*
