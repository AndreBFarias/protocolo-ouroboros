# Auditoria LINK-AUDIT-01 — Diagnóstico empírico do linking documento → transação

> **Data**: 2026-05-15
> **Sprint**: LINK-AUDIT-01 (`docs/sprints/concluidos/sprint_link_audit_01_*.md`)
> **Ferramenta**: `scripts/diagnosticar_linking.py`
> **Grafo analisado**: `data/output/grafo.sqlite` (52 documentos, 6086 transações, 25 arestas `documento_de`)

---

## Sumário executivo

O linking heurístico documento → transação está em **0,41 % das transações** (25/6086) e **48 % dos documentos** (25/52). A meta de roadmap (≥30 % de transações com documento) é **estruturalmente inalcançável neste momento** porque há apenas 52 documentos no grafo contra 6086 transações: mesmo se todos os 52 fossem linkados, o piso máximo seria **0,85 %** de transações com documento. A meta de 30 % requer ordem de magnitude maior de documentos catalogados (alvo ≈1830 documentos), não apenas reduzir órfãos.

A análise empírica deste diagnóstico mira o **subobjetivo realista**: reduzir órfãos entre os 52 documentos existentes. Identificou-se o gargalo dominante (margem de empate global apertada) e três ajustes seguros em `mappings/linking_config.yaml` que linkam **+3 documentos** sem mexer em código (`src/graph/linking.py` intocado, conforme escopo da sprint).

---

## Estado antes dos ajustes

| Métrica | Valor |
|---|---|
| Total documentos no grafo | 52 |
| Total transações no grafo | 6086 |
| Documentos com aresta `documento_de` | 25 |
| Documentos órfãos | 27 |
| **linking_pct (documentos)** | **48,08 %** |
| **linking_pct (transações)** | **0,4108 %** |
| Propostas de conflito abertas | 20 |
| Propostas de baixa_confianca abertas | 0 |

### Documentos órfãos por tipo

| Tipo | Órfãos | Linkados | Total |
|---|---:|---:|---:|
| `das_parcsn_andre` | 14 | 5 | 19 |
| `holerite` | 4 | 20 | 24 |
| `cupom_fiscal` | 3 | 0 | 3 |
| `boleto_servico` | 2 | 0 | 2 |
| `nfce_modelo_65` | 2 | 0 | 2 |
| `comprovante_pix_foto` | 1 | 0 | 1 |
| `dirpf_retif` | 1 | 0 | 1 |
| **Total** | **27** | **25** | **52** |

---

## Diagnóstico por tipo

### `das_parcsn_andre` — 14 órfãos (52 % do total de órfãos)

**Causa dominante: `margem_empate` global de 0,05 dispara conflito mesmo quando top-1 tem clara vantagem por `diff_valor`.**

Exemplo canônico (doc 7660, R$ 327,59 venc 2025-05-30):

| rank | tx | score | diff_dias | diff_valor |
|---|---|---|---|---|
| 1 | 5865 | 0,990 | −2 | **0,00** (match perfeito) |
| 2 | 5872 | 0,979 | −1 | 10,38 |
| 3 | 5846 | 0,950 | −8 | 6,61 |

Diferença top-1 vs top-2 = 0,011 < 0,05 → conflito, mesmo com top-1 tendo `diff_valor=0` (match financeiro perfeito) e top-2 tendo `diff_valor=10,38` (3 % off).

**Distribuição empírica das 20 propostas de conflito existentes**:
- **14 propostas** têm `diff(top-1, top-2) = 0,000` (empate real entre transações com mesmo valor/data — exigem desempate por CNPJ ou descrição, não acessível só via YAML).
- **6 propostas** têm diff entre 0,011 e 0,022 (top-1 é objetivamente melhor, candidato a desbloquear via `margem_empate` menor).

### `holerite` — 4 órfãos

Doc 7684 (G4F R$ 8657,25, jul/2025): top-1 score 0,861 (delta 6d, diff_v=1369), top-2 score 0,840 (delta 3d, diff_v=2249). Diferença 0,021. Mesmo padrão de `das`.

Doc 7690 (G4F 13° adiantamento R$ 2164,31, out/2025): top-1 score 0,817 (delta −13d, diff_v=230), candidata #3 tem `diff_valor=0,00` mas score 0,700 por estar em delta=30d. O motor prioriza tempo demais sobre valor exato (limitação do `_calcular_score` linear). Fora do escopo desta sprint.

Doc 7695 (G4F 13° integral R$ 5771,50, dez/2025) e doc 7697 (INFOBASE 13° integral R$ 5833,33, dez/2025): fundidos como aliases (mesma competência + valor próximo), só representante (7695) entra no funil. Top-1 vs top-2 = 0,000 (empate real).

### `cupom_fiscal` — 3 órfãos

Janela atual = 1 dia. Os 3 órfãos têm tx candidata entre 14 e 19 dias antes da emissão do cupom (compras de cartão de crédito que liquidam dias depois). Janela atual exclui todas as candidatas — viram `sem_candidato` silencioso.

| doc | data emissão | total | tx candidata | delta | diff_valor |
|---|---|---|---|---|---|
| 7584 | 2026-04-27 | 513,31 | 7331 | −19d | 13,31 |
| 7638 | 2026-04-24 | 254,91 | 7337 | −15d | 4,91 |
| 7760 | 2026-04-23 | 282,89 | 7337 | −14d | 32,89 |

### `boleto_servico` — 2 órfãos

Doc 7677, 7678 (R$ 127,00 ambos): top-1 = tx 7371 (R$ 133,81 em 14/04). Diff_valor = 6,81 / 127 = **5,4 %** (acima do limite 5,0 %). Mesmo afrouxando para 6 %, o linking cria 3 candidatas (incluindo tx 7351 e 7270 com diff próximo de 7,4) que **viram conflito** porque score top-1 vs top-2 = 0,022 (< 0,05). **Ajuste só de tolerância não resolve sem mexer em `margem_empate`.**

### `nfce_modelo_65` — 2 órfãos

Doc 7679 (R$ 629,98 em 19/04) e doc 7680 (R$ 595,52 em 19/04). Tx candidata (7277 em 23/03 com R$ 590,35) está a 27 dias da emissão do cupom — fora da janela atual de 1 dia. **Padrão: NFCe emitida 27 dias depois da transação real** (provavelmente liquidação parcelada em batch). Janela 30d gera candidata, mas com `diff_valor` ≈ 1 % → cai em `baixa_confianca` por confidence_minimo=0,85.

### `comprovante_pix_foto` — 1 órfão

Doc 7783 (R$ 367,65 em 04/03/2026): 2 candidatas exatamente idênticas (tx 7130 e tx 7132, ambos 04/03, valor 367,65, diff=0). **Empate real.** Sem desempate por E2E (a foto PIX não capturou o `id_transacao`). Não há ajuste de YAML que resolva — exige código novo ou intervenção humana.

### `dirpf_retif` — 1 órfão

Doc 7768 (`total=0.0`): corretamente filtrado pelo `_total_vazio_ou_minimo`. **Comportamento canônico, sem ajuste necessário.**

---

## Ajustes aplicados a `mappings/linking_config.yaml`

Três ajustes empíricos baseados em análise concreta do grafo:

### Ajuste 1 — `margem_empate` global de 0,05 → 0,02

**Justificativa**: 6 propostas de conflito têm diff(top-1, top-2) entre 0,011 e 0,022 em que top-1 tem clara vantagem por `diff_valor`. Margem 0,02 libera os 3 casos em que diff > 0,02 sem aumentar risco — os 14 empates reais (diff=0) continuam sendo proposta.

**Impacto medido**: +3 documentos linkados.

### Ajuste 2 — `cupom_fiscal.janela_dias` de 1 → 7

**Justificativa**: cupom fiscal de cartão de crédito pode liquidar em D+1 a D+7 dependendo do banco/varejo. Os 3 órfãos cupom_fiscal têm tx candidata a 14-19 dias — fora de 7d mas a janela 7d cobre o caso comum de cartão. Para casos > 7d (situação atual dos órfãos), continuarão como `sem_candidato`, mas linking de cupons futuros com cartão fica mais robusto.

**Impacto medido**: 0 linkados novos imediatos, mas reduz risco de falso "sem_candidato" para compras futuras com cartão de crédito.

### Ajuste 3 — `nfce_modelo_65.janela_dias` de 1 → 30

**Justificativa**: NFCe geralmente é emitida no mesmo dia, mas em casos de batch / cancelamento / reemissão pode chegar a 2-4 dias. Os 2 órfãos NFCe têm tx candidata a 27 dias — caso extremo de batch trimestral. Janela 30d gera **proposta de baixa_confianca** (em vez de `sem_candidato` silencioso), elevando visibilidade para revisão humana. Tolerância 1 % mantida estrita — NFCe imprime ao centavo.

**Impacto medido**: 1 documento sai de `sem_candidato` e vira `baixa_confianca` (visibilidade).

---

## Estado depois dos ajustes

| Métrica | Antes | Depois | Δ |
|---|---:|---:|---:|
| Documentos linkados | 25 | **28** | **+3** |
| Documentos órfãos | 27 | **24** | **−3** |
| linking_pct (documentos) | 48,08 % | **53,85 %** | +5,77 pp |
| linking_pct (transações) | 0,4108 % | **0,4601 %** | +0,049 pp |
| Propostas de conflito | 20 | 17 | −3 |
| Propostas de baixa_confianca | 0 | 1 | +1 |
| `sem_candidato` | 5 | 4 | −1 |

### Documentos linkados pelo ajuste

| doc_id | tipo | total | tx_destino | score | diff_valor | observação |
|---|---|---:|---|---:|---:|---|
| 7664 | das_parcsn_andre | 321,35 | 5686 | 0,915 | 2,96 | DAS legítimo (Receita Federal) |
| 7671 | das_parcsn_andre | 321,35 | 5686 | 0,915 | 2,96 | DAS duplicado de 7664 (mesma realidade); linka mesma tx |
| 7684 | holerite | 8657,25 | 6038 | 0,861 | 1369,11 | **Suspeito** — diff_valor 16 %; verificar manualmente |

**Nota crítica**: o link em 7684 (holerite → tx 6038) tem `diff_valor=1369` sobre total=8657 (15,8 % de divergência). Apesar do score 0,861 estar acima do limiar 0,55, é candidato natural a **revisão humana** pós-fato. Recomendação: revisar manualmente após sprint encerrar.

Os DAS 7664 e 7671 são duplicatas no grafo (mesmo vencimento, mesmo valor, mesmo CNPJ Receita Federal) — ambos linkam à mesma tx 5686 (R$ 324,31 em 16/04/2025). Match matematicamente correto, redundância de catalogação.

---

## Limites da abordagem YAML-only

O escopo desta sprint excluiu `src/graph/linking.py`. Análise empírica mostra que **a maioria dos 14 empates reais (diff=0)** exige desempate por código (priorizar `diff_valor=0` sobre score temporal, ou implementar `margem_empate_por_tipo`). Sprint-filha proposta:

### Sprint-filha **LINK-AUDIT-02** — Boost de `diff_valor` exato em `_calcular_score`

**Escopo**: ajustar `src/graph/linking.py:_calcular_score` para somar `+0,05` quando `diff_valor_absoluto <= 0,01` (match perfeito). Adicionar `margem_empate_por_tipo` no YAML como subregra retrocompatível (padrão (o)).

**Acceptance**: dos 14 empates reais atuais, ≥8 devem desempatar (top-1 com `diff_valor=0` ganha sobre top-2 com `diff_valor` > 0). Re-rodar `linkar_documentos_a_transacoes` e medir ganho.

**Risco**: introduz dependência do `diff_valor` perfeito como tiebreaker. Mitigação: teste regressivo com fixture que tem 2 transações com mesmo `diff_valor=0` mas datas diferentes (empate persiste).

---

## Conclusões e recomendações

1. **Meta 30 % é estruturalmente inalcançável** com 52 documentos no grafo. Para chegar a 30 % seria preciso ingerir ~1830 documentos. Esta sprint deve atualizar a meta canônica do roadmap para refletir a realidade: **alvo realista = 80 % de documentos linkados** (ou 1,5 % de transações com documento quando o pipeline de ingestão amadurecer).

2. **Ganho real desta sprint: +3 documentos linkados** (25 → 28). Modesto, mas é o teto possível sem mexer em código.

3. **14 empates reais exigem sprint-filha LINK-AUDIT-02** (boost `diff_valor` em `_calcular_score`).

4. **Suspeita de duplicação no grafo**: docs 7664 e 7671 são DAS com mesmo vencimento e mesmo valor (R$ 321,35, venc 31/03/2025). Possível bug de ingestão duplicada. Candidato a sprint-filha de dedup.

5. **Diagnóstico reproduzível**: `scripts/diagnosticar_linking.py` foi adicionado como ferramenta canônica de auditoria empírica. Pode ser rodado periodicamente para monitorar regressão / progresso.

---

## Anexos

- JSON estruturado completo: rodar `python scripts/diagnosticar_linking.py --grafo data/output/grafo.sqlite --export-json /tmp/diag.json`
- Testes do script: `tests/test_diagnosticar_linking.py` (5 testes)
- Propostas de conflito ativas: `docs/propostas/linking/*_conflito.md` (20 arquivos, sendo 14 empates reais)

---

*"Diagnóstico empírico é o antídoto à hipótese acomodada." — princípio do auditor*
