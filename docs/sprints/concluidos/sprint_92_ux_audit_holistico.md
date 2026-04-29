---
concluida_em: 2026-04-23
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 92
  title: "UX audit holístico -- heurísticas, IA, wireframes, plano de redesign"
  touches:
    - path: docs/ux/audit_2026-xx-xx.md
      reason: "relatório estruturado (sem código)"
    - path: docs/ux/wireframes/
      reason: "esboços por aba (ascii ou mermaid; nenhuma implementação)"
    - path: docs/ux/design_tokens.md
      reason: "sistema de espaçamento, tipografia, cor, iconografia"
  forbidden:
    - "Implementar código de dashboard nesta sprint -- saída é DOCUMENTO"
    - "Propor redesign sem evidência (cada recomendação cita screenshot)"
    - "Ignorar restrições técnicas do Streamlit (componente nativo vs custom)"
  tests:
    - cmd: "bash scripts/check_doc_ux.sh (se existir) -- OK se ausente"
  acceptance_criteria:
    - "docs/ux/audit_2026-xx-xx.md cobre 10 heurísticas Nielsen aplicadas às 13 abas do dashboard"
    - "Mapa de Information Architecture: 13 abas agrupadas em no máx 5 clusters (Visão, Dinheiro, Documentos, Meta, Admin)"
    - "User journeys: 3 personas (André operador diário, Vitória consulta rápida, futuro auditor) com fluxo de 3-5 passos cada"
    - "Design tokens: paleta Dracula com uso declarado por contexto (alerta, sucesso, dado, neutro); escala tipográfica (h1..h4, body, caption); espaçamento 8pt grid"
    - "Wireframes ASCII de pelo menos 4 abas redesenhadas (Visão Geral, Extrato, Completude, Grafo)"
    - "Plano de execução em 3 sprints (92a, 92b, 92c) com acceptance por sprint"
    - "Sprint 91 (polish cirúrgico) marcada como dependência nulificada por esta (se 92a cobrir os 6 fixes) ou mantida em paralelo"
```

---

# Sprint 92 -- UX audit holístico

**Status:** BACKLOG
**Prioridade:** P2 (estratégica; influencia todo o produto)
**Dependências:** Sprint 86.3-86.9 validada (12 screenshots em `docs/screenshots/sprint_86_2026-04-24/`)
**Origem:** usuário apontou que Sprint 91 é polish cirúrgico; pediu estudo de UX de verdade

## Escopo

### 92.1 -- Auditoria heurística (Nielsen)

Para cada uma das 13 abas (Visão Geral, Categorias, Extrato, Contas, Pagamentos, Projeções, Metas, Análise, IRPF, Catalogação, Busca Global, Grafo + Obsidian, Completude), avaliar contra 10 heurísticas:

1. Visibilidade do status do sistema
2. Correspondência com mundo real
3. Controle e liberdade do usuário
4. Consistência e padrões
5. Prevenção de erros
6. Reconhecer em vez de lembrar
7. Flexibilidade e eficiência
8. Estética e design minimalista
9. Ajudar a reconhecer, diagnosticar, recuperar de erros
10. Ajuda e documentação

Cada aba recebe nota 0-5 por heurística + 1 recomendação.

### 92.2 -- Information Architecture

13 abas é demais. Proposta de redução para 5 clusters:

- **Hoje** (Visão Geral atual)
- **Dinheiro** (Extrato, Contas, Pagamentos, Projeções)
- **Documentos** (Catalogação, Completude, Busca Global, Grafo + Obsidian)
- **Análise** (Categorias, Análise, IRPF)
- **Metas** (Metas, Projeções de longo prazo)

Decisão arquitetural: Streamlit tabs nativas suportam essa hierarquia? Se não, usar `st.sidebar.radio` para cluster + `st.tabs` para abas dentro do cluster.

### 92.3 -- User journeys

Três personas identificadas:
- **André operador diário** (abre dashboard 3x/semana): quer ver "como está o mês", confere última transação, vê alertas
- **Vitória consulta rápida**: quer saber quanto posso gastar até fim do mês
- **Auditor futuro (IRPF, advogado)**: quer documentos + categoria + valor por mês

Para cada persona, mapear fluxo atual (quantos cliques, quantas abas) vs fluxo ideal (1-2 cliques).

### 92.4 -- Design system

- **Paleta Dracula com uso declarado:**
  - `#282a36` fundo base
  - `#44475a` fundo elevado
  - `#f8f8f2` texto primário
  - `#6272a4` texto secundário
  - `#50fa7b` verde (sucesso, positivo, saudável)
  - `#ff5555` vermelho (erro, alerta, atrasado)
  - `#ffb86c` laranja (aviso, questionável)
  - `#bd93f9` roxo (destaque primário, brand)
  - `#f1fa8c` amarelo (atenção suave, info)
  - `#ff79c6` rosa (ação secundária)
- **Tipografia:** JetBrainsMono ou IBM Plex Mono (já usada). Escala 13/14/16/20/24/32.
- **Espaçamento:** 8pt grid -- 8, 16, 24, 32, 48, 64.
- **Iconografia:** Feather ou Lucide (minimalista, traço fino).

### 92.5 -- Wireframes

Para pelo menos 4 abas críticas, produzir wireframe ASCII/mermaid mostrando:
- Estrutura de grid (12 colunas)
- Hierarquia visual (h1, h2, caption)
- Posicionamento de gráficos, tabelas, filtros
- Estados (vazio, com dados, com erro)

### 92.6 -- Plano de execução (sub-sprints)

92a -- fixes cirúrgicos (equivalente à Sprint 91 ou absorve)
92b -- IA + reorganização de abas
92c -- Design system implementado (tokens em CSS + tema.py)

## Proof-of-work

- `docs/ux/audit_2026-xx-xx.md` com 10x13=130 notas + recomendações.
- `docs/ux/wireframes/visao_geral.md`, `extrato.md`, `completude.md`, `grafo.md`.
- `docs/ux/design_tokens.md`.
- `docs/sprints/backlog/sprint_92a.md`, `92b.md`, `92c.md`.

## Armadilhas

- Risco de paralisia por análise: audit é DOCUMENTO, não projeto infinito. Time-box: 1 sessão dedicada (3-4h).
- Streamlit tem limites: não dá para redesenhar como site custom React. Wireframes devem respeitar componentes nativos (st.columns, st.tabs, st.sidebar).
- Não delegar para agente de design (não temos). Audit é tarefa do dono (André) ou sessão dedicada Opus + dono.

---

*"Primeiro entender o problema; depois descrever a solução; só então escrever código." -- princípio de design responsável*
