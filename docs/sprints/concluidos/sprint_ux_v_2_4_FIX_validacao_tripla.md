---
id: UX-V-2.4-FIX
titulo: Validação Tripla — corrigir layout 3-col + título acentuado + tabela completa
status: concluída
concluida_em: 2026-05-08
commit: b833ef7
prioridade: altissima
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: [INFRA-EXTRACAO-TRIPLA-SCHEMA]
esforco_estimado_horas: 3
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md A1 + M2
mockup: novo-mockup/mockups/10-validacao-arquivos.html <!-- noqa: accent -->
---

# Sprint UX-V-2.4-FIX — Validação Tripla com layout canônico

## Contexto

Spec UX-V-2.4 declarou paridade visual mas a inspeção 2026-05-08 mostrou:
- Título renderiza `EXTRAÇAO TRIPLA` (sem `ã`) violando regra `(b)`.
- Layout é 2-col (selectbox + tabela) em vez de 3-col (lista por TIPO + tabela ETL×Opus×Humano + KPIs).
- Coluna Opus 100% vazia (`—`) — bloqueado por INFRA-EXTRACAO-TRIPLA-SCHEMA.
- Status nunca atinge CONSENSO/DIVERGENTE.
- Header KPIs tem PARIDADE/DIVERGÊNCIAS/EM REVISÃO mas falta UNILATERAIS.

## Objetivo

1. Corrigir título: `EXTRAÇÃO TRIPLA` (com ção+ã).
2. Migrar para layout 3-col real: lista lateral agrupada por TIPO + tabela central + (KPIs no topo full-width).
3. Adicionar 4ª KPI: `UNILATERAIS` (campos só ETL ou só Opus).
4. Quando schema canônico (INFRA-) está populado, renderizar badges CONSENSO/DIVERGENTE corretamente.
5. Linhas divergentes em laranja conforme spec V-2.4 original (mantém regra existente).

## Validação ANTES (grep)

```bash
grep -n "EXTRAÇAO\|EXTRACAO\|EXTRAÇÃO" src/dashboard/paginas/extracao_tripla.py
grep -n "selectbox\|st.columns\|UNILATERAIS\|CONSENSO\|DIVERGENTE" src/dashboard/paginas/extracao_tripla.py | head
```

## Não-objetivos

- NÃO mudar schema (responsabilidade da INFRA-).
- NÃO implementar persistência humana completa.
- NÃO chamar Opus em runtime.

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k "extracao_tripla or validacao" -q
```

Validação visual: `cluster=Documentos&tab=Validação+por+Arquivo` deve mostrar:
1. Título "EXTRAÇÃO TRIPLA" (com ção+ã).
2. Header com 4 KPIs: PARIDADE / DIVERGÊNCIAS / UNILATERAIS / EM REVISÃO + counter ARQUIVOS.
3. Lista esquerda agrupada por TIPO (PDF/IMG/CSV/XLSX) — mesmo se tem 1 grupo só com dado real.
4. Tabela central com colunas Campo / ETL / Opus / Humano / Status.
5. Linhas com badge CONSENSO (verde) quando ETL=Opus, DIVERGENTE (laranja) quando diferente.

## Critério de aceitação

1. Título corrigido — `validar-acentuacao.py` passa.
2. Layout 3-col em viewport >=1280px.
3. Quando >=1 registro tem Opus preenchido (via INFRA-), aparecem badges CONSENSO + DIVERGENTE.
4. UNILATERAIS no header reflete contagem real.
5. Lint OK + smoke 10/10.

## Referência

- Spec original: `docs/sprints/concluidos/sprint_ux_v_2_4_validacao_tripla.md`.
- Mockup: `novo-mockup/mockups/10-validacao-arquivos.html` <!-- noqa: accent -->.
- Auditoria: A1 + M2 em AUDITORIA 2026-05-08.

*"Onde dois extratores divergem, o humano decide — mas só se a coluna existir." — princípio V-2.4-FIX*
