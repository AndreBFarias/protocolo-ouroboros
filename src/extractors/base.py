"""Classe base abstrata e dataclass para todos os extratores de dados financeiros."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

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
        """Detecta a pessoa (André ou Vitória) com base no caminho do arquivo."""
        partes: str = str(caminho).lower()
        if "andre" in partes:
            return "André"
        if "vitoria" in partes:
            return "Vitória"
        return "Desconhecido"


# "Não é porque as coisas são difíceis que não ousamos;
#  é porque não ousamos que elas são difíceis." -- Sêneca
