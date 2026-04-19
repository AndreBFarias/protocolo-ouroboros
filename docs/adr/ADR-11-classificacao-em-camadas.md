# ADR-11: Classificação em Camadas

## Status: Aceita

## Contexto

Categorizar e classificar ~3.000 transações/ano envolve decidir quem tem a última palavra quando múltiplas fontes concordam ou discordam. Hoje o projeto tem pelo menos quatro fontes potenciais de classificação: overrides manuais, regras regex, armadilhas por valor (Ki-Sabor), e — a partir da Sprint 31 — o supervisor LLM.

Sem uma ordem de precedência explícita, qualquer adição de camada nova cria ambiguidade: o LLM passa por cima do override? O regex sobrescreve a correção manual? O fallback executa antes ou depois do supervisor?

Alternativas consideradas:
- **Qualquer fonte pode escrever a qualquer hora**: máxima flexibilidade, caos garantido.
- **LLM decide quando regex falha**: rápido mas introduz LLM direto no pipeline (viola ADR-08).
- **Hierarquia estrita, LLM apenas como sugestor externo**: mais disciplinado, alinhado com ADR-08 e ADR-09.

## Decisão

Toda classificação em produção segue hierarquia fixa, avaliada em ordem:

1. **`mappings/overrides.yaml`** — correção manual explícita para a transação. Sempre ganha. Tem prioridade absoluta porque representa decisão humana deliberada.
2. **`mappings/categorias.yaml`** — 111 regras regex determinísticas. Se casar, categoriza. Aplicar com `break` (não `return`) para garantir que a classificação (Obrigatório/Questionável/Supérfluo/N/A) sempre execute depois.
3. **`mappings/irpf_regras.yaml`** (a partir da Sprint 35) — regras IRPF em YAML, seguindo mesma lógica.
4. **Fallback determinístico:** `categoria = "Outros"`, `classificacao = "Questionável"`. Nunca inventar categoria nova.
5. **Supervisor LLM** — **não participa** da classificação em produção. Apenas observa o que caiu no fallback, propõe nova regra via ADR-08, aguarda aprovação. Quando aprovada, a regra migra para a camada 2, tornando a camada 4 cada vez menor.

## Consequências

**Positivas:**
- Determinismo total: mesma entrada sempre produz mesma saída em produção
- Fluxo de melhoria claro: casos fallback viram material de treino para o supervisor
- Separação estrita de responsabilidades: humano decide, regex executa, LLM sugere
- Alinha com ADR-08 (supervisor-aprovador) e ADR-09 (autossuficiência progressiva)
- Facilita testes: cada camada é isolada e auditável

**Negativas:**
- Correções urgentes exigem editar YAML e fazer commit (sem "hotfix via LLM")
- Conflitos entre regras regex ainda precisam ser resolvidos na ordem do arquivo
- Camada 4 (fallback) pode ficar visível no relatório até que o supervisor + humano fechem o gap

---

*"Uma coisa de cada vez, e cada coisa em seu lugar." -- Ordem medieval*
