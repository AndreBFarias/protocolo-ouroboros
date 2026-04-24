"""Extrator de faturas de cartão C6 Bank (formato XLS criptografado)."""

import hashlib
import io
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import msoffcrypto
import xlrd

from src.extractors.base import ExtratorBase, Transacao
from src.utils.logger import configurar_logger
from src.utils.senhas import carregar_senhas_pdf

LINHA_CABECALHO: int = 1

INDICES_COLUNAS: dict[str, int] = {
    "data_compra": 0,
    "nome_cartao": 1,
    "final_cartao": 2,
    "categoria": 3,
    "descricao": 4,
    "parcela": 5,
    "valor_usd": 6,
    "cotacao_brl": 7,
    "valor_brl": 8,
}

REGEX_PAGAMENTO: re.Pattern[str] = re.compile(
    r"Pag\s+Fatura|Inclus[aã]o\s+de\s+Pagamento",
    re.IGNORECASE,
)


class ExtratorC6Cartao(ExtratorBase):
    """Extrai transações de XLS criptografados de fatura do cartão C6.

    Formato: XLS protegido por senha com msoffcrypto.
    Colunas: Data de compra, Nome no cartão, Final do Cartão, Categoria,
             Descrição, Parcela, Valor (em US$), Cotação (em R$), Valor (em R$)
    """

    def __init__(self, caminho: Path) -> None:
        super().__init__(caminho)
        self.logger = configurar_logger("ExtratorC6Cartao")
        self.senhas: list[str] = self._carregar_senhas()

    def pode_processar(self, caminho: Path) -> bool:
        """Verifica se é um XLS de fatura do cartão C6."""
        if not caminho.suffix.lower() == ".xls":
            return False
        return "c6_cartao" in str(caminho).lower() or "fatura-cpf" in caminho.name.lower()

    def extrair(self) -> list[Transacao]:
        """Extrai todas as transações dos XLS de fatura C6."""
        transacoes: list[Transacao] = []
        arquivos: list[Path] = self._listar_arquivos()

        if not arquivos:
            self.logger.warning("Nenhum arquivo XLS encontrado em %s", self.caminho)
            return transacoes

        for arquivo in arquivos:
            self.logger.info("Processando fatura C6 cartão: %s", arquivo.name)
            transacoes.extend(self._processar_arquivo(arquivo))

        self.logger.info("Total de transações extraídas (C6 cartão): %d", len(transacoes))
        return transacoes

    def _listar_arquivos(self) -> list[Path]:
        """Lista todos os XLS válidos no diretório."""
        if self.caminho.is_file():
            return [self.caminho] if self.pode_processar(self.caminho) else []
        return sorted(f for f in self.caminho.glob("*.xls") if self.pode_processar(f))

    def _processar_arquivo(self, arquivo: Path) -> list[Transacao]:
        """Processa um único XLS e retorna lista de transações."""
        transacoes: list[Transacao] = []
        wb: Optional[xlrd.Book] = self._abrir_workbook(arquivo)

        if wb is None:
            return transacoes

        sh: xlrd.sheet.Sheet = wb.sheet_by_index(0)

        for idx in range(LINHA_CABECALHO + 1, sh.nrows):
            valores: list[Any] = sh.row_values(idx)
            transacao: Optional[Transacao] = self._parse_linha(valores, arquivo)
            if transacao:
                transacoes.append(transacao)

        return transacoes

    def _abrir_workbook(self, arquivo: Path) -> Optional[xlrd.Book]:
        """Abre e descriptografa o XLS com as senhas disponíveis."""
        for senha in self.senhas:
            try:
                with open(arquivo, "rb") as f:
                    ms = msoffcrypto.OfficeFile(f)
                    ms.load_key(password=senha)
                    buf: io.BytesIO = io.BytesIO()
                    ms.decrypt(buf)
                    buf.seek(0)
                    wb: xlrd.Book = xlrd.open_workbook(file_contents=buf.read())
                    self.logger.debug("Arquivo %s descriptografado com sucesso", arquivo.name)
                    return wb
            except Exception:
                continue

        self.logger.error("Nenhuma senha válida para %s", arquivo.name)
        return None

    def _parse_linha(
        self,
        valores: list[Any],
        arquivo: Path,
    ) -> Optional[Transacao]:
        """Converte uma linha da planilha em Transação."""
        try:
            if len(valores) < 9:
                return None

            data_str: Any = valores[INDICES_COLUNAS["data_compra"]]
            descricao: Any = valores[INDICES_COLUNAS["descricao"]]
            parcela_str: Any = valores[INDICES_COLUNAS["parcela"]]
            valor_usd: Any = valores[INDICES_COLUNAS["valor_usd"]]
            cotacao: Any = valores[INDICES_COLUNAS["cotacao_brl"]]
            valor_brl: Any = valores[INDICES_COLUNAS["valor_brl"]]

            if not data_str or not descricao:
                return None

            data_transacao: Optional[date] = self._parse_data(data_str)
            if data_transacao is None:
                return None

            descricao_str: str = str(descricao).strip()
            parcela_info: str = str(parcela_str).strip() if parcela_str else ""

            valor: float = self._determinar_valor(valor_brl, valor_usd, cotacao)
            if valor == 0.0:
                return None

            if REGEX_PAGAMENTO.search(descricao_str):
                # Sprint 82b: em vez de descartar, emitimos linha virtual
                # (contraparte espelho). O pagamento corresponde a uma
                # saida real em outra conta (Itau, Nubank CC, etc.); o
                # espelho permite que deduplicator paree os dois lados
                # como Transferencia Interna. Flag _virtual impede que
                # a linha contamine somatorios -- e o tipo ja nasce TI.
                self.logger.debug(
                    "Pagamento de fatura detectado -- emitindo espelho virtual: %s (%s)",
                    descricao_str,
                    valor,
                )
                identificador_virtual: str = self._gerar_hash(
                    str(data_transacao), descricao_str, str(valor)
                )
                return Transacao(
                    data=data_transacao,
                    valor=abs(valor),
                    descricao=descricao_str,
                    banco_origem="C6",
                    pessoa="André",
                    forma_pagamento="Crédito",
                    tipo="Transferência Interna",
                    identificador=identificador_virtual,
                    arquivo_origem=str(arquivo.name),
                    _virtual=True,
                )

            descricao_completa: str = descricao_str
            if parcela_info and parcela_info != "Única":
                descricao_completa = f"{descricao_str} - {parcela_info}"

            identificador: str = self._gerar_hash(str(data_transacao), descricao_str, str(valor))

            return Transacao(
                data=data_transacao,
                valor=abs(valor),
                descricao=descricao_completa,
                banco_origem="C6",
                pessoa="André",
                forma_pagamento="Crédito",
                tipo="Despesa",
                identificador=identificador,
                arquivo_origem=str(arquivo.name),
            )
        except (ValueError, TypeError, IndexError) as erro:
            self.logger.warning("Linha ignorada em %s: %s - %s", arquivo.name, valores, erro)
            return None

    @staticmethod
    def _parse_data(valor: Any) -> Optional[date]:
        """Converte valor de data (string DD/MM/YYYY) para date."""
        if isinstance(valor, str):
            try:
                return datetime.strptime(valor.strip(), "%d/%m/%Y").date()
            except ValueError:
                return None
        return None

    @staticmethod
    def _determinar_valor(
        valor_brl: Any,
        valor_usd: Any,
        cotacao: Any,
    ) -> float:
        """Determina o valor em reais da transação.

        Se Valor (em R$) estiver preenchido, usa diretamente.
        Senão, calcula a partir de Valor (em US$) * Cotação (em R$).
        """
        brl: float = float(valor_brl) if valor_brl else 0.0
        usd: float = float(valor_usd) if valor_usd else 0.0
        cot: float = float(cotacao) if cotacao else 0.0

        if brl != 0.0:
            return brl
        if usd != 0.0 and cot != 0.0:
            return round(usd * cot, 2)
        if usd != 0.0:
            return usd
        return 0.0

    @staticmethod
    def _gerar_hash(data: str, descricao: str, valor: str) -> str:
        """Gera hash determinístico como identificador."""
        conteudo: str = f"{data}|{descricao}|{valor}"
        return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _carregar_senhas() -> list[str]:
        """Carrega senhas via módulo centralizado."""
        return carregar_senhas_pdf()


# "O preço de qualquer coisa é a quantidade de vida
#  que você troca por ela." -- Henry David Thoreau
