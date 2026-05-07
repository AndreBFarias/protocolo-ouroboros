---
id: UX-V-2.2
titulo: Página Pagamentos com calendário mês inteiro + lista lateral acionável
status: backlog
prioridade: alta
data_criacao: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-02]
co_executavel_com: [UX-V-2.1, UX-V-2.3, UX-V-2.7]
esforco_estimado_horas: 5
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (página 04)
mockup: novo-mockup/mockups/04-pagamentos.html
---

# Sprint UX-V-2.2 — Página Pagamentos paridade com mockup

## Contexto

Auditoria 2026-05-07 identificou divergência ALTA na página **Pagamentos** vs `mockups/04-pagamentos.html`:

- Mockup mostra **calendário do MÊS INTEIRO** (5 semanas Seg-Dom) com pílulas coloridas em datas com pagamentos
- Mockup tem **setas de navegação** ◀ ▶ entre meses + cabeçalho "MAIO · 2026"
- Mockup tem **lista lateral PROXIMOS 14 DIAS** com **valores** + **botões "pagar"/"agendar"** por linha
- Mockup tem **legenda no rodapé** do calendário (fixo/variável/cartão/em atraso) + total mensal "10 pagamentos no mês · R$ 18.509,00"

Dashboard atual mostra apenas **14 dias** sem botões nem valores na lista lateral.

## Página afetada

`src/dashboard/paginas/pagamentos.py` apenas.

## Objetivo

1. Expandir calendário para mês inteiro (5 semanas Seg-Dom).
2. Adicionar setas de navegação entre meses + cabeçalho "MES · ANO".
3. Lista lateral mostrar **8-10 vencimentos** com valor + botão "agendar" inline.
4. Adicionar legenda fixo/variável/cartão/em atraso no rodapé do calendário.
5. Adicionar total mensal no rodapé ("N pagamentos no mês · R$ X").

## Validação ANTES (grep obrigatório — padrão `(k)`)

```bash
wc -l src/dashboard/paginas/pagamentos.py
grep -n "calendario\|calend\|14\|próximos\|prazos" src/dashboard/paginas/pagamentos.py | head -10

# Origem dos dados de pagamento
grep -rn "prazos\|aluguel\|natacao\|sesc\|vencimento" src/dashboard/dados.py mappings/ 2>/dev/null | head -10

# XLSX tem aba prazos?
python3 -c "
from openpyxl import load_workbook
import sys
try:
    wb = load_workbook('data/output/ouroboros_2026.xlsx', read_only=True)
    print('abas:', wb.sheetnames)
except Exception as e:
    print('erro:', e)
"
```

## Spec de implementação

### 1. Função para calcular calendário do mês

```python
from calendar import monthrange
from datetime import date, timedelta

def _gerar_calendario_mes(ano: int, mes: int) -> list[list[date | None]]:
    """Retorna matriz 5x7 (semanas x dias) com datas do mês.
    
    Células fora do mês = None. Primeira semana começa Seg, última Dom.
    """
    primeiro_dia = date(ano, mes, 1)
    _, total_dias = monthrange(ano, mes)
    # Dias antes do dia 1 (preencher início da primeira semana)
    weekday_inicio = primeiro_dia.weekday()  # Seg=0
    dias = []
    for _ in range(weekday_inicio):
        dias.append(None)
    for d in range(1, total_dias + 1):
        dias.append(date(ano, mes, d))
    # Preencher até completar última semana
    while len(dias) % 7 != 0:
        dias.append(None)
    # Particionar em semanas
    semanas = [dias[i:i+7] for i in range(0, len(dias), 7)]
    return semanas
```

### 2. Função para mapear pagamentos por data

```python
def _pagamentos_por_data(df_prazos: pd.DataFrame, ano: int, mes: int) -> dict[date, list[dict]]:
    """Agrupa pagamentos do mês por data de vencimento.
    
    Retorna ``{date(2026,5,10): [{label, tipo, valor}], ...}``.
    Tipos canônicos: "fixo", "variavel", "cartao", "em_atraso".
    """
    if df_prazos.empty:
        return {}
    pgs = {}
    hoje = date.today()
    for _, row in df_prazos.iterrows():
        try:
            dia = int(row.get('dia_vencimento', 0))
        except (ValueError, TypeError):
            continue
        if dia < 1 or dia > 31:
            continue
        try:
            d = date(ano, mes, dia)
        except ValueError:
            continue
        valor = float(row.get('valor', 0) or 0)
        label = str(row.get('conta', row.get('nome', '?'))).strip()
        tipo = "em_atraso" if d < hoje else "fixo"
        pgs.setdefault(d, []).append({
            "label": label[:14],
            "tipo": tipo,
            "valor": valor,
        })
    return pgs
```

### 3. Renderização do calendário

```python
def _calendario_html(ano: int, mes: int, pagamentos_por_data: dict) -> str:
    semanas = _gerar_calendario_mes(ano, mes)
    cabecalho = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
    NOMES_MESES = ["", "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO",
                   "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO",
                   "NOVEMBRO", "DEZEMBRO"]
    
    head_dias = "".join(f'<div class="cal-head-dia">{d}</div>' for d in cabecalho)
    
    celulas = []
    total_pgs = 0
    total_valor = 0.0
    for semana in semanas:
        for d in semana:
            if d is None:
                celulas.append('<div class="cal-celula cal-empty"></div>')
                continue
            pg_dia = pagamentos_por_data.get(d, [])
            pills = ""
            classe_dia = ""
            if pg_dia:
                total_pgs += len(pg_dia)
                total_valor += sum(p["valor"] for p in pg_dia)
                classe_dia = " cal-tem-pg"
                pills = "".join(
                    f'<span class="cal-pill cal-pill-{p["tipo"]}">'
                    f'{p["label"].upper()}</span>'
                    for p in pg_dia
                )
            celulas.append(
                f'<div class="cal-celula{classe_dia}">'
                f'<span class="cal-num">{d.day:02d}</span>'
                f'{pills}'
                f'</div>'
            )
    
    grid = head_dias + "".join(celulas)
    
    return minificar(f"""
    <div class="pagamentos-calendario">
      <div class="cal-header">
        <span class="cal-titulo">{NOMES_MESES[mes].lower()} · {ano}</span>
        <div class="cal-nav">
          <button class="cal-nav-btn">SEG-DOM</button>
        </div>
      </div>
      <div class="cal-grid">{grid}</div>
      <div class="cal-legenda">
        <span class="cal-legenda-item"><span class="cal-pill cal-pill-fixo"></span> fixo</span>
        <span class="cal-legenda-item"><span class="cal-pill cal-pill-variavel"></span> variável</span>
        <span class="cal-legenda-item"><span class="cal-pill cal-pill-cartao"></span> cartão</span>
        <span class="cal-legenda-item"><span class="cal-pill cal-pill-em_atraso"></span> em atraso</span>
        <span class="cal-legenda-total">{total_pgs} pagamentos no mês · R$ {total_valor:,.2f}</span>
      </div>
    </div>
    """)
```

### 4. Lista lateral com botões

```python
def _lista_proximos_html(pagamentos_por_data: dict) -> str:
    hoje = date.today()
    proximos = sorted(
        [(d, pgs) for d, pgs in pagamentos_por_data.items() if d >= hoje]
    )[:10]
    
    if not proximos:
        return '<div class="proximos-vazio">Nenhum vencimento próximo.</div>'
    
    linhas = []
    for d, pgs in proximos:
        for p in pgs:
            classe = "linha-em-atraso" if d < hoje else ""
            linhas.append(f"""
            <div class="proximo-linha {classe}">
              <div class="prox-data">
                <span class="prox-dia">{d.day:02d}</span>
                <span class="prox-mes">{['JAN','FEV','MAR','ABR','MAI','JUN','JUL','AGO','SET','OUT','NOV','DEZ'][d.month-1]}</span>
              </div>
              <div class="prox-detalhes">
                <span class="prox-label">{p["label"]}</span>
                <span class="prox-meta">{p["tipo"]}</span>
              </div>
              <span class="prox-valor">R$ {p["valor"]:,.2f}</span>
              <button class="prox-btn">agendar</button>
            </div>
            """)
    
    return minificar('<div class="proximos-lista">' + "".join(linhas) + '</div>')
```

### 5. Renderizar (substituir bloco atual)

```python
def renderizar(dados, mes_selecionado, pessoa, ctx=None):
    # ... topbar_actions, page_header existentes ...
    st.markdown(minificar(carregar_css_pagina("pagamentos")), unsafe_allow_html=True)
    
    # ... KPIs existentes (manter) ...
    
    # Determinar mes/ano do filtro global
    ano, mes = 2026, 5  # placeholder; usar mes_selecionado se disponível
    if isinstance(mes_selecionado, str) and "-" in mes_selecionado:
        partes = mes_selecionado.split("-")
        if len(partes) >= 2:
            try:
                ano, mes = int(partes[0]), int(partes[1])
            except ValueError:
                pass
    
    df_prazos = dados.get('prazos', pd.DataFrame())
    pgs_por_data = _pagamentos_por_data(df_prazos, ano, mes)
    
    col_cal, col_lista = st.columns([2, 1])
    with col_cal:
        st.markdown(_calendario_html(ano, mes, pgs_por_data), unsafe_allow_html=True)
    with col_lista:
        st.markdown('<h3 class="proximos-titulo">PRÓXIMOS 14 DIAS</h3>', unsafe_allow_html=True)
        st.markdown(_lista_proximos_html(pgs_por_data), unsafe_allow_html=True)
```

### 6. CSS dedicado

Criar `src/dashboard/css/paginas/pagamentos.css`:

```css
/* Página Pagamentos -- UX-V-2.2 paridade com mockup 04-pagamentos.html */

.pagamentos-calendario {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-md);
    padding: var(--sp-4);
}

.cal-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: var(--sp-3);
}
.cal-titulo {
    font-family: var(--ff-mono); font-size: 13px;
    text-transform: uppercase; letter-spacing: 0.06em;
    color: var(--text-secondary);
}
.cal-nav-btn {
    font-family: var(--ff-mono); font-size: 10px;
    background: var(--bg-elevated); color: var(--text-muted);
    border: 1px solid var(--border-subtle); border-radius: var(--r-sm);
    padding: 2px 8px;
}

.cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
}
.cal-head-dia {
    font-family: var(--ff-mono); font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.10em;
    color: var(--text-muted);
    text-align: center; padding: 4px 0;
}
.cal-celula {
    background: var(--bg-inset);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-sm);
    min-height: 60px;
    padding: 4px;
    display: flex; flex-direction: column; gap: 2px;
}
.cal-celula.cal-empty {
    background: transparent; border: none;
}
.cal-num {
    font-family: var(--ff-mono); font-size: 11px;
    color: var(--text-muted);
}
.cal-celula.cal-tem-pg .cal-num { color: var(--text-primary); }

.cal-pill {
    display: block;
    font-family: var(--ff-mono); font-size: 9px;
    padding: 1px 4px;
    border-radius: var(--r-xs);
    background: rgba(189, 147, 249, 0.20);
    color: var(--accent-purple);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.cal-pill-fixo { background: rgba(189, 147, 249, 0.20); color: var(--accent-purple); }
.cal-pill-variavel { background: rgba(255, 121, 198, 0.20); color: var(--accent-pink); }
.cal-pill-cartao { background: rgba(139, 233, 253, 0.20); color: var(--accent-cyan); }
.cal-pill-em_atraso { background: rgba(255, 85, 85, 0.20); color: var(--accent-red); }

.cal-legenda {
    display: flex; gap: var(--sp-3); align-items: center;
    margin-top: var(--sp-3);
    font-family: var(--ff-mono); font-size: 10px;
    color: var(--text-muted);
}
.cal-legenda-item {
    display: flex; align-items: center; gap: 4px;
}
.cal-legenda-item .cal-pill { width: 10px; height: 10px; padding: 0; }
.cal-legenda-total {
    margin-left: auto;
    font-variant-numeric: tabular-nums;
}

/* Lista lateral */
.proximos-titulo {
    font-family: var(--ff-mono); font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.10em;
    color: var(--text-secondary);
    margin: 0 0 var(--sp-3);
}
.proximos-lista {
    display: flex; flex-direction: column;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-md);
}
.proximo-linha {
    display: grid;
    grid-template-columns: 50px 1fr auto auto;
    gap: var(--sp-2);
    padding: var(--sp-2) var(--sp-3);
    border-bottom: 1px solid var(--border-subtle);
    align-items: center;
}
.proximo-linha:last-child { border-bottom: none; }
.proximo-linha.linha-em-atraso { background: rgba(255, 85, 85, 0.05); }

.prox-dia {
    font-family: var(--ff-mono); font-size: 16px;
    color: var(--text-primary); display: block;
}
.prox-mes {
    font-family: var(--ff-mono); font-size: 10px;
    color: var(--text-muted); text-transform: uppercase;
}
.prox-label {
    font-family: var(--ff-mono); font-size: 12px;
    color: var(--text-primary); display: block;
}
.prox-meta {
    font-family: var(--ff-mono); font-size: 10px;
    color: var(--text-muted);
}
.prox-valor {
    font-family: var(--ff-mono); font-size: 12px;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
}
.prox-btn {
    font-family: var(--ff-mono); font-size: 10px;
    background: var(--bg-elevated); color: var(--text-secondary);
    border: 1px solid var(--border-subtle); border-radius: var(--r-sm);
    padding: 2px 8px;
}
```

## Validação DEPOIS

```bash
test -f src/dashboard/css/paginas/pagamentos.css
make lint && make smoke
.venv/bin/python -m pytest tests/test_dashboard_pagamentos*.py -q | tail -3
```

## Proof-of-work runtime-real

Validação visual side-by-side via skill `validacao-visual`:
- Dashboard: `cluster=Finanças&tab=Pagamentos`
- Mockup: `mockups/04-pagamentos.html`

Cada screenshot deve mostrar:
1. KPIs no topo (manter atuais)
2. **Calendário 5 semanas** (Seg-Dom) com pílulas coloridas em datas com pagamentos
3. Cabeçalho "maio · 2026" + botão SEG-DOM
4. Legenda no rodapé (fixo/variável/cartão/em atraso) + total mensal
5. **Lista PRÓXIMOS 14 DIAS** lateral com 5+ linhas, cada uma com data, label, tipo, valor R$, botão "agendar"

## Critério de aceitação

1. Calendário do mês inteiro (5 semanas) renderizando.
2. Pílulas coloridas em datas com pagamentos.
3. Lista lateral com botões "agendar" inline.
4. Legenda no rodapé + total mensal.
5. CSS `pagamentos.css` criado.
6. Lint OK + smoke 10/10 + cluster pytest verde.

## Não-objetivos

- NÃO implementar "agendar" funcional (só visual; click pode ser no-op).
- NÃO mexer em outras páginas.
- NÃO inventar dados sintéticos — usar `dados['prazos']` real do XLSX.

## Referência

- Mockup: `novo-mockup/mockups/04-pagamentos.html`.
- Auditoria: `docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md` linha 04.
- VALIDATOR_BRIEF padrões: `(a)/(b)/(k)/(u)`.

*"Calendário inteiro vê o mês como um todo." — princípio V-2.2*
