# ruff: noqa: E501
"""Helpers para a Visão Geral canônica (UX-T-01).

Funções puras que leem fontes reais (grafo SQLite, validacao_arquivos.csv,
docs/sprints/) e devolvem estruturas para a renderização HTML em
``paginas/visao_geral.py``. Graceful degradation (ADR-10): se a fonte
estiver ausente, devolvem placeholders ('-' ou listas vazias) sem
inventar dados (regra inviolável #6 do CLAUDE.md).
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


class KpisAgentic(TypedDict):
    arquivos_catalogados: str
    arquivos_delta: str
    paridade_pct: str
    paridade_meta: str
    aguardando_humano: str
    aguardando_breakdown: str
    skills_regredindo: str
    skills_nomes: str


class TimelineEntry(TypedDict):
    when: str  # HH:MM
    glyph: str  # nome do glyph
    what_html: str  # HTML pré-renderizado da mensagem


class SprintAtual(TypedDict):
    sprint_numero: str  # ex.: "Sprint 4"
    periodo: str  # ex.: "2026-04-22 → 2026-05-06"
    titulo: str  # ex.: "VALIDACAO-CSV-01"
    descricao: str
    pill_texto: str  # ex.: "em calibração"
    pill_tipo: str  # d7-calibracao / d7-graduado / d7-regredindo


def _raiz_repo() -> Path:
    return Path(__file__).resolve().parents[3]


def _caminho_grafo() -> Path:
    return _raiz_repo() / "data" / "output" / "grafo.sqlite"


def _caminho_validacao() -> Path:
    return _raiz_repo() / "data" / "output" / "validacao_arquivos.csv"


def calcular_kpis_agentic() -> KpisAgentic:
    """Retorna 4 KPIs agentic-first do mockup canônico.

    - **Arquivos catalogados**: count node WHERE tipo='documento' no grafo.
    - **Paridade ETL ↔ Opus**: % linhas em validacao_arquivos.csv com
      ``valor_etl == valor_opus`` (case-insensitive trim).
    - **Aguardando humano**: count linhas com ``valor_humano`` vazio E
      ``status_etl != status_opus`` (divergência sem decisão).
    - **Skills regredindo**: count tipos onde paridade está abaixo da
      média menos uma escala (placeholder pragmático até skills D7
      registry exportar contagem real).
    """
    grafo_path = _caminho_grafo()
    validacao_path = _caminho_validacao()

    arquivos = "-"
    arquivos_delta = "-"
    if grafo_path.exists():
        try:
            with sqlite3.connect(str(grafo_path)) as conn:
                cur = conn.execute(
                    "SELECT COUNT(*) FROM node WHERE tipo='documento'"
                )
                total = int(cur.fetchone()[0] or 0)
                arquivos = str(total)
                cur = conn.execute("SELECT COUNT(DISTINCT tipo) FROM node WHERE tipo IS NOT NULL")
                tipos = int(cur.fetchone()[0] or 0)
                arquivos_delta = f"{tipos} tipos no grafo"
        except sqlite3.DatabaseError:
            pass

    paridade = "-"
    paridade_meta = "Meta sprint: 90%"
    aguardando = "-"
    aguardando_breakdown = "-"
    skills_regredindo = "-"
    skills_nomes = "-"

    if validacao_path.exists():
        import csv

        with validacao_path.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
        if rows:
            total = len(rows)
            iguais = 0
            divergencias_sem_humano = 0
            baixa_confianca = 0
            por_tipo: dict[str, dict[str, int]] = {}
            for r in rows:
                etl = (r.get("valor_etl") or "").strip().lower()
                opus = (r.get("valor_opus") or "").strip().lower()
                humano = (r.get("valor_humano") or "").strip()
                tipo_arq = (r.get("tipo_arquivo") or "").strip() or "-"
                if etl and opus and etl == opus:
                    iguais += 1
                if etl != opus and not humano:
                    divergencias_sem_humano += 1
                try:
                    confianca = float(r.get("confianca_opus") or 0)
                except ValueError:
                    confianca = 0.0
                if confianca < 0.6 and not humano:
                    baixa_confianca += 1
                por_tipo.setdefault(tipo_arq, {"total": 0, "iguais": 0})
                por_tipo[tipo_arq]["total"] += 1
                if etl and opus and etl == opus:
                    por_tipo[tipo_arq]["iguais"] += 1
            pct = (iguais / total * 100) if total > 0 else 0
            paridade = f"{int(round(pct))}%"
            aguardando = str(divergencias_sem_humano + baixa_confianca)
            aguardando_breakdown = (
                f"{divergencias_sem_humano} divergências · "
                f"{baixa_confianca} baixa confiança"
            )
            # Skills regredindo: tipos com paridade abaixo de 60%.
            regredindo = [
                t
                for t, v in por_tipo.items()
                if v["total"] >= 2 and (v["iguais"] / v["total"] < 0.6)
            ]
            skills_regredindo = str(len(regredindo))
            if regredindo:
                skills_nomes = " · ".join(regredindo[:3])
            else:
                skills_nomes = "nenhum em calibração"

    return {
        "arquivos_catalogados": arquivos,
        "arquivos_delta": arquivos_delta,
        "paridade_pct": paridade,
        "paridade_meta": paridade_meta,
        "aguardando_humano": aguardando,
        "aguardando_breakdown": aguardando_breakdown,
        "skills_regredindo": skills_regredindo,
        "skills_nomes": skills_nomes,
    }


def ler_atividade_recente(n: int = 6) -> list[TimelineEntry]:
    """Lê últimos eventos do grafo SQLite (nodes recentes) para a timeline.

    Estratégia:
      1. Documentos mais recentes (até n//2).
      2. Sprints concluídas mais recentes do diretório docs/sprints/concluidos/.
      3. Eventos de pipeline (logs/) se houver — placeholder para futuro.

    Retorna lista de dicts com ``when``, ``glyph``, ``what_html`` prontos
    para renderização. Vazia se nenhuma fonte disponível.
    """
    import html as _html

    entries: list[TimelineEntry] = []
    grafo_path = _caminho_grafo()
    if grafo_path.exists():
        try:
            with sqlite3.connect(str(grafo_path)) as conn:
                cur = conn.execute(
                    "SELECT id, label, criado_em FROM node "
                    "WHERE tipo='documento' "
                    "ORDER BY criado_em DESC LIMIT ?",
                    (n,),
                )
                for row in cur.fetchall():
                    rid, label, criado = row
                    when = "—"
                    if criado:
                        try:
                            dt = datetime.fromisoformat(str(criado))
                            when = dt.strftime("%d/%m %H:%M")
                        except ValueError:
                            when = str(criado)[:16]
                    sha8 = str(rid)[:8] if rid else "—"
                    label_safe = _html.escape(str(label or "(sem label)"))
                    entries.append(
                        {
                            "when": when,
                            "glyph": "upload",
                            "what_html": (
                                f"<strong>{label_safe}</strong> registrado · "
                                f"<code>{sha8}</code>"
                            ),
                        }
                    )
        except sqlite3.DatabaseError:
            pass

    # Sprint concluida mais recente (não-T para não recursividade).
    concluidos = _raiz_repo() / "docs" / "sprints" / "concluidos"
    if concluidos.exists():
        recentes = sorted(
            concluidos.glob("*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:2]
        for p in recentes:
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
            nome = p.stem.replace("sprint_", "").replace("_", " ").upper()[:50]
            entries.append(
                {
                    "when": mtime.strftime("%d/%m %H:%M"),
                    "glyph": "check",
                    "what_html": (
                        f"Sprint <strong>{_html.escape(nome)}</strong> concluída"
                    ),
                }
            )

    return entries[:n]


def ler_sprint_atual() -> SprintAtual | None:
    """Lê metadata da sprint vigente.

    Procura primeiro spec ativa em ``docs/sprints/backlog/`` (se houver
    apenas uma com mtime recente, considera vigente). Se não, lê a mais
    recente concluída de ``docs/sprints/concluidos/`` para mostrar como
    "última fechada". Devolve ``None`` se não encontrar nada.
    """
    backlog = _raiz_repo() / "docs" / "sprints" / "backlog"
    concluidos = _raiz_repo() / "docs" / "sprints" / "concluidos"

    candidato = None
    if backlog.exists():
        # spec mais recentemente modificada no backlog é a "vigente".
        mds = sorted(
            backlog.glob("*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if mds:
            candidato = mds[0]
            status_pill = "em execução"
            status_tipo = "d7-calibracao"

    if not candidato and concluidos.exists():
        mds = sorted(
            concluidos.glob("*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if mds:
            candidato = mds[0]
            status_pill = "concluída"
            status_tipo = "d7-graduado"

    if not candidato:
        return None

    texto = candidato.read_text(encoding="utf-8")
    titulo_match = re.search(r"title:\s*\"([^\"]+)\"|title:\s*'([^']+)'|title:\s*([^\n]+)", texto)
    titulo = "—"
    if titulo_match:
        titulo = (titulo_match.group(1) or titulo_match.group(2) or titulo_match.group(3) or "—").strip()
    id_match = re.search(r"\bid:\s*([A-Z][A-Z0-9-]+)", texto)
    sprint_id = id_match.group(1) if id_match else candidato.stem.upper()
    desc_match = re.search(r"(?m)^# +Sprint [^—\-]*[—\-]\s*(.+)$", texto)
    descricao = desc_match.group(1).strip() if desc_match else titulo

    # tentar extrair período da spec; senão usar mtime + 14 dias como aproximação
    mtime = datetime.fromtimestamp(candidato.stat().st_mtime, tz=timezone.utc)
    periodo = mtime.strftime("%Y-%m-%d") + " → ?"

    return {
        "sprint_numero": sprint_id,
        "periodo": periodo,
        "titulo": titulo[:60],
        "descricao": descricao[:200],
        "pill_texto": status_pill,
        "pill_tipo": status_tipo,
    }


# Cards canônicos do mockup `_visao-render.js` linha 130. Cada tupla:
# (href, glyph, nome, descricao, label_left, label_right) — valores
# reais virão de calcular_kpis_clusters() em sprint futura; por hora,
# os contadores são lidos do grafo SQLite quando possível.
def montar_clusters_canonicos() -> list[dict[str, str]]:
    """Devolve 6 cards do bloco 'OS 5 CLUSTERS' do mockup canônico.

    Contadores lidos do grafo quando disponível; fallback '-'.
    """
    grafo_path = _caminho_grafo()
    contadores: dict[str, int] = {}
    if grafo_path.exists():
        try:
            with sqlite3.connect(str(grafo_path)) as conn:
                cur = conn.execute(
                    "SELECT tipo, COUNT(*) FROM node GROUP BY tipo"
                )
                for tipo, count in cur.fetchall():
                    if tipo:
                        contadores[str(tipo)] = int(count)
        except sqlite3.DatabaseError:
            pass

    fmt = lambda k: str(contadores.get(k, "-"))  # noqa: E731

    return [
        {
            "href": "?cluster=Inbox&tab=Inbox",
            "glyph": "inbox",
            "nome": "Inbox",
            "descricao": "Entrada de dados. Drop por sha8.",
            "stat1_label": "aguardando",
            "stat1_value": "-",
            "stat2_label": "na fila",
            "stat2_value": "-",
        },
        {
            "href": "?cluster=Finan%C3%A7as&tab=Extrato",
            "glyph": "wallet",
            "nome": "Finanças",
            "descricao": "Extrato, contas, pagamentos, projeções.",
            "stat1_label": "contas",
            "stat1_value": fmt("conta"),
            "stat2_label": "txns",
            "stat2_value": _fmt_compact(contadores.get("transacao", 0)),
        },
        {
            "href": "?cluster=Documentos&tab=Busca+Global",
            "glyph": "file",
            "nome": "Documentos",
            "descricao": "Busca, catálogo, completude, revisor, validação.",
            "stat1_label": "arquivos",
            "stat1_value": fmt("documento"),
            "stat2_label": "tipos",
            "stat2_value": str(len(contadores)),
        },
        {
            "href": "?cluster=An%C3%A1lise&tab=Categorias",
            "glyph": "sankey",
            "nome": "Análise",
            "descricao": "Categorias, multi-perspectiva, IRPF.",
            "stat1_label": "categorias",
            "stat1_value": fmt("categoria"),
            "stat2_label": "tags IRPF",
            "stat2_value": fmt("tag_irpf"),
        },
        {
            "href": "?cluster=Metas&tab=Metas",
            "glyph": "target",
            "nome": "Metas",
            "descricao": "Financeiras + operacionais (skills D7).",
            "stat1_label": "fornecedores",
            "stat1_value": _fmt_compact(contadores.get("fornecedor", 0)),
            "stat2_label": "períodos",
            "stat2_value": fmt("periodo"),
        },
        {
            "href": "?cluster=Sistema&tab=Skills+D7",
            "glyph": "sigma",
            "nome": "Sistema",
            "descricao": "Skills D7, runs, ADRs, configuração.",
            "stat1_label": "ADRs",
            "stat1_value": "—",
            "stat2_label": "skills",
            "stat2_value": "—",
        },
    ]


def _fmt_compact(n: int) -> str:
    """Formata inteiro grande como compacto (1.2k, 3.4M)."""
    if n is None or n == 0:
        return "0"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"{n/1_000:.1f}k".replace(".0k", "k")
    return str(n)


# "Cada peça é o índice do todo." -- Heráclito
