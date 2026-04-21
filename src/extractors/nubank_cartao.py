"""Extrator de faturas de cartão de crédito Nubank (formato CSV: date,title,amount)."""

import csv
import hashlib
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from src.extractors.base import ExtratorBase, Transacao
from src.transform.canonicalizer_casal import e_transferencia_do_casal
from src.utils.logger import configurar_logger


class ExtratorNubankCartao(ExtratorBase):
    """Extrai transações de CSVs de fatura do cartão Nubank.

    Formato esperado: date,title,amount
    Usado por:
        - André: data/raw/andre/nubank_cartao/
        - Vitória PJ: data/raw/vitoria/nubank_pj_cartao/
    """

    def __init__(self, caminho: Path) -> None:
        super().__init__(caminho)
        self.logger = configurar_logger("ExtratorNubankCartao")

    def pode_processar(self, caminho: Path) -> bool:
        """Verifica se é um CSV de cartão Nubank pelo nome e cabeçalho."""
        if not caminho.suffix.lower() == ".csv":
            return False
        nome_lower: str = caminho.name.lower()
        if "nubank" not in nome_lower:
            return False
        try:
            with open(caminho, encoding="utf-8") as f:
                cabecalho: str = f.readline().strip()
                return cabecalho == "date,title,amount"
        except (OSError, UnicodeDecodeError):
            return False

    def extrair(self) -> list[Transacao]:
        """Extrai todas as transações dos CSVs no diretório configurado."""
        transacoes: list[Transacao] = []
        arquivos: list[Path] = self._listar_arquivos()

        if not arquivos:
            self.logger.warning("Nenhum arquivo CSV encontrado em %s", self.caminho)
            return transacoes

        for arquivo in arquivos:
            self.logger.info("Processando fatura Nubank cartão: %s", arquivo.name)
            transacoes.extend(self._processar_arquivo(arquivo))

        self.logger.info("Total de transações extraídas (Nubank cartão): %d", len(transacoes))
        return transacoes

    def _listar_arquivos(self) -> list[Path]:
        """Lista todos os CSVs válidos no diretório."""
        if self.caminho.is_file():
            return [self.caminho] if self.pode_processar(self.caminho) else []
        return sorted(f for f in self.caminho.glob("*.csv") if self.pode_processar(f))

    def _processar_arquivo(self, arquivo: Path) -> list[Transacao]:
        """Processa um único CSV e retorna lista de transações."""
        transacoes: list[Transacao] = []
        pessoa: str = self._detectar_pessoa(arquivo)

        try:
            with open(arquivo, encoding="utf-8") as f:
                leitor = csv.DictReader(f)
                for linha in leitor:
                    transacao: Optional[Transacao] = self._parse_linha(linha, pessoa, arquivo)
                    if transacao:
                        transacoes.append(transacao)
        except (OSError, csv.Error) as erro:
            self.logger.error("Erro ao processar %s: %s", arquivo.name, erro)

        return transacoes

    def _parse_linha(
        self,
        linha: dict[str, str],
        pessoa: str,
        arquivo: Path,
    ) -> Optional[Transacao]:
        """Converte uma linha do CSV em Transação."""
        try:
            data_str: str = linha["date"].strip()
            titulo: str = linha["title"].strip()
            valor_str: str = linha["amount"].strip()

            data_transacao: date = datetime.strptime(data_str, "%Y-%m-%d").date()
            valor: float = abs(float(valor_str))
            tipo: str = self._classificar_tipo(titulo, pessoa)
            identificador: str = self._gerar_hash(data_str, titulo, valor_str)

            return Transacao(
                data=data_transacao,
                valor=valor,
                descricao=titulo,
                banco_origem="Nubank",
                pessoa=pessoa,
                forma_pagamento="Crédito",
                tipo=tipo,
                identificador=identificador,
                arquivo_origem=str(arquivo.name),
            )
        except (ValueError, KeyError) as erro:
            self.logger.warning("Linha ignorada em %s: %s - %s", arquivo.name, linha, erro)
            return None

    def _classificar_tipo(self, titulo: str, pessoa: str) -> str:
        """Classifica o tipo da transação baseado no título.

        Regra de cartão de crédito: default é Despesa (fatura é débito).

        Sprint 68b: substituídas listas hardcoded `PADROES_PARCEIRO` /
        `PARCEIROS` (fragmentos genéricos como `andre`, `vitoria` que
        podiam casar estabelecimentos comerciais com esses nomes) pelo
        matcher formal `canonicalizer_casal.e_transferencia_do_casal`,
        que consulta `mappings/contas_casal.yaml`. Na prática, PIX entre
        casal não aparece em fatura de cartão; a checagem permanece como
        defesa em profundidade para descrições de estorno que citem o
        parceiro ou eventuais créditos internos.

        Exceções:
            - Transferência Interna: descrição casa identidade do casal.
            - Receita: estorno, reembolso, crédito na fatura (entradas).
        """
        titulo_lower: str = titulo.lower()

        if e_transferencia_do_casal(titulo):
            return "Transferência Interna"

        if re.search(
            r"\bestorno\b|\breembolso\b|cr[eé]dito\s+a\s+fatura|cr[eé]dito\s+na\s+fatura",
            titulo_lower,
        ):
            return "Receita"

        return "Despesa"

    @staticmethod
    def _gerar_hash(data: str, titulo: str, valor: str) -> str:
        """Gera hash determinístico como identificador único."""
        conteudo: str = f"{data}|{titulo}|{valor}"
        return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()[:16]


# "A riqueza não consiste em ter grandes posses,
#  mas em ter poucas necessidades." -- Epicteto
