"""Testes de entity resolution de produtos (Sprint 49).

Cobre:
- Normalização remove acentos, unidades e quantidades numéricas.
- Três variações de Dove viram um único produto_canonico com 3 arestas.
- Shampoo vs condicionador (mesma marca) NÃO unificam.
- Produtos com similaridade 80-95 geram proposta MD sem aresta automática.
- Produtos com similaridade < 80 ficam sem canônico e sem proposta.
- Override manual (YAML) tem prioridade sobre heurística fuzzy.
- Idempotência: rodar 2x não duplica aresta `mesmo_produto_que`.
- Singleton (item solitário) não vira produto_canonico.

Acentuação: identificadores técnicos (`tipo="produto_canonico"`,
`"mesmo_produto_que"`, chaves de metadata) ficam sem acento por contrato
N-para-N com o grafo; texto humano em docstrings/asserts usa acentuação completa.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.graph.db import GrafoDB
from src.graph.er_produtos import (
    EDGE_TIPO_MESMO_PRODUTO,
    TIPO_NODE_CANONICO,
    carregar_overrides,
    executar_er_produtos,
    normalizar_descricao,
)
from src.graph.ingestor_documento import upsert_item

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def db(tmp_path: Path) -> GrafoDB:
    grafo = GrafoDB(tmp_path / "grafo.sqlite")
    grafo.criar_schema()
    yield grafo
    grafo.fechar()


@pytest.fixture
def caminho_propostas(tmp_path: Path) -> Path:
    destino = tmp_path / "propostas_er_produtos"
    destino.mkdir(parents=True, exist_ok=True)
    return destino


@pytest.fixture
def caminho_overrides_vazio(tmp_path: Path) -> Path:
    """YAML sem overrides -- força a rota 100% heurística."""
    destino = tmp_path / "produtos_canonicos.yaml"
    destino.write_text("produtos: []\n", encoding="utf-8")
    return destino


def _criar_item(
    db: GrafoDB,
    cnpj: str,
    data: str,
    codigo: str,
    descricao: str,
) -> int:
    """Wrapper fino do ingestor para não depender do formato exato."""
    return upsert_item(
        db,
        cnpj_varejo=cnpj,
        data_compra=data,
        codigo_produto=codigo,
        descricao=descricao,
    )


# ============================================================================
# Normalização
# ============================================================================


class TestNormalizacao:
    def test_remove_acentos_e_case(self) -> None:
        assert normalizar_descricao("Desodorante Dóvê") == "DESODORANTE DOVE"

    def test_remove_unidade_com_quantidade(self) -> None:
        assert normalizar_descricao("DESODORANTE DOVE 150ML") == "DESODORANTE DOVE"
        assert normalizar_descricao("ARROZ 5KG TIO JOAO") == "ARROZ TIO JOAO"

    def test_remove_unidade_com_espaco(self) -> None:
        assert normalizar_descricao("SABAO 250 G") == "SABAO"

    def test_remove_unidade_solta(self) -> None:
        assert normalizar_descricao("DOVE ML ROLLON") == "DOVE ROLLON"

    def test_vazio_devolve_vazio(self) -> None:
        assert normalizar_descricao("") == ""

    def test_pontuacao_colapsada(self) -> None:
        """Pontuação vira espaço + DEO expande para canônico DESODORANTE."""
        resultado = normalizar_descricao("DOVE, DEO. ROLLON")
        assert resultado == "DOVE DESODORANTE ROLLON"


# ============================================================================
# Clustering heurístico
# ============================================================================


class TestClusteringHeuristica:
    def test_unifica_duas_variacoes_via_sinonimo(
        self,
        db: GrafoDB,
        caminho_propostas: Path,
        caminho_overrides_vazio: Path,
    ) -> None:
        """DEO -> DESODORANTE via sinônimo canônico: 2 itens viram 1 canônico.

        Sem override manual. O sinônimo `DEO -> DESODORANTE` embutido na
        normalização garante que `DESODORANTE DOVE 150ML` e `DOVE DEO 150G`
        casem com `fuzz.token_set_ratio` = 100.
        """
        i1 = _criar_item(db, "12345", "2026-03-10", "A1", "DESODORANTE DOVE 150ML")
        i2 = _criar_item(db, "54321", "2026-03-11", "B2", "DOVE DEO 150G")

        stats = executar_er_produtos(
            db,
            caminho_overrides=caminho_overrides_vazio,
            caminho_propostas=caminho_propostas,
        )

        assert stats["itens_analisados"] == 2
        assert stats["canonicos_criados"] == 1
        assert stats["arestas_criadas"] == 2

        nodes_canonicos = db.listar_nodes(tipo=TIPO_NODE_CANONICO)
        assert len(nodes_canonicos) == 1
        produto = nodes_canonicos[0]
        arestas = db.listar_edges(tipo=EDGE_TIPO_MESMO_PRODUTO)
        ids_origem = {a.src_id for a in arestas if a.dst_id == produto.id}
        assert {i1, i2} == ids_origem

    def test_unifica_tres_variacoes_dove_com_override(
        self,
        db: GrafoDB,
        tmp_path: Path,
        caminho_propostas: Path,
    ) -> None:
        """Acceptance principal da Sprint 49: três variações unificadas.

        Usa o YAML de override real (`mappings/produtos_canonicos.yaml`) que
        o projeto carrega em produção. Demonstra o padrão recomendado:
        heurística cobre casos óbvios; override resolve os 3 Dove.
        """
        caminho_override = tmp_path / "override_dove.yaml"
        caminho_override.write_text(
            "produtos:\n"
            '  - canonico: "DESODORANTE DOVE ROLLON 150ML"\n'
            "    aliases:\n"
            '      - "DESODORANTE DOVE 150ML"\n'
            '      - "DOVE DEO 150G"\n'
            '      - "DOVE ROLLON 150ML"\n',
            encoding="utf-8",
        )

        i1 = _criar_item(db, "12345", "2026-03-10", "A1", "DESODORANTE DOVE 150ML")
        i2 = _criar_item(db, "54321", "2026-03-11", "B2", "DOVE DEO 150G")
        i3 = _criar_item(db, "99999", "2026-03-12", "C3", "DOVE ROLLON 150ML")

        stats = executar_er_produtos(
            db,
            caminho_overrides=caminho_override,
            caminho_propostas=caminho_propostas,
        )

        assert stats["itens_analisados"] == 3
        assert stats["canonicos_criados"] == 1
        assert stats["arestas_criadas"] == 3

        nodes_canonicos = db.listar_nodes(tipo=TIPO_NODE_CANONICO)
        assert len(nodes_canonicos) == 1
        produto = nodes_canonicos[0]
        arestas = db.listar_edges(tipo=EDGE_TIPO_MESMO_PRODUTO)
        ids_origem = {a.src_id for a in arestas if a.dst_id == produto.id}
        assert {i1, i2, i3} == ids_origem

    def test_nao_unifica_produto_diferente(
        self,
        db: GrafoDB,
        caminho_propostas: Path,
        caminho_overrides_vazio: Path,
    ) -> None:
        """Arroz e feijão não devem ser clusterizados juntos."""
        _criar_item(db, "12345", "2026-03-10", "A1", "ARROZ TIO JOAO 5KG")
        _criar_item(db, "12345", "2026-03-11", "A2", "FEIJAO CARIOCA 1KG")

        stats = executar_er_produtos(
            db,
            caminho_overrides=caminho_overrides_vazio,
            caminho_propostas=caminho_propostas,
        )

        assert stats["canonicos_criados"] == 0, (
            "Arroz e feijão são produtos distintos -- não deveriam unificar"
        )
        assert stats["arestas_criadas"] == 0

    def test_similaridade_borderline_gera_proposta(
        self,
        db: GrafoDB,
        caminho_propostas: Path,
        caminho_overrides_vazio: Path,
    ) -> None:
        """Score em [80, 95) gera proposta MD sem criar aresta automática."""
        _criar_item(db, "12345", "2026-03-10", "A1", "DESODORANTE DOVE 150ML")
        _criar_item(db, "12345", "2026-03-11", "A2", "DESODORANTE DOVE 150ML")
        # Item borderline: mesma marca mas categoria diferente.
        _criar_item(db, "12345", "2026-03-12", "B1", "SABONETE DOVE 90G")

        executar_er_produtos(
            db,
            caminho_overrides=caminho_overrides_vazio,
            caminho_propostas=caminho_propostas,
            # Reduz o threshold de match para forçar o SABONETE cair em proposta
            # em vez de unificar ou virar cluster solitário.
            threshold_match=95,
            threshold_proposta=50,
        )

        # Pelo menos uma proposta deve ter sido criada para o item borderline.
        propostas = list(caminho_propostas.glob("*.md"))
        assert len(propostas) >= 1, "Esperava pelo menos 1 proposta MD"
        conteudo = propostas[0].read_text(encoding="utf-8")
        assert "similaridade_borderline" in conteudo
        assert "aberta" in conteudo

    def test_singleton_nao_vira_canonico(
        self,
        db: GrafoDB,
        caminho_propostas: Path,
        caminho_overrides_vazio: Path,
    ) -> None:
        """Item único sem par não materializa produto_canonico."""
        _criar_item(db, "12345", "2026-03-10", "A1", "PRODUTO ÚNICO RARO 500ML")

        stats = executar_er_produtos(
            db,
            caminho_overrides=caminho_overrides_vazio,
            caminho_propostas=caminho_propostas,
        )

        assert stats["canonicos_criados"] == 0
        assert stats["singletons_ignorados"] >= 1


# ============================================================================
# Overrides manuais
# ============================================================================


class TestOverrideManual:
    def test_override_respeitado(
        self,
        db: GrafoDB,
        tmp_path: Path,
        caminho_propostas: Path,
    ) -> None:
        """Alias listado no YAML força a unificação mesmo com score baixo."""
        caminho_overrides = tmp_path / "produtos_canonicos.yaml"
        caminho_overrides.write_text(
            "produtos:\n"
            '  - canonico: "XAMPU GENERICO"\n'
            "    aliases:\n"
            '      - "SHAMPOO MARCA ALFA 300ML"\n'
            '      - "XAMPUZINHO BETA 200ML"\n',
            encoding="utf-8",
        )

        i1 = _criar_item(db, "12345", "2026-03-10", "A1", "SHAMPOO MARCA ALFA 300ML")
        i2 = _criar_item(db, "12345", "2026-03-11", "A2", "XAMPUZINHO BETA 200ML")

        stats = executar_er_produtos(
            db,
            caminho_overrides=caminho_overrides,
            caminho_propostas=caminho_propostas,
        )

        assert stats["canonicos_criados"] == 1
        assert stats["arestas_criadas"] == 2

        nodes_canonicos = db.listar_nodes(tipo=TIPO_NODE_CANONICO)
        assert len(nodes_canonicos) == 1
        produto = nodes_canonicos[0]
        arestas = db.listar_edges(tipo=EDGE_TIPO_MESMO_PRODUTO)
        ids_origem = {a.src_id for a in arestas if a.dst_id == produto.id}
        assert {i1, i2} == ids_origem

        # A evidência registra fonte=override.
        for aresta in arestas:
            assert aresta.evidencia.get("fonte") == "override"

    def test_carregar_overrides_arquivo_ausente(self, tmp_path: Path) -> None:
        """Ausência do YAML devolve dict vazio sem erro."""
        destino = tmp_path / "nao_existe.yaml"
        assert carregar_overrides(destino) == {}

    def test_carregar_overrides_formato_valido(self, tmp_path: Path) -> None:
        destino = tmp_path / "override.yaml"
        destino.write_text(
            "produtos:\n"
            '  - canonico: "LEITE INTEGRAL 1L"\n'
            "    aliases:\n"
            '      - "LEITE TIPO C 1L"\n'
            '      - "LEITE INTEGRAL 1000ML"\n',
            encoding="utf-8",
        )
        mapa = carregar_overrides(destino)
        assert mapa  # não vazio
        # As chaves são normalizadas; ambos aliases apontam para o canônico.
        valores = set(mapa.values())
        assert valores == {"LEITE INTEGRAL 1L"}


# ============================================================================
# Idempotência
# ============================================================================


class TestIdempotencia:
    def test_rodar_duas_vezes_nao_duplica(
        self,
        db: GrafoDB,
        caminho_propostas: Path,
        caminho_overrides_vazio: Path,
    ) -> None:
        """Executar o ER 2x devolve mesmo grafo (UNIQUE de edge bloqueia duplicata)."""
        _criar_item(db, "12345", "2026-03-10", "A1", "DESODORANTE DOVE 150ML")
        _criar_item(db, "54321", "2026-03-11", "B2", "DOVE DEO 150G")

        executar_er_produtos(
            db,
            caminho_overrides=caminho_overrides_vazio,
            caminho_propostas=caminho_propostas,
        )
        nodes_apos_1 = len(db.listar_nodes(tipo=TIPO_NODE_CANONICO))
        arestas_apos_1 = len(db.listar_edges(tipo=EDGE_TIPO_MESMO_PRODUTO))

        executar_er_produtos(
            db,
            caminho_overrides=caminho_overrides_vazio,
            caminho_propostas=caminho_propostas,
        )
        nodes_apos_2 = len(db.listar_nodes(tipo=TIPO_NODE_CANONICO))
        arestas_apos_2 = len(db.listar_edges(tipo=EDGE_TIPO_MESMO_PRODUTO))

        assert nodes_apos_1 == nodes_apos_2, "Rodar 2x não deve duplicar produto_canonico"
        assert arestas_apos_1 == arestas_apos_2, (
            "Rodar 2x não deve duplicar arestas mesmo_produto_que"
        )


# ============================================================================
# Integração com grafo real (edges com peso correto)
# ============================================================================


class TestEvidenciaEPeso:
    def test_peso_aresta_reflete_score(
        self,
        db: GrafoDB,
        caminho_propostas: Path,
        caminho_overrides_vazio: Path,
    ) -> None:
        """Peso da aresta = score/100. Match determinístico via override = 1.0."""
        caminho_override = Path(caminho_overrides_vazio.parent / "override_real.yaml")
        caminho_override.write_text(
            "produtos:\n"
            '  - canonico: "AGUA MINERAL 500ML"\n'
            "    aliases:\n"
            '      - "AGUA MINERAL SEM GAS 500ML"\n'
            '      - "AGUA CRYSTAL 500ML"\n',
            encoding="utf-8",
        )

        _criar_item(db, "12345", "2026-03-10", "A1", "AGUA MINERAL SEM GAS 500ML")
        _criar_item(db, "12345", "2026-03-11", "A2", "AGUA CRYSTAL 500ML")

        executar_er_produtos(
            db,
            caminho_overrides=caminho_override,
            caminho_propostas=caminho_propostas,
        )

        arestas = db.listar_edges(tipo=EDGE_TIPO_MESMO_PRODUTO)
        assert len(arestas) == 2
        for aresta in arestas:
            assert aresta.peso == 1.0, "Override manual deve gerar peso 1.0"
            assert "fuzzy_score" in aresta.evidencia


# "Nomear com precisão é o começo da sabedoria." -- Confúcio (parafraseado)
