---
id: UX-V-3.3-FIX-ROTA
titulo: Catalogação — corrigir bug de roteamento que renderiza Busca Global
status: concluida
concluida_em: 2026-05-08
prioridade: altissima
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 1
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md M5 (bug funcional)
mockup: novo-mockup/mockups/07-catalogacao.html
---

# Sprint UX-V-3.3-FIX-ROTA — fix bug de roteamento Catalogação

## Contexto

Bug funcional crítico detectado em 2026-05-08: navegando para `?cluster=Documentos&tab=Catalogação` o conteúdo renderizado é a página BUSCA GLOBAL (mesmo título, mesmos chips Tipos rápidos). Apenas o breadcrumb dinâmico mostra "DOCUMENTOS / CATALOGAÇÃO".

A causa pode ser:
- Tabela de roteamento em `src/dashboard/app.py` apontando errado para Catalogação.
- Função `renderizar` da Catalogação chamando a função de Busca por engano.
- Encoding de URL `?tab=Catalogac%C3%A3o` (com ã) sendo interpretado como fallback.

## Objetivo

1. Investigar via grep onde Catalogação é registrada no roteador.
2. Corrigir mapping para apontar para `src/dashboard/paginas/catalogacao.py:renderizar` (ou nome real do arquivo).
3. Confirmar que `?tab=Catalogação` renderiza conteúdo Catalogação real (não Busca).

## Validação ANTES (grep)

```bash
grep -n "Catalogação\|catalogacao\|tab=Catalogação\|renderizar.*catalog" src/dashboard/app.py src/dashboard/paginas/catalogacao.py | head -20
ls src/dashboard/paginas/catalogacao.py
```

## Não-objetivos

- NÃO redesenhar Catalogação — é responsabilidade da V-3.3-CATALOGACAO-GRID.
- NÃO mexer no roteamento de outras páginas.

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k catalogacao -q
```

Captura visual: navegar `?cluster=Documentos&tab=Catalogação` deve mostrar título da Catalogação real (não BUSCA GLOBAL).

## Critério de aceitação

1. URL canônica renderiza página Catalogação real.
2. Breadcrumb e título coerentes.
3. Lint + smoke + baseline pytest.

## Referência

- Auditoria: M5 `AUDITORIA_PARIDADE_VISUAL_2026-05-08.md`.
- Mockup: `07-catalogacao.html`.

*"Roteamento errado é mentira de URL." — princípio V-3.3-FIX-ROTA*
