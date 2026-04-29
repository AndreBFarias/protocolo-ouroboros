# Sprint ANTI-MIGUE-03 -- Reconciliar testes 1.987 vs 2.028

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29, item 36).
**Prioridade**: P1
**Onda**: 1
**concluida_em**: 2026-04-29
**Esforço real**: 15min (diagnóstico puro)

## Problema

Documentação (CLAUDE.md, ESTADO_ATUAL.md) declarava `1.987 passed`. `pytest --collect-only` retornava `2.028 tests collected`. Delta de 41 sem reconciliação: ou são testes fantasma (skip silencioso) ou doc desatualizada.

## Diagnóstico

```
$ .venv/bin/pytest -q --tb=no
2.018 passed, 9 skipped, 1 xfailed, 32 warnings in 40.39s

$ .venv/bin/pytest --collect-only -q
2028 tests collected
```

Soma: 2.018 + 9 + 1 = **2.028** (bate com `--collect-only`). Skip e xfail consistentes nas duas medições.

## Conclusão

**Zero testes fantasma.** Doc estava apenas desatualizada (provável esquecimento da última sessão de cluster UX). Delta real: +31 testes adicionados desde o último update da doc.

## Fix

Atualização de baseline em `contexto/ESTADO_ATUAL.md` (gitignored, local) e `CLAUDE.md` (linha de referência em `tests/`).

## Acceptance atendido

- [x] Causa identificada: doc desatualizada, não bug.
- [x] Baseline real medido: 2.018 passed.
- [x] Documentação atualizada nos arquivos canônicos.
