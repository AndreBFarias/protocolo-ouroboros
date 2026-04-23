"""Roteador do intake: arquiva original, move artefatos para o destino canônico,
gerencia descarte da inbox e auditoria de envelope.

Política (alinhada no chat):

- `shutil.move` SEMPRE -- nunca `Path.rename`. inbox/ e data/ podem
  estar em mounts diferentes; rename cross-device levanta OSError.
- Original da inbox é COPIADO para `data/raw/_envelopes/originais/<sha8>.<ext>`
  ANTES de qualquer processamento. Trilha de auditoria sem perda.
- Atomicidade por artefato: mkdir + move são transacionais por página/anexo
  individualmente. Falha de um artefato vai pra `_classificar/`; outros
  artefatos do mesmo envelope continuam normalmente.
- Original na inbox SÓ é descartado quando o batch (todos os artefatos
  do envelope) termina com sucesso. Em sucesso parcial, mantém na inbox
  para o supervisor reprocessar manualmente.
- Cleanup do diretório de split em `_envelopes/<tipo>/<sha8>/` segue a
  política definida em `extractors_envelope.cleanup_envelope`: remove em
  sucesso total, mantém em sucesso parcial.

Este módulo expõe primitivos de baixo nível (`arquivar_original`,
`rotear_artefato`, `descartar_da_inbox`) e um orquestrador de lote
(`rotear_lote`) que aplica os primitivos a todos os artefatos de UM
envelope. A orquestração de "varrer inbox/, decidir envelope por MIME,
expandir, classificar" é responsabilidade do `inbox_processor.py`
(sub-passo seguinte da Sprint 41).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from src.intake import sha8_arquivo
from src.intake.classifier import Decisao
from src.intake.extractors_envelope import (
    _resolver_destino_sem_colisao,
    cleanup_envelope,
)
from src.utils.logger import configurar_logger

logger = configurar_logger("intake.router")

# Caminhos canônicos
_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_ORIGINAIS_BASE: Path = _RAIZ_REPO / "data" / "raw" / "_envelopes" / "originais"


# ============================================================================
# Estruturas
# ============================================================================


@dataclass(frozen=True)
class ArtefatoArquivado:
    """Resultado de mover UM artefato (página de PDF, anexo, membro de ZIP)."""

    artefato_origem: Path  # split em _envelopes/<tipo>/<sha8>/
    decisao: Decisao  # do classifier
    caminho_final: Path  # canônico em data/raw/<pessoa>/... ou _classificar/
    sucesso: bool  # True = pasta canônica; False = _classificar/ por falha
    motivo: str | None = None  # explica fallback se sucesso=False


@dataclass(frozen=True)
class RelatorioRoteamento:
    """Resultado de rotear todos os artefatos de UM envelope (1 arquivo da inbox)."""

    arquivo_inbox: Path
    sha8_envelope: str
    copia_original: Path  # _envelopes/originais/<sha8>.<ext>
    artefatos: list[ArtefatoArquivado]
    erros: list[str]  # do envelope + warnings do roteamento

    @property
    def sucesso_total(self) -> bool:
        """True se TODOS os artefatos foram para pasta canônica E sem erros de envelope.

        Política para descarte da inbox e cleanup do diretório _envelopes/<sha8>/:
        em sucesso parcial, conserva tudo para o supervisor.
        """
        if not self.artefatos:
            return False
        if self.erros:
            return False
        return all(a.sucesso for a in self.artefatos)


# ============================================================================
# Primitivos
# ============================================================================


def arquivar_original(arquivo_inbox: Path) -> Path:
    """Copia o arquivo da inbox para `data/raw/_envelopes/originais/<sha8>.<ext>`.

    Roda ANTES de qualquer processamento -- garante trilha de auditoria
    mesmo se page-split, classificação ou move falharem catastroficamente.
    Devolve o caminho da cópia. Se já existir cópia com mesmo sha8 (mesmo
    arquivo já processado em sessão anterior), mantém a existente e devolve.

    Levanta FileNotFoundError se o arquivo da inbox não existir.
    """
    if not arquivo_inbox.exists():
        raise FileNotFoundError(f"arquivo da inbox não existe: {arquivo_inbox}")
    sha8 = sha8_arquivo(arquivo_inbox)
    extensao = arquivo_inbox.suffix.lstrip(".").lower() or "bin"
    _ORIGINAIS_BASE.mkdir(parents=True, exist_ok=True)
    destino = _ORIGINAIS_BASE / f"{sha8}.{extensao}"
    if destino.exists():
        logger.debug("original já arquivado em %s -- mantém", destino)
        return destino
    shutil.copy2(arquivo_inbox, destino)
    logger.info("original arquivado: %s -> %s", arquivo_inbox.name, destino)
    return destino


def rotear_artefato(artefato_origem: Path, decisao: Decisao) -> ArtefatoArquivado:
    """Move UM artefato para o destino canônico determinado pela `Decisao`.

    Atomicidade por artefato: se mkdir ou move falhar, joga o artefato em
    `data/raw/_classificar/` com o mesmo sha8 e marca `sucesso=False`.
    NÃO levanta -- envelope continua processando os próximos artefatos.

    Sempre usa `shutil.move` (cross-device-safe). Se o destino já existir
    (mesma pasta, mesmo nome canônico), aplica desambiguação `_1`/`_2`/...
    via `_resolver_destino_sem_colisao` (compartilhado com envelope).
    """
    if not artefato_origem.exists():
        return _fallback_classificar(
            artefato_origem,
            decisao,
            motivo=f"artefato origem inexistente: {artefato_origem}",
        )
    try:
        decisao.pasta_destino.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _fallback_classificar(
            artefato_origem,
            decisao,
            motivo=f"falha ao criar pasta destino {decisao.pasta_destino}: {exc}",
        )
    destino = _resolver_destino_sem_colisao(
        decisao.pasta_destino, decisao.nome_canonico, arquivo_origem=artefato_origem
    )
    # P2.3 2026-04-23: se destino resolvido == origem (idempotência por
    # conteúdo), pula o move -- nada a fazer.
    if destino.resolve() == artefato_origem.resolve():
        logger.info(
            "rotear_artefato idempotente (mesmo conteúdo já em %s): %s",
            destino,
            artefato_origem.name,
        )
        return ArtefatoArquivado(
            artefato_origem=artefato_origem,
            decisao=decisao,
            caminho_final=destino,
            sucesso=True,
            motivo=None,
        )
    # P2.3: se destino existe com mesmo hash mas path diferente (origem é
    # staging temporário), move sobrescrevendo (destino canônico ganha,
    # origem descartada). Evita cópias `_1.pdf`, `_2.pdf` literais.
    if destino.exists():
        try:
            destino.unlink()
        except OSError:
            pass
    try:
        shutil.move(str(artefato_origem), str(destino))
    except (OSError, shutil.Error) as exc:
        return _fallback_classificar(
            artefato_origem,
            decisao,
            motivo=f"falha ao mover {artefato_origem} -> {destino}: {exc}",
        )
    logger.info(
        "rotear_artefato OK: tipo=%s pessoa-ind, %s -> %s",
        decisao.tipo or "_classificar",
        artefato_origem.name,
        destino,
    )
    return ArtefatoArquivado(
        artefato_origem=artefato_origem,
        decisao=decisao,
        caminho_final=destino,
        sucesso=decisao.tipo is not None,
        motivo=decisao.motivo_fallback if decisao.tipo is None else None,
    )


def descartar_da_inbox(arquivo_inbox: Path, sucesso_total: bool) -> bool:
    """Remove o arquivo da inbox SÓ se o batch terminou com sucesso total.

    Em sucesso parcial, conserva para o supervisor decidir o que fazer.
    Devolve True se removeu, False se manteve.
    """
    if not sucesso_total:
        logger.info("inbox preservada (sucesso parcial): %s -- supervisor revisa", arquivo_inbox)
        return False
    if not arquivo_inbox.exists():
        return False
    try:
        arquivo_inbox.unlink()
        logger.info("inbox descartada (sucesso total): %s", arquivo_inbox)
        return True
    except OSError as exc:
        logger.warning("falha ao remover %s da inbox: %s", arquivo_inbox, exc)
        return False


# ============================================================================
# Orquestrador de lote (1 envelope -> N artefatos)
# ============================================================================


def rotear_lote(
    arquivo_inbox: Path,
    sha8_envelope: str,
    diretorio_envelope: Path,
    pares_artefato_decisao: list[tuple[Path, Decisao]],
    erros_envelope: list[str] | None = None,
) -> RelatorioRoteamento:
    """Aplica `rotear_artefato` a cada par (artefato, decisao), faz cleanup do
    envelope conforme sucesso, e devolve relatório consolidado.

    NÃO chama o classifier nem o envelope -- recebe os pares já decididos.
    NÃO descarta o arquivo da inbox -- isso é uma chamada separada
    (`descartar_da_inbox`) para que o caller decida o momento (ex.: depois
    de gravar o relatório no grafo).

    `arquivo_inbox` precisa ter sido passado por `arquivar_original` antes;
    aqui, só usamos para registrar no relatório. `sha8_envelope` é o que
    o envelope devolveu (espelha o sha8 da cópia em `_envelopes/originais/`).
    """
    erros_iniciais = list(erros_envelope or [])
    copia_original = _ORIGINAIS_BASE / f"{sha8_envelope}{arquivo_inbox.suffix.lower()}"
    if not copia_original.exists():
        # Calcula a extensão de novo caso o caller não tenha passado o arquivo certo
        copia_original = _ORIGINAIS_BASE / sha8_envelope

    artefatos_arquivados: list[ArtefatoArquivado] = []
    for artefato_origem, decisao in pares_artefato_decisao:
        resultado = rotear_artefato(artefato_origem, decisao)
        artefatos_arquivados.append(resultado)

    relatorio = RelatorioRoteamento(
        arquivo_inbox=arquivo_inbox,
        sha8_envelope=sha8_envelope,
        copia_original=copia_original,
        artefatos=artefatos_arquivados,
        erros=erros_iniciais,
    )

    cleanup_envelope(diretorio_envelope, sucesso_total=relatorio.sucesso_total)
    logger.info(
        "rotear_lote: arquivo=%s, %d artefatos (%d ok, %d _classificar/), "
        "sucesso_total=%s, erros_envelope=%d",
        arquivo_inbox.name,
        len(artefatos_arquivados),
        sum(1 for a in artefatos_arquivados if a.sucesso),
        sum(1 for a in artefatos_arquivados if not a.sucesso),
        relatorio.sucesso_total,
        len(relatorio.erros),
    )
    return relatorio


# ============================================================================
# Internals
# ============================================================================


def _fallback_classificar(
    artefato_origem: Path, decisao: Decisao, motivo: str
) -> ArtefatoArquivado:
    """Joga o artefato no `_classificar/` com o sha8 do split e marca falha.

    Não levanta. Se até o fallback falhar (caso patológico), registra warning
    e devolve `ArtefatoArquivado` apontando para a origem (artefato perdura
    no _envelopes/, evidência preservada).
    """
    pasta_fallback = _RAIZ_REPO / "data" / "raw" / "_classificar"
    try:
        pasta_fallback.mkdir(parents=True, exist_ok=True)
        nome = artefato_origem.name
        destino = _resolver_destino_sem_colisao(pasta_fallback, nome)
        if artefato_origem.exists():
            shutil.move(str(artefato_origem), str(destino))
        else:
            destino = artefato_origem  # mantém referência simbólica à origem
        logger.warning("rotear_artefato fallback _classificar/: %s -- %s", destino, motivo)
        return ArtefatoArquivado(
            artefato_origem=artefato_origem,
            decisao=decisao,
            caminho_final=destino,
            sucesso=False,
            motivo=motivo,
        )
    except OSError as exc:
        logger.error(
            "fallback _classificar/ FALHOU para %s: %s -- artefato fica em %s",
            artefato_origem,
            exc,
            artefato_origem.parent,
        )
        return ArtefatoArquivado(
            artefato_origem=artefato_origem,
            decisao=decisao,
            caminho_final=artefato_origem,
            sucesso=False,
            motivo=f"{motivo}; fallback também falhou: {exc}",
        )


# "Cada coisa em seu lugar e um lugar para cada coisa." -- Benjamin Franklin
