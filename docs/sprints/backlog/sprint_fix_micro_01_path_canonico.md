---
id: FIX-MICRO-01-PATH-CANONICO
titulo: Sprint FIX-MICRO-01-PATH — Re-localizar módulo MICRO-01 (condicional)
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-29'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint FIX-MICRO-01-PATH — Re-localizar módulo MICRO-01 (condicional)

**Origem**: achado da terceira sessão de validação (DOC-VERDADE-01.F, 2026-04-29). Spec MICRO-01 propõe criar `src/transform/linking_micro.py`, mas linking canônico do projeto vive em `src/graph/linking.py` (Sprint 48). Inconsistência menor de spec.
**Prioridade**: P3 (condicional — só executa se grep confirmar que `src/graph/` é canônico)
**Onda**: 4 (cruzamento micro)
**Esforço estimado**: 30min (apenas mover + atualizar spec MICRO-01)
**Depende de**: decisão tomada pelo Opus que executar MICRO-01 (passo 4 da resposta do dono em 2026-04-29)

## Problema

Spec atual:
> sprint_micro_01_linking_micro_runtime.md propõe módulo em `src/transform/linking_micro.py`

Realidade:
> `src/graph/linking.py` existe e é o linking canônico (Sprint 48). Outros módulos de linking deveriam viver lá por convenção.

## Hipótese (a validar com grep antes de mexer)

Se `grep -rn "linking" src/graph/linking.py src/transform/ | head` mostrar que `src/graph/` é claramente o canônico (mais provável), o módulo da MICRO-01 deve ser criado em `src/graph/linking_micro.py`, não em `src/transform/`.

Se grep mostrar separação válida (transform = lógica de transformação de dados; graph = ingestão e arestas), pode ser intenção legítima da spec original.

## Implementação proposta (condicional)

**Caso A — grep confirma canônico em `src/graph/`**:

1. Editar `sprint_micro_01_linking_micro_runtime.md` substituindo `src/transform/linking_micro.py` por `src/graph/linking_micro.py` (e instâncias correlatas).
2. Adicionar nota na spec: "Path original era `src/transform/`; movido para `src/graph/` por consistência com linking canônico Sprint 48 — decisão tomada via FIX-MICRO-01-PATH 2026-04-29."
3. Esta sprint move-se imediatamente para `concluidos/` com frontmatter `concluida_em`.

**Caso B — grep mostra separação válida**:

1. Editar a spec MICRO-01 adicionando seção "Por que `src/transform/` e não `src/graph/`" justificando a separação.
2. Esta sprint move-se para `concluidos/` com nota "rejeitada — separação intencional".

## Acceptance criteria

- Spec MICRO-01 não-ambígua sobre localização do módulo.
- Decisão documentada com evidência grep no commit body desta sprint.
- Nenhum módulo criado em path errado por descuido.

## Proof-of-work

Output do grep canônico capturado em commit body. Spec MICRO-01 atualizada antes de qualquer execução.

---

## Papel do supervisor (Opus Claude Code)

Conforme ADR-13 e `docs/SUPERVISOR_OPUS.md`, eu (Opus principal nesta sessão interativa) executo:

1. `grep -rn "linking" src/graph/linking.py src/transform/ | head` para evidência empírica.
2. Decido entre Caso A e Caso B com base no grep.
3. Edit na spec MICRO-01 conforme decisão.
4. Commit com evidência grep no body.

Trivial — pode rodar in-process sem despachar subagent. **NÃO há chamada Anthropic API.**

## Gate anti-migué

9 checks padrão.
