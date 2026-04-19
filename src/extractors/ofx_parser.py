"""Extrator genérico de arquivos OFX (Open Financial Exchange).

Lê arquivos .ofx exportados por qualquer banco brasileiro (Itaú, Santander,
Nubank, C6, BB, Caixa) e converte para o schema padrão do Ouroboros.
"""

import hashlib
import io
import re
from datetime import date
from pathlib import Path
from typing import Optional

from ofxparse import OfxParser as OfxLib

from src.extractors.base import ExtratorBase, Transacao
from src.utils.logger import configurar_logger

REGEX_ENCODING_HEADER = re.compile(rb"^(ENCODING:\s*)([^\r\n]+)", re.MULTILINE)

logger = configurar_logger("ExtratorOFX")

MAPA_BANCOS: dict[str, str] = {
    "itau": "Itaú",
    "itaú": "Itaú",
    "santander": "Santander",
    "nubank": "Nubank",
    "nu pagamentos": "Nubank",
    "c6": "C6",
    "banco do brasil": "BB",
    "caixa": "Caixa",
    "bradesco": "Bradesco",
}

MAPA_TIPO_TRANSACAO: dict[str, str] = {
    "debit": "Débito",
    "credit": "Crédito",
    "xfer": "Transferência",
    "payment": "Boleto",
    "directdebit": "Débito",
    "dep": "Depósito",
    "atm": "Débito",
    "pos": "Débito",
    "other": "Débito",
}


class ExtratorOFX(ExtratorBase):
    """Extrator genérico para arquivos OFX de qualquer banco."""

    def __init__(self, caminho: Path) -> None:
        super().__init__(caminho)

    def pode_processar(self, caminho: Path) -> bool:
        """Verifica se o arquivo é OFX."""
        return caminho.suffix.lower() == ".ofx"

    def extrair(self) -> list[Transacao]:
        """Extrai transações de um arquivo OFX."""
        transacoes: list[Transacao] = []
        arquivos = self._listar_arquivos()

        for arquivo in arquivos:
            resultado = self._processar_arquivo(arquivo)
            transacoes.extend(resultado)

        logger.info("Total de transações extraídas (OFX): %d", len(transacoes))
        return transacoes

    def _listar_arquivos(self) -> list[Path]:
        """Lista arquivos OFX no caminho configurado."""
        if self.caminho.is_file():
            return [self.caminho]
        return sorted(self.caminho.glob("*.ofx"))

    def _processar_arquivo(self, arquivo: Path) -> list[Transacao]:
        """Processa um único arquivo OFX."""
        transacoes: list[Transacao] = []
        pessoa = self._detectar_pessoa(arquivo)

        try:
            with open(arquivo, "rb") as f:
                conteudo = f.read()
            conteudo = REGEX_ENCODING_HEADER.sub(
                lambda m: m.group(1) + m.group(2).replace(b" ", b""),
                conteudo,
            )
            ofx = OfxLib.parse(io.BytesIO(conteudo))
        except Exception as e:
            logger.error("Erro ao parsear OFX %s: %s", arquivo.name, e)
            return []

        banco_origem = self._detectar_banco(ofx)

        # Processar contas correntes
        if ofx.account and ofx.account.statement:
            for transacao_ofx in ofx.account.statement.transactions:
                t = self._converter_transacao(
                    transacao_ofx,
                    banco_origem,
                    pessoa,
                    arquivo,
                )
                if t:
                    transacoes.append(t)

        # Processar múltiplas contas (se houver)
        if hasattr(ofx, "accounts"):
            for conta in ofx.accounts:
                if hasattr(conta, "statement") and conta.statement:
                    for transacao_ofx in conta.statement.transactions:
                        t = self._converter_transacao(
                            transacao_ofx,
                            banco_origem,
                            pessoa,
                            arquivo,
                        )
                        if t:
                            transacoes.append(t)

        logger.info(
            "Extraídas %d transações de %s (%s)",
            len(transacoes),
            arquivo.name,
            banco_origem,
        )
        return transacoes

    def _detectar_banco(self, ofx: object) -> str:
        """Detecta o banco pelo campo org do header OFX."""
        org = ""
        if hasattr(ofx, "account") and ofx.account:
            if hasattr(ofx.account, "institution"):
                inst = ofx.account.institution
                if hasattr(inst, "organization"):
                    org = str(inst.organization or "").lower()

        for chave, nome in MAPA_BANCOS.items():
            if chave in org:
                return nome

        if org:
            logger.warning("Banco não mapeado no OFX: '%s'", org)
        return "OFX"

    def _converter_transacao(
        self,
        t_ofx: object,
        banco_origem: str,
        pessoa: str,
        arquivo: Path,
    ) -> Optional[Transacao]:
        """Converte uma transação OFX para Transação do Ouroboros."""
        try:
            data_t: date = t_ofx.date.date() if hasattr(t_ofx.date, "date") else t_ofx.date
            valor: float = float(t_ofx.amount)
            descricao: str = str(t_ofx.memo or t_ofx.payee or "").strip()

            if not descricao and hasattr(t_ofx, "name"):
                descricao = str(t_ofx.name or "").strip()

            if not descricao:
                descricao = "Transação OFX sem descrição"

            tipo_ofx = str(getattr(t_ofx, "type", "other")).lower()
            forma = MAPA_TIPO_TRANSACAO.get(tipo_ofx, "Débito")

            if valor > 0:
                tipo = "Receita"
            else:
                tipo = "Despesa"
                valor = abs(valor)

            ofx_id = getattr(t_ofx, "id", None)
            if ofx_id:
                identificador = str(ofx_id)
            else:
                identificador = self._gerar_hash(data_t, valor, descricao)

            return Transacao(
                data=data_t,
                valor=valor,
                descricao=descricao,
                banco_origem=banco_origem,
                pessoa=pessoa,
                forma_pagamento=forma,
                tipo=tipo,
                identificador=identificador,
                arquivo_origem=str(arquivo),
            )
        except Exception as e:
            logger.warning("Erro ao converter transação OFX: %s", e)
            return None

    @staticmethod
    def _gerar_hash(data_t: date, valor: float, descricao: str) -> str:
        """Gera hash determinístico como identificador de fallback."""
        chave = f"{data_t.isoformat()}|{valor:.2f}|{descricao}"
        return hashlib.sha256(chave.encode()).hexdigest()[:16]


# "O começo é a parte mais importante do trabalho." -- Platão
