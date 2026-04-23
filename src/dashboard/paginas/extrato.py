"""Página de extrato detalhado do dashboard financeiro."""

from functools import lru_cache
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from src.dashboard.componentes.drilldown import (
    filtros_ativos_do_session_state,
    limpar_filtro,
)
from src.dashboard.componentes.modal_transacao import mostrar_modal
from src.dashboard.dados import (
    filtrar_por_forma_pagamento,
    filtrar_por_periodo,
    filtrar_por_pessoa,
    filtro_forma_ativo,
)
from src.dashboard.tema import CORES, FONTE_CORPO

# Sprint 73: mapeamento dos filtros vindos de drill-down para colunas do DF.
_MAPA_FILTRO_COLUNA: dict[str, str] = {
    "mes": "mes_ref",
    "mes_ref": "mes_ref",
    "categoria": "categoria",
    "classificacao": "classificacao",
    "fornecedor": "local",  # fuzzy contains, case-insensitive
    "local": "local",
    "banco": "banco_origem",
    "banco_origem": "banco_origem",
    "forma": "forma_pagamento",
    "forma_pagamento": "forma_pagamento",
}


def _aplicar_drilldown(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    """Aplica filtros vindos de drill-down (Sprint 73). Retorna df filtrado
    e dict dos filtros efetivos aplicados (para breadcrumb)."""
    filtros = filtros_ativos_do_session_state()
    aplicados: dict[str, str] = {}
    for campo, valor in filtros.items():
        coluna = _MAPA_FILTRO_COLUNA.get(campo)
        if not coluna or coluna not in df.columns:
            continue
        if campo in ("fornecedor", "local"):
            mascara = df[coluna].fillna("").astype(str).str.contains(
                valor, case=False, na=False, regex=False
            )
            df = df[mascara]
        else:
            df = df[df[coluna].astype(str) == valor]
        aplicados[campo] = valor
    return df, aplicados


def _renderizar_breadcrumb(filtros: dict[str, str]) -> None:
    """Exibe breadcrumb com X para remover cada filtro ativo (Sprint 73)."""
    if not filtros:
        return
    import streamlit as st

    st.markdown(
        f'<p style="color: {CORES["destaque"]}; font-size: {FONTE_CORPO}px;">'
        "Filtros ativos (clique no X para remover):</p>",
        unsafe_allow_html=True,
    )
    cols = st.columns(len(filtros))
    for i, (campo, valor) in enumerate(filtros.items()):
        with cols[i]:
            rotulo = f"{campo}: {valor}   ×"
            if st.button(rotulo, key=f"limpar_filtro_{campo}"):
                limpar_filtro(campo)
                st.rerun()


_CAMINHO_CATEGORIAS_TRACKING: Path = (
    Path(__file__).resolve().parents[3] / "mappings" / "categorias_tracking.yaml"
)


@lru_cache(maxsize=1)
def _carregar_categorias_obrigatorias() -> frozenset[str]:
    """Lê `mappings/categorias_tracking.yaml` uma vez e cacheia em memória."""
    if not _CAMINHO_CATEGORIAS_TRACKING.exists():
        return frozenset()
    try:
        dados = yaml.safe_load(_CAMINHO_CATEGORIAS_TRACKING.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return frozenset()
    lista = (dados or {}).get("obrigatoria_tracking", []) or []
    return frozenset(str(c) for c in lista)


def _marcar_tracking(
    row: pd.Series,
    obrigatorias: frozenset[str],
    ids_com_doc: set[str],
) -> str:
    """Sprint 87.2 (ADR-20): devolve o marcador da coluna "Doc?" do Extrato.

    Prioridade:
      1. Transação com `identificador` em `ids_com_doc` (aresta `documento_de`
         no grafo) -> "OK".
      2. Transação em categoria obrigatória sem vínculo -> "!".
      3. Caso contrário -> "".

    Função pura para permitir teste sem mockar streamlit. `row` é uma `pd.Series`
    de uma linha do DataFrame do extrato (pode ou não ter coluna `identificador`).
    """
    ident = row.get("identificador") if hasattr(row, "get") else None
    if ident is not None and not pd.isna(ident):
        ident_str = str(ident)
        if ident_str and ident_str in ids_com_doc:
            return "OK"
    categoria = row.get("categoria", "") if hasattr(row, "get") else ""
    return "!" if categoria in obrigatorias else ""


@st.cache_data(ttl=30)
def _carregar_ids_com_doc() -> set[str]:
    """Sprint 87.2 (ADR-20): transações do grafo com documento vinculado.

    Consulta `src.graph.queries.transacoes_com_documento` uma vez por render
    (TTL 30s) e devolve o conjunto de `nome_canonico` de nodes `transacao`  # noqa: accent
    com ao menos uma aresta `documento_de`. Graceful degradation: se o grafo
    não existir ou houver erro de import, loga info e devolve set vazio —
    a coluna "Doc?" cai no comportamento antigo (apenas heurística de
    categoria obrigatória).
    """
    try:
        from src.graph.db import GrafoDB, caminho_padrao
        from src.graph.queries import transacoes_com_documento
    except ImportError:  # pragma: no cover -- módulo de grafo ausente no dev local
        return set()

    try:
        db_path = caminho_padrao()
        if not db_path.exists():
            return set()
        with GrafoDB(db_path) as db:
            return transacoes_com_documento(db)
    except Exception:  # noqa: BLE001 -- dashboard nunca deve quebrar por grafo ausente
        return set()


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página de extrato."""
    if "extrato" not in dados:
        st.warning("Nenhum dado encontrado para o extrato.")
        return

    gran = ctx.get("granularidade", "Mês") if ctx else "Mês"
    periodo = ctx.get("periodo", mes_selecionado) if ctx else mes_selecionado

    extrato = dados["extrato"]
    df = filtrar_por_periodo(extrato, gran, periodo)
    df = filtrar_por_pessoa(df, pessoa)
    df = filtrar_por_forma_pagamento(df, filtro_forma_ativo())
    # Sprint 73 (ADR-19): aplica filtros vindos de drill-down (URL / clique).
    df, filtros_drilldown = _aplicar_drilldown(df)
    _renderizar_breadcrumb(filtros_drilldown)

    if df.empty:
        st.info("Sem transações para o período selecionado.")
        return

    busca = st.text_input(
        "Buscar por local",
        key="busca_local",
        placeholder="Digite para filtrar...",
    )

    st.markdown(
        "<style>.stSelectbox { margin-bottom: 12px; }</style>",
        unsafe_allow_html=True,
    )

    # Sprint 77: keys prefixadas com `avancado_` evitam colisão com as
    # chaves `filtro_*` que o drilldown.ler_filtros_da_url() popula via
    # query_params (Sprint 73). Sem esse prefixo, selectbox e drill-down
    # disputavam o mesmo slot em session_state.
    with st.expander("Filtros avançados", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            categorias = ["Todas"] + sorted(df["categoria"].dropna().unique().tolist())
            categoria_sel = st.selectbox("Categoria", categorias, key="avancado_categoria")

            bancos = ["Todos"] + sorted(df["banco_origem"].dropna().unique().tolist())
            banco_sel = st.selectbox("Banco", bancos, key="avancado_banco")

        with col2:
            classificacoes = ["Todas"] + sorted(df["classificacao"].dropna().unique().tolist())
            classificacao_sel = st.selectbox(
                "Classificação",
                classificacoes,
                key="avancado_classificacao",
            )

            tipos = ["Todos"] + sorted(df["tipo"].dropna().unique().tolist())
            tipo_sel = st.selectbox("Tipo", tipos, key="avancado_tipo")

    resultado = df.copy()

    if busca.strip():
        mascara = resultado["local"].fillna("").str.contains(busca.strip(), case=False, na=False)
        resultado = resultado[mascara]

    if categoria_sel != "Todas":
        resultado = resultado[resultado["categoria"] == categoria_sel]

    if classificacao_sel != "Todas":
        resultado = resultado[resultado["classificacao"] == classificacao_sel]

    if banco_sel != "Todos":
        resultado = resultado[resultado["banco_origem"] == banco_sel]

    if tipo_sel != "Todos":
        resultado = resultado[resultado["tipo"] == tipo_sel]

    _exibir_tabela(resultado)
    _inspecionar_transacao(resultado)


def _exibir_tabela(df: pd.DataFrame) -> None:
    """Exibe tabela interativa de transações e botão de export."""
    st.markdown(
        f'<p style="color: {CORES["destaque"]};'
        f" font-size: {FONTE_CORPO}px;"
        f' font-weight: bold; margin: 10px 0;">'
        f"{len(df)} transações encontradas</p>",
        unsafe_allow_html=True,
    )

    colunas_exibicao: list[str] = [
        "data",
        "valor",
        "local",
        "categoria",
        "classificacao",
        "banco_origem",
        "tipo",
        "quem",
    ]

    colunas_presentes = [c for c in colunas_exibicao if c in df.columns]
    df_exibir = df[colunas_presentes].copy()

    # Sprint 74 (ADR-20) + Sprint 87.2: coluna de tracking documental.
    # Se a transação tem aresta `documento_de` no grafo -> "OK".
    # Se a categoria é obrigatória e ainda não há vínculo -> "!".
    # Senão -> vazio. Graceful degradation: quando o grafo não existe ou a
    # coluna `identificador` não chegou ao df, o resultado cai no fallback
    # histórico (apenas heurística de categoria).
    obrigatorias = _carregar_categorias_obrigatorias()
    if obrigatorias and "categoria" in df.columns:
        ids_com_doc = _carregar_ids_com_doc()
        df_exibir["tracking"] = df.apply(
            lambda row: _marcar_tracking(row, obrigatorias, ids_com_doc),
            axis=1,
        ).values

    nomes_colunas: dict[str, str] = {
        "data": "Data",
        "valor": "Valor",
        "local": "Local",
        "categoria": "Categoria",
        "classificacao": "Classificação",
        "banco_origem": "Banco",
        "tipo": "Tipo",
        "quem": "Quem",
        "tracking": "Doc?",
    }

    if "data" in df_exibir.columns:
        datas = pd.to_datetime(df_exibir["data"], errors="coerce")
        df_exibir["data"] = datas.dt.strftime("%Y-%m-%d")

    df_exibir = df_exibir.rename(columns=nomes_colunas)

    st.dataframe(
        df_exibir,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        },
    )

    csv = "\ufeff" + df_exibir.to_csv(index=False, sep=";", decimal=",")
    st.download_button(
        label="Exportar CSV",
        data=csv,
        file_name="extrato.csv",
        mime="text/csv",
    )


def _inspecionar_transacao(df: pd.DataFrame) -> None:
    """Sprint 74 — Modal detalhado de uma transação com preview de docs vinculados.

    Streamlit não suporta clique nativo em linha do `st.dataframe`; usamos um
    selectbox + botão como compromisso. O modal exibe metadados, estado
    documental e preview inline dos documentos (Sprint 74, ADR-20).
    """
    if df.empty:
        return

    st.markdown("---")
    st.markdown(
        f'<p style="color: {CORES["destaque"]}; font-size: {FONTE_CORPO}px; '
        f'font-weight: bold; margin: 10px 0;">Inspecionar transação</p>',
        unsafe_allow_html=True,
    )

    rotulos: list[str] = []
    for _, row in df.head(500).iterrows():
        data_v = row.get("data")
        data_str = (
            pd.to_datetime(data_v).strftime("%Y-%m-%d")
            if data_v is not None and not pd.isna(data_v)
            else "-"
        )
        valor = float(row.get("valor") or 0.0)
        local = str(row.get("local", ""))[:40]
        rotulos.append(f"{data_str} — R$ {valor:.2f} — {local}")

    col_sel, col_btn = st.columns([4, 1])
    with col_sel:
        idx = st.selectbox(
            "Escolha uma transação (até 500 primeiras)",
            options=list(range(len(rotulos))),
            format_func=lambda i: rotulos[i] if i < len(rotulos) else "",
            key="extrato_tx_inspecionar",
        )
    with col_btn:
        st.write("")  # padding vertical
        clicou = st.button("Ver detalhes", key="extrato_btn_modal", type="primary")

    if clicou and idx is not None and idx < len(df):
        row = df.iloc[idx]
        tx = {
            "data": pd.to_datetime(row.get("data"))
            if row.get("data") is not None
            else None,
            "valor": float(row.get("valor") or 0.0),
            "categoria": row.get("categoria", "-"),
            "banco_origem": row.get("banco_origem", "-"),
            "local": row.get("local", "-"),
            "quem": row.get("quem", "-"),
        }
        mostrar_modal(tx, [])


# "O dinheiro é um bom servo, mas um mau mestre." -- Francis Bacon
