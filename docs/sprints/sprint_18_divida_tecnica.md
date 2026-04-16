# Sprint 18 -- Dívida Técnica: Acentuação e Deduplicação

## Status: Concluída

## Objetivo

Resolver dívida técnica identificada na validação de produção: corrigir 56 problemas de acentuação em strings/docs/scripts e revisar 16 duplicatas fuzzy residuais para confirmação manual.

## Contexto

A Sprint 14 implementou os hooks de verificação (`check_acentuacao.py`, `check_gauntlet_freshness.py`) e a integração no `make lint`. Os hooks funcionam e detectam problemas. Esta sprint executa a correção dos 56 problemas reais encontrados.

O deduplicator nível 2 (fuzzy) marca transações com mesmo `data|valor` entre bancos diferentes. As 16 marcadas podem ser coincidências legítimas ou duplicatas reais. Revisão manual necessária.

## Entregas

### Acentuação (56 correções)

Todos em strings, docstrings, docs e scripts -- NÃO em identificadores Python.

- [ ] Corrigir `src/extractors/*.py` (8 ocorrências)
  - c6_cartao.py: `Transacao` -> `transação`
  - c6_cc.py: `Transacao`, `descricao` -> `transação`, `descrição`
  - itau_pdf.py: `Transacao` -> `transação`
  - nubank_cartao.py: `Transacao` -> `transação`
  - nubank_cc.py: `Transacao` -> `transação`
  - santander_pdf.py: `DESCRICAO` (3x), `Transacao` -> `descrição`, `transação`
- [ ] Corrigir `src/dashboard/*.py` (2 ocorrências)
  - app.py: `ultima` -> `última`
  - dados.py: `inicio` -> `início`
- [ ] Corrigir `src/transform/normalizer.py` (1 ocorrência)
  - `classificacao` -> `classificação`
- [ ] Corrigir `src/load/xlsx_writer.py` (1 ocorrência)
  - `transacoes` -> `transações`
- [ ] Corrigir `src/inbox_processor.py` (1 ocorrência)
  - `NAO` -> `não`
- [ ] Corrigir `src/utils/senhas.py` (3 ocorrências)
  - `nao` -> `não`
- [ ] Corrigir `src/obsidian/sync.py` (3 ocorrências)
  - `Relatorios` -> `relatórios`
- [ ] Corrigir `scripts/gauntlet/fases/*.py` (5 ocorrências)
  - categorias.py: `descricao` (4x) -> `descrição`
  - relatorio.py: `conteudo` -> `conteúdo`
- [ ] Corrigir `run.sh` (11 ocorrências)
  - `relatorio`, `transacoes`, `conteudo` -> formas acentuadas
- [ ] Corrigir documentação `docs/*.md` (7 ocorrências)
  - ARMADILHAS.md, AUDITORIA_SPRINTS.md, MODELOS.md, extractors/, sprints/, adr/
- [ ] Corrigir `CLAUDE.md` e `GAUNTLET_REPORT.md` (4 ocorrências)

### Deduplicação fuzzy (revisão manual)

- [ ] Extrair lista das 16 transações marcadas com `_duplicata_fuzzy`
- [ ] Classificar cada par: duplicata real ou coincidência legítima
- [ ] Para duplicatas confirmadas: adicionar em `mappings/overrides.yaml` como `Transferência Interna`
- [ ] Para coincidências legítimas: documentar em `docs/ARMADILHAS.md`
- [ ] Avaliar se threshold do nível 2 precisa de ajuste

## Armadilhas conhecidas

- Strings com `descricao` podem ser chaves de dicionário usadas em lógica de negócio (verificar se renomear não quebra o pipeline)
- `DESCRICAO` no Santander pode vir do header do PDF (manter sem acento se for parsing)
- `run.sh` usa variáveis bash -- acentos em nomes de variáveis funcionam em bash mas são má prática (acentuar apenas strings visíveis ao usuário)
- Duplicatas fuzzy entre Itaú (débito) e Nubank (crédito) para mesma compra são transferências internas, não duplicatas

## Arquivos modificados

| Arquivo | Tipo de correção |
|---------|------------------|
| `src/extractors/*.py` | Strings e logs |
| `src/dashboard/app.py` | Strings de UI |
| `src/dashboard/dados.py` | Strings de UI |
| `src/transform/normalizer.py` | Strings de log |
| `src/load/xlsx_writer.py` | Strings de log |
| `src/inbox_processor.py` | Strings de log |
| `src/utils/senhas.py` | Strings de log |
| `src/obsidian/sync.py` | Strings de path/log |
| `scripts/gauntlet/fases/*.py` | Strings de teste |
| `run.sh` | Strings visíveis ao usuário |
| `docs/*.md` | Texto livre |
| `CLAUDE.md` | Texto livre |
| `GAUNTLET_REPORT.md` | Texto livre |
| `mappings/overrides.yaml` | Possíveis novas regras de dedup |
| `docs/ARMADILHAS.md` | Documentação de duplicatas legítimas |

## Critério de sucesso

`make lint` passa sem erros de acentuação (zero dos 56 atuais). Validador reporta zero ou menos duplicatas residuais. Pipeline continua gerando 2859 transações com 100% de categorização.

## Dependências

Sprint 14 (hooks -- já concluída parcialmente). Nenhuma outra dependência técnica.
