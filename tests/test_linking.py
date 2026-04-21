"""Testes do motor de linking documento->transação bancária (Sprint 48).

Cobre:
- Match CNPJ+data+valor exato gera aresta `documento_de` com evidência JSON
- Ausência de match não cria aresta
- Múltiplos candidatos próximos viram proposta de conflito (não linka)
- Score baixo vira proposta de baixa_confianca (não linka)
- Idempotência: rodar 2x não duplica aresta
- Registro em pipeline: passo 12 aciona linking quando grafo existe

Observação sobre acentuação: identificadores técnicos que participam de
contrato N-para-N com o grafo (chaves de dict, nomes canônicos como
`"transacao"`, `"documento_de"`) ficam sem acento por consistência com
`src/graph/ingestor_documento.py`. Texto humano em docstrings e mensagens
usa acentuação completa.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from src.graph.db import GrafoDB
from src.graph.ingestor_documento import ingerir_documento_fiscal
from src.graph.linking import (
    candidatas_para_documento,
    carregar_config,
    linkar_documentos_a_transacoes,
)

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
    destino = tmp_path / "propostas_linking"
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def _criar_transacao(
    db: GrafoDB,
    *,
    nome: str,
    data_iso: str,
    valor: float,
    local: str,
    banco: str = "Itau",
    cnpj_fornecedor: str | None = None,
) -> int:
    """Cria um node transação e, opcionalmente, fornecedor + contraparte."""
    metadata = {
        "data": data_iso,
        "valor": valor,
        "local": local,
        "banco": banco,
        "tipo": "Despesa",
        "forma_pagamento": "Credito",
    }
    tid = db.upsert_node("transacao", nome, metadata=metadata)
    if cnpj_fornecedor:
        fid = db.upsert_node(
            "fornecedor",
            cnpj_fornecedor,
            metadata={"cnpj": cnpj_fornecedor, "razao_social": local},
            aliases=[local],
        )
        db.adicionar_edge(tid, fid, "contraparte")
    return tid


def _ingerir_nfce(
    db: GrafoDB,
    *,
    chave_44: str,
    cnpj_emitente: str,
    data_emissao: str,
    total: float,
    razao_social: str = "LOJA EXEMPLO LTDA",
    tipo_documento: str = "nfce_modelo_65",
) -> int:
    """Helper para ingerir um NFC-e minimamente válido no grafo."""
    doc = {
        "chave_44": chave_44,
        "cnpj_emitente": cnpj_emitente,
        "data_emissao": data_emissao,
        "tipo_documento": tipo_documento,
        "total": total,
        "razao_social": razao_social,
    }
    itens = [
        {
            "codigo": "001",
            "descricao": "PRODUTO GENERICO",
            "qtde": 1,
            "valor_unit": total,
            "valor_total": total,
        }
    ]
    return ingerir_documento_fiscal(db, doc, itens)


# ============================================================================
# Config
# ============================================================================


def test_carregar_config_default_quando_arquivo_ausente(tmp_path: Path):
    inexistente = tmp_path / "nao_existe.yaml"
    config = carregar_config(inexistente)
    assert "default" in config
    assert config["default"]["janela_dias"] >= 0
    assert config["default"]["confidence_minimo"] >= 0.0
    assert "margem_empate" in config


def test_carregar_config_oficial_tem_tipos_fiscais():
    config = carregar_config()
    assert "nfce_modelo_65" in config["tipos"]
    assert "danfe_nfe" in config["tipos"]
    assert "cupom_fiscal" in config["tipos"]
    assert config["tipos"]["nfce_modelo_65"]["confidence_minimo"] >= 0.8


# ============================================================================
# Match basico
# ============================================================================


def test_link_danfe_exato_cnpj_data_valor(db: GrafoDB, caminho_propostas: Path):
    """DANFE com CNPJ X, data Y, total Z bate exato com transação mesma data/valor."""
    cnpj = "12.345.678/0001-90"
    data = "2026-04-10"
    total = 1234.56
    chave = "52260412345678000190550010000000001123456789"

    _ingerir_nfce(
        db,
        chave_44=chave,
        cnpj_emitente=cnpj,
        data_emissao=data,
        total=total,
        razao_social="FORNECEDOR EXATO LTDA",
        tipo_documento="danfe_nfe",
    )
    tid = _criar_transacao(
        db,
        nome="t-exata",
        data_iso=data,
        valor=total,
        local="FORNECEDOR EXATO LTDA",
        cnpj_fornecedor=cnpj,
    )

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)
    assert stats["linkados"] == 1
    assert stats["sem_candidato"] == 0
    assert stats["conflitos"] == 0

    edges_doc_de = db.listar_edges(tipo="documento_de")
    assert len(edges_doc_de) == 1
    aresta = edges_doc_de[0]
    assert aresta.dst_id == tid
    evid = aresta.evidencia
    assert evid["diff_dias"] == 0
    assert evid["diff_valor"] == 0.0
    assert evid["heuristica"] == "cnpj_data_valor_exato"
    assert evid["confidence"] >= 0.9
    assert evid["cnpj_bate"] is True


def test_link_nfce_americanas_sintetico(db: GrafoDB, caminho_propostas: Path):
    """Simula o cenário real de produção: NFC-e Americanas em janela 1 dia."""
    cnpj = "00.776.574/0006-60"  # Americanas SA (formato canônico)
    data_nf = "2026-03-25"
    data_trans = "2026-03-26"  # compra no cartão entra no dia seguinte
    total = 89.90
    chave = "35260300776574000660650010000000001234567890"

    _ingerir_nfce(
        db,
        chave_44=chave,
        cnpj_emitente=cnpj,
        data_emissao=data_nf,
        total=total,
        razao_social="AMERICANAS SA",
    )
    _criar_transacao(
        db,
        nome="t-americanas",
        data_iso=data_trans,
        valor=total,
        local="AMERICANAS",
        cnpj_fornecedor=cnpj,
    )

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)
    assert stats["linkados"] == 1
    aresta = db.listar_edges(tipo="documento_de")[0]
    assert aresta.evidencia["diff_dias"] == 1
    assert aresta.evidencia["cnpj_bate"] is True
    assert aresta.evidencia["confidence"] >= 0.85


def test_sem_match_nao_cria_edge(db: GrafoDB, caminho_propostas: Path):
    """Documento sem transação compatível não cria aresta nem proposta."""
    _ingerir_nfce(
        db,
        chave_44="52260499999999000199550010000000009999999999",
        cnpj_emitente="99.999.999/0001-99",
        data_emissao="2026-04-10",
        total=500.00,
    )
    # transação existe mas valor/data não batem
    _criar_transacao(
        db,
        nome="t-outra",
        data_iso="2026-02-01",
        valor=10.00,
        local="OUTRO LUGAR",
    )

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)
    assert stats["sem_candidato"] == 1
    assert stats["linkados"] == 0
    assert db.listar_edges(tipo="documento_de") == []
    # Sem candidato não gera proposta.
    assert list(caminho_propostas.glob("*.md")) == []


# ============================================================================
# Conflitos e baixa confiança
# ============================================================================


def test_multiplos_candidatos_cria_proposta_conflito(db: GrafoDB, caminho_propostas: Path):
    """Duas transações idênticas na mesma data e valor -> proposta, sem linkar."""
    cnpj = "11.111.111/0001-11"
    data = "2026-04-15"
    total = 200.00
    chave = "52260411111111000111550010000000001234509876"

    _ingerir_nfce(
        db,
        chave_44=chave,
        cnpj_emitente=cnpj,
        data_emissao=data,
        total=total,
    )
    # DUAS transações indistinguíveis: mesmo valor, mesma data, mesmo CNPJ
    _criar_transacao(
        db,
        nome="t-dup-1",
        data_iso=data,
        valor=total,
        local="LOJA X",
        cnpj_fornecedor=cnpj,
    )
    _criar_transacao(
        db,
        nome="t-dup-2",
        data_iso=data,
        valor=total,
        local="LOJA X",
        cnpj_fornecedor=cnpj,
    )

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)
    assert stats["conflitos"] == 1
    assert stats["linkados"] == 0
    assert db.listar_edges(tipo="documento_de") == []
    propostas = list(caminho_propostas.glob("*_conflito.md"))
    assert len(propostas) == 1
    texto = propostas[0].read_text(encoding="utf-8")
    assert "Conflito" in texto
    # A tabela de candidatas cita os transacao_ids das 2 duplicadas.  # noqa: accent
    trans_ids = [nd.id for nd in db.listar_nodes(tipo="transacao")]
    assert len(trans_ids) == 2
    for tid in trans_ids:
        assert f"| {tid} |" in texto, f"transação {tid} ausente da proposta"
    assert "cnpj_bate" in texto


def test_falso_positivo_rejeitado_por_threshold(db: GrafoDB, caminho_propostas: Path):
    """DANFE com data deslocada 3 dias e sem CNPJ batendo -> baixa confiança."""
    cnpj_doc = "22.222.222/0001-22"
    cnpj_outro = "33.333.333/0001-33"
    _ingerir_nfce(
        db,
        chave_44="52260422222222000122550010000000001111111111",
        cnpj_emitente=cnpj_doc,
        data_emissao="2026-04-10",
        total=1000.00,
        tipo_documento="danfe_nfe",
    )
    # Transação 3 dias depois, com fornecedor de CNPJ diferente.
    _criar_transacao(
        db,
        nome="t-diferente",
        data_iso="2026-04-13",
        valor=1000.00,
        local="OUTRO FORNECEDOR",
        cnpj_fornecedor=cnpj_outro,
    )

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)
    # Score: 1.0 - 0.3 (3 dias) - 0.0 (valor) + 0.0 (cnpj não bate) = 0.70
    # confidence_minimo danfe_nfe = 0.80 -> proposta de baixa_confianca
    assert stats["baixa_confianca"] == 1
    assert stats["linkados"] == 0
    propostas = list(caminho_propostas.glob("*_baixa_confianca.md"))
    assert len(propostas) == 1
    texto = propostas[0].read_text(encoding="utf-8")
    assert "Baixa" in texto or "baixa" in texto


# ============================================================================
# Estrutura da evidência
# ============================================================================


def test_edge_tem_evidencia_json_completa(db: GrafoDB, caminho_propostas: Path):
    """Aresta `documento_de` criada deve conter todos os campos obrigatórios
    da evidência em formato JSON.
    """
    cnpj = "44.444.444/0001-44"
    data = "2026-04-05"
    total = 75.00
    _ingerir_nfce(
        db,
        chave_44="52260444444444000144650010000000002222222222",
        cnpj_emitente=cnpj,
        data_emissao=data,
        total=total,
    )
    _criar_transacao(
        db,
        nome="t-evid",
        data_iso=data,
        valor=total,
        local="LOJA Y",
        cnpj_fornecedor=cnpj,
    )

    linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)

    aresta = db.listar_edges(tipo="documento_de")[0]
    # evidência desserializada (dict)
    evid = aresta.evidencia
    for chave_evid in (
        "diff_dias",
        "diff_valor",
        "diff_valor_pct",
        "heuristica",
        "confidence",
    ):
        assert chave_evid in evid, f"campo {chave_evid} ausente em evidência"

    # confere que também é JSON-serializável (round-trip)
    serializado = json.dumps(evid, ensure_ascii=False, sort_keys=True, default=str)
    restaurado = json.loads(serializado)
    assert restaurado["diff_dias"] == evid["diff_dias"]
    assert float(restaurado["confidence"]) == float(evid["confidence"])


# ============================================================================
# Idempotência
# ============================================================================


def test_linkagem_idempotente(db: GrafoDB, caminho_propostas: Path):
    """Rodar linking 2x não duplica a aresta `documento_de`."""
    cnpj = "55.555.555/0001-55"
    data = "2026-04-20"
    total = 42.00
    _ingerir_nfce(
        db,
        chave_44="52260455555555000155650010000000003333333333",
        cnpj_emitente=cnpj,
        data_emissao=data,
        total=total,
    )
    _criar_transacao(
        db,
        nome="t-idem",
        data_iso=data,
        valor=total,
        local="LOJA Z",
        cnpj_fornecedor=cnpj,
    )

    stats1 = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)
    assert stats1["linkados"] == 1
    arestas_depois_1 = db.listar_edges(tipo="documento_de")
    assert len(arestas_depois_1) == 1

    stats2 = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)
    # Segunda rodada: aresta já existe (INSERT OR IGNORE), não deve haver mais
    # aresta criada -- rastreamento pelo count total do grafo.
    arestas_depois_2 = db.listar_edges(tipo="documento_de")
    assert len(arestas_depois_2) == 1
    # `linkados` da segunda rodada pode ser 1 (chamamos adicionar_edge de novo),
    # mas o UNIQUE(src,dst,tipo) do schema garante que não duplica.
    assert stats2["linkados"] in (0, 1)


def test_transacao_com_timestamp_e_aceita(db: GrafoDB, caminho_propostas: Path):
    """Transações reais do grafo vêm com `data="YYYY-MM-DD HH:MM:SS"`.

    O parser de data deve truncar em [:10] e casar como se fosse ISO puro.
    Cenário derivado do grafo de produção (migracao_inicial grava timestamps).
    """
    cnpj = "88.888.888/0001-88"
    data_doc = "2026-04-10"
    total = 123.45
    _ingerir_nfce(
        db,
        chave_44="52260488888888000188650010000000006666666666",
        cnpj_emitente=cnpj,
        data_emissao=data_doc,
        total=total,
    )
    # Timestamp igual ao emitido pelo migracao_inicial._str_normalizada
    db.upsert_node(
        "transacao",
        "hash-timestamp",
        metadata={
            "data": "2026-04-10 00:00:00",
            "valor": total,
            "local": "LOJA COM TIMESTAMP",
            "banco": "C6",
        },
    )
    tid_f = db.upsert_node(
        "fornecedor",
        cnpj,
        metadata={"cnpj": cnpj, "razao_social": "LOJA TS"},
    )
    tid_trans = db.listar_nodes(tipo="transacao")[0].id
    db.adicionar_edge(tid_trans, tid_f, "contraparte")

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)
    assert stats["linkados"] == 1
    aresta = db.listar_edges(tipo="documento_de")[0]
    assert aresta.evidencia["diff_dias"] == 0
    assert aresta.evidencia["cnpj_bate"] is True


def test_candidatas_ordenadas_por_score(db: GrafoDB):
    """`candidatas_para_documento` retorna a lista em ordem descrescente."""
    cnpj = "66.666.666/0001-66"
    data = "2026-04-01"
    total = 300.00
    _ingerir_nfce(
        db,
        chave_44="52260466666666000166650010000000004444444444",
        cnpj_emitente=cnpj,
        data_emissao=data,
        total=total,
    )
    # Candidata A: exata (mesmo dia, mesmo valor, mesmo CNPJ) -> score alto
    _criar_transacao(
        db,
        nome="t-A",
        data_iso=data,
        valor=total,
        local="LOJA EXATA",
        cnpj_fornecedor=cnpj,
    )
    # Candidata B: 1 dia depois, valor idêntico, sem CNPJ -> score mais baixo
    _criar_transacao(
        db,
        nome="t-B",
        data_iso="2026-04-02",
        valor=total,
        local="OUTRO",
    )

    # Busca o doc
    docs = db.listar_nodes(tipo="documento")
    assert len(docs) == 1
    candidatas = candidatas_para_documento(db, docs[0])
    assert len(candidatas) == 2
    scores = [c[1]["confidence"] for c in candidatas]
    assert scores[0] >= scores[1]


# ============================================================================
# Integração com pipeline
# ============================================================================


def test_registro_em_pipeline_funcao_existe():
    """Função `_executar_linking_documentos` existe e é chamável em pipeline."""
    from src import pipeline

    assert hasattr(pipeline, "_executar_linking_documentos")
    # Não deve quebrar quando o grafo não existe (lógica defensiva).
    # Como o grafo padrão *pode* existir em ambiente real, só garantimos que a
    # função roda sem exception -- não afirmamos sobre side-effects.
    try:
        pipeline._executar_linking_documentos()
    except Exception as erro:
        pytest.fail(f"pipeline._executar_linking_documentos levantou: {erro}")


def test_respeita_linking_humano_aprovado(db: GrafoDB, caminho_propostas: Path):
    """Se aresta `documento_de` já existe com `aprovador`, não mexer."""
    cnpj = "77.777.777/0001-77"
    data = "2026-03-15"
    total = 500.00

    doc_id = _ingerir_nfce(
        db,
        chave_44="52260377777777000177650010000000005555555555",
        cnpj_emitente=cnpj,
        data_emissao=data,
        total=total,
    )
    # Cria transação mas liga manualmente com evidencia["aprovador"]
    tid = _criar_transacao(
        db,
        nome="t-aprovada",
        data_iso=data,
        valor=total,
        local="LOJA AP",
        cnpj_fornecedor=cnpj,
    )
    db.adicionar_edge(
        doc_id,
        tid,
        "documento_de",
        peso=1.0,
        evidencia={
            "aprovador": "humano:andre",
            "data_aprovacao": date.today().isoformat(),
            "heuristica": "manual",
        },
    )

    # Cria uma OUTRA transação com score melhor no automático
    _criar_transacao(
        db,
        nome="t-tentador",
        data_iso=data,
        valor=total,
        local="LOJA AP",
        cnpj_fornecedor=cnpj,
    )

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)
    assert stats["ja_linkados"] == 1
    # Continua sendo apenas 1 aresta documento_de (a humana)
    arestas = db.listar_edges(tipo="documento_de")
    assert len(arestas) == 1
    assert arestas[0].evidencia.get("aprovador") == "humano:andre"


# "Testar é recusar o benefício da dúvida a si mesmo." -- princípio da verificação
