"""Auditoria de fidelidade dos extratores bancários.

Para cada banco suportado, compara a soma das transações extraídas diretamente
de um arquivo bruto (via extrator oficial) com a soma das linhas correspondentes
no XLSX consolidado `data/output/ouroboros_2026.xlsx`.

Delta esperado: R$ 0,00 (tolerância R$ 0,02 para arredondamento).

Uso:
    python scripts/auditar_extratores.py --banco itau_cc --mes 2026-03
    python scripts/auditar_extratores.py --banco nubank_cartao --arquivo <path>
    python scripts/auditar_extratores.py --tudo
    python scripts/auditar_extratores.py --tudo --relatorio docs/auditoria.md

Veredito por linha:
    OK          delta <= R$ 0,02
    DIVERGE     delta > R$ 0,02
    SEM_DADOS   arquivo ausente ou nenhuma transação nem no bruto nem no XLSX
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable, Iterable, Optional

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.extractors.base import ExtratorBase, Transacao  # noqa: E402
from src.extractors.c6_cartao import ExtratorC6Cartao  # noqa: E402
from src.extractors.c6_cc import ExtratorC6CC  # noqa: E402
from src.extractors.itau_pdf import ExtratorItauPDF  # noqa: E402
from src.extractors.nubank_cartao import ExtratorNubankCartao  # noqa: E402
from src.extractors.nubank_cc import ExtratorNubankCC  # noqa: E402
from src.extractors.ofx_parser import ExtratorOFX  # noqa: E402
from src.extractors.santander_pdf import ExtratorSantanderPDF  # noqa: E402
from src.transform.deduplicator import (  # noqa: E402
    deduplicar_por_hash_fuzzy,
    deduplicar_por_identificador,
)

# Silencia os loggers dos extratores durante a auditoria. O que queremos ver é
# o resumo tabular no final -- não o chatter de cada arquivo processado.
logging.getLogger().setLevel(logging.WARNING)

XLSX_PADRAO = RAIZ / "data" / "output" / "ouroboros_2026.xlsx"
TOLERANCIA_REAIS = 0.02


# --------------------------------------------------------------------------- #
# Mapeamento banco -> (extrator, diretório padrão, filtro XLSX)                #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class FiltroXLSX:
    """Critério para isolar linhas do XLSX equivalentes ao extrator.

    O XLSX consolida múltiplos extratores sob a mesma coluna `banco_origem`
    (ex.: `nubank_cc` e `nubank_cartao` viram `banco_origem="Nubank"`). Para
    comparar com fidelidade, filtramos adicionalmente por `forma_pagamento`.

    `bancos_origem` aceita múltiplos rótulos porque o pipeline real pode
    consolidar variantes (ex: `Nubank (PJ)` e `Nubank`) na mesma coluna;
    nesse caso passamos ambos e verificamos presença.
    """

    bancos_origem: tuple[str, ...]
    formas_pagamento: Optional[tuple[str, ...]] = None
    quem: Optional[tuple[str, ...]] = None

    @classmethod
    def simples(
        cls,
        banco_origem: str,
        formas_pagamento: Optional[tuple[str, ...]] = None,
        quem: Optional[tuple[str, ...]] = None,
    ) -> "FiltroXLSX":
        return cls(
            bancos_origem=(banco_origem,),
            formas_pagamento=formas_pagamento,
            quem=quem,
        )

    def aplicar(self, df: pd.DataFrame) -> pd.DataFrame:
        filtrado = df[df["banco_origem"].isin(self.bancos_origem)]
        if self.formas_pagamento is not None:
            filtrado = filtrado[filtrado["forma_pagamento"].isin(self.formas_pagamento)]
        if self.quem is not None:
            filtrado = filtrado[filtrado["quem"].isin(self.quem)]
        return filtrado


@dataclass(frozen=True)
class DefinicaoBanco:
    """Metadados para auditar um banco específico.

    Campos novos Sprint 93b:
      - `aceita_ofx_complementar`: quando True, a flag global `--com-ofx`
        faz o auditor incluir tx dos arquivos `.ofx` do diretório na soma
        do extrator. Reflete o fato de que o pipeline real consome OFX
        em paralelo ao extrator canônico para esse banco.
      - `aceita_ignorar_ti`: quando True, a flag global `--ignorar-ti`
        remove do lado XLSX as linhas com `tipo=Transferência Interna`.
        Usado quando a contraparte de uma TI (ex: pagamento de fatura
        C6 via débito em CC) entra no XLSX com o mesmo `banco_origem`
        mas não provém do extrator auditado.

    Ambas as flags são opt-in por banco: bancos sem esses switches as
    ignoram, mantendo comportamento retrocompatível.
    """

    chave: str
    titulo: str
    extrator_cls: type[ExtratorBase]
    diretorio_relativo: Path
    filtro_xlsx: FiltroXLSX
    extensoes: tuple[str, ...]
    aceita_ofx_complementar: bool = False
    aceita_ignorar_ti: bool = False


BANCOS: dict[str, DefinicaoBanco] = {
    "itau_cc": DefinicaoBanco(
        chave="itau_cc",
        titulo="Itaú CC",
        extrator_cls=ExtratorItauPDF,
        diretorio_relativo=Path("data/raw/andre/itau_cc"),
        filtro_xlsx=FiltroXLSX.simples(banco_origem="Itaú"),
        extensoes=(".pdf",),
    ),
    "santander_cartao": DefinicaoBanco(
        chave="santander_cartao",
        titulo="Santander Cartão",
        extrator_cls=ExtratorSantanderPDF,
        diretorio_relativo=Path("data/raw/andre/santander_cartao"),
        filtro_xlsx=FiltroXLSX.simples(
            banco_origem="Santander",
            formas_pagamento=("Crédito",),
        ),
        extensoes=(".pdf",),
    ),
    "c6_cc": DefinicaoBanco(
        chave="c6_cc",
        titulo="C6 CC",
        extrator_cls=ExtratorC6CC,
        diretorio_relativo=Path("data/raw/andre/c6_cc"),
        filtro_xlsx=FiltroXLSX.simples(
            banco_origem="C6",
            formas_pagamento=("Débito", "Pix", "Boleto"),
        ),
        extensoes=(".xlsx",),
        aceita_ofx_complementar=True,
        aceita_ignorar_ti=True,
    ),
    "c6_cartao": DefinicaoBanco(
        chave="c6_cartao",
        titulo="C6 Cartão",
        extrator_cls=ExtratorC6Cartao,
        diretorio_relativo=Path("data/raw/andre/c6_cartao"),
        filtro_xlsx=FiltroXLSX.simples(
            banco_origem="C6",
            formas_pagamento=("Crédito",),
        ),
        extensoes=(".xls",),
        aceita_ignorar_ti=True,
    ),
    "nubank_cartao": DefinicaoBanco(
        chave="nubank_cartao",
        titulo="Nubank Cartão (André)",
        extrator_cls=ExtratorNubankCartao,
        diretorio_relativo=Path("data/raw/andre/nubank_cartao"),
        filtro_xlsx=FiltroXLSX.simples(
            banco_origem="Nubank",
            formas_pagamento=("Crédito",),
            quem=("André",),
        ),
        extensoes=(".csv",),
        aceita_ignorar_ti=True,
    ),
    "nubank_cc": DefinicaoBanco(
        chave="nubank_cc",
        titulo="Nubank CC (André)",
        extrator_cls=ExtratorNubankCC,
        diretorio_relativo=Path("data/raw/andre/nubank_cc"),
        filtro_xlsx=FiltroXLSX.simples(
            banco_origem="Nubank",
            formas_pagamento=("Débito", "Pix", "Boleto"),
            quem=("André",),
        ),
        extensoes=(".csv",),
        aceita_ofx_complementar=True,
    ),
    "nubank_pf_cc": DefinicaoBanco(
        chave="nubank_pf_cc",
        titulo="Nubank PF CC (Vitória)",
        extrator_cls=ExtratorNubankCC,
        diretorio_relativo=Path("data/raw/vitoria/nubank_pf_cc"),
        filtro_xlsx=FiltroXLSX.simples(banco_origem="Nubank (PF)"),
        extensoes=(".csv",),
    ),
    # Nubank PJ: o extrator marca `banco_origem="Nubank (PJ)"`, mas o XLSX
    # atual só tem as rotulagens `Nubank` e `Nubank (PF)`. Portanto aceitamos
    # ambas e deixamos a DIVERGÊNCIA visível quando o pipeline ainda não
    # populou o rótulo PJ.
    "nubank_pj_cc": DefinicaoBanco(
        chave="nubank_pj_cc",
        titulo="Nubank PJ CC (Vitória)",
        extrator_cls=ExtratorNubankCC,
        diretorio_relativo=Path("data/raw/vitoria/nubank_pj_cc"),
        filtro_xlsx=FiltroXLSX(
            bancos_origem=("Nubank (PJ)", "Nubank"),
            formas_pagamento=("Débito", "Pix", "Boleto", "Transferência"),
            quem=("Vitória",),
        ),
        extensoes=(".csv",),
    ),
    "nubank_pj_cartao": DefinicaoBanco(
        chave="nubank_pj_cartao",
        titulo="Nubank PJ Cartão (Vitória)",
        extrator_cls=ExtratorNubankCartao,
        diretorio_relativo=Path("data/raw/vitoria/nubank_pj_cartao"),
        filtro_xlsx=FiltroXLSX(
            bancos_origem=("Nubank (PJ)", "Nubank"),
            formas_pagamento=("Crédito",),
            quem=("Vitória",),
        ),
        extensoes=(".csv",),
    ),
}


# --------------------------------------------------------------------------- #
# Tipos do resultado                                                           #
# --------------------------------------------------------------------------- #


@dataclass
class ResultadoAuditoria:
    """Resultado de auditar um arquivo específico contra o XLSX."""

    banco: str
    mes_ref: Optional[str]
    arquivo: Optional[Path]
    total_extrator: float
    total_xlsx: float
    n_extrator: int
    n_xlsx: int
    veredito: str
    observacao: str = ""
    linhas_ausentes_no_xlsx: list[dict] = field(default_factory=list)
    linhas_fantasma_no_xlsx: list[dict] = field(default_factory=list)
    arquivos_fisicos: int = 0
    arquivos_unicos_sha: int = 0
    n_pos_dedup: int = 0
    total_pos_dedup: float = 0.0
    modo_dedup: bool = False
    n_ofx_complementar: int = 0
    total_ofx_complementar: float = 0.0
    n_xlsx_ti_ignoradas: int = 0
    total_xlsx_ti_ignoradas: float = 0.0

    @property
    def delta(self) -> float:
        return abs(self.total_extrator - self.total_xlsx)

    def formatar_linha_tabela(self) -> str:
        nome_arquivo = self.arquivo.name if self.arquivo else "-"
        mes = self.mes_ref or "-"
        return (
            f"| {self.banco} | {mes} | {nome_arquivo} "
            f"| {self.total_extrator:.2f} | {self.total_xlsx:.2f} "
            f"| {self.delta:.2f} | {self.n_extrator} | {self.n_xlsx} "
            f"| {self.veredito} |"
        )


# --------------------------------------------------------------------------- #
# Auditoria                                                                    #
# --------------------------------------------------------------------------- #


def _soma_absoluta(transacoes: Iterable[Transacao]) -> float:
    return float(sum(abs(t.valor) for t in transacoes))


def _mes_ref_da_transacao(t: Transacao) -> str:
    d: date = t.data
    return f"{d.year:04d}-{d.month:02d}"


def _sha256_arquivo(caminho: Path, bloco: int = 65536) -> str:
    """Calcula SHA-256 do conteúdo binário do arquivo."""
    h = hashlib.sha256()
    with caminho.open("rb") as fh:
        for chunk in iter(lambda: fh.read(bloco), b""):
            h.update(chunk)
    return h.hexdigest()


def _unicos_por_sha(arquivos: list[Path]) -> list[Path]:
    """Remove cópias físicas idênticas (mesmo conteúdo binário).

    Preserva a primeira ocorrência pela ordem de entrada. Sprint 93a
    mapeou que cerca de 86% dos arquivos nos diretórios bancários são
    cópias baixadas múltiplas vezes com sufixos `_1.pdf`, `_2.pdf` etc.
    O pipeline real processa o fluxo inbox → raw e o `inbox_processor`
    detecta duplicatas antes de mover; a auditoria reproduz esse
    comportamento quando roda em modo `--deduplicado`.
    """
    vistos: set[str] = set()
    resultado: list[Path] = []
    for arquivo in arquivos:
        sha = _sha256_arquivo(arquivo)
        if sha in vistos:
            continue
        vistos.add(sha)
        resultado.append(arquivo)
    return resultado


def _transacao_para_dict(t: Transacao) -> dict:
    """Converte a transação no dict esperado pelo `deduplicator`.

    Simetria com `src/transform/normalizer.py`, que também popula
    `local` a partir da descrição original antes da chamada de
    `deduplicar()`.
    """
    return {
        "data": t.data,
        "valor": t.valor,
        "local": t.descricao or "",
        "_identificador": t.identificador,
        "_descricao_original": t.descricao,
        "banco_origem": t.banco_origem,
    }


def _extrair_com_dedup_fisica(
    definicao: "DefinicaoBanco", diretorio: Path
) -> list[Transacao]:
    """Executa o extrator sobre cópias únicas por SHA-256 do diretório.

    Aplica dedup físico ANTES de instanciar o extrator para evitar
    reprocessar o mesmo arquivo 7x (padrão mais comum no diretório real).
    """
    arquivos = sorted(
        f
        for f in diretorio.iterdir()
        if f.is_file() and f.suffix.lower() in definicao.extensoes
    )
    unicos = _unicos_por_sha(arquivos)
    transacoes: list[Transacao] = []
    for arquivo in unicos:
        transacoes.extend(definicao.extrator_cls(arquivo).extrair())
    return transacoes


def _extrair_ofx_complementar(diretorio: Path) -> list[Transacao]:
    """Roda `ExtratorOFX` sobre arquivos `.ofx` únicos por SHA do diretório.

    Sprint 93b: diagnosticou que o XLSX consolidado acumula tx provenientes
    tanto do extrator canônico do banco (PDF/CSV/XLS) quanto de arquivos OFX
    baixados via Open Finance. O pipeline real processa ambos; o auditor
    precisa reproduzir esse comportamento quando a flag `--com-ofx` é usada
    para auditar fidelidade runtime-real.

    Retorna lista vazia quando o diretório não tem arquivos `.ofx` únicos.
    """
    arquivos = sorted(
        f
        for f in diretorio.iterdir()
        if f.is_file() and f.suffix.lower() == ".ofx"
    )
    unicos = _unicos_por_sha(arquivos)
    transacoes: list[Transacao] = []
    for arquivo in unicos:
        try:
            transacoes.extend(ExtratorOFX(arquivo).extrair())
        except Exception as exc:  # noqa: BLE001 -- registrar e seguir
            logging.getLogger("auditar_extratores").warning(
                "OFX complementar falhou em %s: %s", arquivo.name, exc
            )
    return transacoes


def _aplicar_dedup_pipeline(transacoes: list[Transacao]) -> list[Transacao]:
    """Replica os níveis 1 e 2 do deduplicador do pipeline principal.

    O nível 3 (`marcar_transferencias_internas`) não é aplicado aqui
    porque ele muda `tipo` para "Transferência Interna" mas não remove
    linhas; a soma absoluta do extrator ficaria igual. Manter fiel ao
    que o XLSX consolidado contém.
    """
    dicts = [_transacao_para_dict(t) for t in transacoes]
    dicts = deduplicar_por_identificador(dicts)
    dicts = deduplicar_por_hash_fuzzy(dicts)
    ids_preservados = {
        (d.get("_identificador"), d["data"], float(d["valor"]), d["local"])
        for d in dicts
    }

    resultado: list[Transacao] = []
    ja_visto: set[tuple] = set()
    for t in transacoes:
        chave = (t.identificador, t.data, float(t.valor), t.descricao or "")
        if chave in ja_visto:
            continue
        if chave in ids_preservados:
            ja_visto.add(chave)
            resultado.append(t)
    return resultado


def _carregar_xlsx(caminho: Path) -> pd.DataFrame:
    return pd.read_excel(caminho, sheet_name="extrato")


def _selecionar_arquivo_para_mes(
    definicao: DefinicaoBanco, raiz: Path, mes_ref: Optional[str]
) -> Optional[Path]:
    """Escolhe o primeiro arquivo do diretório que contém o mês, se indicado.

    Usa apenas o nome do arquivo. Se `mes_ref` é None, escolhe o primeiro arquivo
    pela ordem alfabética (representativo mas determinístico).
    """
    diretorio = raiz / definicao.diretorio_relativo
    if not diretorio.exists():
        return None

    arquivos = [
        f
        for f in sorted(diretorio.iterdir())
        if f.is_file() and f.suffix.lower() in definicao.extensoes
    ]
    if not arquivos:
        return None

    if mes_ref is None:
        return arquivos[0]

    for arquivo in arquivos:
        if mes_ref in arquivo.name:
            return arquivo
    return None


def auditar_banco(
    definicao: DefinicaoBanco,
    raiz: Path,
    mes_ref: Optional[str],
    arquivo: Optional[Path] = None,
    xlsx: Optional[Path] = None,
    carregador_xlsx: Callable[[Path], pd.DataFrame] = _carregar_xlsx,
    modo_abrangente: bool = False,
    deduplicado: bool = False,
    com_ofx: bool = False,
    ignorar_ti: bool = False,
) -> ResultadoAuditoria:
    """Audita um banco em um mês específico.

    Parâmetros:
        definicao: metadados do banco (extrator + filtro XLSX).
        raiz: raiz do repo (para resolver caminhos relativos).
        mes_ref: 'YYYY-MM'. Ignorado quando `modo_abrangente=True`.
            Quando None e `modo_abrangente=False`, usa o mês dominante
            extraído das transações.
        arquivo: caminho específico do arquivo bruto. Se None, escolhe
            heuristicamente pelo mes_ref (ou primeiro alfabético se
            mes_ref também None).
        xlsx: caminho para o XLSX consolidado.
        carregador_xlsx: injetável para testes.
        modo_abrangente: quando True, soma TODAS as tx do extrator
            (sem filtrar por mês) e filtra o XLSX pelos MESMOS meses
            cobertos pelas tx extraídas. Recomendado para arquivos que
            naturalmente abrangem múltiplos meses (faturas com lançamentos
            atrasados, CSVs acumulados).
        deduplicado: quando True e combinado com diretório completo,
            (1) deduplica cópias físicas idênticas por SHA-256 antes de
            rodar o extrator e (2) aplica os níveis 1 e 2 do deduplicador
            do pipeline (identificador + hash fuzzy data|valor|local).
            Reproduz o que o `pipeline.py` real faz -- Sprint 93a.
        com_ofx: quando True (Sprint 93b), complementa a extração do banco
            com as transações de quaisquer arquivos `.ofx` únicos por SHA
            existentes no mesmo diretório. Reproduz o fato de que o
            pipeline real consome tanto PDF/CSV/XLS como OFX via
            `src/extractors/ofx_parser.py`. Útil para bancos cujo XLSX
            consolidado acumula tx de múltiplas fontes (notadamente c6_cc
            com 1784 tx em OFX de 2022-2026 contra 285 no .xlsx canônico).
        ignorar_ti: quando True (Sprint 93b), remove do lado XLSX as linhas
            com `tipo=Transferência Interna`. Útil para c6_cartao onde a
            contraparte de pagamento de fatura entra no XLSX como
            `banco_origem=C6 + forma_pagamento=Crédito + tipo=TI`, mas
            não provém do extrator de cartão.
    """
    diretorio_alvo = raiz / definicao.diretorio_relativo
    usar_diretorio_completo = arquivo is None and mes_ref is None and modo_abrangente

    arquivos_fisicos = 0
    arquivos_unicos_sha = 0

    if usar_diretorio_completo:
        if not diretorio_alvo.exists():
            return ResultadoAuditoria(
                banco=definicao.chave,
                mes_ref=None,
                arquivo=None,
                total_extrator=0.0,
                total_xlsx=0.0,
                n_extrator=0,
                n_xlsx=0,
                veredito="SEM_DADOS",
                observacao=f"diretório ausente: {diretorio_alvo}",
                modo_dedup=deduplicado,
            )
        if deduplicado:
            arquivos_fisicos = sum(
                1
                for f in diretorio_alvo.iterdir()
                if f.is_file() and f.suffix.lower() in definicao.extensoes
            )
            transacoes = _extrair_com_dedup_fisica(definicao, diretorio_alvo)
            # Contagem de únicos: o helper já rodou sha; re-uso a lista
            arquivos_ordenados = sorted(
                f
                for f in diretorio_alvo.iterdir()
                if f.is_file() and f.suffix.lower() in definicao.extensoes
            )
            arquivos_unicos_sha = len(_unicos_por_sha(arquivos_ordenados))
        else:
            extrator = definicao.extrator_cls(diretorio_alvo)
            transacoes = extrator.extrair()
        arquivo_escolhido = diretorio_alvo
    else:
        arquivo_escolhido = arquivo or _selecionar_arquivo_para_mes(
            definicao, raiz, mes_ref
        )
        if arquivo_escolhido is None or not arquivo_escolhido.exists():
            return ResultadoAuditoria(
                banco=definicao.chave,
                mes_ref=mes_ref,
                arquivo=arquivo_escolhido,
                total_extrator=0.0,
                total_xlsx=0.0,
                n_extrator=0,
                n_xlsx=0,
                veredito="SEM_DADOS",
                observacao="arquivo bruto não encontrado",
                modo_dedup=deduplicado,
            )
        extrator = definicao.extrator_cls(arquivo_escolhido)
        transacoes = extrator.extrair()

    # Sprint 93b: complementa com OFX do mesmo diretório quando solicitado.
    # Só faz sentido em modo diretório completo e para bancos que o
    # aceitam explicitamente via `DefinicaoBanco.aceita_ofx_complementar`.
    # Em modo arquivo único o usuário indicou um arquivo específico e
    # não queremos injetar OFX silenciosamente.
    n_ofx_complementar = 0
    total_ofx_complementar = 0.0
    if (
        com_ofx
        and usar_diretorio_completo
        and definicao.aceita_ofx_complementar
    ):
        tx_ofx = _extrair_ofx_complementar(diretorio_alvo)
        n_ofx_complementar = len(tx_ofx)
        total_ofx_complementar = _soma_absoluta(tx_ofx)
        transacoes = transacoes + tx_ofx

    total_extrator = _soma_absoluta(transacoes)
    n_extrator = len(transacoes)

    # Aplica dedup nível 1 e 2 do pipeline se solicitado.
    n_pos_dedup = n_extrator
    total_pos_dedup = total_extrator
    if deduplicado and transacoes:
        transacoes_dedup = _aplicar_dedup_pipeline(transacoes)
        n_pos_dedup = len(transacoes_dedup)
        total_pos_dedup = _soma_absoluta(transacoes_dedup)
        # Usa o conjunto deduplicado como referência para comparar com XLSX.
        total_extrator = total_pos_dedup
        n_extrator = n_pos_dedup
        transacoes = transacoes_dedup

    meses_cobertos = sorted({_mes_ref_da_transacao(t) for t in transacoes})

    # Quando mes_ref não foi fornecido e não estamos em modo abrangente,
    # usa o mês dominante das transações como filtro do XLSX.
    if mes_ref is None and transacoes and not modo_abrangente:
        meses_todos = [_mes_ref_da_transacao(t) for t in transacoes]
        mes_ref = max(set(meses_todos), key=meses_todos.count)

    caminho_xlsx = xlsx or (raiz / "data" / "output" / "ouroboros_2026.xlsx")
    if not caminho_xlsx.exists():
        return ResultadoAuditoria(
            banco=definicao.chave,
            mes_ref=mes_ref,
            arquivo=arquivo_escolhido,
            total_extrator=total_extrator,
            total_xlsx=0.0,
            n_extrator=n_extrator,
            n_xlsx=0,
            veredito="SEM_DADOS",
            observacao=f"xlsx ausente: {caminho_xlsx}",
        )

    df = carregador_xlsx(caminho_xlsx)
    df_banco = definicao.filtro_xlsx.aplicar(df)
    if modo_abrangente and meses_cobertos:
        df_filtro = df_banco[df_banco["mes_ref"].isin(meses_cobertos)]
    elif mes_ref is not None:
        df_filtro = df_banco[df_banco["mes_ref"] == mes_ref]
    else:
        df_filtro = df_banco.iloc[0:0]

    # Sprint 93b: flag `--ignorar-ti` remove contrapartes de transferência
    # interna do lado XLSX (ex: pagamento de fatura C6 aparece como
    # `banco_origem=C6 + forma=Crédito + tipo=TI`, mas não sai do extrator
    # de cartão). Opt-in por banco via `DefinicaoBanco.aceita_ignorar_ti`.
    # Aplicado APÓS o filtro de meses para instrumentar o que foi removido.
    n_xlsx_ti_ignoradas = 0
    total_xlsx_ti_ignoradas = 0.0
    if (
        ignorar_ti
        and definicao.aceita_ignorar_ti
        and "tipo" in df_filtro.columns
    ):
        df_ti = df_filtro[df_filtro["tipo"] == "Transferência Interna"]
        n_xlsx_ti_ignoradas = len(df_ti)
        total_xlsx_ti_ignoradas = float(df_ti["valor"].abs().sum())
        df_filtro = df_filtro[df_filtro["tipo"] != "Transferência Interna"]

    total_xlsx = float(df_filtro["valor"].abs().sum())
    n_xlsx = len(df_filtro)

    if n_extrator == 0 and n_xlsx == 0:
        return ResultadoAuditoria(
            banco=definicao.chave,
            mes_ref=mes_ref,
            arquivo=arquivo_escolhido,
            total_extrator=0.0,
            total_xlsx=0.0,
            n_extrator=0,
            n_xlsx=0,
            veredito="SEM_DADOS",
            observacao="nem extrator nem xlsx trouxeram linhas",
        )

    delta = abs(total_extrator - total_xlsx)
    veredito = "OK" if delta <= TOLERANCIA_REAIS else "DIVERGE"

    observacao = ""
    mes_label = mes_ref
    if modo_abrangente and meses_cobertos:
        mes_label = (
            f"{meses_cobertos[0]}..{meses_cobertos[-1]}"
            if len(meses_cobertos) > 1
            else meses_cobertos[0]
        )
        observacao = f"meses cobertos: {', '.join(meses_cobertos)}"

    if deduplicado and arquivos_fisicos:
        obs_dedup = (
            f"arquivos físicos: {arquivos_fisicos}; "
            f"SHA únicos: {arquivos_unicos_sha}; "
            f"duplicatas removidas: {arquivos_fisicos - arquivos_unicos_sha}"
        )
        observacao = f"{observacao}; {obs_dedup}" if observacao else obs_dedup

    if com_ofx and n_ofx_complementar:
        obs_ofx = (
            f"OFX complementar: +{n_ofx_complementar} tx "
            f"(R$ {total_ofx_complementar:,.2f})"
        )
        observacao = f"{observacao}; {obs_ofx}" if observacao else obs_ofx

    if ignorar_ti and n_xlsx_ti_ignoradas:
        obs_ti = (
            f"TI ignoradas no XLSX: -{n_xlsx_ti_ignoradas} tx "
            f"(R$ {total_xlsx_ti_ignoradas:,.2f})"
        )
        observacao = f"{observacao}; {obs_ti}" if observacao else obs_ti

    return ResultadoAuditoria(
        banco=definicao.chave,
        mes_ref=mes_label,
        arquivo=arquivo_escolhido,
        total_extrator=total_extrator,
        total_xlsx=total_xlsx,
        n_extrator=n_extrator,
        n_xlsx=n_xlsx,
        veredito=veredito,
        observacao=observacao,
        arquivos_fisicos=arquivos_fisicos,
        arquivos_unicos_sha=arquivos_unicos_sha,
        n_pos_dedup=n_pos_dedup,
        total_pos_dedup=total_pos_dedup,
        modo_dedup=deduplicado,
        n_ofx_complementar=n_ofx_complementar,
        total_ofx_complementar=total_ofx_complementar,
        n_xlsx_ti_ignoradas=n_xlsx_ti_ignoradas,
        total_xlsx_ti_ignoradas=total_xlsx_ti_ignoradas,
    )


# --------------------------------------------------------------------------- #
# Relatório                                                                    #
# --------------------------------------------------------------------------- #

CABECALHO_TABELA = (
    "| Banco | Mês | Arquivo | Tot extrator | Tot XLSX | Delta | N_ex | N_xlsx | Veredito |\n"
    "|---|---|---|---:|---:|---:|---:|---:|---|"
)


def gerar_relatorio(
    resultados: list[ResultadoAuditoria], data_execucao: Optional[date] = None
) -> str:
    """Gera relatório Markdown consolidado."""
    data_execucao = data_execucao or date.today()
    linhas = [
        f"# Auditoria de fidelidade dos extratores -- {data_execucao.isoformat()}",
        "",
        "Script: `scripts/auditar_extratores.py`",
        "Tolerância: R$ 0,02 (arredondamento).",
        "",
        "## Resumo",
        "",
        CABECALHO_TABELA,
    ]
    for r in resultados:
        linhas.append(r.formatar_linha_tabela())

    linhas.extend(["", "## Veredictos", ""])
    oks = [r for r in resultados if r.veredito == "OK"]
    diverges = [r for r in resultados if r.veredito == "DIVERGE"]
    sem_dados = [r for r in resultados if r.veredito == "SEM_DADOS"]
    linhas.append(f"- OK: {len(oks)} / {len(resultados)}")
    linhas.append(f"- DIVERGE: {len(diverges)}")
    linhas.append(f"- SEM_DADOS: {len(sem_dados)}")

    if diverges:
        linhas.extend(["", "## Divergências detectadas", ""])
        for r in diverges:
            linhas.append(
                f"### {r.banco} {r.mes_ref} -- delta R$ {r.delta:.2f}"
            )
            linhas.append(
                f"- Total extrator: R$ {r.total_extrator:.2f} ({r.n_extrator} tx)"
            )
            linhas.append(
                f"- Total XLSX: R$ {r.total_xlsx:.2f} ({r.n_xlsx} tx)"
            )
            linhas.append(f"- Arquivo: `{r.arquivo}`")
            linhas.append("- Sprint-filha sugerida: `sprint_93a_<banco>.md`")
            linhas.append("")

    if sem_dados:
        linhas.extend(["", "## Sem dados (auditoria pulada)", ""])
        for r in sem_dados:
            linhas.append(
                f"- {r.banco} {r.mes_ref or '-'}: {r.observacao}"
            )

    linhas.extend(
        [
            "",
            "---",
            "",
            "*\"Teste automatizado prova que o código não quebra; "
            "auditoria prova que o código faz o que deveria.\" "
            "-- princípio de fidelidade*",
            "",
        ]
    )
    return "\n".join(linhas)


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


def _candidatos_padrao() -> list[tuple[str, Optional[str]]]:
    """Lista (banco, mes_ref) representativa para --tudo.

    mes_ref=None em todos os bancos: o script escolhe o primeiro arquivo
    alfabeticamente de cada diretório e infere o mês dominante a partir das
    transações. Evita a frágil suposição de que o nome do arquivo reflete o
    mês das transações (armadilha detectada na primeira rodada: faturas
    batizadas `2026-01` continham lançamentos de `2026-02`/`2026-03`).
    """
    return [
        ("itau_cc", None),
        ("santander_cartao", None),
        ("c6_cc", None),
        ("c6_cartao", None),
        ("nubank_cartao", None),
        ("nubank_cc", None),
        ("nubank_pf_cc", None),
        ("nubank_pj_cc", None),
        ("nubank_pj_cartao", None),
    ]


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Audita fidelidade dos extratores contra o XLSX consolidado.",
    )
    p.add_argument(
        "--banco",
        choices=list(BANCOS.keys()),
        help="Chave do banco a auditar.",
    )
    p.add_argument(
        "--mes",
        help="Mes de referencia YYYY-MM (ex: 2026-03).",
    )
    p.add_argument(
        "--arquivo",
        type=Path,
        help="Caminho especifico do arquivo bruto. Se omitido, escolhe pela heuristica.",
    )
    p.add_argument(
        "--tudo",
        action="store_true",
        help="Audita os 9 bancos em candidatos representativos.",
    )
    p.add_argument(
        "--xlsx",
        type=Path,
        default=XLSX_PADRAO,
        help=f"Caminho do XLSX consolidado (default: {XLSX_PADRAO.relative_to(RAIZ)}).",
    )
    p.add_argument(
        "--relatorio",
        type=Path,
        help="Grava relatório Markdown no caminho indicado (opcional).",
    )
    p.add_argument(
        "--modo-abrangente",
        action="store_true",
        dest="modo_abrangente",
        help=(
            "Soma TODAS as tx do extrator e filtra o XLSX pelos MESMOS meses "
            "cobertos pelas tx. Recomendado para faturas/CSVs que abrangem "
            "múltiplos meses (comportamento real, não suposição de nome)."
        ),
    )
    p.add_argument(
        "--deduplicado",
        action="store_true",
        dest="deduplicado",
        help=(
            "Reproduz o deduplicador do pipeline antes de comparar: "
            "(1) descarta cópias físicas idênticas por SHA-256 do arquivo "
            "(padrão Sprint 93a: ~86%% dos arquivos nos diretórios são "
            "cópias baixadas múltiplas vezes); (2) aplica níveis 1 e 2 do "
            "`src/transform/deduplicator.py` (identificador + hash fuzzy "
            "data|valor|local). Recomendado com `--modo-abrangente` e "
            "`--tudo` para audit pós-pipeline fiel."
        ),
    )
    p.add_argument(
        "--com-ofx",
        action="store_true",
        dest="com_ofx",
        help=(
            "Sprint 93b: complementa a extração do banco com as tx dos "
            "arquivos `.ofx` únicos por SHA presentes no mesmo diretório. "
            "Reproduz o fato de que o pipeline real consome tanto o "
            "extrator canônico do banco quanto `src/extractors/ofx_parser.py`. "
            "Essencial para c6_cc (OFX 2022-2026 com 1784 tx vs 285 no .xlsx) "
            "e nubank_cc (múltiplos OFX cobrindo anos de histórico)."
        ),
    )
    p.add_argument(
        "--ignorar-ti",
        action="store_true",
        dest="ignorar_ti",
        help=(
            "Sprint 93b: remove do lado XLSX as linhas com "
            "`tipo=Transferência Interna`. Usado quando a contraparte de "
            "um pagamento (ex: fatura de cartão C6 feita via débito em CC) "
            "é marcada no XLSX como parte do mesmo banco_origem mas não "
            "emerge do extrator canônico auditado. Aplica-se apenas ao "
            "lado XLSX da comparação."
        ),
    )
    return p.parse_args(argv)


def _imprimir_tabela(resultados: list[ResultadoAuditoria]) -> None:
    print(CABECALHO_TABELA)
    for r in resultados:
        print(r.formatar_linha_tabela())


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)

    if args.tudo and (args.banco or args.arquivo):
        print("[AUDIT] --tudo não combina com --banco/--arquivo", file=sys.stderr)
        return 2
    if not args.tudo and not args.banco:
        print("[AUDIT] informe --banco <nome> ou --tudo", file=sys.stderr)
        return 2

    candidatos: list[tuple[str, Optional[str], Optional[Path]]]
    if args.tudo:
        candidatos = [(b, m, None) for b, m in _candidatos_padrao()]
    else:
        candidatos = [(args.banco, args.mes, args.arquivo)]

    resultados: list[ResultadoAuditoria] = []
    for banco, mes, arquivo in candidatos:
        definicao = BANCOS[banco]
        resultado = auditar_banco(
            definicao=definicao,
            raiz=RAIZ,
            mes_ref=mes,
            arquivo=arquivo,
            xlsx=args.xlsx,
            modo_abrangente=args.modo_abrangente,
            deduplicado=args.deduplicado,
            com_ofx=args.com_ofx,
            ignorar_ti=args.ignorar_ti,
        )
        resultados.append(resultado)

    _imprimir_tabela(resultados)

    if args.relatorio:
        conteudo = gerar_relatorio(resultados)
        args.relatorio.parent.mkdir(parents=True, exist_ok=True)
        args.relatorio.write_text(conteudo, encoding="utf-8")
        print(f"\n[AUDIT] relatório gravado em {args.relatorio}")

    n_diverge = sum(1 for r in resultados if r.veredito == "DIVERGE")
    return 0 if n_diverge == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


# "Teste automatizado prova que o código não quebra;
#  auditoria prova que o código faz o que deveria." -- princípio de fidelidade
