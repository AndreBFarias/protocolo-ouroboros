---
concluida_em: 2026-04-21
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 55
  title: "Fix crítico: classificador de tipo de transação não respeita sinal do valor"
  touches:
    - path: src/transform/normalizer.py
      reason: "inferir_tipo_transacao descarta sinal e classifica por regex frágil"
    - path: src/extractors/nubank_cartao.py
      reason: "valor = abs(float(valor_str)) perde o sinal antes de normalizar"
    - path: src/extractors/nubank_cc.py
      reason: "_classificar_tipo já correto, mas normalizer sobrescreve"
    - path: src/pipeline.py
      reason: "normalizar_transacao sobrescreve o tipo setado pelos extratores"
    - path: tests/test_normalizer.py
      reason: "novos testes regressivos"
    - path: tests/test_pipeline_tipo_contrato.py
      reason: "teste de contrato global"
  n_to_n_pairs: []
  forbidden:
    - "Remover o extrator nubank_cartao.py"
    - "Trocar Nubank cartão para usar nubank_cc.py"
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/ -x -q"
      timeout: 120
    - cmd: ".venv/bin/pytest tests/test_normalizer.py tests/test_pipeline_tipo_contrato.py -v"
      timeout: 60
  acceptance_criteria:
    - "Transações com descrição 'Juros por fatura atrasada', 'IOF por fatura atrasada', 'Multa por fatura atrasada' são classificadas como Despesa (não Receita)"
    - "Transações com descrição 'TRANSF ENVIADA PIX' são classificadas como Despesa (não Receita)"
    - "Transações com descrição 'Fatura de cartão' em extrato de conta-corrente são classificadas como Transferência Interna"
    - "Compras em varejo (AGROPECUARIA, DROGARIA, SUPERVENDAS, MEG FARMA, etc.) não geram transações com tipo=Receita"
    - "Pipeline preserva sinal original do CSV: valor negativo no CSV Nubank CC vira valor positivo no XLSX com tipo=Despesa; valor positivo com descrição de recebimento vira tipo=Receita"
    - "Extrator nubank_cartao passa sinal implícito (cartão de crédito é sempre Despesa por default, exceto estorno explícito detectado por regex em title)"
    - "Após pipeline, contagem de Receitas no ouroboros_2026.xlsx cai para <= 250 linhas (hoje: 1942)"
    - "Soma de Receitas em 2026-04 <= R$ 8.500 (hoje: R$ 9.939,24) — valor bate com salário + rendimentos + reembolso"
  proof_of_work_esperado: |
    .venv/bin/python <<'EOF'
    import pandas as pd
    df = pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato')
    df['data'] = pd.to_datetime(df['data'])
    abril = df[(df['data']>='2026-04-01') & (df['data']<'2026-05-01')]
    rec_abr = abril[abril['tipo']=='Receita']['valor'].sum()
    n_rec_total = len(df[df['tipo']=='Receita'])
    juros_rec = len(abril[(abril['tipo']=='Receita') & (abril['local'].str.contains('Juros|IOF|Multa', na=False))])
    assert rec_abr <= 8500, f"Receita abril {rec_abr} > 8500"
    assert n_rec_total <= 250, f"Receitas totais {n_rec_total} > 250"
    assert juros_rec == 0, f"Juros/IOF/Multa como Receita: {juros_rec}"
    print(f"OK receita-abril=R$ {rec_abr:,.2f}  receitas-total={n_rec_total}  juros-como-receita={juros_rec}")
    EOF
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 55 — Fix crítico: classificador de tipo de transação

**Status:** CONCLUÍDA
**Data:** 2026-04-21
**Prioridade:** P0 CRÍTICA
**Tipo:** Bugfix estrutural
**Dependências:** nenhuma (bloqueia 56, 57)
**Desbloqueia:** todas as métricas financeiras honestas
**Issue:** AUDIT-2026-04-21-1
**ADR:** --

---

## Problema

Auditoria de 2026-04-21 (ver `docs/auditoria/2026-04-21_dashboard_audit.md` se criado) confirmou:

- **1.761 linhas** no `ouroboros_2026.xlsx` marcadas como `tipo=Receita` que são falsas (compras, juros, multas, transferências enviadas, faturas de cartão).
- **R$ 280.286,31** de "receita" falsa contaminam saldos históricos.
- Em 2026-04: 47 "Receitas" totalizam R$ 9.939,24 enquanto real deveria ser ≈ R$ 8.000 (só salário + rendimentos + reembolso).
- Taxa de poupança exibida "70.1%" é mentirosa; real ≈ 38%.

**Raiz determinística:**

`src/transform/normalizer.py:72-75`:
```python
if valor > 0:
    return "Receita"
return "Despesa"
```

Combinado com:
1. `src/extractors/nubank_cartao.py:102`: `valor = abs(float(valor_str))` — perde sinal antes de chegar ao normalizer.
2. `src/pipeline.py:202`: chama `normalizar_transacao(valor=t.valor, ...)` — sobrescreve o `tipo` correto vindo do extrator.
3. Valores em CSV `date,title,amount` da Nubank cartão já vêm positivos para compras (é fatura, todos são débitos do cartão) — não há sinal útil.

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---|---|---|
| Extrator Nubank cartão | `src/extractors/nubank_cartao.py` | lê CSV de fatura, já tem `_classificar_tipo` que retorna "Despesa" por default |
| Extrator Nubank CC | `src/extractors/nubank_cc.py` | lê CSV de conta-corrente, `_classificar_tipo` já respeita sinal |
| Normalizer | `src/transform/normalizer.py` | normaliza + infere tipo (origem do bug) |
| Pipeline | `src/pipeline.py:190-229` | orquestra extrator→normalizer |

## Implementação

### Fase 1 — Remover reinferência de tipo no normalizer

`normalizar_transacao()` deve ACEITAR o `tipo` vindo do extrator. Assinatura nova:

```python
def normalizar_transacao(
    data_transacao: date,
    valor: float,
    descricao: str,
    banco_origem: str,
    tipo_extrato: str = "cc",
    identificador: Optional[str] = None,
    subtipo: Optional[str] = None,
    arquivo_origem: Optional[str] = None,
    tipo_sugerido: Optional[str] = None,  # novo
    valor_original_com_sinal: Optional[float] = None,  # novo
) -> dict:
```

Lógica:
1. Se `tipo_sugerido` está presente, usa ele, exceto se regex de Transferência Interna/Imposto casa (essas têm prioridade).
2. Senão, usa `valor_original_com_sinal` + regex atuais.
3. **Nunca** usa `abs(valor) > 0` para inferir Receita.

### Fase 2 — Pipeline passa o tipo vindo do extrator

`src/pipeline.py:202-213`:

```python
transacao_norm = normalizar_transacao(
    data_transacao=t.data,
    valor=t.valor,
    descricao=t.descricao,
    banco_origem=t.banco_origem,
    tipo_extrato="cartao" if "cartao" in t.banco_origem.lower() or t.forma_pagamento == "Crédito" else "cc",
    identificador=t.identificador,
    subtipo=_inferir_subtipo(arquivo),
    arquivo_origem=str(arquivo),
    tipo_sugerido=t.tipo,  # <-- novo
)
```

### Fase 3 — Fix nubank_cartao: detectar estorno explícito

Em `src/extractors/nubank_cartao.py:_classificar_tipo`, adicionar regex:

```python
if re.search(r'\bEstorno\b|\bReembolso\b|\bCrédito a fatura\b', titulo, re.IGNORECASE):
    return "Receita"  # estorno/crédito na fatura é entrada
```

Default continua `"Despesa"` (fatura de cartão de crédito, tudo é saída).

### Fase 4 — Reprocessar XLSX

Rodar `./run.sh --tudo` após fix para regenerar `ouroboros_2026.xlsx` com classificações corretas.

### Fase 5 — Testes regressivos

`tests/test_normalizer.py` (novo ou estendido):

```python
def test_juros_fatura_atrasada_e_despesa():
    r = normalizar_transacao(data(2026,4,1), 53.23, "Juros por fatura atrasada", "Nubank",
                             tipo_extrato="cartao", tipo_sugerido="Despesa")
    assert r["tipo"] == "Despesa"

def test_transf_enviada_e_despesa():
    r = normalizar_transacao(date(2026,4,3), 96.15, "TRANSF ENVIADA PIX", "Nubank",
                             tipo_extrato="cc", tipo_sugerido="Despesa", valor_original_com_sinal=-96.15)
    assert r["tipo"] == "Despesa"

def test_fatura_cartao_em_cc_e_transferencia_interna():
    r = normalizar_transacao(date(2026,4,14), 90.64, "Fatura de cartão", "Nubank",
                             tipo_extrato="cc", tipo_sugerido="Despesa", valor_original_com_sinal=-90.64)
    assert r["tipo"] == "Transferência Interna"

def test_salario_e_receita():
    r = normalizar_transacao(date(2026,4,8), 7442.38, "PAGTO SALARIO", "Itaú",
                             tipo_extrato="cc", tipo_sugerido="Receita", valor_original_com_sinal=7442.38)
    assert r["tipo"] == "Receita"

def test_compra_varejo_e_despesa():
    r = normalizar_transacao(date(2026,4,10), 52.00, "DROGARIA SILVA FARMA", "Nubank",
                             tipo_extrato="cartao", tipo_sugerido="Despesa")
    assert r["tipo"] == "Despesa"
```

`tests/test_pipeline_tipo_contrato.py` (novo):

```python
def test_contrato_global_receita_razoavel():
    """Soma de Receitas do XLSX não deve exceder soma de eventos-de-entrada reais."""
    df = pd.read_excel("data/output/ouroboros_2026.xlsx", sheet_name="extrato")
    n_receitas = len(df[df["tipo"] == "Receita"])
    assert n_receitas <= 250, f"Pipeline classificou {n_receitas} transações como Receita (limiar 250)"
```

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A55-1 | Mudar assinatura de `normalizar_transacao` sem parâmetros default quebra callers | Adicionar `tipo_sugerido=None` e `valor_original_com_sinal=None` como kwargs opcionais |
| A55-2 | Regex de Transferência Interna pode casar em falso para "PAGAMENTO DE BOLETO" genérico | Manter regex existente, só confirmar que `re.search(r"PAGAMENTO DE BOLETO.*NU PAGAMENTOS")` continua casando |
| A55-3 | Reprocessar XLSX pode perder classificações manuais de `overrides.yaml` | Verificar que pipeline respeita overrides.yaml ANTES do normalizer |
| A55-4 | Testes unitários passam mas runtime-real pode falhar se CSV de teste não representa realidade | Rodar smoke completo (`./run.sh --tudo`) e conferir XLSX gerado |

## Evidências Obrigatórias

- [ ] `make lint` exit 0
- [ ] `.venv/bin/pytest tests/ -q` exit 0 com novos testes
- [ ] `./run.sh --tudo` completa sem erro
- [ ] Script proof-of-work acima retorna OK
- [ ] Dashboard Visão Geral 2026-04 mostra taxa de poupança coerente (entre 30% e 50%)

## Gauntlet (após fix)

```bash
bash scripts/finish_sprint.sh 55
```

## Conferência Artesanal Opus

Validador abre dashboard, vai em Visão Geral → 2026-04, confirma:
- Receita entre R$ 7.500 e R$ 8.500
- Despesa entre R$ 4.500 e R$ 5.500
- Taxa de poupança entre 30% e 45%
- Zero "Juros por fatura atrasada" como Receita no Extrato
- Zero "TRANSF ENVIADA PIX" como Receita no Extrato

---

*"A verdade é a primeira baixa da guerra." — Ésquilo (invertido aqui: é a primeira vitória da auditoria)*
