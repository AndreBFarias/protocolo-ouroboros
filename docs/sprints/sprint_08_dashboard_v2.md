# Sprint 08 -- Dashboard v2 (Redesign Dracula)

## Status: Pendente
Issue: a criar

## Objetivo

Redesign completo do dashboard Streamlit com paleta Dracula Theme, controles de granularidade temporal, seletor de pessoa como dropdown, fonte mínima 13px e repaginação de todas as 6 abas para melhor leitura e experiência visual.

## Paleta de Cores -- Dracula Theme

```
Fundo principal:   #282A36  (Background)
Fundo cards:       #44475A  (Current Line)
Texto principal:   #F8F8F2  (Foreground)
Texto secundário:  #6272A4  (Comment)
Acento positivo:   #50FA7B  (Green)
Acento negativo:   #FF5555  (Red)
Acento alerta:     #FFB86C  (Orange)
Acento neutro:     #8BE9FD  (Cyan)
Acento destaque:   #BD93F9  (Purple)
Acento especial:   #FF79C6  (Pink)
Acento info:       #F1FA8C  (Yellow)
```

Referência: https://draculatheme.com/spec

## Regras de Tipografia

| Elemento | Tamanho | Peso |
|----------|---------|------|
| Mínimo absoluto (qualquer texto) | 13px | normal |
| Texto de corpo / tabelas / labels | 14px | normal |
| Subtítulos de seção | 16px | bold |
| Valores em cards (R$ X.XXX) | 20-22px | bold |
| Títulos de página (st.subheader) | 18-20px | bold |
| Abas (tab labels) | 15px | normal/bold |

**Regra:** nenhum texto no dashboard renderiza abaixo de 13px.

## Entregas

### 1. Sidebar -- Controles Globais

- [ ] **Pessoa**: trocar `st.radio` por `st.selectbox` (dropdown igual ao mês)
- [ ] **Granularidade**: novo `st.selectbox` com opções:
  - Dia
  - Semana
  - Mês (padrão)
  - Ano
- [ ] **Período**: ajustar seletor conforme granularidade:
  - Dia: lista de datas (DD/MM/YYYY) do mês selecionado
  - Semana: lista de semanas ("Sem 1 - 01/04 a 07/04", "Sem 2 - 08/04 a 14/04" etc.)
  - Mês: lista de meses YYYY-MM (comportamento atual)
  - Ano: lista de anos disponíveis (2022, 2023, 2024, 2025, 2026)
- [ ] Cards de resumo na sidebar: aplicar Dracula e fonte mínima 13px
- [ ] Fundo sidebar: `#282A36`

### 2. CSS Global (`app.py`)

- [ ] Migrar paleta inteira de `#0E1117/#1E2130/#4ECDC4` para Dracula
- [ ] `.streamlit/config.toml`: cores primárias e fundo Dracula
- [ ] Abas: manter fix atual de visibilidade, ajustar cores para Dracula
  - Aba ativa: `#F8F8F2` (branco) com borda `#BD93F9` (purple)
  - Abas inativas: `#6272A4` (comment)
  - Hover: `#F8F8F2`
- [ ] Download button: fundo `#44475A`, borda `#BD93F9`, hover `#BD93F9`
- [ ] Fonte mínima 13px em todo CSS customizado

### 3. Aba Visão Geral (`visao_geral.py`)

- [ ] Cards de métricas: fundo `#44475A`, borda-esquerda colorida, valores 20px+
- [ ] Indicador de saúde financeira: cores Dracula (Green/Orange/Red)
- [ ] Gráfico de barras Receita vs Despesa:
  - Receita: `#50FA7B` (green), Despesa: `#FF5555` (red)
  - Fundo `#282A36`, eixos e texto `#F8F8F2`
  - Título 16px bold
- [ ] Donut chart classificação:
  - Obrigatório: `#8BE9FD` (cyan), Questionável: `#FFB86C` (orange), Supérfluo: `#FF79C6` (pink)
  - Labels 13px+, legenda 13px+
- [ ] Espaçamento uniforme entre componentes (margin 15-20px)

### 4. Aba Categorias (`categorias.py`)

- [ ] Treemap: escala de cores Dracula por classificação
- [ ] Texto do treemap: 13px+ com `textfont.size=13`
- [ ] Top 10 Categorias: tabela com fundo alternado `#282A36`/`#44475A`
- [ ] Evolução Top 5: linhas com cores Dracula (Green, Red, Cyan, Orange, Purple)
- [ ] Títulos de seção 16px bold

### 5. Aba Extrato (`extrato.py`)

- [ ] Filtros: 4 dropdowns com labels 14px
- [ ] Busca: placeholder 13px+
- [ ] Contagem de transações: 14px bold
- [ ] Tabela: fonte 13px+, headers com fundo `#44475A`
- [ ] Botão CSV: estilo Dracula (purple accent)
- [ ] Valores monetários alinhados à direita

### 6. Aba Contas (`contas.py`)

- [ ] Cards de resumo (Pago/Pendente/Total): Dracula colors
  - Pago: `#50FA7B`, Pendente: `#FF5555`, Total: `#8BE9FD`
- [ ] Tabela de dívidas: semáforo visual com cores Dracula
- [ ] Tabela de prazos: fonte 13px+
- [ ] Títulos 16px bold

### 7. Aba Projeções (`projecoes.py`)

- [ ] Cards de cenário: fundo `#44475A`, borda Dracula
  - Ritmo Atual: `#50FA7B`, Pós-Infobase: `#FF5555`, Meta Apê: `#8BE9FD`
- [ ] Nota explicativa cenário negativo: `#FFB86C` (orange)
- [ ] Gráfico patrimônio: linhas Dracula, fundo `#282A36`
- [ ] Marcos (reserva, apê): linhas pontilhadas Dracula
- [ ] Slider de simulação: accent `#BD93F9` (purple)
- [ ] Textos 13px+

### 8. Aba Metas (`metas.py`)

- [ ] Contagem de metas: 14px
- [ ] Cards de meta: fundo `#44475A`, borda por prioridade
  - P1: `#FF5555` (red), P2: `#FFB86C` (orange), P3: `#8BE9FD` (cyan), P4: `#50FA7B` (green)
- [ ] Barra de progresso: cor `#BD93F9` (purple) em vez de verde padrão
- [ ] Timeline: marcadores Dracula, texto 13px+
- [ ] Prazo/urgência: cores Dracula
- [ ] Textos 13px+

## Constantes Centralizadas

Criar `src/dashboard/tema.py` com:

```python
DRACULA = {
    "fundo": "#282A36",
    "fundo_card": "#44475A",
    "texto": "#F8F8F2",
    "texto_sec": "#6272A4",
    "verde": "#50FA7B",
    "vermelho": "#FF5555",
    "laranja": "#FFB86C",
    "ciano": "#8BE9FD",
    "roxo": "#BD93F9",
    "rosa": "#FF79C6",
    "amarelo": "#F1FA8C",
}

FONTE_MINIMA: int = 13
FONTE_CORPO: int = 14
FONTE_SUBTITULO: int = 16
FONTE_VALOR: int = 20
FONTE_TITULO: int = 18
```

Todos os módulos de página importam de `tema.py` em vez de definir dicts `CORES` locais.

## Fluxo de Granularidade

```
Usuário seleciona "Ano" no dropdown de granularidade
  -> Seletor de período mostra: [2022, 2023, 2024, 2025, 2026]
  -> Dados filtrados por ano inteiro
  -> Gráficos agregam por mês dentro do ano

Usuário seleciona "Mês" (padrão)
  -> Seletor mostra: [2026-10, 2026-09, ..., 2022-08]
  -> Comportamento atual mantido

Usuário seleciona "Semana"
  -> Seletor mostra semanas do mês atual: [Sem 1, Sem 2, Sem 3, Sem 4]
  -> Precisa de seletor de mês auxiliar para navegar entre meses

Usuário seleciona "Dia"
  -> Seletor mostra datas do mês atual: [14/04/2026, 13/04/2026, ...]
  -> Precisa de seletor de mês auxiliar
```

## Armadilhas Conhecidas

- Streamlit `st.progress` não aceita cor customizada -- usar HTML/CSS override
- `st.dataframe` headers têm estilo interno difícil de sobrescrever -- pode precisar de `st.markdown` com tabela HTML
- Plotly `uniformtext_minsize` pode esconder labels se não couberem no espaço
- Trocar `st.radio` por `st.selectbox` muda a key do widget -- verificar se quebra estado
- Granularidade "Dia" e "Semana" requerem que `dados.py` suporte filtragem por data/semana, não só `mes_ref`
- `.streamlit/config.toml` tem prioridade sobre CSS injetado -- cores devem ser consistentes

## Arquivos a Criar/Modificar

| Arquivo | Descrição |
|---------|-----------|
| `src/dashboard/tema.py` | **NOVO** -- constantes Dracula centralizadas |
| `src/dashboard/app.py` | CSS global Dracula, sidebar, granularidade |
| `src/dashboard/dados.py` | Suporte a filtragem por dia/semana/ano |
| `src/dashboard/paginas/visao_geral.py` | Redesign Dracula |
| `src/dashboard/paginas/categorias.py` | Redesign Dracula |
| `src/dashboard/paginas/extrato.py` | Redesign Dracula |
| `src/dashboard/paginas/contas.py` | Redesign Dracula |
| `src/dashboard/paginas/projecoes.py` | Redesign Dracula |
| `src/dashboard/paginas/metas.py` | Redesign Dracula |
| `.streamlit/config.toml` | Tema Dracula nativo |

## Processo de Validação (Chrome MCP)

1. Iniciar dashboard (`make dashboard`)
2. Para cada aba:
   - Verificar que NENHUM texto está abaixo de 13px
   - Verificar cores Dracula aplicadas
   - Verificar legibilidade em dark mode
   - Testar com filtros (pessoa, granularidade)
3. Testar troca de granularidade: Mês -> Ano -> Semana -> Dia
4. Testar seletor de Pessoa como dropdown
5. Verificar navegação entre abas sem erro Python
6. Gauntlet: fase dashboard deve passar 8/8

## Critério de Sucesso

- [ ] Paleta Dracula em 100% dos componentes visuais
- [ ] Fonte mínima 13px em absolutamente tudo
- [ ] Pessoa como dropdown (não radio)
- [ ] Seletor de granularidade funcional (ano/mês/semana/dia)
- [ ] Período ajusta conforme granularidade
- [ ] 6 abas repaginadas e validadas via Chrome MCP
- [ ] Constantes centralizadas em `tema.py`
- [ ] Gauntlet 44/44

## Dependências

Sprint 03 (dashboard v1) + Sprint 05 (projeções e metas). Ambas concluídas.

---

*"A simplicidade é a sofisticação suprema." -- Leonardo da Vinci*
