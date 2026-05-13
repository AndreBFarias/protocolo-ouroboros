---
id: SUBAGENTE-EXTRACAO-01-PARALELIZACAO-FROZEN
titulo: Sprint SUBAGENTE-EXTRACAO-01 -- Paralelização agentic (FROZEN, P3)
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-29'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint SUBAGENTE-EXTRACAO-01 -- Paralelização agentic (FROZEN, P3)

> **Slug ASCII para referência cruzada**: `subagente_extracao_01`. Em texto livre, usar "SUBAGENTE-EXTRACAO-01".
>
> **STATUS**: FROZEN -- não-fazer sem volume justificativo. Spec existe para registrar a ideia, não para execução imediata.

**Origem**: prompt complementar do dono em 2026-04-29 (Gap 5 da sequência D7-extendida).
**Prioridade**: P3.
**Onda**: backlog frio.
**Esforço estimado**: ~10h (estimativa preliminar; refinar quando descongelar).
**Depende de**: AGENTIC-FALLBACK-01 + VALIDAR-BATCH-01 + volume mensurável (≥50 arquivos pendentes).

## Critério de despertar

**ABRIR esta sprint somente se**:

1. `data/inbox/` tem ≥50 arquivos por ≥7 dias consecutivos, OU
2. `data/output/validacao_arquivos.csv` tem ≥100 linhas com `status_opus=pendente` por ≥7 dias, OU
3. Dono mede tempo gasto em validação manual em 1 sessão e excede 2h consecutivas (gargalo real).

Antes desses critérios: NÃO mexer. Fazer paralelização sem volume = optimization premature; ADR-09 sugere que pipeline determinístico cresce e reduz necessidade de processamento agentic em massa naturalmente.

## Hipótese (a validar quando descongelar)

Quando validação agentic vira gargalo, despachar `Agent` tool com subagentes para processar fila em paralelo. Cada subagente: lê 1 arquivo, marca campos no CSV, retorna sumário.

**Restrição absoluta (ADR-13)**: subagentes são instâncias do mesmo Opus interativo, NÃO chamadas a SDK Anthropic. Limite natural: número de subagentes simultâneos suportados pelo Claude Code (~3-10).

## Esboço de implementação (rascunho, não-final)

- Wrapper sobre `validar_inbox.py` que despacha N subagentes em paralelo.
- Cada subagente: prompt mínimo com `caminho_arquivo` + `campos_esperados` + invocação `validar_arquivo.py --marcar`.
- Reduzir contexto: cada subagente lê APENAS o arquivo dele, não a sessão inteira.
- Reportar agregado quando todos terminam.

## Não-objetivos

- **Não fazer**: agora.
- **Não fazer**: criar enquanto AGENTIC-FALLBACK-01 e VALIDAR-BATCH-01 não estiverem em produção.
- **Não fazer**: confundir "subagente" com "API call paralela" -- são instâncias do Opus interativo.
- **Não fazer**: otimizar processo que ainda não existe em produção.

## Quando promover

Mover de `backlog/` para `sprints_ativas/` apenas após dono confirmar que critério de despertar foi atingido E que VALIDAR-BATCH-01 está rodando há ≥30 dias com volume.

---

*"Premature optimization is the root of all evil." -- Knuth. Vale para paralelização de agentes também.*
