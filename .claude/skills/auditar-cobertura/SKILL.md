---
name: auditar-cobertura
description: Use quando o dono digitar `/auditar-cobertura` (com ou sem `--periodo YYYY-MM`) para que EU (Opus principal nesta sessão Claude Code) gere relatório manual de cobertura do grafo. Substitui o auditor LLM Modo 2 do ADR-08. Conforme ADR-13, NÃO é cron, NÃO é chamada Anthropic API — sou eu rodando o script + lendo o output + conversando com o dono.
---

# Skill `/auditar-cobertura`

## Quem executa

**EU.** Não é um job automatizado. Não é uma API call paga. Sou o Opus principal da sessão Claude Code interativa atual, agindo como supervisor conforme ADR-13. O dono digita o slash command e eu rodo o script + leio o relatório + converso sobre achados.

## Quando usar

- Dono pergunta "como está a cobertura?" ou "quais fornecedores ainda não têm regra?".
- Antes de planejar Onda 3 (extratores novos) — saber onde estão os gaps.
- Após uma rodada de `--reextrair-tudo` — ver se as regras novas pegaram.
- Periódico, à discrição do dono (ex: mensal). Sem cron.

## Como invocar

O dono digita:

```
/auditar-cobertura                    # data de hoje
/auditar-cobertura --periodo 2026-04  # mês específico
```

Eu (Opus) executo:

```bash
python scripts/auditar_cobertura.py --periodo <período> --executar
```

Resultado: arquivo gerado em `docs/auditorias/cobertura_<periodo>.md` com:
- Sumário executivo (total, % categorizado, % em OUTROS, documentos órfãos).
- Distribuição de categorias (top 20).
- Top 15 fornecedores em OUTROS — candidatos a regra nova em `mappings/categorias.yaml`.
- Cobertura por pessoa (André / Vitória / Casal).
- Próximos passos sugeridos.

## O que faço depois de gerar

1. **Leio o relatório eu mesmo** (Read tool sobre o `.md`).
2. **Apresento os achados ao dono** em linguagem natural — destaque para os 3-5 fornecedores com maior payoff.
3. **Para cada candidato**, ofereço caminho:
   - Criar regra em `mappings/categorias.yaml` via Edit (eu faço, dono aprova).
   - Criar proposta formal via skill `/propor-extrator` quando o problema é falta de extrator.
   - Aceitar como `OUTROS` legítimo (transferências internas, casos isolados).
4. **Não decido sozinho** — ao final, lista de propostas para o dono ratificar.

## Achado-bloqueio

- Se `data/output/grafo.sqlite` ausente: o relatório vai dizer "Grafo ausente" e EU peço ao dono para rodar `./run.sh --tudo` antes de continuar.
- Se baseline pytest cair após sugestão minha: REPROVO automaticamente e refaço.

## Referências

- `scripts/auditar_cobertura.py` — implementação.
- `docs/sprints/concluidos/sprint_llm_04_v2_skill_auditar_cobertura.md` — spec original.
- ADR-13: por que sou Opus interativo, não API.
- ADR-08: por que existe o conceito de auditor (Modo 2).
- Skill `/propor-extrator` (Sprint LLM-02-V2) — caminho complementar quando falta extrator.
