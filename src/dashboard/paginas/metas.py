"""Página de metas financeiras do dashboard."""

from datetime import date
from pathlib import Path
from typing import Any

import streamlit as st
import yaml

from src.dashboard.dados import formatar_moeda

CORES: dict[str, str] = {
    "positivo": "#4ECDC4",
    "negativo": "#FF6B6B",
    "neutro": "#45B7D1",
    "alerta": "#FFA726",
    "fundo": "#0E1117",
    "card_fundo": "#1E2130",
}

CAMINHO_METAS: Path = (
    Path(__file__).resolve().parents[3] / "mappings" / "metas.yaml"
)


def _carregar_metas() -> list[dict[str, Any]]:
    """Carrega metas do arquivo YAML."""
    if not CAMINHO_METAS.exists():
        return []

    with open(CAMINHO_METAS, encoding="utf-8") as f:
        dados = yaml.safe_load(f)

    return dados.get("metas", [])


def _calcular_progresso(meta: dict[str, Any]) -> float:
    """Calcula progresso percentual (0.0 a 1.0)."""
    if meta.get("tipo") == "binario":
        return 0.0

    valor_alvo = meta.get("valor_alvo", 0)
    valor_atual = meta.get("valor_atual", 0)

    if valor_alvo <= 0:
        return 0.0

    return min(valor_atual / valor_alvo, 1.0)


def _meses_restantes(prazo: str) -> int:
    """Calcula meses restantes até o prazo."""
    hoje = date.today()
    partes = prazo.split("-")
    ano = int(partes[0])
    mes = int(partes[1])
    return (ano - hoje.year) * 12 + (mes - hoje.month)


def _cor_prioridade(prioridade: int) -> str:
    """Retorna cor baseada na prioridade."""
    mapa: dict[int, str] = {
        1: CORES["negativo"],
        2: CORES["alerta"],
        3: CORES["neutro"],
        4: CORES["positivo"],
    }
    return mapa.get(prioridade, CORES["neutro"])


def _card_meta(meta: dict[str, Any]) -> str:
    """Gera HTML de card para uma meta."""
    nome = meta.get("nome", "Sem nome")
    prazo = meta.get("prazo", "")
    prioridade = meta.get("prioridade", 3)
    nota = meta.get("nota", "")
    tipo = meta.get("tipo", "valor")
    cor = _cor_prioridade(prioridade)

    meses = _meses_restantes(prazo) if prazo else 0
    if meses < 0:
        urgencia = "Atrasado"
    else:
        urgencia = f"{meses} meses restantes"

    if meses < 0:
        cor_urgencia = CORES["negativo"]
    elif meses > 6:
        cor_urgencia = CORES["positivo"]
    else:
        cor_urgencia = CORES["alerta"]

    if tipo == "binario":
        status = "Pendente"
        detalhe = ""
    else:
        valor_alvo = meta.get("valor_alvo", 0)
        valor_atual = meta.get("valor_atual", 0)
        status = (
            f"{formatar_moeda(valor_atual)} "
            f"/ {formatar_moeda(valor_alvo)}"
        )
        progresso_pct = _calcular_progresso(meta) * 100
        detalhe = (
            '<p style="color: #AAAAAA;'
            " font-size: 12px;"
            ' margin: 2px 0;">'
            f"Progresso: {progresso_pct:.0f}%</p>"
        )

    nota_html = ""
    if nota:
        nota_html = (
            '<p style="color: #888;'
            " font-size: 11px;"
            " font-style: italic;"
            f' margin: 6px 0 0 0;">{nota}</p>'
        )

    deps = meta.get("depende_de", [])
    deps_html = ""
    if deps:
        deps_texto = ", ".join(deps)
        deps_html = (
            '<p style="color: #888;'
            " font-size: 11px;"
            ' margin: 4px 0 0 0;">'
            f"Depende de: {deps_texto}</p>"
        )

    fundo = CORES["card_fundo"]

    return (
        f'<div style="background-color: {fundo};'
        f" border-left: 4px solid {cor};"
        " border-radius: 8px; padding: 16px;"
        ' margin: 8px 0;">'
        '<div style="display: flex;'
        " justify-content: space-between;"
        ' align-items: center;">'
        '<p style="color: #FAFAFA;'
        " font-size: 15px; font-weight: bold;"
        f' margin: 0;">{nome}</p>'
        f'<span style="color: {cor};'
        " font-size: 12px;"
        f' font-weight: bold;">P{prioridade}</span>'
        "</div>"
        '<p style="color: #AAAAAA;'
        " font-size: 13px;"
        f' margin: 4px 0;">{status}</p>'
        f"{detalhe}"
        f'<p style="color: {cor_urgencia};'
        " font-size: 12px;"
        f' margin: 4px 0;">'
        f"Prazo: {prazo} ({urgencia})</p>"
        f"{nota_html}"
        f"{deps_html}"
        "</div>"
    )


def renderizar(
    dados: dict, mes_selecionado: str, pessoa: str
) -> None:
    """Renderiza a página de metas financeiras."""
    metas = _carregar_metas()

    if not metas:
        st.warning(
            "Nenhuma meta encontrada."
            " Verifique mappings/metas.yaml."
        )
        return

    st.subheader("Metas Financeiras")

    metas_valor = [
        m for m in metas if m.get("tipo") != "binario"
    ]
    metas_binarias = [
        m for m in metas if m.get("tipo") == "binario"
    ]

    if metas_valor:
        st.markdown("### Metas com Valor")
        for meta in sorted(
            metas_valor, key=lambda m: m.get("prioridade", 99)
        ):
            st.markdown(
                _card_meta(meta), unsafe_allow_html=True
            )
            progresso = _calcular_progresso(meta)
            st.progress(
                progresso, text=f"{progresso * 100:.0f}%"
            )

    if metas_binarias:
        st.markdown("### Metas Binárias (Sim/Não)")
        for meta in sorted(
            metas_binarias,
            key=lambda m: m.get("prioridade", 99),
        ):
            st.markdown(
                _card_meta(meta), unsafe_allow_html=True
            )

    st.markdown("---")
    st.subheader("Timeline de Prazos")
    _timeline_metas(metas)


def _timeline_metas(metas: list[dict[str, Any]]) -> None:
    """Exibe timeline simplificada de prazos."""
    metas_com_prazo = [m for m in metas if m.get("prazo")]
    metas_ordenadas = sorted(
        metas_com_prazo, key=lambda m: m["prazo"]
    )

    hoje = date.today()
    hoje_str = hoje.strftime("%Y-%m")

    cor_pos = CORES["positivo"]
    fundo = CORES["card_fundo"]

    linhas: list[str] = []
    linhas.append(
        f'<div style="background-color: {fundo};'
        ' border-radius: 8px; padding: 20px;">'
    )
    linhas.append(
        '<div style="border-left: 2px solid #555;'
        ' padding-left: 20px; margin-left: 10px;">'
    )

    linhas.append(
        '<div style="position: relative;'
        ' margin-bottom: 15px;">'
        '<div style="position: absolute;'
        " left: -27px; top: 3px;"
        " width: 12px; height: 12px;"
        f" background-color: {cor_pos};"
        ' border-radius: 50%;"></div>'
        f'<p style="color: {cor_pos};'
        " font-size: 13px;"
        ' font-weight: bold; margin: 0;">'
        f"HOJE ({hoje_str})</p></div>"
    )

    for meta in metas_ordenadas:
        prazo = meta["prazo"]
        nome = meta.get("nome", "")
        prioridade = meta.get("prioridade", 3)
        cor = _cor_prioridade(prioridade)
        meses = _meses_restantes(prazo)

        if meses < 0:
            status_texto = "ATRASADO"
            cor_status = CORES["negativo"]
        elif meses == 0:
            status_texto = "ESTE MES"
            cor_status = CORES["alerta"]
        else:
            status_texto = f"em {meses} meses"
            cor_status = cor

        linhas.append(
            '<div style="position: relative;'
            ' margin-bottom: 15px;">'
            '<div style="position: absolute;'
            " left: -27px; top: 3px;"
            " width: 12px; height: 12px;"
            f" background-color: {cor};"
            ' border-radius: 50%;"></div>'
            '<p style="color: #FAFAFA;'
            ' font-size: 13px; margin: 0;">'
            f'<span style="color: {cor_status};'
            f' font-weight: bold;">{prazo}</span>'
            f" -- {nome} "
            f'<span style="color: {cor_status};'
            f' font-size: 11px;">'
            f"({status_texto})</span></p></div>"
        )

    linhas.append("</div></div>")

    st.markdown("\n".join(linhas), unsafe_allow_html=True)


# "A disciplina é a ponte entre metas e realizações."
# -- Jim Rohn
