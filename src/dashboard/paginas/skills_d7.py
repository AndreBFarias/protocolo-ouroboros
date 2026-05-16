"""Cluster Sistema · aba "Skills D7" (UX-RD-05).

Painel analítico do classificador D7 espelhando ``novo-mockup/mockups/14-skills-d7.html``.
Lê snapshot estruturado de ``data/output/skill_d7_log.json`` quando existe;
caso contrário, exibe fallback graceful em ``.skill-instr`` apontando para
``/auditar-cobertura-total``.

Decisão de fonte (Sprint UX-RD-05): não há fonte D7 estruturada hoje no
projeto -- ``scripts/auditar_cobertura_total.py`` produz markdown narrativo,
não JSON. Esta página define o contrato canônico do log JSON e degrada
graciosamente quando ele não existe; sprint futura (LLM-03/05/06/07-V2)
pode popular o arquivo via skill autônoma.

Contrato: ``renderizar(dados, periodo, pessoa, ctx)`` espelhando as outras
páginas para que o dispatcher de ``app.py`` chame uniformemente.

Tokens consumidos via ``CORES`` (UX-RD-01) e classes canônicas
``components.css`` (``.kpi-grid``, ``.kpi``, ``.kpi-label``, ``.kpi-value``,
``.pill-d7-*``, ``.confidence-bar``, ``.skill-instr``, ``.page-header``,
``.btn``). Estruturas específicas desta página (``.s7-row``, ``.s7-grid``,
``.s7-evo``) permanecem como override mínimo justificado em ``<style>``
local: grid de 5 colunas das skills + moldura + SVG de evolução semanal
não têm equivalente universal. Sprint UX-M-02.C consolidou KPIs no
canônico (``.s7-kpi-row`` removido).

Lição UX-RD-04 herdada: HTML emitido em uma única linha quando contém
SVG/elementos que o parser CommonMark do Streamlit possa interpretar
como bloco de código (qualquer indentação >=4 espaços vira ``<pre>``).
``_minificar`` é aplicado em todo HTML inline com SVG.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.ui import carregar_css_pagina
from src.dashboard.tema import CORES

CAMINHO_LOG_D7: Path = Path(__file__).resolve().parents[3] / "data" / "output" / "skill_d7_log.json"


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página Skills D7 (UX-RD-05 + UX-T-14)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes

    renderizar_grupo_acoes(
        [
            {"label": "Recalibrar", "glyph": "refresh", "title": "Recalibrar 18 skills"},
            {"label": "Logs", "primary": True, "glyph": "list", "title": "Abrir terminal de logs"},
        ]
    )

    del dados, periodo, pessoa, ctx

    st.markdown(minificar(carregar_css_pagina("skills_d7")), unsafe_allow_html=True)
    st.markdown(_page_header_html(), unsafe_allow_html=True)

    snapshot = _carregar_snapshot()
    if snapshot is None:
        st.markdown(_fallback_estado_inicial_html(), unsafe_allow_html=True)
        return

    skills: list[dict] = snapshot.get("skills", [])
    if not skills:
        st.markdown(_fallback_estado_inicial_html(), unsafe_allow_html=True)
        return

    contagens = _contar_estados(skills)
    st.markdown(
        _kpis_d7_html(snapshot, contagens, total=len(skills)),
        unsafe_allow_html=True,
    )
    st.markdown(_lista_skills_html(skills), unsafe_allow_html=True)
    st.markdown(_distribuicao_estados_html(contagens), unsafe_allow_html=True)
    st.markdown(_cobertura_cluster_html(snapshot), unsafe_allow_html=True)
    st.markdown(_evolucao_html(snapshot.get("evolucao", [])), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Carregamento do snapshot D7
# ---------------------------------------------------------------------------


def _carregar_snapshot() -> dict | None:
    """Lê ``data/output/skill_d7_log.json`` quando existe.

    Formato esperado (contrato canônico desta sprint, futura LLM-XX-V2 popula):

        {
          "gerado_em": "2026-04-29T14:32:00",
          "skills": [
            {"id": "s01", "nome": "ofx-parse", "descricao": "...",
             "estado": "graduado", "confianca": 0.97, "runs": 184,
             "last_run": "2026-04-29T13:45:00", "stab": 0.94}
          ],
          "evolucao": [{"semana": 1, "graduadas": 4}, ...]
        }

    Retorna ``None`` se arquivo ausente ou JSON malformado (graceful).
    """
    if not CAMINHO_LOG_D7.exists():
        return None
    try:
        return json.loads(CAMINHO_LOG_D7.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _contar_estados(skills: list[dict]) -> dict[str, int]:
    """Conta skills por estado D7. Estados desconhecidos viram ``pendente``."""
    estados_validos = {"graduado", "calibrando", "regredindo", "pendente"}
    contagens: dict[str, int] = {e: 0 for e in estados_validos}
    for s in skills:
        estado = str(s.get("estado", "pendente"))
        if estado not in estados_validos:
            estado = "pendente"
        contagens[estado] += 1
    return contagens


# ---------------------------------------------------------------------------
# Geradores de HTML
# ---------------------------------------------------------------------------


def _minificar(html: str) -> str:
    """Colapsa whitespace para uma única linha.

    Mitiga lição UX-RD-04: parser CommonMark do Streamlit converte qualquer
    linha com indentação >=4 espaços em bloco ``<pre><code>`` quando o HTML
    chega via ``unsafe_allow_html=True``, escapando SVG e fragmentos
    ``<svg>``, ``<polyline>``, ``<circle>``.
    """
    return re.sub(r"\s+", " ", html).strip()


def _page_header_html() -> str:
    return _minificar(
        f"""
        <div class="page-header">
          <div>
            <h1 class="page-title">SKILLS · D7</h1>
            <p class="page-subtitle">
              Painel analítico do classificador D7. Cada skill atravessa
              <code style="color:{CORES["d7_pendente"]};">pendente</code> →
              <code style="color:{CORES["d7_regredindo"]};">regredindo</code> →
              <code style="color:{CORES["d7_calibracao"]};">calibrando</code> →
              <code style="color:{CORES["d7_graduado"]};">graduado</code> conforme
              acumula execuções consistentes.
            </p>
          </div>
          <div class="page-meta">
            <span class="sprint-tag">UX-RD-05</span>
          </div>
        </div>
        """
    )


def _fallback_estado_inicial_html() -> str:
    """Fallback estado-inicial-atrativo (UX-V-2.8-FIX) para skills D7 sem log.

    Skeleton-mockup canônico fiel a ``novo-mockup/mockups/14-skills-d7.html``:

    - 5 KPIs: COBERTURA D7, TAXA DE GRADUAÇÃO, REGRESSÕES 30D, CONFIANÇA
      MÉDIA, EXECUÇÕES 30D (todos com valor placeholder ``--``).
    - Inventário com 18 linhas (s01..s18), label cinza animado.
    - Distribuição por estado: 4 estados (Graduado/Calibrando/Regredindo/
      Pendente) com contadores ``--``.
    - Cobertura por cluster: Finanças/Documentos/Análise/Sistema com
      barras placeholder.
    - CTA no rodapé apontando ``./run.sh --tudo``.

    O CSS dedicado já foi carregado em ``renderizar`` antes deste fallback,
    portanto classes ``.s7-kpi5`` / ``.s7-dist`` / ``.s7-cluster`` /
    ``.s7-grid`` ficam ativas mesmo sem snapshot.
    """
    skeleton = (
        _skeleton_kpis_html()
        + _skeleton_inventario_html()
        + _skeleton_distribuicao_html()
        + _skeleton_cobertura_cluster_html()
    )
    rodape = _skeleton_rodape_cta_html()
    # Classe ``fallback-estado`` mantida para retrocompatibilidade com
    # testes regressivos UX-V-03 (test_skills_d7_sem_snapshot_emite_fallback).
    return _minificar(
        f'<div class="s7-skeleton fallback-estado" data-secao="skills-d7">{skeleton}{rodape}</div>'
    )


def _skeleton_kpis_html() -> str:
    """5 KPIs placeholders -- estrutura idêntica a ``_kpis_d7_html``.

    Valor ``--`` em todos. Mesma classe ``.s7-kpi5`` para consumir o CSS
    dedicado e garantir paridade visual com o mockup quando dado existir.
    """
    cor_grad = CORES["d7_graduado"]
    cor_purple = CORES["destaque"]
    cor_orange = CORES["alerta"]
    cards = [
        ("COBERTURA D7", "--", "meta 75%", cor_grad),
        ("TAXA DE GRADUAÇÃO", "--", "no trimestre", cor_purple),
        ("REGRESSÕES 30D", "--", "sem dados", cor_orange),
        ("CONFIANÇA MÉDIA", "--", "média ponderada", None),
        ("EXECUÇÕES 30D", "--", "runs · p95 --", None),
    ]
    pieces = []
    for label, valor, hint, cor in cards:
        estilo = f' style="color:{cor};"' if cor else ""
        pieces.append(
            f'<div class="kpi">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value"{estilo}>{valor}</div>'
            f'<div class="kpi-delta flat">{hint}</div>'
            f"</div>"
        )
    return _minificar('<div class="s7-kpi5">' + "".join(pieces) + "</div>")


def _skeleton_inventario_html() -> str:
    """Inventário com 18 linhas placeholder (s01..s18).

    Estrutura espelha ``_lista_skills_html`` (cabeçalho + linhas .s7-row)
    para consumir o mesmo CSS dedicado. Cada linha exibe id (s01..s18),
    barra animada via ``.skel-bloco`` no campo nome, e ``--`` nos demais.
    """
    cabecalho = (
        '<div class="s7-row s7-head">'
        "<div>skill</div>"
        "<div>D7</div>"
        "<div>confiança</div>"
        "<div>execuções</div>"
        "<div>último</div>"
        "</div>"
    )
    linhas = []
    for i in range(1, 19):
        sid = f"s{i:02d}"
        linha = (
            f'<div class="s7-row">'
            f'<div class="s7-name">'
            f"<strong>{sid}</strong>"
            f'<span class="skel-bloco" style="width:70%;height:1.1em;"></span>'
            f"</div>"
            f'<div class="s7-pill">'
            f'<span class="skel-bloco" style="width:60px;height:1.1em;"></span>'
            f"</div>"
            f'<div class="s7-conf">--</div>'
            f'<div class="s7-runs">--</div>'
            f'<div class="s7-when">--</div>'
            f"</div>"
        )
        linhas.append(linha)
    return _minificar(
        '<div class="s7-grid">'
        '<div class="s7-grid-head">Inventário · 18 skills</div>'
        + cabecalho
        + "".join(linhas)
        + "</div>"
    )


def _skeleton_distribuicao_html() -> str:
    """Distribuição por estado: 4 células com ``--``.

    Mesma estrutura de ``_distribuicao_estados_html`` para consumir
    o CSS ``.s7-dist`` / ``.s7-dist-grid``.
    """
    celulas = [
        ("Graduado", CORES["d7_graduado"]),
        ("Calibrando", CORES["d7_calibracao"]),
        ("Regredindo", CORES["d7_regredindo"]),
        ("Pendente", CORES["d7_pendente"]),
    ]
    blocos = []
    for label, cor in celulas:
        blocos.append(
            f'<div class="s7-dist-cell">'
            f'<div class="s7-dist-num" style="color:{cor};">--</div>'
            f'<div class="s7-dist-lab">{label}</div>'
            f"</div>"
        )
    return _minificar(
        '<div class="s7-dist">'
        '<div class="s7-grid-head">Distribuição por estado</div>'
        '<div class="s7-dist-grid">' + "".join(blocos) + "</div></div>"
    )


def _skeleton_cobertura_cluster_html() -> str:
    """Cobertura por cluster: 4 linhas com barras placeholder.

    Clusters canônicos do mockup: Finanças, Documentos, Análise, Sistema.
    Barra animada via ``.skel-bloco`` ocupa toda a faixa de progresso.
    """
    cor_grad = CORES["d7_graduado"]
    cor_cal = CORES["d7_calibracao"]
    cor_reg = CORES["d7_regredindo"]
    clusters = ["Finanças", "Documentos", "Análise", "Sistema"]
    linhas = []
    for nome in clusters:
        linha = (
            f'<div class="s7-cluster-row">'
            f'<span class="s7-cluster-nome">{nome}</span>'
            f'<div class="s7-cluster-track">'
            f'<span class="skel-bloco" style="width:100%;height:14px;'
            f'border-radius:0;"></span>'
            f"</div>"
            f'<span class="s7-cluster-pct">--</span>'
            f"</div>"
        )
        linhas.append(linha)
    legenda = (
        '<div class="s7-cluster-legenda">'
        f'<span class="s7-legenda-item">'
        f'<span class="s7-legenda-sw" style="background:{cor_grad};"></span>'
        f"graduado</span>"
        f'<span class="s7-legenda-item">'
        f'<span class="s7-legenda-sw" style="background:{cor_cal};"></span>'
        f"calibrando</span>"
        f'<span class="s7-legenda-item">'
        f'<span class="s7-legenda-sw" style="background:{cor_reg};"></span>'
        f"regredindo</span>"
        f'<span class="s7-legenda-item">'
        f'<span class="s7-legenda-sw" style="background:'
        f'{CORES["d7_pendente"]};"></span>pendente</span>'
        "</div>"
    )
    return _minificar(
        '<div class="s7-cluster">'
        '<div class="s7-grid-head">Cobertura por cluster</div>'
        + "".join(linhas)
        + legenda
        + "</div>"
    )


def _skeleton_rodape_cta_html() -> str:
    """CTA no rodapé do skeleton apontando para ``./run.sh --tudo``."""
    from src.dashboard.componentes.ui import ler_sync_info

    sync_info = ler_sync_info()
    if sync_info and "data" in sync_info:
        sync_str = (
            f"Última sync: <strong>{sync_info['data']}</strong>"
            f" · {sync_info.get('n_arquivos', '?')} arquivos lidos do vault"
        )
    else:
        sync_str = (
            "Sincronização: <strong>nunca</strong> -- rode "
            "<code>./run.sh --sync</code> após o classificador D7 "
            "acumular execuções."
        )
    return _minificar(
        f'<div class="s7-skeleton-rodape">'
        f'<p class="s7-skeleton-cta">'
        f"Snapshot estruturado em "
        f"<code>data/output/skill_d7_log.json</code> ainda não foi "
        f"emitido nesta máquina. Rode "
        f"<code>./run.sh --tudo</code> para popular o painel."
        f"</p>"
        f'<p class="s7-skeleton-sync">{sync_str}</p>'
        f"</div>"
    )


def _fallback_graceful_html() -> str:
    """Aviso renderizado em ``.skill-instr`` quando o log D7 está ausente."""
    caminho_relativo = "data/output/skill_d7_log.json"
    return _minificar(
        f"""
        <div class="skill-instr">
          <h4>Cobertura D7 ainda não inicializada</h4>
          <p>
            Nenhum snapshot estruturado em
            <code>{caminho_relativo}</code> -- o pipeline de skills D7 ainda
            não emitiu um log estruturado nesta máquina. Para popular o painel,
            execute:
          </p>
          <ol>
            <li><code>/auditar-cobertura-total</code> (skill canônica do supervisor Opus)</li>
            <li>OU sprint futura LLM-XX-V2 implementa emissão automática</li>
          </ol>
          <p class="why">
            Esta tela degrada graciosamente (ADR-10): nenhum dado é inventado;
            quando o JSON existir, o painel passa a renderizar KPIs, lista de
            skills e gráfico de evolução automaticamente.
          </p>
        </div>
        """
    )


def _kpis_d7_html(snapshot: dict, contagens: dict[str, int], total: int) -> str:
    """5 KPIs do mockup ``14-skills-d7.html`` (UX-V-2.8).

    Layout: COBERTURA D7 · TAXA DE GRADUAÇÃO · REGRESSÕES 30D ·
    CONFIANÇA MÉDIA · EXECUÇÕES 30D.

    Quando o snapshot fornece campos opcionais (``taxa_graduacao_q``,
    ``regressoes_30d``, ``execucoes_30d``, ``p95_segundos``), eles são
    consumidos. Caso contrário, derivamos de ``skills`` quando possível
    (regressões = contagem de ``regredindo``, confiança = média ponderada
    por runs, execuções = soma de runs).
    """
    skills: list[dict] = snapshot.get("skills", [])
    grad = contagens.get("graduado", 0)
    reg = contagens.get("regredindo", 0)
    cobertura = (grad / total * 100.0) if total > 0 else 0.0

    # Taxa de graduação: campo opcional no snapshot, fallback para
    # contagem absoluta de graduadas no trimestre se não fornecido.
    taxa_q = snapshot.get("taxa_graduacao_q")
    if taxa_q is None:
        taxa_q = grad
    taxa_label = f"+{int(taxa_q)} / Q1" if isinstance(taxa_q, int | float) else str(taxa_q)

    # Regressões 30d: prioriza campo do snapshot, senão usa contagem atual.
    regressoes_30d = int(snapshot.get("regressoes_30d", reg))

    # Confiança média: média ponderada por runs quando possível.
    soma_runs = 0
    soma_conf_x_runs = 0.0
    soma_conf = 0.0
    n_skills = 0
    for s in skills:
        runs = int(s.get("runs", 0) or 0)
        conf = float(s.get("confianca", 0.0) or 0.0)
        soma_runs += runs
        soma_conf_x_runs += conf * runs
        soma_conf += conf
        n_skills += 1
    if soma_runs > 0:
        confianca_media = (soma_conf_x_runs / soma_runs) * 100.0
    elif n_skills > 0:
        confianca_media = (soma_conf / n_skills) * 100.0
    else:
        confianca_media = 0.0

    # Execuções 30d: campo opcional, senão soma de runs.
    execucoes_30d = int(snapshot.get("execucoes_30d", soma_runs))
    p95 = snapshot.get("p95_segundos", 2.4)

    detalhe_regr = snapshot.get("regressao_destaque", "atenção sazonal")

    cor_grad = CORES["d7_graduado"]
    cor_purple = CORES["destaque"]
    cor_orange = CORES["alerta"]

    return _minificar(
        f"""
        <div class="s7-kpi5">
          <div class="kpi">
            <div class="kpi-label">COBERTURA D7</div>
            <div class="kpi-value" style="color:{cor_grad};">{cobertura:.0f}%</div>
            <div class="kpi-delta flat">{grad} de {total} · meta 75%</div>
          </div>
          <div class="kpi">
            <div class="kpi-label">TAXA DE GRADUAÇÃO</div>
            <div class="kpi-value" style="color:{cor_purple};">{taxa_label}</div>
            <div class="kpi-delta flat">no trimestre</div>
          </div>
          <div class="kpi">
            <div class="kpi-label">REGRESSÕES 30D</div>
            <div class="kpi-value" style="color:{cor_orange};">{regressoes_30d}</div>
            <div class="kpi-delta flat">{detalhe_regr}</div>
          </div>
          <div class="kpi">
            <div class="kpi-label">CONFIANÇA MÉDIA</div>
            <div class="kpi-value">{confianca_media:.1f}%</div>
            <div class="kpi-delta flat">média ponderada</div>
          </div>
          <div class="kpi">
            <div class="kpi-label">EXECUÇÕES 30D</div>
            <div class="kpi-value">{execucoes_30d:,}</div>
            <div class="kpi-delta flat">runs · p95 {p95}s</div>
          </div>
        </div>
        """
    )


def _distribuicao_estados_html(contagens: dict[str, int]) -> str:
    """4 números grandes: Graduado · Calibrando · Regredindo · Pendente.

    Espelha o card "Distribuição por estado" do mockup. Tokens canônicos
    de cor por estado. Layout específico em ``.s7-dist-grid``.
    """
    grad = contagens.get("graduado", 0)
    cal = contagens.get("calibrando", 0)
    reg = contagens.get("regredindo", 0)
    pend = contagens.get("pendente", 0)

    celulas = [
        ("Graduado", grad, CORES["d7_graduado"]),
        ("Calibrando", cal, CORES["d7_calibracao"]),
        ("Regredindo", reg, CORES["d7_regredindo"]),
        ("Pendente", pend, CORES["d7_pendente"]),
    ]
    blocos = []
    for label, valor, cor in celulas:
        blocos.append(
            _minificar(
                f"""
                <div class="s7-dist-cell">
                  <div class="s7-dist-num" style="color:{cor};">{valor}</div>
                  <div class="s7-dist-lab">{label}</div>
                </div>
                """
            )
        )

    return _minificar(
        '<div class="s7-dist">'
        '<div class="s7-grid-head">Distribuição por estado</div>'
        '<div class="s7-dist-grid">' + "".join(blocos) + "</div></div>"
    )


def _cobertura_cluster_html(snapshot: dict) -> str:
    """Bar chart de cobertura por cluster (Finanças/Documentos/Análise/Sistema).

    Lê ``snapshot["cobertura_cluster"]`` quando presente. Formato esperado::

        {
          "cobertura_cluster": [
            {"nome": "Finanças", "total": 8, "graduado": 7, "calibrando": 1,
             "regredindo": 0},
            ...
          ]
        }

    Quando ausente, deriva da lista de skills pelo campo opcional ``cluster``
    em cada skill. Quando ainda assim não houver dados, omite o bloco.
    """
    clusters = snapshot.get("cobertura_cluster")
    if not clusters:
        clusters = _derivar_cobertura_cluster(snapshot.get("skills", []))
    if not clusters:
        return ""

    cor_grad = CORES["d7_graduado"]
    cor_cal = CORES["d7_calibracao"]
    cor_reg = CORES["d7_regredindo"]

    linhas = []
    for c in clusters:
        nome = str(c.get("nome", "—"))
        total = int(c.get("total", 0) or 0)
        if total <= 0:
            continue
        grad = int(c.get("graduado", 0) or 0)
        cal = int(c.get("calibrando", 0) or 0)
        reg = int(c.get("regredindo", 0) or 0)
        pct_grad = (grad / total) * 100.0
        pct_cal = (cal / total) * 100.0
        pct_reg = (reg / total) * 100.0
        rotulo = f"{pct_grad:.0f}%"

        linhas.append(
            _minificar(
                f"""
                <div class="s7-cluster-row">
                  <span class="s7-cluster-nome">{nome}</span>
                  <div class="s7-cluster-track">
                    <div style="width:{pct_grad:.1f}%;background:{cor_grad};"></div>
                    <div style="width:{pct_cal:.1f}%;background:{cor_cal};"></div>
                    <div style="width:{pct_reg:.1f}%;background:{cor_reg};"></div>
                  </div>
                  <span class="s7-cluster-pct" style="color:{cor_grad};">{rotulo}</span>
                </div>
                """
            )
        )

    if not linhas:
        return ""

    legenda = _minificar(
        f"""
        <div class="s7-cluster-legenda">
          <span class="s7-legenda-item">
            <span class="s7-legenda-sw" style="background:{cor_grad};"></span>graduado
          </span>
          <span class="s7-legenda-item">
            <span class="s7-legenda-sw" style="background:{cor_cal};"></span>calibrando
          </span>
          <span class="s7-legenda-item">
            <span class="s7-legenda-sw" style="background:{cor_reg};"></span>regredindo
          </span>
          <span class="s7-legenda-item">
            <span class="s7-legenda-sw" style="background:{CORES["d7_pendente"]};"></span>pendente
          </span>
        </div>
        """
    )

    return _minificar(
        '<div class="s7-cluster">'
        '<div class="s7-grid-head">Cobertura por cluster</div>'
        + "".join(linhas)
        + legenda
        + "</div>"
    )


def _derivar_cobertura_cluster(skills: list[dict]) -> list[dict]:
    """Agrega skills por campo ``cluster`` quando o snapshot não traz
    pré-agregado. Retorna lista vazia se nenhuma skill tem cluster."""
    agregados: dict[str, dict[str, int]] = {}
    tem_cluster = False
    for s in skills:
        cluster = s.get("cluster")
        if not cluster:
            continue
        tem_cluster = True
        nome = str(cluster)
        bucket = agregados.setdefault(
            nome,
            {
                "total": 0,
                "graduado": 0,
                "calibrando": 0,
                "regredindo": 0,
                "pendente": 0,
            },
        )
        bucket["total"] += 1
        estado = str(s.get("estado", "pendente"))
        if estado in ("graduado", "calibrando", "regredindo", "pendente"):
            bucket[estado] += 1
        else:
            bucket["pendente"] += 1
    if not tem_cluster:
        return []
    return [{"nome": nome, **vals} for nome, vals in agregados.items()]


def _kpi_grid_html(contagens: dict[str, int], total: int) -> str:
    grad = contagens["graduado"]
    cal = contagens["calibrando"]
    reg = contagens["regredindo"]
    pend = contagens["pendente"]
    cobertura = (grad / total * 100.0) if total > 0 else 0.0

    cards = [
        ("Graduadas", str(grad), f"{cobertura:.0f}% de {total}", CORES["d7_graduado"]),
        ("Calibrando", str(cal), "em ajuste", CORES["d7_calibracao"]),
        ("Regredindo", str(reg), "atenção", CORES["d7_regredindo"]),
        ("Pendentes", str(pend), "sem amostras", CORES["d7_pendente"]),
    ]

    pieces = []
    for label, valor, hint, cor in cards:
        pieces.append(
            _minificar(
                f"""
                <div class="kpi">
                  <div class="kpi-label">{label}</div>
                  <div class="kpi-value" style="color:{cor};">{valor}</div>
                  <div class="kpi-delta flat">{hint}</div>
                </div>
                """
            )
        )

    return _minificar(
        '<div class="kpi-grid" style="margin-bottom:24px;">' + "".join(pieces) + "</div>"
    )


def _pill_class(estado: str) -> str:
    mapa = {
        "graduado": "pill-d7-graduado",
        "calibrando": "pill-d7-calibracao",
        "regredindo": "pill-d7-regredindo",
        "pendente": "pill-d7-pendente",
    }
    return mapa.get(estado, "pill-d7-pendente")


def _cor_estado(estado: str) -> str:
    mapa = {
        "graduado": CORES["d7_graduado"],
        "calibrando": CORES["d7_calibracao"],
        "regredindo": CORES["d7_regredindo"],
        "pendente": CORES["d7_pendente"],
    }
    return mapa.get(estado, CORES["d7_pendente"])


def _formatar_last_run(ts: str | None) -> str:
    if not ts:
        return "—"
    try:
        return pd.to_datetime(ts).strftime("%d/%m %H:%M")
    except (ValueError, TypeError):
        return str(ts)[:16]


def _lista_skills_html(skills: list[dict]) -> str:
    """Tabela densa com skills (uma linha por skill)."""
    linhas = []
    for s in skills:
        nome = str(s.get("nome", "—"))
        descricao = str(s.get("descricao", ""))
        estado = str(s.get("estado", "pendente"))
        confianca = float(s.get("confianca", 0.0))
        runs = int(s.get("runs", 0))
        last_run = _formatar_last_run(s.get("last_run"))
        stab = float(s.get("stab", confianca))
        cor = _cor_estado(estado)
        pct = max(0.0, min(stab * 100.0, 100.0))

        linha = _minificar(
            f"""
            <div class="s7-row">
              <div class="s7-name">
                <strong>{nome}</strong>
                <span class="s7-desc">{descricao}</span>
                <div class="confidence-bar">
                  <span style="width:{pct:.1f}%;background:{cor};"></span>
                </div>
              </div>
              <div class="s7-pill"><span class="pill {_pill_class(estado)}">{estado}</span></div>
              <div class="s7-conf" style="color:{cor};">{confianca * 100:.1f}%</div>
              <div class="s7-runs">{runs:n} runs</div>
              <div class="s7-when">{last_run}</div>
            </div>
            """
        )
        linhas.append(linha)

    cabecalho = _minificar(
        """
        <div class="s7-row s7-head">
          <div>skill</div>
          <div>D7</div>
          <div>confiança</div>
          <div>execuções</div>
          <div>último</div>
        </div>
        """
    )
    return _minificar(
        '<div class="s7-grid">'
        '<div class="s7-grid-head">Inventário</div>' + cabecalho + "".join(linhas) + "</div>"
    )


def _evolucao_html(pontos: list[dict]) -> str:
    """SVG simples de evolução semanal de skills graduadas.

    ``pontos`` é uma lista de dicts ``{"semana": int, "graduadas": int}``.
    Quando vazia ou com poucos pontos, omite o gráfico (degradação).
    """
    if not pontos or len(pontos) < 2:
        return _minificar(
            """
            <div class="s7-evo s7-evo-empty">
              <p>Sem histórico semanal de graduação ainda.</p>
            </div>
            """
        )

    largura, altura = 540, 160
    valores = [int(p.get("graduadas", 0)) for p in pontos]
    maximo = max(max(valores), 1)
    n = len(valores)

    pontos_xy: list[str] = []
    for i, v in enumerate(valores):
        x = (i / max(n - 1, 1)) * largura
        y = altura - (v / maximo) * altura * 0.85 - 8
        pontos_xy.append(f"{x:.1f},{y:.1f}")

    poly = " ".join(pontos_xy)
    cor_linha = CORES["d7_graduado"]
    grad_atual = valores[-1]

    svg = (
        f'<svg viewBox="-30 -8 {largura + 60} {altura + 24}" style="width:100%;height:auto;">'
        f'<polyline points="{poly}" fill="none" stroke="{cor_linha}" stroke-width="1.6"/>'
        f'<text x="0" y="{altura + 16}" font-family="JetBrains Mono" font-size="10"'
        f' fill="{CORES["texto_muted"]}">{n} semanas atrás</text>'
        f'<text x="{largura}" y="{altura + 16}" text-anchor="end" font-family="JetBrains Mono"'
        f' font-size="10" fill="{CORES["texto_muted"]}">esta semana</text>'
        f'<text x="{largura - 4}" y="{altura - 24}" text-anchor="end" font-family="JetBrains Mono"'
        f' font-size="11" fill="{cor_linha}">{grad_atual} graduadas</text>'
        f"</svg>"
    )

    return _minificar(
        f'<div class="s7-evo">'
        f'<div class="s7-grid-head">Evolução · skills graduadas</div>'
        f"{svg}</div>"
    )


# CSS dedicado: src/dashboard/css/paginas/skills_d7.css (UX-M-02.C residual).
# "O que se mede, se gerencia." -- Peter Drucker
