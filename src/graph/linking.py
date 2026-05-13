"""Motor heurístico de linking documento -> transação bancária (Sprint 48 + Sprint 95).

Cria arestas `documento_de` entre nodes `documento` e nodes `transacao` quando  # noqa: accent
há correspondência forte entre data/valor/fornecedor. Quando há ambiguidade
(top-1 e top-2 com scores próximos) gera proposta Markdown em
`docs/propostas/linking/<chave>.md` em vez de linkar silenciosamente.

Heurísticas de score aplicadas (soma linear, max=1.4, min=0.0):
    base 1.0
    - peso_temporal_diario por dia de diferença (módulo); default 0.10
    - 0.50 * diff_valor_percentual (razão |v_t - total| / total)
    + 0.30 se CNPJ do documento bate com contraparte da transação
             (via aresta `contraparte` -> fornecedor que tem metadata.cnpj)
    + 0.10 adicional quando delta_dias == 0 e CNPJ bate (Pix instantâneo)

Sprint 95: o `peso_temporal_diario` é configurável por tipo. Tipos que pagam
dias depois da emissão do documento (holerite, DAS PARCSN, boleto de serviço,
DIRPF) usam peso menor (0.005-0.01) para que delta natural de 30-60 dias não
zere o score. Default mantém 0.10 (comportamento original).

Confiança final = score clamp [0, 1]. Se < confidence_minimo do tipo, gera
proposta. Se top-1 e top-2 diferem menos que `margem_empate`, gera proposta.

Exports públicos:
    carregar_config()  -> dict
    linkar_documentos_a_transacoes(db, ...) -> dict[str, int]
    candidatas_para_documento(db, doc_node, config) -> list[(tid, evidencia)]

Idempotência: aresta `documento_de` tem UNIQUE(src,dst,tipo); rodar 2x não
duplica. Proposta por (chave-documento, conflito) é deduplicada por nome de
arquivo determinístico.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from src.graph.db import GrafoDB
from src.graph.models import Node
from src.graph.queries import obter_transacoes_candidatas_para_documento
from src.utils.logger import configurar_logger

logger = configurar_logger("graph.linking")

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_PATH_CONFIG_PADRAO: Path = _RAIZ_REPO / "mappings" / "linking_config.yaml"
_PATH_PROPOSTAS_PADRAO: Path = _RAIZ_REPO / "docs" / "propostas" / "linking"

EDGE_TIPO_DOCUMENTO_DE: str = "documento_de"
EDGE_TIPO_CONTRAPARTE: str = "contraparte"
# Sprint INFRA-LINKING-HOLERITE-MULTI-FONTE (2026-05-13): aresta que marca um
# holerite como "alias da mesma realidade" de outro holerite escolhido como
# representante para o linking. Mantida no grafo para trilha de auditoria sem
# precisar mexer no schema -- apenas mais um valor de `tipo` na tabela `edge`.
EDGE_TIPO_ALIAS_REALIDADE: str = "_alias_de"

# Tolerância default (em fração de 1, ex: 0.05 = 5%) usada para considerar
# dois holerites como "mesma realidade" quando a competência coincide. Vide
# `_fundir_holerites_mesma_realidade`.
TOLERANCIA_VALOR_HOLERITE_MULTI_FONTE: float = 0.05

# Sprint INFRA-LINKING-DIRPF-TOTAL-ZERO (2026-05-13): documentos com total
# monetário nulo, zero ou abaixo de R$ 0,01 não devem entrar na heurística
# `data_valor_aproximado`. DIRPF/retificadora, contratos sem valor declarado e
# certidões frequentemente chegam ao grafo com `total=0.0`; como a métrica de
# proporção fica indefinida, qualquer transação pequena (R$ 0,01) casa
# proporcionalmente e gera 2+ candidatas dentro da margem de empate, virando
# proposta de conflito ruidosa. O filtro abaixo é defesa em camadas (padrão
# (n)): `candidatas_para_documento` devolve lista vazia e
# `linkar_documentos_a_transacoes` pula antes mesmo de consultar candidatas,
# contabilizando em `total_vazio`.
TOTAL_MINIMO_ELEGIVEL: float = 0.01

# Sprint 74 (ADR-20): classificação semântica do tipo de vínculo entre um
# documento e a transação que ele comprova. Armazenado em `evidencia.tipo_edge_semantico`
# da aresta `documento_de` para preservar idempotência e retrocompatibilidade com
# o motor da Sprint 48.
TIPO_EDGE_SEMANTICO_PAGO_COM: str = "pago_com"  # fatura/extrato que origina a transação
TIPO_EDGE_SEMANTICO_CONFIRMA: str = "confirma"  # boleto que instrui a transação
TIPO_EDGE_SEMANTICO_COMPROVANTE: str = "comprovante"  # cupom/recibo/NFC-e recebido
TIPO_EDGE_SEMANTICO_ORIGEM: str = "origem"  # contrato/apólice que origina a obrigação

# Mapeamento canônico tipo_documento -> tipo_edge_semantico. Usado por
# `classificar_tipo_edge` e pela UI do dashboard (modal) para colorir o vínculo.
_MAPA_TIPO_EDGE_SEMANTICO: dict[str, str] = {
    # Boletos / faturas que "instruem" um pagamento futuro
    "boleto": TIPO_EDGE_SEMANTICO_CONFIRMA,
    "boleto_servico": TIPO_EDGE_SEMANTICO_CONFIRMA,
    "fatura_cartao": TIPO_EDGE_SEMANTICO_CONFIRMA,
    "conta_luz": TIPO_EDGE_SEMANTICO_CONFIRMA,
    "conta_agua": TIPO_EDGE_SEMANTICO_CONFIRMA,
    # Cupons/recibos/NFs que "comprovam" um pagamento passado
    "cupom_termico": TIPO_EDGE_SEMANTICO_COMPROVANTE,
    "cupom_fiscal_foto": TIPO_EDGE_SEMANTICO_COMPROVANTE,
    "cupom_termico_foto": TIPO_EDGE_SEMANTICO_COMPROVANTE,
    "cupom_nao_fiscal": TIPO_EDGE_SEMANTICO_COMPROVANTE,
    "recibo": TIPO_EDGE_SEMANTICO_COMPROVANTE,
    "recibo_nao_fiscal": TIPO_EDGE_SEMANTICO_COMPROVANTE,
    "nfce": TIPO_EDGE_SEMANTICO_COMPROVANTE,
    "nfce_consumidor_eletronica": TIPO_EDGE_SEMANTICO_COMPROVANTE,
    "danfe": TIPO_EDGE_SEMANTICO_COMPROVANTE,
    "danfe_nfe55": TIPO_EDGE_SEMANTICO_COMPROVANTE,
    "xml_nfe": TIPO_EDGE_SEMANTICO_COMPROVANTE,
    "voucher": TIPO_EDGE_SEMANTICO_COMPROVANTE,
    "holerite": TIPO_EDGE_SEMANTICO_COMPROVANTE,
    # Documentos que originam uma obrigação recorrente
    "contrato": TIPO_EDGE_SEMANTICO_ORIGEM,
    "apolice": TIPO_EDGE_SEMANTICO_ORIGEM,
    "cupom_garantia": TIPO_EDGE_SEMANTICO_ORIGEM,
    "cupom_garantia_estendida": TIPO_EDGE_SEMANTICO_ORIGEM,
    "garantia_fabricante": TIPO_EDGE_SEMANTICO_ORIGEM,
    "receita_medica": TIPO_EDGE_SEMANTICO_ORIGEM,
    # Extrato bancário "paga com" a própria conta-origem
    "extrato_bancario": TIPO_EDGE_SEMANTICO_PAGO_COM,
}


def classificar_tipo_edge(tipo_documento: str | None) -> str:
    """Mapeia um `tipo_documento` para o tipo de edge semântico (Sprint 74).

    Retorna um dos 4 valores canônicos:
      - ``pago_com``      (extrato origem)
      - ``confirma``      (boleto/fatura/conta)
      - ``comprovante``   (cupom/recibo/NFC-e/NF/holerite)
      - ``origem``        (contrato/apólice/receita médica/garantia)

    Tipos desconhecidos caem em ``pago_com`` (conservador — o documento
    carrega o registro do pagamento sem semântica adicional).
    """
    if not tipo_documento:
        return TIPO_EDGE_SEMANTICO_PAGO_COM
    return _MAPA_TIPO_EDGE_SEMANTICO.get(tipo_documento, TIPO_EDGE_SEMANTICO_PAGO_COM)


# ============================================================================
# Carregamento de config
# ============================================================================


def carregar_config(caminho: Path | None = None) -> dict[str, Any]:
    """Lê `mappings/linking_config.yaml` e devolve dict puro.

    Mantém acesso leniente: seções faltantes viram defaults internos para não
    quebrar chamadores em ambientes de teste que carregam config parcial.
    """
    caminho = caminho or _PATH_CONFIG_PADRAO
    if not caminho.exists():
        logger.warning("config de linking não encontrada: %s -- usando defaults", caminho)
        return _config_default()
    try:
        with caminho.open("r", encoding="utf-8") as fh:
            dados = yaml.safe_load(fh) or {}
    except yaml.YAMLError as erro:
        logger.error("erro ao parsear %s: %s -- usando defaults", caminho, erro)  # noqa: accent
        return _config_default()

    if not isinstance(dados, dict):
        return _config_default()

    dados.setdefault("tipos", {})
    dados.setdefault("default", _config_default()["default"])
    dados.setdefault("margem_empate", 0.05)
    return dados


def _config_default() -> dict[str, Any]:
    return {
        "tipos": {},
        "default": {
            "janela_dias": 3,
            "diff_valor_percentual": 0.02,
            "confidence_minimo": 0.75,
            "peso_temporal_diario": 0.10,
        },
        "margem_empate": 0.05,
    }


def _parametros_para_tipo(tipo_documento: str | None, config: dict[str, Any]) -> dict[str, Any]:
    """Devolve parâmetros (janela_dias, diff_valor_percentual, confidence_minimo,
    peso_temporal_diario) para um tipo de documento, com fallback no `default`.

    Sprint 95: garante que `peso_temporal_diario` esteja sempre presente no dict
    devolvido, mesmo se o tipo do YAML omitir a chave -- caso contrário caem em
    KeyError no chamador. Default canônico é 0.10 (comportamento Sprint 48).
    """
    tipos = config.get("tipos", {}) or {}
    if tipo_documento and tipo_documento in tipos:
        base = dict(config.get("default", {}))
        base.update(tipos[tipo_documento] or {})
    else:
        base = dict(config.get("default", {}))
    base.setdefault("peso_temporal_diario", 0.10)
    return base


# ============================================================================
# Score
# ============================================================================


def _cnpj_do_documento(doc_metadata: dict[str, Any]) -> str | None:
    """Normaliza CNPJ do emitente/varejo do documento."""
    for chave in ("cnpj_emitente", "cnpj_emissor", "varejo_cnpj", "cnpj"):
        valor = doc_metadata.get(chave)
        if valor:
            return str(valor).strip()
    return None


def _cnpj_da_transacao(db: GrafoDB, transacao_id: int) -> str | None:
    """Retorna o CNPJ do fornecedor apontado pela aresta `contraparte` da
    transação, quando existir. Se houver múltiplas, usa a primeira.
    """
    for aresta in db.listar_edges(src_id=transacao_id, tipo=EDGE_TIPO_CONTRAPARTE):
        fornecedor = db.buscar_node_por_id(aresta.dst_id)
        if fornecedor is None:
            continue
        cnpj = fornecedor.metadata.get("cnpj")
        if cnpj:
            return str(cnpj).strip()
    return None


def _calcular_score(
    delta_dias: int,
    diff_valor_absoluto: float,
    valor_doc: float,
    cnpj_bate: bool,
    peso_temporal_diario: float = 0.10,
) -> tuple[float, float]:
    """Retorna (score, diff_valor_percentual).

    Score é clampado em [0, 1]; diff_valor_percentual em [0, 1+] (pode passar
    de 1 se |diff| > |total|, mas o filtro de janela já impede isso).

    Sprint 95: `peso_temporal_diario` é configurável por tipo de documento
    (default 0.10). Tipos que pagam tarde (holerite, DAS, boleto) usam pesos
    reduzidos (0.005-0.01) para que delta natural de 30-60 dias não zere o
    score. CNPJ bonus (+0.30 / +0.10 quando delta=0) é preservado.
    """
    valor_ref = max(abs(valor_doc), 1.0)
    diff_pct = min(abs(diff_valor_absoluto) / valor_ref, 1.0)
    score = 1.0
    score -= abs(delta_dias) * peso_temporal_diario
    score -= diff_pct * 0.50
    if cnpj_bate:
        score += 0.30
        if delta_dias == 0:
            score += 0.10
    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0
    return round(score, 4), round(diff_pct, 4)


# ============================================================================
# Candidatas
# ============================================================================


def candidatas_para_documento(
    db: GrafoDB,
    doc_node: Node,
    config: dict[str, Any] | None = None,
) -> list[tuple[int, dict[str, Any]]]:
    """Devolve lista ordenada (transacao_id, evidencia) de candidatas.

    A evidência é um dict pronto para ser serializado como JSON em
    `edge.evidencia` e contém: diff_dias, diff_valor, diff_valor_pct,
    heuristica, confidence.
    """
    config = config or carregar_config()
    meta = doc_node.metadata
    total = meta.get("total")
    tipo_doc = meta.get("tipo_documento")

    parametros = _parametros_para_tipo(tipo_doc, config)
    # Sprint 95b: ancora temporal configuravel por tipo (default 'data_emissao').
    # Permite DAS PARCSN centrar a janela em 'vencimento' em vez de data da guia
    # -- pagamento PIX cai proximo do vencimento, não da emissao. Fallback
    # automatico para 'data_emissao' se o campo declarado não existir no doc.
    ancora_campo = str(parametros.get("ancora_temporal", "data_emissao"))
    ancora_data = meta.get(ancora_campo) or meta.get("data_emissao")

    if not ancora_data or total is None:
        logger.debug(
            "documento %s sem %s/total -- sem candidatas",
            doc_node.nome_canonico,
            ancora_campo,
        )
        return []

    try:
        total_f = float(total)
    except (TypeError, ValueError):
        return []

    # Sprint INFRA-LINKING-DIRPF-TOTAL-ZERO: total monetário nulo, zero ou
    # abaixo do mínimo elegível inviabiliza a métrica proporcional. Documento
    # sai do funil silenciosamente (defesa em camadas com o filtro do
    # orquestrador `linkar_documentos_a_transacoes`).
    if abs(total_f) <= TOTAL_MINIMO_ELEGIVEL:
        logger.debug(
            "documento %s com total<=%.2f -- fora da heurística por valor",
            doc_node.nome_canonico,
            TOTAL_MINIMO_ELEGIVEL,
        )
        return []

    candidatas_raw = obter_transacoes_candidatas_para_documento(
        db,
        data_iso=str(ancora_data),
        total=total_f,
        janela_dias=int(parametros["janela_dias"]),
        diff_valor_percentual=float(parametros["diff_valor_percentual"]),
    )

    peso_temporal = float(parametros.get("peso_temporal_diario", 0.10))
    cnpj_doc = _cnpj_do_documento(meta)
    resultado: list[tuple[int, dict[str, Any]]] = []
    for cand in candidatas_raw:
        transacao_id = cand["id"]
        if transacao_id is None:
            continue
        meta_t = cand["metadata"]
        delta_dias_assinado = _delta_dias_assinado(str(ancora_data), meta_t.get("data"))
        diff_valor_abs = abs(abs(float(meta_t.get("valor") or 0.0)) - abs(total_f))
        cnpj_trans = _cnpj_da_transacao(db, transacao_id) if cnpj_doc else None
        cnpj_bate = bool(cnpj_doc and cnpj_trans and cnpj_doc == cnpj_trans)
        score, diff_pct = _calcular_score(
            delta_dias=delta_dias_assinado,
            diff_valor_absoluto=diff_valor_abs,
            valor_doc=total_f,
            cnpj_bate=cnpj_bate,
            peso_temporal_diario=peso_temporal,
        )
        heuristica = _nome_heuristica(delta_dias_assinado, diff_valor_abs, cnpj_bate)
        evidencia = {
            "diff_dias": delta_dias_assinado,
            "diff_valor": round(diff_valor_abs, 2),
            "diff_valor_pct": diff_pct,
            "heuristica": heuristica,
            "confidence": score,
            "cnpj_bate": cnpj_bate,
            "tipo_documento": tipo_doc,
            "tipo_edge_semantico": classificar_tipo_edge(tipo_doc),
        }
        resultado.append((transacao_id, evidencia))

    resultado.sort(key=lambda par: par[1]["confidence"], reverse=True)
    return resultado


def _delta_dias_assinado(data_doc_iso: str, data_transacao: Any) -> int:
    """Delta em dias (transação - documento). Negativo = transação antes do doc."""
    try:
        d_doc = date.fromisoformat(str(data_doc_iso)[:10])
        d_trans = date.fromisoformat(str(data_transacao or "")[:10])
    except (ValueError, TypeError):
        return 0
    return (d_trans - d_doc).days


def _nome_heuristica(delta_dias: int, diff_valor_abs: float, cnpj_bate: bool) -> str:
    if cnpj_bate and delta_dias == 0 and diff_valor_abs <= 0.01:
        return "cnpj_data_valor_exato"
    if cnpj_bate and diff_valor_abs <= 0.01:
        return "cnpj_valor_exato_janela"
    if cnpj_bate:
        return "cnpj_valor_aproximado"
    if diff_valor_abs <= 0.01 and delta_dias == 0:
        return "data_valor_exato_sem_cnpj"
    return "data_valor_aproximado"


# ============================================================================
# Aplicação do linking + propostas
# ============================================================================


def _competencia_do_holerite(doc: Node) -> str | None:
    """Extrai a competência (YYYY-MM) de um documento holerite.

    Preferência: `metadata.periodo_apuracao` (formato canônico do extrator
    de contracheque). Fallback: sufixo `|YYYY-MM` do `nome_canonico`.

    Devolve None quando nem o metadata nem o nome canônico carregam a
    competência -- holerites sem competência não são candidatos a fusão.
    """
    valor = doc.metadata.get("periodo_apuracao")
    if isinstance(valor, str) and len(valor) >= 7 and valor[4] == "-":
        return valor[:7]
    nome = doc.nome_canonico or ""
    if "|" in nome:
        sufixo = nome.rsplit("|", 1)[-1].strip()
        if len(sufixo) >= 7 and sufixo[4] == "-" and sufixo[:4].isdigit():
            return sufixo[:7]
    return None


def _fundir_holerites_mesma_realidade(
    documentos: list[Node],
    *,
    tolerancia_pct: float = TOLERANCIA_VALOR_HOLERITE_MULTI_FONTE,
) -> tuple[list[Node], dict[int, int]]:
    """Agrupa holerites multi-fonte por (competência, valor próximo) e devolve
    a lista filtrada com apenas o representante de cada grupo.

    Critério: dois holerites pertencem à mesma realidade quando:
      - ambos têm `tipo_documento` igual a `holerite`;
      - têm a mesma competência (`YYYY-MM`) extraída via
        `_competencia_do_holerite`;
      - têm `metadata.total` definidos e a diferença relativa ao menor dos
        dois é menor ou igual a `tolerancia_pct` (default 5%).

    O representante de cada grupo é o documento com menor `id` (determinístico
    e estável entre runs -- depende apenas da ordem de ingestão no grafo).

    Devolve:
      - Lista filtrada com apenas os representantes (holerites que não foram
        fundidos passam intactos, junto dos outros tipos de documento).
      - Mapa `alias_id -> representante_id` para registrar arestas
        `_alias_de` posteriormente.

    Holerites sem competência ou sem `total` não são candidatos -- passam
    intactos para o linker (comportamento mais conservador).
    """
    # Particiona: holerites com competência + total -> elegíveis;
    # resto -> passa direto.
    elegiveis: list[Node] = []
    pass_direto: list[Node] = []
    for doc in documentos:
        if doc.metadata.get("tipo_documento") != "holerite":
            pass_direto.append(doc)
            continue
        competencia = _competencia_do_holerite(doc)
        total = doc.metadata.get("total")
        if competencia is None or total is None:
            pass_direto.append(doc)
            continue
        try:
            float(total)
        except (TypeError, ValueError):
            pass_direto.append(doc)
            continue
        elegiveis.append(doc)

    # Agrupa elegíveis por competência.
    por_competencia: dict[str, list[Node]] = {}
    for doc in elegiveis:
        chave = _competencia_do_holerite(doc) or ""
        por_competencia.setdefault(chave, []).append(doc)

    representantes: list[Node] = []
    alias_para_rep: dict[int, int] = {}

    for competencia, lista in por_competencia.items():
        if len(lista) <= 1:
            representantes.extend(lista)
            continue
        # Agrupa por proximidade de valor. Algoritmo O(n^2) é aceitável --
        # poucos holerites por competência (no máximo 2-4 fontes na vida real).
        grupos: list[list[Node]] = []
        for doc in sorted(lista, key=lambda n: n.id or 0):
            total_doc = float(doc.metadata["total"])
            colocado = False
            for grupo in grupos:
                referencia = float(grupo[0].metadata["total"])
                menor = min(abs(total_doc), abs(referencia))
                if menor <= 0:
                    continue
                diferenca_relativa = abs(total_doc - referencia) / menor
                if diferenca_relativa <= tolerancia_pct:
                    grupo.append(doc)
                    colocado = True
                    break
            if not colocado:
                grupos.append([doc])

        for grupo in grupos:
            # Representante: menor id (determinístico).
            grupo_ordenado = sorted(grupo, key=lambda n: n.id or 0)
            representante = grupo_ordenado[0]
            representantes.append(representante)
            for alias in grupo_ordenado[1:]:
                if alias.id is not None and representante.id is not None:
                    alias_para_rep[alias.id] = representante.id
                    logger.info(
                        "holerite alias detectado: %s (id=%s) -> representante %s (id=%s)"
                        " competência=%s diff_relativa<=%.2f",
                        alias.nome_canonico,
                        alias.id,
                        representante.nome_canonico,
                        representante.id,
                        competencia,
                        tolerancia_pct,
                    )

    return pass_direto + representantes, alias_para_rep


def _registrar_arestas_alias(db: GrafoDB, alias_para_rep: dict[int, int]) -> None:
    """Persiste no grafo a relação `alias_id -[_alias_de]-> representante_id`.

    Idempotente: `adicionar_edge` usa INSERT OR IGNORE na unique (src,dst,tipo).
    Rodar 2x não duplica nem altera evidência prévia.
    """
    for alias_id, rep_id in alias_para_rep.items():
        db.adicionar_edge(
            src_id=alias_id,
            dst_id=rep_id,
            tipo=EDGE_TIPO_ALIAS_REALIDADE,
            peso=1.0,
            evidencia={
                "motivo": "holerite_mesma_competencia_valor_proximo",
                "sprint": "INFRA-LINKING-HOLERITE-MULTI-FONTE",
            },
        )


def linkar_documentos_a_transacoes(
    db: GrafoDB,
    config: dict[str, Any] | None = None,
    caminho_propostas: Path | None = None,
    tipos_documento: list[str] | None = None,
) -> dict[str, int]:
    """Percorre documentos do grafo e tenta linkar cada um a uma transação.

    - Documentos que já possuem aresta `documento_de` com `aprovador` na
      evidência são preservados (não sobrescreve decisão humana).
    - Documentos sem candidata viram log info (não criam proposta).
    - Documentos com 1 candidata acima do confidence_minimo: linka.
    - Documentos com top-1/top-2 próximos (margem_empate): gera proposta
      de CONFLITO sem linkar.
    - Documentos com top-1 abaixo do confidence_minimo: gera proposta
      BAIXA_CONFIANCA sem linkar.

    Sprint INFRA-LINKING-HOLERITE-MULTI-FONTE (2026-05-13): antes de processar
    holerites, agrupa por (competência, valor próximo ±5%) e linka apenas o
    representante de cada grupo. Os demais (alias) recebem aresta `_alias_de`
    apontando para o representante e ficam fora do linking principal.

    Devolve dict com contadores: linkados, conflitos, baixa_confianca,
    sem_candidato, ja_linkados, alias_fundidos.
    """
    config = config or carregar_config()
    caminho_propostas = caminho_propostas or _PATH_PROPOSTAS_PADRAO
    caminho_propostas.mkdir(parents=True, exist_ok=True)

    margem_empate = float(config.get("margem_empate", 0.05))
    tolerancia_holerite = float(
        config.get("tolerancia_holerite_multi_fonte", TOLERANCIA_VALOR_HOLERITE_MULTI_FONTE)
    )

    stats = {
        "linkados": 0,
        "conflitos": 0,
        "baixa_confianca": 0,
        "sem_candidato": 0,
        "ja_linkados": 0,
        "total_vazio": 0,
        "alias_fundidos": 0,
    }

    documentos_todos = db.listar_nodes(tipo="documento")
    documentos, alias_para_rep = _fundir_holerites_mesma_realidade(
        documentos_todos, tolerancia_pct=tolerancia_holerite
    )
    if alias_para_rep:
        _registrar_arestas_alias(db, alias_para_rep)
        stats["alias_fundidos"] = len(alias_para_rep)

    for doc in documentos:
        if doc.id is None:
            continue
        tipo_doc = doc.metadata.get("tipo_documento")
        if tipos_documento is not None and tipo_doc not in tipos_documento:
            continue

        if _ja_linkado_humano(db, doc.id):
            stats["ja_linkados"] += 1
            continue

        # Sprint INFRA-LINKING-DIRPF-TOTAL-ZERO: documentos com total nulo
        # ou <= R$ 0,01 (DIRPF retificadora, certidões, contratos sem valor)
        # não entram no funil heurístico por valor. Evita propostas conflito
        # ruidosas em que qualquer transação pequena casa proporcionalmente.
        if _total_vazio_ou_minimo(doc.metadata.get("total")):
            stats["total_vazio"] += 1
            logger.info(
                "documento %s (%s) com total ausente/<=%.2f -- fora do linking por valor",
                doc.nome_canonico,
                tipo_doc,
                TOTAL_MINIMO_ELEGIVEL,
            )
            continue

        candidatas = candidatas_para_documento(db, doc, config=config)
        if not candidatas:
            stats["sem_candidato"] += 1
            logger.info(
                "documento %s (%s) sem candidata de transação",
                doc.nome_canonico,
                tipo_doc,
            )
            continue

        top_id, top_evidencia = candidatas[0]
        parametros = _parametros_para_tipo(tipo_doc, config)
        confidence_minimo = float(parametros["confidence_minimo"])
        top_score = float(top_evidencia["confidence"])

        # Empate entre top-1 e top-2 -> proposta de conflito.
        if len(candidatas) >= 2:
            segundo_score = float(candidatas[1][1]["confidence"])
            if (top_score - segundo_score) < margem_empate:
                _gerar_proposta_conflito(doc, candidatas[:3], caminho_propostas, parametros)
                stats["conflitos"] += 1
                continue

        if top_score < confidence_minimo:
            _gerar_proposta_baixa_confianca(doc, candidatas[:3], caminho_propostas, parametros)
            stats["baixa_confianca"] += 1
            continue

        # Criação da aresta com confidence >= mínimo e sem empate.
        db.adicionar_edge(
            src_id=doc.id,
            dst_id=top_id,
            tipo=EDGE_TIPO_DOCUMENTO_DE,
            peso=top_score,
            evidencia=top_evidencia,
        )
        stats["linkados"] += 1
        logger.info(
            "linked documento %s -> transação %s (score=%.3f, heurística=%s)",
            doc.nome_canonico,
            top_id,
            top_score,
            top_evidencia["heuristica"],
        )

    logger.info("linking concluído: %s", stats)
    return stats


def _total_vazio_ou_minimo(total: Any) -> bool:
    """True quando o total monetário do documento é None, não-numérico ou
    em módulo menor/igual a `TOTAL_MINIMO_ELEGIVEL` (R$ 0,01).

    Justificativa: DIRPF retificadora, contratos sem valor declarado e
    certidões chegam com `total=0.0`; aplicar heurística proporcional sobre
    valor zero faz qualquer transação de centavos bater, gerando propostas
    conflito ruidosas (incidente 2026-05-13 com `DIRPF|05127373122|2025_RETIF`).
    """
    if total is None:
        return True
    try:
        return abs(float(total)) <= TOTAL_MINIMO_ELEGIVEL
    except (TypeError, ValueError):
        return True


def _ja_linkado_humano(db: GrafoDB, doc_id: int) -> bool:
    """Verifica se há aresta `documento_de` com `aprovador` na evidência."""
    for aresta in db.listar_edges(src_id=doc_id, tipo=EDGE_TIPO_DOCUMENTO_DE):
        if aresta.evidencia.get("aprovador"):
            return True
    return False


# ============================================================================
# Propostas Markdown
# ============================================================================


def _gerar_proposta_conflito(
    doc: Node,
    candidatas: list[tuple[int, dict[str, Any]]],
    caminho_propostas: Path,
    parametros: dict[str, Any],
) -> Path:
    """Gera arquivo Markdown de CONFLITO quando top-1 e top-2 empatam."""
    return _escrever_proposta(doc, candidatas, caminho_propostas, parametros, motivo="conflito")


def _gerar_proposta_baixa_confianca(
    doc: Node,
    candidatas: list[tuple[int, dict[str, Any]]],
    caminho_propostas: Path,
    parametros: dict[str, Any],
) -> Path:
    """Gera arquivo Markdown de BAIXA_CONFIANCA quando top-1 < threshold."""
    return _escrever_proposta(
        doc, candidatas, caminho_propostas, parametros, motivo="baixa_confianca"
    )


def _escrever_proposta(
    doc: Node,
    candidatas: list[tuple[int, dict[str, Any]]],
    caminho_propostas: Path,
    parametros: dict[str, Any],
    motivo: str,
) -> Path:
    """Escreve proposta Markdown com nome determinístico por (doc_id, motivo).

    Idempotente: reprocessar o mesmo documento sobrescreve o arquivo em vez
    de gerar variantes (nome vem do nome_canonico do documento + motivo).
    """
    caminho_propostas.mkdir(parents=True, exist_ok=True)
    chave_slug = _slug(doc.nome_canonico)
    nome_arquivo = f"{doc.id:06d}_{chave_slug}_{motivo}.md"
    destino = caminho_propostas / nome_arquivo

    linhas: list[str] = []
    linhas.append("---")
    linhas.append(f"id: doc{doc.id}_{motivo}")
    linhas.append("tipo: linking")
    linhas.append(f"motivo: {motivo}")
    linhas.append("status: aberta")
    linhas.append("autor_proposta: linking-heuristico-sprint48")
    linhas.append("sprint_contexto: 48")
    linhas.append("---")
    linhas.append("")
    titulo = (
        "Conflito de linking documento -> transação"
        if motivo == "conflito"
        else "Baixa confiança no linking documento -> transação"
    )
    linhas.append(f"# {titulo}")
    linhas.append("")
    linhas.append("## Documento")
    linhas.append("")
    linhas.append(f"- id grafo: `{doc.id}`")
    linhas.append(f"- nome_canonico: `{doc.nome_canonico}`")
    tipo_doc = doc.metadata.get("tipo_documento", "desconhecido")
    linhas.append(f"- tipo_documento: `{tipo_doc}`")
    linhas.append(f"- data_emissao: `{doc.metadata.get('data_emissao', '?')}`")
    linhas.append(f"- total: `{doc.metadata.get('total', '?')}`")
    cnpj = _cnpj_do_documento(doc.metadata)
    if cnpj:
        linhas.append(f"- cnpj_emitente: `{cnpj}`")
    linhas.append("")
    linhas.append("## Parâmetros heurísticos aplicados")
    linhas.append("")
    linhas.append(f"- janela_dias: `{parametros.get('janela_dias')}`")
    linhas.append(f"- diff_valor_percentual: `{parametros.get('diff_valor_percentual')}`")
    linhas.append(f"- confidence_minimo: `{parametros.get('confidence_minimo')}`")
    linhas.append("")
    linhas.append("## Candidatas avaliadas")
    linhas.append("")
    linhas.append(
        "| rank | transacao_id | score | diff_dias | diff_valor | heuristica | cnpj_bate |"
    )
    linhas.append(
        "|------|--------------|-------|-----------|------------|------------|-----------|"
    )
    for i, (tid, evid) in enumerate(candidatas, start=1):
        linhas.append(
            "| {} | {} | {:.3f} | {} | {:.2f} | {} | {} |".format(
                i,
                tid,
                float(evid["confidence"]),
                evid["diff_dias"],
                float(evid["diff_valor"]),
                evid["heuristica"],
                evid["cnpj_bate"],
            )
        )
    linhas.append("")
    linhas.append("## Decisão humana")
    linhas.append("")
    linhas.append("- **Aprovada em:** (preencher)")
    linhas.append("- **Transação escolhida:** (preencher id)")
    linhas.append("- **Rejeitada em:** (preencher)")
    linhas.append("- **Motivo:** (preencher)")
    linhas.append("")
    linhas.append("---")
    linhas.append("")
    linhas.append(
        '*"Ligar é responsabilidade -- ligar errado é confundir a memória."'
        " -- princípio do arquivista*"
    )
    linhas.append("")

    destino.write_text("\n".join(linhas), encoding="utf-8")
    logger.info(
        "proposta %s escrita em %s (doc=%s, candidatas=%d)",
        motivo,
        destino,
        doc.nome_canonico,
        len(candidatas),
    )
    return destino


def _slug(texto: str) -> str:
    """Slug mínimo: alfanumérico e `-`. Evita caracteres inválidos em FS."""
    out_chars: list[str] = []
    for ch in texto.lower():
        if ch.isalnum():
            out_chars.append(ch)
        elif ch in {"-", "_"}:
            out_chars.append(ch)
        elif out_chars and out_chars[-1] != "-":
            out_chars.append("-")
    slug = "".join(out_chars).strip("-")
    return slug[:60] or "doc"


# ============================================================================
# Linker especializado: comprovante PIX foto -> transação bancária
# ============================================================================
#
# Sprint INFRA-LINKAR-PIX-TRANSACAO  # noqa: accent (2026-05-13). Adicionado em modo ADITIVO
# PURO: nenhuma função existente foi alterada -- apenas estendemos o motor com
# um pipeline dedicado para o tipo ``comprovante_pix_foto`` (entregue por
# DOC-27 + MOB-bridge-5).
#
# Por que um caminho dedicado em vez de reusar ``linkar_documentos_a_transacoes``
# direto com ``tipos_documento=["comprovante_pix_foto"]``? Porque o PIX traz um
# identificador canônico único -- o ``id_transacao`` E2E do BACEN -- que pode
# bater literalmente na descrição da transação bancária e elevar o score a 1.0
# com confiança absoluta (BACEN garante unicidade do E2E entre todos os bancos).
# Esse boost é específico de PIX e não cabe no motor genérico (que está
# parametrizado por valor + data + CNPJ).
#
# Estratégia de scoring (3 camadas, executadas após o motor canônico):
#
#   1) E2E literal na descrição da transação -> score = 1.0 (selo BACEN).
#      Heurística canônica: "pix_e2e_literal_match".
#   2) E2E não bate, mas data+valor+marcador PIX/TRANSF na descrição com
#      parte do nome do destinatário/remetente -> score original + 0.10
#      (boost de prosa). Heurística: "pix_marcador_textual".
#   3) Apenas data+valor (sem E2E nem marcador textual) -> score original do
#      motor (heurísticas data_valor_*).
#
# A geração de aresta usa o mesmo ``EDGE_TIPO_DOCUMENTO_DE`` (idempotente via
# UNIQUE(src,dst,tipo)) e as propostas de conflito/baixa-confiança reusam as
# funções existentes ``_gerar_proposta_conflito`` / ``_gerar_proposta_baixa_confianca``.


_PIX_MARCADORES_DESCRICAO: tuple[str, ...] = (
    "PIX",
    "TRANSF",
    "TRANSFERENCIA",
    "TRANSFERÊNCIA",
)


def _normalizar_texto_busca(texto: Any) -> str:
    """Uppercase e strip para comparação case-insensitive resiliente a None."""
    if not texto:
        return ""
    return str(texto).strip().upper()


def _e2e_literal_na_transacao(e2e: str | None, metadata_tx: dict[str, Any]) -> bool:
    """Verifica se o ``id_transacao`` E2E do PIX aparece literal em qualquer
    campo textual da transação (local, descrição, observacao, identificador).

    O E2E PIX tem 32 caracteres (formato BACEN ``E<ISPB><AAAAMMDDHHMM><Seq>``)
    e é único globalmente -- match literal é selo de identidade quase absoluto.
    """
    if not e2e:
        return False
    alvo = _normalizar_texto_busca(e2e)
    if len(alvo) < 8:
        return False
    for chave in ("local", "descricao", "observacao", "identificador", "memo"):
        valor = _normalizar_texto_busca(metadata_tx.get(chave))
        if alvo in valor:
            return True
    return False


def _marcador_pix_e_nome_na_descricao(
    razao_social: str | None,
    metadata_tx: dict[str, Any],
) -> bool:
    """``True`` quando a descrição da transação tem marcador PIX/TRANSF +
    pelo menos um token significativo (>=4 chars) do nome do destinatário.

    Heurística de prosa para o caso comum: extrato do banco grava
    ``PIX TRANSF JOAO DA SILVA 14:32:01`` ou similar. Bater algum token
    distintivo do nome reforça que é a mesma transação.
    """
    texto_alvo = ""
    for chave in ("local", "descricao", "observacao", "identificador", "memo"):
        valor = _normalizar_texto_busca(metadata_tx.get(chave))
        if valor:
            texto_alvo += " " + valor
    if not texto_alvo:
        return False
    tem_marcador = any(m in texto_alvo for m in _PIX_MARCADORES_DESCRICAO)
    if not tem_marcador:
        return False
    nome_norm = _normalizar_texto_busca(razao_social)
    if not nome_norm:
        return False
    # Token >= 4 chars (descarta "DA", "DE", "DO", "DOS" etc.)
    tokens = [t for t in nome_norm.split() if len(t) >= 4]
    for tok in tokens:
        if tok in texto_alvo:
            return True
    return False


def linkar_pix_transacao(
    db: GrafoDB,
    config: dict[str, Any] | None = None,
    caminho_propostas: Path | None = None,
) -> dict[str, int]:
    """Linker dedicado para documentos ``comprovante_pix_foto``.

    Percorre nós ``documento`` com ``metadata.tipo_documento == 'comprovante_pix_foto'``
    e tenta amarrar cada um à transação correspondente no extrato bancário usando
    o motor canônico (``candidatas_para_documento``) reforçado por dois boosts
    específicos de PIX:

    - **Boost E2E (1.0)**: se ``metadata.pix_id_transacao`` (E2E do BACEN) aparece
      literal em algum campo textual da transação candidata, score = 1.0.
    - **Boost textual (+0.10)**: se a descrição da transação tem marcador
      ``PIX``/``TRANSF`` e algum token significativo (>=4 chars) do nome do
      destinatário, soma 0.10 ao score original (clampado em 1.0).

    Idempotência: ``adicionar_edge`` usa ``INSERT OR IGNORE`` no schema; rodar
    duas vezes nunca duplica. Documentos já com aresta marcada por revisão
    humana (``evidencia.aprovador``) são preservados.

    Conflito top-1/top-2 (``margem_empate``) gera proposta em
    ``docs/propostas/linking/``; baixa-confiança (top-1 < ``confidence_minimo``)
    idem -- ambas via as mesmas funções de proposta usadas pelo motor canônico.

    Devolve dict com contadores: ``linkados``, ``conflitos``,
    ``baixa_confianca``, ``sem_candidato``, ``ja_linkados``, ``boost_e2e``,
    ``boost_textual``.
    """
    config = config or carregar_config()
    caminho_propostas = caminho_propostas or _PATH_PROPOSTAS_PADRAO
    caminho_propostas.mkdir(parents=True, exist_ok=True)

    margem_empate = float(config.get("margem_empate", 0.05))

    stats: dict[str, int] = {
        "linkados": 0,
        "conflitos": 0,
        "baixa_confianca": 0,
        "sem_candidato": 0,
        "ja_linkados": 0,
        "boost_e2e": 0,
        "boost_textual": 0,
    }

    documentos = db.listar_nodes(tipo="documento")
    for doc in documentos:
        if doc.id is None:
            continue
        if doc.metadata.get("tipo_documento") != "comprovante_pix_foto":
            continue

        if _ja_linkado_humano(db, doc.id):
            stats["ja_linkados"] += 1
            continue

        candidatas = candidatas_para_documento(db, doc, config=config)
        if not candidatas:
            stats["sem_candidato"] += 1
            logger.info(
                "comprovante_pix_foto %s sem candidata de transação",
                doc.nome_canonico,
            )
            continue

        # Aplica boosts PIX. Reordena por score boosteado.
        e2e_pix = doc.metadata.get("pix_id_transacao")
        razao_social = doc.metadata.get("razao_social")
        candidatas_boostadas: list[tuple[int, dict[str, Any]]] = []
        for tid, evid in candidatas:
            tx_node = db.buscar_node_por_id(tid)
            if tx_node is None:
                candidatas_boostadas.append((tid, evid))
                continue
            meta_tx = tx_node.metadata
            evid_novo = dict(evid)
            if _e2e_literal_na_transacao(e2e_pix, meta_tx):
                evid_novo["confidence"] = 1.0
                evid_novo["heuristica"] = "pix_e2e_literal_match"
                evid_novo["pix_boost"] = "e2e"
            elif _marcador_pix_e_nome_na_descricao(razao_social, meta_tx):
                score_antigo = float(evid_novo.get("confidence", 0.0))
                evid_novo["confidence"] = min(score_antigo + 0.10, 1.0)
                evid_novo["heuristica"] = "pix_marcador_textual"
                evid_novo["pix_boost"] = "textual"
            candidatas_boostadas.append((tid, evid_novo))

        candidatas_boostadas.sort(
            key=lambda par: float(par[1]["confidence"]), reverse=True
        )

        top_id, top_evidencia = candidatas_boostadas[0]
        parametros = _parametros_para_tipo("comprovante_pix_foto", config)
        confidence_minimo = float(parametros["confidence_minimo"])
        top_score = float(top_evidencia["confidence"])

        # Empate top-1/top-2 -> proposta de conflito (mesma regra do motor canônico).
        if len(candidatas_boostadas) >= 2:
            segundo_score = float(candidatas_boostadas[1][1]["confidence"])
            if (top_score - segundo_score) < margem_empate:
                _gerar_proposta_conflito(
                    doc, candidatas_boostadas[:3], caminho_propostas, parametros
                )
                stats["conflitos"] += 1
                continue

        if top_score < confidence_minimo:
            _gerar_proposta_baixa_confianca(
                doc, candidatas_boostadas[:3], caminho_propostas, parametros
            )
            stats["baixa_confianca"] += 1
            continue

        db.adicionar_edge(
            src_id=doc.id,
            dst_id=top_id,
            tipo=EDGE_TIPO_DOCUMENTO_DE,
            peso=top_score,
            evidencia=top_evidencia,
        )
        stats["linkados"] += 1
        boost_aplicado = top_evidencia.get("pix_boost")
        if boost_aplicado == "e2e":
            stats["boost_e2e"] += 1
        elif boost_aplicado == "textual":
            stats["boost_textual"] += 1

        # PII: E2E e nome canônico do destinatário NÃO vão para log INFO -- usamos
        # prefixo curto (E2E[:8]) e id do nó (numérico). Padrão (bb).
        e2e_curto = (e2e_pix or "")[:8] or "sem-e2e"
        logger.info(
            "linked PIX %s (e2e=%s, boost=%s) -> transação %s (score=%.3f)",
            doc.id,
            e2e_curto,
            boost_aplicado or "nenhum",
            top_id,
            top_score,
        )

    logger.info("linking PIX concluído: %s", stats)
    return stats


# ============================================================================
# CLI auxiliar
# ============================================================================


def main() -> None:
    """Entrypoint CLI: `python -m src.graph.linking` roda linking no grafo padrão.

    Sprint INFRA-LINKAR-PIX-TRANSACAO (2026-05-13)  # noqa: accent
    após o motor canônico, roda o linker dedicado de PIX (boost E2E + textual).
    Aditivo -- não substitui ``linkar_documentos_a_transacoes``.
    """
    from src.graph.db import caminho_padrao

    logger.info("linking CLI -- abrindo grafo em %s", caminho_padrao())
    with GrafoDB(caminho_padrao()) as db:
        stats_canonico = linkar_documentos_a_transacoes(db)
        stats_pix = linkar_pix_transacao(db)
    logger.info("estatísticas canônico: %s", json.dumps(stats_canonico, ensure_ascii=False))
    logger.info("estatísticas PIX dedicado: %s", json.dumps(stats_pix, ensure_ascii=False))


if __name__ == "__main__":
    main()


# "Ligar é responsabilidade; ligar errado é confundir a memória." -- princípio do arquivista
