"""Parsers canônicos de valores em formato brasileiro (R$ 1.234,56 -> 1234.56)."""

from __future__ import annotations


def parse_valor_br(valor_str: str | None) -> float | None:
    """Converte 'X.XXX,YY' (BR) em float. None em entrada inválida/vazia.

    Contrato permissivo usado por extratores fiscais (NF/cupons/boletos)
    que já validam presença antes. None preserva a ausência sem
    contaminar agregações. Consolida BRIEF §91.

    Exemplos:
        parse_valor_br("1.234,56") -> 1234.56
        parse_valor_br("103,93")   -> 103.93
        parse_valor_br(None)       -> None
        parse_valor_br("")         -> None
        parse_valor_br("abc")      -> None
    """
    if valor_str is None:
        return None
    limpo = valor_str.replace(".", "").replace(",", ".").strip()
    if not limpo:
        return None
    try:
        return float(limpo)
    except (ValueError, TypeError):
        return None


def parse_valor_br_float(valor_str: str | None, default: float = 0.0) -> float:
    """Versão não-nullable: devolve `default` em falha. Usado onde o caller
    soma valores ou espera float incondicional (ex.: contracheque_pdf).
    """
    resultado = parse_valor_br(valor_str)
    return resultado if resultado is not None else default


# "O que se repete em muitos lugares merece um nome só." -- princípio DRY
