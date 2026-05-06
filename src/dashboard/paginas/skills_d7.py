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

Tokens consumidos via ``CORES`` (UX-RD-01) e classes utilitárias UX-RD-02
(``.kpi``, ``.pill-d7-*``, ``.confidence-bar``, ``.skill-instr``,
``.page-header``, ``.btn``). Estilos específicos desta página
(``.s7-row``, ``.s7-grid``, ``.s7-tl-row``) são emitidos via ``<style>``
local para não tocar ``tema_css.py``.

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

from src.dashboard.tema import CORES

CAMINHO_LOG_D7: Path = (
    Path(__file__).resolve().parents[3] / "data" / "output" / "skill_d7_log.json"
)


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página Skills D7 (UX-RD-05 + UX-T-14)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Recalibrar", "title": "Recalibrar 18 skills"},
        {"label": "Logs", "primary": True,
         "title": "Abrir terminal de logs"},
    ])

    del dados, periodo, pessoa, ctx

    st.markdown(_estilos_locais(), unsafe_allow_html=True)
    st.markdown(_page_header_html(), unsafe_allow_html=True)

    snapshot = _carregar_snapshot()
    if snapshot is None:
        st.markdown(_fallback_graceful_html(), unsafe_allow_html=True)
        return

    skills: list[dict] = snapshot.get("skills", [])
    if not skills:
        st.markdown(_fallback_graceful_html(), unsafe_allow_html=True)
        return

    contagens = _contar_estados(skills)
    st.markdown(_kpi_grid_html(contagens, total=len(skills)), unsafe_allow_html=True)
    st.markdown(_lista_skills_html(skills), unsafe_allow_html=True)
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
        '<div class="s7-kpi-row">' + "".join(pieces) + "</div>"
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
        '<div class="s7-grid-head">Inventário</div>'
        + cabecalho
        + "".join(linhas)
        + "</div>"
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


def _estilos_locais() -> str:
    """CSS específico desta página -- isolado de ``tema_css.py``."""
    fundo = CORES["card_fundo"]
    inset = CORES["fundo_inset"]
    texto_pri = CORES["texto"]
    texto_sec = CORES["texto_sec"]
    texto_muted = CORES["texto_muted"]
    border_subtle = "#2a2d3a"

    return f"""
    <style>
      .s7-kpi-row {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 24px;
      }}
      .s7-grid {{
        background: {fundo};
        border: 1px solid {border_subtle};
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
      }}
      .s7-grid-head {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 11px;
        letter-spacing: 0.10em;
        text-transform: uppercase;
        color: {texto_muted};
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid {border_subtle};
      }}
      .s7-row {{
        display: grid;
        grid-template-columns: 2fr 110px 90px 90px 110px;
        gap: 12px;
        align-items: center;
        padding: 10px 0;
        border-bottom: 1px dashed {border_subtle};
        font-size: 13px;
        color: {texto_sec};
      }}
      .s7-row:last-child {{ border-bottom: none; }}
      .s7-row.s7-head {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 10px;
        color: {texto_muted};
        letter-spacing: 0.08em;
        text-transform: uppercase;
        padding: 6px 0;
      }}
      .s7-name strong {{
        display: block;
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 13px;
        color: {texto_pri};
      }}
      .s7-desc {{
        display: block;
        font-size: 11px;
        color: {texto_muted};
        margin: 2px 0 4px;
      }}
      .s7-conf, .s7-runs, .s7-when {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 12px;
        font-variant-numeric: tabular-nums;
      }}
      .s7-runs, .s7-when {{ color: {texto_muted}; }}
      .s7-evo {{
        background: {fundo};
        border: 1px solid {border_subtle};
        border-radius: 12px;
        padding: 16px;
      }}
      .s7-evo-empty {{
        color: {texto_muted};
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 12px;
      }}
      .s7-evo-empty p {{ margin: 0; padding: 16px 0; text-align: center; }}
      .s7-evo svg {{ background: {inset}; border-radius: 8px; padding: 8px; }}
    </style>
    """


# "O que se mede, se gerencia." -- Peter Drucker
