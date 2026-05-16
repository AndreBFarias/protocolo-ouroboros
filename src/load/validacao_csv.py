"""CSV de validação por arquivo (ETL × Opus × Humano).

Sprint VALIDAÇÃO-CSV-01.

Materializa pedido literal do dono em 2026-04-29: "vamos marcando num csv da
vida pra verificar se o pdf, xsx, csx, imagem e os valores extraidos estão
certos. Aí isso resolve pra gente".

Complementa (não substitui) o Revisor 4-way em
``src/dashboard/paginas/revisor.py`` (Sprint D2). O Revisor valida
**transações** individuais; este CSV valida **arquivos** e seus campos.
Os dois coexistem por design.

Schema canônico do CSV ``data/output/validacao_arquivos.csv``:

    sha8_arquivo, tipo_arquivo, caminho_relativo, ts_processado,
    campo, valor_etl, valor_opus, valor_humano,
    status_etl, status_opus, status_humano,
    observacoes_humano

Status válidos: ``ok`` | ``erro`` | ``lacuna`` | ``pendente``.

Idempotência: chave de deduplicação é ``(sha8_arquivo, campo)``. Re-rodar
``registrar_extracao()`` com o mesmo par atualiza ``valor_etl`` mas
**preserva** ``valor_opus``, ``valor_humano`` e ``observacoes_humano``
(o trabalho humano nunca é sobrescrito por reextração).

Concorrência: escrita usa pattern "read full → mutate → write tmp → rename
atômico" (``Path.replace``) para evitar corrupção em múltiplas execuções
simultâneas. Não usa lockfile (excessivo para escrita atômica).
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.utils.logger import configurar_logger

logger = configurar_logger(__name__)

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_PATH_CSV_PADRAO: Path = _RAIZ_REPO / "data" / "output" / "validacao_arquivos.csv"

CABECALHO: list[str] = [
    "sha8_arquivo",
    "tipo_arquivo",
    "caminho_relativo",
    "ts_processado",
    "campo",
    "valor_etl",
    "valor_opus",
    # Sprint UX-RD-11: confianca_opus (float 0..1) registra o quanto a
    # extração agentic Opus está segura. Default 0.0; preenchido pela skill
    # /validar-arquivo. Inserido aqui após `valor_opus` para preservar a
    # ordem semântica "valor + confiança" antes do `valor_humano`.
    "confianca_opus",
    "valor_humano",
    "status_etl",
    "status_opus",
    "status_humano",
    "observacoes_humano",
]

STATUS_VALIDOS: frozenset[str] = frozenset({"ok", "erro", "lacuna", "pendente"})


@dataclass
class LinhaValidacao:
    """Representa uma linha do CSV de validação.

    Campos opcionais usam string vazia como sentinela (CSV friendly).
    ``status_*`` default ``pendente`` força chamador a marcar explicitamente.
    """

    sha8_arquivo: str
    tipo_arquivo: str
    caminho_relativo: str
    campo: str
    valor_etl: str = ""
    ts_processado: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    valor_opus: str = ""
    # Sprint UX-RD-11: confiança 0..1 da extração agentic Opus
    confianca_opus: str = "0.0"
    valor_humano: str = ""
    status_etl: str = "pendente"
    status_opus: str = "pendente"
    status_humano: str = "pendente"
    observacoes_humano: str = ""

    def chave(self) -> tuple[str, str]:
        """Chave de deduplicação canônica."""
        return (self.sha8_arquivo, self.campo)

    def to_row(self) -> dict[str, str]:
        return {nome: getattr(self, nome) for nome in CABECALHO}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def calcular_sha8(caminho: Path) -> str:
    """Devolve os 8 primeiros caracteres do SHA-256 do arquivo."""
    if not caminho.exists() or not caminho.is_file():
        return ""
    h = hashlib.sha256()
    with caminho.open("rb") as fh:
        for bloco in iter(lambda: fh.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()[:8]


def caminho_relativo_seguro(caminho: Path, raiz: Path = _RAIZ_REPO) -> str:
    """Devolve caminho relativo à raiz; cai em absoluto se fora do repo."""
    try:
        return str(caminho.resolve().relative_to(raiz))
    except ValueError:
        return str(caminho.resolve())


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------


def ler_csv(caminho_csv: Path | None = None) -> list[LinhaValidacao]:
    """Lê o CSV inteiro como lista de ``LinhaValidacao``.

    Tolera arquivo ausente (devolve lista vazia). Cabeçalhos extras no CSV
    são ignorados; cabeçalhos faltantes ficam com string vazia.
    """
    caminho_csv = caminho_csv or _PATH_CSV_PADRAO
    if not caminho_csv.exists():
        return []
    linhas: list[LinhaValidacao] = []
    with caminho_csv.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            kwargs = {nome: (row.get(nome) or "") for nome in CABECALHO}
            # Sprint UX-RD-11: confianca_opus default 0.0 quando ausente em
            # CSV antigo (pré-migração) ou quando humano deixou em branco.
            if not kwargs.get("confianca_opus"):
                kwargs["confianca_opus"] = "0.0"
            try:
                linhas.append(LinhaValidacao(**kwargs))
            except TypeError as erro:
                logger.warning("linha invalida no CSV ignorada (%s): %s", caminho_csv.name, erro)
    return linhas


def filtrar_pendentes_opus(
    linhas: list[LinhaValidacao] | None = None,
    caminho_csv: Path | None = None,
) -> list[LinhaValidacao]:
    """Filtra linhas com ``status_opus=pendente`` -- alvo do batch Opus."""
    if linhas is None:
        linhas = ler_csv(caminho_csv)
    return [linha for linha in linhas if linha.status_opus == "pendente"]


def filtrar_pendentes_humano(
    linhas: list[LinhaValidacao] | None = None,
    caminho_csv: Path | None = None,
) -> list[LinhaValidacao]:
    """Filtra linhas com ``status_humano=pendente`` -- alvo do dashboard."""
    if linhas is None:
        linhas = ler_csv(caminho_csv)
    return [linha for linha in linhas if linha.status_humano == "pendente"]


# ---------------------------------------------------------------------------
# Escrita atômica
# ---------------------------------------------------------------------------


def _escrever_tmp_e_renomear(linhas: list[LinhaValidacao], caminho_csv: Path) -> None:
    """Escreve em arquivo temporário no mesmo diretório e renomeia atomicamente."""
    caminho_csv.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho_csv.with_suffix(caminho_csv.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CABECALHO)
        writer.writeheader()
        for linha in linhas:
            writer.writerow(linha.to_row())
    tmp.replace(caminho_csv)


def gravar_csv(linhas: list[LinhaValidacao], caminho_csv: Path | None = None) -> Path:
    """Reescreve o CSV inteiro a partir da lista. Atômico via tmp + rename."""
    caminho_csv = caminho_csv or _PATH_CSV_PADRAO
    _escrever_tmp_e_renomear(linhas, caminho_csv)
    return caminho_csv


def _mesclar_preservando_humano(existente: LinhaValidacao, nova: LinhaValidacao) -> LinhaValidacao:
    """Mescla linha nova sobre existente, preservando valor/status/obs humanos.

    Atualiza ``valor_etl`` e ``status_etl`` se a nova traz valores. Atualiza
    ``ts_processado``. Mantém intactos os campos de Opus e humano.
    """
    return LinhaValidacao(
        sha8_arquivo=existente.sha8_arquivo,
        tipo_arquivo=existente.tipo_arquivo or nova.tipo_arquivo,
        caminho_relativo=existente.caminho_relativo or nova.caminho_relativo,
        ts_processado=nova.ts_processado or existente.ts_processado,
        campo=existente.campo,
        valor_etl=nova.valor_etl or existente.valor_etl,
        valor_opus=existente.valor_opus,
        confianca_opus=existente.confianca_opus,
        valor_humano=existente.valor_humano,
        status_etl=nova.status_etl or existente.status_etl,
        status_opus=existente.status_opus,
        status_humano=existente.status_humano,
        observacoes_humano=existente.observacoes_humano,
    )


def upsert_linhas(novas: list[LinhaValidacao], caminho_csv: Path | None = None) -> Path:
    """Insere ou atualiza linhas via chave (sha8, campo). Preserva trabalho humano.

    Retorna o caminho do CSV escrito.
    """
    caminho_csv = caminho_csv or _PATH_CSV_PADRAO
    existentes = ler_csv(caminho_csv)
    indice = {linha.chave(): linha for linha in existentes}
    for nova in novas:
        chave = nova.chave()
        if chave in indice:
            indice[chave] = _mesclar_preservando_humano(indice[chave], nova)
        else:
            indice[chave] = nova
    todas = sorted(indice.values(), key=lambda linha: (linha.sha8_arquivo, linha.campo))
    _escrever_tmp_e_renomear(todas, caminho_csv)
    return caminho_csv


# ---------------------------------------------------------------------------
# API pública para extratores
# ---------------------------------------------------------------------------


def registrar_extracao(
    arquivo: Path,
    tipo_arquivo: str,
    campos: dict[str, object],
    caminho_csv: Path | None = None,
) -> Path:
    """Registra todos os campos extraídos de um arquivo no CSV.

    Cada item de ``campos`` (chave=nome canônico, valor=valor extraído) gera
    1 linha no CSV. Se a linha já existe (mesmo sha8 + campo), atualiza
    apenas ``valor_etl`` + ``ts_processado`` -- nunca toca valor_opus,
    valor_humano, observacoes_humano.

    Retorna o caminho do CSV escrito.
    """
    sha8 = calcular_sha8(arquivo)
    if not sha8:
        logger.warning("registrar_extracao: arquivo inacessivel %s", arquivo)
        return caminho_csv or _PATH_CSV_PADRAO
    caminho_rel = caminho_relativo_seguro(arquivo)
    novas: list[LinhaValidacao] = []
    for campo, valor in campos.items():
        novas.append(
            LinhaValidacao(
                sha8_arquivo=sha8,
                tipo_arquivo=tipo_arquivo,
                caminho_relativo=caminho_rel,
                campo=campo,
                valor_etl=str(valor) if valor is not None else "",
                status_etl="ok" if valor not in (None, "") else "lacuna",
            )
        )
    return upsert_linhas(novas, caminho_csv)


def atualizar_validacao_opus(
    sha8: str,
    campo: str,
    valor_opus: str,
    status_opus: str = "ok",
    caminho_csv: Path | None = None,
    *,
    confianca_opus: float | str | None = None,
) -> bool:
    """Atualiza valor_opus + status_opus + (opcional) confianca_opus.

    Sprint UX-RD-11: parâmetro ``confianca_opus`` opcional **keyword-only**
    (preserva assinatura posicional histórica: ``(sha8, campo, valor_opus,
    status_opus, caminho_csv)``). Se omitido, preserva valor anterior.
    Retorna ``True`` se a linha foi encontrada.
    """
    if status_opus not in STATUS_VALIDOS:
        raise ValueError(f"status_opus inválido: {status_opus}")
    caminho_csv = caminho_csv or _PATH_CSV_PADRAO
    linhas = ler_csv(caminho_csv)
    for linha in linhas:
        if linha.sha8_arquivo == sha8 and linha.campo == campo:
            linha.valor_opus = valor_opus
            linha.status_opus = status_opus
            if confianca_opus is not None:
                linha.confianca_opus = str(confianca_opus)
            gravar_csv(linhas, caminho_csv)
            return True
    return False


def atualizar_validacao_humana(
    sha8: str,
    campo: str,
    valor_humano: str,
    status_humano: str = "ok",
    observacoes: str = "",
    caminho_csv: Path | None = None,
) -> bool:
    """Atualiza valor_humano + status_humano + observacoes_humano de uma linha.

    Retorna ``True`` se a linha foi encontrada. Não cria linha nova.
    """
    if status_humano not in STATUS_VALIDOS:
        raise ValueError(f"status_humano inválido: {status_humano}")
    caminho_csv = caminho_csv or _PATH_CSV_PADRAO
    linhas = ler_csv(caminho_csv)
    for linha in linhas:
        if linha.sha8_arquivo == sha8 and linha.campo == campo:
            linha.valor_humano = valor_humano
            linha.status_humano = status_humano
            linha.observacoes_humano = observacoes
            gravar_csv(linhas, caminho_csv)
            return True
    return False


# "Cada valor anotado, cada arquivo lido. Validar é confessar com método."
#  -- princípio operacional do Protocolo Ouroboros
