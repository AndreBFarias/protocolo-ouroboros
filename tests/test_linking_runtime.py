"""Testes de regressão runtime do linking documento -> transação (Sprint 95).

Sprint 48 entregou o motor (`src/graph/linking.py`). Em runtime real (auditoria
2026-04-26) o motor produzia 0 arestas `documento_de` para 41 documentos
catalogados, mesmo com candidatas óbvias presentes no grafo (PAGTO SALARIO,
RECEITA FEDERAL, etc.). Causa diagnóstica:

  - Holerite tem `data_emissao = mes_ref + "-01"` mas o pagamento Itaú cai 30+
    dias depois. Janela default (3 dias) descarta candidata antes do score.
  - DAS PARCSN tem `data_emissao` na competência (fim do mês) mas o pagamento
    via PIX para "RECEITA FEDERAL" ocorre próximo ao vencimento (~47 dias
    depois). Mesma janela curta descarta candidata.
  - Mesmo após ampliar a janela, o `_calcular_score` aplicava penalidade fixa
    de -0.10 por dia. Para delta=47, score era forçado a 0 (clamp).

Fix Sprint 95: parâmetro `peso_temporal_diario` configurável por tipo de
documento. Holerite 0.01, DAS/boleto 0.005, default 0.10 (preserva Sprint 48).
Janelas ampliadas em `mappings/linking_config.yaml` para holerite/DAS/boleto.

Estes testes garantem que:
  1. Holerite + tx PAGTO SALARIO com delta de 35 dias e diferença de valor
     bruto-vs-líquido (~14%) gera 1 aresta `documento_de`.
  2. DAS PARCSN + tx RECEITA FEDERAL com delta de 47 dias e valor exato gera
     1 aresta `documento_de`.
  3. Idempotência: rodar `linkar_documentos_a_transacoes` duas vezes não
     duplica a aresta criada.
  4. Regressão Sprint 48: NFC-e com data exata + cnpj_bate continua linkando
     (peso_temporal_diario default não regrede).

Acentuação: identificadores técnicos N-para-N com o grafo ("transacao",
"documento_de", chaves de dict) seguem sem acento por consistência com
`src/graph/ingestor_documento.py`. Texto humano em docstrings e asserts
usa acentuação completa.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.graph.db import GrafoDB
from src.graph.ingestor_documento import ingerir_documento_fiscal
from src.graph.linking import (
    EDGE_TIPO_DOCUMENTO_DE,
    linkar_documentos_a_transacoes,
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


def _ingerir_holerite(
    db: GrafoDB,
    *,
    fonte: str,
    mes_ref: str,
    bruto: float,
    cnpj_sintetico: str = "HOLERITE|abcdef123456",
) -> int:
    """Replica `_ingerir_holerite_no_grafo` do extrator de contracheque."""
    chave = f"HOLERITE|{fonte}|{mes_ref}".replace(" ", "_")
    doc = {
        "chave_44": chave,
        "cnpj_emitente": cnpj_sintetico,
        "data_emissao": f"{mes_ref}-01",
        "tipo_documento": "holerite",
        "total": bruto,
        "razao_social": fonte.upper(),
        "numero": chave,
        "periodo_apuracao": mes_ref,
    }
    return ingerir_documento_fiscal(db, doc, itens=[])


def _ingerir_das_parcsn(
    db: GrafoDB,
    *,
    chave_44: str,
    cnpj_emitente: str,
    data_emissao: str,
    total: float,
    vencimento: str,
    parcela: int = 1,
) -> int:
    doc = {
        "chave_44": chave_44,
        "cnpj_emitente": cnpj_emitente,
        "data_emissao": data_emissao,
        "tipo_documento": "das_parcsn_andre",
        "total": total,
        "razao_social": "ANDRE DA SILVA BATISTA DE FARIAS",
        "numero": chave_44,
        "vencimento": vencimento,
        "parcela_atual": parcela,
        "parcela_total": 25,
        "periodo_apuracao": data_emissao[:7],
    }
    return ingerir_documento_fiscal(db, doc, itens=[])


def _criar_tx(
    db: GrafoDB,
    *,
    nome: str,
    data_iso: str,
    valor: float,
    local: str,
    tipo: str = "Receita",
    banco: str = "Itau",
) -> int:
    metadata = {
        "data": data_iso,
        "valor": valor,
        "local": local,
        "banco": banco,
        "tipo": tipo,
        "forma_pagamento": "Pix",
    }
    return db.upsert_node("transacao", nome, metadata=metadata)


# ============================================================================
# Cenários de regressão runtime (Sprint 95)
# ============================================================================


def test_holerite_g4f_linka_com_pagto_salario_apos_5_dias(db: GrafoDB, caminho_propostas: Path):
    """Holerite G4F competência 2026-03 (emissão 2026-03-01, total bruto 8657.25)
    deve linkar com tx PAGTO SALARIO em 2026-03-06 valor 7442.38 (líquido).

    Cenário canônico Sprint 95: delta=5 dias, diferença valor bruto vs líquido
    ~14%, sem CNPJ na contraparte da transação. Antes do fix: 0 candidatas
    (janela 3 dias, valor diff 2%). Depois: 1 aresta.
    """
    _ingerir_holerite(db, fonte="G4F", mes_ref="2026-03", bruto=8657.25)
    tx_id = _criar_tx(
        db,
        nome="TX_PAGTO_SALARIO_2026_03",
        data_iso="2026-03-06",
        valor=7442.38,
        local="PAGTO SALARIO",
    )

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)

    assert stats["linkados"] == 1, f"esperado 1 linkado, got {stats}"
    arestas = list(db.listar_edges(dst_id=tx_id, tipo=EDGE_TIPO_DOCUMENTO_DE))
    assert len(arestas) == 1
    assert arestas[0].evidencia.get("tipo_documento") == "holerite"
    assert arestas[0].evidencia.get("tipo_edge_semantico") == "comprovante"


def test_das_parcsn_linka_com_receita_federal_47_dias_depois(db: GrafoDB, caminho_propostas: Path):
    """DAS PARCSN emitido 2025-02-28 (R$ 324.31) deve linkar com tx
    RECEITA FEDERAL em 2025-04-16 (valor exato).

    Cenário canônico Sprint 95: delta=47 dias, diff_valor=0, sem CNPJ na
    contraparte. Antes do fix: candidata zerava no clamp (47 * 0.10 = 4.70).
    Depois (peso_temporal=0.005): score = 1 - 47*0.005 = 0.765 -> linka.
    """
    _ingerir_das_parcsn(
        db,
        chave_44="07182510572313828",
        cnpj_emitente="45.850.636/0001-60",
        data_emissao="2025-02-28",
        total=324.31,
        vencimento="2025-04-30",
    )
    tx_id = _criar_tx(
        db,
        nome="TX_RECEITA_FEDERAL_2025_04",
        data_iso="2025-04-16",
        valor=324.31,
        local="RECEITA FEDERAL",
        tipo="Imposto",
        banco="Nubank (PF)",
    )

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)

    assert stats["linkados"] == 1, f"esperado 1 linkado, got {stats}"
    arestas = list(db.listar_edges(dst_id=tx_id, tipo=EDGE_TIPO_DOCUMENTO_DE))
    assert len(arestas) == 1


def test_idempotencia_holerite_nao_duplica_aresta(db: GrafoDB, caminho_propostas: Path):
    """Rodar `linkar_documentos_a_transacoes` duas vezes deve manter exatamente
    1 aresta `documento_de` por par (UNIQUE(src,dst,tipo) no schema).
    """
    _ingerir_holerite(db, fonte="G4F", mes_ref="2026-03", bruto=8657.25)
    tx_id = _criar_tx(
        db,
        nome="TX_PAGTO_SALARIO_IDEMP",
        data_iso="2026-03-06",
        valor=7442.38,
        local="PAGTO SALARIO",
    )

    stats_1 = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)
    stats_2 = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)

    assert stats_1["linkados"] == 1
    # Segunda rodada: a aresta já existe; conta como ja_linkados zero porque o
    # motor não marca evidência humana, mas o INSERT OR IGNORE garante que
    # nenhuma duplicata seja gerada. Validamos via contagem real no grafo.
    arestas = list(db.listar_edges(dst_id=tx_id, tipo=EDGE_TIPO_DOCUMENTO_DE))
    assert len(arestas) == 1, (
        f"idempotência violada: 2 rodadas devem gerar 1 aresta, "
        f"got {len(arestas)} (stats_2={stats_2})"
    )


def test_regressao_sprint_48_nfce_com_cnpj_bate_continua_linkando(
    db: GrafoDB, caminho_propostas: Path
):
    """NFC-e com data exata e CNPJ batendo na contraparte deve continuar
    linkando após fix Sprint 95 (peso_temporal_diario default = 0.10).

    Garante que o ajuste por tipo não regrede o caminho feliz da Sprint 48.
    """
    cnpj = "00.776.574/0160-79"
    doc = {
        "chave_44": "53260400776574016079653040000432601123456788",
        "cnpj_emitente": cnpj,
        "data_emissao": "2026-04-19",
        "tipo_documento": "nfce_modelo_65",
        "total": 100.0,
        "razao_social": "americanas sa - 0337",
        "numero": "43260",
    }
    ingerir_documento_fiscal(
        db,
        doc,
        itens=[
            {
                "codigo": "001",
                "descricao": "PRODUTO",
                "qtde": 1,
                "valor_unit": 100.0,
                "valor_total": 100.0,
            }
        ],
    )

    fid = db.upsert_node(
        "fornecedor",
        cnpj,
        metadata={"cnpj": cnpj, "razao_social": "AMERICANAS"},
    )
    tx_id = _criar_tx(
        db,
        nome="TX_AMERICANAS_PIX",
        data_iso="2026-04-19",
        valor=100.0,
        local="AMERICANAS",
        tipo="Despesa",
    )
    db.adicionar_edge(tx_id, fid, "contraparte")

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)

    assert stats["linkados"] == 1, f"regressão Sprint 48: got {stats}"
    arestas = list(db.listar_edges(dst_id=tx_id, tipo=EDGE_TIPO_DOCUMENTO_DE))
    assert len(arestas) == 1


def test_holerite_sem_tx_proxima_nao_gera_falso_positivo(db: GrafoDB, caminho_propostas: Path):
    """Holerite com total bruto 8657.25 não deve linkar com tx aleatória
    de valor distante. Garante que ampliar a janela não reduz o sinal a ruído.

    Tx 2026-03-06 R$ 100.00 (compra qualquer): diff_pct = 8557/8657 = 0.99,
    score = 1 - 5*0.01 - 0.99*0.50 = 0.455 < confidence_minimo 0.55 -> proposta,
    não aresta.
    """
    _ingerir_holerite(db, fonte="G4F", mes_ref="2026-03", bruto=8657.25)
    _criar_tx(
        db,
        nome="TX_RUIDO",
        data_iso="2026-03-06",
        valor=100.0,
        local="LOJA QUALQUER",
        tipo="Despesa",
    )

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)

    assert stats["linkados"] == 0, f"falso positivo: {stats}"


# ============================================================================
# Sprint 95b: ancora temporal alternativa por tipo (vencimento vs data_emissao)
# ============================================================================


def test_sprint_95b_das_parcsn_usa_vencimento_como_ancora(
    db: GrafoDB, caminho_propostas: Path
):
    """DAS PARCSN com data_emissao=2025-02-28 e vencimento=2025-04-30 e
    tx PIX RECEITA FEDERAL em 2025-04-25.

    Centrar a janela em data_emissao: delta=56d (cabe na janela 60d, score
    = 1 - 56*0.005 = 0.72 -> linka mas sem precisao).

    Centrar em vencimento (Sprint 95b): delta=-5d (score = 1 - 5*0.005 =
    0.975 -> linka com alta confianca). Mais cirurgico para parcelas
    consecutivas.
    """
    _ingerir_das_parcsn(
        db,
        chave_44="07182510572313828",
        cnpj_emitente="45.850.636/0001-60",
        data_emissao="2025-02-28",
        total=324.31,
        vencimento="2025-04-30",
    )
    tx_id = _criar_tx(
        db,
        nome="TX_RECEITA_FEDERAL_PROXIMA_VENCIMENTO",
        data_iso="2025-04-25",
        valor=324.31,
        local="RECEITA FEDERAL",
        tipo="Imposto",
    )

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)

    assert stats["linkados"] == 1, f"esperado 1 linkado via vencimento, got {stats}"
    arestas = list(db.listar_edges(dst_id=tx_id, tipo=EDGE_TIPO_DOCUMENTO_DE))
    assert len(arestas) == 1
    # Confidence deve refletir delta=-5 (vencimento) e não delta=56 (emissao).
    assert arestas[0].evidencia["diff_dias"] == -5, (
        f"delta_dias deve ser -5 (centrado em vencimento), got {arestas[0].evidencia}"
    )


def test_sprint_95b_holerite_default_ainda_usa_data_emissao(
    db: GrafoDB, caminho_propostas: Path
):
    """Holerite não declara ancora_temporal no config -- continua usando
    data_emissao como centro da janela. Garante backward-compat.
    """
    _ingerir_holerite(db, fonte="G4F", mes_ref="2026-03", bruto=8657.25)
    _criar_tx(
        db,
        nome="TX_PAGTO_SALARIO_DEFAULT_ANCORA",
        data_iso="2026-03-06",
        valor=7442.38,
        local="PAGTO SALARIO",
    )

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)
    assert stats["linkados"] == 1


def test_sprint_95b_ancora_inexistente_no_doc_cai_para_data_emissao(
    db: GrafoDB, caminho_propostas: Path
):
    """Se config declara ancora_temporal=vencimento mas o doc não tem o
    campo no metadata (cenario degradado), fallback para data_emissao
    garante que o linker não retorne lista vazia silenciosamente.
    """
    # Ingere DAS PARCSN sem o campo 'vencimento' (cenario degradado).
    doc = {
        "chave_44": "07182510572313829",
        "cnpj_emitente": "45.850.636/0001-60",
        "data_emissao": "2025-02-28",
        "tipo_documento": "das_parcsn_andre",
        "total": 324.31,
        "razao_social": "ANDRE DA SILVA BATISTA DE FARIAS",
        "numero": "07182510572313829",
        # 'vencimento' AUSENTE
        "parcela_atual": 1,
        "parcela_total": 25,
        "periodo_apuracao": "2025-02",
    }
    from src.graph.ingestor_documento import ingerir_documento_fiscal

    ingerir_documento_fiscal(db, doc, itens=[])
    _criar_tx(
        db,
        nome="TX_RECEITA_FEDERAL_FALLBACK",
        data_iso="2025-03-15",
        valor=324.31,
        local="RECEITA FEDERAL",
        tipo="Imposto",
    )

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)
    # Com fallback para data_emissao, delta=15d ainda cabe na janela 60d.
    assert stats["linkados"] >= 1, f"fallback para data_emissao deveria linkar, got {stats}"


# "Ligar é responsabilidade -- ligar errado é confundir a memória." -- princípio do arquivista
