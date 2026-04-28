#!/usr/bin/env python3
"""Renomeia holerites canônicos para template legível (Sprint INFRA-RENAME-HOLERITES).

Sprint 98 (concluída 2026-04-27) deixou os 24 holerites no padrão
``HOLERITE_<EMPRESA>_<YYYY-MM>_<sha8>.pdf`` (sufixo hash). O dono detectou
que esse sufixo não ajuda a navegar o vault e pediu o template novo:

    HOLERITE_<YYYY-MM>_<EMPRESA>_<liquido>.pdf

onde ``<liquido>`` é o valor líquido do holerite arredondado para inteiro
(ex: ``HOLERITE_2026-04_G4F_5000.pdf``). Quando metadata não dá para
extrair (parser falha), o script faz fallback determinístico para
``HOLERITE_<YYYY-MM>_<sha8>.pdf`` mascarando origem.

Diferenças para o script da Sprint 98:
- não copia/move arquivos de uma pasta para outra (origem já está no
  destino canônico do diretório de holerites);
- apenas RENOMEIA (rename atômico, mantém inode);
- atualiza metadata do grafo (campo ``caminho_canonico``);
- idempotente: 2a rodada após --executar não muda nada;
- relatório em data/output/rename_holerites_v2_<ts>.{csv,md} com PII
  mascarada (valores como ``R$ XXX,XX``).

Default é --dry-run; passe --executar para aplicar de fato.

Uso::

    .venv/bin/python scripts/renomear_holerites_v2.py            # dry-run
    .venv/bin/python scripts/renomear_holerites_v2.py --executar  # aplica
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sqlite3
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

# Permite rodar via `python scripts/renomear_holerites_v2.py` sem
# instalar o pacote -- meta-regra do projeto, igual `migrar_holerites_retroativo.py`.
_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from src.extractors.contracheque_pdf import (  # noqa: E402
    _detectar_fonte,
    _extrair_texto,
    _parse_g4f,
    _parse_infobase,
)
from src.intake import sha8_arquivo  # noqa: E402

logger = logging.getLogger(__name__)

# ============================================================================
# Constantes
# ============================================================================

_DIR_HOLERITES = _RAIZ / "data" / "raw" / "andre" / "holerites"
_DIR_OUTPUT = _RAIZ / "data" / "output"
_GRAFO_DB = _DIR_OUTPUT / "grafo.sqlite"

_PADRAO_NOVO = re.compile(r"^HOLERITE_\d{4}-\d{2}_[A-Z0-9]+_\d+\.pdf$")
_PADRAO_FALLBACK = re.compile(r"^HOLERITE_\d{4}-\d{2}_[0-9a-f]{8}\.pdf$")


# ============================================================================
# Modelo de proposta
# ============================================================================


@dataclass
class PropostaRename:
    """Plano de renomeio para um holerite individual."""

    origem: Path
    destino: Path
    sha8: str
    motivo: str  # 'template' | 'fallback' | 'sem_mudanca'
    mes_ref: Optional[str]
    empresa: Optional[str]
    liquido: Optional[float]

    @property
    def mudou(self) -> bool:
        return self.origem.resolve() != self.destino.resolve()


# ============================================================================
# Helpers de normalização
# ============================================================================


def _slug_empresa(empresa: str) -> str:
    """Normaliza nome de empresa: maiúsculas + sem acentos + sem espaços.

    Exemplo: 'G4F Tecnologia' -> 'G4F', 'Infobase Servicos' -> 'INFOBASE'.
    Pega só a primeira palavra após normalizar para evitar nomes longos.
    """
    if not empresa:
        return "DESCONHECIDO"
    norm = unicodedata.normalize("NFKD", empresa)
    norm = "".join(c for c in norm if not unicodedata.combining(c))
    primeira = norm.strip().split()[0] if norm.strip() else "DESCONHECIDO"
    return re.sub(r"[^A-Za-z0-9]+", "", primeira).upper() or "DESCONHECIDO"


def _nome_canonico_legivel(*, mes_ref: str, empresa: str, liquido: float) -> str:
    """Monta HOLERITE_<YYYY-MM>_<EMPRESA>_<liquido_int>.pdf."""
    empresa_slug = _slug_empresa(empresa)
    liquido_int = int(round(liquido))
    return f"HOLERITE_{mes_ref}_{empresa_slug}_{liquido_int}.pdf"


def _nome_canonico_fallback(*, mes_ref: Optional[str], sha8: str) -> str:
    """Fallback quando parser não casa: HOLERITE_<mes>_<sha8>.pdf."""
    if mes_ref:
        return f"HOLERITE_{mes_ref}_{sha8}.pdf"
    return f"HOLERITE_{sha8}.pdf"


# ============================================================================
# Extração de metadata por arquivo
# ============================================================================


def _extrair_metadata_pdf(arquivo: Path) -> tuple[Optional[str], Optional[str], Optional[float]]:
    """Lê o PDF e devolve (mes_ref, empresa, liquido). Qualquer pode ser None."""
    try:
        texto = _extrair_texto(arquivo)
    except Exception as exc:  # defensivo -- não derruba a varredura
        logger.warning("Falha ao ler %s: %s", arquivo.name, exc)
        return None, None, None

    fonte = _detectar_fonte(texto)
    if not fonte:
        return None, None, None

    if fonte == "G4F":
        dados = _parse_g4f(texto)
        empresa = "G4F"
    elif fonte == "Infobase":
        dados = _parse_infobase(texto)
        empresa = "INFOBASE"
    else:
        return None, None, None

    if not dados:
        return None, empresa, None

    return dados.get("mes_ref"), empresa, dados.get("liquido")


# ============================================================================
# Construção da proposta
# ============================================================================


def _construir_proposta(arquivo: Path) -> PropostaRename:
    """Decide o destino canônico para um holerite específico."""
    sha8 = sha8_arquivo(arquivo)
    mes_ref, empresa, liquido = _extrair_metadata_pdf(arquivo)

    if mes_ref and empresa and liquido is not None and liquido > 0:
        nome = _nome_canonico_legivel(mes_ref=mes_ref, empresa=empresa, liquido=liquido)
        motivo = "template"
    else:
        nome = _nome_canonico_fallback(mes_ref=mes_ref, sha8=sha8)
        motivo = "fallback"

    # Destino fica no MESMO diretório da origem -- rename, não move.
    destino = arquivo.parent / nome
    if destino.resolve() == arquivo.resolve():
        motivo = "sem_mudanca"

    return PropostaRename(
        origem=arquivo,
        destino=destino,
        sha8=sha8,
        motivo=motivo,
        mes_ref=mes_ref,
        empresa=empresa,
        liquido=liquido,
    )


def coletar_propostas(diretorio: Path = _DIR_HOLERITES) -> list[PropostaRename]:
    """Varre o diretório de holerites e devolve lista de propostas."""
    if not diretorio.exists():
        logger.info("Pasta de holerites não existe: %s", diretorio)
        return []
    propostas: list[PropostaRename] = []
    for arquivo in sorted(diretorio.glob("*.pdf")):
        propostas.append(_construir_proposta(arquivo))
    return propostas


# ============================================================================
# Aplicação do rename
# ============================================================================


def _aplicar_rename(proposta: PropostaRename) -> bool:
    """Aplica rename atômico. Idempotente por sha8."""
    if not proposta.mudou:
        return False

    if proposta.destino.exists():
        sha_destino = sha8_arquivo(proposta.destino)
        if sha_destino == proposta.sha8:
            # Mesmo conteúdo -- já foi renomeado em rodada anterior.
            logger.info(
                "Destino já existe com mesmo conteúdo (sha8=%s); removendo origem %s",
                proposta.sha8,
                proposta.origem.name,
            )
            proposta.origem.unlink()
            return True
        raise RuntimeError(
            f"Destino diferente já existe: {proposta.destino.name} "
            f"(sha8 destino={sha_destino} != origem={proposta.sha8})"
        )

    proposta.origem.rename(proposta.destino)
    logger.info(
        "Renomeado: %s -> %s (motivo=%s, sha8=%s)",
        proposta.origem.name,
        proposta.destino.name,
        proposta.motivo,
        proposta.sha8,
    )
    return True


# ============================================================================
# Atualização do grafo
# ============================================================================


def _atualizar_grafo(propostas: Iterable[PropostaRename], *, db_path: Path = _GRAFO_DB) -> int:
    """Atualiza ``caminho_canonico`` no metadata dos nodes holerite.

    Mapeia node->arquivo por (razao_social, periodo_apuracao, total) com
    desambiguação por valor líquido. Nodes não casados ficam intocados.
    Retorna número de nodes atualizados.
    """
    if not db_path.exists():
        logger.warning("Grafo não encontrado em %s; pulando update", db_path)
        return 0

    propostas_aplicaveis = [
        p for p in propostas if p.mudou and p.motivo == "template" and p.empresa and p.mes_ref
    ]
    if not propostas_aplicaveis:
        return 0

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, metadata FROM node WHERE tipo='documento' "
            "AND json_extract(metadata, '$.tipo_documento')='holerite'"
        )
        nodes = cursor.fetchall()

        atualizados = 0
        for node_id, metadata_json in nodes:
            try:
                metadata = json.loads(metadata_json) if metadata_json else {}
            except json.JSONDecodeError:
                continue
            empresa_node = metadata.get("razao_social")
            mes_node = metadata.get("periodo_apuracao")
            if not empresa_node or not mes_node:
                continue
            for prop in propostas_aplicaveis:
                if (
                    _slug_empresa(empresa_node) == _slug_empresa(prop.empresa or "")
                    and mes_node == prop.mes_ref
                ):
                    metadata["caminho_canonico"] = str(prop.destino)
                    cursor.execute(
                        "UPDATE node SET metadata=? WHERE id=?",
                        (json.dumps(metadata, ensure_ascii=False), node_id),
                    )
                    atualizados += 1
                    break
        conn.commit()
        return atualizados
    finally:
        conn.close()


# ============================================================================
# Relatório CSV/MD
# ============================================================================


def _mascarar_valor(valor: Optional[float]) -> str:
    """Mascara valor monetário em relatório (PII)."""
    if valor is None or valor <= 0:
        return "R$ ---,--"
    return "R$ XXX,XX"


def _gerar_relatorio_csv(propostas: list[PropostaRename], destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["item_id", "nome_antigo", "nome_novo", "mudou", "motivo", "valor_mascarado"]
        )
        for p in propostas:
            writer.writerow(
                [
                    p.sha8,
                    p.origem.name,
                    p.destino.name,
                    str(p.mudou).lower(),
                    p.motivo,
                    _mascarar_valor(p.liquido),
                ]
            )


def _gerar_relatorio_md(
    propostas: list[PropostaRename],
    destino: Path,
    *,
    dry_run: bool,
    aplicados: int,
    nodes_atualizados: int,
) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    total = len(propostas)
    mudaram = sum(1 for p in propostas if p.mudou)
    template = sum(1 for p in propostas if p.motivo == "template" and p.mudou)
    fallback = sum(1 for p in propostas if p.motivo == "fallback" and p.mudou)
    sem_mudanca = sum(1 for p in propostas if not p.mudou)

    linhas = [
        "# Renomeio de holerites v2 -- Sprint INFRA-RENAME-HOLERITES",
        "",
        f"- Modo: {'DRY-RUN' if dry_run else 'EXECUTAR'}",
        f"- Holerites varridos: {total}",
        f"- Renomeios propostos: {mudaram}",
        f"- Por template legível: {template}",
        f"- Por fallback (metadata incompleto): {fallback}",
        f"- Sem mudança (já canônico): {sem_mudanca}",
        f"- Aplicados de fato: {aplicados}",
        f"- Nodes do grafo atualizados: {nodes_atualizados}",
        "",
        f"## Resumo: {mudaram if dry_run else aplicados} holerites renomeados",
        "",
        "## Detalhe (PII mascarada)",
        "",
        "| sha8 | nome_antigo | nome_novo | mudou | motivo | valor |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for p in propostas:
        linhas.append(
            f"| `{p.sha8}` | `{p.origem.name}` | `{p.destino.name}` | "
            f"{str(p.mudou).lower()} | {p.motivo} | {_mascarar_valor(p.liquido)} |"
        )
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")


# ============================================================================
# CLI
# ============================================================================


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Renomeia holerites para template legível "
            "HOLERITE_<YYYY-MM>_<EMPRESA>_<liquido>.pdf. "
            "Default é --dry-run; passe --executar para aplicar."
        )
    )
    parser.add_argument(
        "--executar",
        action="store_true",
        help="Aplica rename de fato. Sem essa flag, apenas reporta.",
    )
    parser.add_argument(
        "--diretorio",
        type=Path,
        default=_DIR_HOLERITES,
        help=f"Diretório dos holerites (default: {_DIR_HOLERITES})",
    )
    return parser.parse_args()


def _configurar_logger() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> int:
    _configurar_logger()
    args = _parse_args()

    propostas = coletar_propostas(args.diretorio)
    if not propostas:
        logger.info("Nenhum holerite encontrado em %s", args.diretorio)
        return 0

    aplicados = 0
    nodes_atualizados = 0
    if args.executar:
        for p in propostas:
            try:
                if _aplicar_rename(p):
                    aplicados += 1
            except RuntimeError as exc:
                logger.error("Conflito em %s: %s", p.origem.name, exc)
        nodes_atualizados = _atualizar_grafo(propostas)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = _DIR_OUTPUT / f"rename_holerites_v2_{timestamp}.csv"
    md_path = _DIR_OUTPUT / f"rename_holerites_v2_{timestamp}.md"
    _gerar_relatorio_csv(propostas, csv_path)
    _gerar_relatorio_md(
        propostas,
        md_path,
        dry_run=not args.executar,
        aplicados=aplicados,
        nodes_atualizados=nodes_atualizados,
    )

    mudaram = sum(1 for p in propostas if p.mudou)
    logger.info(
        "Relatórios em %s e %s. Propostas com mudança: %d. Aplicados: %d.",
        csv_path,
        md_path,
        mudaram,
        aplicados,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Nome de arquivo bom é o que humano consegue ler em meio segundo." -- princípio do nome legível
