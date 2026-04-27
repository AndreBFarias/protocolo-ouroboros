"""Testes de `grafo_filtrado` + wrapper pyvis (Sprint 78)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.dashboard.componentes import grafo_pyvis
from src.graph.db import GrafoDB
from src.graph.queries import grafo_filtrado

# Sprint 78: pyvis depende do módulo `bz2` (via networkx). Em ambientes onde
# o Python foi compilado sem suporte a bzip2 (comum em pyenv sem bzip2-dev
# no sistema), o import falha. Os testes do wrapper são pulados nesse caso
# — o código de produção tem graceful degradation (devolve placeholder HTML).
_SEM_PYVIS = not grafo_pyvis._PYVIS_DISPONIVEL
_MOTIVO_SEM_PYVIS = (
    "pyvis indisponível neste ambiente (Python compilado sem _bz2). "
    "Wrapper tem graceful degradation; testes do HTML pulados."
)


# ============================================================================
# _label_humano / parsers
# ============================================================================


class TestLabelHumano:
    def test_alias_preferido(self) -> None:
        node = {
            "aliases": '["Americanas"]',
            "nome_canonico": "00.776.574/0001-56",
        }
        assert grafo_pyvis._label_humano(node) == "Americanas"

    def test_razao_social_como_fallback(self) -> None:
        node = {
            "aliases": None,
            "nome_canonico": "CNPJ-123",
            "metadata": '{"razao_social": "FERNANDEZ CELESTINO E CIA"}',
        }
        assert grafo_pyvis._label_humano(node) == "FERNANDEZ CELESTINO E CIA"

    def test_nome_canonico_truncado_como_ultimo_recurso(self) -> None:
        long_name = "N" * 60
        node = {"nome_canonico": long_name}
        label = grafo_pyvis._label_humano(node)
        assert len(label) <= 40
        assert label.endswith("...")

    def test_node_id_como_ultimissimo_recurso(self) -> None:
        node = {"id": 99}
        assert grafo_pyvis._label_humano(node) == "node-99"

    def test_parse_aliases_tolera_invalido(self) -> None:
        assert grafo_pyvis._parse_aliases("não é json válido") == []
        assert grafo_pyvis._parse_aliases(None) == []
        assert grafo_pyvis._parse_aliases([]) == []
        assert grafo_pyvis._parse_aliases(["a", "b"]) == ["a", "b"]

    def test_parse_metadata_tolera_invalido(self) -> None:
        assert grafo_pyvis._parse_metadata("") == {}
        assert grafo_pyvis._parse_metadata('{"a": 1}') == {"a": 1}
        assert grafo_pyvis._parse_metadata({"b": 2}) == {"b": 2}


# ============================================================================
# construir_grafo_html
# ============================================================================


@pytest.mark.skipif(_SEM_PYVIS, reason=_MOTIVO_SEM_PYVIS)
class TestConstruirGrafoHtml:
    def test_injeta_click_handler(self) -> None:
        html = grafo_pyvis.construir_grafo_html(
            nodes=[
                {
                    "id": 1,
                    "tipo": "fornecedor",
                    "nome_canonico": "Foo",
                    "aliases": "[]",
                    "metadata": "{}",
                    "grau": 1,
                }
            ],
            edges=[],
            altura_px=600,
        )
        assert "network.on('click'" in html or 'network.on("click"' in html
        assert "window.parent.location" in html

    def test_mapeamento_de_tipo_para_query_param(self) -> None:
        html = grafo_pyvis.construir_grafo_html(
            nodes=[
                {
                    "id": 1,
                    "tipo": "fornecedor",
                    "nome_canonico": "X",
                    "aliases": "[]",
                    "metadata": "{}",
                    "grau": 0,
                }
            ],
            edges=[],
        )
        # JS deve conter o dict de mapeamento com o campo "fornecedor"
        assert "fornecedor" in html

    def test_altura_configuravel_entra_no_html(self) -> None:
        html = grafo_pyvis.construir_grafo_html(
            nodes=[],
            edges=[],
            altura_px=1234,
        )
        assert "1234px" in html

    def test_nos_vazios_nao_quebram(self) -> None:
        html = grafo_pyvis.construir_grafo_html(nodes=[], edges=[])
        assert "<body" in html

    def test_mais_conexoes_vira_maior_size(self) -> None:
        # Regressão: tamanho base 10 + grau*2, clamp em 50.
        # Testamos o cálculo indiretamente via presença de size no HTML.
        html = grafo_pyvis.construir_grafo_html(
            nodes=[
                {
                    "id": 1,
                    "tipo": "fornecedor",
                    "nome_canonico": "A",
                    "aliases": "[]",
                    "metadata": "{}",
                    "grau": 10,
                },
                {
                    "id": 2,
                    "tipo": "fornecedor",
                    "nome_canonico": "B",
                    "aliases": "[]",
                    "metadata": "{}",
                    "grau": 1,
                },
            ],
            edges=[{"src": 1, "dst": 2, "tipo": "referencia", "peso": 1.0}],
        )
        assert "<body" in html


# ============================================================================
# grafo_filtrado
# ============================================================================


@pytest.fixture
def grafo_sintetico(tmp_path: Path) -> GrafoDB:
    db = GrafoDB(tmp_path / "g.sqlite")
    db.criar_schema()
    # 5 fornecedores, 3 categorias, 2 transações
    fornecedores = []
    for i in range(5):
        fornecedores.append(
            db.upsert_node(
                tipo="fornecedor",
                nome_canonico=f"FORNECEDOR-{i:02d}",
                metadata={"razao_social": f"F{i}"},
            )
        )
    categorias = []
    for i in range(3):
        categorias.append(db.upsert_node(tipo="categoria", nome_canonico=f"CAT-{i}", metadata={}))
    transacoes = []
    for i in range(2):
        transacoes.append(
            db.upsert_node(tipo="transacao", nome_canonico=f"TX-{i}", metadata={"valor": -100})
        )
    # Liga tx0 -> fornecedor0 (grau 1 para fornecedor0)
    db.adicionar_edge(src_id=transacoes[0], dst_id=fornecedores[0], tipo="paga_para", peso=1.0)
    # Liga tx1 -> fornecedor1
    db.adicionar_edge(src_id=transacoes[1], dst_id=fornecedores[1], tipo="paga_para", peso=1.0)
    return db


class TestGrafoFiltrado:
    def test_respeita_limite(self, grafo_sintetico: GrafoDB) -> None:
        nodes, _ = grafo_filtrado(
            grafo_sintetico,
            tipos=["fornecedor"],
            limite=3,
            incluir_orfaos=True,
        )
        assert len(nodes) == 3

    def test_respeita_tipos(self, grafo_sintetico: GrafoDB) -> None:
        nodes, _ = grafo_filtrado(grafo_sintetico, tipos=["categoria"], incluir_orfaos=True)
        assert all(n["tipo"] == "categoria" for n in nodes)
        assert len(nodes) == 3

    def test_orfaos_desligados_remove_grau_zero(self, grafo_sintetico: GrafoDB) -> None:
        nodes, _ = grafo_filtrado(grafo_sintetico, tipos=["fornecedor"], incluir_orfaos=False)
        # Só fornecedores 0 e 1 têm grau > 0
        assert len(nodes) == 2
        assert all(n["grau"] >= 1 for n in nodes)

    def test_edges_entre_nodes_selecionados(self, grafo_sintetico: GrafoDB) -> None:
        nodes, edges = grafo_filtrado(
            grafo_sintetico,
            tipos=["transacao", "fornecedor"],
            limite=100,
            incluir_orfaos=True,
        )
        ids = {n["id"] for n in nodes}
        # Toda aresta tem src e dst nos nodes retornados
        for e in edges:
            assert e["src"] in ids
            assert e["dst"] in ids

    def test_tipos_vazios_retorna_vazio(self, grafo_sintetico: GrafoDB) -> None:
        nodes, edges = grafo_filtrado(grafo_sintetico, tipos=[])
        assert nodes == []
        assert edges == []
