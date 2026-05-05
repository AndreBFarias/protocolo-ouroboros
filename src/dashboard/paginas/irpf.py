"""Página IRPF — UX-RD-14.

Reescrita conforme mockup ``novo-mockup/mockups/15-irpf.html``.

Layout em grid 1fr / 380px:

* **Esquerda** — 8 categorias canônicas IRPF (compiladas das tags
  geradas por ``src/transform/irpf_tagger.py``). Cada linha mostra
  label uppercase, valor mono tabular, contagem de transações e barra
  de "completude" (proxy: fração de transações com ``cnpj_cpf``
  preenchido — comprovante mais robusto).
* **Direita** — card "Pacote IRPF <ano>" com totalizador, lista dos
  4 artefatos a serem gerados e botão "Gerar pacote", que invoca
  ``src/exports/pacote_irpf.gerar_pacote(ano)``.

A regra ``forbidden`` da spec UX-RD-14 é literal: **só lê tags reais**
do tagger. As categorias ``dedutivel_educacional``, ``previdencia_privada``
e ``doacao_dedutivel`` ainda não têm regex no tagger atual; elas
aparecem zeradas no painel para que o redesign exponha a estrutura
canônica completa, sem inventar valores.

Função pública preservada:
* ``renderizar(dados, periodo, pessoa, ctx)`` — entrypoint do dispatcher.

Assinatura de antes (``renderizar(dados, periodo, pessoa, ctx)``)
permanece inalterada -- ver ``src/dashboard/app.py`` linha ~512.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
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
    """Renderiza a página IRPF com 8 categorias + card de pacote anual."""
    extrato = dados.get("extrato") if isinstance(dados, dict) else None
    anos_disponiveis = _extrair_anos(extrato)

    if not anos_disponiveis:
        st.markdown(_page_header_html("--", 0, 0, 0.0), unsafe_allow_html=True)
        st.info("Sem extrato carregado para análise IRPF.")
        return

    ano_selecionado = st.selectbox(
        "Ano-calendário",
        anos_disponiveis,
        index=0,
        key="irpf_ano",
    )
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

    col_categorias, col_pacote = st.columns([1.0, 0.42])

    with col_categorias:
        for categoria in CATEGORIAS_IRPF:
            info = totais.get(categoria, {"valor": 0.0, "count": 0})
            completude = _calcular_completude(eventos, categoria)
            st.markdown(
                _row_categoria_html(categoria, info, completude),
                unsafe_allow_html=True,
            )

    with col_pacote:
        st.markdown(
            _card_pacote_html(ano_int, soma_total, n_eventos, totais, eventos),
            unsafe_allow_html=True,
        )

        # Botão real (Streamlit) para acionar a geração. O HTML do mockup
        # acima é só visual; o controle interativo precisa ser do
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
# HTML helpers (UX-RD-14)
# ---------------------------------------------------------------------------


def _page_header_html(
    ano: str,
    n_eventos: int,
    n_categorias_ativas: int,
    soma_total: float,
) -> str:
    """HTML do page-header UX-RD-14 (título + sprint-tag + pill ano)."""
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
            <h1 class="page-title">IRPF</h1>
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


def _row_categoria_html(
    categoria: str,
    info: dict[str, float],
    completude: float,
) -> str:
    """HTML de uma linha de categoria IRPF.

    Layout: label uppercase + descrição + barra de completude + valor
    mono tabular + count + sinal narrativo de comprovante (OK/parcial/falta).
    """
    meta = META_CATEGORIAS.get(categoria, {"cor": CORES["texto_sec"], "descricao": ""})
    cor = meta["cor"]
    descricao = meta["descricao"]
    valor = info.get("valor", 0.0)
    count = int(info.get("count", 0))
    pct = max(0.0, min(1.0, completude))
    pct_int = int(round(pct * 100))

    # Sinal de comprovante: "OK" se ao menos 80% dos eventos têm
    # CNPJ/CPF; "parcial" entre 30 e 80; "falta" abaixo de 30 (e count>0).
    if count == 0:
        sinal_label = "sem dados"
        sinal_cor = CORES["texto_sec"]
    elif pct >= 0.8:
        sinal_label = "comprovante: OK"
        sinal_cor = CORES["positivo"]
    elif pct >= 0.3:
        sinal_label = "comprovante: parcial"
        sinal_cor = CORES["alerta"]
    else:
        sinal_label = "comprovante: falta"
        sinal_cor = CORES["negativo"]

    valor_fmt = formatar_moeda(valor)

    return minificar(
        f"""
        <div style="
            background: {CORES['card_fundo']};
            border: 1px solid {CORES['texto_sec']}33;
            border-left: 4px solid {cor};
            border-radius: 8px;
            padding: 14px 18px;
            margin: 6px 0;
            display: grid;
            grid-template-columns: 1.2fr 1fr 0.6fr 0.6fr;
            gap: 16px;
            align-items: center;
        ">
          <div>
            <div style="
                font-family: ui-monospace, 'JetBrains Mono', monospace;
                font-size: 13px;
                color: {CORES['texto']};
                text-transform: uppercase;
                letter-spacing: 0.04em;
                font-weight: 600;
            ">{categoria}</div>
            <div style="
                font-size: 11px;
                color: {CORES['texto_sec']};
                margin-top: 2px;
            ">{descricao}</div>
          </div>
          <div>
            <div style="
                font-family: ui-monospace, 'JetBrains Mono', monospace;
                font-size: 11px;
                color: {CORES['texto_sec']};
                margin-bottom: 4px;
                display: flex;
                justify-content: space-between;
            ">
              <span>{count} registro(s)</span>
              <span>{pct_int}% completude</span>
            </div>
            <div style="
                height: 6px;
                background: {CORES['texto_sec']}22;
                border-radius: 3px;
                overflow: hidden;
            ">
              <span style="
                  display: block;
                  height: 100%;
                  width: {pct_int}%;
                  background: {cor};
              "></span>
            </div>
          </div>
          <div style="
              font-family: ui-monospace, 'JetBrains Mono', monospace;
              font-size: 16px;
              font-weight: 500;
              text-align: right;
              color: {CORES['texto']};
              font-variant-numeric: tabular-nums;
          ">{valor_fmt}</div>
          <div style="
              text-align: right;
              font-family: ui-monospace, 'JetBrains Mono', monospace;
              font-size: 11px;
              color: {sinal_cor};
              border: 1px solid {sinal_cor}55;
              border-radius: 4px;
              padding: 3px 8px;
              white-space: nowrap;
          ">{sinal_label}</div>
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
    """HTML do card lateral 'Pacote IRPF <ano>' (sticky, 380px)."""
    total_fmt = formatar_moeda(soma_total)
    n_categorias_ativas = sum(1 for info in totais.values() if info["count"] > 0)
    n_com_cnpj = sum(1 for ev in eventos if ev.get("cnpj_cpf"))
    n_sem_cnpj = max(0, n_eventos - n_com_cnpj)
    pct_validados = (n_com_cnpj / n_eventos * 100) if n_eventos else 100

    if n_categorias_ativas >= 6:
        ck1_cor = CORES["positivo"]
        ck1_glyph = "OK"
    else:
        ck1_cor = CORES["alerta"]
        ck1_glyph = "!"

    if pct_validados >= 80:
        ck2_cor = CORES["positivo"]
        ck2_glyph = "OK"
    else:
        ck2_cor = CORES["alerta"]
        ck2_glyph = "!"

    if n_sem_cnpj == 0:
        ck3_cor = CORES["positivo"]
        ck3_glyph = "OK"
    else:
        ck3_cor = CORES["alerta"]
        ck3_glyph = "!"

    return minificar(
        f"""
        <aside style="
            background: {CORES['card_fundo']};
            border: 1px solid {CORES['texto_sec']}33;
            border-radius: 8px;
            padding: 20px;
            position: sticky;
            top: 16px;
        ">
          <h3 style="
              font-family: ui-monospace, 'JetBrains Mono', monospace;
              font-size: 13px;
              letter-spacing: 0.04em;
              margin: 0 0 8px;
              color: {CORES['destaque']};
              text-transform: uppercase;
          ">Pacote IRPF {ano}</h3>
          <div style="
              font-family: ui-monospace, 'JetBrains Mono', monospace;
              font-size: 28px;
              font-weight: 500;
              color: {CORES['destaque']};
              font-variant-numeric: tabular-nums;
          ">{total_fmt}</div>
          <div style="
              font-family: ui-monospace, 'JetBrains Mono', monospace;
              font-size: 11px;
              color: {CORES['texto_sec']};
              margin-top: 4px;
          ">soma das tags · {n_eventos} eventos</div>

          <h4 style="
              font-family: ui-monospace, 'JetBrains Mono', monospace;
              font-size: 11px;
              letter-spacing: 0.08em;
              text-transform: uppercase;
              color: {CORES['texto_sec']};
              margin: 18px 0 8px;
          ">Será gerado em data/aplicacoes/irpf_{ano}/</h4>
          <ul style="
              list-style: none;
              padding: 8px 12px;
              margin: 0 0 16px;
              background: {CORES['fundo']};
              border: 1px solid {CORES['texto_sec']}22;
              border-radius: 4px;
              font-family: ui-monospace, 'JetBrains Mono', monospace;
              font-size: 11px;
          ">
            <li style="display:flex;justify-content:space-between;
              color:{CORES['texto_sec']};padding:3px 0;">
              <span>relatorio.pdf</span><code style="color:{CORES['destaque']};">PDF</code>
            </li>
            <li style="display:flex;justify-content:space-between;
              color:{CORES['texto_sec']};padding:3px 0;">
              <span>dados.xlsx</span><code style="color:{CORES['destaque']};">XLSX</code>
            </li>
            <li style="display:flex;justify-content:space-between;
              color:{CORES['texto_sec']};padding:3px 0;">
              <span>dados.json</span><code style="color:{CORES['destaque']};">JSON</code>
            </li>
            <li style="display:flex;justify-content:space-between;
              color:{CORES['texto_sec']};padding:3px 0;">
              <span>originais/</span><code style="color:{CORES['destaque']};">DIR</code>
            </li>
          </ul>

          <h4 style="
              font-family: ui-monospace, 'JetBrains Mono', monospace;
              font-size: 11px;
              letter-spacing: 0.08em;
              text-transform: uppercase;
              color: {CORES['texto_sec']};
              margin: 0 0 6px;
          ">Checklist</h4>
          <ul style="
              list-style: none;
              padding: 0;
              margin: 0 0 12px;
              font-size: 12px;
              color: {CORES['texto']};
          ">
            <li style="padding:3px 0;">
              <span style="color:{ck1_cor};font-weight:bold;margin-right:6px;">[{ck1_glyph}]</span>
              {n_categorias_ativas}/8 categorias com dados reais
            </li>
            <li style="padding:3px 0;">
              <span style="color:{ck2_cor};font-weight:bold;margin-right:6px;">[{ck2_glyph}]</span>
              {n_com_cnpj}/{n_eventos} eventos com CNPJ/CPF ({pct_validados:.0f}%)
            </li>
            <li style="padding:3px 0;">
              <span style="color:{ck3_cor};font-weight:bold;margin-right:6px;">[{ck3_glyph}]</span>
              {n_sem_cnpj} eventos sem identificador da fonte
            </li>
          </ul>
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
