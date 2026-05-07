"""Cluster Bem-estar · aba "Hoje" (UX-RD-17).

Agregador do dia: hero esquerda com captura rápida de humor (4 sliders
1..5 + chips de tags + sono + medicação + frase) e coluna direita com
3 mini-cards (diários, eventos, medidas) lendo o cache JSON gerado por
``mobile_cache.varrer_vault``.

Layout espelha ``novo-mockup/mockups/17-bem-estar-hoje.html``:

* ``page-header`` com sprint-tag UX-RD-17 + pill data atual.
* ``.hoje-layout``: 2 colunas grid (1.4fr + 1fr).
* ``hero-humor`` (esquerda) -- form Streamlit com sliders + button.
* ``.coluna-dir`` (direita) -- 3 cards filtrados pelo dia atual.

Ao clicar "Registrar humor", invoca :func:`escrever_registro` que grava
``daily/<YYYY-MM-DD>.md`` no vault e regenera o cache. A próxima
re-renderização do Streamlit já mostra o registro novo no card
"Diários do dia" (idempotente -- registros do mesmo dia/pessoa
sobrescrevem).

Lições UX-RD aplicadas:

* HTML emitido via :func:`minificar` (UX-RD-04).
* Cores via ``CORES`` em ``src.dashboard.tema`` -- nunca hex literal.
* Fallback graceful: se o vault não for encontrado, mostra aviso
  visível em vez de crash (UX-RD-15).
* Função pública ``renderizar(dados, periodo, pessoa, ctx)`` -- contrato
  uniforme do dispatcher de ``app.py``.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.page_header import renderizar_page_header
from src.dashboard.componentes.ui import callout_html, kpi_card
from src.dashboard.tema import CORES
from src.mobile_cache.escrever_humor import TAGS_CANONICAS, escrever_registro
from src.mobile_cache.varrer_vault import descobrir_vault_root

# Chaves do session_state isoladas por página.
_KEY_HUMOR = "be_hoje_humor"
_KEY_ENERGIA = "be_hoje_energia"
_KEY_ANSIEDADE = "be_hoje_ansiedade"
_KEY_FOCO = "be_hoje_foco"
_KEY_MEDICACAO = "be_hoje_medicacao"
_KEY_SONO = "be_hoje_sono"
_KEY_TAGS = "be_hoje_tags"
_KEY_FRASE = "be_hoje_frase"
_KEY_FLASH = "be_hoje_flash"


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página Bem-estar / Hoje.

    Args:
        dados: estrutura padrão de DataFrames (não consumida; a página
            opera sobre o vault Bem-estar fora do XLSX financeiro).
        periodo: período da sidebar (ignorado nesta aba).
        pessoa: pessoa selecionada na sidebar
            (``pessoa_a``/``pessoa_b``/``casal``); usado como autor
            default ao gravar humor.
        ctx: contexto extra (granularidade etc., ignorado).
    """
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Diário emocional", "glyph": "heart",
         "href": "?cluster=Bem-estar&tab=Diário",
         "title": "Ir para o diário"},
        {"label": "Salvar humor", "primary": True, "glyph": "validar",
         "title": "Persistir registro de humor de hoje"},
    ])

    del dados, periodo, ctx

    st.markdown(_estilos_locais(), unsafe_allow_html=True)

    pessoa_default = pessoa if pessoa in {"pessoa_a", "pessoa_b", "casal"} else "pessoa_a"
    if pessoa_default == "casal":
        pessoa_default = "pessoa_a"

    hoje = date.today()
    vault_root = descobrir_vault_root()

    st.markdown(_page_header_canonico(hoje), unsafe_allow_html=True)

    if vault_root is None:
        _renderizar_fallback_vault()
        return

    flash = st.session_state.pop(_KEY_FLASH, None)
    if flash:
        st.success(flash)

    coluna_esq, coluna_dir = st.columns([1.4, 1])

    with coluna_esq:
        _renderizar_hero_humor(vault_root, hoje, pessoa_default)

    with coluna_dir:
        _renderizar_mini_cards(vault_root, hoje)


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------


def _page_header_canonico(hoje: date) -> str:
    """Page-header canônico via UX-M-02 (substitui markup local)."""
    data_pt = hoje.strftime("%d/%m/%Y")
    return renderizar_page_header(
        titulo="BEM-ESTAR · HOJE",
        subtitulo=(
            f"Captura rápida de humor (<30s) e agregado dos registros do dia. "
            f"Persiste em daily/{hoje.isoformat()}.md com autor canônico "
            f"(pessoa_a / pessoa_b / casal)."
        ),
        sprint_tag="UX-RD-17",
        pills=[{"texto": data_pt, "tipo": "d7-graduado"}],
    )


def _renderizar_fallback_vault() -> None:
    """Callout visível quando o vault Bem-estar não é encontrado."""
    st.markdown(
        callout_html(
            "warning",
            (
                "Vault Bem-estar não encontrado. Configure a variável de "
                "ambiente OUROBOROS_VAULT apontando para a raiz do vault "
                "Obsidian, ou crie um dos diretórios candidatos canônicos. "
                "Sem o vault, a captura de humor e os mini-cards do dia "
                "ficam indisponíveis."
            ),
            titulo="Vault indisponível",
        ),
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Hero humor (formulário)
# ---------------------------------------------------------------------------


def _cores_sliders() -> dict[str, str]:
    return {
        "humor": CORES["superfluo"],     # pink
        "energia": CORES["info"],        # yellow
        "ansiedade": CORES["alerta"],    # orange
        "foco": CORES["neutro"],         # cyan
    }


def _slider_humor(rotulo: str, cor: str, key: str) -> int:
    """Renderiza um slider 1..5 com label colorido em monospace.

    Helper interno: substitui 4 blocos repetidos de ~12 linhas cada por
    chamada única. Reduz acoplamento e centraliza estilo do label.
    """
    st.markdown(
        f'<span class="slider-cor-tag" style="color:{cor};">{rotulo}</span>',
        unsafe_allow_html=True,
    )
    return st.slider(
        rotulo,
        min_value=1,
        max_value=5,
        value=int(st.session_state.get(key, 3)),
        key=key,
        label_visibility="collapsed",
    )


def _renderizar_hero_humor(
    vault_root: Path,
    hoje: date,
    pessoa_default: str,
) -> None:
    cores = _cores_sliders()
    st.markdown(
        minificar(
            f"""
            <div class="hero-humor-marker">
              <div class="hero-head">
                <h2 class="hero-titulo">Como você está agora?</h2>
                <span class="hero-data">{hoje.strftime('%A · %d %b')}</span>
              </div>
              <div class="hero-legend">
                4 sliders 1..5 · multi-tag · sono · medicação · frase do dia
              </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    with st.form(key="be_hoje_form_humor", clear_on_submit=False):
        col_h, col_e = st.columns(2)
        with col_h:
            humor = _slider_humor("humor", cores["humor"], _KEY_HUMOR)
            energia = _slider_humor("energia", cores["energia"], _KEY_ENERGIA)
        with col_e:
            ansiedade = _slider_humor("ansiedade", cores["ansiedade"], _KEY_ANSIEDADE)
            foco = _slider_humor("foco", cores["foco"], _KEY_FOCO)

        col_med, col_sono = st.columns(2)
        with col_med:
            medicacao = st.checkbox(
                "Medicação tomada hoje",
                value=bool(st.session_state.get(_KEY_MEDICACAO, False)),
                key=_KEY_MEDICACAO,
            )
        with col_sono:
            sono = st.number_input(
                "Horas de sono",
                min_value=0.0,
                max_value=24.0,
                step=0.5,
                value=float(st.session_state.get(_KEY_SONO, 7.0)),
                key=_KEY_SONO,
            )

        tags_atuais: list[str] = list(st.session_state.get(_KEY_TAGS, []))
        tags = st.multiselect(
            "Tags do momento",
            options=list(TAGS_CANONICAS),
            default=tags_atuais,
            key=_KEY_TAGS,
        )

        frase = st.text_area(
            "Frase do dia (opcional)",
            value=str(st.session_state.get(_KEY_FRASE, "")),
            key=_KEY_FRASE,
            height=80,
            placeholder="ex.: manhã produtiva, sono ok, tomei medicação no horário",
        )

        opcoes_pessoa = ["pessoa_a", "pessoa_b", "casal"]
        idx_default = (
            opcoes_pessoa.index(pessoa_default)
            if pessoa_default in opcoes_pessoa
            else 0
        )
        pessoa_escolhida = st.selectbox(
            "Esse registro é para",
            options=opcoes_pessoa,
            index=idx_default,
            format_func=lambda v: {
                "pessoa_a": "para mim (pessoa A)",
                "pessoa_b": "para Pessoa B",
                "casal": "para o casal",
            }.get(v, v),
            key="be_hoje_pessoa",
        )

        registrar = st.form_submit_button("Registrar humor")

    if registrar:
        try:
            arquivo = escrever_registro(
                vault_root,
                hoje,
                humor=humor,
                energia=energia,
                ansiedade=ansiedade,
                foco=foco,
                medicacao=medicacao,
                horas_sono=float(sono),
                tags=tags,
                frase=frase,
                pessoa=pessoa_escolhida,
            )
            st.session_state[_KEY_FLASH] = (
                f"Humor registrado em {arquivo.name} "
                f"(humor {humor}/5, autor={pessoa_escolhida}). "
                "O cache foi atualizado."
            )
            st.rerun()
        except (ValueError, OSError) as exc:
            st.error(f"Falha ao registrar humor: {exc}")


# ---------------------------------------------------------------------------
# Coluna direita: 3 mini-cards
# ---------------------------------------------------------------------------


def _carregar_cache(vault_root: Path, schema: str) -> dict[str, Any] | None:
    """Lê ``<vault>/.ouroboros/cache/<schema>.json`` se existir."""
    arquivo = vault_root / ".ouroboros" / "cache" / f"{schema}.json"
    if not arquivo.exists():
        return None
    try:
        texto = arquivo.read_text(encoding="utf-8")
        return json.loads(texto)
    except (OSError, json.JSONDecodeError):
        return None


def _filtrar_por_dia(
    items: list[dict[str, Any]],
    hoje: date,
    *,
    chave_data: str = "data",
) -> list[dict[str, Any]]:
    """Mantém apenas itens cuja ``chave_data`` casa com ``hoje`` (ISO)."""
    iso = hoje.isoformat()
    resultado: list[dict[str, Any]] = []
    for it in items:
        valor = it.get(chave_data)
        if isinstance(valor, str) and valor.startswith(iso):
            resultado.append(it)
            continue
        if isinstance(valor, datetime) and valor.date() == hoje:
            resultado.append(it)
            continue
        if isinstance(valor, date) and valor == hoje:
            resultado.append(it)
    return resultado


def _renderizar_mini_cards(vault_root: Path, hoje: date) -> None:
    """Renderiza 3 KPIs canônicos (kpi_card) + listas dos itens do dia.

    Estrutura de configuração compacta: cada entrada define o cache, chave
    interna, accent visual, descrição e texto vazio. Loop único substitui
    3 blocos repetidos manualmente.
    """
    diarios = _carregar_cache(vault_root, "diario-emocional") or {}
    eventos = _carregar_cache(vault_root, "eventos") or {}
    medidas = _carregar_cache(vault_root, "medidas") or {}

    cards: list[tuple[str, list[dict[str, Any]], str, str, str, str]] = [
        (
            "Diários do dia",
            _filtrar_por_dia(diarios.get("registros", []) or [], hoje),
            "registros emocionais",
            "pink",
            "titulo",
            "Sem diário hoje",
        ),
        (
            "Eventos do dia",
            _filtrar_por_dia(eventos.get("eventos", []) or [], hoje, chave_data="inicio"),
            "agenda + alarmes",
            "cyan",
            "titulo",
            "Sem eventos hoje",
        ),
        (
            "Medidas do dia",
            _filtrar_por_dia(medidas.get("medidas", []) or [], hoje),
            "peso · pressão · glicose",
            "green",
            "tipo",
            "Sem medidas hoje",
        ),
    ]

    for titulo, items, sub, accent, chave, vazio in cards:
        st.markdown(
            kpi_card(titulo, str(len(items)), sub_label=sub, accent=accent),
            unsafe_allow_html=True,
        )
        if items:
            st.markdown(_lista_mini_html(items, chave), unsafe_allow_html=True)
        else:
            st.markdown(_vazio_html(vazio), unsafe_allow_html=True)


def _lista_mini_html(items: list[dict[str, Any]], chave_titulo: str) -> str:
    linhas = []
    for it in items[:5]:
        titulo = str(it.get(chave_titulo, "—"))
        linhas.append(f'<li class="mini-item">{titulo}</li>')
    if not linhas:
        return ""
    return minificar(f'<ul class="mini-lista">{"".join(linhas)}</ul>')


def _vazio_html(texto: str) -> str:
    return minificar(
        f'<div class="mini-vazio" style="color:{CORES["texto_muted"]};">{texto}</div>'
    )


# ---------------------------------------------------------------------------
# CSS local
# ---------------------------------------------------------------------------


def _estilos_locais() -> str:
    """Override mínimo: hero-humor (marker form) + listas mini específicas.

    Não duplica componentes canônicos (kpi_card, callout_html já usados via
    ui.py). Mantém apenas marcações específicas da página Hoje (hero do
    formulário, listas dos resultados do dia, vazio).
    """
    return minificar(
        f"""
        <style>
          .hero-humor-marker {{
            background: {CORES['card_fundo']};
            border: 1px solid {CORES['card_elevado']};
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 12px;
          }}
          .hero-humor-marker .hero-head {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
          }}
          .hero-humor-marker .hero-titulo {{
            font-family: monospace;
            font-size: 13px;
            letter-spacing: 0.10em;
            text-transform: uppercase;
            color: {CORES['texto_muted']};
            margin: 0;
          }}
          .hero-humor-marker .hero-data {{
            font-family: monospace;
            font-size: 12px;
            color: {CORES['texto_sec']};
          }}
          .hero-humor-marker .hero-legend {{
            font-size: 11px;
            color: {CORES['texto_muted']};
            font-family: monospace;
          }}
          .slider-cor-tag {{
            font-family: monospace;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
          }}
          .mini-lista {{
            list-style: none;
            padding: 0;
            margin: 4px 0 12px 0;
          }}
          .mini-lista .mini-item {{
            font-size: 12px;
            color: {CORES['texto']};
            padding: 4px 8px;
            border-left: 2px solid {CORES['card_elevado']};
            margin-bottom: 4px;
          }}
          .mini-vazio {{
            font-size: 11px;
            font-style: italic;
            margin: 4px 0 12px 4px;
          }}
        </style>
        """
    )


# "O dia bem registrado é o dia bem vivido." -- princípio do diarismo
