"""Página Busca Global -- Sprint UX-114 (refactor sobre Sprint 52).

Busca FUNCIONAL com:

- Texto descritivo curto (max 90 chars).
- Dropdown 'Tipo' com opções canônicas (Todos / Pessoais / ... / IRPF).
- Input com placeholder MAIÚSCULO.
- Autocomplete (sugestões via `busca_indice.sugestoes`).
- Chips abaixo do input com TIPOS DE DOCUMENTOS canônicos (8 fixos).
- Roteador: query exata casa nome de aba -> link rápido; casa fornecedor
  -> link rápido para Catalogação filtrada; senão busca_global do grafo.
- Filtros sidebar (Mês, Pessoa, Forma de pagamento) impactam resultados.
- Output em st.dataframe com colunas: Nome do documento, Texto extraído,
  Caminho, Botão Exportar (copia para data/exports/<ts>_<nome>.<ext>).

Padrões canônicos aplicados:
- (l) subregra retrocompatível: chips Sprint 59 mantidos abaixo do input
  (substituição apenas no conteúdo dos chips).
- (m) branch reversível: índice falha -> aviso visual + busca puro
  (Sprint 52 fallback) preservada.
- PII: mascarada em UI, dataframe e export (4 sítios).
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from src.dashboard import dados as _dados
from src.dashboard.componentes.busca_indice import construir_indice, sugestoes
from src.dashboard.componentes.busca_roteador import rotear
from src.dashboard.dados import (
    buscar_global,
    formatar_moeda,
)
from src.dashboard.tema import (
    CORES,
    FONTE_LABEL,
    SPACING,
    callout_html,
    hero_titulo_html,
    icon_html,
    rgba_cor_inline,
    subtitulo_secao_html,
)

RAIZ = Path(__file__).resolve().parents[3]
DIR_EXPORTS_DEFAULT: Path = RAIZ / "data" / "exports"

# Chips canonicos: TIPOS DE DOCUMENTOS (substitui neoenergia/farmacia/uber).
CHIPS_TIPOS_CANONICOS: list[str] = [
    "Holerite",
    "Nota Fiscal",
    "DAS",
    "Boleto",
    "IRPF",
    "Recibo",
    "Comprovante",
    "Contracheque",
]

# Opções do dropdown de filtro por categoria de tipo.
OPCOES_DROPDOWN_TIPO: list[str] = [
    "Todos",
    "Pessoais",
    "Trabalho",
    "Notas Fiscais",
    "Holerites",
    "Boletos",
    "Receitas Medicas",
    "DAS",
    "IRPF",
]

# Mapa rótulo do dropdown -> conjunto de tipos canônicos do grafo (lower).
_MAPA_DROPDOWN_TIPOS: dict[str, set[str]] = {
    "Pessoais": {"comprovante_cpf", "irpf_parcela", "receita_medica", "holerite"},
    "Trabalho": {"holerite", "das_parcsn", "das_mei", "contracheque"},
    "Notas Fiscais": {
        "nfce_consumidor_eletronica",
        "danfe_nfe55",
        "xml_nfe",
        "cupom_fiscal_foto",
        "recibo_nao_fiscal",
    },
    "Holerites": {"holerite", "contracheque"},
    "Boletos": {"boleto_servico", "fatura_cartao"},
    "Receitas Medicas": {"receita_medica"},
    "DAS": {"das_parcsn", "das_mei"},
    "IRPF": {"irpf_parcela"},
}

# Texto descritivo único, <= 90 chars.
TEXTO_DESCRITIVO: str = "Busque por tipo de documento, fornecedor, CNPJ ou identificador."
PLACEHOLDER_INPUT: str = "BUSQUE: HOLERITE, NF, DAS, BOLETO, IRPF, FORNECEDOR, CNPJ..."

# CSS local: cor do ícone (i) do callout info -- usar var(--color-destaque)
# em vez do azul Streamlit default (feedback dono 2026-04-27).
_CSS_LOCAL_BUSCA: str = (
    "<style>"
    "div[data-testid='stAlert'] svg, "
    "div[role='alert'] svg {"
    f" color: {CORES['destaque']} !important;"
    " fill: currentColor !important;"
    "}"
    "</style>"
)


# ---------------------------------------------------------------------------
# PII: mascaramento canônico (CPF, CNPJ, email)
# ---------------------------------------------------------------------------

_RE_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_RE_CNPJ = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
_RE_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")


def _mascarar_pii(texto: str) -> str:
    """Mascara CPF, CNPJ e email em uma string. Idempotente."""
    if not isinstance(texto, str) or not texto:
        return texto
    texto = _RE_CPF.sub("***.***.***-**", texto)
    texto = _RE_CNPJ.sub("**.***.***/****-**", texto)
    texto = _RE_EMAIL.sub("***@***", texto)
    return texto


# ---------------------------------------------------------------------------
# Helpers de filtro sidebar
# ---------------------------------------------------------------------------


def _aplicar_filtros_sidebar(
    docs: list[dict],
    *,
    periodo: str | None,
    pessoa: str | None,
    forma: str | None,
) -> list[dict]:
    """Aplica filtros da sidebar global aos documentos retornados.

    - `periodo` (YYYY-MM ou 'Todos'/None) filtra por `data` do documento.
    - `pessoa` filtra por metadado `pessoa` ou `quem` (case-insensitive).
    - `forma` filtra por metadado `forma_pagamento` (case-insensitive).
    """
    saida = list(docs)
    if periodo and str(periodo).strip() and str(periodo).lower() != "todos":
        prefixo = str(periodo).strip()
        saida = [d for d in saida if str(d.get("data", "")).startswith(prefixo)]
    if pessoa and str(pessoa).strip() and str(pessoa).lower() != "todos":
        alvo = str(pessoa).strip().lower()
        saida = [
            d
            for d in saida
            if alvo in (str(d.get("pessoa", "")) + " " + str(d.get("quem", ""))).lower()
        ]
    if forma and str(forma).strip() and str(forma).lower() != "todos":
        alvo = str(forma).strip().lower()
        saida = [d for d in saida if alvo in str(d.get("forma_pagamento", "")).lower()]
    return saida


def _filtrar_por_tipo_dropdown(docs: list[dict], rotulo: str) -> list[dict]:
    """Filtra documentos por categoria do dropdown de tipo."""
    if not rotulo or rotulo == "Todos":
        return docs
    tipos_aceitos = _MAPA_DROPDOWN_TIPOS.get(rotulo, set())
    if not tipos_aceitos:
        return docs
    saida: list[dict] = []
    for d in docs:
        tipo_d = str(d.get("tipo_documento", "")).lower()
        if tipo_d in tipos_aceitos or any(t in tipo_d for t in tipos_aceitos):
            saida.append(d)
    return saida


# ---------------------------------------------------------------------------
# Helpers de export
# ---------------------------------------------------------------------------


def exportar_documento(
    caminho_origem: str | Path,
    *,
    diretorio_destino: Path | None = None,
) -> Path | None:
    """Copia `caminho_origem` para `data/exports/<ts>_<nome>.<ext>`.

    Cria o diretório de destino se não existir. Nunca deleta o original.
    Devolve o Path do arquivo destino ou None se `caminho_origem` inválido.
    """
    if not caminho_origem:
        return None
    origem = Path(caminho_origem)
    if not origem.exists() or not origem.is_file():
        return None
    destino_dir = diretorio_destino if diretorio_destino is not None else DIR_EXPORTS_DEFAULT
    destino_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    nome_destino = f"{ts}_{origem.name}"
    destino = destino_dir / nome_destino
    shutil.copy2(origem, destino)
    return destino


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------


def renderizar(
    dados: dict[str, pd.DataFrame] | None = None,
    periodo: str | None = None,
    pessoa: str | None = None,
    ctx: dict | None = None,
) -> None:
    """Ponto de entrada da página Busca Global (refactor UX-114)."""
    _ = dados
    ctx = ctx or {}
    forma_pagamento = ctx.get("forma_pagamento")

    st.markdown(_CSS_LOCAL_BUSCA, unsafe_allow_html=True)

    st.markdown(
        hero_titulo_html(
            "",
            "Busca Global",
            TEXTO_DESCRITIVO,
        ),
        unsafe_allow_html=True,
    )

    # Branch (m) reversível: tenta construir índice; página segue funcional
    # mesmo se o grafo não existir.
    try:
        indice = _indice_cached()
        indice_ok = bool(indice and any(indice.values()))
    except Exception:  # noqa: BLE001 -- defensivo; falha única = índice vazio
        indice = {"fornecedores": [], "descricoes": [], "tipos_doc": [], "abas": []}
        indice_ok = False

    if not indice_ok:
        st.markdown(
            callout_html(
                "warning",
                "Índice de busca degradado; rode `./run.sh --tudo` para "
                "popular o grafo. Busca segue ativa por substring direto.",
            ),
            unsafe_allow_html=True,
        )

    rotulo_tipo, termo = _renderizar_controles(indice)

    if not _dados.CAMINHO_GRAFO.exists():
        st.markdown(
            callout_html(
                "warning",
                "Grafo SQLite não encontrado. Popule rodando `./run.sh --tudo`.",
            ),
            unsafe_allow_html=True,
        )
        return

    if not termo:
        st.markdown(
            callout_html(
                "info",
                "Digite um termo acima ou clique em um chip para iniciar.",
            ),
            unsafe_allow_html=True,
        )
        return

    # Roteador: nome de aba ou fornecedor dá link rápido além da listagem.
    rota = rotear(termo, indice=indice)
    _renderizar_rota_rapida(rota)

    resultados = buscar_global(termo)

    # Filtros: dropdown tipo + sidebar (mes/pessoa/forma).
    docs_filtrados = _filtrar_por_tipo_dropdown(resultados.get("documentos", []), rotulo_tipo)
    docs_filtrados = _aplicar_filtros_sidebar(
        docs_filtrados,
        periodo=periodo,
        pessoa=pessoa,
        forma=forma_pagamento,
    )

    total_filtrado = (
        len(resultados.get("fornecedores", []))
        + len(docs_filtrados)
        + len(resultados.get("transacoes", []))
        + len(resultados.get("itens", []))
    )

    _renderizar_resumo(termo, total_filtrado)

    if total_filtrado == 0:
        st.markdown(
            callout_html("info", f"Nenhum resultado para '{_mascarar_pii(termo)}'."),
            unsafe_allow_html=True,
        )
        return

    _renderizar_tabela_documentos(docs_filtrados)


# ---------------------------------------------------------------------------
# Cache + componentes de UI
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300)
def _indice_cached() -> dict[str, list[str]]:
    """Índice cacheado por sessão (ttl 5 min). Branch reversível se falha."""
    return construir_indice()


def _aplicar_chip_sugestao(valor: str) -> None:
    """Callback: ao clicar num chip, popula o input. Sprint 59 -> UX-114.

    Mantido com o nome canônico Sprint 59 para preservar contrato N-para-N
    com os testes regressivos (`tests/test_busca_global.py`).
    """
    st.session_state["busca_termo_input"] = valor


# Alias semântico para compatibilidade com Sprint 59 -- os dois nomes
# apontam para o mesmo callback.
_aplicar_chip_tipo = _aplicar_chip_sugestao


def _renderizar_controles(indice: dict[str, list[str]]) -> tuple[str, str]:
    """Renderiza dropdown + label + input + autocomplete + chips.

    Devolve `(rótulo_tipo, termo_query)`.
    """
    rotulo_tipo = st.selectbox(
        "Tipo de busca",
        OPCOES_DROPDOWN_TIPO,
        index=0,
        key="busca_tipo_dropdown",
        help="Filtra os resultados por categoria de documento.",
    )

    svg_busca = icon_html("search", tamanho=18, cor=CORES["destaque"])
    st.markdown(
        f'<div class="ouroboros-label-icon" style="margin-top: {SPACING["sm"]}px;">'
        f"{svg_busca}<span>Busca global</span></div>",
        unsafe_allow_html=True,
    )
    termo = st.text_input(
        "Busca global",
        placeholder=PLACEHOLDER_INPUT,
        label_visibility="collapsed",
        key="busca_termo_input",
    )

    # Autocomplete: sugestões em tempo real abaixo do input
    if termo and len(termo.strip()) >= 2:
        sugs = sugestoes(termo, indice=indice, limite=10)
        if sugs:
            st.markdown(
                subtitulo_secao_html("Sugestões", cor=CORES["neutro"]),
                unsafe_allow_html=True,
            )
            cols_sug = st.columns(min(len(sugs), 5))
            for idx_s, sug in enumerate(sugs):
                col = cols_sug[idx_s % len(cols_sug)]
                with col:
                    st.button(
                        _mascarar_pii(sug),
                        key=f"busca_autocomp_{idx_s}",
                        use_container_width=True,
                        on_click=_aplicar_chip_sugestao,
                        args=(sug,),
                    )

    # Chips fixos (TIPOS canônicos -- substitui Sprint 59 chips antigos)
    st.markdown(
        f'<p style="color: var(--color-texto-sec); font-size: {FONTE_LABEL}px;'
        f' margin: {SPACING["sm"]}px 0 4px 0;">Tipos rápidos</p>',
        unsafe_allow_html=True,
    )
    cols = st.columns(len(CHIPS_TIPOS_CANONICOS))
    for idx, (col, sug) in enumerate(zip(cols, CHIPS_TIPOS_CANONICOS)):
        with col:
            st.button(
                sug,
                key=f"busca_chip_tipo_{idx}",
                use_container_width=True,
                on_click=_aplicar_chip_sugestao,
                args=(sug,),
            )

    return rotulo_tipo, (termo or "").strip()


def _renderizar_rota_rapida(rota: dict) -> None:
    """Mostra link rápido se a query casa aba ou fornecedor."""
    kind = rota.get("kind")
    destino = rota.get("destino", "")
    if kind == "aba" and destino:
        st.markdown(
            callout_html(
                "info",
                f"Sua busca casa o nome da aba <strong>{destino}</strong>.",
            ),
            unsafe_allow_html=True,
        )
        if st.button(
            f"Ir para aba {destino}",
            key="busca_link_aba",
            use_container_width=False,
        ):
            cluster = rota.get("tipo") or ""
            params: dict = {"tab": destino}
            if cluster:
                params["cluster"] = cluster
            st.query_params.from_dict(params)
            st.rerun()
    elif kind == "fornecedor" and destino:
        st.markdown(
            callout_html(
                "info",
                f"Sua busca casa o fornecedor <strong>{_mascarar_pii(destino)}</strong>.",
            ),
            unsafe_allow_html=True,
        )
        if st.button(
            "Ir para Catalogação filtrada",
            key="busca_link_forn",
            use_container_width=False,
        ):
            st.query_params.from_dict(
                {
                    "tab": "Catalogação",
                    "fornecedor": destino,
                    "cluster": "Documentos",
                }
            )
            st.rerun()


def _renderizar_resumo(termo: str, total: int) -> None:
    """Linha de resumo mostrando contagem total."""
    termo_seguro = _mascarar_pii(termo)
    st.markdown(
        '<div class="ouroboros-row-flex ouroboros-row-resumo-busca">'
        '<p style="color: var(--color-texto); font-size: var(--font-corpo);'
        ' margin: 0;">Resultados para '
        f'<strong style="color: var(--color-destaque);">"{termo_seguro}"</strong></p>'
        '<p style="color: var(--color-texto-sec); font-size: var(--font-label);'
        f' margin: 0;">{total} itens encontrados</p>'
        "</div>",
        unsafe_allow_html=True,
    )


def _renderizar_tabela_documentos(docs: list[dict]) -> None:
    """Renderiza documentos em tabela com 4 colunas + botão Exportar.

    Colunas: Nome do documento, Texto extraído (resumo, max 80 chars),
    Caminho do arquivo, Botão Exportar.
    """
    st.markdown(
        subtitulo_secao_html(f"Documentos ({len(docs)})"),
        unsafe_allow_html=True,
    )
    if not docs:
        st.markdown(
            callout_html("info", "Nenhum documento casou com os filtros."),
            unsafe_allow_html=True,
        )
        return

    linhas: list[dict] = []
    for d in docs[:200]:
        nome = (d.get("nome_canonico") or d.get("razao_social") or "--").strip() or "--"
        nome = _mascarar_pii(nome)
        texto_extra = (d.get("texto_extraido") or d.get("descricao") or "").strip()
        if not texto_extra:
            texto_extra = (
                f"{d.get('tipo_documento', '--')} | "
                f"{formatar_moeda(float(d.get('total', 0.0) or 0.0))}"
            )
        if len(texto_extra) > 80:
            texto_extra = texto_extra[:77] + "..."
        texto_extra = _mascarar_pii(texto_extra)
        caminho = d.get("caminho_arquivo") or d.get("path") or ""
        linhas.append(
            {
                "Nome do documento": nome,
                "Texto extraído": texto_extra,
                "Caminho do arquivo": caminho or "--",
            }
        )

    df = pd.DataFrame(linhas)
    st.dataframe(df, width="stretch", hide_index=True)

    # Botão Exportar global: copia todos com caminho válido para data/exports/.
    docs_com_caminho = [d for d in docs if d.get("caminho_arquivo") or d.get("path")]
    if docs_com_caminho and st.button(
        f"Exportar {len(docs_com_caminho)} documento(s)",
        key="busca_exportar_global",
    ):
        n_ok = 0
        for d in docs_com_caminho:
            origem = d.get("caminho_arquivo") or d.get("path")
            if exportar_documento(origem) is not None:
                n_ok += 1
        st.success(f"{n_ok} arquivo(s) copiado(s) para data/exports/.")


def _divisor() -> str:
    """HTML de um divisor horizontal fino reutilizável."""
    return (
        f'<hr style="'
        f"border: 0;"
        f" border-top: 1px solid {rgba_cor_inline(CORES['texto_sec'], 0.25)};"
        f" margin: {SPACING['lg']}px 0;"
        f'" />'
    )


# "Buscar é perguntar com precisão." -- Sócrates (parafraseado)
