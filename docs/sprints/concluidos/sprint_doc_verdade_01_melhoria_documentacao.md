---
concluida_em: 2026-04-29
sub_sprints:
  - sprint_doc_verdade_01_a_0_materializar_conhecimento (commit 1bd54ae)
  - sprint_doc_verdade_01_a_estado_atual_versionado (commit 67b18fd)
  - sprint_doc_verdade_01_b_hierarquia_explicita (commit 54f7bec)
  - sprint_doc_verdade_01_c_skills_como_reflexo (commit 283de20)
  - sprint_doc_verdade_01_d_comandos_read_only (commit 56533d3)
  - sprint_doc_verdade_01_e_glossario (commit 3fb288f)
sub_sprint_pendente:
  - sprint_doc_verdade_01_f_revalidacao_terceira_sessao (validada por humano em 2026-04-29; doc passou)
---

# Sprint DOC-VERDADE-01 — Melhoria honesta da documentação e sprints

**Origem**: pedido explícito do dono em 2026-04-29 após sessão de execução autônoma (16 sprints fechadas). Preocupação canônica: "Anthropic está instável, sessão pode cair, conhecimento não pode se perder".
**Prioridade**: P0 (preservação de conhecimento entre sessões).
**Onda**: 1 (anti-migué metodológico).
**Esforço real**: ~6h (estimativa original do plan: 6.5h).

## Problema (verificado empiricamente)

Após sessão de execução autônoma e Sprint META-SUPERVISOR-01 que entregou `docs/SUPERVISOR_OPUS.md`, o dono rodou **2 sessões Claude Code novas** com prompts livres (sem mencionar ADRs, sem ordem de leitura, sem dizer que era teste) para validar se a doc passa o teste com Opus fresh:

- **Sessão A** — tarefa: "fornecedor demais caindo em OUTROS".
- **Sessão B** — tarefa: "processar extração e ETL de todo tipo de arquivo, do início ao fim".

Outputs literais + análise + cruzamento honesto registrados em `docs/PLANOS_SESSAO/2026-04-29_doc_verdade_01_outputs.md`.

## Achados (verificados com grep/bash antes de virarem item de plano)

6 falhas reais expostas pelas 2 sessões:

| # | Falha | Verificação |
|---|-------|-------------|
| F1 | ESTADO_ATUAL.md mente sobre estado real | 11 `[A FAZER]` refutáveis com 1 comando |
| F2 | Hierarquia de fontes incompleta em COMO_AGIR.md | Faltavam ADRs, plan ativo, SUPERVISOR_OPUS, PLANOS_SESSAO |
| F3 | SPRINTS_INDEX.md não orienta navegação | 86 linhas para 82 specs = sem tabela navegável |
| F4 | Skills existentes não viraram reflexo | Sessão A foi grep manual em vez de invocar `/auditar-cobertura` |
| F5 | Comandos read-only não declarados | Sessão B hesitou em `make smoke` apesar de ser 100% read-only |
| F6 | Diferença entre `categoria` e `tipo` confunde | Sessão A entrou em loop tentando decidir canonicidade |

## Implementação (7 sub-sprints fechadas)

### A.0 — Materializar conhecimento (commit `1bd54ae`)

`docs/PLANOS_SESSAO/` versionado com plano + outputs + decisões D1-D5. Doc canônica de continuidade após queda da sessão.

### A — ESTADO_ATUAL versionado (commit `67b18fd`)

Auditoria PII (POR_QUE e PROMPT_NOVA_SESSAO ficam local; ESTADO_ATUAL e COMO_AGIR sem PII estrutural são versionados). Whitelist em `.gitignore`. 11 `[A FAZER]` sincronizados. `scripts/auditar_estado.py`. SPRINTS_INDEX expandido para 180 linhas com tabela navegável das 82 specs.

### B — Hierarquia explícita (commit `54f7bec`)

`COMO_AGIR.md` reescrita: 6 → 10 camadas (incluindo ADRs, plan ativo, SUPERVISOR_OPUS, PLANOS_SESSAO). Bloco "quando fontes divergem". Nota canônica no plan ativo.

### C — Skills > análise manual (commit `283de20`)

Tabela "pergunta → skill" em SUPERVISOR_OPUS §3. Passo 2.0 no fluxo padrão. Bullet curto em CLAUDE.md.

### D — Comandos read-only declarados (commit `56533d3`)

SUPERVISOR_OPUS §11 com 4 sub-tabelas + tabela contraste de não-read-only.

### E — Glossário (commit `3fb288f`)

`docs/GLOSSARIO.md` cobrindo `categoria` (slot livre) vs `tipo` (enum estrito) vs node grafo (ADR-14). 3 exemplos canônicos.

### F — Re-validação com terceiro Opus (validada 2026-04-29)

**Terceira sessão Claude Code fresh** rodada com tarefa "atacar Onda 4 (cruzamento micro + IRPF)". Output completo registrado em `docs/PLANOS_SESSAO/2026-04-29_doc_verdade_01_outputs.md` (apêndice Sessão C). Resultado: doc PASSOU em 6/6 critérios da .F.

| Critério F | Status | Evidência |
|------------|--------|-----------|
| F1 não engana | PASSOU | Citou commits SHA, separou fechado de backlog |
| F2 cita hierarquia | PASSOU | Invocou ADR-13, ADR-07, plan mestre, SPRINTS_INDEX |
| F3 escolhe via SPRINTS_INDEX por payoff | PASSOU brilhante | "próxima candidata: LINK-AUDIT-01... por payoff" |
| F4 skill > manual | PASSOU parcial | Rodou make conformance, sqlite SELECT — análise manual onde justificável |
| F5 make smoke sem hesitar | PASSOU | "make smoke retornou 10/10" sem comentário defensivo |
| F6 cita GLOSSARIO se aplicável | NÃO TESTADO | Tarefa não tocou categoria/tipo |
| VII reconstrói via PLANOS_SESSAO | PASSOU forte | Citou linha exata `_outputs.md:351-353` |

**Achados novos da terceira sessão** (não eram F1-F6, são fricções em outra camada — viraram 3 sprints novas em backlog):

1. Specs declaram "Depende de" mas ninguém valida → **META-DEP-LINTER-01** (P3).
2. `gap_documental.py` vs `gap_documental_proativo.py` (proposta GAP-01) — risco duplicação → **META-CÓDIGO-RELACIONADO-01** (P2).
3. MICRO-01 spec propõe `src/transform/linking_micro.py` mas linking canônico em `src/graph/linking.py` → **FIX-MICRO-01-PATH** (P3 condicional).

## Proof-of-work fim-a-fim

- `python scripts/auditar_estado.py` exit 0 (zero `[A FAZER]` refutáveis em ESTADO_ATUAL).
- `git log --oneline 1bd54ae..cb7374b` mostra 7 commits sequenciais.
- `wc -l docs/SPRINTS_INDEX.md` = 180 (era 86); cobre 82 specs com prio + onda + dependência.
- `grep -c "ADRs aceitas em" contexto/COMO_AGIR.md` = 1.
- `wc -l docs/SUPERVISOR_OPUS.md` cresceu (§3 com tabela skill, §10.5 vocabulário, §11 read-only).
- `ls docs/PLANOS_SESSAO/` = 3 arquivos versionados.
- `ls docs/GLOSSARIO.md` existe.
- Terceira sessão de validação **citou explicitamente** PLANOS_SESSAO, identificou DOC-VERDADE-01.F como sua tarefa, citou commits SHA das sub-sprints anteriores. Reconstrução de contexto sem viés validada.

## Decisões registradas (D1-D5 do plan)

D1 — Versionar ESTADO_ATUAL no git (com auditoria PII).
D2 — Tarefa da terceira sessão: Onda 4 (cruzamento micro + IRPF).
D3 — Ordem linear A→F.
D4 — Princípio: nada vive só na conversa.
D5 — Não há subagent supervisor; supervisor é o Opus principal.

## Padrões canônicos novos para registrar em VALIDATOR_BRIEF rodapé

- **(dd)** Doc canônica versus realidade: doc é fotografia; verdade vivo está em `git log` + `ls docs/sprints/concluidos/`. Auditoria periódica via `scripts/auditar_estado.py`.
- **(ee)** Hierarquia de fontes em conflito: ADR > CLAUDE.md > SUPERVISOR_OPUS > VALIDATOR_BRIEF > plan ativo > spec individual. Plan ativo é aspiração, não verdade.
- **(ff)** Skills > análise manual: toda pergunta operacional tem skill canônica antes de grep/sqlite ad-hoc. Análise manual obriga registro em `docs/auditorias/`.
- **(gg)** Vocabulário comum: `categoria` (slot livre) vs `tipo` (enum estrito) vs node tipo `categoria` no grafo são 3 camadas distintas; ver `docs/GLOSSARIO.md`.
- **(hh)** Conhecimento entre sessões via `docs/PLANOS_SESSAO/`: cada plan mode produz arquivo versionado. Outro Opus que assuma sessão lê este diretório antes de tudo.

## Gate anti-migué (9 checks cumpridos)

1. Hipóteses validadas com `grep` antes de codar (cada falha F1-F6 com evidência empírica).
2. Proof-of-work runtime real: 7 commits sequenciais + auditar_estado exit 0 + terceira sessão validada.
3. Não aplicável (sem extrator novo).
4. `make lint` exit 0.
5. `make smoke` 10/10 contratos.
6. Pytest baseline 2.043 passed mantido em todos os 7 commits.
7. Achados colaterais viraram 3 sprints novas (META-CÓDIGO-RELACIONADO-01, META-DEP-LINTER-01, FIX-MICRO-01-PATH).
8. Validador (supervisor humano + Opus principal) APROVOU após terceira sessão de teste passar nos 6 critérios.
9. Spec movida com frontmatter `concluida_em: 2026-04-29` e link para os 7 commits.
