"""Aba "Extração Tripla" -- Sprint UX-RD-11 + paridade visual UX-V-2.4.

Layout 2 colunas alinhado ao mockup canônico de validação por arquivo:

  - Header com 4 KPIs (PARIDADE, DIVERGÊNCIAS, EM REVISÃO, total ARQUIVOS).
  - Coluna esquerda: lista de arquivos agrupada por TIPO/formato com badge,
    flag de status humano e paridade %.
  - Coluna direita: tabela ETL × Opus × Humano para o arquivo selecionado.
    Linhas divergentes destacadas com fundo laranja/vermelho, linhas
    consenso pré-populam o input humano. Badges DIVERGENTE / CONSENSO.

Sprint VALIDAÇÃO-CSV-01 (regra 11 do CLAUDE.md): alimenta
``data/output/validacao_arquivos.csv``.

Princípios:

  - Coexiste com Revisor 4-way (Sprint D2). Revisor opera sobre transações;
    esta aba opera sobre (arquivo, campo). Sem fusão.
  - Cobertura total: lista todos os arquivos pendentes, sem filtro de
    inclusão por valor (Decisão D5/D7 do dono em 2026-04-29).
  - Tema dark Dracula via tokens em ``css/tokens.css``. Divergência usa
    ``var(--accent-orange)``.
  - PII mascarada antes de exibir, conforme padrão do Revisor.
  - HTML grande passa por ``html_utils.minificar`` para evitar bloco
    ``<pre><code>`` indesejado do CommonMark do Streamlit (UX-RD-04).
  - CSS dedicado em ``src/dashboard/css/paginas/extracao_tripla.css``
    (padrão Onda M).

API pública: ``renderizar(dados, mes_selecionado, pessoa, ctx)``.
"""

from __future__ import annotations

import re
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.ui import callout_html, carregar_css_pagina
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

# Mapa formato -> token de classe CSS para cor de borda no grupo da lista.
_GRUPO_CLASSE: dict[str, str] = {
    "PDF": "tipo-pdf",
    "IMG": "tipo-imagem",
    "CSV": "tipo-csv",
    "XLSX": "tipo-xlsx",
    "OFX": "tipo-ofx",
    "HTML": "tipo-html",
    "XML": "tipo-html",
    "???": "tipo-html",
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


def _classificar_status_campo(linha: pd.Series) -> str:
    """Classifica status do campo: ``ok`` (consenso), ``divergente``,
    ``apenas_etl``, ``apenas_opus`` ou ``so_humano``.

    Espelha a lógica do mockup ``_extracao-render.js::statusCampo``.
    """
    etl = str(linha.get("valor_etl") or "").strip()
    opus = str(linha.get("valor_opus") or "").strip()
    if etl and opus:
        return "ok" if etl == opus else "divergente"
    if etl and not opus:
        return "apenas_etl"
    if opus and not etl:
        return "apenas_opus"
    return "so_humano"


def _detectar_divergencia(linha: pd.Series) -> bool:
    """True se ETL e Opus discordam (ambos não-vazios e diferentes)."""
    return _classificar_status_campo(linha) == "divergente"


def _consenso(linha: pd.Series) -> str:
    """Devolve consenso ETL ∩ Opus quando aplicável; senão string vazia."""
    etl = str(linha.get("valor_etl") or "").strip()
    opus = str(linha.get("valor_opus") or "").strip()
    if etl and opus and etl == opus:
        return etl
    return ""


def _calcular_paridade(df_arquivo: pd.DataFrame) -> float:
    """% de campos onde ETL e Opus concordam (ambos não-vazios e iguais).

    Retorna 0.0 se DataFrame vazio. Considera o universo como total de
    linhas (cada linha = um campo) para casar com a leitura do mockup.
    """
    if df_arquivo.empty:
        return 0.0
    iguais = sum(
        1 for _, linha in df_arquivo.iterrows()
        if _classificar_status_campo(linha) == "ok"
    )
    return iguais / len(df_arquivo) * 100


def _agrupar_por_arquivo(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa por (sha8_arquivo, caminho_relativo) e calcula paridade global.

    Colunas devolvidas:
      - sha8_arquivo, tipo_arquivo, caminho_relativo, total_campos
      - paridade_pct (0..100)
      - status_humano (aprovado / em_revisao / pendente) -- novo UX-V-2.4
      - status_global (validado / conflito / extraido / aguardando) -- legado
      - n_divergencias, n_unilaterais

    A coluna ``status_global`` preserva o contrato da Sprint UX-RD-11 para
    retrocompat de testes; ``status_humano`` é o agregado novo alinhado ao
    mockup (paridade visual com lista esquerda e flag de cor).
    """
    colunas_padrao = [
        "sha8_arquivo",
        "tipo_arquivo",
        "caminho_relativo",
        "total_campos",
        "paridade_pct",
        "status_humano",
        "status_global",
        "n_divergencias",
        "n_unilaterais",
    ]
    if df.empty:
        return pd.DataFrame(columns=colunas_padrao)

    grupos = []
    for (sha8, caminho), grupo in df.groupby(["sha8_arquivo", "caminho_relativo"]):
        tipo = str(grupo["tipo_arquivo"].iloc[0])
        total = len(grupo)
        paridade = _calcular_paridade(grupo)

        # status_humano: agregado por status_humano da linha (UX-V-2.4)
        status_humanos_raw = set(grupo["status_humano"].astype(str).str.lower())
        if status_humanos_raw and status_humanos_raw.issubset({"ok", "aprovado"}):
            status_h = "aprovado"
        elif "ok" in status_humanos_raw or "aprovado" in status_humanos_raw:
            status_h = "em_revisao"
        else:
            status_h = "pendente"

        # status_global: contrato legado UX-RD-11 (validado / conflito / extraido / aguardando)
        if status_humanos_raw and status_humanos_raw.issubset({"ok", "aprovado"}):
            status_g = "validado"
        else:
            divergencias = (
                (grupo["valor_etl"].astype(str) != "")
                & (grupo["valor_opus"].astype(str) != "")
                & (grupo["valor_etl"].astype(str) != grupo["valor_opus"].astype(str))
            )
            if bool(divergencias.any()):
                status_g = "conflito"
            elif (
                (grupo["valor_etl"].astype(str) != "").any()
                or (grupo["valor_opus"].astype(str) != "").any()
            ):
                status_g = "extraido"
            else:
                status_g = "aguardando"

        n_div = sum(
            1 for _, linha in grupo.iterrows()
            if _classificar_status_campo(linha) == "divergente"
        )
        n_uni = sum(
            1 for _, linha in grupo.iterrows()
            if _classificar_status_campo(linha) in {"apenas_etl", "apenas_opus"}
        )

        grupos.append(
            {
                "sha8_arquivo": sha8,
                "tipo_arquivo": tipo,
                "caminho_relativo": caminho,
                "total_campos": total,
                "paridade_pct": paridade,
                "status_humano": status_h,
                "status_global": status_g,
                "n_divergencias": n_div,
                "n_unilaterais": n_uni,
            }
        )
    return pd.DataFrame(grupos)


# ---------------------------------------------------------------------------
# Helpers de render HTML
# ---------------------------------------------------------------------------


def _classe_paridade(paridade_pct: float) -> str:
    """Retorna classe CSS conforme faixa de paridade (alta/media/baixa)."""
    if paridade_pct >= 90:
        return "paridade-alta"
    if paridade_pct >= 70:
        return "paridade-media"
    return "paridade-baixa"


def _classe_confianca(confianca: float) -> str:
    """Retorna classe CSS conforme faixa de confiança Opus."""
    if confianca >= 0.85:
        return "conf-alta"
    if confianca >= 0.65:
        return "conf-media"
    return "conf-baixa"


def _flag_status_humano(status: str) -> str:
    """Retorna classe CSS da flag (círculo) por status humano."""
    if status == "aprovado":
        return "flag-aprovado"
    if status == "em_revisao":
        return "flag-revisar"
    return "flag-pendente"


def _kpis_header_html(
    media_paridade: float,
    n_divergencias: int,
    n_revisao: int,
    n_total: int,
) -> str:
    """KPIs do topo: PARIDADE %, DIVERGÊNCIAS N, EM REVISÃO N, total ARQUIVOS."""
    return minificar(
        f"""
        <div class="tripla-header">
          <div class="tripla-kpi tripla-kpi-paridade">
            PARIDADE <strong>{media_paridade:.0f}%</strong>
          </div>
          <div class="tripla-kpi tripla-kpi-divergencias">
            DIVERGÊNCIAS <strong>{n_divergencias}</strong>
          </div>
          <div class="tripla-kpi tripla-kpi-revisao">
            EM REVISÃO <strong>{n_revisao}</strong>
          </div>
          <div class="tripla-kpi">
            <strong>{n_total}</strong> ARQUIVOS
          </div>
        </div>
        """
    )


def _lista_arquivos_html(
    df_grupos: pd.DataFrame,
    caminho_selecionado: str | None,
) -> str:
    """Renderiza lista esquerda agrupada por TIPO de formato (PDF/IMG/...)."""
    if df_grupos.empty:
        return (
            '<div class="lista-arquivos">'
            '<p class="lista-vazia">Sem arquivos catalogados ainda.</p>'
            "</div>"
        )

    # Agrupar por badge formato (PDF, IMG, CSV, ...) — ordem fixa.
    ordem_formato = ["PDF", "IMG", "CSV", "XLSX", "OFX", "HTML", "XML", "???"]
    por_formato: dict[str, list[dict]] = {}
    for _, grupo in df_grupos.iterrows():
        badge = _badge_formato(str(grupo["caminho_relativo"]))
        por_formato.setdefault(badge, []).append(grupo.to_dict())

    grupos_html: list[str] = []
    for fmt in ordem_formato:
        if fmt not in por_formato:
            continue
        arquivos = por_formato[fmt]
        classe_grupo = _GRUPO_CLASSE.get(fmt, "tipo-html")

        items_html: list[str] = []
        for arq in arquivos:
            caminho = str(arq["caminho_relativo"])
            nome = Path(caminho).name
            tipo_sem = str(arq.get("tipo_arquivo") or "—")
            paridade_pct = float(arq.get("paridade_pct") or 0.0)
            classe_par = _classe_paridade(paridade_pct)
            status = str(arq.get("status_humano") or "pendente")
            classe_flag = _flag_status_humano(status)
            classe_sel = "selecionado" if caminho == caminho_selecionado else ""

            items_html.append(
                f"""
                <div class="arquivo-linha {classe_sel}">
                  <div class="arq-top">
                    <span class="arq-flag {classe_flag}"
                          title="status humano: {escape(status)}"></span>
                    <span class="arq-nome" title="{escape(nome)}">{escape(nome)}</span>
                  </div>
                  <div class="arq-meta">
                    <span class="arq-tipo-badge">{escape(tipo_sem)}</span>
                    <span class="arq-paridade {classe_par}">
                      {paridade_pct:.0f}% ok
                    </span>
                  </div>
                </div>
                """
            )

        grupos_html.append(
            f"""
            <div class="lista-grupo-tipo">
              <div class="lista-grupo-head {classe_grupo}">
                <span>{fmt}</span>
                <span class="lista-grupo-count">{len(arquivos)}</span>
              </div>
              <div class="lista-grupo-body">{''.join(items_html)}</div>
            </div>
            """
        )

    return minificar(
        '<div class="lista-arquivos">' + "".join(grupos_html) + "</div>"
    )


def _tabela_tripla_html(
    df_arquivo: pd.DataFrame,
    extractor_versao: str = "ETL",
) -> str:
    """Tabela ETL × Opus × Humano para 1 arquivo selecionado.

    Usa apenas inputs visuais (read-only HTML); persistência continua via
    botão Streamlit fora do HTML (ver ``renderizar``).
    """
    if df_arquivo.empty:
        return '<p class="tabela-vazia">Selecione um arquivo na lista esquerda.</p>'

    n_campos = len(df_arquivo)

    linhas_html: list[str] = []
    for _, linha in df_arquivo.iterrows():
        campo = str(linha.get("campo") or "")
        etl_v = _mascarar_pii(str(linha.get("valor_etl") or ""))
        opus_v = _mascarar_pii(str(linha.get("valor_opus") or ""))
        humano_v = _mascarar_pii(str(linha.get("valor_humano") or ""))

        try:
            confianca = float(linha.get("confianca_opus") or 0.0)
        except (TypeError, ValueError):
            confianca = 0.0

        status = _classificar_status_campo(linha)

        # Pré-preenchimento humano: se consenso, usa o valor; se divergente
        # ou unilateral, deixa input vazio para humano resolver.
        if not humano_v:
            humano_v = _consenso(linha)

        # Classes de linha por status
        if status == "divergente":
            tr_classe = "linha-divergente"
            badge_html = '<span class="badge-divergente">DIVERGENTE</span>'
        elif status == "apenas_etl":
            tr_classe = "linha-uni-etl"
            badge_html = '<span class="badge-uni-etl">só ETL</span>'
        elif status == "apenas_opus":
            tr_classe = "linha-uni-opus"
            badge_html = '<span class="badge-uni-opus">só Opus</span>'
        elif status == "ok":
            tr_classe = "linha-consenso"
            badge_html = '<span class="badge-consenso">CONSENSO</span>'
        else:
            tr_classe = "linha-so-humano"
            badge_html = '<span class="badge-uni-etl">só humano</span>'

        # Cell ETL
        if etl_v:
            etl_html = f'<span class="val">{escape(etl_v)}</span>'
        else:
            etl_html = '<span class="cel-vazio">—</span>'

        # Cell Opus + confiança
        classe_conf = _classificar_confianca = _classe_confianca(confianca)
        if opus_v:
            opus_html = (
                f'<span class="val">{escape(opus_v)}</span>'
                f'<span class="conf {classe_conf}">{confianca:.0%}</span>'
            )
        else:
            opus_html = '<span class="cel-vazio">—</span>'

        # Cell Humano (input visual; Streamlit form fora cuida da persistência)
        humano_input = (
            f'<input type="text" class="user-input" '
            f'value="{escape(humano_v)}" '
            f'placeholder="preencher..." '
            f'data-campo="{escape(campo)}" readonly />'
        )

        linhas_html.append(
            f"""
            <tr class="{tr_classe}">
              <td class="cel-campo">
                <div class="campo-nome">{escape(campo)}</div>
              </td>
              <td class="cel-etl">{etl_html}</td>
              <td class="cel-opus">{opus_html}</td>
              <td class="cel-humano">{humano_input}</td>
              <td class="cel-status">{badge_html}</td>
            </tr>
            """
        )

    return minificar(
        f"""
        <div class="tabela-tripla-host">
          <table class="tabela-tripla">
            <thead>
              <tr>
                <th class="th-campo">CAMPO</th>
                <th class="th-etl">
                  <div class="th-fonte">
                    <span>ETL determinístico</span>
                  </div>
                  <div class="th-fonte-sub">{escape(extractor_versao)}</div>
                </th>
                <th class="th-opus">
                  <div class="th-fonte">
                    <span>Claude Opus agentic</span>
                  </div>
                  <div class="th-fonte-sub">opus_v1 · {n_campos} campos</div>
                </th>
                <th class="th-humano">
                  <div class="th-fonte">
                    <span>Validação humana</span>
                  </div>
                  <div class="th-fonte-sub">consenso pré-preenchido</div>
                </th>
                <th class="th-status">STATUS</th>
              </tr>
            </thead>
            <tbody>{''.join(linhas_html)}</tbody>
          </table>
        </div>
        """
    )


# ---------------------------------------------------------------------------
# Persistência (form Streamlit fora do HTML estático)
# ---------------------------------------------------------------------------


def _form_validar_arquivo(
    df_arquivo: pd.DataFrame,
    sha8: str,
    caminho_csv: Path,
) -> None:
    """Form Streamlit nativo para coletar valor_humano editável + persistir.

    O HTML da tabela mostra o overview visual. Para garantir persistência
    real (sem JS custom), usamos st.text_input em expander discreto abaixo
    da tabela, alinhado ao princípio "HTML para visual, Streamlit para
    interatividade" (ADR-19).
    """
    if df_arquivo.empty:
        return

    with st.expander("Editar campos humanos e enviar validação", expanded=False):
        valores_humanos: dict[str, str] = {}
        for _, linha in df_arquivo.iterrows():
            campo = str(linha.get("campo") or "")
            humano_inicial = _mascarar_pii(str(linha.get("valor_humano") or ""))
            if not humano_inicial:
                humano_inicial = _consenso(linha)

            valores_humanos[campo] = st.text_input(
                campo,
                value=humano_inicial,
                key=f"vh_{sha8}_{campo}",
            )

        if st.button(
            "Enviar validação",
            type="primary",
            key=f"validar_{sha8}",
            help="Persiste valor_humano + status_humano=ok no CSV.",
        ):
            atualizadas = 0
            for _, linha in df_arquivo.iterrows():
                campo = str(linha.get("campo") or "")
                valor_humano = str(valores_humanos.get(campo, "")).strip()
                if not valor_humano:
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Entry point da aba Extração Tripla (UX-V-2.4)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Baixar lote", "glyph": "download",
         "title": "ZIP com 10 arquivos"},
        {"label": "Salvar validações", "primary": True, "glyph": "validar",
         "title": "Persistir flags humanas"},
    ])

    del dados, mes_selecionado, pessoa, ctx

    # CSS dedicado da página (padrão Onda M).
    st.markdown(
        minificar(carregar_css_pagina("extracao_tripla")),
        unsafe_allow_html=True,
    )

    # UX-U-03: page-header canônico via helper.
    from src.dashboard.componentes.page_header import renderizar_page_header
    st.markdown(
        renderizar_page_header(
            titulo="EXTRAÇÃO TRIPLA",
            subtitulo=(
                "Cada arquivo passa por dois extratores -- ETL determinístico e "
                "Claude Opus agentic. A coluna humana chega pré-preenchida com o "
                "consenso; você só edita as divergências e envia."
            ),
            sprint_tag="UX-V-2.4",
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
                "popular `data/output/validacao_arquivos.csv`. "
                "Quando o pipeline de inbox processa um novo arquivo, ele é "
                "extraído por **ETL determinístico** e por "
                "**Claude Opus agentic**. Divergências aparecem aqui para "
                "validação humana.",
            ),
            unsafe_allow_html=True,
        )
        return

    df_grupos = _agrupar_por_arquivo(df)

    # Estado de seleção (default: primeiro arquivo)
    arquivo_selecionado = st.session_state.get(
        CHAVE_SESSION_ARQUIVO_SELECIONADO, None
    )
    if not arquivo_selecionado and not df_grupos.empty:
        arquivo_selecionado = str(df_grupos.iloc[0]["caminho_relativo"])
        st.session_state[CHAVE_SESSION_ARQUIVO_SELECIONADO] = arquivo_selecionado

    # KPIs no topo
    n_total = len(df_grupos)
    n_aprovado = int((df_grupos["status_humano"] == "aprovado").sum())
    n_revisao = max(0, n_total - n_aprovado)
    media_paridade = (
        float(df_grupos["paridade_pct"].mean()) if not df_grupos.empty else 0.0
    )
    n_divergencias = int(df_grupos["n_divergencias"].sum())

    st.markdown(
        _kpis_header_html(media_paridade, n_divergencias, n_revisao, n_total),
        unsafe_allow_html=True,
    )

    # Layout 2-col: lista esquerda | painel direito (cabeçalho + tabela tripla)
    col_lista, col_painel = st.columns([1, 3])

    with col_lista:
        # Selectbox Streamlit nativo para seleção real (a lista HTML é visual)
        rotulos = [
            f"{Path(str(g['caminho_relativo'])).name} ({g['paridade_pct']:.0f}%)"
            for _, g in df_grupos.iterrows()
        ]
        caminhos = [str(g["caminho_relativo"]) for _, g in df_grupos.iterrows()]
        idx_default = 0
        if arquivo_selecionado in caminhos:
            idx_default = caminhos.index(arquivo_selecionado)
        idx = st.selectbox(
            "Arquivo",
            range(len(rotulos)),
            index=idx_default,
            format_func=lambda i: rotulos[i],
            label_visibility="collapsed",
        )
        arquivo_selecionado = caminhos[idx]
        st.session_state[CHAVE_SESSION_ARQUIVO_SELECIONADO] = arquivo_selecionado

        st.markdown(
            _lista_arquivos_html(df_grupos, arquivo_selecionado),
            unsafe_allow_html=True,
        )

    with col_painel:
        df_arquivo = df[df["caminho_relativo"] == arquivo_selecionado]
        sha8 = (
            str(df_arquivo["sha8_arquivo"].iloc[0])
            if not df_arquivo.empty
            else ""
        )

        st.markdown(
            _tabela_tripla_html(df_arquivo, extractor_versao=f"sha8 {sha8}"),
            unsafe_allow_html=True,
        )

        # Form de persistência abaixo da tabela visual
        _form_validar_arquivo(df_arquivo, sha8, caminho_csv)


# "Onde dois extratores divergem, o humano decide."
#  -- princípio V-2.4 da triangulação
