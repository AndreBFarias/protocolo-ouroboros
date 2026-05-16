"""Sugestor de categorias para transações "Outros" via TF-IDF + cosseno.

Sprint CATEGORIZER-SUGESTAO-TFIDF (2026-05-16). Treina sobre transações
já categorizadas (≠ "Outros") e prediz top-K vizinhos para cada
transação "Outros" usando TF-IDF + similaridade cosseno. Vota por
categoria mais frequente entre os vizinhos.

Implementação manual (sem sklearn) — leve, sem dependência adicional.
Para datasets grandes (~10000 transações), runtime ~3-5s. Para uso
diário do dashboard, aceitável.

Schema do output:

```python
{
    "<id_transacao>": {
        "descricao": "...",
        "top1": "ALIMENTACAO",
        "confianca_top1": 0.78,
        "sugestoes": [
            {"categoria": "ALIMENTACAO", "confianca": 0.78, "votos": 4},
            {"categoria": "TRANSPORTE", "confianca": 0.12, "votos": 1},
        ],
    },
    ...
}
```

Threshold de confiança recomendado para auto-promoção: ≥ 0.85.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

CATEGORIA_OUTROS = "Outros"


@dataclass(frozen=True)
class Transacao:
    """View mínima sobre transação para sugestão."""

    id: str
    descricao: str
    categoria: str


def _tokenizar(texto: str) -> list[str]:
    """Tokens lowercase >= 2 chars (mantém siglas como CC, PJ)."""
    if not texto:
        return []
    raw = re.findall(r"[a-zA-ZÀ-ÿ0-9]{2,}", texto.lower())
    return raw


def _idf(textos_tokens: list[list[str]]) -> dict[str, float]:
    """Inverse document frequency: log(N / (1 + df))."""
    n = len(textos_tokens)
    if n == 0:
        return {}
    df: Counter[str] = Counter()
    for tokens in textos_tokens:
        df.update(set(tokens))
    return {token: math.log(n / (1 + freq)) + 1.0 for token, freq in df.items()}


def _tfidf(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    """TF-IDF de um documento, retornado como dict esparso."""
    if not tokens:
        return {}
    tf = Counter(tokens)
    total = len(tokens)
    return {t: (c / total) * idf.get(t, 0.0) for t, c in tf.items() if idf.get(t, 0.0) > 0}


def _cosseno(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosseno entre 2 vetores esparsos."""
    if not a or not b:
        return 0.0
    chaves_comuns = set(a) & set(b)
    if not chaves_comuns:
        return 0.0
    produto = sum(a[k] * b[k] for k in chaves_comuns)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return produto / (norm_a * norm_b)


def gerar_sugestoes(
    transacoes: list[Transacao], top_k: int = 5
) -> dict[str, dict]:
    """Para cada transação "Outros", calcula top-K vizinhos e vota.

    Retorna dict {id: {descricao, top1, confianca_top1, sugestoes[]}}.
    Apenas transações com categoria "Outros" entram no output.
    """
    if not transacoes:
        return {}

    treino = [t for t in transacoes if t.categoria != CATEGORIA_OUTROS]
    alvo = [t for t in transacoes if t.categoria == CATEGORIA_OUTROS]
    if not treino or not alvo:
        return {}

    treino_tokens = [_tokenizar(t.descricao) for t in treino]
    alvo_tokens = [_tokenizar(t.descricao) for t in alvo]
    idf = _idf(treino_tokens + alvo_tokens)
    treino_vetores = [_tfidf(toks, idf) for toks in treino_tokens]

    saida: dict[str, dict] = {}
    for tx, toks in zip(alvo, alvo_tokens, strict=False):
        vec = _tfidf(toks, idf)
        if not vec:
            continue
        # Top-K vizinhos por cosseno:
        scores = [
            (_cosseno(vec, vt), treino[i].categoria)
            for i, vt in enumerate(treino_vetores)
        ]
        # Filtra zeros para não votar em treino disjunto:
        scores = [s for s in scores if s[0] > 0]
        if not scores:
            continue
        scores.sort(reverse=True)
        top_vizinhos = scores[:top_k]

        # Vota por categoria, pondera pelo score:
        peso_por_cat: Counter[str] = Counter()
        votos_por_cat: Counter[str] = Counter()
        for score, cat in top_vizinhos:
            peso_por_cat[cat] += score
            votos_por_cat[cat] += 1

        # Normaliza pelo total de peso:
        total_peso = sum(peso_por_cat.values()) or 1.0
        sugestoes = [
            {
                "categoria": cat,
                "confianca": round(peso / total_peso, 3),
                "votos": votos_por_cat[cat],
            }
            for cat, peso in peso_por_cat.most_common(5)
        ]
        if not sugestoes:
            continue
        saida[tx.id] = {
            "descricao": tx.descricao,
            "top1": sugestoes[0]["categoria"],
            "confianca_top1": sugestoes[0]["confianca"],
            "sugestoes": sugestoes,
        }
    return saida


# "Outros é débito cognitivo acumulado." -- principio do sugestor honesto
