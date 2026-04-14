# Sprint 04 -- Inteligência de Categorização

## Status: Concluída
Data de conclusão: 2026-04-14
Commit: 12b778c
Issue: #4

## Objetivo

Elevar a precisão da categorização com overrides manuais, implementar tagging automático para IRPF e criar validador de integridade do pipeline.

## Entregas

- [x] Overrides manuais via overrides.yaml (10 overrides com prioridade sobre regex)
- [x] Suporte a regra_valor nos overrides (ex: Ki-Sabor >= R$ 800 = Aluguel)
- [x] Detecção de padrões não mapeados (3+ ocorrências)
- [x] IRPF tagger com 21 regras em 5 tipos de tag
- [x] Tag rendimento_tributavel (G4F, Infobase, salários)
- [x] Tag rendimento_isento (NEES/UFAL, FGTS, poupança)
- [x] Tag dedutivel_medico (clínicas, hospitais, dentistas, planos)
- [x] Tag imposto_pago (DARF, DAS MEI, Receita Federal)
- [x] Tag inss_retido
- [x] Validador com 6 checks de integridade
- [x] Integração no pipeline como passo 7

## O que ficou faltando

- Deduplicação cruzada CC x cartão: exige lógica mais complexa de pareamento temporal
- Deduplicação PIX entre contas: difícil sem metadados de destino
- Validação receitas vs holerites: não havia dados de holerite disponíveis
- Saldos 31/12 para IRPF: exige integração com extrato de final de ano

## Armadilhas conhecidas

- Ki-Sabor tem regra de valor: abaixo de R$ 800 é alimentação, acima é aluguel
- Categorizer original usava break em vez de return, causando aplicação de múltiplas regras
- Tags IRPF não sobrescrevem tags já existentes de overrides/categorizer

## Arquivos criados/modificados

| Arquivo | Descrição |
|---------|-----------|
| `mappings/overrides.yaml` | 10 overrides manuais (nomes pessoais, Ki-Sabor) |
| `src/transform/irpf_tagger.py` | 21 regras IRPF em 5 tipos de tag (79 tags geradas) |
| `src/utils/validator.py` | 6 validações de integridade, executável via CLI |
| `src/transform/categorizer.py` | Refatorado: overrides como prioridade 1 |
| `src/pipeline.py` | Integrado irpf_tagger como passo 7 |

## Critério de sucesso

Validador roda sem erros críticos. 100% das transações categorizadas. Tags IRPF aplicadas corretamente. Pipeline integrado e funcional.

## Dependências

Sprint 03 (dashboard funcional).
