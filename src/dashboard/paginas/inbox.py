"""Cluster Inbox · aba "Inbox" (UX-RD-15).

Página que materializa o cluster Inbox no dashboard. Antes da Sprint
UX-RD-15 o cluster era declarado em ``CLUSTERS_VALIDOS`` mas devolvia
fallback graceful (``_renderizar_fallback_cluster``); a partir desta
sprint a página dispatcha a fila real lida de ``<raiz>/inbox/`` (ou
``data/inbox/`` quando existir) via ``src.intake.inbox_reader``.

Estrutura visual (espelha ``novo-mockup/mockups/16-inbox.html`` +
``_inbox-render.js``):

  1. Page header: título "INBOX" + sprint-tag + subtítulo dinâmico.
  2. Barra de status: 4 tiles (aguardando, extraído, falhou, duplicado)
     + tile total. Cores via tokens D7 do tema.
  3. Dropzone: ``st.file_uploader`` com ``accept_multiple_files=True``.
     Arquivos subidos são gravados em ``<inbox>/<filename>`` via
     ``inbox_reader.gravar_arquivo_inbox``. A classificação automática
     permanece responsabilidade do CLI (``./run.sh --inbox``) -- a
     página apenas registra a chegada (humano-no-loop deliberado, ADR-13).
  4. Fila: tabela densa (.table) com thumb + filename + sha8 + estado
     pill + ts. Linhas com mtime nos últimos 60s ganham classe
     ``.row-novo`` (animação fade purple 0.8s já definida em
     ``tema_css.py``).
  5. Drawer sidecar: ao selecionar uma linha (via ``st.radio`` mapeado
     para ``session_state``), renderiza painel HTML com JSON sidecar
     formatado e syntax-highlight básico.
  6. Skill-instr: bloco mono explicando como acionar extração via
     Claude Code CLI (``/validar-arquivo``) -- alinha com ADR-13.

Contrato uniforme do dispatcher: ``renderizar(dados, periodo, pessoa, ctx)``.

Lição UX-RD-04 herdada: HTML emitido com ``minificar()`` -- parser
CommonMark do Streamlit interpreta indentação >=4 espaços como
``<pre><code>``. Nunca emitir HTML com indentação Python crua.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.ui import carregar_css_pagina
from src.dashboard.tema import CORES
from src.intake.inbox_reader import (
    contar_estados,
    gravar_arquivo_inbox,
    listar_inbox,
)

# Chave do session_state para o sha8 selecionado (drawer aberto).
_SESSION_DRAWER = "inbox_drawer_sha8"

# Texto literal do skill-instr (verificado por test_inbox_real).
SKILL_INSTR_TITULO: str = "Para extrair os arquivos pendentes"
SKILL_INSTR_COMANDO: str = "/validar-arquivo"
SKILL_INSTR_ADR: str = "ADR-13"


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página Inbox.

    Args:
        dados: Estrutura padrão de DataFrames (não consumida -- a página
            é cross-financeira, opera sobre filesystem).
        periodo: Período selecionado na sidebar (ignorado).
        pessoa: Pessoa selecionada na sidebar (ignorada).
        ctx: Contexto extra (granularidade etc., ignorado).
    """
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Abrir pasta", "glyph": "docs",
         "title": "Abrir ~/Ouroboros/inbox"},
        {"label": "Atualizar fila", "primary": True, "glyph": "refresh",
         "title": "Verificar novos arquivos"},
    ])

    del dados, periodo, pessoa, ctx

    st.markdown(minificar(carregar_css_pagina("inbox")), unsafe_allow_html=True)

    itens = listar_inbox()
    contagens = contar_estados(itens)
    total = len(itens)
    aguardando = contagens["aguardando"]

    st.markdown(_page_header_html(aguardando), unsafe_allow_html=True)
    st.markdown(_barra_status_html(contagens, total=total), unsafe_allow_html=True)

    _renderizar_dropzone()

    if not itens:
        st.markdown(_fila_vazia_html(), unsafe_allow_html=True)
    else:
        _renderizar_fila(itens)
        _renderizar_drawer_se_aberto(itens)

    st.markdown(_skill_instr_html(), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Dropzone (st.file_uploader)
# ---------------------------------------------------------------------------


def _renderizar_dropzone() -> None:
    """Componente Streamlit para upload de arquivos.

    ``st.file_uploader`` aceita drag&drop nativamente. Arquivos são
    gravados em ``<inbox>/<filename>`` com colisão resolvida por prefixo
    sha8. Nada de classificação automática nesta camada -- ADR-13.
    """
    st.markdown(
        minificar(
            f"""
            <div class="inbox-dropzone-marker">
              <div class="inbox-dz-glyph">⤓</div>
              <h3>Arraste arquivos aqui ou clique para escolher</h3>
              <p>
                Aceita extratos bancários, faturas, recibos, cupons, notas e
                comprovantes. Cada arquivo é registrado por sha8 -- duplicados
                são detectados antes da extração pelo pipeline.
              </p>
              <div class="inbox-tipo-chips">
                {''.join(f'<span class="inbox-tipo-chip">{t}</span>' for t in
                  ["PDF","CSV","XLSX","OFX","JPG","PNG","HTML","TXT","JSON"])}
              </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    arquivos = st.file_uploader(
        "Subir arquivos para a inbox",
        accept_multiple_files=True,
        type=["pdf", "csv", "xlsx", "xls", "ofx", "jpg", "jpeg", "png", "html", "txt", "json"],
        key="inbox_uploader",
        label_visibility="collapsed",
    )

    if not arquivos:
        return

    # st.file_uploader devolve a mesma lista enquanto o widget existe.
    # Usamos um marker em session_state para gravar cada arquivo apenas
    # uma vez (idempotência por nome+tamanho).
    chave_marker = "inbox_uploader_processados"
    processados: set[str] = st.session_state.get(chave_marker, set())

    novos: list[str] = []
    for arq in arquivos:
        marca = f"{arq.name}::{arq.size}"
        if marca in processados:
            continue
        try:
            destino = gravar_arquivo_inbox(arq.name, arq.getvalue())
            novos.append(destino.name)
            processados.add(marca)
        except OSError as exc:
            st.error(f"Falha ao gravar {arq.name}: {exc}")

    st.session_state[chave_marker] = processados

    if novos:
        st.success(
            f"{len(novos)} arquivo(s) registrado(s) na inbox. "
            "Para extrair, abra o terminal: `/validar-arquivo`."
        )


# ---------------------------------------------------------------------------
# Fila (tabela)
# ---------------------------------------------------------------------------


def _renderizar_fila(itens: list[dict[str, Any]]) -> None:
    """Tabela de arquivos da inbox + select para abrir drawer."""
    st.markdown(_fila_html(itens), unsafe_allow_html=True)

    opcoes_sha = [it["sha8"] for it in itens]
    rotulos = {
        it["sha8"]: f"{it['sha8']} · {it['filename']}" for it in itens
    }

    sha_atual = st.session_state.get(_SESSION_DRAWER)
    if sha_atual not in opcoes_sha:
        sha_atual = None

    col_sel, col_btn = st.columns([4, 1])
    with col_sel:
        escolha = st.selectbox(
            "Abrir sidecar de:",
            options=["—"] + opcoes_sha,
            format_func=lambda s: "Selecionar arquivo..." if s == "—" else rotulos[s],
            index=0 if sha_atual is None else opcoes_sha.index(sha_atual) + 1,
            key="inbox_select_drawer",
            label_visibility="collapsed",
        )
    with col_btn:
        if st.button("Fechar drawer", key="inbox_btn_fechar"):
            st.session_state[_SESSION_DRAWER] = None
            escolha = "—"

    if escolha != "—":
        st.session_state[_SESSION_DRAWER] = escolha


def _renderizar_drawer_se_aberto(itens: list[dict[str, Any]]) -> None:
    sha = st.session_state.get(_SESSION_DRAWER)
    if not sha:
        return
    item = next((it for it in itens if it["sha8"] == sha), None)
    if item is None:
        return
    st.markdown(_drawer_html(item), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Geradores HTML
# ---------------------------------------------------------------------------


def _page_header_html(aguardando: int) -> str:
    palavra = "arquivo" if aguardando == 1 else "arquivos"
    cor_destaque = CORES["destaque"]
    return minificar(
        f"""
        <div class="page-header">
          <div>
            <h1 class="page-title">INBOX</h1>
            <p class="page-subtitle">
              Entrada de dados. Arquivos chegam aqui antes de serem
              extraídos pelo pipeline.
              <strong style="color:{cor_destaque};">{aguardando}</strong>
              {palavra} aguardando extração.
            </p>
          </div>
          <div class="page-meta">
            <span class="sprint-tag">UX-RD-15</span>
            <span class="pill pill-d7-calibracao">Em calibração</span>
          </div>
        </div>
        """
    )


def _barra_status_html(contagens: dict[str, int], total: int) -> str:
    aguardando = contagens["aguardando"]
    extraido = contagens["extraido"]
    falhou = contagens["falhou"]
    duplicado = contagens["duplicado"]

    cor_aguardando = CORES["texto_sec"]
    cor_extraido = CORES["d7_graduado"]
    cor_falhou = CORES["negativo"]
    cor_duplicado = CORES["info"]
    cor_total = CORES["texto"]

    return minificar(
        f"""
        <div class="kpi-grid" style="margin-bottom:16px;">
          <div class="kpi">
            <div class="kpi-label">Aguardando</div>
            <div class="kpi-value" style="color:{cor_aguardando};">{aguardando}</div>
          </div>
          <div class="kpi">
            <div class="kpi-label">Extraído</div>
            <div class="kpi-value" style="color:{cor_extraido};">{extraido}</div>
          </div>
          <div class="kpi">
            <div class="kpi-label">Falhou</div>
            <div class="kpi-value" style="color:{cor_falhou};">{falhou}</div>
          </div>
          <div class="kpi">
            <div class="kpi-label">Pulado (duplicado)</div>
            <div class="kpi-value" style="color:{cor_duplicado};">{duplicado}</div>
          </div>
          <div class="kpi">
            <div class="kpi-label">Total na fila</div>
            <div class="kpi-value" style="color:{cor_total};">{total}</div>
          </div>
        </div>
        """
    )


def _classe_pill_estado(estado: str) -> str:
    mapa = {
        "aguardando": "pill-d7-pendente",
        "extraido": "pill-d7-graduado",
        "falhou": "pill-humano-rejeitado",
        "duplicado": "pill-d7-calibracao",
    }
    return mapa.get(estado, "pill-d7-pendente")


def _label_estado(estado: str) -> str:
    mapa = {
        "aguardando": "aguardando",
        "extraido": "extraído",
        "falhou": "falhou",
        "duplicado": "pulado-duplicado",
    }
    return mapa.get(estado, estado)


def _glyph_tipo(tipo: str) -> str:
    mapa = {
        "pdf": "PDF",
        "csv": "CSV",
        "xlsx": "XLS",
        "ofx": "OFX",
        "img": "IMG",
        "html": "HTM",
        "json": "JSN",
        "xml": "XML",
        "eml": "EML",
        "zip": "ZIP",
        "txt": "TXT",
    }
    return mapa.get(tipo, tipo[:3].upper())


def _fila_html(itens: list[dict[str, Any]]) -> str:
    """Tabela densa espelhando o mockup."""
    from time import time

    agora = time()
    linhas: list[str] = []
    for it in itens:
        ts_iso = it["ts_iso"]
        try:
            from datetime import datetime as _dt

            mtime_epoch = _dt.fromisoformat(ts_iso).timestamp()
        except (ValueError, TypeError):
            mtime_epoch = 0.0
        novo = (agora - mtime_epoch) < 60.0
        classe_tr = "row-novo inbox-fila-tr" if novo else "inbox-fila-tr"

        tipo_arquivo = it.get("tipo_arquivo") or "—"
        estado = it["estado"]
        pill_cls = _classe_pill_estado(estado)
        label = _label_estado(estado)
        glyph = _glyph_tipo(it["tipo"])
        sha8 = it["sha8"]
        filename = it["filename"]
        tamanho = it["tamanho_humano"]
        ts_humano = it["ts_humano"]

        linhas.append(
            minificar(
                f"""
                <tr class="{classe_tr}" data-sha="{sha8}">
                  <td class="thumb-cell">
                    <div class="inbox-fila-thumb">{glyph}</div>
                  </td>
                  <td>
                    <div class="inbox-filename">{filename}</div>
                    <div class="inbox-tipo-arq">{tipo_arquivo}</div>
                  </td>
                  <td class="col-num">{tamanho}</td>
                  <td class="col-mono inbox-sha8">{sha8}</td>
                  <td><span class="pill {pill_cls}">{label}</span></td>
                  <td class="col-mono inbox-ts">{ts_humano}</td>
                </tr>
                """
            )
        )

    return minificar(
        f"""
        <div class="card inbox-fila-card">
          <div class="inbox-fila-head">
            <h2>Fila</h2>
            <span class="inbox-fila-count">{len(itens)} arquivo(s)</span>
          </div>
          <div class="inbox-fila-scroll">
            <table class="table inbox-fila-table">
              <thead>
                <tr>
                  <th></th>
                  <th>Arquivo</th>
                  <th class="col-num">Tamanho</th>
                  <th>sha8</th>
                  <th>Status</th>
                  <th>Registrado</th>
                </tr>
              </thead>
              <tbody>
                {''.join(linhas)}
              </tbody>
            </table>
          </div>
        </div>
        """
    )


def _fila_vazia_html() -> str:
    return minificar(
        """
        <div class="card inbox-fila-card inbox-fila-vazia">
          <div class="inbox-fila-head">
            <h2>Fila</h2>
            <span class="inbox-fila-count">0 arquivo(s)</span>
          </div>
          <div class="inbox-vazia-msg">
            <p>Nenhum arquivo na inbox. Use o dropzone acima ou copie
            arquivos diretamente para o diretório <code>inbox/</code>.</p>
          </div>
        </div>
        """
    )


def _drawer_html(item: dict[str, Any]) -> str:
    """HTML do drawer sidecar (sha8 + JSON formatado)."""
    sha8 = item["sha8"]
    sidecar = item.get("sidecar")

    if sidecar is None:
        corpo = minificar(
            """
            <div class="inbox-drawer-sem-sidecar">
              <p>Este arquivo ainda não foi extraído. Sem sidecar JSON
              disponível.</p>
              <p>Para extrair: abra o terminal na raiz do projeto e
              digite <code>/validar-arquivo</code>.</p>
            </div>
            """
        )
    else:
        corpo = _sidecar_pre_html(sidecar)

    erro = item.get("erro")
    badge_erro = ""
    if erro:
        badge_erro = minificar(
            f"""
            <div class="inbox-drawer-erro">
              <strong>Erro registrado:</strong> {erro}
            </div>
            """
        )

    return minificar(
        f"""
        <aside class="drawer inbox-drawer" role="dialog"
               aria-label="Sidecar do arquivo {sha8}">
          <div class="drawer-head">
            <div>
              <div class="inbox-drawer-rotulo">SIDECAR</div>
              <div class="inbox-drawer-sha">{sha8}</div>
              <div class="inbox-drawer-filename">{item['filename']}</div>
            </div>
          </div>
          <div class="drawer-body">
            {badge_erro}
            {corpo}
          </div>
        </aside>
        """
    )


def _sidecar_pre_html(sidecar: dict[str, Any]) -> str:
    """JSON formatado com syntax-highlight básico via spans CSS."""
    raw = json.dumps(sidecar, indent=2, ensure_ascii=False, sort_keys=True)
    # Substituições conservadoras (ordem importa: chave antes do valor).
    cor_chave = CORES["destaque"]
    cor_string = CORES["positivo"]
    cor_numero = CORES["neutro"]
    cor_bool = CORES["alerta"]

    import html as _html
    import re as _re

    s = _html.escape(raw)
    s = _re.sub(
        r'(&quot;[^&]+?&quot;)(\s*:)',
        rf'<span style="color:{cor_chave};">\1</span>\2',
        s,
    )
    s = _re.sub(
        r':\s*(&quot;[^&]*?&quot;)',
        rf': <span style="color:{cor_string};">\1</span>',
        s,
    )
    s = _re.sub(
        r':\s*(-?\d+\.?\d*)',
        rf': <span style="color:{cor_numero};">\1</span>',
        s,
    )
    s = _re.sub(
        r':\s*(true|false|null)',
        rf': <span style="color:{cor_bool};">\1</span>',
        s,
    )

    return f'<pre class="inbox-sidecar-pre">{s}</pre>'


def _skill_instr_html() -> str:
    return minificar(
        f"""
        <div class="skill-instr">
          <h4>{SKILL_INSTR_TITULO}</h4>
          <ol>
            <li>Abra o Claude Code CLI no terminal, na raiz do projeto.</li>
            <li>Digite: <code>{SKILL_INSTR_COMANDO}</code></li>
            <li>Volte aqui — a fila atualiza automaticamente.</li>
          </ol>
          <div class="why">
            Por que terminal? <strong>{SKILL_INSTR_ADR}</strong> --
            paradigma agentic-first. A sessão de IA é parte do pipeline,
            não cliente externo dele. Sem custo de API, sem cron,
            humano-no-loop deliberado.
          </div>
        </div>
        """
    )


# ---------------------------------------------------------------------------
# CSS local
# ---------------------------------------------------------------------------


# CSS dedicado: src/dashboard/css/paginas/inbox.css (UX-M-02.C residual).
# "O caos organizado é o primeiro passo da ordem." -- princípio do GTD
