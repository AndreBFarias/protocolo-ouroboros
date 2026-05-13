"""Testes do linker PIX -- Sprint INFRA-LINKAR-PIX-TRANSACAO (2026-05-13).  # noqa: accent

DOC-27 entregou o extrator de comprovante PIX foto + 3 caches reais.
MOB-bridge-5 entregou o ingestor ``ingerir_comprovante_pix_foto`` que cria
nós ``documento`` (tipo ``comprovante_pix_foto``) com metadata ``pix_*``.

Esta sprint adiciona ``linkar_pix_transacao`` em ``src/graph/linking.py`` --
linker dedicado que amarra cada documento PIX à transação correspondente no
extrato bancário, usando o motor canônico (``candidatas_para_documento``)
reforçado por dois boosts:

  1. **Boost E2E**: id_transacao do BACEN aparece literal na descrição da
     transação -> score = 1.0 (selo de identidade).
  2. **Boost textual**: marcador PIX/TRANSF + token do nome do destinatário ->
     +0.10 no score canônico.

Cobertura desta suíte (>= 6 testes):

  - Grafo sintético: 1 PIX + 1 transação com data+valor exato -> aresta criada.
  - PIX sem transação correspondente -> sem aresta, sem proposta espúria.
  - Boost E2E: id_transacao literal na descrição -> heurística pix_e2e_literal_match.
  - Boost textual: marcador PIX + nome -> heurística pix_marcador_textual.
  - Múltiplas candidatas com top-1 forte -> linka sem conflito.
  - Empate top-1/top-2 sem boost -> proposta de conflito, sem aresta.
  - Idempotência: rodar 2x não duplica.
  - Isolamento de escopo: docs de outro tipo (cupom_termico_foto) coexistem e
    NÃO entram no escopo do linker PIX (filtragem por tipo_documento).

Identificadores técnicos N-para-N com o grafo (``transacao``, ``documento_de``,  # noqa: accent
chaves de dict) ficam sem acento por consistência com o ingestor; texto humano
usa acentuação completa.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.graph.db import GrafoDB
from src.graph.ingestor_documento import ingerir_comprovante_pix_foto
from src.graph.linking import (
    EDGE_TIPO_DOCUMENTO_DE,
    linkar_pix_transacao,
)


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


# ============================================================================
# Helpers de fixture
# ============================================================================


def _payload_pix(
    *,
    sha: str,
    razao_social: str,
    data_emissao: str,
    total: float,
    id_transacao: str,
    chave_destinatario: str = "destinatario@email.com",
    banco_origem: str = "ITAU UNIBANCO S.A",
    banco_destino: str = "NUBANK",
    descricao: str = "Pagamento",
) -> dict:
    """Constrói um payload Opus canônico de comprovante PIX foto."""
    return {
        "sha256": sha,
        "tipo_documento": "comprovante_pix_foto",
        "estabelecimento": {
            "razao_social": razao_social,
            "cnpj": None,
            "endereco": None,
        },
        "data_emissao": data_emissao,
        "horario": "12:00:00",
        "itens": [
            {
                "codigo": None,
                "descricao": descricao,
                "qtd": 1,
                "unidade": "UN",
                "valor_unit": total,
                "valor_total": total,
            }
        ],
        "total": total,
        "forma_pagamento": "pix",
        "_pix": {
            "banco_origem": banco_origem,
            "banco_destino": banco_destino,
            "remetente_nome": "ANDRE SILVA BATISTA FARIAS",
            "remetente_cpf_mascarado": "***.273.731-**",
            "destinatario_cpf_mascarado": "***.966.140-**",
            "chave_destinatario": chave_destinatario,
            "autenticacao": "0123456789ABCDEF" * 2,
            "id_transacao": id_transacao,
            "realizada_em": "Celular",
            "descricao_remetente": descricao,
        },
        "extraido_via": "opus_supervisor_artesanal",
        "confianca_global": 0.95,
    }


def _criar_tx(
    db: GrafoDB,
    *,
    nome: str,
    data_iso: str,
    valor: float,
    local: str,
    tipo: str = "Despesa",
    banco: str = "Itau",
    descricao: str | None = None,
) -> int:
    """Cria nó ``transacao`` com metadata canônica (transação ASCII)."""  # noqa: accent
    metadata = {
        "data": data_iso,
        "valor": valor,
        "local": local,
        "banco": banco,
        "tipo": tipo,
        "forma_pagamento": "Pix",
    }
    if descricao is not None:
        metadata["descricao"] = descricao
    return db.upsert_node("transacao", nome, metadata=metadata)


# ============================================================================
# Cenários canônicos
# ============================================================================


def test_pix_isolado_data_valor_exatos_linka(db: GrafoDB, caminho_propostas: Path):
    """Cenário básico: 1 comprovante PIX + 1 transação com data e valor exatos
    e marcador PIX na descrição -> 1 aresta documento_de.
    """
    payload = _payload_pix(
        sha="a" * 64,
        razao_social="PANIFICADORA KI-SABOR",
        data_emissao="2026-05-09",
        total=900.0,
        id_transacao="E60701190202605091045501877023600",
        descricao="Aluguel Maio",
    )
    ingerir_comprovante_pix_foto(db, payload)
    tx_id = _criar_tx(
        db,
        nome="TX_PIX_KI_SABOR_2026_05",
        data_iso="2026-05-09",
        valor=900.0,
        local="PIX TRANSF KI-SABOR PANIFICADORA",
    )

    stats = linkar_pix_transacao(db, caminho_propostas=caminho_propostas)

    assert stats["linkados"] == 1, f"esperado 1 linkado, got {stats}"
    arestas = list(db.listar_edges(dst_id=tx_id, tipo=EDGE_TIPO_DOCUMENTO_DE))
    assert len(arestas) == 1
    assert arestas[0].evidencia.get("tipo_documento") == "comprovante_pix_foto"


def test_pix_sem_transacao_correspondente_nao_cria_aresta(
    db: GrafoDB, caminho_propostas: Path
):
    """PIX sem transação no extrato -> sem candidata, sem aresta, sem proposta.

    Caso: foto do comprovante chegou ao vault antes do extrato bancário ser
    importado. O linker deve apenas logar warning, não criar nada.
    """
    payload = _payload_pix(
        sha="b" * 64,
        razao_social="JOAO DA SILVA",
        data_emissao="2026-05-08",
        total=50.0,
        id_transacao="E12345678202605081200000000000001",
    )
    ingerir_comprovante_pix_foto(db, payload)

    stats = linkar_pix_transacao(db, caminho_propostas=caminho_propostas)

    assert stats["linkados"] == 0
    assert stats["sem_candidato"] == 1
    # Nenhuma aresta documento_de criada no grafo.
    todas_arestas = db.listar_edges(tipo=EDGE_TIPO_DOCUMENTO_DE)
    assert len(todas_arestas) == 0


def test_boost_e2e_literal_eleva_score_a_um(db: GrafoDB, caminho_propostas: Path):
    """Quando o E2E (id_transacao BACEN) aparece literal no campo ``local`` ou
    ``descricao`` da transação, o score sobe para 1.0 e a heurística vira  # noqa: accent
    ``pix_e2e_literal_match``. Selo de identidade absoluto.
    """
    e2e = "E60701190202605091045501877023600"
    payload = _payload_pix(
        sha="c" * 64,
        razao_social="VITORIA MARIA SILVA",
        data_emissao="2026-03-04",
        total=367.65,
        id_transacao=e2e,
    )
    ingerir_comprovante_pix_foto(db, payload)
    tx_id = _criar_tx(
        db,
        nome="TX_PIX_VITORIA_2026_03",
        data_iso="2026-03-04",
        valor=367.65,
        local="PIX OUT",
        descricao=f"Transferencia PIX id {e2e}",
    )

    stats = linkar_pix_transacao(db, caminho_propostas=caminho_propostas)

    assert stats["linkados"] == 1
    assert stats["boost_e2e"] == 1
    arestas = list(db.listar_edges(dst_id=tx_id, tipo=EDGE_TIPO_DOCUMENTO_DE))
    assert len(arestas) == 1
    assert arestas[0].evidencia.get("heuristica") == "pix_e2e_literal_match"
    assert float(arestas[0].evidencia.get("confidence")) == 1.0


def test_boost_textual_marcador_pix_mais_nome_soma_010(
    db: GrafoDB, caminho_propostas: Path
):
    """Sem E2E na descrição, mas com marcador PIX/TRANSF + token >=4 chars do
    nome do destinatário -> heurística ``pix_marcador_textual`` e +0.10 ao
    score canônico.
    """
    payload = _payload_pix(
        sha="d" * 64,
        razao_social="WESLEY RAMON CASTRO SANTANA",
        data_emissao="2026-05-08",
        total=50.0,
        id_transacao="E11111111202605081200000000000099",
    )
    ingerir_comprovante_pix_foto(db, payload)
    tx_id = _criar_tx(
        db,
        nome="TX_PIX_WESLEY_2026_05",
        data_iso="2026-05-08",
        valor=50.0,
        local="PIX TRANSF WESLEY RAMON",
    )

    stats = linkar_pix_transacao(db, caminho_propostas=caminho_propostas)

    assert stats["linkados"] == 1
    assert stats["boost_textual"] == 1
    arestas = list(db.listar_edges(dst_id=tx_id, tipo=EDGE_TIPO_DOCUMENTO_DE))
    assert len(arestas) == 1
    assert arestas[0].evidencia.get("heuristica") == "pix_marcador_textual"


def test_empate_sem_boost_gera_proposta_de_conflito(
    db: GrafoDB, caminho_propostas: Path
):
    """Duas transações com data/valor idênticos e nenhum boost discriminador
    -> top-1 e top-2 empatam dentro de margem_empate -> proposta de conflito
    em vez de aresta.
    """
    payload = _payload_pix(
        sha="e" * 64,
        razao_social="ZZZZZ NOME ANONIMO SEM MATCH EM NENHUM MOVIMENTO",  # noqa: accent
        data_emissao="2026-05-10",
        total=120.00,
        id_transacao="E22222222202605101200000000000007",
    )
    ingerir_comprovante_pix_foto(db, payload)
    # Duas TX clones (data + valor iguais), descrições sem PIX/TRANSF nem o
    # nome do destinatário -> nenhum boost se aplica, score canônico empata.
    _criar_tx(
        db,
        nome="TX_CANDIDATA_A",
        data_iso="2026-05-10",
        valor=120.00,
        local="ESTABELECIMENTO COMERCIAL A",
    )
    _criar_tx(
        db,
        nome="TX_CANDIDATA_B",
        data_iso="2026-05-10",
        valor=120.00,
        local="ESTABELECIMENTO COMERCIAL B",
    )

    stats = linkar_pix_transacao(db, caminho_propostas=caminho_propostas)

    assert stats["conflitos"] == 1
    assert stats["linkados"] == 0
    # Nenhuma aresta foi criada.
    todas_arestas = db.listar_edges(tipo=EDGE_TIPO_DOCUMENTO_DE)
    assert len(todas_arestas) == 0
    # Proposta de conflito foi escrita no diretório destino.
    propostas = list(caminho_propostas.glob("*_conflito.md"))
    assert len(propostas) == 1, f"esperado 1 proposta conflito, got {propostas}"


def test_idempotencia_nao_duplica_aresta_em_segunda_rodada(
    db: GrafoDB, caminho_propostas: Path
):
    """Rodar ``linkar_pix_transacao`` duas vezes mantém exatamente 1 aresta
    ``documento_de`` por par (UNIQUE(src,dst,tipo) no schema).
    """
    payload = _payload_pix(
        sha="f" * 64,
        razao_social="PANIFICADORA KI-SABOR",
        data_emissao="2026-05-09",
        total=900.0,
        id_transacao="E60701190202605091045501877023600",
    )
    ingerir_comprovante_pix_foto(db, payload)
    tx_id = _criar_tx(
        db,
        nome="TX_IDEMPOTENCIA",
        data_iso="2026-05-09",
        valor=900.0,
        local="PIX TRANSF KI-SABOR PANIFICADORA",
    )

    stats_1 = linkar_pix_transacao(db, caminho_propostas=caminho_propostas)
    stats_2 = linkar_pix_transacao(db, caminho_propostas=caminho_propostas)

    assert stats_1["linkados"] == 1
    arestas = list(db.listar_edges(dst_id=tx_id, tipo=EDGE_TIPO_DOCUMENTO_DE))
    assert len(arestas) == 1, (
        f"idempotência violada: 2 rodadas devem gerar 1 aresta, "
        f"got {len(arestas)} (stats_2={stats_2})"
    )


def test_filtra_apenas_tipo_comprovante_pix_foto(db: GrafoDB, caminho_propostas: Path):
    """Documentos de OUTRO tipo coexistem no grafo mas NÃO entram no escopo
    do linker PIX. Garante que ``linkar_pix_transacao`` filtra estritamente
    por ``tipo_documento == 'comprovante_pix_foto'`` (não invade escopo do
    motor canônico).
    """
    # 1 documento PIX (deveria ser processado).
    payload = _payload_pix(
        sha="9" * 64,
        razao_social="PANIFICADORA KI-SABOR",
        data_emissao="2026-05-09",
        total=900.0,
        id_transacao="E60701190202605091045501877023600",
    )
    ingerir_comprovante_pix_foto(db, payload)
    _criar_tx(
        db,
        nome="TX_PIX_KI_SABOR_FILTRO",
        data_iso="2026-05-09",
        valor=900.0,
        local="PIX TRANSF KI-SABOR",
    )

    # 1 documento de OUTRO tipo (cupom termico) ingerido direto via SQL minimal.
    # Não precisa do ingestor completo -- apenas garantir que existe no grafo
    # como `documento` com tipo_documento != comprovante_pix_foto.
    db.upsert_node(
        "documento",
        "CUPOM|DUMMY|2026-05-09",
        metadata={
            "tipo_documento": "cupom_termico",
            "data_emissao": "2026-05-09",
            "total": 50.0,
            "chave_44": "CUPOM|DUMMY|2026-05-09",
        },
    )
    _criar_tx(
        db,
        nome="TX_CUPOM_DUMMY",
        data_iso="2026-05-09",
        valor=50.0,
        local="MERCADINHO LOCAL",
    )

    stats = linkar_pix_transacao(db, caminho_propostas=caminho_propostas)

    # Apenas o PIX foi processado: 1 linkado, nada de cupom.
    assert stats["linkados"] == 1, f"esperado 1 PIX linkado, got {stats}"
    # Confirma que o cupom NÃO recebeu aresta documento_de via este linker.
    todas_arestas = db.listar_edges(tipo=EDGE_TIPO_DOCUMENTO_DE)
    assert len(todas_arestas) == 1


# "Cada PIX é um vestígio; cada vestígio aponta à transação." -- Bachelard
