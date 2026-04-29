"""Lógica pura do Revisor (sem dependência streamlit).

Extraído de ``revisor.py`` na Sprint ANTI-MIGUE-08 para manter a pagina
abaixo de 800 linhas. Re-exportado por ``revisor`` para preservar
contratos públicos (testes importam direto via
``from src.dashboard.paginas.revisor import garantir_schema``).

Conteúdo: regex de mascaramento PII, schema SQLite, persistência de
marcações (UPSERT), exportação ground-truth CSV (3 e 4-way), detecção
de padrões recorrentes e geração de relatório Markdown.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path

# Limite mínimo para acionar sugestão de patch (3+ pendências com mesma
# dimensão errada -> padrão recorrente). Mantido aqui para que a lógica
# pura seja independente da UI.
LIMITE_PADRAO_RECORRENTE: int = 3


# Mascaramento PII (LGPD) antes de gravar relatório em disco.
_REGEX_CPF = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
_REGEX_CNPJ = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
_REGEX_CPF_CRU = re.compile(r"(?<!\d)\d{11}(?!\d)")
_REGEX_CNPJ_CRU = re.compile(r"(?<!\d)\d{14}(?!\d)")


def mascarar_pii(texto: str) -> str:
    """Mascara CPFs e CNPJs em texto livre (regex formatado e cru).

    LGPD-safe: relatório local de revisão pode ser exportado/compartilhado;
    melhor garantir que nenhum identificador escape. Não muda a semântica do
    texto -- só substitui dígitos por ``X``.
    """
    if not texto:
        return texto
    saida = _REGEX_CPF.sub("XXX.XXX.XXX-XX", texto)
    saida = _REGEX_CNPJ.sub("XX.XXX.XXX/XXXX-XX", saida)
    saida = _REGEX_CPF_CRU.sub("XXXXXXXXXXX", saida)
    saida = _REGEX_CNPJ_CRU.sub("XXXXXXXXXXXXXX", saida)
    return saida


def garantir_schema(caminho: Path) -> None:
    """Cria o SQLite de revisão com schema canônico se não existir.

    Schema:
      revisao(item_id, dimensao, ok, observacao, ts, valor_etl, valor_opus,
              valor_grafo_real)
      PK (item_id, dimensao); índices em ts e dimensao.

    ``ok`` admite ``NULL`` (estado "não-aplicável"). Por isso a coluna não é
    NOT NULL aqui (decisão consciente: a spec diz NULL=N/A).

    Sprint 103: adicionadas colunas ``valor_etl`` e ``valor_opus`` (TEXT, NULL).
    Sessão 2026-04-29 (auditoria 4-way): adicionada ``valor_grafo_real``
    (TEXT, NULL). Permite a 4ª comparação ETL × Opus × Grafo × Humano,
    expondo divergências de normalização (Tipo B: ETL ≠ Grafo apos
    sintético Sprint 107, etc.). Migração graceful via ALTER TABLE.
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(caminho)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS revisao (
                item_id TEXT NOT NULL,
                dimensao TEXT NOT NULL,
                ok INTEGER,
                observacao TEXT,
                ts TEXT DEFAULT (datetime('now')),
                valor_etl TEXT,
                valor_opus TEXT,
                valor_grafo_real TEXT,
                PRIMARY KEY (item_id, dimensao)
            );
            CREATE INDEX IF NOT EXISTS idx_revisao_ts ON revisao (ts);
            CREATE INDEX IF NOT EXISTS idx_revisao_dimensao ON revisao (dimensao);
            """
        )
        # Migração graceful (DBs criados antes da Sprint 103 ou da auditoria 4-way).
        cur = conn.execute("PRAGMA table_info(revisao)")
        colunas = {row[1] for row in cur.fetchall()}
        if "valor_etl" not in colunas:
            conn.execute("ALTER TABLE revisao ADD COLUMN valor_etl TEXT")
        if "valor_opus" not in colunas:
            conn.execute("ALTER TABLE revisao ADD COLUMN valor_opus TEXT")
        if "valor_grafo_real" not in colunas:
            conn.execute("ALTER TABLE revisao ADD COLUMN valor_grafo_real TEXT")
        conn.commit()
    finally:
        conn.close()


def salvar_marcacao(
    caminho: Path,
    item_id: str,
    dimensao: str,
    ok: int | None,
    observacao: str = "",
    valor_etl: str | None = None,
    valor_opus: str | None = None,
    valor_grafo_real: str | None = None,
) -> None:
    """Persiste UPSERT de marcação por (item_id, dimensao).

    Se já existe marcação para o par, sobrescreve com ``ts = now`` -- isto
    é intencional (humano pode revisar a própria marcação na sessão).

    Sprint 103: ``valor_etl`` e ``valor_opus`` (None = preserva valor anterior
    quando UPSERT). Para limpar explicitamente, passar string vazia.
    Auditoria 4-way: ``valor_grafo_real`` segue mesma semantica (None preserva).
    """
    garantir_schema(caminho)
    conn = sqlite3.connect(caminho)
    try:
        # COALESCE no UPDATE garante que None novo não sobrescreve valor
        # ja gravado (preserva histórico se quem chama não se importa com
        # essas colunas).
        conn.execute(
            """
            INSERT INTO revisao (item_id, dimensao, ok, observacao, ts,
                                 valor_etl, valor_opus, valor_grafo_real)
            VALUES (?, ?, ?, ?, datetime('now'), ?, ?, ?)
            ON CONFLICT(item_id, dimensao) DO UPDATE SET
              ok = excluded.ok,
              observacao = excluded.observacao,
              ts = excluded.ts,
              valor_etl = COALESCE(excluded.valor_etl, valor_etl),
              valor_opus = COALESCE(excluded.valor_opus, valor_opus),
              valor_grafo_real = COALESCE(excluded.valor_grafo_real, valor_grafo_real)
            """,
            (item_id, dimensao, ok, observacao, valor_etl, valor_opus, valor_grafo_real),
        )
        conn.commit()
    finally:
        conn.close()


def carregar_marcacoes(caminho: Path, item_id: str | None = None) -> list[dict]:
    """Carrega marcações (todas ou de um item específico).

    Sprint 103: campos `valor_etl` e `valor_opus` retornam None se não
    existirem (DBs antigos). garantir_schema() faz a migração graceful.
    Auditoria 4-way: `valor_grafo_real` segue a mesma logica.
    """
    if not caminho.exists():
        return []
    garantir_schema(caminho)  # migra DBs antigos antes de SELECT
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    try:
        colunas = (
            "item_id, dimensao, ok, observacao, ts, valor_etl, valor_opus, "
            "valor_grafo_real"
        )
        if item_id is not None:
            cursor = conn.execute(
                f"SELECT {colunas} FROM revisao WHERE item_id = ?",
                (item_id,),
            )
        else:
            cursor = conn.execute(f"SELECT {colunas} FROM revisao")
        resultado = [dict(row) for row in cursor]
    finally:
        conn.close()
    return resultado


def extrair_valor_etl_para_dimensao(pendencia: dict, dimensao: str) -> str:
    """Sprint 103: mapeia o metadata da pendência para o "valor extraído" que
    o ETL atribuiu a cada dimensão canônica.

    Heurísticas:
      - data       -> metadata.data_emissao
      - valor      -> metadata.total
      - itens      -> metadata.itens (lista) -> contagem
      - fornecedor -> metadata.razao_social ou nome_canonico
      - pessoa     -> metadata.pessoa ou inferida do path

    Retorna string vazia se o ETL não preencheu a dimensão (sinal claro
    para o revisor de que o pipeline NÃO sabe). PII mascarada
    defensivamente.
    """
    meta = pendencia.get("metadata") or {}
    if dimensao == "data":
        return mascarar_pii(str(meta.get("data_emissao", "")))
    if dimensao == "valor":
        total = meta.get("total")
        return f"{float(total):.2f}" if total not in (None, "") else ""
    if dimensao == "itens":
        itens = meta.get("itens")
        if isinstance(itens, list):
            return f"{len(itens)} item(ns)"
        return ""
    if dimensao == "fornecedor":
        razao = meta.get("razao_social") or meta.get("nome_canonico", "")
        return mascarar_pii(str(razao))
    if dimensao == "pessoa":
        pessoa = meta.get("pessoa")
        if pessoa:
            return str(pessoa)
        # Fallback: infere do caminho ('andre/' ou 'casal/' no caminho).
        caminho = str(pendencia.get("caminho", ""))
        if "/andre/" in caminho:
            return "andre (inferido)"
        if "/casal/" in caminho:
            return "casal (inferido)"
        if "/vitoria/" in caminho:
            return "vitoria (inferido)"
        return ""
    return ""


_HEADER_GROUND_TRUTH_CSV: list[str] = [
    # Sprint 103 (3-way) — preserva ordem original para retro-compat de
    # consumidores antigos.
    "item_id",
    "dimensao",
    "valor_etl",
    "valor_opus",
    "valor_humano",
    "divergencia",
    "observacao",
    "ts",
    # Auditoria 4-way (sessão 2026-04-29) — colunas anexadas no fim.
    "valor_grafo_real",
    "divergencia_etl_grafo",
    "divergencia_grafo_opus",
]


def _comparar_canonico(a: str, b: str) -> bool:
    """True se ambos preenchidos e diferem (case-insensitive, sem espaços)."""
    if not a or not b:
        return False
    return a.strip().lower() != b.strip().lower()


def gerar_ground_truth_csv(caminho_db: Path, caminho_csv: Path) -> int:
    """Exporta tabela `revisao` para CSV com 4 colunas de valor (ETL/Opus/
    Grafo/Humano) por dimensao + flags de divergencia.

    Header: item_id, dimensao, valor_etl, valor_opus, valor_humano,
    divergencia, observacao, ts, valor_grafo_real, divergencia_etl_grafo,
    divergencia_grafo_opus. Ordem mantem 8 colunas originais Sprint 103
    para retro-compat e anexa 3 novas no fim (auditoria 4-way 2026-04-29).

    `valor_humano` mapeia ok={1: "OK", 0: "Erro", None: "Não-aplicável"}.
    `divergencia` = "1" se ETL != Opus OR humano marcou Erro (Sprint 103).
    `divergencia_etl_grafo` = "1" se ETL != Grafo (Tipo B — perda na
    transformacao, ex: sintetico Sprint 107).
    `divergencia_grafo_opus` = "1" se Grafo != Opus (Tipo A pos-norm).
    PII mascarada antes da escrita.

    Retorna número de linhas escritas (excluindo cabecalho).
    """
    import csv

    if not caminho_db.exists():
        # CSV vazio (so cabecalho).
        caminho_csv.parent.mkdir(parents=True, exist_ok=True)
        with caminho_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(_HEADER_GROUND_TRUTH_CSV)
        return 0

    marcacoes = carregar_marcacoes(caminho_db)
    rotulo_humano = {1: "OK", 0: "Erro", None: "Não-aplicável"}

    caminho_csv.parent.mkdir(parents=True, exist_ok=True)
    with caminho_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(_HEADER_GROUND_TRUTH_CSV)
        n = 0
        for m in marcacoes:
            valor_etl = mascarar_pii(m.get("valor_etl") or "")
            valor_opus = mascarar_pii(m.get("valor_opus") or "")
            valor_grafo = mascarar_pii(m.get("valor_grafo_real") or "")
            valor_humano = rotulo_humano.get(m.get("ok"), "Não-aplicável")
            divergencia = "1" if (
                _comparar_canonico(valor_etl, valor_opus) or m.get("ok") == 0
            ) else "0"
            div_etl_grafo = "1" if _comparar_canonico(valor_etl, valor_grafo) else "0"
            div_grafo_opus = "1" if _comparar_canonico(valor_grafo, valor_opus) else "0"
            writer.writerow(
                [
                    m["item_id"],
                    m["dimensao"],
                    valor_etl,
                    valor_opus,
                    valor_humano,
                    divergencia,
                    mascarar_pii(m.get("observacao") or ""),
                    m.get("ts") or "",
                    valor_grafo,
                    div_etl_grafo,
                    div_grafo_opus,
                ]
            )
            n += 1
    return n


def _taxa_fidelidade(marcacoes: list[dict]) -> float:
    """Proporção de marcações com ``ok = 1`` em relação ao total não-NULL.

    Marcações ``NULL`` (não-aplicável) ficam fora do denominador para não
    poluir a métrica. Retorna 0.0 quando não há nada relevante.
    """
    relevantes = [m for m in marcacoes if m["ok"] is not None]
    if not relevantes:
        return 0.0
    aprovadas = sum(1 for m in relevantes if m["ok"] == 1)
    return aprovadas / len(relevantes)


def detectar_padroes_recorrentes(
    marcacoes: list[dict],
    limite: int = LIMITE_PADRAO_RECORRENTE,
) -> list[dict]:
    """Agrupa marcações ``ok=0`` por dimensão e devolve as recorrentes.

    Retorna lista de dicts ``{dimensao: str, contagem: int, item_ids: list[str]}``
    apenas para dimensões com pelo menos ``limite`` reprovações. Padrão
    recorrente vira candidato a "Sugerir patch".
    """
    por_dimensao: dict[str, list[str]] = {}
    for marca in marcacoes:
        if marca["ok"] == 0:
            por_dimensao.setdefault(marca["dimensao"], []).append(marca["item_id"])
    resultado: list[dict] = []
    for dimensao, item_ids in por_dimensao.items():
        if len(item_ids) >= limite:
            resultado.append(
                {
                    "dimensao": dimensao,
                    "contagem": len(item_ids),
                    "item_ids": sorted(set(item_ids)),
                }
            )
    resultado.sort(key=lambda d: -d["contagem"])
    return resultado


def gerar_relatorio_markdown(
    marcacoes: list[dict],
    pendencias_indexadas: dict[str, dict] | None = None,
) -> str:
    """Produz relatório em Markdown da sessão atual.

    PII mascarada (CPF/CNPJ formatados e crus). Inclui:
      - Cabeçalho com data/hora.
      - Taxa de fidelidade global.
      - Tabela por item com dimensões aprovadas/reprovadas.
      - Padrões recorrentes (>=3 reprovações na mesma dimensão).

    ``pendencias_indexadas`` é opcional: se fornecido, enriquece a tabela
    com ``tipo_documento`` e nome canônico.
    """
    pendencias_indexadas = pendencias_indexadas or {}
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    taxa = _taxa_fidelidade(marcacoes)
    padroes = detectar_padroes_recorrentes(marcacoes)

    linhas: list[str] = []
    linhas.append(f"# Revisão visual -- sessão {agora}\n")
    linhas.append(f"Total de marcações: **{len(marcacoes)}**\n")
    linhas.append(
        f"Taxa de fidelidade humana: **{taxa * 100:.1f}%** "
        f"({sum(1 for m in marcacoes if m['ok'] == 1)} OK / "
        f"{sum(1 for m in marcacoes if m['ok'] is not None)} avaliadas)\n"
    )

    linhas.append("\n## Itens revisados\n")
    por_item: dict[str, list[dict]] = {}
    for marca in marcacoes:
        por_item.setdefault(marca["item_id"], []).append(marca)
    for item_id, lista in sorted(por_item.items()):
        info = pendencias_indexadas.get(item_id, {})
        tipo_doc = info.get("metadata", {}).get("tipo_documento", info.get("tipo", "?"))
        linhas.append(f"\n### {mascarar_pii(item_id)}\n")
        linhas.append(f"- Tipo: `{tipo_doc}`")
        for marca in sorted(lista, key=lambda m: m["dimensao"]):
            estado = "OK" if marca["ok"] == 1 else "ERRO" if marca["ok"] == 0 else "Não-aplicável"
            obs = mascarar_pii(marca.get("observacao") or "")
            obs_render = f" -- {obs}" if obs else ""
            linhas.append(f"- {marca['dimensao']}: **{estado}**{obs_render}")

    if padroes:
        linhas.append("\n## Padrões recorrentes\n")
        for pad in padroes:
            linhas.append(
                f"- Dimensão `{pad['dimensao']}` reprovada em "
                f"**{pad['contagem']}** itens. Candidato a regra YAML."
            )

    linhas.append("\n---\n")
    linhas.append(
        '*"A revisão visual é a ponte entre intuição humana e automação '
        'determinística." -- princípio do alinhamento mensurável*\n'
    )
    return "\n".join(linhas)


def gravar_relatorio(
    marcacoes: list[dict],
    diretorio: Path,
    pendencias_indexadas: dict[str, dict] | None = None,
) -> Path:
    """Grava relatório em ``diretorio/<YYYY-MM-DD>.md`` (sobrescreve)."""
    diretorio.mkdir(parents=True, exist_ok=True)
    data_str = datetime.now().strftime("%Y-%m-%d")
    destino = diretorio / f"{data_str}.md"
    conteudo = gerar_relatorio_markdown(marcacoes, pendencias_indexadas)
    destino.write_text(conteudo, encoding="utf-8")
    return destino


def sugerir_patch_yaml(padroes: list[dict]) -> str:
    """Gera diff sugerido em YAML para copy-paste manual.

    Estratégia: para cada dimensão recorrentemente reprovada, propõe um bloco
    de regra placeholder em ``mappings/categorias_item.yaml`` (ou similar).
    Decisão consciente: NUNCA aplica patch automaticamente -- humano sempre
    aprova edição manual (regra do projeto).
    """
    if not padroes:
        return "# nenhum padrão recorrente detectado nesta sessão\n"
    blocos: list[str] = ["# diff sugerido para copy-paste em mappings/*.yaml\n"]
    for pad in padroes:
        blocos.append(f"# Dimensão '{pad['dimensao']}' reprovada {pad['contagem']}x.")
        blocos.append("# Itens afetados:")
        for iid in pad["item_ids"][:5]:
            blocos.append(f"#   - {mascarar_pii(iid)}")
        blocos.append("# Sugestão: adicionar regra YAML abaixo (humano edita campo)\n")
        blocos.append(f"- nome: ajuste_{pad['dimensao']}_pos_revisao_humana")
        blocos.append("  pattern: TODO_humano")
        blocos.append(f"  campo: {pad['dimensao']}")
        blocos.append("  prioridade: 100\n")
    return "\n".join(blocos)


# "A revisão visual é a ponte entre intuição humana e
# automação determinística." -- princípio do alinhamento mensurável
