---
id: CATEGORIZER-SUGESTAO-AUDITORIA-RUIDO
titulo: "Sugestor TF-IDF tem ruído alto mesmo em confiança 1.0 — auditoria + threshold ajustado"
status: backlog
concluida_em: null
prioridade: P2
data_criacao: 2026-05-16
fase: QUALIDADE
epico: 3
depende_de:
  - CATEGORIZER-SUGESTAO-TFIDF (concluída — sugestor criado)
esforco_estimado_horas: 2
origem: "achado da fase 2 de CATEGORIZER-SUGESTAO-TFIDF (2026-05-16). Tentativa de promoção em batch das 319 sugestões com conf >= 0.85 revelou ruído inaceitável mesmo em conf=1.0. Exemplos detectados: 'Lab Pat e Prev do Cancer' → Natação; 'Mp *Barbearia' → Bebidas; 'Acougue Valente' → Pessoal (deveria ser Alimentação); 'Tarifa - Saque' → Transporte. Promoção em batch NÃO foi aplicada."
---

# Sprint CATEGORIZER-SUGESTAO-AUDITORIA-RUIDO

## Contexto

O sugestor TF-IDF entregue em CATEGORIZER-SUGESTAO-TFIDF (commit `bfb3999`)
gera sugestão para 863 das 1031 transações "Outros". 319 com confiança
≥0.85. Threshold sugerido pela spec original: 0.85 → auto-promoção.

**Fase 2 (2026-05-16) descobriu**: confiança ≠ accuracy. Mesmo em conf=1.0:
- `"Lab Pat e Prev do Cancer" → Natação` (deveria ser Saúde)
- `"Mp *Barbearia" → Bebidas` (deveria ser Pessoal/Higiene)
- `"Acougue Valente" → Pessoal` (deveria ser Alimentação)
- `"Tarifa - Saque" → Transporte` (deveria ser Tarifa bancária)

Causa-raiz provável (sem confirmar): TF-IDF puro casa por tokens
isolados que coincidem entre descrições não relacionadas. Token "Mp" em
"Mp *Barbearia" casa com "Mp *Outro" categorizado como Bebidas no
histórico. Sem domain knowledge, modelo amplifica viés do treino.

## Hipótese e validação ANTES

```bash
# H1: medir accuracy real em amostra de 50 sugestoes top
.venv/bin/python <<EOF
import json
sug = json.load(open('data/output/sugestoes_categoria.json'))
items = sug['sugestoes']
ordenado = sorted(items.items(), key=lambda kv: -kv[1].get('confianca_top1', 0))[:50]
# Imprime para auditoria humana:
for tx_id, item in ordenado:
    print(f"{item['confianca_top1']:.2f} {item['top1']:30s} {item['descricao'][:50]}")
EOF

# H2: medir overlap entre treino e alvo (tokens repetidos)
# (a implementar: medir Jaccard médio entre alvo "Outros" e treino correto)
```

## Objetivo

1. **Auditoria manual**: o dono revisa amostra de 50 sugestões top
   (conf >= 0.95) e marca cada uma como `correto` / `errado` /
   `parcialmente`. Output: `data/output/auditoria_sugestoes_2026-05-16.json`.

2. **Ajuste de heurística**: baseado na taxa de erro:
   - Se >30% errado em conf=0.95: threshold mínimo sobe para 0.98
   - Se erros concentrados em N categorias específicas: blacklist
     (não auto-promover Natação, Bebidas, Pessoal — confirmado errado)

3. **Melhoria do sugestor** (escopo opcional):
   - Adicionar filtro de "domínio": só sugerir categoria X se a
     transação tem token Y específico (ex: Alimentação → tokens
     `acougue`, `padaria`, `mercado`)
   - Filtro de valor: tarifas bancárias são tipicamente <R$ 10;
     compras alimentação <R$ 200

4. **UI**: dashboard "Sugestor Outros" mostra "tipo de erro estimado"
   ou cor de risco baseado em features auxiliares (token frequência,
   valor outlier, etc).

## Não-objetivos

- Não introduzir ML pesado (TF-IDF + heurísticas simples são OK).
- Não auto-promover sem revisão humana (decidido após fase 2).
- Não tocar `categorizer.py` em runtime (apenas o sugestor).

## Proof-of-work runtime-real

```bash
# Após implementação:
.venv/bin/python -m scripts.sugerir_categorias  # regera
.venv/bin/python -m scripts.promover_sugestoes_categoria --threshold 0.98
# Esperado: N candidatos cai significativamente, mas accuracy real >=85%
```

## Acceptance

- Auditoria manual documentada em
  `data/output/auditoria_sugestoes_2026-05-16.json` com 50 amostras.
- Threshold ajustado (provavelmente >= 0.98) ou blacklist categorias
  com erro alto.
- Dashboard mostra "risco de erro" para sugestões abaixo de bar mais
  alta.
- Pytest > 3145 + testes novos.

## Padrões aplicáveis

- (y) Anti-cosmético — confiança não é validação.
- (n) Defesa em camadas — threshold + domain filter + revisão humana.
- (l) Anti-débito — achado vira sprint concreta.

## Arquivos a modificar

- `src/transform/categorizer_suggest.py` (filtros de domínio)
- `src/dashboard/paginas/categorizer_sugestoes.py` (UI de risco)
- `scripts/promover_sugestoes_categoria.py` (threshold default sobe)
- `data/output/auditoria_sugestoes_2026-05-16.json` (CRIAR — humano)

---

*"Modelo sem validação humana é palpite com decimal." — princípio do confidence-vs-accuracy*
