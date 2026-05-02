"""Linking heurístico documento médico -> transação dedutível.

Sprint IRPF-02 (escopo refinado por padrão (k) BRIEF -- corpus real
ainda não tem nodes ``receita_medica``/``exame_medico`` porque DOC-09 e
DOC-10 estão em backlog).

Cria aresta ``dedutivel_medico`` entre nodes do tipo ``documento`` (com
``tipo_documento`` em ``{receita_medica, exame_medico, plano_saude_carteirinha}``)
e nodes ``transação`` que comprovam o pagamento, aplicando heurística:

  - **CPF do paciente** (preferencial): metadata.cpf_paciente do
    documento bate com metadata.cnpj_cpf da transação OU metadata.quem
    (pessoa_a/pessoa_b) mapeia para o CPF declarado em
    ``mappings/pessoas.yaml`` (PII gitignored).
  - **Data**: |data_emissao_documento - data_transacao| <= 30 dias.
  - **Valor**: |total_documento - valor_transacao| <= 10% do total.
  - **Tag IRPF**: bonus se a transação já tem
    ``tag_irpf == "dedutivel_medico"`` (sinal forte do irpf_tagger).

Score combinado:

  score = base 1.0
        - 0.01 * delta_dias       (peso temporal: 0.01/dia, max 30 dias = 0.30)
        - 0.50 * diff_valor_pct   (peso valor: até 0.50)
        + 0.20 se cpf_bate (preferencial) ou +0.10 se quem_bate (fallback)
        + 0.10 se tag_irpf == "dedutivel_medico"
        floor em 0.0; sem teto interno (bonus extras criam separação no
        ranking quando candidatas saturariam em 1.0). O ``peso`` gravado na
        aresta é clampado em [0, 1] para preservar contrato do grafo;
        o ``confidence`` na evidência preserva o valor cru para auditoria.

Cria aresta apenas se ``score >= confidence_minimo`` (default 0.55, mais
permissivo que linking genérico porque match médico é alto risco
falso-negativo: paciente paga em dinheiro/cartão sem comprovante e a
edge é a única forma de IRPF reconhecer dedutibilidade).

Conforme ADR-13: heurística determinística, sem chamada Anthropic API.
Idempotência: aresta tem UNIQUE(src,dst,tipo) -- rodar 2x não duplica.

Quando DOC-09/10 fecharem e nodes médicos aparecerem no grafo, esta
função pode ser chamada no pipeline (``src/pipeline.py``) após
``linkar_documentos_a_transacoes``. Ver sprint follow-up
``IRPF-02-FOLLOWUP-CORPUS-MEDICO`` em backlog.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from src.graph.db import GrafoDB
from src.graph.models import Edge, Node
from src.utils.logger import configurar_logger

logger = configurar_logger("transform.linking_medico")

EDGE_DEDUTIVEL_MEDICO: str = "dedutivel_medico"
TIPOS_DOCUMENTO_MEDICO: frozenset[str] = frozenset(
    {"receita_medica", "exame_medico", "plano_saude_carteirinha"}
)

JANELA_DIAS_DEFAULT: int = 30
DIFF_VALOR_PCT_DEFAULT: float = 0.10
CONFIDENCE_MINIMO_DEFAULT: float = 0.55
PESO_TEMPORAL_DIARIO: float = 0.01

BONUS_CPF_BATE: float = 0.20
BONUS_QUEM_BATE: float = 0.10
BONUS_TAG_IRPF: float = 0.10


def _parse_data(valor: Any) -> date | None:
    """Aceita ISO 'YYYY-MM-DD' ou 'YYYY-MM-DD HH:MM:SS'. Retorna None se inválido."""
    if not valor:
        return None
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def _normalizar_cpf(valor: Any) -> str | None:
    """Devolve CPF apenas dígitos (11 caracteres) ou None."""
    if not valor:
        return None
    digitos = "".join(ch for ch in str(valor) if ch.isdigit())
    if len(digitos) != 11:
        return None
    return digitos


def _calcular_score(
    delta_dias: int,
    valor_documento: float,
    valor_transacao: float,
    cpf_bate: bool,
    quem_bate: bool,
    tag_irpf_dedutivel: bool,
) -> tuple[float, float]:
    """Devolve (score, diff_valor_percentual)."""
    valor_ref = max(abs(valor_documento), 1.0)
    diff_pct = min(abs(valor_documento - valor_transacao) / valor_ref, 1.0)

    score = 1.0
    score -= abs(delta_dias) * PESO_TEMPORAL_DIARIO
    score -= diff_pct * 0.50
    if cpf_bate:
        score += BONUS_CPF_BATE
    elif quem_bate:
        score += BONUS_QUEM_BATE
    if tag_irpf_dedutivel:
        score += BONUS_TAG_IRPF

    if score < 0.0:
        score = 0.0
    return round(score, 4), round(diff_pct, 4)


def _candidatas_transacao(
    db: GrafoDB,
    documento: Node,
    janela_dias: int,
    diff_valor_pct: float,
) -> list[tuple[Node, dict[str, Any]]]:
    """Lista transações candidatas para um documento médico, com evidência."""
    metadata_doc = documento.metadata
    data_doc = _parse_data(metadata_doc.get("data_emissao"))
    total_doc = metadata_doc.get("total")
    cpf_paciente = _normalizar_cpf(metadata_doc.get("cpf_paciente"))
    quem_paciente = (metadata_doc.get("quem") or "").strip().lower()

    if data_doc is None or total_doc is None:
        return []
    try:
        total_doc_f = float(total_doc)
    except (TypeError, ValueError):
        return []

    margem_valor = abs(total_doc_f) * diff_valor_pct
    janela = timedelta(days=janela_dias)

    candidatas: list[tuple[Node, dict[str, Any]]] = []
    for transacao in db.listar_nodes(tipo="transacao"):
        if transacao.id is None:
            continue
        m_tx = transacao.metadata
        data_tx = _parse_data(m_tx.get("data"))
        valor_tx = m_tx.get("valor")
        if data_tx is None or valor_tx is None:
            continue
        try:
            valor_tx_f = float(valor_tx)
        except (TypeError, ValueError):
            continue

        if abs((data_tx - data_doc).days) > janela.days:
            continue
        if abs(valor_tx_f - total_doc_f) > margem_valor:
            continue

        cpf_bate = False
        quem_bate = False
        cnpj_cpf_tx = _normalizar_cpf(m_tx.get("cnpj_cpf"))
        if cpf_paciente and cnpj_cpf_tx and cpf_paciente == cnpj_cpf_tx:
            cpf_bate = True
        elif quem_paciente:
            quem_tx = (m_tx.get("quem") or "").strip().lower()
            if quem_tx and quem_paciente in {quem_tx, "casal"}:
                quem_bate = True

        tag = (m_tx.get("tag_irpf") or "").strip().lower()
        tag_irpf_dedutivel = tag == "dedutivel_medico"

        delta_dias = (data_tx - data_doc).days
        score, diff_pct = _calcular_score(
            delta_dias=delta_dias,
            valor_documento=total_doc_f,
            valor_transacao=valor_tx_f,
            cpf_bate=cpf_bate,
            quem_bate=quem_bate,
            tag_irpf_dedutivel=tag_irpf_dedutivel,
        )

        evidencia = {
            "delta_dias": delta_dias,
            "diff_valor_pct": diff_pct,
            "cpf_bate": cpf_bate,
            "quem_bate": quem_bate,
            "tag_irpf_dedutivel": tag_irpf_dedutivel,
            "confidence": score,
            "heuristica": "linking_medico_v1",
        }
        candidatas.append((transacao, evidencia))

    candidatas.sort(key=lambda par: par[1]["confidence"], reverse=True)
    return candidatas


def linkar_dedutivel_medico(
    db: GrafoDB,
    janela_dias: int = JANELA_DIAS_DEFAULT,
    diff_valor_pct: float = DIFF_VALOR_PCT_DEFAULT,
    confidence_minimo: float = CONFIDENCE_MINIMO_DEFAULT,
) -> dict[str, int]:
    """Cria arestas ``dedutivel_medico`` entre documentos médicos e transações.

    Itera nodes ``documento`` com ``tipo_documento`` em
    ``TIPOS_DOCUMENTO_MEDICO``. Para cada um, busca transação compatível
    (data ±janela_dias, valor ±diff_valor_pct, opcional CPF/quem/tag).
    Cria aresta apenas se ``score >= confidence_minimo``.

    Idempotência: ``adicionar_edge`` usa INSERT OR IGNORE -- rodar 2x
    não duplica.

    Retorna dict com contadores: ``documentos_analisados``, ``linkados``,
    ``sem_candidata``, ``baixa_confianca``.
    """
    stats = {
        "documentos_analisados": 0,
        "linkados": 0,
        "sem_candidata": 0,
        "baixa_confianca": 0,
    }
    for documento in db.listar_nodes(tipo="documento"):
        tipo_doc = documento.metadata.get("tipo_documento")
        if tipo_doc not in TIPOS_DOCUMENTO_MEDICO:
            continue
        if documento.id is None:
            continue
        stats["documentos_analisados"] += 1

        candidatas = _candidatas_transacao(
            db, documento, janela_dias, diff_valor_pct
        )
        if not candidatas:
            stats["sem_candidata"] += 1
            continue

        top_node, top_evidencia = candidatas[0]
        if top_evidencia["confidence"] < confidence_minimo:
            stats["baixa_confianca"] += 1
            continue

        if top_node.id is None:
            continue

        db.adicionar_edge(
            src_id=documento.id,
            dst_id=top_node.id,
            tipo=EDGE_DEDUTIVEL_MEDICO,
            peso=min(top_evidencia["confidence"], 1.0),
            evidencia=top_evidencia,
        )
        stats["linkados"] += 1
        logger.info(
            "linked dedutivel_medico: doc %s -> tx %s (score=%.3f)",
            documento.nome_canonico,
            top_node.id,
            top_evidencia["confidence"],
        )

    logger.info("linking_medico concluído: %s", stats)
    return stats


def listar_arestas_dedutivel_medico(db: GrafoDB) -> list[Edge]:
    """Devolve todas as arestas ``dedutivel_medico`` -- útil para auditoria IRPF."""
    return db.listar_edges(tipo=EDGE_DEDUTIVEL_MEDICO)


# "Cada despesa medica é uma evidencia, cada evidencia uma deducao."
#  -- princípio operacional do Protocolo Ouroboros
