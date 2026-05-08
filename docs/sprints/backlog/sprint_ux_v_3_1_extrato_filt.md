---
id: UX-V-3.1
titulo: Extrato — filt-bar inline canônica + lista por dia com pílulas tipadas
status: backlog
prioridade: media
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 3
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (proposta) + 2026-05-08 (página 02)
mockup: novo-mockup/mockups/02-extrato.html
---

# Sprint UX-V-3.1 — Extrato com filt-bar canônica e lista por dia

## Contexto

A auditoria 2026-05-07 propôs sprint V-3.1 mas nunca foi criada. Inspeção 2026-05-08 confirma os gaps:

- Mockup tem filt-bar inline canônica `.t02-filt-bar` (CONTA: todas (3) | CATEGORIA | PERÍODO | BUSCA + chips só-saídas / com-sidecar / não-categorizadas + counter "142 transações").
- Mockup tem lista por dia com header `2026-04-30 · QUI - R$ 2.832,40` + linhas com pílulas tipo (NB/IF/PX/UB/EX) + categoria + conta + sha8 + valor.
- Dashboard só tem "Buscar por local" + "> Filtros avançados" expander + 3 cards lado a lado no topo (Saldo 90D + Breakdown + Origens) — semelhante ao mockup mas SEM lista de transações.

## Objetivo

1. Adicionar filt-bar canônica entre KPIs e cards laterais.
2. Renderizar lista por dia: agrupar transações por data DESC, header com data + total dia, linhas com pílula tipo (2 letras), categoria chip, conta, sha8, valor à direita tabular.
3. Chips toggle: só-saídas / com-sidecar / não-categorizadas filtram a lista.

## Validação ANTES (grep)

```bash
wc -l src/dashboard/paginas/extrato.py
grep -n "filt-bar\|t02-filt\|lista_por_dia\|chip.*saidas" src/dashboard/paginas/extrato.py src/dashboard/css/paginas/extrato.css | head
```

## Não-objetivos

- NÃO mexer no Saldo 90D / Breakdown / Origens (já entregues).
- NÃO implementar paginação completa nesta sprint (limite 50 linhas para começar).

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k extrato -q
```

Captura visual: cluster=Finanças&tab=Extrato mostra filt-bar + chips + lista agrupada por dia com pílulas.

## Critério de aceitação

1. Filt-bar canônica visível abaixo dos KPIs.
2. Lista por dia renderiza >=10 linhas (caso dado real).
3. 3 chips funcionais filtrando a lista.
4. Pílulas com 2 letras coloridas por tipo.
5. Lint + smoke + baseline pytest.

## Referência

- Mockup: `02-extrato.html`.
- Auditoria: `AUDITORIA_PARIDADE_VISUAL_2026-05-08.md` página 02.

*"Lista por dia mostra o ritmo do dinheiro." — princípio V-3.1*
