---
name: auditar-cobertura-total
description: Use quando o dono digitar `/auditar-cobertura-total` (com ou sem `--executar`) para EU (Opus principal nesta sessão Claude Code) gerar relatório de cobertura D7 -- "extrair tudo, catalogar tudo". Sprint META-COBERTURA-TOTAL-01. Conforme ADR-13, NÃO é cron, NÃO é chamada Anthropic API -- sou eu rodando o script + lendo o output + decidindo próximas ações.
---

# Skill `/auditar-cobertura-total`

## Quem executa

**EU.** Não é job automatizado. Não é API call paga. Sou o Opus principal da sessão Claude Code interativa, agindo como supervisor conforme ADR-13.

## Quando usar

- Dono pergunta "extratores estão pegando tudo?" ou "tem extrator silenciando falha?".
- Após N sprints fechadas (ex: a cada 5) -- detecção de regressão silenciosa.
- Antes de iniciar Sprint RETRABALHO-EXTRATORES-01 -- relatório alimenta a triagem em tiers A/B/C/D.
- Após `--reextrair-tudo` -- ver se cobertura cresceu.
- Periódico, à discrição do dono. Sem cron.

## Como invocar

O dono digita:

```
/auditar-cobertura-total              # dry-run, só sumário no terminal
/auditar-cobertura-total --executar   # grava docs/auditorias/cobertura_total_<data>.md
```

Eu (Opus) executo:

```bash
.venv/bin/python scripts/auditar_cobertura_total.py [--executar]
```

## Distinção vs `/auditar-cobertura` (Sprint LLM-04-V2)

| Skill | Pergunta operacional | Foco |
|---|---|---|
| `/auditar-cobertura` | "como está a cobertura de **categorias**?" | Categorização (regras YAML × fornecedores) |
| `/auditar-cobertura-total` | "como está a cobertura de **extração**?" | Extratores (D7: extrair tudo dos arquivos) |

Coexistem por design (decisão D2 do plan glittery-munching-russell, replicada para skills). Não fundir sem revisão explícita do dono.

## O que faço depois de gerar

1. **Leio o relatório eu mesmo** (Read tool sobre `docs/auditorias/cobertura_total_<data>.md`).
2. **Apresento achados ao dono** em linguagem natural -- destaque para extratores com violação no lint estático e tipos de documento com baixa cobertura no grafo.
3. **Para cada extrator suspeito**:
   - Se já existe sprint-filha em `docs/sprints/backlog/sprint_retrabalho_<extrator>.md`, lembro o status.
   - Se não existe, ofereço criar via Sprint RETRABALHO-EXTRATORES-01 (ramificar).
4. **Comparo com auditoria anterior** (se houver `cobertura_total_*.md` mais antigo): aponto progressões e regressões.
5. **Não decido sozinho** -- ao final, listo propostas para o dono ratificar.

## Saídas que produzo

- Arquivo `docs/auditorias/cobertura_total_<YYYY-MM-DD>.md` (apêndice, leniente -- nunca mutua código).
- Sumário no terminal: "X extratores | Y violacoes | Z tipos no grafo".
- Conversa subsequente proposta ao dono.

## Referências

- Sprint META-COBERTURA-TOTAL-01 (`docs/sprints/concluidos/` quando fechada).
- Decisão D7 em `~/.claude/plans/glittery-munching-russell.md`.
- Sprint guarda-chuva RETRABALHO-EXTRATORES-01 (consome este relatório).
- ADR-13 (sem chamada Anthropic API: Opus = Claude Code interativo).
