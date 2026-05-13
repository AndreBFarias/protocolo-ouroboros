"""Gerador de pacote IRPF anual — Sprint UX-RD-14.

Compila os 4 artefatos canônicos de uma declaração IRPF a partir do
``extrato`` consolidado, recortado pelo ano-calendário:

* ``relatorio.pdf`` — relatório executivo com totais por categoria de tag
  IRPF, gerado via ``reportlab`` (já dependência do projeto, ver
  ``pyproject.toml``).
* ``dados.xlsx`` — planilha com aba ``IRPF_<ano>`` listando cada
  transação com tag, valor, fonte (banco_origem), CNPJ/CPF (quando
  presente) e mês de referência. Gerada via ``openpyxl``.
* ``dados.json`` — dataset em formato JSON legível por máquina, schema
  canônico (lista de eventos com ``tag``, ``valor``, ``fonte``,
  ``cnpj_cpf``, ``mes``, ``data``, ``descricao``).  # noqa: accent
* ``originais/`` — diretório que reúne cópias dos arquivos originais
  vinculados às transações tagueadas (PDFs, imagens). A cópia respeita o
  princípio "Local First" (ADR-07): arquivos viajam junto do pacote.

Princípios canonizados (sprint UX-RD-14):

* **Idempotência**: chamar ``gerar_pacote(ano)`` duas vezes sobrescreve o
  pacote. O caller é responsável por versionar via Git/snapshot se quiser
  preservar histórico.
* **Tags reais apenas** (regra ``forbidden`` da spec): só lê
  ``tag_irpf`` populada por ``src/transform/irpf_tagger.py``. Não inventa
  deduções; categorias sem dado ficam zeradas no relatório.
* **Sem PII em log**: CPF/CNPJ aparecem nos artefatos (são necessários
  para a declaração) mas o ``logger`` mascara.

A função pública é ``gerar_pacote(ano: int, dados: dict | None = None,
diretorio_base: Path | None = None) -> Path``. Os parâmetros opcionais
permitem injetar um dataset alternativo (testes) ou redirecionar o
diretório-base (testes/sandbox).
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.utils.logger import configurar_logger

logger = configurar_logger("pacote_irpf")

# Categorias canônicas exibidas pelo dashboard UX-RD-14 (15-irpf.html).
# Mantemos a ordem fiel ao mockup; tags ausentes do tagger atual
# (``dedutivel_educacional``, ``previdencia_privada``,
# ``doacao_dedutivel``) ficam zeradas mas presentes para o pacote
# expor a estrutura completa.
CATEGORIAS_IRPF: tuple[str, ...] = (
    "rendimento_tributavel",
    "rendimento_isento",
    "dedutivel_medico",
    "dedutivel_educacional",
    "previdencia_privada",
    "imposto_pago",
    "inss_retido",
    "doacao_dedutivel",
)

# Mascara PII para mensagens de log; CNPJ/CPF aparecem nos artefatos finais
# (necessários para a declaração) mas nunca no stdout/log.
_REGEX_CNPJ = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/\d{4}-?\d{2}")
_REGEX_CPF = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")


def _mascarar_pii(texto: str) -> str:
    """Mascara CNPJ/CPF antes de escrever em log."""
    texto = _REGEX_CNPJ.sub("XX.XXX.XXX/XXXX-XX", texto)
    texto = _REGEX_CPF.sub("XXX.XXX.XXX-XX", texto)
    return texto


def _diretorio_padrao(ano: int, base: Path | None = None) -> Path:
    """Resolve o diretório de saída ``data/aplicacoes/irpf_<ano>/``."""
    raiz = base or Path(__file__).resolve().parents[2] / "data" / "aplicacoes"
    return raiz / f"irpf_{ano}"


def _filtrar_extrato_ano(df: pd.DataFrame, ano: int) -> pd.DataFrame:
    """Filtra extrato pelo ano-calendário usando ``mes_ref`` (YYYY-MM)."""
    if df is None or df.empty or "mes_ref" not in df.columns:
        return pd.DataFrame()
    prefixo = f"{ano:04d}"
    recorte = df[df["mes_ref"].astype(str).str.startswith(prefixo)].copy()
    return recorte


def _filtrar_por_devedora(df: pd.DataFrame, pessoa: str | None) -> pd.DataFrame:
    """Filtra extrato pela pessoa fiscalmente devedora (Sprint DASH-PAGAMENTOS-CRUZADOS-CASAL).

    Quando ``pessoa`` é fornecida (ex: ``"pessoa_a"``), o filtro escolhe a
    coluna canônica ``pessoa_devedora`` se populada; caso contrário, cai em
    ``quem`` (fallback retrocompat -- padrão (o)). Resultado: imposto pago
    de pessoa_a entra na declaração de pessoa_a mesmo quando outra pessoa
    pagou efetivamente da conta dela.

    Quando ``pessoa is None``, devolve o DataFrame inteiro (pacote global,
    comportamento original).
    """
    if df is None or df.empty or pessoa is None:
        return df if df is not None else pd.DataFrame()
    if "quem" not in df.columns:
        return df
    if "pessoa_devedora" in df.columns:
        # Constrói coluna efetiva: pessoa_devedora quando populada, senão quem.
        efetiva = df["pessoa_devedora"].where(df["pessoa_devedora"].notna(), df["quem"])
    else:
        efetiva = df["quem"]
    return df[efetiva == pessoa].copy()


def compilar_eventos(df_ano: pd.DataFrame) -> list[dict[str, Any]]:
    """Compila lista de eventos canônicos para JSON/XLSX/PDF.

    Cada evento expõe ``tag``, ``valor`` (positivo absoluto), ``fonte``,
    ``cnpj_cpf``, ``mes``, ``data`` e ``descricao``. Apenas linhas com  # noqa: accent
    ``tag_irpf`` populada entram.
    """
    if df_ano.empty or "tag_irpf" not in df_ano.columns:
        return []
    sub = df_ano[df_ano["tag_irpf"].notna()].copy()
    if sub.empty:
        return []

    eventos: list[dict[str, Any]] = []
    for _, linha in sub.iterrows():
        tag = _str_seguro(linha.get("tag_irpf"))
        if not tag:
            continue
        valor = abs(float(linha.get("valor") or 0))
        descricao = (
            _str_seguro(linha.get("local"))
            or _str_seguro(linha.get("_descricao_original"))
            or _str_seguro(linha.get("obs"))
            or ""
        )
        cnpj = _str_seguro(linha.get("cnpj_cpf"))
        evento = {
            "tag": tag,
            "valor": round(valor, 2),
            "fonte": _str_seguro(linha.get("banco_origem")),
            "cnpj_cpf": cnpj or None,
            "mes": _str_seguro(linha.get("mes_ref")),
            "data": _str_seguro(linha.get("data")),
            "descricao": descricao,
        }
        eventos.append(evento)
    return eventos


def _str_seguro(valor: Any) -> str:
    """Converte valor de célula pandas para str respeitando NaN/None.

    pandas representa células ausentes como ``NaN`` (``float('nan')``) e
    ``str(NaN)`` retorna ``'nan'`` -- string ruidosa que vaza para JSON.
    Aqui devolvemos string vazia tanto para ``None`` quanto para ``NaN``.
    """
    if valor is None:
        return ""
    # NaN é o único valor que não é igual a si mesmo.
    try:
        if valor != valor:  # noqa: PLR0124
            return ""
    except TypeError:
        # Tipos não comparáveis (ex.: dict): trata como vazio.
        return ""
    texto = str(valor).strip()
    if texto.lower() == "nan":
        return ""
    return texto


def compilar_totais(eventos: Iterable[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Compila totais por categoria, sempre incluindo as 8 canônicas."""
    base: dict[str, dict[str, float]] = {
        cat: {"valor": 0.0, "count": 0} for cat in CATEGORIAS_IRPF
    }
    for evento in eventos:
        tag = evento.get("tag")
        if tag not in base:
            # Tag desconhecida (extensão futura do tagger) ainda entra
            # como linha extra para auditoria — não silenciar.
            base[tag] = {"valor": 0.0, "count": 0}
        base[tag]["valor"] += float(evento.get("valor") or 0)
        base[tag]["count"] += 1
    # Arredonda no final para evitar acumular ruído de ponto flutuante.
    for cat in base:
        base[cat]["valor"] = round(base[cat]["valor"], 2)
    return base


def _escrever_json(eventos: list[dict[str, Any]], totais: dict, ano: int, destino: Path) -> Path:
    """Escreve dados.json com schema canônico."""
    payload = {
        "ano_calendario": ano,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "totais_por_categoria": totais,
        "eventos": eventos,
    }
    destino.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return destino


def _escrever_xlsx(eventos: list[dict[str, Any]], ano: int, destino: Path) -> Path:
    """Escreve dados.xlsx com aba ``IRPF_<ano>``."""
    wb = Workbook()
    ws = wb.active
    ws.title = f"IRPF_{ano}"
    cabecalho = ["data", "mes", "tag", "valor", "fonte", "cnpj_cpf", "descricao"]
    ws.append(cabecalho)
    for evento in eventos:
        ws.append(
            [
                evento.get("data", ""),
                evento.get("mes", ""),
                evento.get("tag", ""),
                evento.get("valor", 0.0),
                evento.get("fonte", ""),
                evento.get("cnpj_cpf") or "",
                evento.get("descricao", ""),
            ]
        )
    wb.save(destino)
    return destino


def _escrever_pdf(totais: dict, eventos: list[dict[str, Any]], ano: int, destino: Path) -> Path:
    """Escreve relatorio.pdf com tabela de totais por categoria."""
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "TituloIRPF",
        parent=estilos["Title"],
        fontSize=16,
        spaceAfter=12,
    )
    subtitulo = ParagraphStyle(
        "SubtituloIRPF",
        parent=estilos["Heading2"],
        fontSize=12,
        spaceAfter=8,
    )
    corpo = estilos["BodyText"]

    doc = SimpleDocTemplate(
        str(destino),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    flow: list[Any] = []
    flow.append(Paragraph(f"Relatório IRPF {ano}", titulo))
    flow.append(
        Paragraph(
            "Compilação automática a partir do banco catalogado. "
            "Cada categoria agrega transações com a mesma classificação fiscal.",
            corpo,
        )
    )
    flow.append(Spacer(1, 12))

    flow.append(Paragraph("Totais por categoria", subtitulo))

    dados_tabela: list[list[str]] = [["Categoria", "Quantidade", "Valor (R$)"]]
    soma_total = 0.0
    for categoria in CATEGORIAS_IRPF:
        info = totais.get(categoria, {"valor": 0.0, "count": 0})
        valor = float(info.get("valor") or 0)
        soma_total += valor
        dados_tabela.append(
            [
                categoria,
                str(int(info.get("count") or 0)),
                f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            ]
        )
    dados_tabela.append(
        [
            "TOTAL",
            str(len(eventos)),
            f"{soma_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        ]
    )

    tabela = Table(dados_tabela, colWidths=[7 * cm, 3 * cm, 5 * cm])
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#edf2f7")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e0")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    flow.append(tabela)
    flow.append(Spacer(1, 16))
    flow.append(
        Paragraph(
            f"Eventos compilados: {len(eventos)}. "
            f"Pacote completo em data/aplicacoes/irpf_{ano}/.",
            corpo,
        )
    )

    doc.build(flow)
    return destino


def _copiar_originais(
    eventos: list[dict[str, Any]],
    df_ano: pd.DataFrame,
    destino_dir: Path,
) -> int:
    """Copia arquivos originais vinculados quando há coluna ``arquivo_origem``.

    Retorna a quantidade de arquivos copiados. O diretório é sempre criado
    (mesmo vazio) para que o pacote tenha a estrutura canônica completa.
    """
    destino_dir.mkdir(parents=True, exist_ok=True)
    if df_ano.empty or "arquivo_origem" not in df_ano.columns:
        return 0
    sub = df_ano[df_ano["tag_irpf"].notna() & df_ano["arquivo_origem"].notna()]
    copiados = 0
    vistos: set[str] = set()
    for caminho_str in sub["arquivo_origem"].astype(str):
        if not caminho_str or caminho_str in vistos:
            continue
        vistos.add(caminho_str)
        origem = Path(caminho_str)
        if not origem.exists():
            continue
        alvo = destino_dir / origem.name
        try:
            shutil.copy2(origem, alvo)
            copiados += 1
        except OSError as exc:
            logger.warning("falha ao copiar original %s: %s", _mascarar_pii(str(origem)), exc)
    return copiados


def gerar_pacote(
    ano: int,
    dados: dict[str, pd.DataFrame] | None = None,
    diretorio_base: Path | None = None,
    pessoa: str | None = None,
) -> Path:
    """Gera o pacote IRPF do ``ano`` e devolve o diretório criado.

    * ``dados``: dict com ao menos ``extrato`` (DataFrame). Se ``None``,
      tenta carregar via ``src.dashboard.dados.carregar_dados()``
      (atalho útil para o botão do dashboard; testes injetam ``dados``).
    * ``diretorio_base``: redireciona ``data/aplicacoes`` (testes/sandbox).
    * ``pessoa``: identificador genérico (``pessoa_a`` / ``pessoa_b``)
      para gerar pacote individual filtrando por ``pessoa_devedora``
      (fallback ``quem``). ``None`` mantém comportamento original
      (pacote global). Padrão (o): default retrocompat.

    O diretório resultante contém ``relatorio.pdf``, ``dados.xlsx``,
    ``dados.json`` e ``originais/`` (sempre criado, mesmo vazio).
    Idempotente: chamadas repetidas sobrescrevem.
    """
    if dados is None:
        # Import lazy: evita ciclo dashboard <-> exports nos testes.
        from src.dashboard.dados import carregar_dados

        dados = carregar_dados()

    extrato = dados.get("extrato") if isinstance(dados, dict) else None
    if extrato is None:
        extrato = pd.DataFrame()
    df_ano = _filtrar_extrato_ano(extrato, ano)
    df_ano = _filtrar_por_devedora(df_ano, pessoa)

    diretorio = _diretorio_padrao(ano, diretorio_base)
    if diretorio.exists():
        logger.warning("pacote IRPF %d já existia; sobrescrevendo em %s", ano, diretorio)
    diretorio.mkdir(parents=True, exist_ok=True)

    eventos = compilar_eventos(df_ano)
    totais = compilar_totais(eventos)

    destino_pdf = diretorio / "relatorio.pdf"
    destino_xlsx = diretorio / "dados.xlsx"
    destino_json = diretorio / "dados.json"
    destino_originais = diretorio / "originais"

    _escrever_pdf(totais, eventos, ano, destino_pdf)
    _escrever_xlsx(eventos, ano, destino_xlsx)
    _escrever_json(eventos, totais, ano, destino_json)
    copiados = _copiar_originais(eventos, df_ano, destino_originais)

    logger.info(
        "pacote IRPF %d gerado em %s (eventos=%d, originais=%d)",
        ano,
        diretorio,
        len(eventos),
        copiados,
    )
    return diretorio


# "O que é deduzível precisa ser comprovável." -- princípio do contribuinte
