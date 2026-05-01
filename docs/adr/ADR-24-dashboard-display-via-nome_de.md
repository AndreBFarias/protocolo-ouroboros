# ADR-24 — Dashboard local-first exibe `display_name` via `nome_de` em runtime

- **Status:** aceita
- **Data:** 2026-05-01
- **Sprint:** MOB-bridge-1
- **Cruzamento:** ADR-23 (identidade genérica no backend)

## Contexto

ADR-23 retira nomes reais (`André`, `Vitória`) do código Python do
backend. A coluna `quem` do XLSX, os filtros do dashboard e as
agregações do relatório passam a operar sobre identificadores
genéricos `pessoa_a` / `pessoa_b` / `casal`.

Surge a tensão de produto: o dashboard Streamlit é uma ferramenta
local-first (rodando em `localhost:8501` na máquina do dono, sem
exposição pública), e tinha como afeto operacional óbvio mostrar
"André" e "Vitória" nos selectboxes, KPIs, tabelas e títulos. Um
dashboard que apresenta `pessoa_a` e `pessoa_b` ao próprio dono é
ergonomicamente pior sem ganho real de privacidade — o dono já tem
acesso a todos os dados do casal por definição (auth = quem está
sentado na frente do laptop).

## Decisão

**O dashboard mantém os labels reais ao dono.** A identidade
mostrada na UI é resolvida em runtime via
`src.utils.pessoas.nome_de(pessoa_id)`, que lê o `display_name`
declarado em `mappings/pessoas.yaml` (gitignored).

Distinção em três camadas:

1. **Persistência (XLSX, grafo, logs):** identificador genérico
   sempre. ADR-23.
2. **Filtragem interna (queries, agregações):** identificador
   genérico sempre. Filtros do dashboard convertem o
   `display_name` selecionado pelo usuário para genérico via
   `pessoa_id_de_legacy()` antes de aplicar `df["quem"] == ...`.
3. **Apresentação (selectbox, KPIs, tabelas, títulos):**
   `display_name` resolvido em runtime via `nome_de()`. Ex:
   - Selectbox de pessoa: `["Todos", nome_de("pessoa_a"),
     nome_de("pessoa_b")]`.
   - Tabela "Gastos por pessoa" do relatório:
     `f"| {nome_de('pessoa_a')} | {valor} |"`.

### Por que isso não é vazamento

- `mappings/pessoas.yaml` está no `.gitignore` desde a Sprint 90.
- `display_name` só existe nessa camada local. Nada vai para o
  repositório nem para artefato persistido.
- Repos público + clones em outras máquinas terão `pessoas.yaml`
  ausente; `nome_de()` cai no fallback do próprio identificador
  (`pessoa_a` / `pessoa_b` / `casal`), e o dashboard mostra os
  identificadores genéricos sem nenhuma quebra. Local-first com
  graceful degradation perfeita.
- O dono do laptop é a única audiência da UI; mostrar nome real a
  ele é ergonomia, não PII leak.

### Compatibilidade com XLSX legado

`filtrar_por_pessoa(df, pessoa)` em `src/dashboard/dados.py` aceita
ambos os formatos no parâmetro (`"André"`, `"Vitória"`,
`"pessoa_a"`, `"pessoa_b"`, `"Todos"`) e em `df["quem"]`. A
normalização bilateral via `pessoa_id_de_legacy` garante que o
filtro funciona mesmo se o usuário ainda tem XLSX antigo aberto
em paralelo.

## Consequências

### Positivas

- UX preservada: dono continua vendo "André" e "Vitória" na UI.
- Zero PII em código versionado.
- Graceful degradation se `pessoas.yaml` ausente: UI mostra
  identificadores genéricos sem crash.
- Mudar nome real (apelido, casamento etc.) é editar 1 yaml; código
  e XLSX não precisam ser migrados.

### Negativas

- Uma chamada a `nome_de()` em runtime nas páginas que mostram
  pessoa. Custo desprezível (resolver tem cache lru no yaml).

### Neutras

- Análises automáticas internas (smoke aritmético, testes,
  scripts de auditoria) operam direto sobre o identificador
  genérico, sem precisar passar pelo `display_name`. Consistência
  com schema único do XLSX.

## Verificação

```bash
# UI mostra display real ao dono.
make dashboard
# Sidebar -> Pessoa: "Todos / André / Vitória" (não pessoa_a / pessoa_b).

# Mas o dado no XLSX e em queries internas é genérico.
.venv/bin/python -c "
import pandas as pd
df = pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato')
print(df['quem'].value_counts())
# pessoa_a    NNN
# pessoa_b    NNN
# casal       NNN
"
```
