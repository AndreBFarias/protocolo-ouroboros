"""Gerador do cache ``financas-cache.json`` consumido pelo Mobile.

Le o XLSX consolidado em ``data/output/ouroboros_*.xlsx`` (aba
``extrato``), filtra a semana ISO de referencia (default: semana
atual) e produz payload com:

- ``gasto_semana``: soma das despesas da semana
- ``gasto_semana_anterior``: soma da semana ISO anterior
- ``delta_textual``: heuristica vs media de 12 semanas
- ``top_categorias``: top 5 categorias por valor com percentual
- ``ultimas_transacoes``: 20 transações mais recentes (por data desc)

Schema canonico: ``Protocolo-Mob-Ouroboros/docs/ADRs/0012-cache-mobile-readonly.md``.
Identidade de pessoa em ``autor`` e sempre
``pessoa_a``/``pessoa_b``/``casal`` (Regra -1).

Saida padrao: ``<vault_root>/.ouroboros/cache/financas-cache.json``.
Escrita atomica via ``write_json_atomic``.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.mobile_cache.atomic import write_json_atomic
from src.utils.logger import configurar_logger
from src.utils.pessoas import pessoa_id_de_legacy

logger = configurar_logger("mobile_cache.financas_cache")

SCHEMA_VERSION = 1
TZ_LOCAL = timezone(timedelta(hours=-3))

# Sprint MOB-bridge-1: tipos canonicos do schema XLSX.
# `Despesa` e `Imposto` contam como gasto; demais (Receita,
# Transferência Interna) ficam fora do agregado de gasto semanal.
TIPOS_GASTO: frozenset[str] = frozenset({"Despesa", "Imposto"})

# Heuristica do delta textual vs media 12 semanas.
LIMITE_FAIXA_DENTRO = 0.15  # +/- 15% e considerado "dentro da media"


def _gerado_em_iso(referencia: datetime | None = None) -> str:
    """Retorna ISO 8601 com timezone -03:00 (formato canonico do schema)."""
    momento = referencia or datetime.now(TZ_LOCAL)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=TZ_LOCAL)
    else:
        momento = momento.astimezone(TZ_LOCAL)
    momento = momento.replace(microsecond=0)
    return momento.isoformat()


def _semana_iso(referencia: date) -> tuple[date, date]:
    """Retorna (segunda, domingo) da semana ISO que contem ``referencia``."""
    # ISO: segunda = 1, domingo = 7. ``weekday()`` da 0=segunda..6=domingo.
    inicio = referencia - timedelta(days=referencia.weekday())
    fim = inicio + timedelta(days=6)
    return inicio, fim


def _carregar_extrato(xlsx_path: Path) -> pd.DataFrame:
    """Le a aba ``extrato`` do XLSX consolidado. Retorna DataFrame vazio se ausente."""
    if not xlsx_path.exists():
        logger.warning("XLSX não encontrado em %s -- cache vazio", xlsx_path)
        return pd.DataFrame()
    try:
        df = pd.read_excel(
            xlsx_path,
            sheet_name="extrato",
            keep_default_na=False,
            na_values=[""],
        )
    except (ValueError, OSError) as exc:
        logger.warning("falha ao ler XLSX %s: %s", xlsx_path, exc)
        return pd.DataFrame()
    if df.empty:
        return df
    # Garante coluna `data` como ``date``.
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date
    return df


def _filtrar_gastos(df: pd.DataFrame) -> pd.DataFrame:
    """Mantem apenas linhas cuja `tipo` esta em TIPOS_GASTO e `data` valida."""
    if df.empty:
        return df
    if "tipo" not in df.columns:
        return df.iloc[0:0].copy()
    mask = df["tipo"].isin(TIPOS_GASTO)
    if "data" in df.columns:
        mask = mask & df["data"].notna()
    return df[mask].copy()


def _filtrar_intervalo(
    df: pd.DataFrame,
    inicio: date,
    fim: date,
) -> pd.DataFrame:
    """Subconjunto de ``df`` no intervalo fechado entre as duas datas."""
    if df.empty or "data" not in df.columns:
        return df.iloc[0:0].copy() if not df.empty else df
    mask = (df["data"] >= inicio) & (df["data"] <= fim)
    return df[mask].copy()


def _agregar_top_categorias(
    df_semana: pd.DataFrame,
    gasto_semana: float,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """Top N categorias por valor absoluto na semana, com percentual."""
    if df_semana.empty or "categoria" not in df_semana.columns or gasto_semana <= 0:
        return []
    soma = (
        df_semana.assign(_valor=df_semana["valor"].abs())
        .groupby("categoria", dropna=False)["_valor"]
        .sum()
        .sort_values(ascending=False)
    )
    resultado: list[dict[str, Any]] = []
    for categoria, valor in soma.head(top_n).items():
        nome = str(categoria) if categoria is not None and str(categoria).strip() else "outros"
        resultado.append(
            {
                "nome": nome,
                "valor": round(float(valor), 2),
                "percentual": round(float(valor) / gasto_semana * 100, 1),
            }
        )
    return resultado


def _ultimas_transacoes(df_gastos: pd.DataFrame, n: int = 20) -> list[dict[str, Any]]:
    """20 transações mais recentes do extrato inteiro (por data desc)."""
    if df_gastos.empty or "data" not in df_gastos.columns:
        return []
    df_ord = df_gastos.sort_values("data", ascending=False).head(n)
    transacoes: list[dict[str, Any]] = []
    for _, row in df_ord.iterrows():
        data_iso = _data_para_iso(row.get("data"))
        if data_iso is None:
            continue
        autor = pessoa_id_de_legacy(row.get("quem"))
        valor = row.get("valor")
        try:
            valor_f = round(float(valor), 2)
        except (TypeError, ValueError):
            valor_f = 0.0
        tipo_raw = str(row.get("tipo", "")).strip().lower()
        tipo_canonico = "despesa" if tipo_raw in {"despesa", "imposto"} else tipo_raw or "despesa"
        destino = _str_seguro(row.get("local"))
        categoria = _str_seguro(row.get("categoria"))
        transacoes.append(
            {
                "data": data_iso,
                "autor": autor,
                "tipo": tipo_canonico,
                "valor": valor_f,
                "destino": destino,
                "categoria": categoria or "outros",
            }
        )
    return transacoes


def _str_seguro(valor: Any) -> str:
    """Converte valor para str limpa; vazio se None/NaN."""
    if valor is None:
        return ""
    try:
        if pd.isna(valor):
            return ""
    except (TypeError, ValueError):
        pass  # noqa: BLE001 -- pd.isna não aceita certos tipos; segue para str(valor)
    texto = str(valor).strip()
    return texto


def _data_para_iso(valor: Any) -> str | None:
    """Aceita date/datetime/str; retorna ISO 8601 'YYYY-MM-DD' ou None."""
    if valor is None:
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass  # noqa: BLE001 -- pd.isna não aceita certos tipos; segue para isoformat
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, str):
        candidato = valor.strip()
        if not candidato:
            return None
        try:
            return date.fromisoformat(candidato).isoformat()
        except ValueError:
            try:
                return pd.to_datetime(candidato).date().isoformat()
            except (ValueError, TypeError):
                return None
    return None


def _calcular_delta_textual(gasto_semana: float, gastos_por_semana: list[float]) -> str:
    """Compara ``gasto_semana`` com a media das 12 semanas anteriores."""
    if not gastos_por_semana:
        return "dentro da media"
    media = sum(gastos_por_semana) / len(gastos_por_semana)
    if media <= 0:
        return "dentro da media"
    razao = gasto_semana / media
    if razao > 1 + LIMITE_FAIXA_DENTRO:
        return "acima da media"
    if razao < 1 - LIMITE_FAIXA_DENTRO:
        return "abaixo da media"
    return "dentro da media"


def _gastos_12_semanas(df_gastos: pd.DataFrame, fim_semana_atual: date) -> list[float]:
    """Soma de gastos para cada uma das 12 semanas anteriores a fim_semana_atual."""
    if df_gastos.empty:
        return []
    gastos: list[float] = []
    for offset in range(1, 13):
        ini, fim = _semana_iso(fim_semana_atual - timedelta(days=7 * offset))
        df_s = _filtrar_intervalo(df_gastos, ini, fim)
        if df_s.empty:
            continue
        soma = float(df_s["valor"].abs().sum())
        if soma > 0:
            gastos.append(soma)
    return gastos


def gerar_financas_cache(
    vault_root: Path,
    xlsx_path: Path | None = None,
    referencia: date | None = None,
    saida: Path | None = None,
    gerado_em: datetime | None = None,
) -> Path:
    """Gera ``financas-cache.json`` no Vault.

    Parametros:
        vault_root: raiz do vault Mobile.
        xlsx_path: XLSX consolidado. Default
            ``<repo>/data/output/ouroboros_2026.xlsx``.
        referencia: data dentro da semana a ser computada. Default:
            hoje (TZ -03:00).
        saida: caminho final do JSON. Default
            ``<vault_root>/.ouroboros/cache/financas-cache.json``.
        gerado_em: timestamp do payload. Default: agora.

    Retorna o ``Path`` do arquivo gravado.
    """
    vault_root = Path(vault_root).expanduser().resolve()
    if xlsx_path is None:
        repo_root = Path(__file__).resolve().parents[2]
        xlsx_path = repo_root / "data" / "output" / "ouroboros_2026.xlsx"
    else:
        xlsx_path = Path(xlsx_path)
    if referencia is None:
        referencia = datetime.now(TZ_LOCAL).date()
    if saida is None:
        saida = vault_root / ".ouroboros" / "cache" / "financas-cache.json"
    else:
        saida = Path(saida)

    df = _carregar_extrato(xlsx_path)
    df_gastos = _filtrar_gastos(df)

    inicio_atual, fim_atual = _semana_iso(referencia)
    inicio_anterior, fim_anterior = _semana_iso(referencia - timedelta(days=7))

    df_atual = _filtrar_intervalo(df_gastos, inicio_atual, fim_atual)
    df_anterior = _filtrar_intervalo(df_gastos, inicio_anterior, fim_anterior)

    gasto_semana = round(float(df_atual["valor"].abs().sum()) if not df_atual.empty else 0.0, 2)
    gasto_semana_anterior = round(
        float(df_anterior["valor"].abs().sum()) if not df_anterior.empty else 0.0, 2
    )

    historico = _gastos_12_semanas(df_gastos, inicio_atual)
    delta_textual = _calcular_delta_textual(gasto_semana, historico)

    top_categorias = _agregar_top_categorias(df_atual, gasto_semana)
    ultimas = _ultimas_transacoes(df_gastos)

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "gerado_em": _gerado_em_iso(gerado_em),
        "periodo_referencia": f"{inicio_atual.isoformat()} a {fim_atual.isoformat()}",
        "gasto_semana": gasto_semana,
        "gasto_semana_anterior": gasto_semana_anterior,
        "delta_textual": delta_textual,
        "top_categorias": top_categorias,
        "ultimas_transacoes": ultimas,
    }
    write_json_atomic(saida, payload)
    logger.info(
        "financas-cache.json gerado: gasto_semana=%.2f, top=%d, ultimas=%d",
        gasto_semana,
        len(top_categorias),
        len(ultimas),
    )
    return saida


# "O dinheiro e um bom servo, mas um mau mestre." -- Francis Bacon
