"""Cluster Bem-estar -- página "Editor TOML" (UX-RD-19 + UX-V-2.16).

Editor TOML em layout 3-col (lista de arquivos + editor + preview ao vivo).
Lê arquivos `.toml` em ``<vault>/.ouroboros/rotina/`` (criando o diretório
quando ausente). Edição valida via :mod:`tomllib` e persiste em disco
apenas quando passa no schema mínimo.

Mockup-fonte: ``novo-mockup/mockups/28-rotina-toml.html``. UX-V-2.16
trouxe paridade visual com lista lateral, validação inline (0 erros / N
avisos) e preview ao vivo dos itens parseados em tempo real.

Lições aplicadas:

* HTML emitido via :func:`minificar` (UX-RD-04).
* Cores via tokens CSS (`var(--accent-purple)`, etc.) -- nunca hex literal.
* CSS dedicado em ``css/paginas/be_editor_toml.css`` (Onda M).
* Fallback graceful quando vault ausente: ``~/.ouroboros/rotina/``.
* Contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.
* Persistência via ``git`` é objetivo separado (UX-V-2.16 não-objetivo).
"""

from __future__ import annotations

import difflib
import html
import subprocess
import tomllib
from pathlib import Path

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.ui import carregar_css_pagina
from src.mobile_cache.varrer_vault import descobrir_vault_root

_KEY_FLASH = "be_editor_toml_flash"
_KEY_CONTEUDO = "be_editor_toml_conteudo"
_KEY_ARQUIVO = "be_editor_toml_arquivo_sel"

_TEMPLATE_DEFAULT = """# manha.toml -- alarmes, tarefas e contadores recorrentes
# Cada arquivo de rotina é um TOML versionado em git, validado por
# schema e referenciado pelas páginas Hoje, Rotina e Recap.

[[alarme]]
id = "acordar"
nome = "Acordar"
hora = "07:00"
dias = ["seg", "ter", "qua", "qui", "sex"]
som = "padrao.mp3"
snooze = true
tags = ["saude", "cedo"]

[[tarefa]]
id = "diario"
nome = "Escrever diário"
duracao_min = 5
tipo = "diario"

[[contador]]
id = "agua"
nome = "Copos d'água"
meta = 8
reset = "diario"
"""

_NOME_PADRAO = "manha.toml"


# ---------------------------------------------------------------------------
# Helpers de filesystem
# ---------------------------------------------------------------------------

def _resolver_pasta_rotina() -> Path:
    """Resolve a pasta canônica que abriga ``*.toml`` de rotina.

    Preferência:

    1. ``<vault>/.ouroboros/rotina/`` quando o vault existe.
    2. ``~/.ouroboros/rotina/`` como fallback.
    """
    vault_root = descobrir_vault_root()
    base = vault_root if vault_root is not None else Path.home()
    return base / ".ouroboros" / "rotina"


def _resolver_caminho_rotina(nome: str = _NOME_PADRAO) -> Path:
    """Resolve o destino canônico de um arquivo ``<nome>.toml``."""
    return _resolver_pasta_rotina() / nome


def _listar_arquivos_toml(pasta: Path) -> list[dict[str, object]]:
    """Lista ``*.toml`` na pasta com contagem de itens parseáveis.

    Retorna lista de dicts com chaves ``path``, ``nome`` e ``count``
    (alarmes + tarefas + contadores). Quando o arquivo é inválido,
    ``count`` cai para ``0`` sem propagar erro.
    """
    if not pasta.exists():
        return []
    items: list[dict[str, object]] = []
    for arq in sorted(pasta.glob("*.toml")):
        try:
            d = tomllib.loads(arq.read_text(encoding="utf-8"))
            n = sum(len(d.get(k, [])) for k in ("alarme", "tarefa", "contador"))
        except (tomllib.TOMLDecodeError, OSError):
            n = 0
        items.append({"path": str(arq), "nome": arq.name, "count": n})
    return items


def _carregar_conteudo_inicial(caminho: Path) -> str:
    """Lê arquivo se existe; retorna template default caso contrário."""
    if caminho.exists():
        try:
            return caminho.read_text(encoding="utf-8")
        except OSError:
            return _TEMPLATE_DEFAULT
    return _TEMPLATE_DEFAULT


def _salvar(caminho: Path, texto: str) -> None:
    """Grava o texto em disco, criando diretório intermediário."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")


# ---------------------------------------------------------------------------
# Validação semântica
# ---------------------------------------------------------------------------

def _validar_toml(texto: str) -> tuple[bool, str]:
    """Tenta parsear o texto como TOML.

    Retorna ``(True, "")`` quando válido, ou ``(False, mensagem)`` com
    descrição do erro.
    """
    try:
        tomllib.loads(texto)
    except tomllib.TOMLDecodeError as exc:
        return False, str(exc)
    return True, ""


def _validar_com_avisos(texto: str) -> tuple[int, int, list[tuple[str, str]]]:
    """Validação rica: retorna ``(n_erros, n_avisos, mensagens)``.

    ``mensagens`` é lista de tuplas ``(nivel, texto)`` onde ``nivel`` é
    ``"erro"`` ou ``"aviso"``.
    """
    msgs: list[tuple[str, str]] = []
    try:
        d = tomllib.loads(texto)
    except tomllib.TOMLDecodeError as exc:
        return 1, 0, [("erro", f"sintaxe TOML inválida: {exc}")]

    for a in d.get("alarme", []):
        nome = a.get("nome", "?")
        if not a.get("som"):
            msgs.append(("aviso", f"alarme '{nome}' sem campo 'som'"))
        if not a.get("hora"):
            msgs.append(("aviso", f"alarme '{nome}' sem campo 'hora'"))
        if not a.get("dias"):
            msgs.append(("aviso", f"alarme '{nome}' sem campo 'dias'"))
    for t in d.get("tarefa", []):
        nome = t.get("nome", "?")
        if not t.get("tipo"):
            msgs.append(("aviso", f"tarefa '{nome}' sem campo 'tipo'"))
    for c in d.get("contador", []):
        nome = c.get("nome", "?")
        if not c.get("meta"):
            msgs.append(("aviso", f"contador '{nome}' sem campo 'meta'"))
    return 0, len(msgs), msgs


# ---------------------------------------------------------------------------
# Preview ao vivo
# ---------------------------------------------------------------------------

def _preview_visual_cards_html(conteudo: str) -> str:
    """Renderiza HTML rico do preview Visual (cards de alarme/tarefa/contador).

    Monta cartões com hora destacada, dias-bolinhas e tags conforme
    mockup ``28-rotina-toml.html``.
    """
    try:
        d = tomllib.loads(conteudo)
    except tomllib.TOMLDecodeError:
        return minificar(
            '<div class="preview-erro">TOML inválido -- corrija a sintaxe '
            "para liberar o preview.</div>"
        )

    alarmes = d.get("alarme", []) or []
    tarefas = d.get("tarefa", []) or []
    contadores = d.get("contador", []) or []

    if not (alarmes or tarefas or contadores):
        return minificar(
            '<div class="preview-vazio">Sem alarmes, tarefas ou contadores '
            "para mostrar.</div>"
        )

    partes: list[str] = []
    resumo = (
        f"{len(alarmes)} alarme(s) - {len(tarefas)} tarefa(s) - "
        f"{len(contadores)} contador(es)"
    )
    partes.append(f'<div class="preview-resumo">{html.escape(resumo)}</div>')

    dias_canon = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
    rotulos = ["S", "T", "Q", "Q", "S", "S", "D"]

    if alarmes:
        partes.append('<div class="preview-secao">Alarmes</div>')
        for a in alarmes:
            hora = html.escape(str(a.get("hora", "??:??")))
            nome = html.escape(str(a.get("nome", "(sem nome)")))
            ativos = {str(x).lower() for x in (a.get("dias") or [])}
            tags = a.get("tags") or []
            bolinhas = "".join(
                f'<div class="d {"on" if dias_canon[i] in ativos else ""}">'
                f"{rotulos[i]}</div>"
                for i in range(7)
            )
            tags_html = "".join(
                f'<span class="t">{html.escape(str(t))}</span>' for t in tags
            )
            partes.append(
                '<div class="alarme-card">'
                f'<div class="alarme-hr">{hora}</div>'
                '<div class="alarme-meta">'
                f'<div class="nome">{nome}</div>'
                f'<div class="dias">{bolinhas}</div>'
                "</div>"
                f'<div class="alarme-tags">{tags_html}</div>'
                "</div>"
            )

    if tarefas:
        partes.append(
            '<div class="preview-secao">Tarefas geradas em "Hoje"</div>'
        )
        for t in tarefas:
            nome = html.escape(str(t.get("nome", "(sem nome)")))
            tipo = html.escape(str(t.get("tipo", "?")))
            duracao = t.get("duracao_min") or t.get("duracao") or ""
            duracao_txt = (
                f' <span class="meta">~{duracao}min</span>' if duracao else ""
            )
            partes.append(
                '<div class="tarefa-card">'
                '<div class="checkbox"></div>'
                f'<div class="nome">{nome}{duracao_txt}</div>'
                f'<div class="tipo">tipo: {tipo}</div>'
                "</div>"
            )

    if contadores:
        partes.append('<div class="preview-secao">Contadores</div>')
        for c in contadores:
            nome = html.escape(str(c.get("nome", "(sem nome)")))
            meta = html.escape(str(c.get("meta", "?")))
            reset = html.escape(str(c.get("reset", "?")))
            partes.append(
                '<div class="contador-card">'
                f'<div class="nome">{nome}</div>'
                f'<div class="meta">meta: {meta} - reset {reset}</div>'
                "</div>"
            )

    return minificar(f'<div class="preview-bloco">{"".join(partes)}</div>')


def _git_show_head(caminho: Path) -> str | None:
    """Retorna o conteúdo do arquivo na revisão HEAD ou None se ausente.

    Usa ``git show HEAD:<caminho-relativo>``. Se o arquivo não existe
    no HEAD (novo) ou git falha, retorna None.
    """
    try:
        repo_root = Path(
            subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    try:
        rel = caminho.resolve().relative_to(repo_root)
    except ValueError:
        return None

    try:
        out = subprocess.check_output(
            ["git", "show", f"HEAD:{rel.as_posix()}"],
            cwd=str(repo_root),
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return out


def _preview_diff_html(caminho: Path, texto_atual: str) -> str:
    """Renderiza HTML do diff vs HEAD git.

    Quando arquivo não tem versão em HEAD, mostra aviso. Sem diff
    (igual a HEAD), mostra ``sem alterações``.
    """
    head = _git_show_head(caminho)
    if head is None:
        return minificar(
            '<div class="preview-vazio">Arquivo não versionado em HEAD '
            "(novo ou fora do repositório).</div>"
        )

    if head == texto_atual:
        return minificar(
            '<div class="preview-vazio">Sem alterações vs HEAD.</div>'
        )

    linhas: list[str] = []
    diff = difflib.unified_diff(
        head.splitlines(),
        texto_atual.splitlines(),
        fromfile="HEAD",
        tofile="atual",
        lineterm="",
        n=2,
    )
    for ln in diff:
        if ln.startswith("+++") or ln.startswith("---") or ln.startswith("@@"):
            continue
        if ln.startswith("+"):
            linhas.append(f'<span class="add">{html.escape(ln[1:])}</span>')
        elif ln.startswith("-"):
            linhas.append(f'<span class="rem">{html.escape(ln[1:])}</span>')
        else:
            linhas.append(f'<span class="ctx">{html.escape(ln[1:])}</span>')

    rodape = (
        f'<div class="diff-rodape">vs HEAD - '
        f"{html.escape(caminho.name)} - não commitado</div>"
    )
    return minificar(
        f'<div class="diff">{"".join(linhas)}</div>{rodape}'
    )


def _preview_schema_html() -> str:
    """Renderiza HTML do schema canônico aceito (3 entidades)."""
    secoes = [
        (
            "[[alarme]]",
            [
                ("id", "string", True, "identificador único, slug-case"),
                ("nome", "string", True, "rótulo legível em Hoje"),
                ("hora", 'string "HH:MM"', True, "hora local"),
                (
                    "dias",
                    "array<dia>",
                    True,
                    "subconjunto de seg/ter/qua/qui/sex/sab/dom",
                ),
                ("som", "string", False, "default: padrão.mp3"),
                ("snooze", "bool", False, "permite adiar - default true"),
                ("tags", "array<string>", False, "filtros e cruzamentos"),
            ],
        ),
        (
            "[[tarefa]]",
            [
                ("id", "string", True, "identificador único"),
                ("nome", "string", True, "rótulo legível"),
                ("tipo", "string", True, "diário/semanal/recorrente"),
                ("duracao_min", "int", False, "minutos sugeridos"),
            ],
        ),
        (
            "[[contador]]",
            [
                ("id", "string", True, "identificador único"),
                ("nome", "string", True, "rótulo legível"),
                ("meta", "int", True, "valor alvo do período"),
                ("reset", "string", False, "diário/semanal"),
            ],
        ),
    ]
    blocos: list[str] = []
    for titulo, campos in secoes:
        items: list[str] = []
        for k, t, req, desc in campos:
            req_html = (
                '<span class="req">obrigatório</span>' if req else ""
            )
            items.append(
                '<div class="campo">'
                f'<span class="k">{html.escape(k)}</span>'
                f'<span class="tipo">: {html.escape(t)}</span>'
                f"{req_html}"
                f'<span class="desc">{html.escape(desc)}</span>'
                "</div>"
            )
        blocos.append(
            f'<div class="schema-titulo">{html.escape(titulo)} - campos</div>'
            f'<div class="schema">{"".join(items)}</div>'
        )
    return minificar("".join(blocos))


# ---------------------------------------------------------------------------
# Editor: header com badges + linhas numeradas
# ---------------------------------------------------------------------------

def _editor_header_html(
    caminho: Path, modificado: bool, schema_ok: bool
) -> str:
    """Renderiza tools/header do editor (path + status MODIFICADO/SCHEMA OK).

    Espelha ``.editor-tools`` do mockup 28-rotina-toml.html.
    """
    badge_modif = (
        '<span class="status dirty">modificado</span>'
        if modificado
        else '<span class="status clean">limpo</span>'
    )
    badge_schema = (
        '<span class="status ok">schema ok</span>'
        if schema_ok
        else '<span class="status err">schema inválido</span>'
    )
    path_legivel = html.escape(str(caminho))
    return minificar(
        '<div class="editor-tools">'
        f'<span class="path">{path_legivel}</span>'
        f"{badge_modif}{badge_schema}"
        "</div>"
    )


def _renderizar_validacao_rodape(
    erros: int, avisos: int, msgs: list[tuple[str, str]]
) -> str:
    """Renderiza bloco Validação de rodapé (3-col, abaixo das colunas).

    Mostra título `Validação - N erros, M avisos`, lista de mensagens
    e bloco final OK quando schema válido sem avisos.
    """
    titulo_txt = f"Validação - {erros} erro(s), {avisos} aviso(s)"
    cabecalho = (
        '<div class="rv-bloco-titulo">'
        f"{html.escape(titulo_txt)}"
        "</div>"
    )
    if not msgs:
        corpo = (
            '<div class="rv-bloco-vazio">'
            "Schema bate - sem alertas."
            "</div>"
        )
        return minificar(
            f'<div class="rv-bloco">{cabecalho}{corpo}</div>'
        )

    items = []
    for nivel, texto in msgs:
        cls = "err-item erro" if nivel == "erro" else "err-item aviso"
        items.append(
            f'<div class="{cls}">'
            f'<span class="msg">{html.escape(texto)}</span>'
            "</div>"
        )
    corpo = f'<div class="err-list">{"".join(items)}</div>'
    return minificar(
        f'<div class="rv-bloco">{cabecalho}{corpo}</div>'
    )


# ---------------------------------------------------------------------------
# Cabeçalho e painel
# ---------------------------------------------------------------------------

def _page_header_html(pasta: Path, n_arquivos: int) -> str:
    """UX-U-03: usa helper canônico ``componentes/page_header``."""
    from src.dashboard.componentes.page_header import renderizar_page_header

    return renderizar_page_header(
        titulo="EDITOR · ROTINA TOML",
        subtitulo=(
            "Edite arquivos TOML de alarmes, tarefas e contadores recorrentes. "
            "Validação inline e preview ao vivo antes de salvar."
        ),
        sprint_tag="UX-V-2.16",
        pills=[
            {"texto": str(pasta), "tipo": "generica"},
            {"texto": f"{n_arquivos} arquivo(s)", "tipo": "generica"},
        ],
    )


def _renderizar_lista_arquivos(arquivos: list[dict[str, object]], nome_sel: str) -> str:
    """Renderiza HTML da lista visual de arquivos (coluna 1)."""
    if not arquivos:
        return minificar(
            '<div class="lista-vazia">Sem arquivos .toml em '
            "&lt;vault&gt;/.ouroboros/rotina/</div>"
        )
    linhas = ['<div class="toml-files-titulo">Arquivos</div>']
    for arq in arquivos:
        nome = html.escape(str(arq["nome"]))
        count = arq["count"]
        ativo = "ativo" if arq["nome"] == nome_sel else ""
        linhas.append(
            f'<div class="lista-item {ativo}">'
            f'<span class="nome">{nome}</span>'
            f'<span class="count">{count}</span>'
            "</div>"
        )
    return minificar("".join(linhas))


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------

def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Editor TOML (UX-V-2.16, layout 3-col)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes

    renderizar_grupo_acoes(
        [
            {
                "label": "Histórico (git log)",
                "glyph": "list",
                "title": "git log .ouroboros/rotina/",
            },
            {
                "label": "Salvar (commit)",
                "primary": True,
                "glyph": "validar",
                "title": "git commit -m 'rotina: ...'",
            },
        ]
    )

    del dados, periodo, pessoa, ctx

    st.markdown(minificar(carregar_css_pagina("be_editor_toml")), unsafe_allow_html=True)

    pasta = _resolver_pasta_rotina()
    arquivos = _listar_arquivos_toml(pasta)
    st.markdown(_page_header_html(pasta, len(arquivos)), unsafe_allow_html=True)

    flash = st.session_state.pop(_KEY_FLASH, None)
    if flash:
        nivel, mensagem = flash
        if nivel == "ok":
            st.success(mensagem)
        elif nivel == "erro":
            st.error(mensagem)
        else:
            st.info(mensagem)

    col_lista, col_editor, col_preview = st.columns([1, 2, 2])

    # ----- Coluna 1 -- lista de arquivos ----------------------------------
    with col_lista:
        nomes = [str(a["nome"]) for a in arquivos]
        if not nomes:
            nomes = [_NOME_PADRAO]
            st.markdown(
                minificar(
                    '<div class="toml-files-titulo">Arquivos</div>'
                    '<div class="lista-vazia">Sem arquivos -- abra o '
                    "template default e salve.</div>"
                ),
                unsafe_allow_html=True,
            )
        nome_default = st.session_state.get(_KEY_ARQUIVO, nomes[0])
        if nome_default not in nomes:
            nome_default = nomes[0]
        nome_sel = st.selectbox(
            "Arquivo",
            nomes,
            index=nomes.index(nome_default),
            key="be_editor_toml_select_arquivo",
        )
        if arquivos:
            st.markdown(
                _renderizar_lista_arquivos(arquivos, nome_sel),
                unsafe_allow_html=True,
            )

    if nome_sel != st.session_state.get(_KEY_ARQUIVO):
        st.session_state[_KEY_ARQUIVO] = nome_sel
        caminho_sel = _resolver_caminho_rotina(nome_sel)
        st.session_state[_KEY_CONTEUDO] = _carregar_conteudo_inicial(caminho_sel)
    else:
        caminho_sel = _resolver_caminho_rotina(nome_sel)

    if _KEY_CONTEUDO not in st.session_state:
        st.session_state[_KEY_CONTEUDO] = _carregar_conteudo_inicial(caminho_sel)

    # ----- Coluna 2 -- editor ---------------------------------------------
    with col_editor:
        # Header com badges MODIFICADO/SCHEMA OK
        texto_em_disco = _carregar_conteudo_inicial(caminho_sel)
        texto_atual = st.session_state.get(_KEY_CONTEUDO, texto_em_disco)
        modificado_pre = texto_atual != texto_em_disco
        ok_pre, _ = _validar_toml(texto_atual)
        st.markdown(
            _editor_header_html(caminho_sel, modificado_pre, ok_pre),
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="toml-editor-wrap">', unsafe_allow_html=True
        )
        texto = st.text_area(
            "Conteúdo do TOML",
            key=_KEY_CONTEUDO,
            height=480,
            help="Edite o arquivo TOML. Validação inline mostra erros e avisos.",
            label_visibility="collapsed",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        erros, avisos, msgs = _validar_com_avisos(texto)

        col_validar, col_salvar, col_recarregar = st.columns([1, 1, 1])
        with col_validar:
            if st.button(
                "Validar",
                key="be_editor_toml_btn_validar",
                use_container_width=True,
            ):
                ok, msg = _validar_toml(texto)
                if ok:
                    st.success("TOML válido. Schema mínimo conferido.")
                else:
                    st.error(f"TOML inválido: {msg}")

        with col_salvar:
            if st.button(
                "Salvar",
                key="be_editor_toml_btn_salvar",
                type="primary",
                use_container_width=True,
            ):
                ok, msg = _validar_toml(texto)
                if not ok:
                    st.session_state[_KEY_FLASH] = (
                        "erro",
                        f"Não salvei: TOML inválido ({msg}).",
                    )
                else:
                    try:
                        _salvar(caminho_sel, texto)
                    except OSError as exc:
                        st.session_state[_KEY_FLASH] = (
                            "erro",
                            f"Falha ao gravar {caminho_sel}: {exc}",
                        )
                    else:
                        st.session_state[_KEY_FLASH] = (
                            "ok",
                            f"Gravado em {caminho_sel}.",
                        )
                st.rerun()

        with col_recarregar:
            if st.button(
                "Recarregar",
                key="be_editor_toml_btn_recarregar",
                use_container_width=True,
            ):
                st.session_state[_KEY_CONTEUDO] = _carregar_conteudo_inicial(
                    caminho_sel
                )
                st.session_state[_KEY_FLASH] = (
                    "info",
                    "Conteúdo recarregado do disco.",
                )
                st.rerun()

    # ----- Coluna 3 -- preview ao vivo (3 tabs) ---------------------------
    with col_preview:
        st.markdown(
            minificar('<div class="preview-titulo">Preview ao vivo</div>'),
            unsafe_allow_html=True,
        )
        tab_visual, tab_diff, tab_schema = st.tabs(
            ["Visual", "Diff vs HEAD", "Schema"]
        )
        with tab_visual:
            st.markdown(
                _preview_visual_cards_html(texto),
                unsafe_allow_html=True,
            )
        with tab_diff:
            st.markdown(
                _preview_diff_html(caminho_sel, texto),
                unsafe_allow_html=True,
            )
        with tab_schema:
            st.markdown(_preview_schema_html(), unsafe_allow_html=True)

    # ----- Rodape global -- bloco Validação -------------------------------
    st.markdown(
        _renderizar_validacao_rodape(erros, avisos, msgs),
        unsafe_allow_html=True,
    )


# CSS dedicado: src/dashboard/css/paginas/be_editor_toml.css (UX-V-2.16).

# "A escrita é a pintura da voz." -- Voltaire
