"""Testes dos três níveis de deduplicação."""

from datetime import date

from src.transform.deduplicator import (
    deduplicar,
    deduplicar_por_hash_fuzzy,
    deduplicar_por_identificador,
    marcar_transferencias_internas,
)


def test_nivel1_remove_uuid_duplicado(transacao):
    """Armadilha #13: Nubank CC tem duplicatas (1) (2) -- dedup por UUID."""
    t1 = transacao(identificador="abc123", local="Compra X")
    t2 = transacao(identificador="abc123", local="Compra X (1)")
    t3 = transacao(identificador="xyz789", local="Outra")
    resultado = deduplicar_por_identificador([t1, t2, t3])
    assert len(resultado) == 2
    assert resultado[0]["_identificador"] == "abc123"
    assert resultado[1]["_identificador"] == "xyz789"


def test_nivel1_preserva_sem_identificador(transacao):
    """Transações sem _identificador (histórico) não são filtradas pelo nível 1."""
    t1 = transacao(identificador=None, local="Sem UUID 1")
    t2 = transacao(identificador=None, local="Sem UUID 2")
    resultado = deduplicar_por_identificador([t1, t2])
    assert len(resultado) == 2


def test_nivel2_remove_mesma_data_valor_local(transacao):
    """Dois registros com mesmo data+valor+local (OFX vs XLSX) são consolidados."""
    t1 = transacao(data_t=date(2025, 1, 10), valor=100.0, local="Mercado A", banco="C6")
    t2 = transacao(data_t=date(2025, 1, 10), valor=100.0, local="Mercado A", banco="C6")
    resultado = deduplicar_por_hash_fuzzy([t1, t2])
    assert len(resultado) == 1


def test_nivel2_preserva_localizacoes_diferentes(transacao):
    """Mesmo valor e data em locais diferentes não é duplicata."""
    t1 = transacao(data_t=date(2025, 1, 10), valor=50.0, local="Mercado A")
    t2 = transacao(data_t=date(2025, 1, 10), valor=50.0, local="Mercado B")
    resultado = deduplicar_por_hash_fuzzy([t1, t2])
    assert len(resultado) == 2


def test_nivel2_prefere_nao_historico(transacao):
    """Dedupe mantém versão com banco_origem != 'Histórico' (metadados melhores)."""
    t_hist = transacao(valor=200.0, local="Loja Y", banco="Histórico", quem="André")
    t_nova = transacao(valor=200.0, local="Loja Y", banco="Nubank (PF)", quem="Casal")
    resultado = deduplicar_por_hash_fuzzy([t_hist, t_nova])
    assert len(resultado) == 1
    assert resultado[0]["banco_origem"] == "Nubank (PF)"


def test_nivel2_inclui_transferencia_interna(transacao):
    """TI duplicada na mesma conta (OFX+CSV) também deve ser removida."""
    t1 = transacao(
        data_t=date(2025, 6, 6),
        valor=236.0,
        local="ANDRE DA SILVA",
        tipo="Transferência Interna",
        banco="Nubank (PF)",
    )
    t2 = transacao(
        data_t=date(2025, 6, 6),
        valor=236.0,
        local="ANDRE DA SILVA",
        tipo="Transferência Interna",
        banco="Nubank (PF)",
    )
    resultado = deduplicar_por_hash_fuzzy([t1, t2])
    assert len(resultado) == 1


def test_nivel3_par_transferencia_marca_ambos_lados(transacao):
    """Nível 3: Pix André→Vitória marca ambas pontas como Transferência Interna."""
    saida = transacao(
        data_t=date(2025, 5, 10),
        valor=500.0,
        local="Pix para Vitória",
        tipo="Despesa",
        quem="André",
    )
    entrada = transacao(
        data_t=date(2025, 5, 10),
        valor=500.0,
        local="Pix recebido de André",
        tipo="Receita",
        quem="Vitória",
    )
    resultado = marcar_transferencias_internas([saida, entrada])
    assert all(t["tipo"] == "Transferência Interna" for t in resultado)


def test_nivel3_nao_confunde_mesma_pessoa(transacao):
    """Mesmo valor e data no mesmo `quem` não é par de TI."""
    t1 = transacao(valor=100.0, tipo="Despesa", quem="André")
    t2 = transacao(valor=100.0, tipo="Receita", quem="André")
    resultado = marcar_transferencias_internas([t1, t2])
    assert resultado[0]["tipo"] == "Despesa"
    assert resultado[1]["tipo"] == "Receita"


def test_deduplicar_orquestra_tres_niveis(transacao):
    """Smoke test: pipeline completo de dedup consolida todas as fases."""
    t_hist = transacao(
        valor=200.0, local="Loja Z", banco="Histórico", identificador=None
    )
    t_nova = transacao(
        valor=200.0, local="Loja Z", banco="Nubank (PF)", identificador="uuid1"
    )
    t_dup = transacao(
        valor=200.0, local="Loja Z", banco="Nubank (PF)", identificador="uuid1"
    )
    resultado = deduplicar([t_hist, t_nova, t_dup])
    assert len(resultado) == 1


# "O semelhante gera o semelhante, e o igual reconhece o igual." -- Heráclito
