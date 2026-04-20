"""Testes do pacote src.graph (Sprint 42).

Cobre:
- GrafoDB: schema idempotente, upsert por (tipo, nome_canonico),
  edges com UNIQUE(src,dst,tipo), foreign keys ON
- Models: serialização JSON estável, normalização de nome_canonico
- Entity resolution: normalização determinística + fuzzy threshold
- Migração inicial: idempotente, popula transações + arestas + entity-resolved
- Queries: vida_de_transacao, fornecedores_recorrentes, estatisticas
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.graph import entity_resolution as er
from src.graph import models, queries
from src.graph.db import GrafoDB
from src.graph.migracao_inicial import executar


@pytest.fixture
def db(tmp_path: Path) -> GrafoDB:
    grafo = GrafoDB(tmp_path / "grafo.sqlite")
    grafo.criar_schema()
    yield grafo
    grafo.fechar()


# ============================================================================
# Models -- normalização e serialização
# ============================================================================


def test_normalizar_nome_canonico_upper_strip():
    assert models.normalizar_nome_canonico("  neoenergia  ") == "NEOENERGIA"


def test_serializar_aliases_ordenado_e_dedupe():
    out = models.serializar_aliases(["b", "a", "b", "c"])
    assert out == '["a", "b", "c"]'


def test_serializar_metadata_chaves_ordenadas():
    out = models.serializar_metadata({"z": 1, "a": 2})
    assert out == '{"a": 2, "z": 1}'


def test_deserializar_aliases_invalido_retorna_vazio():
    assert models.deserializar_aliases("not json") == []
    assert models.deserializar_aliases(None) == []


# ============================================================================
# GrafoDB -- schema, upsert, edges
# ============================================================================


def test_criar_schema_idempotente(tmp_path):
    g = GrafoDB(tmp_path / "g.sqlite")
    g.criar_schema()
    g.criar_schema()  # 2x não deve falhar
    assert g.estatisticas()["nodes_total"] == 0
    g.fechar()


def test_upsert_node_unico_por_tipo_e_nome(db):
    id1 = db.upsert_node("fornecedor", "neoenergia", metadata={"cnpj": "12345"})
    id2 = db.upsert_node("fornecedor", "Neoenergia", metadata={"endereco": "X"})
    # mesma chave normalizada -> mesmo id
    assert id1 == id2
    # metadata é mergeada
    n = db.buscar_node_por_id(id1)
    assert n is not None
    assert n.nome_canonico == "NEOENERGIA"
    assert n.metadata["cnpj"] == "12345"
    assert n.metadata["endereco"] == "X"


def test_upsert_node_aliases_unidos(db):
    db.upsert_node("fornecedor", "X", aliases=["a", "b"])
    db.upsert_node("fornecedor", "X", aliases=["b", "c"])
    n = db.buscar_node("fornecedor", "X")
    assert n is not None
    assert sorted(n.aliases) == ["a", "b", "c"]


def test_adicionar_edge_dedup_por_tripla(db):
    a = db.upsert_node("fornecedor", "A")
    b = db.upsert_node("periodo", "2026-04")
    db.adicionar_edge(a, b, "ocorre_em")
    db.adicionar_edge(a, b, "ocorre_em")  # duplicada -> ignora
    db.adicionar_edge(a, b, "outra_aresta")  # tipo diferente -> aceita
    edges = db.listar_edges(src_id=a)
    tipos = sorted(e.tipo for e in edges)
    assert tipos == ["ocorre_em", "outra_aresta"]


def test_listar_nodes_filtra_por_tipo(db):
    db.upsert_node("fornecedor", "F1")
    db.upsert_node("categoria", "Energia")
    db.upsert_node("fornecedor", "F2")
    fornecedores = db.listar_nodes(tipo="fornecedor")
    assert len(fornecedores) == 2
    todos = db.listar_nodes()
    assert len(todos) == 3


def test_estatisticas_conta_por_tipo(db):
    db.upsert_node("fornecedor", "F1")
    db.upsert_node("categoria", "Energia")
    a = db.upsert_node("fornecedor", "F2")
    b = db.upsert_node("periodo", "P")
    db.adicionar_edge(a, b, "ocorre_em")
    stats = db.estatisticas()
    assert stats["nodes_por_tipo"] == {"fornecedor": 2, "categoria": 1, "periodo": 1}
    assert stats["edges_por_tipo"] == {"ocorre_em": 1}
    assert stats["nodes_total"] == 4
    assert stats["edges_total"] == 1


# ============================================================================
# Entity resolution
# ============================================================================


def test_normalizar_remove_sufixo_societario():
    assert er.normalizar_fornecedor("Neoenergia S/A") == "NEOENERGIA"
    assert er.normalizar_fornecedor("acme ltda") == "ACME"
    assert er.normalizar_fornecedor("X EIRELI") == "X"


def test_resolver_fornecedor_sem_candidatos_marca_novo():
    r = er.resolver_fornecedor("NEOENERGIA", [])
    assert r.decisao == "novo"
    assert r.nome_canonico == "NEOENERGIA"


def test_resolver_fornecedor_match_deterministico_apos_normalizar():
    r = er.resolver_fornecedor("Neoenergia S/A", ["NEOENERGIA"])
    assert r.decisao == "match"
    assert r.fonte == "deterministico"
    assert r.nome_canonico == "NEOENERGIA"


def test_resolver_fornecedor_fuzzy_alto_unifica():
    r = er.resolver_fornecedor("MERCADO SAO JOAO", ["MERCADO SÃO JOÃO"])
    assert r.decisao in {"match", "sugestao"}
    # Deve achar similaridade boa apesar dos acentos
    assert r.similaridade >= 80


def test_resolver_fornecedor_fuzzy_baixo_marca_novo():
    r = er.resolver_fornecedor("IFOOD", ["NEOENERGIA"])
    assert r.decisao == "novo"


def test_resolver_fornecedor_cnpj_diferente_nao_unifica():
    r = er.resolver_fornecedor(
        "ACME LTDA",
        ["ACME"],
        cnpj_novo="11.111.111/0001-11",
        cnpjs_por_canonico={"ACME": "22.222.222/0001-22"},
    )
    assert r.decisao == "novo"
    assert r.fonte == "cnpj_diferente"


# ============================================================================
# Queries
# ============================================================================


def test_vida_de_transacao_lista_arestas_saindo(db):
    t = db.upsert_node("transacao", "hash_t")
    cat = db.upsert_node("categoria", "Energia")
    per = db.upsert_node("periodo", "2026-04")
    db.adicionar_edge(t, cat, "categoria_de")
    db.adicionar_edge(t, per, "ocorre_em")
    arestas = queries.vida_de_transacao(db, t)
    assert len(arestas) == 2
    tipos_dst = sorted(a["dst_tipo"] for a in arestas)
    assert tipos_dst == ["categoria", "periodo"]


def test_fornecedores_recorrentes_top_por_arestas(db):
    t1 = db.upsert_node("transacao", "t1")
    t2 = db.upsert_node("transacao", "t2")
    t3 = db.upsert_node("transacao", "t3")
    f_top = db.upsert_node("fornecedor", "TOP")
    f_um = db.upsert_node("fornecedor", "UM")
    db.adicionar_edge(t1, f_top, "fornecido_por")
    db.adicionar_edge(t2, f_top, "fornecido_por")
    db.adicionar_edge(t3, f_top, "fornecido_por")
    db.adicionar_edge(t1, f_um, "fornecido_por")
    top = queries.fornecedores_recorrentes(db, edge_tipo="fornecido_por", minimo=2)
    assert len(top) == 1
    assert top[0]["nome_canonico"] == "TOP"
    assert top[0]["ocorrencias"] == 3


# ============================================================================
# Migração inicial -- contra XLSX sintético
# ============================================================================


def test_migracao_inicial_popula_transacoes_e_arestas(tmp_path):
    """XLSX sintético com 5 linhas representativas."""
    df = pd.DataFrame(
        [
            {
                "data": "2026-04-01",
                "valor": -50.00,
                "forma_pagamento": "Pix",
                "local": "NEOENERGIA",
                "quem": "André",
                "categoria": "Energia",
                "classificacao": "Obrigatório",
                "banco_origem": "Itaú",
                "tipo": "Despesa",
                "mes_ref": "2026-04",
                "tag_irpf": None,
                "obs": None,
            },
            {
                "data": "2026-04-02",
                "valor": -120.00,
                "forma_pagamento": "Crédito",
                "local": "Neoenergia S/A",  # mesma entidade após normalização
                "quem": "André",
                "categoria": "Energia",
                "classificacao": "Obrigatório",
                "banco_origem": "Itaú",
                "tipo": "Despesa",
                "mes_ref": "2026-04",
                "tag_irpf": None,
                "obs": None,
            },
            {
                "data": "2026-04-05",
                "valor": -800.00,
                "forma_pagamento": "Boleto",
                "local": "Aluguel Ki-Sabor",
                "quem": "Casal",
                "categoria": "Aluguel",
                "classificacao": "Obrigatório",
                "banco_origem": "Itaú",
                "tipo": "Despesa",
                "mes_ref": "2026-04",
                "tag_irpf": "Aluguel-Pago",
                "obs": None,
            },
            {
                "data": "2026-04-10",
                "valor": 5000.00,
                "forma_pagamento": "Transferência",
                "local": "Salário G4F",
                "quem": "André",
                "categoria": "Salário",
                "classificacao": "N/A",
                "banco_origem": "Itaú",
                "tipo": "Receita",
                "mes_ref": "2026-04",
                "tag_irpf": "Rendimento-PJ",
                "obs": None,
            },
            {
                "data": "2026-04-15",
                "valor": -30.00,
                "forma_pagamento": "Débito",
                "local": "Padaria X",
                "quem": "André",
                "categoria": "Padaria",
                "classificacao": "Questionável",
                "banco_origem": "Itaú",
                "tipo": "Despesa",
                "mes_ref": "2026-04",
                "tag_irpf": None,
                "obs": None,
            },
        ]
    )
    xlsx_path = tmp_path / "ouroboros_2026.xlsx"
    df.to_excel(xlsx_path, sheet_name="extrato", index=False)

    db_path = tmp_path / "grafo.sqlite"
    stats = executar(db_path=db_path, xlsx_path=xlsx_path)

    # Conferências
    assert stats["nodes_por_tipo"]["transacao"] == 5
    assert stats["nodes_por_tipo"]["categoria"] == 4  # Energia, Aluguel, Salário, Padaria
    assert stats["nodes_por_tipo"]["periodo"] == 1  # 2026-04
    assert stats["nodes_por_tipo"]["conta"] == 1  # Itaú
    assert stats["nodes_por_tipo"]["tag_irpf"] == 2  # Aluguel-Pago, Rendimento-PJ
    # NEOENERGIA + Neoenergia S/A unificados em 1 fornecedor
    assert (
        stats["nodes_por_tipo"]["fornecedor"] == 4
    )  # NEOENERGIA, Aluguel Ki-Sabor, Salário G4F, Padaria X

    # Arestas: cada transação tem categoria_de + ocorre_em + origem + contraparte = 4 arestas
    # + 2 transações com tag_irpf = 2 arestas extras
    # Total esperado: 5*4 + 2 = 22
    assert stats["edges_total"] == 22


def test_migracao_inicial_idempotente(tmp_path):
    """Rodar migração 2x não duplica nodes nem edges."""
    df = pd.DataFrame(
        [
            {
                "data": "2026-04-01",
                "valor": -50.00,
                "forma_pagamento": "Pix",
                "local": "NEOENERGIA",
                "quem": "André",
                "categoria": "Energia",
                "classificacao": "Obrigatório",
                "banco_origem": "Itaú",
                "tipo": "Despesa",
                "mes_ref": "2026-04",
                "tag_irpf": None,
                "obs": None,
            },
        ]
    )
    xlsx_path = tmp_path / "ouroboros_2026.xlsx"
    df.to_excel(xlsx_path, sheet_name="extrato", index=False)
    db_path = tmp_path / "grafo.sqlite"

    stats1 = executar(db_path=db_path, xlsx_path=xlsx_path)
    stats2 = executar(db_path=db_path, xlsx_path=xlsx_path)
    assert stats1 == stats2


def test_migracao_inicial_xlsx_inexistente_levanta(tmp_path):
    with pytest.raises(FileNotFoundError):
        executar(db_path=tmp_path / "g.sqlite", xlsx_path=tmp_path / "inexistente.xlsx")


# "O grafo é o esqueleto; as arestas são o que lembra." -- princípio de cartógrafo
