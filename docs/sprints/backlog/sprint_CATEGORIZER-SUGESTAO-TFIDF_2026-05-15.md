---
id: CATEGORIZER-SUGESTAO-TFIDF
titulo: Sugestão automática de categoria para transações "Outros" (TF-IDF similar)
status: backlog
concluida_em: null
prioridade: P2
data_criacao: 2026-05-15
fase: QUALIDADE
epico: 3
depende_de: []
esforco_estimado_horas: 3
origem: auditoria 2026-05-15. Categorização "Outros" 17,7% (~1031 transações sem categoria). Hoje supervisor LLM v2 lê multimodal ocasionalmente. Não há mecanismo de sugestão automática baseado em similaridade com regras já existentes em `mappings/categorias.yaml`. Meta roadmap ≤5%.
---

# Sprint CATEGORIZER-SUGESTAO-TFIDF

## Contexto

`mappings/categorias.yaml` tem 111 regras regex que categorizam ~82% das transações. Os 17,7% restantes vão para "Outros" + "Questionável". Hoje resolver isso requer:
- Dono lê manualmente cada uma
- OU supervisor LLM v2 (Sprint 03_v2) propõe regras
- OU ficam em "Outros" eternamente

Há uma terceira via: **similaridade TF-IDF** entre descrições "Outros" e descrições já categorizadas. Se "RAPPI BRASIL LTDA" cai em "Alimentação", e aparece "RAPPI 4324" sem categoria, a similaridade dispara sugestão "Alimentação (92%)".

## Hipótese e validação ANTES

H1: existe baseline de transações Outros no XLSX:

```bash
.venv/bin/python -c "
import openpyxl
wb = openpyxl.load_workbook('data/output/ouroboros_2026.xlsx', read_only=True)
ws = wb['extrato']
total = 0
outros = 0
for row in ws.iter_rows(min_row=2, values_only=True):
    total += 1
    if row[5] == 'Outros':
        outros += 1
print(f'Total: {total}, Outros: {outros} ({outros/total*100:.1f}%)')
"
# Esperado: ~17,7%
```

H2: scikit-learn não está em dependências (validar antes):

```bash
grep -i "scikit-learn\|sklearn" pyproject.toml requirements-lock.txt
# Esperado: 0 hits — vai precisar adicionar OU implementar TF-IDF manual
```

## Objetivo

1. Criar `src/transform/categorizer_suggest.py`:
   - Lê transações categorizadas como CORPUS (descrição + categoria).
   - Lê transações "Outros" como QUERY.
   - Calcula similaridade TF-IDF (sklearn ou implementação manual com `collections.Counter`).
   - Para cada Outros, top-3 candidatos com score.
   - Filtro: só sugere se top-1 ≥ 0.6.
2. Grava `data/output/sugestoes_categoria.json`:
   ```json
   {
     "gerado_em": "...",
     "sugestoes": [
       {"transacao_id": 7383, "descricao": "RAPPI 4324", "sugestao": "Alimentação", "confianca": 0.92, "exemplo_match": "RAPPI BRASIL"},
       ...
     ]
   }
   ```
3. Dashboard página `extrato.py` ou nova `revisor_categorias.py` exibe coluna "Sugestão (confiança)" + botão "promover para overrides.yaml".
4. Botão "promover" adiciona entry em `mappings/overrides.yaml` com chave canônica + comentário "auto-sugerido em 2026-05-15".

## Não-objetivos

- Não substituir supervisor LLM v2 (ferramenta complementar).
- Não auto-aplicar sugestões (dono aprova cada).
- Não treinar modelo ML pesado (TF-IDF clássico basta).

## Proof-of-work runtime-real

```bash
.venv/bin/python -m src.transform.categorizer_suggest --gerar
cat data/output/sugestoes_categoria.json | python -c "
import json, sys
d = json.load(sys.stdin)
print(f'{len(d[\"sugestoes\"])} sugestões geradas')
print('Top 5 mais confiáveis:')
for s in sorted(d['sugestoes'], key=lambda x: -x['confianca'])[:5]:
    print(f'  [{s[\"confianca\"]:.2f}] {s[\"descricao\"][:50]} → {s[\"sugestao\"]}')
"
# Esperado: lista >0 com sugestões plausíveis
```

## Acceptance

- `src/transform/categorizer_suggest.py` criado.
- `data/output/sugestoes_categoria.json` gerado.
- Dashboard mostra coluna sugestão.
- Botão promover funciona (idempotente em overrides.yaml).
- 5 testes em `tests/test_categorizer_suggest.py`.
- `make categorizer-sugerir` no Makefile (target adicional além da sprint META-MAKEFILE-OBSERVABILIDADE).
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (u) Proof-of-work runtime — sugestões saem do XLSX/grafo real.
- (l) Achado colateral vira sprint-filha — se sugestões revelam padrões massivos, abrir CATEGORIZADOR-REGRA-BATCH.

---

*"Categoria sugerida é regra em embrião; só vira regra quando humano confirma." — princípio do classificador honesto*
