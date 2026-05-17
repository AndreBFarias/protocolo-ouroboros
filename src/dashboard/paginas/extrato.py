"""Página de extrato detalhado (UX-RD-06: tabela densa + breakdown + drawer).

Reescrita da página Extrato seguindo o mockup ``novo-mockup/mockups/02-extrato.html``:

* **Saldo no topo**: card grande mono 32px tabular-nums + 3 mini-KPIs do
  período (Receita, Despesa, Transações count).
* **Tabela densa** (.table do tema_css.py UX-RD-02): row-h 32px, sticky
  thead, mono em valor/data, alinhamento tabular nos valores, hover/selected.
* **Breakdown lateral por categoria**: top 5 categorias em barras
  proporcionais (1fr direita contra 2.5fr da tabela).
* **Drawer JSON syntax-highlighted**: clicar uma linha (via selectbox +
  botão "Abrir drawer") mostra o JSON da transação no painel lateral
  com cores --syn-key/string/number/bool/null.

Lições aplicadas
----------------
* UX-RD-04: HTML grande (tabela com N linhas, breakdown, drawer) emitido
  via ``minificar()`` para evitar que o parser CommonMark interprete a
  indentação Python como bloco ``<pre><code>``.
* Sprint 73 (drill-down) preservada: ``_aplicar_drilldown`` + breadcrumb.
* Sprint 87.2 (tracking documental): coluna ``Doc?`` continua funcionando
  via ``_marcar_tracking`` + grafo SQLite.
* Sprint 92a.8 (paginação 25 linhas): mantida.
* Filtros (``filtrar_por_periodo``, ``filtrar_por_pessoa``,
  ``filtrar_por_forma_pagamento``) e exportação CSV: preservados.

Decisão drawer (Streamlit não tem drawer nativo)
------------------------------------------------
Optamos por HTML absolute-positioned via ``st.markdown(..., unsafe_allow_html=True)``
controlado por ``st.session_state["extrato_drawer_idx"]``. O drawer é
renderizado depois da tabela (no DOM) mas vai para a direita via
``position: fixed`` do CSS de UX-RD-02. Botão "Fechar" emite ``st.button``
que limpa o estado e dá rerun. Trade-off: drawer ocupa espaço da tabela em
viewport estreito; em widescreen fica ao lado, espelhando o mockup.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import yaml

from src.dashboard.componentes.drawer_transacao import (
    renderizar_drawer,
    transacao_para_dict,
)
from src.dashboard.componentes.drilldown import (
    filtros_ativos_do_session_state,
    limpar_filtro,
)
from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.painel_drill_down import (
    persistir_revisao,
    renderizar_painel_drill_down,
)
from src.dashboard.componentes.ui import (
    callout_html,
    carregar_css_pagina,
)
from src.dashboard.dados import (
    filtrar_por_forma_pagamento,
    filtrar_por_periodo,
    filtrar_por_pessoa,
    filtro_forma_ativo,
)
from src.dashboard.tema import (
    CORES,
    FONTE_CORPO,
    breadcrumb_drilldown_html,
    icon_html,
)

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


_CAMINHO_CATEGORIAS_TRACKING: Path = (
    Path(__file__).resolve().parents[3] / "mappings" / "categorias_tracking.yaml"
)

TAMANHO_PAGINA_EXTRATO: int = 25
"""Sprint 92a.8: número de linhas por página na tabela do Extrato."""

_CHAVE_DRAWER_IDX = "extrato_drawer_idx"


# ---------------------------------------------------------------------------
# Helpers (drilldown, tracking documental)
# ---------------------------------------------------------------------------


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
            mascara = (
                df[coluna]
                .fillna("")
                .astype(str)
                .str.contains(valor, case=False, na=False, regex=False)
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
    st.markdown(
        breadcrumb_drilldown_html(filtros),
        unsafe_allow_html=True,
    )
    cols = st.columns(len(filtros))
    for i, (campo, _valor) in enumerate(filtros.items()):
        with cols[i]:
            if st.button(
                f"× remover {campo}",
                key=f"limpar_filtro_{campo}",
                use_container_width=True,
            ):
                limpar_filtro(campo)
                st.rerun()


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
    """Sprint 87.2 (ADR-20): devolve o marcador da coluna "Doc?" do Extrato."""
    ident = row.get("identificador") if hasattr(row, "get") else None
    if ident is not None and not pd.isna(ident):
        ident_str = str(ident)
        if ident_str and ident_str in ids_com_doc:
            return "Doc ok"
    categoria = row.get("categoria", "") if hasattr(row, "get") else ""
    return "Faltando" if categoria in obrigatorias else ""


@st.cache_data(ttl=30)
def _carregar_ids_com_doc() -> set[str]:
    """Sprint 87.2 (ADR-20): transações do grafo com documento vinculado."""
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


# ---------------------------------------------------------------------------
# Cálculos (saldo topo, breakdown lateral)
# ---------------------------------------------------------------------------


def calcular_saldo_topo(df: pd.DataFrame) -> dict[str, float]:
    """Calcula saldo, receita, despesa, investido e count para o card de topo.

    Convenção: ``valor`` negativo é despesa, positivo é receita. ``tipo``
    "Transferência Interna" é excluído de ambos para não inflar nem somas
    nem perdas. UX-T-02: campo ``investido`` adicionado (despesas com
    categoria que contém "Investimento", case-insensitive).
    """
    if df.empty:
        return {
            "saldo": 0.0,
            "receita": 0.0,
            "despesa": 0.0,
            "investido": 0.0,
            "transacoes": 0,
        }

    if "tipo" in df.columns:
        operacional = df[df["tipo"].astype(str) != "Transferência Interna"]
    else:
        operacional = df

    # FIX-02: filtrar por coluna canônica `tipo` (enum estrito do schema)
    # em vez de signal `valor < 0`. XLSX armazena valores positivos; o tipo
    # (Receita/Despesa/Transferência Interna/Imposto) é o sinalizador.
    # Robusto a ambos os formatos: XLSX real (positivos) ou mock (negativos).
    valores = pd.to_numeric(operacional.get("valor"), errors="coerce").fillna(0.0)
    if "tipo" in operacional.columns:
        receita = float(valores[operacional["tipo"] == "Receita"].sum())
        despesa_raw = float(valores[operacional["tipo"] == "Despesa"].sum())
    else:
        # fallback (df sem coluna tipo): heurística antiga por signal
        receita = float(valores[valores > 0].sum())
        despesa_raw = float(valores[valores < 0].sum())  # negativo
    # Saldo = receita - magnitude(despesa); funciona com ambos os sinais.
    saldo = receita - abs(despesa_raw)
    # UX-T-02: investido = despesas categorizadas como "Investimento".
    investido = 0.0
    if "categoria" in operacional.columns and "tipo" in operacional.columns:
        cat_str = operacional["categoria"].astype(str).str.lower()
        eh_investimento = cat_str.str.contains("investimento", na=False)
        eh_despesa = operacional["tipo"] == "Despesa"
        investido = abs(float(valores[eh_despesa & eh_investimento].sum()))
    return {
        "saldo": saldo,
        "receita": receita,
        "despesa": despesa_raw,
        "investido": investido,
        "transacoes": int(len(df)),
    }


def calcular_breakdown_categorias(df: pd.DataFrame, top_n: int = 5) -> list[dict[str, Any]]:
    """Top-N categorias por valor absoluto de despesa.

    Retorna lista ordenada decrescente de dicts ``{categoria, valor, pct}``
    onde ``valor`` é o total absoluto de despesas (positivo) e ``pct`` é
    a proporção (0..100) sobre o total.
    """
    if df.empty or "categoria" not in df.columns:
        return []

    if "tipo" in df.columns:
        operacional = df[df["tipo"].astype(str) != "Transferência Interna"]
    else:
        operacional = df

    # FIX-02: filtrar por tipo == "Despesa" (canônico do schema XLSX) em vez
    # de valor < 0 (XLSX armazena valores positivos; tipo é o sinalizador).
    # O filtro antigo retornava conjunto vazio porque valores são sempre
    # positivos -> bug "Despesa R$ 0,00" mesmo com 4760 despesas no XLSX.
    apenas_despesas = operacional[operacional["tipo"] == "Despesa"].copy()
    apenas_despesas["__abs"] = (
        pd.to_numeric(apenas_despesas["valor"], errors="coerce").fillna(0.0).abs()
    )

    if apenas_despesas.empty:
        return []

    agrupado = (
        apenas_despesas.groupby("categoria", dropna=False)["__abs"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
    )
    total = float(agrupado.sum())
    if total <= 0:
        return []

    resultado: list[dict[str, Any]] = []
    for categoria, valor in agrupado.items():
        cat = str(categoria) if not pd.isna(categoria) else "Sem categoria"
        resultado.append(
            {
                "categoria": cat,
                "valor": float(valor),
                "pct": float(valor) / total * 100.0,
            }
        )
    return resultado


# ---------------------------------------------------------------------------
# HTML builders
# ---------------------------------------------------------------------------


def _formatar_brl(valor: float) -> str:
    sinal = "-" if valor < 0 else ""
    return f"{sinal}R$ {abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------------------
# UX-V-3.1: filt-bar canônica + lista por dia com pílulas tipadas
# ---------------------------------------------------------------------------


# Mapa banco_origem -> pílula 2 letras. Inclui variações sem acento e
# substrings comuns. Fallback: primeiras 2 letras do banco em maiúsculas.
_PILULA_BANCO_MAP: dict[str, str] = {
    "nubank": "NB",
    "nu": "NB",
    "itau": "IT",
    "itaú": "IT",
    "inter": "IN",
    "c6": "C6",
    "bradesco": "BR",
    "santander": "ST",
    "caixa": "CX",
    "bb": "BB",
    "banco do brasil": "BB",
}


def _pilula_tipo(banco_origem: str | None, forma_pagamento: str | None) -> str:
    """Inferência simples para a pílula tipo (2 letras) da lista por dia.

    Regra:
    1. Se forma_pagamento contém "pix" (case-insensitive) -> "PX".
    2. Se banco_origem casa um prefixo conhecido -> sigla canônica.
    3. Fallback: primeiras 2 letras do banco em maiúsculas, ou "??".
    """
    forma_str = str(forma_pagamento or "").lower()
    if "pix" in forma_str:
        return "PX"
    banco_str = str(banco_origem or "").strip().lower()
    if not banco_str:
        return "??"
    for chave, sigla in _PILULA_BANCO_MAP.items():
        if banco_str.startswith(chave) or chave in banco_str:
            return sigla
    # Fallback: 2 primeiras letras alfabéticas do nome do banco
    letras = "".join(c for c in banco_str if c.isalpha())[:2]
    return letras.upper() or "??"


def _filt_bar_canonica(
    df: pd.DataFrame,
    contas_disponiveis: list[str],
    categorias_disponiveis: list[str],
) -> dict[str, Any]:
    """Renderiza a filt-bar canônica acima da lista por dia.

    Usa st.columns + st.selectbox + st.checkbox; o "look" canônico vem do CSS
    (.t02-filt-bar) aplicado ao container HTML que envolve o counter ao final.

    Retorna dicionário com chaves:
      - conta: str (rótulo "todas (N)" ou nome do banco)
      - categoria: str ("todas" ou nome da categoria)
      - busca: str (texto livre)
      - so_saidas: bool
      - com_sidecar: bool
      - nao_categorizadas: bool
    """
    n_contas = len(contas_disponiveis)
    contas_opcoes = [f"todas ({n_contas})"] + contas_disponiveis
    categorias_opcoes = ["todas"] + categorias_disponiveis

    col_c, col_cat, col_per, col_busca = st.columns([1, 1, 1, 1.5])
    with col_c:
        conta_sel = st.selectbox(
            "Conta",
            contas_opcoes,
            key="t02_filt_conta",
        )
    with col_cat:
        categoria_sel = st.selectbox(
            "Categoria",
            categorias_opcoes,
            key="t02_filt_categoria",
        )
    with col_per:
        # Período é informativo aqui (a sprint usa o ctx global do dashboard);
        # exibido para casar com o mockup. Não filtra por enquanto.
        st.selectbox(
            "Período",
            ["período do dashboard"],
            key="t02_filt_periodo",
            disabled=True,
        )
    with col_busca:
        busca_local = st.text_input(
            "Busca",
            key="t02_filt_busca",
            placeholder="descrição, sha8, valor",
        )

    col_chip1, col_chip2, col_chip3, col_count = st.columns([1, 1, 1, 2])
    with col_chip1:
        so_saidas = st.checkbox("só saídas", key="t02_chip_saidas")
    with col_chip2:
        com_sidecar = st.checkbox("com sidecar", key="t02_chip_sidecar")
    with col_chip3:
        nao_categorizadas = st.checkbox(
            "não categorizadas",
            key="t02_chip_naocat",
        )
    with col_count:
        n_total = int(len(df))
        st.markdown(
            f'<span class="t02-filt-counter">{n_total} transações</span>',
            unsafe_allow_html=True,
        )

    return {
        "conta": conta_sel,
        "categoria": categoria_sel,
        "busca": busca_local,
        "so_saidas": so_saidas,
        "com_sidecar": com_sidecar,
        "nao_categorizadas": nao_categorizadas,
    }


def _aplicar_filt_bar(df: pd.DataFrame, filtros: dict[str, Any]) -> pd.DataFrame:
    """Aplica filtros vindos da filt-bar canônica."""
    if df.empty:
        return df
    resultado = df

    conta = str(filtros.get("conta", ""))
    if conta and not conta.startswith("todas") and "banco_origem" in resultado.columns:
        resultado = resultado[resultado["banco_origem"].astype(str) == conta]

    categoria = str(filtros.get("categoria", ""))
    if categoria and categoria != "todas" and "categoria" in resultado.columns:
        resultado = resultado[resultado["categoria"].astype(str) == categoria]

    busca = str(filtros.get("busca", "")).strip()
    if busca and "local" in resultado.columns:
        mascara = (
            resultado["local"]
            .fillna("")
            .astype(str)
            .str.contains(
                busca,
                case=False,
                na=False,
                regex=False,
            )
        )
        resultado = resultado[mascara]

    if filtros.get("so_saidas") and "tipo" in resultado.columns:
        resultado = resultado[resultado["tipo"].astype(str) == "Despesa"]

    if filtros.get("com_sidecar") and "__tracking" in resultado.columns:
        resultado = resultado[resultado["__tracking"].astype(str) == "Doc ok"]

    if filtros.get("nao_categorizadas") and "categoria" in resultado.columns:
        cat_str = resultado["categoria"].fillna("").astype(str).str.strip()
        resultado = resultado[(cat_str == "") | (cat_str.str.lower() == "sem categoria")]

    return resultado


_DIAS_SEMANA_ABREV = {
    0: "SEG",
    1: "TER",
    2: "QUA",
    3: "QUI",
    4: "SEX",
    5: "SAB",
    6: "DOM",
}


def _lista_por_dia_html(df: pd.DataFrame, limite: int = 50) -> str:
    """Renderiza lista agrupada por dia (DESC) com pílulas tipadas.

    Limita a ``limite`` linhas para evitar HTML gigante (Não-objetivo da
    sprint: paginação completa fica para depois).
    """
    if df.empty or "data" not in df.columns:
        return minificar('<div class="t02-lista-vazia">Sem transações para exibir.</div>')

    df_local = df.copy()
    df_local["__data_dt"] = pd.to_datetime(df_local["data"], errors="coerce")
    df_local = df_local.dropna(subset=["__data_dt"])
    if df_local.empty:
        return minificar('<div class="t02-lista-vazia">Sem transações para exibir.</div>')

    # Ordena DESC por data e limita.
    df_local = df_local.sort_values("__data_dt", ascending=False).head(limite)

    # Agrupa por data (sem hora). Mantém a ordem DESC já estabelecida.
    df_local["__data_key"] = df_local["__data_dt"].dt.date

    grupos_html: list[str] = []
    # Itera grupos respeitando a ordem DESC.
    chaves_vistas: list[Any] = []
    for chave in df_local["__data_key"]:
        if chave not in chaves_vistas:
            chaves_vistas.append(chave)

    for chave in chaves_vistas:
        bloco = df_local[df_local["__data_key"] == chave]
        # Total do dia: receitas positivas, despesas negativas.
        if "tipo" in bloco.columns:
            valores_signed = bloco.apply(
                lambda r: (
                    float(pd.to_numeric(r.get("valor"), errors="coerce") or 0.0)
                    if str(r.get("tipo", "")) == "Receita"
                    else -abs(float(pd.to_numeric(r.get("valor"), errors="coerce") or 0.0))
                ),
                axis=1,
            )
        else:
            valores_signed = pd.to_numeric(bloco["valor"], errors="coerce").fillna(0.0)
        total_dia = float(valores_signed.sum())

        data_str = chave.strftime("%Y-%m-%d")
        dia_semana = _DIAS_SEMANA_ABREV.get(chave.weekday(), "")
        cor_total = "var(--d7-graduado)" if total_dia >= 0 else "var(--accent-red)"
        sinal_total = "+" if total_dia >= 0 else "-"
        total_str = _formatar_brl(abs(total_dia))

        head_html = (
            '<div class="t02-day-head">'
            f'<span class="when">{data_str} · {dia_semana}</span>'
            f'<span class="total" style="color:{cor_total};">'
            f"{sinal_total} {total_str}</span>"
            "</div>"
        )

        linhas: list[str] = []
        for _, row in bloco.iterrows():
            banco = row.get("banco_origem") if hasattr(row, "get") else None
            forma = row.get("forma_pagamento") if hasattr(row, "get") else None
            sigla = _pilula_tipo(banco, forma)

            descricao = str(row.get("local") or "-")
            if len(descricao) > 56:
                descricao = descricao[:53] + "..."

            categoria = str(row.get("categoria") or "—")
            conta_str = str(banco or "—")
            forma_str = str(forma or "—")

            ident = row.get("identificador") if hasattr(row, "get") else None
            sha8 = ""
            if ident is not None and not pd.isna(ident):
                sha8 = str(ident)[:8]

            if row.name in valores_signed.index:
                valor_signed = float(valores_signed.loc[row.name])
            else:
                valor_signed = 0.0
            cor_val_class = "neg" if valor_signed < 0 else "pos"
            sinal_val = "+" if valor_signed >= 0 else "-"
            valor_str = _formatar_brl(abs(valor_signed))

            meta_html = (
                f'<span class="meta">{_escape(forma_str)}'
                + (f' · sha8 <span class="sha">{sha8}</span>' if sha8 else "")
                + "</span>"
            )

            linha = (
                '<div class="t02-txn">'
                f'<div class="ic {sigla}">{sigla}</div>'
                f'<div class="desc"><strong>{_escape(descricao)}</strong>'
                f"{meta_html}</div>"
                f'<div><span class="cat">{_escape(categoria)}</span></div>'
                f'<div class="conta">{_escape(conta_str)}</div>'
                f'<div class="val {cor_val_class}">'
                f"{sinal_val} {valor_str}</div>"
                "</div>"
            )
            linhas.append(linha)

        grupo = '<div class="t02-day-group">' + head_html + "".join(linhas) + "</div>"
        grupos_html.append(grupo)

    return minificar("".join(grupos_html))


# ---------------------------------------------------------------------------
# Saldo topo (existente)
# ---------------------------------------------------------------------------


def _saldo_topo_html(metricas: dict[str, float], periodo_rotulo: str) -> str:
    """UX-T-02: 4 KPIs canônicos do mockup ``02-extrato.html``.

    Saldo Consolidado · Entrada · 30d · Saída · 30d · Investido · 30d
    (labels canônicos do mockup). Mantém sufixo ``periodo_rotulo`` para
    contextualizar a janela ativa quando o usuário muda o filtro.
    """
    saldo = metricas["saldo"]
    receita = metricas["receita"]
    despesa = metricas["despesa"]
    n = int(metricas["transacoes"])

    investido = float(metricas.get("investido", 0.0))
    pct_investido = (investido / receita * 100.0) if receita > 0 else 0.0

    return minificar(
        f"""
        <div class="t02-kpi-row">
            <div class="t02-kpi">
                <div class="l">Saldo consolidado</div>
                <div class="v">{_formatar_brl(saldo)}</div>
                <div class="d">{n} transações · {periodo_rotulo}</div>
            </div>
            <div class="t02-kpi">
                <div class="l">Entrada · 30d</div>
                <div class="v" style="color:var(--d7-graduado);">
                    {_formatar_brl(receita)}
                </div>
                <div class="d">PJ + salário + dividendos</div>
            </div>
            <div class="t02-kpi">
                <div class="l">Saída · 30d</div>
                <div class="v" style="color:var(--accent-red);">
                    {_formatar_brl(abs(despesa))}
                </div>
                <div class="d">{n} txns no período</div>
            </div>
            <div class="t02-kpi">
                <div class="l">Investido · 30d</div>
                <div class="v" style="color:var(--accent-purple);">
                    {_formatar_brl(investido)}
                </div>
                <div class="d">{pct_investido:.0f}% da receita</div>
            </div>
        </div>
        """
    )


def _tabela_densa_html(df: pd.DataFrame, idx_drawer: int | None = None) -> str:
    """Emite ``<table class="table">`` com as linhas do DF.

    Cada linha é gerada como uma única string concatenada (sem indentação
    interna) e o conjunto é minificado antes do retorno. Isso evita que o
    parser CommonMark veja indentação ≥ 4 e renderize ``<pre><code>``.
    """
    if df.empty:
        return minificar(
            """
            <p class="extrato-vazio">Sem transações para exibir nesta página.</p>
            """
        )

    # Formatação leve de cada coluna.
    linhas: list[str] = []
    for ord_idx, (_real_idx, row) in enumerate(df.iterrows()):
        data_v = row.get("data")
        if data_v is None or pd.isna(data_v):
            data_str = "-"
        else:
            data_str = pd.to_datetime(data_v).strftime("%Y-%m-%d")

        valor = float(pd.to_numeric(row.get("valor"), errors="coerce") or 0.0)
        cor_val = CORES["negativo"] if valor < 0 else CORES["positivo"]
        valor_str = _formatar_brl(valor)

        descricao = str(row.get("local") or "-")
        if len(descricao) > 48:
            descricao = descricao[:45] + "..."

        categoria = str(row.get("categoria") or "-")
        forma = str(row.get("forma_pagamento") or "-")
        quem = str(row.get("quem") or "-")

        # Marcador "Doc?" — vem de _marcar_tracking se a coluna existir
        tracking = str(row.get("__tracking", "") or "")
        if tracking == "Doc ok":
            doc_cell = '<span class="extrato-doc-ok" title="Documento vinculado no grafo">+</span>'
        elif tracking == "Faltando":
            doc_cell = (
                '<span class="extrato-doc-faltando" '
                'title="Categoria obrigatória sem comprovante">!</span>'
            )
        else:
            doc_cell = '<span class="extrato-doc-vazio">·</span>'

        classe_linha = "selected" if (idx_drawer is not None and idx_drawer == ord_idx) else ""

        linha = (
            f'<tr class="{classe_linha}">'
            f'<td class="col-mono">{data_str}</td>'
            f'<td class="col-desc">{_escape(descricao)}</td>'
            f'<td><span class="extrato-pill-cat">{_escape(categoria)}</span></td>'
            f'<td class="col-num" style="color:{cor_val};">{valor_str}</td>'
            f'<td class="col-mono">{_escape(forma)}</td>'
            f'<td><span class="extrato-pill-pessoa">{_escape(quem)}</span></td>'
            f'<td class="col-doc">{doc_cell}</td>'
            f"</tr>"
        )
        linhas.append(linha)

    cabecalho = (
        "<thead><tr>"
        "<th>Data</th>"
        "<th>Descrição</th>"
        "<th>Categoria</th>"
        '<th class="col-num">Valor</th>'
        "<th>Forma</th>"
        "<th>Pessoa</th>"
        "<th>Doc?</th>"
        "</tr></thead>"
    )
    corpo = "<tbody>" + "".join(linhas) + "</tbody>"
    return minificar(
        f'<div class="extrato-tabela-wrap"><table class="table">{cabecalho}{corpo}</table></div>'
    )


def _escape(texto: str) -> str:
    """Escape mínimo para evitar quebra de tags via < ou > em descrição."""
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _breakdown_lateral_html(top_categorias: list[dict[str, Any]]) -> str:
    """Card lateral com top-N categorias em barras horizontais."""
    if not top_categorias:
        return minificar(
            """
            <div class="extrato-breakdown">
                <span class="extrato-breakdown-titulo">BREAKDOWN POR CATEGORIA</span>
                <p class="extrato-breakdown-vazio">Sem despesas no período.</p>
            </div>
            """
        )

    # Paleta cíclica reusando tokens existentes.
    paleta = [
        "var(--accent-purple)",
        "var(--accent-pink)",
        "var(--accent-cyan)",
        "var(--accent-green)",
        "var(--accent-yellow)",
    ]

    barras: list[str] = []
    for i, item in enumerate(top_categorias):
        cor = paleta[i % len(paleta)]
        nome = _escape(item["categoria"])
        valor = _formatar_brl(item["valor"])
        pct = item["pct"]
        barra = (
            f'<div class="extrato-cat-barra">'
            f'<div class="extrato-cat-linha">'
            f'<span class="extrato-cat-nome">'
            f'<span class="extrato-cat-dot" style="background:{cor};"></span>'
            f"{nome}"
            f"</span>"
            f'<span class="extrato-cat-valor">{valor}</span>'
            f"</div>"
            f'<div class="extrato-cat-track">'
            f'<span style="width:{pct:.1f}%; background:{cor};"></span>'
            f"</div>"
            f'<span class="extrato-cat-pct">{pct:.0f}%</span>'
            f"</div>"
        )
        barras.append(barra)

    return minificar(
        '<div class="extrato-breakdown">'
        '<span class="extrato-breakdown-titulo">'
        "BREAKDOWN · TOP 5 CATEGORIAS"
        "</span>" + "".join(barras) + "</div>"
    )


# CSS dedicado da página: src/dashboard/css/paginas/extrato.css
# (UX-M-02.B.1 extraiu de _estilos_locais_html inline -- 375L removidas.)


# ---------------------------------------------------------------------------
# Função pública
# ---------------------------------------------------------------------------


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página de extrato (UX-RD-06).

    Mantém assinatura intocada para que ``app.py`` continue chamando
    ``renderizar(dados, periodo, pessoa, ctx)`` sem mudança.
    """
    # UX-T-02: topbar-actions canônicas (Importar OFX + Exportar primary).
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes

    renderizar_grupo_acoes(
        [
            {
                "label": "Importar OFX",
                "glyph": "upload",
                "href": "?cluster=Inbox&tab=Inbox",
                "title": "Abrir Inbox para importar arquivo OFX",
            },
            {
                "label": "Exportar",
                "primary": True,
                "glyph": "download",
                "title": "Exportar transações filtradas",
            },
        ]
    )

    st.markdown(minificar(carregar_css_pagina("extrato")), unsafe_allow_html=True)
    # UX-U-03 + UX-T-02: page-header canônico via helper.
    from src.dashboard.componentes.page_header import renderizar_page_header

    st.markdown(
        renderizar_page_header(
            titulo="EXTRATO",
            subtitulo=(
                "Transações normalizadas dos OFX, faturas, comprovantes Pix. "
                "Cada linha tem sha8 de origem rastreável até o arquivo bruto."
            ),
            sprint_tag="UX-T-02",
            pills=[{"texto": "rastreabilidade sha256", "tipo": "d7-graduado"}],
        ),
        unsafe_allow_html=True,
    )

    if "extrato" not in dados:
        st.markdown(
            callout_html("warning", "Nenhum dado encontrado para o extrato."),
            unsafe_allow_html=True,
        )
        return

    gran = ctx.get("granularidade", "Mês") if ctx else "Mês"
    periodo = ctx.get("periodo", mes_selecionado) if ctx else mes_selecionado

    extrato = dados["extrato"]
    # Sprint UX-SPINNER-PROGRESS-FEEDBACK (2026-05-17): chain de filtros sobre
    # extrato XLSX pode levar ~500ms-1s em datasets grandes (4k+ transações).
    with st.spinner("Filtrando extrato..."):
        df = filtrar_por_periodo(extrato, gran, periodo)
        df = filtrar_por_pessoa(df, pessoa)
        df = filtrar_por_forma_pagamento(df, filtro_forma_ativo())
        # Sprint 73 (ADR-19): aplica filtros vindos de drill-down.
        df, filtros_drilldown = _aplicar_drilldown(df)
    _renderizar_breadcrumb(filtros_drilldown)

    if df.empty:
        st.markdown(
            callout_html("info", "Sem transações para o período selecionado."),
            unsafe_allow_html=True,
        )
        return

    # ---------- Saldo no topo ----------
    metricas_topo = calcular_saldo_topo(df)
    rotulo_periodo = str(periodo) if periodo else "período"
    st.markdown(
        _saldo_topo_html(metricas_topo, rotulo_periodo),
        unsafe_allow_html=True,
    )

    # ---------- UX-V-3.1: filt-bar canônica (entre KPIs e right-cards) -------
    contas_disp = (
        sorted(df["banco_origem"].dropna().astype(str).unique().tolist())
        if "banco_origem" in df.columns
        else []
    )
    categorias_disp = (
        sorted(df["categoria"].dropna().astype(str).unique().tolist())
        if "categoria" in df.columns
        else []
    )
    filtros_canonicos = _filt_bar_canonica(df, contas_disp, categorias_disp)
    df_filtrado_canon = _aplicar_filt_bar(df, filtros_canonicos)

    # ---------- T-02.B right-cards (Saldo 90d + Breakdown + Origens) ----------
    breakdown_top5 = calcular_breakdown_categorias(df_filtrado_canon, top_n=5)
    extrato_full = filtrar_por_pessoa(extrato, pessoa)
    extrato_full = filtrar_por_forma_pagamento(extrato_full, filtro_forma_ativo())
    st.markdown(
        _t02_right_cards_html(
            df_filtrado=df_filtrado_canon,
            breakdown=breakdown_top5,
            extrato_completo=extrato_full,
        ),
        unsafe_allow_html=True,
    )

    # ---------- UX-V-3.1: lista por dia com pílulas tipadas ------------------
    st.markdown(
        _lista_por_dia_html(df_filtrado_canon, limite=50),
        unsafe_allow_html=True,
    )

    # ---------- Filtros locais (busca + avançados) ----------
    busca = st.text_input(
        "Buscar por local",
        key="busca_local",
        placeholder="Digite para filtrar...",
    )

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

    # Sprint 87.2: tracking documental — coluna oculta usada pela tabela HTML.
    obrigatorias = _carregar_categorias_obrigatorias()
    if obrigatorias and "categoria" in resultado.columns:
        ids_com_doc = _carregar_ids_com_doc()
        resultado = resultado.copy()
        resultado["__tracking"] = resultado.apply(
            lambda row: _marcar_tracking(row, obrigatorias, ids_com_doc),
            axis=1,
        ).values

    # ---------- Layout: tabela (esquerda) + breakdown (direita) ----------
    breakdown = calcular_breakdown_categorias(resultado)
    _exibir_layout(resultado, breakdown)

    # ---------- Exportação CSV ----------
    _exibir_exportacao(resultado)

    # ---------- Painel drill-down item (INFRA-DRILL-DOWN-ITEM) ----------
    # Acionado por query-param ``?transacao_id=<sha8|sha256>``. Tem
    # prioridade sobre o drawer JSON: se ambos estão setados, mostra só
    # o painel (drawer continua disponível via session_state).
    _exibir_painel_drill_down(resultado)

    # ---------- Drawer (renderizado quando idx setado) ----------
    _exibir_drawer(resultado)


def _exibir_layout(df: pd.DataFrame, breakdown: list[dict[str, Any]]) -> None:
    """Layout 2.5fr (tabela paginada) + 1fr (breakdown) via st.columns."""
    total = len(df)
    if total == 0:
        st.markdown(
            callout_html("info", "Nenhuma transação após filtros."),
            unsafe_allow_html=True,
        )
        return

    tamanho = TAMANHO_PAGINA_EXTRATO
    n_paginas = max(1, (total + tamanho - 1) // tamanho)

    col_info, col_pag = st.columns([3, 1])
    with col_pag:
        pagina = st.selectbox(
            "Página",
            options=list(range(1, n_paginas + 1)),
            index=0,
            key="extrato_pagina",
            label_visibility="collapsed",
        )

    inicio, fim = _calcular_slice_pagina(total, tamanho, int(pagina))

    with col_info:
        st.markdown(
            f'<p class="extrato-info-pagina">'
            f"Mostrando {inicio + 1}-{fim} de {total} transações</p>",
            unsafe_allow_html=True,
        )

    df_pagina = df.iloc[inicio:fim]

    # Sprint 92c: legenda educativa da coluna ``Doc?`` (preservada após
    # migração para tabela HTML densa em UX-RD-06). Usa ``icon_html`` para
    # renderizar Feather inline (check-circle / alert-triangle) e mantém os
    # rótulos PT-BR ``Doc ok`` / ``Faltando`` para casar com o contrato de
    # ``_marcar_tracking``.
    icone_ok = icon_html("check-circle", tamanho=14, cor=CORES["positivo"])
    icone_falt = icon_html("alert-triangle", tamanho=14, cor=CORES["alerta"])
    legenda_doc_html = minificar(
        f"""
        <p class="extrato-legenda-doc" style="color:{CORES["texto_sec"]};
            font-size:{FONTE_CORPO}px; margin: 4px 0 12px 0;">
            Coluna 'Doc?':
            <span style="color:{CORES["positivo"]};">{icone_ok} Doc ok</span>
            = documento vinculado no grafo;
            <span style="color:{CORES["alerta"]};">{icone_falt} Faltando</span>
            = categoria obrigatória sem comprovante; vazio = sem tracking.
        </p>
        """
    )

    idx_drawer = st.session_state.get(_CHAVE_DRAWER_IDX)
    idx_drawer_pagina: int | None = None
    if idx_drawer is not None:
        try:
            idx_int = int(idx_drawer)
            if inicio <= idx_int < fim:
                idx_drawer_pagina = idx_int - inicio
        except (TypeError, ValueError):
            idx_drawer_pagina = None

    col_tabela, col_breakdown = st.columns([2.5, 1])
    with col_tabela:
        st.markdown(
            _tabela_densa_html(df_pagina, idx_drawer=idx_drawer_pagina),
            unsafe_allow_html=True,
        )
        st.markdown(legenda_doc_html, unsafe_allow_html=True)
    with col_breakdown:
        st.markdown(
            _breakdown_lateral_html(breakdown),
            unsafe_allow_html=True,
        )

    # Seletor + botão "Abrir drawer" (compromisso pragmático Streamlit).
    rotulos = _rotulos_transacoes(df_pagina)
    if rotulos:
        col_sel, col_btn = st.columns([4, 1])
        with col_sel:
            sel_local = st.selectbox(
                "Inspecionar transação",
                options=list(range(len(rotulos))),
                format_func=lambda i: rotulos[i] if i < len(rotulos) else "",
                key="extrato_seletor_drawer",
            )
        with col_btn:
            st.write("")
            if st.button("Abrir drawer", key="extrato_btn_drawer", type="primary"):
                # Converte índice da página para índice global no df filtrado.
                idx_global = inicio + int(sel_local)
                st.session_state[_CHAVE_DRAWER_IDX] = idx_global


def _rotulos_transacoes(df: pd.DataFrame) -> list[str]:
    """Rótulos curtos para o selectbox de inspeção."""
    rotulos: list[str] = []
    for _, row in df.iterrows():
        data_v = row.get("data")
        data_str = (
            pd.to_datetime(data_v).strftime("%Y-%m-%d")
            if data_v is not None and not pd.isna(data_v)
            else "-"
        )
        valor = float(pd.to_numeric(row.get("valor"), errors="coerce") or 0.0)
        local = str(row.get("local") or "")[:40]
        rotulos.append(f"{data_str} · R$ {valor:,.2f} · {local}")
    return rotulos


def _exibir_exportacao(df: pd.DataFrame) -> None:
    """Botão de download CSV (preserva contrato Sprint 92)."""
    if df.empty:
        return
    colunas_export = [
        c
        for c in [
            "data",
            "valor",
            "local",
            "categoria",
            "classificacao",
            "forma_pagamento",
            "banco_origem",
            "tipo",
            "quem",
            "mes_ref",
        ]
        if c in df.columns
    ]
    csv = "﻿" + df[colunas_export].to_csv(index=False, sep=";", decimal=",")
    st.download_button(
        label="Exportar CSV",
        data=csv,
        file_name="extrato.csv",
        mime="text/csv",
    )


_CAMINHO_REVISAO_HUMANA: Path = (
    Path(__file__).resolve().parents[3] / "data" / "output" / "revisao_humana.sqlite"
)


def _ler_query_param_transacao_id() -> str | None:
    """Devolve ``?transacao_id=<x>`` se presente, senão None.

    Aceita sha8 (prefixo) ou sha256 completo. Validação leve: só strings
    não vazias, alfanuméricas. Strings inválidas são tratadas como ausentes
    (graceful degradation -- nunca quebrar o render por query param ruim).
    """
    try:
        qs = st.query_params  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return None
    valor = qs.get("transacao_id")
    if not valor:
        return None
    if isinstance(valor, list):
        valor = valor[0] if valor else None
    if not valor:
        return None
    valor_str = str(valor).strip()
    if not valor_str or not valor_str.isalnum():
        return None
    return valor_str


def _localizar_linha_transacao(df: pd.DataFrame, identificador: str) -> pd.Series | None:
    """Encontra a linha do DF cujo ``identificador`` casa com prefix.

    O sha256 da transação é guardado em ``df['identificador']``. Aceita
    prefixo (sha8) -- usa ``str.startswith``. Quando há múltiplos matches
    retorna o primeiro; quando nenhum, devolve None.
    """
    if "identificador" not in df.columns or df.empty:
        return None
    serie_id = df["identificador"].fillna("").astype(str)
    mascara = serie_id.str.startswith(identificador)
    encontrados = df[mascara]
    if encontrados.empty:
        return None
    return encontrados.iloc[0]


def _exibir_painel_drill_down(df: pd.DataFrame) -> None:
    """Renderiza o painel lateral de drill-down item.

    Acionado por ``?transacao_id=<sha8|sha256>`` na URL. Busca a transação
    no DataFrame local (para meta básica) + no grafo (para documento e
    itens) e injeta o HTML do painel.

    Quando o param está ausente ou a transação não existe, no-op.
    """
    identificador = _ler_query_param_transacao_id()
    if identificador is None:
        return

    linha = _localizar_linha_transacao(df, identificador)
    if linha is None:
        st.markdown(
            callout_html(
                "warning",
                f"Transação {identificador[:8]} não encontrada no período "
                "filtrado. Ajuste filtros ou cole o sha256 completo.",
            ),
            unsafe_allow_html=True,
        )
        return

    transacao_dict = transacao_para_dict(linha)
    documento, itens = _buscar_drill_down_grafo(identificador)

    painel_html = renderizar_painel_drill_down(transacao_dict, documento=documento, itens=itens)
    st.markdown(painel_html, unsafe_allow_html=True)

    # Botão "marcar revisado" -- best-effort em revisao_humana.sqlite.
    col_rev, col_fechar = st.columns([1, 1])
    with col_rev:
        if st.button(
            "Marcar revisado",
            key=f"painel_drill_revisar_{identificador[:8]}",
        ):
            tx_id = _resolver_transacao_id_no_grafo(identificador)
            if tx_id is None:
                st.toast("Transação não localizada no grafo.")
            else:
                ok = persistir_revisao(tx_id, _CAMINHO_REVISAO_HUMANA)
                if ok:
                    st.toast(f"Marcado como revisado (id={tx_id}).")
                else:
                    st.toast("revisao_humana.sqlite ausente -- no-op.")
    with col_fechar:
        if st.button("Fechar painel", key=f"painel_drill_fechar_{identificador[:8]}"):
            try:
                qs = st.query_params  # type: ignore[attr-defined]
                if "transacao_id" in qs:
                    del qs["transacao_id"]
            except Exception:  # noqa: BLE001
                pass  # noqa: BLE001 -- query_params pode falhar em runtime antigo; rerun segue
            st.rerun()


def _buscar_drill_down_grafo(
    identificador: str,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Resolve documento + itens do grafo para a transação.

    Wrapper sobre ``dados_grafo.buscar_transacao_id_por_identificador`` +
    ``dados_grafo.carregar_drill_down_transacao``. Faz graceful
    degradation em qualquer erro (ADR-10): retorna (None, []) e o painel
    mostra callout "sem documento vinculado".
    """
    try:
        from src.dashboard.dados_grafo import (
            buscar_transacao_id_por_identificador,
            carregar_drill_down_transacao,
        )
    except ImportError:
        return None, []
    try:
        tx_id = buscar_transacao_id_por_identificador(identificador)
        if tx_id is None:
            return None, []
        resultado = carregar_drill_down_transacao(tx_id)
        return resultado.get("documento"), resultado.get("itens", [])
    except Exception:  # noqa: BLE001
        return None, []


def _resolver_transacao_id_no_grafo(identificador: str) -> int | None:
    """Wrapper resiliente para localizar transação_id (PK) no grafo."""
    try:
        from src.dashboard.dados_grafo import buscar_transacao_id_por_identificador
    except ImportError:
        return None
    try:
        return buscar_transacao_id_por_identificador(identificador)
    except Exception:  # noqa: BLE001
        return None


def _exibir_drawer(df: pd.DataFrame) -> None:
    """Renderiza o drawer JSON quando ``session_state`` tem índice setado."""
    idx = st.session_state.get(_CHAVE_DRAWER_IDX)
    if idx is None:
        return
    try:
        idx_int = int(idx)
    except (TypeError, ValueError):
        return
    if idx_int < 0 or idx_int >= len(df):
        # índice obsoleto (filtro mudou); limpa silenciosamente.
        # Sprint UX-BE-SESSION-STATE-SAFE (2026-05-17): pop seguro vs del.
        st.session_state.pop(_CHAVE_DRAWER_IDX, None)
        return

    row = df.iloc[idx_int]
    transacao = transacao_para_dict(row)

    # Documento vinculado pelo grafo (best-effort).
    doc_vinculado = _buscar_doc_vinculado(row)

    drawer_html = renderizar_drawer(transacao, doc_vinculado)
    st.markdown(drawer_html, unsafe_allow_html=True)

    if st.button("Fechar drawer", key="extrato_btn_fechar_drawer"):
        # Sprint UX-BE-SESSION-STATE-SAFE (2026-05-17): pop seguro vs del.
        st.session_state.pop(_CHAVE_DRAWER_IDX, None)
        st.rerun()


def _buscar_doc_vinculado(row: pd.Series) -> dict[str, Any] | None:
    """Best-effort: busca primeiro documento vinculado à transação no grafo.

    Não há ainda função canônica ``documentos_de_transacao`` em
    ``src/graph/queries.py``; o caminho atual (UX-RD-06) checa apenas se o
    ``identificador`` da transação está no conjunto de transações com
    documento vinculado e devolve um stub mínimo. Quando uma sprint futura
    adicionar a query rica, basta substituir o corpo desta função.
    """
    ident = row.get("identificador") if hasattr(row, "get") else None
    if ident is None or pd.isna(ident):
        return None
    try:
        ids_com_doc = _carregar_ids_com_doc()
    except Exception:  # noqa: BLE001
        return None
    if str(ident) not in ids_com_doc:
        return None
    return {
        "sha8": str(ident)[:8],
        "tipo_edge_semantico": "documento_de",
        "nome": "ver módulo de Documentos",
    }


def _calcular_slice_pagina(
    total_linhas: int, tamanho_pagina: int, pagina_1_based: int
) -> tuple[int, int]:
    """Sprint 92a.8: devolve ``(start, stop)`` 0-indexado para ``iloc``."""
    if total_linhas <= 0 or tamanho_pagina <= 0:
        return (0, 0)
    n_paginas = max(1, (total_linhas + tamanho_pagina - 1) // tamanho_pagina)
    pagina = max(1, min(pagina_1_based, n_paginas))
    inicio = (pagina - 1) * tamanho_pagina
    fim = min(inicio + tamanho_pagina, total_linhas)
    return (inicio, fim)


# ---------------------------------------------------------------------------
# T-02.B — Right-cards canônicos (Saldo 90d / Breakdown / Origens)
# ---------------------------------------------------------------------------


def _saldo_90d_svg(saldos: list[float], w: int = 540, h: int = 120) -> str:
    """SVG inline de área de saldo 90 dias. Espelha _extrato-render.js."""
    if not saldos or len(saldos) < 2:
        return '<div style="color:var(--text-muted);font-size:12px;">Sem dados.</div>'
    minv = min(saldos)
    maxv = max(saldos)
    span = max(maxv - minv, 1.0)
    n = len(saldos) - 1
    pts = " ".join(
        f"{(i / n) * w:.1f},{h - ((v - minv) / span) * h * 0.85 - 6:.1f}"
        for i, v in enumerate(saldos)
    )
    area = f"0,{h} {pts} {w},{h}"
    txt_l = (
        f'<text x="0" y="{h + 14}" font-family="JetBrains Mono" '
        'font-size="10" fill="var(--text-muted)">90 dias atrás</text>'
    )
    txt_r = (
        f'<text x="{w}" y="{h + 14}" text-anchor="end" '
        'font-family="JetBrains Mono" font-size="10" '
        'fill="var(--text-muted)">hoje</text>'
    )
    return (
        f'<svg viewBox="0 0 {w} {h + 18}" '
        'style="width:100%;height:auto;display:block;">'
        '<defs><linearGradient id="t02sg" x1="0" x2="0" y1="0" y2="1">'
        '<stop offset="0%" stop-color="#bd93f9" stop-opacity="0.4"/>'
        '<stop offset="100%" stop-color="#bd93f9" stop-opacity="0.02"/>'
        "</linearGradient></defs>"
        f'<polygon points="{area}" fill="url(#t02sg)"/>'
        f'<polyline points="{pts}" fill="none" '
        'stroke="var(--accent-purple)" stroke-width="1.4"/>'
        f"{txt_l}{txt_r}"
        "</svg>"
    )


def _calcular_saldo_90d(extrato_full: pd.DataFrame) -> list[float]:
    """Calcula série diária de saldo cumulativo dos últimos 90 dias."""
    if extrato_full.empty or "data" not in extrato_full.columns:
        return []
    df = extrato_full.copy()
    df["__data"] = pd.to_datetime(df["data"], errors="coerce")
    df = df.dropna(subset=["__data"])
    if df.empty:
        return []
    df["__valor_signed"] = df.apply(
        lambda r: (
            float(r.get("valor", 0))
            if str(r.get("tipo", "")) == "Receita"
            else -abs(float(r.get("valor", 0)))
        ),
        axis=1,
    )
    df = df.sort_values("__data")
    diario = df.groupby(df["__data"].dt.date)["__valor_signed"].sum().sort_index()
    cum = diario.cumsum()
    if len(cum) > 90:
        cum = cum.tail(90)
    return [float(v) for v in cum.tolist()]


def _t02_right_cards_html(
    df_filtrado: pd.DataFrame,
    breakdown: list[dict[str, Any]],
    extrato_completo: pd.DataFrame,
) -> str:
    """3 cards lado-a-lado (mockup 02-extrato.html right-cards)."""
    saldos = _calcular_saldo_90d(extrato_completo)
    saldo_chart = _saldo_90d_svg(saldos)
    if saldos:
        minimo = min(saldos)
        maximo = max(saldos)
        delta = saldos[-1] - saldos[0]
        saldo_meta = (
            f'<div style="display:flex;gap:12px;margin-top:8px;'
            'font-family:var(--ff-mono);font-size:11px;">'
            f'<div><span style="color:var(--text-muted);">mín</span> '
            f"{_formatar_brl(minimo)}</div>"
            f'<div><span style="color:var(--text-muted);">máx</span> '
            f"{_formatar_brl(maximo)}</div>"
            f'<div style="margin-left:auto;color:'
            f'{"var(--d7-graduado)" if delta >= 0 else "var(--accent-red)"};">'
            f"{'+' if delta >= 0 else ''}{_formatar_brl(delta)}</div>"
            "</div>"
        )
    else:
        saldo_meta = ""

    bd_html = ""
    if breakdown:
        total_bd = sum(c["valor"] for c in breakdown) or 1
        for c in breakdown:
            pct = (c["valor"] / total_bd) * 100
            bd_html += (
                '<div class="t02-cat-bar">'
                f'<span class="name">{c["categoria"]}</span>'
                f'<span class="v">{_formatar_brl(c["valor"])} · {pct:.0f}%</span>'
                f'<div class="track"><span style="width:{pct:.1f}%;'
                'background:var(--accent-purple);"></span></div>'
                "</div>"
            )
    else:
        bd_html = (
            '<div style="color:var(--text-muted);font-size:12px;">Sem despesas no período.</div>'
        )

    bancos: dict[str, int] = {}
    if "banco_origem" in df_filtrado.columns and not df_filtrado.empty:
        bancos = df_filtrado["banco_origem"].fillna("—").astype(str).value_counts().to_dict()
    total_origens = sum(int(v) for v in bancos.values()) or 1
    cores = [
        "var(--d7-graduado)",
        "var(--accent-purple)",
        "var(--accent-pink)",
        "var(--accent-yellow)",
        "var(--accent-cyan)",
    ]
    origens_html = ""
    for i, (banco, count) in enumerate(list(bancos.items())[:5]):
        pct = (count / total_origens) * 100
        cor = cores[i % len(cores)]
        origens_html += (
            '<div style="display:flex;align-items:center;gap:8px;'
            'margin-bottom:6px;">'
            f'<span style="font-family:var(--ff-mono);width:80px;color:{cor};'
            f'font-size:11px;">{banco}</span>'
            '<div style="flex:1;height:4px;background:var(--bg-inset);'
            'border-radius:2px;overflow:hidden;">'
            f'<span style="display:block;height:100%;width:{pct:.1f}%;'
            f'background:{cor};"></span></div>'
            f'<span style="font-family:var(--ff-mono);color:var(--text-muted);'
            f'font-size:11px;">{count} txns</span>'
            "</div>"
        )
    if not origens_html:
        origens_html = (
            '<div style="color:var(--text-muted);font-size:12px;">Sem origens no período.</div>'
        )

    return minificar(
        '<div style="display:grid;grid-template-columns:repeat(3,1fr);'
        'gap:12px;margin-bottom:16px;">'
        '<div class="t02-right-card">'
        "<h3>Saldo · 90 dias</h3>"
        f"{saldo_chart}{saldo_meta}"
        "</div>"
        '<div class="t02-right-card">'
        "<h3>Breakdown · saída do período</h3>"
        f"{bd_html}"
        "</div>"
        '<div class="t02-right-card">'
        "<h3>Origens dos dados</h3>"
        f"{origens_html}"
        "</div>"
        "</div>"
    )


# "O dinheiro é um bom servo, mas um mau mestre." -- Francis Bacon
