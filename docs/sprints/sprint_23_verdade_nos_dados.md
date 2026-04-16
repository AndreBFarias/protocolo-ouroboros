# Sprint 23 -- Verdade nos Dados: Eliminar Placeholders e Dados Estáticos

## Status: Concluída (parcial -- itens de visão movidos para Sprints 25 e 26)

## Objetivo

O XLSX tem abas com dados falsos, estáticos ou vazios que dão a impressão de funcionalidade que não existe. Cada campo que aparece vazio ou com placeholder é uma mentira silenciosa. Esta sprint elimina todos eles: ou preenche com dados reais, ou remove o campo, ou documenta explicitamente que o dado não está disponível.

---

## Entregas

### Aba `renda` -- colunas sempre vazias

- [ ] **INSS, IRRF, VR/VA sempre vazios**
  - O pipeline infere receita das transações (tipo == "Receita"), mas não tem como extrair INSS retido, IRRF na fonte ou VR/VA
  - Sem extrator de contracheque, esses dados nunca existirão automaticamente
  - Decisão: remover as colunas vazias OU renomear a aba para refletir o que realmente contém (ex: "receitas" em vez de "renda")
  - O schema no CLAUDE.md documenta essas colunas como se existissem
  - Arquivo: `src/load/xlsx_writer.py`, `CLAUDE.md`

### Aba `analise` -- texto estático falso

- [ ] **Conteúdo é soma de totais, não análise**
  - Deveria conter "texto livre com insights gerados por mês" (CLAUDE.md)
  - Na realidade: gera frases genéricas como "Total de X transações, Y receita, Z despesa"
  - Sem LLM local (Sprint 08), não há análise inteligente possível
  - Decisão: gerar insights baseados em regras (anomalias, comparativos) OU renomear para "resumo" e documentar que análise real depende da Sprint 08
  - Arquivo: `src/load/xlsx_writer.py` (seção de análise)

### Aba `dividas_ativas` -- dados congelados de 2023

- [ ] **Importados do controle_antigo.xlsx, nunca atualizados**
  - 26 linhas com status "Pago"/"Não Pago" de 2022-2023
  - As dívidas reais atuais (Nubank PF R$13.049 + PJ R$10.783) não estão refletidas
  - Decisão: criar entrada manual em YAML para dívidas ativas OU marcar a aba como "histórico" e não "ativas"
  - Arquivo: `src/load/xlsx_writer.py`, possível `mappings/dividas.yaml` (novo)

### Aba `inventario` -- dados congelados de 2023

- [ ] **18 bens importados do histórico, sem atualização**
  - Depreciação calculada a partir de dados estáticos
  - Nenhum mecanismo para adicionar/remover bens
  - Decisão: criar `mappings/inventario.yaml` para manutenção manual OU documentar como snapshot histórico
  - Arquivo: `src/load/xlsx_writer.py`, possível `mappings/inventario.yaml` (novo)

### Aba `prazos` -- 6 prazos estáticos

- [ ] **Importados do histórico, layout frágil (depende de índices de coluna)**
  - Leitura usa fallback entre índices de coluna C/D e A/B
  - Nenhum mecanismo para atualizar prazos
  - Decisão: migrar para `mappings/prazos.yaml` OU consolidar com `mappings/metas.yaml`
  - Arquivo: `src/load/xlsx_writer.py`

### Aba `irpf` -- campo cnpj_cpf sempre vazio

- [ ] **Coluna cnpj_cpf nunca preenchida**
  - O tagger IRPF não extrai CNPJ/CPF do contraparte
  - Para declaração real, esse campo é essencial
  - Decisão: extrair CNPJ quando aparece na descrição (regex) OU remover coluna
  - Arquivo: `src/transform/irpf_tagger.py`, `src/load/xlsx_writer.py`

### Projeção com --mes usando dados filtrados

- [ ] **Bug remanescente da Sprint 19**
  - Quando `--mes YYYY-MM` é usado, `gerar_relatorios()` recebe dados já filtrados
  - Projeção calcula média de 1 mês em vez dos 3 últimos
  - Fix: passar transações completas para `gerar_relatorios()` mesmo quando --mes filtra o extrato
  - Arquivo: `src/pipeline.py` (fluxo de --mes), `src/load/relatorio.py`

---

## Armadilhas

- Remover colunas do XLSX pode quebrar o dashboard se ele referencia pelo nome
- A aba `dividas_ativas` é exibida na aba Contas do dashboard -- mudanças precisam ser refletidas
- Mover dados estáticos para YAML cria mais arquivos para manter, mas é honesto
- O campo cnpj_cpf precisa de regex robusta (formatos variados nos PDFs)

## Critério de sucesso

Zero campos que exibem dados que não existem. Cada coluna no XLSX ou tem dado real ou não existe. CLAUDE.md reflete a verdade sobre o que cada aba contém.

---

*"A verdade é sempre a melhor defesa." -- Aristóteles*
