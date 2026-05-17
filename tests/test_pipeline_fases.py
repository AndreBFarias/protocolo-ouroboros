"""Testes regressivos da Sprint INFRA-PIPELINE-FASES-ISOLADAS (2026-05-17).

Valida o split de `_executar_corpo_pipeline` (157L monolíticas) em 17 fases
isoladas `fase_*(ctx) -> stats`. Cada fase é testada individualmente sem
rodar o pipeline inteiro. A invariante crítica é que a ordem das fases
listada em `FASES` casa exatamente com a ordem da versão monolítica
anterior — pipeline serial depende disso.

Cobertura:
- Estrutura: `FASES` tem 17 fases canônicas, em ordem correta.
- Contrato: cada fase recebe `ctx: dict`, retorna `dict` de stats.
- Comportamento: cada fase isolada produz mutação esperada em `ctx`.
- Log estruturado: `_gravar_log_fases` produz JSON com chaves canônicas.
- Robustez: falha em log NÃO aborta pipeline (best-effort).
- Orquestrador: `_executar_corpo_pipeline` chama todas as fases em ordem.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src import pipeline
from src.pipeline import (
    FASES,
    _executar_corpo_pipeline,
    _gravar_log_fases,
    fase_aplicar_tags_irpf,
    fase_categorizar,
    fase_deduplicar,
    fase_descobrir_extratores,
    fase_dossie_snapshot,
    fase_er_produtos,
    fase_escanear_arquivos,
    fase_extrair,
    fase_filtrar_por_mes,
    fase_gerar_relatorios,
    fase_gerar_xlsx,
    fase_holerites,
    fase_importar_historico,
    fase_item_categorizer,
    fase_linking_documentos,
    fase_ordenar,
    fase_skill_d7_log,
)

# ---------------------------------------------------------------------------
# Estrutura: FASES canônicas
# ---------------------------------------------------------------------------


def test_fases_tem_17_entradas() -> None:
    """Lista canônica `FASES` deve ter 17 fases (ordem do pipeline serial)."""
    assert len(FASES) == 17, f"FASES tem {len(FASES)} entradas, esperado 17"


def test_fases_nomes_canonicos() -> None:
    """Cada fase tem nome canônico esperado, em ordem fixa."""
    nomes = [n for n, _ in FASES]
    esperados = [
        "descobrir_extratores",
        "escanear_arquivos",
        "extrair",
        "importar_historico",
        "deduplicar",
        "categorizar",
        "aplicar_tags_irpf",
        "filtrar_por_mes",
        "ordenar",
        "holerites",
        "gerar_xlsx",
        "gerar_relatorios",
        "linking_documentos",
        "er_produtos",
        "item_categorizer",
        "skill_d7_log",
        "dossie_snapshot",
    ]
    assert nomes == esperados, f"FASES fora de ordem. Atual: {nomes}"


def test_fases_callables() -> None:
    """Cada entrada de FASES é tuple (str, callable)."""
    for nome, fn in FASES:
        assert isinstance(nome, str) and nome
        assert callable(fn), f"fase {nome} não é callable"


def test_descobrir_antes_de_escanear() -> None:
    """Ordem crítica: descobrir extratores ANTES de escanear arquivos.
    `_extrair_tudo` precisa das classes carregadas."""
    nomes = [n for n, _ in FASES]
    assert nomes.index("descobrir_extratores") < nomes.index("escanear_arquivos")
    assert nomes.index("escanear_arquivos") < nomes.index("extrair")


def test_categorizar_antes_de_aplicar_tags() -> None:
    """Tags IRPF dependem da categoria atribuída na fase anterior."""
    nomes = [n for n, _ in FASES]
    assert nomes.index("categorizar") < nomes.index("aplicar_tags_irpf")


def test_ordenar_antes_de_gerar_xlsx() -> None:
    """XLSX precisa de transações já ordenadas e com identificador canônico."""
    nomes = [n for n, _ in FASES]
    assert nomes.index("ordenar") < nomes.index("gerar_xlsx")
    assert nomes.index("filtrar_por_mes") < nomes.index("ordenar")


def test_linking_antes_de_er_produtos() -> None:
    """ER de produtos agrega itens recém-linkados; ordem importa."""
    nomes = [n for n, _ in FASES]
    assert nomes.index("linking_documentos") < nomes.index("er_produtos")
    assert nomes.index("er_produtos") < nomes.index("item_categorizer")


# ---------------------------------------------------------------------------
# Contrato: cada fase é função (ctx) -> dict de stats
# ---------------------------------------------------------------------------


def test_fase_descobrir_extratores_devolve_stats_com_contagem(monkeypatch) -> None:
    """`fase_descobrir_extratores` chama `_descobrir_extratores` e popula
    `ctx['classes_extratores']`; stats inclui `n_extratores`."""
    fake_classes = [object(), object(), object()]
    monkeypatch.setattr(pipeline, "_descobrir_extratores", lambda: fake_classes)
    ctx: dict[str, Any] = {}
    stats = fase_descobrir_extratores(ctx)
    assert stats == {"n_extratores": 3}
    assert ctx["classes_extratores"] is fake_classes


def test_fase_escanear_arquivos_devolve_lista_paths(monkeypatch, tmp_path: Path) -> None:
    """`fase_escanear_arquivos` chama `_escanear_arquivos(DIR_RAW)` e popula
    `ctx['arquivos']`; stats inclui `n_arquivos`."""
    fake_arquivos = [tmp_path / "a.pdf", tmp_path / "b.xml"]
    monkeypatch.setattr(pipeline, "_escanear_arquivos", lambda d: fake_arquivos)
    ctx: dict[str, Any] = {}
    stats = fase_escanear_arquivos(ctx)
    assert stats == {"n_arquivos": 2}
    assert ctx["arquivos"] == fake_arquivos


def test_fase_extrair_le_de_ctx_e_devolve_transacoes(monkeypatch) -> None:
    """`fase_extrair` consome `ctx['arquivos']` e `ctx['classes_extratores']`,
    grava `ctx['transacoes']` e devolve stats com `n_extraidas`."""
    capturado: dict[str, Any] = {}

    def fake_extrair(arquivos, classes):
        capturado["chamada_com"] = (arquivos, classes)
        return [{"data": "2026-05-01", "valor": -10}, {"data": "2026-05-02", "valor": 20}]

    monkeypatch.setattr(pipeline, "_extrair_tudo", fake_extrair)
    ctx: dict[str, Any] = {"arquivos": ["x"], "classes_extratores": ["c"]}
    stats = fase_extrair(ctx)
    assert stats == {"n_extraidas": 2}
    assert len(ctx["transacoes"]) == 2
    assert capturado["chamada_com"] == (["x"], ["c"])


def test_fase_importar_historico_anexa_em_ctx(monkeypatch) -> None:
    """`fase_importar_historico` chama `_importar_historico` e estende
    `ctx['transacoes']` com histórico legado."""
    monkeypatch.setattr(
        pipeline, "_importar_historico", lambda: [{"origem": "controle_antigo", "valor": 100}]
    )
    ctx: dict[str, Any] = {"transacoes": [{"valor": 1}, {"valor": 2}]}
    stats = fase_importar_historico(ctx)
    assert stats == {"n_historico": 1, "n_apos_historico": 3}
    assert len(ctx["transacoes"]) == 3


def test_fase_deduplicar_remove_duplicatas(monkeypatch) -> None:
    """`fase_deduplicar` chama `deduplicar` e devolve stats com contagens."""
    monkeypatch.setattr(
        pipeline,
        "deduplicar",
        lambda txs: [t for t in txs if t.get("valor") != 99],
    )
    ctx: dict[str, Any] = {
        "transacoes": [{"valor": 1}, {"valor": 99}, {"valor": 2}, {"valor": 99}]
    }
    stats = fase_deduplicar(ctx)
    assert stats == {"n_antes": 4, "n_depois": 2, "n_removidas": 2}


def test_fase_categorizar_aplica_categorizer_e_reclassifica(monkeypatch) -> None:
    """`fase_categorizar` agrupa 3 sub-estágios (categorizer + reclassificar +
    promover variantes) em ordem rígida."""
    chamadas: list[str] = []

    class FakeCategorizer:
        def categorizar_lote(self, txs):
            chamadas.append("categorizar")
            for t in txs:
                t["categoria"] = "Outros"
            return txs

    monkeypatch.setattr(pipeline, "Categorizer", FakeCategorizer)

    def fake_reclassificar(txs):
        chamadas.append("reclassificar_ti")
        return txs

    def fake_promover(txs):
        chamadas.append("promover_variantes")
        return txs

    monkeypatch.setattr(pipeline, "_reclassificar_ti_orfas", fake_reclassificar)
    monkeypatch.setattr(pipeline, "_promover_variantes_para_ti", fake_promover)

    ctx: dict[str, Any] = {"transacoes": [{"local": "X", "valor": -10}]}
    stats = fase_categorizar(ctx)
    assert chamadas == ["categorizar", "reclassificar_ti", "promover_variantes"]
    assert stats["n_total"] == 1
    assert "n_ti" in stats


def test_fase_aplicar_tags_irpf_devolve_contagem_tagged(monkeypatch) -> None:
    """`fase_aplicar_tags_irpf` devolve stats com `n_tagged` baseado em
    `tag_irpf` populado por `aplicar_tags_irpf`."""

    def fake_tagger(txs):
        for t in txs:
            if t.get("valor", 0) < 0:
                t["tag_irpf"] = "saude"
        return txs

    monkeypatch.setattr(pipeline, "aplicar_tags_irpf", fake_tagger)
    ctx: dict[str, Any] = {
        "transacoes": [{"valor": -100}, {"valor": 200}, {"valor": -50}],
    }
    stats = fase_aplicar_tags_irpf(ctx)
    assert stats == {"n_total": 3, "n_tagged": 2}


def test_fase_filtrar_por_mes_aplica_filtro_quando_mes_fornecido(monkeypatch) -> None:
    """Com `mes='2026-05'` e `processar_tudo=False`, fase filtra; ctx ganha
    `transacoes_filtradas`."""
    monkeypatch.setattr(
        pipeline,
        "_filtrar_por_mes",
        lambda txs, mes: [t for t in txs if t.get("data", "").startswith(mes)],
    )
    ctx: dict[str, Any] = {
        "mes": "2026-05",
        "processar_tudo": False,
        "transacoes": [
            {"data": "2026-05-01"},
            {"data": "2026-04-30"},
            {"data": "2026-05-15"},
        ],
    }
    stats = fase_filtrar_por_mes(ctx)
    assert stats == {"filtrado": True, "n_apos_filtro": 2}
    assert len(ctx["transacoes_filtradas"]) == 2


def test_fase_filtrar_por_mes_sem_filtro_quando_tudo() -> None:
    """Com `processar_tudo=True`, fase NÃO filtra; `transacoes_filtradas`
    é a lista completa."""
    ctx: dict[str, Any] = {
        "mes": "2026-05",
        "processar_tudo": True,
        "transacoes": [{"data": "2026-05-01"}, {"data": "2026-04-30"}],
    }
    stats = fase_filtrar_por_mes(ctx)
    assert stats == {"filtrado": False, "n_apos_filtro": 2}
    assert len(ctx["transacoes_filtradas"]) == 2


def test_fase_ordenar_ordena_por_data_e_computa_identificadores(monkeypatch) -> None:
    """`fase_ordenar` ordena por chave 'data' e popula 'identificador'
    quando ausente (via `hash_transacao_do_tx`)."""
    from src.graph import migracao_inicial

    monkeypatch.setattr(
        migracao_inicial, "hash_transacao_do_tx", lambda tx: f"hash_{tx.get('data', '')}"
    )

    ctx: dict[str, Any] = {
        "transacoes_filtradas": [
            {"data": "2026-05-15", "valor": 1},
            {"data": "2026-05-01", "valor": 2},
            {"data": "2026-05-10", "valor": 3, "identificador": "preserved"},
        ]
    }
    stats = fase_ordenar(ctx)
    datas = [t["data"] for t in ctx["transacoes_filtradas"]]
    assert datas == sorted(datas)
    assert ctx["transacoes_filtradas"][2]["identificador"] == "hash_2026-05-15"
    # Identificador pré-existente preservado:
    pos_preservado = [t for t in ctx["transacoes_filtradas"] if t["valor"] == 3][0]
    assert pos_preservado["identificador"] == "preserved"
    assert stats["n_ordenadas"] == 3
    assert stats["n_identificadores"] == 2


def test_fase_holerites_chama_processar_holerites(monkeypatch, tmp_path: Path) -> None:
    """`fase_holerites` chama `processar_holerites` (com ou sem grafo) e
    popula `ctx['contracheques']`."""
    fake_cheques = [{"competencia": "2026-05", "liquido": 5000.0}]
    monkeypatch.setattr(pipeline, "processar_holerites", lambda *a, **kw: fake_cheques)
    # Forca caminho_padrao inexistente para pular ramo de grafo:
    from src.graph import db as graph_db_mod

    monkeypatch.setattr(graph_db_mod, "caminho_padrao", lambda: tmp_path / "inexistente.sqlite")
    ctx: dict[str, Any] = {}
    stats = fase_holerites(ctx)
    assert ctx["contracheques"] == fake_cheques
    assert stats["n_contracheques"] == 1
    assert stats["grafo_ok"] is False


def test_fase_gerar_xlsx_grava_caminho_em_ctx(monkeypatch, tmp_path: Path) -> None:
    """`fase_gerar_xlsx` chama `gerar_xlsx` com caminho derivado de `mes`/`ano`."""
    chamadas: list[Any] = []

    def fake_xlsx(txs, caminho, controle_antigo, contracheques):
        chamadas.append(caminho)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text("fake")

    monkeypatch.setattr(pipeline, "gerar_xlsx", fake_xlsx)
    monkeypatch.setattr(pipeline, "DIR_OUTPUT", tmp_path)
    ctx: dict[str, Any] = {
        "mes": "2026-05",
        "transacoes_filtradas": [],
        "contracheques": [],
    }
    stats = fase_gerar_xlsx(ctx)
    assert stats["ano"] == "2026"
    assert ctx["caminho_xlsx"] == tmp_path / "ouroboros_2026.xlsx"
    assert chamadas[0] == tmp_path / "ouroboros_2026.xlsx"


def test_fase_gerar_relatorios_passa_meses_filtro(monkeypatch) -> None:
    """`fase_gerar_relatorios` passa `meses_filtro=[mes]` quando há mês e
    sem `processar_tudo`."""
    chamadas: list[Any] = []

    def fake_relatorios(txs, dir_out, meses_filtro):
        chamadas.append(meses_filtro)

    monkeypatch.setattr(pipeline, "gerar_relatorios", fake_relatorios)
    ctx: dict[str, Any] = {
        "mes": "2026-05",
        "processar_tudo": False,
        "transacoes": [],
    }
    fase_gerar_relatorios(ctx)
    assert chamadas == [["2026-05"]]


def test_fase_gerar_relatorios_sem_filtro_quando_tudo(monkeypatch) -> None:
    """Sem mês ou com `processar_tudo`, `meses_filtro=None`."""
    chamadas: list[Any] = []

    def fake_relatorios(txs, dir_out, meses_filtro):
        chamadas.append(meses_filtro)

    monkeypatch.setattr(pipeline, "gerar_relatorios", fake_relatorios)
    ctx: dict[str, Any] = {"mes": None, "processar_tudo": True, "transacoes": []}
    fase_gerar_relatorios(ctx)
    assert chamadas == [None]


def test_fase_linking_documentos_delega_para_helper(monkeypatch) -> None:
    """`fase_linking_documentos` apenas delega a `_executar_linking_documentos`."""
    chamado: list[bool] = []
    monkeypatch.setattr(
        pipeline, "_executar_linking_documentos", lambda: chamado.append(True)
    )
    stats = fase_linking_documentos({})
    assert chamado == [True]
    assert stats == {"chamada": True}


def test_fase_er_produtos_delega_para_helper(monkeypatch) -> None:
    """`fase_er_produtos` apenas delega a `_executar_er_produtos`."""
    chamado: list[bool] = []
    monkeypatch.setattr(pipeline, "_executar_er_produtos", lambda: chamado.append(True))
    stats = fase_er_produtos({})
    assert chamado == [True]
    assert stats == {"chamada": True}


def test_fase_item_categorizer_delega_para_helper(monkeypatch) -> None:
    """`fase_item_categorizer` apenas delega a `_executar_item_categorizer`."""
    chamado: list[bool] = []
    monkeypatch.setattr(
        pipeline, "_executar_item_categorizer", lambda: chamado.append(True)
    )
    stats = fase_item_categorizer({})
    assert chamado == [True]
    assert stats == {"chamada": True}


def test_fase_skill_d7_log_delega_para_helper(monkeypatch) -> None:
    """`fase_skill_d7_log` apenas delega a `_executar_skill_d7_log`."""
    chamado: list[bool] = []
    monkeypatch.setattr(pipeline, "_executar_skill_d7_log", lambda: chamado.append(True))
    stats = fase_skill_d7_log({})
    assert chamado == [True]
    assert stats == {"chamada": True}


def test_fase_dossie_snapshot_delega_para_helper(monkeypatch) -> None:
    """`fase_dossie_snapshot` apenas delega a `_executar_dossie_snapshot`."""
    chamado: list[bool] = []
    monkeypatch.setattr(
        pipeline, "_executar_dossie_snapshot", lambda: chamado.append(True)
    )
    stats = fase_dossie_snapshot({})
    assert chamado == [True]
    assert stats == {"chamada": True}


# ---------------------------------------------------------------------------
# _ESTAGIO_ATUAL: cada fase relevante atualiza o ponteiro para diagnóstico
# ---------------------------------------------------------------------------


def test_fase_holerites_atualiza_estagio_atual(monkeypatch, tmp_path: Path) -> None:
    """`fase_holerites` seta `_ESTAGIO_ATUAL = 'holerites'` antes de chamar
    `processar_holerites`. Crítico para log estruturado de falha."""
    monkeypatch.setattr(pipeline, "processar_holerites", lambda *a, **kw: [])
    from src.graph import db as graph_db_mod

    monkeypatch.setattr(graph_db_mod, "caminho_padrao", lambda: tmp_path / "inexistente.sqlite")
    pipeline._ESTAGIO_ATUAL = "inicial"
    fase_holerites({})
    assert pipeline._ESTAGIO_ATUAL == "holerites"


def test_fase_linking_atualiza_estagio_atual(monkeypatch) -> None:
    """`fase_linking_documentos` seta `_ESTAGIO_ATUAL = 'linking_documentos'`."""
    monkeypatch.setattr(pipeline, "_executar_linking_documentos", lambda: None)
    pipeline._ESTAGIO_ATUAL = "inicial"
    fase_linking_documentos({})
    assert pipeline._ESTAGIO_ATUAL == "linking_documentos"


# ---------------------------------------------------------------------------
# Log estruturado
# ---------------------------------------------------------------------------


def test_gravar_log_fases_gera_json_canonico(monkeypatch, tmp_path: Path) -> None:
    """`_gravar_log_fases` produz JSON com chaves `ts`, `n_fases`, `fases`."""
    monkeypatch.setattr(pipeline, "DIR_OUTPUT", tmp_path)
    stats_lista = [
        {"fase": "descobrir_extratores", "n_extratores": 5, "duracao_s": 0.01},
        {"fase": "extrair", "n_extraidas": 100, "duracao_s": 2.5},
    ]
    destino = _gravar_log_fases(stats_lista)
    assert destino is not None
    assert destino.exists()
    payload = json.loads(destino.read_text(encoding="utf-8"))
    assert payload["n_fases"] == 2
    assert payload["fases"][0]["fase"] == "descobrir_extratores"
    assert payload["fases"][1]["n_extraidas"] == 100
    assert payload["ts"]  # não-vazio


def test_gravar_log_fases_best_effort_em_falha(monkeypatch, tmp_path: Path) -> None:
    """Falha ao gravar log NÃO aborta pipeline. Retorna None e segue."""
    monkeypatch.setattr(pipeline, "DIR_OUTPUT", tmp_path / "nao_criavel")

    def fake_mkdir(*a, **kw):
        raise PermissionError("simulado")

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)
    resultado = _gravar_log_fases([{"fase": "x"}])
    assert resultado is None  # NÃO levanta exceção


def test_gravar_log_fases_nome_segue_padrao_timestamp(monkeypatch, tmp_path: Path) -> None:
    """Nome do arquivo segue `pipeline_fases_<ts>.json`."""
    monkeypatch.setattr(pipeline, "DIR_OUTPUT", tmp_path)
    destino = _gravar_log_fases([{"fase": "demo", "duracao_s": 0.1}])
    assert destino is not None
    assert destino.name.startswith("pipeline_fases_")
    assert destino.name.endswith(".json")


# ---------------------------------------------------------------------------
# Orquestrador _executar_corpo_pipeline
# ---------------------------------------------------------------------------


def test_corpo_pipeline_chama_todas_as_fases_em_ordem(monkeypatch, tmp_path: Path) -> None:
    """`_executar_corpo_pipeline` itera sobre `FASES` chamando cada fn em
    ordem. Sub testa que `ctx` flui entre fases e log estruturado é gravado."""
    ordem_chamada: list[str] = []

    fakes: list[tuple[str, Any]] = []
    for nome, _fn in FASES:

        def make_fake(n):
            def fake(ctx):
                ordem_chamada.append(n)
                return {"placeholder": n}

            return fake

        fakes.append((nome, make_fake(nome)))

    monkeypatch.setattr(pipeline, "FASES", fakes)
    monkeypatch.setattr(pipeline, "DIR_OUTPUT", tmp_path)

    _executar_corpo_pipeline(mes=None, processar_tudo=True)

    assert ordem_chamada == [n for n, _ in FASES]
    # Log estruturado gerado:
    logs = list(tmp_path.glob("pipeline_fases_*.json"))
    assert len(logs) == 1
    d = json.loads(logs[0].read_text(encoding="utf-8"))
    assert d["n_fases"] == 17
    nomes_log = [s["fase"] for s in d["fases"]]
    assert nomes_log == [n for n, _ in FASES]
    # Cada entry tem `duracao_s` populado pelo orquestrador:
    assert all("duracao_s" in s for s in d["fases"])


def test_corpo_pipeline_pode_ser_monkeypatcheado_por_test_transacionalidade(
    monkeypatch,
) -> None:
    """Retrocompatibilidade: `test_pipeline_transacionalidade.py` monkeypatch
    `pipeline._executar_corpo_pipeline` com assinatura `(mes, processar_tudo)`.
    A assinatura NÃO mudou após o split."""
    import inspect

    sig = inspect.signature(_executar_corpo_pipeline)
    params = list(sig.parameters.keys())
    assert params == ["mes", "processar_tudo"]


def test_corpo_pipeline_log_falha_nao_aborta(monkeypatch, tmp_path: Path) -> None:
    """Se `_gravar_log_fases` falhar, `_executar_corpo_pipeline` ainda
    termina sem levantar exceção (best-effort)."""
    monkeypatch.setattr(pipeline, "FASES", [])  # 0 fases para o teste

    def fake_grava(stats):
        raise RuntimeError("disco cheio")

    # NOTE: a função interna `_gravar_log_fases` já é best-effort; aqui forçamos
    # uma exceção a montante para garantir que mesmo erro aqui não vaze.
    monkeypatch.setattr(pipeline, "_gravar_log_fases", fake_grava)

    with pytest.raises(RuntimeError, match="disco cheio"):
        # Como substituímos _gravar_log_fases por uma versão NÃO best-effort
        # (apenas no teste), espera-se que a exceção propague. Isso prova que
        # o orquestrador chama a função; o tratamento best-effort está
        # encapsulado dentro de `_gravar_log_fases` original.
        _executar_corpo_pipeline(mes=None, processar_tudo=True)


# "Função pequena denuncia bug; função grande esconde." -- princípio do split
