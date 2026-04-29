# Sprint UX-01 -- Migrar 4 arquivos st.error/warning/info/success → callout_html

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P0
**Onda**: 6
**Esforço estimado**: 2h
**Depende de**: nenhuma
**Fecha itens da auditoria**: itens 1–4 da auditoria

## Problema

preview_documento.py, app.py, modal_transacao.py, busca.py usam componentes nativos do Streamlit fora do tema Dracula.

## Hipótese

Replace direto por callout_html (Sprint 92c).

## Implementação proposta

Edits cirúrgicos nos 4 arquivos.

## Proof-of-work (runtime real)

grep st.error|warning|info|success em src/dashboard/ → 0 matches.

## Acceptance criteria

- Migração 100%.
- Validação visual.

## Gate anti-migué

Para mover esta spec para `docs/sprints/concluidos/`:

1. Hipótese declarada validada com `grep` antes de codar.
2. Proof-of-work runtime real capturado em log.
3. `make conformance-<tipo>` exit 0 quando aplicável (>=3 amostras 4-way).
4. `make lint` exit 0.
5. `make smoke` 10/10 contratos.
6. `pytest` baseline mantida ou crescida.
7. Achados colaterais viraram sprint-ID OU Edit-pronto. Zero TODO solto.
8. Validador (humano ou subagent) APROVOU.
9. Frontmatter `concluida_em: YYYY-MM-DD` adicionado.
