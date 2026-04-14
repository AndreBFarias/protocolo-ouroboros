# ADR-05: Streamlit para dashboard interativo

## Status: Aceita

## Contexto

O usuário precisa de visualização interativa dos dados financeiros: gráficos de gastos por categoria, evolução mensal, filtros por pessoa e período. A solução deve ser Python-only (sem necessidade de frontend separado) e sem infraestrutura adicional.

Alternativas consideradas:
- **Dash (Plotly)**: mais controle de layout, mas boilerplate significativo. Callbacks explícitos tornam o código mais complexo.
- **Grafana**: poderoso para monitoramento, mas exige banco de dados (InfluxDB/Postgres) e infraestrutura Docker.
- **Jupyter/Voila**: bom para exploração, mas não é uma aplicação web real.
- **Panel (HoloViz)**: menos popular, documentação mais escassa.

## Decisão

Usar Streamlit com gráficos Plotly. 6 páginas organizadas por tema: visão geral, categorias, extrato detalhado, contas fixas, projeções e metas. Sidebar com filtros globais (mês, pessoa). Tema dark configurado via `.streamlit/config.toml`.

## Consequências

**Positivas:**
- Prototipagem extremamente rápida: página nova em ~100 linhas
- Python-only: sem HTML, CSS ou JavaScript manual
- Plotly integrado nativamente para gráficos interativos
- `streamlit run` é suficiente, sem servidor web separado

**Negativas:**
- Layout limitado: não há grid system flexível, responsividade precária em mobile
- Problemas de UI encontrados: botões invisíveis com tema dark, fontes inconsistentes
- Tabs com JavaScript: troca de aba programática requer hack JS, não API nativa
- Cada interação re-executa o script inteiro (mitigado com `st.cache_data`)
- Não é ideal para deploy público (sem autenticação nativa robusta)

---

*"A ferramenta certa é aquela que resolve o problema de hoje sem criar o problema de amanhã." -- Desconhecido*
