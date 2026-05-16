---
id: UX-V-2.4
titulo: Validação por Arquivo / Extração Tripla com tabela ETL × Opus × Humano
status: concluída  <!-- noqa: accent -->
concluida_em: 2026-05-07
prioridade: altissima
data_criacao: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-V-02]
co_executavel_com: [UX-V-2.5, UX-V-2.6, UX-V-2.17]
esforco_estimado_horas: 8
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (página 10 -- divergência ESTRUTURAL CRÍTICA)
mockup: novo-mockup/mockups/10-validacao-arquivos.html <!-- noqa: accent -->
---

# Sprint UX-V-2.4 — Validação Tripla (estrutural)

## Contexto

Auditoria 2026-05-07 marcou esta como **divergência ESTRUTURAL CRÍTICA**: o mockup `10-validacao-arquivos.html` mostra o ESSÊNCIA da página — uma tabela ETL × Opus × Validação humana com paridade %, divergências em laranja, badges CONSENSO/DIVERGENTE e botão "Enviar validação". O dashboard atual mostra apenas lista de PDF + viewer — funcionalidade central ausente.

Esta página é o coração do supervisor artesanal (ADR-13 + ADR-08): humano valida divergências entre extrator determinístico (ETL) e Opus interativo agêntico, alimentando a fila de revisão.

## Página afetada

`src/dashboard/paginas/extracao_tripla.py` (também conhecido como Validação por Arquivo). Dashboard hoje serve como `validacao_arquivos.py` — confirmar com grep antes de codar.

## Objetivo

1. Layout 3-col: lista de arquivos esquerda (agrupada por TIPO) | tabela central ETL × Opus × Humano | (cabeçalho com paridade % no topo).
2. Tabela com colunas: Campo / ETL determinístico / Opus agentic / Validação humana (input editável) / Status (CONSENSO / DIVERGENTE).
3. Linhas com divergência destacadas em laranja; consenso pré-preenche o input humano.
4. Botão "Enviar validação" persiste em `data/output/validacao_arquivos.csv` (já existe — Sprint VALIDAÇÃO-CSV-01 do CLAUDE.md).
5. Header com badge "EM REVISÃO", contadores PARIDADE %, DIVERGÊNCIAS N, UNILATERAIS N.

## Validação ANTES (grep obrigatório — padrão `(k)`)

```bash
# Confirmar nome do arquivo correto
ls src/dashboard/paginas/extracao_tripla.py src/dashboard/paginas/validacao_arquivos.py 2>/dev/null
wc -l src/dashboard/paginas/extracao_tripla.py 2>/dev/null
wc -l src/dashboard/paginas/validacao_arquivos.py 2>/dev/null

# Origem dos dados de extração tripla (ETL × Opus × Humano)
grep -rn "validacao_arquivos.csv\|extracao_tripla\|opus_extracao" src/ data/output/ 2>/dev/null | head -10

# CSV existente
ls data/output/validacao_arquivos.csv 2>/dev/null && head -3 data/output/validacao_arquivos.csv
```

Se ETL × Opus × Humano data NÃO existe estruturada, é achado-bloqueio sério — registrar e propor sub-sprint INFRA-EXTRACAO-TRIPLA-DATA antes de continuar.

## Spec de implementação

### 1. Schema canônico de extração tripla

```python
# Cada arquivo tem extracao_tripla:
{
    "sha256": "...",
    "filename": "fatura_c6_cartao_2026-03.pdf",
    "tipo": "fatura_cartao",
    "etl": {
        "extractor_versao": "c6_cartao v1.8.2",
        "campos": {
            "banco": ("C6 Bank", 1.0),  # (valor, confianca)
            "bandeira": ("Mastercard", 1.0),
            "total_fatura": (2847.90, 0.95),
            ...
        },
    },
    "opus": {
        "versao": "opus_v1",
        "n_campos": 10,
        "campos": {
            "banco": ("C6 Bank", 0.99),
            "bandeira": ("Mastercard", 0.98),
            "total_fatura": (2874.90, 0.71),  # divergente!
            ...
        },
    },
    "humano": {
        "validado_em": None,  # ainda em revisão
        "campos": {},
    },
}
```

### 2. Carregar dados de extração tripla

```python
def _carregar_extracoes_triplas() -> list[dict]:
    """Lê data/output/validacao_arquivos.csv ou similar fonte canônica.
    
    Schema esperado: cada linha = um arquivo + uma versão (ETL/Opus/Humano)
    OU JSON estruturado em data/output/extracao_tripla.json.
    
    Se nada existe, retorna [] (graceful, ADR-10).
    """
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[3]
    csv_path = raiz / "data" / "output" / "validacao_arquivos.csv"
    json_path = raiz / "data" / "output" / "extracao_tripla.json"
    
    if json_path.exists():
        try:
            import json
            return json.loads(json_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            pass
    
    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            return df.to_dict('records')
        except (OSError, pd.errors.ParserError):
            pass
    
    return []
```

### 3. Renderizar lista de arquivos esquerda (agrupada por tipo)

```python
def _lista_arquivos_html(extracoes: list[dict], sha_selecionado: str | None) -> str:
    if not extracoes:
        return '<p class="lista-vazia">Sem arquivos pendentes de validação.</p>'
    
    # Agrupar por tipo
    por_tipo = {}
    for e in extracoes:
        tipo = e.get('tipo', '?')
        por_tipo.setdefault(tipo, []).append(e)
    
    grupos = []
    for tipo, arquivos in sorted(por_tipo.items()):
        items = []
        for arq in arquivos:
            sha = arq.get('sha256', '')[:8]
            paridade = _calcular_paridade(arq)
            classe_sel = "selecionado" if sha == sha_selecionado else ""
            items.append(f"""
            <div class="arquivo-linha {classe_sel}" data-sha="{sha}">
              <span class="arq-nome">{arq.get('filename', '?')[:30]}</span>
              <span class="arq-paridade">{paridade:.0f}% ok</span>
            </div>
            """)
        grupos.append(f"""
        <div class="lista-grupo-tipo">
          <h4 class="grupo-titulo">{tipo.upper()}</h4>
          {''.join(items)}
        </div>
        """)
    return minificar('<div class="lista-arquivos">' + "".join(grupos) + '</div>')
```

### 4. Renderizar tabela ETL × Opus × Humano

```python
def _calcular_paridade(extracao: dict) -> float:
    """% de campos onde ETL e Opus concordam."""
    etl_c = extracao.get('etl', {}).get('campos', {})
    opus_c = extracao.get('opus', {}).get('campos', {})
    if not etl_c or not opus_c:
        return 0.0
    chaves = set(etl_c.keys()) & set(opus_c.keys())
    if not chaves:
        return 0.0
    iguais = sum(1 for k in chaves if etl_c[k][0] == opus_c[k][0])
    return iguais / len(chaves) * 100


def _tabela_tripla_html(extracao: dict) -> str:
    """Tabela ETL × Opus × Humano para 1 arquivo selecionado."""
    if not extracao:
        return '<p class="tabela-vazia">Selecione um arquivo na lista esquerda.</p>'
    
    etl_c = extracao.get('etl', {}).get('campos', {})
    opus_c = extracao.get('opus', {}).get('campos', {})
    humano_c = extracao.get('humano', {}).get('campos', {})
    
    chaves = sorted(set(etl_c.keys()) | set(opus_c.keys()))
    
    linhas = []
    for k in chaves:
        etl_v, etl_conf = etl_c.get(k, ("--", 0))
        opus_v, opus_conf = opus_c.get(k, ("--", 0))
        humano_v = humano_c.get(k, "")
        
        divergente = etl_v != opus_v
        classe = "linha-divergente" if divergente else "linha-consenso"
        
        # Pré-preenchimento humano: se consenso, usa o valor; se divergente, vazio
        valor_input = humano_v or (etl_v if not divergente else "")
        status_badge = (
            '<span class="badge-divergente">DIVERGENTE</span>' if divergente
            else '<span class="badge-consenso">CONSENSO</span>'
        )
        
        linhas.append(f"""
        <tr class="{classe}">
          <td class="campo-nome">{k}</td>
          <td class="campo-etl">{etl_v} <span class="conf">{etl_conf:.0%}</span></td>
          <td class="campo-opus">{opus_v} <span class="conf">{opus_conf:.0%}</span></td>
          <td class="campo-humano">
            <input type="text" value="{valor_input}"
              placeholder="preencher..." data-campo="{k}" />
          </td>
          <td class="campo-status">{status_badge}</td>
        </tr>
        """)
    
    return minificar(f"""
    <table class="tabela-tripla">
      <thead>
        <tr>
          <th>CAMPO</th>
          <th>ETL determinístico<br><span class="th-sub">{extracao.get('etl', {}).get('extractor_versao', '?')}</span></th>
          <th>Claude Opus agentic<br><span class="th-sub">opus_v1</span></th>
          <th>Validação humana<br><span class="th-sub">consenso pré-preenchido</span></th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>{''.join(linhas)}</tbody>
    </table>
    """)
```

### 5. Render

```python
def renderizar(dados, mes_selecionado, pessoa, ctx=None):
    # ... topbar_actions, page_header existentes ...
    st.markdown(minificar(carregar_css_pagina("extracao_tripla")), unsafe_allow_html=True)
    
    extracoes = _carregar_extracoes_triplas()
    if not extracoes:
        st.markdown(fallback_estado_inicial_html(
            titulo="EXTRAÇÃO TRIPLA · sem arquivos pendentes",
            descricao=("Quando o pipeline de inbox processa um novo arquivo, ele é "
                       "extraído por <code>ETL determinístico</code> e por "
                       "<code>Claude Opus agentic</code> (sessão interativa). "
                       "Divergências aparecem aqui para validação humana."),
            cta_secao="extracao_tripla",
            sync_info=ler_sync_info(),
        ), unsafe_allow_html=True)
        return
    
    # KPIs no topo
    n_total = len(extracoes)
    n_revisao = sum(1 for e in extracoes if not e.get('humano', {}).get('validado_em'))
    media_paridade = sum(_calcular_paridade(e) for e in extracoes) / n_total
    n_divergencias = sum(
        1 for e in extracoes
        for k in (set(e.get('etl', {}).get('campos', {}).keys()) & set(e.get('opus', {}).get('campos', {}).keys()))
        if e['etl']['campos'][k][0] != e['opus']['campos'][k][0]
    )
    
    st.markdown(minificar(f"""
    <div class="tripla-header">
      <div class="tripla-kpi">PARIDADE <strong>{media_paridade:.0f}%</strong></div>
      <div class="tripla-kpi">DIVERGÊNCIAS <strong>{n_divergencias}</strong></div>
      <div class="tripla-kpi">EM REVISÃO <strong>{n_revisao}</strong></div>
      <div class="tripla-kpi">{n_total} ARQUIVOS</div>
    </div>
    """), unsafe_allow_html=True)
    
    # Layout 3-col simulado com 2 columns(esquerda lista, direita tabela)
    col_lista, col_tabela = st.columns([1, 3])
    with col_lista:
        # Selectbox simples para escolher SHA (HTML-only seria refator maior)
        opcoes = [f"{e.get('filename', '?')[:30]} ({e.get('sha256', '')[:8]})" for e in extracoes]
        idx = st.selectbox("Arquivo", range(len(opcoes)), format_func=lambda i: opcoes[i])
        sha_sel = extracoes[idx].get('sha256', '')
        st.markdown(_lista_arquivos_html(extracoes, sha_sel), unsafe_allow_html=True)
    with col_tabela:
        st.markdown(_tabela_tripla_html(extracoes[idx]), unsafe_allow_html=True)
        if st.button("Enviar validação", type="primary"):
            st.success("Validação registrada em data/output/validacao_arquivos.csv (placeholder; persistência real requer endpoint).")
```

### 6. CSS dedicado em `src/dashboard/css/paginas/extracao_tripla.css`

```css
/* Validação Tripla -- UX-V-2.4 */

.tripla-header {
    display: flex; gap: var(--sp-4); align-items: center;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-md);
    padding: var(--sp-3) var(--sp-4);
    margin-bottom: var(--sp-4);
}
.tripla-kpi {
    font-family: var(--ff-mono); font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.06em;
}
.tripla-kpi strong {
    font-size: 16px; color: var(--text-primary);
    font-variant-numeric: tabular-nums;
    margin-left: 4px;
}

.lista-arquivos {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-md);
    padding: var(--sp-2);
}
.lista-grupo-tipo {
    margin-bottom: var(--sp-3);
}
.grupo-titulo {
    font-family: var(--ff-mono); font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.10em;
    color: var(--text-muted);
    padding: var(--sp-2) var(--sp-2) var(--sp-1);
    margin: 0;
}
.arquivo-linha {
    display: flex; justify-content: space-between;
    padding: 4px var(--sp-2);
    border-radius: var(--r-xs);
    font-size: 11px;
    cursor: pointer;
}
.arquivo-linha:hover {
    background: var(--bg-elevated);
}
.arquivo-linha.selecionado {
    background: rgba(189, 147, 249, 0.10);
    border-left: 2px solid var(--accent-purple);
}
.arq-nome {
    color: var(--text-primary);
    font-family: var(--ff-mono);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.arq-paridade {
    color: var(--text-muted);
    font-family: var(--ff-mono);
}

.tabela-tripla {
    width: 100%;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-md);
    border-collapse: collapse;
}
.tabela-tripla th {
    padding: var(--sp-2) var(--sp-3);
    text-align: left;
    background: var(--bg-inset);
    font-family: var(--ff-mono); font-size: 11px;
    color: var(--text-secondary);
    text-transform: uppercase; letter-spacing: 0.06em;
    border-bottom: 1px solid var(--border-subtle);
}
.th-sub {
    display: block;
    font-family: var(--ff-mono); font-size: 9px;
    color: var(--text-muted);
    text-transform: lowercase;
    margin-top: 2px;
}
.tabela-tripla td {
    padding: var(--sp-2) var(--sp-3);
    border-bottom: 1px solid var(--border-subtle);
    font-size: 12px;
}
.tabela-tripla tr.linha-divergente {
    background: rgba(255, 184, 108, 0.05);
}
.tabela-tripla tr.linha-divergente td {
    color: var(--accent-orange);
}
.tabela-tripla tr.linha-divergente td.campo-nome {
    color: var(--accent-orange); font-weight: 500;
}

.campo-nome {
    font-family: var(--ff-mono);
    color: var(--text-primary);
}
.campo-etl, .campo-opus {
    font-family: var(--ff-mono);
    color: var(--text-secondary);
    font-variant-numeric: tabular-nums;
}
.conf {
    font-size: 10px; color: var(--text-muted);
    margin-left: 4px;
}
.campo-humano input {
    width: 100%;
    background: var(--bg-inset);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-xs);
    padding: 2px 6px;
    font-family: var(--ff-mono); font-size: 12px;
    color: var(--text-primary);
}
.badge-consenso {
    background: rgba(80, 250, 123, 0.15);
    color: var(--accent-green);
    padding: 2px 8px;
    border-radius: var(--r-full);
    font-family: var(--ff-mono); font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.06em;
}
.badge-divergente {
    background: rgba(255, 184, 108, 0.15);
    color: var(--accent-orange);
    padding: 2px 8px;
    border-radius: var(--r-full);
    font-family: var(--ff-mono); font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.06em;
}

.tabela-vazia, .lista-vazia {
    color: var(--text-muted);
    padding: var(--sp-4);
    text-align: center;
    font-size: 12px;
}
```

## Validação DEPOIS

```bash
test -f src/dashboard/css/paginas/extracao_tripla.css
make lint && make smoke
.venv/bin/python -m pytest tests/test_*extracao*.py tests/test_*validacao*.py -q 2>&1 | tail -3
```

## Proof-of-work runtime-real

Validação visual side-by-side em `cluster=Documentos&tab=Validação+por+Arquivo` vs `mockups/10-validacao-arquivos.html <!-- noqa: accent -->`. Screenshot deve mostrar:
1. Header com 4 KPIs (PARIDADE %, DIVERGÊNCIAS N, EM REVISÃO N, N ARQUIVOS)
2. Lista de arquivos esquerda agrupada por TIPO (PDF, IMG, CSV, XLSX, OFX) com paridade %
3. Tabela central com colunas Campo | ETL | Opus | Humano | Status
4. Linhas divergentes em laranja com badges DIVERGENTE
5. Linhas consenso em verde com badges CONSENSO
6. Inputs editáveis na coluna humano
7. Botão "Enviar validação" no rodapé

## Critério de aceitação

1. Tabela ETL × Opus × Humano renderizando se há dados.
2. Fallback graceful via `fallback_estado_inicial_html` se sem dados.
3. KPIs no topo com valores reais.
4. Linhas divergentes destacadas em laranja.
5. CSS criado.
6. Lint OK + smoke 10/10 + cluster pytest verde.

## Não-objetivos

- NÃO implementar persistência completa de validação humana (placeholder OK; refator separado).
- NÃO chamar API de Opus aqui — dados de Opus vêm pré-extraídos no cache JSON.
- NÃO mexer em Revisor (página adjacente, escopo separado).
- Se schema de extracao_tripla.json não existe, **PARAR e propor sub-sprint** INFRA-EXTRACAO-TRIPLA-SCHEMA antes de continuar.

## Referência

- Mockup: `novo-mockup/mockups/10-validacao-arquivos.html <!-- noqa: accent -->`.
- Auditoria: linha 10 (estrutural crítica).
- ADR-08 (supervisor-aprovador) + ADR-13 (supervisor artesanal).
- Sprint VALIDAÇÃO-CSV-01 (CLAUDE.md regra 11): `data/output/validacao_arquivos.csv`.

*"Onde dois extratores divergem, o humano decide." — princípio V-2.4*
