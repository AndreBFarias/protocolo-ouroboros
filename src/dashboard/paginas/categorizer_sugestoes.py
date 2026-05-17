"""Cluster Sistema, aba "Sugestor Outros" (Sprint CATEGORIZER-SUGESTAO-TFIDF).

Lê `data/output/sugestoes_categoria.json` gerado por
`scripts/sugerir_categorias.py`. Cada entry sugere top-K categorias
para uma transação atualmente classificada como "Outros". O dashboard
expõe:

- KPIs: total Outros, total sugeridas, alta confiança (>= 0.85).
- Filtros: confiança mínima slider + categoria sugerida multiselect.
- Tabela: id transação, descrição (truncada), top1, confiança.
- Expander por transação: lista completa de top-K + botão "Promover
  para overrides" (cria entry em mappings/overrides.yaml).

Contrato: ``renderizar(dados, periodo, pessoa, ctx)``.
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

_RAIZ = Path(__file__).resolve().parents[3]

PATH_SUGESTOES = _RAIZ / "data" / "output" / "sugestoes_categoria.json"
PATH_OVERRIDES = _RAIZ / "mappings" / "overrides.yaml"


def _carregar_sugestoes(path: Path | None = None) -> tuple[list[dict], dict]:
    """Lê JSON gerado pelo script CLI.

    Retorna (sugestoes_lista, metadata). Sugestões viram lista de dicts
    achatados (sem o id como chave) para iteração simples.
    """
    p = path if path is not None else PATH_SUGESTOES
    if not p.exists():
        return [], {}
    try:
        bruto = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [], {}
    sug_dict = bruto.get("sugestoes", {})
    lista = []
    for tx_id, item in sug_dict.items():
        lista.append(
            {
                "id": tx_id,
                "descricao": item.get("descricao", ""),
                "valor": float(item.get("valor", 0.0) or 0.0),
                "top1": item.get("top1", ""),
                "confianca_top1": float(item.get("confianca_top1", 0.0)),
                # Sprint CATEGORIZER-SUGESTAO-AUDITORIA-RUIDO:
                "risco_estimado": item.get("risco_estimado", "DESCONHECIDO"),
                "filtros_aplicados": item.get("filtros_aplicados", []),
                "sugestoes_detalhes": item.get("sugestoes", []),
            }
        )
    meta = {
        "gerado_em": bruto.get("gerado_em", ""),
        "xlsx_origem": bruto.get("xlsx_origem", ""),
        "total_transacoes": int(bruto.get("total_transacoes", 0)),
        "total_outros": int(bruto.get("total_outros", 0)),
        "total_sugeridas": int(bruto.get("total_sugeridas", 0)),
    }
    return lista, meta


def _aplicar_filtros(
    lista: list[dict],
    confianca_minima: float,
    categorias_selecionadas: list[str],
    riscos_aceitos: list[str] | None = None,
) -> list[dict]:
    """Sprint CATEGORIZER-SUGESTAO-AUDITORIA-RUIDO: aceita filtro de risco."""
    out = lista
    if confianca_minima > 0:
        out = [i for i in out if i["confianca_top1"] >= confianca_minima]
    if categorias_selecionadas:
        out = [i for i in out if i["top1"] in categorias_selecionadas]
    if riscos_aceitos:
        out = [i for i in out if i.get("risco_estimado", "DESCONHECIDO") in riscos_aceitos]
    return out


def _promover_para_overrides(descricao: str, categoria: str, path_yaml: Path | None = None) -> dict:
    """Apenda entry em overrides.yaml com `match`, `categoria`, `origem`.

    O override usa match exato pelo `local`. Para regras mais amplas
    (regex sobre n-grams), revisão manual fica responsável.
    """
    destino = path_yaml if path_yaml is not None else PATH_OVERRIDES
    sufixo_data = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    bloco = (
        f"\n# CATEGORIZER-SUGESTAO-TFIDF promocao em {sufixo_data}\n"
        f"- match: {json.dumps(descricao)}\n"
        f"  categoria: {categoria}\n"
        f"  origem: CATEGORIZER-SUGESTAO-TFIDF\n"
    )
    if destino.exists():
        destino.write_text(
            destino.read_text(encoding="utf-8").rstrip() + "\n" + bloco,
            encoding="utf-8",
        )
    else:
        destino.write_text(bloco.lstrip(), encoding="utf-8")
    return {
        "yaml_path": str(destino),
        "match": descricao,
        "categoria": categoria,
    }


def _regenerar() -> tuple[int, str]:
    """Roda `python -m scripts.sugerir_categorias`. Devolve (rc, out)."""
    try:
        r = subprocess.run(
            ["python", "-m", "scripts.sugerir_categorias"],
            cwd=str(_RAIZ),
            capture_output=True,
            text=True,
            timeout=120,
        )
        return r.returncode, r.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return 1, str(exc)


def _renderizar_kpis(lista: list[dict], meta: dict) -> None:
    """Sprint CATEGORIZER-SUGESTAO-AUDITORIA-RUIDO: KPIs por risco_estimado."""
    total_baixo = sum(1 for i in lista if i.get("risco_estimado") == "BAIXO")
    total_medio = sum(1 for i in lista if i.get("risco_estimado") == "MEDIO")
    total_alto = sum(1 for i in lista if i.get("risco_estimado") == "ALTO")
    total_desconhecido = sum(
        1 for i in lista if i.get("risco_estimado") == "DESCONHECIDO"
    )
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Outros no XLSX", meta.get("total_outros", 0))
    c2.metric("Risco BAIXO", total_baixo, help="Filtro de domínio aprovou — candidato seguro")
    c3.metric("Risco MEDIO", total_medio, help="1 filtro falhou — revisar")
    c4.metric(
        "Risco ALTO",
        total_alto,
        help="Token proibitivo OU 2+ filtros falharam — rejeitar",
    )
    c5.metric(
        "Desconhecido",
        total_desconhecido,
        help="Categoria sem entry em dominio_categorias.yaml",
    )


def _renderizar_tabela(lista: list[dict]) -> pd.DataFrame:
    """Tabela com coluna risco. Para colorir, usa emoji só nesse contexto."""
    if not lista:
        st.info("Nenhuma sugestão — rode `Regenerar` para gerar a partir do XLSX.")
        return pd.DataFrame()
    df = pd.DataFrame(
        [
            {
                "id": i["id"],
                "descricao": i["descricao"][:60],
                "valor": round(i.get("valor", 0.0), 2),
                "sugestao_top1": i["top1"],
                "confianca": round(i["confianca_top1"], 2),
                "risco": i.get("risco_estimado", "DESCONHECIDO"),
            }
            for i in lista
        ]
    )
    st.dataframe(df, hide_index=True, use_container_width=True)
    return df


def renderizar(dados=None, periodo=None, pessoa=None, ctx=None) -> None:  # noqa: ARG001
    """Render principal da aba "Sugestor Outros"."""
    st.title("Sugestor Outros (TF-IDF)")
    st.caption(
        "Sugere categorias para transações atualmente classificadas como "
        "**Outros** via similaridade cosseno + TF-IDF sobre transações já "
        "categorizadas. Threshold ≥ 0.85 é candidato razoável para auto-promoção."
    )

    lista, meta = _carregar_sugestoes()
    _renderizar_kpis(lista, meta)
    if meta.get("gerado_em"):
        st.caption(f"Última geração: {meta['gerado_em']}")

    # Filtros + regenerar:
    col_a, col_b = st.columns([3, 1])
    with col_a:
        confianca_minima = st.slider(
            "Confiança mínima",
            min_value=0.0,
            max_value=1.0,
            value=0.85,
            step=0.05,
            key="sugestor_conf",
        )
        riscos_sel = st.multiselect(
            "Risco estimado (filtro de domínio)",
            options=["BAIXO", "MEDIO", "ALTO", "DESCONHECIDO"],
            default=["BAIXO"],
            key="sugestor_risco",
            help="BAIXO = filtro de domínio aprovou. Recomendado promover apenas BAIXO.",
        )
        categorias_disponiveis = sorted(Counter(i["top1"] for i in lista).keys())
        categorias_sel = st.multiselect(
            "Categoria sugerida (top1)",
            options=categorias_disponiveis,
            default=[],
            key="sugestor_cat",
        )
    with col_b:
        st.markdown("&nbsp;")
        if st.button("Regenerar", help="Re-executa scripts/sugerir_categorias.py"):
            rc, out = _regenerar()
            if rc == 0:
                st.success("Regenerado.")
                st.code(out[-300:])
            else:
                st.error(f"Falha rc={rc}: {out[:300]}")

    filtradas = _aplicar_filtros(lista, confianca_minima, categorias_sel, riscos_sel)
    st.write(f"**{len(filtradas)} sugestões após filtros.**")
    _renderizar_tabela(filtradas)

    # Expander por sugestão (máx 50 pra não pesar):
    for item in filtradas[:50]:
        risco = item.get("risco_estimado", "DESCONHECIDO")
        with st.expander(
            f"[{risco}] {item['descricao'][:60]} → {item['top1']} "
            f"({item['confianca_top1']:.2f}) — R$ {item.get('valor', 0):.2f}"
        ):
            filtros_str = ", ".join(item.get("filtros_aplicados", []) or ["(nenhum)"])
            st.write(f"**Filtros aplicados**: `{filtros_str}`")
            for s in item["sugestoes_detalhes"]:
                st.write(
                    f"  - **{s.get('categoria')}** · "
                    f"conf {s.get('confianca'):.2f} · "
                    f"votos {s.get('votos', 0)}"
                )
            if st.button(
                f"Promover '{item['top1']}' para overrides",
                key=f"promover_{item['id']}",
                help="Apenda match exato em mappings/overrides.yaml",
            ):
                info = _promover_para_overrides(item["descricao"], item["top1"])
                st.success(f"Promovido em {info['yaml_path']}")


# "Outros e debito cognitivo; sugestor e juro pago." -- principio
