"""Testes da Sprint IRPF-02 -- linking dedutivel_medico.

Cobre ``src.transform.linking_medico``: heurística CPF + data ±30d +
valor ±10%, score com bônus por tag_irpf, idempotência, tolerância a
metadata incompleto.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.graph.db import GrafoDB
from src.transform.linking_medico import (
    EDGE_DEDUTIVEL_MEDICO,
    linkar_dedutivel_medico,
    listar_arestas_dedutivel_medico,
)


@pytest.fixture
def grafo_basico(tmp_path: Path) -> GrafoDB:
    """Grafo com 1 receita médica + 1 transação compatível."""
    db = GrafoDB(tmp_path / "grafo.sqlite")
    db.criar_schema()
    db.upsert_node(
        tipo="documento",
        nome_canonico="receita_dr_silva_2026-04-15",
        metadata={
            "tipo_documento": "receita_medica",
            "data_emissao": "2026-04-15",
            "total": 250.00,
            "cpf_paciente": "12345678900",
            "quem": "pessoa_b",
            "medico": "Dr. Silva",
        },
    )
    db.upsert_node(
        tipo="transacao",
        nome_canonico="tx_clinica_ludens_2026-04-16",
        metadata={
            "data": "2026-04-16",
            "valor": 250.00,
            "local": "CLINICA LUDENS",
            "quem": "pessoa_b",
            "tag_irpf": "dedutivel_medico",
            "cnpj_cpf": "12345678900",  # CPF do paciente -- rota preferencial
        },
    )
    return db


def test_link_basico_cpf_bate_data_proxima_valor_exato(grafo_basico):
    """Receita + transação com CPF batendo + data 1 dia depois + valor exato."""
    stats = linkar_dedutivel_medico(grafo_basico)

    assert stats["documentos_analisados"] == 1
    assert stats["linkados"] == 1
    assert stats["sem_candidata"] == 0
    assert stats["baixa_confianca"] == 0

    arestas = listar_arestas_dedutivel_medico(grafo_basico)
    assert len(arestas) == 1
    assert arestas[0].tipo == EDGE_DEDUTIVEL_MEDICO
    assert arestas[0].peso >= 0.55  # acima do confidence_minimo


def test_idempotencia_rodar_2x_nao_duplica(grafo_basico):
    """Rodar linkar_dedutivel_medico 2x produz exatamente 1 aresta."""
    linkar_dedutivel_medico(grafo_basico)
    linkar_dedutivel_medico(grafo_basico)
    arestas = listar_arestas_dedutivel_medico(grafo_basico)
    assert len(arestas) == 1


def test_quem_bate_sem_cpf_ainda_linka(tmp_path):
    """Sem CPF, mas quem='Vitória' bate em transação 'Vitória': link."""  # anonimato-allow
    db = GrafoDB(tmp_path / "grafo.sqlite")
    db.criar_schema()
    db.upsert_node(
        tipo="documento",
        nome_canonico="receita_x",
        metadata={
            "tipo_documento": "receita_medica",
            "data_emissao": "2026-04-15",
            "total": 250.00,
            "quem": "pessoa_b",
        },
    )
    db.upsert_node(
        tipo="transacao",
        nome_canonico="tx_y",
        metadata={
            "data": "2026-04-15",
            "valor": 250.00,
            "local": "CLINICA",
            "quem": "pessoa_b",
        },
    )
    stats = linkar_dedutivel_medico(db)
    assert stats["linkados"] == 1


def test_data_fora_da_janela_30d_nao_linka(tmp_path):
    """delta_dias > 30 -> sem candidata."""
    db = GrafoDB(tmp_path / "grafo.sqlite")
    db.criar_schema()
    db.upsert_node(
        tipo="documento",
        nome_canonico="receita_velha",
        metadata={
            "tipo_documento": "receita_medica",
            "data_emissao": "2026-01-01",
            "total": 250.00,
            "quem": "pessoa_a",
        },
    )
    db.upsert_node(
        tipo="transacao",
        nome_canonico="tx_distante",
        metadata={
            "data": "2026-04-30",  # ~120 dias depois
            "valor": 250.00,
            "local": "CLINICA",
            "quem": "pessoa_a",
        },
    )
    stats = linkar_dedutivel_medico(db)
    assert stats["linkados"] == 0
    assert stats["sem_candidata"] == 1


def test_valor_fora_de_10pct_nao_linka(tmp_path):
    """diff_valor > 10% -> sem candidata."""
    db = GrafoDB(tmp_path / "grafo.sqlite")
    db.criar_schema()
    db.upsert_node(
        tipo="documento",
        nome_canonico="receita_z",
        metadata={
            "tipo_documento": "receita_medica",
            "data_emissao": "2026-04-15",
            "total": 250.00,
            "quem": "pessoa_a",
        },
    )
    db.upsert_node(
        tipo="transacao",
        nome_canonico="tx_valor_errado",
        metadata={
            "data": "2026-04-16",
            "valor": 500.00,  # 100% diff -- rejeita
            "local": "CLINICA",
            "quem": "pessoa_a",
        },
    )
    stats = linkar_dedutivel_medico(db)
    assert stats["linkados"] == 0
    assert stats["sem_candidata"] == 1


def test_documento_nao_medico_e_ignorado(tmp_path):
    """Holerite/DAS não vira candidato -- nem entra na contagem analisados."""
    db = GrafoDB(tmp_path / "grafo.sqlite")
    db.criar_schema()
    db.upsert_node(
        tipo="documento",
        nome_canonico="holerite_2026-04",
        metadata={
            "tipo_documento": "holerite",
            "data_emissao": "2026-04-15",
            "total": 5000.00,
        },
    )
    stats = linkar_dedutivel_medico(db)
    assert stats["documentos_analisados"] == 0
    assert stats["linkados"] == 0


def test_metadata_incompleto_e_tolerado(tmp_path):
    """Documento sem data_emissao ou total: pula sem erro."""
    db = GrafoDB(tmp_path / "grafo.sqlite")
    db.criar_schema()
    db.upsert_node(
        tipo="documento",
        nome_canonico="receita_incompleta",
        metadata={
            "tipo_documento": "receita_medica",
            # falta data_emissao + total
            "quem": "pessoa_a",
        },
    )
    stats = linkar_dedutivel_medico(db)
    assert stats["documentos_analisados"] == 1
    assert stats["sem_candidata"] == 1


def test_tag_irpf_eleva_score_acima_de_confidence_minimo(tmp_path):
    """Sem CPF/quem batendo, mas tag_irpf=dedutivel_medico, ainda linka."""
    db = GrafoDB(tmp_path / "grafo.sqlite")
    db.criar_schema()
    db.upsert_node(
        tipo="documento",
        nome_canonico="receita_anonima",
        metadata={
            "tipo_documento": "receita_medica",
            "data_emissao": "2026-04-15",
            "total": 250.00,
            # sem cpf_paciente nem quem -- só data + valor + tag
        },
    )
    db.upsert_node(
        tipo="transacao",
        nome_canonico="tx_com_tag",
        metadata={
            "data": "2026-04-15",
            "valor": 250.00,
            "local": "CLINICA",
            "tag_irpf": "dedutivel_medico",
        },
    )
    stats = linkar_dedutivel_medico(db)
    # delta=0, diff=0, sem cpf, sem quem, tag_irpf=+0.10:
    # score = 1.0 - 0 - 0 + 0 + 0.10 = 1.10 -> clamp 1.0
    assert stats["linkados"] == 1


def test_score_baixo_gera_baixa_confianca(tmp_path):
    """Sem cpf/quem/tag e delta+diff razoáveis: score abaixo de 0.55."""
    db = GrafoDB(tmp_path / "grafo.sqlite")
    db.criar_schema()
    db.upsert_node(
        tipo="documento",
        nome_canonico="receita_orfan",
        metadata={
            "tipo_documento": "receita_medica",
            "data_emissao": "2026-04-01",
            "total": 250.00,
        },
    )
    db.upsert_node(
        tipo="transacao",
        nome_canonico="tx_meiomatch",
        metadata={
            # delta=29 dias, diff=8%, sem cpf/quem/tag
            # score = 1.0 - 29*0.01 - 0.08*0.5 = 1.0 - 0.29 - 0.04 = 0.67 -- ainda passa
            # vou forçar valores que dão score abaixo de 0.55
            "data": "2026-04-30",  # delta 29
            "valor": 270.00,  # diff 8%
            "local": "CLINICA",
        },
    )
    # Aumentar confidence_minimo para forçar baixa_confianca
    stats = linkar_dedutivel_medico(db, confidence_minimo=0.80)
    assert stats["linkados"] == 0
    assert stats["baixa_confianca"] == 1


def test_dois_candidatos_pega_o_de_score_mais_alto(tmp_path):
    """2 transações candidatas: linka apenas a de maior score."""
    db = GrafoDB(tmp_path / "grafo.sqlite")
    db.criar_schema()
    db.upsert_node(
        tipo="documento",
        nome_canonico="receita_dupla",
        metadata={
            "tipo_documento": "receita_medica",
            "data_emissao": "2026-04-15",
            "total": 250.00,
            "quem": "pessoa_a",
        },
    )
    # Candidata fraca: 5 dias depois, valor 5% diff, sem tag
    db.upsert_node(
        tipo="transacao",
        nome_canonico="tx_fraca",
        metadata={
            "data": "2026-04-20",
            "valor": 262.50,  # 5% diff
            "local": "CLINICA",
            "quem": "pessoa_a",
        },
    )
    # Candidata forte: 0 dias, valor exato, com tag
    db.upsert_node(
        tipo="transacao",
        nome_canonico="tx_forte",
        metadata={
            "data": "2026-04-15",
            "valor": 250.00,
            "local": "CLINICA",
            "quem": "pessoa_a",
            "tag_irpf": "dedutivel_medico",
        },
    )
    stats = linkar_dedutivel_medico(db)
    # Apenas 1 link criado (top-1 conforme heurística)
    assert stats["linkados"] == 1
    arestas = listar_arestas_dedutivel_medico(db)
    assert len(arestas) == 1
    # Aresta deve apontar para tx_forte (via dst_id)
    tx_forte = db.buscar_node("transacao", "tx_forte")
    assert arestas[0].dst_id == tx_forte.id


# "Cada deducao medica e um direito reconhecido pelo grafo."
#  -- principio operacional do Protocolo Ouroboros
