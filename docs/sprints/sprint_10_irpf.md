# Sprint 10 -- IRPF Completo

## Status: Pendente
Issue: a criar

## Objetivo

Automatizar a preparação completa da declaração do Imposto de Renda. Gerar pacote com CSVs organizados, simular regimes tributários e fornecer interface interativa.

## Entregas

- [ ] Gerador de pacote IRPF (CSVs separados por categoria fiscal + resumo consolidado)
- [ ] Simulador completo vs simplificado (cálculo de imposto em ambos os regimes)
- [ ] Checklist de documentos (coletado vs faltando para declaração completa)
- [ ] Página Streamlit IRPF (dashboard do ano-calendário, simulação interativa)
- [ ] `./run.sh --irpf ANO` (gera pacote completo)

## Armadilhas conhecidas

- Regras fiscais brasileiras mudam anualmente, tabelas precisam ser atualizáveis
- Simulação de regimes exige precisão numérica (arredondamento IRPF tem regras próprias)
- Checklist depende de mapeamento completo das categorias fiscais para tipos IRPF
- Deduções médicas exigem CNPJ do prestador, que nem sempre está disponível nos extratos

## Arquivos criados/modificados

| Arquivo | Descrição |
|---------|-----------|
| `src/irpf/__init__.py` | Init do módulo IRPF |
| `src/irpf/gerador_pacote.py` | Gerador de CSVs por categoria fiscal |
| `src/irpf/simulador.py` | Simulador de regimes tributários |
| `src/irpf/checklist.py` | Checklist de documentos |
| `src/dashboard/paginas/irpf.py` | Página Streamlit IRPF |
| `mappings/tabelas_irpf.yaml` | Tabelas de alíquotas e deduções |
| `run.sh` | Flag --irpf adicionada |

## Critério de sucesso

`./run.sh --irpf 2026` gera pacote completo com CSVs, simulação de regime e checklist de documentos. Página IRPF no dashboard exibe dados corretos do ano-calendário.

## Dependências

Sprint 04 (tags IRPF automáticas).
