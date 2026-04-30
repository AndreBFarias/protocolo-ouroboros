# Sprint GAP-01 -- Alerta proativo: transação sem NF/comprovante (cobertura total)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 4
**Esforço estimado**: 4h
**Depende de**: MICRO-01a (backbone do linking transação-documento)
**Fecha itens da auditoria**: item E da revisão 2026-04-29 (visão do dono)

## Problema

Visão do dono: 'gastei 800 na amazon com idiotice, falta a nota fiscal'. Hoje sistema não reage proativamente: transação aparece no XLSX, mas se não vem NF, fica invisível. IRPF anual chega incompleto sem alerta intermediário.

Reforço do dono em 2026-04-29: **"temos que ter cobertura pra tudo. Não só >500, é tudo tudo mesmo"**. E em complemento: **"a ideia é extrair tudo das imagens e pdfs, tudo mesmo, cada valor e catalogar tudo"**. Princípio de cobertura total -- nenhuma transação fora do radar, mesmo de baixo valor.

## Hipótese

Detector cruzando extrato vs grafo: para **cada transação sem aresta `documento_de`** (independente de valor), listar como 'gap documental'. **Cobertura total** -- nenhum filtro de inclusão por valor.

Limiar opcional por categoria existe **apenas para ordenação** (top-N do relatório/notificação) e nunca para excluir transação da lista. Auditoria 2026-04-29 baseline: 6.073 das 6.086 transações sem doc (99,8%). Após MICRO-01a fechar: ≤6.071 transações sem doc.

## Relação com `gap_documental.py` existente (adicionado pela DOC-VERDADE-01 M1)

**Atenção**: já existe `src/analysis/gap_documental.py` (Sprint 75, ~210L) em uso por `src/dashboard/paginas/completude.py:17`. Esta sprint **cria módulo paralelo** (`gap_documental_proativo.py`) por **decisão explícita do dono em 2026-04-29**, não por desconhecimento.

Limites de cada módulo:

| Módulo | Domínio | Quando usar | Quem consome |
|--------|---------|-------------|--------------|
| `gap_documental.py` (Sprint 75) | Cobertura **categorial** (mês × categoria com ou sem documento). Calcula heatmap de completude visual. | Análise retrospectiva de meses fechados | Aba `completude.py` no dashboard |
| `gap_documental_proativo.py` (esta sprint) | **Alerta por transação**: cruza valor da tx individual com presença de aresta `documento_de` no grafo. Limiar configurável por categoria. | Alerta em runtime / mensal sobre tx específica sem NF | Aba "Gaps Documentais" + cache mobile |

Ambos coexistem por design. Não fundir. Se em sessão futura aparecer fricção real, abrir sprint `META-CONSOLIDA-GAP-DOC` decidindo fusão.

## Implementação proposta

1. `src/analysis/gap_documental_proativo.py` -- função `detectar_gaps(limiar_alerta=None)` retornando **todas** as transações sem `documento_de`. `limiar_alerta` controla apenas o subconjunto destacado para notificação, nunca o subconjunto incluído.
2. `mappings/limiares_gap.yaml` por categoria (Mercado: R$ 100; Eletrônicos: R$ 50; etc.). **Função do limiar é apenas ordenação/destaque**, nunca filtro de inclusão.
3. Aba 'Gaps Documentais' no dashboard listando 100% das transações sem `documento_de`. Paginação Streamlit + ordenação por valor + filtro visual opcional pelo usuário (não código). Renderização ≤2s para 6.000+ entradas.
4. Relatório mensal com top-N gaps acima de limiar (R$ 100 default) + total geral.
5. Cache `data/output/gaps.json` regenerado a cada `--full-cycle`. Mobile bridge fica para Onda 5/MOB-02 (não cria pasta `vault/.ouroboros/` agora).
6. **Não tocar em `gap_documental.py` nem em `completude.py`** -- escopo isolado.

## Proof-of-work (runtime real)

Corpus real → detecta **todas** as transações sem `documento_de`. Baseline 2026-04-29: 6.073 detecções. Métrica deve sempre bater: `gaps_detectados == total_transacoes - transacoes_com_documento_de`.

## Acceptance criteria

- Módulo + ≥8 testes (cobrindo cobertura total + ordenação por limiar + paginação + cache).
- Aba dashboard com cobertura total (sem filtro de inclusão por valor).
- Relatório mensal com top-N por limiar de alerta.
- Cache `data/output/gaps.json` regenerado em cada `--full-cycle`.
- Performance: aba renderiza ≤2s mesmo com 6.000+ entradas.

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
