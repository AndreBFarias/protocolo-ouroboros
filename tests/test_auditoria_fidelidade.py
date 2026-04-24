"""Testes do script de auditoria de fidelidade dos extratores.

Cobrem: FiltroXLSX, geração de relatório, seleção de arquivo por mês e a
função `auditar_banco` com extrator e loader injetáveis. Não consomem dados
reais de `data/raw/`.

Testes `@pytest.mark.slow` são opcionais: se os dados reais em `data/raw/`
existirem, rodam auditoria contra ao menos um banco. Fora desse caso, pulam.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from scripts.auditar_extratores import (
    BANCOS,
    DefinicaoBanco,
    FiltroXLSX,
    ResultadoAuditoria,
    _selecionar_arquivo_para_mes,
    auditar_banco,
    gerar_relatorio,
    main,
)
from src.extractors.base import ExtratorBase, Transacao

# --------------------------------------------------------------------------- #
# Extrator sintético                                                           #
# --------------------------------------------------------------------------- #


class _ExtratorFake(ExtratorBase):
    """Extrator fake: retorna a lista pré-definida de transações."""

    TRANSACOES: list[Transacao] = []

    def __init__(self, caminho: Path) -> None:  # noqa: D401 - concreto
        super().__init__(caminho)

    def pode_processar(self, caminho: Path) -> bool:  # pragma: no cover
        return True

    def extrair(self) -> list[Transacao]:
        return list(self.TRANSACOES)


def _mk_tx(valor: float, d: date = date(2026, 3, 10)) -> Transacao:
    return Transacao(
        data=d,
        valor=valor,
        descricao="tx sintetica",
        banco_origem="Itaú",
        pessoa="André",
        forma_pagamento="Débito",
        tipo="Despesa",
    )


# --------------------------------------------------------------------------- #
# FiltroXLSX                                                                   #
# --------------------------------------------------------------------------- #


def _df_fake() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "banco_origem": "Itaú",
                "forma_pagamento": "Débito",
                "quem": "André",
                "mes_ref": "2026-03",
                "valor": 100.0,
            },
            {
                "banco_origem": "Itaú",
                "forma_pagamento": "Pix",
                "quem": "André",
                "mes_ref": "2026-03",
                "valor": 50.0,
            },
            {
                "banco_origem": "Santander",
                "forma_pagamento": "Crédito",
                "quem": "André",
                "mes_ref": "2026-03",
                "valor": 70.0,
            },
            {
                "banco_origem": "Nubank",
                "forma_pagamento": "Crédito",
                "quem": "Vitória",
                "mes_ref": "2026-03",
                "valor": 30.0,
            },
            {
                "banco_origem": "Nubank",
                "forma_pagamento": "Crédito",
                "quem": "André",
                "mes_ref": "2026-03",
                "valor": 200.0,
            },
        ]
    )


def test_filtro_xlsx_banco_somente() -> None:
    filtro = FiltroXLSX.simples(banco_origem="Itaú")
    df = filtro.aplicar(_df_fake())
    assert len(df) == 2
    assert df["valor"].sum() == 150.0


def test_filtro_xlsx_com_forma_pagamento() -> None:
    filtro = FiltroXLSX.simples(
        banco_origem="Itaú", formas_pagamento=("Débito",)
    )
    df = filtro.aplicar(_df_fake())
    assert len(df) == 1
    assert df.iloc[0]["valor"] == 100.0


def test_filtro_xlsx_separa_cartao_nubank_por_quem() -> None:
    filtro = FiltroXLSX.simples(
        banco_origem="Nubank",
        formas_pagamento=("Crédito",),
        quem=("André",),
    )
    df = filtro.aplicar(_df_fake())
    assert len(df) == 1
    assert df.iloc[0]["valor"] == 200.0


def test_filtro_xlsx_multiplos_bancos_aceitos() -> None:
    """Aceita múltiplos rótulos para o mesmo extrator (ex: Nubank (PJ) + Nubank)."""
    filtro = FiltroXLSX(
        bancos_origem=("Nubank (PJ)", "Nubank"),
        quem=("Vitória",),
    )
    df = filtro.aplicar(_df_fake())
    # Só a linha Vitória+Nubank entra (Nubank (PJ) não existe no fake).
    assert len(df) == 1
    assert df.iloc[0]["valor"] == 30.0


# --------------------------------------------------------------------------- #
# _selecionar_arquivo_para_mes                                                 #
# --------------------------------------------------------------------------- #


def test_selecionar_arquivo_por_mes(tmp_path: Path) -> None:
    diretorio = tmp_path / "data" / "raw" / "andre" / "itau_cc"
    diretorio.mkdir(parents=True)
    (diretorio / "ITAU_2026-02_abc.pdf").write_bytes(b"")
    arquivo_alvo = diretorio / "ITAU_2026-03_abc.pdf"
    arquivo_alvo.write_bytes(b"")

    definicao = BANCOS["itau_cc"]
    escolhido = _selecionar_arquivo_para_mes(definicao, tmp_path, "2026-03")
    assert escolhido == arquivo_alvo


def test_selecionar_arquivo_sem_match(tmp_path: Path) -> None:
    diretorio = tmp_path / "data" / "raw" / "andre" / "itau_cc"
    diretorio.mkdir(parents=True)
    (diretorio / "ITAU_2026-02_abc.pdf").write_bytes(b"")
    definicao = BANCOS["itau_cc"]
    assert (
        _selecionar_arquivo_para_mes(definicao, tmp_path, "2026-12")
        is None
    )


def test_selecionar_arquivo_sem_mes_retorna_primeiro(tmp_path: Path) -> None:
    diretorio = tmp_path / "data" / "raw" / "andre" / "itau_cc"
    diretorio.mkdir(parents=True)
    (diretorio / "ITAU_2026-01.pdf").write_bytes(b"")
    (diretorio / "ITAU_2026-02.pdf").write_bytes(b"")
    definicao = BANCOS["itau_cc"]
    escolhido = _selecionar_arquivo_para_mes(definicao, tmp_path, None)
    assert escolhido is not None
    assert escolhido.name == "ITAU_2026-01.pdf"


# --------------------------------------------------------------------------- #
# auditar_banco                                                                #
# --------------------------------------------------------------------------- #


def _definicao_fake(tmp_raiz: Path) -> DefinicaoBanco:
    diretorio = tmp_raiz / "data" / "raw" / "andre" / "itau_cc"
    diretorio.mkdir(parents=True, exist_ok=True)
    (diretorio / "ITAU_2026-03.pdf").write_bytes(b"")
    return DefinicaoBanco(
        chave="itau_cc",
        titulo="Itaú CC (fake)",
        extrator_cls=_ExtratorFake,
        diretorio_relativo=Path("data/raw/andre/itau_cc"),
        filtro_xlsx=FiltroXLSX.simples(banco_origem="Itaú"),
        extensoes=(".pdf",),
    )


def test_auditar_banco_delta_zero(tmp_path: Path) -> None:
    definicao = _definicao_fake(tmp_path)
    _ExtratorFake.TRANSACOES = [
        _mk_tx(100.0),
        _mk_tx(50.0),
    ]
    df = _df_fake()

    def carregador(_: Path) -> pd.DataFrame:
        return df

    # Força existência do "xlsx" (necessário para não cair em SEM_DADOS)
    (tmp_path / "xlsx_ficticio.xlsx").write_bytes(b"")
    resultado = auditar_banco(
        definicao=definicao,
        raiz=tmp_path,
        mes_ref="2026-03",
        xlsx=tmp_path / "xlsx_ficticio.xlsx",
        carregador_xlsx=carregador,
    )

    assert resultado.veredito == "OK"
    assert resultado.delta <= 0.02
    assert resultado.n_extrator == 2
    assert resultado.n_xlsx == 2
    assert resultado.total_extrator == pytest.approx(150.0)
    assert resultado.total_xlsx == pytest.approx(150.0)


def test_auditar_banco_delta_acima_tolerancia(tmp_path: Path) -> None:
    definicao = _definicao_fake(tmp_path)
    _ExtratorFake.TRANSACOES = [_mk_tx(100.0)]
    df = _df_fake()
    (tmp_path / "xlsx_ficticio.xlsx").write_bytes(b"")
    resultado = auditar_banco(
        definicao=definicao,
        raiz=tmp_path,
        mes_ref="2026-03",
        xlsx=tmp_path / "xlsx_ficticio.xlsx",
        carregador_xlsx=lambda _: df,
    )
    assert resultado.veredito == "DIVERGE"
    assert resultado.delta > 0.02
    assert resultado.n_extrator == 1
    assert resultado.n_xlsx == 2


def test_auditar_banco_sem_dados_arquivo_ausente(tmp_path: Path) -> None:
    # Diretório existe mas está vazio.
    (tmp_path / "data" / "raw" / "andre" / "itau_cc").mkdir(parents=True)
    definicao = DefinicaoBanco(
        chave="itau_cc",
        titulo="Itaú CC",
        extrator_cls=_ExtratorFake,
        diretorio_relativo=Path("data/raw/andre/itau_cc"),
        filtro_xlsx=FiltroXLSX.simples(banco_origem="Itaú"),
        extensoes=(".pdf",),
    )
    resultado = auditar_banco(
        definicao=definicao,
        raiz=tmp_path,
        mes_ref="2026-03",
    )
    assert resultado.veredito == "SEM_DADOS"
    assert "não encontrado" in resultado.observacao


def test_auditar_banco_extrai_mes_dominante_quando_mes_none(
    tmp_path: Path,
) -> None:
    definicao = _definicao_fake(tmp_path)
    _ExtratorFake.TRANSACOES = [
        _mk_tx(100.0, date(2026, 3, 10)),
        _mk_tx(50.0, date(2026, 3, 20)),
        _mk_tx(10.0, date(2026, 2, 15)),
    ]
    df = _df_fake()
    (tmp_path / "xlsx_ficticio.xlsx").write_bytes(b"")
    resultado = auditar_banco(
        definicao=definicao,
        raiz=tmp_path,
        mes_ref=None,
        xlsx=tmp_path / "xlsx_ficticio.xlsx",
        carregador_xlsx=lambda _: df,
    )
    assert resultado.mes_ref == "2026-03"


# --------------------------------------------------------------------------- #
# Relatório                                                                    #
# --------------------------------------------------------------------------- #


def test_gerar_relatorio_contem_tabela_e_veredito() -> None:
    resultados = [
        ResultadoAuditoria(
            banco="itau_cc",
            mes_ref="2026-03",
            arquivo=Path("fatura_202603.pdf"),
            total_extrator=150.0,
            total_xlsx=150.0,
            n_extrator=2,
            n_xlsx=2,
            veredito="OK",
        ),
        ResultadoAuditoria(
            banco="santander_cartao",
            mes_ref="2026-01",
            arquivo=Path("santander_202601.pdf"),
            total_extrator=320.0,
            total_xlsx=321.27,
            n_extrator=10,
            n_xlsx=11,
            veredito="DIVERGE",
        ),
    ]
    texto = gerar_relatorio(resultados, data_execucao=date(2026, 4, 23))
    assert "Auditoria de fidelidade dos extratores -- 2026-04-23" in texto
    assert "| itau_cc | 2026-03 | fatura_202603.pdf" in texto
    assert "OK |" in texto
    assert "DIVERGE |" in texto
    assert "Divergências detectadas" in texto
    assert "santander_cartao 2026-01" in texto
    assert "sprint_93a_<banco>.md" in texto


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #


def test_cli_exige_banco_ou_tudo(capsys) -> None:
    rc = main([])
    assert rc == 2


def test_cli_banco_e_tudo_conflitam(capsys) -> None:
    rc = main(["--tudo", "--banco", "itau_cc"])
    assert rc == 2


def test_cli_chaves_de_banco_incluem_9_extratores() -> None:
    # O menu de --banco deve conter os 9 bancos acordados na spec.
    esperados = {
        "itau_cc",
        "santander_cartao",
        "c6_cc",
        "c6_cartao",
        "nubank_cartao",
        "nubank_cc",
        "nubank_pf_cc",
        "nubank_pj_cc",
        "nubank_pj_cartao",
    }
    assert esperados.issubset(set(BANCOS.keys()))


# --------------------------------------------------------------------------- #
# Runtime real (slow)                                                          #
# --------------------------------------------------------------------------- #


@pytest.mark.slow
def test_auditar_banco_real_nubank_cartao_mes_dominante() -> None:
    """Executa auditoria real contra o XLSX quando dados disponíveis.

    Usa mes_ref=None e confia no mês dominante das transações extraídas. Isso
    evita depender de uma convenção frágil de nome-de-arquivo que varia entre
    bancos. Se os dados reais não existirem, o teste é pulado.
    """
    raiz = Path(__file__).resolve().parent.parent
    xlsx = raiz / "data" / "output" / "ouroboros_2026.xlsx"
    diretorio = raiz / "data" / "raw" / "andre" / "nubank_cartao"
    if not xlsx.exists() or not diretorio.exists():
        pytest.skip("dados reais ausentes; auditoria real não executada")
    definicao = BANCOS["nubank_cartao"]
    resultado = auditar_banco(
        definicao=definicao, raiz=raiz, mes_ref=None, xlsx=xlsx
    )
    # Vereditos aceitaveis: OK ou DIVERGE. Nunca SEM_DADOS nesse cenario.
    assert resultado.veredito in {"OK", "DIVERGE"}, resultado.observacao
    assert resultado.n_extrator > 0


# "Evidência é o único juiz.
#  Teste unitário prova que o código não quebra;
#  auditoria prova que o código faz o que deveria." -- princípio de fidelidade
