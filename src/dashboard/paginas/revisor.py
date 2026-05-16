"""Página Revisor Visual Semi-Automatizado — Sprint D2 + redesign UX-RD-10.

Reescrita do redesign UX-RD-10 a partir do mockup
``novo-mockup/mockups/09-revisor.html``. Preserva integralmente:

  * Schema SQLite ``revisao(item_id, dimensao, ok, observacao, ts,
    valor_etl, valor_opus, valor_grafo_real)`` (Sprint D2 + 103 + AUDIT2-*).
  * Auditoria 4-way ETL × Opus × Grafo × Humano (Sprint D2 + AUDIT2-*).
  * Função ``listar_pendencias_revisao()``, ``salvar_marcacao()`` e demais
    re-exports do ``revisor_logic`` (testes importam direto pelo módulo).
  * Botões "Gerar relatório", "Sugerir patch", "Exportar ground-truth CSV".

Mudanças de UX (UX-RD-10):

  * ``page-header`` "REVISOR" + ``sprint-tag UX-RD-10`` + pill com contagem
    de pendências.
  * Cada pendência vira um **card** com ``data-revisor-card`` (ancorado por
    JS dos atalhos j/k/a/r) e bloco "fontes" com 4 colunas semânticas:
    ETL (verde) | Opus (roxo) | Grafo (amarelo) | Humano (rosa). Cada
    coluna tem ``border-left`` colorida que marca a origem.
  * Atalhos de teclado j/k/a/r via ``componentes/atalhos_revisor.py``.
  * Botões aprovar/rejeitar emitem ``data-revisor-aprovar`` /
    ``data-revisor-rejeitar`` para que o JS clique programaticamente.

Decisão sobre 4 vs 5 colunas (proof-of-work UX-RD-10): mantemos as 4 fontes
de verdade (ETL/Opus/Grafo/Humano). O **OFX original** (preview do arquivo
de origem) ocupa o painel "Original" lateral, não compete espaço com as 4
colunas semânticas — preserva valor da Sprint D2 (Grafo é a fonte de
verdade dedup) sem quebrar o layout em monitores 1366×768.

Princípios preservados:
  * Read-only em ``data/raw/`` (revisor não move/deleta arquivos).
  * SQLite (não JSON/YAML) para alinhamento com ``grafo.sqlite``.
  * PII mascarada antes de gravar relatório (regex CPF/CNPJ).
  * ``revisor_*`` é o namespace de session_state.
  * Paginação 10 itens por vez (volume real de 760 PDFs esgotaria browser).
"""

from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from src.dashboard.componentes.atalhos_revisor import gerar_html_atalhos_revisor
from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.preview_documento import preview_documento
from src.dashboard.componentes.ui import (
    callout_html,
    carregar_css_pagina,
    subtitulo_secao_html,
)
from src.dashboard.dados import (
    CAMINHO_REVISAO_HUMANA,
    listar_pendencias_revisao,
)
from src.dashboard.dados_extracao_tripla import carregar_extracoes_triplas

# Dimensões canônicas que o supervisor avalia. A ordem reflete a importância
# percebida durante a auditoria 2026-04-26 (data e valor têm impacto direto
# no XLSX; itens/fornecedor/pessoa são metadados secundários).
DIMENSOES_CANONICAS: tuple[str, ...] = (
    "data",
    "valor",
    "itens",
    "fornecedor",
    "pessoa",
)

# Estados de marcação por dimensão.
ESTADO_OK: int = 1
ESTADO_ERRO: int = 0
ESTADO_NA: None = None

ROTULOS_ESTADO: dict[str, int | None] = {
    "OK": ESTADO_OK,
    "Erro": ESTADO_ERRO,
    "Não-aplicável": ESTADO_NA,
}

# Limite de paginação evita carregar 760 PDFs no navegador.
ITENS_POR_PAGINA: int = 10

# Sprint ANTI-MIGUE-08: logica pura extraida para revisor_logic.py.
# Re-export local preserva contratos importados por testes
# (``from src.dashboard.paginas.revisor import garantir_schema, ...``).
from src.dashboard.paginas.revisor_logic import (  # noqa: E402, F401
    _HEADER_GROUND_TRUTH_CSV,
    _REGEX_CNPJ,
    _REGEX_CNPJ_CRU,
    _REGEX_CPF,
    _REGEX_CPF_CRU,
    LIMITE_PADRAO_RECORRENTE,
    _comparar_canonico,
    _taxa_fidelidade,
    carregar_marcacoes,
    detectar_padroes_recorrentes,
    extrair_valor_etl_para_dimensao,
    garantir_schema,
    gerar_ground_truth_csv,
    gerar_relatorio_markdown,
    gravar_relatorio,
    mascarar_pii,
    salvar_marcacao,
    sugerir_patch_yaml,
)


def _page_header_html(total: int, revisados: int, taxa: float) -> str:
    """HTML do page-header UX-RD-10 (título + sprint-tag + pill pendências)."""
    aguardando = max(0, total - revisados)
    if aguardando == 0:
        pill_classe = "pill-d7-graduado"
        pill_texto = "0 pendências"
    elif aguardando <= 10:
        pill_classe = "pill-d7-calibracao"
        pill_texto = f"{aguardando} pendências"
    else:
        pill_classe = "pill-d7-regredindo"
        pill_texto = f"{aguardando} pendências"
    return minificar(
        f"""
        <div class="page-header">
          <div>
            <h1 class="page-title">REVISOR</h1>
            <p class="page-subtitle">
              Validação semi-automatizada com auditoria 4-way
              (ETL &times; Opus &times; Grafo &times; Humano). Cards
              comparam fontes lado-a-lado; atalhos
              <kbd class="kbd">j</kbd>/<kbd class="kbd">k</kbd> navegam,
              <kbd class="kbd">a</kbd>/<kbd class="kbd">r</kbd>
              aprovam/rejeitam o card focado.
            </p>
          </div>
          <div class="page-meta">
            <span class="sprint-tag">UX-RD-10</span>
            <span class="pill {pill_classe}">{pill_texto}</span>
            <span class="pill pill-humano-aprovado">fidelidade {taxa * 100:.0f}%</span>
          </div>
        </div>
        """
    )


def _bloco_fontes_html(
    valor_etl: str,
    valor_opus: str,
    valor_grafo: str,
    valor_humano_label: str,
    div_etl_opus: bool,
    div_etl_grafo: bool,
    div_grafo_opus: bool,
) -> str:
    """HTML do bloco 4-fontes (ETL | Opus | Grafo | Humano).

    Cada coluna tem ``border-left`` colorida (verde/roxo/amarelo/rosa) e
    classe ``revisor-fonte-valor.diverge`` quando há divergência ativa.
    """

    def _renderizar(valor: str, classe_extra: str, rotulo: str, diverge: bool) -> str:
        valor_render = valor if valor else "—"
        if len(valor_render) > 80:
            valor_render = valor_render[:77] + "..."
        cls = "revisor-fonte-valor"
        if diverge:
            cls += " diverge"
        return (
            f'<div class="revisor-fonte {classe_extra}">'
            f'<div class="revisor-fonte-rotulo">{rotulo}</div>'
            f'<div class="{cls}">{valor_render}</div>'
            "</div>"
        )

    return minificar(
        f"""
        <div class="revisor-card-fontes">
          {_renderizar(valor_etl, "revisor-fonte-etl", "ETL", div_etl_opus or div_etl_grafo)}
          {_renderizar(valor_opus, "revisor-fonte-opus", "Opus", div_etl_opus or div_grafo_opus)}
          {_renderizar(valor_grafo, "revisor-fonte-grafo", "Grafo",
                       div_etl_grafo or div_grafo_opus)}
          {_renderizar(valor_humano_label, "revisor-fonte-humano", "Humano", False)}
        </div>
        """
    )


def _renderizar_painel_item(pendencia: dict, marcacoes_item: list[dict]) -> dict[str, Any]:
    """Renderiza painel de uma pendência e devolve marcações coletadas.

    Retorna dict ``{dimensao: (estado_int_ou_none, observacao_str, valor_etl,
    valor_grafo)}``. Não persiste em disco — caller decide quando chamar
    ``salvar_marcacao``.
    """
    item_id = pendencia["item_id"]
    caminho_str = pendencia.get("caminho", "")
    metadata = pendencia.get("metadata", {})

    col_esq, col_dir = st.columns([3, 2])

    with col_esq:
        st.markdown(subtitulo_secao_html("Original"), unsafe_allow_html=True)
        if caminho_str:
            caminho = Path(caminho_str)
            if not caminho.exists():
                st.markdown(
                    callout_html(
                        "warning",
                        f"Arquivo original ausente: `{caminho.name}`",
                    ),
                    unsafe_allow_html=True,
                )
            elif caminho.is_dir():
                # Pendências em data/raw/_conferir/ podem ser diretórios
                # com fallback de supervisor (várias fotos + proposta MD).
                # Lista o conteúdo em vez de tentar preview de arquivo único.
                st.markdown(
                    callout_html(
                        "info",
                        f"Pendência é um diretório com fallback de "
                        f"supervisor: `{caminho.name}`",
                    ),
                    unsafe_allow_html=True,
                )
                arquivos = sorted(p for p in caminho.iterdir() if p.is_file())
                if arquivos:
                    primeira_imagem = next(
                        (
                            p
                            for p in arquivos
                            if p.suffix.lower()
                            in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
                        ),
                        None,
                    )
                    if primeira_imagem is not None:
                        preview_documento(primeira_imagem, altura=460)
                    st.caption(
                        "Conteúdo do diretório: "
                        + ", ".join(p.name for p in arquivos[:8])
                        + ("..." if len(arquivos) > 8 else "")
                    )
                else:
                    st.caption("Diretório vazio.")
            else:
                preview_documento(caminho, altura=520)
        else:
            st.markdown(
                callout_html(
                    "info",
                    "Pendência sem caminho de arquivo (somente node do grafo).",
                ),
                unsafe_allow_html=True,
            )

    with col_dir:
        st.markdown(subtitulo_secao_html("Extraído"), unsafe_allow_html=True)
        # Metadata serializada -- não tem PII via design (já passou pelo mask
        # do extrator), mas mascaramos defensivamente para st.code render.
        meta_render = mascarar_pii(json.dumps(metadata, indent=2, ensure_ascii=False))
        st.code(meta_render, language="json")
        st.caption(f"item_id: `{item_id[:60]}{'…' if len(item_id) > 60 else ''}`")
        st.caption(f"tipo: `{pendencia.get('tipo', '?')}`")

    st.markdown("---")
    st.markdown(
        subtitulo_secao_html("Avaliação por dimensão"),
        unsafe_allow_html=True,
    )

    estados_existentes: dict[str, dict] = {m["dimensao"]: m for m in marcacoes_item}
    coletadas: dict[str, tuple[int | None, str, str, str]] = {}

    for dimensao in DIMENSOES_CANONICAS:
        # Auditoria 4-way (sessão 2026-04-29): 4 fontes (ETL/Opus/Grafo/Humano).
        valor_etl = extrair_valor_etl_para_dimensao(pendencia, dimensao)
        valor_opus = estados_existentes.get(dimensao, {}).get("valor_opus") or ""
        valor_grafo = estados_existentes.get(dimensao, {}).get("valor_grafo_real") or ""

        # Comparacao canonica (case-insensitive, sem espacos).
        div_etl_grafo = _comparar_canonico(valor_etl, valor_grafo)  # Tipo B
        div_etl_opus = _comparar_canonico(valor_etl, valor_opus)  # Tipo A
        div_grafo_opus = _comparar_canonico(valor_grafo, valor_opus)  # Tipo A pos-norm

        # Estado humano existente (para indicar default do radio + label).
        valor_humano_existente = estados_existentes.get(dimensao, {}).get("ok")
        if valor_humano_existente == 1:
            valor_humano_label = "OK (humano)"
        elif valor_humano_existente == 0:
            valor_humano_label = "Erro (humano)"
        else:
            valor_humano_label = "—"

        # Card por dimensão com bloco 4-fontes.
        card_titulo = minificar(
            f"""
            <div class="revisor-card-titulo">
              <span class="revisor-card-dimensao">{dimensao}</span>
              <span>4-way</span>
            </div>
            """
        )
        bloco_fontes = _bloco_fontes_html(
            valor_etl,
            valor_opus,
            valor_grafo,
            valor_humano_label,
            div_etl_opus,
            div_etl_grafo,
            div_grafo_opus,
        )
        st.markdown(card_titulo + bloco_fontes, unsafe_allow_html=True)

        col_radio, col_obs = st.columns([1, 2])
        with col_radio:
            obs_existente = (
                estados_existentes.get(dimensao, {}).get("observacao") or ""
            )
            indice_default = 2  # Não-aplicável
            if valor_humano_existente == 1:
                indice_default = 0
            elif valor_humano_existente == 0:
                indice_default = 1
            rotulo = st.radio(
                f"Estado {dimensao}",
                list(ROTULOS_ESTADO.keys()),
                index=indice_default,
                key=f"revisor_estado_{item_id}_{dimensao}",
                label_visibility="collapsed",
                horizontal=True,
            )
        with col_obs:
            obs = st.text_input(
                f"Observação {dimensao}",
                value=obs_existente,
                key=f"revisor_obs_{item_id}_{dimensao}",
                label_visibility="collapsed",
                placeholder="observação opcional",
            )
        coletadas[dimensao] = (ROTULOS_ESTADO[rotulo], obs, valor_etl, valor_grafo)

    return coletadas


def _gravar_decisao_global(
    item_id: str,
    coletadas: dict[str, tuple[int | None, str, str, str]],
    decisao: int | None,
    observacao_global: str,
) -> None:
    """Grava uma decisão global (aprovar/rejeitar) replicando-a nas dimensões.

    ``a`` (aprovar) -> grava ``ok=1`` em todas as dimensões cujo estado humano
    ainda está "Não-aplicável"; preserva marcações já confirmadas.
    ``r`` (rejeitar) -> mesmo, com ``ok=0``.

    A observação global vai junto de cada gravação (anexada à observação
    livre se já existe).
    """
    for dimensao, (estado_radio, obs, valor_etl, valor_grafo) in coletadas.items():
        # Preserva o que o humano já marcou explicitamente (OK ou Erro).
        # Só sobrescreve quando estava em "Não-aplicável" (None).
        estado_final = estado_radio if estado_radio is not None else decisao
        obs_final = obs
        if observacao_global:
            obs_final = (
                f"{obs} | {observacao_global}".strip(" |")
                if obs
                else observacao_global
            )
        salvar_marcacao(
            CAMINHO_REVISAO_HUMANA,
            item_id,
            dimensao,
            estado_final,
            obs_final,
            valor_etl=valor_etl,
            valor_grafo_real=valor_grafo,
        )


# ---------------------------------------------------------------------------
# Sprint UX-V-4 -- Layout 4-way canônico (mockup 09-revisor.html)
#
# A reescrita visual coexiste com o painel legado de pendências (Sprint D2):
# o 4-way fica no topo, lendo o schema canônico ``extracao_tripla.json``
# (via ``dados_extracao_tripla``); o painel legado preserva todos os widgets
# e contratos testados (multiselect 'Tipo de pendência', number_input
# 'Página', re-exports do revisor_logic, atalhos j/k/a/r). Padrão (o):
# subregra retrocompatível.
# ---------------------------------------------------------------------------

# Filtros canônicos das tabs do topo.
TABS_FILTRO_CANONICAS: tuple[str, ...] = (
    "Mês atual",
    "Só divergentes",
    "Só rascunhos",
    "Apurado",
)

# Tabs do rodapé.
TABS_RODAPE_CANONICAS: tuple[str, ...] = (
    "Detalhes",
    "Auditoria do Opus",
    "Histórico",
    "Hints",
)


def _registro_para_transacao(registro: dict[str, Any]) -> dict[str, Any]:  # noqa: accent
    """Converte um registro do schema canônico em uma transação para a lista.

    Cada registro do JSON canônico vira uma linha da lista lateral. O
    estado (``apurado`` / ``rascunho`` / ``divergente``) é inferido a partir
    da divergência ETL × Opus (padrão usado pela aba Validação Tripla).

    Args:
        registro: dict com chaves ``sha256``, ``filename``, ``tipo``,
            ``etl``, ``opus``, ``humano``.

    Returns:
        Dict com chaves ``id``, ``sha8``, ``descricao``, ``valor_str``,  # noqa: accent
        ``data``, ``estado``, ``confianca``.
    """
    sha256 = str(registro.get("sha256") or "")
    filename = str(registro.get("filename") or "")
    etl_campos = (registro.get("etl") or {}).get("campos") or {}
    opus_campos = (registro.get("opus") or {}).get("campos") or {}
    humano_bloco = registro.get("humano") or {}

    descricao = ""
    for campo_desc in ("descricao", "razao_social", "fornecedor"):
        if campo_desc in etl_campos and etl_campos[campo_desc]:
            descricao = str(etl_campos[campo_desc][0] or "")
        elif campo_desc in opus_campos and opus_campos[campo_desc]:
            descricao = str(opus_campos[campo_desc][0] or "")
        if descricao:
            break
    if not descricao:
        descricao = filename

    valor_str = ""
    for campo_v in ("valor", "total"):
        if campo_v in etl_campos and etl_campos[campo_v]:
            valor_str = f"R$ {etl_campos[campo_v][0]}"
            break
        if campo_v in opus_campos and opus_campos[campo_v]:
            valor_str = f"R$ {opus_campos[campo_v][0]}"
            break

    data_str = ""
    for campo_d in ("data", "data_emissao", "data_pagamento"):
        if campo_d in etl_campos and etl_campos[campo_d]:
            data_str = str(etl_campos[campo_d][0] or "")
            break
        if campo_d in opus_campos and opus_campos[campo_d]:
            data_str = str(opus_campos[campo_d][0] or "")
            break

    chaves_comuns = set(etl_campos.keys()) & set(opus_campos.keys())
    div = 0
    confianca_total = 0.0
    for k in chaves_comuns:
        v_etl = etl_campos[k][0] if etl_campos[k] else ""
        v_opus = opus_campos[k][0] if opus_campos[k] else ""
        if v_etl and v_opus and v_etl != v_opus:
            div += 1
    for k in opus_campos:
        try:
            confianca_total += float(opus_campos[k][1])
        except (TypeError, ValueError, IndexError):
            pass  # noqa: BLE001 -- confianca opus campo malformado; soma o que conseguir
    confianca = confianca_total / max(1, len(opus_campos))

    if humano_bloco.get("validado_em"):
        estado = "apurado"
    elif div > 0:
        estado = "divergente"
    else:
        estado = "rascunho"

    return {
        "id": sha256[:8] or "—",
        "sha8": sha256[:8],
        "descricao": descricao,
        "valor_str": valor_str,
        "data": data_str,
        "estado": estado,
        "confianca": confianca,
        "filename": filename,
        "registro": registro,
    }


def _filtrar_transacoes(
    transacoes: list[dict[str, Any]],
    filtro: str,
) -> list[dict[str, Any]]:
    """Aplica o filtro selecionado na tab do topo.

    ``Mês atual`` devolve tudo (sem filtro temporal -- implementação stub).
    Os outros filtros usam o campo ``estado`` da transação.
    """
    if filtro == "Só divergentes":
        return [t for t in transacoes if t["estado"] == "divergente"]
    if filtro == "Só rascunhos":
        return [t for t in transacoes if t["estado"] == "rascunho"]
    if filtro == "Apurado":
        return [t for t in transacoes if t["estado"] == "apurado"]
    return list(transacoes)


def _tabs_filtro_html(filtro_ativo: str) -> str:
    """HTML das tabs filtro do topo da lista (Mês atual / Só divergentes / etc)."""
    tabs = "".join(
        f'<span class="tab{" active" if t == filtro_ativo else ""}">{escape(t)}</span>'
        for t in TABS_FILTRO_CANONICAS
    )
    return f'<div class="revisor-tabs-filtro">{tabs}</div>'


def _estado_pill_html(estado: str) -> str:
    """HTML da pílula de estado (APURADO/DIVERGENTE/RASCUNHO)."""
    classe = estado if estado in {"apurado", "divergente", "rascunho"} else "rascunho"
    return f'<span class="revisor-estado-pill {classe}">{classe}</span>'


def _transacao_row_html(  # noqa: accent
    transacao: dict[str, Any], selecionada: bool  # noqa: accent
) -> str:
    """HTML de uma linha da lista lateral de transações."""
    cls_sel = " sel" if selecionada else ""
    valor = transacao.get("valor_str") or "—"
    cls_val = "neg" if valor.lstrip("R$ ").startswith("-") else "pos"
    conf_txt = f"{transacao.get('confianca', 0.0) * 100:.0f}%"
    sha_attr = escape(transacao.get("sha8") or "")
    data_attr = escape(transacao.get("data") or "—")
    desc_attr = escape(transacao.get("descricao") or "")
    estado_attr = transacao.get("estado") or "rascunho"
    valor_attr = escape(valor)
    return minificar(
        f'<div class="revisor-t-row{cls_sel}" data-sha8="{sha_attr}">'
        f'<span class="data">{data_attr}</span>'
        f"{_estado_pill_html(estado_attr)}"
        f'<span class="desc" title="{desc_attr}">{desc_attr}</span>'
        f'<span class="val {cls_val}">{valor_attr}</span>'
        f'<span class="conf">{conf_txt}</span>'
        "</div>"
    )


def _campos_card_html(
    campos: dict[str, Any], destacar_diff: tuple[str, ...] = ()
) -> str:
    """Renderiza dict de campos do schema (chave -> [valor, conf]) como linhas."""
    if not campos:
        return (
            '<div class="revisor-field"><span class="k">—</span>'
            '<span class="v miss">vazio</span></div>'
        )
    linhas: list[str] = []
    for k in sorted(campos.keys()):
        par = campos[k] or ["", 0.0]
        valor = str(par[0] if len(par) > 0 else "")
        cls = ""
        if k in destacar_diff:
            cls = "diff"
        elif not valor:
            cls = "miss"
        valor_render = valor if valor else "— vazio —"
        linhas.append(
            f'<div class="revisor-field"><span class="k">{escape(k)}</span>'
            f'<span class="v {cls}">{escape(valor_render)}</span></div>'
        )
    return "".join(linhas)


def _humano_inputs_html(
    humano_campos: dict[str, str], campos_referencia: list[str]
) -> str:
    """HTML que exibe campos do humano (placeholder UX-V-4 sem persistência)."""
    if not campos_referencia:
        return (
            '<div class="revisor-field"><span class="k">—</span>'
            '<span class="v miss">sem referência</span></div>'
        )
    linhas: list[str] = []
    for k in campos_referencia:
        valor = str(humano_campos.get(k) or "")
        valor_render = valor if valor else "(aguardando humano)"
        cls = "" if valor else "miss"
        linhas.append(
            f'<div class="revisor-field"><span class="k">{escape(k)}</span>'
            f'<span class="v {cls}">{escape(valor_render)}</span></div>'
        )
    return "".join(linhas)


def _renderizar_4way_card(
    classe_col: str,
    titulo: str,
    fonte: str,
    corpo_html: str,
    rodape_acao_texto: str,
) -> str:
    """HTML de um card 4-way (OFX/Rascunho/Opus/Humano)."""
    return minificar(
        f'<div class="revisor-fw-card revisor-col-{classe_col}">'
        '<div class="fw-head">'
        f'<div><div class="ttl">{escape(titulo)}</div>'
        f'<div class="src">{escape(fonte)}</div></div>'
        "</div>"
        f'<div class="fw-body">{corpo_html}</div>'
        f'<div class="fw-action-row">{escape(rodape_acao_texto)}</div>'
        "</div>"
    )


def _campos_divergentes(registro: dict[str, Any]) -> tuple[str, ...]:
    """Devolve tuple de campos onde ETL e Opus discordam (ambos não-vazios)."""
    etl_campos = (registro.get("etl") or {}).get("campos") or {}
    opus_campos = (registro.get("opus") or {}).get("campos") or {}
    div: list[str] = []
    for k in set(etl_campos.keys()) & set(opus_campos.keys()):
        v_etl = etl_campos[k][0] if etl_campos[k] else ""
        v_opus = opus_campos[k][0] if opus_campos[k] else ""
        if v_etl and v_opus and v_etl != v_opus:
            div.append(k)
    return tuple(sorted(div))


def _trace_raciocinio_html(registro: dict[str, Any]) -> str:
    """Constrói trace de raciocínio quando há divergências.

    Sem chamada ao Opus em runtime (não-objetivo). Usa heurísticas locais
    para narrar passos a partir do diff ETL × Opus.
    """
    div = _campos_divergentes(registro)
    if not div:
        return (
            '<div class="revisor-trace-corpo">'
            "<div>Sem divergências entre ETL e Opus para este registro.</div>"
            "<div>Apuração imediata recomendada.</div>"
            "</div>"
        )
    etl_campos = (registro.get("etl") or {}).get("campos") or {}
    opus_campos = (registro.get("opus") or {}).get("campos") or {}
    sha8 = str(registro.get("sha256") or "")[:8]
    linhas: list[str] = [
        f"<div>1. Identifiquei {len(div)} campo(s) divergente(s) no registro "
        f'<span class="destaque-roxo">{escape(sha8)}</span>.</div>',
    ]
    for idx, campo in enumerate(div[:3], start=2):
        v_etl = etl_campos[campo][0] if etl_campos.get(campo) else ""
        v_opus = opus_campos[campo][0] if opus_campos.get(campo) else ""
        linhas.append(
            f'<div>{idx}. Campo <span class="destaque-roxo">{escape(campo)}</span>: '
            f'ETL=<span class="destaque-amarelo">{escape(str(v_etl))}</span> '
            f'vs Opus=<span class="destaque-amarelo">{escape(str(v_opus))}</span>.</div>'
        )
    linhas.append(
        "<div>Hipótese: divergência aritmética ou de formato. "
        "Revisor humano deve apurar.</div>"
    )
    return f'<div class="revisor-trace-corpo">{"".join(linhas)}</div>'


def _arquivos_consultados_html(registro: dict[str, Any]) -> str:
    """Card de arquivos consultados pelo Opus para o registro selecionado."""
    sha8 = str(registro.get("sha256") or "")[:8]
    filename = str(registro.get("filename") or "—")
    return (
        f'<div class="revisor-arquivo-card">'
        f'<span class="arquivo-nome">{escape(filename)}</span>'
        f'<span class="arquivo-sha">{escape(sha8)}</span>'
        "</div>"
    )


def _proximas_acoes_html(registro: dict[str, Any]) -> str:
    """Sugestões de próximas ações com base na presença de divergências."""
    div = _campos_divergentes(registro)
    if div:
        itens = [
            "Confirmar valor com o documento original",
            f"Reprocessar com hint específico para {div[0]}",
            "Marcar como apurada após validação",
        ]
    else:
        itens = [
            "Aceitar proposta Opus",
            "Confirmar com extrato bancário",
            "Apurar transação",  # noqa: accent
        ]
    lis = "".join(f"<li>{escape(i)}</li>" for i in itens)
    return f'<ul class="revisor-proximas-acoes">{lis}</ul>'


def _renderizar_layout_4way(registros: list[dict[str, Any]]) -> None:
    """Renderiza a arquitetura 4-way (Sprint UX-V-4).

    Quando o schema ``extracao_tripla.json`` não tem registros, mostra um
    aviso amistoso e cai para o painel legado. A função NÃO levanta exceção
    quando o JSON está ausente (graceful fallback ADR-10).
    """
    st.markdown(
        subtitulo_secao_html("Apuração 4-way (OFX × Rascunho × Opus × Humano)"),
        unsafe_allow_html=True,
    )

    if not registros:
        st.markdown(
            '<div class="revisor-fourway-vazio">'
            "Sem registros canônicos em <code>extracao_tripla.json</code>. "
            "Rode <code>python scripts/popular_extracao_tripla.py</code> para "
            "alimentar a arquitetura 4-way."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    transacoes = [_registro_para_transacao(r) for r in registros]
    tabs_filtro = st.tabs(list(TABS_FILTRO_CANONICAS))

    for idx_tab, nome_tab in enumerate(TABS_FILTRO_CANONICAS):
        with tabs_filtro[idx_tab]:
            transacoes_filtradas = _filtrar_transacoes(transacoes, nome_tab)
            if not transacoes_filtradas:
                st.markdown(
                    f'<div class="revisor-fourway-vazio">'
                    f"Nenhuma transação no filtro <strong>"
                    f"{escape(nome_tab)}</strong>."
                    "</div>",  # noqa: accent
                    unsafe_allow_html=True,
                )
                continue

            col_lista, col_centro = st.columns([1, 3])

            with col_lista:
                rows_html = "".join(
                    _transacao_row_html(t, selecionada=(i == 0))
                    for i, t in enumerate(transacoes_filtradas)
                )
                rodape_total = len(transacoes_filtradas)
                lista_html = (
                    '<div class="revisor-tx-list">'
                    f"{_tabs_filtro_html(nome_tab)}"
                    f'<div style="overflow:auto; flex:1;">{rows_html}</div>'
                    '<div class="revisor-list-rodape">'
                    f"<span>{rodape_total} transação(ões)</span>"
                    f"<span>filtro: <strong>{escape(nome_tab)}</strong></span>"
                    "</div>"
                    "</div>"
                )
                st.markdown(minificar(lista_html), unsafe_allow_html=True)

            with col_centro:
                opcoes_select = [
                    f"{t.get('sha8') or '—'} · "
                    f"{t.get('descricao') or '(sem descrição)'}"
                    for t in transacoes_filtradas
                ]
                idx_selecionada = st.selectbox(
                    "Transação inspecionada",  # noqa: accent
                    range(len(opcoes_select)),
                    format_func=lambda i: opcoes_select[i],
                    key=f"revisor_4way_selecao_{nome_tab}",
                )
                transacao = transacoes_filtradas[idx_selecionada]
                registro = transacao["registro"]

                header_html = (
                    '<div class="revisor-fourway-header">'
                    "<div>"
                    '<div class="selecao-rotulo">transação selecionada</div>'  # noqa: accent
                    '<div class="selecao-titulo">'
                    f"{escape(transacao.get('sha8') or '—')} · "
                    f"{escape(transacao.get('data') or '—')} · "
                    f"{escape(transacao.get('descricao') or '—')}"
                    "</div>"
                    "</div>"
                    f"{_estado_pill_html(transacao.get('estado') or 'rascunho')}"
                    '<span class="revisor-estado-pill" '
                    'style="color:var(--text-muted);'
                    'border-color:var(--border-subtle);text-transform:none;">'
                    f"sha8 {escape(transacao.get('sha8') or '—')}"
                    "</span>"
                    "</div>"
                )
                st.markdown(minificar(header_html), unsafe_allow_html=True)

                divergentes = _campos_divergentes(registro)
                etl_campos = (registro.get("etl") or {}).get("campos") or {}
                opus_campos = (registro.get("opus") or {}).get("campos") or {}
                humano_campos = (registro.get("humano") or {}).get("campos") or {}
                ofx_corpo = _campos_card_html(etl_campos, destacar_diff=())
                rascunho_corpo = _campos_card_html(
                    etl_campos, destacar_diff=divergentes
                )
                opus_corpo = _campos_card_html(
                    opus_campos, destacar_diff=divergentes
                )
                campos_referencia = sorted(
                    set(etl_campos.keys()) | set(opus_campos.keys())
                )
                humano_corpo = _humano_inputs_html(humano_campos, campos_referencia)

                etl_versao = (
                    (registro.get("etl") or {}).get("extractor_versao") or "—"
                )
                opus_versao = (registro.get("opus") or {}).get("versao") or "—"

                cards_html = (
                    '<div class="revisor-fourway">'
                    + _renderizar_4way_card(
                        "ofx",
                        "OFX",
                        "banco · imutável",
                        ofx_corpo,
                        "read-only · banco",
                    )
                    + _renderizar_4way_card(
                        "rascunho",
                        "Rascunho ETL",
                        f"extractor · {etl_versao}",
                        rascunho_corpo,
                        "usar como ponto de partida",
                    )
                    + _renderizar_4way_card(
                        "opus",
                        "Opus",
                        f"agentic · {opus_versao}",
                        opus_corpo,
                        "Aceitar como humano · Re-gerar c/ hint",
                    )
                    + _renderizar_4way_card(
                        "humano",
                        "Humano",
                        "aguardando você",
                        humano_corpo,
                        "Apurar transação · Marcar para revisar depois",  # noqa: accent
                    )
                    + "</div>"
                )
                st.markdown(cards_html, unsafe_allow_html=True)

                tabs_rodape = "".join(
                    f'<span class="tab'
                    f'{" active" if t == "Auditoria do Opus" else ""}">'
                    f"{escape(t)}</span>"
                    for t in TABS_RODAPE_CANONICAS
                )
                rodape_html = (
                    '<div class="revisor-rodape">'
                    f'<div class="revisor-rodape-tabs">{tabs_rodape}</div>'
                    '<div class="revisor-rodape-corpo">'
                    "<div>"
                    '<div class="revisor-trace-titulo">trace de raciocínio</div>'
                    f"{_trace_raciocinio_html(registro)}"
                    "</div>"
                    "<div>"
                    '<div class="revisor-trace-titulo">arquivos consultados</div>'
                    f"{_arquivos_consultados_html(registro)}"
                    '<div class="revisor-trace-titulo" '
                    'style="margin-top: 12px;">próximas ações sugeridas</div>'
                    f"{_proximas_acoes_html(registro)}"
                    "</div>"
                    "</div>"
                    "</div>"
                )
                st.markdown(minificar(rodape_html), unsafe_allow_html=True)


def renderizar(
    dados: dict | None = None,
    periodo: str | None = None,
    pessoa: str | None = None,
    ctx: dict | None = None,
) -> None:
    """Ponto de entrada da página Revisor (UX-T-09 + UX-V-4)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Próxima divergência", "glyph": "diff",
         "title": "Pular para próxima divergência"},
        {"label": "Aprovar Opus & avançar", "primary": True, "glyph": "validar",
         "title": "Aceitar extração Opus para a transação corrente"},
    ])

    _ = dados, periodo, pessoa, ctx

    # CSS dedicado da página (Sprint UX-V-4 -- padrão Onda M).
    st.markdown(
        minificar(carregar_css_pagina("revisor")),
        unsafe_allow_html=True,
    )

    # Layout 4-way canônico (Sprint UX-V-4) lê schema ``extracao_tripla.json``.
    # Graceful fallback: lista vazia quando JSON ausente.
    registros_canonicos = carregar_extracoes_triplas()
    _renderizar_layout_4way(registros_canonicos)

    st.markdown("---")

    pendencias = listar_pendencias_revisao()
    total = len(pendencias)
    indexadas = {p["item_id"]: p for p in pendencias}

    marcacoes = carregar_marcacoes(CAMINHO_REVISAO_HUMANA)
    item_ids_revisados = {m["item_id"] for m in marcacoes}
    revisados = sum(1 for p in pendencias if p["item_id"] in item_ids_revisados)
    aguardando = total - revisados
    taxa = _taxa_fidelidade(marcacoes)

    st.markdown(_page_header_html(total, revisados, taxa), unsafe_allow_html=True)

    # Atalhos j/k/a/r — registram listener via JS (idempotente, restrito à
    # página Revisor por checagem de query string interna).
    components.html(gerar_html_atalhos_revisor(), height=0)

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Pendências", total)
    col_b.metric("Revisadas", revisados)
    col_c.metric("Aguardando", aguardando)
    col_d.metric("Fidelidade", f"{taxa * 100:.0f}%")

    # Sprint 103: resumo de divergências ETL vs Opus em tabela.
    com_opus = [m for m in marcacoes if m.get("valor_opus")]
    if com_opus:
        divergentes = [
            m
            for m in com_opus
            if (m.get("valor_etl") or "").strip().lower()
            != (m.get("valor_opus") or "").strip().lower()
            and m.get("valor_etl")
        ]
        st.markdown(
            subtitulo_secao_html(
                f"Comparação ETL × Opus ({len(divergentes)} divergentes "
                f"de {len(com_opus)} marcações com proposta Opus)"
            ),
            unsafe_allow_html=True,
        )
        if divergentes:
            tabela_diff = [
                {
                    "item": d["item_id"][:50] + ("…" if len(d["item_id"]) > 50 else ""),
                    "dimensão": d["dimensao"],
                    "ETL": (d.get("valor_etl") or "")[:40],
                    "Opus": (d.get("valor_opus") or "")[:40],
                }
                for d in divergentes[:30]
            ]
            st.dataframe(tabela_diff, use_container_width=True, hide_index=True)
            if len(divergentes) > 30:
                st.caption(
                    f"... e mais {len(divergentes) - 30} divergências. Use "
                    "export CSV para ver todas."
                )

    if total == 0:
        st.markdown(
            callout_html(
                "success",
                "Nenhuma pendência de revisão. Tudo está classificado e "
                "vinculado dentro do limiar de confiança.",
                titulo="Inbox limpa",
            ),
            unsafe_allow_html=True,
        )
        return

    st.markdown("---")

    # Sprint UX-117: filtros 'Tipo de pendência' e 'Página' renderizam no
    # topo da página Revisor (st.columns([2,1])), NÃO mais na sidebar global.
    # Antes poluíam Hoje/Dinheiro/Análise/Metas que não usam esses filtros.
    # Mês / Pessoa / Forma de pagamento permanecem na sidebar global como
    # filtros transversais. Session_state keys preservadas
    # (revisor_filtro_tipo, revisor_pagina) para retrocompatibilidade.
    tipos_disponiveis = sorted({p["tipo"] for p in pendencias})

    # total_paginas depende do filtro de tipo. Calcula primeiro o filtro,
    # depois total_paginas, depois renderiza number_input com max_value real.
    col_tipo, col_pagina = st.columns([2, 1])
    with col_tipo:
        tipo_filtro = st.multiselect(
            "Tipo de pendência",
            tipos_disponiveis,
            default=tipos_disponiveis,
            key="revisor_filtro_tipo",
        )
    pendencias_filtradas = [p for p in pendencias if p["tipo"] in tipo_filtro]

    if not pendencias_filtradas:
        st.markdown(
            callout_html(
                "info",
                "Nenhuma pendência casa o filtro atual.",
            ),
            unsafe_allow_html=True,
        )
        return

    # Paginação 10 por página (volume real esgotaria browser).
    total_paginas = max(
        1,
        (len(pendencias_filtradas) + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA,
    )
    with col_pagina:
        pagina_atual = st.number_input(
            "Página",
            min_value=1,
            max_value=total_paginas,
            value=1,
            step=1,
            key="revisor_pagina",
        )
    inicio = (pagina_atual - 1) * ITENS_POR_PAGINA
    fim = inicio + ITENS_POR_PAGINA
    pagina = pendencias_filtradas[inicio:fim]

    st.caption(
        f"Exibindo {len(pagina)} de {len(pendencias_filtradas)} pendências "
        f"(página {pagina_atual} de {total_paginas})."
    )

    for idx, pendencia in enumerate(pagina, start=1):
        item_id = pendencia["item_id"]
        # Wrapper com data-revisor-card para o JS dos atalhos.
        # st.container devolve um bloco visualmente isolado; encapsulamos
        # com markdown abrindo/fechando o atributo via classe CSS.
        st.markdown(
            f'<div class="revisor-card" data-revisor-card data-revisor-idx="{idx - 1}" '
            f'data-revisor-item-id="{item_id}">',
            unsafe_allow_html=True,
        )
        with st.expander(
            f"[{pendencia['tipo']}] {item_id[:80]}",
            expanded=(idx == 1),
        ):
            marcacoes_item = [m for m in marcacoes if m["item_id"] == item_id]
            coletadas = _renderizar_painel_item(pendencia, marcacoes_item)

            col_save, col_aprovar, col_rejeitar = st.columns([1, 1, 1])
            with col_save:
                if st.button(
                    "Salvar marcações",
                    key=f"revisor_salvar_{item_id}",
                ):
                    for dimensao, (
                        estado,
                        obs,
                        valor_etl,
                        valor_grafo,
                    ) in coletadas.items():
                        salvar_marcacao(
                            CAMINHO_REVISAO_HUMANA,
                            item_id,
                            dimensao,
                            estado,
                            obs,
                            valor_etl=valor_etl,
                            valor_grafo_real=valor_grafo,
                        )
                    st.markdown(
                        callout_html(
                            "success",
                            f"Marcações de `{len(coletadas)}` dimensões "
                            "persistidas.",
                        ),
                        unsafe_allow_html=True,
                    )
            with col_aprovar:
                # Botão "aprovar" -- atalho `a` clica via JS (data-revisor-aprovar).
                if st.button(
                    "Aprovar (a)",
                    key=f"revisor_aprovar_{item_id}",
                    help="Marca todas as dimensões 'Não-aplicáveis' como OK.",
                ):
                    _gravar_decisao_global(
                        item_id, coletadas, ESTADO_OK, "aprovado-via-atalho"
                    )
                    st.markdown(
                        callout_html(
                            "success",
                            "Item aprovado e persistido em revisao_humana.sqlite.",
                        ),
                        unsafe_allow_html=True,
                    )
            with col_rejeitar:
                # Botão "rejeitar" -- atalho `r` clica via JS (data-revisor-rejeitar).
                if st.button(
                    "Rejeitar (r)",
                    key=f"revisor_rejeitar_{item_id}",
                    help="Marca todas as dimensões 'Não-aplicáveis' como Erro.",
                ):
                    _gravar_decisao_global(
                        item_id, coletadas, ESTADO_ERRO, "rejeitado-via-atalho"
                    )
                    st.markdown(
                        callout_html(
                            "warning",
                            "Item rejeitado e persistido em revisao_humana.sqlite.",
                        ),
                        unsafe_allow_html=True,
                    )

            # Tags ocultas para o JS dos atalhos j/k/a/r encontrar os botões.
            # Streamlit renderiza os botões acima como <button>; injetamos
            # marcadores invisíveis com seletor estável.
            st.markdown(
                minificar(
                    f"""
                    <span data-revisor-aprovar-marker
                          data-revisor-target="revisor_aprovar_{item_id}"
                          style="display:none"></span>
                    <span data-revisor-rejeitar-marker
                          data-revisor-target="revisor_rejeitar_{item_id}"
                          style="display:none"></span>
                    """
                ),
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Ações da sessão: relatório + sugestor de patch + export ground-truth (S103).
    col_rel, col_patch, col_csv = st.columns(3)
    with col_rel:
        if st.button("Gerar relatório da sessão", key="revisor_gerar_relatorio"):
            destino_dir = Path(__file__).resolve().parents[3] / "docs" / "revisoes"
            destino = gravar_relatorio(
                marcacoes,
                destino_dir,
                pendencias_indexadas=indexadas,
            )
            st.markdown(
                callout_html(
                    "success",
                    f"Relatório gravado em "
                    f"`{destino.relative_to(destino_dir.parents[1])}`. "
                    "PII mascarada (CPF/CNPJ).",
                    titulo="Relatório pronto",
                ),
                unsafe_allow_html=True,
            )
    with col_csv:
        # Sprint 103: export ground-truth CSV com 3 colunas (ETL/Opus/Humano)
        # + flag divergencia. Util para análise quantitativa pós-sessão e
        # para alimentar futuras métricas de fidelidade do extrator.
        if st.button("Exportar ground-truth CSV", key="revisor_exportar_csv"):
            destino_csv = (
                Path(__file__).resolve().parents[3]
                / "docs"
                / "revisoes"
                / f"ground_truth_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"
            )
            n = gerar_ground_truth_csv(CAMINHO_REVISAO_HUMANA, destino_csv)
            st.markdown(
                callout_html(
                    "success",
                    f"CSV gerado: `{destino_csv.relative_to(destino_csv.parents[2])}` "
                    f"({n} linha(s)). PII mascarada.",
                    titulo="Ground-truth pronto",
                ),
                unsafe_allow_html=True,
            )

    with col_patch:
        padroes = detectar_padroes_recorrentes(marcacoes)
        if padroes and st.button("Sugerir patch YAML", key="revisor_sugerir_patch"):
            diff = sugerir_patch_yaml(padroes)
            st.markdown(
                callout_html(
                    "info",
                    f"{len(padroes)} padrão(ões) detectado(s). Diff abaixo "
                    "para copy-paste manual em `mappings/*.yaml`.",
                ),
                unsafe_allow_html=True,
            )
            st.code(diff, language="yaml")
        elif not padroes:
            st.caption(
                "Sugestor de patch fica disponível ao detectar "
                f">= {LIMITE_PADRAO_RECORRENTE} reprovações na mesma dimensão."
            )


# "A revisão visual é a ponte entre intuição humana e automação determinística."
# -- princípio do alinhamento mensurável
