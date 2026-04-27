## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-114
  title: "Busca Global funcional: autocomplete + dropdown tipos + filtros + roteador tab/doc"
  prioridade: P0
  estimativa: 5h
  origem: "feedback dono 2026-04-27 -- Busca Global hoje so tem chips clicaveis e text_input plano; nao busca de fato; sem autocomplete; sem filtragem por tipo; filtros sidebar nao impactam"
  pre_requisito_de: [100]
  touches:
    - path: src/dashboard/paginas/busca.py
      reason: "refactor completo: substitui chips estaticos por autocomplete + dropdown tipos + filtros sidebar impactam + roteador"
    - path: src/dashboard/componentes/busca_indice.py
      reason: "NOVO -- indice em memoria (cached) com nomes de fornecedores, descricoes de itens, tipos de doc, abas do dashboard"
    - path: src/dashboard/componentes/busca_roteador.py
      reason: "NOVO -- decide se query casa nome de aba (navega) ou conteudo (filtra Busca Global)"
    - path: tests/test_busca_global_funcional.py
      reason: "NOVO -- 12 testes minimo: indexacao, autocomplete, dropdown tipos, filtros sidebar impactam, roteador tab vs doc, link rapido para documento"
  forbidden:
    - "Adicionar deps externas (manter pure-Streamlit + pure-Python)"
    - "Carregar todo o grafo em memoria a cada render (usar @st.cache_data)"
    - "Quebrar Sprint 59 (chips clicaveis no select-and-go) -- deixar opcao secundaria abaixo do dropdown"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_busca_global_funcional.py -v"
    - cmd: ".venv/bin/pytest tests/test_dashboard*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Indice cached: lista de nomes de fornecedores (do grafo, tipo='fornecedor'), descricoes de items, tipos de documento (mappings/tipos_documento.yaml), nomes de abas do dashboard"
    - "Autocomplete: ao digitar X chars, mostra ate 10 suggestions casando case-insensitive substring no indice"
    - "Dropdown 'Tipo' acima do input com opcoes: Todos, Pessoais, Trabalho, Notas Fiscais, Holerites, Boletos, Receitas Medicas, DAS, IRPF; filtra resultados"
    - "Filtros sidebar (Mes, Pessoa, Forma de pagamento) impactam resultados: documento de 2026-03 nao aparece se sidebar filtra Mes=2026-04"
    - "Roteador: query exata casa nome de aba -> 'Ir para aba <Nome>' (link no resultado); query casa nome de fornecedor -> link para Catalogacao filtrada; senao -> lista resultados agrupados por tipo"
    - "Botoes com link rapido na lista de resultados: cada documento mostra botao 'Abrir' que navega para Revisor com item_id"
    - "Borda visivel no input de busca, destacada em foco (depende UX-112 mas pode ser feita inline aqui se UX-112 ainda nao mergeada)"
    - "Pelo menos 12 testes regressivos cobrindo as funcionalidades acima"
    # === Adicoes feedback dono 2026-04-27 ===
    - "Chips abaixo do input substituem 'neoenergia/farmacia/uber/posto/2026-03/americanas' (exemplos aleatorios) por TIPOS DE DOCUMENTOS canonicos: Holerite, Nota Fiscal, DAS, Boleto, IRPF, Recibo, Comprovante, Contracheque (8 chips fixos OU resultados em tempo real apos digitar)"
    - "Placeholder do input em MAIUSCULAS: 'BUSQUE: HOLERITE, NF, DAS, BOLETO, IRPF, FORNECEDOR, CNPJ...'"
    - "Texto descritivo reescrito em uma linha so (max 90 chars): 'Busque por tipo de documento, fornecedor, CNPJ ou identificador.' (era 3 linhas confusas com 'Input unico permanente...')"
    - "Output em tabela formatada via st.dataframe ou tabela HTML com colunas: Nome do documento, Texto extraido (resumo), Caminho do arquivo, Botao Exportar"
    - "Botao Exportar de cada linha copia o arquivo para data/exports/<ts>_<nome>.<ext> (cria diretorio se nao existir; nunca deleta original)"
    - "Cor do icone (i) do callout info nao destoa do tema -- usar var(--color-destaque) ou var(--color-neutro) em vez de azul Streamlit default"
    - "Espacamento do bloco de texto descritivo respeita PADDING_INTERNO (UX-112) -- nao colado a borda"
    - "Pelo menos 5 testes regressivos adicionais: chips renderizam tipos canonicos; placeholder maiusculo; tabela tem 4 colunas obrigatorias; export cria arquivo em data/exports/; PII mascarada no output da tabela"
  proof_of_work_esperado: |
    # Probe 1: indexar
    .venv/bin/python -c "
    from src.dashboard.componentes.busca_indice import construir_indice
    from src.graph.db import GrafoDB
    db = GrafoDB('data/output/grafo.sqlite')
    idx = construir_indice(db)
    print('fornecedores:', len(idx['fornecedores']))
    print('descricoes_itens:', len(idx['descricoes']))
    print('tipos_doc:', len(idx['tipos_doc']))
    print('abas:', len(idx['abas']))
    "
    # Esperado: contagens > 0

    # Probe 2: autocomplete
    .venv/bin/python -c "
    from src.dashboard.componentes.busca_indice import sugestoes
    print(sugestoes('neoen', limite=10))
    "
    # Esperado: ['Neoenergia', 'Neoenergia DF', ...] case-insensitive

    # Probe 3: roteador
    .venv/bin/python -c "
    from src.dashboard.componentes.busca_roteador import rotear
    print(rotear('Revisor'))   # casa nome de aba
    print(rotear('Neoenergia'))   # casa fornecedor
    print(rotear('R\\\$ 100,00'))   # nao casa nada -> busca livre
    "
    # Esperado: dict com kind in {'aba', 'fornecedor', 'livre'}

    # Probe 4: validacao visual (Streamlit)
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # Abrir aba Busca Global
    # Confirmar: dropdown tipos visivel; input com borda; digitar 'neo' mostra sugestoes; submit em 'Revisor' navega
```

---

# Sprint UX-114 -- Busca Global funcional

**Status:** BACKLOG (P0, criada 2026-04-27, pré-requisito da Sprint 100)

Hoje a página `paginas/busca.py` (506L) é mockup: chips estáticos + text_input plano + caption sugerindo "digite ou clique nas sugestões". Nada filtra de fato — apenas redireciona com query_param.

Sprint refactora para uma busca real:
1. **Índice em memória** (cached por sessão Streamlit) com nomes de fornecedores, descrições de itens, tipos canônicos, abas do dashboard.
2. **Autocomplete** ativo (substring case-insensitive, ≤10 suggestions).
3. **Dropdown de tipos** no topo: Todos / Pessoais / Trabalho / Notas Fiscais / Holerites / Boletos / DAS / IRPF / Receitas Médicas.
4. **Filtros da sidebar** (Mês, Pessoa, Forma de pagamento) **impactam** os resultados.
5. **Roteador**: query exata que casa nome de aba retorna link para a aba; query que casa fornecedor retorna link para Catalogação filtrada; senão lista resultados agrupados.
6. **Botões "Abrir"** em cada documento navegam direto para o Revisor com `item_id`.

Padrão (l) subregra retrocompatível aplicável: novo dropdown convive com chips Sprint 59 abaixo (não quebra).

Padrão (m) branch reversível aplicável: se índice falha em construir (ex: grafo vazio), cair em Sprint 59 puro com aviso visual.

---

*"Busca que não filtra é mockup. Busca que filtra mas não responde 'achei' ou 'não achei' é frustração." -- princípio da busca que comunica*
