"""Testes de ``src.marcos_auto.dedup`` (Sprint MOB-bridge-3).

Cobertura:

    - hash determinístico (mesma entrada → mesma saída).
    - hash distinto entre tipos/datas/descrições diferentes.
    - hash de 12 caracteres hexadecimais.
    - tolerância a campos extras (autor, tags, auto, origem).
    - falha rápida quando faltam campos obrigatórios.
"""

from __future__ import annotations

import re

import pytest

from src.marcos_auto.dedup import hash_marco


def test_hash_deterministico():
    """Mesma combinação dos três campos do schema produz mesmo hash."""
    meta = {"tipo": "marco", "data": "2026-04-29", "descricao": "Tres treinos."}
    assert hash_marco(meta) == hash_marco(meta)


def test_hash_e_doze_chars_hex():
    """Hash tem exatamente 12 caracteres hexadecimais minúsculos."""
    h = hash_marco({"tipo": "marco", "data": "2026-04-29", "descricao": "Tres treinos."})
    assert len(h) == 12
    assert re.fullmatch(r"[0-9a-f]{12}", h) is not None


def test_hash_distinto_para_tipos_diferentes():
    base_data = "2026-04-29"
    base_desc = "Tres treinos."
    h1 = hash_marco({"tipo": "marco", "data": base_data, "descricao": base_desc})
    h2 = hash_marco({"tipo": "outro", "data": base_data, "descricao": base_desc})
    assert h1 != h2


def test_hash_distinto_para_datas_diferentes():
    base_tipo = "marco"
    base_desc = "Tres treinos."
    h1 = hash_marco({"tipo": base_tipo, "data": "2026-04-29", "descricao": base_desc})
    h2 = hash_marco({"tipo": base_tipo, "data": "2026-04-30", "descricao": base_desc})
    assert h1 != h2


def test_hash_distinto_para_descricoes_diferentes():
    base_tipo = "marco"
    base_data = "2026-04-29"
    h1 = hash_marco({"tipo": base_tipo, "data": base_data, "descricao": "Tres treinos."})
    h2 = hash_marco({"tipo": base_tipo, "data": base_data, "descricao": "Voltou apos 5 dias."})
    assert h1 != h2


def test_hash_ignora_campos_extras():
    """Campos como autor, tags, auto, origem não afetam o hash."""
    nucleo = {"tipo": "marco", "data": "2026-04-29", "descricao": "Tres treinos."}
    com_extras = dict(nucleo)
    com_extras.update({"autor": "pessoa_a", "tags": ["auto"], "auto": True, "origem": "backend"})
    assert hash_marco(nucleo) == hash_marco(com_extras)


def test_hash_falha_quando_falta_campo_obrigatorio():
    with pytest.raises(KeyError):
        hash_marco({"tipo": "marco", "data": "2026-04-29"})


def test_hash_idempotente_sob_reexecucao():
    """Re-executar a função N vezes sempre retorna o mesmo valor."""
    meta = {"tipo": "marco", "data": "2026-04-29", "descricao": "Sete dias."}
    valores = {hash_marco(meta) for _ in range(20)}
    assert len(valores) == 1


# "A constancia do simbolo é o que torna a memória possível." -- Aristoteles
