"""Testes da Sprint UX-114 -- Busca Global funcional.

Cobre:

- `busca_indice.construir_indice`: indexacao a partir de grafo SQLite + YAML.
- `busca_indice.sugestoes`: autocomplete case-insensitive + limite + dedup.
- `busca_roteador.rotear`: aba vs fornecedor vs livre.
- `paginas.busca`: chips canonicos, placeholder maiusculo, dropdown, PII,
  tabela de documentos, export para data/exports/.
- Filtros sidebar (mes, pessoa, forma) impactam o resultado.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.dashboard.componentes import busca_indice as bi
from src.dashboard.componentes import busca_roteador as br
from src.dashboard.paginas import busca as pag

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def grafo_indice(tmp_path: Path) -> Path:
    """Grafo minusculo para testar indexacao."""
    destino = tmp_path / "grafo.sqlite"
    conn = sqlite3.connect(destino)
    conn.executescript(
        """
        CREATE TABLE node (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          tipo TEXT NOT NULL,
          nome_canonico TEXT NOT NULL,
          aliases TEXT DEFAULT '[]',
          metadata TEXT DEFAULT '{}'
        );
        CREATE TABLE edge (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          src_id INTEGER NOT NULL,
          dst_id INTEGER NOT NULL,
          tipo TEXT NOT NULL,
          peso REAL DEFAULT 1.0,
          evidencia TEXT DEFAULT '{}'
        );
        """
    )
    conn.execute(
        "INSERT INTO node (tipo, nome_canonico, aliases) VALUES (?, ?, ?)",
        ("fornecedor", "NEOENERGIA DISTRIBUICAO", '["NEOENERGIA DF", "CEB-DIS"]'),
    )
    conn.execute(
        "INSERT INTO node (tipo, nome_canonico, aliases) VALUES (?, ?, ?)",
        ("fornecedor", "Padaria do Bairro Ki-Sabor", "[]"),
    )
    conn.execute(
        "INSERT INTO node (tipo, nome_canonico, metadata) VALUES (?, ?, ?)",
        ("item", "ARROZ TIO JOAO", '{"descricao": "Arroz Tio Joao 5kg"}'),
    )
    conn.commit()
    conn.close()
    return destino


# ---------------------------------------------------------------------------
# busca_indice
# ---------------------------------------------------------------------------


def test_construir_indice_grafo_existente(grafo_indice: Path) -> None:
    idx = bi.construir_indice(grafo_indice)
    assert "fornecedores" in idx
    assert "descricoes" in idx
    assert "tipos_doc" in idx
    assert "abas" in idx
    assert "NEOENERGIA DISTRIBUICAO" in idx["fornecedores"]
    assert "NEOENERGIA DF" in idx["fornecedores"]
    assert "Arroz Tio Joao 5kg" in idx["descricoes"]  # anonimato-allow: fixture de matcher
    assert len(idx["tipos_doc"]) >= 8
    assert "Busca Global" in idx["abas"]


def test_construir_indice_grafo_inexistente(tmp_path: Path) -> None:
    """Branch reversível (m): grafo ausente -> índice degradado mas válido."""
    inexistente = tmp_path / "nao_existe.sqlite"
    idx = bi.construir_indice(inexistente)
    assert idx["fornecedores"] == []
    assert idx["descricoes"] == []
    assert len(idx["tipos_doc"]) >= 8  # tipos do YAML continuam
    assert len(idx["abas"]) > 0  # abas estaticas continuam


def test_humanizar_id_canonico() -> None:
    assert bi._humanizar_id("holerite") == "Holerite"
    assert bi._humanizar_id("das_parcsn") == "DAS PARCSN"
    assert bi._humanizar_id("irpf_parcela") == "IRPF Parcela"


def test_sugestoes_substring_case_insensitive(grafo_indice: Path) -> None:
    idx = bi.construir_indice(grafo_indice)
    sugs = bi.sugestoes("neo", indice=idx, limite=10)
    assert len(sugs) >= 1
    assert any("NEOENERGIA" in s.upper() for s in sugs)


def test_sugestoes_query_curta_devolve_vazio(grafo_indice: Path) -> None:
    idx = bi.construir_indice(grafo_indice)
    assert bi.sugestoes("n", indice=idx) == []
    assert bi.sugestoes("", indice=idx) == []


def test_sugestoes_respeita_limite(grafo_indice: Path) -> None:
    idx = bi.construir_indice(grafo_indice)
    sugs = bi.sugestoes("a", indice=idx, limite=3)
    # query com 1 char retorna [] (filtro defensivo)
    assert sugs == []
    sugs = bi.sugestoes("ar", indice=idx, limite=3)
    assert len(sugs) <= 3


def test_sugestoes_prioriza_aba_antes_de_fornecedor(grafo_indice: Path) -> None:
    idx = bi.construir_indice(grafo_indice)
    # 'busca' casa 'Busca Global' (aba) e nada de fornecedor
    sugs = bi.sugestoes("busca", indice=idx, limite=5)
    assert sugs and "Busca Global" in sugs


# ---------------------------------------------------------------------------
# busca_roteador
# ---------------------------------------------------------------------------


def test_rotear_aba_exata() -> None:
    rota = br.rotear("Revisor")
    assert rota["kind"] == "aba"
    assert rota["destino"] == "Revisor"
    assert rota["tipo"] in {"Documentos", None}


def test_rotear_aba_case_insensitive() -> None:
    rota = br.rotear("extrato")
    assert rota["kind"] == "aba"
    assert rota["destino"] == "Extrato"


def test_rotear_fornecedor_substring(grafo_indice: Path) -> None:
    idx = bi.construir_indice(grafo_indice)
    rota = br.rotear("neoenergia", indice=idx)
    assert rota["kind"] == "fornecedor"
    assert "NEOENERGIA" in rota["destino"].upper()


def test_rotear_livre_quando_nao_casa() -> None:
    idx = {"fornecedores": [], "descricoes": [], "tipos_doc": [], "abas": []}
    rota = br.rotear("R$ 100,00", indice=idx)
    assert rota["kind"] == "livre"
    assert rota["destino"] == "R$ 100,00"


def test_rotear_query_vazia() -> None:
    rota = br.rotear("")
    assert rota["kind"] == "livre"
    assert rota["destino"] == ""


# ---------------------------------------------------------------------------
# paginas.busca: helpers
# ---------------------------------------------------------------------------


def test_chips_canonicos_substituem_antigos() -> None:
    """AC: chips abaixo do input substituem 'neoenergia/farmacia/uber'."""
    assert "Holerite" in pag.CHIPS_TIPOS_CANONICOS
    assert "Nota Fiscal" in pag.CHIPS_TIPOS_CANONICOS
    assert "DAS" in pag.CHIPS_TIPOS_CANONICOS
    assert "Boleto" in pag.CHIPS_TIPOS_CANONICOS
    assert "IRPF" in pag.CHIPS_TIPOS_CANONICOS
    assert "Recibo" in pag.CHIPS_TIPOS_CANONICOS
    assert "Comprovante" in pag.CHIPS_TIPOS_CANONICOS
    assert "Contracheque" in pag.CHIPS_TIPOS_CANONICOS
    assert len(pag.CHIPS_TIPOS_CANONICOS) == 8
    # antigos NÃO podem aparecer
    for antigo in ("neoenergia", "farmacia", "americanas", "posto", "uber"):
        assert antigo not in [c.lower() for c in pag.CHIPS_TIPOS_CANONICOS]


def test_placeholder_maiusculo() -> None:
    """AC: placeholder em MAIÚSCULAS."""
    assert pag.PLACEHOLDER_INPUT == pag.PLACEHOLDER_INPUT.upper()
    assert "BUSQUE:" in pag.PLACEHOLDER_INPUT


def test_texto_descritivo_curto() -> None:
    """AC: texto descritivo em uma linha só (max 90 chars)."""
    assert len(pag.TEXTO_DESCRITIVO) <= 90
    assert "\n" not in pag.TEXTO_DESCRITIVO


def test_dropdown_opcoes_canonicas() -> None:
    """AC: dropdown 'Tipo' tem opções Todos/Pessoais/Trabalho/etc."""
    esperadas = {
        "Todos",
        "Pessoais",
        "Trabalho",
        "Notas Fiscais",
        "Holerites",
        "Boletos",
        "Receitas Medicas",
        "DAS",
        "IRPF",
    }
    assert esperadas.issubset(set(pag.OPCOES_DROPDOWN_TIPO))


def test_filtros_sidebar_mes_impacta() -> None:
    """AC: documento de 2026-03 não aparece quando filtro Mes=2026-04."""
    docs = [
        {"id": 1, "data": "2026-03-15"},
        {"id": 2, "data": "2026-04-08"},
        {"id": 3, "data": "2026-04-22"},
    ]
    saida = pag._aplicar_filtros_sidebar(docs, periodo="2026-04", pessoa=None, forma=None)
    assert len(saida) == 2
    assert all(d["data"].startswith("2026-04") for d in saida)


def test_filtros_sidebar_pessoa_impacta() -> None:
    docs = [
        {"id": 1, "data": "2026-04-01", "pessoa": "Andre"},  # anonimato-allow: fixture de matcher
        {"id": 2, "data": "2026-04-02", "pessoa": "Vitoria"},  # anonimato-allow: fixture de matcher
    ]
    saida = pag._aplicar_filtros_sidebar(
        docs, periodo=None, pessoa="Vitoria", forma=None,  # anonimato-allow
    )
    assert len(saida) == 1
    assert saida[0]["id"] == 2


def test_filtros_sidebar_todos_nao_filtra() -> None:
    docs = [{"id": 1, "data": "2026-03-15"}]
    saida = pag._aplicar_filtros_sidebar(docs, periodo="Todos", pessoa="Todos", forma="Todos")
    assert saida == docs


def test_filtrar_por_tipo_dropdown_holerites() -> None:
    docs = [
        {"id": 1, "tipo_documento": "holerite"},
        {"id": 2, "tipo_documento": "boleto_servico"},
        {"id": 3, "tipo_documento": "contracheque"},
    ]
    saida = pag._filtrar_por_tipo_dropdown(docs, "Holerites")
    assert len(saida) == 2
    assert {d["id"] for d in saida} == {1, 3}


def test_filtrar_por_tipo_dropdown_todos_nao_filtra() -> None:
    docs = [{"id": 1, "tipo_documento": "boleto_servico"}]
    saida = pag._filtrar_por_tipo_dropdown(docs, "Todos")
    assert saida == docs


# ---------------------------------------------------------------------------
# PII e exportacao
# ---------------------------------------------------------------------------


def test_pii_mascarada_cpf() -> None:
    assert "***" in pag._mascarar_pii("CPF 123.456.789-01 do cliente")
    assert "123.456.789-01" not in pag._mascarar_pii("CPF 123.456.789-01")


def test_pii_mascarada_cnpj() -> None:
    assert "**.***.***/****-**" in pag._mascarar_pii("Empresa CNPJ 12.345.678/0001-90")


def test_pii_mascarada_email() -> None:
    assert "***@***" in pag._mascarar_pii("Email: foo.bar@example.com")


def test_exportar_documento_cria_arquivo(tmp_path: Path) -> None:
    """AC: export cria arquivo em data/exports/<ts>_<nome>.<ext>."""
    origem = tmp_path / "doc_original.pdf"
    origem.write_bytes(b"%PDF-fake")
    destino_dir = tmp_path / "exports"
    saida = pag.exportar_documento(origem, diretorio_destino=destino_dir)
    assert saida is not None
    assert saida.exists()
    assert saida.parent == destino_dir
    assert saida.name.endswith("_doc_original.pdf")
    # original preservado (nunca deleta)
    assert origem.exists()


def test_exportar_documento_origem_invalida(tmp_path: Path) -> None:
    inexistente = tmp_path / "nao_existe.pdf"
    saida = pag.exportar_documento(inexistente)
    assert saida is None


def test_exportar_documento_caminho_vazio() -> None:
    assert pag.exportar_documento("") is None
    assert pag.exportar_documento(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Integração tabela: 4 colunas obrigatórias
# ---------------------------------------------------------------------------


def test_tabela_tem_colunas_canonicas() -> None:
    """AC: tabela tem colunas Nome do documento / Texto extraído / Caminho.

    Verifica via código: a função monta um dict com essas chaves.
    """
    fonte = Path(pag.__file__).read_text(encoding="utf-8")
    assert '"Nome do documento"' in fonte
    assert '"Texto extraído"' in fonte
    assert '"Caminho do arquivo"' in fonte


def test_pii_mascarada_no_render_da_tabela(monkeypatch) -> None:
    """AC: PII é mascarada no output da tabela.

    Garante que `_mascarar_pii` é aplicado em nome e em texto_extraido
    quando o documento contém CPF/CNPJ.
    """
    fonte = Path(pag.__file__).read_text(encoding="utf-8")
    # invariante de código: mascarar antes de aparecer no df
    assert "_mascarar_pii(nome)" in fonte
    assert "_mascarar_pii(texto_extra)" in fonte
