## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-112
  title: "Padding/margin/borda foco-ativo globais (design system polish)"
  prioridade: P1
  estimativa: 3h
  origem: "feedback dono 2026-04-27 -- nenhum elemento pode estar colado na borda da box do fundo; foco precisa de borda destacada"
  pre_requisito_de: [100]
  touches:
    - path: src/dashboard/tema.py
      reason: "css_global() ganha regras universais de padding/margin/borda; adicionar tokens PADDING_INTERNO, BORDA_FOCO"
    - path: src/dashboard/paginas/busca.py
      reason: "input principal da Busca Global recebe borda visivel default + borda destacada em foco"
    - path: tests/test_dashboard_tema.py
      reason: "regressao: css_global contem regras de padding/borda via tokens"
  forbidden:
    - "Tocar em logica de pagina especifica que nao seja CSS (deixa para outra sprint)"
    - "Mudar layout estrutural (so spacing e bordas)"
    - "Hardcode de px em pagina especifica -- so via tokens em tema.py"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dashboard_tema.py -v"
    - cmd: ".venv/bin/pytest tests/test_dashboard*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Tokens novos em tema.py: PADDING_INTERNO=24px (conteudo), PADDING_CHIP=16px, BORDA_RAIO=8px, BORDA_ATIVA_PX=2px"
    - "css_global() emite regras universais para .stTextInput, .stSelectbox, .stMultiSelect, expander, st.tabs body"
    - "Box da Busca Global tem borda visivel padrao (1px texto_sec) e destacada em :focus-within (2px destaque)"
    - "Box do conteudo principal tem padding 24px (.main .block-container ja tem desde Sprint 76, manter)"
    - "Validacao visual humana: nenhum texto colado em borda; foco ativo visivel"
  proof_of_work_esperado: |
    # Antes (validacao visual)
    # Captura screenshot do dashboard atual: textos da Busca Global colados nas bordas da box

    # Depois (validacao visual)
    # Mesma tela: padding visivel em todos os contornos; borda da box de busca presente
    # Foco no input: borda muda de 1px texto_sec para 2px destaque (#BD93F9)

    # Confirmacao tecnica
    grep -E 'PADDING_INTERNO|BORDA_RAIO' src/dashboard/tema.py
    # = >=2 ocorrencias (definicao + uso em css_global)
```

---

# Sprint UX-112 -- Padding/borda global

**Status:** BACKLOG (P1, criada 2026-04-27, pré-requisito da Sprint 100)

Hoje texto fica "ultra colado" em bordas e elemento focado não comunica visualmente que está ativo. Sprint adiciona tokens de spacing + borda no `tema.py` e aplica via `css_global` para todas as páginas herdarem.

Sprint 92c (concluída 2026-04-23) já estabeleceu CSS vars + helpers; UX-112 estende esses tokens com `PADDING_INTERNO`, `BORDA_RAIO`, `BORDA_ATIVA_PX`. Reuso direto.

---

*"Espaço em branco também é design. Borda não é decoração — é mensagem de estado." -- princípio do contraste honesto*
