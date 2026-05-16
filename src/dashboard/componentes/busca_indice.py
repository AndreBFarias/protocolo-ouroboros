"""Índice em memória para autocomplete da Busca Global -- Sprint UX-114.

Constrói um índice cacheado por sessão Streamlit a partir de quatro fontes:

1. **Fornecedores**: nodes do grafo SQLite com `tipo='fornecedor'` (nome
   canônico + aliases).
2. **Descrições de itens**: nodes do grafo com `tipo='item'` (campo
   `descricao` no metadata, ou `nome_canonico`).  # noqa: accent
3. **Tipos canônicos de documento**: ids de `mappings/tipos_documento.yaml`
   normalizados em label humano (ex: `holerite -> Holerite`,
   `nfce_consumidor_eletronica -> NFCe Consumidor Eletronica`).
4. **Nomes de abas**: chaves de `MAPA_ABA_PARA_CLUSTER` (ADR-22).

Padrão (m) -- branch reversível: se o grafo não existe ou está vazio,
o índice retorna estrutura com listas vazias mas as outras fontes
(tipos canônicos, abas) seguem populadas. A página de busca cai em
modo degradado mas ainda funcional para roteamento de aba.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import yaml

from src.dashboard.componentes.drilldown import MAPA_ABA_PARA_CLUSTER

RAIZ = Path(__file__).resolve().parents[3]
CAMINHO_GRAFO_DEFAULT: Path = RAIZ / "data" / "output" / "grafo.sqlite"
CAMINHO_TIPOS_DOC: Path = RAIZ / "mappings" / "tipos_documento.yaml"

# Limites defensivos -- evita estourar memória se o grafo crescer muito.
LIMITE_FORNECEDORES: int = 5000
LIMITE_DESCRICOES: int = 5000


def _humanizar_id(id_tipo: str) -> str:
    """Converte id snake_case em label humano com primeira letra maiúscula.

    Exemplos:
        holerite                       -> Holerite
        nfce_consumidor_eletronica     -> NFCe Consumidor Eletronica
        das_parcsn                     -> DAS PARCSN
        irpf_parcela                   -> IRPF Parcela
    """
    siglas = {"das", "irpf", "nfce", "nfe", "cnpj", "cpf", "parcsn", "mei"}
    partes = id_tipo.split("_")
    humano = []
    for parte in partes:
        if parte.lower() in siglas:
            humano.append(parte.upper())
        else:
            humano.append(parte.capitalize())
    return " ".join(humano)


def _carregar_tipos_documento(caminho: Path = CAMINHO_TIPOS_DOC) -> list[str]:
    """Lê ids canônicos de tipos_documento.yaml e devolve labels humanos.

    Se o YAML não existe ou está corrompido, retorna fallback estático
    com os 8 chips canônicos (Holerite, Nota Fiscal, DAS, Boleto, IRPF,
    Recibo, Comprovante, Contracheque).
    """
    fallback = [
        "Holerite",
        "Nota Fiscal",
        "DAS",
        "Boleto",
        "IRPF",
        "Recibo",
        "Comprovante",
        "Contracheque",
    ]
    if not caminho.exists():
        return fallback
    try:
        with caminho.open("r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
    except (yaml.YAMLError, OSError):
        return fallback
    tipos = cfg.get("tipos") or []
    labels: list[str] = []
    for tipo in tipos:
        id_t = tipo.get("id") if isinstance(tipo, dict) else None
        if id_t:
            labels.append(_humanizar_id(id_t))
    if not labels:
        return fallback
    return labels


def _carregar_fornecedores_e_descricoes(
    caminho_grafo: Path,
) -> tuple[list[str], list[str]]:
    """Lê fornecedores e descrições de itens do grafo SQLite (read-only).

    Retorna (fornecedores, descricoes). Listas vazias se o grafo não existe
    ou se a query falha (graceful degradation -- ADR-10).
    """
    if not caminho_grafo.exists():
        return [], []
    try:
        conn = sqlite3.connect(f"file:{caminho_grafo}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        return [], []

    fornecedores: list[str] = []
    descricoes: list[str] = []
    try:
        try:
            cur = conn.execute(
                "SELECT nome_canonico, aliases FROM node "
                "WHERE tipo = 'fornecedor' "
                "ORDER BY nome_canonico LIMIT ?",
                (LIMITE_FORNECEDORES,),
            )
            for row in cur:
                nome = (row["nome_canonico"] or "").strip()
                if nome:
                    fornecedores.append(nome)
                try:
                    aliases = json.loads(row["aliases"] or "[]")
                except (json.JSONDecodeError, TypeError):
                    aliases = []
                for alias in aliases:
                    if isinstance(alias, str) and alias.strip():
                        fornecedores.append(alias.strip())
        except sqlite3.Error:
            pass  # noqa: BLE001 -- tabela node pode não existir em vault novo; busca degrada graciosamente

        try:
            cur = conn.execute(
                "SELECT nome_canonico, metadata FROM node WHERE tipo = 'item' LIMIT ?",
                (LIMITE_DESCRICOES,),
            )
            for row in cur:
                try:
                    meta = json.loads(row["metadata"] or "{}")
                except (json.JSONDecodeError, TypeError):
                    meta = {}
                desc = (meta.get("descricao") or row["nome_canonico"] or "").strip()
                if desc:
                    descricoes.append(desc)
        except sqlite3.Error:
            pass  # noqa: BLE001 -- tabela node pode não existir em vault novo; busca degrada graciosamente
    finally:
        conn.close()

    # dedup preservando ordem
    fornecedores = list(dict.fromkeys(fornecedores))
    descricoes = list(dict.fromkeys(descricoes))
    return fornecedores, descricoes


def construir_indice(
    caminho_grafo: Path | None = None,
) -> dict[str, list[str]]:
    """Constrói o índice canônico para autocomplete.

    Retorno:
        {
            "fornecedores":  [...nomes + aliases...],
            "descricoes":    [...descrições de itens...],
            "tipos_doc":     [...labels humanos dos ids canônicos...],
            "abas":          [...chaves de MAPA_ABA_PARA_CLUSTER...],
        }

    Se `caminho_grafo` for None, usa `data/output/grafo.sqlite` da raiz
    do projeto. Listas que não puderam ser carregadas vêm vazias.
    """
    grafo = caminho_grafo if caminho_grafo is not None else CAMINHO_GRAFO_DEFAULT
    fornecedores, descricoes = _carregar_fornecedores_e_descricoes(grafo)
    tipos_doc = _carregar_tipos_documento()
    abas = sorted(MAPA_ABA_PARA_CLUSTER.keys())
    return {
        "fornecedores": fornecedores,
        "descricoes": descricoes,
        "tipos_doc": tipos_doc,
        "abas": abas,
    }


def sugestoes(
    query: str,
    indice: dict[str, list[str]] | None = None,
    limite: int = 10,
    caminho_grafo: Path | None = None,
) -> list[str]:
    """Retorna até `limite` sugestões case-insensitive substring.

    Ordem de prioridade na hora de combinar:
    1. Abas (navegação rápida tem precedência)
    2. Tipos canônicos de documento
    3. Fornecedores
    4. Descrições de itens

    Filtra duplicatas (string equal case-insensitive). Devolve [] se a
    query tem menos de 2 caracteres significativos.
    """
    q = (query or "").strip().lower()
    if len(q) < 2:
        return []
    idx = indice if indice is not None else construir_indice(caminho_grafo)

    bag: list[str] = []
    fontes_ordenadas = ["abas", "tipos_doc", "fornecedores", "descricoes"]
    for fonte in fontes_ordenadas:
        for item in idx.get(fonte, []):
            if not isinstance(item, str):
                continue
            if q in item.lower():
                bag.append(item)
                if len(bag) >= limite * 2:
                    break

    # dedup case-insensitive preservando ordem
    vistos: set[str] = set()
    saida: list[str] = []
    for item in bag:
        chave = item.lower()
        if chave in vistos:
            continue
        vistos.add(chave)
        saida.append(item)
        if len(saida) >= limite:
            break
    return saida


# "Quem busca, encontra; mas precisa primeiro saber o que procura." -- Aristóteles
