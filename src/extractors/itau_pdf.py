"""Extrator de extratos bancários Itaú em PDF protegido por senha."""

import hashlib
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pdfplumber

from src.extractors.base import ExtratorBase, Transacao
from src.utils.logger import configurar_logger
from src.utils.senhas import carregar_senhas_pdf

REGEX_LANCAMENTO: re.Pattern[str] = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\-]?[\d\.]+,\d{2})$"
)

REGEX_SALDO_DIA: re.Pattern[str] = re.compile(
    r"SALDO\s+DO\s+DIA",
    re.IGNORECASE,
)

REGEX_PIX: re.Pattern[str] = re.compile(
    r"PIX\s+QRS|PIX\s+TRANSF|PIX\s+ENVIADO|PIX\s+RECEBIDO",
    re.IGNORECASE,
)

REGEX_TED: re.Pattern[str] = re.compile(
    r"\bTED\b|TRANSF\s+ELET",
    re.IGNORECASE,
)

REGEX_BOLETO: re.Pattern[str] = re.compile(
    r"PAG\s+BOLETO|PGTO\s+BOLETO|PAGTO.*BOLETO",
    re.IGNORECASE,
)

REGEX_DEBITO: re.Pattern[str] = re.compile(
    r"DEB\s+AUTO|DEBITO\s+AUTO|DEB\.?\s+AUT",
    re.IGNORECASE,
)

REGEX_SALARIO: re.Pattern[str] = re.compile(
    r"PAGTO\s+SALARIO|CREDITO\s+SALARIO",
    re.IGNORECASE,
)

REGEX_RENDIMENTO: re.Pattern[str] = re.compile(
    r"REND\s+PAGO\s+APLIC",
    re.IGNORECASE,
)

REGEX_VITORIA: re.Pattern[str] = re.compile(
    r"Vit[oó]ria|VITORIA",
    re.IGNORECASE,
)

REGEX_PAGAMENTO_FATURA: re.Pattern[str] = re.compile(
    r"NU\s*PAGAMENT|BANCO\s+SANTA",
    re.IGNORECASE,
)

REGEX_IMPOSTO: re.Pattern[str] = re.compile(
    r"RECEITA\s*FED|DARF|DAS.*SIMPL",
    re.IGNORECASE,
)


class ExtratorItauPDF(ExtratorBase):
    """Extrai transações de PDFs de extrato Itaú protegidos por senha.

    Formato: texto extraído via pdfplumber.
    Cada linha de lançamento segue o padrão:
        DD/MM/YYYY <histórico> <valor com sinal>
    Linhas de SALDO DO DIA são ignoradas.
    """

    def __init__(self, caminho: Path) -> None:
        super().__init__(caminho)
        self.logger = configurar_logger("ExtratorItauPDF")
        self.senhas: list[str] = self._carregar_senhas()

    def pode_processar(self, caminho: Path) -> bool:
        """Verifica se é um PDF de extrato Itaú."""
        if not caminho.suffix.lower() == ".pdf":
            return False
        return "itau" in str(caminho).lower()

    def extrair(self) -> list[Transacao]:
        """Extrai todas as transações dos PDFs no diretório configurado."""
        transacoes: list[Transacao] = []
        arquivos: list[Path] = self._listar_arquivos()

        if not arquivos:
            self.logger.warning("Nenhum arquivo PDF encontrado em %s", self.caminho)
            return transacoes

        for arquivo in arquivos:
            self.logger.info("Processando extrato Itaú: %s", arquivo.name)
            transacoes.extend(self._processar_arquivo(arquivo))

        self.logger.info("Total de transações extraídas (Itaú): %d", len(transacoes))
        return transacoes

    def _listar_arquivos(self) -> list[Path]:
        """Lista todos os PDFs válidos no diretório."""
        if self.caminho.is_file():
            return [self.caminho] if self.pode_processar(self.caminho) else []
        return sorted(f for f in self.caminho.glob("*.pdf") if self.pode_processar(f))

    def _processar_arquivo(self, arquivo: Path) -> list[Transacao]:
        """Processa um único PDF e retorna lista de transações."""
        transacoes: list[Transacao] = []
        pdf = self._abrir_pdf(arquivo)

        if pdf is None:
            return transacoes

        try:
            for pagina in pdf.pages:
                texto: Optional[str] = pagina.extract_text()
                if not texto:
                    continue
                transacoes.extend(self._extrair_de_texto(texto, arquivo))
        except Exception as erro:
            self.logger.error("Erro ao processar páginas de %s: %s", arquivo.name, erro)
        finally:
            pdf.close()

        return transacoes

    def _abrir_pdf(self, arquivo: Path) -> Optional[pdfplumber.PDF]:
        """Tenta abrir o PDF com as senhas disponíveis."""
        for senha in self.senhas:
            try:
                pdf = pdfplumber.open(str(arquivo), password=senha)
                self.logger.debug("PDF %s aberto com sucesso", arquivo.name)
                return pdf
            except Exception:
                continue

        self.logger.error("Nenhuma senha válida para %s", arquivo.name)
        return None

    def _extrair_de_texto(
        self,
        texto: str,
        arquivo: Path,
    ) -> list[Transacao]:
        """Extrai transações do texto de uma página."""
        transacoes: list[Transacao] = []

        for linha in texto.split("\n"):
            linha_limpa: str = linha.strip()

            if not linha_limpa:
                continue

            if REGEX_SALDO_DIA.search(linha_limpa):
                continue

            match: Optional[re.Match[str]] = REGEX_LANCAMENTO.match(linha_limpa)
            if not match:
                continue

            transacao: Optional[Transacao] = self._parse_lancamento(match, arquivo)
            if transacao:
                transacoes.append(transacao)

        return transacoes

    def _parse_lancamento(
        self,
        match: re.Match[str],
        arquivo: Path,
    ) -> Optional[Transacao]:
        """Converte um match de regex em Transação."""
        try:
            data_str: str = match.group(1)
            historico: str = match.group(2).strip()
            valor_str: str = match.group(3)

            data_transacao: date = datetime.strptime(data_str, "%d/%m/%Y").date()
            valor: float = self._parse_valor_br(valor_str)

            forma_pagamento: str = self._inferir_forma_pagamento(historico)
            tipo: str = self._classificar_tipo(historico, valor)
            identificador: str = self._gerar_hash(data_str, historico, valor_str)

            return Transacao(
                data=data_transacao,
                valor=valor,
                descricao=historico,
                banco_origem="Itaú",
                pessoa="André",
                forma_pagamento=forma_pagamento,
                tipo=tipo,
                identificador=identificador,
                arquivo_origem=str(arquivo.name),
            )
        except (ValueError, IndexError) as erro:
            self.logger.warning("Lançamento ignorado: %s - %s", match.group(0), erro)
            return None

    @staticmethod
    def _parse_valor_br(valor_str: str) -> float:
        """Converte valor no formato brasileiro (1.234,56) para float."""
        limpo: str = valor_str.strip()
        limpo = limpo.replace(".", "").replace(",", ".")
        return float(limpo)

    @staticmethod
    def _inferir_forma_pagamento(historico: str) -> str:
        """Infere a forma de pagamento a partir do histórico."""
        if REGEX_PIX.search(historico):
            return "Pix"
        if REGEX_BOLETO.search(historico):
            return "Boleto"
        if REGEX_TED.search(historico):
            return "Transferência"
        if REGEX_DEBITO.search(historico):
            return "Débito"
        return "Transferência"

    @staticmethod
    def _classificar_tipo(historico: str, valor: float) -> str:
        """Classifica o tipo da transação baseado no histórico e valor."""
        if REGEX_VITORIA.search(historico):
            return "Transferência Interna"

        if REGEX_PAGAMENTO_FATURA.search(historico):
            return "Transferência Interna"

        if REGEX_SALARIO.search(historico):
            return "Receita"

        if REGEX_RENDIMENTO.search(historico):
            return "Receita"

        if REGEX_IMPOSTO.search(historico):
            return "Imposto"

        if valor > 0:
            return "Receita"

        return "Despesa"

    @staticmethod
    def _gerar_hash(data: str, historico: str, valor: str) -> str:
        """Gera hash determinístico como identificador."""
        conteudo: str = f"itau|{data}|{historico}|{valor}"
        return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _carregar_senhas() -> list[str]:
        """Carrega senhas via módulo centralizado."""
        return carregar_senhas_pdf()


# "A verdadeira riqueza de um homem é o bem que ele faz no mundo." -- Maomé
