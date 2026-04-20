"""Pacote de intake universal: classifica, expande envelopes e roteia arquivos da inbox.

Sub-módulos:
- glyph_tolerant: regex e helpers tolerantes a fonte ToUnicode quebrada (ARMADILHAS #20)
- classifier: avalia tipos_documento.yaml e devolve decisão de roteamento (Sprint 41 Fase 1)
- extractors_envelope: page-split de PDF, expansão de ZIP/EML, diagnóstico scan/nativo
- router: move/renomeia para a pasta canônica conforme decisão do classifier
- preview: extrai preview rápido (texto nativo ou OCR baixa resolução) para alimentar classifier
"""

from __future__ import annotations

import hashlib
from pathlib import Path

__all__ = ["sha8_arquivo"]


def sha8_arquivo(caminho: Path) -> str:
    """SHA-256 dos bytes do arquivo, truncado nos primeiros 8 hex chars.

    8 hex = 32 bits = ~4 bilhões de slots. Para a inbox doméstica
    (centenas de arquivos/mês), risco de colisão é desprezível. Se a
    base crescer ordens de magnitude, aumentar para 12 ou 16 hex.

    Helper compartilhado entre classifier e extractors_envelope para que
    o nome canônico do arquivo classificado e o nome do diretório de
    page-split usem a MESMA referência -- meta-regra N-para-N #1.
    """
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()[:8]


# "Ler antes de codar." -- princípio do supervisor artesanal
