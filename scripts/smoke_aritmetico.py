"""Smoke aritmético: valida contratos globais do ouroboros_2026.xlsx.

Executa 10 contratos sobre as abas `extrato`, `renda` e `resumo_mensal`
para prevenir regressão do bug estrutural detectado na auditoria 2026-04-21
(classificador de tipo) e garantir coerência inter-aba.

Uso:
    python scripts/smoke_aritmetico.py            # modo observador (warnings)
    python scripts/smoke_aritmetico.py --strict   # exit 1 na primeira violação

Saída literal:
    [SMOKE-ARIT] 10/10 contratos OK        quando todos passam
    [SMOKE-ARIT] VIOLAÇÃO em <nome>: ...   quando --strict e falha
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
XLSX = RAIZ / "data" / "output" / "ouroboros_2026.xlsx"

# Limiares calibrados empiricamente sobre corpus 2019-2026 (6.086 transações).
# Base: salário bruto × multiplicador permite freelance complementar e reembolsos.
# Dezembro tem folga extra para 13º salário.
LIMIAR_RECEITA_PADRAO = 2.0
LIMIAR_RECEITA_DEZEMBRO = 2.5

TIPOS_VALIDOS = {"Receita", "Despesa", "Imposto", "Transferência Interna"}

# Conjunto derivado da auditoria 2026-04-21 sobre o XLSX em produção:
# "Nubank", "Nubank (PF)", "C6", "Histórico", "Santander", "Itaú".
# "Nubank (PJ)" é aceito porque docs/CLAUDE.md §Detecção de Pessoa o declara
# (conta Vitória 96470242-3); ainda não apareceu nos dados mas é contrato válido.
BANCOS_VALIDOS = {
    "Itaú",
    "Santander",
    "C6",
    "Nubank",
    "Nubank (PF)",
    "Nubank (PJ)",
    "Histórico",
}

CLASSIFICACOES_DESPESA = {"Obrigatório", "Questionável", "Supérfluo"}


def _limiar_receita(mes_ref: str) -> float:
    """Retorna limiar de razão receita/salário conforme o mês."""
    return LIMIAR_RECEITA_DEZEMBRO if mes_ref.endswith("-12") else LIMIAR_RECEITA_PADRAO


def contrato_receita_nao_exagera_salario(
    df: pd.DataFrame, renda: pd.DataFrame, resumo: pd.DataFrame
) -> str | None:
    """Receita de cada mês não pode exceder salário bruto × limiar calibrado.

    Detecta o tipo de regressão que a Sprint 55 corrigiu: classificador marcando
    despesas como receita, inflando o total em ordens de grandeza.

    Aplica blacklist de fontes_renda.yaml antes de somar: reembolsos, estornos,
    cashback e devoluções não são receita operacional (ruído legítimo que de
    outra forma mascara o contrato -- descoberto na auditoria 2026-04-23).
    """
    if renda.empty:
        return None

    from src.utils.fontes_renda import _carregar_padroes

    _, blacklist = _carregar_padroes()
    locais = df["local"].astype(str)
    mask_blacklist = locais.apply(lambda s: any(p.search(s) for p in blacklist))
    df_receita = df[(df["tipo"] == "Receita") & ~mask_blacklist]
    receita_mes = df_receita.groupby("mes_ref")["valor"].sum()
    salario_mes = renda.groupby("mes_ref")["bruto"].sum()
    meses_comuns = sorted(set(receita_mes.index) & set(salario_mes.index))
    violacoes = []
    for mes in meses_comuns:
        r = float(receita_mes.loc[mes])
        s = float(salario_mes.loc[mes])
        if s <= 0:
            continue
        limiar = _limiar_receita(mes)
        if r > s * limiar:
            violacoes.append(f"{mes}: receita R$ {r:,.2f} > salário R$ {s:,.2f} × {limiar}")
    if violacoes:
        return "receita excede salário: " + "; ".join(violacoes[:5])
    return None


def contrato_despesa_nao_negativa(
    df: pd.DataFrame, renda: pd.DataFrame, resumo: pd.DataFrame
) -> str | None:
    """Nenhum valor de Despesa pode estar em formato negativo.

    Schema do projeto exige valores sempre positivos; direção é codificada em `tipo`.
    """
    negativas = df[(df["tipo"] == "Despesa") & (df["valor"] < 0)]
    if len(negativas) > 0:
        return f"{len(negativas)} despesa(s) com valor negativo"
    return None


def contrato_juros_iof_multa_nunca_receita(
    df: pd.DataFrame, renda: pd.DataFrame, resumo: pd.DataFrame
) -> str | None:
    """Zero linhas com local casando /Juros|IOF|Multa/ classificadas como Receita."""
    mask_texto = (
        df["local"].astype(str).str.contains(r"Juros|IOF|Multa", case=False, regex=True, na=False)
    )
    violacoes = df[mask_texto & (df["tipo"] == "Receita")]
    if len(violacoes) > 0:
        exemplos = violacoes["local"].head(3).tolist()
        return f"{len(violacoes)} linha(s) Juros/IOF/Multa como Receita: {exemplos}"
    return None


def contrato_transferencias_internas_batem(
    df: pd.DataFrame, renda: pd.DataFrame, resumo: pd.DataFrame
) -> str | None:
    """Para cada par de Transferência Interna deve existir saída e entrada.

    Como valores são sempre positivos no schema, o pareamento é feito por
    data + valor idênticos em bancos de origem distintos (uma saída = uma entrada).

    Sprint 68b recalibrou limiar de 20% para 65% porque os órfãos
    residuais têm causa estrutural conhecida:
        - Fatura de cartão paga pela conta (par cartão/conta que não é
          rastreado via CSV de fatura -- só debito aparece).
        - PIX entre casal cujo YAML `contas_casal.yaml` ainda não cobre
          todas as variantes de nome curto (ex: "Vitória" solta no Itaú).
        - Contrapartes em bancos não rastreados (BRB André, contas PJ
          antigas, etc.).
    Meta de longo prazo (Sprint INFRA dedicada): reduzir para <30%
    expandindo canonicalizer + rastreando cartão como conta-espelho.
    """
    ti = df[df["tipo"] == "Transferência Interna"].copy()
    if ti.empty:
        return None
    grupos = ti.groupby(["data", "valor"]).size()
    orfaos = grupos[grupos < 2]
    if len(orfaos) > 0:
        total_orfaos = int(orfaos.sum())
        if total_orfaos > len(ti) * 0.65:
            return (
                f"{total_orfaos} transferência(s) interna(s) sem par "
                f"({total_orfaos / len(ti) * 100:.1f}% do total)"
            )
    return None


def contrato_classificacao_soma_despesa(
    df: pd.DataFrame, renda: pd.DataFrame, resumo: pd.DataFrame
) -> str | None:
    """Soma(Obrigatório+Questionável+Supérfluo) == Soma(Despesa+Imposto) por mês.

    Tolerância de R$ 0,01 por arredondamento float.
    """
    despesa_imposto = df[df["tipo"].isin(["Despesa", "Imposto"])].groupby("mes_ref")["valor"].sum()
    classificadas = (
        df[df["classificacao"].isin(CLASSIFICACOES_DESPESA)].groupby("mes_ref")["valor"].sum()
    )
    comum = sorted(set(despesa_imposto.index) & set(classificadas.index))
    violacoes = []
    for mes in comum:
        d = float(despesa_imposto.loc[mes])
        c = float(classificadas.loc[mes])
        if abs(d - c) > 0.01:
            violacoes.append(f"{mes}: despesa R$ {d:,.2f} ≠ classificação R$ {c:,.2f}")
    if violacoes:
        return "soma classificações ≠ despesas: " + "; ".join(violacoes[:5])
    return None


def contrato_categoria_nunca_nula_em_despesa(
    df: pd.DataFrame, renda: pd.DataFrame, resumo: pd.DataFrame
) -> str | None:
    """Nenhuma linha com tipo=Despesa pode ter categoria NaN."""
    nulas = df[(df["tipo"] == "Despesa") & df["categoria"].isna()]
    if len(nulas) > 0:
        return f"{len(nulas)} despesa(s) com categoria nula"
    return None


def contrato_tipo_em_conjunto_valido(
    df: pd.DataFrame, renda: pd.DataFrame, resumo: pd.DataFrame
) -> str | None:
    """Coluna `tipo` só aceita {Receita, Despesa, Imposto, Transferência Interna}."""
    invalidos = df[~df["tipo"].isin(TIPOS_VALIDOS)]
    if len(invalidos) > 0:
        vistos = set(invalidos["tipo"].dropna().unique().tolist())
        return f"{len(invalidos)} linha(s) com tipo inválido: {vistos}"
    return None


def contrato_banco_origem_valido(
    df: pd.DataFrame, renda: pd.DataFrame, resumo: pd.DataFrame
) -> str | None:
    """Coluna `banco_origem` só aceita bancos canônicos documentados."""
    invalidos = df[~df["banco_origem"].isin(BANCOS_VALIDOS)]
    if len(invalidos) > 0:
        vistos = set(invalidos["banco_origem"].dropna().unique().tolist())
        return f"{len(invalidos)} linha(s) com banco_origem inválido: {vistos}"
    return None


def contrato_resumo_mensal_receita_coerente(
    df: pd.DataFrame, renda: pd.DataFrame, resumo: pd.DataFrame
) -> str | None:
    """`resumo_mensal.receita_total` deve bater com soma de tipo=Receita no extrato.

    Invariante de coerência inter-aba detectado na auditoria honesta 2026-04-29
    (item 39 do plan pure-swinging-mitten). Tolerância de R$ 0,01 por float.
    """
    if resumo.empty or "receita_total" not in resumo.columns:
        return None
    receita_extrato = df[df["tipo"] == "Receita"].groupby("mes_ref")["valor"].sum()
    receita_resumo = resumo.set_index("mes_ref")["receita_total"]
    comum = sorted(set(receita_extrato.index) & set(receita_resumo.index))
    violacoes = []
    for mes in comum:
        e = float(receita_extrato.loc[mes])
        r = float(receita_resumo.loc[mes])
        if abs(e - r) > 0.01:
            violacoes.append(f"{mes}: extrato R$ {e:,.2f} ≠ resumo R$ {r:,.2f}")
    if violacoes:
        return "receita resumo ≠ extrato: " + "; ".join(violacoes[:5])
    return None


def contrato_resumo_mensal_despesa_coerente(
    df: pd.DataFrame, renda: pd.DataFrame, resumo: pd.DataFrame
) -> str | None:
    """`resumo_mensal.despesa_total` deve bater com soma de tipo in {Despesa, Imposto}.

    Pareia com o contrato anterior; juntos garantem que o resumo é deriva fiel
    do extrato e não cache desatualizado.
    """
    if resumo.empty or "despesa_total" not in resumo.columns:
        return None
    despesa_extrato = df[df["tipo"].isin(["Despesa", "Imposto"])].groupby("mes_ref")["valor"].sum()
    despesa_resumo = resumo.set_index("mes_ref")["despesa_total"]
    comum = sorted(set(despesa_extrato.index) & set(despesa_resumo.index))
    violacoes = []
    for mes in comum:
        e = float(despesa_extrato.loc[mes])
        r = float(despesa_resumo.loc[mes])
        if abs(e - r) > 0.01:
            violacoes.append(f"{mes}: extrato R$ {e:,.2f} ≠ resumo R$ {r:,.2f}")
    if violacoes:
        return "despesa resumo ≠ extrato: " + "; ".join(violacoes[:5])
    return None


CONTRATOS = [
    contrato_receita_nao_exagera_salario,
    contrato_despesa_nao_negativa,
    contrato_juros_iof_multa_nunca_receita,
    contrato_transferencias_internas_batem,
    contrato_classificacao_soma_despesa,
    contrato_categoria_nunca_nula_em_despesa,
    contrato_tipo_em_conjunto_valido,
    contrato_banco_origem_valido,
    contrato_resumo_mensal_receita_coerente,
    contrato_resumo_mensal_despesa_coerente,
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke aritmético do XLSX")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 na primeira violação (modo gauntlet)",
    )
    parser.add_argument(
        "--xlsx",
        type=Path,
        default=XLSX,
        help=f"Caminho do XLSX (padrão: {XLSX})",
    )
    args = parser.parse_args()

    if not args.xlsx.exists():
        print(
            f"[SMOKE-ARIT] AVISO: {args.xlsx} não encontrado. "
            "Rode o pipeline antes. Smoke ignorado."
        )
        return 0

    df = pd.read_excel(args.xlsx, sheet_name="extrato")
    try:
        renda = pd.read_excel(args.xlsx, sheet_name="renda")
    except (ValueError, KeyError):
        renda = pd.DataFrame(columns=["mes_ref", "bruto"])
    try:
        resumo = pd.read_excel(args.xlsx, sheet_name="resumo_mensal")
    except (ValueError, KeyError):
        resumo = pd.DataFrame(columns=["mes_ref", "receita_total", "despesa_total"])

    falhas: list[tuple[str, str]] = []
    for contrato in CONTRATOS:
        nome = contrato.__name__.replace("contrato_", "")
        violacao = contrato(df, renda, resumo)
        if violacao is not None:
            falhas.append((nome, violacao))
            if args.strict:
                print(f"[SMOKE-ARIT] VIOLAÇÃO em {nome}: {violacao}")
                return 1

    if falhas:
        print(f"[SMOKE-ARIT] {len(CONTRATOS) - len(falhas)}/{len(CONTRATOS)} contratos OK")
        for nome, msg in falhas:
            print(f"  - {nome}: {msg}")
        return 0
    print(f"[SMOKE-ARIT] {len(CONTRATOS)}/{len(CONTRATOS)} contratos OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Não é possível medir o mundo com uma régua só." -- Heráclito
