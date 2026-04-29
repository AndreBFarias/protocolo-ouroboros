# Auditorias de cobertura

Relatórios de cobertura do grafo e categorização gerados via skill `/auditar-cobertura`.

## Quem gera

**O Opus principal (Claude Code interativo)** — eu — quando o dono pede na sessão. Não é cron, não é automação programática. Conforme ADR-13, sou o supervisor; cada arquivo aqui é fruto de uma sessão de trabalho interativa.

## Convenção de nome

`cobertura_<periodo>.md` onde `<periodo>` pode ser:
- Data ISO completa (`2026-04-29`) quando é auditoria de "agora".
- Mês (`2026-04`) quando é foco mensal.
- Ano (`2026`) quando é foco anual.

## O que cada relatório contém

- Sumário executivo: total de transações, % categorizado, % em `OUTROS`, documentos órfãos.
- Distribuição das 20 maiores categorias.
- Top 15 fornecedores em `OUTROS` — candidatos a regra nova.
- Cobertura por pessoa (André / Vitória / Casal).
- Próximos passos sugeridos pelo supervisor (eu).

## Por que manter histórico

Comparar relatórios sucessivos mostra a tendência da autossuficiência (ADR-09): quanto mais regras YAML cobrirem o cotidiano, menor o `OUTROS%`. Meta: convergir para `OUTROS%` < 5% em todas as pessoas.

## Não delete arquivos antigos

Mesmo após resolver os gaps apontados, mantenha o histórico. Custo de armazenamento é zero, valor de auditabilidade cresce com o tempo.
