"""CSS global do dashboard (extraído de tema.py).

Sprint ANTI-MIGUE-08: o bloco ``css_global()`` ficou com >500 linhas
e dominava ``tema.py``. Movido para módulo dedicado, re-exportado pelo
módulo ``tema`` para preservar contratos públicos
(``from src.dashboard.tema import css_global``).

Sprint UX-RD-02: o ``css_global()`` foi estendido (não reescrito) com
duas camadas novas vindas de ``novo-mockup/_shared/{tokens.css,
components.css}``:

  1. Bloco ``:root`` adicional publica os tokens hifenizados do redesign
     (``--bg-base``, ``--accent-purple``, ``--sp-*``, ``--r-*``, ``--ff-*``,
     ``--fs-*``, ``--sh-*``, ``--d7-*``, ``--humano-*``, ``--syn-*``,
     ``--diff-*``). Convive lado a lado com o ``:root`` legado
     (``--color-fundo``, ``--spacing-*``, ``--font-*``) que ainda alimenta
     14 páginas e 81 testes regressivos.

  2. Classes utilitárias do redesign (``.shell``, ``.sidebar``,
     ``.page-header``, ``.kpi``, ``.pill-d7-*``, ``.pill-humano-*``,
     ``.table`` densa, ``.drawer``, ``.skill-instr``, ``.btn-*``,
     ``.card.interactive``, ``.sprint-tag``, ``.confidence``) injetadas
     em sequência. Páginas redesenhadas (UX-RD-03+) consomem essas
     classes; páginas legadas continuam renderizando exatamente como
     antes pois nenhum seletor antigo foi tocado.

Decisão sobre fontes (ADR-07 Local First): a Sprint UX-RD-02 usa
fallback nativo (``ui-sans-serif``, ``ui-monospace``) declarado na
cascata dos tokens ``--ff-sans`` e ``--ff-mono``. Self-host em
``assets/fonts/`` está documentado em ``assets/fonts/README.md`` para
sprint futura UX-RD-02b. Sem requisição externa em runtime.

Tokens (CORES, SPACING, fontes, paddings, breakpoints) continuam
declarados em ``tema.py`` e são consumidos aqui via import explícito.
"""

from __future__ import annotations

from pathlib import Path

from src.dashboard.tema import (
    BORDA_ATIVA_PX,
    BORDA_RAIO,
    BREAKPOINT_COMPACTO,
    BREAKPOINT_MINIMO,
    CORES,
    FLUID_LABEL_KPI,
    FLUID_VALOR_KPI,
    FONTE_CORPO,
    FONTE_HERO,
    FONTE_LABEL,
    FONTE_MIN_ABSOLUTA,
    FONTE_SUBTITULO,
    FONTE_TITULO,
    PADDING_CHIP,
    PADDING_INTERNO,
    SPACING,
)

# Sprint UX-M-01: tokens.css canônico carregado via I/O (Streamlit não
# suporta @import url() em <style> dinâmico). Cópia 1:1 de
# novo-mockup/_shared/tokens.css. Espelho Python: tema.py (CORES, SPACING,
# FONTE_*). Manter sincronizado.
_RAIZ_DASHBOARD = Path(__file__).resolve().parent
_TOKENS_CSS = (_RAIZ_DASHBOARD / "css" / "tokens.css").read_text(encoding="utf-8")

# Sprint UX-M-04: shell.css canônico carregado via I/O. Substitui ~80% das
# regras que antes rodavam em runtime via setProperty('important') na
# função instalar_fix_sidebar_padding(). Specificity escopada via
# "html body [data-testid='...']" (0,1,2) vence Streamlit emotion (0,1,0)
# com !important. Manter sincronizado com shell.py se layout mudar.
_SHELL_CSS = (_RAIZ_DASHBOARD / "css" / "shell.css").read_text(encoding="utf-8")


def _root_redesign() -> str:
    """Tokens canônicos do dashboard. Sprint UX-M-01.

    Carrega ``src/dashboard/css/tokens.css`` (cópia 1:1 de
    ``novo-mockup/_shared/tokens.css``). Antes do UX-M-01 esta função
    interpolava ``CORES["..."]`` via f-string; agora usa CSS estático
    canônico, evitando duplicação de fonte de verdade.

    Espelho Python (CORES, SPACING, FONTE_* em tema.py) preservado
    para compat com 30+ páginas e 81+ testes que importam de tema.py.
    Manter sincronizado: editar tokens.css E tema.py na MESMA sprint.
    """
    return _TOKENS_CSS


def _shell_redesign() -> str:
    """Regras canônicas do shell (sidebar, topbar, main). Sprint UX-M-04.

    Carrega ``src/dashboard/css/shell.css`` que substitui ~80% das
    regras que antes rodavam em runtime via JS (setProperty) na função
    ``instalar_fix_sidebar_padding()``. CSS estático escopado via
    ``html body [data-testid="..."]`` (specificity 0,1,2 com !important)
    vence o Streamlit emotion CSS-in-JS (0,1,0).

    Anti-padrão (w) do VALIDATOR_BRIEF: JS runtime global afetando todas
    as páginas; cada nova regra setProperty era universal e quebrou
    layouts internos no commit 928628c (revertido em 2817706). Esta
    refatoração mata 46 das 56 ``setProperty`` originais.

    O JS residual em ``shell.py::instalar_fix_sidebar_padding()`` mantém
    apenas o que CSS comprovadamente não alcança: atributos HTML
    (``target='_self'``) e detecção runtime de filhos invisíveis (h=0).
    """
    return _SHELL_CSS


def _classes_redesign() -> str:
    """Classes utilitárias UX-RD-02 espelhando ``components.css``.

    Cada bloco corresponde a uma seção do components.css dos mockups.
    Páginas legadas (até UX-RD-03 ser entregue) ignoram essas classes
    pois não as referenciam. Páginas redesenhadas começam a consumi-las
    a partir de UX-RD-03.
    """
    return """
    /* ============================================================
       UX-RD-02: Classes utilitárias do redesign
       Fonte canônica: novo-mockup/_shared/components.css
       ============================================================ */

    /* ─── SHELL: sidebar + topbar + main ─── */
    .shell {
        display: grid;
        grid-template-columns: var(--sidebar-w) 1fr;
        grid-template-rows: var(--topbar-h) 1fr;
        grid-template-areas:
            "sidebar topbar"
            "sidebar main";
        min-height: 100vh;
    }
    .shell.sidebar-collapsed { grid-template-columns: var(--sidebar-collapsed) 1fr; }

    .sidebar {
        grid-area: sidebar;
        background: var(--bg-surface);
        border-right: 1px solid var(--border-subtle);
        padding: var(--sp-3) 0;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: var(--sp-2);
    }
    /* UX-U-04 + auditoria-sidebar: !important para vencer cascata
       Streamlit. Padding canônico 8px 16px (mockup) = h 36px com fs
       14px line 1.45. Antes h era 40px por padding excessivo. */
    .sidebar-brand,
    [data-testid="stSidebar"] a.sidebar-brand,
    [data-testid="stSidebar"] .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px !important;
        font-family: var(--ff-mono) !important;
        font-weight: 500 !important;
        font-size: var(--fs-14) !important;
        line-height: 1.45 !important;
        letter-spacing: 0.04em !important;
        text-transform: uppercase !important;
    }
    .sidebar-brand-glyph { width: 20px; height: 20px; color: var(--accent-purple); }
    .sidebar-search { margin: 0 var(--sp-3) var(--sp-2); position: relative; }
    .sidebar-search input {
        width: 100%;
        background: var(--bg-inset);
        border: 1px solid var(--border-subtle);
        border-radius: var(--r-sm);
        padding: 6px var(--sp-2) 6px 28px;
        font-size: var(--fs-12);
        color: var(--text-primary);
    }
    .sidebar-search-icon {
        position: absolute; left: var(--sp-2); top: 50%; transform: translateY(-50%);
        width: 14px; height: 14px; color: var(--text-muted);
    }
    .sidebar-search kbd {
        position: absolute; right: var(--sp-2); top: 50%; transform: translateY(-50%);
        font-family: var(--ff-mono); font-size: 10px;
        background: var(--bg-elevated); color: var(--text-muted);
        border: 1px solid var(--border-subtle); border-radius: var(--r-xs);
        padding: 1px 4px;
    }

    /* auditoria-sidebar-2026-05-06: cluster fontSize 14px (era 15px
       herdado de p,div,span global). H igual ao mockup (32px = 8px
       padding * 2 + 16px line-height de 11px font). */
    .sidebar-cluster {
        margin-top: var(--sp-1);
        font-size: var(--fs-13) !important;
    }
    .sidebar-cluster-header,
    [data-testid="stSidebar"] .sidebar-cluster-header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 8px 16px !important;
        font-family: var(--ff-mono) !important;
        font-size: var(--fs-11) !important;
        font-weight: 400 !important;
        line-height: 1.45 !important;
        letter-spacing: 0.10em !important;
        text-transform: uppercase !important;
        color: var(--text-muted) !important;
        overflow: visible !important;
    }
    /* Badge não deve ser cortada por overflow do parent. */
    .sidebar-cluster-header .badge {
        flex-shrink: 0 !important;
    }
    /* SVG dos cluster headers herda cor + tamanho fixo. */
    .sidebar-cluster-header svg {
        flex-shrink: 0;
        color: var(--accent-purple);
    }
    .sidebar-cluster-header .badge {
        font-family: var(--ff-mono);
        font-size: 10px;
        background: var(--accent-purple);
        color: var(--text-inverse);
        border-radius: var(--r-full);
        padding: 1px 6px;
        font-weight: 500;
        letter-spacing: 0;
    }
    /* UX-U-04 followup: Streamlit aplica CSS agressivo em
       [data-testid="stSidebar"] a (cor azul de link, sublinhado).
       Forçar !important + reset text-decoration para a sidebar item
       respeitar o token canônico do mockup (var(--text-secondary),
       sem sublinhado, sem cor de link). */
    /* SIDEBAR-CANON-FIX: cursor pointer !important para vencer cascata
       Streamlit (que pode aplicar col-resize ou default em <a>). */
    [data-testid="stSidebar"] a.sidebar-item,
    [data-testid="stSidebar"] .sidebar-item,
    .sidebar-item {
        display: flex !important;
        align-items: center;
        gap: var(--sp-2);
        padding: 4px 16px 4px 32px !important;
        font-family: var(--ff-sans) !important;
        font-size: var(--fs-13) !important;
        font-weight: 400 !important;
        line-height: 1.5 !important;
        letter-spacing: normal !important;
        text-transform: none !important;
        color: var(--text-secondary) !important;
        text-decoration: none !important;
        border-left: 2px solid transparent;
        cursor: pointer !important;
        user-select: none;
        transition: background .15s, color .15s, border-color .15s;
    }
    [data-testid="stSidebar"] a.sidebar-item:hover,
    [data-testid="stSidebar"] .sidebar-item:hover,
    .sidebar-item:hover {
        background: var(--bg-elevated) !important;
        color: var(--text-primary) !important;
        text-decoration: none !important;
        cursor: pointer !important;
    }
    [data-testid="stSidebar"] a.sidebar-item.active,
    .sidebar-item.active {
        background: linear-gradient(90deg, rgba(189,147,249,0.12), transparent 60%);
        color: var(--text-primary) !important;
        border-left-color: var(--accent-purple);
    }
    .sidebar-item .count {
        margin-left: auto;
        font-family: var(--ff-mono); font-size: 10px;
        color: var(--text-muted) !important;
    }
    /* Brand glyph link: também precisa reset de text-decoration + cursor. */
    [data-testid="stSidebar"] a.sidebar-brand,
    .sidebar-brand {
        text-decoration: none !important;
        color: var(--text-primary) !important;
        cursor: pointer !important;
    }

    /* UX-U-04 followup: topbar canônica do mockup tem 56px de altura
       (00-shell-navegacao.html mede 56px). Sem min-height, o header
       colapsa para a altura do breadcrumb (~22px) que não acomoda
       botões da topbar-actions (T-01 vai preencher). */
    .topbar {
        grid-area: topbar;
        background: var(--bg-surface);
        border-bottom: 1px solid var(--border-subtle);
        display: flex; align-items: center;
        padding: 0 var(--sp-6);
        gap: var(--sp-4);
        min-height: 56px;
    }
    .breadcrumb {
        display: flex; align-items: center; gap: var(--sp-2);
        font-family: var(--ff-mono); font-size: var(--fs-12);
        color: var(--text-muted); letter-spacing: 0.04em; text-transform: uppercase;
    }
    .breadcrumb .seg { color: var(--text-secondary); }
    .breadcrumb .seg.current { color: var(--text-primary); }
    .breadcrumb .sep { color: var(--border-strong); }
    .topbar-actions { margin-left: auto; display: flex; align-items: center; gap: var(--sp-2); }

    .main { grid-area: main; padding: var(--sp-6); overflow-y: auto; }

    /* ─── PAGE HEADER ─── */
    .page-header {
        display: flex; align-items: flex-end; justify-content: space-between;
        gap: var(--sp-4);
        padding-bottom: var(--sp-4);
        border-bottom: 1px solid var(--border-subtle);
        margin-bottom: var(--sp-6);
    }
    /* UX-U-04 followup: !important para vencer h1 { font-size: 28px !important }
       global do tema (linha 1059) e p,div,span { font-size: FONTE_CORPO } que
       deformam page-title (40 -> 28) e page-subtitle (13 -> 15). */
    .page-title,
    h1.page-title {
        font-family: var(--ff-mono) !important;
        font-size: var(--fs-40) !important;
        font-weight: 500 !important;
        letter-spacing: -0.02em !important;
        text-transform: uppercase !important;
        margin: 0 !important;
        line-height: 1 !important;
        padding: 0 !important;
        background: linear-gradient(
            180deg,
            var(--text-primary) 0%,
            color-mix(in oklch, var(--text-primary) 80%, var(--accent-purple)) 100%
        );
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .page-subtitle,
    p.page-subtitle {
        font-family: var(--ff-sans) !important;
        font-size: var(--fs-13) !important;
        font-weight: 400 !important;
        color: var(--text-secondary) !important;
        margin: var(--sp-2) 0 0 !important;
        max-width: 720px;
    }
    .page-meta {
        display: flex; gap: var(--sp-2); align-items: center; flex-wrap: wrap;
    }

    /* ─── BOTÕES ─── */
    /* auditoria-sidebar: btn canônico mockup tem fs 12px / padding 4px 8px /
       gap 6-8px, h ~27px. Antes era 31px com fs 13px. !important para
       vencer o estilo de Streamlit ``[data-testid] a`` que aplica cor
       azul de link em ``<a class="btn">`` (incluindo btn-primary). */
    .btn,
    .topbar-actions a.btn,
    .topbar-actions button.btn {
        display: inline-flex !important;
        align-items: center !important;
        gap: 8px !important;
        background: var(--bg-elevated) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--r-sm) !important;
        padding: 4px 8px !important;
        font-family: var(--ff-sans) !important;
        font-size: var(--fs-12) !important;
        font-weight: 500 !important;
        text-decoration: none !important;
        line-height: 1.45 !important;
        transition: border-color .15s, background .15s, transform .12s;
    }
    .btn:active,
    .topbar-actions a.btn:active { transform: translateY(1px); }
    .btn:hover,
    .topbar-actions a.btn:hover {
        border-color: var(--border-strong) !important;
        background: var(--bg-surface) !important;
    }
    .btn-primary,
    .topbar-actions a.btn-primary,
    .topbar-actions button.btn-primary {
        background: var(--accent-purple) !important;
        color: var(--text-inverse) !important;
        border-color: var(--accent-purple) !important;
    }
    .btn-primary:hover,
    .topbar-actions a.btn-primary:hover { filter: brightness(1.08); }
    .btn-ghost { background: transparent; }
    .btn-danger {
        background: transparent;
        color: var(--accent-red);
        border-color: rgba(255,85,85,0.30);
    }
    .btn-sm { padding: 4px 8px; font-size: var(--fs-12); }
    .btn-icon { padding: 6px; }
    .btn-icon svg { width: 14px; height: 14px; }

    /* ─── CARDS ─── */
    .card {
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: var(--r-md);
        padding: var(--sp-4);
        transition: border-color .18s, transform .18s, box-shadow .18s;
    }
    .card.interactive { cursor: pointer; }
    .card.interactive:hover {
        border-color: var(--accent-purple);
        transform: translateY(-1px);
        box-shadow: 0 6px 20px -10px rgba(189,147,249,0.30);
    }
    .card-compact { padding: var(--sp-3); }
    .card-head {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: var(--sp-3);
    }
    .card-title {
        font-size: var(--fs-11);
        font-weight: 500;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-secondary);
        margin: 0;
    }

    /* ─── KPI tile ─── */
    .kpi {
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: var(--r-md);
        padding: var(--sp-3) var(--sp-4);
        min-width: var(--kpi-w);
        height: var(--kpi-h);
        display: flex; flex-direction: column; justify-content: space-between;
        transition: border-color .18s, transform .18s;
        position: relative; overflow: hidden;
    }
    .kpi::after {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, transparent, var(--accent-purple), transparent);
        opacity: 0; transition: opacity .18s;
    }
    .kpi:hover { border-color: var(--border-strong); transform: translateY(-1px); }
    .kpi:hover::after { opacity: 0.5; }
    .kpi-label {
        font-size: var(--fs-11); font-weight: 500;
        letter-spacing: 0.08em; text-transform: uppercase;
        color: var(--text-muted);
    }
    .kpi-value {
        font-family: var(--ff-mono);
        font-size: var(--fs-32); font-weight: 500;
        letter-spacing: -0.02em;
        font-variant-numeric: tabular-nums;
        line-height: 1;
    }
    .kpi-delta {
        font-family: var(--ff-mono); font-size: var(--fs-12);
        display: inline-flex; align-items: center; gap: 4px;
    }
    .kpi-delta.up    { color: var(--accent-green); }
    .kpi-delta.down  { color: var(--accent-red); }
    .kpi-delta.flat  { color: var(--text-muted); }

    /* ─── PILLS / BADGES ─── */
    /* UX-U-04 followup: !important para vencer p,div,span { font-size: 15px }
       global (FONTE_CORPO). Pills canônicas ficam em 11px JetBrains Mono. */
    .pill,
    span.pill {
        display: inline-flex !important; align-items: center; gap: 4px;
        font-family: var(--ff-mono) !important;
        font-size: var(--fs-11) !important;
        font-weight: 500 !important;
        letter-spacing: 0.04em !important;
        text-transform: uppercase !important;
        padding: 2px 8px !important;
        border-radius: var(--r-full);
        border: 1px solid transparent;
        white-space: nowrap;
    }
    .pill-d7-graduado {
        background: rgba(107,142,127,0.15);
        color: var(--d7-graduado);
        border-color: rgba(107,142,127,0.30);
    }
    .pill-d7-calibracao {
        background: rgba(241,250,140,0.10);
        color: var(--d7-calibracao);
        border-color: rgba(241,250,140,0.25);
    }
    .pill-d7-regredindo {
        background: rgba(255,184,108,0.10);
        color: var(--d7-regredindo);
        border-color: rgba(255,184,108,0.30);
    }
    .pill-d7-pendente {
        background: rgba(108,111,125,0.15);
        color: var(--d7-pendente);
        border-color: rgba(108,111,125,0.30);
    }

    .pill-humano-aprovado {
        background: rgba(107,142,127,0.15);
        color: var(--humano-aprovado);
        border-color: rgba(107,142,127,0.30);
    }
    .pill-humano-rejeitado {
        background: rgba(255,85,85,0.10);
        color: var(--humano-rejeitado);
        border-color: rgba(255,85,85,0.30);
    }
    .pill-humano-revisar {
        background: rgba(241,250,140,0.10);
        color: var(--humano-revisar);
        border-color: rgba(241,250,140,0.25);
    }
    .pill-humano-pendente {
        background: rgba(108,111,125,0.15);
        color: var(--humano-pendente);
        border-color: rgba(108,111,125,0.30);
    }

    /* UX-U-04 followup: !important para vencer cascata global. */
    .sprint-tag,
    span.sprint-tag {
        display: inline-flex !important; align-items: center; gap: 4px;
        font-family: var(--ff-mono) !important;
        font-size: var(--fs-11) !important;
        font-weight: 500 !important;
        letter-spacing: 0.04em !important;
        text-transform: uppercase !important;
        color: var(--text-muted) !important;
        padding: 2px 6px !important;
        border: 1px solid var(--border-subtle);
        border-radius: var(--r-xs);
        background: var(--bg-inset);
    }
    .sprint-tag::before { content: ""; font-size: 8px; color: var(--accent-purple); }

    .confidence {
        display: inline-flex; align-items: center; gap: 4px;
        font-family: var(--ff-mono);
        font-size: var(--fs-11);
        padding: 2px 6px;
        border-radius: var(--r-xs);
        font-variant-numeric: tabular-nums;
    }
    .confidence-bar {
        display: inline-block;
        width: 36px; height: 4px;
        background: var(--bg-inset);
        border-radius: var(--r-full);
        overflow: hidden;
        position: relative;
    }
    .confidence-bar > span {
        position: absolute; left: 0; top: 0; bottom: 0;
        background: var(--d7-graduado);
    }

    /* ─── TABELA DENSA ─── */
    .table {
        width: 100%;
        border-collapse: collapse;
        font-size: var(--fs-13);
    }
    .table th, .table td {
        height: var(--row-h);
        padding: 0 var(--sp-3);
        text-align: left;
        border-bottom: 1px solid var(--border-subtle);
        vertical-align: middle;
        white-space: nowrap;
    }
    .table thead th {
        position: sticky; top: 0;
        background: var(--bg-surface);
        font-family: var(--ff-mono);
        font-size: var(--fs-11);
        font-weight: 500;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--text-muted);
        border-bottom: 1px solid var(--border-strong);
    }
    .table tbody tr:hover { background: var(--bg-elevated); }
    .table tbody tr.selected { background: rgba(189,147,249,0.08); }
    .table .col-num {
        text-align: right;
        font-family: var(--ff-mono);
        font-variant-numeric: tabular-nums;
    }
    .table .col-mono { font-family: var(--ff-mono); }

    /* ─── DRAWER (painel lateral deslizante) ─── */
    .drawer-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.40); z-index: 39; }
    .drawer {
        position: fixed; top: 0; right: 0; bottom: 0;
        width: var(--drawer-w);
        background: var(--bg-elevated);
        border-left: 1px solid var(--border-subtle);
        box-shadow: var(--sh-xl);
        z-index: 40;
        display: flex; flex-direction: column;
    }
    .drawer-head {
        display: flex; align-items: center; justify-content: space-between;
        padding: var(--sp-4);
        border-bottom: 1px solid var(--border-subtle);
    }
    .drawer-tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border-subtle); }
    .drawer-tab {
        padding: var(--sp-3) var(--sp-4);
        font-size: var(--fs-12); font-weight: 500;
        color: var(--text-secondary);
        border-bottom: 2px solid transparent;
        cursor: pointer;
        background: transparent; border-top: none; border-left: none; border-right: none;
    }
    .drawer-tab.active { color: var(--text-primary); border-bottom-color: var(--accent-purple); }
    .drawer-body { padding: var(--sp-4); overflow-y: auto; flex: 1; }

    /* ─── INSTRUÇÃO SKILL (Inbox) ─── */
    .skill-instr {
        border: 1px solid var(--border-subtle);
        border-radius: var(--r-md);
        background: var(--bg-inset);
        padding: var(--sp-4);
        font-family: var(--ff-mono);
        font-size: var(--fs-13);
        line-height: 1.6;
    }
    .skill-instr h4 {
        margin: 0 0 var(--sp-3);
        font-size: var(--fs-11);
        letter-spacing: 0.10em;
        text-transform: uppercase;
        color: var(--accent-purple);
    }
    .skill-instr code {
        background: var(--bg-elevated);
        border: 1px solid var(--border-subtle);
        border-radius: var(--r-xs);
        padding: 2px 6px;
        color: var(--accent-pink);
    }
    .skill-instr ol { margin: 0; padding-left: var(--sp-5); }
    .skill-instr .why {
        margin-top: var(--sp-3);
        padding-top: var(--sp-3);
        border-top: 1px dashed var(--border-subtle);
        color: var(--text-muted);
        font-size: var(--fs-12);
    }

    /* ─── COMPLETUDE (UX-RD-10) — matriz tipo × mês ─── */
    .completude-matriz-card {
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: var(--r-md);
        padding: var(--sp-4);
        margin-bottom: var(--sp-4);
    }
    .completude-matriz-grid {
        display: grid;
        gap: 3px;
        font-family: var(--ff-mono);
        font-size: 10px;
    }
    .completude-matriz-h {
        color: var(--text-muted);
        padding: 4px;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .completude-matriz-rotulo {
        color: var(--text-muted);
        padding: 8px 4px;
        text-align: right;
        font-size: 11px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .completude-cell {
        aspect-ratio: 1.5;
        border-radius: var(--r-xs);
        display: grid;
        place-items: center;
        cursor: pointer;
        position: relative;
        font-size: 10px;
        color: var(--bg-base);
        font-weight: 500;
        text-decoration: none;
        transition: transform 90ms ease;
    }
    .completude-cell-full    { background: var(--d7-graduado); }
    .completude-cell-partial { background: var(--accent-yellow); color: var(--bg-base); }
    .completude-cell-missing { background: var(--accent-red); color: var(--bg-base); }
    .completude-cell-empty   {
        background: var(--bg-inset); color: var(--text-muted); cursor: default;
    }
    .completude-cell:hover:not(.completude-cell-empty) {
        transform: scale(1.08);
        z-index: 1;
        box-shadow: 0 0 0 2px var(--accent-purple);
    }
    .completude-matriz-legenda {
        display: flex;
        gap: var(--sp-3);
        font-family: var(--ff-mono);
        font-size: 11px;
        color: var(--text-muted);
        margin-top: var(--sp-3);
    }
    .completude-matriz-legenda .dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 2px;
        vertical-align: middle;
        margin-right: 4px;
    }
    .completude-secao-titulo {
        font-family: var(--ff-mono);
        font-size: 12px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-secondary);
        margin: var(--sp-4) 0 var(--sp-3);
    }

    /* ─── REVISOR (UX-RD-10) — cards de divergência 4-way ─── */
    .revisor-card {
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: var(--r-md);
        padding: var(--sp-3) var(--sp-4);
        margin-bottom: var(--sp-3);
        position: relative;
        transition: box-shadow 120ms ease;
    }
    .revisor-card[data-revisor-foco="1"] {
        box-shadow: 0 0 0 2px var(--accent-purple);
    }
    .revisor-card-fontes {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: var(--sp-3);
        margin-top: var(--sp-3);
    }
    .revisor-fonte {
        background: var(--bg-inset);
        border-left: 3px solid var(--border-subtle);
        border-radius: var(--r-sm);
        padding: var(--sp-2) var(--sp-3);
        min-height: 64px;
        font-family: var(--ff-mono);
        font-size: var(--fs-12);
    }
    .revisor-fonte-etl    { border-left-color: var(--accent-green); }
    .revisor-fonte-opus   { border-left-color: var(--accent-purple); }
    .revisor-fonte-grafo  { border-left-color: var(--accent-yellow); }
    .revisor-fonte-humano { border-left-color: var(--accent-pink); }
    .revisor-fonte-rotulo {
        font-size: 10px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-muted);
        margin-bottom: 4px;
    }
    .revisor-fonte-valor {
        color: var(--text-primary);
        word-break: break-word;
    }
    .revisor-fonte-valor.diverge {
        background: var(--diff-added-bg, rgba(255, 121, 198, 0.08));
        padding: 2px 4px;
        border-radius: var(--r-xs);
    }
    .revisor-card-titulo {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--sp-3);
        font-family: var(--ff-mono);
        font-size: var(--fs-12);
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--text-secondary);
    }
    .revisor-card-dimensao {
        font-weight: 500;
        color: var(--text-primary);
    }
    """


def css_global() -> str:
    """Retorna bloco CSS global para o dashboard.

    Sprint UX-RD-02: estende o ``css_global()`` original com (1) bloco
    ``:root`` adicional dos tokens hifenizados (``--bg-base``,
    ``--accent-*``, ``--sp-*``, ``--r-*``, ``--ff-*``, ``--fs-*``,
    ``--sh-*``, ``--d7-*``, ``--humano-*``) e (2) classes utilitárias do
    redesign (``.shell``, ``.sidebar``, ``.kpi``, ``.pill-*``,
    ``.table`` densa, ``.drawer``, ``.skill-instr``, ``.btn-*``,
    ``.card.interactive``, ``.page-header``, ``.sprint-tag``,
    ``.confidence``). Tokens e regras legados (``--color-*``,
    ``--spacing-*``, regras [data-testid=*]) preservados intactos para
    zero regressão nas 14 páginas legadas e nos 81 testes existentes
    em ``test_dashboard_tema.py``, ``test_ux_tokens.py``,
    ``test_dashboard_components.py``.

    Sprint 92c (legado): publica CSS custom properties em ``:root`` a
    partir dos tokens Python já existentes (``CORES``, ``SPACING``,
    fontes). Helpers HTML (callout, progress_inline, metric_semantic,
    breadcrumb) referenciam esses tokens via ``var(--color-*)`` em vez
    de interpolar hex, permitindo que temas futuros sobrescrevam apenas
    o bloco ``:root`` sem tocar em helper algum. Componentes Plotly
    continuam usando hex direto pois JSON inline não resolve ``var()``.
    """
    bloco_redesign_root = _root_redesign()
    bloco_redesign_classes = _classes_redesign()
    bloco_shell_redesign = _shell_redesign()
    return f"""
    <style>
    /* SIDEBAR-CANON-FIX (2026-05-06): cor de fundo do body é bg-base
       (#0e0f15), não bg-surface (#1a1d28). Sidebar mantém bg-surface
       para destaque visual. Antes: stApp herdava cor errada. */
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
        background-color: #0e0f15 !important;
    }}

    /* =========================================================
       SIDEBAR-CANON-FIX-2 (2026-05-06): paridade visual definitiva
       com mockup 00-shell-navegacao.html. Espelha:
       (1) header Streamlit oculto (mockup não tem cabeçalho extra),
       (2) sidebar começa em x=0,y=0 (sem padding interno do wrapper),
       (3) sidebar SEM scroll vertical próprio — scroll é da página
           inteira (overflow herda do body, não da sidebar),
       (4) badge não cortada (overflow visible no header).
       Estas regras vêm ANTES das outras para vencer a cascata local
       e a herança Streamlit. ============================================ */
    header[data-testid="stHeader"],
    [data-testid="stHeader"] {{
        display: none !important;
    }}
    [data-testid="stAppViewContainer"] > section.stMain,
    [data-testid="stMain"] {{
        padding-top: 0 !important;
    }}
    /* Sidebar wrapper: SEM padding, SEM overflow vertical próprio,
       altura natural (cresce com conteúdo, scroll é da página). */
    [data-testid="stSidebar"] {{
        height: auto !important;
        max-height: none !important;
        min-height: 100vh !important;
        overflow-y: visible !important;
        overflow-x: hidden !important;
        padding: 0 !important;
        margin: 0 !important;
    }}
    [data-testid="stSidebarContent"],
    [data-testid="stSidebar"] [data-testid="stSidebarContent"],
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebar"] > div > div,
    [data-testid="stSidebar"] section {{
        padding: 0 !important;
        margin: 0 !important;
        height: auto !important;
        max-height: none !important;
        overflow-y: visible !important;
        overflow-x: hidden !important;
        width: 240px !important;
        min-width: 240px !important;
        max-width: 240px !important;
        box-sizing: border-box !important;
    }}
    /* Streamlit envolve nosso aside em vários containers (stVerticalBlock,
       stElementContainer, stMarkdown, stMarkdownContainer). Todos com padding
       ou margin default que empurram o aside para x=26. Zeramos TUDO. */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"],
    [data-testid="stSidebar"] [data-testid="stElementContainer"],
    [data-testid="stSidebar"] [data-testid="stMarkdown"],
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{
        padding: 0 !important;
        margin: 0 !important;
        gap: 0 !important;
        width: 240px !important;
        max-width: 240px !important;
        overflow-x: hidden !important;
        overflow-y: visible !important;
        box-sizing: border-box !important;
    }}
    /* aside.sidebar começa em x=0, y=0 absoluto da viewport. Streamlit
       wrapper aplica padding 16px que não conseguimos vencer via
       cascata de classe emotion (mudam a cada release). Solução:
       margin negativa puxa o aside de volta ao canto + width >= 240px. */
    [data-testid="stSidebar"] aside.sidebar,
    aside.sidebar.ouroboros-sidebar-redesign {{
        position: relative !important;
        width: 240px !important;
        max-width: 240px !important;
        margin: -16px 0 0 -16px !important;
        padding: 12px 0 !important;
        height: auto !important;
        max-height: none !important;
        overflow-y: visible !important;
        overflow-x: hidden !important;
        box-sizing: border-box !important;
    }}
    /* Badge nunca cortada. */
    .sidebar-cluster-header {{
        overflow: visible !important;
    }}
    .sidebar-cluster-header .badge {{
        flex-shrink: 0 !important;
        margin-right: 12px !important;
    }}

    {bloco_redesign_root}
    :root {{
        --color-fundo: {CORES["fundo"]};
        --color-card-fundo: {CORES["card_fundo"]};
        --color-texto: {CORES["texto"]};
        --color-texto-sec: {CORES["texto_sec"]};
        --color-positivo: {CORES["positivo"]};
        --color-negativo: {CORES["negativo"]};
        --color-alerta: {CORES["alerta"]};
        --color-destaque: {CORES["destaque"]};
        --color-neutro: {CORES["neutro"]};
        --color-info: {CORES["info"]};
        --color-superfluo: {CORES["superfluo"]};
        --color-obrigatorio: {CORES["obrigatorio"]};   /* noqa: accent (CSS ident ASCII) */
        --color-questionavel: {CORES["questionavel"]}; /* noqa: accent (CSS ident ASCII) */
        --spacing-xs: {SPACING["xs"]}px;
        --spacing-sm: {SPACING["sm"]}px;
        --spacing-md: {SPACING["md"]}px;
        --spacing-lg: {SPACING["lg"]}px;
        --spacing-xl: {SPACING["xl"]}px;
        --spacing-xxl: {SPACING["xxl"]}px;
        --font-min: {FONTE_MIN_ABSOLUTA}px;
        --font-label: {FONTE_LABEL}px;
        --font-corpo: {FONTE_CORPO}px;
        --font-subtitulo: {FONTE_SUBTITULO}px;
        --font-titulo: {FONTE_TITULO}px;
        --font-hero: {FONTE_HERO}px;
        --padding-interno: {PADDING_INTERNO}px;
        --padding-chip: {PADDING_CHIP}px;
        --borda-raio: {BORDA_RAIO}px;
        --borda-ativa-px: {BORDA_ATIVA_PX}px;
    }}
    {bloco_redesign_classes}
    html, body, .stApp, [data-testid="stAppViewContainer"] {{
        font-size: {FONTE_CORPO}px;
    }}
    /* Sprint 76: floor absoluto de {FONTE_MIN_ABSOLUTA}px. Impede que regras
       herdadas ou inline reduzam texto abaixo do legível. Aplicado via
       seletor universal sem !important para respeitar hierarquia quando
       a classe alvo define valor >= {FONTE_MIN_ABSOLUTA}px. */
    [data-testid="stAppViewContainer"] p,
    [data-testid="stAppViewContainer"] span,
    [data-testid="stAppViewContainer"] li,
    [data-testid="stAppViewContainer"] label {{
        font-size: max({FONTE_MIN_ABSOLUTA}px, 1em);
    }}
    .js-plotly-plot .plotly text {{
        font-size: {FONTE_MIN_ABSOLUTA}px !important;
    }}
    /* Sprint 76 + Sprint UX-116: padding interno generoso nos retângulos
       das páginas, evitando texto colado na borda em Grafo/IRPF/Metas/Extrato.
       UX-116 substitui o shorthand da Sprint 76 por 4 declarações explícitas
       padding-{{top,right,bottom,left}} para tornar o contrato testável
       direção por direção e garantir respiro nos 4 lados em todas as abas. */
    .main .block-container {{
        padding-top: {PADDING_INTERNO}px !important;
        padding-right: {PADDING_INTERNO}px !important;
        padding-bottom: {PADDING_INTERNO}px !important;
        padding-left: {PADDING_INTERNO}px !important;
    }}
    /* Sprint UX-125 AC1: body 100% horizontal -- Streamlit por padrão aplica
       max-width restritivo (~736px ou 1200px conforme tema) ao
       .block-container, deixando faixa preta à direita do conteúdo em
       monitores wide. Forçamos max-width: 100% e width: 100% para que o
       conteúdo ocupe toda a viewport. Regra separada do bloco de padding
       (acima) para preservar regex de testes legados (test_ux_tokens
       ::test_css_global_declara_padding_bloco) que casa o seletor seguido
       imediatamente de uma declaração de padding. Aplicado também no
       testid moderno [data-testid="stMainBlockContainer"] (>=1.32). */
    .main .block-container,
    [data-testid="stMainBlockContainer"] {{
        max-width: 100% !important;
        width: 100% !important;
    }}
    .block-container {{ padding-top: {SPACING["xl"]}px; }}
    /* Sprint UX-115 + Sprint UX-119 AC14 (unificação de cor): o container
       externo do conteúdo principal ([data-testid="stMain"]) ficava em
       cor de fundo Dracula (color-fundo) por default, criando faixa
       vertical à esquerda e faixa inferior em volta do bloco interno.
       UX-115 pintou com literal próximo (gambiarra); UX-119 troca por
       var(--color-card-fundo) -- token CORES['card_fundo']. Resultado:
       stMain e sidebar ficam exatamente no mesmo tom, eliminando a
       diferença de 1 ponto no canal verde que o dono detectou.
       Sobrescreve apenas este seletor; não afeta fundo da app inteira
       (html/body continuam regidos por --color-fundo). */
    [data-testid="stMain"] {{
        background-color: var(--color-card-fundo);
    }}
    /* Sprint UX-118: faixas escuras residuais (#282A36 padrão Dracula) que
       apareciam no contorno do app são cobertas trocando o fundo do
       container raiz [data-testid="stApp"] por --color-card-fundo
       (#44475A). Tokens CORES['fundo'] e DRACULA['background'] permanecem
       intocados; apenas o seletor stApp passa a usar o tom card. */
    [data-testid="stApp"] {{
        background-color: var(--color-card-fundo) !important;
    }}
    /* Sprint UX-119 AC2: status widget e toast da Streamlit (top warning bar
       que mostra avisos como `--no-sandbox`, deprecation warnings, etc.)
       herdam fundo escuro #282A36 e destoam da paleta unificada. Pintamos
       com var(--color-card-fundo) para alinhar ao restante do app.
       stStatusWidget cobre o status de execução (canto superior direito);
       stToast cobre toasts efêmeros; stAlertContainer cobre alertas em
       containers; stHeader cobre a top bar onde a deprecation aparece. */
    [data-testid="stStatusWidget"],
    [data-testid="stToast"],
    [data-testid="stAlertContainer"],
    [data-testid="stHeader"] {{
        background-color: var(--color-card-fundo) !important;
    }}
    /* Sprint UX-119 AC3: selectboxes ganham altura mínima 44px e proteção
       contra glyphs cortados (`Mâs`, `2A26-04`, `Todos` apareciam mutilados
       pela altura justa). nowrap + overflow:hidden + text-overflow:ellipsis
       no VALOR SELECIONADO impedem quebra de palavra; o dropdown aberto
       usa overflow:visible herdado para não truncar opções. */
    [data-testid="stSelectbox"] > div > div,
    [data-testid="stSelectbox"] div[role="combobox"] {{
        min-height: 44px;
        white-space: nowrap;
    }}
    [data-testid="stSelectbox"] div[role="combobox"] > div {{
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    /* Sprint UX-125 AC5: input de busca da sidebar ganha altura mínima
       44px (mesma altura dos selectboxes) para alinhamento visual e
       acessibilidade WCAG 2.1 (target tátil mínimo). Largura 100% do
       container já é default do Streamlit; reforçamos para evitar
       regressão em temas customizados. */
    [data-testid="stSidebar"] [data-testid="stTextInput"] > div > div {{
        min-height: 44px;
    }}
    /* Sprint UX-119 AC6: separador vertical roxo 2px entre sidebar e body.
       border-right adiciona linha visual sem mudar background (preservando
       regra UX-116 que define background-color e padding). Usar
       var(--color-destaque) (#BD93F9) garante coerência com a barra das
       tabs (UX-118) e com o token global de destaque. */
    [data-testid="stSidebar"] {{
        border-right: 2px solid var(--color-destaque);
    }}
    /* Sprint UX-119 AC7: header das páginas ganha respiro adicional
       (~48px) entre o título H1 e o conteúdo abaixo. Substitui o pedido
       informal "/n /n /n" do dono por margin-bottom estável no h1 dentro
       do main block container. Mantém PADDING_INTERNO (24px) original
       como padding do container e adiciona margin-bottom no título. */
    [data-testid="stMainBlockContainer"] h1 {{
        margin-bottom: {SPACING["xl"]}px !important;
    }}
    /* Sprint UX-119 AC10/11: container de chips e sugestões da página
       Busca Global (paginas/busca.py) usa flex-wrap + nowrap para garantir
       que nenhuma palavra quebra ao meio. Quando não couber numa linha, o
       botão inteiro vai para baixo. min-width 140px alinha visualmente os
       8 chips de tipo (Holerite/NF/DAS/Boleto/IRPF/Recibo/Comprovante/
       Contracheque) e as sugestões de autocomplete. As classes
       .ouroboros-chips-container e .ouroboros-sugestoes-container são
       adotadas em paginas/busca.py num passo posterior; por ora pintam
       qualquer container que receba a class. */
    .ouroboros-chips-container,
    .ouroboros-sugestoes-container {{
        display: flex;
        flex-wrap: wrap;
        gap: {SPACING["sm"]}px;
    }}
    .ouroboros-chips-container [data-testid="stButton"] > button,
    .ouroboros-sugestoes-container [data-testid="stButton"] > button {{
        flex: 0 0 auto;
        min-width: 140px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    /* Sprint UX-119 AC13: padronização global de stButton. Cards
       "DOCUMENTOS POR TIPO" da Catalogação e botões em geral ganham
       altura/largura mínima e proteção contra quebra de palavra. Quando
       o container não couber, o flex-wrap externo joga a linha inteira
       para baixo (regra do AC10/11). Aplicamos no seletor universal de
       stButton para cobrir todas as páginas de uma vez. */
    [data-testid="stButton"] > button {{
        min-height: 44px;
        min-width: 140px;
        white-space: nowrap;
    }}
    /* Sprint UX-118: logo da sidebar sai de 64x65 renderizado (apertado
       pela largura útil da sidebar) para ~120px com proporção da arte
       original (724x733px). Sprint UX-126 AC5: width/height/aspect-ratio
       agora carregam !important para vencer o atributo HTML width="64"
       que o caller (app.py) ainda passa por compatibilidade com versões
       legadas; o tamanho efetivo deve ser 120px independente do width
       atribuído ao <img>. */
    .ouroboros-logo-img {{
        width: 120px !important;
        height: auto !important;
        aspect-ratio: 724 / 733 !important;
        max-width: 120px !important;
        margin: 0 auto !important;
        display: block !important;
    }}
    /* Sprint UX-126 AC2: padding simétrico ao redor dos cards de tipos
       de documento. O container de st.columns ([data-testid=
       "stHorizontalBlock"]) recebe margin-top e margin-bottom iguais
       para que a distância entre o título "Documentos por tipo"
       (subtitulo_secao_html) e os cards seja igual à distância entre
       os cards e o divisor <hr> abaixo. */
    [data-testid="stHorizontalBlock"] {{
        margin-top: {SPACING["md"]}px;
        margin-bottom: {SPACING["md"]}px;
    }}
    /* SIDEBAR-CANON-FIX (2026-05-06): wrapper Streamlit precisa de
       box-sizing: border-box + overflow-x: hidden para não criar barra
       de rolagem horizontal no rodapé. Antes: stSidebarContent tinha
       padding default 16px sem box-sizing -> width effective 256px ->
       overflow-x: auto ativado automaticamente pelo Streamlit. */
    [data-testid="stSidebar"] {{
        background-color: {CORES["card_fundo"]};
        width: 240px !important;
        min-width: 240px !important;
        max-width: 240px !important;
        border-right: 1px solid var(--border-subtle) !important;
        overflow-x: hidden !important;
    }}
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebar"] > div > div,
    [data-testid="stSidebarContent"],
    [data-testid="stSidebar"] section {{
        width: 240px !important;
        min-width: 240px !important;
        max-width: 240px !important;
        padding: 0 !important;
        margin: 0 !important;
        box-sizing: border-box !important;
        overflow-x: hidden !important;
    }}
    /* aside.sidebar (HTML interno) ocupa 240px completos. */
    [data-testid="stSidebar"] aside.sidebar,
    aside.sidebar.ouroboros-sidebar-redesign {{
        width: 240px !important;
        max-width: 240px !important;
        margin: 0 !important;
        padding: 12px 0 !important;
        box-sizing: border-box !important;
        overflow-x: hidden !important;
    }}
    /* Sprint UX-116: sidebar interna ganha padding 4 direções com PADDING_CHIP
       (16px). O retângulo interno [data-testid="stSidebar"] > div:first-child
       abriga logo + radio de cluster + filtros; sem padding explícito,
       controles colam na borda esquerda da sidebar. */
    [data-testid="stSidebar"] > div:first-child {{
        padding-top: {PADDING_CHIP}px !important;
        padding-right: {PADDING_CHIP}px !important;
        padding-bottom: {PADDING_CHIP}px !important;
        padding-left: {PADDING_CHIP}px !important;
    }}
    [data-testid="stSidebar"] h1 {{ color: {CORES["destaque"]}; }}
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {{ font-size: {FONTE_CORPO}px; }}
    [data-testid="stDownloadButton"] button {{
        background-color: {CORES["card_fundo"]};
        color: {CORES["texto"]};
        border: 1px solid {CORES["destaque"]};
        font-size: {FONTE_CORPO}px;
    }}
    [data-testid="stDownloadButton"] button:hover {{
        background-color: {CORES["destaque"]};
        color: {CORES["fundo"]};
    }}
    h1 {{ font-size: {FONTE_HERO}px !important; font-weight: 700 !important; }}
    h2 {{ font-size: {FONTE_TITULO}px !important; font-weight: 700 !important; }}
    h3 {{ font-size: {FONTE_SUBTITULO}px !important; font-weight: 600 !important; }}
    p, li, span, div {{ font-size: {FONTE_CORPO}px; }}
    .stTabs [data-baseweb="tab-list"],
    .stTabs [data-baseweb="tab-list"] > div,
    .stTabs > div:first-child {{
        gap: {SPACING["sm"]}px;
        background-color: {CORES["card_fundo"]};
        border-radius: 8px;
        min-height: 60px !important;
        height: auto !important;
        overflow: visible !important;
        overflow-y: visible !important;
        overflow-x: auto !important;
    }}
    /* Sprint UX-118: barra de tabs fica fixa no topo durante scroll com
       linha 2px na cor destaque (#BD93F9) abaixo, marcando o limite entre
       navegação e conteúdo. position: sticky + top: 0 + z-index alto
       garantem que tabs não sejam cobertas pelo conteúdo ao rolar. Aplicado
       só ao seletor pai (tab-list) — não estendemos para os filhos > div
       para evitar duplicar a borda. */
    .stTabs [data-baseweb="tab-list"] {{
        position: sticky;
        top: 0;
        z-index: 10;
        border-bottom: 2px solid var(--color-destaque);
    }}
    .stTabs [data-baseweb="tab"] {{
        color: {CORES["texto_sec"]} !important;
        font-size: {FONTE_CORPO}px !important;
        padding: {SPACING["md"]}px {SPACING["md"] + 4}px !important;
        height: auto !important;
        min-height: 48px !important;
        white-space: nowrap !important;
        overflow: visible !important;
        display: flex !important;
        align-items: center !important;
    }}
    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] div {{
        color: inherit !important;
        font-size: {FONTE_CORPO}px !important;
        overflow: visible !important;
        line-height: 1.4 !important;
    }}
    .stTabs [aria-selected="true"] {{
        color: {CORES["texto"]} !important;
        font-weight: bold !important;
        border-bottom: 3px solid {CORES["destaque"]} !important;
    }}
    .stTabs [aria-selected="true"] p,
    .stTabs [aria-selected="true"] div {{
        color: {CORES["texto"]} !important;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        color: {CORES["texto"]} !important;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{
        background-color: transparent !important;
        display: none !important;
    }}
    .element-container {{ margin-bottom: {SPACING["md"]}px; }}
    [data-testid="stHorizontalBlock"] {{ gap: {SPACING["md"]}px; }}

    /* P2.2 2026-04-23: alertas do Streamlit alinhados ao tema Dracula.
       Default usa amarelo pálido que destoa do tema escuro. */
    [data-testid="stAlert"] {{
        background-color: {CORES["card_fundo"]} !important;
        color: {CORES["texto"]} !important;
        border-left: 4px solid {CORES["destaque"]} !important;
        border-radius: 6px;
    }}
    [data-testid="stAlert"] p,
    [data-testid="stAlert"] span,
    [data-testid="stAlert"] div {{
        color: {CORES["texto"]} !important;
    }}

    /* --- Sprint UX-112: bordas e padding universais em inputs/selects --- */
    /* Borda padrão 1px texto_sec; foco eleva para borda-ativa-px destaque.
       Padding-chip aplicado em controles compactos. */
    [data-testid="stTextInput"] > div > div,
    [data-testid="stSelectbox"] > div > div,
    [data-testid="stMultiSelect"] > div > div,
    [data-testid="stTextArea"] > div > div,
    [data-testid="stNumberInput"] > div > div,
    [data-testid="stDateInput"] > div > div {{
        border: 1px solid {CORES["texto_sec"]} !important;
        border-radius: var(--borda-raio) !important;
        background-color: {CORES["card_fundo"]} !important;
        padding: var(--spacing-xs) var(--padding-chip) !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }}
    [data-testid="stTextInput"]:focus-within > div > div,
    [data-testid="stSelectbox"]:focus-within > div > div,
    [data-testid="stMultiSelect"]:focus-within > div > div,
    [data-testid="stTextArea"]:focus-within > div > div,
    [data-testid="stNumberInput"]:focus-within > div > div,
    [data-testid="stDateInput"]:focus-within > div > div {{
        border: var(--borda-ativa-px) solid {CORES["destaque"]} !important;
        box-shadow: 0 0 0 1px {CORES["destaque"]}33 !important;
    }}

    /* Expanders ganham borda visível e padding interno coerente. */
    [data-testid="stExpander"] {{
        border: 1px solid {CORES["texto_sec"]} !important;
        border-radius: var(--borda-raio) !important;
        background-color: {CORES["card_fundo"]} !important;
        margin: var(--spacing-sm) 0;
    }}
    [data-testid="stExpander"] details > summary {{
        padding: var(--spacing-sm) var(--padding-chip) !important;
    }}
    [data-testid="stExpander"] details[open] > div:last-child,
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
        padding: var(--padding-chip) var(--padding-interno) !important;
    }}

    /* Corpo das tabs (painel abaixo da barra) ganha padding-top para evitar
       conteúdo colado no separador. */
    .stTabs [data-baseweb="tab-panel"] {{
        padding-top: var(--padding-chip) !important;
    }}

    /* --- Grid responsivo de KPI cards (Sprint 62) ------------------------ */
    /* Grid fluido com minmax: 3 colunas em telas largas, 2 em médias e 1 em
       estreitas. Substitui `st.columns(3)` rígido quando renderizado como
       bloco HTML custom via kpi_grid_html(). */
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: {SPACING["md"]}px;
        width: 100%;
    }}
    .kpi-grid > .kpi-card {{
        min-width: 0;  /* permite shrink abaixo do conteúdo */
    }}
    .kpi-card .kpi-label {{
        color: {CORES["texto_sec"]};
        font-size: {FLUID_LABEL_KPI};
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .kpi-card .kpi-valor {{
        font-size: {FLUID_VALOR_KPI};
        font-weight: bold;
        margin: {SPACING["xs"]}px 0 0 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    @media (max-width: {BREAKPOINT_COMPACTO}px) {{
        .kpi-grid {{
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }}
        /* Streamlit columns fallback: quando visao_geral ainda usa st.columns(3),
           força cada coluna a 50% em viewports compactos. */
        [data-testid="stHorizontalBlock"] {{
            flex-wrap: wrap !important;
        }}
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
            flex: 1 1 calc(50% - {SPACING["md"]}px) !important;
            min-width: calc(50% - {SPACING["md"]}px) !important;
        }}
    }}
    @media (max-width: {BREAKPOINT_MINIMO}px) {{
        .kpi-grid {{
            grid-template-columns: 1fr;
        }}
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }}
        /* Sprint UX-127 AC1: input de busca da sidebar não corta em viewport
           estreito. Em telas <=700px o container interno e o <input> ganham
           width: 100% + box-sizing: border-box + overflow: visible. Sem
           isso, o conteúdo do <input> some quando a sidebar encolhe abaixo
           do default do Streamlit (~280px) e o usuário não vê o que digita.
           Combina com a regra UX-125 AC5 (min-height: 44px) que já vive em
           outro bloco do css_global. */
        [data-testid="stSidebar"] [data-testid="stTextInput"] > div > div {{
            width: 100% !important;
            overflow: visible !important;
        }}
        [data-testid="stSidebar"] [data-testid="stTextInput"] input {{
            width: 100% !important;
            box-sizing: border-box !important;
        }}
    }}

    /* --- Gráfico: título não sobrepõe legenda (Sprint 62) --------------- */
    /* Plotly em viewport estreito cola a legenda horizontal no topo do
       gráfico. Garante espaçamento mínimo entre título e legenda. */
    .js-plotly-plot .plotly .g-gtitle {{
        margin-bottom: {SPACING["md"]}px;
    }}

    /* --- Sprint 92c: classes utilitarias de layout ---------------------- */
    /* Substitui inline <div style="display: flex; ..."> pontuais nas paginas
       pelo menor conjunto possivel de classes reutilizaveis. CSS vars acima
       em :root garantem coerencia de spacing e cor. */
    .ouroboros-row-between {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: var(--spacing-sm);
    }}
    .ouroboros-row-flex {{
        display: flex;
        flex-wrap: wrap;
        gap: var(--spacing-sm);
        align-items: center;
    }}
    .ouroboros-row-flex-xs {{
        display: flex;
        flex-wrap: wrap;
        gap: var(--spacing-xs);
    }}
    .ouroboros-label-icon {{
        display: flex;
        align-items: center;
        gap: var(--spacing-xs);
        color: var(--color-destaque);
        font-size: var(--font-corpo);
        font-weight: 600;
        margin-bottom: var(--spacing-xs);
        /* Sprint UX-115: contrato explícito de alinhamento à esquerda --
           label "Busca global" deve iniciar em x=0 do block-container,
           coincidindo com a borda esquerda do input principal. */
        margin-left: 0;
        padding-left: 0;
        justify-content: flex-start;
    }}
    .ouroboros-row-resumo-busca {{
        margin: var(--spacing-md) 0;
    }}
    .ouroboros-card-hero-busca {{
        background-color: var(--color-card-fundo);
        border-radius: 10px;
        padding: var(--spacing-md);
        margin-bottom: var(--spacing-sm);
        border-left: 4px solid var(--color-destaque);
    }}
    .ouroboros-aliases-line {{
        display: flex;
        flex-wrap: wrap;
        gap: var(--spacing-xs);
    }}
    .ouroboros-ritmo-card {{
        padding: var(--spacing-xs) 0;
    }}
    .ouroboros-timeline-container {{
        background-color: var(--color-card-fundo);
        border-radius: 8px;
        padding: var(--spacing-lg);
    }}
    .ouroboros-timeline-tronco {{
        border-left: 2px solid var(--color-card-fundo);
        padding-left: var(--spacing-lg);
        margin-left: var(--spacing-sm);
    }}
    .ouroboros-chips-tipos {{
        display: flex;
        flex-wrap: wrap;
        gap: var(--spacing-xs);
        margin-top: var(--spacing-sm);
    }}
    .ouroboros-moc-preview {{
        background-color: var(--color-card-fundo);
        border-radius: 10px;
        padding: var(--spacing-md) calc(var(--spacing-md) + 4px);
        margin-top: var(--spacing-sm);
        max-height: 520px;
        overflow-y: auto;
        font-family: 'JetBrains Mono', monospace;
        font-size: var(--font-label);
        line-height: 1.6;
        color: var(--color-texto);
    }}
    .ouroboros-timeline-evento {{
        position: relative;
        margin-bottom: var(--spacing-lg);
    }}

    /* UX-U-01: Sidebar canônica.
       Garante scroll interno (8 clusters acessíveis em qualquer viewport)
       + scrollbar discreta do mockup (tokens.css linhas 134-137: 10px,
       track bg-base, thumb border-subtle, hover border-strong). */
    [data-testid="stSidebar"] {{
        overflow-y: auto !important;
        height: 100vh !important;
        max-height: 100vh !important;
    }}
    [data-testid="stSidebar"]::-webkit-scrollbar {{ width: 10px; }}
    [data-testid="stSidebar"]::-webkit-scrollbar-track {{ background: var(--bg-base); }}
    [data-testid="stSidebar"]::-webkit-scrollbar-thumb {{
        background: var(--border-subtle);
        border-radius: var(--r-sm);
    }}
    [data-testid="stSidebar"]::-webkit-scrollbar-thumb:hover {{
        background: var(--border-strong);
    }}

    /* FIX-12: skip-link + sr-only-focusable (WCAG 2.4.1).
       Invisível por padrão; aparece como CTA accent-purple quando focado
       pela tecla Tab. Ancora #main-root no início do conteúdo principal. */
    .sr-only,
    .sr-only-focusable:not(:focus):not(:focus-within) {{
        position: absolute !important;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
    }}
    .skip-link:focus {{
        position: fixed;
        top: 8px;
        left: 8px;
        background: var(--accent-purple);
        color: var(--text-inverse);
        padding: 8px 16px;
        border-radius: var(--r-sm);
        z-index: 99999;
        text-decoration: none;
        font-family: var(--ff-mono);
        font-size: var(--fs-12);
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}

    /* FIX-04 + FIX-08: importar fontes web canônicas. Inter (sans) é a
       família padrão do mockup; JetBrains Mono é usada em números, headings
       técnicos, breadcrumb, pills, sprint-tags e tabela. Material Symbols
       carrega os ícones do Streamlit (sem ela vazam como texto). */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');

    /* FIX-08: aplicar Inter (sans) globalmente em corpo, parágrafo,
       sidebar items, KPI label, botão. Antes config.toml font="monospace"
       fazia Streamlit aplicar "Source Code Pro" em tudo, perdendo a
       hierarquia tipográfica do mockup (sans no corpo, mono em UI técnica). */
    html, body, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdown"] p,
    [data-testid="stMarkdown"] li,
    [data-testid="stSidebar"] a,
    [data-testid="stSidebar"] label,
    button,
    input,
    textarea,
    select {{
        font-family: var(--ff-sans) !important;
    }}

    /* FIX-08: elementos canônicos em JetBrains Mono. Mockup pede mono em:
       page-title (40px UPPERCASE com gradient), breadcrumb, pill, sprint-tag,
       kpi-value, .table thead th, code, pre, kbd, .col-mono, st.metric value. */
    .page-title,
    .breadcrumb,
    .breadcrumb .seg,
    .kpi-value,
    .kpi-delta,
    .pill,
    .sprint-tag,
    .col-mono,
    .col-num,
    .table thead th,
    .mono,
    .num,
    code,
    pre,
    kbd,
    [data-testid="stMetricValue"],
    [data-testid="stCodeBlock"] {{
        font-family: var(--ff-mono) !important;
        font-variant-numeric: tabular-nums;
    }}

    /* FIX-04 + UX-U-04 followup: Streamlit nativo carrega
       "Material Symbols Rounded" (não Outlined). Ainda assim páginas
       referenciam classes como ``material-symbols-outlined`` cujo CSS
       solicita a família Outlined. Como Streamlit só fornece Rounded,
       o nome do ícone vaza como texto literal (ex.: "keyboard_arrow_right",
       "wait", "open"). Fix: aplicar a família REAL que Streamlit
       carrega (Rounded) com fallback para Outlined caso uma página
       opt-in importe via @import próprio. As ligatures (nomes dos
       ícones) são idênticas entre Outlined/Rounded/Sharp. */
    [data-testid="stIconMaterial"],
    span[class*="material-symbols"],
    .stMaterialIcon,
    .material-symbols-outlined,
    .material-symbols-rounded {{
        font-family: "Material Symbols Rounded",
                     "Material Symbols Outlined",
                     "Material Icons" !important;
        font-weight: normal !important;
        font-style: normal !important;
        line-height: 1;
        letter-spacing: normal;
        text-transform: none;
        display: inline-block;
        white-space: nowrap;
        word-wrap: normal;
        direction: ltr;
        font-feature-settings: "liga";
        -webkit-font-smoothing: antialiased;
    }}

    /* ============================================================
       UX-M-04 — Shell consolidado em CSS estático escopado.
       Substitui ~80% das regras de instalar_fix_sidebar_padding()
       que antes rodavam via setProperty('important') em runtime.
       Specificity 'html body [data-testid=...]' (0,1,2) vence o
       Streamlit emotion CSS-in-JS (0,1,0) com !important.
       Fonte canônica: src/dashboard/css/shell.css.
       ============================================================ */
    {bloco_shell_redesign}
    </style>
    """


# "Forma é a expressão visível da função." -- Louis Sullivan
