# CLAUDE.md -- Protocolo Ouroboros

```
VERSÃO: 2.0 | STATUS: PRODUÇÃO | LANG: PT-BR
TRANSAÇÕES: 2.859 | MESES: 44 (ago/2022 a out/2026) | BANCOS: 6
SPRINTS CONCLUÍDAS: 4/14 | CATEGORIZAÇÃO: 100% | IRPF TAGS: 79
```

---

## Missão

Pipeline ETL financeiro pessoal para o casal André e Vitória. Centraliza dados bancários de múltiplas fontes em XLSX consolidado + dashboard Streamlit + relatórios mensais + integração Obsidian.

**Princípio:** a IA toma TODAS as decisões técnicas. Ao receber arquivos novos, ela lê, extrai, categoriza, deduplica e gera saída. Sem perguntas desnecessárias.

---

## Regras Invioláveis

1. **Acentuação correta** em TUDO: código, commits, docs, comentários, variáveis em português. Nunca "funcao", "validacao", "descricao" -- o correto é "função", "validação", "descrição". Sem exceção.
2. **Zero emojis** em código, commits, docs e respostas.
3. **Zero menções a IA** em commits e código (nomes como Claude, GPT, Anthropic). Commits limpos e anônimos.
4. **Local First** -- tudo funciona offline. APIs externas são opcionais.
5. **Nunca `print()`** em produção. Logging via `rich` + `logging` com rotação (5MB, 3 backups).
6. **Nunca inventar dados.** Se não reconhecer um arquivo, loga warning e pula.
7. **Nunca remover código funcional** sem autorização explícita.
8. **`data/` inteiro no .gitignore** -- dados financeiros nunca no repositório.
9. **Paths relativos via `Path`** -- nunca hardcoded absolutos.
10. **Citação de filósofo** como comentário final de todo arquivo .py.

---

## Armadilhas Críticas

Aprendizados das Sprints 1-4 que PRECISAM ser respeitados:

| # | Armadilha | Solução |
|---|-----------|---------|
| 1 | C6 XLS encriptado -- xlrd sozinho falha | Usar `msoffcrypto-tool` para decriptar ANTES, depois `xlrd` |
| 2 | Itaú PDF protegido | Senha via `senhas.yaml` + pdfplumber. Nunca PyPDF2 |
| 3 | Nubank tem 2 formatos CSV incompatíveis | Cartão: `date,title,amount`. CC: `Data,Valor,Identificador,Descrição` |
| 4 | Ki-Sabor: mesmo local, 2 categorias | Valor >= R$ 800 = Aluguel. Valor < R$ 800 = Padaria. Regra de valor |
| 5 | Categorizer: `return` após match impede fallback | Trocado por `break` para que classificação N/A sempre execute |
| 6 | Histórico: classificações corrompidas | "Obrigatórios" (com s), "Rou" (truncado) -- normalizar no pipeline |
| 7 | Prazos no XLSX antigo: colunas erradas | Índices 2/3 no histórico, não 0/1. Verificar ambos |
| 8 | Git push requer SSH alias | `git@github.com-personal:[REDACTED]/Financas.git` |
| 9 | Pre-commit: `core.hooksPath` global | Usar script local `scripts/pre-commit-check.sh`, não `pre-commit install` |
| 10 | Tesseract OCR para energia | Valores R$ = 100% precisos. Consumo kWh = 67% (layout do app confunde) |
| 11 | Streamlit tabs: troca visual | Requer JavaScript (`document.querySelectorAll('[role="tab"]')[N].click()`) |
| 12 | Santander "Black Way" | É o cartão Elite Visa, final 7342 |
| 13 | Nubank CC tem duplicatas "(1)" "(2)" | Deduplicação por UUID é essencial |
| 14 | `msoffcrypto-tool` é dependência crítica | Não é óbvio -- sem ela, C6 XLS não abre |

---

## Identificação de Arquivos

A IA deve ler o CONTEÚDO (não confiar no nome) para detectar:

| Pista no conteúdo | Banco/Fonte |
|-------------------|-------------|
| "ITAÚ UNIBANCO", "itau.com.br", agência 6450 | Itaú -- extrato CC |
| "SANTANDER", "4220 XXXX XXXX 7342" | Santander -- fatura cartão |
| "NU PAGAMENTOS", "NUBANK", "Nu Financeira" | Nubank |
| "BCO C6 S.A.", "31.872.495" | C6 Bank |
| CSV: `date,title,amount` | Nubank cartão (André ou Vitória PJ) |
| CSV: `Data,Valor,Identificador,Descrição` | Nubank CC (Vitória PF/PJ) |
| "Neoenergia", "CEB", "Kwh" | Conta de energia (OCR) |
| "CAESB", "Saneamento" | Conta de água |

---

## Schema do XLSX (8 abas)

### extrato (tabela principal)

| Coluna | Tipo | Obrigatório |
|--------|------|-------------|
| data | date | sim |
| valor | float | sim |
| forma_pagamento | str (Pix/Débito/Crédito/Boleto/Transferência) | sim |
| local | str | sim |
| quem | str (André/Vitória/Casal) | sim |
| categoria | str | sim |
| classificacao | str (Obrigatório/Questionável/Supérfluo/N/A) | sim |
| banco_origem | str | sim |
| tipo | str (Despesa/Receita/Transferência Interna/Imposto) | sim |
| mes_ref | str (YYYY-MM) | sim |
| tag_irpf | str ou null | não |
| obs | str | não |

### renda

| Coluna | Tipo |
|--------|------|
| mes_ref | str (YYYY-MM) |
| fonte | str (G4F/Infobase/PJ Vitória/Rendimentos) |
| bruto | float |
| inss | float |
| irrf | float |
| vr_va | float |
| liquido | float |
| banco | str |

### dividas_ativas

| Coluna | Tipo |
|--------|------|
| mes_ref | str |
| custo | str |
| valor | float |
| status | str (Pago/Não Pago/Parcial) |
| vencimento | int |
| quem | str |
| recorrente | bool |
| obs | str |

### inventario

| Coluna | Tipo |
|--------|------|
| bem | str |
| valor_aquisicao | float |
| vida_util_anos | int |
| depreciacao_anual | float |
| perda_mensal | float |

### prazos

| Coluna | Tipo |
|--------|------|
| conta | str |
| dia_vencimento | int |
| banco_pagamento | str |
| auto_debito | bool |

### resumo_mensal (gerada automaticamente)

| Coluna | Tipo |
|--------|------|
| mes_ref | str |
| receita_total | float |
| despesa_total | float |
| saldo | float |
| top_categoria | str |
| top_gasto | str |
| total_obrigatorio | float |
| total_superfluo | float |
| total_questionavel | float |

### irpf

| Coluna | Tipo |
|--------|------|
| ano | int |
| tipo | str (rendimento_tributavel/inss/irrf/despesa_medica/isento/imposto_pago) |
| fonte | str |
| cnpj_cpf | str |
| valor | float |
| mes | str |

### análise

Texto livre com insights gerados por mês.

---

## Categorização

Regras em `mappings/categorias.yaml` (111 regras). Overrides manuais em `mappings/overrides.yaml` (prioridade sobre regex). Tags IRPF em `src/transform/irpf_tagger.py` (21 regras, 5 tipos).

**Ordem de prioridade:**
1. Overrides manuais (overrides.yaml)
2. Regras regex (categorias.yaml)
3. Fallback: `Outros` + `Questionável`

**Classificações válidas:** `Obrigatório`, `Questionável`, `Supérfluo`, `N/A`
- N/A: transferências internas e receitas (não são despesas classificáveis)
- Imposto: sempre `Obrigatório`

**Regra de ouro:** se não reconhecer, marca como `Outros` + `Questionável`. Nunca inventar categoria.

---

## Deduplicação

3 níveis implementados:
1. **UUID** -- Nubank CC tem identificador único. Elimina CSVs duplicados "(1)", "(2)"
2. **Hash** -- `hash(data + local + valor)` para cruzar fontes diferentes. Marca mas não remove
3. **Pares de transferência** -- Saída Itaú = entrada Nubank. Marca como `Transferência Interna`

Transferências entre contas próprias NÃO são gastos.

---

## Detecção de Pessoa

- Bancos do André (Itaú, Santander, C6, Nubank cartão) -> `André`
- Bancos da Vitória (Nubank PF 97737068-1, PJ 96470242-3) -> `Vitória`
- Indeterminado -> `Casal`
- PIX para Vitória = `Transferência Interna`, não gasto

---

## Senhas

PDFs bancários protegidos. Senhas carregadas de `mappings/senhas.yaml` (não rastreado pelo git).
Se o arquivo não existir, perguntar ao usuário.

---

## Workflow Obrigatório

### Antes de implementar
1. Ler `CLAUDE.md` e `GSD.md`
2. Ler a sprint atual em `docs/sprints/`
3. Ler `docs/ARMADILHAS.md`
4. `make lint` para verificar estado atual

### Ao implementar
1. Manter compatibilidade com pipeline existente
2. Testar incrementalmente (`make process` após cada mudança)
3. Verificar acentuação em todo código novo
4. Nunca quebrar as 8 abas do XLSX

### Antes de concluir
1. `make lint` (ruff check + format)
2. `make process` (pipeline completo)
3. `python -m src.utils.validator` (6 checagens de integridade)
4. Verificar dashboard se houver mudanças visuais
5. Commit com mensagem PT-BR no formato `tipo: descrição imperativa`

---

## Convenções

- PT-BR em tudo (código, comentários, outputs)
- Commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- Datas ISO 8601 (YYYY-MM-DD)
- Valores float com 2 casas decimais
- Limite de 800 linhas por arquivo (exceto config e testes)
- Sem `# TODO` ou `# FIXME` inline (criar issue no GitHub)
- Sem nomes pessoais em docstrings

---

## Estrutura do Projeto

```
protocolo-ouroboros/
├── CLAUDE.md                     # Este arquivo
├── GSD.md                        # Onboarding rápido para qualquer IA
├── README.md                     # Documentação pública
├── pyproject.toml                # Dependências Python
├── Makefile                      # 13 targets (help, install, process, dashboard...)
├── install.sh                    # Setup completo (venv + deps + tesseract)
├── run.sh                        # Entrypoint CLI (--mes, --tudo, --inbox, --dashboard, --sync)
├── .env                          # Senhas e paths (no .gitignore)
│
├── data/                         # TUDO no .gitignore
│   ├── raw/{pessoa}/{banco}/     # Arquivos brutos por pessoa e banco
│   ├── processed/                # CSVs intermediários
│   ├── output/                   # XLSX final + relatórios MD
│   └── historico/                # XLSX antigo importado
│
├── src/
│   ├── pipeline.py               # Orquestrador (11 passos)
│   ├── inbox_processor.py        # Detecta, renomeia, move arquivos
│   ├── extractors/               # 7 extratores (nubank, c6, itaú, santander, energia)
│   ├── transform/                # categorizer, normalizer, deduplicator, irpf_tagger
│   ├── load/                     # xlsx_writer (8 abas), relatório (MD)
│   ├── projections/              # cenários financeiros
│   ├── dashboard/                # Streamlit app (6 páginas)
│   ├── obsidian/                 # Sync com vault Obsidian
│   └── utils/                    # logger, pdf_reader, file_detector, validator
│
├── mappings/
│   ├── categorias.yaml           # 111 regras regex
│   ├── overrides.yaml            # Correções manuais
│   ├── metas.yaml                # Metas financeiras
│   └── senhas.yaml               # Senhas PDFs e contas bancárias
│
├── docs/
│   ├── ARCHITECTURE.md           # Diagrama de fluxo ETL
│   ├── ARMADILHAS.md             # Bugs e aprendizados críticos
│   ├── AUDITORIA_SPRINTS.md      # Auditoria sincera de cada sprint
│   ├── MODELOS.md                # Schemas de dados
│   ├── adr/                      # Architecture Decision Records (7)
│   ├── sprints/                  # Documentação de cada sprint (14)
│   └── extractors/               # Auto-documentação de formatos (7)
│
├── scripts/
│   └── pre-commit-check.sh       # ruff + bloqueio de dados sensíveis
│
└── tests/                        # Fixtures sintéticas (Sprint 9)
```

---

## Referências Rápidas

| Recurso | Caminho |
|---------|---------|
| Regras de categorização | `mappings/categorias.yaml` |
| Overrides manuais | `mappings/overrides.yaml` |
| Metas financeiras | `mappings/metas.yaml` |
| Senhas PDFs | `mappings/senhas.yaml` |
| Validador | `python -m src.utils.validator` |
| Pipeline completo | `make process` ou `./run.sh --tudo` |
| Dashboard | `make dashboard` ou `./run.sh --dashboard` |
| Sync Obsidian | `./run.sh --sync` |
| Lint | `make lint` |
| Sprints | `docs/sprints/sprint_NN_*.md` |
| ADRs | `docs/adr/ADR-NN-*.md` |
| Armadilhas | `docs/ARMADILHAS.md` |
| Arquitetura | `docs/ARCHITECTURE.md` |
| Dados faltantes | `DADOS_FALTANTES.md` |

---

## Contexto Ativo

- **Sprints concluídas:** 1 (MVP), 2 (Infra), 4 (Inteligência), 8 (Dashboard v2 Dracula), 13 (Rebranding), 14 (UI/UX)
- **Sprints com código integrado:** 3 (Dashboard v1), 5 (Relatórios), 6 (Obsidian)
- **Próximas sprints:** 09 (LLM), 10 (Grafos), 11 (IRPF), 12 (Vault Final -- absorção CdB)
- **Sprints finais:** 15 (Acentuação), 16 (Dashboard Polish), 17 (Testes CI/CD), 18 (Auditoria)
- **Plano de convergência:** Ouroboros absorve vault ~/Controle de Bordo (plano em .claude/plans/)
- **Transações:** 2.859 (1.214 histórico + 1.645 dados brutos)
- **Cobertura de meses:** 44 (ago/2022 a out/2026)
- **Bancos:** Itaú, Santander, C6, Nubank (André) + Nubank PF/PJ (Vitória)
- **Categorização:** 100% (111 regras + 10 overrides)
- **IRPF tags:** 79 registros em 5 tipos

---

*"O dinheiro é um bom servo, mas um mau mestre." -- Francis Bacon*
