"""Extrator de extratos de conta corrente Nubank (CSV: Data,Valor,ID,Descrição)."""

import csv
import html
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from src.extractors.base import ExtratorBase, Transacao
from src.transform.canonicalizer_casal import e_transferencia_do_casal
from src.utils.logger import configurar_logger


class ExtratorNubankCC(ExtratorBase):
    """Extrai transações de CSVs de conta corrente Nubank.

    Formato esperado: Data,Valor,Identificador,Descrição
    Usado por:
        - pessoa_b PF: data/raw/vitoria/nubank_pf_cc/
        - pessoa_b PJ: data/raw/vitoria/nubank_pj_cc/
    """

    REGEX_ANDRE: re.Pattern[str] = re.compile(
        r"ANDRE.*SILVA.*BATISTA|Andr[eé]\s+da\s+Silva|73551559-3",
        re.IGNORECASE,
    )

    REGEX_AGENCIA_ANDRE: re.Pattern[str] = re.compile(
        r"Ag[eê]ncia:\s*6450",
        re.IGNORECASE,
    )

    REGEX_PIX: re.Pattern[str] = re.compile(
        r"Pix|PIX",
    )

    REGEX_BOLETO: re.Pattern[str] = re.compile(
        r"boleto|Boleto|BOLETO",
    )

    REGEX_DEBITO: re.Pattern[str] = re.compile(
        r"[Dd][eé]bito",
    )

    REGEX_TED: re.Pattern[str] = re.compile(
        r"TED|[Tt]ransfer[eê]ncia\s+enviada(?!\s+pelo\s+Pix)",
    )

    REGEX_TRANSFERENCIA_RECEBIDA: re.Pattern[str] = re.compile(
        r"Transfer[eê]ncia\s+Recebida",
        re.IGNORECASE,
    )

    REGEX_RESGATE: re.Pattern[str] = re.compile(
        r"Resgate\s+RDB|Resgate\s+CDB",
        re.IGNORECASE,
    )

    REGEX_APLICACAO: re.Pattern[str] = re.compile(
        r"Aplica[cç][aã]o\s+RDB|Aplica[cç][aã]o\s+CDB",
        re.IGNORECASE,
    )

    REGEX_PAGAMENTO_FATURA: re.Pattern[str] = re.compile(
        r"NU\s*PAGAMENT|pagamento\s+de\s+fatura",
        re.IGNORECASE,
    )

    def __init__(self, caminho: Path) -> None:
        super().__init__(caminho)
        self.logger = configurar_logger("ExtratorNubankCC")

    def pode_processar(self, caminho: Path) -> bool:
        """Verifica se é um CSV de conta corrente Nubank."""
        if not caminho.suffix.lower() == ".csv":
            return False
        try:
            with open(caminho, encoding="utf-8") as f:
                cabecalho: str = f.readline().strip()
                campos: list[str] = [c.strip() for c in cabecalho.split(",")]
                return campos == ["Data", "Valor", "Identificador", "Descrição"]
        except (OSError, UnicodeDecodeError):
            return False

    def extrair(self) -> list[Transacao]:
        """Extrai todas as transações dos CSVs no diretório configurado."""
        transacoes: list[Transacao] = []
        arquivos: list[Path] = self._listar_arquivos()

        if not arquivos:
            self.logger.warning("Nenhum arquivo CSV encontrado em %s", self.caminho)
            return transacoes

        ids_vistos: set[str] = set()

        for arquivo in arquivos:
            self.logger.info("Processando extrato Nubank CC: %s", arquivo.name)
            novas: list[Transacao] = self._processar_arquivo(arquivo)

            for transacao in novas:
                if transacao.identificador and transacao.identificador in ids_vistos:
                    self.logger.debug("Transação duplicada ignorada: %s", transacao.identificador)
                    continue
                if transacao.identificador:
                    ids_vistos.add(transacao.identificador)
                transacoes.append(transacao)

        self.logger.info("Total de transações extraídas (Nubank CC): %d", len(transacoes))
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
        conta_tipo: str = self._detectar_conta(arquivo)

        try:
            with open(arquivo, encoding="utf-8") as f:
                leitor = csv.DictReader(f)
                for linha in leitor:
                    transacao: Optional[Transacao] = self._parse_linha(
                        linha, pessoa, conta_tipo, arquivo
                    )
                    if transacao:
                        transacoes.append(transacao)
        except (OSError, csv.Error) as erro:
            self.logger.error("Erro ao processar %s: %s", arquivo.name, erro)

        return transacoes

    def _parse_linha(
        self,
        linha: dict[str, str],
        pessoa: str,
        conta_tipo: str,
        arquivo: Path,
    ) -> Optional[Transacao]:
        """Converte uma linha do CSV em Transação."""
        try:
            data_str: str = linha["Data"].strip()
            valor_str: str = linha["Valor"].strip()
            identificador: str = linha["Identificador"].strip()
            descricao_raw: str = linha["Descrição"].strip()

            descricao: str = html.unescape(descricao_raw)

            data_transacao: date = datetime.strptime(data_str, "%d/%m/%Y").date()
            valor: float = float(valor_str)

            forma_pagamento: str = self._inferir_forma_pagamento(descricao)
            tipo: str = self._classificar_tipo(descricao, valor, pessoa)

            banco_origem: str = f"Nubank ({conta_tipo})"

            return Transacao(
                data=data_transacao,
                valor=valor,
                descricao=descricao,
                banco_origem=banco_origem,
                pessoa=pessoa,
                forma_pagamento=forma_pagamento,
                tipo=tipo,
                identificador=identificador,
                arquivo_origem=str(arquivo.name),
            )
        except (ValueError, KeyError) as erro:
            self.logger.warning("Linha ignorada em %s: %s - %s", arquivo.name, linha, erro)
            return None

    def _detectar_conta(self, caminho: Path) -> str:
        """Detecta o tipo de conta (PF ou PJ) pelo caminho."""
        partes: str = str(caminho).lower()
        if "nubank_pj" in partes:
            return "PJ"
        return "PF"

    def _inferir_forma_pagamento(self, descricao: str) -> str:
        """Infere a forma de pagamento a partir da descrição."""
        if self.REGEX_PIX.search(descricao):
            return "Pix"
        if self.REGEX_BOLETO.search(descricao):
            return "Boleto"
        if self.REGEX_DEBITO.search(descricao):
            return "Débito"
        if self.REGEX_TED.search(descricao):
            return "Transferência"
        return "Transferência"

    def _classificar_tipo(self, descricao: str, valor: float, pessoa: str) -> str:
        """Classifica o tipo da transação baseado na descrição e valor.

        Sprint 68: substituída whitelist regex hardcoded (REGEX_ANDRE com
        fragmentos genéricos como `ANDRE.*SILVA.*BATISTA`) pelo matcher
        formal `canonicalizer_casal.e_transferencia_do_casal`, que consulta
        `mappings/contas_casal.yaml`. Mantém exceções operacionais legítimas
        (pagamento de fatura, resgate/aplicação CDB/RDB, agência 6450).
        """
        if e_transferencia_do_casal(descricao):
            return "Transferência Interna"

        if self._e_transferencia_do_andre(descricao):
            return "Transferência Interna"

        if self.REGEX_RESGATE.search(descricao) or self.REGEX_APLICACAO.search(descricao):
            return "Transferência Interna"

        if valor > 0:
            if self.REGEX_TRANSFERENCIA_RECEBIDA.search(descricao):
                return "Receita"
            return "Receita"

        if valor < 0:
            if re.search(r"DAS.*Simples|DARF|RECEITA\s*FED", descricao, re.IGNORECASE):
                return "Imposto"
            return "Despesa"

        return "Despesa"

    def _e_transferencia_do_andre(self, descricao: str) -> bool:
        """Verifica operacionalmente se a transação é da pessoa_a via agência/conta.

        Nota Sprint 68: a checagem por nome ("ANDRE.*SILVA.*BATISTA") migrou
        para `canonicalizer_casal.e_transferencia_do_casal`. Este método
        agora cobre apenas os sinalizadores operacionais que a whitelist de
        nomes não captura (agência 6450 do Itaú).
        """
        if self.REGEX_AGENCIA_ANDRE.search(descricao):
            return True
        return False


# "A liberdade é o direito de fazer tudo o que as leis permitem." -- Montesquieu
