"""Heterogeneity Detection -- decide se um PDF deve passar por page-split (heterogêneo)
ou ser tratado como envelope `single` (homogêneo).

Sprint 41d. Definição operacional alinhada no chat:

  Um PDF é HETEROGÊNEO se >= 2 identificadores únicos DISTINTOS aparecem
  em CONJUNTOS DE PÁGINAS DIFERENTES.

Identificadores únicos considerados:
  - Chave NFe 44 dígitos (identifica documento fiscal individual)
  - Número de bilhete 12-18 dígitos (identifica apólice de seguro)
  - CPF (identifica pessoa segurada/destinatária)

CNPJ NÃO é usado: o mesmo CNPJ aparece em todas as páginas de um extrato
bancário (CNPJ do banco emissor), portanto não desambigua.

Casos canônicos:
  - pdf_notas.pdf (3 cupons garantia, 3 bilhetes distintos, 3 pgs)        -> heterogêneo
  - notas-de-garantia (2 NFC-e + 2 cupons garantia, 4 pgs)                -> heterogêneo
  - extrato_itau_4_pgs (mesmo CNPJ + mesmo CPF em todas as 4 páginas)     -> homogêneo
  - holerite_1_pg                                                         -> homogêneo
  - PDF compilado onde mesmo bilhete aparece em pg1 e pg2 (duplicata)     -> homogêneo
"""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from src.intake.glyph_tolerant import extrair_chave_nfe44, extrair_cpf
from src.utils.logger import configurar_logger

logger = configurar_logger("intake.heterogeneidade")

# Reusa o mesmo regex do envelope (DRY se for promovido a módulo público depois)
_REGEX_BILHETE: re.Pattern[str] = re.compile(
    r"[B8]ILHETE\s+INDIVIDUAL[:\s]+(\d{12,18})", re.IGNORECASE
)


# ============================================================================
# API pública
# ============================================================================


def e_heterogeneo(pdf_path: Path) -> bool:
    """Devolve True se o PDF tem >= 2 documentos lógicos distintos.

    Critério: scan página-a-página coletando identificadores únicos
    (chave NFe 44, bilhete 12-18 dígitos, CPF). Se houver >= 2 IDs
    distintos cujas páginas de aparição diferem, é heterogêneo.

    Falha silenciosa: PDF corrompido, encriptado, ou sem texto extraível
    devolve False (assume homogêneo). Comportamento conservador --
    melhor tratar como single envelope do que tentar splittar mal.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) <= 1:
                return False  # 1 página nunca é heterogêneo
            ids_por_pagina: list[set[str]] = []
            for pagina in pdf.pages:
                texto = pagina.extract_text() or ""
                ids_por_pagina.append(_coletar_identificadores(texto))
        decisao = _ha_distintos_em_paginas_distintas(ids_por_pagina)
        logger.debug(
            "e_heterogeneo(%s) = %s -- ids_por_pagina=%s",
            pdf_path.name,
            decisao,
            [sorted(s) for s in ids_por_pagina],
        )
        return decisao
    except Exception as exc:  # noqa: BLE001 -- defensivo
        logger.warning(
            "e_heterogeneo(%s) falhou: %s -- assumindo homogêneo",
            pdf_path,
            exc,
        )
        return False


# ============================================================================
# Internals
# ============================================================================


def _coletar_identificadores(texto: str) -> set[str]:
    """Extrai identificadores únicos do texto de UMA página.

    Devolve set de strings prefixadas pelo tipo (`chave44:`, `bilhete:`,
    `cpf:`) para evitar colisão entre numerações distintas.
    """
    ids: set[str] = set()
    chave = extrair_chave_nfe44(texto)
    if chave:
        ids.add(f"chave44:{chave}")
    match_bilhete = _REGEX_BILHETE.search(texto)
    if match_bilhete:
        ids.add(f"bilhete:{match_bilhete.group(1)}")
    cpf = extrair_cpf(texto)
    if cpf:
        ids.add(f"cpf:{cpf}")
    return ids


def _ha_distintos_em_paginas_distintas(ids_por_pagina: list[set[str]]) -> bool:
    """Devolve True se >= 2 IDs distintos aparecem em conjuntos de páginas diferentes.

    Mesmo bilhete em 2 páginas (caso da duplicata pg1==pg2 do pdf_notas)
    NÃO conta -- vira 1 ID único.

    IDs todos na mesma página (caso patológico onde pg1 cita um bilhete
    e a chave NFe correspondente) também não conta -- não há divisão real
    de documentos lógicos.
    """
    todos_ids: set[str] = set()
    for ids in ids_por_pagina:
        todos_ids.update(ids)
    if len(todos_ids) < 2:
        return False
    # Verifica se existe algum par (id_a, id_b) cujas páginas de aparição
    # divergem -- se sim, são documentos lógicos diferentes.
    for id_a in todos_ids:
        paginas_a = frozenset(i for i, ids in enumerate(ids_por_pagina) if id_a in ids)
        for id_b in todos_ids:
            if id_a >= id_b:
                continue  # evita comparar consigo e duplicar pares
            paginas_b = frozenset(i for i, ids in enumerate(ids_por_pagina) if id_b in ids)
            if paginas_a != paginas_b:
                return True
    return False


# "Não toda multidão é desordem; nem toda página é documento à parte." -- princípio do diagnóstico
