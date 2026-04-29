---
concluida_em: 2026-04-27
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-115
  title: "Faixas vazias do bloco principal preenchidas + label busca alinhado"
  prioridade: P2
  estimativa: 30min
  origem: "feedback dono 2026-04-27 -- ha faixa vertical esquerda + bloco inferior em #282A36 (fundo) que cria quebra visual em vez de bloco continuo. Alem disso, label 'Busca global' nao alinha com input principal. Aceito como gambiarra ate UX-114 reescrever a pagina."
  pre_requisito_de: [UX-114]
  touches:
    - path: src/dashboard/tema.py
      reason: "css_global() ganha regra que pinta [data-testid='stMain'] (a area externa ao block-container) com cor #444659; bloco interno permanece com card_fundo"
    - path: src/dashboard/paginas/busca.py
      reason: "label 'Busca global' (paragraph com Q de search + texto) alinhado a esquerda igual ao input principal -- remover qualquer offset/centralizacao se houver"
    - path: tests/test_dashboard_tema.py
      reason: "regressao: css_global contem regra para stMain ou .main com background #444659"
  forbidden:
    - "Mudar tokens existentes da UX-112 (PADDING_INTERNO, BORDA_RAIO etc.)"
    - "Tocar em outras paginas (so a Busca Global e regra global do .main)"
    - "Adicionar deps externas"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dashboard_tema.py -v"
    - cmd: ".venv/bin/pytest tests/test_dashboard*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "[data-testid='stMain'] (ou seletor equivalente do streamlit) recebe background #444659 via css_global()"
    - "Bloco interno (.main .block-container) permanece distinto -- ou adota background ainda mais escuro/claro para criar contraste de bloco"
    - "Label 'Busca global' inicia em x igual ao input principal (sem indentacao adicional)"
    - "Validacao visual humana: bloco da Busca Global aparece como retangulo continuo sem 'faixa vertical escura' a esquerda nem 'faixa horizontal escura' embaixo"
    - "Pelo menos 2 testes regressivos: css_global contem cor #444659 aplicada ao container principal; cor mantida quando tema renderiza"
  proof_of_work_esperado: |
    # Antes
    # Faixa vertical esquerda (entre sidebar e bloco) em #282A36
    # Faixa inferior (abaixo do callout) em #282A36
    # Label "Busca global" desalinhado do input

    # Depois
    # .main pintado com #444659 -- continuidade visual com bloco interno
    # Label "Busca global" inicia exatamente na mesma coluna x do input
    # Captura runtime via Playwright em http://localhost:8520/?cluster=Documentos
```

---

# Sprint UX-115 -- Faixas vazias preenchidas + label alinhado

**Status:** CONCLUÍDA (commit `d187972`, 2026-04-27 — aguarda validação visual humana)

Hoje a página Busca Global mostra um bloco interno (card_fundo) cercado por faixas em `#282A36` (fundo da app), criando uma quebra visual. O dono pediu pintar essas faixas com `#444659` para virar um bloco contínuo. O label "Busca global" também está desalinhado do input — sprint corrige.

Escopo deliberadamente cirúrgico: solução gambiarra que será substituída quando UX-114 reescrever a página inteira. Não introduzir tokens novos — aplicar regra inline no `css_global()` justificada como gambiarra.

---

*"Continuidade visual e a forma mais barata de comunicar coerencia." -- principio do bloco continuo*
