"""Helpers compartilhados das mini-views do cluster Home -- Sprint UX-123.

As 4 páginas `home_dinheiro`, `home_docs`, `home_analise` e `home_metas`
reusam estes helpers para não duplicar lógica de filtro temporal e KPI
compacto. Mantido como módulo "privado" (prefixo `_`) porque a interface
pública do dashboard são as páginas `renderizar(...)`, não estes helpers.

Padrão canônico:
- `filtrar_para_hoje(df)` filtra um DataFrame por data == data mais recente
  disponível. "Hoje" é o último dia do mês mais recente do dataset, não o
  `date.today()` real -- isso garante UX consistente quando o pipeline
  ainda não processou as transações do dia atual.
- `renderizar_kpi_compacto(titulo, valor, cor)` delega ao `card_html`
  canônico do tema com cabeçalho menor para caber na grid 4-col da Home.

Limite de complexidade da Sprint UX-123: cada mini-view deve ficar abaixo
de 200L; este helper centraliza decisões que antes seriam duplicadas.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from src.dashboard.tema import card_html


def data_referencia_hoje(df: pd.DataFrame, coluna_data: str = "data") -> str | None:
    """Retorna a data de referência para "hoje" no dataset.

    Estratégia:
      1. Se `date.today()` existe no dataframe, usa-o (caso dataset está
         atualizado em tempo real).
      2. Senão, usa a data mais recente disponível (último dia processado).
      3. Se o df não tem a coluna de data ou está vazio, retorna None.

    Devolve string `YYYY-MM-DD` para casamento exato com `df[coluna]`.
    """
    if df is None or df.empty or coluna_data not in df.columns:
        return None

    serie_dt = pd.to_datetime(df[coluna_data], errors="coerce").dropna()
    if serie_dt.empty:
        return None

    hoje = pd.Timestamp(date.today())
    if (serie_dt.dt.date == hoje.date()).any():
        return hoje.strftime("%Y-%m-%d")

    mais_recente = serie_dt.max()
    return mais_recente.strftime("%Y-%m-%d")


def filtrar_para_hoje(df: pd.DataFrame, coluna_data: str = "data") -> pd.DataFrame:
    """Filtra o DataFrame para o dia de referência (hoje ou último dia).

    Empty in -> empty out. Se a coluna `coluna_data` não existe, devolve
    o df original sem alteração (graceful degradation -- a mini-view
    decide se quer alertar ou mostrar agregado).
    """
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()

    if coluna_data not in df.columns:
        return df

    referencia = data_referencia_hoje(df, coluna_data)
    if referencia is None:
        return df.iloc[0:0].copy()

    df_copia = df.copy()
    df_copia["_data_referencia"] = pd.to_datetime(
        df_copia[coluna_data], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    resultado = df_copia[df_copia["_data_referencia"] == referencia].drop(
        columns=["_data_referencia"]
    )
    return resultado


def renderizar_kpi_compacto(titulo: str, valor: Any, cor: str) -> str:
    """Wrapper sobre `card_html` para uso uniforme nas 4 mini-views.

    Recebe valor `Any` para aceitar string formatada (`R$ 123,45`),
    contagem (`5`) ou percentual (`75%`). O caller é responsável pela
    formatação final; este helper apenas garante consistência visual.
    """
    return card_html(titulo, str(valor), cor)


# "Pequeno e claro vence grande e nebuloso." -- princípio de design enxuto
