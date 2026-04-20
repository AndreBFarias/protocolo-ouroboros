"""Ingestor compartilhado de documentos no grafo (Sprint 47c -- reusável 44/44b/46/47).

Sprint 47c (cupom de garantia estendida) é o primeiro caller; Sprints 44 (DANFE),
44b (NFC-e), 46 (XML NFe) e 47 (recibo) devem reusar os helpers públicos deste módulo
(upsert_fornecedor, upsert_periodo, localizar_item) sem reimplementá-los.

Tipos de nó manipulados:

- apolice     (Sprint 47c) -- chave: número do bilhete individual (15 dígitos)
- seguradora  (Sprint 47c) -- chave: CNPJ canônico
- fornecedor  (Sprint 42+) -- chave: CNPJ canônico (usado como "varejo" no 47c)
- periodo     (Sprint 42)  -- chave: YYYY-MM
- item        (futuro 44/44b) -- chave: <cnpj_varejo>|<data>|<descricao_norm>
- documento   (futuro 44/44b) -- chave: chave-44 ou número da nota

Tipos de aresta:

- emitida_por  (apolice -> seguradora)
- vendida_em   (apolice -> fornecedor/varejo)
- ocorre_em    (apolice|documento -> periodo)
- assegura     (apolice -> item)   -- opcional; só se o item já estiver no grafo
- fornecido_por (documento -> fornecedor)  -- futuro
- contem_item   (documento -> item)         -- futuro
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from src.graph.db import GrafoDB
from src.utils.logger import configurar_logger

logger = configurar_logger("graph.ingestor_documento")


JANELA_MATCH_ITEM_DIAS: int = 1
THRESHOLD_DESCRICAO: int = 82
MARGEM_DESEMPATE: int = 5


# ============================================================================
# Upserts de nós de apoio
# ============================================================================


def upsert_fornecedor(
    db: GrafoDB,
    cnpj: str,
    razao_social: str | None = None,
    metadata_extra: dict[str, Any] | None = None,
) -> int:
    """Upsert de fornecedor/varejo por CNPJ canônico.

    `razao_social` entra como alias (busca textual) e como metadata.
    """
    meta: dict[str, Any] = {"cnpj": cnpj}
    if razao_social:
        meta["razao_social"] = razao_social
    if metadata_extra:
        meta.update(metadata_extra)
    aliases = [razao_social] if razao_social else []
    return db.upsert_node("fornecedor", cnpj, metadata=meta, aliases=aliases)


def upsert_seguradora(
    db: GrafoDB,
    cnpj: str,
    razao_social: str,
    codigo_susep: str | None = None,
    aliases: list[str] | None = None,
    metadata_extra: dict[str, Any] | None = None,
) -> int:
    """Upsert de seguradora por CNPJ canônico.

    Código SUSEP é metadado auxiliar -- nunca chave, pois o glyph às vezes
    troca `0` por `D` (Armadilha A47c-3 da Sprint 47c).
    """
    meta: dict[str, Any] = {"cnpj": cnpj, "razao_social": razao_social}
    if codigo_susep:
        meta["codigo_susep"] = codigo_susep
    if metadata_extra:
        meta.update(metadata_extra)
    aliases_unicos = sorted({razao_social, *(aliases or [])})
    return db.upsert_node("seguradora", cnpj, metadata=meta, aliases=aliases_unicos)


def upsert_periodo(db: GrafoDB, mes_yyyy_mm: str) -> int:
    """Upsert do nó 'periodo' no formato YYYY-MM."""
    return db.upsert_node("periodo", mes_yyyy_mm, metadata={"mes": mes_yyyy_mm})


# ============================================================================
# Ingestão de apólice (Sprint 47c)
# ============================================================================


CAMPOS_OBRIGATORIOS_APOLICE: tuple[str, ...] = (
    "numero_bilhete",
    "seguradora_cnpj",
    "varejo_cnpj",
)


def ingerir_apolice(
    db: GrafoDB,
    bilhete: dict[str, Any],
    caminho_arquivo: Path | None = None,
) -> int:
    """Insere uma apólice de seguro (bilhete de garantia estendida) e suas arestas.

    Campos esperados em `bilhete` (os 3 primeiros são obrigatórios):

        numero_bilhete:          15 dígitos, chave canônica do nó apolice
        seguradora_cnpj:         CNPJ canônico XX.XXX.XXX/XXXX-XX
        varejo_cnpj:             CNPJ canônico do estabelecimento varejista
        processo_susep:          XXXXX.XXXXXX/XXXX-XX
        cpf_segurado:            CPF canônico XXX.XXX.XXX-XX
        bem_segurado:            descrição textual do item coberto
        valor_bem:               R$ (limite máximo de indenização)
        premio_liquido:          R$
        iof:                     R$
        premio_total:            R$ (soma de premio_liquido + iof)
        forma_pagamento:         string crua (ex.: "PARCELA ÚNICA: 53,98")
        vigencia_inicio:         YYYY-MM-DD
        vigencia_fim:            YYYY-MM-DD
        cobertura_inicio:        YYYY-MM-DD
        cobertura_fim:           YYYY-MM-DD
        seguradora_razao_social: string
        seguradora_codigo_susep: string de 5 dígitos
        varejo_razao_social:     string
        varejo_endereco:         string
        data_emissao:            YYYY-MM-DD

    Campos não listados acima são preservados em `metadata` desde que não
    comecem com `_` (prefixo reservado para dados internos do extrator).

    Arestas criadas:
        apolice -> seguradora (emitida_por)
        apolice -> varejo     (vendida_em)
        apolice -> periodo    (ocorre_em)
        apolice -> item       (assegura) -- só se houver match por
                                             descrição + varejo + janela temporal

    Idempotente: rodar duas vezes com o mesmo bilhete NÃO duplica arestas
    (graças ao UNIQUE(src,dst,tipo) do schema.sql).

    Devolve o id do nó apolice.
    """
    for campo in CAMPOS_OBRIGATORIOS_APOLICE:
        if not bilhete.get(campo):
            raise ValueError(
                f"bilhete sem '{campo}' -- ingestão abortada "
                "(nó apolice ou aresta ficaria órfã)"
            )

    metadata = {
        chave: valor
        for chave, valor in bilhete.items()
        if valor is not None and not chave.startswith("_")
    }
    metadata["tipo_documento"] = "cupom_garantia_estendida"
    if caminho_arquivo is not None:
        metadata["arquivo_origem"] = str(caminho_arquivo)

    apolice_id = db.upsert_node("apolice", bilhete["numero_bilhete"], metadata=metadata)

    seguradora_id = upsert_seguradora(
        db,
        bilhete["seguradora_cnpj"],
        bilhete.get("seguradora_razao_social", ""),
        codigo_susep=bilhete.get("seguradora_codigo_susep"),
    )
    varejo_meta = (
        {"endereco": bilhete["varejo_endereco"]} if bilhete.get("varejo_endereco") else None
    )
    varejo_id = upsert_fornecedor(
        db,
        bilhete["varejo_cnpj"],
        razao_social=bilhete.get("varejo_razao_social"),
        metadata_extra=varejo_meta,
    )

    db.adicionar_edge(apolice_id, seguradora_id, "emitida_por")
    db.adicionar_edge(apolice_id, varejo_id, "vendida_em")

    data_referencia = bilhete.get("data_emissao") or bilhete.get("vigencia_inicio")
    mes_ref = _extrair_mes_ref(data_referencia)
    if mes_ref:
        periodo_id = upsert_periodo(db, mes_ref)
        db.adicionar_edge(apolice_id, periodo_id, "ocorre_em")

    item_id = localizar_item(
        db,
        descricao=bilhete.get("bem_segurado", ""),
        cnpj_varejo=bilhete["varejo_cnpj"],
        data_iso=data_referencia,
    )
    if item_id is not None:
        db.adicionar_edge(
            apolice_id,
            item_id,
            "assegura",
            evidencia={"match": "descricao+cnpj_varejo+janela_data"},
        )
        logger.info(
            "apolice %s linkada a item %s via 'assegura'", apolice_id, item_id
        )
    else:
        logger.debug(
            "apolice %s sem item pareado (Sprint 44/44b pode não ter processado NFC-e ainda)",
            apolice_id,
        )

    return apolice_id


# ============================================================================
# Matching heurístico apólice <-> item
# ============================================================================


def localizar_item(
    db: GrafoDB,
    descricao: str,
    cnpj_varejo: str,
    data_iso: str | None,
) -> int | None:
    """Tenta casar a apólice a um `item` já existente no grafo.

    Critérios conjugados:
      1. `metadata.cnpj_varejo` == `cnpj_varejo` (exato)
      2. `metadata.data_compra` dentro de ±JANELA_MATCH_ITEM_DIAS da `data_iso`
      3. `rapidfuzz.token_set_ratio(descricao)` >= THRESHOLD_DESCRICAO

    Ambiguidade (mais de um candidato com score similar) devolve None -- a
    aresta `assegura` é opcional e NUNCA deve chutar. Sprint 48 (linking global)
    pode revisitar com mais contexto.
    """
    if not descricao or not data_iso:
        return None

    candidatos = _candidatos_item(db, cnpj_varejo, data_iso)
    if not candidatos:
        return None

    descricao_norm = descricao.upper().strip()
    rankings: list[tuple[int, float]] = []
    for node_id, descricao_item in candidatos:
        score = fuzz.token_set_ratio(descricao_norm, descricao_item.upper())
        if score >= THRESHOLD_DESCRICAO:
            rankings.append((node_id, score))

    if not rankings:
        return None

    rankings.sort(key=lambda par: par[1], reverse=True)
    if len(rankings) >= 2 and (rankings[0][1] - rankings[1][1]) < MARGEM_DESEMPATE:
        logger.warning(
            "match ambíguo para '%s' (varejo %s): %d candidatos com score similar",
            descricao,
            cnpj_varejo,
            len(rankings),
        )
        return None
    return rankings[0][0]


def _candidatos_item(
    db: GrafoDB,
    cnpj_varejo: str,
    data_iso: str,
) -> list[tuple[int, str]]:
    """Varre nós `item` e filtra por cnpj_varejo + janela temporal."""
    try:
        data_ref = date.fromisoformat(data_iso[:10])
    except (ValueError, TypeError):
        return []

    janela_inicio = data_ref - timedelta(days=JANELA_MATCH_ITEM_DIAS)
    janela_fim = data_ref + timedelta(days=JANELA_MATCH_ITEM_DIAS)

    resultados: list[tuple[int, str]] = []
    for node in db.listar_nodes("item"):
        meta = node.metadata
        if meta.get("cnpj_varejo") != cnpj_varejo:
            continue
        data_compra = meta.get("data_compra")
        if not isinstance(data_compra, str):
            continue
        try:
            dc = date.fromisoformat(data_compra[:10])
        except ValueError:
            continue
        if not (janela_inicio <= dc <= janela_fim):
            continue
        descricao_item = meta.get("descricao") or node.nome_canonico
        if node.id is not None:
            resultados.append((node.id, descricao_item))
    return resultados


# ============================================================================
# Helpers internos
# ============================================================================


def _extrair_mes_ref(data_iso: str | None) -> str | None:
    """Extrai YYYY-MM de uma data ISO. Devolve None se ilegível."""
    if not isinstance(data_iso, str) or len(data_iso) < 7:
        return None
    prefixo = data_iso[:7]
    if len(prefixo) == 7 and prefixo[4] == "-":
        return prefixo
    return None


# "Cada documento é um nó; cada nó é uma memória." -- princípio de arquivista
