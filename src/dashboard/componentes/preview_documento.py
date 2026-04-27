"""Preview inline de documento (PDF ou imagem) no dashboard — Sprint 74.

Streamlit não serve arquivos locais via `file://` (bloqueio CORS). Para
preview totalmente offline, embedamos o PDF via `data:application/pdf;base64,…`
em `<iframe>` e imagens via `st.image`.

Regras:
  - PDF acima de `LIMITE_BYTES_EMBED` (5 MB) vira `st.download_button` (base64
    infla ~33% e o iframe trava).
  - Imagens comuns (PNG/JPG/WEBP/GIF) renderizam via `st.image` responsivo.
  - Tipos não suportados caem em `st.download_button` + aviso.

API pública:

    preview_documento(caminho_original, altura=600)
    tipo_arquivo(caminho) -> "pdf" | "imagem" | "outro"
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Literal

TipoArquivo = Literal["pdf", "imagem", "outro"]

LIMITE_BYTES_EMBED: int = 5 * 1024 * 1024  # 5 MB
SUFIXOS_IMAGEM: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})


def tipo_arquivo(caminho: Path) -> TipoArquivo:
    """Classifica extensão em {pdf, imagem, outro}."""
    suf = caminho.suffix.lower()
    if suf == ".pdf":
        return "pdf"
    if suf in SUFIXOS_IMAGEM:
        return "imagem"
    return "outro"


def _tipo_arquivo(caminho: Path) -> TipoArquivo:
    """Alias privado mantido pela compatibilidade dos testes do spec."""
    return tipo_arquivo(caminho)


def _pdf_iframe_html(b64: str, altura: int) -> str:
    """Monta o HTML do iframe base64. Isolado para facilitar teste."""
    return (
        f'<iframe src="data:application/pdf;base64,{b64}" '
        f'width="100%" height="{altura}" '
        f'style="border:1px solid #44475a; border-radius:6px;">'
        f"</iframe>"
    )


def preview_documento(caminho_original: Path, altura: int = 600) -> None:
    """Renderiza preview inline ou fallback download.

    Ordem de tentativa:
      1. Arquivo inexistente → ``st.error``.
      2. PDF > 5 MB → ``st.warning`` + ``st.download_button``.
      3. PDF <= 5 MB → iframe data URL base64.
      4. Imagem → ``st.image``.
      5. Outro → ``st.info`` + ``st.download_button``.
    """
    try:
        import streamlit as st
    except ImportError:  # pragma: no cover — runtime sempre tem streamlit
        raise RuntimeError("streamlit é dependência obrigatória em runtime")

    if not caminho_original.exists():
        st.error(f"Arquivo não encontrado: {caminho_original.name}")
        return

    tipo = tipo_arquivo(caminho_original)
    tamanho = caminho_original.stat().st_size

    if tipo == "pdf":
        if tamanho > LIMITE_BYTES_EMBED:
            st.warning(f"PDF grande ({tamanho / 1024 / 1024:.1f} MB). Baixe para visualizar.")
            st.download_button(
                "Baixar PDF",
                data=caminho_original.read_bytes(),
                file_name=caminho_original.name,
                mime="application/pdf",
            )
            return
        b64 = base64.b64encode(caminho_original.read_bytes()).decode("utf-8")
        st.markdown(_pdf_iframe_html(b64, altura), unsafe_allow_html=True)
        return

    if tipo == "imagem":
        # use_container_width substituiu use_column_width em Streamlit 1.33.
        try:
            st.image(str(caminho_original), use_container_width=True)
        except TypeError:  # pragma: no cover — Streamlit antigo
            st.image(str(caminho_original), use_column_width=True)
        return

    st.info(f"Preview não suportado para {caminho_original.suffix}")
    st.download_button(
        "Baixar arquivo",
        data=caminho_original.read_bytes(),
        file_name=caminho_original.name,
    )


# "Um documento que não se vê é um documento que não existe." — princípio
