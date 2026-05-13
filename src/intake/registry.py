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

# Sprint 90a: assinaturas fortes de holerite/contracheque. PDFs com qualquer uma
# destas pulam o detector bancário legado e vão direto para o classifier YAML,
# evitando falso-positivo em holerites G4F que mencionam o banco do funcionário
# (ex.: "Conta para crédito: SANTANDER ag X cc Y") e cairiam em bancario_*
# pelo file_detector que casa "SANTANDER" / "ITAÚ UNIBANCO" no texto bruto.
_ASSINATURAS_HOLERITE: tuple[str, ...] = (
    "Demonstrativo de Pagamento de Salário",
    "Demonstrativo de Pagamento de Salario",
    "G4F SOLUCOES CORPORATIVAS",
    "G4F SOLUÇÕES CORPORATIVAS",
    "INFOBASE TECNOLOGIA",
    "Recibo de Pagamento de Salário",
    "Recibo de Pagamento de Salario",
)


# MOB-bridge-4: hint mapping subtipo_mobile -> tipo canonico.
# Origem: app mobile Protocolo-Mob-Ouroboros, src/lib/share/categorias.ts,
# constante INBOX_SUBTIPOS (8 subtipos, 4 areas). Quando o app deposita o
# arquivo em inbox/<area>/<subtipo>/, o registry usa esse mapping como hint
# preferencial sobre a cascata YAML.
#
# Decisão deliberada: 'extrato' não entra no mapping -- cascata bancária
# legada (file_detector) tem 600+ linhas de heurística para Nubank/C6/Itaú/
# Santander e é mais precisa do que um hint genérico.
_MAPPING_SUBTIPO_MOBILE_TO_TIPO: dict[str, str] = {
    "pix": "comprovante_pix_foto",
    "nota": "cupom_fiscal_foto",      # refinado por MIME (PDF -> nfce_modelo_65)
    "exame": "exame_medico",           # DOC-09
    "receita": "receita_medica",       # DOC-10
    "garantia": "cupom_garantia_estendida_pdf",
    "contrato": "contrato_locacao",    # DOC-21
    "outro": "indeterminado",          # cai em _classificar/
    # 'extrato': deliberadamente não mapeado -- cascata bancária legada decide
}


# ============================================================================
# API pública
# ============================================================================


def detectar_tipo(
    caminho: Path,
    mime: str,
    preview: str | None,
    pessoa: str = "_indefinida",
    subtipo_mobile: str | None = None,
) -> Decisao:
    """Decide o tipo de UM arquivo combinando detector legado + classifier YAML.

    Devolve `Decisao` -- mesmo contrato do classifier YAML. Quando o legado
    casa, o resultado é adaptado de `DeteccaoArquivo` para `Decisao` com
    `tipo="bancario_<banco>_<tipo>"` e pasta `data/raw/<pessoa>/<banco>_<tipo>/`.

    MOB-bridge-4: quando `subtipo_mobile` está mapeado em
    `_MAPPING_SUBTIPO_MOBILE_TO_TIPO`, vira hint preferencial sobre cascata
    legada+YAML. Exceção: `subtipo_mobile='extrato'` (ou não mapeado) cai
    na cascata atual.
    """
    if subtipo_mobile and subtipo_mobile in _MAPPING_SUBTIPO_MOBILE_TO_TIPO:
        tipo_canonico = _MAPPING_SUBTIPO_MOBILE_TO_TIPO[subtipo_mobile]
        # PDF de 'nota' vira NFC-e (modelo 65); imagem vira cupom_fiscal_foto.
        if subtipo_mobile == "nota" and mime == "application/pdf":
            tipo_canonico = "nfce_modelo_65"
        return _decidir_via_hint_mobile(caminho, mime, preview, pessoa, tipo_canonico)

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
        # Sprint 90a: pre-check de holerite antes do legado. Se o preview tem
        # assinatura forte de contracheque (Demonstrativo de Pagamento, G4F,
        # INFOBASE), pula o detector bancário legado -- ele casaria por
        # menção a "ITAÚ UNIBANCO"/"SANTANDER" no rodapé de dados bancários
        # do funcionário e roteria errado. YAML decide com regra `holerite`
        # de prioridade `especifico`.
        if preview and _tem_assinatura_holerite(preview):
            logger.info(
                "PDF com assinatura de holerite detectada em preview: %s -- "
                "delegando para classifier YAML",
                caminho.name,
            )
            return classificar(caminho, mime, preview, pessoa=pessoa)
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


def _decidir_via_hint_mobile(
    caminho: Path,
    mime: str,
    preview: str | None,
    pessoa: str,
    tipo_canonico: str,
) -> Decisao:
    """MOB-bridge-4: Decisão canônica via hint do app mobile.

    Quando o tipo canônico existe no YAML, delega para o classifier (que
    resolve pasta_destino + nome_canonico via templates declarativos).
    Quando não existe (ex.: pix antes do DOC-27, exame antes do DOC-09),
    devolve `Decisao` com tipo populado mas pasta_destino=`_classificar/`,
    preservando o hint para auditoria.
    """
    del preview  # não usado por enquanto; reservado para futura extração de data
    from src.intake.classifier import _TIPOS_CACHE, recarregar_tipos

    tipos = _TIPOS_CACHE if _TIPOS_CACHE is not None else recarregar_tipos()
    tipo_yaml = next((t for t in tipos if t.get("id") == tipo_canonico), None)

    sha8 = sha8_arquivo(caminho)
    extensao = caminho.suffix.lstrip(".").lower() or "bin"
    pessoa_resolvida = pessoa or "_indefinida"

    if tipo_yaml is None:
        # Tipo canônico ainda não registrado no YAML (DOC-27, DOC-09, etc.).
        # Mantém o hint no campo `tipo` para auditoria; arquivo vai para
        # _classificar/ até o extrator/regra do tipo nascer.
        pasta = (_PATH_DATA_RAW / "_classificar").resolve()
        nome = f"_CLASSIFICAR_{tipo_canonico.upper()}_{sha8}.{extensao}"
        return Decisao(
            tipo=tipo_canonico,
            prioridade="normal",
            match_mode=None,
            extrator_modulo=None,
            origem_sprint="MOB-bridge-4",
            pasta_destino=pasta,
            nome_canonico=nome,
            data_detectada_iso=None,
            regras_avaliadas=0,
            motivo_fallback="tipo_canonico_sem_regra_yaml_ainda",
        )

    # Tipo registrado no YAML -- monta Decisao com templates declarativos.
    from src.intake.classifier import _resolver_nome, _resolver_pasta

    pasta = _resolver_pasta(tipo_yaml["pasta_destino_template"], pessoa_resolvida)
    nome = _resolver_nome(
        templates=tipo_yaml["renomear_template"],
        sha8=sha8,
        extensao=extensao,
        data_iso=None,
    )
    return Decisao(
        tipo=tipo_yaml["id"],
        prioridade=tipo_yaml.get("prioridade"),
        match_mode=None,
        extrator_modulo=tipo_yaml.get("extrator_modulo"),
        origem_sprint="MOB-bridge-4",
        pasta_destino=pasta,
        nome_canonico=nome,
        data_detectada_iso=None,
        regras_avaliadas=0,
    )


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


def _tem_assinatura_holerite(preview: str) -> bool:
    """Sprint 90a: detecta assinatura forte de holerite no preview do PDF.

    Comparação case-insensitive sobre `_ASSINATURAS_HOLERITE`. Quando casa,
    o registry pula o detector bancário legado e delega para o classifier
    YAML, que tem a regra `holerite` em prioridade `especifico`.

    Sem regex aqui de propósito -- assinaturas são literais curtas que
    não exigem flexibilidade. Para tolerância a glyph quebrado em PDF
    nativo, o classifier YAML usa `glyph_tolerant.casa_padroes`.
    """
    if not preview:
        return False
    preview_upper = preview.upper()
    return any(assinatura.upper() in preview_upper for assinatura in _ASSINATURAS_HOLERITE)


# "Dois caminhos para o mesmo destino é um caminho perdido." -- princípio da unificação
