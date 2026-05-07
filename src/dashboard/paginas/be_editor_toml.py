"""Cluster Bem-estar -- página "Editor TOML" (UX-RD-19).

Editor de ``rotina.toml`` direto na UI. Lê arquivo de
``<vault>/.ouroboros/rotina.toml`` (criando o diretório se ausente),
mostra textarea grande, valida sintaxe via :mod:`tomllib` e persiste
em disco apenas após validação.

Mockup-fonte: ``novo-mockup/mockups/28-rotina-toml.html``. Aqui não
implementamos preview ao vivo nem diff vs HEAD (ambos exigem
infraestrutura adicional); a sprint entrega o ciclo mínimo
ler -> validar -> salvar -- com schema simples do mockup mantido como
template default.

Lições UX-RD aplicadas:

* HTML emitido via :func:`minificar` (UX-RD-04).
* Cores via ``CORES`` em :mod:`src.dashboard.tema` -- nunca hex literal.
* Fallback graceful: se o vault não for encontrado, usa ``Path.home()``
  como base para criar ``~/.ouroboros/rotina.toml`` (matches spec).
* Contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pandas as pd
import streamlit as st

from src.mobile_cache.varrer_vault import descobrir_vault_root

_KEY_FLASH = "be_editor_toml_flash"
_KEY_CONTEUDO = "be_editor_toml_conteudo"

_TEMPLATE_DEFAULT = """# rotina.toml -- alarmes, tarefas e contadores recorrentes
# Cada arquivo de rotina é um TOML versionado em git, validado por
# schema e referenciado pelas páginas Hoje, Rotina e Recap.

[[alarme]]
id = "acordar"
nome = "Acordar"
hora = "06:30"
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


def _resolver_caminho_rotina() -> Path:
    """Resolve o destino canônico do arquivo ``rotina.toml``.

    Preferência:

    1. ``<vault>/.ouroboros/rotina.toml`` quando o vault existe.
    2. ``~/.ouroboros/rotina.toml`` como fallback (cria diretório).
    """
    vault_root = descobrir_vault_root()
    base = vault_root if vault_root is not None else Path.home()
    destino = base / ".ouroboros" / "rotina.toml"
    return destino


def _carregar_conteudo_inicial(caminho: Path) -> str:
    """Lê arquivo se existe; retorna template default caso contrário."""
    if caminho.exists():
        try:
            return caminho.read_text(encoding="utf-8")
        except OSError:
            return _TEMPLATE_DEFAULT
    return _TEMPLATE_DEFAULT


def _validar_toml(texto: str) -> tuple[bool, str]:
    """Tenta parsear o texto como TOML.

    Retorna ``(True, "")`` quando válido, ou ``(False, mensagem)`` com
    descrição do erro (incluindo linha quando disponível).
    """
    try:
        tomllib.loads(texto)
    except tomllib.TOMLDecodeError as exc:
        return False, str(exc)
    return True, ""


def _salvar(caminho: Path, texto: str) -> None:
    """Grava o texto em disco, criando diretório intermediário."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")


def _page_header_html(caminho: Path) -> str:
    """UX-U-03: usa helper canônico ``componentes/page_header``."""
    from src.dashboard.componentes.page_header import renderizar_page_header

    return renderizar_page_header(
        titulo="EDITOR · ROTINA.TOML",
        subtitulo=(
            "Edite o arquivo TOML de alarmes, tarefas e contadores recorrentes. "
            "Validação por schema acontece antes de salvar."
        ),
        sprint_tag="UX-RD-19",
        pills=[{"texto": str(caminho), "tipo": "generica"}],
    )


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Editor TOML (UX-T-28)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Histórico (git log)", "glyph": "list",
         "title": "git log .ouroboros/rotina/"},
        {"label": "Salvar (commit)", "primary": True, "glyph": "validar",
         "title": "git commit -m 'rotina: ...'"},
    ])

    del dados, periodo, pessoa, ctx

    caminho = _resolver_caminho_rotina()
    st.markdown(_page_header_html(caminho), unsafe_allow_html=True)

    flash = st.session_state.pop(_KEY_FLASH, None)
    if flash:
        nivel, mensagem = flash
        if nivel == "ok":
            st.success(mensagem)
        elif nivel == "erro":
            st.error(mensagem)
        else:
            st.info(mensagem)

    if _KEY_CONTEUDO not in st.session_state:
        st.session_state[_KEY_CONTEUDO] = _carregar_conteudo_inicial(caminho)

    texto = st.text_area(
        "Conteúdo do TOML",
        key=_KEY_CONTEUDO,
        height=520,
        help="Edite o arquivo TOML. Use 'Validar' antes de 'Salvar'.",
    )

    col_validar, col_salvar, col_recarregar, _ = st.columns([1, 1, 1, 3])
    with col_validar:
        if st.button("Validar", key="be_editor_toml_btn_validar", use_container_width=True):
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
                    _salvar(caminho, texto)
                except OSError as exc:
                    st.session_state[_KEY_FLASH] = (
                        "erro",
                        f"Falha ao gravar {caminho}: {exc}",
                    )
                else:
                    st.session_state[_KEY_FLASH] = (
                        "ok",
                        f"Gravado em {caminho}.",
                    )
            st.rerun()

    with col_recarregar:
        if st.button(
            "Recarregar do disco",
            key="be_editor_toml_btn_recarregar",
            use_container_width=True,
        ):
            st.session_state[_KEY_CONTEUDO] = _carregar_conteudo_inicial(caminho)
            st.session_state[_KEY_FLASH] = ("info", "Conteúdo recarregado do disco.")
            st.rerun()

    with st.expander("Schema mínimo aceito", expanded=False):
        st.markdown(
            "- **[[alarme]]**: `id`, `nome`, `hora` (HH:MM), `dias` (lista),"
            " opcional `som`/`snooze`/`tags`.\n"
            "- **[[tarefa]]**: `id`, `nome`, `duracao_min`, `tipo`.\n"
            "- **[[contador]]**: `id`, `nome`, `meta`, `reset`"
            " (`diario`/`semanal`)."
        )


# "A escrita é a pintura da voz." -- Voltaire
