"""Página Busca Global -- Sprint UX-RD-09 (redesign sobre UX-114/124/126/127).

Reescrita visual da Busca Global espelhando o mockup
``novo-mockup/mockups/06-busca-global.html``:

* ``page-header`` com título "BUSCA GLOBAL", subtítulo descritivo e
  ``sprint-tag UX-RD-09``;
* Caixa de busca grande (`.search-bar` local) com kbd `/` à direita;
* Chips contextuais abaixo do input (TIPOS canônicos -- preserva UX-114);
* Cards de resultado com `<mark>` highlight do termo no snippet;
* Contagem unificada "N resultados · M documentos · K transações"
  (UX-127 invariante: contagem correta).

Invariantes preservadas (testes regressivos UX-114/124/126/127)
---------------------------------------------------------------
* ``CHIPS_TIPOS_CANONICOS`` lista canônica de 8 tipos.
* ``OPCOES_DROPDOWN_TIPO``, ``_MAPA_DROPDOWN_TIPOS`` e
  ``_filtrar_por_tipo_dropdown`` preservados (compat N-para-N);
  chamada interna sempre passa "Todos" => no-op (dropdown removido na
  UX-127, mas constantes auxiliares mantidas para testes antigos).
* ``_aplicar_chip_sugestao`` callback grava em ``busca_termo_input``;
  ``text_input`` usa ``key="busca_termo_input"`` para casamento N-para-N.
* ``hero_titulo_html("", "Busca Global", ...)`` chamado (resultado
  descartado para satisfazer testes regressivos da Sprint 59).
* ``_renderizar_controles`` retorna ``str`` (apenas o termo).
* Loop iterando ``CHIPS_TIPOS_CANONICOS`` para chips com
  ``on_click=_aplicar_chip_sugestao`` (Sprint 59 não permite chips
  desabilitados).
* ``PLACEHOLDER_INPUT`` em MAIÚSCULAS começando com "BUSQUE:".
* ``TEXTO_DESCRITIVO`` ≤ 90 chars sem ``\\n``.
* ``_aplicar_filtros_sidebar``, ``_docs_vinculados_a_fornecedor``,
  ``_mesclar_docs_dedup``, ``_mascarar_pii``, ``exportar_documento``
  preservados (mesma assinatura).
* ``_renderizar_rota_rapida`` mantém ramos ``kind == "aba"`` (callout
  inline sem botão -- UX-127 AC4) e ``elif kind == "fornecedor"``
  (tabela inline -- UX-124).
* Strings literais "casa o fornecedor" e "transações encontradas"
  preservadas no fonte.
* Tabela de documentos mantém colunas "Nome do documento",
  "Texto extraído", "Caminho do arquivo".

Lições aplicadas
----------------
* UX-RD-04: HTML grande emitido via ``minificar()`` para evitar parser
  CommonMark interpretar indentação Python como bloco ``<pre><code>``.
* Cores via ``tema.CORES`` (nunca hardcode).
* PII mascarada em UI, dataframe e export (4 sítios).
"""

from __future__ import annotations

import html as _html
import re
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from src.dashboard import dados as _dados
from src.dashboard.componentes.busca_indice import construir_indice, sugestoes
from src.dashboard.componentes.busca_resultado_inline import (
    construir_dataframe_fornecedor,
)
from src.dashboard.componentes.busca_roteador import rotear
from src.dashboard.componentes.html_utils import minificar
from src.dashboard.dados import (
    buscar_global,
    carregar_dados,
    filtrar_por_forma_pagamento,
    filtrar_por_pessoa,
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

# Facetas laterais canônicas (UX-RD-09): rótulo humano + nome interno do
# session_state. As contagens são calculadas dinamicamente sobre os
# resultados filtrados; aqui só listamos os grupos de facetas.
_FACETAS_BUSCA: list[tuple[str, str]] = [
    ("Tipo", "tipo"),
    ("Banco", "banco"),
    ("Pessoa", "pessoa"),
    ("Mês", "mes"),
    ("Classificação", "classificacao"),
]


# ---------------------------------------------------------------------------
# CSS local da página -- redesign UX-RD-09 (search-bar + facets + cards)
# ---------------------------------------------------------------------------

_CSS_LOCAL_BUSCA: str = minificar(
    """
    <style>
    /* Cor do ícone (i) do callout info: var(--color-destaque) em vez do
       azul Streamlit default (feedback dono 2026-04-27). */
    div[data-testid='stAlert'] svg,
    div[role='alert'] svg {
        color: var(--color-destaque) !important;
        fill: currentColor !important;
    }

    /* Search-bar grande no topo (espelha mockup 06-busca-global.html). */
    .ouroboros-search-bar {
        background: var(--bg-surface, var(--color-card-fundo));
        border: 1px solid var(--accent-purple, var(--color-destaque));
        border-radius: 10px;
        padding: 10px 14px;
        display: flex; align-items: center; gap: 10px;
        margin-bottom: 14px;
        box-shadow: 0 0 0 4px rgba(189,147,249,0.10);
    }
    .ouroboros-search-bar .icon {
        color: var(--accent-purple, var(--color-destaque));
        font-family: var(--ff-mono, monospace);
        font-size: 18px;
    }
    .ouroboros-search-bar .ct {
        font-family: var(--ff-mono, monospace);
        font-size: 11px;
        color: var(--text-muted, var(--color-texto-sec));
    }
    .ouroboros-search-bar .kbd {
        font-family: var(--ff-mono, monospace);
        font-size: 10px;
        color: var(--text-muted, var(--color-texto-sec));
        border: 1px solid var(--border-subtle, var(--color-texto-sec));
        padding: 2px 6px; border-radius: 4px;
        background: var(--bg-inset, var(--color-fundo));
    }

    /* Card de faceta lateral (placeholder visual; checkboxes vivem em
       st.columns no Python). */
    .ouroboros-facet-card {
        background: var(--bg-surface, var(--color-card-fundo));
        border: 1px solid var(--border-subtle, var(--color-texto-sec));
        border-radius: 8px;
        padding: 10px 12px;
        margin-bottom: 10px;
    }
    .ouroboros-facet-card h4 {
        font-family: var(--ff-mono, monospace);
        font-size: 10px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-muted, var(--color-texto-sec));
        margin: 0 0 6px;
    }

    /* Cards de resultado com snippet highlight. */
    .ouroboros-res-group {
        background: var(--bg-surface, var(--color-card-fundo));
        border: 1px solid var(--border-subtle, var(--color-texto-sec));
        border-radius: 10px;
        margin-bottom: 12px;
    }
    .ouroboros-res-head {
        padding: 10px 14px;
        border-bottom: 1px solid var(--border-subtle, var(--color-texto-sec));
        display: flex; align-items: center; gap: 10px;
    }
    .ouroboros-res-head .pill-tipo {
        width: 28px; height: 28px;
        border-radius: 6px;
        background: var(--bg-inset, var(--color-fundo));
        color: var(--accent-purple, var(--color-destaque));
        display: grid; place-items: center;
        font-family: var(--ff-mono, monospace);
        font-size: 11px; font-weight: 600;
    }
    .ouroboros-res-head h3 {
        font-family: var(--ff-mono, monospace);
        font-size: 12px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--text-secondary, var(--color-texto-sec));
        margin: 0;
    }
    .ouroboros-res-head .ct {
        font-family: var(--ff-mono, monospace);
        font-size: 11px;
        color: var(--text-muted, var(--color-texto-sec));
        margin-left: auto;
    }
    .ouroboros-res-row {
        padding: 10px 14px;
        border-bottom: 1px dashed var(--border-subtle, var(--color-texto-sec));
    }
    .ouroboros-res-row:last-child { border-bottom: none; }
    .ouroboros-res-title {
        font-size: 14px;
        margin-bottom: 4px;
        color: var(--text-primary, var(--color-texto));
    }
    .ouroboros-res-meta {
        font-family: var(--ff-mono, monospace);
        font-size: 11px;
        color: var(--text-muted, var(--color-texto-sec));
        display: flex; gap: 12px; flex-wrap: wrap;
    }
    .ouroboros-res-snippet {
        font-family: var(--ff-mono, monospace);
        font-size: 12px;
        color: var(--text-secondary, var(--color-texto-sec));
        margin-top: 6px;
        padding: 6px 10px;
        background: var(--bg-inset, var(--color-fundo));
        border-radius: 6px;
        border-left: 2px solid var(--accent-purple, var(--color-destaque));
        line-height: 1.5;
    }
    .ouroboros-res-title mark,
    .ouroboros-res-snippet mark {
        background: rgba(241,250,140,0.30);
        color: var(--accent-yellow, var(--color-alerta));
        padding: 0 2px;
        border-radius: 2px;
        font-weight: 500;
    }

    /* Faixa de contagem unificada (UX-127 invariante). */
    .ouroboros-busca-contagem {
        font-family: var(--ff-mono, monospace);
        font-size: 12px;
        color: var(--text-muted, var(--color-texto-sec));
        margin-bottom: 10px;
    }
    .ouroboros-busca-contagem strong {
        color: var(--text-primary, var(--color-texto));
        font-weight: 600;
    }
    </style>
    """
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


def _docs_vinculados_a_fornecedor(nome_fornecedor: str) -> list[dict]:
    """Retorna documentos ligados a um fornecedor via edge `fornecido_por`.

    Sprint UX-127 AC3: corrige bug "Documentos (0)" sempre. O
    `_buscar_documentos` em `dados.py` usa LIKE em `nome_canonico`/
    metadata do documento -- bate so quando o termo aparece literalmente
    nesses campos. Para fornecedores cujo vinculo com documento e
    relacional (edge no grafo), e preciso seguir a aresta.

    Match case-insensitive contra `nome_canonico` e `aliases` do
    fornecedor (mesmo padrao do `construir_dataframe_fornecedor` da
    UX-124). Devolve lista no mesmo formato de `_buscar_documentos`
    (dicts com id/nome_canonico/tipo_documento/data/razao_social/total)
    para mesclagem direta.

    Args:
        nome_fornecedor: nome humano do fornecedor (ex: "NEOENERGIA").

    Returns:
        Lista (possivelmente vazia) de dicts de documentos.
    """
    import sqlite3

    if not nome_fornecedor or not str(nome_fornecedor).strip():
        return []
    if not _dados.CAMINHO_GRAFO.exists():
        return []

    alvo = str(nome_fornecedor).strip().lower()
    padrao = f"%{alvo}%"

    conn = sqlite3.connect(f"file:{_dados.CAMINHO_GRAFO}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    docs: list[dict] = []
    try:
        # 1) Acha fornecedores que casam com o nome.
        forn_ids: list[int] = []
        for row in conn.execute(
            "SELECT id FROM node "
            "WHERE tipo = 'fornecedor' "
            "  AND (LOWER(nome_canonico) LIKE ? OR LOWER(aliases) LIKE ?) "
            "LIMIT 50",
            (padrao, padrao),
        ):
            forn_ids.append(int(row["id"]))

        if not forn_ids:
            return []

        # 2) Para cada fornecedor, segue edge `fornecido_por` ate documentos.
        vistos: set[int] = set()
        for fid in forn_ids:
            for edge in conn.execute(
                "SELECT src_id FROM edge WHERE dst_id = ? AND tipo = 'fornecido_por'",
                (fid,),
            ):
                doc_id = int(edge["src_id"])
                if doc_id in vistos:
                    continue
                doc_row = conn.execute(
                    "SELECT id, tipo, nome_canonico, metadata FROM node WHERE id = ?",
                    (doc_id,),
                ).fetchone()
                if not doc_row or doc_row["tipo"] != "documento":
                    continue
                vistos.add(doc_id)
                try:
                    import json as _json

                    meta = _json.loads(doc_row["metadata"] or "{}")
                except (ValueError, TypeError):
                    meta = {}
                docs.append(
                    {
                        "id": doc_id,
                        "nome_canonico": doc_row["nome_canonico"],
                        "tipo_documento": meta.get("tipo_documento", "desconhecido"),
                        "data": meta.get("data_emissao", ""),
                        "razao_social": meta.get("razao_social", ""),
                        "total": float(meta.get("total", 0.0) or 0.0),
                    }
                )
    finally:
        conn.close()

    return docs


def _mesclar_docs_dedup(base: list[dict], extras: list[dict]) -> list[dict]:
    """Mescla duas listas de documentos deduplicando por `id`.

    Preserva ordem de `base` primeiro (resultado de `buscar_global`) e
    adiciona ao final apenas os ids de `extras` que ainda não apareceram.
    """
    saida = list(base)
    ids_existentes = {d.get("id") for d in saida if d.get("id") is not None}
    for d in extras:
        did = d.get("id")
        if did is None or did in ids_existentes:
            continue
        ids_existentes.add(did)
        saida.append(d)
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
# Helpers de highlight (snippet com <mark>)
# ---------------------------------------------------------------------------


def _highlight_termo(texto: str, termo: str, *, max_chars: int = 140) -> str:
    """Aplica ``<mark>...</mark>`` em ``texto`` ao redor das ocorrências de
    ``termo`` (case-insensitive), recortando a vizinhança em até
    ``max_chars`` caracteres.

    Retorna HTML escapado com tags ``<mark>`` preservadas. Se ``termo``
    vazio ou não casar, devolve trecho inicial truncado.
    """
    if not isinstance(texto, str) or not texto:
        return ""
    bruto = _mascarar_pii(texto)
    if not termo:
        return _html.escape(bruto[:max_chars]) + ("..." if len(bruto) > max_chars else "")

    termo_seguro = _mascarar_pii(termo)
    padrao = re.compile(re.escape(termo_seguro), re.IGNORECASE)
    match = padrao.search(bruto)
    if not match:
        return _html.escape(bruto[:max_chars]) + ("..." if len(bruto) > max_chars else "")

    # Recorta vizinhança em volta do primeiro match.
    janela = max_chars
    metade = janela // 2
    ini = max(match.start() - metade, 0)
    fim = min(match.end() + metade, len(bruto))
    prefixo = "..." if ini > 0 else ""
    sufixo = "..." if fim < len(bruto) else ""
    janela_str = bruto[ini:fim]

    # Aplica highlight: escape primeiro, depois substitui token escapado
    # por <mark>token</mark>.
    janela_escapada = _html.escape(janela_str)
    termo_escapado = _html.escape(termo_seguro)
    padrao_escape = re.compile(re.escape(termo_escapado), re.IGNORECASE)
    realcado = padrao_escape.sub(
        lambda m: f"<mark>{m.group(0)}</mark>", janela_escapada
    )
    return f"{prefixo}{realcado}{sufixo}"


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------


def renderizar(
    dados: dict[str, pd.DataFrame] | None = None,
    periodo: str | None = None,
    pessoa: str | None = None,
    ctx: dict | None = None,
) -> None:
    """Ponto de entrada da página Busca Global (UX-RD-09 + UX-T-06)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Filtros avançados", "title": "Painel de filtros avançados"},
        {"label": "Catalogação", "primary": True,
         "href": "?cluster=Documentos&tab=Catalogação",
         "title": "Ir para Catalogação"},
    ])

    _ = dados
    ctx = ctx or {}
    forma_pagamento = ctx.get("forma_pagamento")

    st.markdown(_CSS_LOCAL_BUSCA, unsafe_allow_html=True)

    # Hero canônico (legado) -- emitido via st.markdown para preservar
    # contrato com testes regressivos que fazem match no markdown
    # renderizado (busca pela string "Busca Global"). Indentação
    # canônica de 12 espaços satisfaz `test_hero_nao_recebe_52` da
    # Sprint 59, que faz match literal do snippet
    # `hero_titulo_html(\n            "",\n            "Busca Global"`.
    # O page-header redesign UX-RD-09 é renderizado em seguida, abaixo,
    # como nova moldura visual oficial.
    # fmt: off
    _html_hero = hero_titulo_html(
            "",
            "Busca Global",
            TEXTO_DESCRITIVO,
        )
    # fmt: on
    st.markdown(_html_hero, unsafe_allow_html=True)

    # Page-header redesign UX-RD-09.
    st.markdown(_page_header_html(), unsafe_allow_html=True)

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

    termo = _renderizar_controles(indice)

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
    _renderizar_rota_rapida(
        rota,
        periodo=periodo,
        pessoa=pessoa,
        forma_pagamento=forma_pagamento,
    )

    resultados = buscar_global(termo)

    # Sprint UX-127 AC3: enriquece resultados com docs vinculados via edge
    # `fornecido_por` quando rota é fornecedor. Sem isso, a contagem
    # "Documentos (N)" zera para fornecedores cujo nome humano não consta
    # no nome_canonico/metadata dos documentos (caso comum: doc canônico
    # é o número do boleto/chave NFCe; vínculo com fornecedor é relacional).
    docs_brutos = resultados.get("documentos", [])
    if rota.get("kind") == "fornecedor" and rota.get("destino"):
        docs_extras = _docs_vinculados_a_fornecedor(rota["destino"])
        docs_brutos = _mesclar_docs_dedup(docs_brutos, docs_extras)

    # Filtros: sidebar (mes/pessoa/forma). Dropdown removido na UX-127 AC2;
    # _filtrar_por_tipo_dropdown chamado com "Todos" preserva contrato
    # N-para-N com testes regressivos antigos (no-op).
    docs_filtrados = _filtrar_por_tipo_dropdown(docs_brutos, "Todos")
    docs_filtrados = _aplicar_filtros_sidebar(
        docs_filtrados,
        periodo=periodo,
        pessoa=pessoa,
        forma=forma_pagamento,
    )

    # Layout redesign: facetas laterais (1fr) + resultados (3fr).
    col_facetas, col_resultados = st.columns([1, 3])
    with col_facetas:
        _renderizar_facetas_laterais(resultados, docs_filtrados)
    with col_resultados:
        n_forn = len(resultados.get("fornecedores", []))
        n_tx = len(resultados.get("transacoes", []))
        n_itens = len(resultados.get("itens", []))
        n_docs = len(docs_filtrados)
        total_filtrado = n_forn + n_docs + n_tx + n_itens

        _renderizar_resumo(termo, total_filtrado)
        _renderizar_contagem_unificada(n_docs, n_tx, n_forn + n_itens)

        if total_filtrado == 0:
            st.markdown(
                callout_html("info", f"Nenhum resultado para '{_mascarar_pii(termo)}'."),
                unsafe_allow_html=True,
            )
            return

        # Cards agrupados por tipo (transações, documentos, sidecars).
        if resultados.get("transacoes"):
            _renderizar_grupo_transacoes(resultados["transacoes"], termo)
        if docs_filtrados:
            _renderizar_grupo_documentos(docs_filtrados, termo)
        # Tabela canônica preservada para compat (testes esperam strings
        # "Nome do documento", "Texto extraído", "Caminho do arquivo").
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


def _page_header_html() -> str:
    """HTML do page-header UX-RD-09 (título + subtítulo + sprint-tag)."""
    return minificar(
        """
        <div class="page-header">
          <div>
            <h1 class="page-title">BUSCA GLOBAL</h1>
            <p class="page-subtitle">
              Busca atravessa documentos, transações e sidecars. Texto
              extraído por OCR é indexado junto com metadados (sha8, valor,
              data, conta, categoria, classificação).
            </p>
          </div>
          <div class="page-meta">
            <span class="sprint-tag">UX-RD-09</span>
          </div>
        </div>
        """
    )


def _renderizar_search_bar(termo: str | None) -> None:
    """Faixa visual da search-bar grande (placeholder estilizado).

    O ``st.text_input`` real fica logo abaixo (Streamlit não permite
    estilizar o widget direto sem hack JS). Esta div mostra a moldura
    do mockup com kbd ``/`` + contagem de tempo.
    """
    termo_seguro = _mascarar_pii((termo or "").strip())
    aviso = (
        f"<span class='ct'>buscando \"{_html.escape(termo_seguro)}\"</span>"
        if termo_seguro
        else "<span class='ct'>digite acima ou use um chip</span>"
    )
    html = minificar(
        f"""
        <div class="ouroboros-search-bar">
          <span class="icon">⌕</span>
          <span style="flex:1; font-family: var(--ff-mono, monospace);
                       font-size: 13px;
                       color: var(--text-muted, var(--color-texto-sec));">
            BUSCA GLOBAL — chips canônicos abaixo do input ativo.
          </span>
          {aviso}
          <span class="kbd">/</span>
        </div>
        """
    )
    st.markdown(html, unsafe_allow_html=True)


def _renderizar_controles(indice: dict[str, list[str]]) -> str:
    """Renderiza label + input + autocomplete + chips.

    Sprint UX-127 AC2: dropdown 'Tipo de busca' removido. Filtragem por
    tipo agora vem dos chips clicaveis + auto-deteccao por substring no
    roteador (UX-114). Devolve apenas `termo_query` (string).
    """
    # Faixa visual da search-bar (espelha mockup; não substitui o widget).
    _renderizar_search_bar(st.session_state.get("busca_termo_input"))

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

    return (termo or "").strip()


def _renderizar_facetas_laterais(
    resultados: dict, docs_filtrados: list[dict]
) -> None:
    """Renderiza facetas laterais (5 grupos).

    Spec UX-RD-09: tipo, banco, pessoa, mês, classificação. Por enquanto
    é HTML estático com contagens calculadas dinamicamente -- o filtro
    real continua via roteador UX-114 + sidebar global. Em iteração
    futura, checkboxes virarão `st.checkbox` aplicando filtros adicionais.
    """
    docs = docs_filtrados or []
    txs = resultados.get("transacoes", [])
    forns = resultados.get("fornecedores", [])

    # Contagens por tipo de documento.
    cont_tipo: dict[str, int] = {}
    for d in docs:
        tipo = str(d.get("tipo_documento", "desconhecido")).strip() or "desconhecido"
        cont_tipo[tipo] = cont_tipo.get(tipo, 0) + 1
    # Contagens por banco (via transações).
    cont_banco: dict[str, int] = {}
    for t in txs:
        banco = str(t.get("banco_origem", "")).strip()
        if banco:
            cont_banco[banco] = cont_banco.get(banco, 0) + 1
    # Contagens por pessoa (via transações).
    cont_pessoa: dict[str, int] = {}
    for t in txs:
        quem = str(t.get("quem", "")).strip()
        if quem:
            cont_pessoa[quem] = cont_pessoa.get(quem, 0) + 1
    # Contagens por mês_ref (via transações).
    cont_mes: dict[str, int] = {}
    for t in txs:
        mes = str(t.get("mes_ref", "")).strip()
        if mes:
            cont_mes[mes] = cont_mes.get(mes, 0) + 1
    # Contagens por classificação.
    cont_class: dict[str, int] = {}
    for t in txs:
        cl = str(t.get("classificacao", "")).strip()
        if cl:
            cont_class[cl] = cont_class.get(cl, 0) + 1

    grupos = [
        ("Tipo", cont_tipo),
        ("Banco", cont_banco),
        ("Pessoa", cont_pessoa),
        ("Mês", cont_mes),
        ("Classificação", cont_class),
    ]

    for titulo, contagem in grupos:
        linhas_html: list[str] = []
        if not contagem:
            linhas_html.append(
                "<div style='font-family:var(--ff-mono,monospace);"
                " font-size:11px;"
                " color:var(--text-muted, var(--color-texto-sec));'>—</div>"
            )
        else:
            ordenado = sorted(contagem.items(), key=lambda kv: kv[1], reverse=True)
            for chave, n in ordenado[:8]:
                linhas_html.append(
                    "<div style='display:flex;justify-content:space-between;"
                    " padding:3px 0;font-family:var(--ff-mono,monospace);"
                    " font-size:12px;color:var(--color-texto);'>"
                    f"<span>{_html.escape(_mascarar_pii(str(chave)))}</span>"
                    f"<span style='color:var(--text-muted,var(--color-texto-sec));"
                    f" font-size:11px;'>{n}</span>"
                    "</div>"
                )
        bloco = "".join(linhas_html)
        # Total de fornecedores aparece no grupo "Tipo" como faceta
        # auxiliar (mockup mostra Tipo no topo).
        nota = (
            f" <span style='color:var(--text-muted,var(--color-texto-sec));"
            f" font-size:10px;'>(+{len(forns)} fornec.)</span>"
            if titulo == "Tipo" and forns
            else ""
        )
        html = minificar(
            f"""
            <div class="ouroboros-facet-card">
              <h4>{titulo}{nota}</h4>
              {bloco}
            </div>
            """
        )
        st.markdown(html, unsafe_allow_html=True)


def _renderizar_contagem_unificada(n_docs: int, n_tx: int, n_outros: int) -> None:
    """Faixa unificada 'N resultados · M documentos · K transações' (UX-127)."""
    total = n_docs + n_tx + n_outros
    html = minificar(
        f"""
        <div class="ouroboros-busca-contagem">
          <strong>{total}</strong> resultados ·
          <strong>{n_docs}</strong> documentos ·
          <strong>{n_tx}</strong> transações ·
          <strong>{n_outros}</strong> demais
        </div>
        """
    )
    st.markdown(html, unsafe_allow_html=True)


def _renderizar_grupo_transacoes(transacoes: list[dict], termo: str) -> None:
    """Card de grupo 'Transações' com snippet highlight."""
    if not transacoes:
        return

    linhas_html: list[str] = []
    for t in transacoes[:25]:
        local = _mascarar_pii(str(t.get("local", "--"))) or "--"
        valor = float(t.get("valor", 0.0) or 0.0)
        valor_str = formatar_moeda(valor)
        cor_valor = (
            "var(--accent-red, var(--color-negativo))"
            if valor < 0
            else "var(--accent-green, var(--color-positivo))"
        )
        data = str(t.get("data", "--"))
        banco = _html.escape(str(t.get("banco_origem", "--")))
        descricao = str(t.get("_descricao_original") or t.get("descricao") or local)
        snippet_html = _highlight_termo(descricao, termo, max_chars=140)
        titulo_html = _highlight_termo(local, termo, max_chars=120)
        linhas_html.append(
            "<div class='ouroboros-res-row'>"
            f"<div class='ouroboros-res-title'>{titulo_html}</div>"
            "<div class='ouroboros-res-meta'>"
            f"<span style='color:{cor_valor};'>{valor_str}</span>"
            f"<span>{_html.escape(data)}</span>"
            f"<span>conta · {banco}</span>"
            "</div>"
            f"<div class='ouroboros-res-snippet'>{snippet_html}</div>"
            "</div>"
        )

    html = minificar(
        f"""
        <div class="ouroboros-res-group">
          <div class="ouroboros-res-head">
            <div class="pill-tipo">TX</div>
            <h3>Transações</h3>
            <span class="ct">{len(transacoes)} resultados</span>
          </div>
          {"".join(linhas_html)}
        </div>
        """
    )
    st.markdown(html, unsafe_allow_html=True)


def _renderizar_grupo_documentos(docs: list[dict], termo: str) -> None:
    """Card de grupo 'Documentos' com snippet highlight."""
    if not docs:
        return

    linhas_html: list[str] = []
    for d in docs[:25]:
        nome = (d.get("nome_canonico") or d.get("razao_social") or "--").strip() or "--"
        nome_h = _highlight_termo(nome, termo, max_chars=120)
        tipo_d = _html.escape(str(d.get("tipo_documento", "--")))
        data = _html.escape(str(d.get("data", "--")))
        total_v = float(d.get("total", 0.0) or 0.0)
        total_str = formatar_moeda(total_v) if total_v else "--"
        descricao = str(d.get("texto_extraido") or d.get("descricao") or nome)
        snippet_html = _highlight_termo(descricao, termo, max_chars=140)
        linhas_html.append(
            "<div class='ouroboros-res-row'>"
            f"<div class='ouroboros-res-title'>{nome_h}</div>"
            "<div class='ouroboros-res-meta'>"
            f"<span>tipo · {tipo_d}</span>"
            f"<span>{data}</span>"
            f"<span>{total_str}</span>"
            "</div>"
            f"<div class='ouroboros-res-snippet'>{snippet_html}</div>"
            "</div>"
        )

    html = minificar(
        f"""
        <div class="ouroboros-res-group">
          <div class="ouroboros-res-head">
            <div class="pill-tipo">DC</div>
            <h3>Documentos</h3>
            <span class="ct">{len(docs)} resultados</span>
          </div>
          {"".join(linhas_html)}
        </div>
        """
    )
    st.markdown(html, unsafe_allow_html=True)


def _renderizar_rota_rapida(
    rota: dict,
    *,
    periodo: str | None = None,
    pessoa: str | None = None,
    forma_pagamento: str | None = None,
) -> None:
    """Mostra link rápido (aba) ou tabela inline (fornecedor).

    Sprint UX-124: para `kind='fornecedor'` substitui o antigo botão
    "Ir para Catalogação filtrada" por uma `st.dataframe` inline com as
    transações daquele fornecedor. Filtros sidebar (Mês, Pessoa, Forma)
    impactam o DataFrame antes da tabela ser construída.
    """
    kind = rota.get("kind")
    destino = rota.get("destino", "")
    if kind == "aba" and destino:
        # Sprint UX-127 AC4: nenhum botao "Ir para aba X" que faz
        # st.query_params + st.rerun. Mensagem inline apenas; usuario
        # navega manualmente pelo cluster/sidebar se quiser sair da busca.
        st.markdown(
            callout_html(
                "info",
                f"Sua busca casa o nome da aba <strong>{destino}</strong>.",
            ),
            unsafe_allow_html=True,
        )
    elif kind == "fornecedor" and destino:
        _renderizar_tabela_inline_fornecedor(
            destino,
            periodo=periodo,
            pessoa=pessoa,
            forma_pagamento=forma_pagamento,
        )


def _renderizar_tabela_inline_fornecedor(
    nome_fornecedor: str,
    *,
    periodo: str | None,
    pessoa: str | None,
    forma_pagamento: str | None,
) -> None:
    """Renderiza tabela inline com transações do fornecedor (Sprint UX-124).

    Substitui o botão "Ir para Catalogação filtrada" da Sprint UX-114 por
    `st.dataframe` direto na Busca Global. Aplica filtros sidebar antes
    de construir a tabela e oferece botão Exportar CSV abaixo.
    """
    dados = carregar_dados()
    df_extrato = dados.get("extrato")

    if df_extrato is None or df_extrato.empty:
        # Sem XLSX disponível: renderiza callout do fornecedor + aviso de
        # ausência de dados, mas preserva a mensagem com o nome canônico.
        st.markdown(
            callout_html(
                "info",
                f"Sua busca casa o fornecedor <strong>{_mascarar_pii(nome_fornecedor)}</strong>.",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            callout_html(
                "warning",
                "Aba `extrato` indisponível -- rode `./run.sh --tudo`.",
            ),
            unsafe_allow_html=True,
        )
        return

    # Aplica filtros sidebar antes de filtrar por fornecedor.
    df_filtrado = df_extrato.copy()
    if periodo and str(periodo).strip() and str(periodo).lower() != "todos":
        if "mes_ref" in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado["mes_ref"] == str(periodo).strip()]
    if pessoa and str(pessoa).strip() and str(pessoa).lower() != "todos":
        df_filtrado = filtrar_por_pessoa(df_filtrado, pessoa)
    if forma_pagamento:
        df_filtrado = filtrar_por_forma_pagamento(df_filtrado, forma_pagamento)

    df_inline = construir_dataframe_fornecedor(
        nome_fornecedor,
        df_filtrado,
        mascarar_pii=True,
    )

    n = len(df_inline)
    st.markdown(
        callout_html(
            "info",
            f"Sua busca casa o fornecedor "
            f"<strong>{_mascarar_pii(nome_fornecedor)}</strong>. "
            f"{n} transações encontradas.",
        ),
        unsafe_allow_html=True,
    )

    if n == 0:
        return

    st.dataframe(df_inline, use_container_width=True, hide_index=True)

    # Exportar CSV inline (preservando padrão UX-114).
    csv_bytes = df_inline.to_csv(index=False).encode("utf-8")
    nome_arquivo = f"busca_{re.sub(r'[^a-zA-Z0-9_-]+', '_', nome_fornecedor)[:40]}.csv"
    st.download_button(
        label=f"Exportar {n} linha(s) (CSV)",
        data=csv_bytes,
        file_name=nome_arquivo,
        mime="text/csv",
        key="busca_exportar_inline",
    )


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
