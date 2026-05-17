---
id: UX-SPINNER-PROGRESS-FEEDBACK
titulo: "Adicionar `st.spinner` em operações lentas no dashboard (atualmente só 2/42 páginas)"
status: concluída
concluida_em: 2026-05-17
prioridade: P3
data_criacao: 2026-05-17
fase: UX
epico: 5
depende_de: []
esforco_estimado_horas: 1.5
origem: "auditoria independente 2026-05-17. Grep `st.spinner|st.progress` em `paginas/*.py` retorna apenas 2 ocorrências. Operações com >500ms (indexação busca, renderização grafo pyvis, paginação extrato) não dão feedback visual ao usuário. UX degradada: clicar e ver tela parada faz dono clicar de novo, gerando trabalho duplicado."
---

# Sprint UX-SPINNER-PROGRESS-FEEDBACK

## Contexto

Dashboard Streamlit tem 42 páginas. Apenas 2 usam `st.spinner`:

```bash
grep -rln "st.spinner\|st.progress" src/dashboard/paginas/ | wc -l
# 2
```

Operações reconhecidamente lentas:
1. **Busca Global** — `_indice_cached()` na primeira chamada da sessão (~1-2s).
2. **Grafo + Obsidian** — `construir_grafo_interativo()` via pyvis (~2-5s).
3. **Extrato (paginação)** — carrega XLSX e filtra (~500ms-1s).
4. **Catalogação** — carrega docs do grafo (~1s).
5. **Análise Avançada** — Plotly + agregações (~1-2s).

UX problema: dono clica numa aba, vê tela branca, acha que travou, clica de novo → "session_state polluído" + trabalho duplicado.

## Hipótese e validação ANTES

```bash
grep -rln "st.spinner\|st.progress" src/dashboard/paginas/ | wc -l
# Esperado: 2

# Identificar operações lentas: procurar carregamento de XLSX, grafo, pyvis:
grep -rn "carregar_dados\|construir_grafo\|read_excel\|load_workbook" src/dashboard/paginas/ | head -10
```

## Objetivo

1. Adicionar `st.spinner` nos 5 sítios identificados:
   ```python
   with st.spinner("Carregando índice de busca..."):
       indice = _indice_cached(mtime)

   with st.spinner("Renderizando grafo..."):
       html = construir_grafo_interativo(...)

   with st.spinner("Filtrando extrato..."):
       df_filtrado = paginar_extrato(...)
   ```

2. Onde fizer sentido, **`st.progress`** para operações batch:
   ```python
   barra = st.progress(0, "Processando documentos...")
   for i, doc in enumerate(docs):
       processar(doc)
       barra.progress((i+1)/len(docs))
   ```

3. **Mensagens humanas em PT-BR** (não jargão técnico):
   - "Carregando índice..." (não "Loading cache...")
   - "Filtrando R\$ 500-1000..." (com valores reais quando aplicável)

4. **Testes regressivos NÃO** — render Streamlit não é unit-test friendly. Validação visual.

## Não-objetivos

- Não tocar lógica das funções subjacentes.
- Não criar spinner global em `main()` (péssima UX — não diz O QUE está carregando).
- Não substituir `@st.cache_data` (cache continua valendo).

## Proof-of-work runtime-real

```bash
# Validação manual:
make dashboard
# Abrir cada aba lenta e confirmar spinner aparece.

# Grep pós-fix:
grep -rln "st.spinner" src/dashboard/paginas/ | wc -l
# Esperado: 5+
```

## Acceptance

- 5+ páginas com `st.spinner` em operações >500ms.
- Mensagens em PT-BR.
- Pytest baseline mantida (spinners não afetam testes).

## Padrões aplicáveis

- (a) Edit incremental — adicionar wrapper, não tocar lógica.

---

*"Tela parada é tela suspeita; spinner é honestidade visual." — princípio do feedback*
