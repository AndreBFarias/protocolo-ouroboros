"""Sprint INFRA-LINKING-NFE-TRANSACAO -- matcher em massa transação<->NF/cupom.  # noqa: accent

Wrapper de massa em torno de `src.graph.linking.candidatas_para_documento`
que cria edges `documento_de` entre nodes `transacao` e nodes `documento`  # noqa: accent
(NFCe / cupom_fiscal / cupom_termico / fatura_cartao / recibo_* /
comprovante_pix / nfce / danfe / xml_nfe).

Diferenças em relação ao motor existente
(`src.graph.linking.linkar_documentos_a_transacoes`):

  - Motor existente gera proposta Markdown em
    `docs/propostas/linking/<doc>.md` quando há ambiguidade
    (top-1/top-2 dentro de `margem_empate`) ou baixa confiança.
  - Esta sprint pede comportamento diferente para o caso ambíguo:
    cria edge mesmo assim com `peso=0.5` e flag `revisar_humano=true`
    na evidência -- útil para drill-down do dashboard (cupom aparece
    sob a transação com badge "revisar").
  - Quando houver candidato único acima do `confidence_minimo`, cria
    edge com `peso=top_score` (idêntico ao motor existente).
  - Quando não há candidato, nada é feito (não inventa vínculo).
  - Vínculos manuais (com `aprovador` na evidência) são preservados.

Tipos suportados (filtro padrão -- ajustável via --tipos):
  - nfce_modelo_65, nfce, nfce_consumidor_eletronica
  - danfe, danfe_nfe55, xml_nfe
  - cupom_fiscal, cupom_fiscal_foto, cupom_termico, cupom_termico_foto,
    cupom_nao_fiscal
  - recibo, recibo_nao_fiscal
  - comprovante_pix
  - fatura_cartao

Uso:

    python scripts/linking_nfe_transacao_massa.py --dry-run
    python scripts/linking_nfe_transacao_massa.py
    python scripts/linking_nfe_transacao_massa.py --tipos cupom_fiscal nfce

Idempotência: aresta `documento_de` tem UNIQUE(src,dst,tipo); rerodar
não duplica. Reaproveita `_ja_linkado_humano` do motor para preservar
decisões com `aprovador` na evidência.

Acentuação: identificadores técnicos N-para-N com o grafo (`transacao`,  # noqa: accent
`documento_de`, chaves de dict) seguem sem acento por consistência com
`src/graph/linking.py`. Texto humano em docstrings e logs com acentuação
completa.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Garante que o pacote `src` resolve quando o script roda solto.
RAIZ_REPO = Path(__file__).resolve().parents[1]
if str(RAIZ_REPO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPO))

from src.graph.db import GrafoDB, caminho_padrao  # noqa: E402
from src.graph.linking import (  # noqa: E402
    EDGE_TIPO_DOCUMENTO_DE,
    _ja_linkado_humano,  # noqa: PLC2701  -- helper interno reusado de propósito
    candidatas_para_documento,
    carregar_config,
)

logger = logging.getLogger(__name__)


# Tipos NF-like que esta sprint quer linkar em massa. Lista vem da spec
# (`docs/sprints/backlog/sprint_INFRA_linking_nfe_transacao.md`).
TIPOS_NF_LIKE_PADRAO: tuple[str, ...] = (
    "nfce_modelo_65",
    "nfce",
    "nfce_consumidor_eletronica",
    "danfe",
    "danfe_nfe55",
    "xml_nfe",
    "cupom_fiscal",
    "cupom_fiscal_foto",
    "cupom_termico",
    "cupom_termico_foto",
    "cupom_nao_fiscal",
    "recibo",
    "recibo_nao_fiscal",
    "comprovante_pix",
    "fatura_cartao",
)

PESO_AMBIGUO: float = 0.5


def _argv_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Matcher em massa transação<->NF/cupom. Cria edges `documento_de` "
            "no grafo SQLite a partir das heurísticas de "
            "`src/graph/linking.py`."
        )
    )
    parser.add_argument(
        "--grafo",
        type=Path,
        default=None,
        help="Caminho do grafo SQLite (default: data/output/grafo.sqlite).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Avalia candidatas e imprime totais sem gravar edges.",
    )
    parser.add_argument(
        "--tipos",
        nargs="+",
        default=None,
        metavar="TIPO",
        help=(
            "Sobrescreve a lista de tipos de documento processados "
            "(default: cupom/NF/recibo/fatura/comprovante_pix). "
            "Use --tipos all para processar todos os tipos do grafo."
        ),
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Loga cada documento processado (DEBUG).",
    )
    return parser


def _resolver_tipos(arg_tipos: list[str] | None) -> tuple[str, ...] | None:
    if arg_tipos is None:
        return TIPOS_NF_LIKE_PADRAO
    if len(arg_tipos) == 1 and arg_tipos[0].lower() == "all":
        return None  # None -> motor lê todos
    return tuple(arg_tipos)


def contar_edges_documento_de(db: GrafoDB) -> int:
    """Conta arestas `documento_de` existentes no grafo. Usa SQL direto
    em vez de iterar `listar_edges` para evitar custo O(N) sobre 6k+ tx."""
    cursor = db._conn.execute(  # noqa: SLF001  -- inspeção pontual
        "SELECT COUNT(*) FROM edge WHERE tipo = ?",
        (EDGE_TIPO_DOCUMENTO_DE,),
    )
    row = cursor.fetchone()
    return int(row[0]) if row else 0


def processar(
    db: GrafoDB,
    *,
    tipos_documento: tuple[str, ...] | None,
    dry_run: bool,
) -> dict[str, int]:
    """Roda matcher em massa. Devolve dict de contadores.

    Contadores:
      - linkados_unico: edge criada com peso = top_score (top-1 acima do
        `confidence_minimo` e sem empate com top-2).
      - linkados_ambiguo: edge criada com peso=0.5 e
        `revisar_humano=true` na evidência (top-1 e top-2 dentro de
        `margem_empate`).
      - baixa_confianca: top-1 abaixo do `confidence_minimo` -- nenhuma
        edge criada (não inventa vínculo).
      - sem_candidato: documento sem nenhuma transação candidata.
      - ja_linkado_humano: documento já tem aresta com `aprovador` na
        evidência (preservado).
      - ja_linkado_motor: documento já tem aresta `documento_de` (sem
        `aprovador`) -- pulado para idempotência prática (mesmo o
        UNIQUE da DB segura, evitamos a chamada).
      - ignorado_tipo: documento cujo `tipo_documento` não está na lista
        filtrada.
      - total_documentos: documentos varridos.
    """
    config = carregar_config()
    margem_empate = float(config.get("margem_empate", 0.05))

    stats: dict[str, int] = {
        "total_documentos": 0,
        "linkados_unico": 0,
        "linkados_ambiguo": 0,
        "baixa_confianca": 0,
        "sem_candidato": 0,
        "ja_linkado_humano": 0,
        "ja_linkado_motor": 0,
        "ignorado_tipo": 0,
    }

    documentos = db.listar_nodes(tipo="documento")
    stats["total_documentos"] = len(documentos)

    for doc in documentos:
        if doc.id is None:
            continue
        tipo_doc = doc.metadata.get("tipo_documento")

        if tipos_documento is not None and tipo_doc not in tipos_documento:
            stats["ignorado_tipo"] += 1
            continue

        if _ja_linkado_humano(db, doc.id):
            stats["ja_linkado_humano"] += 1
            continue

        # Idempotência prática: já existe edge `documento_de` saindo
        # deste doc? Pular para não recalcular score nem regravar
        # evidência (edge UNIQUE no schema também segura, mas evitamos
        # I/O desnecessário em runs subsequentes da massa).
        if db.listar_edges(src_id=doc.id, tipo=EDGE_TIPO_DOCUMENTO_DE):
            stats["ja_linkado_motor"] += 1
            continue

        candidatas = candidatas_para_documento(db, doc, config=config)
        if not candidatas:
            stats["sem_candidato"] += 1
            logger.debug(
                "documento %s (%s) sem candidata",
                doc.nome_canonico,
                tipo_doc,
            )
            continue

        top_id, top_evidencia = candidatas[0]
        # `_parametros_para_tipo` é interno; replicamos a lógica via config
        # leniente para evitar acoplar ao símbolo privado do motor.
        parametros_tipo = (config.get("tipos") or {}).get(tipo_doc) or {}
        confidence_minimo = float(
            parametros_tipo.get(
                "confidence_minimo",
                config.get("default", {}).get("confidence_minimo", 0.75),
            )
        )
        top_score = float(top_evidencia["confidence"])

        # Empate top-1 / top-2 -> edge ambígua com peso=0.5 e flag.
        if len(candidatas) >= 2:
            segundo_id, segundo_evid = candidatas[1]
            segundo_score = float(segundo_evid["confidence"])
            if (top_score - segundo_score) < margem_empate:
                evidencia = dict(top_evidencia)
                evidencia["revisar_humano"] = True
                evidencia["motivo_revisao"] = "empate_top1_top2"
                evidencia["top1_score"] = top_score
                evidencia["top2_score"] = segundo_score
                evidencia["top2_transacao_id"] = segundo_id
                if not dry_run:
                    db.adicionar_edge(
                        src_id=doc.id,
                        dst_id=top_id,
                        tipo=EDGE_TIPO_DOCUMENTO_DE,
                        peso=PESO_AMBIGUO,
                        evidencia=evidencia,
                    )
                stats["linkados_ambiguo"] += 1
                logger.info(
                    "documento %s -> tx %s (AMBÍGUO, score=%.3f vs %.3f)",
                    doc.nome_canonico,
                    top_id,
                    top_score,
                    segundo_score,
                )
                continue

        # Top-1 abaixo do mínimo -> não linka. Não geramos proposta MD
        # aqui (motor existente já cobre). Apenas contabiliza.
        if top_score < confidence_minimo:
            stats["baixa_confianca"] += 1
            logger.debug(
                "documento %s baixa confiança (score=%.3f < %.3f)",
                doc.nome_canonico,
                top_score,
                confidence_minimo,
            )
            continue

        # Caso ouro: top-1 sozinho acima do mínimo.
        if not dry_run:
            db.adicionar_edge(
                src_id=doc.id,
                dst_id=top_id,
                tipo=EDGE_TIPO_DOCUMENTO_DE,
                peso=top_score,
                evidencia=top_evidencia,
            )
        stats["linkados_unico"] += 1
        logger.info(
            "documento %s -> tx %s (score=%.3f, heurística=%s)",
            doc.nome_canonico,
            top_id,
            top_score,
            top_evidencia["heuristica"],
        )

    return stats


def _formatar_relatorio(
    stats: dict[str, int],
    edges_antes: int,
    edges_depois: int,
    *,
    dry_run: bool,
) -> str:
    linhas: list[str] = []
    titulo = "DRY-RUN" if dry_run else "EXECUTADO"
    linhas.append(f"=== Linking massa transação<->NF/cupom -- {titulo} ===")
    linhas.append(f"  documentos varridos       : {stats['total_documentos']}")
    linhas.append(f"  ignorados por tipo        : {stats['ignorado_tipo']}")
    linhas.append(f"  já linkados (humano)      : {stats['ja_linkado_humano']}")
    linhas.append(f"  já linkados (motor)       : {stats['ja_linkado_motor']}")
    linhas.append(f"  sem candidato             : {stats['sem_candidato']}")
    linhas.append(f"  baixa confiança           : {stats['baixa_confianca']}")
    linhas.append(f"  novos vínculos únicos     : {stats['linkados_unico']}")
    linhas.append(f"  novos vínculos ambíguos   : {stats['linkados_ambiguo']}")
    linhas.append("")
    linhas.append(f"  edges `documento_de` antes: {edges_antes}")
    linhas.append(f"  edges `documento_de` agora: {edges_depois}")
    linhas.append(f"  delta                     : {edges_depois - edges_antes}")
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    args = _argv_parser().parse_args(argv)
    nivel = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=nivel,
        format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
    )

    grafo_path = args.grafo or caminho_padrao()
    if not grafo_path.exists():
        logger.error("grafo não encontrado em %s", grafo_path)
        return 2

    tipos = _resolver_tipos(args.tipos)
    if tipos is None:
        logger.info("processando TODOS os tipos de documento (--tipos all)")
    else:
        logger.info("processando tipos NF-like: %s", ", ".join(tipos))

    with GrafoDB(grafo_path) as db:
        edges_antes = contar_edges_documento_de(db)
        stats = processar(db, tipos_documento=tipos, dry_run=args.dry_run)
        edges_depois = contar_edges_documento_de(db)

    relatorio = _formatar_relatorio(stats, edges_antes, edges_depois, dry_run=args.dry_run)
    sys.stdout.write(relatorio + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# "Match sem dado é heurística; match com dado é ouro."
# -- princípio INFRA-LINKING-NFE-TRANSACAO  # noqa: accent
