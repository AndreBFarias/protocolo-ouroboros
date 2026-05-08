---
id: UX-V-3.2
titulo: Busca Global — facet-card lateral + grupos resultado + snippet highlight
status: concluída
concluida_em: 2026-05-08
commit: 998fe6e
prioridade: media
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 3
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md (página 06)
mockup: novo-mockup/mockups/06-busca-global.html
---

# Sprint UX-V-3.2 — Busca Global com facetas e snippets

## Contexto

Estado vazio (sem query) está OK. Quando há query, o mockup mostra:
- Subtítulo com counters reais: "439 documentos · 2.847 transações · 1.284 sidecars".
- Layout 2-col: facet-card lateral esquerda (TIPO/PERÍODO/CONTA/CATEGORIA com counts em cada faceta) + resultados em grupos (TRANSAÇÕES + DOCUMENTOS) com snippet highlight `<mark>` na palavra buscada.

Dashboard real só mostra chips de tipos rápidos + estado vazio. Quando há query, busca acontece mas não tem facet-card nem snippet highlight.

## Objetivo

1. Subtítulo com counters reais no header.
2. Facet-card lateral 4 facetas (TIPO/PERÍODO/CONTA/CATEGORIA), cada uma listando opções com count à direita; clique filtra resultados.
3. Resultados agrupados em "TRANSAÇÕES" + "DOCUMENTOS" com counter no header de cada grupo.
4. Snippet highlight: palavra buscada destacada com `<mark>` no preview do resultado.

## Validação ANTES (grep)

```bash
grep -n "facet\|snippet\|<mark>\|res-group" src/dashboard/paginas/busca.py src/dashboard/css/paginas/busca.css | head
```

## Não-objetivos

- NÃO mexer nos chips Tipos rápidos.
- NÃO implementar busca semântica.

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k busca -q
```

Captura visual: query "aluguel" mostra layout 2-col com facetas lateral + 2 grupos resultado.

## Critério de aceitação

1. Counters reais no subtítulo.
2. Facet-card 4 facetas presente quando há query.
3. Resultados agrupados TRANSAÇÕES + DOCUMENTOS.
4. Snippet com palavra destacada.
5. Lint + smoke + baseline pytest.

## Referência

- Mockup: `06-busca-global.html`.

*"Facetas reduzem ruído, snippets entregam contexto." — princípio V-3.2*
