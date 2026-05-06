"""Cluster Bem-estar -- página "Privacidade" (UX-RD-19).

6 toggles que controlam o que pessoa_a vê de pessoa_b (e vice-versa)
por schema de dados (humor, diário, eventos, medidas, treinos, ciclo).
Estado persistido em ``<vault>/.ouroboros/privacidade.toml`` (ou
``~/.ouroboros/privacidade.toml`` no fallback).

Mockup-fonte: ``novo-mockup/mockups/27-privacidade.html``.

Lições UX-RD aplicadas:

* HTML emitido via :func:`minificar` (UX-RD-04).
* Cores via ``CORES`` em :mod:`src.dashboard.tema` -- nunca hex literal.
* Fallback graceful: arquivo ausente vira default conservador (tudo
  oculto), criado ao primeiro save.
* Contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pandas as pd
import streamlit as st

from src.dashboard.tema import CORES
from src.mobile_cache.varrer_vault import descobrir_vault_root

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
    vault_root = descobrir_vault_root()
    base = vault_root if vault_root is not None else Path.home()
    return base / ".ouroboros" / "privacidade.toml"


def _ler_estado(caminho: Path) -> dict[str, bool]:
    """Lê arquivo TOML e retorna ``{schema: bool}`` para os 6 schemas.

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
    """Grava o TOML com a seção ``[compartilhar]``."""
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


def _page_header_html(qtd_compartilhadas: int, caminho: Path) -> str:
    """UX-U-03: usa helper canônico ``componentes/page_header``."""
    from src.dashboard.componentes.page_header import renderizar_page_header

    return renderizar_page_header(
        titulo="PRIVACIDADE · A ↔ B",
        subtitulo=(
            f"Controle por schema do que cada pessoa vê do outro. "
            f"{qtd_compartilhadas} de 6 áreas compartilhadas."
        ),
        sprint_tag="UX-RD-19",
        pills=[{"texto": caminho.name, "tipo": "generica"}],
    )


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página Bem-estar / Privacidade."""
    del dados, periodo, pessoa, ctx

    caminho = _resolver_caminho()
    estado_atual = _ler_estado(caminho)
    qtd = sum(1 for v in estado_atual.values() if v)

    st.markdown(_page_header_html(qtd, caminho), unsafe_allow_html=True)

    flash = st.session_state.pop(_KEY_FLASH, None)
    if flash:
        nivel, mensagem = flash
        if nivel == "ok":
            st.success(mensagem)
        else:
            st.error(mensagem)

    st.markdown(
        f'<p style="color:{CORES["texto_muted"]};font-size:12px;'
        f'font-family:ui-monospace,monospace;">'
        f"Default conservador: tudo começa em oculto. Liberar campo a "
        f"campo gera entrada no audit log do próximo sync."
        f"</p>",
        unsafe_allow_html=True,
    )

    novo_estado: dict[str, bool] = {}
    for s in SCHEMAS:
        chave = f"be_priv_{s}"
        novo_estado[s] = st.toggle(
            LABEL_SCHEMA[s],
            value=estado_atual[s],
            key=chave,
            help=f"Compartilhar dados de {LABEL_SCHEMA[s]} com a outra pessoa.",
        )

    col_salvar, col_resetar, _ = st.columns([1, 1, 4])
    with col_salvar:
        if st.button(
            "Salvar",
            key="be_priv_btn_salvar",
            type="primary",
            use_container_width=True,
        ):
            try:
                _salvar_estado(caminho, novo_estado)
            except OSError as exc:
                st.session_state[_KEY_FLASH] = (
                    "erro",
                    f"Falha ao gravar {caminho}: {exc}",
                )
            else:
                st.session_state[_KEY_FLASH] = (
                    "ok",
                    f"Privacidade salva em {caminho}.",
                )
            st.rerun()

    with col_resetar:
        if st.button(
            "Resetar tudo",
            key="be_priv_btn_resetar",
            use_container_width=True,
        ):
            zerado = {s: False for s in SCHEMAS}
            try:
                _salvar_estado(caminho, zerado)
            except OSError as exc:
                st.session_state[_KEY_FLASH] = (
                    "erro",
                    f"Falha ao resetar {caminho}: {exc}",
                )
            else:
                st.session_state[_KEY_FLASH] = (
                    "ok",
                    "Privacidade resetada (tudo oculto).",
                )
            st.rerun()


# "A liberdade é o direito de fazer o que as leis permitem." -- Montesquieu
