"""Página Revisor Visual Semi-Automatizado -- Sprint D2.

Substitui a Sprint AUDITORIA-ARTESANAL-FINAL (revisão CLI 1-a-1 inviável em
~760 arquivos). Aqui o supervisor humano valida lado-a-lado:

  - Esquerda: preview do arquivo original (PDF/imagem) via componente Sprint 74.
  - Direita: JSON estruturado do que o extrator viu (data, valor, itens,
    fornecedor, pessoa).
  - Embaixo: checkboxes por dimensão (3 estados: OK / erro / não-aplicável) +
    campo livre para observação.

Marcações persistem em ``data/output/revisao_humana.sqlite`` (gitignored).
Botão "Gerar relatório" produz ``docs/revisoes/<data>.md`` com PII mascarada
e taxa de fidelidade. Botão "Sugerir patch" abre diff em ``mappings/*.yaml``
quando padrão recorrente é detectado (3+ pendências com mesma dimensão errada).

Princípios:
  - Read-only em ``data/raw/`` (revisor não move/deleta arquivos).
  - SQLite (não JSON/YAML) para alinhamento com ``grafo.sqlite``.
  - PII mascarada antes de gravar relatório (regex CPF/CNPJ).
  - ``revisor_*`` é o namespace de session_state (não colide com
    ``filtro_*`` da Sprint 73 nem ``avancado_*`` da Sprint 77).
  - Paginação 10 itens por vez (volume real de 760 PDFs esgotaria browser).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from src.dashboard.componentes.preview_documento import preview_documento
from src.dashboard.dados import (
    CAMINHO_REVISAO_HUMANA,
    listar_pendencias_revisao,
)
from src.dashboard.tema import (
    callout_html,
    hero_titulo_html,
    subtitulo_secao_html,
)

# Dimensões canônicas que o supervisor avalia. A ordem reflete a importância
# percebida durante a auditoria 2026-04-26 (data e valor têm impacto direto
# no XLSX; itens/fornecedor/pessoa são metadados secundários).
DIMENSOES_CANONICAS: tuple[str, ...] = (
    "data",
    "valor",
    "itens",
    "fornecedor",
    "pessoa",
)

# Estados de marcação por dimensão.
ESTADO_OK: int = 1
ESTADO_ERRO: int = 0
ESTADO_NA: None = None

ROTULOS_ESTADO: dict[str, int | None] = {
    "OK": ESTADO_OK,
    "Erro": ESTADO_ERRO,
    "Não-aplicável": ESTADO_NA,
}

# Limite de paginação evita carregar 760 PDFs no navegador.
ITENS_POR_PAGINA: int = 10

# Sprint ANTI-MIGUE-08: logica pura extraida para revisor_logic.py.
# Re-export local preserva contratos importados por testes
# (``from src.dashboard.paginas.revisor import garantir_schema, ...``).
from src.dashboard.paginas.revisor_logic import (  # noqa: E402, F401
    _HEADER_GROUND_TRUTH_CSV,
    _REGEX_CNPJ,
    _REGEX_CNPJ_CRU,
    _REGEX_CPF,
    _REGEX_CPF_CRU,
    LIMITE_PADRAO_RECORRENTE,
    _comparar_canonico,
    _taxa_fidelidade,
    carregar_marcacoes,
    detectar_padroes_recorrentes,
    extrair_valor_etl_para_dimensao,
    garantir_schema,
    gerar_ground_truth_csv,
    gerar_relatorio_markdown,
    gravar_relatorio,
    mascarar_pii,
    salvar_marcacao,
    sugerir_patch_yaml,
)


def _renderizar_painel_item(pendencia: dict, marcacoes_item: list[dict]) -> dict[str, Any]:
    """Renderiza painel de uma pendência e devolve marcações coletadas.

    Retorna dict ``{dimensao: (estado_int_ou_none, observacao_str)}``.
    Não persiste em disco -- caller decide quando chamar ``salvar_marcacao``.
    """
    item_id = pendencia["item_id"]
    caminho_str = pendencia.get("caminho", "")
    metadata = pendencia.get("metadata", {})

    col_esq, col_dir = st.columns([3, 2])

    with col_esq:
        st.markdown(subtitulo_secao_html("Original"), unsafe_allow_html=True)
        if caminho_str:
            caminho = Path(caminho_str)
            if not caminho.exists():
                st.markdown(
                    callout_html(
                        "warning",
                        f"Arquivo original ausente: `{caminho.name}`",
                    ),
                    unsafe_allow_html=True,
                )
            elif caminho.is_dir():
                # Pendências em data/raw/_conferir/ podem ser diretórios
                # com fallback de supervisor (várias fotos + proposta MD).
                # Lista o conteúdo em vez de tentar preview de arquivo único.
                st.markdown(
                    callout_html(
                        "info",
                        f"Pendência é um diretório com fallback de supervisor: `{caminho.name}`",
                    ),
                    unsafe_allow_html=True,
                )
                arquivos = sorted(p for p in caminho.iterdir() if p.is_file())
                if arquivos:
                    primeira_imagem = next(
                        (
                            p
                            for p in arquivos
                            if p.suffix.lower()
                            in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
                        ),
                        None,
                    )
                    if primeira_imagem is not None:
                        preview_documento(primeira_imagem, altura=460)
                    st.caption(
                        "Conteúdo do diretório: "
                        + ", ".join(p.name for p in arquivos[:8])
                        + ("..." if len(arquivos) > 8 else "")
                    )
                else:
                    st.caption("Diretório vazio.")
            else:
                preview_documento(caminho, altura=520)
        else:
            st.markdown(
                callout_html(
                    "info",
                    "Pendência sem caminho de arquivo (somente node do grafo).",
                ),
                unsafe_allow_html=True,
            )

    with col_dir:
        st.markdown(subtitulo_secao_html("Extraído"), unsafe_allow_html=True)
        # Metadata serializada -- não tem PII via design (já passou pelo mask
        # do extrator), mas mascaramos defensivamente para st.code render.
        meta_render = mascarar_pii(json.dumps(metadata, indent=2, ensure_ascii=False))
        st.code(meta_render, language="json")
        st.caption(f"item_id: `{item_id[:60]}{'…' if len(item_id) > 60 else ''}`")
        st.caption(f"tipo: `{pendencia.get('tipo', '?')}`")

    st.markdown("---")
    st.markdown(subtitulo_secao_html("Avaliação por dimensão"), unsafe_allow_html=True)

    estados_existentes: dict[str, dict] = {m["dimensao"]: m for m in marcacoes_item}
    coletadas: dict[str, tuple[int | None, str]] = {}

    cols = st.columns(len(DIMENSOES_CANONICAS))
    for idx, dimensao in enumerate(DIMENSOES_CANONICAS):
        with cols[idx]:
            st.markdown(f"**{dimensao}**")
            # Auditoria 4-way (sessão 2026-04-29): 4 fontes (ETL/Opus/Grafo/Humano).
            valor_etl = extrair_valor_etl_para_dimensao(pendencia, dimensao)
            valor_opus = (
                estados_existentes.get(dimensao, {}).get("valor_opus") or ""
            )
            valor_grafo = (
                estados_existentes.get(dimensao, {}).get("valor_grafo_real") or ""
            )

            # Comparacao canonica (case-insensitive, sem espacos).
            div_etl_grafo = _comparar_canonico(valor_etl, valor_grafo)  # Tipo B
            div_etl_opus = _comparar_canonico(valor_etl, valor_opus)    # Tipo A
            div_grafo_opus = _comparar_canonico(valor_grafo, valor_opus)  # Tipo A pos-norm

            # ETL: o que o pipeline extraiu (sempre exibido).
            marcador_etl = " :red[(diverge)]" if (div_etl_opus or div_etl_grafo) else ""
            st.caption(f"**ETL:** {valor_etl or '---'}{marcador_etl}")

            # Opus: o que o supervisor Opus marcou.
            if valor_opus:
                marcador_opus = " :red[(diverge)]" if (div_etl_opus or div_grafo_opus) else ""
                opus_render = valor_opus if len(valor_opus) <= 60 else valor_opus[:57] + "..."
                st.caption(f"**Opus:** {opus_render}{marcador_opus}")
            else:
                st.caption("**Opus:** _(sem proposta)_")

            # Grafo: estado canonico apos normalizacao (sintetico Sprint 107 etc).
            if valor_grafo:
                marcador_grafo = " :red[(diverge)]" if (div_etl_grafo or div_grafo_opus) else ""
                grafo_render = valor_grafo if len(valor_grafo) <= 60 else valor_grafo[:57] + "..."
                st.caption(f"**Grafo:** {grafo_render}{marcador_grafo}")
            else:
                st.caption("**Grafo:** _(sem node ou não populado)_")

            # Humano: radio OK/Erro/N-A.
            valor_existente = estados_existentes.get(dimensao, {}).get("ok")
            obs_existente = estados_existentes.get(dimensao, {}).get("observacao") or ""
            indice_default = 2  # Não-aplicável
            if valor_existente == 1:
                indice_default = 0
            elif valor_existente == 0:
                indice_default = 1
            rotulo = st.radio(
                f"Estado {dimensao}",
                list(ROTULOS_ESTADO.keys()),
                index=indice_default,
                key=f"revisor_estado_{item_id}_{dimensao}",
                label_visibility="collapsed",
            )
            obs = st.text_input(
                f"Observação {dimensao}",
                value=obs_existente,
                key=f"revisor_obs_{item_id}_{dimensao}",
                label_visibility="collapsed",
                placeholder="observação opcional",
            )
            # Persiste valor_etl + valor_grafo_real junto com o estado humano
            # para permitir export ground-truth a posteriori.
            coletadas[dimensao] = (ROTULOS_ESTADO[rotulo], obs, valor_etl, valor_grafo)

    return coletadas


def renderizar(
    dados: dict | None = None,
    periodo: str | None = None,
    pessoa: str | None = None,
    ctx: dict | None = None,
) -> None:
    """Ponto de entrada da página Revisor (cluster Documentos).

    Argumentos não utilizados: a fonte de verdade é o grafo + diretórios
    raw, não o XLSX. Mantido apenas para casar a assinatura comum das
    demais páginas (compatibilidade com ``app.py``).
    """
    _ = dados, periodo, pessoa, ctx

    st.markdown(
        hero_titulo_html(
            "",
            "Revisor Visual",
            "Validação semi-automatizada de extrações ambíguas. Marcação "
            "lado-a-lado (foto/PDF + JSON) para alinhar visão humano-máquina.",
        ),
        unsafe_allow_html=True,
    )

    pendencias = listar_pendencias_revisao()
    total = len(pendencias)
    indexadas = {p["item_id"]: p for p in pendencias}

    marcacoes = carregar_marcacoes(CAMINHO_REVISAO_HUMANA)
    item_ids_revisados = {m["item_id"] for m in marcacoes}
    revisados = sum(1 for p in pendencias if p["item_id"] in item_ids_revisados)
    aguardando = total - revisados
    taxa = _taxa_fidelidade(marcacoes)

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Pendências", total)
    col_b.metric("Revisadas", revisados)
    col_c.metric("Aguardando", aguardando)
    col_d.metric("Fidelidade", f"{taxa * 100:.0f}%")

    # Sprint 103: resumo de divergências ETL vs Opus em tabela.
    com_opus = [m for m in marcacoes if m.get("valor_opus")]
    if com_opus:
        divergentes = [
            m
            for m in com_opus
            if (m.get("valor_etl") or "").strip().lower()
            != (m.get("valor_opus") or "").strip().lower()
            and m.get("valor_etl")
        ]
        st.markdown(
            subtitulo_secao_html(
                f"Comparação ETL × Opus ({len(divergentes)} divergentes "
                f"de {len(com_opus)} marcações com proposta Opus)"
            ),
            unsafe_allow_html=True,
        )
        if divergentes:
            tabela_diff = [
                {
                    "item": d["item_id"][:50] + ("…" if len(d["item_id"]) > 50 else ""),
                    "dimensão": d["dimensao"],
                    "ETL": (d.get("valor_etl") or "")[:40],
                    "Opus": (d.get("valor_opus") or "")[:40],
                }
                for d in divergentes[:30]
            ]
            st.dataframe(tabela_diff, use_container_width=True, hide_index=True)
            if len(divergentes) > 30:
                st.caption(
                    f"... e mais {len(divergentes) - 30} divergências. Use export CSV "
                    "para ver todas."
                )

    if total == 0:
        st.markdown(
            callout_html(
                "success",
                "Nenhuma pendência de revisão. Tudo está classificado e "
                "vinculado dentro do limiar de confiança.",
                titulo="Inbox limpa",
            ),
            unsafe_allow_html=True,
        )
        return

    st.markdown("---")

    # Sprint UX-117: filtros 'Tipo de pendência' e 'Página' renderizam no
    # topo da página Revisor (st.columns([2,1])), NÃO mais na sidebar global.
    # Antes poluíam Hoje/Dinheiro/Análise/Metas que não usam esses filtros.
    # Mês / Pessoa / Forma de pagamento permanecem na sidebar global como
    # filtros transversais. Session_state keys preservadas (revisor_filtro_tipo,
    # revisor_pagina) para retrocompatibilidade.
    tipos_disponiveis = sorted({p["tipo"] for p in pendencias})

    # total_paginas depende do filtro de tipo. Calcula primeiro o filtro,
    # depois total_paginas, depois renderiza number_input com max_value real.
    col_tipo, col_pagina = st.columns([2, 1])
    with col_tipo:
        tipo_filtro = st.multiselect(
            "Tipo de pendência",
            tipos_disponiveis,
            default=tipos_disponiveis,
            key="revisor_filtro_tipo",
        )
    pendencias_filtradas = [p for p in pendencias if p["tipo"] in tipo_filtro]

    if not pendencias_filtradas:
        st.markdown(
            callout_html(
                "info",
                "Nenhuma pendência casa o filtro atual.",
            ),
            unsafe_allow_html=True,
        )
        return

    # Paginação 10 por página (volume real esgotaria browser).
    total_paginas = max(1, (len(pendencias_filtradas) + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)
    with col_pagina:
        pagina_atual = st.number_input(
            "Página",
            min_value=1,
            max_value=total_paginas,
            value=1,
            step=1,
            key="revisor_pagina",
        )
    inicio = (pagina_atual - 1) * ITENS_POR_PAGINA
    fim = inicio + ITENS_POR_PAGINA
    pagina = pendencias_filtradas[inicio:fim]

    st.caption(
        f"Exibindo {len(pagina)} de {len(pendencias_filtradas)} pendências "
        f"(página {pagina_atual} de {total_paginas})."
    )

    for idx, pendencia in enumerate(pagina, start=1):
        item_id = pendencia["item_id"]
        with st.expander(
            f"[{pendencia['tipo']}] {item_id[:80]}",
            expanded=(idx == 1),
        ):
            marcacoes_item = [m for m in marcacoes if m["item_id"] == item_id]
            coletadas = _renderizar_painel_item(pendencia, marcacoes_item)

            col_save, col_skip = st.columns([1, 1])
            with col_save:
                if st.button(
                    "Salvar marcações",
                    key=f"revisor_salvar_{item_id}",
                ):
                    for dimensao, (estado, obs, valor_etl, valor_grafo) in coletadas.items():
                        salvar_marcacao(
                            CAMINHO_REVISAO_HUMANA,
                            item_id,
                            dimensao,
                            estado,
                            obs,
                            valor_etl=valor_etl,
                            valor_grafo_real=valor_grafo,
                        )
                    st.markdown(
                        callout_html(
                            "success",
                            f"Marcações de `{len(coletadas)}` dimensões persistidas.",
                        ),
                        unsafe_allow_html=True,
                    )
            with col_skip:
                st.caption(
                    "Pular: feche o expander e abra o próximo. Marcações "
                    "não salvas são descartadas."
                )

    st.markdown("---")

    # Ações da sessão: relatório + sugestor de patch + export ground-truth (S103).
    col_rel, col_patch, col_csv = st.columns(3)
    with col_rel:
        if st.button("Gerar relatório da sessão", key="revisor_gerar_relatorio"):
            destino_dir = Path(__file__).resolve().parents[3] / "docs" / "revisoes"
            destino = gravar_relatorio(
                marcacoes,
                destino_dir,
                pendencias_indexadas=indexadas,
            )
            st.markdown(
                callout_html(
                    "success",
                    f"Relatório gravado em `{destino.relative_to(destino_dir.parents[1])}`. "
                    f"PII mascarada (CPF/CNPJ).",
                    titulo="Relatório pronto",
                ),
                unsafe_allow_html=True,
            )
    with col_csv:
        # Sprint 103: export ground-truth CSV com 3 colunas (ETL/Opus/Humano)
        # + flag divergencia. Util para análise quantitativa pós-sessão e
        # para alimentar futuras métricas de fidelidade do extrator.
        if st.button("Exportar ground-truth CSV", key="revisor_exportar_csv"):
            destino_csv = (
                Path(__file__).resolve().parents[3]
                / "docs"
                / "revisoes"
                / f"ground_truth_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"
            )
            n = gerar_ground_truth_csv(CAMINHO_REVISAO_HUMANA, destino_csv)
            st.markdown(
                callout_html(
                    "success",
                    f"CSV gerado: `{destino_csv.relative_to(destino_csv.parents[2])}` "
                    f"({n} linha(s)). PII mascarada.",
                    titulo="Ground-truth pronto",
                ),
                unsafe_allow_html=True,
            )

    with col_patch:
        padroes = detectar_padroes_recorrentes(marcacoes)
        if padroes and st.button("Sugerir patch YAML", key="revisor_sugerir_patch"):
            diff = sugerir_patch_yaml(padroes)
            st.markdown(
                callout_html(
                    "info",
                    f"{len(padroes)} padrão(ões) detectado(s). Diff abaixo "
                    "para copy-paste manual em `mappings/*.yaml`.",
                ),
                unsafe_allow_html=True,
            )
            st.code(diff, language="yaml")
        elif not padroes:
            st.caption(
                f"Sugestor de patch fica disponível ao detectar "
                f">= {LIMITE_PADRAO_RECORRENTE} reprovações na mesma dimensão."
            )


# "A revisão visual é a ponte entre intuição humana e automação determinística."
# -- princípio do alinhamento mensurável
