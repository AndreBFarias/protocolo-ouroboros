# Sprint 10 - Automação Completa do IRPF

## Objetivo

Automatizar a preparação completa da declaração do Imposto de Renda. Gerar pacote com CSVs organizados, simular regimes tributários e fornecer interface interativa para acompanhamento.

## Entregas

- [ ] Gerador de pacote IRPF: CSVs separados por categoria fiscal + resumo consolidado
- [ ] Simulador completo vs simplificado: cálculo de imposto em ambos os regimes, recomendação do melhor, comparação com IRRF já retido
- [ ] Checklist de documentos: lista do que já foi coletado vs o que falta para declaração completa
- [ ] Página Streamlit IRPF: dashboard do ano-calendário, simulação interativa de regime, visualização de deduções

## Dependências

Sprint 4 (tags IRPF automáticas) + Sprint 5 (relatórios e projeções).

## Critério de Sucesso

`./run.sh --irpf 2026` gera pacote completo com CSVs, simulação de regime e checklist de documentos. Página IRPF no dashboard exibe dados corretos do ano-calendário.

## Estimativa de Complexidade

**Alta.** Regras fiscais brasileiras são complexas e mudam anualmente. Simulação de regimes exige precisão numérica. Checklist de documentos depende de mapeamento completo das categorias fiscais. Estimativa: 2-3 semanas.
