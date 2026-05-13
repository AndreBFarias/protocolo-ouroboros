---
id: META-CODIGO-RELACIONADO-01-TEMPLATE-SPEC
titulo: Sprint META-CODIGO-RELACIONADO-01 — Campo "código relacionado já no repo"
  no template de spec
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-29'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint META-CODIGO-RELACIONADO-01 — Campo "código relacionado já no repo" no template de spec

**Origem**: achado da terceira sessão de validação (DOC-VERDADE-01.F, 2026-04-29). Spec GAP-01 propõe `src/analysis/gap_documental_proativo.py` paralelo a `src/analysis/gap_documental.py` (Sprint 75) sem que a spec mencione a coexistência. Risco real: outro Opus pode criar duplicação por descuido.
**Prioridade**: P2
**Onda**: 1 (anti-migué metodológico)
**Esforço estimado**: 2h
**Depende de**: nenhuma

## Problema

Specs declaram "criar `src/X/Y.py`" sem cruzar com `src/X/` existente. Se houver módulo de domínio próximo (ex: `gap_documental.py` vs `gap_documental_proativo.py`), o Opus que executar a sprint pode:
- Criar o paralelo cego (gera duplicação real).
- Estender o existente cego (viola contrato declarado da spec).
- Pausar para perguntar (custo de turno).

Hoje só descobre a sobreposição via grep manual — frágil, depende de Opus se lembrar de checar.

## Hipótese

Adicionar campo obrigatório no template de spec **"Código relacionado já no repo"** que liste módulos com domínio próximo (mesmo prefixo, mesma pasta, palavras-chave compartilhadas) + 1 frase explicando relação. Quem redige a spec faz `grep` antes; quem executa lê e age informado.

## Implementação proposta

1. Editar `docs/propostas/_template.md` (Sprint LLM-01-V2) adicionando bloco `## Código relacionado já no repo` no corpo padrão.
2. Atualizar `docs/sprints/backlog/sprint_gap_01_alerta_proativo_transacao_sem_nf.md` retroativamente com a relação `gap_documental.py` ↔ `gap_documental_proativo.py` (delimitar escopo de cada um). Esta é a M1 da DOC-VERDADE-01 que motivou esta sprint.
3. Criar checklist em `docs/SUPERVISOR_OPUS.md §2` (fluxo padrão): "Antes de criar módulo novo em src/, rode `ls src/<pasta>/ | grep <prefixo>` + `grep -rln <palavra-chave> src/` para confirmar não-duplicação."
4. Audit retroativo das 82 specs em `docs/sprints/backlog/`: identificar quais propõem módulo cujo nome tem prefixo/palavra-chave compartilhada com algo já em `src/`. Resultado vira `docs/auditorias/codigo_relacionado_<data>.md`.

## Acceptance criteria

- Template de proposta atualizado com bloco "Código relacionado".
- Spec GAP-01 com seção "Relação com gap_documental.py" pré-execução.
- Checklist em SUPERVISOR_OPUS.md §2.
- Audit retroativo gerado e revisado.

## Proof-of-work

`grep -c "Código relacionado" docs/propostas/_template.md` retorna >= 1. Spec GAP-01 não-ambígua para Opus que executar.

---

## Papel do supervisor (Opus Claude Code)

Conforme ADR-13 e `docs/SUPERVISOR_OPUS.md`, eu (Opus principal nesta sessão interativa) executo esta sprint metodológica:

1. Edit no template `docs/propostas/_template.md` adicionando bloco.
2. Edit retroativo na spec GAP-01.
3. Edit em SUPERVISOR_OPUS.md §2.
4. Audit das 82 specs via grep + ls cruzado com `src/`.
5. Relatório em `docs/auditorias/codigo_relacionado_<data>.md`.

**NÃO há chamada Anthropic API. NÃO há cliente Python `anthropic`.** Regra inviolável (ADR-13).

## Gate anti-migué

9 checks padrão.
