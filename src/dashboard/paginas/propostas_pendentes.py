"""Cluster Sistema, aba "Propostas" (Sprint META-PROPOSTAS-DASHBOARD).

Lista propostas com ``status: aberta`` em ``docs/propostas/<categoria>/``.
Cada proposta é um arquivo Markdown com frontmatter YAML. O dashboard
expõe:

- KPI de pendentes no topo (também consumido como contador global pelo
  cluster Sistema).
- Filtros por tipo de proposta (descoberto dinamicamente das subpastas) e
  por idade em dias (alerta amareloesverdeado > 7d, vermelho > 30d).
- Expander por proposta com Markdown renderizado.
- Botão "Aprovar" move o arquivo para ``<categoria>/_aprovadas/<data>/``.
- Botão "Rejeitar" move para ``<categoria>/_rejeitadas/<data>/``.

A página é puramente leitor + mover-arquivo: não toca grafo, YAML de
mappings ou pipeline. A geração de propostas continua nos upstream
(``item_categorizer.py`` e ``linking_heuristico.py``). Aprovações que
exigem efeito downstream (e.g. adicionar regra em
``mappings/categorias_item.yaml``) ficam para sprints subsequentes, com a
movimentação física servindo como sinal "decisão aplicada".

Contrato: ``renderizar(dados, periodo, pessoa, ctx)`` espelhando as
outras páginas. Os 4 argumentos posicionais não são consumidos.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

_RAIZ = Path(__file__).resolve().parents[3]

# Raiz canônica das propostas. Apontada para um diretório configurável em
# testes via ``monkeypatch.setattr``.
DIR_PROPOSTAS = _RAIZ / "docs" / "propostas"

# Subpastas terminais que NÃO devem ser varridas como categorias-fonte
# (são destinos pós-decisão). Preservadas como prefixo de filename
# ``_`` ou ``data`` (ex: ``_aprovadas``, ``_rejeitadas``, ``_obsoletas``).
_PASTAS_TERMINAIS: frozenset[str] = frozenset(
    {"_aprovadas", "_rejeitadas", "_obsoletas", "sprint_nova"}
)


@dataclass(frozen=True)
class Proposta:
    """Proposta pendente lida do disco.

    Campos brutos do frontmatter (``id``, ``tipo``, ``status``,
    ``autor_proposta``) preservam o que o agente upstream gravou.
    Campos derivados (``categoria``, ``criado_em``, ``idade_dias``) são
    calculados na leitura para alimentar KPIs e filtros sem
    re-parsear o arquivo a cada render.
    """

    path: Path
    categoria: str  # nome da subpasta (categoria_item, linking, regra, ...)
    proposta_id: str
    tipo: str
    autor_proposta: str
    criado_em: datetime
    idade_dias: int
    conteudo_md: str


def _parse_frontmatter_yaml(texto: str) -> dict[str, str]:
    """Parser mínimo de frontmatter YAML de uma proposta.

    Sem dependência de PyYAML porque o frontmatter usado nas propostas é
    um dicionário plano de strings (sem listas, sem aninhamento). Evita
    obrigatoriedade de importar yaml na inicialização da página.
    """
    if not texto.startswith("---"):
        return {}
    fim = texto.find("\n---", 3)
    if fim < 0:
        return {}
    bloco = texto[3:fim].strip()
    out: dict[str, str] = {}
    for linha in bloco.splitlines():
        if ":" not in linha:
            continue
        chave, _, valor = linha.partition(":")
        # Trim "# comment" trailing comum em frontmatters legados que
        # vivem com lint relaxado (ex: o tipo canônico da subpasta
        # tem nome ASCII e o frontmatter coloca um comentário em linha
        # indicando suppressão de check de acentuação no arquivo todo).
        valor = valor.split("#", 1)[0]
        out[chave.strip()] = valor.strip()
    return out


def _ler_proposta(path: Path, agora: datetime) -> Proposta | None:
    """Lê arquivo de proposta. Retorna None se não estiver com status aberta."""
    try:
        texto = path.read_text(encoding="utf-8")
    except OSError:
        return None
    fm = _parse_frontmatter_yaml(texto)
    if fm.get("status") != "aberta":
        return None
    # mtime serve como timestamp robusto (frontmatter raramente carrega
    # ``criado_em``); mantemos coerência de fuso usando UTC.
    try:
        mtime_ts = path.stat().st_mtime
    except OSError:
        return None
    criado_em = datetime.fromtimestamp(mtime_ts, tz=timezone.utc)
    idade = max((agora - criado_em).days, 0)
    categoria = path.parent.name
    return Proposta(
        path=path,
        categoria=categoria,
        proposta_id=fm.get("id", path.stem),
        tipo=fm.get("tipo", categoria),
        autor_proposta=fm.get("autor_proposta", ""),
        criado_em=criado_em,
        idade_dias=idade,
        conteudo_md=texto,
    )


def _listar_pendentes(
    diretorio: Path | None = None,
    agora: datetime | None = None,
) -> list[Proposta]:
    """Varre ``docs/propostas/<categoria>/*.md`` retornando pendentes.

    Ignora pastas terminais (``_aprovadas``, ``_rejeitadas``,
    ``_obsoletas``, ``sprint_nova``) e arquivos na raiz de
    ``docs/propostas/`` (READMEs, templates, sprints de conferência).
    """
    base = diretorio if diretorio is not None else DIR_PROPOSTAS
    if not base.exists():
        return []
    ref = agora if agora is not None else datetime.now(timezone.utc)
    propostas: list[Proposta] = []
    for sub in sorted(base.iterdir()):
        if not sub.is_dir():
            continue
        if sub.name in _PASTAS_TERMINAIS or sub.name.startswith("_"):
            continue
        for md in sorted(sub.glob("*.md")):
            p = _ler_proposta(md, ref)
            if p is not None:
                propostas.append(p)
    return propostas


def _contar_pendentes(diretorio: Path | None = None) -> int:
    """KPI simples consumido pela página e potencialmente pelo header global."""
    return len(_listar_pendentes(diretorio))


def _mover_para_destino(
    proposta: Proposta, decisao: str, data_iso: str | None = None
) -> Path:
    """Move proposta para ``<categoria>/_<decisao>/<data>/<filename>``.

    ``decisao`` em {"aprovadas", "rejeitadas"}. Cria diretório destino se
    necessário. Retorna o path final do arquivo movido. Usado pelos
    botões "Aprovar" e "Rejeitar".
    """
    if decisao not in {"aprovadas", "rejeitadas"}:
        raise ValueError(f"decisao invalida: {decisao!r}")
    data = data_iso or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    destino_dir = proposta.path.parent / f"_{decisao}" / data
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / proposta.path.name
    shutil.move(str(proposta.path), str(destino))
    return destino


def _classificar_idade(dias: int) -> tuple[str, str]:
    """Devolve (rotulo, cor_css) para alerta visual da idade."""
    if dias > 30:
        return ("crítico", "#cc3344")
    if dias > 7:
        return ("alerta", "#cc9933")
    return ("recente", "#33aa55")


def _renderizar_kpis(propostas: list[Proposta]) -> None:
    total = len(propostas)
    criticos = sum(1 for p in propostas if p.idade_dias > 30)
    alertas = sum(1 for p in propostas if 7 < p.idade_dias <= 30)
    recentes = total - criticos - alertas
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pendentes", total)
    c2.metric(
        "Críticas (> 30d)",
        criticos,
        delta="atenção" if criticos else None,
        delta_color="inverse" if criticos else "normal",
    )
    c3.metric("Alertas (> 7d)", alertas)
    c4.metric("Recentes (≤ 7d)", recentes)


def _renderizar_tabela(propostas: list[Proposta]) -> pd.DataFrame:
    """Renderiza tabela compacta + devolve o DataFrame usado (para testes)."""
    linhas = [
        {
            "id": p.proposta_id,
            "tipo": p.tipo,
            "categoria": p.categoria,
            "criado_em": p.criado_em.strftime("%Y-%m-%d"),
            "idade_dias": p.idade_dias,
            "path": str(p.path.relative_to(_RAIZ)) if _RAIZ in p.path.parents else str(p.path),
        }
        for p in propostas
    ]
    df = pd.DataFrame(linhas)
    if df.empty:
        st.info("Nenhuma proposta casa com os filtros selecionados.")
        return df
    st.dataframe(df, hide_index=True, use_container_width=True)
    return df


def _aplicar_filtros(
    propostas: list[Proposta],
    tipos_selecionados: list[str],
    idade_minima: int,
) -> list[Proposta]:
    """Filtros: subconjunto de tipos + idade >= corte. Sem filtros mantém tudo."""
    out = propostas
    if tipos_selecionados:
        out = [p for p in out if p.tipo in tipos_selecionados or p.categoria in tipos_selecionados]
    if idade_minima > 0:
        out = [p for p in out if p.idade_dias >= idade_minima]
    return out


def _render_acoes(proposta: Proposta) -> None:
    """Botões aprovar / rejeitar dentro do expander de cada proposta."""
    col_ok, col_no = st.columns(2)
    chave_base = f"prop_{proposta.proposta_id}_{proposta.path.name}"
    with col_ok:
        if st.button("Aprovar", key=f"{chave_base}_ok"):
            destino = _mover_para_destino(proposta, "aprovadas")
            st.success(f"Movida para `{destino.relative_to(_RAIZ)}`.")
            st.rerun()
    with col_no:
        if st.button("Rejeitar", key=f"{chave_base}_no"):
            destino = _mover_para_destino(proposta, "rejeitadas")
            st.info(f"Rejeitada e arquivada em `{destino.relative_to(_RAIZ)}`.")
            st.rerun()


def renderizar(
    dados: dict[str, pd.DataFrame] | None = None,
    periodo: str | None = None,
    pessoa: str | None = None,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página Propostas (cluster Sistema, aba 4)."""
    del dados, periodo, pessoa, ctx

    st.markdown(
        "<h1 style='margin-bottom:.4rem;'>Propostas pendentes</h1>"
        "<p style='color:#888;margin-top:0;'>"
        "Decisões humanas pendentes nas propostas geradas pelos agentes "
        "(<code>item_categorizer</code>, <code>linking_heuristico</code> "
        "e demais). Aprovar move para <code>_aprovadas/&lt;data&gt;/</code>; "
        "rejeitar move para <code>_rejeitadas/&lt;data&gt;/</code>."
        "</p>",
        unsafe_allow_html=True,
    )

    propostas = _listar_pendentes()
    _renderizar_kpis(propostas)
    st.divider()

    if not propostas:
        st.success(
            "Sem propostas pendentes. Quando algum agente upstream emitir "
            "novo `.md` em `docs/propostas/<categoria>/`, ele aparece aqui."
        )
        return

    tipos_distintos = sorted({p.tipo for p in propostas} | {p.categoria for p in propostas})
    col_tipo, col_idade = st.columns([3, 1])
    with col_tipo:
        tipos_selecionados = st.multiselect(
            "Filtrar por tipo",
            options=tipos_distintos,
            default=[],
            key="propostas_tipos",
        )
    with col_idade:
        opcoes_idade = {"Todas": 0, "> 7 dias": 8, "> 30 dias": 31}
        rotulo_idade = st.selectbox(
            "Idade mínima",
            options=list(opcoes_idade.keys()),
            index=0,
            key="propostas_idade",
        )
        idade_minima = opcoes_idade[rotulo_idade]

    filtradas = _aplicar_filtros(propostas, tipos_selecionados, idade_minima)
    _renderizar_tabela(filtradas)

    st.divider()
    st.subheader("Detalhe e ação")
    for p in filtradas:
        rotulo_idade_p, cor_idade = _classificar_idade(p.idade_dias)
        titulo = (
            f"{p.proposta_id} — {p.tipo} — {p.idade_dias}d ({rotulo_idade_p})"
        )
        with st.expander(titulo):
            st.markdown(
                f"<div style='color:{cor_idade};font-size:.85em;'>"
                f"Categoria: <code>{p.categoria}</code> · "
                f"Autor: <code>{p.autor_proposta or '—'}</code> · "
                f"Criada em: {p.criado_em.strftime('%Y-%m-%d %H:%M UTC')}"
                "</div>",
                unsafe_allow_html=True,
            )
            st.markdown(p.conteudo_md)
            _render_acoes(p)


# "Decisão guardada na pasta é decisão sumida da memória; decisão na tela
# é decisão a um clique de virar regra." -- princípio do balcão de aprovações
