---
name: validar-arquivo
description: Use quando o dono digitar `/validar-arquivo` para EU (Opus principal nesta sessão Claude Code) abrir arquivo via Read multimodal e marcar coluna `valor_opus` no `data/output/validacao_arquivos.csv`. Sprint VALIDAÇÃO-CSV-01. Conforme ADR-13, NÃO é cron, NÃO é chamada Anthropic API -- sou eu lendo o arquivo + atualizando linha do CSV via script.
---

# Skill `/validar-arquivo`

## Quem executa

**EU.** Não é job automatizado. Não é API call paga. Sou o Opus principal da sessão Claude Code interativa, agindo como supervisor conforme ADR-13.

## Quando usar

- Dono pede "valida esses arquivos novos" ou "confere se o ETL pegou tudo".
- Após ETL processar lote de documentos -- linhas com `status_opus=pendente` no CSV esperam minha leitura multimodal.
- Antes de sessão humana de validação no dashboard -- coluna `valor_opus` ajuda o dono a comparar lado-a-lado.
- Após ramificação de uma sub-sprint da `RETRABALHO-EXTRATORES-01` -- valida cobertura de campos por extrator.

## Como invocar

O dono digita:

```
/validar-arquivo                           # listar pendencias do Opus
/validar-arquivo --resumo                  # dashboard agregado
/validar-arquivo --tipo holerite           # filtrar por tipo
/validar-arquivo --sha8 <X>                # ver linhas + abrir arquivo
```

Eu (Opus) executo internamente:

```bash
.venv/bin/python scripts/validar_arquivo.py --listar
.venv/bin/python scripts/validar_arquivo.py --sha8 <sha8> # me prepara
# leio o arquivo via Read tool
.venv/bin/python scripts/validar_arquivo.py --marcar \
    --sha8 <sha8> --campo <campo> --valor "<o que li>" --status ok
```

## O fluxo canônico que sigo

1. Listar pendências (`--listar`) -- escolho um sha8 alvo.
2. Inspecionar metadata (`--sha8 X`) -- pego `caminho_relativo` e lista de campos.
3. Abrir arquivo via **Read multimodal** sobre o caminho retornado.
4. Para cada campo, comparo `valor_etl` com o que leio:
   - Bate exatamente: marco `--status ok` com mesmo `--valor`.
   - Diverge mas eu leio valor diferente: marco `--status erro` com meu valor.
   - Campo deveria existir mas não consigo ler: marco `--status lacuna`.
5. Se descubro **campos NÃO listados** que existem no arquivo: registro achado em `docs/auditorias/cobertura_extracao_<data>.md` (Sprint META-COBERTURA-TOTAL-01) e/ou abro sprint-filha `sprint_retrabalho_<extrator>.md` (Sprint RETRABALHO-EXTRATORES-01).

## Saídas que produzo

- Atualização da coluna `valor_opus` + `status_opus` no CSV.
- Conversa com dono apontando 2-3 achados notáveis (campos com erro recorrente, lacunas).
- Eventuais sprints-filhas de retrabalho.

## Distinção vs `/auditar-cobertura-total`

| Skill | Foco | Granularidade |
|---|---|---|
| `/auditar-cobertura-total` | Visão estatística (lint + grafo + lista extratores) | Por extrator |
| `/validar-arquivo` | Leitura concreta de arquivo individual | Por (arquivo, campo) |

Coexistem por design.

## Referências

- Sprint VALIDAÇÃO-CSV-01 (`docs/sprints/concluidos/sprint_validacao_csv_01_*.md` quando fechada).
- Pedido literal do dono em 2026-04-29: "vamos marcando num csv da vida pra verificar se o pdf, xsx, csx, imagem e os valores extraidos estão certos".
- Sprint META-COBERTURA-TOTAL-01 (sprint irmã, lint estático).
- Sprint RETRABALHO-EXTRATORES-01 (consome o CSV).
- ADR-13 (sem chamada Anthropic API: Opus = Claude Code interativo).
