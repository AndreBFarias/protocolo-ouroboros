---
concluida_em: 2026-04-19
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 30
  title: "Base Honesta: testes mínimos para módulos críticos"
  touches:
    - path: tests/test_categorizer.py
      reason: "30 fixtures de descrição cobrindo regex, overrides e fallback N/A"
    - path: tests/test_deduplicator.py
      reason: "três níveis (UUID, hash, pares de transferência)"
    - path: tests/test_irpf_tagger.py
      reason: "21 regras com inputs que devem e não devem casar"
    - path: tests/test_extractors_smoke.py
      reason: "1 smoke test por extrator com fixtures sintéticas"
    - path: tests/fixtures/
      reason: "conjunto sintético de CSV/PDF/XLS mínimos por banco; energia_gabarito.csv já existe"
    - path: tests/conftest.py
      reason: "fixtures compartilhadas (DataFrame mínimo, caminhos relativos)"
    - path: pyproject.toml
      reason: "adicionar pytest, pytest-cov como dev-dependencies se ainda não estiverem"
    - path: Makefile
      reason: "target 'test' roda pytest com --cov"
  n_to_n_pairs:
    - [tests/test_categorizer.py, mappings/categorias.yaml]
    - [tests/test_categorizer.py, mappings/overrides.yaml]
    - [tests/test_irpf_tagger.py, src/transform/irpf_tagger.py]
  forbidden:
    - src/llm/  # testes do supervisor ficam na Sprint 31
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/ -v --cov=src/transform --cov=src/extractors"
      timeout: 300
  acceptance_criteria:
    - "pytest tests/ passa com 0 falhas"
    - "Cobertura em src/transform >= 40%"
    - "Cobertura em src/extractors >= 40%"
    - "tests/test_categorizer.py cobre >=30 cenários"
    - "tests/test_irpf_tagger.py testa inputs positivos E negativos para as 21 regras"
    - "tests/test_deduplicator.py cobre os 3 níveis"
    - "Smoke test existe para cada um dos 8 extratores"
    - "make test funciona e reporta cobertura"
    - "Acentuação PT-BR correta e zero emojis"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 30 -- Base Honesta: testes mínimos para módulos críticos

**Status:** CONCLUÍDA
**Data:** 2026-04-18
**Prioridade:** CRÍTICA
**Tipo:** Infra
**Dependências:** Sprint 22 (Consolidação), Sprint 23 (Verdade nos Dados)
**Desbloqueia:** Sprint 31 (Infra LLM)
**Issue:** --
**ADR:** --

---

## Como Executar

**Comandos principais:**
- `make lint`
- `make test` -- pytest com cobertura
- `.venv/bin/pytest tests/test_categorizer.py -v`
- `.venv/bin/pytest tests/ --cov=src/transform --cov=src/extractors --cov-report=term-missing`

### O que NÃO fazer

- NÃO gerar dados reais em fixtures: usar transações sintéticas, sem CPF/CNPJ verdadeiros.
- NÃO testar UI do dashboard nesta sprint.
- NÃO buscar cobertura total agora; a meta é 40% nos módulos críticos.
- NÃO testar `src/llm/` (objeto da Sprint 31).

---

## Problema

O projeto tem 10.100 linhas, movimenta dinheiro real e a pasta `tests/` só contém `__init__.py`. Isso significa:

- Qualquer refatoração é jogada no escuro.
- Armadilhas históricas (regra regex "CONSULT" casando "consulta médica", Ki-Sabor com duas categorias por valor, Nubank CC com duplicatas "(1)" "(2)") voltam a aparecer porque ninguém as amarra em teste.
- A Sprint 31 (supervisor LLM) vai propor mudanças em `categorias.yaml` e `overrides.yaml` -- sem suíte, não há como validar que a nova regra não quebra as anteriores.

Sprint 16 original (Testes CI/CD) foi absorvida neste §1.4 do plano 30/60/90.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Fixtures de energia | `tests/fixtures/energia_gabarito.csv` | Gabarito OCR existe, usar como referência de formato |
| Categorizador | `src/transform/categorizer.py` | 111 regras regex + overrides + fallback |
| Deduplicador | `src/transform/deduplicator.py` | UUID, hash, pares de transferência |
| IRPF tagger | `src/transform/irpf_tagger.py` | 21 regras em 5 tipos |
| Extratores | `src/extractors/` | 8 extratores (2 Nubank, 2 C6, Itaú, Santander, energia OCR, OFX) |

---

## Implementação

### Fase 1: infra de testes

**Arquivo:** `tests/conftest.py`

- Fixture `df_extrato_minimo` com 20 linhas sintéticas cobrindo cada banco, forma_pagamento e classificação.
- Fixture `tmp_xlsx_path` com `tmp_path` para não poluir `data/`.
- Fixture `categorias_yaml` carregando `mappings/categorias.yaml`.
- Fixture `overrides_yaml` carregando `mappings/overrides.yaml`.

**Arquivo:** `pyproject.toml`

Garantir `pytest>=8`, `pytest-cov>=4` em `[project.optional-dependencies.dev]`.

**Arquivo:** `Makefile`

Adicionar target:

```
test:
	.venv/bin/pytest tests/ -v --cov=src/transform --cov=src/extractors --cov-report=term-missing
```

### Fase 2: tests/test_categorizer.py

**Arquivo:** `tests/test_categorizer.py`

Criar >= 30 cenários cobrindo:

- Cada família de regra em `categorias.yaml` (alimentação, transporte, saúde, moradia, lazer, educação, imposto, transferência, etc.).
- Overrides manuais vs regex (verificar prioridade).
- Fallback: descrição não reconhecida → `Outros` + `Questionável`.
- Armadilha histórica: Ki-Sabor >= R$ 800 = Aluguel; < R$ 800 = Padaria.
- Armadilha histórica: "CONSULT" NÃO casa "consulta médica" (teste negativo explícito).
- Classificação de transferências internas → `N/A`.
- Receita → `N/A`.

Estrutura: `@pytest.mark.parametrize("descricao,valor,esperado", [...])`.

### Fase 3: tests/test_deduplicator.py

**Arquivo:** `tests/test_deduplicator.py`

Cobrir:

- **UUID:** 2 linhas com mesmo `uuid_nubank`, dedup deixa 1.
- **Hash:** 2 linhas com mesma `data + local + valor` de bancos diferentes são marcadas (sinal), não removidas.
- **Pares de transferência:** saída do Itaú + entrada do Nubank com valores opostos e datas próximas → ambas marcadas como `Transferência Interna`.
- Caso negativo: transferências com datas distantes (> 3 dias) NÃO são pareadas.

### Fase 4: tests/test_irpf_tagger.py

**Arquivo:** `tests/test_irpf_tagger.py`

Para cada uma das 21 regras: 1 caso positivo + 1 caso negativo (input que parece mas não deve casar). Exemplo crítico:

- Positivo: `"CONSULT LTDA ME"` → tipo `Serviços Profissionais`.
- Negativo: `"CONSULTA MEDICA DR X"` → NÃO tipo `Serviços Profissionais` (é `Saúde`).

Testar também extração de CNPJ (após Sprint 23): descrição com CNPJ retorna `cnpj_cpf` formatado corretamente; sem CNPJ retorna vazio.

### Fase 5: tests/test_extractors_smoke.py

**Arquivo:** `tests/test_extractors_smoke.py`

Um smoke test por extrator usando fixtures em `tests/fixtures/`:

- `itau_mini.pdf` (pdf protegido com senha conhecida, 3 linhas)
- `santander_mini.pdf` (3 linhas)
- `nubank_cartao_mini.csv` (`date,title,amount`, 3 linhas)
- `nubank_cc_mini.csv` (`Data,Valor,Identificador,Descrição`, 3 linhas)
- `c6_mini.xls` (criptografado com senha conhecida)
- `c6_cc_mini.xls` (idem)
- `energia_mini.png` (imagem pequena, usar gabarito existente)
- `ofx_mini.ofx` (formato OFX sintético)

Cada teste: instancia extrator, chama `extrair(caminho)`, verifica `len(df) == 3` e colunas obrigatórias presentes.

### Fase 6: cobertura e CI local

**Arquivo:** `Makefile` (target `test` adicionado na Fase 1)

Garantir que `make test` falha se cobertura em `src/transform` ou `src/extractors` < 40%. Usar flag `--cov-fail-under=40`.

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A30-1 | Fixtures com dados reais vazam no repositório | Usar valores e nomes sintéticos; `tests/fixtures/README.md` documenta origem |
| A30-2 | PDF Itaú sintético sem senha real não abre | Criar PDF com senha `TEST` e salvar em `tests/fixtures/`; `mappings/senhas.yaml` não deve ser usado nos testes (injetar via fixture) |
| A30-3 | C6 XLS precisa de `msoffcrypto-tool` | Dependência já está no pyproject; se teste falha, adicionar ao CI |
| A30-4 | Testes de regex casam acidentalmente em inputs de controle | Sempre incluir caso negativo explícito; revisar armadilha A5 do CLAUDE.md |
| A30-5 | `--cov-fail-under=40` pode bloquear sprints futuras | Começar em 40; Sprint 34+ aumenta o alvo progressivamente |
| A30-6 | Smoke test de energia depende de tesseract | Marcar com `@pytest.mark.skipif(shutil.which('tesseract') is None, ...)` |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] `make lint` passa sem erros
- [ ] `.venv/bin/pytest tests/ -v --cov=src/transform --cov=src/extractors` retorna 0 falhas
- [ ] Cobertura em `src/transform` >= 40%
- [ ] Cobertura em `src/extractors` >= 40%
- [ ] `tests/test_categorizer.py` tem >= 30 parametrizações
- [ ] `tests/test_irpf_tagger.py` cobre 21 regras (positivo + negativo = 42 testes mínimos)
- [ ] `tests/test_deduplicator.py` cobre 3 níveis
- [ ] `make test` funciona e falha se cobertura cair abaixo de 40%
- [ ] `tests/fixtures/README.md` explica origem dos fixtures

---

## Verificação end-to-end

```bash
make lint
make test
.venv/bin/pytest tests/test_categorizer.py -v
.venv/bin/pytest tests/test_irpf_tagger.py -v
.venv/bin/pytest tests/test_deduplicator.py -v
.venv/bin/pytest tests/test_extractors_smoke.py -v
```

---

*"O que não é testado está quebrado -- você apenas ainda não descobriu." -- Anders Hejlsberg (parafraseado)*
