"""Extrator de DANFE NFe modelo 55 (PDF A4 formal) -- Sprint 44.

DANFE (Documento Auxiliar da Nota Fiscal Eletrônica) é a representação
impressa da NFe modelo 55. Difere da NFC-e modelo 65 (Sprint 44b) em:

- Layout A4 (não mini-cupom 80mm).
- Sempre tem bloco DESTINATÁRIO / REMETENTE.
- Chave 44 dígitos sempre com modelo 55 nos dígitos 21-22.
- Tabela de itens mais detalhada: NCM, CFOP, ICMS, IPI por linha.

Este extrator assume PDF NATIVO (texto extraível via pdfplumber). DANFEs
escaneadas ficam para OCR dedicado (fora do escopo da Sprint 44).

Campos canônicos extraídos:

    chave_44           -- 44 dígitos com DV válido, modelo 55
    numero, serie      -- identificadores SEFAZ  # noqa: accent
    data_emissao       -- YYYY-MM-DD
    cnpj_emitente      -- canônico XX.XXX.XXX/XXXX-XX
    razao_social       -- razão social do emissor
    endereco           -- endereço da loja/prestador
    total              -- R$ (VALOR TOTAL DA NOTA)
    cfop_nota          -- CFOP do cabeçalho (5102, 5933, etc.)
    cpf_cnpj_destinatario -- opcional, do bloco DESTINATÁRIO
    cancelada          -- bool; True se rodapé indica NFe CANCELADA
    itens              -- list[dict] com codigo, descricao, ncm, cfop,  # noqa: accent
                          unidade, qtde, valor_unit, valor_total,
                          icms_valor, ipi_valor

Efeitos colaterais: `extrair()` ingere cada DANFE no grafo via
`src/graph/ingestor_documento.py:ingerir_documento_fiscal` -- cria nó
`documento` + 1 nó `fornecedor` + N nós `item` + arestas
`fornecido_por`/`contem_item`/`ocorre_em`. Retorna lista VAZIA de
`base.Transacao` -- o total já aparece no extrato bancário.

Armadilhas Sprint 44 (ver docs/sprints/producao/sprint_44_extrator_danfe_pdf.md):

    A44-1: extract_tables() falha em tabela sem bordas -> fallback regex.
    A44-2: chave 44 pode quebrar em múltiplas linhas -> normalizar antes.
    A44-3: CFOP 5XXX = saída (este extrator assume saída).
    A44-4: DANFE multipágina -> iterar pdf.pages e concatenar.
    A44-5: valores em R$ com ponto de milhar -> `_parse_valor_br`.
    A44-6: NFe CANCELADA mantém DANFE -> flag `cancelada`, não linkar.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.extractors.base import ExtratorBase, Transacao
from src.graph.db import GrafoDB, caminho_padrao
from src.graph.ingestor_documento import ingerir_documento_fiscal
from src.transform.irpf_tagger import _REGEX_CNPJ
from src.utils.chave_nfe import (
    extrair_cnpj_emitente as cnpj_da_chave,
    extrair_modelo,
    valida_digito_verificador,
)
from src.utils.chave_nfe import (
    normalizar as normalizar_chave,
)
from src.utils.logger import configurar_logger

logger = configurar_logger("danfe_pdf")

EXTENSOES_ACEITAS: tuple[str, ...] = (".pdf",)


# ============================================================================
# Padrões de detecção
# ============================================================================


RE_MARCA_DANFE_TITULO = re.compile(r"\bDANFE\b", re.IGNORECASE | re.UNICODE)
RE_MARCA_DANFE_SUBTITULO = re.compile(
    r"Documento\s+Auxiliar\s+da\s+Nota\s+Fiscal\s+Eletr[ôo]nica",
    re.IGNORECASE | re.UNICODE,
)
RE_MARCA_DESTINATARIO = re.compile(
    r"DESTINAT[ÁA]RIO\s*[/\\]\s*REMETENTE", re.IGNORECASE | re.UNICODE
)
RE_MARCA_CANCELADA = re.compile(
    r"NFe\s+CANCELAD[AO]|NOTA\s+FISCAL\s+CANCELAD[AO]",
    re.IGNORECASE | re.UNICODE,
)


# ============================================================================
# Padrões de cabeçalho
# ============================================================================


# Chave 44 formatada: 11 grupos de 4 dígitos com espaços opcionais
RE_CHAVE_44_DIGITOS = re.compile(
    r"((?:\d{4}\s*){10}\d{4})", re.MULTILINE
)
RE_NUMERO_NOTA = re.compile(
    r"N[ºo°]\s*0*(\d{1,9})", re.IGNORECASE | re.UNICODE
)
RE_SERIE_NOTA = re.compile(
    r"S[ÉE]RIE\s*0*(\d{1,3})", re.IGNORECASE | re.UNICODE
)
RE_DATA_EMISSAO = re.compile(
    r"DATA\s+DE\s+EMISS[ÃA]O\s*:?\s*(\d{2}/\d{2}/\d{4})",
    re.IGNORECASE | re.UNICODE,
)
RE_DATA_DDMMYYYY_GENERICA = re.compile(r"(\d{2}/\d{2}/\d{4})")
RE_CFOP_CABECALHO = re.compile(
    r"CFOP\s*:?\s*(\d{4})", re.IGNORECASE | re.UNICODE
)
RE_TOTAL_NOTA = re.compile(
    r"VALOR\s+TOTAL\s+DA\s+NOTA\s*:?\s*R?\$?\s*([\d.,]+)",
    re.IGNORECASE | re.UNICODE,
)

# Emitente: primeira linha que começa com "Emitente:" ou a primeira linha com
# CNPJ na faixa superior do documento (acima do bloco destinatário).
RE_EMITENTE_ROTULO = re.compile(
    r"Emitente\s*:?\s*([^\n]+)", re.IGNORECASE | re.UNICODE
)
RE_ENDERECO_ROTULO = re.compile(
    r"Endere[çc]o\s*:?\s*([^\n]+)", re.IGNORECASE | re.UNICODE
)


# ============================================================================
# Padrões de item (tabela de produtos)
# ============================================================================


# Linha de item típica em DANFE canônico contém colunas nesta ordem:
# código, descrição, NCM (8 dígitos), CFOP (4 dígitos), unidade, quantidade,
# valor unitário, valor total, base ICMS, valor ICMS, valor IPI, alíquotas.
#
# A descrição pode ter espaços internos; capturamos de forma greedy até
# a primeira ocorrência de NCM (8 dígitos) seguido de CFOP (4 dígitos).
RE_LINHA_ITEM_DANFE = re.compile(
    r"^\s*(?P<codigo>[A-Za-z0-9\-\.]{3,20})\s+"
    r"(?P<descricao>.+?)\s+"
    r"(?P<ncm>\d{8})\s+"
    r"(?P<cfop>\d{4})\s+"
    r"(?P<unidade>[A-Za-z]{1,5})\s+"
    r"(?P<qtde>\d+(?:[.,]\d+)?)\s+"
    r"(?P<valor_unit>[\d.]+,\d{2,3})\s+"
    r"(?P<valor_total>[\d.]+,\d{2,3})"
    r"(?:\s+(?P<base_icms>[\d.]+,\d{2}))?"
    r"(?:\s+(?P<icms_valor>[\d.]+,\d{2}))?"
    r"(?:\s+(?P<ipi_valor>[\d.]+,\d{2}))?"
    r"(?:\s+(?P<aliq_icms>[\d.]+,\d{2}))?"
    r"(?:\s+(?P<aliq_ipi>[\d.]+,\d{2}))?"
    r"\s*$",
    re.MULTILINE | re.UNICODE,
)

# Cabeçalho da tabela de itens: usado para delimitar início da região
RE_INICIO_TABELA_ITENS = re.compile(
    r"C[ÓO]DIGO\s+DESCRI[ÇC][ÃA]O[^\n]*NCM[^\n]*CFOP",
    re.IGNORECASE | re.UNICODE,
)
RE_FIM_TABELA_ITENS = re.compile(
    r"C[ÁA]LCULO\s+DO\s+IMPOSTO|VALOR\s+TOTAL\s+DOS\s+PRODUTOS|"
    r"DADOS\s+ADICIONAIS",
    re.IGNORECASE | re.UNICODE,
)


# ============================================================================
# ExtratorDanfePDF
# ============================================================================


class ExtratorDanfePDF(ExtratorBase):
    """Extrai DANFE NFe modelo 55 em PDF nativo e popula o grafo.

    `pode_processar` aceita `.pdf` em pastas `*/nfs_fiscais/*` (exceto
    `nfce/`, que é da Sprint 44b) ou arquivo com cabeçalho `DANFE` +
    bloco `DESTINATÁRIO / REMETENTE`.

    `extrair` devolve `[]` de `base.Transacao` (total já está no extrato
    bancário). Efeito colateral: nó `documento` + fornecedor + N itens +
    arestas no grafo.
    """

    BANCO_ORIGEM: str = "DANFE NFe55"

    def __init__(self, caminho: Path, grafo: GrafoDB | None = None) -> None:
        super().__init__(caminho)
        self._grafo = grafo

    # --------------------------------------------------------------------
    # Contrato ExtratorBase
    # --------------------------------------------------------------------

    def pode_processar(self, caminho: Path) -> bool:
        if caminho.suffix.lower() not in EXTENSOES_ACEITAS:
            return False
        caminho_lower = str(caminho).lower()
        # Pastas dedicadas: aceita se não for subpasta `nfce` (Sprint 44b)
        if "nfs_fiscais" in caminho_lower and "nfce" not in caminho_lower:
            return True
        if "danfe" in caminho_lower:
            return True
        try:
            texto = self._extrair_texto_total(caminho)
        except Exception as erro:
            self.logger.debug("pode_processar: falha ao ler %s: %s", caminho, erro)
            return False
        return e_danfe(texto)

    def extrair(self) -> list[Transacao]:
        """Extrai DANFEs do arquivo e ingere no grafo. Retorna [] de Transacao."""
        danfes = self.extrair_danfes(self.caminho)
        if not danfes:
            return []
        grafo = self._grafo or GrafoDB(caminho_padrao())
        criou_grafo_localmente = self._grafo is None
        try:
            grafo.criar_schema()
            for doc, itens in danfes:
                if doc.get("cancelada"):
                    self.logger.warning(
                        "DANFE CANCELADA em %s (chave %s) -- não ingerida no grafo",
                        self.caminho.name,
                        doc.get("chave_44"),
                    )
                    continue
                try:
                    ingerir_documento_fiscal(
                        grafo, doc, itens, caminho_arquivo=self.caminho
                    )
                except ValueError as erro:
                    self.logger.warning(
                        "DANFE inválida em %s: %s", self.caminho.name, erro
                    )
        finally:
            if criou_grafo_localmente:
                grafo.fechar()
        self.logger.info(
            "%d DANFE(s) ingerida(s) a partir de %s", len(danfes), self.caminho.name
        )
        return []

    # --------------------------------------------------------------------
    # API pública usável por testes
    # --------------------------------------------------------------------

    def extrair_danfes(
        self,
        caminho: Path,
        texto_override: str | None = None,
    ) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
        """Extrai todas as DANFEs do arquivo. Devolve lista de (documento, itens).

        Quando `texto_override` é dado, lê o texto direto em vez de abrir o
        arquivo via pdfplumber -- ponto de injeção para testes com fixtures
        `.txt` que reproduzem o output do pdfplumber sem depender de binários.

        Fallback seguro: layout desconhecido (cabeçalho válido mas tabela
        ilegível) devolve documento com `itens=[]` e flag de warning,
        respeitando critério "layout desconhecido não crasha".
        """
        if texto_override is not None:
            texto_total = texto_override
        else:
            paginas = self._ler_paginas(caminho)
            texto_total = "\n".join(paginas)

        if not e_danfe(texto_total):
            return []

        documento = _parse_cabecalho_danfe(texto_total)
        if documento is None:
            return []

        itens = _parse_itens_danfe(texto_total)
        documento["qtde_itens"] = len(itens)
        if not itens:
            logger.warning(
                "DANFE %s: nenhum item extraído -- layout desconhecido, fallback supervisor",
                documento.get("chave_44"),
            )
        return [(documento, itens)]

    # --------------------------------------------------------------------
    # Internals
    # --------------------------------------------------------------------

    def _ler_paginas(self, caminho: Path) -> list[str]:
        return _ler_paginas_pdf(caminho)

    def _extrair_texto_total(self, caminho: Path) -> str:
        return "\n".join(self._ler_paginas(caminho))


# ============================================================================
# Detector + parser (funções puras, testáveis isoladamente)
# ============================================================================


def e_danfe(texto: str) -> bool:
    """True se o texto é DANFE modelo 55.

    Critérios:
      - Marcador 'DANFE' no topo.
      - Marcador 'Documento Auxiliar da Nota Fiscal Eletrônica' ou
        bloco 'DESTINATÁRIO / REMETENTE'.
      - Chave 44 com modelo 55 (se presente).
    """
    tem_danfe = bool(RE_MARCA_DANFE_TITULO.search(texto))
    tem_subtitulo = bool(RE_MARCA_DANFE_SUBTITULO.search(texto))
    tem_destinatario = bool(RE_MARCA_DESTINATARIO.search(texto))
    if not tem_danfe:
        return False
    if not (tem_subtitulo or tem_destinatario):
        return False
    chave = _extrair_chave_44(texto)
    if chave and extrair_modelo(chave) != "55":
        return False
    return True


def _extrair_chave_44(texto: str) -> str | None:
    """Extrai primeira chave 44 com DV válido. Tolera espaços/quebras internas."""
    texto_normalizado = re.sub(r"[\s\n]+", " ", texto)
    for match in RE_CHAVE_44_DIGITOS.finditer(texto_normalizado):
        chave = normalizar_chave(match.group(1))
        if chave and valida_digito_verificador(chave):
            return chave
    return None


def _parse_cabecalho_danfe(texto: str) -> dict[str, Any] | None:
    """Parse de campos fiscais. Devolve None se chave 44 faltar ou for inválida."""
    chave = _extrair_chave_44(texto)
    if not chave:
        return None
    if extrair_modelo(chave) != "55":
        return None

    cnpj_emitente, razao_social = _extrair_cnpj_razao_emitente(texto)
    if not cnpj_emitente:
        return None

    cnpj_chave = cnpj_da_chave(chave)
    if cnpj_chave and cnpj_chave != cnpj_emitente:
        logger.warning(
            "CNPJ divergente em DANFE %s: texto=%s, chave=%s -- usando texto",
            chave, cnpj_emitente, cnpj_chave,
        )

    numero = _match_grupo(RE_NUMERO_NOTA, texto)
    serie = _match_grupo(RE_SERIE_NOTA, texto)
    data_emissao = _extrair_data_emissao(texto)
    total = _parse_valor_br(_match_grupo(RE_TOTAL_NOTA, texto))
    cfop = _match_grupo(RE_CFOP_CABECALHO, texto)
    endereco = _extrair_endereco(texto)
    cancelada = bool(RE_MARCA_CANCELADA.search(texto))
    cpf_cnpj_destinatario = _extrair_destinatario(texto)

    return {
        "chave_44": chave,
        "tipo_documento": "nfe_modelo_55",
        "cnpj_emitente": cnpj_emitente,
        "razao_social": razao_social,
        "endereco": endereco,
        "numero": numero,
        "serie": serie,
        "data_emissao": data_emissao,
        "total": total,
        "cfop_nota": cfop,
        "cpf_cnpj_destinatario": cpf_cnpj_destinatario,
        "cancelada": cancelada,
    }


def _parse_itens_danfe(texto: str) -> list[dict[str, Any]]:
    """Extrai itens da tabela de produtos da DANFE.

    Estratégia:
      1. Delimita a região entre o cabeçalho de colunas ('CÓDIGO DESCRIÇÃO NCM')
         e o bloco de cálculo do imposto.
      2. Aplica regex linha-a-linha (fallback quando `extract_tables` do
         pdfplumber falha em tabelas sem bordas -- Armadilha A44-1).
      3. Linhas órfãs (continuação de descrição) são anexadas ao item anterior.
    """
    regiao = _delimitar_regiao_itens(texto)
    if not regiao:
        return []

    itens: list[dict[str, Any]] = []
    for linha in regiao.split("\n"):
        linha_stripada = linha.strip()
        if not linha_stripada:
            continue
        match = RE_LINHA_ITEM_DANFE.match(linha_stripada)
        if match:
            itens.append(_item_de_match(match))
            continue
        # Linha que não casou como item: tenta anexar como continuação de
        # descrição do item anterior, desde que não seja cabeçalho/ruído.
        if itens and not _e_cabecalho_ou_ruido(linha_stripada):
            itens[-1]["descricao"] = _limpar_espacos(
                f"{itens[-1]['descricao']} {linha_stripada}"
            )
    return itens


def _delimitar_regiao_itens(texto: str) -> str:
    """Devolve o trecho de texto entre cabeçalho de itens e cálculo do imposto."""
    inicio_match = RE_INICIO_TABELA_ITENS.search(texto)
    if not inicio_match:
        return ""
    inicio = inicio_match.end()
    fim_match = RE_FIM_TABELA_ITENS.search(texto, inicio)
    fim = fim_match.start() if fim_match else len(texto)
    return texto[inicio:fim]


def _item_de_match(match: re.Match[str]) -> dict[str, Any]:
    grupos = match.groupdict()
    return {
        "codigo": grupos["codigo"],
        "descricao": _limpar_espacos(grupos["descricao"]),
        "ncm": grupos["ncm"],
        "cfop": grupos["cfop"],
        "unidade": grupos["unidade"].upper(),
        "qtde": _parse_valor_br(grupos["qtde"]),
        "valor_unit": _parse_valor_br(grupos["valor_unit"]),
        "valor_total": _parse_valor_br(grupos["valor_total"]),
        "icms_valor": _parse_valor_br(grupos.get("icms_valor")),
        "ipi_valor": _parse_valor_br(grupos.get("ipi_valor")),
    }


def _e_cabecalho_ou_ruido(linha: str) -> bool:
    """True se a linha é cabeçalho, separador ou ruído."""
    if re.match(r"^[\s\-=_|]{3,}$", linha):
        return True
    cabecalho = (
        r"^(C[ÓO]DIGO|DESCRI|NCM|CFOP|UN|QTD|V\.|B\.|BASE|VALOR|AL[ÍI]Q|"
        r"CÁLCULO|CALCULO|DADOS|INFORMA|PROTOCOLO|NATUREZA|DESTINAT|"
        r"FOLHA|N[ºo]|S[ÉE]RIE|HORA|CEP|MUNIC[ÍI]|NOME|EMITENTE|ENDERE|"
        r"CHAVE|BRASILIA|TAGUATINGA|GAMA|SAO\s+PAULO|\d+\s*-\s*(ENTRADA|SA[ÍI]DA))\b"
    )
    if re.match(cabecalho, linha, re.IGNORECASE | re.UNICODE):
        return True
    return False


# ============================================================================
# Helpers de extração dos campos de cabeçalho
# ============================================================================


def _extrair_cnpj_razao_emitente(texto: str) -> tuple[str | None, str | None]:
    """Detecta emitente: rótulo 'Emitente:' ou primeira linha com CNPJ antes do
    bloco DESTINATÁRIO."""
    razao: str | None = None
    rotulo_match = RE_EMITENTE_ROTULO.search(texto)
    if rotulo_match:
        razao_bruta = rotulo_match.group(1).strip()
        razao = _limpar_razao_emitente(razao_bruta)

    # Limitamos a busca ao topo do documento (até o bloco DESTINATÁRIO).
    pos_destinatario = RE_MARCA_DESTINATARIO.search(texto)
    limite = pos_destinatario.start() if pos_destinatario else len(texto)
    topo = texto[:limite]

    cnpjs_topo = _REGEX_CNPJ.findall(topo)
    if cnpjs_topo:
        return _canonicalizar_cnpj(cnpjs_topo[0]), razao

    # Fallback: qualquer CNPJ do documento todo.
    cnpjs_todos = _REGEX_CNPJ.findall(texto)
    if cnpjs_todos:
        return _canonicalizar_cnpj(cnpjs_todos[0]), razao

    return None, razao


def _canonicalizar_cnpj(cnpj_bruto: str) -> str:
    """Normaliza CNPJ para XX.XXX.XXX/XXXX-XX."""
    digitos = re.sub(r"\D", "", cnpj_bruto)
    if len(digitos) != 14:
        return cnpj_bruto
    return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"


def _limpar_razao_emitente(linha: str) -> str | None:
    """Remove CNPJ/IE eventualmente grudados na mesma linha da razão social."""
    limpa = re.sub(
        r"CNPJ\s*:?\s*\d{2}\.?\d{3}\.?\d{3}/\d{4}-?\d{2}",
        "",
        linha,
        flags=re.IGNORECASE,
    )
    limpa = re.sub(r"IE\s*:?\s*[\w\s\-\.]+$", "", limpa, flags=re.IGNORECASE)
    limpa = limpa.strip(" -\t")
    return limpa or None


def _extrair_endereco(texto: str) -> str | None:
    match = RE_ENDERECO_ROTULO.search(texto)
    if not match:
        return None
    return _limpar_espacos(match.group(1))


def _extrair_data_emissao(texto: str) -> str | None:
    """Data de emissão: preferência pelo rótulo explícito; fallback primeira DD/MM/YYYY."""
    match = RE_DATA_EMISSAO.search(texto)
    if match:
        return _iso_de_ddmmyyyy(match.group(1))
    match_gen = RE_DATA_DDMMYYYY_GENERICA.search(texto)
    if match_gen:
        return _iso_de_ddmmyyyy(match_gen.group(1))
    return None


def _iso_de_ddmmyyyy(bruto: str) -> str | None:
    partes = bruto.split("/")
    if len(partes) != 3:
        return None
    dia, mes, ano = partes
    return f"{ano}-{mes}-{dia}"


def _extrair_destinatario(texto: str) -> str | None:
    """CPF/CNPJ do destinatário. Procura no bloco após DESTINATÁRIO / REMETENTE."""
    pos = RE_MARCA_DESTINATARIO.search(texto)
    if not pos:
        return None
    bloco = texto[pos.end() : pos.end() + 400]
    match_cnpj = _REGEX_CNPJ.search(bloco)
    if match_cnpj:
        return _canonicalizar_cnpj(match_cnpj.group(0))
    match_cpf = re.search(r"(\d{3}\.\d{3}\.\d{3}-\d{2})", bloco)
    if match_cpf:
        return match_cpf.group(1)
    return None


# ============================================================================
# Helpers de leitura de PDF
# ============================================================================


def _ler_paginas_pdf(caminho: Path) -> list[str]:
    try:
        import pdfplumber
    except ImportError as erro:
        logger.error("pdfplumber indisponível: %s", erro)
        return []
    paginas: list[str] = []
    try:
        with pdfplumber.open(caminho) as pdf:
            for pg in pdf.pages:
                paginas.append(pg.extract_text() or "")
    except Exception as erro:
        logger.warning("falha ao ler %s via pdfplumber: %s", caminho, erro)
        return []
    return paginas


# ============================================================================
# Helpers numéricos / textuais
# ============================================================================


def _parse_valor_br(bruto: str | None) -> float | None:
    """Converte string monetária brasileira (1.234,56) em float. Devolve None se falhar."""
    if not bruto:
        return None
    limpo = bruto.replace(".", "").replace(",", ".")
    try:
        return float(limpo)
    except ValueError:
        return None


def _match_grupo(padrao: re.Pattern[str], texto: str) -> str | None:
    match = padrao.search(texto)
    if not match:
        return None
    return match.group(1).strip()


def _limpar_espacos(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


# "A nota fiscal conta a história que o banco não conta." -- princípio do contador
