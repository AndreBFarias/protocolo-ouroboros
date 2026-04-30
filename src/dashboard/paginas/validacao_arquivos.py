"""Aba "Validação por Arquivo" -- Sprint VALIDAÇÃO-CSV-01.

Lê ``data/output/validacao_arquivos.csv`` (gerado por extratores via
``src/load/validacao_csv.py``) e expõe interface para o dono marcar
``valor_humano`` + ``status_humano`` + ``observacoes_humano`` de cada
linha.

Princípios:

  - Coexiste com Revisor 4-way (Sprint D2). Revisor opera sobre transações;
    esta aba opera sobre (arquivo, campo). Sem fusão.
  - Cobertura total: lista todas as linhas pendentes, sem filtro de
    inclusão por valor (Decisão D5/D7 do dono em 2026-04-29).
  - Edição inline via ``st.data_editor``; persistência por botão "Salvar".
  - PII mascarada antes de exibir, conforme padrão do Revisor.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import streamlit as st

from src.dashboard.tema import callout_html, hero_titulo_html
from src.load import validacao_csv as vc

_PADRAO_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_PADRAO_CNPJ = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")


def _mascarar_pii(texto: str) -> str:
    """Mascara CPF e CNPJ que aparecerem em colunas de valor."""
    if not texto:
        return texto
    texto = _PADRAO_CPF.sub("XXX.XXX.XXX-XX", texto)
    texto = _PADRAO_CNPJ.sub("XX.XXX.XXX/XXXX-XX", texto)
    return texto


def _carregar_dataframe(caminho: Path) -> pd.DataFrame:
    """Carrega CSV como DataFrame, devolvendo schema esperado mesmo se vazio."""
    linhas = vc.ler_csv(caminho)
    if not linhas:
        return pd.DataFrame(columns=vc.CABECALHO)
    registros = [linha.to_row() for linha in linhas]
    return pd.DataFrame(registros, columns=vc.CABECALHO)


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Entry point da aba Validação por Arquivo."""
    del dados, mes_selecionado, pessoa, ctx  # aba opera sobre CSV próprio

    st.markdown(
        hero_titulo_html(
            "",
            "Validação por Arquivo",
            "Marcação humana sobre cada (arquivo × campo extraído). "
            "Coexiste com Revisor 4-way -- aqui o foco é cobertura por arquivo.",
        ),
        unsafe_allow_html=True,
    )

    raiz_repo = Path(__file__).resolve().parents[3]
    caminho_csv = raiz_repo / "data" / "output" / "validacao_arquivos.csv"

    df = _carregar_dataframe(caminho_csv)
    if df.empty:
        st.markdown(
            callout_html(
                "info",
                "CSV ainda vazio. Rode o pipeline para extratores começarem a "
                "popular `data/output/validacao_arquivos.csv`.",
            ),
            unsafe_allow_html=True,
        )
        return

    # Mascarar PII em colunas de valor antes de exibir
    for coluna in ("valor_etl", "valor_opus", "valor_humano"):
        df[coluna] = df[coluna].astype(str).apply(_mascarar_pii)

    # Sumário em pills
    total = len(df)
    pendentes_humano = int((df["status_humano"] == "pendente").sum())
    com_etl = int((df["valor_etl"].astype(str) != "").sum())
    concordancia_3way = int(
        (
            (df["status_etl"] == "ok")
            & (df["status_opus"] == "ok")
            & (df["status_humano"] == "ok")
        ).sum()
    )

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Total linhas", total)
    col_b.metric("Pendentes humano", pendentes_humano)
    col_c.metric("Com valor ETL", com_etl)
    col_d.metric("Concordância 3-way (ok×3)", concordancia_3way)

    # Filtros
    st.subheader("Filtros")
    f_col1, f_col2 = st.columns(2)
    tipos = sorted(df["tipo_arquivo"].astype(str).unique().tolist())
    tipo_filtro = f_col1.selectbox(
        "Tipo de arquivo",
        options=["(todos)"] + tipos,
        key="validacao_filtro_tipo",
    )
    status_filtro = f_col2.selectbox(
        "Status humano",
        options=["(todos)"] + sorted(vc.STATUS_VALIDOS),
        key="validacao_filtro_status",
    )

    df_filtrado = df.copy()
    if tipo_filtro != "(todos)":
        df_filtrado = df_filtrado[df_filtrado["tipo_arquivo"] == tipo_filtro]
    if status_filtro != "(todos)":
        df_filtrado = df_filtrado[df_filtrado["status_humano"] == status_filtro]

    if df_filtrado.empty:
        st.markdown(
            callout_html("info", "Sem linhas após aplicar filtros."),
            unsafe_allow_html=True,
        )
        return

    # Edição inline -- apenas valor_humano, status_humano, observacoes_humano
    st.subheader(f"Edição ({len(df_filtrado)} linhas)")
    st.caption(
        "Edite as colunas `valor_humano`, `status_humano` e "
        "`observacoes_humano`. Demais colunas são read-only. "
        "Clique em 'Salvar alterações' ao final."
    )

    colunas_edicao = ["valor_humano", "status_humano", "observacoes_humano"]
    colunas_leitura = [c for c in vc.CABECALHO if c not in colunas_edicao]

    config_colunas = {
        coluna: st.column_config.TextColumn(coluna, disabled=True)
        for coluna in colunas_leitura
    }
    config_colunas["valor_humano"] = st.column_config.TextColumn(
        "valor_humano", help="Valor confirmado pelo dono"
    )
    config_colunas["status_humano"] = st.column_config.SelectboxColumn(
        "status_humano",
        options=sorted(vc.STATUS_VALIDOS),
        required=True,
    )
    config_colunas["observacoes_humano"] = st.column_config.TextColumn(
        "observacoes_humano", help="Notas livres -- ex.: 'bate com PDF'"
    )

    df_editado = st.data_editor(
        df_filtrado,
        column_config=config_colunas,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        key="validacao_data_editor",
    )

    if st.button("Salvar alterações", type="primary"):
        atualizadas = 0
        for _, linha in df_editado.iterrows():
            ok = vc.atualizar_validacao_humana(
                sha8=str(linha["sha8_arquivo"]),
                campo=str(linha["campo"]),
                valor_humano=str(linha["valor_humano"]),
                status_humano=str(linha["status_humano"]),
                observacoes=str(linha["observacoes_humano"]),
                caminho_csv=caminho_csv,
            )
            if ok:
                atualizadas += 1
        st.success(f"{atualizadas} linha(s) atualizada(s) em {caminho_csv.name}.")
