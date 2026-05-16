---
id: UX-INFRA-SPLIT-RESTANTES
titulo: Modularizar busca.py (1162L) e analise_avancada.py (957L) -- ultimos splits do limite 800L
status: backlog
concluida_em: null
prioridade: P2
data_criacao: 2026-05-12
fase: MODULARIZACAO
depende_de: []
esforco_estimado_horas: 5
origem: "Plano 2026-05-12 secao Fase B (achado do auditor C2 paridade visual); 5 splits ja em backlog (INFRA-SPLIT-*) mas busca.py e analise_avancada.py nao tem.  <!-- noqa: accent -->"
---

# Sprint UX-INFRA-SPLIT-RESTANTES -- modularizacao busca + analise_avancada

## Contexto

Auditor C2 (paridade visual 2026-05-12) identificou 10 páginas violando o limite 800L do padrão `(h)` do VALIDATOR_BRIEF:

| Arquivo | Linhas | Spec INFRA-SPLIT existe? |
|---|---|---|
| `extrato.py` | 1497 | sim (INFRA-SPLIT-EXTRATO) |
| `revisor.py` | 1196 | sim (INFRA-SPLIT-REVISOR) |
| `busca.py` | 1162 | **NÃO** |
| `catalogacao.py` | 1048 | sim (INFRA-SPLIT-CATALOGACAO) |
| `analise_avancada.py` | 957 | **NÃO** |
| `projecoes.py` | 871 | sim (INFRA-SPLIT-PROJECOES) |
| `contas.py` | 869 | (verificar) |
| `completude.py` | 845 | (verificar) |
| `skills_d7.py` | 826 | (verificar) |
| `be_recap.py` | 825 | sim (INFRA-SPLIT-RECAP) |

Esta sprint cobre os 2 ausentes: `busca.py` e `analise_avancada.py`.

## Objetivo

1. **Split `busca.py` (1162L → ≤ 800L em arquivo principal)**:
   - Extrair componentes para `src/dashboard/paginas/busca/`:
     - `busca/__init__.py` — re-exporta `render()`.
     - `busca/filtros.py` — chip-bar + popovers.
     - `busca/resultados.py` — lista de cards.
     - `busca/facetas.py` — sidebar facetas.
     - `busca/exportar.py` — botões CSV/PDF.
2. **Split `analise_avancada.py` (957L → ≤ 800L)**:
   - Extrair sub-páginas:
     - `analise_avancada/__init__.py`.
     - `analise_avancada/fluxo.py` — sub-aba fluxo.
     - `analise_avancada/comparativo.py` — sub-aba comparativo mensal.
     - `analise_avancada/padroes.py` — sub-aba padrões detectados.
3. Manter retrocompat: `from src.dashboard.paginas.busca import render` continua funcionando (re-export em `__init__.py`).
4. Atualizar imports no `app.py` se necessário (provavelmente não muda).
5. Testes regressivos: `tests/test_dashboard_busca.py` + `tests/test_dashboard_analise_avancada.py` continuam verdes.

## Validação ANTES (grep -- padrão (k))

```bash
wc -l src/dashboard/paginas/busca.py src/dashboard/paginas/analise_avancada.py
grep -n "^def \|^class " src/dashboard/paginas/busca.py | head -20
grep -n "^def \|^class " src/dashboard/paginas/analise_avancada.py | head -20
ls docs/sprints/backlog/ | grep -i SPLIT
ls docs/sprints/concluidos/ | grep -i SPLIT
```

Confirma: (a) arquivos têm tamanho declarado, (b) há funções extraíveis para módulos, (c) não há spec duplicada em backlog/concluidos.

## Não-objetivos (padrão (t))

- **NÃO** alterar comportamento; refactor é puramente estrutural.
- **NÃO** introduzir novos componentes UI (apenas reorganizar existentes).
- **NÃO** modificar `app.py` (page registry) — re-export preserva API.
- **NÃO** tocar nos outros 8 arquivos > 800L (cobertos por specs próprias).
- **NÃO** quebrar testes existentes (eles são gate canônico para o refactor — padrão `(cc)`).

## Spec de implementação

### Estratégia padrão (mesma dos splits anteriores)

1. Identificar fronteiras claras nas funções existentes (filtros, resultados, etc.).
2. Mover cada bloco para módulo dedicado.
3. Manter `render()` em `__init__.py` orquestrando.
4. Re-exportar para manter `from src.dashboard.paginas.busca import render`.

### busca.py — partição sugerida

```
busca/
├── __init__.py        (60L) -- re-exports + render() orquestrador
├── filtros.py         (180L) -- chip-bar, popovers, contrato 3-tuple
├── resultados.py      (320L) -- lista, cards, paginacao
├── facetas.py         (240L) -- sidebar facetas, contagens
└── exportar.py        (120L) -- botoes CSV/PDF + handler
```

Soma estimada: 920L distribuídos em 5 arquivos. `busca.py` original (`mv` → `busca/__init__.py` finalmente com tamanho ≤ 80L).

### analise_avancada.py — partição sugerida

```
analise_avancada/
├── __init__.py            (50L) -- re-exports + render() escolhe sub-aba
├── fluxo.py               (300L) -- aba fluxo (sankey + tabela)
├── comparativo.py         (240L) -- aba comparativo mensal
└── padroes.py             (220L) -- aba padroes detectados
```

Soma estimada: 810L distribuídos em 4 arquivos.

## Proof-of-work (padrão (u))

```bash
# 1. Confirmar tamanho dos arquivos novos
wc -l src/dashboard/paginas/busca/*.py
wc -l src/dashboard/paginas/analise_avancada/*.py
# Esperado: cada arquivo individual <= 800L

# 2. Imports preservados (retrocompat)
.venv/bin/python -c "
from src.dashboard.paginas.busca import render as render_busca
from src.dashboard.paginas.analise_avancada import render as render_aa
print('imports OK')
"

# 3. Testes regressivos
.venv/bin/pytest tests/test_dashboard_busca.py tests/test_dashboard_analise_avancada.py -v
# Esperado: 100% verdes (refactor nao deve mudar comportamento)

# 4. Validacao visual
./run.sh --dashboard
# Acessar Busca + Analise avancada -- mesmas funcoes do antes

# 5. Gauntlet
make lint && make smoke
.venv/bin/pytest tests/ -q
```

## Critério de aceitação (gate (z))

1. `src/dashboard/paginas/busca/` e `analise_avancada/` criados com módulos partidos.
2. `wc -l src/dashboard/paginas/busca/*.py` mostra todos os arquivos ≤ 800L.
3. Imports antigos continuam funcionando (`from src.dashboard.paginas.busca import render`).
4. Testes regressivos verdes (0 mudança esperada).
5. Validação visual: paridade com estado antes do refactor (screenshot side-by-side se for paranóico).
6. Pytest baseline mantida (não cresce — refactor não adiciona testes).
7. Gauntlet verde.
8. `check_cobertura_total.py` continua exit 0.

## Referência

- Auditor C2: `docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-12.md`.
- Sprints irmãs em backlog: INFRA-SPLIT-EXTRATO, INFRA-SPLIT-REVISOR, INFRA-SPLIT-CATALOGACAO, INFRA-SPLIT-PROJECOES, INFRA-SPLIT-RECAP.
- Padrão `(h)`: limite 800L por arquivo.
- Padrão `(cc)`: refactor revela teste frágil — usar como sentinela.
- Plano de origem: `~/.claude/plans/preciso-que-use-o-crispy-stroustrup.md` Fase B.

*"Arquivo grande nao e prolixidade tecnica; e gambiarra organizacional adiada. Split bem feito e contrato preservado." — princípio UX-INFRA-SPLIT-RESTANTES*  <!-- noqa: accent -->
