# Sprint 07 - Análise Financeira via LLM Local

## Objetivo

Adicionar análise financeira inteligente via LLM rodando localmente. O pipeline deve gerar insights automáticos sem dependência de APIs externas, com fallbacks robustos para garantir que nunca falhe por falta de recurso.

## Entregas

- [ ] Módulo FinancialAnalyst: análise mensal, sugestão de cortes, detecção de anomalias, projeção de metas
- [ ] Configuração de modelo: Gemma 2 2B ou Phi-3 Mini (compatível com Acer Nitro 5, RTX 3050 4GB VRAM)
- [ ] Integração com pipeline: seção "Insights" adicionada ao relatório mensal
- [ ] Fallback sem GPU: execução em CPU com modelo menor
- [ ] Fallback sem LLM: análise baseada em regras (heurísticas pré-definidas)
- [ ] Documentação de possível integração futura com Luna

## Dependências

Sprint 5 (relatórios automáticos e projeções).

## Critério de Sucesso

Pipeline nunca falha por falta de LLM. Se GPU disponível, gera insights via modelo local. Se não, degrada para regras sem perda de funcionalidade crítica.

## Estimativa de Complexidade

**Alta.** Integração com modelos locais, gerenciamento de VRAM limitada, e implementação de cadeia de fallbacks exigem testes extensivos em diferentes configurações de hardware. Estimativa: 2-3 semanas.
