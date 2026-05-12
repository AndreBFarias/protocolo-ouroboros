---
id: UX-AUDIT-VISUAL-2026-05-12
titulo: Re-auditoria visual ao vivo (pipeline 3-tentativas) confirmando paridade textual 85-90% pos-Onda V-3
status: backlog
concluida_em: null
prioridade: P3
data_criacao: 2026-05-12
fase: VALIDACAO_VISUAL
depende_de: []
esforco_estimado_horas: 4
origem: Plano 2026-05-12 secao Fase B (sugerido pelo auditor C2 paridade visual); auditoria textual 2026-05-12 estimou 85-90% mas faltou confronto real-vs-mockup ao vivo via scrot/claude-in-chrome/playwright.  <!-- noqa: accent -->
mockup: novo-mockup/mockups/*.html  <!-- noqa: accent -->
---

# Sprint UX-AUDIT-VISUAL-2026-05-12 -- re-auditoria visual ao vivo pos-Onda V-3

## Contexto

Auditor C2 (paridade visual textual, 2026-05-12) concluiu:
- Onda V-3 (11 sub-sprints) **toda concluída e arquivada** entre 2026-05-08 e 2026-05-12.
- ROTEIRO_TELAS_2026-05-06 **executado integralmente** via Onda U+T+Q.
- Paridade textual atingida estimada: ~85-90%.
- **Mas** a auditoria foi puramente textual (comparou `.py` vs `.html` sem renderizar).

Esta sprint **confirma empíricamente** via pipeline 3-tentativas do skill `validacao-visual`:
- Tentativa 1: scrot/import X11 (Streamlit local + browser local).
- Tentativa 2: claude-in-chrome MCP.
- Tentativa 3: playwright MCP.

Resultado esperado: confirma 85-90% OU revela gap silencioso (CSS aplicada errado, componente faltando que `grep` não pegou, etc.).

## Objetivo

1. Iniciar dashboard local em modo headless ou desktop (`./run.sh --dashboard`).
2. Para cada uma das 8 páginas-amostra (visao_geral, extrato, busca, catalogacao, projecoes, irpf, inbox, revisor):
   - Capturar screenshot real via pipeline 3-tentativas (`scrot` → `claude-in-chrome` → `playwright`).
   - Capturar mockup correspondente em `novo-mockup/mockups/*.html` (render simulado ou screenshot do browser local com o HTML aberto).
   - Side-by-side em `docs/screenshots/UX-AUDIT-VISUAL-2026-05-12/<pagina>_dashboard.png` + `<pagina>_mockup.png`.
3. Para cada par, classificar via **3 métricas objetivas combinadas**:
   - **(M1) SSIM estrutural** (`skimage.metrics.structural_similarity` em grayscale após resize comum 1280×720): peso 0.5.
   - **(M2) Histograma RGB cosine similarity** (3 canais, bins=32 cada): peso 0.3.
   - **(M3) Checklist estrutural manual** (presença de: sidebar, topbar, page-header, KPIs, tabela/gráfico principal, footer): peso 0.2 (cada componente presente = 1/N).

   Score = 0.5·SSIM + 0.3·hist_cos + 0.2·estrutural. Bandas:
   - **PARIDADE_VISUAL_ALTA** (score ≥ 0.85): aprovado.
   - **PARIDADE_VISUAL_MEDIA** (0.65 ≤ score < 0.85): aprovado com ressalvas; listar gaps.
   - **PARIDADE_VISUAL_BAIXA** (score < 0.65): reprovado; sprint-filha.
4. Relatório `docs/auditorias/AUDITORIA_PARIDADE_VISUAL_LIVE_2026-MM-DD.md` consolidando.
5. Sprints-filhas se houver gaps reais (BAIXA).

## Validação ANTES (grep -- padrão (k))

```bash
ls novo-mockup/mockups/ | wc -l    # esperado: 28+
which scrot && which import     # X11 pre-autorizado
ls docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-12.md
.venv/bin/streamlit --version
# Verificar capacidades MCP
echo "MCPs disponiveis serao carregados via ToolSearch durante a execucao"
```

Confirma: (a) mockups existem, (b) X11 tools instaladas, (c) auditoria textual de partida está presente, (d) Streamlit instalado.

## Não-objetivos (padrão (t))

- **NÃO** alterar páginas dashboard nesta sprint — apenas observar.
- **NÃO** criar mockups novos; usar os 28 canônicos.
- **NÃO** depender de network externa (claude-in-chrome e playwright podem rodar offline com tabs já carregadas).
- **NÃO** validar páginas Bem-estar dependentes de vault mob (app não republicou v1.0.0 ainda).
- **NÃO** processar mais que 8 páginas-amostra (universo total seria 28; foco estratégico nas mais críticas).

## Spec de implementação

### Loop por página

Para cada `<pagina>` em [visao_geral, extrato, busca, catalogacao, projecoes, irpf, inbox, revisor]:

#### Tentativa 1 — scrot + dashboard local

```bash
./run.sh --dashboard &
DASHBOARD_PID=$!
sleep 8

# Abrir browser na pagina
xdotool search --name "Streamlit" windowactivate
# Navegar ate <pagina> via JS (Streamlit URL params)
xdotool key ctrl+l && xdotool type "http://localhost:8501/?pagina=<pagina>" && xdotool key Return
sleep 5

# Capturar
scrot -u docs/screenshots/UX-AUDIT-VISUAL-2026-05-12/<pagina>_dashboard.png
```

#### Tentativa 2 — claude-in-chrome MCP (se Tentativa 1 falhar)

```bash
# Carregar via ToolSearch
# Tab existente ou criar novo
# Screenshot via mcp__claude-in-chrome__computer
```

#### Tentativa 3 — playwright MCP (último recurso)

```bash
# Carregar via ToolSearch
# mcp__plugin_playwright_playwright__browser_navigate http://localhost:8501/<pagina>
# mcp__plugin_playwright_playwright__browser_take_screenshot
```

#### Captura do mockup (referência)

```bash
xdg-open novo-mockup/mockups/<numero>-<pagina>.html
sleep 3
scrot -u docs/screenshots/UX-AUDIT-VISUAL-2026-05-12/<pagina>_mockup.png
```

#### Comparação (script canônico)

```python
# scripts/calcular_paridade_visual.py
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from scipy.spatial.distance import cosine

def paridade(pagina_png: Path, mockup_png: Path, checklist_estrutural: list[bool]) -> dict:
    a = np.array(Image.open(pagina_png).convert("L").resize((1280, 720)))
    b = np.array(Image.open(mockup_png).convert("L").resize((1280, 720)))
    m1 = ssim(a, b, data_range=255)

    hist_a = np.histogram(np.array(Image.open(pagina_png).convert("RGB")).reshape(-1, 3), bins=32)[0]
    hist_b = np.histogram(np.array(Image.open(mockup_png).convert("RGB")).reshape(-1, 3), bins=32)[0]
    m2 = 1 - cosine(hist_a.flatten(), hist_b.flatten())

    m3 = sum(checklist_estrutural) / len(checklist_estrutural) if checklist_estrutural else 0
    score = 0.5 * m1 + 0.3 * m2 + 0.2 * m3
    return {"ssim": m1, "hist_cos": m2, "estrutural": m3, "score": score, "banda": _classificar(score)}

def _classificar(score: float) -> str:
    if score >= 0.85: return "PARIDADE_VISUAL_ALTA"
    if score >= 0.65: return "PARIDADE_VISUAL_MEDIA"
    return "PARIDADE_VISUAL_BAIXA"
```

Critério obrigatório: **score reportado para todas as 8 páginas com todos os 3 valores intermediários**. Sem isso, sprint REPROVA — não basta "olhei e parece igual".

## Proof-of-work (padrão (u))

```bash
# 1. Dashboard iniciado
ps aux | grep streamlit | grep -v grep

# 2. Screenshots gerados
ls docs/screenshots/UX-AUDIT-VISUAL-2026-05-12/*.png | wc -l
# Esperado: 16 (8 paginas x 2 imagens)

# 3. Relatorio
ls docs/auditorias/AUDITORIA_PARIDADE_VISUAL_LIVE_*.md

# 4. Gauntlet (esta sprint nao modifica codigo)
make lint && make smoke

# 5. Cleanup
kill $DASHBOARD_PID
```

## Critério de aceitação (gate (z))

1. 8 páginas amostradas: 16 screenshots gerados.
2. Relatório markdown com classificação ALTA/MEDIA/BAIXA por página.
3. Score final declarado e comparado à estimativa textual (85-90%).
4. Sprints-filhas geradas para cada PARIDADE_VISUAL_BAIXA (se houver).
5. Pipeline 3-tentativas: pelo menos 1 das 3 funcionou para cada página (skill `validacao-visual` canônica).
6. Score por página calculado via `scripts/calcular_paridade_visual.py` — todos os 3 valores intermediários (SSIM, hist_cos, estrutural) publicados no relatório por página.
6. Gauntlet verde (nenhuma alteração de código).

## Referência

- Auditor textual C2: `docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-12.md`.
- Skill canônica: `validacao-visual`.
- Pipeline 3-tentativas: `VALIDATOR_BRIEF.md` [CORE] Capacidades visuais aplicáveis.
- Mockups: `novo-mockup/mockups/*.html`.
- Plano de origem: `~/.claude/plans/preciso-que-use-o-crispy-stroustrup.md` Fase B (achado C2).

*"Auditoria textual e suspeita fundada; auditoria visual e prova." — princípio UX-AUDIT-VISUAL-2026-05-12*
