"""Fixtures para testes de ``src.marcos_auto`` (Sprint MOB-bridge-3).

Monta um Vault temporário em ``tmp_path`` com:

    - 14 dias consecutivos de ``daily/`` (humor) para pessoa_a.
    - 5 ``treinos/`` distribuídos em 9 dias (gera 3-em-7 e
      retorno-apos-hiato).
    - 2 ``inbox/mente/diario/`` (um trigger, uma vitoria).
    - 1 ``eventos/`` com modo positivo.
    - Diretório ``marcos/`` vazio.

Cada fixture devolve o ``Path`` raiz do vault. O teste opera direto
nesse vault e verifica artefatos em ``marcos/``.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml


def _gravar_md(path: Path, frontmatter: dict, body: str = "") -> None:
    """Helper local para gravar markdown com frontmatter durante setup."""
    path.parent.mkdir(parents=True, exist_ok=True)
    bloco = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
    if body:
        path.write_text(f"---\n{bloco}---\n\n{body}\n", encoding="utf-8")
    else:
        path.write_text(f"---\n{bloco}---\n", encoding="utf-8")


@pytest.fixture
def vault_basico(tmp_path: Path) -> Path:
    """Vault mínimo: só estrutura de diretórios, zero eventos."""
    for sub in ("daily", "treinos", "eventos", "marcos", "inbox/mente/diario"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def vault_rico(tmp_path: Path) -> Path:
    """Vault com 14 dailies, 5 treinos, 2 diários, 1 evento.

    Datas-base partem de 2026-04-01 para isolamento determinístico
    (independe da data atual). 14 dailies consecutivos garantem
    sete_dias_humor; 5 treinos em janela de 9 dias garantem
    tres_treinos_em_sete_dias e gap >= 5 dias gera retorno_apos_hiato.
    """
    for sub in ("daily", "treinos", "eventos", "marcos", "inbox/mente/diario"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)

    base = date(2026, 4, 1)

    # 14 dailies consecutivos para pessoa_a.
    for i in range(14):
        d = base + timedelta(days=i)
        _gravar_md(
            tmp_path / "daily" / f"{d.isoformat()}.md",
            {
                "tipo": "humor",
                "data": d.isoformat(),
                "autor": "pessoa_a",
                "humor": 4,
                "energia": 3,
                "ansiedade": 2,
                "foco": 4,
                "tags": ["test"],
            },
            body="dia normal.",
        )

    # 5 treinos: 3 em 7 dias + gap >= 5 dias. pessoa_a.
    treinos_offsets = [0, 2, 5, 12, 14]  # gap entre 5 e 12 = 7 dias
    for offset in treinos_offsets:
        d = base + timedelta(days=offset)
        _gravar_md(
            tmp_path / "treinos" / f"{d.isoformat()}-rotina-a.md",
            {
                "tipo": "treino_sessao",
                "data": f"{d.isoformat()}T18:00:00-03:00",
                "autor": "pessoa_a",
                "rotina": "Rotina A",
                "duracao_min": 30,
                "exercicios": [],
            },
            body="ok.",
        )

    # 2 diarios emocionais: um trigger no dia 1, uma vitoria no dia 13.
    _gravar_md(
        tmp_path / "inbox" / "mente" / "diario" / "2026-04-02-1100-trigger.md",
        {
            "tipo": "diario_emocional",
            "data": "2026-04-02T11:00:00-03:00",
            "autor": "pessoa_a",
            "modo": "trigger",
            "emocoes": ["medo"],
            "intensidade": 4,
        },
        body="evento dificil.",
    )
    _gravar_md(
        tmp_path / "inbox" / "mente" / "diario" / "2026-04-13-1400-vit.md",
        {
            "tipo": "diario_emocional",
            "data": "2026-04-13T14:00:00-03:00",
            "autor": "pessoa_a",
            "modo": "vitoria",
            "emocoes": ["alegria"],
            "intensidade": 4,
        },
        body="terminei.",
    )

    # 1 evento positivo na semana 1.
    _gravar_md(
        tmp_path / "eventos" / "2026-04-03-cafe.md",
        {
            "tipo": "evento",
            "data": "2026-04-03T10:00:00-03:00",
            "autor": "pessoa_a",
            "modo": "positivo",
            "lugar": "padaria",
            "categoria": "rolezinho",
            "intensidade": 4,
        },
        body="cafe da manha.",
    )

    return tmp_path


@pytest.fixture
def vault_sem_trigger(tmp_path: Path) -> Path:
    """Vault com 35 diários consecutivos sem nenhum trigger.

    Garante que ``trinta_dias_sem_trigger`` dispare sem ambiguidade.
    """
    for sub in ("daily", "treinos", "eventos", "marcos", "inbox/mente/diario"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    base = date(2026, 3, 1)
    for i in range(35):
        d = base + timedelta(days=i)
        _gravar_md(
            tmp_path / "inbox" / "mente" / "diario" / f"{d.isoformat()}-1000.md",
            {
                "tipo": "diario_emocional",
                "data": f"{d.isoformat()}T10:00:00-03:00",
                "autor": "pessoa_b",
                "modo": "positivo",
                "emocoes": ["calma"],
                "intensidade": 3,
            },
            body="dia tranquilo.",
        )
    return tmp_path


# "A reprodutibilidade é a forma da honestidade científica." -- Karl Popper
