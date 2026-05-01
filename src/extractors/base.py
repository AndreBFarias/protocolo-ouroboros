"""Classe base abstrata e dataclass para todos os extratores de dados financeiros."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

from src.utils.logger import configurar_logger


@dataclass
class Transacao:
    """Representa uma transação financeira normalizada.

    Sprint 82b: o atributo ``_virtual`` sinaliza linha sintética emitida por
    extrator de cartão quando detecta pagamento de fatura recebido. A linha
    serve de contraparte espelho para o debito correspondente em conta-
    corrente, permitindo que ``deduplicator.marcar_transferencias_internas``
    paree os dois lados como Transferência Interna. A flag é interna do
    pipeline e nunca vira coluna no XLSX (whitelist em ``xlsx_writer``).
    """

    data: date
    valor: float
    descricao: str
    banco_origem: str
    pessoa: str
    forma_pagamento: str
    tipo: str
    identificador: Optional[str] = None
    arquivo_origem: Optional[str] = None
    _virtual: bool = False


class ExtratorBase(ABC):
    """Classe base abstrata para extratores de dados bancários."""

    def __init__(self, caminho: Path) -> None:
        self.caminho: Path = caminho
        self.logger = configurar_logger(self.__class__.__name__)

    @abstractmethod
    def extrair(self) -> list[Transacao]:
        """Extrai transações do arquivo e retorna lista normalizada."""
        ...

    @abstractmethod
    def pode_processar(self, caminho: Path) -> bool:
        """Verifica se o extrator consegue processar o arquivo informado."""
        ...

    def _detectar_pessoa(self, caminho: Path) -> str:
        """Detecta o identificador genérico de pessoa pelo caminho do arquivo.

        Retorna ``pessoa_a`` / ``pessoa_b`` / ``casal`` (Sprint MOB-bridge-1).
        Aceita os aliases históricos de pasta (``andre``/``vitoria``)
        para compatibilidade com a estrutura física legada de
        ``data/raw/`` (preservada por design, ADR-23).
        """
        from src.utils.pessoas import pessoa_id_de_pasta

        resolvido = pessoa_id_de_pasta(caminho)
        if resolvido is None:
            return "casal"
        return resolvido


@dataclass
class ResultadoExtracao:
    """Resultado autoexplicativo de uma extração documental (Sprint META-COBERTURA-TOTAL-01).

    Materializa a Decisão D7 do dono em 2026-04-29: "extrair tudo das imagens e
    pdfs, cada valor, catalogar tudo". Cada extrator que adotar este contrato
    declara, em runtime, quantos valores potenciais o documento tem e quantos
    foram efetivamente extraídos. Quando a razão cai abaixo de
    ``cobertura_minima``, o método ``validar`` emite warning estruturado
    direcionado para auditoria periódica.

    Não substitui ``list[Transacao]`` -- é estrutura paralela usada por  # noqa: accent
    extratores documentais que ingerem no grafo (NFCe, DANFE, holerite) e
    precisam reportar cobertura de itens granulares além de transações.

    Adoção é opcional. Extratores novos podem expor método
    ``extrair_estruturado() -> ResultadoExtracao`` em paralelo ao método
    ``extrair`` legado, mantendo retrocompatibilidade.
    """

    items: list[dict[str, Any]] = field(default_factory=list)
    valores_extraidos: int = 0
    valores_potenciais: int = 0
    cobertura_minima: float = 0.95
    tipo_documento: str = ""
    arquivo_origem: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def cobertura(self) -> float:
        """Razão valores_extraidos / valores_potenciais. Retorna 1.0 se potencial=0."""
        if self.valores_potenciais <= 0:
            return 1.0
        return self.valores_extraidos / self.valores_potenciais

    def validar(self, logger: Any | None = None) -> bool:
        """Verifica se cobertura está acima do mínimo. Emite warning se abaixo.

        Retorna ``True`` se cobertura >= ``cobertura_minima`` ou se
        ``valores_potenciais`` é 0 (caso "sem dados extraíveis"). Retorna
        ``False`` e dispara warning estruturado caso contrário.

        O warning não interrompe a extração: D7 estabelece cobertura como
        invariante observável, não como regra de bloqueio. Auditoria
        periódica agrega os warnings via ``scripts/auditar_cobertura_total.py``.
        """
        if self.valores_potenciais <= 0:
            return True
        razao = self.cobertura
        if razao >= self.cobertura_minima:
            return True
        msg = (
            "[D7] cobertura abaixo do mínimo: %s extraídos de %s potenciais "
            "(razão=%.2f, mínimo=%.2f) tipo=%s arquivo=%s"
        )
        args = (
            self.valores_extraidos,
            self.valores_potenciais,
            razao,
            self.cobertura_minima,
            self.tipo_documento,
            self.arquivo_origem,
        )
        if logger is not None:
            logger.warning(msg, *args)
        return False


# "Não é porque as coisas são difíceis que não ousamos;
#  é porque não ousamos que elas são difíceis." -- Sêneca
