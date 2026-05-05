"""Sprint UX-RD-01 — Tokens novos da paleta migrada.

Cobre os 8 contratos regressivos da migração:

1. CORES tem o novo `fundo` (`#0e0f15`).
2. CORES tem o novo `card_fundo` (`#1a1d28`).
3. Tokens novos `card_elevado` e `fundo_inset` presentes e válidos.
4. Token `texto_sec` migrado para `#a8a9b8` e `texto_muted` novo presente.
5. Tokens D7 (`d7_graduado`, `d7_calibracao`, `d7_regredindo`, `d7_pendente`).
6. Tokens validação humana (`humano_aprovado`, `humano_rejeitado`,
   `humano_revisar`, `humano_pendente`).
7. Aliases legacy (chaves históricas em ASCII -- ver ``CHAVES_LEGACY`` abaixo)
   continuam resolvendo para hex válido após a migração da paleta.
8. ``MAPA_CLASSIFICACAO`` continua coerente com ``CORES``.

Adicional: ``.streamlit/config.toml`` reflete o novo `bg-base` e `bg-surface`.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.dashboard import tema

REGEX_HEX_VALIDO = re.compile(r"^#[0-9a-fA-F]{6}$")

CHAVES_LEGACY = (
    "fundo",
    "card_fundo",
    "texto",
    "texto_sec",
    "positivo",
    "negativo",
    "neutro",
    "alerta",
    "destaque",
    "superfluo",
    "info",
    "obrigatorio",
    "questionavel",
    "na",
)


class TestPaletaMigradaUXRD01:
    """8 contratos da Sprint UX-RD-01."""

    def test_1_fundo_migrado_para_bg_base_novo(self):
        """``fundo`` deixa Dracula clássico (#282A36) pelo novo bg-base."""
        assert tema.CORES["fundo"] == "#0e0f15"

    def test_2_card_fundo_migrado_para_bg_surface_novo(self):
        """``card_fundo`` deixa #44475A pelo novo bg-surface."""
        assert tema.CORES["card_fundo"] == "#1a1d28"

    def test_3_tokens_elevado_e_inset_novos(self):
        """Tokens de profundidade adicional (modais, code blocks)."""
        assert tema.CORES["card_elevado"] == "#232735"
        assert tema.CORES["fundo_inset"] == "#0a0b10"

    def test_4_texto_secundario_e_muted(self):
        """Hierarquia de texto: primary -> secondary -> muted."""
        assert tema.CORES["texto_sec"] == "#a8a9b8"
        assert tema.CORES["texto_muted"] == "#6c6f7d"

    def test_5_tokens_d7_presentes(self):
        """Estados D7: cobertura observável (não gate de promoção)."""
        assert tema.CORES["d7_graduado"] == "#6b8e7f"
        assert tema.CORES["d7_calibracao"] == "#f1fa8c"
        assert tema.CORES["d7_regredindo"] == "#ffb86c"
        assert tema.CORES["d7_pendente"] == "#6c6f7d"

    def test_6_tokens_humano_presentes(self):
        """Estados de validação humana (Revisor 4-way)."""
        assert tema.CORES["humano_aprovado"] == "#6b8e7f"
        assert tema.CORES["humano_rejeitado"] == "#ff5555"
        assert tema.CORES["humano_revisar"] == "#f1fa8c"
        assert tema.CORES["humano_pendente"] == "#6c6f7d"

    def test_7_aliases_legacy_resolvem_para_hex_valido(self):
        """Nenhuma chave legacy pode estar ausente ou retornar string vazia."""
        for chave in CHAVES_LEGACY:
            assert chave in tema.CORES, f"Alias legacy ausente: {chave}"
            valor = tema.CORES[chave]
            assert isinstance(valor, str)
            assert REGEX_HEX_VALIDO.match(valor), (
                f"CORES['{chave}'] = {valor!r} não é hex #RRGGBB válido"
            )

    def test_8_mapa_classificacao_coerente_com_cores(self):
        """``MAPA_CLASSIFICACAO`` deriva de ``CORES`` -- não pode ter chave fantasma."""
        mapa = tema.MAPA_CLASSIFICACAO
        # 4 classificações canônicas
        assert set(mapa.keys()) == {"Obrigatório", "Questionável", "Supérfluo", "N/A"}
        # Cada valor existe no dict CORES (rastreabilidade)
        valores_cores = set(tema.CORES.values())
        for classificacao, hex_cor in mapa.items():
            assert REGEX_HEX_VALIDO.match(hex_cor), (
                f"MAPA_CLASSIFICACAO[{classificacao}] não é hex válido: {hex_cor}"
            )
            assert hex_cor in valores_cores, (
                f"Cor de '{classificacao}' ({hex_cor}) órfã -- sem chave em CORES"
            )


class TestStreamlitConfigMigrado:
    """Sanidade da paleta declarada em ``.streamlit/config.toml``."""

    def test_streamlit_config_background_color_e_bg_base(self):
        """Streamlit precisa pintar o viewport com a mesma cor que o tema."""
        path = Path(__file__).resolve().parents[1] / ".streamlit" / "config.toml"
        texto_toml = path.read_text(encoding="utf-8")
        # Match case-insensitive porque hex pode ser escrito com letras maiúsculas
        assert re.search(
            r'backgroundColor\s*=\s*"#0e0f15"', texto_toml, flags=re.IGNORECASE
        ), "backgroundColor do Streamlit deve ser #0e0f15 (bg-base)"
        assert re.search(
            r'secondaryBackgroundColor\s*=\s*"#1a1d28"',
            texto_toml,
            flags=re.IGNORECASE,
        ), "secondaryBackgroundColor do Streamlit deve ser #1a1d28 (bg-surface)"


# "Sem fundamento sólido, o resto desaba." -- Sêneca
