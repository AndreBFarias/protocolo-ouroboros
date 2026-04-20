"""Validação e introspecção da chave de 44 dígitos NFe/NFC-e (Sprint 44b).

A chave é o identificador fiscal emitido pela SEFAZ que carrega, em 44 dígitos
(43 dados + 1 DV módulo 11), toda a metadata da nota:

    Posições (0-indexed, esquerda->direita):
     0-1  UF emitente (IBGE)
     2-5  AAMM da emissão (ano/mês)
     6-19 CNPJ do emitente (14 dígitos)
    20-21 Modelo da nota (55 = NFe, 65 = NFC-e)
    22-24 Série (3 dígitos)
    25-33 Número da nota (9 dígitos)
    34    Tipo de emissão (1 dígito)
    35-42 Código numérico aleatório (8 dígitos)
    43    Dígito verificador (módulo 11)

Este módulo é a fonte única de verdade para qualquer extrator que precise
validar uma chave (NFe55 da Sprint 44, NFC-e65 da 44b, XML da 46).

Regras do DV (algoritmo oficial SEFAZ):

    1. Dos 43 primeiros dígitos, da direita para a esquerda, multiplicar pelos
       pesos [2,3,4,5,6,7,8,9] ciclicamente.
    2. Somar todos os produtos.
    3. resto = soma % 11.
    4. Se resto < 2, DV = 0; senão, DV = 11 - resto.

O DV validado garante que a chave não tem erro de digitação -- NÃO garante
que a nota existe na SEFAZ (para isso, consulta online).
"""

from __future__ import annotations

import re

_PADRAO_DIGITOS = re.compile(r"\d")


def normalizar(bruto: str | None) -> str | None:
    """Extrai apenas os dígitos de uma string; devolve None se não forem 44.

    Aceita formatações comuns: `"5326 0400 ..."`, `"53.26.04.00..."`,
    `"chave: 5326..."`. Qualquer não-dígito é descartado antes da validação.
    """
    if not bruto:
        return None
    digitos = "".join(_PADRAO_DIGITOS.findall(bruto))
    return digitos if len(digitos) == 44 else None


def valida_digito_verificador(chave: str) -> bool:
    """True se o DV (posição 44, índice 43) bate com o módulo 11 dos outros 43."""
    digitos = normalizar(chave)
    if digitos is None:
        return False
    base, dv_informado = digitos[:43], int(digitos[43])
    return _calcular_dv(base) == dv_informado


def _calcular_dv(base_43: str) -> int:
    soma = 0
    peso = 2
    # Itera da direita para a esquerda -- dígito mais à direita pesa 2.
    for digito in reversed(base_43):
        soma += int(digito) * peso
        peso = 2 if peso == 9 else peso + 1
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


# ============================================================================
# Introspecção -- extrai campos sem precisar de parser externo
# ============================================================================


def extrair_modelo(chave: str) -> str | None:
    """Devolve `"55"` (NFe) ou `"65"` (NFC-e), ou None se chave inválida."""
    digitos = normalizar(chave)
    if digitos is None:
        return None
    return digitos[20:22]


def extrair_cnpj_emitente(chave: str) -> str | None:
    """CNPJ do emitente no formato canônico `XX.XXX.XXX/XXXX-XX`."""
    digitos = normalizar(chave)
    if digitos is None:
        return None
    cnpj = digitos[6:20]
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def extrair_uf_ibge(chave: str) -> str | None:
    """Código IBGE da UF emitente (2 dígitos). Ex.: `53` = DF, `35` = SP."""
    digitos = normalizar(chave)
    return digitos[:2] if digitos else None


def extrair_aamm(chave: str) -> str | None:
    """Ano e mês AAMM da emissão (4 dígitos). Útil para sanity-check vs data impressa."""
    digitos = normalizar(chave)
    return digitos[2:6] if digitos else None


def extrair_serie(chave: str) -> str | None:
    """Série da nota (3 dígitos)."""
    digitos = normalizar(chave)
    return digitos[22:25] if digitos else None


def extrair_numero(chave: str) -> str | None:
    """Número sequencial da nota (9 dígitos)."""
    digitos = normalizar(chave)
    return digitos[25:34] if digitos else None


# "Quando o detalhe do código é a lei, o descuido é o crime." -- princípio contábil
