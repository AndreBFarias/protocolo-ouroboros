---
concluida_em: 2026-04-27
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-126
  title: "Polish iteracao 3: nomes humanizados + layout Catalogacao + caption sidebar reformatada"
  prioridade: P1
  estimativa: 1.5h
  origem: "feedback dono 2026-04-27 (image 21) -- 6 achados na pagina Catalogacao + sidebar"
  pre_requisito_de: [Sprint 100]
  depende_de: [UX-125]
  touches:
    - path: src/dashboard/paginas/catalogacao.py
      reason: "humanizar nomes nos baloes (holerite -> Holerite; das_parcsn_andre -> DAS Parcelado Andre; NFC-e (modelo 65) ja OK; boleto_servico -> Boleto de Servico; dirpf_retif -> DIRPF Retificadora) via mapeamento canonico; restruturar layout: Documentos Recentes ocupa toda a largura, Conflitos Pendentes | Gaps de Cobertura em 50/50 abaixo; chamar hero_titulo_html('Catalogacao de Documentos') no topo se nao chama"
    - path: src/dashboard/tema.py
      reason: "css_global() ganha padding simetrico em containers de cards de tipos; caption sidebar reformatada com align:center; logo class .ouroboros-logo-img reforcada com width: 120px !important e centralizada"
    - path: src/dashboard/app.py (ou logo_sidebar_html em tema.py)
      reason: "caption 'Dados de DD/MM/YYYY as HH:MM' reformatada: 'Dados de DD/MM/YYYY' linha 1 + '- HH:MM -' linha 2 (centralizado com tracos decorativos)"
    - path: mappings/tipos_documento_humanizado.yaml
      reason: "NOVO -- mapping {tipo_canonico: nome_humano}, ex: {holerite: 'Holerite', das_parcsn_andre: 'DAS Parcelado Andre', ...}; usado por catalogacao.py"
    - path: tests/test_catalogacao_humanizado.py
      reason: "NOVO -- 6 testes regressivos (1 por AC)"
  forbidden:
    - "Mudar logica de extracao (so nomes humanos para UI)"
    - "Quebrar mascaramento PII (4 sitios padrao Sprint 99)"
    - "Adicionar deps externas"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_catalogacao_humanizado.py -v"
    - cmd: ".venv/bin/pytest tests/test_dashboard*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    # AC1: nomes humanizados nos baloes
    - "Cards 'DOCUMENTOS POR TIPO' em catalogacao.py exibem nomes humanos: 'Holerite' (era 'holerite'), 'DAS Parcelado Andre' (era 'das_parcsn_andre'), 'Nota Fiscal Eletronica' (era 'NFC-e (modelo 65)'), 'Boleto de Servico' (era 'boleto_servico'), 'DIRPF Retificadora' (era 'dirpf_retif')"
    - "Mapeamento em mappings/tipos_documento_humanizado.yaml; fallback humanizar(slug) para tipos nao listados (replace _ por espaco + title())"
    # AC2: padding simetrico ao redor dos cards
    - "Distancia visual entre 'DOCUMENTOS POR TIPO' titulo e cards (margin-top dos cards) IGUAL a distancia entre cards e linha '---' abaixo (margin-bottom) -- simetria 1:1"
    # AC3: layout Documentos Recentes / Conflitos / Gaps
    - "'DOCUMENTOS RECENTES' (titulo + tabela) ocupa toda a largura horizontal (100%), nao 50% como hoje"
    - "Abaixo de Documentos Recentes: 2 colunas 50/50 com 'CONFLITOS PENDENTES' (esquerda) e 'GAPS DE COBERTURA' (direita), via st.columns([1, 1])"
    # AC4: hero da pagina visivel
    - "hero_titulo_html('', 'Catalogacao de Documentos', subtitulo) chamado no topo de catalogacao.renderizar() -- se nao chama, adicionar"
    # AC5: logo 120px efetivo
    - "logo_sidebar_html() emite <img class='ouroboros-logo-img' width='120'>; CSS '.ouroboros-logo-img { width: 120px !important; height: auto !important; aspect-ratio: 724 / 733; margin: 0 auto; display: block; }'"
    # AC6: caption sidebar reformatada
    - "Caption 'Dados de DD/MM/YYYY as HH:MM' substituida por 2 paragraphs HTML centralizados: 'Dados de DD/MM/YYYY' + '- HH:MM -' (com tracos decorativos)"
    - "Pelo menos 6 testes regressivos cobrindo cada AC"
  proof_of_work_esperado: |
    # AC1
    grep -c "humanizar\|tipos_documento_humanizado" src/dashboard/paginas/catalogacao.py
    # = >=1

    # Probe runtime
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # http://localhost:8520/?cluster=Documentos&tab=Catalogacao -- nomes humanos nos baloes
    # Capturar screenshot e validar visualmente

    # AC5
    .venv/bin/python -c "
    from src.dashboard.tema import css_global
    css = css_global()
    assert '.ouroboros-logo-img' in css and '120px' in css
    print('AC5 OK: logo 120px reforcado')
    "
```

---

# Sprint UX-126 -- Polish iteracao 3

**Status:** CONCLUÍDA (commit `5a78ca8`, 2026-04-27 — 13 testes novos, 37 tipos canônicos no mapping)

6 achados na pagina Catalogacao + sidebar identificados pelo dono apos validar v2:

1. Nomes dos baloes "DOCUMENTOS POR TIPO" estao em snake_case crue (`das_parcsn_andre`); precisam ser humanizados via mapping YAML.
2. Padding simetrico ao redor dos cards (mesma distancia acima e abaixo).
3. Layout vertical: "Documentos Recentes" 100% width + "Conflitos | Gaps" 50/50 abaixo (hoje são colunas erradas).
4. Hero "Catalogacao de Documentos" deve aparecer visivel.
5. Logo da sidebar volta a estar com tamanho ruim; reforcar `.ouroboros-logo-img` com `!important`.
6. Caption "Dados de DD/MM/YYYY as HH:MM" reformatada para 2 linhas centralizadas com tracos decorativos.

Sprint depende de UX-125 mergear primeiro (toca `app.py` que UX-125 esta atualizando).

---

*"Detalhe não é poluição -- é a borda da credibilidade." -- princípio do polish honesto*
