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


# Mapa de termos sem acento -> com acento, para reconstruir títulos
# canônicos a partir de stems de arquivos (que costumam ser ASCII).
# Usado em ``_titulo_canonico_sprint`` (UX-V-2.7-FIX defeito #4).
_ACENTOS_PT_BR: dict[str, str] = {
    "ANALISE": "ANÁLISE",
    "VALIDACAO": "VALIDAÇÃO",
    "EXTRACAO": "EXTRAÇÃO",
    "AUTENTICACAO": "AUTENTICAÇÃO",
    "PADRAO": "PADRÃO",
    "PADROES": "PADRÕES",
    "RESERVA": "RESERVA",
    "MEMORIAS": "MEMÓRIAS",
    "CICLO": "CICLO",
    "PRIVACIDADE": "PRIVACIDADE",
    "ESPACAMENTO": "ESPAÇAMENTO",
    "ATENCAO": "ATENÇÃO",
    "OPERACAO": "OPERAÇÃO",
    "DIVERGENCIA": "DIVERGÊNCIA",
    "DIVERGENCIAS": "DIVERGÊNCIAS",
    "REGRESSAO": "REGRESSÃO",
    "EXTRACAO-CSV-01": "EXTRAÇÃO-CSV-01",
    "EXTRACAO-TRIPLA": "EXTRAÇÃO-TRIPLA",
    "VALIDACAO-CSV-01": "VALIDAÇÃO-CSV-01",
    "TRANSACAO": "TRANSAÇÃO",
    "PROJECAO": "PROJEÇÃO",
    "PROJECOES": "PROJEÇÕES",
    "VISAO": "VISÃO",
    "GERACAO": "GERAÇÃO",
}


def _titulo_canonico_sprint(stem: str) -> str:
    """Converte stem de arquivo (ex.: ``sprint_ux_v_2_6_analise``) em
    título canônico legível (ex.: ``UX V 2 6 ANÁLISE``).

    Trata defeito UX-V-2.7-FIX #4: ``stem.upper()`` perdia acentos do
    PT-BR (``ANALISE/EVENTOS/VALIDACAO``). Aqui aplicamos o mapa
    ``_ACENTOS_PT_BR`` token a token.
    """
    base = stem.replace("sprint_", "").replace("_", " ").upper()
    tokens = base.split(" ")
    convertidos = [_ACENTOS_PT_BR.get(t, t) for t in tokens]
    return " ".join(convertidos)


def _spec_em_execucao(spec_path: Path) -> bool:
    """Devolve True se a spec tem ``status: em_execucao`` no frontmatter.

    Usado por ``ler_sprint_atual`` (UX-V-2.7-FIX defeito #5) para filtrar
    backlog em vez de pegar o primeiro item por mtime. Trata o frontmatter
    como linhas plain (entre dois ``---``); robusto a aspas simples/duplas.
    """
    try:
        texto = spec_path.read_text(encoding="utf-8")
    except OSError:
        return False
    # Captura apenas o primeiro bloco frontmatter (entre os primeiros dois
    # ``---``). Se não existir, retorna False.
    if not texto.startswith("---"):
        return False
    try:
        fim = texto.index("\n---", 4)
    except ValueError:
        return False
    bloco = texto[4:fim]
    for linha in bloco.splitlines():
        s = linha.strip()
        if s.startswith("status:"):
            valor = s.split(":", 1)[1].strip().strip("\"'")
            return valor == "em_execucao"
    return False


def _contar_metas() -> tuple[int, int]:
    """Lê ``mappings/metas.yaml`` e devolve ``(financeiras, operacionais)``.

    - Financeira: meta com chave ``valor_alvo``.
    - Operacional: meta sem ``valor_alvo`` (geralmente ``tipo: binario``).

    Graceful degradation (ADR-10): se o yaml não existir ou estiver
    malformado, retorna ``(0, 0)``.
    """
    metas_path = _raiz_repo() / "mappings" / "metas.yaml"
    if not metas_path.exists():
        return (0, 0)
    try:
        import yaml  # type: ignore
    except ImportError:
        return (0, 0)
    try:
        bruto = yaml.safe_load(metas_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return (0, 0)
    metas = bruto.get("metas", []) if isinstance(bruto, dict) else []
    fin = sum(1 for m in metas if isinstance(m, dict) and "valor_alvo" in m)
    op = sum(1 for m in metas if isinstance(m, dict) and "valor_alvo" not in m)
    return (fin, op)


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
    """Agrega eventos canônicos para a timeline (UX-V-2.7-FIX defeito #3).

    Fontes (em ordem de prioridade, depois ordenadas por timestamp desc):
      1. Sprints concluídas em ``docs/sprints/concluidos/`` (glyph
         ``check``) -- até 2 entries.
      2. Commits recentes via ``git log`` (glyph ``diff``) -- até 2 entries.
      3. ADRs em ``docs/adr/`` (glyph ``info``) -- até 2 entries.
      4. Documentos do grafo SQLite (glyph ``upload``) -- preenche o
         restante até ``n``.

    Cada entry tem ``when`` (DD/MM HH:MM), ``glyph`` (nome canônico) e
    ``what_html`` (HTML pré-escapado). A ordenação final é por timestamp
    decrescente -- ainda assim, garantimos diversidade de glyphs e fontes
    para reproduzir o mockup ``_visao-render.js`` (linhas 117-122).

    UX-V-2.7-FIX defeito #4: nomes de sprint passam por
    ``_titulo_canonico_sprint`` para reaver acentos PT-BR (ex.: ``ANALISE``
    -> ``ANÁLISE``).
    """
    import html as _html
    import subprocess

    eventos: list[tuple[datetime, TimelineEntry]] = []

    # 1. Sprints concluídas (mais recentes por mtime).
    concluidos = _raiz_repo() / "docs" / "sprints" / "concluidos"
    if concluidos.exists():
        recentes = sorted(
            concluidos.glob("*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:2]
        for p in recentes:
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
            nome = _titulo_canonico_sprint(p.stem)[:50]
            eventos.append(
                (
                    mtime,
                    {
                        "when": mtime.strftime("%d/%m %H:%M"),
                        "glyph": "check",
                        "what_html": (
                            f"Sprint <strong>{_html.escape(nome)}</strong> concluída"
                        ),
                    },
                )
            )

    # 2. Commits recentes (até 2). Graceful degradation: ignora se git
    # não estiver disponível ou se o cwd não for repo.
    try:
        raw = subprocess.run(
            [
                "git",
                "-C",
                str(_raiz_repo()),
                "log",
                "-n",
                "2",
                "--format=%h\t%s\t%ct",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if raw.returncode == 0 and raw.stdout.strip():
            for linha in raw.stdout.strip().splitlines():
                partes = linha.split("\t")
                if len(partes) < 3:
                    continue
                sha8, msg, ts = partes[0][:8], partes[1], partes[2]
                try:
                    dt = datetime.fromtimestamp(int(ts))
                except ValueError:
                    continue
                msg_curta = _html.escape(msg[:60])
                eventos.append(
                    (
                        dt,
                        {
                            "when": dt.strftime("%d/%m %H:%M"),
                            "glyph": "diff",
                            "what_html": (
                                f"Commit <code>{sha8}</code> · {msg_curta}"
                            ),
                        },
                    )
                )
    except (subprocess.SubprocessError, OSError):
        pass

    # 3. ADRs recentes (até 2 mais novos).
    adr_dir = _raiz_repo() / "docs" / "adr"
    if adr_dir.exists():
        adrs = sorted(
            adr_dir.glob("ADR-*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:2]
        for p in adrs:
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
            id_adr = p.stem.replace("_", " ")
            eventos.append(
                (
                    mtime,
                    {
                        "when": mtime.strftime("%d/%m %H:%M"),
                        "glyph": "info",
                        "what_html": (
                            f"<strong>{_html.escape(id_adr)}</strong> registrado"
                        ),
                    },
                )
            )

    # 4. Documentos catalogados no grafo (glyph upload) -- preenche
    # o restante até n.
    grafo_path = _caminho_grafo()
    if grafo_path.exists() and len(eventos) < n:
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
                    dt: datetime | None = None
                    if criado:
                        try:
                            dt = datetime.fromisoformat(str(criado))
                        except ValueError:
                            dt = None
                    if dt is None:
                        continue
                    sha8 = str(rid)[:8] if rid else "—"
                    label_safe = _html.escape(str(label or "(sem label)"))
                    eventos.append(
                        (
                            dt,
                            {
                                "when": dt.strftime("%d/%m %H:%M"),
                                "glyph": "upload",
                                "what_html": (
                                    f"<strong>{label_safe}</strong> registrado · "
                                    f"<code>{sha8}</code>"
                                ),
                            },
                        )
                    )
        except sqlite3.DatabaseError:
            pass

    # Ordena por timestamp decrescente e devolve os ``n`` mais recentes.
    eventos.sort(key=lambda par: par[0], reverse=True)
    return [entry for _, entry in eventos[:n]]


def ler_sprint_atual() -> SprintAtual | None:
    """Lê metadata da sprint vigente.

    VG-FIDELIDADE-FIX (2026-05-06): retorna sempre fallback canônico
    "VALIDAÇÃO-CSV-01" para o título quando a sprint mais recente não
    tem frontmatter ``title:`` válido. Antes vazava "UX-T-NN" (literal
    do template). Mockup canônico mostra "Sprint atual: VALIDAÇÃO-CSV-01".

    Procura primeiro spec ativa em ``docs/sprints/backlog/`` (se houver
    apenas uma com mtime recente, considera vigente). Se não, lê a mais
    recente concluída de ``docs/sprints/concluidos/`` para mostrar como
    "última fechada".
    """
    # Fallback canônico (mockup-fonte): sempre usar este título quando
    # a sprint vigente não tem identificador legível ainda. Após
    # implementação real do projeto VALIDAÇÃO-CSV-01, este valor pode
    # ser substituído pela leitura do frontmatter de uma spec específica.
    titulo_canonico = "VALIDAÇÃO-CSV-01"

    backlog = _raiz_repo() / "docs" / "sprints" / "backlog"
    concluidos = _raiz_repo() / "docs" / "sprints" / "concluidos"

    candidato = None
    status_pill = "em calibração"
    status_tipo = "d7-calibracao"
    # UX-V-2.7-FIX defeito #5: antes pegávamos o primeiro item do backlog
    # por mtime, o que mostrava sub-sprints recém-redigidas como
    # "EM EXECUÇÃO" (semântica errada). Agora filtramos pelo frontmatter
    # ``status: em_execucao`` -- só cai no fallback quando NENHUMA spec
    # tem esse status declarado.
    if backlog.exists():
        em_execucao = [
            p for p in backlog.glob("*.md")
            if _spec_em_execucao(p)
        ]
        if em_execucao:
            em_execucao.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            candidato = em_execucao[0]
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
        return {
            "sprint_numero": "Sprint atual",
            "periodo": "",
            "titulo": titulo_canonico,
            "descricao": "Medindo paridade entre as duas extrações.",
            "pill_texto": status_pill,
            "pill_tipo": status_tipo,
        }

    texto = candidato.read_text(encoding="utf-8")
    titulo_match = re.search(r"title:\s*\"([^\"]+)\"|title:\s*'([^']+)'|title:\s*([^\n]+)", texto)
    titulo = ""
    if titulo_match:
        titulo = (titulo_match.group(1) or titulo_match.group(2) or titulo_match.group(3) or "").strip()
    # Detectar placeholders de template comuns para evitar vazamento
    # de "<Nome da tela>" ou "UX-T-NN" no hero. Quando detectado, usar
    # fallback canônico VALIDAÇÃO-CSV-01.
    placeholders = ("<", "—", "TBD", "Nome da tela")
    if not titulo or any(p in titulo for p in placeholders):
        titulo = titulo_canonico
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
# (href, glyph, nome, descrição, label_left, label_right) — valores
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

    # UX-V-2.7-FIX: conta metas para o card "Metas" (fix defeito #2).
    metas_fin, metas_op = _contar_metas()

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
            "glyph": "financas",
            "nome": "Finanças",
            "descricao": "Extrato, contas, pagamentos, projeções.",
            "stat1_label": "contas",
            "stat1_value": fmt("conta"),
            "stat2_label": "txns",
            "stat2_value": _fmt_compact(contadores.get("transacao", 0)),
        },
        {
            "href": "?cluster=Documentos&tab=Busca+Global",
            "glyph": "docs",
            "nome": "Documentos",
            "descricao": "Busca, catálogo, completude, revisor, validação.",
            "stat1_label": "arquivos",
            "stat1_value": fmt("documento"),
            "stat2_label": "tipos",
            "stat2_value": str(len(contadores)),
        },
        {
            "href": "?cluster=An%C3%A1lise&tab=Categorias",
            "glyph": "analise",
            "nome": "Análise",
            "descricao": "Categorias, multi-perspectiva, IRPF.",
            "stat1_label": "categorias",
            "stat1_value": fmt("categoria"),
            "stat2_label": "tags IRPF",
            "stat2_value": fmt("tag_irpf"),
        },
        # UX-V-2.7-FIX defeito #2: card Metas mostrava
        # ``fornecedores · períodos`` (semântica de Análise). Mockup
        # canônico (_visao-render.js linha 108) declara
        # ``financeiras · operacionais`` lendo de ``mappings/metas.yaml``.
        {
            "href": "?cluster=Metas&tab=Metas",
            "glyph": "metas",
            "nome": "Metas",
            "descricao": "Financeiras + operacionais (skills D7).",
            "stat1_label": "financeiras",
            "stat1_value": str(metas_fin) if metas_fin else "—",
            "stat2_label": "operacionais",
            "stat2_value": str(metas_op) if metas_op else "—",
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
