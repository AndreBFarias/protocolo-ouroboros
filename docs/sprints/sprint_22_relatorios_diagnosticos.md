# Sprint 22 -- Relatórios Diagnósticos: de Descritivo para Acionável

## Status: Pendente

## Objetivo

Transformar os relatórios mensais de meros dumps de dados em documentos que um Claude (ou qualquer IA) consiga usar para dar conselhos financeiros reais. Hoje são "bonitos mas ocos" -- mostram o que aconteceu sem explicar por que ou o que fazer.

## Contexto

A pasta `contexto/` contém um plano financeiro de 7 fases, dados de saúde (TDAH, burnout), dívidas em caducidade, metas de reserva de emergência e apartamento. Nada disso aparece nos relatórios. Um Claude lendo o relatório de 2026-04 não saberia que:
- André pode sair da Infobase em 2 meses (impacto de R$6k/mês na renda)
- A renda de R$8.7k é 50% abaixo do normal (deveria ser R$17.4k)
- O delivery caiu 87% como parte de um corte deliberado
- Os R$3-4k/mês em medicação TDAH estão escondidos em categorias espalhadas
- Todas as metas estão em 0% há meses

---

## Entregas

### 1. Seção "Contexto do Mês" (nova)

- [ ] Adicionar ao topo de cada relatório, após os badges:
  - Fase atual do plano (1-7, carregado de `metas.yaml` ou novo campo)
  - Eventos relevantes do mês (campo manual em `metas.yaml` ou `overrides.yaml`)
  - Renda esperada vs realizada (comparar com aba `renda`)
  - Status de dívidas (caducando, negociando, quitado)
- [ ] Se não houver dados de contexto, omitir a seção (graceful degradation)
- [ ] Arquivo: `src/load/relatorio.py` (nova função `_gerar_secao_contexto()`)

### 2. Seção "Renda Realizada" (nova)

- [ ] Breakdown por fonte de renda:
  - G4F (André), Infobase (André), PJ (Vitória), Rendimentos
  - Valor esperado vs realizado (delta com cor)
- [ ] Dados da aba `renda` do XLSX
- [ ] Arquivo: `src/load/relatorio.py` (nova função `_gerar_secao_renda()`)
- [ ] Se não houver dados de renda no mês, mostrar "Dados de renda não disponíveis"

### 3. Seção "Saúde Financeira" (expandir)

- [ ] Agrupamento de custos de saúde:
  - Farmácia + Saúde + Natação = "Total Saúde" (rollup)
  - Percentual do total de despesas
- [ ] Indicadores:
  - % comprometido com obrigatórios
  - % gasto com supérfluos
  - Velocidade de acumulação para metas
- [ ] Arquivo: `src/load/relatorio.py` (expandir `_gerar_secao_resumo()`)

### 4. Seção "Progresso nas Metas" (corrigir)

- [ ] Substituir seção estática atual (que mostra sempre 0%) por tracking real:
  - Ler saldo acumulado (soma de saldos positivos dos últimos N meses)
  - Comparar com valor_alvo de cada meta
  - Calcular velocidade: "No ritmo atual, atinge em X meses"
- [ ] Dados de `mappings/metas.yaml`
- [ ] Arquivo: `src/load/relatorio.py` (reescrever `_gerar_secao_metas()`)

### 5. Seção "Anomalias" (nova)

- [ ] Detectar automaticamente:
  - Categorias com variação > 50% vs mês anterior
  - Meses com renda < 70% da média dos últimos 6 meses
  - Gastos recorrentes que desapareceram (ex: aluguel não pago)
  - Novos gastos que não existiam no mês anterior
- [ ] Formato: lista com bandeira (alerta/info)
- [ ] Arquivo: `src/load/relatorio.py` (nova função `_gerar_secao_anomalias()`)

### 6. Seção "Projeção" (já corrigida na Sprint 20, apenas expandir)

- [ ] Após fix da Sprint 20 (projeções por mês):
  - Adicionar cenário "sem Infobase" se renda de Infobase > 0 no mês
  - Mostrar meses até reserva de emergência e entrada de apartamento
- [ ] Arquivo: `src/load/relatorio.py` (`_gerar_secao_projecao()` já existe)

### 7. Relatórios vazios (meses com poucos dados)

- [ ] Meses com < 5 transações: gerar relatório simplificado
  - Sem Mermaid chart (fica vazio)
  - Sem classificação detalhada
  - Mensagem: "Mês com dados insuficientes para análise completa (N transações)"
- [ ] Arquivo: `src/load/relatorio.py` (guard clause em `gerar_relatorio_mes()`)

### 8. Template para sessão Claude

- [ ] Criar arquivo `docs/templates/prompt_financeiro.md` com:
  - Instruções para Claude: "Você é um consultor financeiro analisando os dados abaixo"
  - Seções a incluir: último relatório + contexto pessoal + metas + dívidas
  - Perguntas sugeridas: "Estamos no caminho certo?", "O que cortar primeiro?"
- [ ] Não é gerado automaticamente -- é um template que o usuário copia e cola

---

## Armadilhas

- A aba `renda` do XLSX tem dados esparsos para 2022-2023 (histórico manual). Seção de renda deve lidar com ausência
- Detecção de anomalias pode gerar falsos positivos em meses de transição (ex: primeiro mês com novo banco)
- O rollup de "Saúde" assume que as categorias são: Farmácia, Saúde, Natação. Se houver novas categorias médicas, precisa ser extensível
- Cenário "sem Infobase" não deve aparecer em meses onde André já saiu (verificar se há renda Infobase no mês)
- Relatórios MD são para leitura humana E para input de IA -- manter formato que funcione para ambos

## Arquivos modificados

| Arquivo | Mudança |
|---------|---------|
| `src/load/relatorio.py` | 5 novas seções + reescrita de metas + guard clause |
| `src/load/formatacao_md.py` | Possíveis novas funções de formatação |
| `mappings/metas.yaml` | Possível adição de campo "fase_atual" e "eventos" |
| `docs/templates/prompt_financeiro.md` | Novo arquivo |

## Critério de sucesso

Um Claude lendo o relatório de 2026-04 consegue responder:
1. "Qual a situação financeira deste mês?" (com contexto, não só números)
2. "A renda está normal ou anômala?" (comparação com esperado)
3. "Quanto falta para a reserva de emergência?" (tracking de meta)
4. "O que mudou em relação ao mês passado?" (anomalias detectadas)
5. "Devo sair da Infobase agora?" (cenário projetado)

---

*"Dados sem contexto são apenas ruído." -- Nate Silver*
