"""Registry: porta única de detecção de tipo no intake.

Une o detector legado procedural (`src/utils/file_detector.py` -- conhece
CSV Nubank x2, XLSX extrato C6, XLS fatura Santander, PDF Itaú/Santander)
com o classifier YAML (`src/intake/classifier.py` -- conhece cupom_garantia,
NFC-e, DANFE, holerite, etc.) num único contrato `Decisao`.

Sprint 41c.

Política de despacho:

  CSV / XLS / XLSX  ->  legado SOMENTE (YAML não cobre)
  OFX               ->  detector simples no registry (legado não cobre)
  PDF               ->  tenta legado primeiro (Itaú/Santander específicos),
                        depois YAML (cupom/garantia/holerite/NFC-e). O legado
                        é PROCEDURAL (decripta com senha, lê 3 páginas) --
                        mais confiável que regex YAML para bancário.
  IMG/XML/EML/etc.  ->  YAML SOMENTE

Princípio: NÃO duplicar regra. O `file_detector.py` já tem 600+ linhas de
detecção bancária; o YAML é declarativo para tipos documentais. Cada um
fica no seu domínio; o registry orquestra.

API:

    decisao = detectar_tipo(caminho, mime, preview, pessoa="_indefinida")

Devolve sempre `Decisao` (mesmo struct do classifier). Se o legado casa,
o registry adapta `DeteccaoArquivo` (com `banco/tipo/pessoa/subtipo/periodo`)
para `Decisao` com `tipo="bancario_<banco>_<tipo>"`, pasta canônica
`data/raw/<pessoa>/<banco>_<tipo>/`, e `data_detectada_iso` derivada do
período YYYY-MM (primeiro dia do mês quando aplicável).
"""

from __future__ import annotations

import re
from pathlib import Path

from src.intake import sha8_arquivo
from src.intake.classifier import Decisao, classificar
from src.utils.file_detector import DeteccaoArquivo, detectar_arquivo
from src.utils.logger import configurar_logger

logger = configurar_logger("intake.registry")

# Caminhos canônicos
_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_PATH_DATA_RAW: Path = _RAIZ_REPO / "data" / "raw"

# Mimes que vão DIRETO pro legado (YAML não cobre)
_MIMES_LEGADO_PURO: frozenset[str] = frozenset(
    {
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
)

_MIMES_OFX: frozenset[str] = frozenset({"application/x-ofx"})

# Bancos conhecidos para detecção de OFX por nome
_BANCOS_OFX_NOME: tuple[tuple[str, str], ...] = (
    ("c6", "c6"),
    ("itau", "itau"),
    ("santander", "santander"),
    ("nubank", "nubank"),
    ("nu_", "nubank"),
)


# ============================================================================
# API pública
# ============================================================================


def detectar_tipo(
    caminho: Path,
    mime: str,
    preview: str | None,
    pessoa: str = "_indefinida",
) -> Decisao:
    """Decide o tipo de UM arquivo combinando detector legado + classifier YAML.

    Devolve `Decisao` -- mesmo contrato do classifier YAML. Quando o legado
    casa, o resultado é adaptado de `DeteccaoArquivo` para `Decisao` com
    `tipo="bancario_<banco>_<tipo>"` e pasta `data/raw/<pessoa>/<banco>_<tipo>/`.
    """
    if mime in _MIMES_LEGADO_PURO:
        deteccao = _detectar_legado_silencioso(caminho)
        if deteccao:
            return _adaptar_legado(deteccao, caminho)
        return classificar(caminho, mime, preview or "", pessoa=pessoa)

    if mime in _MIMES_OFX or caminho.suffix.lower() == ".ofx":
        decisao_ofx = _detectar_ofx(caminho, pessoa)
        if decisao_ofx:
            return decisao_ofx
        return classificar(caminho, mime, preview or "", pessoa=pessoa)

    if mime == "application/pdf":
        # Tenta legado primeiro (Itaú/Santander), depois YAML
        deteccao = _detectar_legado_silencioso(caminho)
        if deteccao:
            return _adaptar_legado(deteccao, caminho)
        return classificar(caminho, mime, preview or "", pessoa=pessoa)

    # Imagens, XML, EML, texto, etc -- YAML cobre tudo
    return classificar(caminho, mime, preview or "", pessoa=pessoa)


# ============================================================================
# Adapter: DeteccaoArquivo (legado) -> Decisao (canônico)
# ============================================================================


def _adaptar_legado(deteccao: DeteccaoArquivo, caminho: Path) -> Decisao:
    """Converte resultado do file_detector para Decisao do orquestrador.

    Tipo canônico: `bancario_<banco>_<tipo>` (ex.: bancario_nubank_cartao,
    bancario_itau_cc, bancario_santander_cartao).

    Pasta destino: `data/raw/<pessoa>/<banco>_<tipo>/` -- preserva a
    convenção legada usada pelos extratores (`itau_pdf`, `nubank_cc`, etc.).

    Nome canônico: `BANCARIO_<BANCO>_<TIPO>_<periodo>_<sha8>.<ext>` ou
    `BANCARIO_<BANCO>_<TIPO>_<sha8>.<ext>` quando sem período.
    """
    pessoa = deteccao.pessoa or "_indefinida"
    pasta_subdir = f"{deteccao.banco}_{deteccao.tipo}"
    pasta = (_PATH_DATA_RAW / pessoa / pasta_subdir).resolve()
    sha8 = sha8_arquivo(caminho)
    extensao = caminho.suffix.lstrip(".").lower() or "bin"
    base = f"BANCARIO_{deteccao.banco}_{deteccao.tipo}".upper()
    if deteccao.periodo:
        nome = f"{base}_{deteccao.periodo}_{sha8}.{extensao}"
        data_iso = _periodo_para_iso(deteccao.periodo)
    else:
        nome = f"{base}_{sha8}.{extensao}"
        data_iso = None
    return Decisao(
        tipo=f"bancario_{deteccao.banco}_{deteccao.tipo}",
        prioridade="normal",
        match_mode=None,
        extrator_modulo=_inferir_extrator_modulo(deteccao),
        origem_sprint="41c",
        pasta_destino=pasta,
        nome_canonico=nome,
        data_detectada_iso=data_iso,
        regras_avaliadas=0,
    )


def _inferir_extrator_modulo(deteccao: DeteccaoArquivo) -> str | None:
    """Mapeia (banco, tipo) -> caminho de import do extrator existente.

    Devolve None quando não há extrator (raro: tipo bancário detectado
    mas sem extrator dedicado -- registra fallback para sprint futura).
    """
    mapping: dict[tuple[str, str], str] = {
        ("nubank", "cartao"): "src.extractors.nubank_cartao",
        ("nubank", "cc"): "src.extractors.nubank_cc",
        ("c6", "cartao"): "src.extractors.c6_cartao",
        ("c6", "cc"): "src.extractors.c6_cc",
        ("itau", "cc"): "src.extractors.itau_pdf",
        ("santander", "cartao"): "src.extractors.santander_pdf",
    }
    return mapping.get((deteccao.banco, deteccao.tipo))


def _periodo_para_iso(periodo: str) -> str | None:
    """Converte 'YYYY-MM' (formato do file_detector) em 'YYYY-MM-01' ISO."""
    match = re.match(r"^(\d{4})-(\d{2})$", periodo)
    if not match:
        return None
    return f"{match.group(1)}-{match.group(2)}-01"


# ============================================================================
# Detector OFX -- legado não cobre, registro aqui
# ============================================================================


def _detectar_ofx(caminho: Path, pessoa: str) -> Decisao | None:
    """Detecta OFX por sufixo + heurística simples para banco/pessoa.

    Banco vem do nome do arquivo (substring case-insensitive). Pessoa
    prefere parâmetro explícito; fallback para pasta-pai.
    """
    if caminho.suffix.lower() != ".ofx":
        return None
    nome_lower = caminho.name.lower()
    banco = "desconhecido"
    for chave, banco_canonico in _BANCOS_OFX_NOME:
        if chave in nome_lower:
            banco = banco_canonico
            break
    pessoa_resolvida = pessoa
    if pessoa_resolvida == "_indefinida":
        pasta_pai = caminho.parent.name.lower()
        if pasta_pai in {"andre", "vitoria"}:
            pessoa_resolvida = pasta_pai
        else:
            pessoa_resolvida = "casal"
    sha8 = sha8_arquivo(caminho)
    pasta = (_PATH_DATA_RAW / pessoa_resolvida / f"{banco}_cc").resolve()
    nome = f"BANCARIO_{banco.upper()}_OFX_{sha8}.ofx"
    return Decisao(
        tipo=f"bancario_{banco}_ofx",
        prioridade="normal",
        match_mode=None,
        extrator_modulo="src.extractors.ofx_parser",
        origem_sprint="41c",
        pasta_destino=pasta,
        nome_canonico=nome,
        data_detectada_iso=None,
        regras_avaliadas=0,
    )


# ============================================================================
# Internals
# ============================================================================


def _detectar_legado_silencioso(caminho: Path) -> DeteccaoArquivo | None:
    """Chama detectar_arquivo capturando exceções (XLS sem senha levanta)."""
    try:
        return detectar_arquivo(caminho)
    except Exception as exc:  # noqa: BLE001 -- defensivo
        logger.warning("file_detector falhou em %s: %s -- delegando para YAML", caminho, exc)
        return None


# "Dois caminhos para o mesmo destino é um caminho perdido." -- princípio da unificação
