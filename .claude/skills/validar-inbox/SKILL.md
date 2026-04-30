---
name: validar-inbox
description: Use quando o dono digitar `/validar-inbox` para EU (Opus principal nesta sessão Claude Code) iterar pendências do `data/output/validacao_arquivos.csv` em batch. Wrapper sobre `/validar-arquivo` -- pré-filtra pendências por tipo/mês/divergência e agrupa por sha8 (1 arquivo = N campos), facilitando leitura sequencial. Sprint VALIDAR-BATCH-01. Conforme ADR-13, NÃO é cron, NÃO é chamada Anthropic API -- sou eu lendo arquivos via Read multimodal e atualizando linhas via script.
---

# Skill `/validar-inbox`

## Quem executa

**EU.** Não é job automatizado. Não é API call paga. Sou o Opus principal da sessão Claude Code interativa, agindo como supervisor conforme ADR-13.

## Quando usar

- Dono diz "tem muito arquivo no inbox para validar" ou "valida tudo que joguei essa semana".
- Após ETL processar lote grande (10+ documentos novos via `./run.sh --tudo` ou `--full-cycle`).
- Temporada IRPF (janeiro/fevereiro), 40-60 documentos novos por mês.
- Após sprint nova de extrator -- valida cobertura inicial em batch.

## Como invocar

O dono digita:

```
/validar-inbox                                # listar todas pendencias (limite 50)
/validar-inbox --tipo nfce_modelo_65          # filtrar por tipo
/validar-inbox --mes 2026-04                  # filtrar por mes
/validar-inbox --apenas-divergentes           # priorizar onde humano discorda do ETL
/validar-inbox --limite 10                    # primeiros 10 apenas
```

Eu (Opus) executo internamente:

```bash
.venv/bin/python scripts/validar_inbox.py [--tipo X] [--mes YYYY-MM] [--apenas-divergentes] [--limite N]
```

O script imprime metadata de cada arquivo pendente. Para cada um, eu:

1. Anoto o `sha8` e a lista de `campos pendentes`.
2. Chamo `/validar-arquivo --sha8 <X>` (skill irmã) para abrir o arquivo via Read multimodal.
3. Para cada campo, comparo `valor_etl` com o que leio e marco com `--marcar`.
4. Sigo para o próximo arquivo.

## Variante implementada: A (interativo, seguro)

A spec lista 2 variantes (interativo vs auto-batch). A implementação atual é **interativa**:

- Imprime metadata de cada arquivo.
- Espera EU chamar `/validar-arquivo --sha8 X` para cada um.
- Não processa em lote automaticamente.

Justificativa: D7 prefere visibilidade humana sobre velocidade. Auto-batch (Variante B) requer confiança de leitura 100% sem checkpoint humano -- inseguro para dados financeiros.

Para ativar Variante B no futuro: spec `VALIDAR-BATCH-02` (não-criada ainda).

## Filtros úteis por contexto

| Contexto | Comando sugerido |
|---|---|
| Validação inicial após ETL grande | `/validar-inbox --limite 10` (1 lote por vez) |
| Foco em tipo específico | `/validar-inbox --tipo holerite_g4f` |
| Revisão mensal | `/validar-inbox --mes 2026-04` |
| Resolver discrepâncias humano vs ETL | `/validar-inbox --apenas-divergentes` |

## Achado durante validação batch

Se EU descubro **padrão de erro recorrente** durante validação (ex: 5 NFCe seguidas têm campo `cnpj_emitente` extraído errado da mesma forma):

1. Marco cada um normalmente via `/validar-arquivo --marcar`.
2. Abro sprint-filha `sprint_retrabalho_<extrator>.md` em `docs/sprints/backlog/` (Sprint RETRABALHO-EXTRATORES-01 prevê isso).
3. Não corrijo extrator inline -- escopo creep.

## Fluxo recomendado por sessão

```
1. /validar-inbox --limite 5         # ver primeiros 5
2. Para cada arquivo:
   /validar-arquivo --sha8 <X>       # abre arquivo, mostra campos
   Read tool sobre o caminho retornado
   /validar-arquivo --marcar ...     # marca cada campo
3. /validar-inbox --apenas-divergentes  # foco em divergencias
4. Repete ate fila esvaziar.
```

## Coexistência

- Complementa (não substitui) `/validar-arquivo` -- batch é wrapper, não fork.
- Reusa `src/load/validacao_csv.py` -- nenhuma infra nova, nenhum schema novo.
- Compatível com aba "Validação por Arquivo" do dashboard (Sprint VALIDAÇÃO-CSV-01).
