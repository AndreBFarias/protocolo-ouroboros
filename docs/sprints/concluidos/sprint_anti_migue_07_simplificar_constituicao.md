# Sprint ANTI-MIGUE-07 -- Simplificar constituição técnica

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29, itens 44 e 45).
**Prioridade**: P1
**Onda**: 1
**concluida_em**: 2026-04-29
**Esforço real**: 1h
**Commit**: `c6cca64`

## Problema

CLAUDE.md tinha **640 linhas** misturando constituição técnica (regras invioláveis, schemas, workflow) com diário cronológico de sessões (~250 linhas de "Sessão 2026-04-XX -- ..."). Documento de contrato vivendo dois estados: regras estáveis + crônica móvel. Difícil de auditar e poluindo o foco.

`contexto/PROMPT_NOVA_SESSAO.md` apontava ordem de leitura desatualizada (HANDOFF_2026-04-27 como "último handoff"; auditoria 2026-04-29 ignorada).

## Hipótese

Separar em 3 documentos:
- **CLAUDE.md** (constituição enxuta, ~250 linhas): regras invioláveis + invariantes + workflow + schema XLSX + ADRs ativos + estrutura.
- **`docs/HISTORICO_SESSOES.md`**: diário cronológico extraído.
- **`contexto/ESTADO_ATUAL.md`** (gitignored): snapshot móvel com baseline real, sprints abertas, ordem de execução.

Atualizar `contexto/CONTEXTO.md` e `PROMPT_NOVA_SESSAO.md` para apontar para o plan ativo `pure-swinging-mitten` em vez da auditoria 2026-04-26.

## Implementação

1. Extrair sessões 2026-04-22 a 2026-04-29 para `docs/HISTORICO_SESSOES.md` (123 linhas).
2. Reescrever CLAUDE.md em 304 linhas: regras + armadilhas + identificação de arquivos + schema XLSX + categorização + dedup + detecção de pessoa + workflow + ADRs + estrutura + cobertura conhecida vs gaps.
3. Atualizar `contexto/CONTEXTO.md` (gitignored) com nova ordem de leitura (7 arquivos em vez de 6).
4. Atualizar `contexto/PROMPT_NOVA_SESSAO.md` (gitignored) com 7 perguntas-validação refletindo estado pós-redesign.

## Proof-of-work

- `wc -l CLAUDE.md` antes: 640 / depois: 304 (52% redução).
- `wc -l docs/HISTORICO_SESSOES.md`: 123 (conteúdo preservado).
- `make lint` exit 0 antes/depois.
- `make smoke` 8/8 antes / 10/10 depois (Sprint ANTI-MIGUE-04 cresceu para 10).
- `pytest` baseline 2.018 mantida.

## Acceptance atendido

- [x] CLAUDE.md ≤ 350 linhas focado em regras invioláveis + invariantes.
- [x] Histórico de sessões preservado em arquivo dedicado.
- [x] `contexto/CONTEXTO.md` aponta para plan pure-swinging-mitten.
- [x] `contexto/PROMPT_NOVA_SESSAO.md` referencia HISTORICO_SESSOES + plan novo.
- [x] Lint + smoke + pytest verdes.

## Achado colateral (zero TODO solto)

CLAUDE.md original tinha referências detalhadas a snapshots históricos das abas `dividas_ativas`, `inventario`, `prazos` (cabeçalho linha 1 + tabela de colunas). Conteúdo restaurado na revisão pré-push em forma resumida (tabelas compactas).
