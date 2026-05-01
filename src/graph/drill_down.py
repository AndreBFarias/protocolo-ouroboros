"""Walks de drill-down sobre o grafo SQLite.

Sprint MICRO-01a (escopo refinado por padrão (k) do BRIEF -- hipótese
empírica refutou parte da spec original).

Resolve walks de leitura para o dashboard e auditoria:

  - ``obter_documentos_da_transacao(db, transacao_id) -> list[Node]``
    Walk de 1 salto: transação --documento_de--> documento.

  - ``obter_items_da_transacao(db, transacao_id) -> list[Node]``
    Walk de 2 saltos: transação --documento_de--> documento
    --contem_item--> item.

Sem efeitos colaterais (read-only). Não cria arestas. Linking de
documentos a transações é responsabilidade de ``src/graph/linking.py``
(motor heurístico Sprint 48 + 95) -- esse módulo apenas consome o
resultado.

Por que existe (escopo refinado da spec MICRO-01a):

A spec original assumia "0 arestas documento_de para nfce_modelo_65" e
propunha criar ``linking_micro.py`` paralelo. Investigação empírica em
2026-04-30 mostrou que:

  - ``linking.py`` JÁ cobre nfce_modelo_65 em
    ``mappings/linking_config.yaml`` desde Sprint 48.
  - Os 2 NFCe atuais no grafo são arquivos PoC sem transação real
    correspondente -- por isso ``linkar_documentos_a_transacoes(db)`` no
    pipeline produziu 0 arestas para eles.
  - O gap real é o resolver de drill-down (walk transação → items)
    que ainda não existia.

Logo, esta sprint entrega o resolver de drill-down. Criação de novas
arestas para NFCe reais fica a cargo de ``linking.py`` quando NFCe
reais aparecerem no inbox (sprint follow-up
``MICRO-01a-FOLLOWUP-NFCE-REAIS``).
"""

from __future__ import annotations

from src.graph.db import GrafoDB
from src.graph.models import Node

EDGE_DOCUMENTO_DE: str = "documento_de"
EDGE_CONTEM_ITEM: str = "contem_item"


def obter_documentos_da_transacao(
    db: GrafoDB, transacao_id: int
) -> list[Node]:
    """Lista os documentos vinculados à transação via aresta ``documento_de``.

    Walk de 1 salto da transação ao documento via aresta ``documento_de``.

    Retorna lista (potencialmente vazia) de nodes ``documento``. Ordem é a
    de criação das arestas (não há ranking semântico aqui -- ranking é
    feito pelo ``linking.py``).
    """
    arestas = db.listar_edges(src_id=transacao_id, tipo=EDGE_DOCUMENTO_DE)
    documentos: list[Node] = []
    for aresta in arestas:
        node = db.buscar_node_por_id(aresta.dst_id)
        if node is not None and node.tipo == "documento":
            documentos.append(node)
    return documentos


def obter_items_da_transacao(db: GrafoDB, transacao_id: int) -> list[Node]:
    """Lista items granulares acessíveis a partir da transação.

    Walk de 2 saltos pela transação: aresta ``documento_de`` chega ao
    documento, aresta ``contem_item`` chega ao item. Retorna apenas
    nodes do tipo ``item``.

    Útil para drill-down "paguei R$ X num NFCe -- mostrar os Y items
    granulares". Quando a transação não tem documento vinculado, ou os
    documentos vinculados não têm items (ex: holerite, DAS), retorna
    lista vazia.

    Deduplicação: se 2 documentos diferentes apontam para o mesmo item
    (raro -- aconteceria se o mesmo item aparece em 2 NFCe da mesma
    transação), a lista contém o item uma única vez (preservando ordem
    de primeira aparição).
    """
    documentos = obter_documentos_da_transacao(db, transacao_id)
    items: list[Node] = []
    ids_vistos: set[int] = set()
    for doc in documentos:
        if doc.id is None:
            continue
        arestas_item = db.listar_edges(src_id=doc.id, tipo=EDGE_CONTEM_ITEM)
        for aresta in arestas_item:
            if aresta.dst_id in ids_vistos:
                continue
            node = db.buscar_node_por_id(aresta.dst_id)
            if node is None or node.tipo != "item":
                continue
            ids_vistos.add(aresta.dst_id)
            items.append(node)
    return items


def contar_drill_down(db: GrafoDB) -> dict[str, int]:
    """Estatística agregada -- útil para auditoria/observabilidade.

    Retorna dict com chaves:

      - ``transacoes_com_documento``: # de transações com >=1 documento_de.
      - ``transacoes_com_items``: # de transações com >=1 item alcançável
        via walk de 2 saltos.
      - ``nfce_no_grafo``: # total de nodes documento tipo nfce_modelo_65.
      - ``nfce_com_documento_de``: # de nfce_modelo_65 com aresta
        ``documento_de`` apontando para alguma transação. Quando este
        número é menor que ``nfce_no_grafo``, há NFCe orfãos (sem
        linking) -- candidatos a investigação manual.
    """
    transacoes_com_documento_set: set[int] = set()
    transacoes_com_items_set: set[int] = set()

    for aresta in db.listar_edges(tipo=EDGE_DOCUMENTO_DE):
        transacoes_com_documento_set.add(aresta.src_id)

    for transacao_id in transacoes_com_documento_set:
        if obter_items_da_transacao(db, transacao_id):
            transacoes_com_items_set.add(transacao_id)

    nfce_total = 0
    nfce_com_doc_de = 0
    for node in db.listar_nodes(tipo="documento"):
        if node.metadata.get("tipo_documento") != "nfce_modelo_65":
            continue
        nfce_total += 1
        if node.id is not None:
            arestas = db.listar_edges(dst_id=node.id, tipo=EDGE_DOCUMENTO_DE)
            if arestas:
                nfce_com_doc_de += 1

    return {
        "transacoes_com_documento": len(transacoes_com_documento_set),
        "transacoes_com_items": len(transacoes_com_items_set),
        "nfce_no_grafo": nfce_total,
        "nfce_com_documento_de": nfce_com_doc_de,
    }


# "O caminho do todo passa pelas partes -- e o caminho das partes pelo todo."
#  -- princípio operacional do drill-down no Protocolo Ouroboros
