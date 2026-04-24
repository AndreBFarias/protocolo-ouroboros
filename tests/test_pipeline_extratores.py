"""Testes de discovery de extratores no `src/pipeline.py::_descobrir_extratores`.

Garantem que extratores novos são efetivamente registrados no pipeline
principal (`./run.sh --tudo`), não apenas em `scripts/reprocessar_documentos.py`.
A divergência historicamente silenciou P1-01 da auditoria técnica 2026-04-23.
"""

from __future__ import annotations

from src.pipeline import _descobrir_extratores


def _nomes_extratores() -> list[str]:
    return [extrator.__name__ for extrator in _descobrir_extratores()]


def test_discovery_inclui_boleto_pdf() -> None:
    """Sprint 87e: ExtratorBoletoPDF deve estar registrado no pipeline.

    Sem isso, boletos novos em inbox são roteados corretamente pelo intake
    (Sprint 70) mas não são ingeridos no grafo pelo `./run.sh --tudo` — o
    operador precisa rodar `reprocessar_documentos.py` manualmente.
    """
    nomes = _nomes_extratores()
    assert "ExtratorBoletoPDF" in nomes, (
        "ExtratorBoletoPDF ausente de _descobrir_extratores. Boletos novos "
        "não serão ingeridos no grafo via pipeline principal."
    )


def test_boleto_vem_antes_do_recibo_nao_fiscal() -> None:
    """Ordem canônica: boleto (específico) antes do recibo_nao_fiscal (catch-all).

    Invariante da Sprint 47 preservado nas Sprints 87.3 e 87e: extratores
    específicos precisam ser testados antes do catch-all, senão este captura
    arquivos que pertencem a DANFE, NFC-e, DAS, DIRPF, boleto, etc.
    """
    nomes = _nomes_extratores()
    idx_boleto = nomes.index("ExtratorBoletoPDF")
    idx_recibo = nomes.index("ExtratorReciboNaoFiscal")
    assert idx_boleto < idx_recibo, (
        "ExtratorBoletoPDF deve aparecer antes de ExtratorReciboNaoFiscal; "
        f"posições atuais: boleto={idx_boleto}, recibo={idx_recibo}"
    )


def test_extratores_documentais_recentes_estao_presentes() -> None:
    """Regressão cobrindo todos os extratores documentais recém-registrados.

    Sprint 87e adiciona boleto_pdf; Sprint P1.1 já registrou DAS PARCSN;
    Sprint P3.1 já registrou DIRPF. Este teste evita que um refactor futuro
    de `_descobrir_extratores` remova silenciosamente qualquer um deles.
    """
    nomes = _nomes_extratores()
    for esperado in (
        "ExtratorDASPARCSNPDF",
        "ExtratorDIRPFDec",
        "ExtratorBoletoPDF",
        "ExtratorReciboNaoFiscal",
    ):
        assert esperado in nomes, f"Extrator esperado ausente: {esperado}"


# "Um extrator não-registrado é um extrator dormindo." -- princípio de discovery automático
