"""Testes do ItemCategorizer (Sprint 50).

Cobre:
- Carga do YAML com as 80+ regras e 15+ categorias mínimas.
- Categorização de itens típicos do varejo brasileiro (alimentos, higiene,
  doces, bebidas, limpeza, medicamentos, eletrônicos, pet, serviços).
- Fallback para "Outros" + "Questionável" quando nenhuma regra casa.
- Override YAML tem prioridade sobre regex.
- Propostas MD geradas para padrões recorrentes em "Outros".
- Aresta `categoria_de` criada entre item e categoria no grafo.
- Idempotência: rodar 2x não duplica aresta.
- Exatamente 1 categoria por item (primeira regra que casa vence).

Acentuação: categorias em asserts usam acentuação completa PT-BR; chaves
técnicas (`tipo="categoria"`, `"categoria_de"`, `"tipo_categoria"`) ficam
sem acento por contrato N-para-N do grafo.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.graph.db import GrafoDB
from src.graph.ingestor_documento import upsert_item
from src.transform.item_categorizer import (
    EDGE_TIPO_CATEGORIA_DE,
    FALLBACK_CATEGORIA,
    FALLBACK_CLASSIFICACAO,
    TIPO_NODE_CATEGORIA,
    ItemCategorizer,
    categorizar_todos_items_no_grafo,
    detectar_padroes_recorrentes,
    gerar_propostas_md,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def db(tmp_path: Path):
    grafo = GrafoDB(tmp_path / "grafo.sqlite")
    grafo.criar_schema()
    yield grafo
    grafo.fechar()


@pytest.fixture
def caminho_overrides_vazio(tmp_path: Path) -> Path:
    """YAML vazio para forçar rota 100% regex."""
    destino = tmp_path / "overrides_item.yaml"
    destino.write_text("overrides: {}\n", encoding="utf-8")
    return destino


@pytest.fixture
def caminho_overrides_sample(tmp_path: Path) -> Path:
    destino = tmp_path / "overrides_item.yaml"
    dados = {
        "overrides": {
            "LEITE MOCA MANUAL": {
                "categoria": "Doces",
                "classificacao": "Supérfluo",
            }
        }
    }
    destino.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
    return destino


@pytest.fixture
def caminho_propostas(tmp_path: Path) -> Path:
    destino = tmp_path / "propostas_categoria_item"
    destino.mkdir(parents=True, exist_ok=True)
    return destino


# ============================================================================
# Carga do YAML
# ============================================================================


def test_carrega_yaml_com_80_regras_minimas():
    """YAML oficial tem >= 80 regras."""
    with open("mappings/categorias_item.yaml", encoding="utf-8") as f:
        dados = yaml.safe_load(f)
    assert "regras" in dados
    assert len(dados["regras"]) >= 80, (
        f"YAML tem apenas {len(dados['regras'])} regras; mínimo é 80"
    )


def test_15_categorias_distintas_cobertas():
    """YAML oficial cobre pelo menos 15 categorias distintas."""
    with open("mappings/categorias_item.yaml", encoding="utf-8") as f:
        dados = yaml.safe_load(f)
    categorias = {r["categoria"] for r in dados["regras"].values()}
    assert len(categorias) >= 15, (
        f"YAML tem apenas {len(categorias)} categorias distintas; mínimo é 15"
    )


def test_categorizer_carrega_regras_reais():
    """ItemCategorizer instanciado carrega as regras do YAML oficial."""
    cat = ItemCategorizer()
    assert len(cat.regras) >= 80


# ============================================================================
# Categorização por regra (casos canônicos)
# ============================================================================


def test_arroz_categoriza_como_alimentos_basicos():
    cat = ItemCategorizer()
    item = {"descricao": "ARROZ TIO JOAO TP1 5KG"}
    cat.categorizar(item)
    assert item["categoria_item"] == "Alimentos Básicos"
    assert item["classificacao_item"] == "Obrigatório"


def test_dove_shampoo_categoriza_como_higiene():
    cat = ItemCategorizer()
    item = {"descricao": "SHAMPOO DOVE NUTRICAO 200ML"}
    cat.categorizar(item)
    assert item["categoria_item"] == "Higiene"
    assert item["classificacao_item"] == "Obrigatório"


def test_chocolate_categoriza_como_doces():
    cat = ItemCategorizer()
    item = {"descricao": "CHOCOLATE LACTA AO LEITE 90G"}
    cat.categorizar(item)
    assert item["categoria_item"] == "Doces"
    assert item["classificacao_item"] == "Supérfluo"


def test_cerveja_categoriza_como_bebidas_alcoolicas():
    cat = ItemCategorizer()
    item = {"descricao": "CERVEJA HEINEKEN LONG NECK 330ML"}
    cat.categorizar(item)
    assert item["categoria_item"] == "Bebidas Alcoólicas"
    assert item["classificacao_item"] == "Supérfluo"


def test_detergente_categoriza_como_limpeza():
    cat = ItemCategorizer()
    item = {"descricao": "DETERGENTE YPE NEUTRO 500ML"}
    cat.categorizar(item)
    assert item["categoria_item"] == "Limpeza"
    assert item["classificacao_item"] == "Obrigatório"


def test_dipirona_categoriza_como_medicamentos():
    cat = ItemCategorizer()
    item = {"descricao": "DIPIRONA SODICA 500MG 20 COMP"}
    cat.categorizar(item)
    assert item["categoria_item"] == "Medicamentos"
    assert item["classificacao_item"] == "Obrigatório"


def test_cabo_usb_categoriza_como_eletronicos():
    cat = ItemCategorizer()
    item = {"descricao": "CABO USB TIPO C 1M"}
    cat.categorizar(item)
    assert item["categoria_item"] == "Eletrônicos"


def test_racao_premier_categoriza_como_pet():
    cat = ItemCategorizer()
    item = {"descricao": "RACAO PREMIER GATO ADULTO 1KG"}
    cat.categorizar(item)
    assert item["categoria_item"] == "Pet"


def test_frango_categoriza_como_carnes():
    cat = ItemCategorizer()
    item = {"descricao": "PEITO FRANGO SASSA CONGELADO KG"}
    cat.categorizar(item)
    assert item["categoria_item"] == "Carnes"
    assert item["classificacao_item"] == "Obrigatório"


def test_tomate_categoriza_como_hortifruti():
    cat = ItemCategorizer()
    item = {"descricao": "TOMATE SALADA KG"}
    cat.categorizar(item)
    assert item["categoria_item"] == "Hortifrúti"


# ============================================================================
# Armadilha A50-1: LEITE MOÇA é doce, não laticínio
# ============================================================================


def test_leite_condensado_cai_em_doces_nao_laticinios():
    """Armadilha A50-1: "LEITE MOCA" não pode virar laticínio."""
    cat = ItemCategorizer()
    item = {"descricao": "LEITE MOCA NESTLE 395G"}
    cat.categorizar(item)
    assert item["categoria_item"] == "Doces"
    assert item["classificacao_item"] == "Supérfluo"


def test_leite_integral_cai_em_alimentos_basicos():
    cat = ItemCategorizer()
    item = {"descricao": "LEITE INTEGRAL ITAMBE 1L"}
    cat.categorizar(item)
    assert item["categoria_item"] == "Alimentos Básicos"


# ============================================================================
# Fallback
# ============================================================================


def test_item_desconhecido_cai_em_outros():
    cat = ItemCategorizer()
    item = {"descricao": "XYZABC PRODUTO DESCONHECIDO ZZZ999"}
    cat.categorizar(item)
    assert item["categoria_item"] == FALLBACK_CATEGORIA
    assert item["classificacao_item"] == FALLBACK_CLASSIFICACAO
    assert item["regra_aplicada"] == "fallback"


def test_descricao_vazia_cai_em_outros():
    cat = ItemCategorizer()
    item = {"descricao": ""}
    cat.categorizar(item)
    assert item["categoria_item"] == FALLBACK_CATEGORIA


# ============================================================================
# Override manual
# ============================================================================


def test_override_yaml_prioritario_sobre_regex(caminho_overrides_sample: Path):
    """Override tem precedência: LEITE MOCA MANUAL força "Doces" mesmo
    que a regex de `doces_leite_cond` já faria isso -- o override rotula
    a regra com nome "override" para auditoria."""
    cat = ItemCategorizer(caminho_overrides=caminho_overrides_sample)
    item = {"descricao": "LEITE MOCA MANUAL 395G"}
    cat.categorizar(item)
    assert item["categoria_item"] == "Doces"
    assert item["classificacao_item"] == "Supérfluo"
    assert item["regra_aplicada"] == "override"


def test_override_prevalece_sobre_regex_conflitante(tmp_path: Path):
    """Se override mapeia SABONETE -> Limpeza (contrariando regex), override ganha."""
    destino = tmp_path / "overrides_item.yaml"
    dados = {
        "overrides": {
            "SABONETE DOVE ESPECIAL": {
                "categoria": "Limpeza",
                "classificacao": "Obrigatório",
            }
        }
    }
    destino.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
    cat = ItemCategorizer(caminho_overrides=destino)
    item = {"descricao": "SABONETE DOVE ESPECIAL ROSA 90G"}
    cat.categorizar(item)
    assert item["categoria_item"] == "Limpeza"
    assert item["regra_aplicada"] == "override"


# ============================================================================
# Detecção de padrões recorrentes + propostas MD
# ============================================================================


def test_item_frequente_gera_proposta(caminho_propostas: Path):
    """Itens em 'Outros' com >= 3 ocorrências geram proposta MD."""
    itens = [
        {"descricao": "WIDGETZ XP-500", "categoria_item": FALLBACK_CATEGORIA},
        {"descricao": "WIDGETZ XP-500", "categoria_item": FALLBACK_CATEGORIA},
        {"descricao": "WIDGETZ XP-500", "categoria_item": FALLBACK_CATEGORIA},
        {"descricao": "GADGET SOLO", "categoria_item": FALLBACK_CATEGORIA},
    ]
    padroes = detectar_padroes_recorrentes(itens, frequencia_minima=3)
    assert "WIDGETZ XP-500" in padroes
    assert padroes["WIDGETZ XP-500"] == 3
    assert "GADGET SOLO" not in padroes  # só 1 ocorrência

    arquivos = gerar_propostas_md(padroes, caminho_propostas)
    assert len(arquivos) == 1
    conteudo = arquivos[0].read_text(encoding="utf-8")
    assert "WIDGETZ XP-500" in conteudo
    assert "tipo: categoria_item" in conteudo
    assert "status: aberta" in conteudo


def test_proposta_idempotente_sobrescreve(caminho_propostas: Path):
    """Gerar proposta 2x não duplica arquivo -- sobrescreve o mesmo slug."""
    itens = [{"descricao": "ITEM RECORRENTE", "categoria_item": FALLBACK_CATEGORIA}] * 3
    padroes = detectar_padroes_recorrentes(itens)
    arquivos_1 = gerar_propostas_md(padroes, caminho_propostas)
    arquivos_2 = gerar_propostas_md(padroes, caminho_propostas)
    assert len(arquivos_1) == 1
    assert arquivos_1 == arquivos_2  # mesmo path


# ============================================================================
# Persistência no grafo (aresta categoria_de)
# ============================================================================


def test_aresta_categoria_de_criada_no_grafo(db: GrafoDB, caminho_propostas: Path):
    """categorizar_todos_items_no_grafo cria aresta item -> categoria."""
    item_id = upsert_item(
        db,
        cnpj_varejo="12345678000190",
        data_compra="2026-04-20",
        codigo_produto="001",
        descricao="ARROZ TIO JOAO TP1 5KG",
    )
    stats = categorizar_todos_items_no_grafo(db, caminho_propostas=caminho_propostas)
    assert stats["items_analisados"] == 1
    assert stats["categorizados"] == 1
    assert stats["arestas_criadas"] == 1

    # Verifica que a aresta existe e aponta para 'Alimentos Básicos'.
    arestas = db.listar_edges(src_id=item_id, tipo=EDGE_TIPO_CATEGORIA_DE)
    assert len(arestas) == 1
    categoria_node = db.buscar_node_por_id(arestas[0].dst_id)
    assert categoria_node is not None
    assert categoria_node.tipo == TIPO_NODE_CATEGORIA
    assert categoria_node.nome_canonico == "ALIMENTOS BÁSICOS"  # upper, acento preservado
    assert categoria_node.metadata.get("tipo_categoria") == "item"


def test_cada_item_tem_exatamente_uma_categoria(db: GrafoDB, caminho_propostas: Path):
    """Sprint 50 acceptance: cada item_canonico tem 1 aresta categoria_de."""
    upsert_item(db, "12345678000190", "2026-04-20", "001", "CHOCOLATE LACTA 90G")
    upsert_item(db, "12345678000190", "2026-04-20", "002", "SHAMPOO DOVE 200ML")
    upsert_item(db, "12345678000190", "2026-04-20", "003", "DETERGENTE YPE 500ML")

    categorizar_todos_items_no_grafo(db, caminho_propostas=caminho_propostas)

    for node in db.listar_nodes(tipo="item"):
        assert node.id is not None
        arestas = db.listar_edges(src_id=node.id, tipo=EDGE_TIPO_CATEGORIA_DE)
        assert len(arestas) == 1, (
            f"item {node.nome_canonico} tem {len(arestas)} arestas categoria_de (esperado 1)"
        )


def test_idempotente_nao_duplica_aresta(db: GrafoDB, caminho_propostas: Path):
    """Rodar categorizar_todos_items_no_grafo 2x não duplica aresta."""
    upsert_item(db, "12345678000190", "2026-04-20", "001", "ARROZ TIO JOAO 5KG")

    categorizar_todos_items_no_grafo(db, caminho_propostas=caminho_propostas)
    stats_1 = db.estatisticas()
    categorizar_todos_items_no_grafo(db, caminho_propostas=caminho_propostas)
    stats_2 = db.estatisticas()

    assert stats_1["edges_total"] == stats_2["edges_total"]
    assert stats_1["nodes_por_tipo"].get("categoria") == stats_2["nodes_por_tipo"].get(
        "categoria"
    )


def test_mutacao_regra_yaml_substitui_aresta_antiga(db: GrafoDB, tmp_path: Path):
    """Sprint 50b (A3 2026-04-23): quando item que foi categorizado em X
    passa a casar regra Y após mutação do YAML, deve haver exatamente 1
    aresta final, apontando para Y (não 2 arestas acumuladas)."""
    import yaml as _yaml

    def _dump_regras(categoria: str, classif: str) -> str:
        return _yaml.safe_dump(
            {
                "regras": {
                    "produto_teste": {
                        "regex": r"\bPRODUTO\b",
                        "categoria": categoria,
                        # chave "classificacao" (sem acento) é schema N-para-N
                        # com mappings/categorias_item.yaml -- BRIEF §89.
                        "classificacao": classif,  # noqa: accent
                    }
                }
            },
            allow_unicode=True,
        )

    yaml_inicial = tmp_path / "regras_v1.yaml"
    yaml_inicial.write_text(_dump_regras("Categoria A", "Obrigatório"), encoding="utf-8")
    yaml_mutado = tmp_path / "regras_v2.yaml"
    yaml_mutado.write_text(_dump_regras("Categoria B", "Supérfluo"), encoding="utf-8")
    propostas = tmp_path / "propostas"

    item_id = upsert_item(db, "12345678000190", "2026-04-20", "001", "PRODUTO TESTE")

    # Rodada 1: categoria A
    categorizar_todos_items_no_grafo(
        db, caminho_regras=yaml_inicial, caminho_propostas=propostas
    )
    arestas = db.listar_edges(src_id=item_id, tipo=EDGE_TIPO_CATEGORIA_DE)
    assert len(arestas) == 1
    categoria_a = db.buscar_node_por_id(arestas[0].dst_id)
    assert categoria_a is not None
    assert "CATEGORIA A" in categoria_a.nome_canonico.upper()

    # Rodada 2: YAML mutado -> item agora deve ter 1 aresta para Categoria B
    categorizar_todos_items_no_grafo(
        db, caminho_regras=yaml_mutado, caminho_propostas=propostas
    )
    arestas = db.listar_edges(src_id=item_id, tipo=EDGE_TIPO_CATEGORIA_DE)
    assert len(arestas) == 1, (
        f"item deve ter exatamente 1 aresta categoria_de após mutação de YAML, "
        f"achei {len(arestas)}"
    )
    categoria_b = db.buscar_node_por_id(arestas[0].dst_id)
    assert categoria_b is not None
    assert "CATEGORIA B" in categoria_b.nome_canonico.upper()


def test_fallback_tambem_cria_aresta(db: GrafoDB, caminho_propostas: Path):
    """Item sem regra também recebe aresta para categoria 'Outros'."""
    item_id = upsert_item(
        db, "12345678000190", "2026-04-20", "999", "XYZABC DESCONHECIDO"
    )
    stats = categorizar_todos_items_no_grafo(db, caminho_propostas=caminho_propostas)
    assert stats["fallback"] == 1
    assert stats["arestas_criadas"] == 1
    arestas = db.listar_edges(src_id=item_id, tipo=EDGE_TIPO_CATEGORIA_DE)
    assert len(arestas) == 1
    categoria_node = db.buscar_node_por_id(arestas[0].dst_id)
    assert categoria_node is not None
    assert categoria_node.nome_canonico == FALLBACK_CATEGORIA.upper()


def test_categorizar_lote_reporta_contagem():
    cat = ItemCategorizer()
    itens = [
        {"descricao": "ARROZ TIO JOAO 5KG"},
        {"descricao": "CHOCOLATE LACTA"},
        {"descricao": "ZZZ DESCONHECIDO 777"},
    ]
    cat.categorizar_lote(itens)
    categorias = [i["categoria_item"] for i in itens]
    assert "Alimentos Básicos" in categorias
    assert "Doces" in categorias
    assert FALLBACK_CATEGORIA in categorias


# "O teste é a verdade que o código tem medo de encarar." -- provérbio estoico parafraseado
