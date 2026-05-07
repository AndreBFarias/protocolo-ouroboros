---
id: UX-M-TESTES-REGRESSIVOS
titulo: Atualizar 4 testes regressivos pre-Onda M (debito historico)
status: concluida
concluida_em: 2026-05-06
prioridade: media
data_criacao: 2026-05-06
fase: MODULARIZAÇÃO
depende_de: []
co_executavel_com: [UX-M-01, UX-M-02, UX-M-03, UX-M-04]
esforco_estimado_horas: 1-2
esforco_real_horas: ~30min
---

# Sprint UX-M-TESTES-REGRESSIVOS — Atualizar 4 testes regressivos pré-Onda M

## Contexto

Auditoria pytest completa em 2026-05-06 (durante UX-M-01) revelou **4 testes que JÁ estavam falhando antes da Onda M** (confirmados em clone limpo do main commit `d16313c`):

1. `tests/test_dashboard_tema.py::TestSprintUX115FaixasVaziasAlinhamento::test_st_main_background_associado_ao_seletor` — espera `var(--color-card-fundo)` mas CSS atual tem `#0e0f15` hardcoded.
2. `tests/test_dashboard_tema.py::TestSprintUX115FaixasVaziasAlinhamento::test_st_main_e_stapp_compartilham_token_card_fundo` — mesmo padrão acima.
3. `tests/test_dashboard_tema.py::TestSprintUX119PolishV2::test_ac6_sidebar_background_preservado` — token de sidebar mudou.
4. `tests/test_dashboard_titulos.py::test_pagina_chama_hero_titulo_sem_numero[contas.py]` e `[projecoes.py]` — esperam que TODAS páginas chamem `hero_titulo_html`, mas o commit `2817706` removeu a chamada de `contas.py` e `projecoes.py` (substituiu por `subtitulo_secao_html` em sub-seções).
5. `tests/test_tema_css_redesign.py::test_hex_hardcoded_no_codigo_fonte_dentro_de_limite` — espera ≤3 hex hardcoded em `tema_css.py`, encontrou 5.

Padrão `(cc)` BRIEF: refactor revela teste frágil — abrir sprint-filha em vez de "consertar" sem spec.

## Objetivo

Atualizar os 4 testes para refletir o estado canônico atual do projeto (pós-Onda T+Q+U + commits `2817706` e `4b62b0b`):

1. **test_st_main_background_associado_ao_seletor**: aceitar tanto `var(--color-card-fundo)` quanto valor literal `#0e0f15` (token canônico atual). Atualizar para verificar token `var(--bg-base)` (mockup) ao invés do legado.
2. **test_st_main_e_stapp_compartilham_token_card_fundo**: idem.
3. **test_ac6_sidebar_background_preservado**: ajustar para token canônico atual.
4. **test_pagina_chama_hero_titulo_sem_numero[contas.py/projecoes.py]**: remover `contas.py` e `projecoes.py` da lista `PAGINAS_COM_HERO` — não chamam mais `hero_titulo_html` (substituído por `subtitulo_secao_html` em sub-seções, conforme commit `2817706`).
5. **test_hex_hardcoded_no_codigo_fonte_dentro_de_limite**: ajustar limite de 3→5 ou refatorar `tema_css.py` para reduzir hex (preferível: refatorar em outra sprint).

## Validação ANTES

```bash
# Confirmar testes falhando isoladamente
pytest tests/test_dashboard_tema.py::TestSprintUX115FaixasVaziasAlinhamento -q 2>&1 | tail -3
# Esperado: 2 failed

pytest "tests/test_dashboard_titulos.py::test_pagina_chama_hero_titulo_sem_numero[contas.py]" "tests/test_dashboard_titulos.py::test_pagina_chama_hero_titulo_sem_numero[projecoes.py]" -q 2>&1 | tail -3
# Esperado: 2 failed

pytest tests/test_tema_css_redesign.py::test_hex_hardcoded_no_codigo_fonte_dentro_de_limite -q 2>&1 | tail -3
# Esperado: 1 failed
```

## Spec de implementação

### 1. tests/test_dashboard_tema.py

Localizar `TestSprintUX115FaixasVaziasAlinhamento` e `TestSprintUX119PolishV2`. Substituir verificação de `var(--color-card-fundo)` legado por verificação flexível que aceita o token canônico atual do tokens.css (`var(--bg-base)` ou hex `#0e0f15`).

### 2. tests/test_dashboard_titulos.py

Localizar lista `PAGINAS_COM_HERO`. Remover `contas.py` e `projecoes.py` — comentar com referência ao commit `2817706` que removeu a chamada.

### 3. tests/test_tema_css_redesign.py

Ajustar limite `hex_total <= 3` para `hex_total <= 5` (estado pós-Onda T+Q+U). Adicionar comment explicando que UX-M-01 reduziu via tokens.css mas restam 5 literais em comments e regras BG-CONTINUITY.

## Validação DEPOIS

```bash
pytest tests/ -q 2>&1 | tail -3
# Esperado: 2554+ passed, 0 failed (era 2550 passed / 4 failed pré-fix)
```

## Critério de aceitação

1. 4 testes verdes (eram falhando).
2. Pytest baseline: 2554+ passed.
3. Lint OK + smoke 10/10.
4. Comentários nos testes mostram justificativa (referência aos commits que mudaram comportamento).

## Não-objetivos

- NÃO refatorar `tema_css.py` para eliminar os 5 hex hardcoded (Onda M-04 endereça parcialmente, mais débito separado).
- NÃO mexer em código fora de `tests/`.

## Referência

- Commits relevantes: `2817706` (remove hero_titulo_html), `4b62b0b` + `d16313c` (Onda M).
- Padrão (cc) BRIEF — refactor revela teste frágil.
- VALIDATOR_BRIEF.md.

*"Teste frágil é débito documental — corrigir é parte da onda." — princípio M-TESTES*
