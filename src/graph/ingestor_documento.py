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

import functools
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from src.graph.db import GrafoDB
from src.graph.path_canonico import to_relativo
from src.utils.logger import configurar_logger

logger = configurar_logger("graph.ingestor_documento")


JANELA_MATCH_ITEM_DIAS: int = 1
THRESHOLD_DESCRICAO: int = 82
MARGEM_DESEMPATE: int = 5


# ============================================================================
# Sprint AUDIT2-METADATA-PESSOA-CANONICA: inferir pessoa no metadata
# ============================================================================


def _inferir_pessoa_canonica(
    documento: dict[str, Any],
    caminho_arquivo: Path | None,
) -> str:
    """Infere a pessoa canonica (andre/vitoria/casal) para um documento.

    Ordem (curto-circuito no primeiro hit):
    1. `documento.contribuinte` ou `documento.__contribuinte_original`
       contem ANDRE/VITORIA (case-insensitive).
    2. `caminho_arquivo` esta em `data/raw/andre/` ou `data/raw/vitoria/`.
    3. Fallback `casal` (ADR-conforme: nunca chuta sem evidencia).

    Heuristica leve (sem invocar OCR ou pessoa_detector cheio) — o
    documento ja foi parseado pelo extractor e tem campos relevantes.
    """
    contribuinte = (
        str(documento.get("__contribuinte_original") or documento.get("contribuinte") or "")
        .upper()
    )
    if "ANDRE" in contribuinte or "ANDRÉ" in contribuinte:
        return "andre"
    if "VITORIA" in contribuinte or "VITÓRIA" in contribuinte:
        return "vitoria"
    if caminho_arquivo is not None:
        partes = {p.lower() for p in Path(caminho_arquivo).parts}
        if "andre" in partes:
            return "andre"
        if "vitoria" in partes:
            return "vitoria"
        if "casal" in partes:
            return "casal"
    return "casal"

# ============================================================================
# Sprint 107: fornecedores sintéticos para impostos
# ============================================================================

_PATH_FORNECEDORES_SINTETICOS: Path = (
    Path(__file__).resolve().parents[2] / "mappings" / "fornecedores_sinteticos.yaml"
)


@functools.lru_cache(maxsize=1)
def _carregar_fornecedores_sinteticos() -> tuple[tuple[str, dict[str, Any]], ...]:
    """AUDIT-CACHE-THREADSAFE: usa lru_cache(maxsize=1) em vez de global mutavel.

    Schema esperado:
        fornecedores:
          RECEITA_FEDERAL:
            cnpj: "00394460000141"
            razao_social: "Receita Federal do Brasil"
            aplica_a_tipos: [das_parcsn_andre, ...]

    Devolve tupla imutável de (tipo_documento, dict) para compatibilidade com
    lru_cache (que exige retorno hashable). Caller converte para dict via dict().
    """
    import yaml

    if not _PATH_FORNECEDORES_SINTETICOS.exists():
        return ()

    with _PATH_FORNECEDORES_SINTETICOS.open(encoding="utf-8") as fh:
        dados = yaml.safe_load(fh) or {}

    fornecedores = dados.get("fornecedores", {}) or {}
    invertido: list[tuple[str, dict[str, Any]]] = []
    for nome, info in fornecedores.items():
        cnpj = info.get("cnpj") or ""
        razao = info.get("razao_social") or nome
        for tipo in info.get("aplica_a_tipos", []) or []:
            invertido.append(
                (
                    tipo,
                    {
                        "nome_canonico": nome,
                        "cnpj": cnpj,
                        "razao_social": razao,
                    },
                )
            )
    return tuple(invertido)


def _resolver_fornecedor_sintetico(tipo_documento: str) -> dict[str, Any] | None:
    """Retorna sintético {cnpj, razao_social, nome_canonico} ou None."""
    if not tipo_documento:
        return None
    for tipo, info in _carregar_fornecedores_sinteticos():
        if tipo == tipo_documento:
            return info
    return None


def _resetar_cache_sinteticos() -> None:
    """Helper para testes -- delega para lru_cache.cache_clear()."""
    _carregar_fornecedores_sinteticos.cache_clear()


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
        metadata["arquivo_origem"] = to_relativo(caminho_arquivo)
    metadata["pessoa"] = _inferir_pessoa_canonica(bilhete, caminho_arquivo)

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


# ============================================================================
# Sprint INFRA-NFCE-DEDUP-OCR-DUPLICATAS: dedup tolerante a ruído de OCR
# ============================================================================

#: Diferença máxima padrão entre duas chave_44 (Levenshtein) para serem
#: consideradas a mesma NFCe quando os demais critérios duros casam.
#: Spec original (2026-05-12) propôs 4; auditoria empírica nos 4 nodes reais
#: do grafo apontou distâncias 9 e 10. Default conservador 4 é mantido para
#: o ingestor (preferir não-fundir a fundir errado); script retroativo passa
#: limite calibrado via parâmetro.
LIMITE_DIFF_CHAVE_44_PADRAO: int = 4


def _distancia_chave(chave_a: str, chave_b: str) -> int:
    """Distância de Levenshtein entre dois dígitos de chave_44 normalizados.

    Usa rapidfuzz (já no requirements -- mesma lib usada em fuzz no item match).
    Comparação operada após normalização básica (strip + dígitos apenas).
    """
    from rapidfuzz.distance import Levenshtein

    a_norm = "".join(ch for ch in (chave_a or "") if ch.isdigit())
    b_norm = "".join(ch for ch in (chave_b or "") if ch.isdigit())
    if not a_norm or not b_norm:
        return max(len(a_norm), len(b_norm))
    return int(Levenshtein.distance(a_norm, b_norm))


def _eh_mesma_nfce(
    chave_a: str,
    chave_b: str,
    total_a: float | int | str | None,
    total_b: float | int | str | None,
    data_a: str | None,
    data_b: str | None,
    cnpj_a: str | None,
    cnpj_b: str | None,
    limite_diff_chave: int = LIMITE_DIFF_CHAVE_44_PADRAO,
) -> bool:
    """True quando duas NFCe são plausivelmente o mesmo cupom físico.

    Quatro critérios duros (todos precisam casar):

      1. Levenshtein(chave_a, chave_b) <= ``limite_diff_chave`` (tolerância OCR)
      2. ``total_a == total_b`` (R$ 0,00 de diferença -- centavos batem)
      3. ``data_a == data_b`` (mesma data de emissão, comparada por prefixo 10)
      4. ``cnpj_a == cnpj_b`` (mesmo emitente, dígitos normalizados)

    Conservador: na dúvida (qualquer campo None), retorna False.
    Mesma chave (distância 0) também retorna True -- caso idempotente.
    """
    if not chave_a or not chave_b:
        return False
    if total_a is None or total_b is None:
        return False
    if not data_a or not data_b:
        return False
    if not cnpj_a or not cnpj_b:
        return False

    # Critério 4: CNPJ emitente (compara só dígitos para escapar de máscara)
    cnpj_a_norm = "".join(ch for ch in str(cnpj_a) if ch.isdigit())
    cnpj_b_norm = "".join(ch for ch in str(cnpj_b) if ch.isdigit())
    if cnpj_a_norm != cnpj_b_norm:
        return False

    # Critério 3: data (compara só YYYY-MM-DD, ignora hora)
    if str(data_a)[:10] != str(data_b)[:10]:
        return False

    # Critério 2: total exato (centavos batem; comparação numérica explícita)
    try:
        if round(float(total_a), 2) != round(float(total_b), 2):
            return False
    except (TypeError, ValueError):
        return False

    # Critério 1: chave_44 próxima (tolerância OCR)
    if _distancia_chave(chave_a, chave_b) > limite_diff_chave:
        return False

    return True


def _localizar_nfce_irma(
    db: GrafoDB,
    documento: dict[str, Any],
    limite_diff_chave: int = LIMITE_DIFF_CHAVE_44_PADRAO,
) -> int | None:
    """Procura um node ``documento`` NFCe já existente que case via _eh_mesma_nfce.

    Filtro inicial barato no SQL (mesmo CNPJ + mesma data + mesmo total) e em
    seguida aplica _eh_mesma_nfce para validar a tolerância de OCR na chave.
    Devolve o id do candidato ou None.
    """
    chave_self = str(documento.get("chave_44") or "")
    total_self = documento.get("total")
    data_self = str(documento.get("data_emissao") or "")[:10]
    cnpj_self = str(documento.get("cnpj_emitente") or "")
    if not (chave_self and total_self is not None and data_self and cnpj_self):
        return None

    cursor = db._conn.execute(  # noqa: SLF001 -- API interna intencional p/ ler nodes
        """
        SELECT id, metadata FROM node
        WHERE tipo = 'documento'
          AND json_extract(metadata, '$.tipo_documento') = 'nfce_modelo_65'
          AND json_extract(metadata, '$.data_emissao') = ?
        """,
        (data_self,),
    )
    import json as _json

    for node_id, meta_raw in cursor.fetchall():
        try:
            meta = _json.loads(meta_raw) if meta_raw else {}
        except (TypeError, _json.JSONDecodeError):
            continue
        if str(meta.get("chave_44") or "") == chave_self:
            # mesma chave -> idempotente, upsert normal cobre. Não é "irmã".
            continue
        if _eh_mesma_nfce(
            chave_self,
            str(meta.get("chave_44") or ""),
            total_self,
            meta.get("total"),
            data_self,
            str(meta.get("data_emissao") or "")[:10],
            cnpj_self,
            str(meta.get("cnpj_emitente") or ""),
            limite_diff_chave=limite_diff_chave,
        ):
            return int(node_id)
    return None


def _completude_nfce(meta: dict[str, Any]) -> int:
    """Mede completude de uma NFCe pelo número de itens com qtde > 0.

    Critério de desempate quando duas NFCe são "a mesma" (OCR alt vs original):
    a com mais itens válidos vence.
    """
    itens = meta.get("itens") if isinstance(meta, dict) else None
    if not isinstance(itens, list):
        return 0
    return sum(
        1
        for it in itens
        if isinstance(it, dict) and float(it.get("qtde") or 0.0) > 0.0
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

    # Sprint 107: troca fornecedor pelo sintético quando tipo_documento casa
    # (ex: DAS PARCSN -> RECEITA_FEDERAL). Contribuinte preservado em metadata.
    sintetico = _resolver_fornecedor_sintetico(documento.get("tipo_documento", ""))
    if sintetico is not None:
        documento = dict(documento)  # copia local para não mutar caller
        documento["__contribuinte_original"] = documento.get("razao_social", "")
        documento["cnpj_emitente"] = sintetico["cnpj"]
        documento["razao_social"] = sintetico["razao_social"]

    metadata = {
        chave: valor
        for chave, valor in documento.items()
        if valor is not None and not chave.startswith("_")
    }
    metadata.setdefault("tipo_documento", "documento_fiscal")
    if caminho_arquivo is not None:
        metadata["arquivo_origem"] = to_relativo(caminho_arquivo)
    if sintetico is not None:
        # AUDIT-CONTRIBUINTE-METADATA: sempre grava (mesmo vazio) para sinalizar
        # que o sintético foi aplicado -- auditoria via SQL pode consultar.
        metadata["contribuinte"] = documento.get("__contribuinte_original", "")
    metadata["pessoa"] = _inferir_pessoa_canonica(documento, caminho_arquivo)

    # Sprint AUDIT2-METADATA-ITENS-LISTA: espelha itens granulares no
    # metadata para a auditoria 4-way no Revisor. Caller pode pre-preencher
    # `documento["itens"]` (caso holerite, sem upsert_item por não ter código)
    # ou deixar que o ingestor monte a lista a partir do argumento `itens`
    # (caso NFC-e / DANFE que também cria nodes item via upsert_item).
    if "itens" not in metadata or not isinstance(metadata.get("itens"), list):
        metadata["itens"] = [
            {
                "descricao": str(it.get("descricao", "")),
                "valor_total": float(it.get("valor_total") or 0.0),
                "qtde": float(it.get("qtde") or 1.0),
                "codigo": str(it.get("codigo", "") or ""),
            }
            for it in (itens or [])
            if it.get("descricao")
        ]

    # Sprint INFRA-NFCE-DEDUP-OCR-DUPLICATAS: para NFCe modelo 65, antes de criar
    # um novo node, procura uma NFCe-irmã (mesma data + CNPJ + total exato, chave
    # com diff <= 4 -- tolerância OCR). Se achar, faz UPDATE no node existente
    # quando a versão nova tem mais itens (mais completude); caso contrário,
    # apenas devolve o id existente sem criar duplicado.
    documento_id: int | None = None
    if metadata.get("tipo_documento") == "nfce_modelo_65":
        irma_id = _localizar_nfce_irma(db, documento)
        if irma_id is not None:
            irma = db.buscar_node_por_id(irma_id)
            completude_nova = _completude_nfce(metadata)
            completude_irma = _completude_nfce(irma.metadata if irma else {})
            if completude_nova > completude_irma:
                # versão nova é mais completa -> sobrescreve metadata da irmã
                # mas preserva chave_44 antiga como alias (auditoria).
                logger.info(
                    "NFCe dedup: node %d (chave %s) é mais completo que irmã "
                    "%d (chave %s) -- fundindo metadata, mantendo node existente",
                    irma_id,
                    documento["chave_44"],
                    irma_id,
                    irma.metadata.get("chave_44") if irma else "?",
                )
                # upsert_node faz merge raso -- usa chave_canonica da irmã
                # para não criar node novo.
                chave_irma = irma.nome_canonico if irma else documento["chave_44"]
                # registra a chave alternativa no metadata e nos aliases
                metadata["chave_44_alternativa"] = (
                    irma.metadata.get("chave_44") if irma else None
                )
                documento_id = db.upsert_node(
                    "documento",
                    chave_irma,
                    metadata=metadata,
                    aliases=[documento["chave_44"]],
                )
            else:
                logger.info(
                    "NFCe dedup: ignorando upsert de %s -- node %d já é a mesma "
                    "NFCe e tem completude maior ou igual",
                    documento["chave_44"],
                    irma_id,
                )
                documento_id = irma_id
    if documento_id is None:
        documento_id = db.upsert_node(
            "documento", documento["chave_44"], metadata=metadata
        )

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
# Sprint INFRA-EXTRATOR-CUPOM-FOTO: adapter schema_opus_ocr -> documento_fiscal
# ============================================================================


CAMPOS_OBRIGATORIOS_PAYLOAD_OPUS: tuple[str, ...] = (
    "sha256",
    "tipo_documento",
    "estabelecimento",
    "data_emissao",
    "itens",
    "total",
)


def ingerir_cupom_foto(
    db: GrafoDB,
    payload_opus: dict[str, Any],
    caminho_arquivo: Path | None = None,
) -> int:
    """Ingere um cupom fiscal fotografado a partir do payload canônico do Opus.

    `payload_opus` segue o schema de ``mappings/schema_opus_ocr.json``
    (saída de ``src.extractors.opus_visao.extrair_via_opus``). Esta função
    é um adapter fino: traduz o schema canônico para o formato esperado
    por ``ingerir_documento_fiscal`` e delega.

    Persistência no grafo (via ``ingerir_documento_fiscal``):

    - 1 nó ``documento`` (chave canônica ``CUPOMFOTO|<sha256>``)
    - 1 nó ``fornecedor`` (CNPJ canônico do estabelecimento)
    - N nós ``item`` (1 por item do cupom)
    - 1 aresta ``fornecido_por`` (documento -> fornecedor) -- equivalente
      semântico de ``emitida_por`` para documentos fiscais sem campo
      "emitente" separado de "fornecedor"
    - 1 aresta ``ocorre_em`` (documento -> periodo)
    - N arestas ``contem_item`` (documento -> item)

    Itens sem código (``codigo`` nulo) recebem código sintético
    ``SEMCOD<NNNN>`` derivado da posição na lista para preservar a
    chave canônica ``<cnpj>|<data>|<codigo>`` do nó ``item``. Itens sem  # noqa: accent
    descrição são descartados (decisão de ``ingerir_documento_fiscal``).

    Idempotente: chave do documento usa o sha256 da imagem, então
    reprocessar o mesmo arquivo nunca duplica nós nem arestas.

    Pendências (``aguardando_supervisor=True``) são rejeitadas com
    ``ValueError`` -- não há dados suficientes para ingerir.

    Devolve o id do nó ``documento`` criado/atualizado.
    """
    if payload_opus.get("aguardando_supervisor"):
        raise ValueError(
            "payload_opus está em estado 'aguardando_supervisor' -- "
            "supervisor humano ainda não transcreveu a imagem. "
            "Ingestão abortada para evitar nó de documento órfão."
        )

    for campo in CAMPOS_OBRIGATORIOS_PAYLOAD_OPUS:
        if not payload_opus.get(campo):
            raise ValueError(
                f"payload_opus sem '{campo}' -- não respeita schema_opus_ocr; "
                "ingestão abortada"
            )

    estabelecimento = payload_opus.get("estabelecimento") or {}
    cnpj = estabelecimento.get("cnpj") or ""
    if not cnpj:
        raise ValueError(
            "payload_opus.estabelecimento.cnpj vazio -- nó fornecedor ficaria órfão"
        )

    sha = payload_opus["sha256"]
    documento: dict[str, Any] = {
        "chave_44": f"CUPOMFOTO|{sha}",
        "cnpj_emitente": cnpj,
        "data_emissao": payload_opus["data_emissao"],
        "tipo_documento": "cupom_fiscal_foto",
        "razao_social": estabelecimento.get("razao_social"),
        "endereco": estabelecimento.get("endereco"),
        "total": float(payload_opus["total"]),
        "forma_pagamento": payload_opus.get("forma_pagamento"),
        "extraido_via": payload_opus.get("extraido_via"),
        "confianca_global": payload_opus.get("confianca_global"),
        "horario": payload_opus.get("horario"),
        "operador": payload_opus.get("operador"),
        "sha256_imagem": sha,
    }

    itens_brutos = payload_opus.get("itens") or []
    itens_canonicos: list[dict[str, Any]] = []
    contador_sem_cod = 0
    for item in itens_brutos:
        descricao = (item.get("descricao") or "").strip()
        if not descricao:
            continue
        codigo = (item.get("codigo") or "").strip()
        if not codigo:
            contador_sem_cod += 1
            codigo = f"SEMCOD{contador_sem_cod:04d}"
        valor_total = item.get("valor_total")
        if valor_total is None:
            continue
        qtde = item.get("qtd") or 1.0
        itens_canonicos.append(
            {
                "codigo": codigo,
                "descricao": descricao,
                "qtde": float(qtde),
                "unidade": item.get("unidade"),
                "valor_unit": item.get("valor_unit"),
                "valor_total": float(valor_total),
            }
        )

    documento_id = ingerir_documento_fiscal(
        db,
        documento,
        itens_canonicos,
        caminho_arquivo=caminho_arquivo,
    )
    logger.info(
        "cupom_foto ingerido: sha=%s itens=%d total=R$ %.2f",
        sha[:12],
        len(itens_canonicos),
        documento["total"],
    )
    return documento_id


# ============================================================================
# Sprint MOB-bridge-5: ingestão de comprovante PIX (foto) no grafo
# ============================================================================


CAMPOS_OBRIGATORIOS_PAYLOAD_PIX: tuple[str, ...] = (
    "sha256",
    "tipo_documento",
    "estabelecimento",
    "data_emissao",
    "total",
)


def _cnpj_sintetico_pix(payload_opus: dict[str, Any]) -> str:
    """Gera CNPJ sintético determinístico para destinatário PIX sem CNPJ.

    Decisão arquitetural MOB-bridge-5 (opção (a) com fallback):

    - Comprovantes PIX para CPF de pessoa física não trazem CNPJ canônico
      do recebedor. Para reaproveitar a infra de ``ingerir_documento_fiscal``
      (que exige ``cnpj_emitente`` para criar nó ``fornecedor``), montamos
      um identificador sintético baseado em dados estáveis do payload.
    - Prioridade da chave de derivação (do mais específico para o menos):
        1. ``_pix.chave_destinatario`` (email/telefone/CPF do recebedor)
        2. ``_pix.destinatario_cpf_mascarado``
        3. ``estabelecimento.razao_social`` (nome do recebedor)
        4. ``sha256`` do comprovante (último recurso)
    - Formato do identificador: ``PIX|<sha8_da_chave>`` -- 12 chars, prefixo
      ``PIX|`` para distinguir de CNPJ real (que tem 18 chars com pontuação).
      Não respeita o padrão de pontuação ``XX.XXX.XXX/XXXX-XX`` deliberadamente,
      para que análises retroativas via SQL filtrem facilmente
      (``WHERE cnpj LIKE 'PIX|%'``).
    - Se o payload trouxer ``estabelecimento.cnpj`` real (caso PIX para PJ),
      esta função NÃO é chamada -- ``ingerir_comprovante_pix_foto`` usa o
      CNPJ direto.

    Determinismo: a mesma chave PIX sempre gera o mesmo identificador,
    permitindo dedup automático no grafo (ex: vários PIX para o mesmo
    destinatário caem no mesmo nó ``fornecedor``).
    """
    import hashlib

    pix = payload_opus.get("_pix") or {}
    candidatos = (
        pix.get("chave_destinatario"),
        pix.get("destinatario_cpf_mascarado"),
        (payload_opus.get("estabelecimento") or {}).get("razao_social"),
        payload_opus.get("sha256"),
    )
    chave_bruta = next(
        (str(c) for c in candidatos if c and str(c).strip()),
        payload_opus.get("sha256", ""),
    )
    sha8 = hashlib.sha256(chave_bruta.encode("utf-8")).hexdigest()[:8]
    return f"PIX|{sha8}"


def ingerir_comprovante_pix_foto(
    db: GrafoDB,
    payload_opus: dict[str, Any],
    caminho_arquivo: Path | None = None,
) -> int:
    """Ingere um comprovante PIX fotografado a partir do payload canônico do Opus.

    Sprint MOB-bridge-5 -- conecta o extrator dedicado (DOC-27) ao grafo.

    ``payload_opus`` segue o schema de ``mappings/schema_opus_ocr.json``
    (saída de ``src.extractors.opus_visao.extrair_via_opus``) com bloco
    extra ``_pix`` carregando metadados específicos do comprovante (E2E,
    chave PIX, banco origem/destino, CPFs mascarados, etc.).

    Persistência no grafo (via ``ingerir_documento_fiscal``):

    - 1 nó ``documento`` (chave canônica ``PIX|<sha256>``)
    - 1 nó ``fornecedor`` (CNPJ canônico do destinatário OU CNPJ sintético
      ``PIX|<sha8>`` quando o recebedor é pessoa física sem CNPJ -- caso
      mais comum em PIX P2P; ver ``_cnpj_sintetico_pix``)
    - 1 aresta ``fornecido_por`` (documento -> fornecedor)
    - 1 aresta ``ocorre_em`` (documento -> periodo)

    Diferenças deliberadas em relação a ``ingerir_cupom_foto``:

    - **Não cria nós ``item``**: PIX é transferência monolítica de valor
      (1 evento = 1 movimentação), sem granularidade de produto fiscal.
      Os ``itens`` do payload (1 entrada com descrição do motivo do PIX)
      ficam apenas no ``metadata["itens"]`` do documento para auditoria.
    - **Sem aresta ``contem_item``**: nada para conter.
    - **CNPJ sintético**: PIX a CPF não tem CNPJ canônico; usamos
      ``PIX|<sha8_chave>`` para preservar idempotência e dedup do
      destinatário entre múltiplos PIX.

    Idempotente: chave do documento usa ``PIX|<sha256_imagem>``; o
    fornecedor é chaveado por CNPJ (real ou sintético). Reprocessar a
    mesma foto nunca duplica nós nem arestas.

    Pendências (``aguardando_supervisor=True``) são rejeitadas com
    ``ValueError`` -- não há dados suficientes para ingerir.

    Não faz linking PIX -> transação no extrato. Essa lógica vive em
    sprint dedicada (``INFRA-LINKAR-PIX-TRANSACAO``, P1), que casa o
    ``id_transacao`` E2E do comprovante com a linha do extrato bancário
    por valor + data.

    Devolve o id do nó ``documento`` criado/atualizado.
    """
    if payload_opus.get("aguardando_supervisor"):
        raise ValueError(
            "payload_opus está em estado 'aguardando_supervisor' -- "
            "supervisor humano ainda não transcreveu a imagem. "
            "Ingestão abortada para evitar nó de documento órfão."
        )

    for campo in CAMPOS_OBRIGATORIOS_PAYLOAD_PIX:
        if not payload_opus.get(campo):
            raise ValueError(
                f"payload_opus sem '{campo}' -- não respeita schema_opus_ocr "
                "para comprovante_pix_foto; ingestão abortada"
            )

    if payload_opus.get("tipo_documento") != "comprovante_pix_foto":
        raise ValueError(
            f"payload_opus.tipo_documento={payload_opus.get('tipo_documento')!r}; "
            "esperado 'comprovante_pix_foto'. Ingestão abortada."
        )

    estabelecimento = payload_opus.get("estabelecimento") or {}
    razao_social = estabelecimento.get("razao_social") or ""
    if not razao_social.strip():
        raise ValueError(
            "payload_opus.estabelecimento.razao_social vazio -- "
            "destinatário PIX sem nome canônico; nó fornecedor ficaria órfão"
        )

    cnpj_real = (estabelecimento.get("cnpj") or "").strip()
    if cnpj_real:
        cnpj_emitente = cnpj_real
        cnpj_origem = "real_do_payload"
    else:
        cnpj_emitente = _cnpj_sintetico_pix(payload_opus)
        cnpj_origem = "sintetico_PIX_chave_destinatario"

    sha = payload_opus["sha256"]
    pix_meta = payload_opus.get("_pix") or {}

    # Itens preservados no metadata para auditoria 4-way (1 entrada típica
    # com descrição do motivo do PIX). Sem upsert_item -- ver docstring.
    itens_metadata: list[dict[str, Any]] = []
    for item in payload_opus.get("itens") or []:
        descricao = (item.get("descricao") or "").strip()
        if not descricao:
            continue
        itens_metadata.append(
            {
                "descricao": descricao,
                "valor_total": float(item.get("valor_total") or 0.0),
                "qtde": float(item.get("qtd") or item.get("qtde") or 1.0),
                "codigo": str(item.get("codigo") or ""),
            }
        )

    documento: dict[str, Any] = {
        "chave_44": f"PIX|{sha}",
        "cnpj_emitente": cnpj_emitente,
        "data_emissao": payload_opus["data_emissao"],
        "tipo_documento": "comprovante_pix_foto",
        "razao_social": razao_social,
        "endereco": estabelecimento.get("endereco"),
        "total": float(payload_opus["total"]),
        "forma_pagamento": payload_opus.get("forma_pagamento") or "pix",
        "extraido_via": payload_opus.get("extraido_via"),
        "confianca_global": payload_opus.get("confianca_global"),
        "horario": payload_opus.get("horario"),
        "sha256_imagem": sha,
        "cnpj_origem": cnpj_origem,
        # Bloco PIX preserva metadados do comprovante (E2E, banco origem/destino,
        # CPFs mascarados) para o linker PIX->transação futuro. Mantemos PII
        # mascarada dentro de metadata; logs INFO devem mascarar via padrão (bb).
        "pix_id_transacao": pix_meta.get("id_transacao"),
        "pix_chave_destinatario": pix_meta.get("chave_destinatario"),
        "pix_banco_origem": pix_meta.get("banco_origem"),
        "pix_banco_destino": pix_meta.get("banco_destino"),
        "pix_destinatario_cpf_mascarado": pix_meta.get("destinatario_cpf_mascarado"),
        "itens": itens_metadata,
    }

    # Reaproveita ingerir_documento_fiscal com lista vazia de itens granulares
    # (PIX não tem itens fiscais; veja docstring). O metadata["itens"] já está
    # populado para a auditoria 4-way não perder o motivo do PIX.
    documento_id = ingerir_documento_fiscal(
        db,
        documento,
        itens=[],  # nenhum nó ``item`` é criado para PIX
        caminho_arquivo=caminho_arquivo,
    )

    # Log mascara identificadores: apenas E2E[:8] e razão social (não-PII forte).
    e2e_curto = (pix_meta.get("id_transacao") or "")[:8] or "sem-e2e"
    logger.info(
        "comprovante_pix ingerido: sha=%s e2e=%s destinatario=%s total=R$ %.2f",
        sha[:12],
        e2e_curto,
        razao_social,
        documento["total"],
    )
    return documento_id


# ============================================================================
# Sprint ANTI-MIGUE-08: ingestores especiais movidos para modulo proprio
# ============================================================================
# As funções ``ingerir_prescricao`` e ``ingerir_garantia`` (e o helper
# privado ``_localizar_item_farmacia_por_principio``) viviam aqui até o
# split. Foram movidas para ``src.graph.ingestor_especiais`` e re-exportadas
# abaixo para preservar contratos públicos
# (``from src.graph.ingestor_documento import ingerir_prescricao``).
from src.graph.ingestor_especiais import (  # noqa: E402, F401
    CAMPOS_OBRIGATORIOS_GARANTIA,
    CAMPOS_OBRIGATORIOS_PRESCRICAO,
    _localizar_item_farmacia_por_principio,
    ingerir_garantia,
    ingerir_prescricao,
)


# "Cada documento é um nó; cada nó é uma memória." -- princípio de arquivista
