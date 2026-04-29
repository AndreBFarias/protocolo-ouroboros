# Sprint GAP-01 -- Alerta proativo: transação alta sem NF/comprovante correspondente

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 4
**Esforço estimado**: 4h
**Depende de**: MICRO-01
**Fecha itens da auditoria**: item E da revisão 2026-04-29 (visão do dono)

## Problema

Visão do dono: 'gastei 800 na amazon com idiotice, falta a nota fiscal'. Hoje sistema não reage proativamente: transação aparece no XLSX, mas se não vem NF, fica invisível. IRPF anual chega incompleto sem alerta intermediário.

## Hipótese

Detector cruzando extrato vs grafo: para cada transação acima de limiar configurável (ex: R$ 100), verificar se existe edge documento_de apontando para ela. Se não, listar como 'gap documental'. Alertar via aba dedicada + relatório mensal + sync para mobile companion (notificação).

## Relação com `gap_documental.py` existente (adicionado pela DOC-VERDADE-01 M1)

**Atenção**: já existe `src/analysis/gap_documental.py` (Sprint 75, ~210L) em uso por `src/dashboard/paginas/completude.py:17`. Esta sprint **cria módulo paralelo** (`gap_documental_proativo.py`) por **decisão explícita do dono em 2026-04-29**, não por desconhecimento.

Limites de cada módulo:

| Módulo | Domínio | Quando usar | Quem consome |
|--------|---------|-------------|--------------|
| `gap_documental.py` (Sprint 75) | Cobertura **categorial** (mês × categoria com ou sem documento). Calcula heatmap de completude visual. | Análise retrospectiva de meses fechados | Aba `completude.py` no dashboard |
| `gap_documental_proativo.py` (esta sprint) | **Alerta por transação**: cruza valor da tx individual com presença de aresta `documento_de` no grafo. Limiar configurável por categoria. | Alerta em runtime / mensal sobre tx específica sem NF | Aba "Gaps Documentais" + cache mobile |

Ambos coexistem por design. Não fundir. Se em sessão futura aparecer fricção real, abrir sprint `META-CONSOLIDA-GAP-DOC` decidindo fusão.

## Implementação proposta

1. src/analysis/gap_documental_proativo.py — `detectar_gaps(limiar)`.
2. mappings/limiares_gap.yaml por categoria (Mercado: R$ 100; Eletrônicos: R$ 50; etc.).
3. Aba 'Gaps documentais' no dashboard com lista filtrada.
4. Relatório mensal com top-N gaps.
5. Cache JSON para mobile (vault/.ouroboros/cache/gaps.json).
6. **Não tocar em `gap_documental.py` nem em `completude.py`** — escopo isolado.

## Proof-of-work (runtime real)

Corpus real → detecta >=10 gaps em transações > R$ 100 sem doc.

## Acceptance criteria

- Módulo + 8 testes.
- Aba dashboard.
- Relatório mensal.
- Cache mobile.

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
