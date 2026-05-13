---
id: INFRA-DEDUP-LANCAMENTO-DUPLICADO-G4F
titulo: 2 lançamentos R$ 6.381,14 G4F idênticos em 06/03/2026 no C6 — investigar duplicação silenciosa
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-12
fase: VALIDACAO_ARTESANAL
depende_de: []
esforco_estimado_horas: 1
origem: docs/auditorias/VALIDACAO_ARTESANAL_HOLERITE_2026-05-12.md -- ressalva 3; 2 lancamentos identicos R$ 6.381,14 no C6 em 06/03/2026 (pessoa_a, categoria Transferencia). Confirmar duplicacao vs legitimo.  <!-- noqa: accent -->
---

# Sprint INFRA-DEDUP-LANCAMENTO-DUPLICADO-G4F -- investigar duplicata silenciosa

## Contexto

Cross-check do salário G4F fev/2026 (R$ 6.381,14) contra extrato bancário revelou **2 lançamentos idênticos** no C6 em 06/03/2026 para pessoa_a:

```
2026-03-06 | 6381.14 | 2026-03 | Transferência | pessoa_a | C6
2026-03-06 | 6381.14 | 2026-03 | Transferência | pessoa_a | C6
```

Possibilidades:
1. **Duplicação real**: importação importou 2x o mesmo extrato C6.
2. **2 transferências legítimas**: G4F pagou 2 parcelas no mesmo dia (improvável mas possível em dia de retroativo).
3. **Falha de dedup por identificador**: lançamentos com sha8 diferente mas mesmo conteúdo bancário.

## Objetivo

1. Inspecionar os 2 lançamentos:
   - `sha8`, `identificador`, `obs`, arquivo origem.
   - Diferenças em colunas auxiliares (forma_pagamento, banco_origem, descrição interna).
2. Determinar se é:
   - Duplicata real → remover 1 dos 2.
   - Lançamentos legítimos diferentes → confirmar identificadores únicos.
3. Se duplicata real: investigar **causa raiz**:
   - Importação dupla do mesmo arquivo C6?
   - Falha no dedup canônico (`src/inbox_processor.py`)?
   - Bug no parser C6?
4. Patch + teste regressivo.

## Validação ANTES

```bash
.venv/bin/python -c "
import pandas as pd
df = pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato')
dup = df[(df['data']=='2026-03-06') & (df['valor']==6381.14) & (df['quem']=='pessoa_a')]
print(dup[['data','valor','identificador','forma_pagamento','banco_origem','obs','classificacao','tipo']])
"
sqlite3 data/output/grafo.sqlite "SELECT id, json_extract(metadata,'\$.data'), json_extract(metadata,'\$.valor'), arquivo_origem FROM node WHERE tipo='transacao' AND json_extract(metadata,'\$.valor')=6381.14 AND json_extract(metadata,'\$.data') LIKE '2026-03%'"
```

## Não-objetivos

- NÃO deletar lançamentos sem confirmar duplicata.
- NÃO modificar parser C6 se a duplicata foi de importação dupla.
- NÃO incluir outras duplicatas potenciais nesta sprint (escopo: só essa).

## Critério de aceitação

1. Diagnóstico claro: duplicata real ou legítimo (com prova de identificadores).
2. Se duplicata: causa-raiz documentada + 1 lançamento removido + teste regressivo.
3. Se legítimo: documentar em `docs/auditorias/LANCAMENTOS_LEGITIMOS_REPETIDOS.md` para evitar reclassificação futura.
4. Pacote IRPF reflete corretamente apenas 1 salário G4F por mês.

## Referência

- Auditoria geradora: `docs/auditorias/VALIDACAO_ARTESANAL_HOLERITE_2026-05-12.md` ressalva 3
- Sprint irmã: INFRA-CATEGORIZAR-SALARIO-G4F-C6 (categoria errada do mesmo lançamento)

*"Duplicata silenciosa em transacao bancaria eh fraude contabil involuntaria; nao se esquece nem se perdoa." -- principio INFRA-DEDUP-LANCAMENTO-DUPLICADO-G4F*
