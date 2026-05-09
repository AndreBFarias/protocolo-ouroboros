<!-- noqa: accent -->
---
id: INFRA-DRILL-DOWN-ITEM
titulo: UI de drill-down item por transação (gastei R$X na farmácia, quais itens?)
status: backlog
prioridade: alta
data_criacao: 2026-05-08
fase: CONCLUSAO_REAL
depende_de: [INFRA-LINKING-NFE-TRANSACAO <!-- noqa: accent -->]
esforco_estimado_horas: 3
origem: docs/auditorias/VALIDACAO_END2END_2026-05-08.md (caso 3 — DROGASIL sem drill-down)
---

# Sprint INFRA-DRILL-DOWN-ITEM — pergunta canônica resolvida

## Contexto

Visão prometida do projeto: "gastei R$ 73,35 na DROGASIL em 2021-04-07, quais remédios comprei?" Hoje a resposta é "não sei" porque transações no extrato não expõem itens da NF/cupom vinculado, mesmo quando o vínculo existe.

Esta sprint adiciona UI de drill-down: clicar em uma linha de transação no Extrato (ou em qualquer agregador por categoria/fornecedor) abre painel lateral mostrando NF/cupom vinculado + lista de itens.

## Objetivo

1. Em `src/dashboard/paginas/extrato.py`, adicionar query-param `?transacao_id=<int>` que abre o painel lateral.
2. Painel lateral renderiza:
   - Header: data, valor, fornecedor, conta, sha8 transação.
   - Bloco "Documento vinculado": link para o sha8 da NF/cupom + thumbnail (PDF render ou JPEG).
   - Bloco "Itens": tabela `código | descrição | qtd | valor unit | valor total` lendo `node.tipo='item'` ligados via `contem_item` ao documento.
   - Bloco "Cruzamentos": outras transações com itens iguais (same `produto_canonico`).
3. Botão "marcar revisado" persiste em `data/output/revisao_humana.sqlite`.

## Validação ANTES

```bash
grep -n "transacao_id\|drill.*item\|painel_lateral" src/dashboard/paginas/extrato.py | head
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM edge WHERE tipo='documento_de'"
# Antes desta sprint: usuário esperaria >= 500 vínculos (após INFRA-LINKING-NFE-TRANSACAO <!-- noqa: accent -->)
```

## Não-objetivos

- NÃO modificar a tabela principal do extrato (apenas adicionar query-param + painel).
- NÃO tentar renderizar PDF inline (link para abrir em nova aba é OK).
- NÃO implementar edição manual de vínculos (UI separada, sprint futura).

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k extrato -q
```

Validação visual: navegar `?cluster=Finanças&tab=Extrato&transacao_id=<id_de_DROGASIL>` deve abrir painel com NF + itens.

## Critério de aceitação

1. Query param `?transacao_id=` abre painel lateral.
2. Painel mostra NF vinculada quando existe + itens da NF.
3. Quando não há vínculo, painel mostra "sem documento vinculado" + botão "ligar manualmente".
4. Lint + smoke + pytest baseline.

## Referência

- Auditoria: `VALIDACAO_END2END_2026-05-08.md` caso 3.
- Sprints dependentes: INFRA-LINKING-NFE-TRANSACAO <!-- noqa: accent --> + INFRA-OCR-OPUS-VISAO.

*"Drill-down é o teste empírico da inteligência prometida." — princípio INFRA-DRILL-DOWN-ITEM*
