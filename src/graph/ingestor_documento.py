"""Ingestor compartilhado de documentos no grafo (Sprint 47c -- reusável 44/44b/46/47).

Sprint 47c (cupom de garantia estendida) é o primeiro caller; Sprints 44 (DANFE),
44b (NFC-e), 46 (XML NFe) e 47 (recibo) devem reusar os helpers públicos deste módulo
(upsert_fornecedor, upsert_periodo, localizar_item) sem reimplementá-los.

Tipos de nó manipulados:

- apolice     (Sprint 47c) -- chave: número do bilhete individual (15 dígitos)
- seguradora  (Sprint 47c) -- chave: CNPJ canônico
- fornecedor  (Sprint 42+) -- chave: CNPJ canônico (usado como "varejo" no 47c)
- periodo     (Sprint 42)  -- chave: YYYY-MM
- item        (futuro 44/44b) -- chave: <cnpj_varejo>|<data>|<descricao_norm>
- documento   (futuro 44/44b) -- chave: chave-44 ou número da nota
- prescricao  (Sprint 47a) -- chave: PRESC|<data>|<crm>|<hash>
- garantia    (Sprint 47b) -- chave: GAR|<cnpj>|<serial>|<data_compra>

Tipos de aresta:

- emitida_por  (apolice|prescricao|garantia -> seguradora|fornecedor)
- vendida_em   (apolice -> fornecedor/varejo)
- ocorre_em    (apolice|documento|prescricao|garantia -> periodo)
- assegura     (apolice -> item)   -- opcional; só se o item já estiver no grafo
- cobre        (garantia -> item)  -- opcional; só se o item já estiver no grafo
- fornecido_por (documento -> fornecedor)  -- futuro
- contem_item   (documento -> item)         -- futuro
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from src.graph.db import GrafoDB
from src.utils.logger import configurar_logger

logger = configurar_logger("graph.ingestor_documento")


JANELA_MATCH_ITEM_DIAS: int = 1
THRESHOLD_DESCRICAO: int = 82
MARGEM_DESEMPATE: int = 5


# ============================================================================
# Upserts de nós de apoio
# ============================================================================


def upsert_fornecedor(
    db: GrafoDB,
    cnpj: str,
    razao_social: str | None = None,
    metadata_extra: dict[str, Any] | None = None,
) -> int:
    """Upsert de fornecedor/varejo por CNPJ canônico.

    `razao_social` entra como alias (busca textual) e como metadata.
    """
    meta: dict[str, Any] = {"cnpj": cnpj}
    if razao_social:
        meta["razao_social"] = razao_social
    if metadata_extra:
        meta.update(metadata_extra)
    aliases = [razao_social] if razao_social else []
    return db.upsert_node("fornecedor", cnpj, metadata=meta, aliases=aliases)


def upsert_seguradora(
    db: GrafoDB,
    cnpj: str,
    razao_social: str,
    codigo_susep: str | None = None,
    aliases: list[str] | None = None,
    metadata_extra: dict[str, Any] | None = None,
) -> int:
    """Upsert de seguradora por CNPJ canônico.

    Código SUSEP é metadado auxiliar -- nunca chave, pois o glyph às vezes
    troca `0` por `D` (Armadilha A47c-3 da Sprint 47c).
    """
    meta: dict[str, Any] = {"cnpj": cnpj, "razao_social": razao_social}
    if codigo_susep:
        meta["codigo_susep"] = codigo_susep
    if metadata_extra:
        meta.update(metadata_extra)
    aliases_unicos = sorted({razao_social, *(aliases or [])})
    return db.upsert_node("seguradora", cnpj, metadata=meta, aliases=aliases_unicos)


def upsert_periodo(db: GrafoDB, mes_yyyy_mm: str) -> int:
    """Upsert do nó 'periodo' no formato YYYY-MM."""
    return db.upsert_node("periodo", mes_yyyy_mm, metadata={"mes": mes_yyyy_mm})


# ============================================================================
# Ingestão de apólice (Sprint 47c)
# ============================================================================


CAMPOS_OBRIGATORIOS_APOLICE: tuple[str, ...] = (
    "numero_bilhete",
    "seguradora_cnpj",
    "varejo_cnpj",
)


def ingerir_apolice(
    db: GrafoDB,
    bilhete: dict[str, Any],
    caminho_arquivo: Path | None = None,
) -> int:
    """Insere uma apólice de seguro (bilhete de garantia estendida) e suas arestas.

    Campos esperados em `bilhete` (os 3 primeiros são obrigatórios):

        numero_bilhete:          15 dígitos, chave canônica do nó apolice
        seguradora_cnpj:         CNPJ canônico XX.XXX.XXX/XXXX-XX
        varejo_cnpj:             CNPJ canônico do estabelecimento varejista
        processo_susep:          XXXXX.XXXXXX/XXXX-XX
        cpf_segurado:            CPF canônico XXX.XXX.XXX-XX
        bem_segurado:            descrição textual do item coberto
        valor_bem:               R$ (limite máximo de indenização)
        premio_liquido:          R$
        iof:                     R$
        premio_total:            R$ (soma de premio_liquido + iof)
        forma_pagamento:         string crua (ex.: "PARCELA ÚNICA: 53,98")
        vigencia_inicio:         YYYY-MM-DD
        vigencia_fim:            YYYY-MM-DD
        cobertura_inicio:        YYYY-MM-DD
        cobertura_fim:           YYYY-MM-DD
        seguradora_razao_social: string
        seguradora_codigo_susep: string de 5 dígitos
        varejo_razao_social:     string
        varejo_endereco:         string
        data_emissao:            YYYY-MM-DD

    Campos não listados acima são preservados em `metadata` desde que não
    comecem com `_` (prefixo reservado para dados internos do extrator).

    Arestas criadas:
        apolice -> seguradora (emitida_por)
        apolice -> varejo     (vendida_em)
        apolice -> periodo    (ocorre_em)
        apolice -> item       (assegura) -- só se houver match por
                                             descrição + varejo + janela temporal

    Idempotente: rodar duas vezes com o mesmo bilhete NÃO duplica arestas
    (graças ao UNIQUE(src,dst,tipo) do schema.sql).

    Devolve o id do nó apolice.
    """
    for campo in CAMPOS_OBRIGATORIOS_APOLICE:
        if not bilhete.get(campo):
            raise ValueError(
                f"bilhete sem '{campo}' -- ingestão abortada (nó apolice ou aresta ficaria órfã)"
            )

    metadata = {
        chave: valor
        for chave, valor in bilhete.items()
        if valor is not None and not chave.startswith("_")
    }
    metadata["tipo_documento"] = "cupom_garantia_estendida"
    if caminho_arquivo is not None:
        metadata["arquivo_origem"] = str(caminho_arquivo)

    apolice_id = db.upsert_node("apolice", bilhete["numero_bilhete"], metadata=metadata)

    seguradora_id = upsert_seguradora(
        db,
        bilhete["seguradora_cnpj"],
        bilhete.get("seguradora_razao_social", ""),
        codigo_susep=bilhete.get("seguradora_codigo_susep"),
    )
    varejo_meta = (
        {"endereco": bilhete["varejo_endereco"]} if bilhete.get("varejo_endereco") else None
    )
    varejo_id = upsert_fornecedor(
        db,
        bilhete["varejo_cnpj"],
        razao_social=bilhete.get("varejo_razao_social"),
        metadata_extra=varejo_meta,
    )

    db.adicionar_edge(apolice_id, seguradora_id, "emitida_por")
    db.adicionar_edge(apolice_id, varejo_id, "vendida_em")

    data_referencia = bilhete.get("data_emissao") or bilhete.get("vigencia_inicio")
    mes_ref = _extrair_mes_ref(data_referencia)
    if mes_ref:
        periodo_id = upsert_periodo(db, mes_ref)
        db.adicionar_edge(apolice_id, periodo_id, "ocorre_em")

    item_id = localizar_item(
        db,
        descricao=bilhete.get("bem_segurado", ""),
        cnpj_varejo=bilhete["varejo_cnpj"],
        data_iso=data_referencia,
    )
    if item_id is not None:
        db.adicionar_edge(
            apolice_id,
            item_id,
            "assegura",
            evidencia={"match": "descricao+cnpj_varejo+janela_data"},
        )
        logger.info("apolice %s linkada a item %s via 'assegura'", apolice_id, item_id)
    else:
        logger.debug(
            "apolice %s sem item pareado (Sprint 44/44b pode não ter processado NFC-e ainda)",
            apolice_id,
        )

    return apolice_id


# ============================================================================
# Matching heurístico apólice <-> item
# ============================================================================


def localizar_item(
    db: GrafoDB,
    descricao: str,
    cnpj_varejo: str,
    data_iso: str | None,
) -> int | None:
    """Tenta casar a apólice a um `item` já existente no grafo.

    Critérios conjugados:
      1. `metadata.cnpj_varejo` == `cnpj_varejo` (exato)
      2. `metadata.data_compra` dentro de ±JANELA_MATCH_ITEM_DIAS da `data_iso`
      3. `rapidfuzz.token_set_ratio(descricao)` >= THRESHOLD_DESCRICAO

    Ambiguidade (mais de um candidato com score similar) devolve None -- a
    aresta `assegura` é opcional e NUNCA deve chutar. Sprint 48 (linking global)
    pode revisitar com mais contexto.
    """
    if not descricao or not data_iso:
        return None

    candidatos = _candidatos_item(db, cnpj_varejo, data_iso)
    if not candidatos:
        return None

    descricao_norm = descricao.upper().strip()
    rankings: list[tuple[int, float]] = []
    for node_id, descricao_item in candidatos:
        score = fuzz.token_set_ratio(descricao_norm, descricao_item.upper())
        if score >= THRESHOLD_DESCRICAO:
            rankings.append((node_id, score))

    if not rankings:
        return None

    rankings.sort(key=lambda par: par[1], reverse=True)
    if len(rankings) >= 2 and (rankings[0][1] - rankings[1][1]) < MARGEM_DESEMPATE:
        logger.warning(
            "match ambíguo para '%s' (varejo %s): %d candidatos com score similar",
            descricao,
            cnpj_varejo,
            len(rankings),
        )
        return None
    return rankings[0][0]


def _candidatos_item(
    db: GrafoDB,
    cnpj_varejo: str,
    data_iso: str,
) -> list[tuple[int, str]]:
    """Varre nós `item` e filtra por cnpj_varejo + janela temporal."""
    try:
        data_ref = date.fromisoformat(data_iso[:10])
    except (ValueError, TypeError):
        return []

    janela_inicio = data_ref - timedelta(days=JANELA_MATCH_ITEM_DIAS)
    janela_fim = data_ref + timedelta(days=JANELA_MATCH_ITEM_DIAS)

    resultados: list[tuple[int, str]] = []
    for node in db.listar_nodes("item"):
        meta = node.metadata
        if meta.get("cnpj_varejo") != cnpj_varejo:
            continue
        data_compra = meta.get("data_compra")
        if not isinstance(data_compra, str):
            continue
        try:
            dc = date.fromisoformat(data_compra[:10])
        except ValueError:
            continue
        if not (janela_inicio <= dc <= janela_fim):
            continue
        descricao_item = meta.get("descricao") or node.nome_canonico
        if node.id is not None:
            resultados.append((node.id, descricao_item))
    return resultados


# ============================================================================
# Helpers internos
# ============================================================================


def _extrair_mes_ref(data_iso: str | None) -> str | None:
    """Extrai YYYY-MM de uma data ISO. Devolve None se ilegível."""
    if not isinstance(data_iso, str) or len(data_iso) < 7:
        return None
    prefixo = data_iso[:7]
    if len(prefixo) == 7 and prefixo[4] == "-":
        return prefixo
    return None


# ============================================================================
# Ingestão de documento fiscal (Sprint 44/44b)
# ============================================================================


CAMPOS_OBRIGATORIOS_DOCUMENTO: tuple[str, ...] = (
    "chave_44",
    "cnpj_emitente",
    "data_emissao",
)


def upsert_item(
    db: GrafoDB,
    cnpj_varejo: str,
    data_compra: str,
    codigo_produto: str,
    descricao: str,
    metadata_extra: dict[str, Any] | None = None,
) -> int:
    """Upsert de nó `item` com chave canônica `<cnpj_varejo>|<data>|<codigo>`.  # noqa: accent

    O mesmo produto (mesmo código) vendido em dias diferentes é item diferente,
    porque o ponto-de-referência para cruzar com apólice é a compra, não o
    SKU. A descrição textual entra como metadata e alias (facilita busca).
    """
    chave_canonica = f"{cnpj_varejo}|{data_compra[:10]}|{codigo_produto}"
    meta: dict[str, Any] = {
        "cnpj_varejo": cnpj_varejo,
        "data_compra": data_compra[:10],
        "codigo_produto": codigo_produto,
        "descricao": descricao,
    }
    if metadata_extra:
        meta.update(metadata_extra)
    aliases = [descricao] if descricao else []
    return db.upsert_node("item", chave_canonica, metadata=meta, aliases=aliases)


def ingerir_documento_fiscal(
    db: GrafoDB,
    documento: dict[str, Any],
    itens: list[dict[str, Any]],
    caminho_arquivo: Path | None = None,
) -> int:
    """Insere um documento fiscal (NFe55 ou NFC-e65) e suas arestas no grafo.

    Campos esperados em `documento` (os 3 primeiros são obrigatórios):

        chave_44:          44 dígitos, DV validado -- chave canônica do nó `documento`
        cnpj_emitente:     CNPJ canônico do varejo
        data_emissao:      YYYY-MM-DD
        tipo_documento:    "nfce_modelo_65" | "nfe_modelo_55"
        numero:            número da nota
        serie:             série da nota
        total:             float
        forma_pagamento:   string canônica ("PIX", "Crédito", "Débito", "Dinheiro")
        cpf_consumidor:    CPF do consumidor (opcional)
        razao_social:      razão social do emitente (para aliases)
        endereco:          endereço da loja

    Cada item em `itens` precisa ter: `codigo`, `descricao`, `qtde`, `valor_unit`,  # noqa: accent
    `valor_total`. O item é chaveado por (cnpj_varejo, data_compra, codigo).  # noqa: accent

    Arestas criadas:
        documento -> fornecedor (fornecido_por)
        documento -> periodo    (ocorre_em)
        documento -> item       (contem_item, uma por item)

    Idempotente: chave 44 é única; reprocessar não duplica nós nem arestas.

    Devolve o id do nó `documento`.
    """
    for campo in CAMPOS_OBRIGATORIOS_DOCUMENTO:
        if not documento.get(campo):
            raise ValueError(
                f"documento sem '{campo}' -- ingestão abortada "
                "(nó documento ou aresta ficaria órfão)"
            )

    metadata = {
        chave: valor
        for chave, valor in documento.items()
        if valor is not None and not chave.startswith("_")
    }
    metadata.setdefault("tipo_documento", "documento_fiscal")
    if caminho_arquivo is not None:
        metadata["arquivo_origem"] = str(caminho_arquivo)

    documento_id = db.upsert_node("documento", documento["chave_44"], metadata=metadata)

    fornecedor_id = upsert_fornecedor(
        db,
        documento["cnpj_emitente"],
        razao_social=documento.get("razao_social"),
        metadata_extra=({"endereco": documento["endereco"]} if documento.get("endereco") else None),
    )
    db.adicionar_edge(documento_id, fornecedor_id, "fornecido_por")

    mes_ref = _extrair_mes_ref(documento["data_emissao"])
    if mes_ref:
        periodo_id = upsert_periodo(db, mes_ref)
        db.adicionar_edge(documento_id, periodo_id, "ocorre_em")

    for item in itens:
        if not item.get("codigo") or not item.get("descricao"):
            logger.warning(
                "item sem código/descrição em documento %s -- pulado",
                documento["chave_44"],
            )
            continue
        meta_item: dict[str, Any] = {
            "qtde": item.get("qtde"),
            "unidade": item.get("unidade"),
            "valor_unit": item.get("valor_unit"),
            "valor_total": item.get("valor_total"),
        }
        # Campos opcionais ricos (Sprint 46 XML NFe): NCM/CFOP/tributos  # noqa: accent
        # federais + origem_fonte. Propagados só quando presentes; None é
        # descartado para não poluir metadata de items DANFE/NFC-e que não
        # os carregam.
        for chave_extra in (
            "ncm",
            "cfop",
            "icms_valor",
            "ipi_valor",
            "pis_valor",
            "cofins_valor",
            "origem_fonte",
        ):
            valor_extra = item.get(chave_extra)
            if valor_extra is not None:
                meta_item[chave_extra] = valor_extra
        item_id = upsert_item(
            db,
            cnpj_varejo=documento["cnpj_emitente"],
            data_compra=documento["data_emissao"],
            codigo_produto=item["codigo"],
            descricao=item["descricao"],
            metadata_extra=meta_item,
        )
        db.adicionar_edge(documento_id, item_id, "contem_item")

    logger.info(
        "documento %s ingerido: %d item(ns), fornecedor %s",
        documento["chave_44"],
        len(itens),
        documento["cnpj_emitente"],
    )
    return documento_id


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
        metadata["arquivo_origem"] = str(caminho_arquivo)

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
        metadata["arquivo_origem"] = str(caminho_arquivo)

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


# "Cada documento é um nó; cada nó é uma memória." -- princípio de arquivista
