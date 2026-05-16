---
id: ROADMAP-META-LINKING-REDEFINIR
titulo: "Redefinir meta `linking_documento_de >= 30%` (estruturalmente inalcançável)"
status: backlog
concluida_em: null
prioridade: P2
data_criacao: 2026-05-16
fase: SANEAMENTO
epico: 8
depende_de:
  - LINK-AUDIT-01 (concluída — provou que 30% é inalcançável)
esforco_estimado_horas: 0.5
origem: "achado arquitetural do executor `a51d3c56` (LINK-AUDIT-01) 2026-05-15. Meta do roadmap 'Linking documento_de >= 30%' é matematicamente impossível: 52 documentos em 6086 transações dá teto absoluto de 0,85% mesmo se todos os documentos linkarem a 1 transação cada. Para atingir 30% precisaria de ~1800 documentos no grafo, mas a fonte são notas fiscais/comprovantes que só existem para subset das compras."
---

# Sprint ROADMAP-META-LINKING-REDEFINIR

## Contexto

A meta `linking_documento_de >= 30%` no `ROADMAP_ATE_PROD.md` mede
porcentagem de TRANSAÇÕES com aresta para documento. Mas a relação é
inversa: cada documento (NFCe, holerite, DAS) linka a 1 transação. O
universo de documentos é estruturalmente menor que o de transações.

Cálculo:
- Transações: 6086 (todas as movimentações bancárias)
- Documentos: 52 (subset com NF/comprovante coletado)
- Teto absoluto: 52/6086 = 0,85% (se todos linkarem)

Meta correta deveria ser **percentual de DOCUMENTOS linkados**, não de
transações. Hoje: 53,85% (após LINK-AUDIT-01). Meta saudável: ≥80%.

## Hipótese e validação ANTES

```bash
sqlite3 data/output/grafo.sqlite "
SELECT
  (SELECT COUNT(*) FROM node WHERE tipo='documento') AS total_docs,
  (SELECT COUNT(DISTINCT src_id) FROM edge WHERE tipo='documento_de') AS docs_linkados,
  (SELECT COUNT(*) FROM node WHERE tipo='transacao') AS total_tx
"
# Esperado: confirma 52, 28, 6086
```

## Objetivo

1. Editar `docs/sprints/ROADMAP_ATE_PROD.md` tabela "Métricas globais":
   - Linha atual: `Linking documento_de | X% (Y/6086) | >=30%`
   - Linha nova: `Linking documento_de | X% (Y/52) | >=80%` (documentos linkados / total docs)
2. Editar `scripts/gerar_metricas_prontidao.py::_linking_pct`:
   - Retornar (pct_documentos_linkados, linked, total_docs) em vez de pct_transacoes.
3. Atualizar `data/output/metricas_prontidao.json` via `make metricas`.

## Não-objetivos

- Não tocar `src/graph/linking.py` (a lógica está correta).
- Não criar métrica nova; apenas redefinir denominador.

## Proof-of-work runtime-real

```bash
make metricas
cat data/output/metricas_prontidao.json | python -c "
import json, sys
m = json.load(sys.stdin)
print(f'linking pct: {m[\"linking_documento_de_pct\"]}% (denominador: {m.get(\"linking_documento_de_total_documentos\", \"?\")})')
"
# Esperado: ~54% sobre 52 documentos (não 0,46% sobre 6086 transações)
```

## Acceptance

- Tabela ROADMAP redefinida.
- Função `_linking_pct` ajustada.
- Métrica em JSON usa denominador correto.
- Pytest > 3080. Lint exit 0.

## Padrões aplicáveis

- (y) Anti-cosmético — métrica honesta vs cosmética.

---

*"Métrica impossível é desculpa eterna; métrica realista é meta de fato." — princípio do alvo alcançável*
