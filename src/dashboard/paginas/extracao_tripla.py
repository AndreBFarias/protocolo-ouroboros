"""Aba "Extração Tripla" -- Sprint UX-RD-11.

Layout 3 colunas que junta no mesmo lugar:

  - Coluna 1 (lista): arquivos por tipo, badge formato, status pill
  - Coluna 2 (viewer): preview do arquivo selecionado (PDF / imagem / CSV / XLSX)
  - Coluna 3 (tabela tripla): linhas = campos extraídos; colunas =
    ETL | Opus | Humano. Divergência ETL ≠ Opus pinta cell laranja.
    Consenso ETL ∩ Opus pré-popula valor_humano. Botão "Validar" grava
    valor_humano + status_humano=ok no CSV via ``validacao_csv``.

Substitui ``paginas/validacao_arquivos.py`` (que vira stub redirecionador
por 1 sprint para retrocompat).

Princípios:

  - Coexiste com Revisor 4-way (Sprint D2). Revisor opera sobre transações;
    esta aba opera sobre (arquivo, campo). Sem fusão.
  - Cobertura total: lista todos os arquivos pendentes, sem filtro de
    inclusão por valor (Decisão D5/D7 do dono em 2026-04-29).
  - Tema dark Dracula via ``CORES`` -- divergência usa ``CORES['alerta']``
    (laranja).
  - PII mascarada antes de exibir, conforme padrão do Revisor.
  - HTML grande passa por ``html_utils.minificar`` para evitar bloco
    ``<pre><code>`` indesejado do CommonMark do Streamlit (UX-RD-04).

API pública: ``renderizar(dados, mes_selecionado, pessoa, ctx)``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.preview_documento import preview_documento
from src.dashboard.componentes.preview_documento import tipo_arquivo as _tipo_preview
from src.dashboard.tema import CORES, callout_html, hero_titulo_html
from src.load import validacao_csv as vc

_PADRAO_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_PADRAO_CNPJ = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")

# Mapa extensão -> badge de formato. Ordem visual: PDF/CSV/IMG/XLSX/OFX/HTML.
_BADGE_FORMATO: dict[str, str] = {
    ".pdf": "PDF",
    ".csv": "CSV",
    ".png": "IMG",
    ".jpg": "IMG",
    ".jpeg": "IMG",
    ".webp": "IMG",
    ".gif": "IMG",
    ".xlsx": "XLSX",
    ".xls": "XLSX",
    ".ofx": "OFX",
    ".html": "HTML",
    ".htm": "HTML",
    ".xml": "XML",
}

# Mapa status -> token de cor (humano_*). Espelha tokens.css do redesign.
_COR_STATUS: dict[str, str] = {
    "ok": CORES["humano_aprovado"],
    "aprovado": CORES["humano_aprovado"],
    "erro": CORES["humano_rejeitado"],
    "lacuna": CORES["humano_revisar"],
    "pendente": CORES["humano_pendente"],
    "conflito": CORES["alerta"],
    "validado": CORES["humano_aprovado"],
    "extraido": CORES["d7_calibracao"],
    "aguardando": CORES["humano_pendente"],
}

CHAVE_SESSION_ARQUIVO_SELECIONADO: str = "extracao_tripla_arquivo_selecionado"


def _mascarar_pii(texto: str) -> str:
    """Mascara CPF e CNPJ que aparecerem em colunas de valor."""
    if not texto:
        return texto
    texto = _PADRAO_CPF.sub("XXX.XXX.XXX-XX", texto)
    texto = _PADRAO_CNPJ.sub("XX.XXX.XXX/XXXX-XX", texto)
    return texto


def _carregar_dataframe(caminho: Path) -> pd.DataFrame:
    """Carrega o CSV inteiro como DataFrame com schema canônico."""
    linhas = vc.ler_csv(caminho)
    if not linhas:
        return pd.DataFrame(columns=vc.CABECALHO)
    registros = [linha.to_row() for linha in linhas]
    return pd.DataFrame(registros, columns=vc.CABECALHO)


def _badge_formato(caminho_relativo: str) -> str:
    """Devolve o token de badge (PDF/CSV/IMG/XLSX/OFX/HTML/XML) ou '???'."""
    suf = Path(caminho_relativo).suffix.lower()
    return _BADGE_FORMATO.get(suf, "???")


def _agrupar_por_arquivo(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa por (sha8_arquivo, caminho_relativo) e resume status global.

    Status agregado:
      - "validado" se todas as linhas têm status_humano in {ok, aprovado}
      - "conflito" se existe alguma divergência ETL≠Opus
      - "extraido" se há valor_etl ou valor_opus em alguma linha
      - "aguardando" caso contrário
    """
    if df.empty:
        return pd.DataFrame(
            columns=[
                "sha8_arquivo",
                "tipo_arquivo",
                "caminho_relativo",
                "total_campos",
                "status_global",
            ]
        )

    grupos = []
    for (sha8, caminho), grupo in df.groupby(["sha8_arquivo", "caminho_relativo"]):
        tipo = str(grupo["tipo_arquivo"].iloc[0])
        total = len(grupo)
        status_humanos = set(grupo["status_humano"].astype(str).str.lower())
        status = "aguardando"
        if status_humanos and status_humanos.issubset({"ok", "aprovado"}):
            status = "validado"
        else:
            divergencias = (
                (grupo["valor_etl"].astype(str) != "")
                & (grupo["valor_opus"].astype(str) != "")
                & (grupo["valor_etl"].astype(str) != grupo["valor_opus"].astype(str))
            )
            if bool(divergencias.any()):
                status = "conflito"
            elif (
                (grupo["valor_etl"].astype(str) != "").any()
                or (grupo["valor_opus"].astype(str) != "").any()
            ):
                status = "extraido"
        grupos.append(
            {
                "sha8_arquivo": sha8,
                "tipo_arquivo": tipo,
                "caminho_relativo": caminho,
                "total_campos": total,
                "status_global": status,
            }
        )
    return pd.DataFrame(grupos)


def _detectar_divergencia(linha: pd.Series) -> bool:
    """True se ETL e Opus discordam (ambos não-vazios e diferentes)."""
    etl = str(linha.get("valor_etl") or "").strip()
    opus = str(linha.get("valor_opus") or "").strip()
    if not etl or not opus:
        return False
    return etl != opus


def _consenso(linha: pd.Series) -> str:
    """Devolve consenso ETL ∩ Opus quando aplicável; senão string vazia."""
    etl = str(linha.get("valor_etl") or "").strip()
    opus = str(linha.get("valor_opus") or "").strip()
    if etl and opus and etl == opus:
        return etl
    return ""


def _renderizar_lista(
    df_grupos: pd.DataFrame,
    arquivo_selecionado: str | None,
) -> None:
    """Renderiza a coluna 1: lista de arquivos com badge + status pill."""
    st.markdown(
        f"<div style='font-size:13px; color:{CORES['texto_sec']}; "
        f"text-transform:uppercase; letter-spacing:0.05em; "
        f"margin-bottom:0.4rem;'>Arquivos ({len(df_grupos)})</div>",
        unsafe_allow_html=True,
    )

    if df_grupos.empty:
        st.markdown(
            callout_html("info", "Sem arquivos catalogados ainda."),
            unsafe_allow_html=True,
        )
        return

    for _, grupo in df_grupos.iterrows():
        caminho = str(grupo["caminho_relativo"])
        nome = Path(caminho).name
        badge = _badge_formato(caminho)
        tipo_sem = str(grupo["tipo_arquivo"]) or "—"
        status = str(grupo["status_global"])
        cor_status = _COR_STATUS.get(status, CORES["texto_muted"])

        ativo = arquivo_selecionado == caminho
        cor_borda = CORES["destaque"] if ativo else CORES["texto_muted"]
        cor_fundo = CORES["card_elevado"] if ativo else CORES["card_fundo"]

        html = minificar(
            f"""
            <div class='extracao-item' style='
                border:1px solid {cor_borda};
                background:{cor_fundo};
                border-radius:6px;
                padding:0.5rem 0.6rem;
                margin-bottom:0.45rem;
                font-size:13px;
            '>
                <div style='display:flex; gap:0.4rem; align-items:center;
                    margin-bottom:0.2rem;'>
                    <span style='
                        background:{CORES["fundo_inset"]};
                        color:{CORES["destaque"]};
                        font-size:11px;
                        font-weight:600;
                        padding:0.1rem 0.4rem;
                        border-radius:3px;
                        letter-spacing:0.04em;
                    '>{badge}</span>
                    <span style='color:{CORES["texto"]};
                        overflow:hidden;
                        text-overflow:ellipsis;
                        white-space:nowrap;
                        flex:1;
                    ' title='{nome}'>{nome}</span>
                </div>
                <div style='display:flex; justify-content:space-between;
                    align-items:center; gap:0.3rem;'>
                    <span style='color:{CORES["texto_muted"]};
                        font-size:11px;
                    '>{tipo_sem}</span>
                    <span class='pill-status' style='
                        background:{cor_status}22;
                        color:{cor_status};
                        font-size:11px;
                        padding:0.05rem 0.45rem;
                        border-radius:10px;
                        border:1px solid {cor_status}66;
                    '>{status}</span>
                </div>
            </div>
            """
        )
        st.markdown(html, unsafe_allow_html=True)

        # Botão minimal para selecionar (Streamlit não suporta click em <div>)
        if st.button(
            f"Abrir {nome[:22]}",
            key=f"sel_{grupo['sha8_arquivo']}",
            use_container_width=True,
        ):
            st.session_state[CHAVE_SESSION_ARQUIVO_SELECIONADO] = caminho
            st.rerun()


def _renderizar_viewer(arquivo_selecionado: str | None, raiz_repo: Path) -> None:
    """Renderiza a coluna 2: viewer do arquivo selecionado."""
    st.markdown(
        f"<div style='font-size:13px; color:{CORES['texto_sec']}; "
        f"text-transform:uppercase; letter-spacing:0.05em; "
        f"margin-bottom:0.4rem;'>Visualização</div>",
        unsafe_allow_html=True,
    )

    if not arquivo_selecionado:
        st.markdown(
            callout_html(
                "info",
                "Selecione um arquivo na lista à esquerda para abrir o "
                "preview e a tabela tripla.",
            ),
            unsafe_allow_html=True,
        )
        return

    caminho_abs = raiz_repo / arquivo_selecionado
    if not caminho_abs.exists():
        st.markdown(
            callout_html(
                "warning",
                f"Arquivo não encontrado em disco: `{arquivo_selecionado}`",
            ),
            unsafe_allow_html=True,
        )
        return

    suf = caminho_abs.suffix.lower()

    # PDF / imagem -- delega ao componente canônico
    if _tipo_preview(caminho_abs) in {"pdf", "imagem"}:
        preview_documento(caminho_abs, altura=520)
        return

    # CSV
    if suf == ".csv":
        try:
            df_csv = pd.read_csv(caminho_abs, nrows=20)
            st.dataframe(df_csv, use_container_width=True, hide_index=True)
        except Exception as erro:
            st.markdown(
                callout_html("error", f"Erro lendo CSV: {erro}"),
                unsafe_allow_html=True,
            )
        return

    # XLSX -- primeira aba, 20 linhas
    if suf in {".xlsx", ".xls"}:
        try:
            df_x = pd.read_excel(caminho_abs, nrows=20)
            st.dataframe(df_x, use_container_width=True, hide_index=True)
        except Exception as erro:
            st.markdown(
                callout_html("error", f"Erro lendo XLSX: {erro}"),
                unsafe_allow_html=True,
            )
        return

    # HTML -- iframe sandboxed
    if suf in {".html", ".htm"}:
        try:
            from streamlit.components import v1 as components

            html = caminho_abs.read_text(encoding="utf-8", errors="ignore")
            components.html(html, height=520, scrolling=True)
        except Exception as erro:
            st.markdown(
                callout_html("error", f"Erro lendo HTML: {erro}"),
                unsafe_allow_html=True,
            )
        return

    # Fallback: download
    st.markdown(
        callout_html(
            "info",
            f"Preview não suportado para `{suf}`. Baixe para inspecionar.",
        ),
        unsafe_allow_html=True,
    )
    try:
        st.download_button(
            f"Baixar {caminho_abs.name}",
            data=caminho_abs.read_bytes(),
            file_name=caminho_abs.name,
        )
    except Exception:
        pass


def _renderizar_tabela_tripla(
    df_arquivo: pd.DataFrame,
    sha8: str,
    caminho_csv: Path,
) -> None:
    """Renderiza a coluna 3: tabela tripla ETL × Opus × Humano editável."""
    st.markdown(
        f"<div style='font-size:13px; color:{CORES['texto_sec']}; "
        f"text-transform:uppercase; letter-spacing:0.05em; "
        f"margin-bottom:0.4rem;'>Tabela ETL × Opus × Humano</div>",
        unsafe_allow_html=True,
    )

    if df_arquivo.empty:
        st.markdown(
            callout_html("info", "Sem campos extraídos para este arquivo."),
            unsafe_allow_html=True,
        )
        return

    # Mascarar PII em cada coluna de valor antes de exibir
    df = df_arquivo.copy()
    for coluna in ("valor_etl", "valor_opus", "valor_humano"):
        df[coluna] = df[coluna].astype(str).apply(_mascarar_pii)

    # Pré-popular valor_humano com consenso quando vazio
    pre_populados = 0
    for idx, linha in df.iterrows():
        if not str(linha.get("valor_humano") or "").strip():
            consenso = _consenso(linha)
            if consenso:
                df.at[idx, "valor_humano"] = consenso
                pre_populados += 1
    if pre_populados:
        st.caption(
            f"{pre_populados} campo(s) pré-populados com consenso ETL ∩ Opus."
        )

    # Detectar divergências e renderizar tabela visual + form de edição
    cabecalho = minificar(
        f"""
        <div class='tabela-tripla-header' style='
            display:grid;
            grid-template-columns: 1.2fr 1fr 1fr 1fr;
            gap:0.4rem;
            padding:0.4rem 0.5rem;
            background:{CORES["fundo_inset"]};
            border:1px solid {CORES["texto_muted"]};
            border-radius:6px 6px 0 0;
            font-size:11px;
            text-transform:uppercase;
            letter-spacing:0.05em;
            color:{CORES["texto_sec"]};
        '>
            <span>Campo</span><span>ETL</span><span>Opus</span><span>Humano</span>
        </div>
        """
    )
    st.markdown(cabecalho, unsafe_allow_html=True)

    valores_humanos: dict[str, str] = {}

    for _, linha in df.iterrows():
        campo = str(linha["campo"])
        etl = str(linha.get("valor_etl") or "")
        opus = str(linha.get("valor_opus") or "")
        humano_inicial = str(linha.get("valor_humano") or "")

        diverge = _detectar_divergencia(linha)
        cor_celula_etl = (
            CORES["alerta"] if diverge else CORES["texto"]
        )
        cor_celula_opus = (
            CORES["alerta"] if diverge else CORES["texto"]
        )
        # classe CSS dedicada (extracao-divergente) para teste por seletor
        classe_div = "extracao-divergente" if diverge else "extracao-consenso"

        col_a, col_b, col_c, col_d = st.columns([1.2, 1, 1, 1])
        with col_a:
            st.markdown(
                f"<div style='padding:0.4rem 0.2rem; "
                f"font-size:13px; color:{CORES['texto']};'>"
                f"<code>{campo}</code></div>",
                unsafe_allow_html=True,
            )
        with col_b:
            st.markdown(
                minificar(
                    f"""
                    <div class='{classe_div}' style='
                        padding:0.4rem 0.5rem;
                        background:{cor_celula_etl}11;
                        border:1px solid {cor_celula_etl}44;
                        border-radius:4px;
                        font-size:13px;
                        color:{cor_celula_etl};
                        word-break:break-word;
                    '>{etl or "—"}</div>
                    """
                ),
                unsafe_allow_html=True,
            )
        with col_c:
            st.markdown(
                minificar(
                    f"""
                    <div class='{classe_div}' style='
                        padding:0.4rem 0.5rem;
                        background:{cor_celula_opus}11;
                        border:1px solid {cor_celula_opus}44;
                        border-radius:4px;
                        font-size:13px;
                        color:{cor_celula_opus};
                        word-break:break-word;
                    '>{opus or "—"}</div>
                    """
                ),
                unsafe_allow_html=True,
            )
        with col_d:
            valores_humanos[campo] = st.text_input(
                f"valor_humano_{campo}",
                value=humano_inicial,
                key=f"vh_{sha8}_{campo}",
                label_visibility="collapsed",
            )

    st.markdown("<div style='margin-top:0.6rem;'></div>", unsafe_allow_html=True)

    if st.button("Validar arquivo", type="primary", key=f"validar_{sha8}"):
        atualizadas = 0
        for _, linha in df_arquivo.iterrows():
            campo = str(linha["campo"])
            valor_humano = str(valores_humanos.get(campo, "")).strip()
            if not valor_humano:
                # mantém pendente quando humano deixou vazio
                continue
            ok = vc.atualizar_validacao_humana(
                sha8=sha8,
                campo=campo,
                valor_humano=valor_humano,
                status_humano="ok",
                observacoes="validado via Extração Tripla",
                caminho_csv=caminho_csv,
            )
            if ok:
                atualizadas += 1
        st.success(
            f"{atualizadas} campo(s) marcado(s) como aprovado(s) por humano."
        )


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Entry point da aba Extração Tripla."""
    del dados, mes_selecionado, pessoa, ctx  # aba opera sobre CSV próprio

    st.markdown(
        hero_titulo_html(
            "",
            "Extração Tripla",
            "Lista de arquivos · viewer · tabela ETL × Opus × Humano. "
            "Divergências em laranja; consenso pré-popula a coluna humana.",
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

    df_grupos = _agrupar_por_arquivo(df)

    arquivo_selecionado = st.session_state.get(
        CHAVE_SESSION_ARQUIVO_SELECIONADO, None
    )
    if not arquivo_selecionado and not df_grupos.empty:
        arquivo_selecionado = str(df_grupos.iloc[0]["caminho_relativo"])
        st.session_state[CHAVE_SESSION_ARQUIVO_SELECIONADO] = arquivo_selecionado

    # Sumário em pills
    total_arq = len(df_grupos)
    total_campos = len(df)
    aprovados = int((df["status_humano"].astype(str) == "ok").sum())
    divergentes = int(
        sum(_detectar_divergencia(linha) for _, linha in df.iterrows())
    )

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Arquivos", total_arq)
    col_b.metric("Campos extraídos", total_campos)
    col_c.metric("Aprovados humano", aprovados)
    col_d.metric("Divergências ETL≠Opus", divergentes)

    # 3 colunas: lista | viewer | tabela
    col_lista, col_viewer, col_tabela = st.columns([1, 1.4, 1.6])

    with col_lista:
        _renderizar_lista(df_grupos, arquivo_selecionado)

    with col_viewer:
        _renderizar_viewer(arquivo_selecionado, raiz_repo)

    with col_tabela:
        if arquivo_selecionado:
            df_arquivo = df[df["caminho_relativo"] == arquivo_selecionado]
            sha8 = (
                str(df_arquivo["sha8_arquivo"].iloc[0])
                if not df_arquivo.empty
                else ""
            )
            _renderizar_tabela_tripla(df_arquivo, sha8, caminho_csv)
        else:
            st.markdown(
                callout_html("info", "Selecione um arquivo para ver os campos."),
                unsafe_allow_html=True,
            )


# "Três fontes independentes que concordam: aproximação da verdade."
#  -- princípio da triangulação
