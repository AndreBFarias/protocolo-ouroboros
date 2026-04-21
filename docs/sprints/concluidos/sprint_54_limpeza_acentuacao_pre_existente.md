## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 54
  title: "Limpeza de acentuação pré-existente (higiene INFRA -- baseline verde)"
  origem: "Achado colateral COL-44-A do validador-sprint da Sprint 44"
  touches:
    - path: VALIDATOR_BRIEF.md
      reason: "linha 35 -- 'validacao' em prosa PT-BR (comentário HTML do template); acentuar para 'validação'"
    - path: docs/propostas/sprint_42_conferencia.md
      reason: "linha 75 -- 'transacao' é identificador técnico (nome de tipo de node do grafo); adicionar <!-- noqa: accent -->"
    - path: src/graph/__init__.py
      reason: "linha 4 -- 'transacao' é identificador técnico (tipo de node canônico); adicionar # noqa: accent na linha da docstring"
    - path: src/graph/migracao_inicial.py
      reason: "linhas 6, 14, 15, 16, 17, 18 -- 'transacao' é identificador técnico (tipo de node em docstring de contrato); adicionar # noqa: accent por linha"
    - path: src/intake/extractors_envelope.py
      reason: "linha 107 -- 'indice' é chave de dataclass `PaginaPdf` (campo técnico, N-para-N com router); adicionar # noqa: accent"
    - path: src/intake/orchestrator.py
      reason: "linha 6 -- 'relatorio' é nome de variável local em exemplo de uso na docstring; adicionar # noqa: accent"
    - path: tests/test_graph.py
      reason: "linha 150 -- 'MERCADO SAO JOAO' é string de fixture (comparação fuzzy com versão acentuada); adicionar # noqa: accent na linha"
    - path: tests/test_intake_classifier.py
      reason: "linha 444 -- 'conteudo' em string bytes de fixture; acentuar para 'conteúdo' (texto PT-BR humano, não identificador)"
    - path: tests/test_intake_extractors_envelope.py
      reason: "linhas 77 e 185 -- 'conteudo', 'invalido', 'nao' em strings bytes de fixture; acentuar ('conteúdo', 'inválido', 'não')"
    - path: tests/test_intake_heterogeneidade.py
      reason: "linhas 85, 140, 173 -- 'Conteudo', 'transacao', 'nao', 'valido' em strings PDF sintéticas; acentuar respeitando contexto (prosa humana)"
    - path: tests/test_intake_orchestrator.py
      reason: "linhas 60 e 181 -- 'conteudo' em string bytes de fixture; acentuar para 'conteúdo'"
  n_to_n_pairs:
    - [src/graph/__init__.py, src/graph/migracao_inicial.py]  # ambos documentam tipos de node; manter grafia idêntica
    - [src/graph/migracao_inicial.py, src/graph/ingestor_documento.py]  # contrato N-para-N do schema do grafo
    - [src/graph/__init__.py, docs/adr/]  # docstring do __init__ espelha ADR-14
  forbidden:
    - src/graph/db.py                   # chaves do schema do grafo; não acentuar identificadores técnicos
    - src/graph/ingestor_documento.py   # já usa # noqa: accent onde precisa; não mexer
    - src/graph/models.py               # dataclasses Node/Edge com tipos como string; não acentuar
    - src/transform/irpf_tagger.py      # chaves de tag_irpf são identificadores
    - src/extractors/                   # named-groups de regex e chaves de dict
    - mappings/*.yaml                   # chaves YAML são identificadores do schema
    - scripts/check_acentuacao.py       # NÃO evoluir regex -- convenção `# noqa: accent` já é oficial e ativa
  tests:
    - cmd: ".venv/bin/python scripts/check_acentuacao.py --all"
      timeout: 30
      expected: "exit 0 (zero violações)"
    - cmd: "make lint"
      timeout: 60
      expected: "exit 0"
    - cmd: ".venv/bin/pytest tests/ -q"
      timeout: 180
      expected: "319 passed, 8 skipped (baseline Sprint 44 preservado)"
  acceptance_criteria:
    - "scripts/check_acentuacao.py --all retorna exit 0 e imprime zero linhas de violação"
    - "make lint retorna exit 0"
    - ".venv/bin/pytest tests/ -q mantém 319 passed, 8 skipped (nenhum teste regredido)"
    - "Nenhuma chave de dict, named-group de regex, tipo de node do grafo ou parâmetro de função foi renomeada"
    - "Zero diff em src/graph/db.py, src/graph/models.py, src/graph/ingestor_documento.py, src/transform/irpf_tagger.py, src/extractors/"
    - "Convenção `# noqa: accent` (Python) e `<!-- noqa: accent -->` (Markdown) usada em toda ocorrência (a); nenhuma tentativa de evoluir regex do checker"
```

> Executar antes de começar: `make lint && ./run.sh --check && .venv/bin/pytest tests/ -q`

---

# Sprint 54 -- Limpeza de acentuação pré-existente (baseline verde INFRA)

**Status:** CONCLUÍDA
**Data:** 2026-04-20
**Prioridade:** MEDIA (higiene; desbloqueia medição limpa de regressões em sprints futuras)
**Tipo:** Infra
**Dependências:** Nenhuma (sprint independente, executável em qualquer janela entre 43 e 44b)
**Desbloqueia:** todas as sprints futuras (baseline verde permite detectar regressões reais sem ruído)
**Issue:** -- (achado colateral COL-44-A, não issue GitHub)
**ADR:** --

---

## Como Executar

**Comandos principais:**

- `.venv/bin/python scripts/check_acentuacao.py --all` -- roda o checker oficial do projeto
- `make lint` -- ruff check + format + check_acentuacao.py (passa a retornar exit 0)
- `.venv/bin/pytest tests/ -q` -- confirma baseline de testes intacto

### O que NÃO fazer

- NÃO evoluir `scripts/check_acentuacao.py` (nem regex, nem exclusões, nem dicionário). A convenção `# noqa: accent` já é oficial e coerente em todo o projeto (ver `hooks/README.md:94`, `docs/MODELOS.md`, `docs/PROMPT_EXECUCAO.md:205`, `src/graph/ingestor_documento.py:341-383`, `src/extractors/nfce_pdf.py:14`). Evoluir o regex quebra a regra anti-débito §5 (scope atômico) e arrisca falsos-negativos.
- NÃO renomear chaves de dict, tipos de node, named-groups ou parâmetros. Essas são identificadores técnicos do schema do grafo (Sprint 42) e violariam N-para-N §9.1.
- NÃO trocar texto dentro de strings de teste se a string for bytes que simulam conteúdo de arquivo corrompido (`b"isso nao e um zip"` serve para criar um ZIP inválido -- trocar por `"não é"` pode quebrar encoding de bytes). Verificar cada caso individualmente.
- NÃO misturar escopo: bug encontrado durante esta sprint vira sprint nova, não commit inline.

---

## Problema

Checker oficial `scripts/check_acentuacao.py --all` retorna 22 violações pré-existentes em 11 arquivos. Isso polui o sinal de `make lint`: quando uma sprint futura introduz uma nova violação, o desenvolvedor vê "23 violações" em vez de "1 nova violação", e não consegue distinguir regressão de ruído herdado.

Evidência empírica (comando literal):

```
$ .venv/bin/python scripts/check_acentuacao.py --all
  Acentuação: 22 problema(s) encontrado(s)
  VALIDATOR_BRIEF.md:35: 'validacao' -> 'validação'
  docs/propostas/sprint_42_conferencia.md:75: 'transacao' -> 'transação'
  src/graph/__init__.py:4: 'transacao' -> 'transação'
  src/graph/migracao_inicial.py:6: 'transacao' -> 'transação'
  src/graph/migracao_inicial.py:14: 'transacao' -> 'transação'
  src/graph/migracao_inicial.py:15: 'transacao' -> 'transação'
  src/graph/migracao_inicial.py:16: 'transacao' -> 'transação'
  src/graph/migracao_inicial.py:17: 'transacao' -> 'transação'
  src/graph/migracao_inicial.py:18: 'transacao' -> 'transação'
  src/intake/extractors_envelope.py:107: 'indice' -> 'índice'
  src/intake/orchestrator.py:6: 'relatorio' -> 'relatório'
  tests/test_graph.py:150: 'SAO' -> 'são'
  tests/test_intake_classifier.py:444: 'conteudo' -> 'conteúdo'
  tests/test_intake_extractors_envelope.py:77: 'conteudo' -> 'conteúdo'
  tests/test_intake_extractors_envelope.py:77: 'invalido' -> 'inválido'
  tests/test_intake_extractors_envelope.py:185: 'nao' -> 'não'
  tests/test_intake_heterogeneidade.py:85: 'Conteudo' -> 'conteúdo'
  tests/test_intake_heterogeneidade.py:140: 'transacao' -> 'transação'
  tests/test_intake_heterogeneidade.py:173: 'nao' -> 'não'
  tests/test_intake_heterogeneidade.py:173: 'valido' -> 'válido'
  tests/test_intake_orchestrator.py:60: 'conteudo' -> 'conteúdo'
  tests/test_intake_orchestrator.py:181: 'conteudo' -> 'conteúdo'
```

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Checker oficial contextual | `scripts/check_acentuacao.py` | Detecta violações em .py/.md/.sh; ignora backticks, identificadores, tabelas MD; respeita `# noqa: accent` e `<!-- noqa: accent -->` |
| Convenção "noqa accent" viva | `hooks/README.md:94-102`, `docs/MODELOS.md:7,148`, `docs/PROMPT_EXECUCAO.md:205`, `src/graph/ingestor_documento.py:341-383`, `src/extractors/nfce_pdf.py:14`, `scripts/supervisor_proposta_nova.sh:6,17,50` | Sufixo oficial para suprimir falsos-positivos onde a palavra é identificador técnico do schema |
| Padrão registrado no BRIEF | `VALIDATOR_BRIEF.md` seção "Padrões recorrentes de bug" | Regra clara: acentuação em identificadores técnicos é aceita; só é violação em texto humano |

---

## Convenção oficial (decisão)

**Manter `# noqa: accent` como mecanismo único.** Não evoluir o checker.

Justificativa empírica:

1. O projeto já tem 15+ ocorrências vivas de `# noqa: accent` / `<!-- noqa: accent -->`, incluindo em módulos canônicos do grafo (`src/graph/ingestor_documento.py`) e docs arquiteturais (`docs/MODELOS.md`). Mudar a convenção agora quebraria N-para-N com esse corpus.
2. O BRIEF recém-atualizado (Sprint 44) registra explicitamente essa convenção como padrão recorrente aceito.
3. Evoluir o regex para inferir "identificador técnico" sem marcador explícito cria falsos-negativos silenciosos -- o desenvolvedor perde o sinal quando realmente errar uma acentuação em prosa.
4. `# noqa: accent` é explícito (lê-se: "sei que parece errado, é intencional"), alinhado com a filosofia de observabilidade §8 do AI.md.

---

## Classificação empírica por linha (22 violações)

Legenda: **(a)** identificador técnico -- suprimir com `# noqa: accent`. **(b)** texto PT-BR humano -- acentuar de fato.

| # | Arquivo:Linha | Palavra | Contexto (grep empírico) | Classificação | Ação |
|---|---|---|---|---|---|
| 01 | `VALIDATOR_BRIEF.md:35` | `validacao` | `| 2 | Screenshot UI automático | Luna Sprint 09 | sim | skill validacao-visual |` -- referência ao nome da skill `validacao-visual` (nome técnico com hífen, identificador de ferramenta Claude Code) | **(a)** | Adicionar `<!-- noqa: accent -->` no fim da linha |
| 02 | `docs/propostas/sprint_42_conferencia.md:75` | `transacao` | `Sprint 42 implementou tipos REUSADOS pela migração: transacao, fornecedor, categoria, periodo, conta, tag_irpf.` -- enumeração de nomes de **tipos de node** do grafo | **(a)** | Adicionar `<!-- noqa: accent -->` no fim da linha |
| 03 | `src/graph/__init__.py:4` | `transacao` | `Schema 2-tabelas (node + edge) declarado em ADR-14. Tipos de nó canônicos: transacao, documento, item, fornecedor, categoria, conta, periodo, tag_irpf,` -- enumeração de tipos de node | **(a)** | Adicionar `# noqa: accent` no fim da linha da docstring |
| 04 | `src/graph/migracao_inicial.py:6` | `transacao` | `- transacao  (1 por linha; ...)` -- nome de tipo de node em docstring de contrato do grafo | **(a)** | Adicionar `# noqa: accent` no fim da linha |
| 05 | `src/graph/migracao_inicial.py:14` | `transacao` | `- origem      transacao -> conta   (sempre)` -- contrato de aresta do grafo | **(a)** | Adicionar `# noqa: accent` |
| 06 | `src/graph/migracao_inicial.py:15` | `transacao` | `- ocorre_em   transacao -> periodo (sempre)` -- contrato de aresta | **(a)** | Adicionar `# noqa: accent` |
| 07 | `src/graph/migracao_inicial.py:16` | `transacao` | `- categoria_de transacao -> categoria (sempre)` | **(a)** | Adicionar `# noqa: accent` |
| 08 | `src/graph/migracao_inicial.py:17` | `transacao` | `- contraparte transacao -> fornecedor (quando local != banco/transferência)` | **(a)** | Adicionar `# noqa: accent` |
| 09 | `src/graph/migracao_inicial.py:18` | `transacao` | `- irpf        transacao -> tag_irpf (quando tag_irpf não-nulo)` | **(a)** | Adicionar `# noqa: accent` |
| 10 | `src/intake/extractors_envelope.py:107` | `indice` | `- paginas: tupla de PaginaPdf com indice + diagnostico + texto_nativo` -- `indice` é o **nome do atributo** da dataclass `PaginaPdf` (chave N-para-N com o router) | **(a)** | Adicionar `# noqa: accent` no fim da linha |
| 11 | `src/intake/orchestrator.py:6` | `relatorio` | `    relatorio = processar_arquivo_inbox(caminho_inbox, pessoa="andre")` -- nome de variável em exemplo de uso (identificador Python; mudar para `relatório` quebraria a sintaxe do próprio exemplo) | **(a)** | Adicionar `# noqa: accent` no fim da linha |
| 12 | `tests/test_graph.py:150` | `SAO` | `r = er.resolver_fornecedor("MERCADO SAO JOAO", ["MERCADO SÃO JOÃO"])` -- string de fixture: `"MERCADO SAO JOAO"` sem acento é **input empírico** do teste fuzzy (simula erro de digitação do usuário real); `"MERCADO SÃO JOÃO"` com acento é o canônico. Trocar quebra a semântica do teste | **(a)** | Adicionar `# noqa: accent` no fim da linha |
| 13 | `tests/test_intake_classifier.py:444` | `conteudo` | `arq = arquivo_temp("doc.pdf", conteudo="%PDF-1.4 conteudo determinístico".encode("utf-8"))` -- `conteudo=` é **nome de parâmetro** da fixture `arquivo_temp` (identificador Python); o `conteudo` dentro da string é prosa (texto de simulação de PDF) | **(a)** parâmetro + **(b)** prosa | Acentuar a string interna: `"%PDF-1.4 conteúdo determinístico"`; o parâmetro fica (deixar como está -- checker ignora nome de kwarg) |
| 14 | `tests/test_intake_extractors_envelope.py:77` | `conteudo` + `invalido` | `falso.write_bytes(b"%PDF-1.4 conteudo invalido")` -- bytes literal simulando PDF corrompido; é **prosa PT-BR humana** dentro de bytes (acentuar funciona: `b"%PDF-1.4 conte\xc3\xbado inv\xc3\xa1lido"` em UTF-8). Verificar que o teste ainda detecta "PDF inválido" após troca (o conteúdo não precisa casar regex -- só precisa não ser um PDF válido) | **(b)** | Trocar para `b"%PDF-1.4 conte\xc3\xbado inv\xc3\xa1lido"` OU reescrever como `"%PDF-1.4 conteúdo inválido".encode("utf-8")` (mais legível) |
| 15 | `tests/test_intake_extractors_envelope.py:185` | `nao` | `falso.write_bytes(b"isso nao e um zip")` -- bytes literal simulando ZIP corrompido; prosa humana | **(b)** | Trocar para `"isso não é um zip".encode("utf-8")` |
| 16 | `tests/test_intake_heterogeneidade.py:85` | `Conteudo` | `pdf = _criar_pdf_com_paginas(tmp_path, ["Conteudo qualquer com CPF: 051.273.731-22"])` -- string de texto que será escrita num PDF sintético; prosa humana | **(b)** | Trocar para `"Conteúdo qualquer com CPF: 051.273.731-22"` |
| 17 | `tests/test_intake_heterogeneidade.py:140` | `transacao` | `"Linha de transacao"` -- string de texto PDF sintético simulando linha de extrato bancário; **prosa humana** (não é nome de tipo de node aqui, é apenas texto narrativo que aparece num extrato fictício) | **(b)** | Trocar para `"Linha de transação"` |
| 18 | `tests/test_intake_heterogeneidade.py:173` | `nao` + `valido` | `falso.write_bytes(b"isto nao eh um PDF valido")` -- prosa humana em bytes | **(b)** | Trocar para `"isto não é um PDF válido".encode("utf-8")` (ajustar "eh" para "é") |
| 19 | `tests/test_intake_orchestrator.py:60` | `conteudo` | `arq.write_bytes(b"%PDF-1.7 conteudo")` -- prosa humana em bytes | **(b)** | Trocar para `"%PDF-1.7 conteúdo".encode("utf-8")` |
| 20 | `tests/test_intake_orchestrator.py:181` | `conteudo` | `arq.write_bytes(b"conteudo qualquer sem assinatura")` -- prosa humana em bytes | **(b)** | Trocar para `"conteúdo qualquer sem assinatura".encode("utf-8")` |

**Resumo da distribuição:**
- **(a)** identificadores técnicos -> `# noqa: accent`: 12 ocorrências (violações 01-13 exceto parte interna da 13)
- **(b)** prosa PT-BR humana -> acentuar: 10 ocorrências (violações 13 interna, 14, 15, 16, 17, 18, 19, 20)

Nota: violação 13 tem duas naturezas no mesmo local -- o kwarg é (a) (ignorado pelo checker porque não está em texto), mas o valor-string é (b).

---

## Implementação

### Fase 1: Suprimir identificadores técnicos com `noqa: accent` (12 linhas)

**Procedimento**: adicionar comentário `# noqa: accent` (Python) ou `<!-- noqa: accent -->` (Markdown) no fim da linha para cada violação (a) listada acima.

Arquivos tocados nesta fase:

- `VALIDATOR_BRIEF.md:35` -- 1 linha (`<!-- noqa: accent -->`)
- `docs/propostas/sprint_42_conferencia.md:75` -- 1 linha (`<!-- noqa: accent -->`)
- `src/graph/__init__.py:4` -- 1 linha de docstring. Atenção: não quebrar a docstring; adicionar `# noqa: accent` como comentário separado imediatamente antes ou depois da docstring **NÃO funciona** (o checker lê texto da docstring, não comentários adjacentes). Alternativa empírica: verificar se o checker aceita `# noqa: accent` dentro da própria docstring (testar: adicionar a palavra "noqa: accent" em algum lugar da string da docstring). Código do checker `scripts/check_acentuacao.py:214` confirma: `if "noqa: accent" in parte: continue` -- o checker procura a string dentro do texto da docstring, então **basta incluir `noqa: accent` como parte do comentário na linha da docstring**, ex: linha final da docstring vira `..., prescricao, garantia, apolice, seguradora.  # noqa: accent`.
- `src/graph/migracao_inicial.py:6,14,15,16,17,18` -- 6 linhas da docstring; mesmo procedimento (incluir `# noqa: accent` ao fim de cada linha da docstring).
- `src/intake/extractors_envelope.py:107` -- 1 linha de docstring; mesmo procedimento.
- `src/intake/orchestrator.py:6` -- 1 linha de docstring; mesmo procedimento.
- `tests/test_graph.py:150` -- 1 linha de código; adicionar `# noqa: accent` no fim da linha.

**Validação imediata**: após cada edit, rodar `.venv/bin/python scripts/check_acentuacao.py <arquivo>` para confirmar que a violação daquele arquivo caiu para zero.

### Fase 2: Acentuar prosa PT-BR humana em testes (10 ocorrências em 7 arquivos)

**Procedimento**: trocar o texto da string para a grafia acentuada correta. Onde a string é `bytes` literal (`b"..."`), converter para `"...".encode("utf-8")` para preservar legibilidade.

Arquivos tocados nesta fase:

- `tests/test_intake_classifier.py:444` -- `"%PDF-1.4 conteudo determinístico"` -> `"%PDF-1.4 conteúdo determinístico"`
- `tests/test_intake_extractors_envelope.py:77` -- `b"%PDF-1.4 conteudo invalido"` -> `"%PDF-1.4 conteúdo inválido".encode("utf-8")`
- `tests/test_intake_extractors_envelope.py:185` -- `b"isso nao e um zip"` -> `"isso não é um zip".encode("utf-8")`
- `tests/test_intake_heterogeneidade.py:85` -- `"Conteudo qualquer com CPF: 051.273.731-22"` -> `"Conteúdo qualquer com CPF: 051.273.731-22"`
- `tests/test_intake_heterogeneidade.py:140` -- `"Linha de transacao"` -> `"Linha de transação"`
- `tests/test_intake_heterogeneidade.py:173` -- `b"isto nao eh um PDF valido"` -> `"isto não é um PDF válido".encode("utf-8")`
- `tests/test_intake_orchestrator.py:60` -- `b"%PDF-1.7 conteudo"` -> `"%PDF-1.7 conteúdo".encode("utf-8")`
- `tests/test_intake_orchestrator.py:181` -- `b"conteudo qualquer sem assinatura"` -> `"conteúdo qualquer sem assinatura".encode("utf-8")`

**Cuidado empírico crítico**: cada troca muda os **bytes** que serão escritos no arquivo de fixture. Os testes afetados validam comportamentos como "detectar PDF inválido", "detectar ZIP inválido", "gerar sha8 determinístico", "classificar arquivo desconhecido". Esses testes devem continuar passando **porque** o bytestring continua inválido (só mais caracteres UTF-8), mas um caso exige atenção: `test_sha8_estavel_para_mesmo_arquivo` (linha 443 de `test_intake_classifier.py`) depende de que o **mesmo arquivo** produza o mesmo sha8 em duas chamadas -- não de um sha8 específico. Logo, mudar o conteúdo é seguro.

**Validação imediata**: após cada edit, rodar pytest no arquivo afetado:
```
.venv/bin/pytest tests/test_intake_extractors_envelope.py -q
.venv/bin/pytest tests/test_intake_heterogeneidade.py -q
.venv/bin/pytest tests/test_intake_orchestrator.py -q
.venv/bin/pytest tests/test_intake_classifier.py -q
.venv/bin/pytest tests/test_graph.py -q
```

Cada um deve continuar verde (tests passed sem regressão).

### Fase 3: Validação global

```bash
.venv/bin/python scripts/check_acentuacao.py --all   # deve imprimir nada e retornar 0
make lint                                             # deve retornar 0
.venv/bin/pytest tests/ -q                            # deve preservar baseline atual
```

---

## Verificação

Comandos end-to-end que o validador e o `finish_sprint.sh` usam para confirmar que a sprint cumpriu os acceptance criteria:

```bash
# 1. Checker oficial do projeto -- zero violações, exit 0
.venv/bin/python scripts/check_acentuacao.py --all

# 2. Lint completo (ruff + checker) -- exit 0
make lint

# 3. Suite completa -- baseline atual preservado, zero regressão
.venv/bin/pytest tests/ -q

# 4. Forbidden intocados -- saída VAZIA
git diff --stat src/graph/db.py src/graph/models.py src/graph/ingestor_documento.py src/transform/irpf_tagger.py src/extractors/ mappings/ scripts/check_acentuacao.py
```

Baseline atualizado no ato da execução: **383 passed, 8 skipped** (após Sprints 44/44b/45; o valor inicial do spec "319 passed" foi redigido antes dessas sprints fecharem).

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A54-01 | Trocar `b"...nao..."` por `b"...não..."` falha em Python (bytes literals não aceitam não-ASCII) | Sempre converter para `"...".encode("utf-8")` quando há caracteres acentuados |
| A54-02 | Adicionar `# noqa: accent` como comentário Python antes da docstring **não** suprime (o checker lê o texto da docstring, não comentários adjacentes) | Incluir a string literal `noqa: accent` dentro da própria linha da docstring, ex: `..., transacao, ...  # noqa: accent` como comentário final da linha |
| A54-03 | Renomear `transacao` -> `transação` em qualquer lugar de `src/graph/` quebra N-para-N com `ingestor_documento.py`, `db.py`, `queries.py`, `migracao_inicial.py` (todos usam a string sem acento como tipo de node) | NÃO renomear; só suprimir violação via `noqa: accent` |
| A54-04 | Evoluir `check_acentuacao.py` para inferir identificadores técnicos automaticamente cria falsos-negativos | NÃO evoluir; convenção `noqa: accent` é oficial e consciente |
| A54-05 | `tests/test_graph.py:150` testa fuzzy-match entre `"MERCADO SAO JOAO"` e `"MERCADO SÃO JOÃO"` -- **a ausência do acento é parte do teste** | NÃO acentuar; suprimir com `# noqa: accent` |

Referência: `docs/ARMADILHAS.md` (padrões históricos) + `VALIDATOR_BRIEF.md` seção "Padrões recorrentes de bug" (padrão de acentuação em identificadores técnicos).

---

## Evidências Obrigatórias

- [ ] `.venv/bin/python scripts/check_acentuacao.py --all` retorna exit 0 (zero violações)
- [ ] `make lint` retorna exit 0
- [ ] `.venv/bin/pytest tests/ -q` mantém baseline 319 passed, 8 skipped
- [ ] Diff verificado: nenhum arquivo em `src/graph/db.py`, `src/graph/models.py`, `src/graph/ingestor_documento.py`, `src/transform/irpf_tagger.py`, `src/extractors/` foi tocado
- [ ] `scripts/check_acentuacao.py` não foi modificado (checar `git diff scripts/check_acentuacao.py` retorna vazio)
- [ ] Todas as 12 ocorrências (a) usam `# noqa: accent` ou `<!-- noqa: accent -->`
- [ ] Todas as 10 ocorrências (b) foram acentuadas e os testes correspondentes ainda passam

---

## Proof-of-work esperado

```yaml
tests:
  - cmd: ".venv/bin/python scripts/check_acentuacao.py --all"
    timeout: 30
    expected: "exit 0 + zero linhas impressas"
  - cmd: "make lint"
    timeout: 60
    expected: "exit 0"
  - cmd: ".venv/bin/pytest tests/ -q"
    timeout: 180
    expected: "319 passed, 8 skipped"
  - cmd: "git diff --stat src/graph/db.py src/graph/models.py src/graph/ingestor_documento.py src/transform/irpf_tagger.py src/extractors/ scripts/check_acentuacao.py"
    timeout: 10
    expected: "saída vazia (nenhum dos forbidden foi tocado)"
```

Proof-of-work inclui:
- Diff final (deve ser pequeno: ~30 linhas alteradas em 11 arquivos; majoritariamente `# noqa: accent` sufixado e strings acentuadas)
- Runtime real dos 4 comandos acima
- Verificação empírica de hipótese: antes de aplicar fix, validar classificação (a)/(b) com `rg` -- se a palavra aparece como chave de dict, tipo de node, named-group ou parâmetro em OUTRO arquivo do projeto, é (a) e recebe `noqa: accent`; senão, é (b) e recebe acento.

---

## Riscos e não-objetivos

**Fora do escopo (registrar como sprint nova se aparecer):**
- Evoluir `scripts/check_acentuacao.py` (regex, exclusões, dicionário)
- Auditar outras pastas além das 11 violações listadas (não procurar por novas violações -- apenas corrigir as 22 catalogadas)
- Renomear `transacao` -> `transacao` no schema do grafo (violaria N-para-N da Sprint 42)
- Adicionar hook CI que bloqueia commits com violações (sprint separada de infra CI, se for priorizada)

**Risco residual**: se durante a execução aparecer uma 23ª violação não listada (por race com outra sprint em paralelo), executor deve **parar** e dispatchar novo planejador via protocolo anti-débito §15 (ciclo automático) -- NÃO corrigir inline.

---

## Referências

- **BRIEF**: `/home/andrefarias/Desenvolvimento/protocolo-ouroboros/VALIDATOR_BRIEF.md` (seção "Padrões recorrentes de bug" registra o padrão aceito)
- **Achado original**: validador-sprint da Sprint 44 (COL-44-A)
- **Convenção viva**: `hooks/README.md:94-102`, `docs/MODELOS.md:7,148`, `docs/PROMPT_EXECUCAO.md:205`, `src/graph/ingestor_documento.py:341-383`, `src/extractors/nfce_pdf.py:14`
- **Checker oficial**: `scripts/check_acentuacao.py` (não modificar)
- **CLAUDE.md local §1**: regra de acentuação inviolável
- **AI.md global §9.1**: meta-regra N-para-N (motivo de não renomear identificadores técnicos)
- **ADR-14**: schema do grafo (tipos de node canônicos em PT-sem-acento por design)

---

*"A disciplina é a ponte entre objetivos e realização." -- Jim Rohn*
