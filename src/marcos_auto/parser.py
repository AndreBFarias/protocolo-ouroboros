"""Parser de frontmatter YAML do Vault Mobile (Sprint MOB-bridge-3).

O Vault armazena cada evento como Markdown com frontmatter YAML
delimitado por ``---``. Este módulo expõe ``ler_frontmatter(path)``
que devolve o dicionário do frontmatter ou ``None`` quando o arquivo
não tem frontmatter ou está malformado.

A função é defensiva por design: arquivos quebrados (YAML inválido,
sem fechamento ``---``, etc.) são silenciosamente ignorados em vez
de derrubar o pipeline. Erros graves devem ser logados pela camada
chamadora.

Schemas conhecidos no Vault:

    treino_sessao: data ISO 8601, autor, rotina, exercicios.
    humor: data ISO date, autor, humor 1-5, tags.
    diario_emocional: data ISO 8601, autor, modo (vitoria|positivo|
        negativo|trigger), emocoes, intensidade.
    evento: data ISO 8601, autor, modo, lugar, categoria.
    marco: data ISO 8601, autor, descricao, tags, auto, origem,  # noqa: accent
        hash. Marcos manuais podem ter ``auto: false`` ou omitir
        flags ``origem`` e ``hash``.

Função pública:

    ler_frontmatter(path) -> dict | None
        Lê o arquivo em ``path``, extrai o frontmatter YAML e
        devolve o dicionário. Devolve ``None`` se o arquivo não
        existe, não começa com ``---`` ou tem YAML inválido.

    listar_frontmatters(diretorio) -> list[dict]  # noqa: accent
        Conveniência: percorre ``diretorio`` (não recursivo),  # noqa: accent
        chama ``ler_frontmatter`` em cada ``*.md`` e devolve a
        lista de dicionários válidos. Inclui o caminho do arquivo
        em cada dict sob a chave ``_origem`` (Path) para facilitar
        diagnóstico downstream.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def ler_frontmatter(path: Path) -> dict[str, Any] | None:
    """Lê o frontmatter YAML de ``path``. Devolve dict ou None.

    Aceita arquivos cujo conteúdo começa com ``---\\n`` (linha
    delimitadora canônica do YAML frontmatter). Procura a próxima
    linha ``---`` para fechar. YAML malformado ou ausente devolve
    ``None``.
    """
    if not path.exists() or not path.is_file():
        return None
    try:
        texto = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if not texto.startswith("---"):
        return None
    # Remove primeira linha "---" e busca fechamento.
    linhas = texto.splitlines()
    if len(linhas) < 2 or linhas[0].strip() != "---":
        return None
    fim = None
    for idx in range(1, len(linhas)):
        if linhas[idx].strip() == "---":
            fim = idx
            break
    if fim is None:
        return None
    bloco = "\n".join(linhas[1:fim])
    try:
        dados = yaml.safe_load(bloco)
    except yaml.YAMLError:
        return None
    if not isinstance(dados, dict):
        return None
    return dados


def listar_frontmatters(diretorio: Path) -> list[dict[str, Any]]:
    """Devolve a lista de frontmatters de todos os ``*.md`` em ``diretorio``.  # noqa: accent

    Não recursivo (cada subsistema do Vault tem diretório próprio).
    Cada dict retornado ganha ``_origem`` apontando para o ``Path``
    do arquivo lido, para diagnóstico downstream sem perder
    rastreabilidade.
    """
    resultado: list[dict[str, Any]] = []
    if not diretorio.exists() or not diretorio.is_dir():
        return resultado
    for arquivo in sorted(diretorio.glob("*.md")):
        dados = ler_frontmatter(arquivo)
        if dados is None:
            continue
        dados["_origem"] = arquivo
        resultado.append(dados)
    return resultado


# "Toda interpretação começa por uma leitura honesta." -- Paul Ricoeur
