"""Cluster Sistema, aba "Tipos por detectar" (Sprint AUTO-TIPO-PROPOSTAS-DASHBOARD).

Lista propostas de tipo documental novo gerado por
``scripts/detectar_tipos_novos.py`` e armazenado em
``data/output/propostas_tipo_novo.json``. Cada proposta agrupa arquivos
de ``data/raw/_classificar/`` por tokens recorrentes no nome + n-grams
de conteúdo extraído. O dashboard expõe:

- KPI de propostas pendentes no topo + total de arquivos analisados.
- Filtros por extensão principal e confiança mínima.
- Expander por proposta com: exemplos de paths, sha256, regex candidatos.
- Botão "Aceitar" cria entry em ``mappings/tipos_documento.yaml`` (com
  status "pendente_validacao" para revisão humana posterior).
- Botão "Rejeitar" marca como rejeitada em
  ``data/output/propostas_tipo_rejeitadas.json``.
- Botão "Regenerar" reexecuta ``scripts/detectar_tipos_novos.py --apply``.

Contrato: ``renderizar(dados, periodo, pessoa, ctx)`` espelhando outras
páginas. Argumentos não são consumidos diretamente.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

_RAIZ = Path(__file__).resolve().parents[3]

PATH_PROPOSTAS = _RAIZ / "data" / "output" / "propostas_tipo_novo.json"
PATH_REJEITADAS = _RAIZ / "data" / "output" / "propostas_tipo_rejeitadas.json"
PATH_TIPOS_YAML = _RAIZ / "mappings" / "tipos_documento.yaml"


@dataclass(frozen=True)
class PropostaTipo:
    """Proposta de tipo documental novo lida do JSON."""

    id_proposto: str
    n_amostras: int
    exemplos_sha256: list[str]
    exemplos_paths: list[str]
    regex_candidatos: list[str]
    mime_principal: str
    extensao_principal: str
    confianca_global: float


def _carregar_propostas(
    path: Path | None = None,
) -> tuple[list[PropostaTipo], dict]:
    """Lê JSON gerado pelo script CLI.

    Retorna (propostas, metadata). Metadata contém ``gerado_em`` e
    ``total_arquivos_analisados``. Se JSON ausente ou inválido, retorna
    listas vazias e dict vazio.
    """
    p = path if path is not None else PATH_PROPOSTAS
    if not p.exists():
        return [], {}
    try:
        bruto = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [], {}
    propostas = [
        PropostaTipo(
            id_proposto=str(item.get("id_proposto", "")),
            n_amostras=int(item.get("n_amostras", 0)),
            exemplos_sha256=list(item.get("exemplos_sha256", [])),
            exemplos_paths=list(item.get("exemplos_paths_relativos", [])),
            regex_candidatos=list(item.get("regex_candidatos", [])),
            mime_principal=str(item.get("mime_principal", "")),
            extensao_principal=str(item.get("extensao_principal", "")),
            confianca_global=float(item.get("confianca_global", 0.0)),
        )
        for item in bruto.get("propostas", [])
    ]
    meta = {
        "gerado_em": bruto.get("gerado_em", ""),
        "total_arquivos_analisados": int(bruto.get("total_arquivos_analisados", 0)),
        "arquivos_sem_grupo": list(bruto.get("arquivos_sem_grupo", [])),
    }
    return propostas, meta


def _rejeitar_proposta(proposta: PropostaTipo, path_rejeitadas: Path | None = None) -> Path:
    """Apenda rejeição em JSON acumulativo. Retorna o path do arquivo."""
    destino = path_rejeitadas if path_rejeitadas is not None else PATH_REJEITADAS
    destino.parent.mkdir(parents=True, exist_ok=True)
    historico: list[dict] = []
    if destino.exists():
        try:
            d = json.loads(destino.read_text(encoding="utf-8"))
            if isinstance(d, list):
                historico = d
            elif isinstance(d, dict) and "rejeitadas" in d:
                historico = list(d["rejeitadas"])
        except (json.JSONDecodeError, OSError):
            historico = []
    historico.append(
        {
            "id_proposto": proposta.id_proposto,
            "rejeitada_em": datetime.now(timezone.utc).isoformat(),
            "n_amostras_quando_rejeitada": proposta.n_amostras,
            "confianca": proposta.confianca_global,
        }
    )
    destino.write_text(
        json.dumps({"rejeitadas": historico}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destino


def _aceitar_proposta(proposta: PropostaTipo, path_yaml: Path | None = None) -> dict:
    """Apenda entry skeleton em ``tipos_documento.yaml`` com status pendente.

    Não substitui regras existentes — apenas adiciona uma entry nova ao
    final, sinalizada com ``# AUTO-TIPO-PROPOSTAS-DASHBOARD aceite``.
    Validação semântica fica para o dono refinar manualmente antes da
    próxima execução do pipeline.

    Retorna dict com ``yaml_path``, ``id_proposto``, ``linha_apendada``.
    """
    destino = path_yaml if path_yaml is not None else PATH_TIPOS_YAML
    regex_lista = (
        "\n".join(f'      - "{rgx}"' for rgx in proposta.regex_candidatos)
        or '      - "PLACEHOLDER_REGEX"'
    )
    sufixo_data = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    chave_desc = "descricao"  # noqa: accent -- chave YAML canônica do schema
    bloco = (
        f"\n  # AUTO-TIPO-PROPOSTAS-DASHBOARD aceite em {sufixo_data}"
        f" -- revisar antes de habilitar\n"
        f"  - id: {proposta.id_proposto}\n"
        f'    {chave_desc}: "[REVISAR] tipo proposto automaticamente '
        f'a partir de {proposta.n_amostras} amostras"\n'
        f"    prioridade: especifico\n"
        f"    match_mode: any\n"
        f'    mimes: ["{proposta.mime_principal}"]\n'
        f"    regex_conteudo:\n{regex_lista}\n"
        f"    extrator_modulo: null\n"
        f"    origem_sprint: AUTO-TIPO-PROPOSTAS-DASHBOARD\n"
        f'    pasta_destino_template: "data/raw/{{pessoa}}/{proposta.id_proposto}/"\n'
        f"    renomear_template:\n"
        f'      com_data: "{proposta.id_proposto.upper()}_{{data:%Y-%m-%d}}_{{sha8}}.{{ext}}"\n'
        f'      sem_data: "{proposta.id_proposto.upper()}_{{sha8}}.{{ext}}"\n'
    )
    if destino.exists():
        atual = destino.read_text(encoding="utf-8")
        novo = atual.rstrip() + "\n" + bloco
        destino.write_text(novo, encoding="utf-8")
    else:
        destino.write_text("tipos:\n" + bloco, encoding="utf-8")
    return {
        "yaml_path": str(destino),
        "id_proposto": proposta.id_proposto,
        "linha_apendada": bloco.count("\n"),
    }


def _regenerar(
    cmd_path: str = "scripts/detectar_tipos_novos.py",
) -> tuple[int, str]:
    """Roda script CLI com --apply. Devolve (returncode, stdout)."""
    try:
        r = subprocess.run(
            ["python", cmd_path, "--apply"],
            cwd=str(_RAIZ),
            capture_output=True,
            text=True,
            timeout=120,
        )
        return r.returncode, r.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return 1, str(exc)


def _renderizar_kpis(propostas: list[PropostaTipo], meta: dict) -> None:
    total = len(propostas)
    total_alta_conf = sum(1 for p in propostas if p.confianca_global >= 0.6)
    c1, c2, c3 = st.columns(3)
    c1.metric("Propostas pendentes", total)
    c2.metric("Alta confiança (≥ 0.6)", total_alta_conf)
    c3.metric(
        "Arquivos analisados",
        meta.get("total_arquivos_analisados", 0),
    )


def _renderizar_tabela(propostas: list[PropostaTipo]) -> pd.DataFrame:
    """Tabela compacta. Retorna DataFrame para testes."""
    linhas = [
        {
            "id_proposto": p.id_proposto,
            "n_amostras": p.n_amostras,
            "extensao": p.extensao_principal,
            "confianca": p.confianca_global,
            "regex_count": len(p.regex_candidatos),
        }
        for p in propostas
    ]
    df = pd.DataFrame(linhas)
    if df.empty:
        st.info("Nenhuma proposta — rode `Regenerar` para varrer `_classificar/`.")
        return df
    st.dataframe(df, hide_index=True, use_container_width=True)
    return df


def _aplicar_filtros(
    propostas: list[PropostaTipo],
    extensoes_selecionadas: list[str],
    confianca_minima: float,
) -> list[PropostaTipo]:
    out = propostas
    if extensoes_selecionadas:
        out = [p for p in out if p.extensao_principal in extensoes_selecionadas]
    if confianca_minima > 0:
        out = [p for p in out if p.confianca_global >= confianca_minima]
    return out


def renderizar(dados=None, periodo=None, pessoa=None, ctx=None) -> None:  # noqa: ARG001
    """Render principal da aba "Tipos por detectar"."""
    st.title("Tipos por detectar")
    st.caption(
        "Propostas geradas automaticamente a partir de arquivos em "
        "``data/raw/_classificar/`` (fósseis sem regra em "
        "``tipos_documento.yaml``)."
    )

    propostas, meta = _carregar_propostas()
    _renderizar_kpis(propostas, meta)

    if meta.get("gerado_em"):
        st.caption(f"Última geração: {meta['gerado_em']}")

    col_a, col_b = st.columns([3, 1])
    with col_a:
        extensoes = sorted({p.extensao_principal for p in propostas if p.extensao_principal})
        extensoes_sel = st.multiselect(
            "Extensão",
            options=extensoes,
            default=extensoes,
            key="tipos_pendentes_ext",
        )
        confianca_minima = st.slider(
            "Confiança mínima",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.05,
            key="tipos_pendentes_conf",
        )
    with col_b:
        st.markdown("&nbsp;")
        if st.button("Regenerar", help="Varre _classificar/ novamente e atualiza JSON"):
            rc, out = _regenerar()
            if rc == 0:
                st.success("Regenerado.")
                st.code(out)
            else:
                st.error(f"Falha rc={rc}: {out[:300]}")

    filtradas = _aplicar_filtros(propostas, extensoes_sel, confianca_minima)
    _renderizar_tabela(filtradas)

    for p in filtradas:
        with st.expander(f"{p.id_proposto} ({p.n_amostras} amostras, conf {p.confianca_global})"):
            st.write(f"**Mime**: `{p.mime_principal}`")
            st.write(f"**Extensão**: `{p.extensao_principal}`")
            if p.regex_candidatos:
                st.write("**Regex candidatos**:")
                for rgx in p.regex_candidatos:
                    st.code(rgx)
            st.write("**Exemplos (sha256/path)**:")
            for sha, path in zip(p.exemplos_sha256, p.exemplos_paths, strict=False):
                st.write(f"  - `{sha}` — `{path}`")

            col_aceitar, col_rejeitar = st.columns(2)
            with col_aceitar:
                if st.button(
                    "Aceitar (cria entry YAML)",
                    key=f"aceitar_{p.id_proposto}",
                    help="Apenda skeleton em mappings/tipos_documento.yaml para revisão manual",
                ):
                    info = _aceitar_proposta(p)
                    st.success(f"Apendado em {info['yaml_path']} ({info['linha_apendada']} linhas)")
            with col_rejeitar:
                if st.button(
                    "Rejeitar",
                    key=f"rejeitar_{p.id_proposto}",
                ):
                    dest = _rejeitar_proposta(p)
                    st.info(f"Marcada em {dest.name}")


# "Cada arquivo em _classificar/ é uma pergunta não respondida." -- princípio da curadoria assistida
