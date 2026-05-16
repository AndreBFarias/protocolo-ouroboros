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
    t_hist = transacao(valor=200.0, local="Loja Y", banco="Histórico", quem="pessoa_a")
    t_nova = transacao(valor=200.0, local="Loja Y", banco="Nubank (PF)", quem="casal")
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


def test_nivel2_cross_bank_pix_mesmo_valor_data_preserva_ambos(transacao):
    """Sprint INFRA-DEDUP-NIVEL-2-INCLUI-BANCO: cross-bank não pode dedupar.

    PIX R$5000 chegando ao Nubank ("Recebimento Pix - EMPRESA X") e PIX
    R$5000 saindo do C6 para "EMPRESA X" no mesmo dia são DUAS transações
    legítimas e distintas. Antes desta sprint, `_normalizar_local_para_chave`
    transformava ambos os `local` em `"empresa x"`, gerando colisão na
    chave 3-tuple `(data, valor, local_normalizado)`. Com a chave 4-tuple
    incluindo `banco_origem`, os dois caem em buckets distintos
    (`"Nubank"` vs `"C6"`) e são preservados.
    """
    t_nubank = transacao(
        data_t=date(2026, 5, 10),
        valor=5000.0,
        local="Recebimento Pix - EMPRESA X",
        banco="Nubank",
        quem="pessoa_a",
    )
    t_nubank["_arquivo_origem"] = "nu.ofx"
    t_c6 = transacao(
        data_t=date(2026, 5, 10),
        valor=5000.0,
        local="EMPRESA X",
        banco="C6",
        quem="pessoa_a",
    )
    t_c6["_arquivo_origem"] = "c6.xlsx"
    resultado = deduplicar_por_hash_fuzzy([t_nubank, t_c6])
    assert len(resultado) == 2, f"cross-bank dedupou erroneamente: {len(resultado)}"
    bancos = sorted(r["banco_origem"] for r in resultado)
    assert bancos == ["C6", "Nubank"], f"bancos inesperados: {bancos}"


def test_nivel2_mesmo_banco_ofx_xlsx_consolida_via_2b(transacao):
    """Sprint INFRA-DEDUP-NIVEL-2-INCLUI-BANCO: mesmo banco OFX+XLSX ainda consolida.

    Garante que o fix cross-bank não regrediu o comportamento da sprint
    anterior `INFRA-DEDUP-C6-OFX-XLSX-AMPLO` (commit `2998b26`): pares
    OFX+XLSX do mesmo banco continuam sendo consolidados via pass 2b
    `_consolidar_pares_ofx_xlsx_mesmo_banco`. A chave 4-tuple do pass 2a
    pode até não casar (locais materialmente distintos), mas o pass 2b
    pega pelo critério `(data, valor, banco_origem, quem)` + diferença
    de extensão de arquivo.
    """
    t_ofx = transacao(
        data_t=date(2026, 5, 10),
        valor=5000.0,
        local="Recebimento Pix - X",
        banco="C6",
        quem="pessoa_a",
    )
    t_ofx["_arquivo_origem"] = "c6.ofx"
    t_xlsx = transacao(
        data_t=date(2026, 5, 10),
        valor=5000.0,
        local="X",
        banco="C6",
        quem="pessoa_a",
    )
    t_xlsx["_arquivo_origem"] = "c6.xlsx"
    resultado = deduplicar_por_hash_fuzzy([t_ofx, t_xlsx])
    assert len(resultado) == 1, f"mesmo-banco não consolidou: {len(resultado)}"
    # Pass 2a normaliza ambos `local` para "x" e a chave 4-tuple casa
    # (mesmo banco "C6"), consolidando direto na fase principal --
    # critério de descrição mais rica preserva o OFX.
    assert resultado[0]["_arquivo_origem"] == "c6.ofx", (
        f"esperado OFX preservado: {resultado[0]}"
    )


def test_nivel3_par_transferencia_marca_ambos_lados(transacao):
    """Nível 3: Pix André→Vitória marca ambas pontas como Transferência Interna.  # anonimato-allow

    Sprint 68 exige identidade formal do casal (nome composto da whitelist
    em `mappings/contas_casal.yaml`) em pelo menos um dos lados do par.
    Fixture ajustada na Sprint 68b para refletir o novo contrato.
    """
    saida = transacao(
        data_t=date(2025, 5, 10),
        valor=500.0,
        local="Pix para VITORIA MARIA SILVA DOS SANTOS",
        tipo="Despesa",
        quem="pessoa_a",
    )
    entrada = transacao(
        data_t=date(2025, 5, 10),
        valor=500.0,
        local="Pix recebido de ANDRE DA SILVA BATISTA DE FARIAS",
        tipo="Receita",
        quem="pessoa_b",
    )
    resultado = marcar_transferencias_internas([saida, entrada])
    assert all(t["tipo"] == "Transferência Interna" for t in resultado)


def test_nivel3_nao_confunde_mesma_pessoa(transacao):
    """Mesmo valor e data no mesmo `quem` não é par de TI."""
    t1 = transacao(valor=100.0, tipo="Despesa", quem="pessoa_a")
    t2 = transacao(valor=100.0, tipo="Receita", quem="pessoa_a")
    resultado = marcar_transferencias_internas([t1, t2])
    assert resultado[0]["tipo"] == "Despesa"
    assert resultado[1]["tipo"] == "Receita"


def test_deduplicar_orquestra_tres_niveis(transacao):
    """Smoke test: pipeline completo de dedup consolida todas as fases."""
    t_hist = transacao(valor=200.0, local="Loja Z", banco="Histórico", identificador=None)
    t_nova = transacao(valor=200.0, local="Loja Z", banco="Nubank (PF)", identificador="uuid1")
    t_dup = transacao(valor=200.0, local="Loja Z", banco="Nubank (PF)", identificador="uuid1")
    resultado = deduplicar([t_hist, t_nova, t_dup])
    assert len(resultado) == 1


# "O semelhante gera o semelhante, e o igual reconhece o igual." -- Heráclito
