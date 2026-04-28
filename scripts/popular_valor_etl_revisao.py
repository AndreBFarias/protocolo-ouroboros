"""Sprint 103 -- popula valor_etl para todas as pendencias do Revisor.

A UI do Revisor preenche valor_etl quando o humano salva uma marcacao
(via _renderizar_painel_item -> salvar_marcacao). Mas para 3-colunas-on-load
(ETL pre-preenchido antes do humano abrir o item), populamos via script:

  - Lista pendencias atuais.
  - Para cada (item, dim), chama extrair_valor_etl_para_dimensao.
  - salvar_marcacao(... valor_etl=<x>) sem mexer em valor_opus nem ok
    (COALESCE preserva valores anteriores).
"""

from __future__ import annotations

import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

import sqlite3  # noqa: E402

from src.dashboard.dados import CAMINHO_REVISAO_HUMANA  # noqa: E402
from src.dashboard.dados_revisor import listar_pendencias_revisao  # noqa: E402
from src.dashboard.paginas.revisor import (  # noqa: E402
    DIMENSOES_CANONICAS,
    extrair_valor_etl_para_dimensao,
    garantir_schema,
)


def main() -> int:
    pendencias = listar_pendencias_revisao()
    print(f"Populando valor_etl para {len(pendencias)} pendencias", file=sys.stderr)

    garantir_schema(CAMINHO_REVISAO_HUMANA)
    persistidas = 0
    conn = sqlite3.connect(CAMINHO_REVISAO_HUMANA)
    try:
        for p in pendencias:
            item_id = p["item_id"]
            for dim in DIMENSOES_CANONICAS:
                valor_etl = extrair_valor_etl_para_dimensao(p, dim)
                # UPDATE/INSERT direto preservando demais colunas do registro.
                # Se o par (item_id, dim) ja existe, so atualiza valor_etl.
                conn.execute(
                    """
                    INSERT INTO revisao (item_id, dimensao, ok, observacao, valor_etl, valor_opus)
                    VALUES (?, ?, NULL, '', ?, NULL)
                    ON CONFLICT(item_id, dimensao) DO UPDATE SET
                      valor_etl = excluded.valor_etl
                    """,
                    (item_id, dim, valor_etl or ""),
                )
                persistidas += 1
        conn.commit()
    finally:
        conn.close()

    print(f"\n[OK] {persistidas} marcacoes atualizadas com valor_etl.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
