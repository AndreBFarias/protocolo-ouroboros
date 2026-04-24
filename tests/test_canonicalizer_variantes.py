"""Testes para o nível 2 do canonicalizer do casal (Sprint 82).

Cobertura:
    1. Variantes curtas legítimas passam sob o contexto bancário correto.
    2. Variantes curtas em banco fora da whitelist NÃO passam.
    3. Falsos-positivos históricos (DEIVID, JOAO, ANDRE BARATA, Crislane
       Vitória da Silva Melo) continuam NÃO casando.
    4. `e_transferencia_do_casal` (nível 1) permanece intocado em
       regressão (acceptance core da Sprint 68b).
    5. Pipeline `_promover_variantes_para_ti` promove corretamente
       Receita/Despesa → Transferência Interna quando variante casa,
       e NÃO toca linhas já TI ou Imposto.
"""

import pytest

from src.pipeline import _promover_variantes_para_ti
from src.transform.canonicalizer_casal import (
    e_transferencia_do_casal,
    resetar_cache,
    variantes_curtas,
)


@pytest.fixture(autouse=True)
def _limpar_cache_yaml():
    """Força releitura do YAML antes de cada teste."""
    resetar_cache()
    yield
    resetar_cache()


class TestVariantesCurtas:
    """Tabela empírica dos casos observados em abril/2026 + armadilhas."""

    @pytest.mark.parametrize(
        "desc,banco,esperado",
        [
            # Casos reais da spec que hoje caem indevidamente como Receita.
            ("PIX TRANSF Vitória09/04", "Itaú", True),
            ("ANDRE SILVA BATISTA FARIAS", "Nubank", True),
            (
                "Transferência recebida pelo Pix - ANDRE SILVA BATISTA FARIAS",
                "Nubank (PF)",
                True,
            ),
            ("ANDRE FARIAS TRANSF 12/04", "Nubank", True),
            # Falsos-positivos que PRECISAM continuar False.
            ("ANDRE BARATA", "Nubank", False),
            ("DEIVID DA SILVA ALVES SANTANA", "Nubank", False),
            ("JOAO DA SILVA", "Nubank", False),
            ("Crislane Vitória da Silva Melo - 111", "Nubank (PF)", False),
            ("PIX RECEBIDO MERCAVITORIA 09/04", "Itaú", False),
            # Banco fora da whitelist não casa.
            ("VITORIA Vitória", "C6", False),
            ("PIX TRANSF Vitória 09/04", "C6", False),
            # Falta contexto (marcador ou data).
            ("Vitória", "Itaú", False),
            ("PIX TRANSF Vitória", "Itaú", False),
            ("Vitória-ES cidade", "Itaú", False),
            # Requer min_matches >= 2 para ANDRE + FARIAS.
            ("ANDRE SOZINHO", "Nubank", False),
            # Parâmetros vazios.
            ("", "Itaú", False),
            ("ANDRE SILVA BATISTA FARIAS", "", False),
        ],
    )
    def test_casos_da_spec(self, desc: str, banco: str, esperado: bool) -> None:
        assert variantes_curtas(desc, banco) is esperado, (
            f"desc={desc!r} banco={banco!r}"
        )

    def test_yaml_ausente_fail_closed(self, tmp_path) -> None:
        """Sem YAML, função retorna False (nunca marca como TI por default)."""
        resetar_cache()
        assert variantes_curtas(
            "ANDRE SILVA BATISTA FARIAS",
            "Nubank",
            caminho_yaml=str(tmp_path / "inexistente.yaml"),
        ) is False

    def test_rigoroso_nao_regressou(self) -> None:
        """Nível 1 do matcher continua rigoroso (Sprint 68b core)."""
        assert e_transferencia_do_casal("ANDRE DA SILVA BATISTA DE FARIAS") is True
        assert e_transferencia_do_casal("VITORIA MARIA SILVA DOS SANTOS") is True
        assert e_transferencia_do_casal("DEIVID DA SILVA ALVES SANTANA") is False
        assert e_transferencia_do_casal("ANDRE BARATA") is False
        # Vitória sozinha NÃO casa no rigoroso (precisa nome completo).
        assert e_transferencia_do_casal("Vitória") is False


class TestPromoverVariantesParaTI:
    """Testa a rede de captura pós-reclassificação (pipeline etapa 6c)."""

    def test_promove_receita_vitoria_itau_para_ti(self) -> None:
        transacoes = [
            {
                "tipo": "Receita",
                "_descricao_original": "PIX TRANSF Vitória09/04",
                "local": "PIX TRANSF Vitória",
                "banco_origem": "Itaú",
                "valor": 2000.0,
            },
        ]
        resultado = _promover_variantes_para_ti(transacoes)
        assert resultado[0]["tipo"] == "Transferência Interna"

    def test_promove_receita_andre_curto_nubank_para_ti(self) -> None:
        desc_original = (
            "Transferência recebida pelo Pix - ANDRE SILVA BATISTA FARIAS"
        )
        transacoes = [
            {
                "tipo": "Receita",
                "_descricao_original": desc_original,
                "local": "ANDRE SILVA BATISTA FARIAS",
                "banco_origem": "Nubank (PF)",
                "valor": 2000.0,
            },
        ]
        resultado = _promover_variantes_para_ti(transacoes)
        assert resultado[0]["tipo"] == "Transferência Interna"

    def test_nao_toca_ti_existente(self) -> None:
        transacoes = [
            {
                "tipo": "Transferência Interna",
                "_descricao_original": "ANDRE DA SILVA BATISTA DE FARIAS",
                "local": "ANDRE DA SILVA BATISTA DE FARIAS",
                "banco_origem": "Nubank",
                "valor": 500.0,
            },
        ]
        resultado = _promover_variantes_para_ti(transacoes)
        assert resultado[0]["tipo"] == "Transferência Interna"

    def test_nao_toca_imposto(self) -> None:
        transacoes = [
            {
                "tipo": "Imposto",
                "_descricao_original": "DAS MEI",
                "local": "DAS - Simples Nacional",
                "banco_origem": "Nubank (PF)",
                "valor": 75.0,
            },
        ]
        resultado = _promover_variantes_para_ti(transacoes)
        assert resultado[0]["tipo"] == "Imposto"

    def test_nao_promove_terceiro_homonimo(self) -> None:
        transacoes = [
            {
                "tipo": "Receita",
                "_descricao_original": "Crislane Vitória da Silva Melo",
                "local": "Crislane Vitória",
                "banco_origem": "Nubank (PF)",
                "valor": 120.0,
            },
            {
                "tipo": "Despesa",
                "_descricao_original": "DEIVID DA SILVA ALVES SANTANA",
                "local": "DEIVID DA SILVA",
                "banco_origem": "Nubank",
                "valor": 50.0,
            },
        ]
        resultado = _promover_variantes_para_ti(transacoes)
        assert resultado[0]["tipo"] == "Receita"
        assert resultado[1]["tipo"] == "Despesa"

    def test_ignora_banco_ausente(self) -> None:
        transacoes = [
            {
                "tipo": "Receita",
                "_descricao_original": "ANDRE SILVA BATISTA FARIAS",
                "local": "ANDRE SILVA BATISTA FARIAS",
                "banco_origem": "",
                "valor": 2000.0,
            },
        ]
        resultado = _promover_variantes_para_ti(transacoes)
        assert resultado[0]["tipo"] == "Receita"


# "Quem vê pouco, precisa de muito. Quem vê bem, enxerga o próximo passo." -- Sêneca
