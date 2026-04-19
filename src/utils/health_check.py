"""Health check do ambiente: verifica infraestrutura, dependências e artefatos."""

from __future__ import annotations

import importlib
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.utils.logger import configurar_logger

logger = configurar_logger("health_check")

RAIZ = Path(__file__).parent.parent.parent
DIR_DATA = RAIZ / "data"
DIR_RAW = DIR_DATA / "raw"
DIR_OUTPUT = DIR_DATA / "output"
DIR_HISTORICO = DIR_DATA / "historico"
DIR_LOGS = RAIZ / "logs"
DIR_MAPPINGS = RAIZ / "mappings"

DEPENDENCIAS_CRITICAS: tuple[str, ...] = (
    "openpyxl",
    "pandas",
    "pdfplumber",
    "msoffcrypto",
    "pytesseract",
    "ofxparse",
    "yaml",
    "rich",
    "streamlit",
)

MAPPINGS_OBRIGATORIOS: tuple[str, ...] = (
    "categorias.yaml",
    "overrides.yaml",
    "metas.yaml",
)

MAPPINGS_OPCIONAIS: tuple[str, ...] = ("senhas.yaml",)


@dataclass(frozen=True)
class Resultado:
    """Representa uma checagem individual do health check."""

    nome: str
    ok: bool
    mensagem: str
    severidade: str = "erro"


def verificar_python() -> Resultado:
    """Confere que o Python é 3.11+ (requisito do projeto)."""
    major, minor = sys.version_info.major, sys.version_info.minor
    versao = f"{major}.{minor}.{sys.version_info.micro}"
    ok = (major, minor) >= (3, 11)
    return Resultado(
        nome="Python 3.11+",
        ok=ok,
        mensagem=f"Python {versao}" + ("" if ok else " -- requer 3.11 ou superior"),
    )


def verificar_venv() -> Resultado:
    """Confere que estamos dentro de um ambiente virtual."""
    ativo = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    return Resultado(
        nome="Ambiente virtual",
        ok=ativo,
        mensagem=f"sys.prefix={sys.prefix}" + ("" if ativo else " -- ative .venv"),
        severidade="aviso" if not ativo else "info",
    )


def verificar_dependencias() -> list[Resultado]:
    """Confere importabilidade das dependências críticas."""
    resultados: list[Resultado] = []
    for nome in DEPENDENCIAS_CRITICAS:
        try:
            modulo = importlib.import_module(nome)
            versao = getattr(modulo, "__version__", "?")
            resultados.append(
                Resultado(
                    nome=f"dep:{nome}",
                    ok=True,
                    mensagem=f"{nome} {versao}",
                )
            )
        except ImportError as err:
            resultados.append(
                Resultado(
                    nome=f"dep:{nome}",
                    ok=False,
                    mensagem=f"{nome} indisponível ({err})",
                )
            )
    return resultados


def verificar_tesseract() -> Resultado:
    """Confere que o binário tesseract está acessível no PATH."""
    caminho = shutil.which("tesseract")
    ok = caminho is not None
    return Resultado(
        nome="Binário tesseract",
        ok=ok,
        mensagem=f"tesseract em {caminho}" if ok else "tesseract não encontrado no PATH",
        severidade="aviso" if not ok else "info",
    )


def verificar_estrutura_data() -> list[Resultado]:
    """Confere que os diretórios esperados em data/ existem."""
    resultados: list[Resultado] = []
    for diretorio in (DIR_DATA, DIR_RAW, DIR_OUTPUT, DIR_HISTORICO):
        existe = diretorio.exists() and diretorio.is_dir()
        resultados.append(
            Resultado(
                nome=f"dir:{diretorio.relative_to(RAIZ)}",
                ok=existe,
                mensagem=(
                    f"{diretorio.relative_to(RAIZ)} existe"
                    if existe
                    else f"{diretorio.relative_to(RAIZ)} ausente"
                ),
                severidade="aviso" if not existe else "info",
            )
        )
    return resultados


def verificar_mappings() -> list[Resultado]:
    """Confere existência dos mappings obrigatórios e opcionais."""
    resultados: list[Resultado] = []
    for nome in MAPPINGS_OBRIGATORIOS:
        caminho = DIR_MAPPINGS / nome
        existe = caminho.exists()
        resultados.append(
            Resultado(
                nome=f"mapping:{nome}",
                ok=existe,
                mensagem=f"{nome} presente" if existe else f"{nome} ausente -- obrigatório",
            )
        )
    for nome in MAPPINGS_OPCIONAIS:
        caminho = DIR_MAPPINGS / nome
        existe = caminho.exists()
        resultados.append(
            Resultado(
                nome=f"mapping:{nome}",
                ok=True,
                mensagem=(f"{nome} presente" if existe else f"{nome} ausente -- opcional"),
                severidade="info" if existe else "aviso",
            )
        )
    return resultados


def _xlsx_mais_recente() -> Path | None:
    """Encontra o XLSX do Ouroboros mais recente."""
    if not DIR_OUTPUT.exists():
        return None
    arquivos = sorted(DIR_OUTPUT.glob("ouroboros_*.xlsx"), reverse=True)
    return arquivos[0] if arquivos else None


def verificar_xlsx() -> Resultado:
    """Confere se existe XLSX gerado e reporta idade."""
    caminho = _xlsx_mais_recente()
    if caminho is None:
        return Resultado(
            nome="XLSX gerado",
            ok=False,
            mensagem="Nenhum ouroboros_*.xlsx em data/output/",
            severidade="aviso",
        )
    mtime = datetime.fromtimestamp(caminho.stat().st_mtime)
    idade_horas = (datetime.now() - mtime).total_seconds() / 3600
    detalhe = f"{caminho.name} ({mtime:%Y-%m-%d %H:%M}, {idade_horas:.1f}h atrás)"
    return Resultado(nome="XLSX gerado", ok=True, mensagem=detalhe)


def verificar_relatorios() -> Resultado:
    """Conta relatórios mensais gerados em data/output/."""
    if not DIR_OUTPUT.exists():
        return Resultado(
            nome="Relatórios mensais",
            ok=False,
            mensagem="data/output/ não existe",
            severidade="aviso",
        )
    relatorios = list(DIR_OUTPUT.glob("*_relatorio.md"))
    total = len(relatorios)
    return Resultado(
        nome="Relatórios mensais",
        ok=total > 0,
        mensagem=f"{total} relatórios .md gerados",
        severidade="info" if total > 0 else "aviso",
    )


def verificar_logs() -> Resultado:
    """Confere se o logger está rotacionando em logs/."""
    if not DIR_LOGS.exists():
        return Resultado(
            nome="Logs",
            ok=False,
            mensagem="diretório logs/ ausente (será criado na próxima execução)",
            severidade="aviso",
        )
    arquivos = list(DIR_LOGS.glob("*.log*"))
    return Resultado(
        nome="Logs",
        ok=True,
        mensagem=f"{len(arquivos)} arquivos de log em logs/",
    )


def _formatar_prefixo(res: Resultado) -> str:
    """Retorna prefixo visual conforme o status."""
    if res.ok:
        return "[OK]"
    if res.severidade == "aviso":
        return "[!!]"
    return "[X] "


def executar_health_check() -> bool:
    """Executa todas as checagens e retorna True se não há erro crítico."""
    checagens: list[Resultado] = []
    checagens.append(verificar_python())
    checagens.append(verificar_venv())
    checagens.extend(verificar_dependencias())
    checagens.append(verificar_tesseract())
    checagens.extend(verificar_estrutura_data())
    checagens.extend(verificar_mappings())
    checagens.append(verificar_xlsx())
    checagens.append(verificar_relatorios())
    checagens.append(verificar_logs())

    erros = 0
    avisos = 0

    logger.info("=== Health Check do Protocolo Ouroboros ===")
    for res in checagens:
        prefixo = _formatar_prefixo(res)
        logger.info("%s %s -- %s", prefixo, res.nome, res.mensagem)
        if not res.ok and res.severidade == "erro":
            erros += 1
        elif not res.ok and res.severidade == "aviso":
            avisos += 1

    logger.info(
        "=== Resumo: %d checagens, %d erros, %d avisos ===",
        len(checagens),
        erros,
        avisos,
    )

    return erros == 0


def main() -> None:
    """Entrypoint CLI para health check."""
    ok = executar_health_check()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()


# "Conhece-te a ti mesmo." -- Sócrates
