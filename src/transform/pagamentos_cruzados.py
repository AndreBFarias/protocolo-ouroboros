"""Reconhecimento de pagamentos cruzados do casal -- Sprint DASH-PAGAMENTOS-CRUZADOS-CASAL.

Resolve o problema "Vitória paga DAS do MEI Andre da conta dela; dashboard
confunde com transferência para terceiro e pacote IRPF de Andre perde a
dedução".

Padrão legítimo observado em 2026-05-12:
  - DAS PARCSN fev/2025 (R$ 324,31, MEI Andre) foi pago em 16/04/2025
    pela conta Nubank PF da Vitória.
  - Transação: ``quem="pessoa_b"``, ``categoria="Impostos"``,
    ``tag_irpf="imposto_pago"``.
  - Documento no grafo: ``tipo_documento="das_parcsn_andre"``, devedor
    Andre (CNPJ 45.850.636).
  - Conclusão correta: ``pessoa_pagadora="pessoa_b"``,
    ``pessoa_devedora="pessoa_a"``.

API pública:

    inferir_pessoa_devedora(transacao, documentos)  # noqa: accent
        Retorna ``pessoa_a`` / ``pessoa_b`` / ``casal`` se um documento
        do grafo casa com a transação por (valor, data proxima, devedor),
        ou ``None`` se nenhum match. Não modifica a transação.

    enriquecer_transacoes(transacoes, grafo)  # noqa: accent
        Aplica ``inferir_pessoa_devedora`` em todas as transações de
        Impostos, populando o campo ``pessoa_devedora`` quando há match.
        Operação in-place. Retorna a mesma lista para encadeamento.

    contar_pagamentos_cruzados(transacoes)
        Conta quantas transações têm ``pessoa_pagadora != pessoa_devedora``
        (apenas quando ``pessoa_devedora`` está populado). Útil para
        sentinelas de drift.

Princípios:
  - Padrão (o): default retrocompat -- transação sem match continua com
    ``pessoa_devedora=None``, comportamento antigo preservado.
  - Padrão (n): match exige 3 critérios convergentes (valor, data ±30d,
    devedor identificado). Sem isso, não atribui.
  - Não muda ``quem`` (padrão imutável herdado do banco origem).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, Optional

from src.utils.logger import configurar_logger

logger = configurar_logger("pagamentos_cruzados")

# CNPJ raiz do MEI da pessoa_a (45.850.636). Convenção do extrator
# ``src/extractors/das_parcsn_pdf.py``: DAS com CNPJ iniciando assim recebe
# ``tipo_documento="das_parcsn_andre"``. Mantido como constante local para
# evitar import cruzado com o extrator (que toca grafo, fora do escopo).
_CNPJ_RAIZ_PESSOA_A: str = "45.850.636"

# Janela canônica para considerar um pagamento como liquidação do documento.
# 30 dias cobre prorrogações e atrasos típicos de DAS/IPVA/IRPF. Janela maior
# poderia gerar falso-positivo (parcelas seguidas do mesmo carnê).
_JANELA_DIAS: int = 30

# Tolerância em centavos para casar valor da transação com o total do
# documento. DAS pode ter ajuste de juros/multa de poucos centavos quando
# pago perto do vencimento; 0.01 é suficiente para o feliz-caminho.
_TOLERANCIA_VALOR: float = 0.05


def _parse_data(valor: Any) -> Optional[date]:
    """Converte ``date``, ``datetime`` ou string ISO em ``date``. None se falha."""
    if valor is None:
        return None
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return None
        # Aceita "YYYY-MM-DD" e variantes ISO com timestamp.
        try:
            return datetime.fromisoformat(texto[:10]).date()
        except ValueError:
            return None
    return None


def _pessoa_devedora_do_documento(documento_meta: dict[str, Any]) -> Optional[str]:
    """Mapeia metadata do documento para identificador genérico de pessoa.

    Regras explícitas (Sprint DASH-PAGAMENTOS-CRUZADOS-CASAL):

    1. ``tipo_documento`` declara devedor diretamente:
       - ``das_parcsn_andre`` -> ``pessoa_a``
       - (outros tipos com sufixo ``_andre`` ou ``_vitoria`` no futuro
         podem ser adicionados aqui; padrão (o): só age sob match
         explícito).
    2. ``cnpj_emitente`` casa com CNPJ raiz da pessoa_a -> ``pessoa_a``.
    3. Nenhum dos casos acima -> ``None`` (não inferir).

    Mantém intencionalmente conservador: prefere None a chutar pessoa_b
    apenas porque o CNPJ não é do Andre (pode ser MEI de terceiro).
    """
    tipo = (documento_meta.get("tipo_documento") or "").lower()
    if tipo.endswith("_andre"):
        return "pessoa_a"
    if tipo.endswith("_vitoria"):
        return "pessoa_b"

    cnpj = (documento_meta.get("cnpj_emitente") or "").strip()
    if cnpj.startswith(_CNPJ_RAIZ_PESSOA_A):
        return "pessoa_a"

    return None


def _documento_casa_transacao(
    transacao: dict[str, Any],
    documento_meta: dict[str, Any],
) -> bool:
    """True se documento parece liquidado por esta transação.

    Critérios convergentes (padrão (n)):
      - Valor casa dentro de tolerância (R$ 0.05).
      - Data da transação cai em janela ±30 dias do vencimento (ou
        data_emissao quando vencimento ausente).
    """
    valor_tx = abs(float(transacao.get("valor") or 0))
    if valor_tx <= 0:
        return False
    valor_doc = float(documento_meta.get("total") or 0)
    if abs(valor_tx - valor_doc) > _TOLERANCIA_VALOR:
        return False

    data_tx = _parse_data(transacao.get("data"))
    if data_tx is None:
        return False
    referencia = _parse_data(documento_meta.get("vencimento") or documento_meta.get("data_emissao"))
    if referencia is None:
        return False
    delta = abs((data_tx - referencia).days)
    return delta <= _JANELA_DIAS


def inferir_pessoa_devedora(
    transacao: dict[str, Any],
    documentos: Iterable[dict[str, Any]],
) -> Optional[str]:
    """Tenta identificar a pessoa devedora cruzando transação com documentos.

    ``transacao`` é dict no schema canônico do normalizer (precisa de  # noqa: accent
    ``valor``, ``data`` e ``categoria``). ``documentos`` é iterável de
    dicts de metadata (lidos de ``GrafoDB.listar_nodes("documento")``).

    Retorna identificador genérico (``pessoa_a`` / ``pessoa_b``) quando
    encontra match único; ``None`` quando não há documento candidato ou
    quando o devedor não pode ser identificado pelo metadata.

    Não muda a transação: caller decide se popula ``pessoa_devedora``.
    """
    categoria = (transacao.get("categoria") or "").strip().lower()
    if categoria != "impostos":
        # Sprint declarou escopo: só impostos. Outras categorias (presentes,
        # almoço) ficam fora -- ver "Não-objetivos" da spec.
        return None

    candidatos: list[str] = []
    for meta in documentos:
        if not isinstance(meta, dict):
            continue
        if not _documento_casa_transacao(transacao, meta):
            continue
        devedora = _pessoa_devedora_do_documento(meta)
        if devedora is not None:
            candidatos.append(devedora)

    if not candidatos:
        return None

    # Se mais de um documento casa (caso raro: dois DAS de mesmo valor +
    # janela), só atribui se TODOS apontam para a mesma pessoa. Divergência
    # silenciosa é melhor que falso-positivo.
    unicos = set(candidatos)
    if len(unicos) == 1:
        return candidatos[0]

    logger.warning(
        "transação com %d documentos candidatos divergentes (%s); não atribui pessoa_devedora",
        len(candidatos),
        sorted(unicos),
    )
    return None


def enriquecer_transacoes(
    transacoes: list[dict[str, Any]],
    documentos: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Aplica ``inferir_pessoa_devedora`` in-place nas transações de Impostos.

    Só toca transações com ``categoria == "Impostos"`` e ``pessoa_devedora``
    ainda ``None`` (retrocompat -- padrão (o)). Retorna a mesma lista para
    permitir encadeamento na pipeline.
    """
    if not transacoes:
        return transacoes

    # Materializa documentos uma vez (iterable pode ser gerador).
    docs_lista = [d for d in documentos if isinstance(d, dict)]
    enriquecidas = 0
    for t in transacoes:
        if not isinstance(t, dict):
            continue
        if t.get("pessoa_devedora") is not None:
            continue
        if (t.get("categoria") or "").strip().lower() != "impostos":
            continue
        devedora = inferir_pessoa_devedora(t, docs_lista)
        if devedora is not None:
            t["pessoa_devedora"] = devedora
            # Garante que pessoa_pagadora esteja populada (espelha quem).
            if t.get("pessoa_pagadora") is None:
                t["pessoa_pagadora"] = t.get("quem")
            enriquecidas += 1

    if enriquecidas:
        logger.info(
            "pagamentos cruzados: %d transações de Impostos enriquecidas com pessoa_devedora",
            enriquecidas,
        )
    return transacoes


def contar_pagamentos_cruzados(transacoes: Iterable[dict[str, Any]]) -> dict[str, int]:
    """Conta transações cruzadas vs alinhadas no universo de Impostos.

    Retorna dict com chaves:
      - ``total_impostos``: total de transações com categoria Impostos.
      - ``com_devedora``: subset com ``pessoa_devedora`` populado.
      - ``cruzados``: subset onde ``pessoa_pagadora != pessoa_devedora``.
      - ``sem_match``: subset com categoria Impostos mas sem
        ``pessoa_devedora`` (candidatos a drift se proporção alta).

    Usado pela sentinela e pelo widget do dashboard.
    """
    total = 0
    com_devedora = 0
    cruzados = 0
    sem_match = 0
    for t in transacoes:
        if not isinstance(t, dict):
            continue
        if (t.get("categoria") or "").strip().lower() != "impostos":
            continue
        total += 1
        devedora = t.get("pessoa_devedora")
        pagadora = t.get("pessoa_pagadora") or t.get("quem")
        if devedora is None:
            sem_match += 1
            continue
        com_devedora += 1
        if pagadora != devedora:
            cruzados += 1
    return {
        "total_impostos": total,
        "com_devedora": com_devedora,
        "cruzados": cruzados,
        "sem_match": sem_match,
    }


def sentinela_drift_impostos(
    transacoes: Iterable[dict[str, Any]],
    limiar_percentual: float = 5.0,
) -> Optional[str]:
    """Sentinela: alerta se >X% dos impostos do mês não tem pessoa_devedora.

    Retorna mensagem de alerta (string) ou ``None`` se está sob controle.
    Critério: se mais de ``limiar_percentual`` % das transações de Impostos
    têm ``pessoa_devedora is None``, isso indica drift de match
    (extrator de DAS pode ter falhado, documento órfão, etc.).
    """
    contagem = contar_pagamentos_cruzados(transacoes)
    total = contagem["total_impostos"]
    if total == 0:
        return None
    sem_match = contagem["sem_match"]
    percentual = (sem_match / total) * 100.0
    if percentual <= limiar_percentual:
        return None
    return (
        f"Drift de match: {sem_match}/{total} ({percentual:.1f}%) transações "
        f"de Impostos sem pessoa_devedora identificada (limiar {limiar_percentual:.1f}%)."
    )


# "Quem paga a conta do outro sem cobrar prova merece reconhecimento contabil."
# -- Aristoteles, Etica a Nicomaco (parafrase)
