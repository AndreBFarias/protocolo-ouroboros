"""Entity resolution de produtos (itens) -- Sprint 49.

Análogo ao `entity_resolution.py` (fornecedores, Sprint 42), mas o domínio aqui
é o texto bruto da DESCRICAO dos nodes `item` do grafo. Dois itens com chave  # noqa: accent
canônica diferente (`<cnpj>|<data>|<codigo>`) podem ser o mesmo produto  # noqa: accent
conceitual vendido em compras distintas; este módulo os agrupa em um node
`produto_canonico` via clustering fuzzy + overrides manuais.

Estratégia em 3 camadas (ordem de prioridade):

  1. **Override manual** -- `mappings/produtos_canonicos.yaml` lista aliases
     validados pelo supervisor. Matching determinístico por substring normalizada.
  2. **Clustering fuzzy** -- rapidfuzz.token_set_ratio entre descrições
     normalizadas. Threshold duplo:
       - score >= THRESHOLD_MATCH (95) -> unifica direto (aresta automática)
       - THRESHOLD_PROPOSTA (80) <= score < THRESHOLD_MATCH -> proposta MD
         em `docs/propostas/er_produtos/` para humano decidir.
       - score < THRESHOLD_PROPOSTA -> não unifica (itens distintos).
  3. **Fallback** -- item sem companhia fica sem produto_canonico; continua
     existindo como node `item` individual.

Arestas criadas:
  item -> produto_canonico : `mesmo_produto_que` (peso=score/100)

Idempotência:
  - UNIQUE(src,dst,tipo) no schema garante que rodar 2x não duplica.
  - upsert_node("produto_canonico", nome) pega o mesmo id sempre.
  - Proposta MD tem nome determinístico por (slug, motivo); sobrescreve.

Tipo de node novo: `produto_canonico`. ADR-14 declara o schema extensível via
`mappings/tipos_node.yaml`; este é o primeiro uso pós-47a (prescricao).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz import fuzz

from src.graph.db import GrafoDB
from src.graph.entity_resolution import normalizar_fornecedor as _norm_basico
from src.graph.models import Node
from src.utils.logger import configurar_logger

logger = configurar_logger("graph.er_produtos")

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_PATH_OVERRIDES_PADRAO: Path = _RAIZ_REPO / "mappings" / "produtos_canonicos.yaml"
_PATH_PROPOSTAS_PADRAO: Path = _RAIZ_REPO / "docs" / "propostas" / "er_produtos"

TIPO_NODE_CANONICO: str = "produto_canonico"
EDGE_TIPO_MESMO_PRODUTO: str = "mesmo_produto_que"

THRESHOLD_MATCH: int = 95  # >= unifica automaticamente
THRESHOLD_PROPOSTA: int = 80  # [80, 95) gera proposta supervisor

# Unidades de medida que aparecem agarradas à quantidade na descrição bruta.
# São normalizadas para "UN" genérico; a informação real de quantidade vive
# em metadata.qtde/valor_total do item, não no texto.
_PADRAO_UNIDADE: re.Pattern[str] = re.compile(
    r"\b\d+([.,]\d+)?\s*(ML|L|LT|G|GR|KG|UN|PC|PCT|CX|MG|MCG)\b",
    re.IGNORECASE,
)
# Restos de unidade após remover a quantidade (ex.: "ML" solto).
_PADRAO_UNIDADE_SOLTA: re.Pattern[str] = re.compile(
    r"\b(ML|L|LT|G|GR|KG|UN|PC|PCT|CX|MG|MCG)\b",
    re.IGNORECASE,
)
# Quantidades numéricas isoladas (ex.: "DOVE 150" sem unidade).
_PADRAO_NUMERO_ISOLADO: re.Pattern[str] = re.compile(r"\b\d+([.,]\d+)?\b")

# Sinônimos/abreviações canonicalizadas antes do fuzzy.
# Regra: o primeiro termo da lista é a forma canônica; os demais são
# substituídos por ela durante a normalização. Evita que "DEO" e "DESODORANTE"
# caiam em clusters separados apenas pela variação de prefixo.
_SINONIMOS_CANONICOS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("DESODORANTE", ("DESOD", "DEODORANT", "DEO")),
    ("SABONETE", ("SABONET", "BAR SOAP", "SOAP", "SAB")),
    ("SHAMPOO", ("XAMPU", "XAMPUZINHO", "SHAMP")),
    ("CONDICIONADOR", ("COND", "CONDITIONER")),
    ("AMACIANTE", ("AMACI", "SOFTENER")),
    ("ROLLON", ("ROLL-ON", "ROL", "ROLON")),
    ("AEROSOL", ("AERO", "SPRAY")),
    ("ARROZ", ("ARROZINHO",)),
    ("FEIJAO", ("FEIJ",)),
)


# ============================================================================
# Estruturas
# ============================================================================


@dataclass(frozen=True)
class ClusterProduto:
    """Cluster de itens equivalentes produzido pelo ER."""

    canonico: str  # texto normalizado representativo
    membros: list[tuple[int, str, int]]  # (item_id, descricao_bruta, score)
    fonte: str  # "override" | "fuzzy"


# ============================================================================
# Normalização
# ============================================================================


def normalizar_descricao(descricao: str) -> str:
    """Normaliza descrição de produto para comparação fuzzy.

    Passos:
      1. Uppercase + strip.
      2. Remove acentos (NFKD -> ascii).
      3. Remove quantidade+unidade ("150ML", "1.5L", "250 G").
      4. Remove unidades soltas restantes ("ML", "KG").
      5. Remove números isolados ("150" sem unidade).
      6. Remove pontuação leve.
      7. Colapsa espaços; ordena tokens? NÃO -- rapidfuzz.token_set_ratio
         já ignora ordem e lida com tokens duplicados.

    Reuso: a primeira passada (upper+strip+pontuação) chama
    `entity_resolution.normalizar_fornecedor` para coerência N-para-N com o
    módulo irmão.
    """
    if not descricao:
        return ""
    texto = _norm_basico(descricao)  # upper, strip, sem pontuação leve
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = _PADRAO_UNIDADE.sub(" ", texto)
    texto = _PADRAO_UNIDADE_SOLTA.sub(" ", texto)
    texto = _PADRAO_NUMERO_ISOLADO.sub(" ", texto)
    texto = _aplicar_sinonimos(texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _aplicar_sinonimos(texto: str) -> str:
    """Substitui abreviações/sinônimos conhecidos pela forma canônica.

    Aplicada ANTES do colapso final de espaços para evitar que variações de
    prefixo ("DEO" vs "DESODORANTE") produzam scores fuzzy artificialmente
    baixos. O casamento é por palavra inteira (`\\b`) -- não quebra tokens
    que contenham a substring por acidente.
    """
    resultado = texto
    for canonico, variantes in _SINONIMOS_CANONICOS:
        for variante in variantes:
            padrao = rf"\b{re.escape(variante)}\b"
            resultado = re.sub(padrao, canonico, resultado)
    return resultado


# ============================================================================
# Overrides manuais (YAML)
# ============================================================================


def carregar_overrides(caminho: Path | None = None) -> dict[str, str]:
    """Lê `produtos_canonicos.yaml` e devolve dict {alias_normalizado: canonico}.

    Chave de lookup é a descrição bruta normalizada (via `normalizar_descricao`)
    para que variações de case/acento/unidade na descrição do item casem com
    o alias listado no YAML.
    """
    caminho = caminho or _PATH_OVERRIDES_PADRAO
    if not caminho.exists():
        logger.debug("overrides de produto ausentes em %s -- heurística only", caminho)
        return {}
    try:
        with caminho.open("r", encoding="utf-8") as fh:
            dados = yaml.safe_load(fh) or {}
    except yaml.YAMLError as erro:
        logger.error("erro ao ler %s: %s -- ignorando overrides", caminho, erro)
        return {}

    if not isinstance(dados, dict):
        return {}

    mapa: dict[str, str] = {}
    produtos = dados.get("produtos") or []
    if not isinstance(produtos, list):
        return {}
    for entrada in produtos:
        if not isinstance(entrada, dict):
            continue
        canonico = str(entrada.get("canonico") or "").strip()
        aliases = entrada.get("aliases") or []
        if not canonico or not isinstance(aliases, list):
            continue
        # O próprio canônico também casa como alias de si mesmo.
        chaves = [canonico, *[str(a) for a in aliases if a]]
        for chave_bruta in chaves:
            chave_norm = normalizar_descricao(chave_bruta)
            if chave_norm:
                mapa[chave_norm] = canonico
    return mapa


# ============================================================================
# Clustering
# ============================================================================


def _descricao_item(node: Node) -> str:
    """Devolve a descrição textual bruta do item (ou nome_canonico de fallback)."""
    descricao = node.metadata.get("descricao")
    if isinstance(descricao, str) and descricao.strip():
        return descricao
    return node.nome_canonico


def _agrupar_por_heuristica(
    itens: list[tuple[int, str, str]],
    overrides: dict[str, str],
    threshold_match: int = THRESHOLD_MATCH,
    threshold_proposta: int = THRESHOLD_PROPOSTA,
) -> list[ClusterProduto]:
    """Produz clusters a partir de [(item_id, descricao_bruta, descricao_norm)].

    1. Primeiro passe: resolve overrides YAML. Cada alias mapeia direto para
       o canônico. Itens que casam vão para o cluster desse canônico com
       `fonte="override"` e score=100.
    2. Segundo passe: para os não-resolvidos, aplica token_set_ratio contra o
       canônico de cada cluster existente (override+fuzzy). Score >= match
       entra no cluster. Score em [proposta, match) também entra mas marca
       o item com flag `proposta=True` para gerar MD; score < proposta cria
       cluster novo singleton (não será materializado como produto_canonico
       porque tem só 1 membro -- regra no escritor).

    Retorno: lista de ClusterProduto, cada um com pelo menos 1 membro.
    """
    clusters: list[dict[str, Any]] = []

    # Pré-popula clusters a partir dos canônicos do override (garante que
    # dois itens cobertos por override viram o mesmo cluster mesmo sem
    # vizinho direto no input).
    canonicos_override: dict[str, int] = {}
    for canonico in set(overrides.values()):
        canonico_norm = normalizar_descricao(canonico)
        if canonico_norm and canonico_norm not in canonicos_override:
            clusters.append(
                {
                    "canonico_norm": canonico_norm,
                    "canonico_bruto": canonico,
                    "membros": [],
                    "fonte": "override",
                    "propostas": [],
                }
            )
            canonicos_override[canonico_norm] = len(clusters) - 1

    # Primeiro passe: overrides
    nao_resolvidos: list[tuple[int, str, str]] = []
    for item_id, descricao_bruta, descricao_norm in itens:
        canonico = overrides.get(descricao_norm)
        if canonico:
            canonico_norm = normalizar_descricao(canonico)
            idx = canonicos_override.get(canonico_norm)
            if idx is None:
                clusters.append(
                    {
                        "canonico_norm": canonico_norm,
                        "canonico_bruto": canonico,
                        "membros": [(item_id, descricao_bruta, 100)],
                        "fonte": "override",
                        "propostas": [],
                    }
                )
                canonicos_override[canonico_norm] = len(clusters) - 1
            else:
                clusters[idx]["membros"].append((item_id, descricao_bruta, 100))
            continue
        nao_resolvidos.append((item_id, descricao_bruta, descricao_norm))

    # Segundo passe: fuzzy em ordem estável (item_id crescente).
    for item_id, descricao_bruta, descricao_norm in sorted(nao_resolvidos):
        if not descricao_norm:
            continue
        melhor_idx: int | None = None
        melhor_score: int = 0
        for idx, cluster in enumerate(clusters):
            score = int(fuzz.token_set_ratio(descricao_norm, cluster["canonico_norm"]))
            if score > melhor_score:
                melhor_score = score
                melhor_idx = idx

        if melhor_idx is not None and melhor_score >= threshold_match:
            clusters[melhor_idx]["membros"].append((item_id, descricao_bruta, melhor_score))
        elif melhor_idx is not None and melhor_score >= threshold_proposta:
            # Borderline: proposta. O item NÃO entra no cluster automaticamente;
            # só registra no slot de propostas para o escritor gerar MD.
            clusters[melhor_idx]["propostas"].append(
                (item_id, descricao_bruta, melhor_score)
            )
        else:
            clusters.append(
                {
                    "canonico_norm": descricao_norm,
                    "canonico_bruto": descricao_bruta,
                    "membros": [(item_id, descricao_bruta, 100)],
                    "fonte": "fuzzy",
                    "propostas": [],
                }
            )

    resultado: list[ClusterProduto] = []
    for cluster in clusters:
        resultado.append(
            ClusterProduto(
                canonico=cluster["canonico_bruto"],
                membros=list(cluster["membros"]),
                fonte=cluster["fonte"],
            )
        )
        # Propostas viram "clusters borderline" sem materialização: o escritor
        # recebe via tupla extra para gerar MD (ver _aplicar_clusters_no_grafo).
    # Anexa propostas como atributo paralelo (via dicionário externo).
    _anexar_propostas_como_atributo(clusters, resultado)
    return resultado


def _anexar_propostas_como_atributo(
    clusters_dict: list[dict[str, Any]],
    clusters_obj: list[ClusterProduto],
) -> None:
    """Cola `propostas` em ClusterProduto via dict externo (dataclass frozen)."""
    # Como ClusterProduto é frozen, propostas vão via mapa id->lista no caller.
    # Aqui apenas normaliza formato para o caller consumir.
    for idx, cluster_dict in enumerate(clusters_dict):
        _PROPOSTAS_POR_CLUSTER.setdefault(id(clusters_obj[idx]), [])
        _PROPOSTAS_POR_CLUSTER[id(clusters_obj[idx])].extend(cluster_dict["propostas"])


# Mapa externo (proposta por cluster) populado durante clustering; consumido
# pelo escritor. Usado como carona porque ClusterProduto é frozen.
_PROPOSTAS_POR_CLUSTER: dict[int, list[tuple[int, str, int]]] = {}


# ============================================================================
# Aplicação no grafo
# ============================================================================


def aplicar_clusters_no_grafo(
    db: GrafoDB,
    clusters: list[ClusterProduto],
    caminho_propostas: Path | None = None,
) -> dict[str, int]:
    """Cria nodes produto_canonico e arestas mesmo_produto_que para clusters.

    Regra: cluster com >= 2 membros vira node produto_canonico materializado.
    Cluster singleton (1 membro) é descartado -- item fica sem agregado.
    Propostas (borderline 80-95) geram MD em caminho_propostas.

    Devolve dict com contadores: canonicos_criados, arestas_criadas,
    propostas_abertas, singletons_ignorados.
    """
    caminho_propostas = caminho_propostas or _PATH_PROPOSTAS_PADRAO
    caminho_propostas.mkdir(parents=True, exist_ok=True)

    stats = {
        "canonicos_criados": 0,
        "arestas_criadas": 0,
        "propostas_abertas": 0,
        "singletons_ignorados": 0,
    }

    for cluster in clusters:
        if len(cluster.membros) < 2:
            stats["singletons_ignorados"] += 1
            # Mesmo sem materializar, propostas anexadas ao cluster singleton
            # continuam relevantes (ex.: override canônico sem item próprio
            # mas com borderline candidato).
            _emitir_propostas_do_cluster(cluster, caminho_propostas, stats)
            continue

        canonico_norm = normalizar_descricao(cluster.canonico) or cluster.canonico
        metadata = {
            "membros_count": len(cluster.membros),
            "fonte": cluster.fonte,
            "descricao_representativa": cluster.canonico,
        }
        aliases_unicos = sorted({descricao for _, descricao, _ in cluster.membros})
        produto_id = db.upsert_node(
            TIPO_NODE_CANONICO,
            canonico_norm,
            metadata=metadata,
            aliases=aliases_unicos,
        )
        stats["canonicos_criados"] += 1

        for item_id, _descricao_bruta, score in cluster.membros:
            db.adicionar_edge(
                src_id=item_id,
                dst_id=produto_id,
                tipo=EDGE_TIPO_MESMO_PRODUTO,
                peso=round(score / 100.0, 4),
                evidencia={
                    "fuzzy_score": score,
                    "fonte": cluster.fonte,
                },
            )
            stats["arestas_criadas"] += 1

        _emitir_propostas_do_cluster(cluster, caminho_propostas, stats)

    return stats


def _emitir_propostas_do_cluster(
    cluster: ClusterProduto,
    caminho_propostas: Path,
    stats: dict[str, int],
) -> None:
    """Gera MD de proposta para itens borderline (80 <= score < 95)."""
    propostas = _PROPOSTAS_POR_CLUSTER.get(id(cluster), [])
    for item_id, descricao_bruta, score in propostas:
        _escrever_proposta_er(
            canonico=cluster.canonico,
            item_id=item_id,
            descricao_bruta=descricao_bruta,
            score=score,
            caminho_propostas=caminho_propostas,
        )
        stats["propostas_abertas"] += 1


def _escrever_proposta_er(
    canonico: str,
    item_id: int,
    descricao_bruta: str,
    score: int,
    caminho_propostas: Path,
) -> Path:
    """Escreve proposta Markdown idempotente para par (item_id, canonico)."""
    caminho_propostas.mkdir(parents=True, exist_ok=True)
    slug_canonico = _slug(canonico)
    nome_arquivo = f"item{item_id:06d}_{slug_canonico}.md"
    destino = caminho_propostas / nome_arquivo

    linhas: list[str] = []
    linhas.append("---")
    linhas.append(f"id: er_produto_item{item_id}_{slug_canonico}")
    linhas.append("tipo: er_produtos")
    linhas.append("motivo: similaridade_borderline")
    linhas.append("status: aberta")
    linhas.append("autor_proposta: er-produtos-sprint49")
    linhas.append("sprint_contexto: 49")
    linhas.append("---")
    linhas.append("")
    linhas.append("# Revisão de equivalência de produto")
    linhas.append("")
    linhas.append("## Candidato")
    linhas.append("")
    linhas.append(f"- item_id: `{item_id}`")
    linhas.append(f"- descrição bruta: `{descricao_bruta}`")
    linhas.append("")
    linhas.append("## Canônico proposto")
    linhas.append("")
    linhas.append(f"- `{canonico}`")
    linhas.append(f"- similaridade: `{score}` (faixa proposta: 80-94)")
    linhas.append("")
    linhas.append("## Decisão humana")
    linhas.append("")
    linhas.append("- **Aprovar equivalência:** (S/N)")
    linhas.append("- **Adicionar alias em `mappings/produtos_canonicos.yaml`:** (S/N)")
    linhas.append("- **Motivo:** (preencher)")
    linhas.append("")
    linhas.append("---")
    linhas.append("")
    linhas.append(
        '*"Nomear com precisão é o começo da sabedoria." -- Confúcio (parafraseado)*'
    )
    linhas.append("")

    destino.write_text("\n".join(linhas), encoding="utf-8")
    return destino


def _slug(texto: str) -> str:
    """Slug mínimo alfanumérico. Replica o estilo de `linking._slug`."""
    out: list[str] = []
    for ch in texto.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in {"-", "_"}:
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    slug = "".join(out).strip("-")
    return slug[:60] or "produto"


# ============================================================================
# API pública de alto nível
# ============================================================================


def executar_er_produtos(
    db: GrafoDB,
    caminho_overrides: Path | None = None,
    caminho_propostas: Path | None = None,
    threshold_match: int = THRESHOLD_MATCH,
    threshold_proposta: int = THRESHOLD_PROPOSTA,
) -> dict[str, int]:
    """Percorre todos os itens do grafo, clusteriza e materializa canônicos.

    Devolve dict com contadores agregados (canonicos_criados, arestas_criadas,
    propostas_abertas, singletons_ignorados, itens_analisados).
    """
    overrides = carregar_overrides(caminho_overrides)

    nodes_item = db.listar_nodes(tipo="item")
    itens_preparados: list[tuple[int, str, str]] = []
    for node in nodes_item:
        if node.id is None:
            continue
        descricao_bruta = _descricao_item(node)
        descricao_norm = normalizar_descricao(descricao_bruta)
        if not descricao_norm:
            continue
        itens_preparados.append((node.id, descricao_bruta, descricao_norm))

    # Limpa mapa de propostas entre execuções (evita vazamento de teste).
    _PROPOSTAS_POR_CLUSTER.clear()

    clusters = _agrupar_por_heuristica(
        itens_preparados,
        overrides,
        threshold_match=threshold_match,
        threshold_proposta=threshold_proposta,
    )

    stats = aplicar_clusters_no_grafo(db, clusters, caminho_propostas=caminho_propostas)
    stats["itens_analisados"] = len(itens_preparados)
    logger.info("ER de produtos concluído: %s", stats)
    return stats


# ============================================================================
# CLI auxiliar
# ============================================================================


def main() -> None:
    """Entrypoint CLI: `python -m src.graph.er_produtos`."""
    from src.graph.db import caminho_padrao

    logger.info("ER de produtos CLI -- abrindo grafo em %s", caminho_padrao())
    with GrafoDB(caminho_padrao()) as db:
        stats = executar_er_produtos(db)
    logger.info("estatísticas finais: %s", stats)


if __name__ == "__main__":
    main()


# "Nomear com precisão é o começo da sabedoria." -- Confúcio (parafraseado)
