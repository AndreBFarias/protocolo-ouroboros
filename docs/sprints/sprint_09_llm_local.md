# Sprint 09 -- LLM Local

## Status: Futuro (backend alternativo da Sprint 29)

## Relação com Sprint 29 (LLM Orquestrado via Claude)

Em 2026-04-16, a decisão foi usar **Claude Opus** como LLM principal durante a fase de melhoria contínua (Sprint 29). Esta sprint 09 permanece válida como **objetivo de longo prazo**: substituir o `ClaudeAPIProvider` por um `LocalLLMProvider` (Gemma/Phi) quando a qualidade local justificar, sem mudar o resto do sistema. A interface `LLMProvider` da Sprint 29 já prevê esse swap.

Iniciar esta sprint só após:
1. Sprint 29 estabilizada.
2. Modelos locais ≥ 4B parâmetros rodarem com qualidade aceitável na RTX 3050.
3. Custo mensal do Claude Opus justificar a troca.

## Objetivo

Adicionar análise financeira inteligente via LLM rodando localmente. O pipeline deve gerar insights automáticos sem dependência de APIs externas, com fallbacks robustos.

## Entregas

- [ ] Módulo FinancialAnalyst (análise mensal, sugestão de cortes, detecção de anomalias)
- [ ] Configuração de modelo (Gemma 2B ou Phi-3 Mini, compatível com RTX 3050 4GB VRAM)
- [ ] Integração com relatório (seção "Insights" no MD mensal)
- [ ] Fallback CPU (modelo menor para máquinas sem GPU)
- [ ] Fallback sem LLM (heurísticas pré-definidas, pipeline nunca falha)
- [ ] Documentação de integração com outros projetos

## Armadilhas conhecidas

- RTX 3050 tem apenas 4GB VRAM, modelos maiores que 2B podem não caber
- Quantização GGUF/GPTQ necessária para rodar em 4GB
- Latência de inferência pode ser alta em CPU, considerar cache de respostas
- Primeira execução precisa baixar o modelo (~1.5GB)

## Arquivos criados/modificados

| Arquivo | Descrição |
|---------|-----------|
| `src/analysis/__init__.py` | Init do módulo de análise |
| `src/analysis/financial_analyst.py` | Módulo principal de análise via LLM |
| `src/analysis/heuristics.py` | Fallback baseado em regras |
| `src/analysis/config.py` | Configuração de modelo e hardware |
| `src/load/relatorio.py` | Seção "Insights" adicionada |

## Critério de sucesso

Pipeline nunca falha por falta de LLM. Se GPU disponível, gera insights via modelo local. Se não, degrada para heurísticas sem perda de funcionalidade crítica.

## Dependências

Sprint 05 (relatórios e projeções).
