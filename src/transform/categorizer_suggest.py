"""Sugestor de categorias para transações "Outros" via TF-IDF + cosseno.

Sprint CATEGORIZER-SUGESTAO-TFIDF (2026-05-16). Treina sobre transações
já categorizadas (≠ "Outros") e prediz top-K vizinhos para cada
transação "Outros" usando TF-IDF + similaridade cosseno. Vota por
categoria mais frequente entre os vizinhos.

Implementação manual (sem sklearn) — leve, sem dependência adicional.
Para datasets grandes (~10000 transações), runtime ~3-5s. Para uso
diário do dashboard, aceitável.

Sprint CATEGORIZER-SUGESTAO-AUDITORIA-RUIDO (2026-05-16): adicionado
filtro de domínio + risco_estimado. Auditoria do dataset 2026-05-16
mostrou ruído inaceitável em conf=1.0 (`Lab Pat e Prev do Cancer → Natação`).
Filtros baseados em `mappings/dominio_categorias.yaml` reclassificam
sugestões em 4 níveis de risco:

- BAIXO: passa filtro de domínio (tokens obrigatórios presentes E nenhum
  proibitivo) + valor dentro da faixa típica + confiança >=0.85.
- MEDIO: confiança alta mas falha 1 das condições acima.
- ALTO: falha 2+ condições OU token proibitivo presente.
- DESCONHECIDO: categoria sem entry em dominio_categorias.yaml.

Schema do output:

```python
{
    "<id_transacao>": {
        "descricao": "...",
        "valor": 50.0,
        "top1": "ALIMENTACAO",
        "confianca_top1": 0.78,
        "risco_estimado": "BAIXO",
        "filtros_aplicados": ["dominio_ok", "valor_ok"],
        "sugestoes": [
            {"categoria": "ALIMENTACAO", "confianca": 0.78, "votos": 4},
        ],
    },
}
```

Threshold de confiança recomendado para auto-promoção: ≥ 0.85 E
``risco_estimado == "BAIXO"``.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

CATEGORIA_OUTROS = "Outros"
PATH_DOMINIO_YAML = Path(__file__).resolve().parents[2] / "mappings" / "dominio_categorias.yaml"

RISCO_BAIXO = "BAIXO"
RISCO_MEDIO = "MEDIO"
RISCO_ALTO = "ALTO"
RISCO_DESCONHECIDO = "DESCONHECIDO"


@dataclass(frozen=True)
class Transacao:
    """View mínima sobre transação para sugestão.

    Sprint CATEGORIZER-SUGESTAO-AUDITORIA-RUIDO: `valor` opcional para
    filtros de domínio (categoria X tem faixa típica de valor).
    """

    id: str
    descricao: str
    categoria: str
    valor: float = 0.0


def _carregar_dominio(path: Path | None = None) -> dict:
    """Lê `mappings/dominio_categorias.yaml`. Falha-soft: dict vazio."""
    p = path if path is not None else PATH_DOMINIO_YAML
    if not p.exists():
        return {}
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return {}
    try:
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    return doc.get("categorias", {}) or {}


def _avaliar_dominio(
    descricao: str,
    categoria: str,
    valor: float,
    dominio: dict,
) -> tuple[str, list[str]]:
    """Avalia risco da sugestão com base em filtros de domínio.

    Retorna (risco, filtros_aplicados). Filtros possíveis:
    - "dominio_ok": tokens obrigatórios encontrados (ou lista vazia)
    - "dominio_faltando_tokens": tokens obrigatórios não encontrados
    - "dominio_proibitivo": token proibitivo encontrado (eleva ALTO)
    - "valor_ok": valor dentro de [min, max]
    - "valor_fora_faixa": valor fora da faixa
    - "sem_dominio_definido": categoria não tem entry no YAML
    """
    cat_info = dominio.get(categoria)
    if not cat_info:
        return RISCO_DESCONHECIDO, ["sem_dominio_definido"]

    desc_lower = (descricao or "").lower()
    filtros: list[str] = []
    falhas = 0

    obrigatorios = cat_info.get("tokens_obrigatorios") or []
    proibitivos = cat_info.get("tokens_proibitivos") or []
    valor_min = cat_info.get("valor_min")
    valor_max = cat_info.get("valor_max")

    # Tokens proibitivos elevam ALTO imediatamente:
    for token in proibitivos:
        t_str = str(token).lower() if token is not None else ""
        if t_str and t_str in desc_lower:
            filtros.append(f"dominio_proibitivo:{t_str}")
            return RISCO_ALTO, filtros

    # Tokens obrigatórios: ao menos 1 precisa estar presente (se lista existe):
    if obrigatorios:
        achou = any(
            str(t).lower() in desc_lower for t in obrigatorios if t is not None
        )
        if achou:
            filtros.append("dominio_ok")
        else:
            filtros.append("dominio_faltando_tokens")
            falhas += 1
    else:
        # Categoria intencionalmente larga (Pessoal, Transferência): aceita.
        filtros.append("dominio_aberto")

    # Filtro de valor:
    if valor_min is not None and valor_max is not None and valor > 0:
        if valor_min <= valor <= valor_max:
            filtros.append("valor_ok")
        else:
            filtros.append("valor_fora_faixa")
            falhas += 1

    if falhas == 0:
        return RISCO_BAIXO, filtros
    if falhas == 1:
        return RISCO_MEDIO, filtros
    return RISCO_ALTO, filtros


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
    transacoes: list[Transacao],
    top_k: int = 5,
    dominio: dict | None = None,
) -> dict[str, dict]:
    """Para cada transação "Outros", calcula top-K vizinhos e vota.

    Sprint CATEGORIZER-SUGESTAO-AUDITORIA-RUIDO: enriquece output com
    ``risco_estimado`` e ``filtros_aplicados`` baseado em
    ``mappings/dominio_categorias.yaml``. Sem arg ``dominio``: carrega do
    arquivo canônico. Para testes: passe dict customizado.

    Retorna dict {id: {descricao, valor, top1, confianca_top1,
    risco_estimado, filtros_aplicados, sugestoes[]}}.
    """
    if not transacoes:
        return {}

    treino = [t for t in transacoes if t.categoria != CATEGORIA_OUTROS]
    alvo = [t for t in transacoes if t.categoria == CATEGORIA_OUTROS]
    if not treino or not alvo:
        return {}

    if dominio is None:
        dominio = _carregar_dominio()

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
        scores = [(_cosseno(vec, vt), treino[i].categoria) for i, vt in enumerate(treino_vetores)]
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
        top1 = sugestoes[0]["categoria"]
        risco, filtros = _avaliar_dominio(tx.descricao, top1, tx.valor, dominio)
        saida[tx.id] = {
            "descricao": tx.descricao,
            "valor": tx.valor,
            "top1": top1,
            "confianca_top1": sugestoes[0]["confianca"],
            "risco_estimado": risco,
            "filtros_aplicados": filtros,
            "sugestoes": sugestoes,
        }
    return saida


# "Outros é débito cognitivo acumulado." -- principio do sugestor honesto
