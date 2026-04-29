---
concluida_em: 2026-04-28
---

# Sprint LLM-04-V2 — Skill /auditar-cobertura (substitui auditor LLM programático)

**Origem**: REVISAO-LLM-ONDA-01 (reescrita sob ADR-13).
**Substitui**: sprint_llm_04_supervisor_modo_auditor + sprint_auditor_01_relatorio_cobertura_documental_por_pessoa (ambas arquivadas).
**Prioridade**: P1
**Onda**: 2
**Esforço estimado**: 2h
**Depende de**: LLM-01-V2

## Problema

ADR-08 prevê auditor LLM Modo 2 (relatório quinzenal). ADR-13 declara que **NÃO HÁ LLM PROGRAMÁTICO** — eu (Opus principal, Claude Code interativo via assinatura Claude Max) sou o supervisor. Falta caminho manual onde o dono pede a auditoria e EU executo na sessão.

## Hipótese

Skill `/auditar-cobertura [--periodo <YYYY-MM>]` em `.claude/skills/auditar-cobertura/SKILL.md`. Quando o dono digita o slash command, **EU (Opus principal nesta sessão)** rodo `scripts/auditar_cobertura.py` que lê `data/output/grafo.sqlite` + `mappings/categorias.yaml` e gera `docs/auditorias/cobertura_<periodo>.md` com:
- % nodes documento sem categoria.
- % transações com `categoria=Outros`.
- Top 10 fornecedores sem regra.
- % cobertura por pessoa (André/Vitória/Casal).

Em seguida, EU leio o relatório e converso com o dono sobre achados — proponho regras novas via skill `/propor-extrator` ou edição direta de `mappings/categorias.yaml`. Sem cron, sem automação programática, sem chamada Anthropic API. Frequência = quando o dono pedir.

## Implementação proposta

1. `.claude/skills/auditar-cobertura/SKILL.md` — frontmatter + descrição do meu papel + comando bash exato que executo.
2. `scripts/auditar_cobertura.py` — lógica Python pura, lê SQLite + YAML, escreve relatório Markdown. Sem dependência de LLM.
3. `docs/auditorias/` — diretório novo, README explicando que cada arquivo lá foi gerado por mim em sessão interativa quando o dono pediu.

## Acceptance criteria

- Skill publicada em `.claude/skills/`.
- Script funcional com argparse + dry-run + `--executar`.
- Relatório real gerado em runtime contra grafo de produção atual.
- README em `docs/auditorias/` deixando explícito que sou EU (Opus interativo) que rodo, não cron.

## Gate anti-migué

9 checks padrão.
