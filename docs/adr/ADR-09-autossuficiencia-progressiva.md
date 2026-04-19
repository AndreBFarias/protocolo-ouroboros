# ADR-09: Autossuficiência Progressiva (complementa ADR-07)

## Status: Aceita

## Contexto

O ADR-07 (Local First) estabelece que o pipeline funciona offline e que APIs pagas são opcionais. O ADR-08 (Supervisor-Aprovador) introduz Claude API como ferramenta de melhoria contínua. À primeira vista há tensão: como justificar uma dependência externa num projeto Local First?

A resposta exige uma decisão explícita sobre o **papel temporal** do LLM. Há dois caminhos opostos:
- **LLM como infraestrutura permanente**: pipeline cresce dependendo cada vez mais do LLM; cada execução paga API; sistema deixa de funcionar offline.
- **LLM como ferramenta provisória de bootstrapping**: LLM ajuda a preencher lacunas do pipeline determinístico, mas cada aprovação **reduz** a necessidade de LLM no futuro. Meta é chegar num ponto onde o LLM quase nunca precisa ser chamado.

A diretriz explícita do projeto é a segunda: *"usar o Claude até conseguirmos a automação perfeita pra não precisar dele"*.

## Decisão

LLM é ferramenta provisória, mensurada e limitada:

1. **Métrica-chave publicada no dashboard:** `% de transações resolvidas determinísticamente`. Baseline atual: 85%. Meta de 90 dias: 98%. Meta de longo prazo: > 99%.
2. **Teto de custo:** variável `ANTHROPIC_MONTHLY_BUDGET_USD` em `.env`. `cost_tracker.py` bloqueia novas chamadas ao atingir o limite. Prompt caching é obrigatório (caching de 90% do contexto → custo de $2-5/mês em uso típico).
3. **Sucesso mede-se pela ausência:** número de proposições aprovadas por mês deve crescer inicialmente e depois cair à medida que o pipeline cobre mais padrões. Meses sem proposição nova = sinal de maturidade, não de falha.
4. **Fallback determinístico obrigatório:** todo módulo que chama LLM precisa de caminho alternativo funcional. OCR energia via Vision cai para tesseract se Claude indisponível. Supervisor pulado se API offline — pipeline continua normal.
5. **Privacidade:** CPF, senhas e identificadores pessoais são mascarados antes de qualquer chamada LLM (teste unitário valida o mascaramento).

## Consequências

**Positivas:**
- Preserva o espírito do ADR-07: dependência externa é exceção explícita, temporária e instrumentada
- Custo operacional permanece irrelevante ($2-5/mês com prompt caching)
- Dashboard cria pressão visual para melhorar as camadas determinísticas
- Projeto pode "desligar o LLM" a qualquer momento sem perder funcionalidade crítica

**Negativas:**
- Requer instrumentação (cost_tracker, métricas IA) antes de qualquer uso real do LLM
- Decisões de quando "desligar" o LLM são subjetivas — a métrica nunca será exatamente 100%
- Prompt caching adiciona complexidade ao design dos prompts (estrutura fixa obrigatória)

---

*"A melhor forma de prever o futuro é criá-lo." -- Peter Drucker*
