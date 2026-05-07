---
id: UX-V-03
titulo: Fallback skeleton + CTA app mobile para páginas Bem-estar com dado vazio
status: concluída
prioridade: alta
data_criacao: 2026-05-07
concluida_em: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-02]
co_executavel_com: [UX-V-01, UX-V-04, UX-V-05]
esforco_estimado_horas: 5
esforco_real_horas: 4
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (P3)
commit: 3439be6
ressalvas:
  - V-02 (insight_card_html, sparkline_html) ainda não fechada -- skeletons usam apenas .skel-bloco + .kpi (componentes já presentes), sem dependência em micro-componentes V-02.
  - ui.py cresceu para 836 linhas (>800 de convenção h). ui.py é fronteira pública canônica; crescimento aceito por UX-M-02. Backlog: sprint REFAC-ui-modulo dividir por domínio.
  - Validação visual via AppTest (11/11 páginas com fallback-estado renderizado) + 2 screenshots reais (be_rotina + skills_d7) que exibem o componente em produção.
---

# Sprint UX-V-03 — Fallback estado-inicial-atrativo + CTA app mob

## Contexto

Auditoria 2026-05-07 (P3) identificou que páginas Bem-estar com dado ausente (Rotina, Skills D7, Humor sem registros, Eventos vazio, Medidas, Ciclo, Memórias, Diário, Recap, Cruzamentos) caem em callouts texto pobres do tipo "Arquivo X não encontrado, abra Editor TOML". Mockups mostram layouts ricos com 47 dias de streak, 14 alarmes, 12 cápsulas, etc.

**Origem dos dados**: app companion `Protocolo-Mob-Ouroboros` (Expo + React Native, em refundação golden-zebra ~50h restantes para v1.0.0 republicar) escreve `.md` no vault Obsidian compartilhado. Desktop lê via `obsidian/sync_rico.py` → caches em `.ouroboros/cache/*.json` → dashboard renderiza.

Decisão do dono em 2026-05-07: **redesenhar fallback como "estado inicial atrativo"** com skeleton do mockup canônico + CTA explicando o app mobile. Sem semear demo (violaria "nunca inventar dados", CLAUDE.md regra 6).

## Páginas afetadas

Páginas Bem-estar que dependem de cache populado pelo mob:

| Página | Cache esperado | Fallback atual | Mockup ref |
|---|---|---|---|
| Be / Hoje | `daily/<data>.md` + `humor.json` | Form vazio + "Sem diário/eventos hoje" | 17-bem-estar-hoje |
| Be / Humor | `.ouroboros/cache/humor-heatmap.json` | 1 célula colorida | 18-humor-heatmap |
| Be / Diário | `.ouroboros/cache/diario-emocional.json` | 1 entrada | 19-diario-emocional |
| Be / Eventos | `.ouroboros/cache/eventos.json` | 1 evento | 22-eventos |
| Be / Rotina | `.ouroboros/rotina/*.toml` | "Arquivo rotina.toml não encontrado" | 20-rotina |
| Be / Recap | múltiplos caches | KPIs zerados | 21-recap |
| Be / Memórias | `.ouroboros/cache/memorias.json` (TBD mob) | Heatmap treinos vazio | 23-memorias |
| Be / Medidas | `.ouroboros/cache/medidas.json` | "Nenhuma medida registrada ainda" | 24-medidas |
| Be / Ciclo | `.ouroboros/cache/ciclo.json` | "Nenhum registro de ciclo" | 25-ciclo |
| Be / Cruzamentos | múltiplos caches | 3 expanders + 1 gráfico vazio | 26-cruzamentos |
| Cluster Sistema / Skills D7 | `data/output/skill_d7_log.json` | Callout `.skill-instr` graceful | 14-skills-d7 |

## Objetivo

1. Criar componente canônico `fallback_estado_inicial_html(...)` em `src/dashboard/componentes/ui.py`.
2. Adicionar classes `.fallback-estado`, `.fallback-skeleton`, `.fallback-cta`, `.fallback-sync-info` em `src/dashboard/css/components.css`.
3. Substituir os callouts pobres atuais nas 11 páginas listadas por `fallback_estado_inicial_html(...)` quando o cache lido está vazio.
4. Componente renderiza:
   - **Skeleton mockup-like** do layout final (sem dados, com placeholder visual claro)
   - **Heading**: "Sem dados ainda — é normal."
   - **CTA mob**: "Use o app Ouroboros Mobile (Android) para começar a registrar [humor/eventos/medidas/...]."
   - **Comando sync**: "Após registrar no app, rode `./run.sh --sync` no desktop para puxar do vault Obsidian."
   - **Última sync**: lê `.ouroboros/cache/last_sync.json` se existir (UX-V-04 vai criar esse arquivo) e exibe "Última sync: <data> · <N arquivos>".

## Validação ANTES (grep obrigatório)

```bash
# Hipótese: nenhum componente fallback-estado canônico existe ainda
grep -rn "def fallback_estado\|fallback_estado_inicial" src/dashboard/ --include="*.py"
# Esperado: 0 matches

# Onde estão os callouts pobres hoje?
grep -rn "Arquivo.*não encontrado\|Nenhum registro\|Nenhuma medida" src/dashboard/paginas/ --include="*.py"
# Esperado: 5+ matches em be_*.py

# skill_instr existe (componente que skills_d7 usa hoje)?
grep -rn "skill-instr\|skill_instr" src/dashboard/ --include="*.py" --include="*.css"
# Esperado: matches em skills_d7.py + components.css (.skill-instr)

# Cache existente (alguns Be ja podem ter dados)
ls -la .ouroboros/cache/*.json 2>/dev/null | head -10
# Pode estar vazio ou ter alguns

# Pré-requisito UX-V-02
grep -c "def insight_card_html\|def sparkline_html" src/dashboard/componentes/ui.py
# Esperado: ≥1 (V-02 deve estar fechada)
```

Se UX-V-02 não estiver fechada, **PARAR e reportar achado-bloqueio** (esta sprint depende dos micro-componentes para o skeleton).

## Spec de implementação

### 1. Helper canônico em `ui.py`

```python
def fallback_estado_inicial_html(
    *,
    titulo: str,
    descricao: str,
    skeleton_html: str = "",
    cta_label: str = "Use o app Ouroboros Mobile",
    cta_secao: str = "geral",
    sync_info: dict | None = None,
) -> str:
    """Fallback estado-inicial-atrativo para páginas com dado vazio.

    Substitui callouts pobres do tipo 'Arquivo X não encontrado'. O dado
    de Bem-estar vem do app companion Protocolo-Mob-Ouroboros (escreve
    .md em vault Obsidian compartilhado) → desktop lê via sync_rico.py
    → caches → dashboard. Quando cache está vazio é porque o usuário
    ainda não registrou no app mobile (ou ainda não rodou ``--sync``).

    Args:
        titulo: heading do bloco (ex.: "Humor — sem registros ainda").
        descricao: parágrafo explicando como popular (ex.: "Registre seu
            humor no app Ouroboros Mobile. Cada registro vira uma célula
            colorida no heatmap acima.").
        skeleton_html: HTML opcional do skeleton (placeholder visual do
            layout final). Se vazio, omite.
        cta_label: texto do botão/link principal. Default "Use o app...".
        cta_secao: identificador da seção (ex.: "humor"). Usado em
            data-attr para tracking.
        sync_info: dict opcional ``{"data": "2026-05-07T14:32",
            "n_arquivos": 12}`` lido de ``.ouroboros/cache/last_sync.json``
            (UX-V-04). Se None ou ausente, mostra "Sincronização: nunca".
    """
    skeleton = (
        f'<div class="fallback-skeleton">{skeleton_html}</div>'
        if skeleton_html else ""
    )
    if sync_info and "data" in sync_info:
        sync_str = (
            f'Última sync: <strong>{sync_info["data"]}</strong>'
            f' · {sync_info.get("n_arquivos", "?")} arquivos lidos do vault'
        )
    else:
        sync_str = "Sincronização: <strong>nunca</strong> — rode <code>./run.sh --sync</code> após registrar no app."

    return minificar(
        f"""
        <div class="fallback-estado" data-secao="{cta_secao}">
          {skeleton}
          <div class="fallback-cta">
            <h3 class="fallback-titulo">{titulo}</h3>
            <p class="fallback-descricao">{descricao}</p>
            <p class="fallback-acao">
              <strong>{cta_label}</strong> (Android) para começar a
              registrar. O app escreve <code>.md</code> no vault Obsidian
              compartilhado; o dashboard lê via sync.
            </p>
            <p class="fallback-sync-info">{sync_str}</p>
          </div>
        </div>
        """
    )
```

Adicionar a `__all__`.

### 2. Helper de sync_info

```python
def ler_sync_info() -> dict | None:
    """Lê ``.ouroboros/cache/last_sync.json`` se existir.

    Formato esperado (criado por UX-V-04):
        {"data": "2026-05-07T14:32", "n_arquivos": 12, "fonte": "vault_obsidian"}
    Retorna ``None`` se ausente ou JSON malformado (graceful, ADR-10).
    """
    import json
    raiz = Path(__file__).resolve().parents[3]
    path = raiz / ".ouroboros" / "cache" / "last_sync.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
```

Adicionar a `__all__`.

### 3. CSS canônico em `components.css`

```css
/* ===== Fallback estado-inicial-atrativo (UX-V-03) ===== */

.fallback-estado {
    display: flex;
    flex-direction: column;
    gap: var(--sp-4);
    padding: var(--sp-5);
    background: var(--bg-surface);
    border: 1px dashed var(--border-subtle);
    border-radius: var(--r-md);
    margin: var(--sp-4) 0;
}

.fallback-skeleton {
    opacity: 0.35;
    pointer-events: none;
    user-select: none;
    border-bottom: 1px solid var(--border-subtle);
    padding-bottom: var(--sp-4);
    filter: grayscale(0.5);
}

.fallback-cta {
    display: flex;
    flex-direction: column;
    gap: var(--sp-2);
}

.fallback-titulo {
    font-family: var(--ff-mono);
    font-size: 14px;
    font-weight: 500;
    color: var(--accent-purple);
    margin: 0;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.fallback-descricao {
    font-size: 13px;
    color: var(--text-secondary);
    margin: 0;
    line-height: 1.5;
}

.fallback-acao {
    font-size: 13px;
    color: var(--text-primary);
    margin: var(--sp-2) 0 0;
    line-height: 1.5;
}
.fallback-acao code {
    background: var(--bg-inset);
    padding: 1px 6px;
    border-radius: var(--r-xs);
    font-size: 12px;
}

.fallback-sync-info {
    font-family: var(--ff-mono);
    font-size: 11px;
    color: var(--text-muted);
    margin: var(--sp-2) 0 0;
    padding-top: var(--sp-2);
    border-top: 1px solid var(--border-subtle);
}
.fallback-sync-info code {
    background: var(--bg-elevated);
    padding: 1px 4px;
    border-radius: var(--r-xs);
}
.fallback-sync-info strong {
    color: var(--text-secondary);
}
```

### 4. Migração de cada página

Para cada página da lista:

```python
# ANTES (be_medidas.py)
if df.empty:
    st.markdown(
        callout_html(
            "info",
            "Nenhuma medida registrada ainda. Crie arquivos em "
            "<vault>/medidas/<pessoa>/<data>.md com frontmatter "
            "tipo: medidas, peso, cintura, etc."
        ),
        unsafe_allow_html=True,
    )
    return

# DEPOIS
if df.empty:
    from src.dashboard.componentes.ui import (
        fallback_estado_inicial_html,
        ler_sync_info,
    )
    st.markdown(
        fallback_estado_inicial_html(
            titulo="MEDIDAS · sem registros ainda",
            descricao=(
                "Métricas físicas (peso, cintura, pressão, frequência) são "
                "capturadas no app mobile via integração Mi Fit/Garmin ou "
                "entrada manual. Cada medida vira um arquivo "
                "<code>.md</code> em <code>vault/medidas/&lt;pessoa&gt;/</code>."
            ),
            skeleton_html=(
                '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">'
                '<div class="kpi"><span class="kpi-label">PESO</span>'
                '<span class="kpi-value">--</span></div>'
                '<div class="kpi"><span class="kpi-label">CINTURA</span>'
                '<span class="kpi-value">--</span></div>'
                '<div class="kpi"><span class="kpi-label">PRESSÃO</span>'
                '<span class="kpi-value">--</span></div>'
                '</div>'
            ),
            cta_secao="medidas",
            sync_info=ler_sync_info(),
        ),
        unsafe_allow_html=True,
    )
    return
```

Cada página adapta o `titulo`, `descricao` e `skeleton_html` ao seu contexto. **Não copiar/colar — escrever skeleton específico para cada página** baseado no mockup correspondente.

### 5. Esqueleto sugerido por página

Tabela de heuristics para o subagent (não dogmático — ajustar ao mockup):

| Página | Skeleton recomendado |
|---|---|
| Humor | grid 13×7 vazio (heatmap placeholder) + 3-4 KPI cards "--" |
| Diário | 1-2 linhas de "card emocional" placeholder |
| Eventos | timeline placeholder com 2-3 entradas "--" |
| Rotina | 4 KPIs "--" + 3 colunas (Alarmes/Tarefas/Contadores) com 2 linhas placeholder cada |
| Medidas | 6 KPI cards "--" + sparkline placeholder vazia |
| Ciclo | anel SVG placeholder cinza + lista sintomas placeholder |
| Recap | 4 KPIs "--" + 1 bloco texto vazio |
| Memórias | 4 KPIs "--" + grid 4×2 cards vazios |
| Cruzamentos | 3 dropdowns placeholder + área scatter cinza |
| Skills D7 | 4 KPIs "--" + tabela placeholder 6 linhas |

Para acelerar, criar `src/dashboard/css/paginas/_skeleton.css` com helpers genéricos:

```css
.skel-bloco {
    background: linear-gradient(
        90deg,
        var(--bg-surface) 0%,
        var(--bg-elevated) 50%,
        var(--bg-surface) 100%
    );
    background-size: 200% 100%;
    animation: skel-pulse 1.5s ease-in-out infinite;
    border-radius: var(--r-sm);
    height: 1.2em;
    min-width: 60px;
    display: inline-block;
}

@keyframes skel-pulse {
    0%, 100% { background-position: 0% 0%; }
    50% { background-position: 100% 0%; }
}
```

### 6. Skills D7 — caso especial

`skills_d7.py` já tem `_fallback_graceful_html()` (callout `.skill-instr`). Substituir por `fallback_estado_inicial_html()` mantendo o ADR-10 de degradação graciosa. Skeleton: 5 KPIs + tabela placeholder de 6 skills.

## Validação DEPOIS

```bash
# Função existe em ui.py
grep -c "def fallback_estado_inicial_html\|def ler_sync_info" src/dashboard/componentes/ui.py
# Esperado: 2

# Em __all__
grep -E "fallback_estado_inicial_html|ler_sync_info" src/dashboard/componentes/ui.py | head -5

# Classes em components.css
grep -cE "^\.(fallback-estado|fallback-skeleton|fallback-cta|fallback-sync-info)" src/dashboard/css/components.css
# Esperado: ≥4

# Callouts pobres removidos das 11 páginas
grep -rn "Arquivo.*não encontrado\|Nenhum registro\|Nenhuma medida" src/dashboard/paginas/ --include="*.py"
# Esperado: 0 (ou só em docstrings, não em st.markdown)

# Migração nas páginas
grep -rln "fallback_estado_inicial_html" src/dashboard/paginas/ | wc -l
# Esperado: ≥10 (10-11 páginas migradas)

# Lint, smoke, pytest cluster
make lint
make smoke
.venv/bin/python -m pytest tests/test_be_*.py tests/test_skill_d7.py -q 2>&1 | tail -5
# Esperado: 0 fails
```

## Proof-of-work runtime-real

```bash
# Restart dashboard com vault vazio (estado normal de início)
pkill -f "streamlit run" 2>/dev/null
setsid -f sh -c '.venv/bin/python -m streamlit run src/dashboard/app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false > /tmp/dash.log 2>&1 &'
sleep 7

# Validação visual em 6 páginas com dado vazio (skill validacao-visual):
# - Be / Humor      (cluster=Bem-estar&tab=Humor)
# - Be / Rotina     (cluster=Bem-estar&tab=Rotina)
# - Be / Medidas    (cluster=Bem-estar&tab=Medidas)
# - Be / Ciclo      (cluster=Bem-estar&tab=Ciclo)
# - Skills D7       (cluster=Sistema&tab=Skills+D7)
# - Cruzamentos     (cluster=Bem-estar&tab=Cruzamentos)

# Cada screenshot deve mostrar:
# 1. Skeleton mockup-like opaco no topo (placeholder visual do layout final)
# 2. Heading "[NOME] - sem registros ainda" em accent-purple
# 3. Descrição explicando origem dos dados (mob → vault → cache)
# 4. CTA "Use o app Ouroboros Mobile..."
# 5. Linha sync-info ("Sincronização: nunca" OU "Última sync: <data>")
```

## Critério de aceitação

1. `fallback_estado_inicial_html` + `ler_sync_info` adicionados a `ui.py` + `__all__`.
2. CSS canônico para 4 classes em `components.css` + opcional `_skeleton.css`.
3. ≥10 páginas migradas — callouts pobres removidos.
4. Skills D7 mantém degradação graciosa via novo padrão.
5. `make lint && make smoke` OK.
6. `pytest cluster Bem-estar + skill_d7` verde.
7. Validação visual: 6 páginas mostram skeleton + CTA mob sem regressão.

## Não-objetivos

- NÃO criar skill `/semear-demo` (decisão do dono em 2026-05-07: viola "nunca inventar").
- NÃO escrever no vault Obsidian — esta sprint só lê (cache existe / não existe).
- NÃO mexer em páginas que já têm dados reais funcionando (Inbox, Extrato, Visão Geral, etc.).
- NÃO criar `last_sync.json` (responsabilidade UX-V-04).

## Referência

- Auditoria 2026-05-07 P3 (`docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md`).
- App mobile: `/home/andrefarias/Desenvolvimento/Protocolo-Mob-Ouroboros/STATE.md` + `ROADMAP.md` (refundação golden-zebra).
- ADR-10 — Resiliência a Dados Incompletos (preserva degradação graciosa).
- ADR-15 — Intake universal multiformato.
- VALIDATOR_BRIEF padrões: `(b)` acentuação PT-BR, `(c)` zero emojis, `(o)` subregra retrocompatível, `(u)` proof-of-work runtime real.

*"Vazio elegante revela o futuro; vazio pobre esconde a falta de plano." — princípio V-03*
