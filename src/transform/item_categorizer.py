"""Categorização automática de itens de NF via regras regex e overrides.

Espelha `src/transform/categorizer.py` (transações) mas opera sobre itens
extraídos de documentos fiscais (NFC-e, DANFE, cupom térmico, XML NFe).

Prioridade: overrides manuais > regras regex > fallback "Outros" + "Questionável".

Integração com o grafo (Sprint 50):
- cada `item_canonico` (nó `tipo=item` no grafo) recebe uma aresta `categoria_de`
  apontando para um nó `tipo=categoria` com `metadata.tipo_categoria="item"`.
  Esta decisão (usar `categoria` em vez de criar `categoria_item`) segue o
  padrão documentado no ADR-14 (tabela `categoria.metadata.tipo_categoria` com
  valores `despesa/receita/item`) e o padrão "Extensão de schema" registrado
  no VALIDATOR_BRIEF.md (usar tipo canônico existente antes de propor tipo
  novo, pattern confirmado na Sprint 47a).
- cada item tem exatamente UMA categoria (a primeira que casar); overrides
  vencem regras, regras vencem fallback.

Detecção de padrões novos: itens em "Outros" com frequência >= 3 geram
proposta em `docs/propostas/categoria_item/<slug>.md` para revisão manual.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any, Optional

import yaml

from src.utils.logger import configurar_logger

logger = configurar_logger("item_categorizer")

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_PATH_REGRAS_PADRAO: Path = _RAIZ_REPO / "mappings" / "categorias_item.yaml"
_PATH_OVERRIDES_PADRAO: Path = _RAIZ_REPO / "mappings" / "overrides_item.yaml"
_PATH_PROPOSTAS_PADRAO: Path = _RAIZ_REPO / "docs" / "propostas" / "categoria_item"

TIPO_NODE_CATEGORIA: str = "categoria"
EDGE_TIPO_CATEGORIA_DE: str = "categoria_de"

FALLBACK_CATEGORIA: str = "Outros"
FALLBACK_CLASSIFICACAO: str = "Questionável"
FREQUENCIA_MIN_PROPOSTA: int = 3


# ============================================================================
# ItemCategorizer
# ============================================================================


class ItemCategorizer:
    """Aplica categoria e classificação a itens de documento fiscal.

    Uso típico:

        cat = ItemCategorizer()
        cat.categorizar_lote(lista_de_itens)
        # cada dict agora tem 'categoria_item' e 'classificacao_item'
    """

    def __init__(
        self,
        caminho_regras: Optional[Path] = None,
        caminho_overrides: Optional[Path] = None,
    ) -> None:
        self.caminho_regras = caminho_regras or _PATH_REGRAS_PADRAO
        self.caminho_overrides = caminho_overrides or _PATH_OVERRIDES_PADRAO

        self.overrides: list[dict[str, Any]] = []
        self.regras: list[dict[str, Any]] = []

        self._carregar_overrides(self.caminho_overrides)
        self._carregar_regras(self.caminho_regras)

    # ------------------------------------------------------------------------
    # Carga de configuração
    # ------------------------------------------------------------------------

    def _carregar_overrides(self, caminho: Path) -> None:
        """Carrega overrides manuais. Arquivo é opcional (criar sob demanda)."""
        if not caminho.exists():
            logger.debug("overrides de item ausentes em %s -- só regex", caminho)
            return

        with caminho.open("r", encoding="utf-8") as f:
            dados = yaml.safe_load(f)

        if not dados or "overrides" not in dados:
            logger.warning("arquivo de overrides_item vazio ou sem chave 'overrides'")
            return

        for descricao, config in dados["overrides"].items():
            self.overrides.append(
                {
                    "descricao": str(descricao).strip(),
                    "categoria": config.get("categoria"),
                    "classificacao": config.get("classificacao"),
                }
            )

        logger.info("carregados %d overrides de item", len(self.overrides))

    def _carregar_regras(self, caminho: Path) -> None:
        """Carrega regras regex do YAML."""
        if not caminho.exists():
            logger.warning("arquivo de regras de item não encontrado: %s", caminho)
            return

        with caminho.open("r", encoding="utf-8") as f:
            dados = yaml.safe_load(f)

        if not dados or "regras" not in dados:
            logger.warning("arquivo de regras de item vazio ou sem chave 'regras'")
            return

        for nome, regra in dados["regras"].items():
            regex_str = regra.get("regex", "")
            try:
                regex_compilado = re.compile(regex_str, re.IGNORECASE)
            except re.error as erro:
                logger.error("regex inválido em regra '%s': %s", nome, erro)
                continue

            self.regras.append(
                {
                    "nome": nome,
                    "regex": regex_compilado,
                    "categoria": regra.get("categoria"),
                    "classificacao": regra.get("classificacao"),
                }
            )

        logger.info("carregadas %d regras de categorização de item", len(self.regras))

    # ------------------------------------------------------------------------
    # Categorização
    # ------------------------------------------------------------------------

    def _aplicar_override(self, item: dict[str, Any]) -> bool:
        """Tenta aplicar override. Retorna True se casou."""
        texto = (item.get("descricao") or "").upper()
        if not texto:
            return False

        for override in self.overrides:
            if override["descricao"].upper() not in texto:
                continue
            if override["categoria"] is not None:
                item["categoria_item"] = override["categoria"]
            if override["classificacao"] is not None:
                item["classificacao_item"] = override["classificacao"]
            item["regra_aplicada"] = "override"
            return True
        return False

    def categorizar(self, item: dict[str, Any]) -> dict[str, Any]:
        """Mutates item com 'categoria_item', 'classificacao_item' e 'regra_aplicada'.

        Ordem:
            1. Override manual (mappings/overrides_item.yaml) -- se existir.
            2. Regras regex (mappings/categorias_item.yaml) -- primeira que casar.
            3. Fallback: categoria='Outros', classificacao='Questionável'.
        """
        if self._aplicar_override(item):
            return item

        texto = item.get("descricao") or ""
        for regra in self.regras:
            if not regra["regex"].search(texto):
                continue
            if regra["categoria"] is not None:
                item["categoria_item"] = regra["categoria"]
            if regra["classificacao"] is not None:
                item["classificacao_item"] = regra["classificacao"]
            item["regra_aplicada"] = regra["nome"]
            return item

        # Fallback
        item["categoria_item"] = FALLBACK_CATEGORIA
        item["classificacao_item"] = FALLBACK_CLASSIFICACAO
        item["regra_aplicada"] = "fallback"
        return item

    def categorizar_lote(self, itens: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Categoriza lista de itens in-place e devolve referência."""
        categorizados = 0
        fallback = 0
        for item in itens:
            self.categorizar(item)
            if item.get("categoria_item") == FALLBACK_CATEGORIA:
                fallback += 1
            else:
                categorizados += 1

        total = len(itens)
        if total > 0:
            pct = (categorizados / total) * 100
            logger.info(
                "categorização de itens: %d/%d (%.1f%%) categorizados, %d em Outros",
                categorizados,
                total,
                pct,
                fallback,
            )
        return itens


# ============================================================================
# Detecção de padrões novos (propostas MD)
# ============================================================================


def detectar_padroes_recorrentes(
    itens: list[dict[str, Any]],
    frequencia_minima: int = FREQUENCIA_MIN_PROPOSTA,
) -> dict[str, int]:
    """Agrupa descrições em 'Outros' que aparecem >= frequencia_minima vezes.

    Devolve dict {descricao_normalizada: contagem} ordenado por contagem DESC.
    """
    descricoes: list[str] = []
    for item in itens:
        if item.get("categoria_item") != FALLBACK_CATEGORIA:
            continue
        descricao = (item.get("descricao") or "").strip().upper()
        if descricao:
            descricoes.append(descricao)

    contagem: Counter[str] = Counter(descricoes)
    return {
        desc: qtd
        for desc, qtd in sorted(contagem.items(), key=lambda x: (-x[1], x[0]))
        if qtd >= frequencia_minima
    }


def gerar_propostas_md(
    padroes: dict[str, int],
    caminho_propostas: Optional[Path] = None,
) -> list[Path]:
    """Gera um MD por padrão recorrente em docs/propostas/categoria_item/.

    Idempotente: nome do arquivo é determinístico a partir do slug da
    descrição. Sobrescreve se existir (mesma contagem ou atualizada).
    """
    caminho_propostas = caminho_propostas or _PATH_PROPOSTAS_PADRAO
    caminho_propostas.mkdir(parents=True, exist_ok=True)

    arquivos_gerados: list[Path] = []
    for descricao, contagem in padroes.items():
        slug = _slug(descricao)
        if not slug:
            continue
        destino = caminho_propostas / f"{slug}.md"
        linhas = _montar_conteudo_proposta(descricao, contagem)
        destino.write_text(linhas, encoding="utf-8")
        arquivos_gerados.append(destino)
    return arquivos_gerados


def _slug(texto: str) -> str:
    """Slug alfanumérico para nome de arquivo. Estilo do `linking._slug`."""
    out: list[str] = []
    for ch in texto.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in {"-", "_"}:
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    slug = "".join(out).strip("-")
    return slug[:60] or "item"


def _montar_conteudo_proposta(descricao: str, contagem: int) -> str:
    """Monta MD de proposta para padrão sem regra."""
    linhas = [
        "---",
        f"id: categoria_item_{_slug(descricao)}",
        "tipo: categoria_item",
        "motivo: padrao_recorrente_sem_regra",
        "status: aberta",
        "autor_proposta: item-categorizer-sprint50",
        "sprint_contexto: 50",
        "---",
        "",
        "# Padrão recorrente sem regra de categoria de item",
        "",
        "## Descrição observada",
        "",
        f"- `{descricao}`",
        f"- ocorrências: **{contagem}**",
        "",
        "## Decisão humana",
        "",
        "- **Categoria sugerida:** (preencher)",
        "- **Classificação (Obrigatório/Questionável/Supérfluo):** (preencher)",
        "- **Regex proposto:** (preencher, espelhar `mappings/categorias_item.yaml`)",
        "- **Motivo:** (preencher)",
        "",
        "---",
        "",
        '*"Nomear com precisão é o começo da sabedoria." -- Confúcio (parafraseado)*',
        "",
    ]
    return "\n".join(linhas)


# ============================================================================
# Persistência no grafo
# ============================================================================


def categorizar_todos_items_no_grafo(
    db: Any,
    caminho_regras: Optional[Path] = None,
    caminho_overrides: Optional[Path] = None,
    caminho_propostas: Optional[Path] = None,
    frequencia_minima: int = FREQUENCIA_MIN_PROPOSTA,
) -> dict[str, int]:
    """Aplica categorização a todos os nodes `item` do grafo.

    Para cada item:
        1. Extrai descrição bruta de `metadata.descricao` (ou `nome_canonico`).
        2. Aplica override > regex > fallback.
        3. Faz upsert do node `categoria` com `tipo_categoria=item`.
        4. Cria aresta `categoria_de` (item -> categoria) idempotente.

    Gera propostas MD para itens em "Outros" com frequência >= minimo.

    Devolve dict com contadores: items_analisados, categorizados, fallback,
    categorias_distintas, arestas_criadas, propostas_abertas.

    Contrato de `db`: instância de `src.graph.db.GrafoDB` (importada
    lazy pelo chamador para manter o módulo sem acoplamento circular).
    """
    categorizer = ItemCategorizer(
        caminho_regras=caminho_regras,
        caminho_overrides=caminho_overrides,
    )

    nodes_item = db.listar_nodes(tipo="item")
    stats: dict[str, int] = {
        "items_analisados": len(nodes_item),
        "categorizados": 0,
        "fallback": 0,
        "categorias_distintas": 0,
        "arestas_criadas": 0,
        "propostas_abertas": 0,
    }

    categoria_ids: dict[str, int] = {}
    items_categorizados: list[dict[str, Any]] = []

    for node in nodes_item:
        if node.id is None:
            continue
        descricao_bruta = node.metadata.get("descricao") or node.nome_canonico
        item_dict: dict[str, Any] = {
            "node_id": node.id,
            "descricao": descricao_bruta,
        }
        categorizer.categorizar(item_dict)
        items_categorizados.append(item_dict)

        categoria_nome = item_dict["categoria_item"]
        classificacao = item_dict["classificacao_item"]
        regra = item_dict["regra_aplicada"]

        if categoria_nome == FALLBACK_CATEGORIA:
            stats["fallback"] += 1
        else:
            stats["categorizados"] += 1

        if categoria_nome not in categoria_ids:
            cat_id = db.upsert_node(
                TIPO_NODE_CATEGORIA,
                categoria_nome,
                metadata={
                    "tipo_categoria": "item",
                    "classificacao_default": classificacao,
                },
            )
            categoria_ids[categoria_nome] = cat_id

        db.adicionar_edge(
            src_id=node.id,
            dst_id=categoria_ids[categoria_nome],
            tipo=EDGE_TIPO_CATEGORIA_DE,
            evidencia={
                "regra_aplicada": regra,
                "classificacao": classificacao,
            },
        )
        stats["arestas_criadas"] += 1

    stats["categorias_distintas"] = len(categoria_ids)

    padroes = detectar_padroes_recorrentes(items_categorizados, frequencia_minima)
    if padroes:
        arquivos = gerar_propostas_md(padroes, caminho_propostas)
        stats["propostas_abertas"] = len(arquivos)

    logger.info("categorização de items no grafo concluída: %s", stats)
    return stats


# "Nomear com precisão é o começo da sabedoria." -- Confúcio (parafraseado)
