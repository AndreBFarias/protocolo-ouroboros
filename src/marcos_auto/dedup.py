"""Hash determinístico de marco para idempotência (Sprint MOB-bridge-3).

Cada marco automático tem um identificador estável derivado de
(``tipo``, ``data``, ``descricao``). O hash é usado como sufixo do  # noqa: accent
nome do arquivo gerado em ``marcos/<data>-auto-<hash>.md``. Mesma
combinação dos três campos produz o mesmo hash, portanto o mesmo
filename, garantindo idempotência: rodar duas vezes não duplica
arquivo.

Cooperação client/backend (M11): o app Mobile implementa heurística
simétrica usando o MESMO algoritmo de hash. Backend e client podem
rodar de forma concorrente que arquivos nunca colidem ou duplicam.

Algoritmo:

    sha256(f"{tipo}|{data}|{descricao}", utf-8) -> hexdigest -> [:12]

12 caracteres de SHA-256 dão 48 bits de entropia, colisão
astronomicamente baixa para o volume esperado (centenas a milhares
de marcos por usuário ao longo de anos). Filename permanece legível.

Decisão da spec MOB-bridge-3 §10: 12 chars escolhido como compromisso
entre legibilidade do nome de arquivo e segurança contra colisão.
"""

from __future__ import annotations

import hashlib
from typing import Mapping


def hash_marco(meta: Mapping[str, object]) -> str:
    """Devolve o hash determinístico de 12 chars do marco.

    O argumento é um mapping com pelo menos as chaves ``tipo``,
    ``data`` e ``descricao``. Outros campos do dict são ignorados  # noqa: accent
    propositadamente: dois marcos só são "iguais" se compartilham
    esses três campos, mesmo que tenham tags ou autor diferentes.

    Conversão de cada campo para string segue ``str(valor)`` direto.
    O separador ``|`` foi escolhido por ser improvável em descrições
    secas (ADR-0005) e em valores ISO de data.

    Levanta ``KeyError`` se algum dos três campos exigidos faltar --
    falha rápida é preferível a hash silenciosamente incorreto.
    """
    tipo = str(meta["tipo"])
    data = str(meta["data"])
    descricao = str(meta["descricao"])
    payload = f"{tipo}|{data}|{descricao}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


# "O que não tem identidade não tem existência." -- Parmênides
