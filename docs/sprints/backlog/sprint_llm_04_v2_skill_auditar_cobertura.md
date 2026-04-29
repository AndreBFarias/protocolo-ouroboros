# Sprint LLM-04-V2 — Skill /auditar-cobertura (substitui auditor LLM programático)

**Origem**: REVISAO-LLM-ONDA-01 (reescrita sob ADR-13).
**Substitui**: sprint_llm_04_supervisor_modo_auditor + sprint_auditor_01_relatorio_cobertura_documental_por_pessoa (ambas arquivadas).
**Prioridade**: P1
**Onda**: 2
**Esforço estimado**: 2h
**Depende de**: LLM-01-V2

## Problema

ADR-08 prevê auditor LLM Modo 2 (relatório quinzenal). ADR-13 proíbe automação programática Anthropic. Falta caminho manual disparado pelo supervisor.

## Hipótese

Skill `/auditar-cobertura [--periodo <mes>]` em `.claude/skills/`: Opus lê `data/output/grafo.sqlite`, compara com `mappings/categorias.yaml`, gera `docs/auditorias/cobertura_<periodo>.md` com:
- % nodes documento sem categoria.
- % transações com `categoria=Outros`.
- Top 10 fornecedores sem regra.
- % cobertura por pessoa (André/Vitória/Casal).

## Implementação proposta

1. `.claude/skills/auditar-cobertura.md` declarando comando + parâmetros.
2. Lógica em `scripts/auditar_cobertura.py` (chamável standalone).
3. Skill = wrapper que chama o script.

## Acceptance criteria

- Skill funcional.
- Relatório gerado em runtime real.
- Frequência discrição do dono (não cron automático — ADR-13).

## Gate anti-migué

9 checks padrão.
