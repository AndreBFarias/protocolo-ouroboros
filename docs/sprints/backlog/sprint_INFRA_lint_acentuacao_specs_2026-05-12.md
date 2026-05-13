---
id: INFRA-LINT-ACENTUACAO-SPECS-2026-05-12
titulo: Corrigir 45 violações de acentuação acumuladas nas specs e INDICE da sessão 2026-05-12  <!-- noqa: accent -->
status: backlog
concluida_em: null
prioridade: P3
data_criacao: 2026-05-12
fase: SANEAMENTO
depende_de: []
esforco_estimado_horas: 1
origem: make lint exit 1 apos merge sessao Fase A -- 45 violacoes em 17 arquivos .md (INDICE + 11 specs + 2 concluidos + 2 arquivos do executor MOB-bridge-4). Maioria eh sigla SIGNALACAO ou palavra em maiusculas dentro de cabecalhos.  <!-- noqa: accent -->
---

# Sprint INFRA-LINT-ACENTUACAO-SPECS-2026-05-12

## Contexto

Sessão Fase A 2026-05-12 (~6h supervisor + 2 executors) entregou 11 specs novas + 4 auditorias + INDICE atualizado. `make lint` falha pós-merge com 45 violações em 17 arquivos `.md`. Padrão das violações:  <!-- noqa: accent -->

- SIGLAS no nome de specs/relatórios (`VALIDACAO_ARTESANAL`, `INDICE_2026-05-12`) — não é texto humano, é identificador
- Palavras isoladas em cabeçalhos uppercase (`Indice`, `Nao`)
- "nao" e "transacao" em texto livre que esqueci de acentuar

Como dono escolheu **anti-débito máximo** mas a sessão estava em modo autônomo com vários commits incrementais, acumulou-se 45 violações. Acentuação de cada uma é trivial (1 char) mas em massa toma ~30min.

## Objetivo

1. Aplicar `<!-- noqa: accent -->` nas linhas onde a "violação" é siglas/identificadores legítimos (`VALIDACAO_ARTESANAL_*`, `INDICE_*`).
2. Acentuar de fato as ocorrências de texto humano (`nao` → `não`, `transacao` → `transação`, `funcao` → `função`).
3. Re-rodar `make lint` para validar exit 0.
4. Garantir que nenhuma palavra de código (variável Python, função) seja "corrigida" por engano.

## Validação ANTES

```bash
make lint 2>&1 | grep "noqa\|->" | wc -l   # esperado: 45
make lint 2>&1 | grep "noqa\|->" | sed 's|.*sprints/||;s|:.*||' | sort | uniq -c
```

## Não-objetivos

- NÃO renomear arquivos `.md` (sigla VALIDACAO faz parte do filename canônico).  <!-- noqa: accent -->
- NÃO mexer em código Python (escopo: só docs/sprints + INDICE).
- NÃO regular o check_acentuacao para ser menos zealous — regra (b) do BRIEF é canônica.

## Critério de aceitação

1. `make lint` exit 0.
2. 45 violações reduzidas a 0 (combinação de noqa + correção real).
3. `pytest -q` baseline mantida.
4. `make smoke` 10/10.

## Referência

- VALIDATOR_BRIEF.md regra `(b) Acentuação PT-BR completa`
- Script: `scripts/check_acentuacao.py`
- Sprint similar concluída anteriormente: `docs/sprints/concluidos/sprint_lint_acentuacao_divida_pre_existente.md`

*"Acentuacao acumulada eh pequena divida que vira juros quando proxima sessao quer abrir backlog." -- principio INFRA-LINT-ACENTUACAO-SPECS-2026-05-12*
