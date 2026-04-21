"""Canonicalização de nomes de fornecedor em descrições bancárias.

CSVs Nubank (PF e PJ) exportam descrições sem acentuação e com razão
social truncada. Este módulo é a fonte única da verdade para restaurar
acentuação plausível e preservar marcadores de razão social (S/A).

Uso:
    from src.transform.canonicalizer_fornecedor import canonicalizar
    nome_canonico = canonicalizar("BRASILIA")  # -> "Brasília"

Contrato:
    - `canonicalizar(nome)` retorna str com acentos plausíveis aplicados.
    - Códigos técnicos (CPF, CNPJ, hash hex >=16, payload puramente
      numérico) são devolvidos intocados.
    - Aplicação é idempotente: canonicalizar(canonicalizar(x)) ==
      canonicalizar(x).
    - Matches são word-boundary e case-insensitive; a forma correta
      (capitalização + acento) substitui a ocorrência original.
    - Ordem de precedência: `razao_social_mapping` (match de padrão
      completo) > `substituicoes` (palavra a palavra) > preservação de
      S/A / S.A.

Não confundir com `canonicalizer_casal`:
    - `canonicalizer_casal` decide se uma descrição pertence ao casal
      (matcher booleano para Transferência Interna).
    - `canonicalizer_fornecedor` restaura apresentação visual de qualquer
      nome de fornecedor (string -> string).
"""

import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from src.utils.logger import configurar_logger

logger = configurar_logger("canonicalizer_fornecedor")

CAMINHO_YAML: Path = Path(__file__).resolve().parents[2] / "mappings" / "fornecedores_acentos.yaml"

# Regex de detecção de códigos técnicos.
REGEX_CNPJ = re.compile(r"^\s*\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\s*$")
REGEX_CPF = re.compile(r"^\s*\d{3}\.\d{3}\.\d{3}-\d{2}\s*$")
REGEX_HASH_HEX = re.compile(r"^\s*[0-9a-fA-F]{16,}\s*$")
REGEX_SO_DIGITOS = re.compile(r"^\s*\d{8,}\s*$")


def _remover_acentos(texto: str) -> str:
    """Normaliza texto removendo acentos (NFD + descarta combining marks)."""
    nfd = unicodedata.normalize("NFD", texto)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


@lru_cache(maxsize=1)
def _carregar_config(caminho: Optional[str] = None) -> dict:
    """Carrega e cacheia o YAML de substituições.

    Retorna dict com chaves `substituicoes` e `razao_social_mapping`.
    Em caso de falha, retorna dict vazio (fail-closed: canonicalização
    vira no-op em vez de derrubar o pipeline).
    """
    alvo = Path(caminho) if caminho else CAMINHO_YAML
    if not alvo.exists():
        logger.warning(
            "fornecedores_acentos.yaml não encontrado em %s; canonicalização será no-op",
            alvo,
        )
        return {}
    try:
        with open(alvo, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        config.setdefault("substituicoes", {})
        config.setdefault("razao_social_mapping", {})
        return config
    except (OSError, yaml.YAMLError) as erro:
        logger.error("Falha ao carregar %s: %s", alvo, erro)
        return {}


def resetar_cache() -> None:
    """Limpa o cache do YAML (útil em testes que recarregam configs)."""
    _carregar_config.cache_clear()


def _e_codigo_tecnico(nome: str) -> bool:
    """Detecta CPF, CNPJ, hash hex, ou payload puramente numérico longo."""
    if not nome:
        return False
    if REGEX_CNPJ.match(nome) or REGEX_CPF.match(nome):
        return True
    if REGEX_HASH_HEX.match(nome):
        return True
    if REGEX_SO_DIGITOS.match(nome):
        return True
    return False


def _aplicar_substituicoes(nome: str, substituicoes: dict) -> str:
    """Aplica substituições palavra-a-palavra com word boundary.

    A busca é insensível a case e acentos (compara normalizado), mas a
    substituição preserva a forma canônica do YAML (com acento e case
    correto).
    """
    if not substituicoes:
        return nome

    def _casa_fragmento(match: re.Match) -> str:
        fragmento = match.group(0)
        chave_norm = _remover_acentos(fragmento.upper())
        return substituicoes.get(chave_norm, fragmento)

    # Monta regex único com todas as chaves normalizadas.
    chaves_ordenadas = sorted(substituicoes.keys(), key=len, reverse=True)
    if not chaves_ordenadas:
        return nome

    alternativas = "|".join(re.escape(k) for k in chaves_ordenadas)
    padrao = re.compile(rf"\b({alternativas})\b", flags=re.IGNORECASE)

    nome_sem_acento = _remover_acentos(nome)

    # Estratégia: percorre `nome_sem_acento` buscando matches e mapeia
    # posição para posição em `nome` original. Como `_remover_acentos` só
    # descarta combining marks, o índice em bytes difere; para contornar,
    # reconstruímos via substituição direta no texto normalizado e depois
    # costuramos de volta mantendo não-casados do original.
    resultado: list[str] = []
    cursor_orig = 0

    # Mapeamento de índices: cada char do original pode gerar 1+ chars no
    # normalizado. Construímos lista posicional: para cada índice no
    # normalizado, qual índice corresponde no original.
    mapa: list[int] = []
    for idx_orig, caractere in enumerate(nome):
        normalizado = _remover_acentos(caractere)
        for _ in normalizado:
            mapa.append(idx_orig)

    for match in padrao.finditer(nome_sem_acento):
        ini_norm, fim_norm = match.start(), match.end()
        if ini_norm >= len(mapa) or fim_norm - 1 >= len(mapa):
            break
        ini_orig = mapa[ini_norm]
        fim_orig = mapa[fim_norm - 1] + 1

        resultado.append(nome[cursor_orig:ini_orig])
        fragmento_orig = nome[ini_orig:fim_orig]
        chave_norm = _remover_acentos(fragmento_orig.upper())
        resultado.append(substituicoes.get(chave_norm, fragmento_orig))

        cursor_orig = fim_orig

    resultado.append(nome[cursor_orig:])
    return "".join(resultado)


def _aplicar_razao_social(nome: str, mapping: dict) -> str:
    """Aplica correções de razão social antes das substituições palavra-a-palavra.

    Match é sobre o nome inteiro (após .upper() + sem-acento) contendo
    uma chave do mapping. A chave que casa substitui totalmente o nome
    pela forma canônica.
    """
    if not mapping:
        return nome

    nome_norm = _remover_acentos(nome.upper()).strip()
    # Ordena por tamanho decrescente para match mais específico primeiro.
    for chave in sorted(mapping.keys(), key=len, reverse=True):
        chave_norm = _remover_acentos(chave.upper()).strip()
        if chave_norm in nome_norm:
            valor_canonico = mapping[chave]
            # Se o nome é exatamente a chave (ou só a chave com whitespace),
            # retorna o valor direto. Caso contrário, substitui o fragmento.
            if nome_norm == chave_norm:
                return valor_canonico
            # Substitui preservando prefixo/sufixo.
            padrao = re.compile(re.escape(chave_norm), flags=re.IGNORECASE)
            # Como trabalhamos com `nome` original mas `chave_norm` é
            # normalizada, fazemos match case-insensitive sobre o nome
            # original (vale para casos ASCII como "AMERICANAS S A" que
            # não têm acento).
            if padrao.search(nome):
                return padrao.sub(valor_canonico, nome, count=1)
            # Caso o original tenha acentos e a chave normalizada não
            # case direto, retorna substituição completa para ser seguro.
            return valor_canonico
    return nome


def _preservar_s_a(nome: str) -> str:
    """Preserva marcadores de razão social S/A, S.A., Ltda.

    Converte ocorrências soltas de " SA " (word boundary) em " S/A " e
    mantém " S/A ", " S.A. ", " Ltda " intactos. Regra aplicada após as
    substituições para não interferir com o word-boundary do
    canonicalizer de palavras comuns.
    """
    # "SA" solto entre word boundaries (não seguido de letra) -> "S/A".
    nome = re.sub(r"\bSA\b(?![A-Za-z])", "S/A", nome)
    # Forma "S A" com espaço (comum em CSV sem pontuação) -> "S/A".
    nome = re.sub(r"\bS\s+A\b(?![A-Za-z])", "S/A", nome)
    return nome


def canonicalizar(nome: str, caminho_yaml: Optional[str] = None) -> str:
    """Restaura acentuação e preserva razão social em nome de fornecedor.

    Pipeline:
        1. Códigos técnicos (CPF, CNPJ, hash) -> intocado.
        2. `razao_social_mapping` (match de padrão completo).
        3. `substituicoes` (palavra a palavra, word boundary,
           case-insensitive, preserva acento do YAML).
        4. Preservação de S/A, S.A., Ltda.

    Idempotente: canonicalizar(canonicalizar(x)) == canonicalizar(x).
    """
    if not nome:
        return nome

    if _e_codigo_tecnico(nome):
        return nome

    config = _carregar_config(caminho_yaml)
    substituicoes = config.get("substituicoes", {}) or {}
    razao_mapping = config.get("razao_social_mapping", {}) or {}

    # Fase 1: razão social (pode reescrever totalmente).
    nome = _aplicar_razao_social(nome, razao_mapping)

    # Fase 2: substituições palavra-a-palavra.
    nome = _aplicar_substituicoes(nome, substituicoes)

    # Fase 3: preservação de S/A.
    nome = _preservar_s_a(nome)

    return nome


# "A palavra certa é a diferença entre um vaga-lume e um relâmpago." -- Mark Twain
