---
id: UX-V-4
titulo: Revisor — layout 4-pane (OFX/Rascunho/Opus/Humano) + tabs filtro + trace de raciocínio
status: backlog
prioridade: alta
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: [INFRA-EXTRACAO-TRIPLA-SCHEMA]
esforco_estimado_horas: 4
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md (página 09)
mockup: novo-mockup/mockups/09-revisor.html
---

# Sprint UX-V-4 — Revisor com arquitetura 4-way canônica

## Contexto

Auditoria 2026-05-07 marcou Revisor como "INVESTIGAR" porque iframe Chrome bloqueava captura. Inspeção 2026-05-08 via Playwright confirmou que o dashboard atual mostra:
- 4 KPIs (Pendências/Revisadas/Aguardando/Fidelidade) + filtro Tipo de pendência + paginação.
- COMPARAÇÃO ETL × OPUS com 0 divergentes (Opus vazio).

Mockup `09-revisor.html` mostra arquitetura totalmente diferente:
- Lista lateral esquerda com transações + pílulas APURADO/DIVERGENTE/RASCUNHO + confiança%.
- Centro: 4 cards lado-a-lado (OFX banco read-only / RASCUNHO ETL / OPUS agentic / HUMANO inputs).
- Tabs no topo: Mês atual / Só divergentes / Só rascunhos / Apurado.
- Rodapé com tabs Detalhes / Auditoria do Opus / Histórico / Hints + trace de raciocínio + arquivos consultados + próximas ações.

## Objetivo

1. Reescrever layout para arquitetura 4-way: lista esquerda + 4 cards centro.
2. Tabs filtro no topo.
3. Detalhe da transação selecionada nos 4 cards.
4. Rodapé com tabs (Detalhes / Auditoria Opus / Histórico / Hints).
5. Trace de raciocínio quando há registro Opus em `extracao_tripla.json`.
6. Botões "Aceitar como humano" / "Re-gerar c/ hint" / "Apurar transação" / "Marcar para revisar depois".

## Validação ANTES (grep)

```bash
wc -l src/dashboard/paginas/revisor.py
grep -n "ofx\|rascunho\|opus_card\|trace\|st.tabs" src/dashboard/paginas/revisor.py | head
```

## Não-objetivos

- NÃO implementar persistência humana real (placeholder OK).
- NÃO chamar Opus em runtime.

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k revisor -q
```

Captura visual via playwright (claude-in-chrome bloqueia iframe): 4 cards lado-a-lado, tabs no topo, trace embaixo.

## Critério de aceitação

1. Layout 4-pane visível em viewport >=1568px.
2. Tabs filtro no topo (Mês atual / Só divergentes / etc).
3. 4 cards (OFX/Rascunho/Opus/Humano) populados quando há registro selecionado.
4. Trace de raciocínio aparece quando Opus tem campos preenchidos.
5. Lint + smoke + baseline pytest.

## Referência

- Mockup: `09-revisor.html`.
- Sub-sprint hard-bloqueante: INFRA-EXTRACAO-TRIPLA-SCHEMA.

*"Revisor sem 4 vias é só lista de pendências." — princípio V-4*
