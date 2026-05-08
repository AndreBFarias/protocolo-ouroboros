"""Página IRPF — UX-RD-14 + UX-V-3.4 (paridade visual com mockup 15-irpf.html).

Layout em grid 1fr / 380px:

* **Esquerda** — 8 categorias canônicas IRPF (compiladas das tags geradas
  por ``src/transform/irpf_tagger.py``). Cada linha mostra label uppercase,
  descrição, barra de completude colorida (verde >=90%, amarelo 70-89%,
  vermelho <70%), valor mono tabular, badge de confiança e botões
  expand/baixar inline.
* **Direita** — card "Pacote IRPF <ano>" com totalizador, lista dos
  4 artefatos a serem gerados, checklist de 5 itens e botão "Gerar pacote",
  que invoca ``src/exports/pacote_irpf.gerar_pacote(ano)``.

Sprint UX-V-3.4 (2026-05-08):
* Ano agora vem do filtro global (``ctx["periodo"]``); selectbox local
  proeminente foi rebaixado a fallback discreto (label colapsado).
* Título exibe ``IRPF {ano}`` literalmente (mockup 15-irpf.html linha 110).
* Barras coloridas por threshold de completude.
* Botões expand/baixar inline por categoria (visual; ação real é
  "Gerar pacote" no card lateral).
* Checklist lateral com 5 itens estruturados (mockup linhas 137-141).

A regra ``forbidden`` da spec UX-RD-14 permanece literal: **só lê tags reais**
do tagger. As categorias ``dedutivel_educacional``, ``previdencia_privada``
e ``doacao_dedutivel`` ainda não têm regex no tagger atual; aparecem zeradas
no painel para que o redesign exponha a estrutura canônica completa, sem
inventar valores.

Função pública preservada:
* ``renderizar(dados, periodo, pessoa, ctx)`` — entrypoint do dispatcher.
"""

from __future__ import annotations

import datetime as _dt

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.ui import carregar_css_pagina
from src.dashboard.dados import formatar_moeda
from src.dashboard.tema import CORES
from src.exports.pacote_irpf import (
    CATEGORIAS_IRPF,
    compilar_eventos,
    compilar_totais,
    gerar_pacote,
)

# Metadados visuais por categoria (cor da borda esquerda + descrição
# narrativa). Espelha o mockup 15-irpf.html mas sem inventar valores --
# os números vêm de ``compilar_totais`` em cima do extrato real.
META_CATEGORIAS: dict[str, dict[str, str]] = {
    "rendimento_tributavel": {
        "cor": CORES["positivo"],
        "descricao": "Salários, pró-labore, aluguéis recebidos.",
    },
    "rendimento_isento": {
        "cor": CORES["info"],
        "descricao": "Bolsa NEES/UFAL, FGTS, rendimentos de poupança.",
    },
    "dedutivel_medico": {
        "cor": CORES["alerta"],
        "descricao": "Consultas, exames, plano de saúde, dentista.",
    },
    "dedutivel_educacional": {
        "cor": CORES["info"],
        "descricao": "Mensalidades de educação formal (ensino regular).",
    },
    "previdencia_privada": {
        "cor": CORES["positivo"],
        "descricao": "Contribuições PGBL elegíveis a dedução.",
    },
    "imposto_pago": {
        "cor": CORES["negativo"],
        "descricao": "DARF, DAS MEI, IRRF retido na fonte.",
    },
    "inss_retido": {
        "cor": CORES["alerta"],
        "descricao": "Contribuição previdenciária retida no contracheque.",
    },
    "doacao_dedutivel": {
        "cor": CORES["info"],
        "descricao": "Fundo da Criança, Idoso, Cultura, ECA.",
    },
}


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página IRPF (UX-RD-14 + UX-V-3.4)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes

    renderizar_grupo_acoes([
        {"label": "Recalcular", "glyph": "refresh",
         "title": "Recalcular IRPF do ano"},
        {"label": "Gerar pacote", "primary": True, "glyph": "download",
         "title": "DEC + DARF + PDFs"},
    ])

    st.markdown(
        minificar(carregar_css_pagina("irpf")),
        unsafe_allow_html=True,
    )

    extrato = dados.get("extrato") if isinstance(dados, dict) else None
    anos_disponiveis = _extrair_anos(extrato)

    # Ano-base: 1) ctx["periodo"] se contiver ano válido, 2) ano corrente,
    # 3) selectbox secundário só aparece se houver múltiplos anos no extrato.
    ano_global = _ano_do_periodo(ctx)
    ano_corrente = _dt.date.today().year
    ano_default = ano_global or (
        anos_disponiveis[0] if anos_disponiveis else str(ano_corrente)
    )

    if not anos_disponiveis:
        st.markdown(_page_header_html(ano_default, 0, 0, 0.0), unsafe_allow_html=True)
        st.info("Sem extrato carregado para análise IRPF.")
        return

    # Selectbox secundário: label colapsado, só visível se houver mais de
    # um ano no extrato. Default é o ano global ou o mais recente.
    if len(anos_disponiveis) > 1:
        try:
            idx_default = anos_disponiveis.index(ano_default)
        except ValueError:
            idx_default = 0
        ano_selecionado = st.selectbox(
            "Trocar ano-calendário",
            anos_disponiveis,
            index=idx_default,
            key="irpf_ano",
            label_visibility="collapsed",
        )
    else:
        ano_selecionado = anos_disponiveis[0]

    ano_int = int(ano_selecionado)

    df_ano = extrato[extrato["mes_ref"].astype(str).str.startswith(ano_selecionado)].copy()
    eventos = compilar_eventos(df_ano)
    totais = compilar_totais(eventos)

    soma_total = round(sum(info["valor"] for info in totais.values()), 2)
    n_eventos = len(eventos)
    n_categorias_ativas = sum(1 for info in totais.values() if info["count"] > 0)

    st.markdown(
        _page_header_html(ano_selecionado, n_eventos, n_categorias_ativas, soma_total),
        unsafe_allow_html=True,
    )

    # Render lista (esquerda) + card sticky (direita) num único bloco HTML
    # para que o grid CSS controle o layout (Streamlit columns quebram o
    # sticky-positioning do card lateral).
    linhas_html = "".join(
        _row_categoria_html(cat, totais.get(cat, {"valor": 0.0, "count": 0}),
                            _calcular_completude(eventos, cat))
        for cat in CATEGORIAS_IRPF
    )
    card_html = _card_pacote_html(ano_int, soma_total, n_eventos, totais, eventos)

    st.markdown(
        minificar(
            f'<div class="irpf-grid">'
            f'<div>{linhas_html}</div>'
            f'{card_html}'
            f'</div>'
        ),
        unsafe_allow_html=True,
    )

    # Botão real (Streamlit) para acionar a geração. O botão "Gerar pacote"
    # do card HTML é puramente visual; o controle interativo precisa ser do
    # Streamlit para disparar callback no servidor.
    if st.button(
        f"Gerar pacote IRPF {ano_int}",
        key=f"irpf_gerar_pacote_{ano_int}",
        type="primary",
        width="stretch",
    ):
        with st.spinner(f"Gerando pacote IRPF {ano_int}..."):
            diretorio = gerar_pacote(ano_int, dados=dados)
        st.success(
            f"Pacote IRPF {ano_int} gerado em `{diretorio}`. "
            "Conteúdo: relatorio.pdf, dados.xlsx, dados.json, originais/."
        )


# ---------------------------------------------------------------------------
# HTML helpers (UX-V-3.4)
# ---------------------------------------------------------------------------


def _page_header_html(
    ano: str,
    n_eventos: int,
    n_categorias_ativas: int,
    soma_total: float,
) -> str:
    """HTML do page-header UX-V-3.4 (título com ano embutido + sprint-tag + pills).

    O ano-calendário deixa de ser dropdown proeminente (movido para o título,
    ``IRPF {ano}``, alinhamento com mockup 15-irpf.html linha 110). A pill
    ``Ano-base {ano}`` permanece como rótulo redundante na faixa de meta
    para manter contrato de teste UX-RD-14 (test_irpf_page_header_html_canonico).
    """
    if n_categorias_ativas >= 6:
        pill_classe = "pill-d7-graduado"
    elif n_categorias_ativas >= 3:
        pill_classe = "pill-d7-calibracao"
    else:
        pill_classe = "pill-d7-regredindo"
    pill_texto = f"{n_categorias_ativas}/8 categorias com dados"
    total_fmt = formatar_moeda(soma_total)
    return minificar(
        f"""
        <div class="page-header">
          <div>
            <h1 class="page-title">IRPF {ano}</h1>
            <p class="page-subtitle">
              Compilação automática a partir do banco catalogado.
              Cada categoria agrega transações com a mesma classificação
              fiscal (8 tags canônicas). Pacote final reúne PDF, XLSX,
              JSON e cópia dos originais.
            </p>
          </div>
          <div class="page-meta">
            <span class="sprint-tag">UX-RD-14</span>
            <span class="pill pill-humano-aprovado">Ano-base {ano}</span>
            <span class="pill {pill_classe}">{pill_texto}</span>
            <span class="pill pill-d7-graduado">total {total_fmt}</span>
          </div>
        </div>
        """
    )


def _classe_cor_completude(pct: float, count: int) -> str:
    """Classifica a cor da linha conforme completude.

    * verde: completude >= 90%
    * amarelo: 70-89%
    * vermelho: < 70% (com pelo menos 1 evento)
    * neutro: sem dados (count == 0)
    """
    if count == 0:
        return "neutral"
    if pct >= 0.9:
        return "green"
    if pct >= 0.7:
        return "yellow"
    return "red"


def _classe_conf(pct: float, count: int) -> tuple[str, str]:
    """Retorna (classe_css, label_textual) do badge de confiança."""
    if count == 0:
        return ("none", "—")
    if pct >= 0.9:
        return ("high", "≥90%")
    if pct >= 0.7:
        return ("mid", "70-90%")
    return ("low", "<70%")


def _row_categoria_html(
    categoria: str,
    info: dict[str, float],
    completude: float,
) -> str:
    """HTML de uma linha de categoria IRPF (UX-V-3.4).

    Layout grid 5 colunas: nome+desc / barra colorida / valor /
    badge de confiança / botões expand+baixar.
    """
    meta = META_CATEGORIAS.get(categoria, {"cor": CORES["texto_sec"], "descricao": ""})
    descricao = meta["descricao"]
    valor = info.get("valor", 0.0)
    count = int(info.get("count", 0))
    pct = max(0.0, min(1.0, completude))
    pct_int = int(round(pct * 100))
    cor_classe = _classe_cor_completude(pct, count)
    conf_classe, conf_label = _classe_conf(pct, count)
    valor_fmt = formatar_moeda(valor)

    return minificar(
        f"""
        <div class="irpf-row" data-cor="{cor_classe}">
          <div>
            <div class="irpf-tag-name">{categoria}</div>
            <div class="irpf-tag-desc">{descricao}</div>
          </div>
          <div>
            <div class="irpf-bar-label">
              <span>{count} arquivo(s)</span>
              <span>{pct_int}% completude</span>
            </div>
            <div class="irpf-bar"><span style="width: {pct_int}%;"></span></div>
          </div>
          <div class="irpf-val">{valor_fmt}</div>
          <div><span class="irpf-conf {conf_classe}">{conf_label}</span></div>
          <div class="irpf-actions">
            <button type="button" title="Ver arquivos">expand</button>
            <button type="button" title="Baixar evidências">baixar</button>
          </div>
        </div>
        """
    )


def _card_pacote_html(
    ano: int,
    soma_total: float,
    n_eventos: int,
    totais: dict[str, dict[str, float]],
    eventos: list[dict],
) -> str:
    """HTML do card lateral 'Pacote IRPF <ano>' (sticky, 380px).

    Checklist com 5 itens estruturados conforme mockup 15-irpf.html
    linhas 137-141:
    1. 8/8 tags compiladas (categorias com dados reais).
    2. X/Y arquivos validados (eventos com cnpj_cpf).
    3. X categorias com confiança < 70% (count > 0 e pct < 0.7).
    4. Totais batem com soma dos arquivos.
    5. X fornecedores ainda não cruzados com CNPJ.
    """
    total_fmt = formatar_moeda(soma_total)
    n_categorias_ativas = sum(1 for info in totais.values() if info["count"] > 0)
    n_com_cnpj = sum(1 for ev in eventos if ev.get("cnpj_cpf"))
    n_sem_cnpj = max(0, n_eventos - n_com_cnpj)

    # Item 3: categorias com confiança < 70% (count > 0).
    n_baixa_conf = 0
    for cat, info in totais.items():
        cnt = int(info.get("count", 0))
        if cnt == 0:
            continue
        eventos_cat = [ev for ev in eventos if ev.get("tag") == cat]
        com_cnpj_cat = sum(1 for ev in eventos_cat if ev.get("cnpj_cpf"))
        pct_cat = (com_cnpj_cat / cnt) if cnt else 0.0
        if pct_cat < 0.7:
            n_baixa_conf += 1

    # Item 1: 8/8 tags se TODAS as 8 estão presentes (count > 0). Caso
    # contrário, X/8 com aviso.
    if n_categorias_ativas == 8:
        ck1_classe, ck1_mark = "ck-ok", "OK"
        ck1_texto = "8/8 tags compiladas"
    else:
        ck1_classe, ck1_mark = "ck-warn", "!"
        ck1_texto = f"{n_categorias_ativas}/8 tags compiladas"

    # Item 2: validados por humano = eventos com cnpj_cpf preenchido.
    if n_eventos == 0:
        ck2_classe, ck2_mark = "ck-warn", "!"
        ck2_texto = "0/0 arquivos validados"
    elif n_com_cnpj == n_eventos:
        ck2_classe, ck2_mark = "ck-ok", "OK"
        ck2_texto = f"{n_com_cnpj}/{n_eventos} arquivos validados"
    else:
        ck2_classe, ck2_mark = "ck-warn", "!"
        ck2_texto = f"{n_com_cnpj}/{n_eventos} arquivos validados"

    # Item 3: confiança baixa.
    if n_baixa_conf == 0:
        ck3_classe, ck3_mark = "ck-ok", "OK"
        ck3_texto = "0 categorias com confiança < 70%"
    else:
        ck3_classe, ck3_mark = "ck-warn", "!"
        ck3_texto = f"{n_baixa_conf} categorias com confiança < 70%"

    # Item 4: totais batem com soma dos eventos. Por construção
    # ``compilar_totais`` é a soma direta -- verificação trivial.
    soma_eventos = sum(abs(ev.get("valor", 0.0)) for ev in eventos)
    diff = abs(soma_eventos - soma_total)
    if diff < 0.01:
        ck4_classe, ck4_mark = "ck-ok", "OK"
        ck4_texto = "totais batem com soma dos arquivos"
    else:
        ck4_classe, ck4_mark = "ck-fail", "X"
        ck4_texto = f"divergência de {formatar_moeda(diff)} entre totais e arquivos"

    # Item 5: fornecedores sem CNPJ.
    if n_sem_cnpj == 0:
        ck5_classe, ck5_mark = "ck-ok", "OK"
        ck5_texto = "todos fornecedores cruzados com CNPJ"
    else:
        ck5_classe, ck5_mark = "ck-warn", "!"
        ck5_texto = f"{n_sem_cnpj} fornecedor(es) sem CNPJ cruzado"

    return minificar(
        f"""
        <aside class="irpf-export-card">
          <h3>Pacote IRPF {ano}</h3>
          <div class="irpf-total">{total_fmt}</div>
          <div class="irpf-total-sub">soma das tags · {n_eventos} eventos</div>

          <h4>Será gerado em data/aplicacoes/irpf_{ano}/</h4>
          <ul class="irpf-files">
            <li><span>relatorio.pdf</span><code>PDF</code></li>
            <li><span>dados.xlsx</span><code>XLSX</code></li>
            <li><span>dados.json</span><code>JSON</code></li>
            <li><span>originais/</span><code>DIR</code></li>
          </ul>

          <h4>Checklist</h4>
          <ul class="irpf-checklist">
            <li><span class="ck-mark {ck1_classe}">[{ck1_mark}]</span><span>{ck1_texto}</span></li>
            <li><span class="ck-mark {ck2_classe}">[{ck2_mark}]</span><span>{ck2_texto}</span></li>
            <li><span class="ck-mark {ck3_classe}">[{ck3_mark}]</span><span>{ck3_texto}</span></li>
            <li><span class="ck-mark {ck4_classe}">[{ck4_mark}]</span><span>{ck4_texto}</span></li>
            <li><span class="ck-mark {ck5_classe}">[{ck5_mark}]</span><span>{ck5_texto}</span></li>
          </ul>

          <p class="irpf-saved-path">
            Salva em <code>data/aplicacoes/irpf_{ano}/</code>
          </p>
        </aside>
        """
    )


# ---------------------------------------------------------------------------
# Funções puras (testáveis)
# ---------------------------------------------------------------------------


def _extrair_anos(extrato: pd.DataFrame | None) -> list[str]:
    """Extrai anos disponíveis do extrato em ordem decrescente."""
    if extrato is None or extrato.empty:
        return []
    if "mes_ref" not in extrato.columns:
        return []
    meses = extrato["mes_ref"].dropna().astype(str).unique().tolist()
    anos = sorted({m[:4] for m in meses if len(m) >= 4}, reverse=True)
    return anos


def _ano_do_periodo(ctx: dict | None) -> str | None:
    """Extrai ano (4 dígitos) do filtro global ``ctx["periodo"]``.

    Suporta os formatos emitidos por ``filtrar_por_periodo``:
    * Ano: ``"2026"``.
    * Mês: ``"2026-04"`` (4 primeiros chars).
    * Dia: ``"15/04/2026"`` (4 últimos chars).

    Retorna ``None`` quando não consegue extrair ano válido.
    """
    if not ctx:
        return None
    periodo = str(ctx.get("periodo", "")).strip()
    if not periodo:
        return None
    # Formato dia DD/MM/YYYY -- ano nos 4 últimos.
    if len(periodo) == 10 and periodo[2] == "/" and periodo[5] == "/":
        candidato = periodo[-4:]
        return candidato if candidato.isdigit() else None
    # Demais formatos (ano ou mês): 4 primeiros chars.
    candidato = periodo[:4]
    return candidato if candidato.isdigit() else None


def _calcular_completude(eventos: list[dict], categoria: str) -> float:
    """Calcula fração de eventos da categoria com ``cnpj_cpf`` preenchido.

    Retorna 0.0 quando a categoria não tem nenhum evento (evita divisão
    por zero e mantém barra zerada visualmente).
    """
    da_categoria = [ev for ev in eventos if ev.get("tag") == categoria]
    if not da_categoria:
        return 0.0
    com_cnpj = sum(1 for ev in da_categoria if ev.get("cnpj_cpf"))
    return com_cnpj / len(da_categoria)


# "Neste mundo, nada é certo, exceto a morte e os impostos." -- Benjamin Franklin
