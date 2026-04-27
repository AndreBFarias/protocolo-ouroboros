"""Configuração centralizada de logging com rotação de arquivos.

Sprint 99: redactor de PII em logs INFO. Filter customizado mascara CPF e
CNPJ literais antes de emit (privacy by default). Em nível DEBUG mantém
literal -- desenvolvedor que ativa DEBUG aceita ver PII para diagnóstico.

Razão social não é mascarada por regex aqui (palavras humanas variam
demais). A mitigação é feita na origem: módulos que exponham razão social
em log devem usar `hash_curto_pii(razao)` em vez de literal.
"""

import hashlib
import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.logging import RichHandler

# Regex compiladas uma vez na importação (custo negligível em emit).
# CPF: 000.000.000-00
_RE_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
# CNPJ: 00.000.000/0000-00
_RE_CNPJ = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")

# Placeholders canônicos. Mantêm o formato visualmente reconhecível para
# debug humano sem expor o valor real.
_PLACEHOLDER_CPF = "XXX.XXX.XXX-XX"
_PLACEHOLDER_CNPJ_PJ = "XX.XXX.XXX/0001-XX"
_PLACEHOLDER_CNPJ_GENERICO = "XX.XXX.XXX/XXXX-XX"


def mascarar_pii(mensagem: str) -> str:
    """Substitui CPF/CNPJ literais por placeholders canônicos.

    Função pura. Reutilizável fora do filter quando necessário (ex.: relatório
    `.md`, JSON exibido em UI, observação humana persistida).

    CNPJ com sufixo `/0001-XX` (matriz, padrão MEI/PJ) recebe placeholder
    distinto que preserva essa pista. Demais CNPJs viram `XX.XXX.XXX/XXXX-XX`.
    """
    if not mensagem:
        return mensagem

    def _sub_cnpj(match: re.Match[str]) -> str:
        original = match.group(0)
        if "/0001-" in original:
            return _PLACEHOLDER_CNPJ_PJ
        return _PLACEHOLDER_CNPJ_GENERICO

    mensagem = _RE_CPF.sub(_PLACEHOLDER_CPF, mensagem)
    mensagem = _RE_CNPJ.sub(_sub_cnpj, mensagem)
    return mensagem


def hash_curto_pii(valor: str) -> str:
    """Devolve hash curto (8 chars hex) para referência sem expor literal.

    Use em logs/relatórios quando precisar correlacionar a mesma entidade
    em mensagens distintas sem vazar nome, CPF ou CNPJ. SHA-256 truncado em
    8 caracteres hex (32 bits) tem colisão prática negligível para volumes
    de dezenas de pessoas/empresas.
    """
    if not valor:
        return "00000000"
    digest = hashlib.sha256(valor.strip().upper().encode("utf-8")).hexdigest()
    return digest[:8]


class FiltroRedactorPII(logging.Filter):
    """Filter que mascara CPF/CNPJ em mensagens com `levelno >= INFO`.

    DEBUG não é tocado (uso dev). Reescreve `record.msg` após formatar com
    `record.getMessage()` para apanhar tanto args literais quanto interpolados.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno < logging.INFO:
            return True
        # Materializa a mensagem final (com args já interpolados) para que o
        # mascaramento funcione tanto em `logger.info("CPF %s", cpf)` quanto
        # em `logger.info(f"CPF {cpf}")`.
        try:
            mensagem_formatada = record.getMessage()
        except (TypeError, ValueError):
            return True
        mensagem_mascarada = mascarar_pii(mensagem_formatada)
        if mensagem_mascarada != mensagem_formatada:
            record.msg = mensagem_mascarada
            record.args = None
        return True


def configurar_logger(nome: str, nivel: int = logging.INFO) -> logging.Logger:
    """Configura e retorna um logger com saída rich no terminal e rotação em arquivo."""
    logger = logging.getLogger(nome)

    if logger.handlers:
        return logger

    logger.setLevel(nivel)

    diretorio_logs = Path(__file__).parent.parent.parent / "logs"
    diretorio_logs.mkdir(exist_ok=True)

    handler_arquivo = RotatingFileHandler(
        diretorio_logs / "controle_de_bordo.log",
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler_arquivo.setLevel(logging.DEBUG)
    handler_arquivo.setFormatter(
        logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
    )

    handler_console = RichHandler(
        rich_tracebacks=True,
        show_time=True,
        show_path=False,
    )
    handler_console.setLevel(nivel)

    logger.addHandler(handler_arquivo)
    logger.addHandler(handler_console)

    # Sprint 99: filter de PII aplicado no logger (afeta os dois handlers).
    # Adiciona apenas se ainda não houver instância -- evita duplicar em
    # reconfigurações de teste.
    if not any(isinstance(f, FiltroRedactorPII) for f in logger.filters):
        logger.addFilter(FiltroRedactorPII())

    return logger


# "O homem que move montanhas começa carregando pequenas pedras." -- Confúcio
