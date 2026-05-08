---
id: UX-V-3.3-GRID
titulo: Catalogação — grid de thumbs com badges + sidebar 3 facetas
status: concluída
concluida_em: 2026-05-08
commit: 6e2bf7a
prioridade: media
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: [UX-V-3.3-FIX-ROTA]
esforco_estimado_horas: 4
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md (página 07) + decisão dono 2026-05-07 hibrido
mockup: novo-mockup/mockups/07-catalogacao.html
---

# Sprint UX-V-3.3-GRID — Catalogação como grid de thumbs

## Contexto

Decisão dono 2026-05-07: Catalogação fica **híbrida** (KPIs+tipos no topo + grid de thumbs abaixo).

Mockup `07-catalogacao.html` mostra:
- Título "CATALOGAÇÃO" + sub "Banco de dados normalizado. 439 arquivos · 7 tipos · 2.847 transações"
- Tag "CLUSTER · CATALOGAÇÃO · GRADUADO"
- Topbar: Exportar consulta / Nova vista
- Search-bar "Buscar por sha8, nome, fornecedor..." + counter "12 de 439" + setas
- Sidebar lateral 3 facetas (TIPO/PERÍODO/FONTE com counts)
- Grid 2x6 de cards-thumb com badge tipo (PDF/IMG/CSV/XLSX/OFX) no canto, nome do arquivo, sha8, data, chips de tipo/banco

## Objetivo

1. Adicionar grid de thumbs abaixo dos KPIs/tipos atuais (decisão híbrida).
2. Cada card-thumb: thumbnail (placeholder cinza ou primeira página rendering), badge tipo no canto, nome com truncate, sha8, data ingest, chip de tipo/banco.
3. Sidebar 3 facetas com counts (clica filtra).
4. Search-bar de cards (`buscar por sha8, nome, fornecedor`) + paginação simples.

## Validação ANTES (grep)

```bash
wc -l src/dashboard/paginas/catalogacao.py
grep -n "thumb\|grid-cards\|facet" src/dashboard/paginas/catalogacao.py src/dashboard/css/paginas/catalogacao.css | head
```

## Não-objetivos

- NÃO renderizar primeira página dos PDFs (thumbnail placeholder OK).
- NÃO mexer nos KPIs/cards-tipos atuais.

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k catalogacao -q
```

Captura visual: grid 2x6 visível com badges + sidebar facetas + search-bar.

## Critério de aceitação

1. Grid de thumbs renderiza >=12 cards (caso dado real).
2. Badge de tipo no canto superior direito de cada card.
3. Sidebar 3 facetas com counts reais.
4. Search-bar filtra cards.
5. Lint + smoke + baseline pytest.

## Referência

- Mockup: `07-catalogacao.html`.
- Sub-sprint hard-bloqueante: V-3.3-FIX-ROTA.

*"Catálogo sem thumbs é planilha." — princípio V-3.3-GRID*
