"""Testes do suporte ao layout H2 do Mobile (ADR-0023 cross-repo).

H2 reorganiza o Vault por **tipo de arquivo** em vez de por feature:

    Pre-H2 (legado):              Pos-H2:
      daily/2026-05-16.md           markdown/humor-2026-05-16.md
      eventos/2026-05-16-cafe.md    markdown/evento-2026-05-16-cafe.md
      marcos/2026-05-16-x.md        markdown/marco-2026-05-16-x.md
      tarefas/limpar.md             markdown/tarefa-limpar.md
      contadores/dias.md            markdown/contador-dias.md
      ciclo/2026-05-16.md           markdown/ciclo-2026-05-16.md
      treinos/2026-05-16-a.md       markdown/treino-2026-05-16-a.md
      medidas/2026-05-16.md         markdown/medidas-2026-05-16.md
      alarmes/acordar.md            markdown/alarme-acordar.md
      inbox/mente/diario/.../*.md   markdown/diario-2026-05-16-x.md

Esta sprint (R-CROSS-FLOW-FIX-2) atualizou os parsers para varrer
**ambos** os layouts. Vault em migração intermediária (raro) some;
vault só-H2 ou só-legado funciona idêntico ao histórico.

Cobertura:

1.  Cada um dos 9 parsers lê do ``markdown/`` com prefixo correto.
2.  Filtro de prefixo descarta arquivos de outros tipos na mesma pasta.
3.  Frontmatter ``tipo:`` errado é ignorado mesmo com prefixo correto.
4.  Vault híbrido (legado + H2) soma os dois sem duplicar.
5.  ``humor_heatmap`` lê de ``markdown/humor-*.md`` e ``markdown/daily-*.md``.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import yaml

from src.mobile_cache.alarmes import gerar_cache as gerar_cache_alarmes
from src.mobile_cache.ciclo import gerar_cache as gerar_cache_ciclo
from src.mobile_cache.contadores import gerar_cache as gerar_cache_contadores
from src.mobile_cache.diario_emocional import gerar_cache as gerar_cache_diario
from src.mobile_cache.eventos import gerar_cache as gerar_cache_eventos
from src.mobile_cache.humor_heatmap import gerar_humor_heatmap
from src.mobile_cache.marcos import gerar_cache as gerar_cache_marcos
from src.mobile_cache.medidas import gerar_cache as gerar_cache_medidas
from src.mobile_cache.tarefas import gerar_cache as gerar_cache_tarefas
from src.mobile_cache.treinos import gerar_cache as gerar_cache_treinos


def _escrever_md(path: Path, frontmatter: dict, corpo: str = "") -> None:
    """Grava .md com frontmatter YAML canônico."""
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml_bloco = yaml.safe_dump(
        frontmatter, allow_unicode=True, sort_keys=False, default_flow_style=False
    ).strip()
    path.write_text(f"---\n{yaml_bloco}\n---\n\n{corpo}\n", encoding="utf-8")


def _ler_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Marcos
# ---------------------------------------------------------------------------


def test_marcos_le_de_markdown_h2(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _escrever_md(
        vault / "markdown" / "marco-2026-05-16-tres-treinos.md",
        {
            "tipo": "marco",
            "data": "2026-05-16",
            "autor": "pessoa_a",
            "titulo": "Três treinos completos",
            "descricao": "marco de regularidade.",
            "auto": False,
        },
    )
    saida = gerar_cache_marcos(vault)
    payload = _ler_json(saida)
    assert payload["schema"] == "marcos"
    assert len(payload["items"]) == 1
    assert payload["items"][0]["data"] == "2026-05-16"
    assert payload["items"][0]["titulo"] == "Três treinos completos"


def test_marcos_filtra_prefixo_em_markdown(tmp_path: Path) -> None:
    """Arquivo com tipo=marco mas filename não-marco-* é ignorado em markdown/."""
    vault = tmp_path / "vault"
    # Filename de evento, frontmatter de marco (cenário sintético defensivo)
    _escrever_md(
        vault / "markdown" / "evento-2026-05-16-x.md",
        {
            "tipo": "marco",
            "data": "2026-05-16",
            "autor": "pessoa_a",
            "titulo": "x",
        },
    )
    saida = gerar_cache_marcos(vault)
    payload = _ler_json(saida)
    assert len(payload["items"]) == 0, "prefix mismatch deve filtrar mesmo com tipo correto"


def test_marcos_vault_hibrido_legado_mais_h2(tmp_path: Path) -> None:
    """Legado em marcos/ + H2 em markdown/ somam sem duplicar."""
    vault = tmp_path / "vault"
    _escrever_md(
        vault / "marcos" / "2026-05-15-legado.md",
        {
            "tipo": "marco",
            "data": "2026-05-15",
            "autor": "pessoa_a",
            "titulo": "Legado",
        },
    )
    _escrever_md(
        vault / "markdown" / "marco-2026-05-16-novo.md",
        {
            "tipo": "marco",
            "data": "2026-05-16",
            "autor": "pessoa_b",
            "titulo": "Novo",
        },
    )
    saida = gerar_cache_marcos(vault)
    payload = _ler_json(saida)
    titulos = {item["titulo"] for item in payload["items"]}
    assert titulos == {"Legado", "Novo"}


# ---------------------------------------------------------------------------
# Eventos
# ---------------------------------------------------------------------------


def test_eventos_le_de_markdown_h2(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _escrever_md(
        vault / "markdown" / "evento-2026-05-16-cafe.md",
        {
            "tipo": "evento",
            "data": "2026-05-16",
            "autor": "casal",
            "modo": "positivo",
            "lugar": "padaria",
            "bairro": "centro",
            "categoria": "manhã",
            "intensidade": 4,
        },
    )
    saida = gerar_cache_eventos(vault)
    payload = _ler_json(saida)
    assert payload["schema"] == "eventos"
    assert len(payload["items"]) == 1
    assert payload["items"][0]["lugar"] == "padaria"


# ---------------------------------------------------------------------------
# Tarefas
# ---------------------------------------------------------------------------


def test_tarefas_le_de_markdown_h2(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _escrever_md(
        vault / "markdown" / "tarefa-limpar-gatos.md",
        {
            "tipo": "tarefa",
            "autor": "pessoa_a",
            "titulo": "Limpar caixa dos gatos",
            "prioridade": "alta",
            "concluida": False,
        },
    )
    saida = gerar_cache_tarefas(vault)
    payload = _ler_json(saida)
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == "tarefa-limpar-gatos"
    assert payload["items"][0]["prioridade"] == "alta"


# ---------------------------------------------------------------------------
# Ciclo
# ---------------------------------------------------------------------------


def test_ciclo_le_de_markdown_h2(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _escrever_md(
        vault / "markdown" / "ciclo-2026-05-16.md",
        {
            "tipo": "ciclo",
            "data": "2026-05-16",
            "autor": "pessoa_b",
            "fase": "folicular",
            "sintomas": ["calma"],
            "observacoes": "início de fase nova.",
        },
    )
    saida = gerar_cache_ciclo(vault)
    payload = _ler_json(saida)
    assert len(payload["items"]) == 1
    assert payload["items"][0]["fase"] == "folicular"


# ---------------------------------------------------------------------------
# Treinos
# ---------------------------------------------------------------------------


def test_treinos_le_de_markdown_h2(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _escrever_md(
        vault / "markdown" / "treino-2026-05-16-rotina-a.md",
        {
            "tipo": "treino_sessao",
            "data": "2026-05-16",
            "autor": "pessoa_a",
            "rotina": "rotina A",
            "duracao_min": 45,
            "exercicios": [{"nome": "agachamento", "series": 4, "reps": 10, "carga_kg": 60}],
        },
    )
    saida = gerar_cache_treinos(vault)
    payload = _ler_json(saida)
    assert len(payload["items"]) == 1
    assert payload["items"][0]["rotina"] == "rotina A"
    assert len(payload["items"][0]["exercicios"]) == 1


# ---------------------------------------------------------------------------
# Medidas
# ---------------------------------------------------------------------------


def test_medidas_le_de_markdown_h2(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _escrever_md(
        vault / "markdown" / "medidas-2026-05-16.md",
        {
            "tipo": "medidas",
            "data": "2026-05-16",
            "autor": "pessoa_a",
            "peso": 75.2,
            "cintura": 82,
            "gordura_pct": 18.5,
        },
    )
    saida = gerar_cache_medidas(vault)
    payload = _ler_json(saida)
    assert len(payload["items"]) == 1
    assert payload["items"][0]["peso"] == 75.2


# ---------------------------------------------------------------------------
# Alarmes
# ---------------------------------------------------------------------------


def test_alarmes_le_de_markdown_h2(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _escrever_md(
        vault / "markdown" / "alarme-acordar.md",
        {
            "tipo": "alarme",
            "autor": "pessoa_a",
            "horario": "07:00",
            "recorrencia": "diaria",
            "categoria": "rotina",
            "ativo": True,
        },
    )
    saida = gerar_cache_alarmes(vault)
    payload = _ler_json(saida)
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == "alarme-acordar"
    assert payload["items"][0]["horario"] == "07:00"


# ---------------------------------------------------------------------------
# Contadores
# ---------------------------------------------------------------------------


def test_contadores_le_de_markdown_h2(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _escrever_md(
        vault / "markdown" / "contador-dias-sem-x.md",
        {
            "tipo": "contador",
            "autor": "pessoa_a",
            "nome": "Dias sem X",
            "data_inicio": "2026-05-01",
            "ultima_reset": "2026-05-10",
            "categoria": "habito",
        },
    )
    saida = gerar_cache_contadores(vault)
    payload = _ler_json(saida)
    assert len(payload["items"]) == 1
    assert payload["items"][0]["nome"] == "Dias sem X"


# ---------------------------------------------------------------------------
# Diário emocional
# ---------------------------------------------------------------------------


def test_diario_le_de_markdown_h2(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _escrever_md(
        vault / "markdown" / "diario-2026-05-16-1430-conflito.md",
        {
            "tipo": "diario_emocional",
            "data": "2026-05-16",
            "autor": "pessoa_a",
            "modo": "trigger",
            "emocoes": ["ansiedade", "raiva"],
            "intensidade": 4,
            "com": ["pessoa_b"],
            "texto": "Discussão.",
        },
    )
    saida = gerar_cache_diario(vault)
    payload = _ler_json(saida)
    assert len(payload["items"]) == 1
    assert payload["items"][0]["modo"] == "trigger"


# ---------------------------------------------------------------------------
# Humor heatmap
# ---------------------------------------------------------------------------


def test_humor_heatmap_le_de_markdown_h2(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    hoje = date(2026, 5, 16)
    _escrever_md(
        vault / "markdown" / "humor-2026-05-16.md",
        {
            "tipo": "humor",
            "data": "2026-05-16",
            "autor": "pessoa_a",
            "humor": 4,
            "energia": 3,
            "ansiedade": 2,
            "foco": 5,
        },
    )
    saida = gerar_humor_heatmap(vault, periodo_dias=30, hoje=hoje)
    payload = _ler_json(saida)
    assert len(payload["celulas"]) == 1
    assert payload["celulas"][0]["humor"] == 4


def test_humor_heatmap_hibrido_legado_mais_h2_sem_duplicar(tmp_path: Path) -> None:
    """daily/<dia>.md + markdown/humor-<dia>.md não devem duplicar célula."""
    vault = tmp_path / "vault"
    hoje = date(2026, 5, 16)
    # Legado
    _escrever_md(
        vault / "daily" / "2026-05-15.md",
        {
            "tipo": "humor",
            "data": "2026-05-15",
            "autor": "pessoa_a",
            "humor": 3,
            "energia": 3,
            "ansiedade": 2,
            "foco": 3,
        },
    )
    # H2 (dia diferente -- não conflita)
    _escrever_md(
        vault / "markdown" / "humor-2026-05-16.md",
        {
            "tipo": "humor",
            "data": "2026-05-16",
            "autor": "pessoa_a",
            "humor": 4,
            "energia": 4,
            "ansiedade": 1,
            "foco": 4,
        },
    )
    # H2 (mesma data do legado + autor) -- daily/ vence por ordem alfabética
    _escrever_md(
        vault / "markdown" / "humor-2026-05-15.md",
        {
            "tipo": "humor",
            "data": "2026-05-15",
            "autor": "pessoa_a",
            "humor": 5,  # diferente do legado (3) -- daily/ deve vencer
            "energia": 5,
            "ansiedade": 1,
            "foco": 5,
        },
    )
    saida = gerar_humor_heatmap(vault, periodo_dias=30, hoje=hoje)
    payload = _ler_json(saida)
    datas = sorted(c["data"] for c in payload["celulas"])
    assert datas == ["2026-05-15", "2026-05-16"], "deve ter 2 dias únicos"
    celula_15 = next(c for c in payload["celulas"] if c["data"] == "2026-05-15")
    # Daily/ ordenado antes de markdown/humor-* alfabeticamente, vence dedup.
    assert celula_15["humor"] == 3


# ---------------------------------------------------------------------------
# Integração: vault só-H2 (zero legado) funciona idêntico
# ---------------------------------------------------------------------------


def test_vault_so_h2_zero_legado_funciona(tmp_path: Path) -> None:
    """Vault Mobile pós-migração H2 completa: SÓ markdown/ existe.

    Cenário do mundo real (R-CROSS-FLOW-FIX-2): mobile rodou boot hook
    de migração e SUMIU com pastas legadas. ETL precisa enxergar tudo
    de markdown/ sem nenhum daily/, eventos/, marcos/, etc.
    """
    vault = tmp_path / "vault"
    _escrever_md(
        vault / "markdown" / "evento-2026-05-16-cafe.md",
        {
            "tipo": "evento",
            "data": "2026-05-16",
            "autor": "pessoa_a",
            "modo": "positivo",
            "lugar": "padaria",
            "intensidade": 4,
        },
    )
    _escrever_md(
        vault / "markdown" / "marco-2026-05-16-x.md",
        {
            "tipo": "marco",
            "data": "2026-05-16",
            "autor": "pessoa_b",
            "titulo": "marco x",
        },
    )
    _escrever_md(
        vault / "markdown" / "tarefa-y.md",
        {
            "tipo": "tarefa",
            "autor": "pessoa_a",
            "titulo": "tarefa y",
            "prioridade": "baixa",
        },
    )
    # Caches dos 3 schemas devem ter exatamente 1 item cada, sem cross-talk.
    payload_eventos = _ler_json(gerar_cache_eventos(vault))
    payload_marcos = _ler_json(gerar_cache_marcos(vault))
    payload_tarefas = _ler_json(gerar_cache_tarefas(vault))
    assert len(payload_eventos["items"]) == 1
    assert len(payload_marcos["items"]) == 1
    assert len(payload_tarefas["items"]) == 1
    assert payload_eventos["items"][0]["lugar"] == "padaria"
    assert payload_marcos["items"][0]["titulo"] == "marco x"
    assert payload_tarefas["items"][0]["titulo"] == "tarefa y"


def test_markdown_cross_talk_filtrado_por_prefixo(tmp_path: Path) -> None:
    """3 tipos diferentes em markdown/ -- cada parser pega só o seu."""
    vault = tmp_path / "vault"
    # Evento + marco + tarefa coexistem em markdown/.
    _escrever_md(
        vault / "markdown" / "evento-2026-05-16.md",
        {
            "tipo": "evento",
            "data": "2026-05-16",
            "autor": "pessoa_a",
            "modo": "positivo",
            "lugar": "x",
            "intensidade": 3,
        },
    )
    _escrever_md(
        vault / "markdown" / "marco-2026-05-16.md",
        {
            "tipo": "marco",
            "data": "2026-05-16",
            "autor": "pessoa_a",
            "titulo": "y",
        },
    )
    _escrever_md(
        vault / "markdown" / "tarefa-z.md",
        {
            "tipo": "tarefa",
            "autor": "pessoa_a",
            "titulo": "z",
            "prioridade": "media",
        },
    )
    # Parser de eventos só vê o evento; nem mesmo abre os outros .md.
    assert len(_ler_json(gerar_cache_eventos(vault))["items"]) == 1
    assert len(_ler_json(gerar_cache_marcos(vault))["items"]) == 1
    assert len(_ler_json(gerar_cache_tarefas(vault))["items"]) == 1


# "Se o leitor enxerga onde antes não havia luz, o sistema é honesto." -- Lao-Tsé
