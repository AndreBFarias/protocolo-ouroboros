# Sprint 08 -- Dashboard v2 (Redesign Visual)

## Status: Pendente
Issue: a criar

## Objetivo

Auditoria visual completa e redesign do dashboard Streamlit. Corrigir problemas visuais identificados na Sprint 03 e polir as páginas adicionadas na Sprint 05.

## Entregas

- [ ] Auditoria de todas as páginas no browser (captura de screenshots)
- [ ] Corrigir botões invisíveis em dark mode
- [ ] Melhorar tipografia e espaçamento entre componentes
- [ ] Melhorar contraste de cards e elementos de destaque
- [ ] Polir páginas Projeções e Metas (vindas da Sprint 05)
- [ ] Testar responsividade em diferentes resoluções
- [ ] Garantir consistência visual entre todas as páginas
- [ ] Melhorar feedback visual de loading e estados vazios

## Armadilhas conhecidas

- Streamlit tem controle limitado sobre CSS nativo
- Dark mode do Streamlit conflita com cores customizadas em st.markdown
- Componentes st.metric e st.dataframe têm estilos próprios difíceis de sobrescrever
- Páginas Projeções e Metas podem não estar funcionais (Sprint 05 não validada)

## Arquivos criados/modificados

| Arquivo | Descrição |
|---------|-----------|
| `src/dashboard/paginas/visao_geral.py` | Redesign visual |
| `src/dashboard/paginas/categorias.py` | Redesign visual |
| `src/dashboard/paginas/extrato.py` | Redesign visual |
| `src/dashboard/paginas/contas.py` | Redesign visual |
| `src/dashboard/paginas/projecoes.py` | Polimento visual |
| `src/dashboard/paginas/metas.py` | Polimento visual |
| `.streamlit/config.toml` | Ajustes de tema |

## Critério de sucesso

Dashboard sem problemas visuais. Todas as páginas testadas no browser em resolução desktop. Contraste e legibilidade adequados em dark mode.

## Dependências

Sprint 05 (páginas Projeções e Metas).
