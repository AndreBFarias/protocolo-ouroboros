## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-11
  title: "Extração Tripla: layout 3-colunas (lista | viewer | tabela ETL/Opus/Humano) substitui validação por arquivo"
  prioridade: P0
  estimativa: 4h
  onda: 3
  origem: "docs/MAPA_FEATURES_MOBILE_DESKTOP.md §5.2 + _extracao-data.js + _extracao-render.js"
  depende_de: [UX-RD-03]
  touches:
    - path: src/dashboard/paginas/extracao_tripla.py
      reason: "NOVO -- substitui paginas/validacao_arquivos.py. Layout 3-cols: (1) lista de arquivos por tipo com badge formato (PDF/CSV/IMG/XLSX/OFX/HTML); (2) viewer central (PDF page nav, imagem zoom, CSV preview); (3) tabela tripla ETL/Opus/Humano com células divergentes em laranja"
    - path: src/dashboard/paginas/validacao_arquivos.py
      reason: "DEPRECAR via stub que redireciona para extracao_tripla; manter por 1 sprint para retrocompat de bookmarks"
    - path: src/dashboard/dados.py
      reason: "Adicionar leitor de arquivo binário com preview (pdfplumber para PDFs, PIL para imagens) -- usar utilidades existentes em src/utils/pdf_reader.py"
    - path: data/output/validacao_arquivos.csv
      reason: "Adicionar coluna confianca_opus (float 0..1, default 0.0). Migrar via script idempotente."
    - path: scripts/migrar_csv_confianca_opus.py
      reason: "NOVO -- adiciona coluna confianca_opus se ausente, idempotente"
    - path: tests/test_extracao_tripla.py
      reason: "NOVO -- 12 testes: 3 colunas renderizam, divergência ETL≠Opus pinta laranja, consenso ETL∩Opus pré-popula valor_humano, click 'Validar' grava status_humano=aprovado + ts + valor_humano final, schema CSV 13 colunas"
  forbidden:
    - "Apagar validacao_arquivos.py imediatamente -- stub por 1 sprint"
    - "Quebrar skill ~/.claude/skills/validar-arquivo (continua escrevendo valor_opus na mesma coluna)"
    - "Hardcodar paths -- ler de CAMINHO_XLSX e derivar"
  hipotese:
    - "validacao_arquivos.csv já tem 12 colunas incluindo valor_opus, status_opus -- confirmado em fase de exploração. Migração só adiciona confianca_opus."
    - "Skill /validar-arquivo é wrapper manual sobre Read+CSV -- não precisa mudar, só receber o novo schema com coluna extra."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/python scripts/migrar_csv_confianca_opus.py --dry-run"
    - cmd: ".venv/bin/python scripts/migrar_csv_confianca_opus.py --executar"
    - cmd: ".venv/bin/pytest tests/test_extracao_tripla.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Layout 3 colunas em viewport ≥1400px (responsivo: stack abaixo)"
    - "Coluna 1 (lista): arquivos por tipo, badge formato, status pill (aguardando/extraído/conflito/validado)"
    - "Coluna 2 (viewer): PDF com page nav, imagem com zoom, CSV preview 20 linhas"
    - "Coluna 3 (tabela tripla): linhas = campos extraídos; colunas = ETL | Opus | Humano; divergência ETL≠Opus pinta cell laranja; consenso pré-preenche Humano"
    - "Botão 'Validar' grava: valor_humano (que pode = consenso ou correção), status_humano=aprovado, ts, calcula score paridade"
    - "Coluna confianca_opus presente no CSV (verificar via head -1)"
    - "validacao_arquivos.py redireciona via st.switch_page ou aviso 'movido para Extração Tripla'"
    - "Skill /validar-arquivo continua funcionando (proof-of-work: invocar manualmente, conferir CSV atualizado)"
    - "pytest baseline mantida"
  proof_of_work_esperado: |
    # Hipótese: schema CSV
    head -1 data/output/validacao_arquivos.csv
    # esperado conter: valor_opus,...

    # AC: migração idempotente
    .venv/bin/python scripts/migrar_csv_confianca_opus.py --executar
    head -1 data/output/validacao_arquivos.csv | tr ',' '\n' | grep -c confianca_opus
    # = 1
    .venv/bin/python scripts/migrar_csv_confianca_opus.py --executar  # idempotente
    # NÃO duplica coluna

    # AC: dashboard
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # 1. ?cluster=Documentos&tab=Extração+Tripla -- 3 colunas visíveis
    # 2. Selecionar PDF na lista -> viewer abre, tabela tripla popula
    # 3. Identificar 1 célula laranja (divergência) -> editar -> Validar
    # 4. tail -1 data/output/validacao_arquivos.csv -> mostra valor_humano + status_humano=aprovado
    # screenshot vs docs/MAPA_FEATURES_MOBILE_DESKTOP.md §5.2
```

---

# Sprint UX-RD-11 — Extração Tripla

**Status:** BACKLOG

Sprint funcionalmente densa. Substitui Validação por Arquivo por uma UI 3
colunas que **junta no mesmo lugar** o arquivo bruto, a extração ETL
determinística, a extração Opus agentic e a confirmação humana.

**Achado de exploração que reduziu escopo:** o CSV já tem `valor_opus` e
`status_opus` — só falta `confianca_opus`. Migração é trivial (1 coluna).

**Validação visual do dono:** o teste real é abrir um PDF de cupom NFCe e
ver as 3 extrações lado-a-lado. Esperado: ETL e Opus concordam em ~70-80%
dos campos; humano confirma divergências em <30s.

**Specs absorvidas:** validação_arquivos antiga (deprecada como stub).

---

*"Três fontes independentes que concordam: aproximação da verdade." — princípio da triangulação*
