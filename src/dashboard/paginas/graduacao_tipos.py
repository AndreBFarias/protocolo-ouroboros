"""Cluster Sistema · aba "Graduação" (UX-DASH-GRADUACAO-TIPOS).

Tabela viva dos 23 tipos documentais canônicos declarados em
``mappings/tipos_documento.yaml``, consumindo o snapshot
``data/output/graduacao_tipos.json`` mantido por ``scripts/dossie_tipo.py``.

Mostra para cada tipo: status (PENDENTE/CALIBRANDO/GRADUADO/REGREDINDO),
contadores (amostras_ok / divergencias_ativas / histórico), alias quando
aplicável, dossiê físico (path interno) e timestamp da última atualização.
Botão "snapshot agora" invoca ``scripts/dossie_tipo.py snapshot`` para
materializar a verdade atual antes de exibir.

Contrato: ``renderizar(dados, periodo, pessoa, ctx)`` espelhando as outras
páginas. Os 4 argumentos posicionais não são consumidos (página é
independente do XLSX/grafo do extrato).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

_RAIZ = Path(__file__).resolve().parents[3]
PATH_GRADUACAO = _RAIZ / "data" / "output" / "graduacao_tipos.json"
PATH_TIPOS_YAML = _RAIZ / "mappings" / "tipos_documento.yaml"
DIR_DOSSIES = _RAIZ / "data" / "output" / "dossies"
SCRIPT_DOSSIE = _RAIZ / "scripts" / "dossie_tipo.py"


def _carregar_dados() -> dict[str, Any]:
    """Lê graduacao_tipos.json + tipos_documento.yaml e devolve estrutura unificada."""
    if not PATH_GRADUACAO.exists():
        return {
            "total": 0,
            "graduados": 0,
            "pendentes": 0,
            "calibrando": 0,
            "regredindo": 0,
            "linhas": [],
            "gerado_em": None,
        }
    snap = json.loads(PATH_GRADUACAO.read_text(encoding="utf-8"))

    aliases_por_canonico: dict[str, list[str]] = {}
    canonicos_yaml: list[str] = []
    if PATH_TIPOS_YAML.exists():
        try:
            import yaml  # type: ignore[import-untyped]

            dados = yaml.safe_load(PATH_TIPOS_YAML.read_text(encoding="utf-8")) or {}
            for t in dados.get("tipos") or []:
                cid = t.get("id")
                if not cid:
                    continue
                canonicos_yaml.append(cid)
                aliases_por_canonico[cid] = t.get("aliases_graduacao") or []
        except ImportError:
            pass

    tipos_no_snap = snap.get("tipos", {})
    linhas: list[dict[str, Any]] = []
    todos = sorted(set(canonicos_yaml) | set(tipos_no_snap.keys()))
    for cid in todos:
        info = tipos_no_snap.get(cid) or {}
        aliases = aliases_por_canonico.get(cid, [])
        linhas.append(
            {
                "tipo": cid,
                "status": info.get("status", "PENDENTE"),
                "amostras_ok": info.get("amostras_ok", 0),
                "divergencias_ativas": info.get("divergencias_ativas", 0),
                "historico_divergencias": info.get("historico_divergencias_count", 0),
                "alias": ", ".join(aliases) if aliases else "—",
                "dossie_path": info.get("dossie_path", "—"),
                "atualizado_em": info.get("atualizado_em") or "—",
            }
        )

    totais = snap.get("totais") or {}
    graduados = totais.get("GRADUADO", 0)
    calibrando = totais.get("CALIBRANDO", 0)
    regredindo = totais.get("REGREDINDO", 0)
    # PENDENTES = total de tipos canônicos (YAML) - os que avançaram.
    # Inclui os que ainda não têm dossiê físico (são contados como PENDENTE
    # nas linhas via fallback do _carregar_dados).
    pendentes = len(linhas) - graduados - calibrando - regredindo
    return {
        "total": len(linhas),
        "graduados": graduados,
        "pendentes": pendentes,
        "calibrando": calibrando,
        "regredindo": regredindo,
        "linhas": linhas,
        "gerado_em": snap.get("gerado_em"),
    }


def _trigger_snapshot() -> tuple[bool, str]:
    """Invoca scripts/dossie_tipo.py snapshot. Retorna (sucesso, mensagem)."""
    try:
        r = subprocess.run(
            ["python", str(SCRIPT_DOSSIE), "snapshot"],
            cwd=str(_RAIZ),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return r.returncode == 0, r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as exc:
        return False, str(exc)


def renderizar(
    dados: dict[str, pd.DataFrame] | None = None,
    periodo: str | None = None,
    pessoa: str | None = None,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página Graduação (cluster Sistema, aba 3)."""
    del dados, periodo, pessoa, ctx

    st.markdown(
        "<h1 style='margin-bottom:.5rem;'>Graduação dos tipos documentais</h1>"
        "<p style='color:#888;margin-top:0;'>"
        "Cada tipo declarado em <code>mappings/tipos_documento.yaml</code> "
        "percorre o ciclo PENDENTE → CALIBRANDO → GRADUADO conforme amostras "
        "reais são validadas artesanalmente pelo supervisor."
        "</p>",
        unsafe_allow_html=True,
    )

    d = _carregar_dados()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("GRADUADOS", f"{d['graduados']}/{d['total']}")
    c2.metric("CALIBRANDO", d["calibrando"])
    c3.metric("PENDENTES", d["pendentes"])
    c4.metric(
        "REGREDINDO",
        d["regredindo"],
        delta="alerta" if d["regredindo"] > 0 else None,
        delta_color="inverse" if d["regredindo"] > 0 else "normal",
    )

    st.divider()

    col_filtros, col_botao = st.columns([4, 1])
    with col_filtros:
        status_filtro = st.multiselect(
            "Filtrar por status",
            ["GRADUADO", "CALIBRANDO", "PENDENTE", "REGREDINDO"],
            default=[],
            key="grad_status_filter",
        )
    with col_botao:
        st.markdown("<div style='height:1.7rem;'></div>", unsafe_allow_html=True)
        if st.button("Snapshot agora", type="primary"):
            ok, msg = _trigger_snapshot()
            if ok:
                st.success(f"Snapshot atualizado.\n```\n{msg.strip()}\n```")
                st.rerun()
            else:
                st.error(f"Falhou: {msg}")

    linhas = d["linhas"]
    if status_filtro:
        linhas = [linha for linha in linhas if linha["status"] in status_filtro]

    if not linhas:
        st.info("Nenhum tipo casa com o filtro selecionado.")
        return

    df = pd.DataFrame(linhas)
    df = df[
        [
            "tipo",
            "status",
            "amostras_ok",
            "divergencias_ativas",
            "historico_divergencias",
            "alias",
            "dossie_path",
            "atualizado_em",
        ]
    ]
    st.dataframe(df, hide_index=True, use_container_width=True)

    if d["gerado_em"]:
        st.caption(f"Snapshot gerado em {d['gerado_em']}")

    st.divider()
    st.subheader("Estado detalhado por tipo")
    for linha in linhas:
        cid = linha["tipo"]
        dossie_nome = linha["dossie_path"] if linha["dossie_path"] != "—" else cid
        dossie_dir = DIR_DOSSIES / dossie_nome
        with st.expander(f"{cid} — {linha['status']}"):
            estado_path = dossie_dir / "estado.json"
            if estado_path.exists():
                try:
                    estado = json.loads(estado_path.read_text(encoding="utf-8"))
                    st.json(estado)
                except json.JSONDecodeError as exc:
                    st.error(f"estado.json corrompido: {exc}")
            else:
                st.info(
                    f"Dossiê ainda não criado em `{dossie_dir}`. "
                    f"Rode `scripts/dossie_tipo.py abrir {cid}`."
                )


# "Tabela viva é compromisso: o que aparece aqui é o que de fato existe."
# -- princípio do painel honesto
