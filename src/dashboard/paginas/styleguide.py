"""Cluster Sistema · aba "Styleguide" (UX-RD-05).

Styleguide vivo do dashboard: renderiza tokens reais consumidos por
``CORES`` (UX-RD-01) e classes do redesign UX-RD-02 (``.kpi``,
``.pill-d7-*``, ``.pill-humano-*``, ``.btn``, ``.table``, ``.drawer``,
``.skill-instr``). Espelha 1:1 ``novo-mockup/styleguide.html`` para QA
visual lado-a-lado.

Decisão de fonte: lê ``CORES`` e ``tema.SPACING`` para tornar a tabela de
swatches "vivo" -- qualquer chave nova adicionada ao dict aparece aqui
automaticamente. Demonstrações de classes utilitárias usam markup HTML
estático que o CSS global de ``css_global()`` já estiliza.

Contrato: ``renderizar(dados, periodo, pessoa, ctx)`` espelhando as outras
páginas.

Lição UX-RD-04 herdada: HTML emitido em uma única linha quando contém
fragmentos que o parser CommonMark possa quebrar. ``_minificar`` aplicado
em qualquer string com indentação Python dentro de ``unsafe_allow_html``.
"""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from src.dashboard.tema import CORES, SPACING


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página Styleguide (cluster Sistema, aba 2)."""
    del dados, periodo, pessoa, ctx

    st.markdown(_estilos_locais(), unsafe_allow_html=True)
    st.markdown(_page_header_html(), unsafe_allow_html=True)

    st.markdown(_secao_cores_html(), unsafe_allow_html=True)
    st.markdown(_secao_tipografia_html(), unsafe_allow_html=True)
    st.markdown(_secao_espacamento_html(), unsafe_allow_html=True)
    st.markdown(_secao_botoes_html(), unsafe_allow_html=True)
    st.markdown(_secao_pills_html(), unsafe_allow_html=True)
    st.markdown(_secao_kpi_html(), unsafe_allow_html=True)
    st.markdown(_secao_tabela_html(), unsafe_allow_html=True)
    st.markdown(_secao_drawer_html(), unsafe_allow_html=True)
    st.markdown(_secao_skill_instr_html(), unsafe_allow_html=True)
    st.markdown(_secao_footer_html(), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minificar(html: str) -> str:
    return re.sub(r"\s+", " ", html).strip()


def _page_header_html() -> str:
    return _minificar(
        """
        <div class="page-header">
          <div>
            <h1 class="page-title">STYLEGUIDE</h1>
            <p class="page-subtitle">
              Tokens, tipografia, espaçamento e componentes do sistema. Toda
              regra usada no redesign está aqui -- se algo aparece em uma tela
              e não está aqui, é débito técnico.
            </p>
          </div>
          <div class="page-meta">
            <span class="pill pill-d7-graduado">Tema · Dracula adaptado</span>
            <span class="sprint-tag">UX-RD-05</span>
          </div>
        </div>
        """
    )


def _swatch_para(chave: str, hex_valor: str) -> str:
    """Renderiza um swatch para um token de cor (CORES[chave])."""
    var_name = f"--color-{chave.replace('_', '-')}"
    return _minificar(
        f"""
        <div class="sg-sw" data-token="{chave}">
          <div class="sg-chip" style="background:{hex_valor};"></div>
          <div class="sg-meta">
            <strong>{chave}</strong>
            <span>{hex_valor}</span>
            <code>{var_name}</code>
          </div>
        </div>
        """
    )


def _secao_cores_html() -> str:
    """Tabela de swatches para TODAS as chaves do dict CORES.

    Iteração direta no dict garante que toda chave nova adicionada (ex:
    ``d7_*`` em UX-RD-01) aparece automaticamente aqui (regressivo).
    """
    swatches = "".join(_swatch_para(k, v) for k, v in CORES.items())
    return _minificar(
        f"""
        <section class="sg-section">
          <h2 class="sg-h2"><span class="num">01</span>Cores</h2>
          <p class="sg-lead">
            Paleta dark-first inspirada em Dracula. {len(CORES)} tokens
            registrados em <code>tema.CORES</code>. D7 mapeia estado de
            graduação 1→1 em cor.
          </p>
          <div class="sg-grid-cores">{swatches}</div>
        </section>
        """
    )


def _secao_tipografia_html() -> str:
    """Demonstra os tokens ``--fs-*`` injetados por ``tema_css``."""
    linhas_fs = []
    fs_tokens = [
        ("--fs-11", "11px", "caption / label"),
        ("--fs-12", "12px", "metadado mono"),
        ("--fs-13", "13px", "corpo padrão"),
        ("--fs-14", "14px", "corpo destaque"),
        ("--fs-16", "16px", "subtítulo"),
        ("--fs-18", "18px", "section title"),
        ("--fs-20", "20px", "título"),
        ("--fs-24", "24px", "valor"),
        ("--fs-32", "32px", "KPI value"),
        ("--fs-40", "40px", "page title"),
    ]
    for token, px, papel in fs_tokens:
        linhas_fs.append(
            _minificar(
                f"""
                <div class="sg-type-row">
                  <div class="sg-type-meta">
                    <strong>{token} · {px}</strong>
                    <span>{papel}</span>
                  </div>
                  <div class="sg-type-demo" style="font-size:{px};">
                    Protocolo Ouroboros · 2026
                  </div>
                </div>
                """
            )
        )
    return _minificar(
        f"""
        <section class="sg-section">
          <h2 class="sg-h2"><span class="num">02</span>Tipografia</h2>
          <p class="sg-lead">
            Mono para tudo que é dado (números, sha, ids, código). Sans para
            texto longo. Hierarquia por <em>peso</em> e <em>letter-spacing</em>,
            não por família.
          </p>
          {"".join(linhas_fs)}
        </section>
        """
    )


def _secao_espacamento_html() -> str:
    blocos = []
    for nome, px in SPACING.items():
        blocos.append(
            _minificar(
                f"""
                <div class="sg-spacer-cell">
                  <div class="sg-spacer-block" style="width:{px}px;height:{px}px;"></div>
                  <div class="sg-spacer-meta">SPACING[{nome!r}] · {px}px</div>
                </div>
                """
            )
        )
    return _minificar(
        f"""
        <section class="sg-section">
          <h2 class="sg-h2"><span class="num">03</span>Espaçamento &amp; raio</h2>
          <p class="sg-lead">
            Escala documentada em <code>tema.SPACING</code> ({len(SPACING)} níveis).
            Tudo encaixa em múltiplos de 4. Bordas pequenas (4px) em controles,
            8px em cards.
          </p>
          <div class="sg-spacer-grid">{"".join(blocos)}</div>
        </section>
        """
    )


def _secao_botoes_html() -> str:
    return _minificar(
        """
        <section class="sg-section">
          <h2 class="sg-h2"><span class="num">04</span>Botões</h2>
          <div class="sg-demo">
            <div class="sg-demo-label">variantes · classe <code>.btn</code></div>
            <div class="sg-demo-row">
              <button class="btn btn-primary">Primário</button>
              <button class="btn">Secundário</button>
              <button class="btn btn-ghost">Ghost</button>
              <button class="btn btn-danger">Danger</button>
              <button class="btn btn-primary btn-sm">small</button>
              <button class="btn btn-icon" aria-label="ícone">+</button>
              <button
                class="btn btn-primary"
                disabled
                style="opacity:0.5;cursor:not-allowed;"
              >disabled</button>
            </div>
          </div>
        </section>
        """
    )


def _secao_pills_html() -> str:
    """Demos de TODAS as pills D7 e Humano."""
    return _minificar(
        """
        <section class="sg-section">
          <h2 class="sg-h2"><span class="num">05</span>Pills &amp; badges</h2>
          <div class="sg-demo">
            <div class="sg-demo-label">D7 · estados de aprendizado</div>
            <div class="sg-demo-row">
              <span class="pill pill-d7-graduado">graduado</span>
              <span class="pill pill-d7-calibracao">calibrando</span>
              <span class="pill pill-d7-regredindo">regredindo</span>
              <span class="pill pill-d7-pendente">pendente</span>
            </div>
          </div>
          <div class="sg-demo">
            <div class="sg-demo-label">Humano · estados de validação</div>
            <div class="sg-demo-row">
              <span class="pill pill-humano-aprovado">aprovado</span>
              <span class="pill pill-humano-rejeitado">rejeitado</span>
              <span class="pill pill-humano-revisar">revisar</span>
              <span class="pill pill-humano-pendente">pendente</span>
            </div>
          </div>
          <div class="sg-demo">
            <div class="sg-demo-label">Sprint tag</div>
            <div class="sg-demo-row">
              <span class="sprint-tag">UX-RD-05</span>
              <span class="sprint-tag">P1</span>
            </div>
          </div>
        </section>
        """
    )


def _secao_kpi_html() -> str:
    """Demo de KPI cards usando a classe canônica ``.kpi``."""
    return _minificar(
        f"""
        <section class="sg-section">
          <h2 class="sg-h2"><span class="num">06</span>KPI cards</h2>
          <div class="sg-demo">
            <div class="sg-demo-label">classe canônica <code>.kpi</code> · 3 estilos</div>
            <div
              class="sg-demo-row"
              style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;"
            >
              <div class="kpi">
                <div class="kpi-label">Cobertura D7</div>
                <div class="kpi-value">78%</div>
                <div class="kpi-delta up">14 / 18 graduadas</div>
              </div>
              <div class="kpi">
                <div class="kpi-label">Saldo</div>
                <div class="kpi-value" style="color:{CORES["d7_graduado"]};">R$ 31.420</div>
                <div class="kpi-delta up">+R$ 1.842 · 30d</div>
              </div>
              <div class="kpi">
                <div class="kpi-label">Despesa mensal</div>
                <div class="kpi-value" style="color:{CORES["alerta"]};">R$ 8.120</div>
                <div class="kpi-delta down">-R$ 412 · 30d</div>
              </div>
            </div>
          </div>
        </section>
        """
    )


def _secao_tabela_html() -> str:
    """Demo da classe ``.table`` densa (UX-RD-02)."""
    return _minificar(
        f"""
        <section class="sg-section">
          <h2 class="sg-h2"><span class="num">07</span>Tabela densa</h2>
          <div class="sg-demo">
            <div class="sg-demo-label">classe <code>.table</code> · linhas densas</div>
            <table class="table">
              <thead>
                <tr><th>data</th><th>descrição</th>
                    <th class="col-num">valor</th><th>conta</th></tr>
              </thead>
              <tbody>
                <tr><td class="col-mono">30/04</td><td>Nubank · cartão</td>
                    <td class="col-num" style="color:{CORES["negativo"]};">-R$ 846,21</td>
                    <td>C6</td></tr>
                <tr><td class="col-mono">28/04</td><td>Aluguel</td>
                    <td class="col-num" style="color:{CORES["negativo"]};">-R$ 1.280,00</td>
                    <td>Itaú</td></tr>
                <tr><td class="col-mono">27/04</td><td>Pix recebido</td>
                    <td class="col-num" style="color:{CORES["d7_graduado"]};">+R$ 1.213,85</td>
                    <td>Itaú</td></tr>
              </tbody>
            </table>
          </div>
        </section>
        """
    )


def _secao_drawer_html() -> str:
    """Mock estático ilustrando classes ``.drawer*`` -- não interativo."""
    return _minificar(
        """
        <section class="sg-section">
          <h2 class="sg-h2"><span class="num">08</span>Drawer (painel lateral)</h2>
          <div class="sg-demo">
            <div class="sg-demo-label">mock estático · classes <code>.drawer*</code></div>
            <div class="sg-drawer-mock">
              <div class="drawer-head">
                <strong>extrato_nubank.pdf</strong>
                <span class="pill pill-d7-calibracao">calibrando</span>
              </div>
              <div class="drawer-tabs">
                <button class="drawer-tab active">Diff</button>
                <button class="drawer-tab">Histórico</button>
                <button class="drawer-tab">Metadados</button>
              </div>
              <div class="drawer-body">
                <p style="font-family:monospace;font-size:13px;line-height:1.6;">
                  Painel lateral acionado por clique numa linha da tabela densa.
                  Classes <code>.drawer-overlay</code>, <code>.drawer-head</code>,
                  <code>.drawer-tabs</code>, <code>.drawer-body</code>.
                </p>
              </div>
            </div>
          </div>
        </section>
        """
    )


def _secao_skill_instr_html() -> str:
    """Demo da classe ``.skill-instr`` (usada no fallback de Skills D7)."""
    return _minificar(
        """
        <section class="sg-section">
          <h2 class="sg-h2"><span class="num">09</span>Skill instruction</h2>
          <div class="sg-demo">
            <div class="sg-demo-label">classe <code>.skill-instr</code> · fallback graceful</div>
            <div class="skill-instr">
              <h4>Como popular este painel</h4>
              <p>Execute a skill canônica <code>/auditar-cobertura-total</code>
                 para gerar o snapshot estruturado.</p>
              <ol>
                <li>Entre em modo supervisor (sessão Opus interativa).</li>
                <li>Rode <code>/auditar-cobertura-total</code>.</li>
                <li>Verifique <code>data/output/skill_d7_log.json</code>.</li>
              </ol>
              <p class="why">Por que: ADR-10 manda degradar graciosamente quando
                 fonte ainda não existe; nunca inventar dados.</p>
            </div>
          </div>
        </section>
        """
    )


def _secao_footer_html() -> str:
    return _minificar(
        """
        <section class="sg-section sg-footer">
          <p>
            Compare lado-a-lado com
            <code>novo-mockup/styleguide.html</code>. Divergência aqui é débito
            técnico do <code>tema_css.py</code> (UX-RD-02).
          </p>
        </section>
        """
    )


def _estilos_locais() -> str:
    """CSS específico do styleguide. Não toca tema_css.py."""
    fundo = CORES["card_fundo"]
    inset = CORES["fundo_inset"]
    texto_pri = CORES["texto"]
    texto_sec = CORES["texto_sec"]
    texto_muted = CORES["texto_muted"]
    accent_purple = CORES["destaque"]
    border_subtle = "#2a2d3a"

    return f"""
    <style>
      .sg-section {{ margin-bottom: 32px; }}
      .sg-h2 {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 18px;
        color: {texto_pri};
        margin: 0 0 8px;
        padding-bottom: 12px;
        border-bottom: 1px solid {border_subtle};
        display: flex;
        align-items: baseline;
        gap: 14px;
      }}
      .sg-h2 .num {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 11px;
        color: {accent_purple};
        letter-spacing: 0.14em;
        text-transform: uppercase;
        font-weight: 400;
        padding: 3px 8px;
        background: rgba(189,147,249,0.12);
        border-radius: 4px;
      }}
      .sg-lead {{
        color: {texto_sec};
        font-size: 13px;
        margin: 0 0 16px;
        max-width: 64ch;
        line-height: 1.6;
      }}
      .sg-grid-cores {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
      }}
      .sg-sw {{
        background: {fundo};
        border: 1px solid {border_subtle};
        border-radius: 8px;
        overflow: hidden;
        transition: border-color .18s, transform .18s;
      }}
      .sg-sw:hover {{
        border-color: {accent_purple};
        transform: translateY(-1px);
      }}
      .sg-chip {{ height: 64px; }}
      .sg-meta {{
        padding: 10px 12px;
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 11px;
      }}
      .sg-meta strong {{
        display: block;
        color: {texto_pri};
        font-size: 12px;
        margin-bottom: 2px;
      }}
      .sg-meta span {{ color: {texto_muted}; display: block; }}
      .sg-meta code {{
        color: {accent_purple};
        background: {inset};
        padding: 1px 4px;
        border-radius: 3px;
        font-size: 10px;
      }}
      .sg-type-row {{
        background: {fundo};
        border: 1px solid {border_subtle};
        border-radius: 8px;
        padding: 16px;
        display: grid;
        grid-template-columns: 220px 1fr;
        gap: 16px;
        align-items: center;
        margin-bottom: 8px;
      }}
      .sg-type-meta {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 11px;
        color: {texto_muted};
      }}
      .sg-type-meta strong {{
        display: block;
        color: {texto_pri};
        font-size: 13px;
        margin-bottom: 4px;
      }}
      .sg-type-demo {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        color: {texto_pri};
        font-variant-numeric: tabular-nums;
      }}
      .sg-spacer-grid {{
        display: flex;
        gap: 16px;
        align-items: flex-end;
        flex-wrap: wrap;
        background: {fundo};
        border: 1px solid {border_subtle};
        border-radius: 8px;
        padding: 16px;
      }}
      .sg-spacer-cell {{ text-align: center; }}
      .sg-spacer-block {{
        background: linear-gradient(135deg, {accent_purple}, {CORES["superfluo"]});
        border-radius: 2px;
      }}
      .sg-spacer-meta {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 10px;
        color: {texto_muted};
        margin-top: 6px;
      }}
      .sg-demo {{
        background: {fundo};
        border: 1px solid {border_subtle};
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
      }}
      .sg-demo-label {{
        font-family: ui-monospace, 'JetBrains Mono', monospace;
        font-size: 10px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: {texto_muted};
        margin-bottom: 12px;
      }}
      .sg-demo-row {{
        display: flex;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;
      }}
      .sg-drawer-mock {{
        max-width: 480px;
        background: {CORES["card_elevado"]};
        border: 1px solid {border_subtle};
        border-radius: 8px;
        overflow: hidden;
      }}
      .sg-footer {{
        padding-top: 16px;
        border-top: 1px solid {border_subtle};
        color: {texto_muted};
        font-size: 12px;
      }}
      .sg-footer code {{
        color: {accent_purple};
        background: {inset};
        padding: 1px 4px;
        border-radius: 3px;
      }}
    </style>
    """


# "Beleza é a primeira prova; não há lugar permanente no mundo para uma
# matemática feia." -- G. H. Hardy
