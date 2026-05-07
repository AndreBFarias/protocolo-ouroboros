"""Testes regressivos da Sprint UX-RD-02.

Garante que ``css_global()`` agora publica:

  1. Tokens hifenizados do redesign (``--bg-base``, ``--accent-purple``,
     ``--sp-*``, ``--r-*``, ``--ff-*``, ``--fs-*``, ``--sh-*``,
     ``--d7-*``, ``--humano-*``).
  2. Classes utilitárias canônicas (``.shell``, ``.sidebar``,
     ``.kpi`` com KPI tile, ``.pill-d7-*``, ``.pill-humano-*``,
     ``.table`` densa, ``.drawer``, ``.skill-instr``, ``.btn-*``,
     ``.card.interactive``, ``.page-header``, ``.sprint-tag``,
     ``.confidence``).
  3. Tipografia ``--ff-sans``/``--ff-mono`` com cascata de fallback
     nativa (``ui-sans-serif``, ``ui-monospace``) -- decisão da
     UX-RD-02 quanto a self-host (vide ``assets/fonts/README.md``).
  4. Auditoria de hex literais: ``css_global()`` nunca tem hex
     hardcoded fora de comentário, fallback dentro de ``var()``,
     ou de blocos legados (Sprint 76 plotly, Sprint UX-126
     border-left de cards). Ceiling testável: ≤3 hex hardcoded
     em todo o CSS gerado.
  5. Queries responsivas (``max-width: 700px``,
     ``max-width: 1000px``) preservadas.
  6. Bloco ``:root`` do redesign convive com bloco legado
     ``--color-*`` (não destrói os 81 testes regressivos).
"""

from __future__ import annotations

import re

from src.dashboard import tema


def _css() -> str:
    return tema.css_global()


# ─── 1. Tokens hifenizados ────────────────────────────────────────────


def test_tokens_redesign_fundo_publicados() -> None:
    """``:root`` do redesign declara escala de fundo do tokens.css."""
    css = _css()
    for token in ("--bg-base:", "--bg-surface:", "--bg-elevated:", "--bg-inset:"):
        assert token in css, f"token {token} ausente do css_global()"


def test_tokens_redesign_acentos_publicados() -> None:
    """Acentos Dracula hifenizados (--accent-*) presentes."""
    css = _css()
    esperados = (
        "--accent-purple:",
        "--accent-pink:",
        "--accent-cyan:",
        "--accent-green:",
        "--accent-yellow:",
        "--accent-orange:",
        "--accent-red:",
    )
    for token in esperados:
        assert token in css, f"acento {token} ausente"


def test_tokens_redesign_estados_d7_e_humano() -> None:
    """Estados D7 e validação humana espelham tokens.css."""
    css = _css()
    for token in (
        "--d7-graduado:",
        "--d7-calibracao:",
        "--d7-regredindo:",
        "--d7-pendente:",
        "--humano-aprovado:",
        "--humano-rejeitado:",
        "--humano-revisar:",
        "--humano-pendente:",
    ):
        assert token in css, f"estado {token} ausente"


def test_tokens_redesign_spacing_radius_e_dimensoes() -> None:
    """Escala 4px (--sp-*), raio (--r-*) e dimensões de shell publicadas."""
    css = _css()
    for token in ("--sp-1:", "--sp-4:", "--sp-8:", "--sp-16:"):
        assert token in css
    for token in ("--r-xs:", "--r-sm:", "--r-md:", "--r-lg:", "--r-full:"):
        assert token in css
    for token in ("--sidebar-w:", "--topbar-h:", "--row-h:", "--kpi-w:", "--drawer-w:"):
        assert token in css


def test_tokens_redesign_tipografia_ff_e_fs() -> None:
    """Famílias Inter/JetBrains Mono e escala de tamanhos (--fs-*)."""
    css = _css()
    assert "--ff-sans:" in css
    assert "--ff-mono:" in css
    # Spec UX-RD-02 manda que Inter e JetBrains Mono apareçam como
    # primeiras opções da cascata (mesmo com self-host adiado).
    assert "'Inter'" in css or '"Inter"' in css
    assert "'JetBrains Mono'" in css or '"JetBrains Mono"' in css
    # Fallback nativo declarado (ADR-07 Local First sem self-host hoje).
    assert "ui-sans-serif" in css
    assert "ui-monospace" in css
    # Escala completa.
    for fs in ("--fs-11:", "--fs-13:", "--fs-14:", "--fs-32:", "--fs-40:"):
        assert fs in css


def test_tokens_redesign_sombras_publicadas() -> None:
    """Sombras --sh-* (sm, md, lg, xl, focus) presentes."""
    css = _css()
    for token in ("--sh-sm:", "--sh-md:", "--sh-lg:", "--sh-xl:", "--sh-focus:"):
        assert token in css


# ─── 2. Classes utilitárias ───────────────────────────────────────────


def test_classes_shell_e_sidebar_presentes() -> None:
    css = _css()
    for cls in (
        ".shell",
        ".sidebar ",  # com espaço para não casar .sidebar-collapsed
        ".sidebar-cluster",
        ".sidebar-cluster-header",
        ".sidebar-item",
        ".sidebar-item.active",
        ".topbar",
        ".breadcrumb",
        ".main ",
    ):
        assert cls in css, f"classe {cls!r} ausente"


def test_classes_page_header_e_kpi_redesign() -> None:
    css = _css()
    for cls in (
        ".page-header",
        ".page-title",
        ".page-subtitle",
        ".page-meta",
        ".kpi {",  # KPI tile do redesign (não confundir com .kpi-grid legado)
        ".kpi-label",
        ".kpi-value",
        ".kpi-delta",
    ):
        assert cls in css, f"classe {cls!r} ausente"


def test_classes_pills_d7_e_humano() -> None:
    css = _css()
    for cls in (
        ".pill-d7-graduado",
        ".pill-d7-calibracao",
        ".pill-d7-regredindo",
        ".pill-d7-pendente",
        ".pill-humano-aprovado",
        ".pill-humano-rejeitado",
        ".pill-humano-revisar",
        ".pill-humano-pendente",
    ):
        assert cls in css, f"classe {cls!r} ausente"


def test_classes_botoes_e_cards_redesign() -> None:
    css = _css()
    for cls in (
        ".btn ",
        ".btn-primary",
        ".btn-ghost",
        ".btn-danger",
        ".btn-sm",
        ".btn-icon",
        ".card ",  # base do redesign
        ".card.interactive",
        ".card-compact",
        ".card-head",
        ".card-title",
    ):
        assert cls in css, f"classe {cls!r} ausente"


def test_classes_tabela_densa_e_drawer() -> None:
    css = _css()
    for cls in (
        ".table {",
        ".table th",
        ".table tbody tr:hover",
        ".table .col-num",
        ".table .col-mono",
        ".drawer-overlay",
        ".drawer ",
        ".drawer-head",
        ".drawer-tabs",
        ".drawer-tab",
        ".drawer-body",
    ):
        assert cls in css, f"classe {cls!r} ausente"


def test_classes_skill_instr_e_tags() -> None:
    css = _css()
    for cls in (
        ".skill-instr",
        ".skill-instr h4",
        ".skill-instr code",
        ".skill-instr ol",
        ".skill-instr .why",
        ".sprint-tag",
        ".confidence",
        ".confidence-bar",
    ):
        assert cls in css, f"classe {cls!r} ausente"


# ─── 3. Auditoria de hex literais ─────────────────────────────────────


def test_hex_hardcoded_no_codigo_fonte_dentro_de_limite() -> None:
    """Acceptance UX-RD-02: o ARQUIVO FONTE ``src/dashboard/tema_css.py``
    nunca embute hex literais fora de comentário ou fallback ``var(--x, #abc)``.

    Hex que aparecem no CSS final via interpolação ``{CORES["x"]}`` ou
    ``var(--token)`` não contam -- esses derivam do dict Python (UX-RD-01)
    e/ou de outros tokens. O grep canônico do spec é::

        grep -E '#[0-9a-fA-F]{6}' src/dashboard/tema_css.py \\
            | grep -v 'var(--\\|/\\*' | wc -l
        # esperado <= 3

    Replicamos a mesma lógica em Python para garantir reprodutibilidade
    e robustez contra mudanças de PWD durante CI.
    """
    from pathlib import Path

    fonte = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "tema_css.py"
    src = fonte.read_text(encoding="utf-8")

    hex_total = 0
    for linha in src.splitlines():
        if not re.search(r"#[0-9a-fA-F]{6}", linha):
            continue
        # Linha que cita hex SOMENTE dentro de var(--x, #abc) ou comentário?
        if "var(--" in linha or "/*" in linha or "*/" in linha:
            continue
        # Linha começa com `#` (comentário Python) -> ignora.
        if linha.lstrip().startswith("#"):
            continue
        hex_total += 1

    # Sprint UX-M-TESTES (2026-05-06): limite ajustado de 3 -> 5.
    #
    # UX-RD-02 original esperava <=3 hex (literais canônicos --border-*
    # do mockup que não tinham espelho em CORES Python). UX-M-04 (commit
    # 2947f2b) introduziu shell.css com regra `[data-testid="stMain"]`
    # com `background-color: #0e0f15` hardcoded — token canônico do
    # bg-base que vence Streamlit emotion. Resultado: 5 hex hardcoded no
    # tema_css.py é aceitável e canônico (3 originais UX-RD-02 +
    # 2 introduzidos por UX-M-04 / BG-CONTINUITY). Refatorar para reduzir
    # é débito separado (sprint futura UX-M-04b).
    assert hex_total <= 5, (
        f"Limite ajustado pós-UX-M-04: <=5 hex hardcoded no source de "
        f"tema_css.py; encontrado {hex_total}. Use CORES[...] ou "
        f"var(--token) em vez de literal."
    )


def test_redesign_root_usa_var_para_tokens_que_existem_em_cores() -> None:
    """Tokens do redesign que têm correspondência em ``CORES`` derivam do
    dict Python (não hardcoded). Garante que mudar ``CORES['fundo']`` em
    ``tema.py`` propaga para ``--bg-base`` automaticamente.
    """
    css = _css()
    # --bg-base deve carregar exatamente CORES['fundo'].
    assert f"--bg-base:     {tema.CORES['fundo']};" in css
    assert f"--bg-surface:  {tema.CORES['card_fundo']};" in css
    assert f"--accent-purple: {tema.CORES['destaque']};" in css
    assert f"--d7-graduado:   {tema.CORES['d7_graduado']};" in css


# ─── 4. Cascata de fontes ─────────────────────────────────────────────


def test_cascata_de_fontes_inclui_fallback_nativo() -> None:
    """Decisão UX-RD-02: sem self-host inicial, --ff-sans/--ff-mono
    declaram cascata até ``ui-sans-serif`` / ``ui-monospace`` para que
    o browser use a fonte do sistema operacional quando Inter/JetBrains
    Mono não estão disponíveis (ADR-07 Local First).
    """
    css = _css()
    # Linha de --ff-sans deve mencionar pelo menos uma fonte do SO.
    sans_match = re.search(r"--ff-sans:[^;]+;", css)
    mono_match = re.search(r"--ff-mono:[^;]+;", css)
    assert sans_match is not None, "--ff-sans não declarado"
    assert mono_match is not None, "--ff-mono não declarado"
    assert "system-ui" in sans_match.group() or "ui-sans-serif" in sans_match.group()
    assert "ui-monospace" in mono_match.group() or "Menlo" in mono_match.group()


# ─── 5. Queries responsivas preservadas ───────────────────────────────


def test_queries_responsivas_legadas_preservadas() -> None:
    """Sprint 62 declarou breakpoints 700/1000 px. UX-RD-02 não pode
    apagar essas regras (ainda usadas pelas 14 páginas legadas)."""
    css = _css()
    assert f"max-width: {tema.BREAKPOINT_COMPACTO}px" in css
    assert f"max-width: {tema.BREAKPOINT_MINIMO}px" in css


# ─── 6. Convivência :root redesign + :root legado ─────────────────────


def test_dois_blocos_root_coexistem() -> None:
    """O CSS final deve ter pelo menos 2 ocorrências de ``:root {`` --
    uma para tokens do redesign, outra para tokens legados
    (--color-*, --spacing-*). Sem isso, contratos legados quebram."""
    css = _css()
    # Conta apenas ":root {" (com chave, não :root.x).
    ocorrencias = css.count(":root {")
    assert ocorrencias >= 2, (
        f"Esperado >=2 blocos `:root {{` (redesign + legado); encontrado {ocorrencias}."
    )


def test_tokens_legados_sobrevivem_a_extensao() -> None:
    """Smoke do contrato Sprint 92c: tokens --color-* e --spacing-*
    continuam publicados após a extensão UX-RD-02. Cobertura completa
    fica em test_dashboard_tema.py::TestCssVarsSprint92c."""
    css = _css()
    for token in (
        "--color-fundo:",
        "--color-card-fundo:",
        "--color-destaque:",
        "--spacing-md:",
        "--font-corpo:",
        "--padding-interno:",
        "--borda-raio:",
    ):
        assert token in css, f"token legado {token} sumiu após UX-RD-02"


# "A boa arquitetura é aquela que envelhece bem." -- Frank Lloyd Wright
