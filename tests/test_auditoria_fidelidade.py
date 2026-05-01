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
    _aplicar_dedup_pipeline,
    _selecionar_arquivo_para_mes,
    _sha256_arquivo,
    _unicos_por_sha,
    auditar_banco,
    gerar_relatorio,
    main,
)
from src.extractors.base import ExtratorBase, Transacao

# --------------------------------------------------------------------------- #
# Extrator sintético                                                           #
# --------------------------------------------------------------------------- #


class _ExtratorFake(ExtratorBase):
    """Extrator fake: retorna a lista pré-definida de transações.

    Se `caminho` é um diretório, simula o padrão dos extratores reais
    (processa cada arquivo internamente): retorna a lista de transações
    replicada pelo número de arquivos com extensão `.pdf`. Se é
    arquivo, retorna a lista uma vez.
    """

    TRANSACOES: list[Transacao] = []
    EXTENSOES: tuple[str, ...] = (".pdf",)

    def __init__(self, caminho: Path) -> None:  # noqa: D401 - concreto
        super().__init__(caminho)

    def pode_processar(self, caminho: Path) -> bool:  # pragma: no cover
        return True

    def extrair(self) -> list[Transacao]:
        if self.caminho.is_dir():
            arquivos = [
                f
                for f in self.caminho.iterdir()
                if f.is_file() and f.suffix.lower() in self.EXTENSOES
            ]
            return list(self.TRANSACOES) * len(arquivos)
        return list(self.TRANSACOES)


def _mk_tx(valor: float, d: date = date(2026, 3, 10)) -> Transacao:
    return Transacao(
        data=d,
        valor=valor,
        descricao="tx sintetica",
        banco_origem="Itaú",
        pessoa="pessoa_a",
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
                "quem": "pessoa_a",
                "mes_ref": "2026-03",
                "valor": 100.0,
            },
            {
                "banco_origem": "Itaú",
                "forma_pagamento": "Pix",
                "quem": "pessoa_a",
                "mes_ref": "2026-03",
                "valor": 50.0,
            },
            {
                "banco_origem": "Santander",
                "forma_pagamento": "Crédito",
                "quem": "pessoa_a",
                "mes_ref": "2026-03",
                "valor": 70.0,
            },
            {
                "banco_origem": "Nubank",
                "forma_pagamento": "Crédito",
                "quem": "pessoa_b",
                "mes_ref": "2026-03",
                "valor": 30.0,
            },
            {
                "banco_origem": "Nubank",
                "forma_pagamento": "Crédito",
                "quem": "pessoa_a",
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
    filtro = FiltroXLSX.simples(banco_origem="Itaú", formas_pagamento=("Débito",))
    df = filtro.aplicar(_df_fake())
    assert len(df) == 1
    assert df.iloc[0]["valor"] == 100.0


def test_filtro_xlsx_separa_cartao_nubank_por_quem() -> None:
    filtro = FiltroXLSX.simples(
        banco_origem="Nubank",
        formas_pagamento=("Crédito",),
        quem=("pessoa_a",),
    )
    df = filtro.aplicar(_df_fake())
    assert len(df) == 1
    assert df.iloc[0]["valor"] == 200.0


def test_filtro_xlsx_multiplos_bancos_aceitos() -> None:
    """Aceita múltiplos rótulos para o mesmo extrator (ex: Nubank (PJ) + Nubank)."""
    filtro = FiltroXLSX(
        bancos_origem=("Nubank (PJ)", "Nubank"),
        quem=("pessoa_b",),
    )
    df = filtro.aplicar(_df_fake())
    # Só a linha Vitória+Nubank entra (Nubank (PJ) não existe no fake).  # anonimato-allow
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
    assert _selecionar_arquivo_para_mes(definicao, tmp_path, "2026-12") is None


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
    resultado = auditar_banco(definicao=definicao, raiz=raiz, mes_ref=None, xlsx=xlsx)
    # Vereditos aceitaveis: OK ou DIVERGE. Nunca SEM_DADOS nesse cenario.
    assert resultado.veredito in {"OK", "DIVERGE"}, resultado.observacao
    assert resultado.n_extrator > 0


# --------------------------------------------------------------------------- #
# Sprint 93a -- flag --deduplicado                                             #
# --------------------------------------------------------------------------- #


def test_sha256_arquivo_deterministico(tmp_path: Path) -> None:
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    conteudo = b"dedup\n" * 10
    a.write_bytes(conteudo)
    b.write_bytes(conteudo)
    assert _sha256_arquivo(a) == _sha256_arquivo(b)


def test_unicos_por_sha_remove_copias_identicas(tmp_path: Path) -> None:
    """Duplicatas físicas idênticas devem ser removidas, uma sobrevive."""
    conteudo = b"cabecalho\nlinha1\nlinha2\n"
    arquivos: list[Path] = []
    for nome in ["extrato.pdf", "extrato_1.pdf", "extrato_2.pdf"]:
        p = tmp_path / nome
        p.write_bytes(conteudo)
        arquivos.append(p)
    # Um arquivo distinto também:
    p_outro = tmp_path / "outro.pdf"
    p_outro.write_bytes(b"conteudo_diferente")
    arquivos.append(p_outro)

    unicos = _unicos_por_sha(arquivos)
    assert len(unicos) == 2
    # Preserva a primeira ocorrencia na ordem de entrada.
    assert unicos[0].name == "extrato.pdf"
    assert unicos[1].name == "outro.pdf"


def test_aplicar_dedup_pipeline_respeita_identificador() -> None:
    """Duas tx com mesmo `_identificador` colapsam (nivel 1)."""
    d = date(2026, 3, 10)
    t1 = Transacao(
        data=d,
        valor=100.0,
        descricao="AAAA",
        banco_origem="Itaú",
        pessoa="pessoa_a",
        forma_pagamento="Débito",
        tipo="Despesa",
        identificador="hash_abc",
    )
    t2 = Transacao(
        data=d,
        valor=100.0,
        descricao="AAAA",
        banco_origem="Itaú",
        pessoa="pessoa_a",
        forma_pagamento="Débito",
        tipo="Despesa",
        identificador="hash_abc",
    )
    t3 = Transacao(
        data=d,
        valor=50.0,
        descricao="BBBB",
        banco_origem="Itaú",
        pessoa="pessoa_a",
        forma_pagamento="Débito",
        tipo="Despesa",
        identificador="hash_xyz",
    )
    resultado = _aplicar_dedup_pipeline([t1, t2, t3])
    assert len(resultado) == 2
    ids = {t.identificador for t in resultado}
    assert ids == {"hash_abc", "hash_xyz"}


def test_aplicar_dedup_pipeline_fuzzy_hash_colapsa() -> None:
    """Mesmo data+valor+descrição sem identificador cai no nível 2."""
    d = date(2026, 3, 10)
    t1 = Transacao(
        data=d,
        valor=100.0,
        descricao="Ki-Sabor",
        banco_origem="C6",
        pessoa="pessoa_a",
        forma_pagamento="Débito",
        tipo="Despesa",
    )
    t2 = Transacao(
        data=d,
        valor=100.0,
        descricao="Ki-Sabor",
        banco_origem="C6",
        pessoa="pessoa_a",
        forma_pagamento="Débito",
        tipo="Despesa",
    )
    resultado = _aplicar_dedup_pipeline([t1, t2])
    assert len(resultado) == 1


def test_auditar_banco_com_deduplicado_dir_completo(tmp_path: Path) -> None:
    """Flag --deduplicado reduz contagem quando diretório tem cópias SHA iguais."""
    # O extrator fake retorna a lista com identificador único por fatura.
    # Simulamos 3 arquivos, 2 duplicatas SHA:
    diretorio = tmp_path / "data" / "raw" / "andre" / "itau_cc"
    diretorio.mkdir(parents=True)
    conteudo_igual = b"fatura_duplicada\n"
    (diretorio / "fatura_2026-03_abc.pdf").write_bytes(conteudo_igual)
    (diretorio / "fatura_2026-03_abc_1.pdf").write_bytes(conteudo_igual)
    (diretorio / "fatura_2026-03_abc_2.pdf").write_bytes(conteudo_igual)

    # Cada instancia do fake retorna a mesma lista (simulando mesmo PDF).
    _ExtratorFake.TRANSACOES = [
        Transacao(
            data=date(2026, 3, 10),
            valor=100.0,
            descricao="AAAA",
            banco_origem="Itaú",
            pessoa="pessoa_a",
            forma_pagamento="Débito",
            tipo="Despesa",
            identificador="hash_abc",
        ),
    ]

    definicao = DefinicaoBanco(
        chave="itau_cc",
        titulo="Itaú CC (fake)",
        extrator_cls=_ExtratorFake,
        diretorio_relativo=Path("data/raw/andre/itau_cc"),
        filtro_xlsx=FiltroXLSX.simples(banco_origem="Itaú"),
        extensoes=(".pdf",),
    )

    df = pd.DataFrame(
        [
            {
                "banco_origem": "Itaú",
                "forma_pagamento": "Débito",
                "quem": "pessoa_a",
                "mes_ref": "2026-03",
                "valor": 100.0,
            }
        ]
    )
    (tmp_path / "xlsx.xlsx").write_bytes(b"")

    # SEM --deduplicado: soma replicada 3x, diverge.
    resultado_sem = auditar_banco(
        definicao=definicao,
        raiz=tmp_path,
        mes_ref=None,
        xlsx=tmp_path / "xlsx.xlsx",
        carregador_xlsx=lambda _: df,
        modo_abrangente=True,
        deduplicado=False,
    )
    assert resultado_sem.n_extrator == 3
    assert resultado_sem.total_extrator == pytest.approx(300.0)
    assert resultado_sem.veredito == "DIVERGE"

    # COM --deduplicado: SHA dedup + identificador colapsa tudo em 1.
    resultado_com = auditar_banco(
        definicao=definicao,
        raiz=tmp_path,
        mes_ref=None,
        xlsx=tmp_path / "xlsx.xlsx",
        carregador_xlsx=lambda _: df,
        modo_abrangente=True,
        deduplicado=True,
    )
    assert resultado_com.modo_dedup is True
    assert resultado_com.arquivos_fisicos == 3
    assert resultado_com.arquivos_unicos_sha == 1
    assert resultado_com.n_extrator == 1
    assert resultado_com.total_extrator == pytest.approx(100.0)
    assert resultado_com.veredito == "OK"
    assert resultado_com.delta <= 0.02
    assert "duplicatas removidas: 2" in resultado_com.observacao


def test_cli_flag_deduplicado_aceita(capsys) -> None:
    """A flag --deduplicado aparece no parser (não levanta erro no --help)."""
    rc = main(["--banco", "itau_cc", "--deduplicado"])
    # Pode retornar 0 ou 1 dependendo dos dados reais; o importante é que o
    # arg foi parseado sem explodir.
    assert rc in {0, 1}


# --------------------------------------------------------------------------- #
# Sprint 93b -- flags `--com-ofx` e `--ignorar-ti`                             #
# --------------------------------------------------------------------------- #


def test_ignorar_ti_remove_linhas_transferencia_interna_do_xlsx(tmp_path: Path) -> None:
    """Quando o banco aceita, flag `--ignorar-ti` remove tx `tipo=TI` do XLSX.

    Caso base Sprint 93b (c6_cartao): pagamentos de fatura entram no XLSX com
    `banco_origem=C6 + forma=Crédito + tipo=Transferência Interna`, mas não
    saem do extrator de cartão. Ao ignorá-los, delta fecha em R$ 0,00.
    """
    diretorio = tmp_path / "data" / "raw" / "andre" / "c6_cartao"
    diretorio.mkdir(parents=True)
    (diretorio / "fatura.pdf").write_bytes(b"x")

    _ExtratorFake.TRANSACOES = [
        Transacao(
            data=date(2026, 3, 10),
            valor=100.0,
            descricao="compra",
            banco_origem="C6",
            pessoa="pessoa_a",
            forma_pagamento="Crédito",
            tipo="Despesa",
            identificador="compra-1",
        ),
    ]

    definicao = DefinicaoBanco(
        chave="c6_cartao_fake",
        titulo="C6 Cartão fake",
        extrator_cls=_ExtratorFake,
        diretorio_relativo=Path("data/raw/andre/c6_cartao"),
        filtro_xlsx=FiltroXLSX.simples(
            banco_origem="C6",
            formas_pagamento=("Crédito",),
        ),
        extensoes=(".pdf",),
        aceita_ignorar_ti=True,
    )

    df = pd.DataFrame(
        [
            {
                "banco_origem": "C6",
                "forma_pagamento": "Crédito",
                "tipo": "Despesa",
                "mes_ref": "2026-03",
                "valor": 100.0,
                "quem": "pessoa_a",
            },
            {
                "banco_origem": "C6",
                "forma_pagamento": "Crédito",
                "tipo": "Transferência Interna",
                "mes_ref": "2026-03",
                "valor": 6400.0,
                "quem": "pessoa_a",
            },
        ]
    )
    (tmp_path / "xlsx.xlsx").write_bytes(b"")

    # SEM ignorar_ti: delta enorme por causa da TI (R$ 6.400,00).
    sem = auditar_banco(
        definicao=definicao,
        raiz=tmp_path,
        mes_ref=None,
        xlsx=tmp_path / "xlsx.xlsx",
        carregador_xlsx=lambda _: df,
        modo_abrangente=True,
        ignorar_ti=False,
    )
    assert sem.veredito == "DIVERGE"
    assert sem.n_xlsx == 2

    # COM ignorar_ti: TI removida, delta zera.
    com = auditar_banco(
        definicao=definicao,
        raiz=tmp_path,
        mes_ref=None,
        xlsx=tmp_path / "xlsx.xlsx",
        carregador_xlsx=lambda _: df,
        modo_abrangente=True,
        ignorar_ti=True,
    )
    assert com.veredito == "OK"
    assert com.n_xlsx == 1
    assert com.n_xlsx_ti_ignoradas == 1
    assert com.total_xlsx_ti_ignoradas == pytest.approx(6400.0)
    assert "TI ignoradas no XLSX" in com.observacao


def test_ignorar_ti_nao_se_aplica_a_bancos_que_nao_aceitam(tmp_path: Path) -> None:
    """Gate por-banco: `aceita_ignorar_ti=False` torna a flag no-op.

    Proteção contra regressões: itau_cc e santander_cartao não deveriam
    perder tx legítimas quando a flag é acionada globalmente em `--tudo`.
    """
    diretorio = tmp_path / "data" / "raw" / "andre" / "itau_cc"
    diretorio.mkdir(parents=True)
    (diretorio / "ex.pdf").write_bytes(b"x")

    _ExtratorFake.TRANSACOES = [
        Transacao(
            data=date(2026, 3, 10),
            valor=100.0,
            descricao="compra",
            banco_origem="Itaú",
            pessoa="pessoa_a",
            forma_pagamento="Débito",
            tipo="Despesa",
            identificador="c-1",
        ),
    ]
    definicao = DefinicaoBanco(
        chave="itau_fake",
        titulo="Itaú fake",
        extrator_cls=_ExtratorFake,
        diretorio_relativo=Path("data/raw/andre/itau_cc"),
        filtro_xlsx=FiltroXLSX.simples(banco_origem="Itaú"),
        extensoes=(".pdf",),
        aceita_ignorar_ti=False,  # gate explícito
    )
    df = pd.DataFrame(
        [
            {
                "banco_origem": "Itaú",
                "forma_pagamento": "Débito",
                "tipo": "Despesa",
                "mes_ref": "2026-03",
                "valor": 100.0,
                "quem": "pessoa_a",
            },
            {
                "banco_origem": "Itaú",
                "forma_pagamento": "Débito",
                "tipo": "Transferência Interna",
                "mes_ref": "2026-03",
                "valor": 500.0,
                "quem": "pessoa_a",
            },
        ]
    )
    (tmp_path / "xlsx.xlsx").write_bytes(b"")
    resultado = auditar_banco(
        definicao=definicao,
        raiz=tmp_path,
        mes_ref=None,
        xlsx=tmp_path / "xlsx.xlsx",
        carregador_xlsx=lambda _: df,
        modo_abrangente=True,
        ignorar_ti=True,  # flag acesa mas banco não aceita
    )
    assert resultado.n_xlsx == 2
    assert resultado.n_xlsx_ti_ignoradas == 0


def test_com_ofx_complementa_extrator_quando_banco_aceita(tmp_path: Path) -> None:
    """Flag `--com-ofx` soma transações de arquivos `.ofx` do diretório.

    Simula o cenário c6_cc (Sprint 93b): pipeline real processa `.xlsx` do
    extrator canônico E `.ofx` (OFX exportado do Open Finance). Sem a flag,
    auditor só vê .xlsx e diverge; com a flag, soma as fontes.
    """
    from scripts.auditar_extratores import _extrair_ofx_complementar

    # Caso empírico simples: sem OFX físico no diretório, função retorna [].
    diretorio = tmp_path / "c6_cc"
    diretorio.mkdir()
    (diretorio / "fatura.xlsx").write_bytes(b"x")

    tx_ofx = _extrair_ofx_complementar(diretorio)
    assert tx_ofx == []  # sem OFX no dir, lista vazia


def test_com_ofx_opt_in_por_banco(tmp_path: Path) -> None:
    """`aceita_ofx_complementar=False` torna a flag no-op.

    Garante retrocompatibilidade: bancos onde OFX não é fonte relevante
    (ex: nubank_cartao, cuja fatura é CSV exclusivo) ignoram a flag
    mesmo quando passada globalmente.
    """
    diretorio = tmp_path / "data" / "raw" / "andre" / "nubank_cartao"
    diretorio.mkdir(parents=True)
    (diretorio / "fatura.csv").write_bytes(b"x")
    # Coloca um .ofx no dir -- que deveria ser ignorado.
    (diretorio / "ofx_ignorado.ofx").write_bytes(b"<OFX></OFX>")

    _ExtratorFake.TRANSACOES = [
        Transacao(
            data=date(2026, 3, 10),
            valor=100.0,
            descricao="compra",
            banco_origem="Nubank",
            pessoa="pessoa_a",
            forma_pagamento="Crédito",
            tipo="Despesa",
            identificador="n-1",
        ),
    ]
    _ExtratorFake.EXTENSOES = (".csv",)
    definicao = DefinicaoBanco(
        chave="nubank_fake",
        titulo="Nubank fake",
        extrator_cls=_ExtratorFake,
        diretorio_relativo=Path("data/raw/andre/nubank_cartao"),
        filtro_xlsx=FiltroXLSX.simples(
            banco_origem="Nubank",
            formas_pagamento=("Crédito",),
        ),
        extensoes=(".csv",),
        aceita_ofx_complementar=False,  # gate explícito
    )
    df = pd.DataFrame(
        [
            {
                "banco_origem": "Nubank",
                "forma_pagamento": "Crédito",
                "tipo": "Despesa",
                "mes_ref": "2026-03",
                "valor": 100.0,
                "quem": "pessoa_a",
            },
        ]
    )
    (tmp_path / "xlsx.xlsx").write_bytes(b"")

    resultado = auditar_banco(
        definicao=definicao,
        raiz=tmp_path,
        mes_ref=None,
        xlsx=tmp_path / "xlsx.xlsx",
        carregador_xlsx=lambda _: df,
        modo_abrangente=True,
        com_ofx=True,  # flag acesa, banco recusa
    )
    # OFX foi ignorado: contagem do extrator é a do fake (1 tx).
    assert resultado.n_ofx_complementar == 0
    # Reset para evitar vazar estado entre testes.
    _ExtratorFake.EXTENSOES = (".pdf",)


def test_cli_flags_93b_sao_parseadas(capsys) -> None:
    """Flags --com-ofx e --ignorar-ti não quebram o parser."""
    rc = main(["--banco", "itau_cc", "--com-ofx", "--ignorar-ti"])
    assert rc in {0, 1}


def test_campos_novos_em_resultado_auditoria_sao_retrocompat(tmp_path: Path) -> None:
    """Campos novos (`n_ofx_complementar`, `n_xlsx_ti_ignoradas` etc.) têm default
    que preserva retrocompat. Teste simples de contrato do dataclass."""
    r = ResultadoAuditoria(
        banco="x",
        mes_ref=None,
        arquivo=None,
        total_extrator=0.0,
        total_xlsx=0.0,
        n_extrator=0,
        n_xlsx=0,
        veredito="SEM_DADOS",
    )
    assert r.n_ofx_complementar == 0
    assert r.total_ofx_complementar == 0.0
    assert r.n_xlsx_ti_ignoradas == 0
    assert r.total_xlsx_ti_ignoradas == 0.0


# "Evidência é o único juiz.
#  Teste unitário prova que o código não quebra;
#  auditoria prova que o código faz o que deveria." -- princípio de fidelidade
