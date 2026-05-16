---
id: META-DOC-ROADMAP-PATH-SPRINT-AUTO-MOVE
titulo: Atualizar referência ao `sprint_auto_move.py` em `docs/ROADMAP.md`
status: backlog
concluida_em: null
prioridade: P3
data_criacao: 2026-05-15
fase: SANEAMENTO
epico: 8
depende_de: []
esforco_estimado_horas: 0.1
origem: achado colateral da sprint META-HOOKS-AUDITAR-E-WIRAR (executor `af13dd9f`, 2026-05-15). Doc `docs/ROADMAP.md:430` referencia `hooks/sprint_auto_move.py` mas o script foi movido para `scripts/sprint_auto_move.py` (não era hook, era utilitário).
---

# Sprint META-DOC-ROADMAP-PATH-SPRINT-AUTO-MOVE

## Contexto

Edit-pronto, ~5min. Substituir referência ao path antigo em 1 arquivo de documentação após a sprint META-HOOKS-AUDITAR-E-WIRAR mover o script.

## Hipótese e validação ANTES

```bash
grep -n "hooks/sprint_auto_move" docs/ROADMAP.md
# Esperado: 1 hit na linha ~430
```

## Objetivo

Edit em `docs/ROADMAP.md` linha ~430: trocar `hooks/sprint_auto_move.py` por `scripts/sprint_auto_move.py`.

## Não-objetivos

- Não atualizar outras referências a paths antigos (foco neste).
- Não tocar outros arquivos de doc.

## Proof-of-work runtime-real

```bash
grep -n "hooks/sprint_auto_move" docs/ROADMAP.md
# Esperado: 0 hits após o fix

grep -n "scripts/sprint_auto_move" docs/ROADMAP.md
# Esperado: 1 hit
```

## Acceptance

- Edit aplicado.
- Grep confirma path novo.
- Pytest baseline mantida. Lint exit 0.

## Padrões aplicáveis

- (a) Edit incremental.
- (l) Achado colateral vira sprint-filha.

---

*"Documento aponta para path que existe — princípio do mapa honesto."*
