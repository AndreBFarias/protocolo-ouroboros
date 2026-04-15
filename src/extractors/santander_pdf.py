"""Extrator de faturas de cartão Santander (PDF sem senha).

Layout especial: PDFs com 2+ páginas de detalhamento possuem layout em
duas colunas (cartão principal esquerda, cartão adicional direita).
O pdfplumber concatena as colunas em cada linha, exigindo extração
via findall ao invés de match por linha.
"""

import hashlib
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pdfplumber

from src.extractors.base import ExtratorBase, Transacao
from src.utils.logger import configurar_logger

REGEX_PARCELA: re.Pattern[str] = re.compile(
    r"(?:^|\s)(?:\d\s+)?(\d{2}/\d{2})\s+"
    r"([A-Za-z*][A-Za-z0-9*\s\-\.\']+?)"
    r"\s+\d{2}/\d{2}\s+"
    r"([\d\.]+,\d{2})"
)

REGEX_TRANSACAO_USD: re.Pattern[str] = re.compile(
    r"(?:^|\s)(?:\d\s+)?(\d{2}/\d{2})\s+"
    r"([A-Za-z*][A-Za-z0-9*\s\-\.\']+?)"
    r"\s+([\d\.]+,\d{2})\s+([\d\.]+,\d{2})"
)

REGEX_TRANSACAO_BRL: re.Pattern[str] = re.compile(
    r"(?:^|\s)(?:\d\s+)?(\d{2}/\d{2})\s+"
    r"((?:PAGAMENTO DE FATURA[^\d]*|[A-Za-z*][A-Za-z0-9*\s\-\.\']+?))"
    r"\s+(-?[\d\.]+,\d{2})"
)

REGEX_PAGAMENTO: re.Pattern[str] = re.compile(
    r"PAGAMENTO\s+DE\s+FATURA",
    re.IGNORECASE,
)

REGEX_DETALHAMENTO: re.Pattern[str] = re.compile(
    r"Detalhamento\s+da\s+Fatura",
    re.IGNORECASE,
)

REGEX_RESUMO: re.Pattern[str] = re.compile(
    r"Resumo\s+da\s+Fatura",
    re.IGNORECASE,
)

REGEX_ANUIDADE: re.Pattern[str] = re.compile(
    r"ANUIDADE",
    re.IGNORECASE,
)

REGEX_LINHA_IGNORAR: re.Pattern[str] = re.compile(
    r"(?:COTA[CÇ][AÃ]O\s+DOLAR|IOF\s+DESPESA|VALOR\s+TOTAL|"
    r"Compra\s+Data\s+Descri|Pagamento\s+e\s+Demais|"
    r"XXXX\s+XXXX|Saldo\s+total|cr[eé]dito\s+e\s+tarifas|"
    r"Saldo\s+Anterior|^\(\+\)|^\(\-\)|^\(=\)|"
    r"Explore\s+descontos|Acesse\s+o\s+site|"
    r"para\s+comprar|Juros\s+e\s+Custo|Aten[cç][aã]o|"
    r"titular|Central\s+de\s+Atendimento|Consultas|"
    r"^Despesas$|^Parcelamentos$|^\d+/\d+$|"
    r"OVALORDAS|PREOCUPE|CONDICAO|DESCONTO\s+NA|"
    r"WWW\.SANTANDER)",
    re.IGNORECASE,
)


class ExtratorSantanderPDF(ExtratorBase):
    """Extrai transações de PDFs de fatura do cartão Santander.

    Cartão SANTANDER ELITE VISA (sem senha).
    Foco nas páginas de Detalhamento da Fatura.
    """

    def __init__(self, caminho: Path) -> None:
        super().__init__(caminho)
        self.logger = configurar_logger("ExtratorSantanderPDF")

    def pode_processar(self, caminho: Path) -> bool:
        """Verifica se é um PDF de fatura Santander."""
        if not caminho.suffix.lower() == ".pdf":
            return False
        return "santander" in str(caminho).lower()

    def extrair(self) -> list[Transacao]:
        """Extrai todas as transações dos PDFs no diretório configurado."""
        transacoes: list[Transacao] = []
        arquivos: list[Path] = self._listar_arquivos()

        if not arquivos:
            self.logger.warning("Nenhum arquivo PDF encontrado em %s", self.caminho)
            return transacoes

        for arquivo in arquivos:
            self.logger.info("Processando fatura Santander: %s", arquivo.name)
            transacoes.extend(self._processar_arquivo(arquivo))

        self.logger.info("Total de transações extraídas (Santander): %d", len(transacoes))
        return transacoes

    def _listar_arquivos(self) -> list[Path]:
        """Lista todos os PDFs válidos no diretório."""
        if self.caminho.is_file():
            return [self.caminho] if self.pode_processar(self.caminho) else []
        return sorted(f for f in self.caminho.glob("*.pdf") if self.pode_processar(f))

    def _processar_arquivo(self, arquivo: Path) -> list[Transacao]:
        """Processa um único PDF e retorna lista de transações."""
        transacoes: list[Transacao] = []

        try:
            pdf = pdfplumber.open(str(arquivo))
        except Exception as erro:
            self.logger.error("Erro ao abrir %s: %s", arquivo.name, erro)
            return transacoes

        try:
            vencimento: Optional[date] = self._extrair_vencimento(pdf)
            if vencimento is None:
                self.logger.warning("Vencimento não encontrado em %s", arquivo.name)

            texto_completo: str = ""
            for pagina in pdf.pages:
                texto: Optional[str] = pagina.extract_text()
                if texto:
                    texto_completo += texto + "\n"

            if REGEX_DETALHAMENTO.search(texto_completo):
                transacoes = self._extrair_transacoes(texto_completo, arquivo, vencimento)
        except Exception as erro:
            self.logger.error("Erro ao processar %s: %s", arquivo.name, erro)
        finally:
            pdf.close()

        return transacoes

    def _extrair_vencimento(self, pdf: pdfplumber.PDF) -> Optional[date]:
        """Extrai a data de vencimento da fatura.

        O layout Santander coloca 'Total a Pagar' e 'Vencimento' no cabeçalho,
        e na linha seguinte: R$ <valor> DD/MM/YYYY [R$<limite>|DD/MM/YYYY]
        """
        for pagina in pdf.pages:
            texto: Optional[str] = pagina.extract_text()
            if not texto:
                continue

            if "Total a Pagar" not in texto:
                continue

            match: Optional[re.Match[str]] = re.search(
                r"R\$\s*[\d\.,]+\s+(\d{2}/\d{2}/\d{4})",
                texto,
            )
            if match:
                try:
                    return datetime.strptime(match.group(1), "%d/%m/%Y").date()
                except ValueError:
                    pass

        return None

    def _extrair_transacoes(
        self,
        texto: str,
        arquivo: Path,
        vencimento: Optional[date],
    ) -> list[Transacao]:
        """Extrai todas as transações do texto completo do PDF."""
        transacoes: list[Transacao] = []
        linhas: list[str] = texto.split("\n")
        em_detalhamento: bool = False
        em_resumo: bool = False

        for linha in linhas:
            linha_limpa: str = linha.strip()

            if not linha_limpa:
                continue

            if REGEX_DETALHAMENTO.search(linha_limpa):
                em_detalhamento = True
                em_resumo = False
                continue

            if REGEX_RESUMO.search(linha_limpa):
                em_resumo = True
                continue

            if em_resumo:
                if REGEX_DETALHAMENTO.search(linha_limpa):
                    em_detalhamento = True
                    em_resumo = False
                continue

            if not em_detalhamento:
                continue

            if REGEX_LINHA_IGNORAR.search(linha_limpa):
                continue

            encontradas: list[Transacao] = self._extrair_da_linha(linha_limpa, arquivo, vencimento)
            transacoes.extend(encontradas)

        return transacoes

    def _extrair_da_linha(
        self,
        linha: str,
        arquivo: Path,
        vencimento: Optional[date],
    ) -> list[Transacao]:
        """Extrai zero ou mais transações de uma linha (layout multi-coluna).

        Ordem de prioridade:
        1. Parcelamentos (DD/MM DESCRIÇÃO DD/MM VALOR) -- a parcela inclui DD/MM
        2. Transações em USD (DD/MM DESCRIÇÃO VALOR_BRL VALOR_USD)
        3. Transações em BRL (DD/MM DESCRIÇÃO VALOR)
        """
        transacoes: list[Transacao] = []
        posicoes_consumidas: set[tuple[int, int]] = set()

        for m in REGEX_PARCELA.finditer(linha):
            posicoes_consumidas.add((m.start(), m.end()))
            transacao: Optional[Transacao] = self._criar_transacao(
                m.group(1), m.group(2).strip(), m.group(3), arquivo, vencimento
            )
            if transacao:
                transacoes.append(transacao)

        for m in REGEX_TRANSACAO_USD.finditer(linha):
            if self._posicao_consumida(m.start(), m.end(), posicoes_consumidas):
                continue
            posicoes_consumidas.add((m.start(), m.end()))
            transacao = self._criar_transacao(
                m.group(1), m.group(2).strip(), m.group(3), arquivo, vencimento
            )
            if transacao:
                transacoes.append(transacao)

        for m in REGEX_TRANSACAO_BRL.finditer(linha):
            if self._posicao_consumida(m.start(), m.end(), posicoes_consumidas):
                continue
            transacao = self._criar_transacao(
                m.group(1), m.group(2).strip(), m.group(3), arquivo, vencimento
            )
            if transacao:
                transacoes.append(transacao)

        return transacoes

    @staticmethod
    def _posicao_consumida(
        inicio: int,
        fim: int,
        consumidas: set[tuple[int, int]],
    ) -> bool:
        """Verifica se uma posição já foi consumida por match anterior."""
        for ci, cf in consumidas:
            if inicio >= ci and fim <= cf:
                return True
            if inicio < cf and fim > ci:
                return True
        return False

    def _criar_transacao(
        self,
        data_parcial: str,
        descricao: str,
        valor_str: str,
        arquivo: Path,
        vencimento: Optional[date],
    ) -> Optional[Transacao]:
        """Cria uma Transação a partir dos componentes parseados."""
        try:
            descricao_limpa: str = descricao.strip()

            if not descricao_limpa:
                return None

            if REGEX_ANUIDADE.search(descricao_limpa):
                valor_check: float = self._parse_valor_br(valor_str)
                if valor_check == 0.0:
                    self.logger.debug("Anuidade com valor zero ignorada")
                    return None

            ano_referencia: int = vencimento.year if vencimento else datetime.now().year
            data_transacao: Optional[date] = self._resolver_data(
                data_parcial, ano_referencia, vencimento
            )
            if data_transacao is None:
                return None

            valor: float = self._parse_valor_br(valor_str)

            e_pagamento: bool = REGEX_PAGAMENTO.search(descricao_limpa) is not None

            if e_pagamento:
                tipo: str = "Transferência Interna"
                valor = -abs(valor)
            else:
                tipo = "Despesa"
                valor = abs(valor)

            identificador: str = self._gerar_hash(str(data_transacao), descricao_limpa, str(valor))

            return Transacao(
                data=data_transacao,
                valor=valor,
                descricao=descricao_limpa,
                banco_origem="Santander",
                pessoa="André",
                forma_pagamento="Crédito",
                tipo=tipo,
                identificador=identificador,
                arquivo_origem=str(arquivo.name),
            )
        except (ValueError, IndexError) as erro:
            self.logger.warning("Transação ignorada: %s - %s", descricao, erro)
            return None

    @staticmethod
    def _resolver_data(
        data_parcial: str,
        ano_referencia: int,
        vencimento: Optional[date],
    ) -> Optional[date]:
        """Resolve data DD/MM para date completa inferindo o ano."""
        try:
            partes: list[str] = data_parcial.split("/")
            dia: int = int(partes[0])
            mes: int = int(partes[1])

            if vencimento:
                if mes <= vencimento.month:
                    ano: int = vencimento.year
                else:
                    ano = vencimento.year - 1
            else:
                ano = ano_referencia

            return date(ano, mes, dia)
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _parse_valor_br(valor_str: str) -> float:
        """Converte valor no formato brasileiro para float."""
        limpo: str = valor_str.strip()
        negativo: bool = limpo.startswith("-")
        limpo = limpo.lstrip("-")
        limpo = limpo.replace(".", "").replace(",", ".")
        resultado: float = float(limpo)
        return -resultado if negativo else resultado

    @staticmethod
    def _gerar_hash(data: str, descricao: str, valor: str) -> str:
        """Gera hash determinístico como identificador."""
        conteudo: str = f"santander|{data}|{descricao}|{valor}"
        return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()[:16]


# "O homem é livre no momento em que deseja sê-lo." -- Voltaire
