"""Extrator de XML NFe (modelo 55) padrão SEFAZ layout 4.0 -- Sprint 46.

XML NFe é a fonte canônica do documento fiscal eletrônico: estruturado,
assinado digitalmente pela SEFAZ, contém todos os campos do DANFE PDF
(Sprint 44) mais os tributos detalhados por item (ICMS/IPI/PIS/COFINS).
Quando disponível, deve ser preferido sobre o DANFE PDF.

Este extrator trabalha com XMLs distribuídos nos envelopes `<nfeProc>`
(layout oficial de NFe autorizada) e `<procEventoNFe>` (evento de
cancelamento envelopando a NFe original). Parse 100% stdlib via
`xml.etree.ElementTree` -- sem dependência nova.

Campos canônicos extraídos:

    chave_44           -- 44 dígitos com DV SEFAZ validado
    numero, serie      -- identificadores do documento (# noqa: accent)
    data_emissao       -- YYYY-MM-DD (da tag `dhEmi`)
    cnpj_emitente      -- canônico XX.XXX.XXX/XXXX-XX
    razao_social       -- `xNome` do emitente
    endereco           -- logradouro + número + bairro + município + UF
    total              -- float (`total/ICMSTot/vNF`)
    cfop_nota          -- CFOP do primeiro item (cabeçalho não tem campo próprio)
    cpf_cnpj_destinatario -- CPF ou CNPJ do destinatário (canônico)
    cancelada          -- bool; True se há `tpEvento=110111` ou `cStat` 101/135
    origem_fonte       -- "xml_nfe" (marca fonte no grafo p/ sobrescrita)
    itens              -- list[dict] com código, descrição (# noqa: accent), ncm, cfop,
                          unidade, qtde, valor_unit, valor_total,
                          icms_valor, ipi_valor, pis_valor, cofins_valor,
                          origem_fonte="xml_nfe"

Efeitos colaterais: `extrair()` ingere cada XML no grafo via
`src/graph/ingestor_documento.py:ingerir_documento_fiscal` -- cria nó
`documento` + 1 nó `fornecedor` + N nós `item` + arestas
`fornecido_por`/`contem_item`/`ocorre_em`. Retorna lista VAZIA de
`base.Transacao` -- o total já aparece no extrato bancário.

Sobrescrita sobre DANFE PDF (Fase 2 do spec): quando um `documento`
com a mesma `chave_44` já foi ingerido por outro extrator (ex.:
`danfe_pdf`), o `upsert_node` do GrafoDB faz merge raso de metadata
-- os campos novos do XML (tributos por item, `origem_fonte`)
sobrescrevem os antigos. Novas arestas `contem_item` são idempotentes
via UNIQUE(src, dst, tipo) do schema.

Armadilhas tratadas (Sprint 46 -- docs/sprints/producao/sprint_46_*.md):

    A46-1: atributo `Id="NFe<chave>"` vs `Id="<chave>"` -- strip do
           prefixo `NFe` antes de validar DV.
    A46-2: NFe cancelada (evento 110111) mantém o XML -- detectada
           por `tpEvento=110111` dentro de `procEventoNFe` OU por
           `cStat` entre 101/135 no `retEvento`.
    A46-3: layout 3.10 tem tags compatíveis com 4.0 para o subset
           que extraímos (ide/emit/dest/det/total/ICMSTot) -- mesmo
           parser funciona; só muda a versão declarada no atributo.
    A46-4: XML pode chegar como bytes com encoding divergente do
           declarado no prólogo -- usar `ET.parse` com arquivo aceita;
           fallback para `ET.fromstring(bytes)` se abertura por caminho
           falhar.
    A46-5: destinatário pode ser CPF (PF) ou CNPJ (PJ) -- tentar
           CNPJ primeiro, fallback CPF (ordem canônica SEFAZ).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from src.extractors.base import ExtratorBase, Transacao
from src.graph.db import GrafoDB, caminho_padrao
from src.graph.ingestor_documento import ingerir_documento_fiscal
from src.utils.chave_nfe import (
    extrair_cnpj_emitente as cnpj_da_chave,
)
from src.utils.chave_nfe import (
    extrair_modelo,
    valida_digito_verificador,
)
from src.utils.chave_nfe import (
    normalizar as normalizar_chave,
)
from src.utils.logger import configurar_logger

logger = configurar_logger("xml_nfe")

EXTENSOES_ACEITAS: tuple[str, ...] = (".xml",)

# Namespace oficial NFe (layouts 3.10 e 4.00 usam o mesmo URI).
NS_NFE: str = "http://www.portalfiscal.inf.br/nfe"
NS: dict[str, str] = {"nfe": NS_NFE}

ORIGEM_FONTE: str = "xml_nfe"

# Código do evento de cancelamento na SEFAZ.
TP_EVENTO_CANCELAMENTO: str = "110111"

# Status SEFAZ que indicam cancelamento (101) ou evento vinculado (135).
STATUS_CANCELAMENTO: frozenset[str] = frozenset({"101", "135"})


# ============================================================================
# ExtratorXmlNFe -- classe pública
# ============================================================================


class ExtratorXmlNFe(ExtratorBase):
    """Extrai XML NFe modelo 55 (layout SEFAZ 4.0) e popula o grafo.

    `pode_processar` aceita `.xml` cuja raiz (ou qualquer descendente)
    tenha namespace `http://www.portalfiscal.inf.br/nfe` e contenha o
    elemento `infNFe` com modelo 55.

    `extrair` devolve `[]` de `base.Transacao` (total já está no extrato
    bancário). Efeito colateral: nó `documento` + fornecedor + N itens +
    arestas no grafo, com `metadata.origem_fonte="xml_nfe"` para
    sobrescrever dados vindos de DANFE PDF da mesma chave 44.
    """

    BANCO_ORIGEM: str = "XML NFe55"

    def __init__(self, caminho: Path, grafo: GrafoDB | None = None) -> None:
        super().__init__(caminho)
        self._grafo = grafo

    # ------------------------------------------------------------------
    # Contrato ExtratorBase
    # ------------------------------------------------------------------

    def pode_processar(self, caminho: Path) -> bool:
        if caminho.suffix.lower() not in EXTENSOES_ACEITAS:
            return False
        try:
            root = _ler_root(caminho)
        except ET.ParseError as erro:
            self.logger.debug("pode_processar: XML inválido em %s: %s", caminho, erro)
            return False
        except OSError as erro:
            self.logger.debug("pode_processar: falha IO em %s: %s", caminho, erro)
            return False
        return e_xml_nfe(root)

    def extrair(self) -> list[Transacao]:
        """Extrai o XML NFe e ingere no grafo. Retorna [] de Transacao."""  # noqa: accent
        xmls = self.extrair_xmls(self.caminho)
        if not xmls:
            return []
        grafo = self._grafo or GrafoDB(caminho_padrao())
        criou_grafo_localmente = self._grafo is None
        try:
            grafo.criar_schema()
            for doc, itens in xmls:
                if doc.get("cancelada"):
                    self.logger.warning(
                        "XML NFe CANCELADA em %s (chave %s) -- não ingerido no grafo",
                        self.caminho.name,
                        doc.get("chave_44"),
                    )
                    continue
                try:
                    ingerir_documento_fiscal(grafo, doc, itens, caminho_arquivo=self.caminho)
                except ValueError as erro:
                    self.logger.warning("XML NFe inválido em %s: %s", self.caminho.name, erro)
        finally:
            if criou_grafo_localmente:
                grafo.fechar()
        self.logger.info("%d XML NFe ingerido(s) a partir de %s", len(xmls), self.caminho.name)
        return []

    # ------------------------------------------------------------------
    # API pública testável
    # ------------------------------------------------------------------

    def extrair_xmls(
        self,
        caminho: Path,
        conteudo_override: bytes | str | None = None,
    ) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
        """Extrai NFe(s) do arquivo XML. Devolve lista de (documento, itens).

        `conteudo_override` permite injetar bytes/str nos testes sem
        depender de IO -- mesma estratégia das Sprints 44/44b com
        `texto_override` dos extratores de PDF.

        Devolve [] se:
          - XML não é NFe (namespace errado ou sem `infNFe`).
          - Modelo da chave não é 55 (extrator rejeita NFC-e 65).
          - Falha de parse XML.
        """
        try:
            if conteudo_override is not None:
                if isinstance(conteudo_override, str):
                    root = ET.fromstring(conteudo_override)
                else:
                    root = ET.fromstring(conteudo_override)
            else:
                root = _ler_root(caminho)
        except ET.ParseError as erro:
            logger.warning("XML inválido em %s: %s", caminho, erro)
            return []

        if not e_xml_nfe(root):
            return []

        documento = _parse_cabecalho(root)
        if documento is None:
            return []

        itens = _parse_itens(root)
        documento["qtde_itens"] = len(itens)
        return [(documento, itens)]


# ============================================================================
# Detector
# ============================================================================


def e_xml_nfe(root: ET.Element) -> bool:
    """True se o XML é uma NFe modelo 55 (ou evento de NFe modelo 55).

    Critérios:
      - Namespace `http://www.portalfiscal.inf.br/nfe` presente.
      - Existe `infNFe` (no próprio root, em `NFe/infNFe` ou envolto
        em `nfeProc`/`procEventoNFe`).
      - Modelo da chave é 55 (rejeita NFC-e modelo 65 que tem extrator
        dedicado na Sprint 44b).
    """
    if not _tem_namespace_nfe(root):
        return False
    infnfe = _buscar_infnfe(root)
    if infnfe is None:
        return False
    chave = _extrair_chave_do_atributo(infnfe)
    if chave is None:
        return False
    if extrair_modelo(chave) != "55":
        return False
    return True


def _tem_namespace_nfe(root: ET.Element) -> bool:
    """Aceita XML cuja tag (do root ou descendentes) use o namespace SEFAZ."""
    if root.tag.startswith("{" + NS_NFE + "}"):
        return True
    for elem in root.iter():
        if elem.tag.startswith("{" + NS_NFE + "}"):
            return True
    return False


def _buscar_infnfe(root: ET.Element) -> ET.Element | None:
    """Localiza `infNFe` independentemente do envelope (nfeProc/procEventoNFe)."""
    # Tag direta no root (raro, mas possível quando o XML já vem sem envelope).
    if root.tag == "{" + NS_NFE + "}infNFe":
        return root
    achado = root.find(".//nfe:infNFe", NS)
    return achado


# ============================================================================
# Parser de cabeçalho
# ============================================================================


def _parse_cabecalho(root: ET.Element) -> dict[str, Any] | None:
    """Parse de campos do cabeçalho. Devolve None se chave faltar ou for inválida."""
    infnfe = _buscar_infnfe(root)
    if infnfe is None:
        return None

    chave = _extrair_chave_do_atributo(infnfe)
    if not chave or not valida_digito_verificador(chave):
        return None
    if extrair_modelo(chave) != "55":
        return None

    ide = infnfe.find("nfe:ide", NS)
    emit = infnfe.find("nfe:emit", NS)
    dest = infnfe.find("nfe:dest", NS)
    total = infnfe.find("nfe:total/nfe:ICMSTot", NS)

    if emit is None:
        return None

    cnpj_emitente = _cnpj_canonico(_texto(emit, "nfe:CNPJ"))
    if not cnpj_emitente:
        return None

    # Sanity check com o CNPJ embutido na chave (Luna feedback #4: evidência).
    cnpj_chave = cnpj_da_chave(chave)
    if cnpj_chave and cnpj_chave != cnpj_emitente:
        logger.warning(
            "CNPJ divergente em XML NFe %s: emit=%s, chave=%s -- usando emit",
            chave,
            cnpj_emitente,
            cnpj_chave,
        )

    numero = _texto(ide, "nfe:nNF") if ide is not None else None
    serie = _texto(ide, "nfe:serie") if ide is not None else None
    data_emissao = _iso_de_dhemi(_texto(ide, "nfe:dhEmi")) if ide is not None else None

    total_valor = _parse_float(_texto(total, "nfe:vNF")) if total is not None else None

    razao_social = _texto(emit, "nfe:xNome")
    endereco = _extrair_endereco(emit.find("nfe:enderEmit", NS))

    cpf_cnpj_destinatario = _extrair_destinatario(dest) if dest is not None else None

    # CFOP "da nota" não existe em NFe -- pega o do primeiro item como proxy.
    primeiro_det = infnfe.find("nfe:det", NS)
    cfop = None
    if primeiro_det is not None:
        cfop = _texto(primeiro_det, "nfe:prod/nfe:CFOP")

    cancelada = _detectar_cancelamento(root)

    return {
        "chave_44": chave,
        "tipo_documento": "nfe_modelo_55",
        "origem_fonte": ORIGEM_FONTE,
        "cnpj_emitente": cnpj_emitente,
        "razao_social": razao_social,
        "endereco": endereco,
        "numero": numero,
        "serie": serie,
        "data_emissao": data_emissao,
        "total": total_valor,
        "cfop_nota": cfop,
        "cpf_cnpj_destinatario": cpf_cnpj_destinatario,
        "cancelada": cancelada,
    }


def _extrair_chave_do_atributo(infnfe: ET.Element) -> str | None:
    """Extrai a chave 44 do atributo `Id="NFe<chave>"` ou `Id="<chave>"`.

    Armadilha A46-1: SEFAZ usa prefixo `NFe` no Id, mas alguns exportadores
    o omitem. Normalizamos removendo qualquer caractere não-dígito antes de
    validar.
    """
    id_bruto = infnfe.get("Id", "")
    if not id_bruto:
        return None
    # Remove prefixo "NFe" e qualquer caractere não-dígito.
    return normalizar_chave(id_bruto)


def _extrair_endereco(ender: ET.Element | None) -> str | None:
    """Monta endereço canônico: 'logradouro, número, bairro, município-UF'."""  # noqa: accent
    if ender is None:
        return None
    partes: list[str] = []
    logradouro = _texto(ender, "nfe:xLgr")
    numero = _texto(ender, "nfe:nro")
    bairro = _texto(ender, "nfe:xBairro")
    municipio = _texto(ender, "nfe:xMun")
    uf = _texto(ender, "nfe:UF")
    if logradouro:
        if numero:
            partes.append(f"{logradouro}, {numero}")
        else:
            partes.append(logradouro)
    if bairro:
        partes.append(bairro)
    if municipio and uf:
        partes.append(f"{municipio}-{uf}")
    elif municipio:
        partes.append(municipio)
    return ", ".join(partes) if partes else None


def _extrair_destinatario(dest: ET.Element) -> str | None:
    """CPF ou CNPJ do destinatário (Armadilha A46-5). CNPJ tem prioridade."""
    cnpj_bruto = _texto(dest, "nfe:CNPJ")
    cnpj = _cnpj_canonico(cnpj_bruto)
    if cnpj:
        return cnpj
    cpf_bruto = _texto(dest, "nfe:CPF")
    return _cpf_canonico(cpf_bruto)


def _detectar_cancelamento(root: ET.Element) -> bool:
    """Detecta cancelamento via evento 110111 ou cStat 101/135 no retEvento.

    Armadilha A46-2: NFe cancelada mantém o XML original envolto em
    `procEventoNFe`. Três marcadores possíveis (qualquer um confirma):
      - `<tpEvento>110111</tpEvento>` no bloco `infEvento`.
      - `<cStat>101</cStat>` em `retEvento/infEvento` (status cancelado).
      - `<cStat>135</cStat>` em `retEvento/infEvento` (evento vinculado).
    """
    if root.tag == "{" + NS_NFE + "}procEventoNFe":
        return True
    for tp_evento in root.iter("{" + NS_NFE + "}tpEvento"):
        if (tp_evento.text or "").strip() == TP_EVENTO_CANCELAMENTO:
            return True
    # Qualquer cStat de cancelamento em qualquer nível.
    for c_stat in root.iter("{" + NS_NFE + "}cStat"):
        if (c_stat.text or "").strip() in STATUS_CANCELAMENTO:
            return True
    return False


# ============================================================================
# Parser de itens
# ============================================================================


def _parse_itens(root: ET.Element) -> list[dict[str, Any]]:
    """Extrai todos os `det` (itens) com tributação completa."""
    infnfe = _buscar_infnfe(root)
    if infnfe is None:
        return []
    itens: list[dict[str, Any]] = []
    for det in infnfe.findall("nfe:det", NS):
        item = _item_de_det(det)
        if item is not None:
            itens.append(item)
    return itens


def _item_de_det(det: ET.Element) -> dict[str, Any] | None:
    """Converte um elemento `<det>` em dict canônico do grafo.

    Inclui tributos (ICMS/IPI/PIS/COFINS) extraídos de dentro de `imposto`.
    Quando o XML não traz o tributo (isenção, Simples, NT), o campo fica None.
    """
    prod = det.find("nfe:prod", NS)
    if prod is None:
        return None
    codigo = _texto(prod, "nfe:cProd")
    descricao = _texto(prod, "nfe:xProd")  # noqa: accent
    if not codigo or not descricao:
        return None
    imposto = det.find("nfe:imposto", NS)
    return {
        "numero_item": det.get("nItem"),
        "codigo": codigo,
        "descricao": descricao,
        "ncm": _texto(prod, "nfe:NCM"),
        "cfop": _texto(prod, "nfe:CFOP"),
        "unidade": (_texto(prod, "nfe:uCom") or "").upper() or None,
        "qtde": _parse_float(_texto(prod, "nfe:qCom")),
        "valor_unit": _parse_float(_texto(prod, "nfe:vUnCom")),
        "valor_total": _parse_float(_texto(prod, "nfe:vProd")),
        "icms_valor": _tributo_valor(imposto, "ICMS", "vICMS"),
        "ipi_valor": _tributo_valor(imposto, "IPI", "vIPI"),
        "pis_valor": _tributo_valor(imposto, "PIS", "vPIS"),
        "cofins_valor": _tributo_valor(imposto, "COFINS", "vCOFINS"),
        "origem_fonte": ORIGEM_FONTE,
    }


def _tributo_valor(imposto: ET.Element | None, grupo: str, tag_valor: str) -> float | None:
    """Busca o valor de um tributo dentro de `<imposto>`.

    Cada grupo (ICMS/IPI/PIS/COFINS) pode ter várias tags-filho para
    diferentes regimes tributários (ex.: ICMS00, ICMSSN102, ICMS70...),
    mas todas elas abrigam a tag de valor (`vICMS`, `vIPI`, `vPIS`,
    `vCOFINS`) no mesmo nível de neto. Usamos `.//` para procurar em
    qualquer profundidade abaixo do grupo.
    """
    if imposto is None:
        return None
    grupo_elem = imposto.find(f"nfe:{grupo}", NS)
    if grupo_elem is None:
        return None
    alvo = grupo_elem.find(f".//nfe:{tag_valor}", NS)
    if alvo is None or not (alvo.text or "").strip():
        return None
    return _parse_float(alvo.text)


# ============================================================================
# Helpers de baixo nível
# ============================================================================


def _ler_root(caminho: Path) -> ET.Element:
    """Lê o XML e devolve o elemento raiz.

    Armadilha A46-4: encoding declarado no prólogo pode divergir do real.
    `ET.parse` aceita o Path -- se falhar, relança; o chamador decide (os
    métodos públicos já tratam `ParseError`/`OSError`).
    """
    tree = ET.parse(caminho)
    return tree.getroot()


def _texto(elem: ET.Element | None, xpath: str) -> str | None:
    """Texto normalizado de um subelemento (strip); None se ausente/vazio."""
    if elem is None:
        return None
    achado = elem.find(xpath, NS)
    if achado is None or achado.text is None:
        return None
    texto = achado.text.strip()
    return texto or None


def _parse_float(bruto: str | None) -> float | None:
    """Converte string numérica XML NFe (ponto decimal padrão XML) em float."""
    if bruto is None:
        return None
    limpo = bruto.strip()
    if not limpo:
        return None
    try:
        return float(limpo)
    except ValueError:
        return None


def _iso_de_dhemi(bruto: str | None) -> str | None:
    """Extrai YYYY-MM-DD do `dhEmi` (formato SEFAZ `YYYY-MM-DDTHH:MM:SS-03:00`)."""
    if not bruto:
        return None
    return bruto[:10] if len(bruto) >= 10 else None


def _cnpj_canonico(bruto: str | None) -> str | None:
    """Normaliza CNPJ para XX.XXX.XXX/XXXX-XX (14 dígitos). None se inválido."""
    if not bruto:
        return None
    digitos = "".join(c for c in bruto if c.isdigit())
    if len(digitos) != 14:
        return None
    return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"


def _cpf_canonico(bruto: str | None) -> str | None:
    """Normaliza CPF para XXX.XXX.XXX-XX (11 dígitos). None se inválido."""
    if not bruto:
        return None
    digitos = "".join(c for c in bruto if c.isdigit())
    if len(digitos) != 11:
        return None
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


# "O ideal do dado é a estrutura -- o XML é a forma do imposto." -- princípio do auditor
