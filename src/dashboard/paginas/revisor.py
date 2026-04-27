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
import re
import sqlite3
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

# Limite mínimo para acionar sugestão de patch (3+ pendências com mesma
# dimensão errada -> padrão recorrente).
LIMITE_PADRAO_RECORRENTE: int = 3

# Mascaramento PII (LGPD) antes de gravar relatório em disco.
_REGEX_CPF = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
_REGEX_CNPJ = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
_REGEX_CPF_CRU = re.compile(r"(?<!\d)\d{11}(?!\d)")
_REGEX_CNPJ_CRU = re.compile(r"(?<!\d)\d{14}(?!\d)")


def mascarar_pii(texto: str) -> str:
    """Mascara CPFs e CNPJs em texto livre (regex formatado e cru).

    LGPD-safe: relatório local de revisão pode ser exportado/compartilhado;
    melhor garantir que nenhum identificador escape. Não muda a semântica do
    texto -- só substitui dígitos por ``X``.
    """
    if not texto:
        return texto
    saida = _REGEX_CPF.sub("XXX.XXX.XXX-XX", texto)
    saida = _REGEX_CNPJ.sub("XX.XXX.XXX/XXXX-XX", saida)
    saida = _REGEX_CPF_CRU.sub("XXXXXXXXXXX", saida)
    saida = _REGEX_CNPJ_CRU.sub("XXXXXXXXXXXXXX", saida)
    return saida


def garantir_schema(caminho: Path) -> None:
    """Cria o SQLite de revisão com schema canônico se não existir.

    Schema:
      revisao(item_id TEXT, dimensao TEXT, ok INTEGER, observacao TEXT, ts TEXT)
      PK (item_id, dimensao); índices em ts e dimensao.

    ``ok`` admite ``NULL`` (estado "não-aplicável"). Por isso a coluna não é
    NOT NULL aqui (decisão consciente: a spec diz NULL=N/A).
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(caminho)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS revisao (
                item_id TEXT NOT NULL,
                dimensao TEXT NOT NULL,
                ok INTEGER,
                observacao TEXT,
                ts TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (item_id, dimensao)
            );
            CREATE INDEX IF NOT EXISTS idx_revisao_ts ON revisao (ts);
            CREATE INDEX IF NOT EXISTS idx_revisao_dimensao ON revisao (dimensao);
            """
        )
        conn.commit()
    finally:
        conn.close()


def salvar_marcacao(
    caminho: Path,
    item_id: str,
    dimensao: str,
    ok: int | None,
    observacao: str = "",
) -> None:
    """Persiste UPSERT de marcação por (item_id, dimensao).

    Se já existe marcação para o par, sobrescreve com ``ts = now`` -- isto
    é intencional (humano pode revisar a própria marcação na sessão).
    """
    garantir_schema(caminho)
    conn = sqlite3.connect(caminho)
    try:
        conn.execute(
            """
            INSERT INTO revisao (item_id, dimensao, ok, observacao, ts)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(item_id, dimensao) DO UPDATE SET
              ok = excluded.ok,
              observacao = excluded.observacao,
              ts = excluded.ts
            """,
            (item_id, dimensao, ok, observacao),
        )
        conn.commit()
    finally:
        conn.close()


def carregar_marcacoes(caminho: Path, item_id: str | None = None) -> list[dict]:
    """Carrega marcações (todas ou de um item específico)."""
    if not caminho.exists():
        return []
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    try:
        if item_id is not None:
            cursor = conn.execute(
                "SELECT item_id, dimensao, ok, observacao, ts FROM revisao WHERE item_id = ?",
                (item_id,),
            )
        else:
            cursor = conn.execute("SELECT item_id, dimensao, ok, observacao, ts FROM revisao")
        resultado = [dict(row) for row in cursor]
    finally:
        conn.close()
    return resultado


def _taxa_fidelidade(marcacoes: list[dict]) -> float:
    """Proporção de marcações com ``ok = 1`` em relação ao total não-NULL.

    Marcações ``NULL`` (não-aplicável) ficam fora do denominador para não
    poluir a métrica. Retorna 0.0 quando não há nada relevante.
    """
    relevantes = [m for m in marcacoes if m["ok"] is not None]
    if not relevantes:
        return 0.0
    aprovadas = sum(1 for m in relevantes if m["ok"] == 1)
    return aprovadas / len(relevantes)


def detectar_padroes_recorrentes(
    marcacoes: list[dict],
    limite: int = LIMITE_PADRAO_RECORRENTE,
) -> list[dict]:
    """Agrupa marcações ``ok=0`` por dimensão e devolve as recorrentes.

    Retorna lista de dicts ``{dimensao: str, contagem: int, item_ids: list[str]}``
    apenas para dimensões com pelo menos ``limite`` reprovações. Padrão
    recorrente vira candidato a "Sugerir patch".
    """
    por_dimensao: dict[str, list[str]] = {}
    for marca in marcacoes:
        if marca["ok"] == 0:
            por_dimensao.setdefault(marca["dimensao"], []).append(marca["item_id"])
    resultado: list[dict] = []
    for dimensao, item_ids in por_dimensao.items():
        if len(item_ids) >= limite:
            resultado.append(
                {
                    "dimensao": dimensao,
                    "contagem": len(item_ids),
                    "item_ids": sorted(set(item_ids)),
                }
            )
    resultado.sort(key=lambda d: -d["contagem"])
    return resultado


def gerar_relatorio_markdown(
    marcacoes: list[dict],
    pendencias_indexadas: dict[str, dict] | None = None,
) -> str:
    """Produz relatório em Markdown da sessão atual.

    PII mascarada (CPF/CNPJ formatados e crus). Inclui:
      - Cabeçalho com data/hora.
      - Taxa de fidelidade global.
      - Tabela por item com dimensões aprovadas/reprovadas.
      - Padrões recorrentes (>=3 reprovações na mesma dimensão).

    ``pendencias_indexadas`` é opcional: se fornecido, enriquece a tabela
    com ``tipo_documento`` e nome canônico.
    """
    pendencias_indexadas = pendencias_indexadas or {}
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    taxa = _taxa_fidelidade(marcacoes)
    padroes = detectar_padroes_recorrentes(marcacoes)

    linhas: list[str] = []
    linhas.append(f"# Revisão visual -- sessão {agora}\n")
    linhas.append(f"Total de marcações: **{len(marcacoes)}**\n")
    linhas.append(
        f"Taxa de fidelidade humana: **{taxa * 100:.1f}%** "
        f"({sum(1 for m in marcacoes if m['ok'] == 1)} OK / "
        f"{sum(1 for m in marcacoes if m['ok'] is not None)} avaliadas)\n"
    )

    linhas.append("\n## Itens revisados\n")
    por_item: dict[str, list[dict]] = {}
    for marca in marcacoes:
        por_item.setdefault(marca["item_id"], []).append(marca)
    for item_id, lista in sorted(por_item.items()):
        info = pendencias_indexadas.get(item_id, {})
        tipo_doc = info.get("metadata", {}).get("tipo_documento", info.get("tipo", "?"))
        linhas.append(f"\n### {mascarar_pii(item_id)}\n")
        linhas.append(f"- Tipo: `{tipo_doc}`")
        for marca in sorted(lista, key=lambda m: m["dimensao"]):
            estado = "OK" if marca["ok"] == 1 else "ERRO" if marca["ok"] == 0 else "Não-aplicável"
            obs = mascarar_pii(marca.get("observacao") or "")
            obs_render = f" -- {obs}" if obs else ""
            linhas.append(f"- {marca['dimensao']}: **{estado}**{obs_render}")

    if padroes:
        linhas.append("\n## Padrões recorrentes\n")
        for pad in padroes:
            linhas.append(
                f"- Dimensão `{pad['dimensao']}` reprovada em "
                f"**{pad['contagem']}** itens. Candidato a regra YAML."
            )

    linhas.append("\n---\n")
    linhas.append(
        '*"A revisão visual é a ponte entre intuição humana e automação '
        'determinística." -- princípio do alinhamento mensurável*\n'
    )
    return "\n".join(linhas)


def gravar_relatorio(
    marcacoes: list[dict],
    diretorio: Path,
    pendencias_indexadas: dict[str, dict] | None = None,
) -> Path:
    """Grava relatório em ``diretorio/<YYYY-MM-DD>.md`` (sobrescreve)."""
    diretorio.mkdir(parents=True, exist_ok=True)
    data_str = datetime.now().strftime("%Y-%m-%d")
    destino = diretorio / f"{data_str}.md"
    conteudo = gerar_relatorio_markdown(marcacoes, pendencias_indexadas)
    destino.write_text(conteudo, encoding="utf-8")
    return destino


def sugerir_patch_yaml(padroes: list[dict]) -> str:
    """Gera diff sugerido em YAML para copy-paste manual.

    Estratégia: para cada dimensão recorrentemente reprovada, propõe um bloco
    de regra placeholder em ``mappings/categorias_item.yaml`` (ou similar).
    Decisão consciente: NUNCA aplica patch automaticamente -- humano sempre
    aprova edição manual (regra do projeto).
    """
    if not padroes:
        return "# nenhum padrão recorrente detectado nesta sessão\n"
    blocos: list[str] = ["# diff sugerido para copy-paste em mappings/*.yaml\n"]
    for pad in padroes:
        blocos.append(f"# Dimensão '{pad['dimensao']}' reprovada {pad['contagem']}x.")
        blocos.append("# Itens afetados:")
        for iid in pad["item_ids"][:5]:
            blocos.append(f"#   - {mascarar_pii(iid)}")
        blocos.append("# Sugestão: adicionar regra YAML abaixo (humano edita campo)\n")
        blocos.append(f"- nome: ajuste_{pad['dimensao']}_pos_revisao_humana")
        blocos.append("  pattern: TODO_humano")
        blocos.append(f"  campo: {pad['dimensao']}")
        blocos.append("  prioridade: 100\n")
    return "\n".join(blocos)


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
            coletadas[dimensao] = (ROTULOS_ESTADO[rotulo], obs)

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
                    for dimensao, (estado, obs) in coletadas.items():
                        salvar_marcacao(
                            CAMINHO_REVISAO_HUMANA,
                            item_id,
                            dimensao,
                            estado,
                            obs,
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

    # Ações da sessão: relatório + sugestor de patch.
    col_rel, col_patch = st.columns(2)
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
