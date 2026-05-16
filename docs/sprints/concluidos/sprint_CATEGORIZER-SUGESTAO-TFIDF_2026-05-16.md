---
id: CATEGORIZER-SUGESTAO-TFIDF
titulo: "Sugestor TF-IDF para categorias `Outros` (17.7% do extrato)"
status: concluída
concluida_em: 2026-05-16
prioridade: P2
data_criacao: 2026-05-16
fase: QUALIDADE
epico: 3
depende_de:
  - AUTO-TIPO-PROPOSTAS-DASHBOARD (recomendado — usa mesmo padrão de proposta JSON)
esforco_estimado_horas: 3
origem: "Achado P2-6 da auditoria 2026-05-15. 1031 transações (17.7%) categorizadas como 'Outros' no XLSX. Meta roadmap ≤5%. Hoje só humano + supervisor LLM v2 podem categorizar. Falta sugestão automática baseada em similaridade com regras existentes em `mappings/categorias.yaml` (111 regex)."
---

# Sprint CATEGORIZER-SUGESTAO-TFIDF

## Contexto

`src/transform/categorizer.py` aplica 111 regex de `mappings/categorias.yaml` em ordem; quando nada casa, transação vai para "Outros". 1031 transações nesse bucket significam: dono tem trabalho recorrente de catalogar manualmente.

Proposta: TF-IDF sobre as descrições já categorizadas (treino) vs descrições "Outros" (predição). Para cada "Outros", calcular vizinhos mais próximos por cosseno + retornar top-3 categorias mais frequentes. Output em `data/output/sugestoes_categoria.json`. Dashboard mostra coluna "sugestão (X% confiança)" e botão "promover para `overrides.yaml`".

## Hipótese e validação ANTES

```bash
.venv/bin/python -c "
import openpyxl
from collections import Counter
wb = openpyxl.load_workbook('data/output/ouroboros_2026.xlsx', read_only=True)
ws = wb['extrato']
cats = Counter(row[5] for row in ws.iter_rows(min_row=2, values_only=True) if row)
total = sum(cats.values())
print(f'Total: {total}')
print(f'Outros: {cats.get(\"Outros\", 0)} ({100*cats.get(\"Outros\", 0)/total:.1f}%)')
print('Top 5:', cats.most_common(5))
"
# Esperado: confirma 17.7% Outros

ls mappings/categorias.yaml && wc -l mappings/categorias.yaml
# Esperado: 111+ regex
```

## Objetivo

1. **Módulo `src/transform/categorizer_suggest.py`** (novo):
   - Função `gerar_sugestoes(transacoes: list[dict]) -> dict`:
     - Separa transações categorizadas (≠ "Outros") como treino.
     - Vetoriza descrições via TF-IDF (sklearn ou implementação simples manual).
     - Para cada transação "Outros": calcula cosseno contra todas do treino.
     - Top-K (k=5) vizinhos → vota por categoria → retorna top-3 categorias com confiança.
   - Output: dict `{transacao_id: {sugestoes: [{categoria, confianca}], top1: str, confianca_top1: float}}`.

2. **Script CLI `scripts/sugerir_categorias.py`**:
   - Lê XLSX, chama `gerar_sugestoes`, grava `data/output/sugestoes_categoria.json`.
   - Opcional: `--promover-confianca-acima 0.85` cria entries auto em `overrides.yaml`.

3. **Dashboard `src/dashboard/paginas/extrato.py`** (Edit):
   - Em transações com categoria "Outros": exibir coluna nova "Sugestão" com tooltip detalhado.
   - Botão "Aceitar sugestão" → adiciona ao `overrides.yaml` via helper.

4. **Tests**:
   - `tests/test_categorizer_suggest.py` — 4 testes (treino vs predição, similaridade Jaccard básica, dataset sintético, edge case sem treino).

## Não-objetivos

- Não tocar `categorizer.py` em runtime (sugestor é avulso).
- Não auto-aplicar sugestões sem confirmação humana.
- Não usar ML pesado (sklearn TF-IDF é OK; sem transformers).
- Não tocar `mappings/categorias.yaml` (foco em `overrides.yaml`).

## Proof-of-work runtime-real

```bash
.venv/bin/python scripts/sugerir_categorias.py
cat data/output/sugestoes_categoria.json | python -c "
import json, sys
d = json.load(sys.stdin)
print(f'{len(d)} transacoes Outros com sugestao')
alta = sum(1 for v in d.values() if v.get('confianca_top1', 0) >= 0.85)
print(f'  {alta} com confianca >= 0.85 (potencial auto-promocao)')
"

streamlit run src/dashboard/app.py
# Manualmente: cluster Financas → Extrato → filtrar categoria="Outros" → ver coluna Sugestão
```

## Acceptance

- Sugestor funcional gera JSON.
- Dashboard exibe coluna sugestão.
- Pelo menos 30% das 1031 "Outros" recebem top-1 com confiança ≥ 0.6.
- 4 testes em `tests/test_categorizer_suggest.py`.
- Pytest > 3105. Lint exit 0. Smoke 10/10.

## Padrões aplicáveis

- (l) Anti-débito — sugestões viram overrides quando aprovadas.
- (n) Defesa em camadas — TF-IDF + threshold + revisão humana.
- (e) PII never in INFO — apenas IDs no log, descrições só no JSON.

## Arquivos a criar/modificar

- `src/transform/categorizer_suggest.py` (CRIAR)
- `scripts/sugerir_categorias.py` (CRIAR)
- `src/dashboard/paginas/extrato.py` (Edit: coluna Sugestão)
- `mappings/overrides.yaml` (helper de write apenas; não Edit manual aqui)
- `tests/test_categorizer_suggest.py` (CRIAR)
- `data/output/sugestoes_categoria.json` (gerado runtime, gitignored)

---

*"Outros é dívida cognitiva acumulada; sugestor é juros pagos." — princípio da redução de carga humana*
