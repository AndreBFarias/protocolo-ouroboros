---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-FIX-02
  title: "Corrigir filtro Despesa R$ 0,00 no card KPI da página Extrato"
  prioridade: P0
  estimativa: 2h
  onda: C1
  origem: "AUDITORIA_REDESIGN_2026-05-05.md §2.3 e §6.3 (top problema #2)"
  depende_de: []
  bloqueia: []
  touches:
    - path: src/dashboard/paginas/extrato.py
      reason: "linhas 238-240 (literal): valores=pd.to_numeric(...); apenas_despesas = operacional[valores < 0].copy(); apenas_despesas['__abs'] = (-valores[valores < 0]).values. As 3 linhas formam o BUG e devem ser substituídas por filtro tipo == 'Despesa' usando valor absoluto direto (sem __abs intermediário)."
    - path: tests/test_extrato_kpi_despesa.py
      reason: "NOVO -- testa que com 78 transações abril/2026 a despesa retornada não é zero"
  forbidden:
    - "Mudar a estrutura do XLSX para fazer valores ficarem negativos"
    - "Alterar contratos de smoke aritmético em scripts/smoke_aritmetico.py"
  hipotese:
    - "Em src/dashboard/paginas/extrato.py:239 o filtro `valores < 0` retorna 0 linhas porque os valores no XLSX são sempre positivos. O tipo correto de filtro é `df['tipo'] == 'Despesa'`. Validar com grep + python."
  tests:
    - cmd: "grep -nE 'valores < 0|tipo.*Despesa' src/dashboard/paginas/extrato.py"
      esperado: "linha 239 ou próxima reflete o novo filtro `df['tipo'] == 'Despesa'`"
    - cmd: ".venv/bin/pytest tests/test_extrato_kpi_despesa.py -v"
      esperado: "PASSED"
    - cmd: ".venv/bin/python -c \"import openpyxl; wb=openpyxl.load_workbook('data/output/ouroboros_2026.xlsx', read_only=True); ws=wb['extrato']; rows=[r for r in ws.iter_rows(values_only=True) if r[0] and str(r[0]).startswith('2026-04') and (r[8] if len(r)>8 else None)=='Despesa']; print('despesas abril', len(rows), sum(float(r[1]) for r in rows))\""
      esperado: "despesas abril 60+ <total != 0>"
  acceptance_criteria:
    - "Card KPI Despesa em Finanças/Extrato mostra valor != R$ 0,00 quando há transações tipo='Despesa' no período"
    - "Para abril/2026: card Despesa exibe R$ 3.391,77 (valor real apurado pela auditoria) ± centavos"
    - "Card Saldo = Receita - Despesa (não Receita = Saldo como hoje)"
    - "Bloco lateral 'Breakdown por Categoria' deixa de mostrar 'Sem despesas no período' quando há despesas"
    - "Sem regressão em outras telas (Análise, Categorias, Metas, IRPF) que usam o mesmo dataframe"
  proof_of_work_esperado: |
    # 1. baseline backend
    .venv/bin/python -c "
    import openpyxl
    wb = openpyxl.load_workbook('data/output/ouroboros_2026.xlsx', read_only=True)
    ws = wb['extrato']
    rows = list(ws.iter_rows(values_only=True))
    despesa_total = sum(float(r[1]) for r in rows[1:] if r and len(r)>8 and r[8]=='Despesa' and r[0] and str(r[0]).startswith('2026-04'))
    print(f'BACKEND despesa abril/26 = R\$ {despesa_total:,.2f}')   # ~3391,77
    "

    # 2. dashboard ao vivo
    nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    .venv/bin/python -c "
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_context().new_page()
        page.goto('http://127.0.0.1:8520/?cluster=Finan%C3%A7as&tab=Extrato')
        page.wait_for_timeout(5000)
        # captura valor do KPI Despesa
        valor = page.evaluate('''() => {
            const labels = Array.from(document.querySelectorAll('[data-testid=\"stMetricLabel\"]'));
            const i = labels.findIndex(l => /DESPESA/i.test(l.textContent));
            if (i < 0) return 'KPI ausente';
            const vs = document.querySelectorAll('[data-testid=\"stMetricValue\"]');
            return vs[i] ? vs[i].textContent : 'sem valor';
        }''')
        print('DASHBOARD KPI Despesa =', valor)   # esperado: 'R\$ 3.391,77' ou similar
        page.screenshot(path='/tmp/proof_fix_02.png', full_page=True)
        b.close()
    "
```

---

# Sprint UX-RD-FIX-02 — Bug Despesa R$ 0,00 no Extrato

**Status:** BACKLOG — Onda C1 (higiene crítica).

## 1. Contexto

A auditoria detectou que a tela `Finanças → Extrato` mostra **Despesa R$ 0,00** mesmo havendo 78 transações em abril/2026. Investigação:

- XLSX `data/output/ouroboros_2026.xlsx` aba `extrato` tem 6094 linhas; 4760 com `tipo == 'Despesa'`; **abril/2026 tem 60+ despesas somando R$ 3.391,77**.
- Em `src/dashboard/paginas/extrato.py:239` o código filtra:
  ```python
  apenas_despesas = operacional[valores < 0].copy()
  ```
- Como **valores são sempre positivos no XLSX** (a coluna `tipo` é o sinalizador, não o sinal), o filtro retorna conjunto vazio.

**Resultado**: bloco "Breakdown por Categoria" mostra "Sem despesas no período" e os KPIs ficam errados (Despesa R$ 0; Saldo == Receita).

## 2. Hipótese verificável (Fase ANTES)

```bash
# 1) Baseline real do XLSX
.venv/bin/python -c "
import openpyxl
wb = openpyxl.load_workbook('data/output/ouroboros_2026.xlsx', read_only=True)
ws = wb['extrato']
print('header', list(next(ws.iter_rows(values_only=True))))
neg = sum(1 for r in ws.iter_rows(values_only=True) if r and r[1] and float(r[1]) < 0)
print(f'linhas com valor<0: {neg}')   # esperado: 0 ou raríssimo
desp = sum(1 for r in ws.iter_rows(values_only=True) if r and len(r)>8 and r[8]=='Despesa')
print(f'linhas tipo=Despesa: {desp}')   # esperado: ~4760
"

# 2) Confirma o bug visualmente
grep -nE 'valores < 0|operacional\[valores' src/dashboard/paginas/extrato.py
```

Se `linhas com valor<0` for 0 e `linhas tipo=Despesa` for 4760+, hipótese confirmada: o filtro está usando o critério errado.

## 3. Tarefas

1. Rodar hipótese (§2).
2. Localizar todos os filtros suspeitos com `grep -nE 'valores [<>]= 0|operacional\[' src/dashboard/paginas/extrato.py`.
3. Substituir o **bloco de 3 linhas** (238-240) por filtro canônico:

   ```python
   # ANTES (linhas 238-240)
   valores = pd.to_numeric(operacional.get("valor"), errors="coerce").fillna(0.0)
   apenas_despesas = operacional[valores < 0].copy()
   apenas_despesas["__abs"] = (-valores[valores < 0]).values

   # DEPOIS
   apenas_despesas = operacional[operacional["tipo"] == "Despesa"].copy()
   apenas_despesas["__abs"] = pd.to_numeric(apenas_despesas["valor"], errors="coerce").fillna(0.0).abs()
   ```

   Verificar se `operacional` tem a coluna `tipo` -- se não, consultar dataframe-pai. Manter coluna `__abs` porque ela é usada em §240+ para agrupamento (mas calcular via `.abs()` direto, não via `-valores[valores < 0]` que retornaria NaN para tipos não-Despesa).
4. Garantir que **Receita**, **Saldo**, **Transferência Interna** continuam corretos (não tocar nesses).
5. Criar `tests/test_extrato_kpi_despesa.py` com pelo menos 4 testes:
   - `test_filtro_despesas_nao_vazio_quando_ha_tipo_despesa()`
   - `test_kpi_despesa_soma_apenas_tipo_despesa()`
   - `test_kpi_saldo_eh_receita_menos_despesa()`
   - `test_breakdown_categorias_inclui_despesas_quando_existem()`
6. Rodar gauntlet e capturar PNG do KPI corrigido (proof-of-work).
7. Validar regressão: `pytest tests/test_extrato.py tests/test_extrato_kpi_despesa.py tests/test_dashboard_app.py -v`.

## 4. Anti-débito

- Se descobrir que outros .py (categorias.py, analise.py) usam o mesmo padrão errado: **NÃO corrigir aqui**. Criar sprint UX-RD-FIX-02.B com escopo cross-pages.
- Se filtro novo `tipo == 'Despesa'` quebrar algum teste: investigar antes de "consertar". O teste antigo pode estar refletindo a regra errada.

## 5. Validação visual

```bash
# Capturar PNG da tela Extrato com KPI corrigido
nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
sleep 6
mkdir -p .playwright-mcp/auditoria/fix-02
.venv/bin/python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_context(viewport={'width':1440,'height':900}).new_page()
    page.goto('http://127.0.0.1:8520/?cluster=Finan%C3%A7as&tab=Extrato')
    page.wait_for_timeout(5000)
    page.screenshot(path='.playwright-mcp/auditoria/fix-02/extrato_corrigido.png', full_page=True)
    b.close()
"
```

Verificar no PNG: KPI **DESPESA** mostra valor formatado em R$ não-zero; bloco lateral mostra categorias com valores.

## 6. Gauntlet

```bash
make lint                                          # exit 0
make smoke                                         # 10/10
.venv/bin/pytest tests/ -q --tb=no                 # >=2520 + 4 novos = >=2524
.venv/bin/pytest tests/test_extrato_kpi_despesa.py -v   # 4/4
```

---

*"O número não mente; mente quem escolhe o filtro." -- adaptado de Tukey*
