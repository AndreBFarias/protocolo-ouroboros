"""Extrator de comprovante PIX em foto (Sprint DOC-27).

Comprovantes PIX gerados por apps de banco (Itaú, C6, Nubank, Inter, etc.)
têm layouts visuais muito distintos. Em vez de manter N regexes frágeis
para cada banco, este extrator delega a extração estruturada ao Opus
multimodal via ``src.extractors.opus_visao.extrair_via_opus`` (ADR-26
rascunho: Opus como OCR canônico).

Modo de operação (ADR-13: supervisor artesanal sem API externa):

1. ``pode_processar`` aceita imagens em pastas ``comprovantes_pix/`` ou
   ``_classificar/`` (intake automático) ou quando o nome do arquivo
   contém ``pix``/``comprovante``.
2. ``extrair`` chama ``extrair_via_opus(caminho)``. Comportamento:
   - Cache hit: devolve dict canônico de comprovante PIX direto.
   - Cache miss: registra pedido em ``data/output/opus_ocr_pendentes/`` e
     devolve stub ``aguardando_supervisor=True``. O supervisor humano
     transcreve a foto para JSON canônico em ``data/output/opus_ocr_cache/``
     na próxima passagem.
3. Não há ingestão automática no grafo nesta sprint. O cache canônico
   serve de input para a sprint ``INFRA-LINKAR-PIX-TRANSACAO`` (futura), que  # noqa: accent
   amarra cada comprovante PIX a uma transação no extrato bancário.

Schema canônico do payload:

   tipo_documento: "comprovante_pix_foto"
   estabelecimento.razao_social: nome do destinatário (beneficiário)
   data_emissao: data ISO do PIX (YYYY-MM-DD)
   total: valor do PIX
   itens: lista com 1 entrada (descrição = motivo do PIX)
   forma_pagamento: "pix"

Não confunde com:
  - ``recibo_nao_fiscal.py`` (recibos formais sem CNPJ, sem ID transação)
  - ``cupom_termico_foto.py`` (cupom fiscal de loja física)
"""

from __future__ import annotations

from pathlib import Path

from src.extractors.base import ExtratorBase, Transacao
from src.extractors.opus_visao import extrair_via_opus
from src.utils.logger import configurar_logger

logger = configurar_logger("comprovante_pix_foto")


EXTENSOES_ACEITAS: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".heic", ".heif", ".pdf")


class ExtratorComprovantePixFoto(ExtratorBase):
    """Extrai comprovante PIX fotografado (JPG/PNG/PDF) via Opus visão.

    ``pode_processar`` aceita imagens em pastas relacionadas a PIX/
    comprovante OU com pistas no nome do arquivo. Para imagens genéricas
    (ex.: cupom fiscal), recusa para não colidir com
    ``cupom_termico_foto.py``.

    ``extrair`` devolve ``[]`` de ``base.Transacao``. Efeito colateral:
    registra pedido pendente OU retorna direto se cache existe. A
    ingestão no grafo é responsabilidade de sprint futura quando o
    linker amarrar o PIX à transação correspondente no extrato.
    """

    BANCO_ORIGEM: str = "Comprovante PIX (foto)"

    def pode_processar(self, caminho: Path) -> bool:
        if caminho.suffix.lower() not in EXTENSOES_ACEITAS:
            return False

        caminho_lower = str(caminho).lower()
        pastas_pix = ("comprovantes_pix", "comprovante_pix", "pix")
        if any(p in caminho_lower for p in pastas_pix):
            return True

        nome_lower = caminho.name.lower()
        pistas = ("pix", "comprovante")
        if any(p in nome_lower for p in pistas):
            return True

        return "_classificar" in caminho_lower or "inbox" in caminho_lower

    def extrair(self) -> list[Transacao]:
        """Chama Opus visão. Cache hit produz dict canônico; cache miss
        registra pedido pendente. Sempre devolve lista vazia de ``Transacao``  # noqa: accent
        (a transação real chega via extrato bancário, não pelo comprovante)."""
        try:
            payload = extrair_via_opus(self.caminho)
        except FileNotFoundError as erro:
            self.logger.error("imagem inexistente: %s", erro)
            return []

        if payload.get("aguardando_supervisor"):
            self.logger.info(
                "comprovante PIX %s aguardando supervisor (sha=%s)",
                self.caminho.name,
                payload.get("sha256", "")[:12],
            )
            return []

        if payload.get("tipo_documento") != "comprovante_pix_foto":
            self.logger.warning(
                "cache Opus para %s tem tipo_documento=%r; esperado 'comprovante_pix_foto'. "
                "Cache não consumido como PIX.",
                self.caminho.name,
                payload.get("tipo_documento"),
            )
            return []

        valor = payload.get("total", 0)
        destinatario = (payload.get("estabelecimento") or {}).get("razao_social", "")
        data = payload.get("data_emissao", "")
        self.logger.info(
            "comprovante PIX extraído: %s — R$ %.2f para %s em %s",
            self.caminho.name,
            float(valor),
            destinatario,
            data,
        )
        return []


def extrair(caminho: Path) -> dict:
    """API funcional: lê comprovante PIX e devolve payload canônico ou
    stub ``aguardando_supervisor=True``.

    Wrapper fino sobre ``extrair_via_opus`` que preserva tipagem da
    operação para callers que precisam do dict (testes, drill-down,
    futuro linker PIX→transação).
    """
    return extrair_via_opus(caminho)


# "Toda transação deixa duas testemunhas: a que move e a que registra." -- Heráclito de Éfeso
