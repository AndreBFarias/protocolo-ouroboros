"""Modal de detalhes da transação — Sprint 74 (ADR-20).

Usa `st.dialog` (Streamlit 1.31+) como modal reutilizável. Exibe: metadados
da transação, estado documental inferido (aberta/confirmada/
totalmente_documentada/irrecuperavel) e preview inline do primeiro
documento vinculado.

Estado documental (heurística simples sobre tipos de edge semânticos da
Sprint 74, lidos de `edge.evidencia.tipo_edge_semantico`):

  - totalmente_documentada: tem ``origem`` + (``confirma`` ou ``comprovante``)
  - confirmada:             tem ``confirma`` ou ``comprovante``
  - aberta:                 nenhum vínculo
  - irrecuperavel:          flag externa (placeholder; Sprint futura)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.dashboard.componentes.preview_documento import preview_documento

_CORES_ESTADO: dict[str, str] = {
    "aberta": "red",
    "confirmada": "orange",
    "totalmente_documentada": "green",
    "irrecuperavel": "gray",
}


def inferir_estado(docs_vinculados: list[dict[str, Any]]) -> str:
    """Deriva estado documental a partir dos tipos de edge semântico."""
    if not docs_vinculados:
        return "aberta"
    tipos = {
        str(d.get("tipo_edge_semantico") or d.get("tipo_edge") or "").lower()
        for d in docs_vinculados
    }
    tipos.discard("")
    if "origem" in tipos and ("confirma" in tipos or "comprovante" in tipos):
        return "totalmente_documentada"
    if "confirma" in tipos or "comprovante" in tipos or "pago_com" in tipos:
        return "confirmada"
    if "origem" in tipos:
        return "confirmada"  # só origem sem comprovante ainda é "confirmada" parcial
    return "aberta"


def _formatar_brl(valor: float) -> str:
    """Formata como R$ 1.234,56 — PT-BR."""
    s = f"{valor:,.2f}"
    # swap: vírgula e ponto PT-BR via placeholder tripla.
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _render_header(tx: dict[str, Any]) -> None:
    """Renderiza 4 metrics no topo do modal: data, valor, categoria, banco."""
    import streamlit as st

    col1, col2, col3, col4 = st.columns(4)
    data_v = tx.get("data")
    data_str = data_v.strftime("%d/%m/%Y") if hasattr(data_v, "strftime") else str(data_v or "-")
    valor = float(tx.get("valor") or 0.0)
    col1.metric("Data", data_str)
    col2.metric("Valor", _formatar_brl(valor))
    col3.metric("Categoria", str(tx.get("categoria", "-")))
    col4.metric("Banco", str(tx.get("banco_origem", "-")))


def _render_estado(estado: str) -> None:
    import streamlit as st

    cor = _CORES_ESTADO.get(estado, "gray")
    rotulo = estado.upper().replace("_", " ")
    st.markdown(f"**Estado:** :{cor}[{rotulo}]")


def _render_documentos(docs_vinculados: list[dict[str, Any]]) -> None:
    """Expander por documento, primeiro expandido. Preview inline se há caminho."""
    import streamlit as st

    for i, doc in enumerate(docs_vinculados):
        tipo_doc = doc.get("tipo_documento") or "documento"
        tipo_edge = doc.get("tipo_edge_semantico") or doc.get("tipo_edge") or "vínculo"
        valor_d = float(doc.get("valor") or 0.0)
        with st.expander(
            f"{tipo_doc} — {tipo_edge} — {_formatar_brl(valor_d)}",
            expanded=(i == 0),
        ):
            caminho_raw = doc.get("arquivo_original") or doc.get("caminho")
            if caminho_raw:
                preview_documento(Path(str(caminho_raw)), altura=500)
            else:
                st.info("Documento sem caminho físico registrado.")


def _render_sem_docs(tx: dict[str, Any]) -> None:
    import streamlit as st

    st.warning("Nenhum comprovante vinculado.")
    st.caption(
        "Jogue um PDF/JPG em `~/Controle de Bordo/Inbox/` e rode "
        "`./run.sh --inbox` para tentar match automático."
    )


def mostrar_conteudo(tx: dict[str, Any], docs_vinculados: list[dict[str, Any]]) -> None:
    """Corpo do modal — sem decorator `st.dialog`, útil para testes.

    A rotina `mostrar_modal` abaixo é o wrapper oficial com decorator
    `@st.dialog`. Separar o corpo permite testar sem contexto Streamlit.
    """
    _render_header(tx)

    try:
        import streamlit as st

        st.divider()
    except ImportError:  # pragma: no cover
        pass

    estado = inferir_estado(docs_vinculados)
    _render_estado(estado)

    if docs_vinculados:
        _render_documentos(docs_vinculados)
    else:
        _render_sem_docs(tx)


def mostrar_modal(tx: dict[str, Any], docs_vinculados: list[dict[str, Any]]) -> None:
    """Abre o modal via `st.dialog`. Streamlit 1.31+ obrigatório."""
    import streamlit as st

    @st.dialog("Detalhes da transação", width="large")
    def _render() -> None:
        mostrar_conteudo(tx, docs_vinculados)

    _render()


# "Cada vínculo é uma memória contra o esquecimento." — princípio
