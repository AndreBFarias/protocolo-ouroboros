"""Regex e helpers tolerantes a glyphs corrompidos em PDF nativo (Armadilha #20).

Contexto: alguns PDFs (ex.: cupons da Americanas em `inbox/pdf_notas.pdf`) embarcam
fonte com mapeamento ToUnicode incompleto. `pdfplumber.extract_text()` devolve
texto legível para humanos, mas com caracteres únicos trocados de forma sistemática:
`CNPJ` aparece como `CNP)`, `S.A.` como `5.A.`, `O BILHETE` como `Q BILHETE`,
`Modelo` como `Modela`, `DÚVIDAS` sem til.

Estratégia: NÃO reescrevemos o texto extraído (perderia evidência). Em vez disso,
o detector de tipo e os extratores usam regex que aceitam classes de char tolerantes.
Este módulo centraliza esses padrões para que a regra "se aparecer mais um par,
adicionar aqui" seja respeitada (sincronização N-para-N -- meta-regra #1 do AI.md).

Uso típico:

    from src.intake.glyph_tolerant import (
        casa_padroes,
        compilar_regex_tolerante,
        extrair_cnpj,
        extrair_data_br,
    )

    if casa_padroes(["CNP" + GLYPH_J, "PR[ÊE]MIO"], texto, modo="all"):
        ...

    cnpj = extrair_cnpj(texto)            # devolve canônico "00.776.574/0160-79" ou None
    iso  = extrair_data_br(texto)         # devolve "2026-04-19" ou None
"""

from __future__ import annotations

import re
from typing import Iterable, Literal, Pattern

# ============================================================================
# Classes de char por glyph corrompido
# ----------------------------------------------------------------------------
# Cada constante mapeia o caractere ORIGINAL para uma classe de char regex que
# cobre as variantes observadas. Adicionar variante exige editar AQUI; jamais
# replicar o literal no caller.
# ============================================================================

GLYPH_J = r"[J\)]"  # 'J' em CNPJ vira ')' -- visto em pdf_notas.pdf
GLYPH_S_MAIUSCULO = r"[S5]"  # 'S' maiúsculo vira '5' -- visto em "5.A." e "5USEP"
GLYPH_O_MAIUSCULO = r"[OQ]"  # 'O' maiúsculo vira 'Q' -- visto em "Q BILHETE"
GLYPH_ZERO = r"[0D]"  # '0' em códigos curtos vira 'D' -- visto em "D6238" (cód. SUSEP)
GLYPH_B_MAIUSCULO = r"[B8]"  # 'B' maiúsculo vira '8' -- precaução para "8ILHETE"

# Vogais com acento: aceitar variante sem acento (fonte às vezes omite)
GLYPH_A_ACENTO = r"[ÁÂÃA]"
GLYPH_E_ACENTO = r"[ÉÊE]"
GLYPH_I_ACENTO = r"[ÍI]"
GLYPH_O_ACENTO = r"[ÓÔÕO]"
GLYPH_U_ACENTO = r"[ÚU]"
GLYPH_C_CEDILHA = r"[ÇC]"


# ============================================================================
# Regex canônicos pré-compilados para campos comuns
# ----------------------------------------------------------------------------
# Cada regex aceita variantes de glyph já catalogadas. Quem precisa de campo
# canônico (CNPJ, CPF, data) deve usar os helpers extrair_*; chamar re.search
# direto no padrão é OK quando a captura adicional não importa.
# ============================================================================

RE_CNPJ_TOLERANTE: Pattern[str] = re.compile(
    r"CNP" + GLYPH_J + r"\s*:?\s*"
    r"(\d{2}[.\s]?\d{3}[.\s]?\d{3}\s*[/\\]\s*\d{4}\s*[-\s]\s*\d{2})",
    re.IGNORECASE,
)

# CNPJ "solto" (sem rótulo CNPJ:) -- 14 dígitos com pontuação opcional.
# Útil quando o detector de fornecedor quer só o número, não o rótulo.
RE_CNPJ_SOLTO: Pattern[str] = re.compile(
    r"\b(\d{2}[.\s]?\d{3}[.\s]?\d{3}\s*[/\\]\s*\d{4}\s*[-\s]\s*\d{2})\b"
)

RE_CPF_TOLERANTE: Pattern[str] = re.compile(
    r"CPF\s*:?\s*"
    r"(\d{3}[.\s]?\d{3}[.\s]?\s*\d{3}\s*[-\s]\s*\d{2})",
    re.IGNORECASE,
)

RE_DATA_BR: Pattern[str] = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")

# Chave 44 da NFe: 11 grupos de 4 dígitos com espaços tolerados; serve NFe55 e NFC-e65.
# Modelo (dígitos 21-22) é validado fora -- aqui só reconhece a forma.
RE_CHAVE_44: Pattern[str] = re.compile(r"\b((?:\d{4}\s*){10}\d{4})\b")


# ============================================================================
# API pública
# ============================================================================


def compilar_regex_tolerante(padrao: str, flags: int = 0) -> Pattern[str]:
    """Compila um padrão com flags padrão IGNORECASE | UNICODE | MULTILINE.

    ATENÇÃO -- MULTILINE é APLICADO POR PADRÃO. Isso muda o comportamento
    de `^` e `$`: passam a casar início/fim de cada LINHA, não do texto
    inteiro. Se você escreveu `^DANFE` esperando casar só no início do
    documento, isso vai casar em qualquer linha que comece com 'DANFE'
    -- comportamento desejado para o classifier (preview multilinha) mas
    pode surpreender em outros contextos. Para desligar MULTILINE, passe
    `flags=re.NOFLAG` e remonte explicitamente as flags que quer.

    IGNORECASE evita o clássico "esqueci a flag e o regex falhou contra
    documento em CAIXA ALTA". UNICODE garante que classes como `\\w`
    cobrem caracteres acentuados.
    """
    return re.compile(padrao, flags | re.IGNORECASE | re.UNICODE | re.MULTILINE)


def casa_padroes(
    padroes: Iterable[str | Pattern[str]],
    texto: str,
    modo: Literal["all", "any"] = "any",
) -> bool:
    """Avalia uma lista de padrões contra o texto segundo o modo (all | any).

    Strings são compiladas com `compilar_regex_tolerante`. Pattern já
    compilados são usados como vieram (respeita as flags do chamador).

    Devolve True/False -- é a função que o classifier chama por tipo do
    `mappings/tipos_documento.yaml`.
    """
    iterador = (
        padrao if isinstance(padrao, re.Pattern) else compilar_regex_tolerante(padrao)
        for padrao in padroes
    )
    if modo == "all":
        return all(p.search(texto) is not None for p in iterador)
    if modo == "any":
        return any(p.search(texto) is not None for p in iterador)
    raise ValueError(f"modo inválido: {modo!r} (esperado 'all' ou 'any')")


def extrair_cnpj(texto: str) -> str | None:
    """Devolve o PRIMEIRO CNPJ canônico `XX.XXX.XXX/XXXX-XX` ou None.

    Aceita rótulo `CNPJ`, `CNP)`, `CNP J` e variantes; também aceita CNPJ
    "solto" (sem rótulo) como fallback. Formato canônico no retorno
    independe do formato de entrada.

    Para extrair MÚLTIPLOS CNPJs (ex.: cupom de garantia tem varejo +
    seguradora), usar `extrair_cnpjs` (plural).
    """
    cnpjs = extrair_cnpjs(texto)
    return cnpjs[0] if cnpjs else None


def extrair_cnpjs(texto: str) -> list[str]:
    """Devolve TODOS os CNPJs encontrados, na ordem de aparição, sem duplicatas.

    Combina os dois padrões (com rótulo `CNP[J)]:` e CNPJ solto) e
    deduplica preservando a ordem. Útil para documentos com múltiplos
    fornecedores/seguradoras (Sprint 47c precisa do CNPJ do varejo E
    da seguradora; Sprint 44 da NFe55 precisa de emissor + destinatário).
    """
    achados: list[str] = []
    vistos: set[str] = set()
    for padrao in (RE_CNPJ_TOLERANTE, RE_CNPJ_SOLTO):
        for match in padrao.finditer(texto):
            canonico = _normalizar_cnpj(match.group(1))
            if canonico not in vistos:
                vistos.add(canonico)
                achados.append(canonico)
    return achados


def extrair_cpf(texto: str) -> str | None:
    """Devolve CPF canônico `XXX.XXX.XXX-XX` ou None.

    Tolera o caso `051.273. 731-22` observado no pdf_notas.pdf (espaço
    inserido pelo glyph quebrado entre os blocos).
    """
    match = RE_CPF_TOLERANTE.search(texto)
    if not match:
        return None
    return _normalizar_cpf(match.group(1))


def extrair_data_br(texto: str) -> str | None:
    """Devolve a primeira data DD/MM/AAAA do texto no formato ISO `YYYY-MM-DD`.

    "Primeira" aqui é a data mais antiga em ordem de leitura -- na maioria
    dos documentos é a data de emissão (cabeçalho). Validação semântica
    (ano plausível, mês 1-12, dia 1-31) é feita aqui; data inválida é
    descartada e a busca segue.
    """
    for match in RE_DATA_BR.finditer(texto):
        dia, mes, ano = match.groups()
        if _data_plausivel(int(dia), int(mes), int(ano)):
            return f"{ano}-{mes}-{dia}"
    return None


def extrair_chave_nfe44(texto: str) -> str | None:
    """Devolve chave 44 dígitos (apenas dígitos, sem espaço) ou None.

    Não valida dígito verificador -- isso é responsabilidade dos extratores
    da Sprint 44/44b. Aqui só reconhece o formato.
    """
    match = RE_CHAVE_44.search(texto)
    if not match:
        return None
    digitos = re.sub(r"\s+", "", match.group(1))
    if len(digitos) != 44:
        return None
    return digitos


# ============================================================================
# Internals
# ============================================================================


def _normalizar_cnpj(bruto: str) -> str:
    digitos = re.sub(r"\D", "", bruto)
    if len(digitos) != 14:
        return bruto.strip()
    return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"


def _normalizar_cpf(bruto: str) -> str:
    digitos = re.sub(r"\D", "", bruto)
    if len(digitos) != 11:
        return bruto.strip()
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


def _data_plausivel(dia: int, mes: int, ano: int) -> bool:
    if not (1 <= dia <= 31):
        return False
    if not (1 <= mes <= 12):
        return False
    if not (1900 <= ano <= 2100):
        return False
    return True


# "Quem persegue verdade não a vence dobrando-a ao caso." -- Marco Aurélio
