# ADR-03: Regex para categorização de transações

## Status: Aceita

## Contexto

Cada transação precisa ser categorizada (Delivery, Transporte, Farmácia, etc.) e classificada (Obrigatório, Questionável, Supérfluo). Com ~3.000 transações/ano de 7 fontes diferentes, as descrições seguem padrões repetitivos por banco.

Alternativas consideradas:
- **Machine Learning (NLP/classificador)**: poderoso, mas requer dados de treino rotulados, e overkill para o volume. Não-determinístico dificulta auditoria.
- **Regras manuais por transação**: não escala, tedioso.
- **LLM (API)**: bom para casos ambíguos, mas viola princípio Local First e gera custo recorrente.

## Decisão

Usar regex compilados em YAML (`mappings/categorias.yaml`) para categorização determinística. Atualmente 111 padrões regex cobrem 100% das transações conhecidas. Overrides manuais (`mappings/overrides.yaml`) têm prioridade para correções pontuais.

O categorizer também detecta padrões novos não reconhecidos e os loga para revisão.

## Consequências

**Positivas:**
- Determinístico: mesma entrada sempre produz mesma saída
- Auditável: qualquer pessoa pode ler o YAML e entender as regras
- Rápido: 111 regex compilados processam 3.000 transações em < 1 segundo
- Fácil de manter: adicionar categoria nova = adicionar bloco YAML
- 100% de cobertura alcançado na Sprint 2

**Negativas:**
- Requer manutenção manual quando novos estabelecimentos aparecem
- Regex pode ter falsos positivos em descrições ambíguas (ex: Ki-Sabor exigiu regra por valor)
- Ordem de avaliação importa: overrides antes de regex, return vs break importa
- Não generaliza: padrões de um banco não se transferem automaticamente para outro

---

*"Toda solução deve ser tão simples quanto possível, mas não mais simples." -- Albert Einstein*
