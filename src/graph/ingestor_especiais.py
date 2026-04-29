"""Ingestores de documentos especiais (prescrição médica + garantia).

Extraídos de ``src.graph.ingestor_documento`` na Sprint ANTI-MIGUE-08
para manter o módulo núcleo abaixo de 800 linhas. Reusam helpers
públicos do módulo núcleo (``upsert_fornecedor``, ``upsert_periodo``,
``localizar_item``, ``_inferir_pessoa_canonica``, ``_extrair_mes_ref``).

Mantidos como módulo separado porque cobrem domínios distintos
(saúde humana e bens duráveis) que não compartilham esquema com o
documento fiscal genérico (``ingerir_documento_fiscal``). Re-exportados
no módulo de origem para preservar contratos públicos
(``from src.graph.ingestor_documento import ingerir_prescricao``).
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.graph.db import GrafoDB
from src.graph.ingestor_documento import (
    _extrair_mes_ref,
    _inferir_pessoa_canonica,
    localizar_item,
    upsert_fornecedor,
    upsert_periodo,
)
from src.graph.path_canonico import to_relativo
from src.utils.logger import configurar_logger

logger = configurar_logger("graph.ingestor_especiais")


JANELA_MATCH_ITEM_DIAS: int = 1
THRESHOLD_DESCRICAO: int = 82
MARGEM_DESEMPATE: int = 5


# ============================================================================
# Ingestão de prescrição médica (Sprint 47a)
# ============================================================================


CAMPOS_OBRIGATORIOS_PRESCRICAO: tuple[str, ...] = (
    "chave_prescricao",
    "crm_completo",
    "data_emissao",
)


def ingerir_prescricao(
    db: GrafoDB,
    prescricao: dict[str, Any],
    medicamentos: list[dict[str, Any]],
    caminho_arquivo: Path | None = None,
) -> int:
    """Insere uma prescrição médica e medicamentos prescritos no grafo.

    Campos esperados em `prescricao` (os 3 primeiros são obrigatórios):

        chave_prescricao: string sintética estável (ex: `PRESC|<data>|<crm>|<hash>`)
        crm_completo:     string canônica tipo `DF|12345` (UF + número)
        data_emissao:     YYYY-MM-DD
        medico_nome:      nome completo do médico
        medico_especialidade: string (opcional)
        paciente_nome:    nome do paciente (LGPD: guardar só o nome)
        validade_meses:   int (default 6 declarado no extrator)
        data_expira:      YYYY-MM-DD calculada pelo extrator
        expirada:         bool
        observacoes:      string livre

    Cada item em `medicamentos` precisa de: `chave_medicamento` (ex: `MED|LOSARTANA`),
    `nome`, `dosagem`, `forma`, `posologia`, `continuo` (bool), `elegivel_dedutivel_irpf`
    (bool), `principio_ativo` (quando reconhecido).

    Arestas criadas:
        prescricao -> fornecedor(medico) (emitida_por)
        prescricao -> periodo            (ocorre_em)
        prescricao -> item(medicamento)  (prescreve, uma por medicamento)
        prescricao -> item(farmacia_match) (prescreve_cobre) -- opcional,
            criada quando localizar_item_farmacia casa descrição do medicamento
            prescrito com node `item` já ingerido (compra de farmácia). Sprint 48
            refina o linking; aqui deixamos o stub ativo para acceptance #3.

    Idempotente: chave_prescricao única; reprocessar não duplica nós nem arestas.

    Devolve o id do nó `prescricao`.
    """
    for campo in CAMPOS_OBRIGATORIOS_PRESCRICAO:
        if not prescricao.get(campo):
            raise ValueError(
                f"prescricao sem '{campo}' -- ingestão abortada "
                "(nó prescricao ou aresta ficaria órfão)"
            )

    metadata = {
        chave: valor
        for chave, valor in prescricao.items()
        if valor is not None and not chave.startswith("_")
    }
    metadata.setdefault("tipo_documento", "receita_medica")
    if caminho_arquivo is not None:
        metadata["arquivo_origem"] = to_relativo(caminho_arquivo)
    metadata["pessoa"] = _inferir_pessoa_canonica(prescricao, caminho_arquivo)

    prescricao_id = db.upsert_node(
        "prescricao",
        prescricao["chave_prescricao"],
        metadata=metadata,
    )

    # Médico: tipo `fornecedor` com chave sintética `CRM|<UF>|<número>`.
    # Schema oficial (ADR-14) não tem tipo `pessoa_medico`; o médico é
    # semanticamente um fornecedor de serviço -- aliases carregam o nome.
    crm_canonico = f"CRM|{prescricao['crm_completo']}"
    medico_meta: dict[str, Any] = {
        "categoria": "medico",
        "crm": prescricao["crm_completo"],
    }
    if prescricao.get("medico_especialidade"):
        medico_meta["especialidade"] = prescricao["medico_especialidade"]
    aliases_medico: list[str] = []
    if prescricao.get("medico_nome"):
        aliases_medico.append(prescricao["medico_nome"])
    medico_id = db.upsert_node(
        "fornecedor",
        crm_canonico,
        metadata=medico_meta,
        aliases=aliases_medico,
    )
    db.adicionar_edge(prescricao_id, medico_id, "emitida_por")

    mes_ref = _extrair_mes_ref(prescricao["data_emissao"])
    if mes_ref:
        periodo_id = upsert_periodo(db, mes_ref)
        db.adicionar_edge(prescricao_id, periodo_id, "ocorre_em")

    for medicamento in medicamentos:
        if not medicamento.get("chave_medicamento") or not medicamento.get("nome"):
            logger.warning(
                "medicamento sem chave/nome em prescricao %s -- pulado",
                prescricao["chave_prescricao"],
            )
            continue
        meta_med: dict[str, Any] = {
            "categoria_item": "medicamento",
            "nome": medicamento["nome"],
        }
        for chave_extra in (
            "dosagem",
            "forma",
            "posologia",
            "continuo",
            "elegivel_dedutivel_irpf",
            "principio_ativo",
            "classe",
        ):
            valor_extra = medicamento.get(chave_extra)
            if valor_extra is not None:
                meta_med[chave_extra] = valor_extra
        aliases_med: list[str] = [medicamento["nome"]]
        principio = medicamento.get("principio_ativo")
        if principio and principio.upper() != medicamento["nome"].upper():
            aliases_med.append(principio)
        item_id = db.upsert_node(
            "item",
            medicamento["chave_medicamento"],
            metadata=meta_med,
            aliases=aliases_med,
        )
        evidencia = {
            "posologia": medicamento.get("posologia"),
            "continuo": bool(medicamento.get("continuo", False)),
        }
        db.adicionar_edge(prescricao_id, item_id, "prescreve", evidencia=evidencia)

        # Stub de linking com farmácia (Sprint 48 refina com threshold real).
        # Heurística mínima: se existe node `item` de farmácia (metadata
        # `categoria_item_fiscal=medicamento` ou descrição com princípio ativo)
        # com janela temporal próxima, cria aresta `prescreve_cobre`. Aqui o
        # linking é opt-in via `localizar_item_farmacia` devolvendo None por
        # padrão -- fica ativo como contrato, inócuo em falta de dados.
        item_farmacia_id = _localizar_item_farmacia_por_principio(
            db,
            principio_ativo=medicamento.get("principio_ativo"),
            nomes_comerciais=medicamento.get("nomes_comerciais", []),
            data_emissao=prescricao["data_emissao"],
            validade_meses=int(prescricao.get("validade_meses") or 6),
        )
        if item_farmacia_id is not None and item_farmacia_id != item_id:
            db.adicionar_edge(
                prescricao_id,
                item_farmacia_id,
                "prescreve_cobre",
                evidencia={
                    "match": "principio_ativo+janela_temporal",
                    "supervisor_valida": True,
                },
            )

    if prescricao.get("expirada"):
        logger.warning(
            "prescricao %s emitida em %s está expirada (validade %s meses)",
            prescricao["chave_prescricao"],
            prescricao["data_emissao"],
            prescricao.get("validade_meses"),
        )

    logger.info(
        "prescricao %s ingerida: %d medicamento(s), medico %s",
        prescricao["chave_prescricao"],
        len(medicamentos),
        prescricao["crm_completo"],
    )
    return prescricao_id


def _localizar_item_farmacia_por_principio(
    db: GrafoDB,
    principio_ativo: str | None,
    nomes_comerciais: list[str],
    data_emissao: str,
    validade_meses: int,
) -> int | None:
    """Varre nós `item` de compras de farmácia que casam com o medicamento.

    Critérios conjugados:
      1. Node tipo `item` com metadata.descricao contendo o princípio ativo
         ou um dos nomes comerciais.
      2. metadata.data_compra dentro da janela [data_emissao, data_emissao +
         validade_meses * 30 dias] -- receita só faz sentido no período de
         validade.

    Devolve o primeiro candidato. Ambiguidade (múltiplos casamentos) é aceita
    aqui -- Sprint 48 refina com rapidfuzz e threshold de confiança.
    """
    if not principio_ativo and not nomes_comerciais:
        return None
    try:
        data_emissao_dt = date.fromisoformat(data_emissao[:10])
    except (ValueError, TypeError):
        return None

    janela_fim = data_emissao_dt + timedelta(days=validade_meses * 30)

    alvos: list[str] = []
    if principio_ativo:
        alvos.append(principio_ativo.upper().strip())
    for nome in nomes_comerciais:
        if nome:
            alvos.append(nome.upper().strip())

    for node in db.listar_nodes("item"):
        meta = node.metadata
        descricao_item = (meta.get("descricao") or node.nome_canonico or "").upper()
        if not any(alvo in descricao_item for alvo in alvos):
            continue
        data_compra = meta.get("data_compra")
        if not isinstance(data_compra, str):
            continue
        try:
            dc = date.fromisoformat(data_compra[:10])
        except ValueError:
            continue
        if not (data_emissao_dt <= dc <= janela_fim):
            continue
        if node.id is not None:
            return node.id
    return None


# ============================================================================
# Ingestão de garantia de fabricante (Sprint 47b)
# ============================================================================

CAMPOS_OBRIGATORIOS_GARANTIA: tuple[str, ...] = (
    "chave_garantia",
    "fornecedor_cnpj",
    "data_inicio",
    "prazo_meses",
)


def ingerir_garantia(
    db: GrafoDB,
    garantia: dict[str, Any],
    caminho_arquivo: Path | None = None,
) -> int:
    """Insere termo de garantia de fabricante (Sprint 47b) e suas arestas.

    Modela garantia NATIVA do produto ou do varejista (pedido) -- distinta
    da Sprint 47c (`ingerir_apolice`: garantia estendida SUSEP com seguradora).
    Campos obrigatórios: chave_garantia (`GAR|<cnpj>|<serial>|<data>`),
    fornecedor_cnpj, data_inicio (YYYY-MM-DD), prazo_meses. Opcionais
    preservados em metadata: data_fim, produto, numero_serie, fornecedor_nome,
    categoria_produto, condicoes, tipo_garantia, expirando. Campos com
    prefixo `_` são filtrados. Arestas: garantia->fornecedor (emitida_por),
    garantia->periodo (ocorre_em), garantia->item (cobre, opcional via
    `localizar_item`). Idempotente: chave_garantia única. Devolve id do nó.
    """
    for campo in CAMPOS_OBRIGATORIOS_GARANTIA:
        if garantia.get(campo) in (None, ""):
            raise ValueError(
                f"garantia sem '{campo}' -- ingestão abortada (nó garantia ou aresta ficaria órfão)"
            )
    metadata = {
        chave: valor
        for chave, valor in garantia.items()
        if valor is not None and not chave.startswith("_")
    }
    metadata.setdefault("tipo_documento", "garantia_fabricante")
    if caminho_arquivo is not None:
        metadata["arquivo_origem"] = to_relativo(caminho_arquivo)
    metadata["pessoa"] = _inferir_pessoa_canonica(garantia, caminho_arquivo)

    garantia_id = db.upsert_node(
        "garantia",
        garantia["chave_garantia"],
        metadata=metadata,
    )
    fornecedor_id = upsert_fornecedor(
        db,
        garantia["fornecedor_cnpj"],
        razao_social=garantia.get("fornecedor_nome"),
    )
    db.adicionar_edge(garantia_id, fornecedor_id, "emitida_por")
    mes_ref = _extrair_mes_ref(garantia["data_inicio"])
    if mes_ref:
        periodo_id = upsert_periodo(db, mes_ref)
        db.adicionar_edge(garantia_id, periodo_id, "ocorre_em")

    # Linking opcional: item já ingerido de NF (44/44b/45) via localizar_item
    # (mesmo casamento heurístico da apólice 47c: cnpj+janela+rapidfuzz).
    produto_descricao = garantia.get("produto") or garantia.get("bem_segurado") or ""
    if produto_descricao:
        item_id = localizar_item(
            db,
            descricao=produto_descricao,
            cnpj_varejo=garantia["fornecedor_cnpj"],
            data_iso=garantia["data_inicio"],
        )
        if item_id is not None:
            db.adicionar_edge(
                garantia_id,
                item_id,
                "cobre",
                evidencia={"match": "descricao+cnpj+janela_data"},
            )
            logger.info(
                "garantia %s linkada a item %s via 'cobre'", garantia["chave_garantia"], item_id
            )

    if garantia.get("expirando"):
        logger.warning(
            "garantia %s (produto %s) expira em %s -- faltam <=30 dias",
            garantia["chave_garantia"],
            produto_descricao or "?",
            garantia.get("data_fim"),
        )
    logger.info(
        "garantia %s ingerida: fornecedor %s, prazo %s meses",
        garantia["chave_garantia"],
        garantia["fornecedor_cnpj"],
        garantia["prazo_meses"],
    )
    return garantia_id


# "Saúde e patrimônio são memórias materiais;
# o grafo só as conserva." -- princípio do arquivista vital
