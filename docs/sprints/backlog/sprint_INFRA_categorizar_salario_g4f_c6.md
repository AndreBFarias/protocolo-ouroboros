---
id: INFRA-CATEGORIZAR-SALARIO-G4F-C6
titulo: Salário G4F R$ 6.381,14 está como Transferência (não Salário) no C6 — investigar e corrigir categorização + tag IRPF
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-12
fase: VALIDACAO_ARTESANAL
depende_de: []
esforco_estimado_horas: 2
origem: docs/auditorias/VALIDACAO_ARTESANAL_HOLERITE_2026-05-12.md -- ressalva 2; cross-check extrato bancario mostrou que salario G4F vai como Transferencia em vez de Salario, com tag_irpf vazia.  <!-- noqa: accent -->
---

# Sprint INFRA-CATEGORIZAR-SALARIO-G4F-C6 -- corrigir drift de categoria

## Contexto

Validação artesanal HOLERITE G4F fev/2026 (líquido R$ 6.381,14) revelou:

- Holerite declara banco credor: Santander 33, Ag 2327, CC 71018701-1.
- Extrato bancário (XLSX `data/output/ouroboros_2026.xlsx`) **não tem conta Santander** importada para Andre.
- Lançamento R$ 6.381,14 aparece no banco **C6** em 06/03/2026 como `categoria: Transferência` (não `Salário`).
- Tag IRPF: **vazia** (deveria ser `rendimento_tributavel`).

Hipóteses possíveis:
1. Conta Santander não foi importada e o salário aparece só após transferência interna (Santander → C6).
2. Categorizador (categorias.yaml + overrides.yaml) não reconhece padrão G4F → C6 como salário.
3. Regra de override está faltando para PIX/transferência de G4F.

## Objetivo

1. **Investigação** (não-destrutiva):
   - Confirmar que conta Santander de Andre não está em `data/raw/`.
   - Identificar como salário G4F entra no fluxo do C6 (descrição da transferência, banco origem, identificador).
   - Determinar se há padrão regular (mesmo valor mensal, mesma data ±3 dias).
2. **Decisão arquitetural**:
   - Opção A: importar extrato Santander (se disponível) — salário entra direto como `Salário`.
   - Opção B: criar regra de override para reconhecer transferência G4F → C6 como salário (pode ser por valor + data + descrição).
   - Opção C: tag manual via revisor — supervisor marca esses lançamentos.
3. **Implementação**:
   - Se Opção A: adicionar extrator Santander e importar arquivos disponíveis.
   - Se Opção B: regra em `mappings/overrides.yaml`.
   - Se Opção C: documentar fluxo do revisor.
4. **Tag IRPF**: garantir que após categorização, salário G4F tem `tag_irpf: rendimento_tributavel` (impacto pacote IRPF).

## Validação ANTES

```bash
ls data/raw/andre/ | grep -i santander
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM node WHERE banco_origem='Santander' AND quem='Andre'"
.venv/bin/python -c "
import pandas as pd
df = pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato')
g4f = df[(df['valor'].between(6300, 6400)) & (df['quem']=='pessoa_a')]
print(g4f[['data','valor','mes_ref','categoria','banco_origem','obs','identificador']].head(20))
"
grep -i "g4f\|6381" mappings/overrides.yaml mappings/categorias.yaml 2>/dev/null | head
```

## Não-objetivos

- NÃO criar categoria customizada para G4F sem confirmar fluxo bancário real.
- NÃO retoaltar transações que estão na categoria correta.
- NÃO mexer em Infobase (já está como Salário no Itaú).

## Critério de aceitação

1. Investigação documentada em `docs/auditorias/INVESTIGACAO_SALARIO_G4F_C6_2026-MM-DD.md`.
2. Opção escolhida (A/B/C) executada.
3. Lançamentos R$ 6.381,14 G4F passam de `Transferência` para `Salário` com `tag_irpf: rendimento_tributavel`.
4. Pytest baseline mantida ou cresce.
5. Pacote IRPF inclui rendimento G4F.

## Referência

- Auditoria geradora: `docs/auditorias/VALIDACAO_ARTESANAL_HOLERITE_2026-05-12.md`
- Holerites G4F: `data/raw/andre/holerites/HOLERITE_*_G4F_*.pdf` (12 meses)

*"Salario nao chamado de salario nao entra no IRPF -- e o tipo de drift que custa multa em marco do ano seguinte." -- principio INFRA-CATEGORIZAR-SALARIO-G4F-C6*
