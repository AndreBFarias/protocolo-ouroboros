"""Migra holerites mal classificados ou com nomes brutos para forma canônica.

Origem: Sprint 98 (auditoria 2026-04-26). Após a Sprint 90a prevenir novos
casos no inbox, esta sprint limpa o legado em duas frentes:

1. Holerites G4F mal classificados em pastas bancárias (`itau_cc/`,
   `santander_cartao/`). A heurística do inbox antigo confundia o PDF
   nativo G4F com extrato Itaú/fatura Santander. Aqui detectamos pelo
   conteúdo (regex de "Demonstrativo de Pagamento de Salário" ou
   "G4F SOLUCOES CORPORATIVAS") e movemos para `holerites/`.
2. Holerites já em `holerites/` com nomes brutos (`document(N).pdf`,
   `holerite_NNNNNNNNNNNN.pdf`) renomeados para o padrão canônico
   `HOLERITE_<fonte>_<mes_ref>_<sha8>.pdf`.

Uso:
    .venv/bin/python scripts/migrar_holerites_retroativo.py            # dry-run
    .venv/bin/python scripts/migrar_holerites_retroativo.py --executar # aplica

Contratos invioláveis:
- Originais em `data/raw/_envelopes/originais/<sha>.<ext>` permanecem
  intactos (preservação ADR-18). Esta migração só toca cópias de trabalho
  em `data/raw/<pessoa>/<banco|holerites>/`.
- Idempotente: se o arquivo já está no destino canônico com o mesmo nome,
  pulamos sem erro.
- Dry-run é o default. Só `--executar` move/renomeia de fato.
- Logs vão para `scripts/migracao_holerites_<YYYY-MM-DD>.log` com hash
  truncado de cada ação. PII (nome do funcionário, CPF) NÃO entra no log.
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import sys
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Optional

_RAIZ = Path(__file__).resolve().parents[1]
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from src.intake import sha8_arquivo  # noqa: E402
from src.utils.logger import configurar_logger  # noqa: E402

logger = configurar_logger("scripts.migrar_holerites_retroativo")


# ============================================================================
# Constantes -- pastas e marcadores
# ============================================================================

_DIR_ANDRE = _RAIZ / "data" / "raw" / "andre"
_DIR_ITAU_CC = _DIR_ANDRE / "itau_cc"
_DIR_SANTANDER_CARTAO = _DIR_ANDRE / "santander_cartao"
_DIR_HOLERITES = _DIR_ANDRE / "holerites"

# Marcadores de holerite no texto da primeira página. Heurística mínima e
# tolerante a variações de acentuação ou caixa. Se QUALQUER um casa, é
# holerite. Os marcadores cobrem os dois fornecedores conhecidos (G4F nativo
# e Infobase escaneado).
_REGEX_DEMONSTRATIVO = re.compile(
    r"Demonstrativo\s+de\s+Pagamento\s+de\s+Sal[aáÁ]rio",
    re.IGNORECASE,
)
_REGEX_G4F_CORPORATIVO = re.compile(
    r"G4F\s+SOLU[CÇ][OÕ]ES\s+CORPORATIVAS",
    re.IGNORECASE,
)
_REGEX_INFOBASE = re.compile(r"INFOBASE", re.IGNORECASE)

# Nomes brutos reconhecidos em `holerites/` que precisam de canonicalização.
# `document(N).pdf`, `document(N) (1).pdf` (duplicata do download), e
# `holerite_<timestamp>.pdf`.
_REGEX_NOME_BRUTO = re.compile(
    r"^(document\(\d+\)(\s*\(\d+\))?|holerite_\d+)$",
    re.IGNORECASE,
)
_REGEX_NOME_CANONICO = re.compile(
    r"^HOLERITE_[A-Za-z0-9]+_\d{4}-\d{2}_[0-9a-f]{8}$",
)


# ============================================================================
# Estruturas
# ============================================================================


class PropostaMigracao:
    """Descrição de uma ação proposta -- usada em dry-run e log."""

    __slots__ = ("origem", "destino", "categoria", "fonte", "mes_ref", "sha8")

    def __init__(
        self,
        *,
        origem: Path,
        destino: Path,
        categoria: str,
        fonte: Optional[str],
        mes_ref: Optional[str],
        sha8: str,
    ) -> None:
        self.origem = origem
        self.destino = destino
        self.categoria = categoria
        self.fonte = fonte
        self.mes_ref = mes_ref
        self.sha8 = sha8

    def linha_log(self) -> str:
        fonte = self.fonte or "?"
        mes = self.mes_ref or "?"
        return (
            f"[{self.categoria}] sha8={self.sha8} fonte={fonte} mes_ref={mes} "
            f"origem={self.origem.relative_to(_RAIZ)} -> "
            f"destino={self.destino.relative_to(_RAIZ)}"
        )


# ============================================================================
# Detecção
# ============================================================================


def _ler_texto_primeira_pagina(caminho: Path) -> str:
    """Extrai texto da primeira página com fallback OCR.

    Reusa o helper privado do extrator de contracheque para manter o mesmo
    contrato (pdfplumber primeiro, OCR via pypdfium2 + tesseract se vazio).
    Importação tardia evita custo de OCR quando o script só lista candidatos.
    """
    from src.extractors.contracheque_pdf import _extrair_texto

    return _extrair_texto(caminho)


def _eh_holerite(texto: str) -> bool:
    """Verdadeiro se o texto contém marcador de holerite conhecido."""
    if not texto:
        return False
    if _REGEX_DEMONSTRATIVO.search(texto):
        return True
    if _REGEX_G4F_CORPORATIVO.search(texto):
        return True
    if _REGEX_INFOBASE.search(texto):
        return True
    return False


def _extrair_fonte_e_mes(texto: str) -> tuple[Optional[str], Optional[str]]:
    """Detecta fonte (G4F/Infobase) e mes_ref (YYYY-MM) reusando o extrator."""
    from src.extractors.contracheque_pdf import (
        _detectar_fonte,
        _parse_g4f,
        _parse_infobase,
    )

    fonte = _detectar_fonte(texto)
    if fonte == "G4F":
        registro = _parse_g4f(texto)
    elif fonte == "Infobase":
        registro = _parse_infobase(texto)
    else:
        registro = None

    if registro is None:
        return fonte, None
    return fonte, registro.get("mes_ref")


# ============================================================================
# Construção de nome canônico
# ============================================================================


def _nome_canonico(*, fonte: str, mes_ref: Optional[str], sha8: str) -> str:
    """Monta o nome canônico HOLERITE_<fonte>_<mes_ref>_<sha8>.pdf.

    Quando `mes_ref` não está disponível (parser não casou), omite a parte
    do mês para preservar idempotência por sha8 e evitar chave inválida.
    """
    fonte_slug = re.sub(r"[^A-Za-z0-9]+", "", fonte).upper() or "DESCONHECIDO"
    if mes_ref:
        return f"HOLERITE_{fonte_slug}_{mes_ref}_{sha8}.pdf"
    return f"HOLERITE_{fonte_slug}_{sha8}.pdf"


# ============================================================================
# Fase 1 -- detectar holerites em pastas bancárias erradas
# ============================================================================


def _proposta_pasta_bancaria(arquivo: Path) -> Optional[PropostaMigracao]:
    """Avalia um PDF em pasta bancária. Retorna ação se for holerite."""
    try:
        texto = _ler_texto_primeira_pagina(arquivo)
    except Exception as exc:  # defensivo -- nunca derrubar a varredura
        logger.warning("Falha ao ler %s: %s", arquivo.name, exc)
        return None

    if not _eh_holerite(texto):
        return None

    sha8 = sha8_arquivo(arquivo)
    fonte, mes_ref = _extrair_fonte_e_mes(texto)
    fonte_efetiva = fonte or "G4F"  # fallback razoável dado contexto histórico
    nome = _nome_canonico(fonte=fonte_efetiva, mes_ref=mes_ref, sha8=sha8)
    destino = _DIR_HOLERITES / nome

    if destino.resolve() == arquivo.resolve():
        return None  # idempotência -- já está canônico no lugar certo

    return PropostaMigracao(
        origem=arquivo,
        destino=destino,
        categoria="MAL_CLASSIFICADO",
        fonte=fonte_efetiva,
        mes_ref=mes_ref,
        sha8=sha8,
    )


def _coletar_pastas_bancarias() -> list[PropostaMigracao]:
    """Varre itau_cc/ e santander_cartao/ procurando holerites."""
    propostas: list[PropostaMigracao] = []
    for pasta in (_DIR_ITAU_CC, _DIR_SANTANDER_CARTAO):
        if not pasta.exists():
            logger.info("Pasta inexistente, pulando: %s", pasta)
            continue
        for arquivo in sorted(pasta.glob("*.pdf")):
            proposta = _proposta_pasta_bancaria(arquivo)
            if proposta is not None:
                propostas.append(proposta)
    return propostas


# ============================================================================
# Fase 2 -- renomear holerites com nomes brutos
# ============================================================================


def _proposta_holerite_bruto(arquivo: Path) -> Optional[PropostaMigracao]:
    """Avalia um PDF em holerites/ com nome bruto. Retorna ação ou None."""
    stem = arquivo.stem
    if _REGEX_NOME_CANONICO.match(stem):
        return None  # já canônico
    if not _REGEX_NOME_BRUTO.match(stem):
        return None  # nome em formato não previsto, deixar para revisão humana

    try:
        texto = _ler_texto_primeira_pagina(arquivo)
    except Exception as exc:
        logger.warning("Falha ao ler %s: %s", arquivo.name, exc)
        return None

    if not _eh_holerite(texto):
        # nome de holerite mas conteúdo não casa -- não tocar
        logger.warning(
            "Arquivo %s tem nome bruto de holerite mas conteúdo não confirma; pulando.",
            arquivo.name,
        )
        return None

    sha8 = sha8_arquivo(arquivo)
    fonte, mes_ref = _extrair_fonte_e_mes(texto)
    fonte_efetiva = fonte or "DESCONHECIDO"
    nome = _nome_canonico(fonte=fonte_efetiva, mes_ref=mes_ref, sha8=sha8)
    destino = arquivo.with_name(nome)

    if destino.resolve() == arquivo.resolve():
        return None

    return PropostaMigracao(
        origem=arquivo,
        destino=destino,
        categoria="NOME_BRUTO",
        fonte=fonte_efetiva,
        mes_ref=mes_ref,
        sha8=sha8,
    )


def _coletar_holerites_brutos() -> list[PropostaMigracao]:
    if not _DIR_HOLERITES.exists():
        logger.info("Pasta holerites/ não existe: %s", _DIR_HOLERITES)
        return []
    propostas: list[PropostaMigracao] = []
    for arquivo in sorted(_DIR_HOLERITES.glob("*.pdf")):
        proposta = _proposta_holerite_bruto(arquivo)
        if proposta is not None:
            propostas.append(proposta)
    return propostas


# ============================================================================
# Execução
# ============================================================================


def _aplicar_acao(proposta: PropostaMigracao) -> bool:
    """Move/renomeia origem -> destino. Idempotente.

    Se destino já existe e tem o mesmo conteúdo (sha8 do arquivo de destino
    == sha8 da origem), apenas remove a origem. Caso contrário levanta
    FileExistsError para não sobrescrever.
    """
    proposta.destino.parent.mkdir(parents=True, exist_ok=True)
    if proposta.destino.exists():
        sha_destino = sha8_arquivo(proposta.destino)
        if sha_destino == proposta.sha8:
            logger.info(
                "Destino já existe com mesmo conteúdo (sha8=%s); removendo origem %s",
                proposta.sha8,
                proposta.origem.name,
            )
            proposta.origem.unlink()
            return True
        raise FileExistsError(
            f"Destino diferente já existe: {proposta.destino} (sha8 destino "
            f"{sha_destino} != origem {proposta.sha8})"
        )
    shutil.move(str(proposta.origem), str(proposta.destino))
    return True


def _abrir_log_migracao() -> logging.Logger:
    """Cria logger de auditoria que persiste em scripts/migracao_holerites_<data>.log."""
    log_path = _RAIZ / "scripts" / f"migracao_holerites_{datetime.now():%Y-%m-%d}.log"
    audit = logging.getLogger("migracao_holerites_audit")
    audit.setLevel(logging.INFO)
    # idempotência do logger -- não duplicar handlers em re-execuções
    if not any(
        isinstance(h, logging.FileHandler) and Path(h.baseFilename) == log_path
        for h in audit.handlers
    ):
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
        audit.addHandler(handler)
    return audit


def _imprimir_resumo(propostas: Iterable[PropostaMigracao], *, dry_run: bool) -> None:
    acoes_lista = list(propostas)
    titulo = "DRY-RUN" if dry_run else "EXECUÇÃO"
    logger.info("=" * 72)
    logger.info("%s -- %d ações propostas", titulo, len(acoes_lista))
    logger.info("=" * 72)

    por_categoria: dict[str, int] = {}
    for proposta in acoes_lista:
        por_categoria[proposta.categoria] = por_categoria.get(proposta.categoria, 0) + 1
        logger.info(proposta.linha_log())

    logger.info("-" * 72)
    for cat, qtd in sorted(por_categoria.items()):
        logger.info("Total %s: %d", cat, qtd)
    logger.info("-" * 72)


# ============================================================================
# CLI
# ============================================================================


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migra holerites mal classificados ou com nomes brutos.",
    )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Lista ações propostas sem mover nada (default).",
    )
    grupo.add_argument(
        "--executar",
        action="store_true",
        default=False,
        help="Aplica as movimentações de fato. Sem isto, só lista.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    dry_run = not args.executar

    logger.info("Coletando holerites mal classificados em pastas bancárias...")
    acoes_pastas = _coletar_pastas_bancarias()
    logger.info("Coletando holerites com nomes brutos em holerites/...")
    acoes_brutos = _coletar_holerites_brutos()
    todas = acoes_pastas + acoes_brutos

    _imprimir_resumo(todas, dry_run=dry_run)

    if dry_run:
        logger.info("Dry-run apenas. Para aplicar: rode novamente com --executar.")
        return 0

    audit = _abrir_log_migracao()
    audit.info("Início execução -- %d ações", len(todas))
    aplicadas = 0
    falhas = 0
    for proposta in todas:
        try:
            _aplicar_acao(proposta)
            audit.info("OK | %s", proposta.linha_log())
            aplicadas += 1
        except Exception as exc:
            audit.error("FALHA | %s | erro=%s", proposta.linha_log(), exc)
            logger.error("Falha em %s: %s", proposta.origem.name, exc)
            falhas += 1
    audit.info("Fim execução -- aplicadas=%d falhas=%d", aplicadas, falhas)
    logger.info("Aplicadas: %d / Falhas: %d", aplicadas, falhas)
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())


# "O que importa não é a velocidade, mas a direção." -- Sêneca
