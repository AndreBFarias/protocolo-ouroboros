---
id: META-ROADMAP-METRICAS-AUTO
titulo: Métricas vivas no ROADMAP_ATE_PROD.md via JSON gerado
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-15
fase: SANEAMENTO
epico: 8
depende_de:
  - META-ESTADO-ATUAL-AUTO (compartilha regenerador)
esforco_estimado_horas: 1.5
origem: 'auditoria 2026-05-15. `docs/sprints/ROADMAP_ATE_PROD.md` linha 42 declara "Tipos GRADUADOS: 4"; realidade 9 (cresceu em sessão 2026-05-14). Linking 0,41% / Outros 17,7% / Pytest 2964 — todas snapshot de 2026-05-13. ROADMAP é leitura canônica (CLAUDE.md item 1) — números errados enganam priorização.'
---

# Sprint META-ROADMAP-METRICAS-AUTO

## Contexto

A tabela "Métricas globais de prontidão" no ROADMAP é referência para decisão de qual épico atacar. Hoje:

| Métrica declarada | Realidade 2026-05-15 |
|---|---|
| Tipos GRADUADOS: 4 | 9 |
| Linking documento_de: 0.41% | ? (não medido auto) |
| Categorização "Outros": 17.7% | ? (não medido auto) |
| Pytest: 2964 | 3019 |

Manter manualmente é desperdício e induz erro.

## Hipótese e validação ANTES

H1: tabela é estática no markdown:

```bash
sed -n '38,50p' docs/sprints/ROADMAP_ATE_PROD.md
# Esperado: bloco markdown com números fixos
```

H2: não há cálculo automático de linking / Outros:

```bash
grep -rln "linking_pct\|percent_outros\|cobertura_documento_de" scripts/ src/
# Esperado: 0 hits
```

## Objetivo

1. Adicionar script `scripts/gerar_metricas_prontidao.py`:
   - Lê `data/output/graduacao_tipos.json` (count GRADUADOS).
   - Calcula linking% via `sqlite3 grafo.sqlite "SELECT COUNT(*) FILTER (WHERE tipo='documento_de') * 100.0 / (SELECT COUNT(*) FROM node WHERE tipo='transacao') FROM edge"`.
   - Calcula Outros% via openpyxl no XLSX (aba `extrato`, coluna 5).
   - Pytest count via `pytest --collect-only -q`.
   - Backup grafo: bool (existe último ≤24h).
   - Transacionalidade pipeline: bool (existe pattern `db.transaction()` em `src/pipeline.py`).
   - Lockfile: bool.
   - Páginas dashboard produtivas: count via `ls src/dashboard/paginas/*.py | wc -l`.
   - Grava `data/output/metricas_prontidao.json`.
2. Markers em ROADMAP:
   ```markdown
   <!-- BEGIN_AUTO_METRICAS_PRONTIDAO -->
   ... tabela gerada ...
   <!-- END_AUTO_METRICAS_PRONTIDAO -->
   ```
3. Integrar com `scripts/regenerar_estado_atual.py` da sprint META-ESTADO-ATUAL-AUTO — chamadas conjuntas via flag `--all` ou targets Make separados.
4. `make metricas` no Makefile.

## Não-objetivos

- Não criar visualização gráfica das métricas (Sprint UX-DASH-GRADUACAO-TIPOS já mostra graduação visual).
- Não tocar épicos do ROADMAP (estrutura estável).
- Não calcular custo de cada épico (estimativas são humanas).

## Proof-of-work runtime-real

```bash
.venv/bin/python scripts/gerar_metricas_prontidao.py
cat data/output/metricas_prontidao.json | python -c "
import json, sys
m = json.load(sys.stdin)
assert m['tipos_graduados'] >= 9
assert 'linking_pct' in m
assert 'outros_pct' in m
print(f'OK tipos={m[\"tipos_graduados\"]}, linking={m[\"linking_pct\"]:.2f}%, outros={m[\"outros_pct\"]:.1f}%')
"

# Aplicar em ROADMAP
.venv/bin/python scripts/gerar_metricas_prontidao.py --aplicar-roadmap
grep -A 1 "Tipos GRADUADOS" docs/sprints/ROADMAP_ATE_PROD.md
# Esperado: número atual, não "4"
```

## Acceptance

- `data/output/metricas_prontidao.json` gerado.
- Markers em ROADMAP funcionais.
- `make metricas` regenera ambos arquivos.
- 4 testes: cada métrica isolada.
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (u) Proof-of-work runtime-real — métricas saem do banco/XLSX, não da memória.
- (y) Anti-cosmético — números são medidos, não chutados.

---

*"Métrica viva é métrica medida; métrica morta é métrica copiada." — princípio do contador honesto*
