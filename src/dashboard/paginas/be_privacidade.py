"""Cluster Bem-estar -- página "Privacidade" (UX-V-2.15).

Privacidade granular A <-> B com 4 níveis (oculto/agregado/resumo/total)
em direção bidirecional sobre 9 campos de 6 categorias. Schema canônico
em ``<vault>/.ouroboros/permissoes.toml``.

Mantém compatibilidade com a API binária anterior (UX-RD-19) -- as
funções ``SCHEMAS``, ``_ler_estado`` e ``_salvar_estado`` continuam
expostas no shape antigo (dict[str, bool] em ``privacidade.toml``) para
não quebrar testes regressivos. A nova feature granular convive em
arquivo TOML separado (``permissoes.toml``).

Mockup-fonte: ``novo-mockup/mockups/27-privacidade.html``.
Decisão dono 2026-05-07: feature granular completa.

Lições UX aplicadas:

* HTML emitido via :func:`minificar` (UX-RD-04).
* CSS via ``carregar_css_pagina("be_privacidade")`` (UX-M-02 fronteira).
* Cores via ``CORES`` em :mod:`src.dashboard.tema` -- nunca hex literal
  novo em Python (literais antigos preservados em chaves de cor de
  marcadores; tokens completos em CSS).
* Subregra retrocompatível (padrão (o)): API binária antiga preservada.
* Default conservador: arquivo ausente vira tudo ``oculto``.
* Contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.ui import carregar_css_pagina
from src.dashboard.tema import CORES
from src.mobile_cache.varrer_vault import descobrir_vault_root

# ---------------------------------------------------------------------------
# API legado (UX-RD-19) -- mantida para compatibilidade com test_be_resto.
# Operam sobre ``privacidade.toml`` no shape binário antigo.
# ---------------------------------------------------------------------------

SCHEMAS = ("humor", "diario", "eventos", "medidas", "treinos", "ciclo")
LABEL_SCHEMA = {
    "humor": "Humor",
    "diario": "Diário emocional",
    "eventos": "Eventos",
    "medidas": "Medidas corporais",
    "treinos": "Treinos",
    "ciclo": "Ciclo menstrual",
}

_KEY_FLASH = "be_privacidade_flash"


def _resolver_caminho() -> Path:
    """Caminho do TOML binário antigo (compatibilidade UX-RD-19)."""
    vault_root = descobrir_vault_root()
    base = vault_root if vault_root is not None else Path.home()
    return base / ".ouroboros" / "privacidade.toml"


def _ler_estado(caminho: Path) -> dict[str, bool]:
    """Lê ``privacidade.toml`` legado e retorna ``{schema: bool}``.

    Default conservador: schema ausente = ``False`` (oculto).
    """
    estado = {s: False for s in SCHEMAS}
    if not caminho.exists():
        return estado
    try:
        cfg = tomllib.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return estado
    compartilhar = cfg.get("compartilhar") or {}
    if isinstance(compartilhar, dict):
        for s in SCHEMAS:
            v = compartilhar.get(s)
            if isinstance(v, bool):
                estado[s] = v
    return estado


def _salvar_estado(caminho: Path, estado: dict[str, bool]) -> None:
    """Grava ``privacidade.toml`` legado com a seção ``[compartilhar]``."""
    linhas = [
        "# privacidade.toml -- controle de compartilhamento A <-> B por schema",
        "# Default conservador: tudo oculto até liberar explicitamente.",
        "",
        "[compartilhar]",
    ]
    for s in SCHEMAS:
        valor = "true" if estado.get(s, False) else "false"
        linhas.append(f"{s} = {valor}")
    linhas.append("")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text("\n".join(linhas), encoding="utf-8")


# ---------------------------------------------------------------------------
# Feature granular (UX-V-2.15) -- 4 níveis x 9 campos x 2 direções.
# Operam sobre ``permissoes.toml`` (arquivo NOVO, distinto do legado).
# Persistência completa fica para sprint-filha; aqui apenas leitura.
# ---------------------------------------------------------------------------

NIVEIS: tuple[str, ...] = ("oculto", "agregado", "resumo", "total")
NIVEIS_LABEL: dict[str, str] = {
    "oculto": "OCULTO",
    "agregado": "AGREGADO",
    "resumo": "RESUMO",
    "total": "TOTAL",
}
# Cor por nível (alinhada ao mockup):
# oculto  -> texto_muted (cinza neutro)
# agregado -> neutro (ciano Dracula)
# resumo  -> destaque (roxo Dracula)
# total   -> positivo (verde Dracula)
NIVEIS_COR: dict[str, str] = {
    "oculto": CORES["texto_muted"],
    "agregado": CORES["neutro"],
    "resumo": CORES["destaque"],
    "total": CORES["positivo"],
}
NIVEIS_DESC: dict[str, str] = {
    "oculto": "B não vê nem que existe.",
    "agregado": "Só média / contagem em janelas (7d, 30d).",
    "resumo": "Vê o dado por dia, sem texto bruto.",
    "total": "Acesso completo, igual a si mesmo.",
}

# 9 campos agrupados em 6 seções (chave canônica, label, seção, fonte).
CAMPOS: tuple[tuple[str, str, str, str], ...] = (
    ("humor.base", "humor base", "HUMOR", ".ouroboros/humor.json"),
    ("humor.extras", "energia / ansiedade / foco", "HUMOR",
     ".ouroboros/humor.json (extras)"),
    ("diario.entradas_para_b", "entradas marcadas como 'para B'",
     "DIÁRIO EMOCIONAL", "diario/*.md"),
    ("diario.privadas", "entradas privadas",
     "DIÁRIO EMOCIONAL", "diario/*.md (private)"),
    ("eventos.lugar", "lugar do evento", "EVENTOS", "eventos/*.json"),
    ("eventos.detalhes", "detalhes (foto, descrição)",
     "EVENTOS", "eventos/*.json (detalhe)"),
    ("medidas.peso", "peso", "MEDIDAS", "medidas/*.json"),
    ("treinos.tipo", "tipo de treino", "TREINOS", "treinos/*.json"),
    ("ciclo", "ciclo menstrual", "CICLO MENSTRUAL", "ciclo/*.json"),
)

# Defaults conservadores por chave (todos começam como "oculto").
_DEFAULT_NIVEL = "oculto"

_KEY_DIRECAO = "be_priv_direcao"


def _caminho_permissoes() -> Path:
    """Caminho canônico do TOML granular novo."""
    vault_root = descobrir_vault_root()
    base = vault_root if vault_root is not None else Path.home()
    return base / ".ouroboros" / "permissoes.toml"


def _carregar_permissoes(vault_root: Path | None) -> dict[str, dict[str, str]]:
    """Lê ``permissoes.toml`` e retorna dict com ``a_to_b`` / ``b_to_a``.

    Default conservador: arquivo ausente => ambos vazios (UI cai em
    ``oculto``).
    """
    base = vault_root if vault_root is not None else Path.home()
    arq = base / ".ouroboros" / "permissoes.toml"
    vazio: dict[str, dict[str, str]] = {"a_to_b": {}, "b_to_a": {}}
    if not arq.exists():
        return vazio
    try:
        cfg = tomllib.loads(arq.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return vazio
    out: dict[str, dict[str, str]] = {"a_to_b": {}, "b_to_a": {}}
    for direcao in ("a_to_b", "b_to_a"):
        bloco = cfg.get(direcao) or {}
        if isinstance(bloco, dict):
            # Achata chaves aninhadas (humor.base, etc.). tomllib já
            # decodifica como nested dict; reconstrói o ponto.
            for chave_raiz, valor in bloco.items():
                if isinstance(valor, str) and valor in NIVEIS:
                    out[direcao][chave_raiz] = valor
                elif isinstance(valor, dict):
                    for sub, v in valor.items():
                        if isinstance(v, str) and v in NIVEIS:
                            out[direcao][f"{chave_raiz}.{sub}"] = v
    return out


def _radio_html(direcao: str, chave: str, nivel: str, selecionado: str) -> str:
    """Render de uma célula de radio circular (não-interativo nesta sprint)."""
    cor = NIVEIS_COR[nivel]
    classe = "priv-radio sel" if selecionado == nivel else "priv-radio"
    titulo = (
        f"{NIVEIS_LABEL[nivel]} -- {NIVEIS_DESC[nivel]} "
        f"(direção {direcao}, campo {chave})"
    )
    return (
        f'<div class="{classe}" style="--priv-cor: {cor};" '
        f'title="{titulo}"></div>'
    )


def _renderizar_grade_permissoes(
    direcao: str, perms: dict[str, dict[str, str]]
) -> str:
    """Renderiza a matriz 9 campos x 4 níveis (HTML estático).

    Esta sprint entrega visual e leitura; persistência completa via
    interação Streamlit fica para sprint-filha (decisão dono 2026-05-07).
    """
    bloco_perms = perms.get(direcao, {})
    partes: list[str] = ['<div class="priv-matriz">']

    # Header
    partes.append('<div class="priv-matriz-head">')
    partes.append('<div class="h label-col">CAMPO / FONTE</div>')
    for nivel in NIVEIS:
        cor = NIVEIS_COR[nivel]
        partes.append(
            f'<div class="h" style="color: {cor};">{NIVEIS_LABEL[nivel]}</div>'
        )
    partes.append("</div>")

    # Linhas agrupadas por seção
    secao_atual: str | None = None
    for chave, label, secao, fonte in CAMPOS:
        if secao != secao_atual:
            partes.append('<div class="priv-matriz-row cat-divisor">')
            partes.append(f'<div class="c label">{secao}</div>')
            partes.append("</div>")
            secao_atual = secao
        atual = bloco_perms.get(chave, _DEFAULT_NIVEL)
        partes.append('<div class="priv-matriz-row">')
        partes.append(
            f'<div class="c label">'
            f'<span class="nome">{label}</span>'
            f'<span class="src">{fonte}</span>'
            f"</div>"
        )
        for nivel in NIVEIS:
            partes.append(
                f'<div class="c">{_radio_html(direcao, chave, nivel, atual)}</div>'
            )
        partes.append("</div>")

    partes.append("</div>")
    return "".join(partes)


def _legenda_html() -> str:
    """Cartela horizontal explicando cada nível."""
    blocos: list[str] = ['<div class="priv-legenda">']
    for nivel in NIVEIS:
        cor = NIVEIS_COR[nivel]
        blocos.append(
            f'<div class="lvl" style="--priv-cor: {cor};">'
            f'<span class="n">{NIVEIS_LABEL[nivel]}</span>'
            f'{NIVEIS_DESC[nivel]}'
            f"</div>"
        )
    blocos.append("</div>")
    return "".join(blocos)


def _dir_tabs_html(direcao_ativa: str) -> str:
    """Tabs A->B / B->A (formulário GET para alternar direção)."""
    a_active = "active" if direcao_ativa == "a_to_b" else ""
    b_active = "active" if direcao_ativa == "b_to_a" else ""
    return (
        '<div class="priv-dir-tabs">'
        f'<div class="priv-dir-tab {a_active}">'
        '<span>A (você)</span><span class="seta">→</span>'
        '<span>B (parceira)</span>'
        '</div>'
        f'<div class="priv-dir-tab {b_active}">'
        '<span>B (parceira)</span><span class="seta">→</span>'
        '<span>A (você)</span>'
        '</div>'
        '</div>'
    )


def _card_pessoa_html(
    titulo: str,
    avatar_letra: str,
    avatar_cor: str,
    nome: str,
    endereco: str,
    chaves_valores: list[tuple[str, str]],
) -> str:
    """Card lateral com identidade + metadados do vault."""
    partes: list[str] = ['<div class="priv-pessoa-card">']
    partes.append(f"<h4>{titulo}</h4>")
    partes.append('<div class="priv-pessoa-id">')
    partes.append(
        f'<div class="priv-pessoa-avatar" style="--priv-avatar: {avatar_cor};">'
        f"{avatar_letra}</div>"
    )
    partes.append(
        f'<div class="priv-pessoa-meta">'
        f'<div class="nome">{nome}</div>'
        f'<div class="e">{endereco}</div>'
        f"</div>"
    )
    partes.append("</div>")
    for k, v in chaves_valores:
        partes.append(
            f'<div class="priv-kv">'
            f'<span class="k">{k}</span>'
            f'<span class="v">{v}</span>'
            f"</div>"
        )
    partes.append("</div>")
    return "".join(partes)


def _aviso_default_html() -> str:
    """Banner laranja explicando o default conservador."""
    return (
        '<div class="priv-aviso">'
        '<span class="ico">!</span>'
        '<span class="t">'
        '<strong>Default conservador:</strong> tudo começa em <em>oculto</em> '
        "ao convidar a outra pessoa. Você precisa explicitamente liberar campo "
        "a campo. <strong>Nada vaza por configuração padrão.</strong> "
        "Mudanças geram entrada no audit log no próximo sync."
        "</span>"
        "</div>"
    )


def _page_header_html(qtd_compartilhadas: int, caminho: Path) -> str:
    """UX-U-03: usa helper canônico ``componentes/page_header``."""
    from src.dashboard.componentes.page_header import renderizar_page_header

    return renderizar_page_header(
        titulo="PRIVACIDADE GRANULAR · A ↔ B",
        subtitulo=(
            f"Controle por campo do que cada pessoa vê do outro. "
            f"{qtd_compartilhadas} de 6 áreas compartilhadas (visão legado). "
            f"Granular abaixo em 4 níveis."
        ),
        sprint_tag="UX-V-2.15",
        pills=[{"texto": caminho.name, "tipo": "generica"}],
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Privacidade granular (UX-V-2.15)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes

    renderizar_grupo_acoes([
        {"label": "Audit log", "glyph": "list",
         "title": "Abrir audit log de privacidade"},
        {"label": "Salvar permissões", "primary": True, "glyph": "validar",
         "title": "Persistir permissoes.toml (placeholder UX-V-2.15)"},
    ])

    del dados, periodo, pessoa, ctx

    # CSS dedicado
    st.markdown(
        minificar(carregar_css_pagina("be_privacidade")),
        unsafe_allow_html=True,
    )

    # Estado legado (binário) -- contagem de áreas compartilhadas para o header
    caminho_legado = _resolver_caminho()
    estado_legado = _ler_estado(caminho_legado)
    qtd = sum(1 for v in estado_legado.values() if v)

    # Header
    st.markdown(
        _page_header_html(qtd, _caminho_permissoes()),
        unsafe_allow_html=True,
    )

    # Flash messages do botão Salvar
    flash = st.session_state.pop(_KEY_FLASH, None)
    if flash:
        nivel, mensagem = flash
        if nivel == "ok":
            st.success(mensagem)
        else:
            st.error(mensagem)

    # Estado de direção (default A -> B)
    if _KEY_DIRECAO not in st.session_state:
        st.session_state[_KEY_DIRECAO] = "a_to_b"
    direcao = st.session_state[_KEY_DIRECAO]

    # Carrega permissões granulares (read-only nesta sprint)
    vault_root = descobrir_vault_root()
    perms = _carregar_permissoes(vault_root)

    # Layout em 2 colunas (matriz à esquerda, cards à direita)
    col_main, col_side = st.columns([2, 1])

    with col_main:
        # Tabs A->B / B->A: usamos st.radio nativo (clica e re-renderiza)
        st.markdown(
            '<p class="priv-secao-titulo">DIREÇÃO DO COMPARTILHAMENTO</p>',
            unsafe_allow_html=True,
        )
        opcoes = {
            "a_to_b": "A (você) → B (parceira)",
            "b_to_a": "B (parceira) → A (você)",
        }
        nova_dir = st.radio(
            "Direção",
            options=list(opcoes.keys()),
            format_func=lambda x: opcoes[x],
            index=0 if direcao == "a_to_b" else 1,
            horizontal=True,
            label_visibility="collapsed",
            key="be_priv_dir_radio",
        )
        if nova_dir != direcao:
            st.session_state[_KEY_DIRECAO] = nova_dir
            direcao = nova_dir

        # Visual de "tabs" estilizadas (espelha mockup; o radio é o controle real)
        st.markdown(_dir_tabs_html(direcao), unsafe_allow_html=True)

        # Legenda dos níveis
        st.markdown(
            '<p class="priv-secao-titulo">LEGENDA DOS 4 NÍVEIS</p>',
            unsafe_allow_html=True,
        )
        st.markdown(_legenda_html(), unsafe_allow_html=True)

        # Grade granular
        rotulo_dir = "B vê de A" if direcao == "a_to_b" else "A vê de B"
        st.markdown(
            f'<p class="priv-secao-titulo">PERMISSÕES POR CAMPO · {rotulo_dir}</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            _renderizar_grade_permissoes(direcao, perms),
            unsafe_allow_html=True,
        )

        # Aviso default
        st.markdown(_aviso_default_html(), unsafe_allow_html=True)

        # Botão Salvar (placeholder -- persiste apenas o legado por enquanto)
        col_salvar, col_resetar, _esp = st.columns([1, 1, 4])
        with col_salvar:
            if st.button(
                "Salvar permissões",
                key="be_priv_btn_salvar_v2",
                type="primary",
                use_container_width=True,
            ):
                # Placeholder: persistência granular fica para sprint-filha.
                # Mantém compatibilidade com o legado.
                try:
                    _salvar_estado(caminho_legado, estado_legado)
                except OSError as exc:
                    st.session_state[_KEY_FLASH] = (
                        "erro",
                        f"Falha ao gravar {caminho_legado}: {exc}",
                    )
                else:
                    st.session_state[_KEY_FLASH] = (
                        "ok",
                        "Permissões registradas (granular: placeholder; "
                        "legado: ok).",
                    )
                st.rerun()

        with col_resetar:
            if st.button(
                "Resetar tudo",
                key="be_priv_btn_resetar_v2",
                use_container_width=True,
            ):
                zerado = {s: False for s in SCHEMAS}
                try:
                    _salvar_estado(caminho_legado, zerado)
                except OSError as exc:
                    st.session_state[_KEY_FLASH] = (
                        "erro",
                        f"Falha ao resetar {caminho_legado}: {exc}",
                    )
                else:
                    st.session_state[_KEY_FLASH] = (
                        "ok",
                        "Privacidade legado resetada (tudo oculto).",
                    )
                st.rerun()

    with col_side:
        # Card "Você (A)"
        st.markdown(
            _card_pessoa_html(
                titulo="VOCÊ (A)",
                avatar_letra="A",
                avatar_cor=CORES["destaque"],
                nome="vault local",
                endereco="~/.ouroboros/",
                chaves_valores=[
                    ("vault id", "local"),
                    ("último sync", "—"),
                    ("modo", "local-first"),
                ],
            ),
            unsafe_allow_html=True,
        )

        # Card "Parceira (B)"
        st.markdown(
            _card_pessoa_html(
                titulo="PARCEIRA (B)",
                avatar_letra="B",
                avatar_cor=CORES["superfluo"],
                nome="vault remoto",
                endereco="rad:* (pendente)",
                chaves_valores=[
                    ("conectado em", "—"),
                    ("último sync", "—"),
                    ("aceitou termos", "pendente"),
                ],
            ),
            unsafe_allow_html=True,
        )

        # Card "Features opcionais" (visual; toggles reais em sprint-filha)
        st.markdown(
            '<div class="priv-pessoa-card">'
            "<h4>FEATURES OPCIONAIS</h4>"
            '<div class="priv-kv"><span class="k">notificar B em mudanças</span>'
            '<span class="v">pendente</span></div>'
            '<div class="priv-kv"><span class="k">modo férias</span>'
            '<span class="v">pendente</span></div>'
            '<div class="priv-kv"><span class="k">recap conjunto</span>'
            '<span class="v">pendente</span></div>'
            "</div>",
            unsafe_allow_html=True,
        )


# "A liberdade é o direito de fazer o que as leis permitem." -- Montesquieu
