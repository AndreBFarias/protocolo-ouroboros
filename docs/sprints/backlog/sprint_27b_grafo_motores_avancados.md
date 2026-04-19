## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 27b
  title: "Grafo avançado -- motores de linking documento-transação e eventos"
  touches:
    - path: src/graph/linker.py
      reason: "Motor 1 -- associar boletos PDF/imagens às transações"
    - path: src/graph/event_detector.py
      reason: "Motor 3 -- detectar cadeias temporais por entidade"
    - path: src/graph/visual.py
      reason: "visualização pyvis + Sankey + heatmap (absorve Sprint 09)"
    - path: src/dashboard/paginas/grafo_visual.py
      reason: "nova página com grafo interativo"
  n_to_n_pairs:
    - [src/graph/linker.py, src/graph/models.py]
    - [src/graph/event_detector.py, src/graph/models.py]
  forbidden:
    - src/graph/models.py  # schema fechado na Sprint 27a; aqui só adiciona migrations
  tests:
    - cmd: "make lint"
      timeout: 60
  acceptance_criteria:
    - "A definir na abertura da sprint -- bloqueada até base de 90 dias estável"
    - "Acentuação PT-BR correta"
    - "Zero emojis e zero menções a IA"
```

---

# Sprint 27b -- Grafo avançado: motores de linking e eventos

**Status:** PENDENTE
**Data:** 2026-04-18
**Prioridade:** BAIXA
**Tipo:** Feature
**Dependências:** Sprint 27a (grafo mínimo), Sprint 29a (UX base), Sprint 36 (audit final)
**Desbloqueia:** --
**Issue:** (a criar quando a sprint for ativada)
**ADR:** --

---

## Como Executar

Sprint de visão pós-90 dias. **Não abrir sem o plano 30/60/90 ter sido concluído e estabilizado.** Critérios de entrada:
- Sprint 27a em produção há pelo menos 30 dias sem regressão
- Sprint 29a com busca global estável
- Custo mensal de provedor de IA consistente com a previsão (< $10)

### O que NÃO fazer

- NÃO iniciar antes da estabilização dos 90 dias
- NÃO tocar no schema da Sprint 27a (só estender via migrations)
- NÃO explodir o grafo com `pyvis` sobre 10k+ nodes sem amostragem

---

## Problema

Após a base mínima da Sprint 27a, o grafo ainda é estático: sabe que existem entidades e transações, mas não liga boletos PDF aos pagamentos, nem detecta cadeias ("ciclo de fatura Santander", "parcelamento 10x na Amazon"). Além disso, a visualização gráfica (`pyvis`, Sankey, heatmap) -- antes prevista na Sprint 09 -- é necessária para uso humano real.

Esta sprint absorve:
1. Escopo original da Sprint 27 que não coube em 27a (Motor 1 e Motor 3).
2. Escopo da Sprint 09 (grafos analíticos Sankey/heatmap), que foi cancelada como sprint autônoma e redirecionada aqui.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Modelos de grafo | `src/graph/models.py` | `Node` e `Edge` via SQLAlchemy (Sprint 27a) |
| Entity resolution | `src/graph/entity_resolution.py` | unificação por `rapidfuzz` (Sprint 27a) |
| Página Grafo | `src/dashboard/paginas/grafo.py` | lista tabular de entidades (Sprint 27a) |
| Busca global | `src/dashboard/paginas/busca.py` | busca textual (Sprint 29a) |

---

## Implementação

### Fase 1: Motor 1 -- Linking documento-transação

**Arquivo:** `src/graph/linker.py`

Para cada `Documento` (PDF/imagem de boleto ingerido), procurar `Transacao` candidatas:
- Categoria compatível (energia-pagamento para conta de luz)
- `|valor_doc - valor_transacao| <= max(1.00, valor_doc * 0.02)`
- Data entre `data_emissao - 3 dias` e `data_vencimento + 10 dias`

Score:
- 0.95 se 3 critérios batem
- 0.80 se 2 batem e 1 é frouxo
- 0.50 loga alerta, não grava

Ambiguidade (2+ candidatas empatando) cria `Alerta/ambiguidade` para revisão humana.

### Fase 2: Motor 3 -- Eventos e cadeias

**Arquivo:** `src/graph/event_detector.py`

- **Parcelamento**: série N transações com mesma contraparte, valor igual, intervalo mensal -> `Evento` + aresta `parte_de`.
- **Assinatura**: série recorrente >= 3 meses, mesma entidade, valor semelhante -> `Assinatura` + aresta `instancia_de`.
- **Estorno/reembolso**: transação positiva <= 30 dias de débito da mesma entidade -> aresta `reembolsa`.
- **Ciclo de fatura**: entidade bancária com ciclo fechado e pago no mesmo mês -> `Evento` tipo ciclo.

### Fase 3: Visualização (absorve Sprint 09)

**Arquivo:** `src/graph/visual.py` + `src/dashboard/paginas/grafo_visual.py`

- `pyvis` com amostragem por entidade/período (limite 500 nodes visíveis).
- Sankey: fluxo receita -> categorias -> classificação (`plotly`).
- Heatmap temporal: meses vs categorias.
- Filtros obrigatórios: tipo de nó, período, threshold de confiança.

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A27b-1 | `pyvis` explodindo com >10k nodes | Amostragem obrigatória + aviso ao usuário |
| A27b-2 | Motor 1 com falsos positivos (2 contas de luz no mesmo mês) | Confidence mínima 0.8 + flag de revisão |
| A27b-3 | Motor 3 confundindo mesada recorrente com assinatura | Só cria `Assinatura` se houver entidade canônica em `mappings/entidades.yaml` |
| A27b-4 | Histórico reinterpretado retroativamente | Snapshot do grafo antes da execução + diff |
| A27b-5 | Sankey com 40+ categorias ilegível | Agregar "top 10 + Outros" |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

A definir na abertura da sprint. Não escrever código antes de revalidar se as premissas dos 90 dias ainda valem.

---

## Verificação end-to-end

```bash
# Placeholder -- definir ao abrir sprint
make lint
```

---

*"O todo é maior que a soma das partes, mas conhecer as partes é condição para conhecer o todo." -- Aristóteles*
