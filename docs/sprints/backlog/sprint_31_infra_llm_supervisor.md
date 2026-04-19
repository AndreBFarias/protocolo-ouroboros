## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 31
  title: "Infra LLM + Supervisor de Melhoria Contínua (Modo 1)"
  touches:
    - path: pyproject.toml
      reason: "adicionar anthropic>=0.40 e pydantic>=2.0 como dependências opcionais"
    - path: .env.example
      reason: "adicionar ANTHROPIC_API_KEY e LLM_MONTHLY_BUDGET_USD"
    - path: src/llm/__init__.py
      reason: "pacote novo"
    - path: src/llm/provider.py
      reason: "classe abstrata ProvedorLLM + implementação concreta via API externa"
    - path: src/llm/cache.py
      reason: "cache SQLite em data/output/llm_cache.sqlite; chave hash(prompt+input+versao_prompt)"
    - path: src/llm/cost_tracker.py
      reason: "registra tokens, custo, modelo em data/output/llm_costs.jsonl; kill switch por orçamento"
    - path: src/llm/schemas.py
      reason: "Pydantic fechado: SugestaoRegra, SugestaoOverride, SugestaoTagIRPF, AuditoriaClassificacao"
    - path: src/llm/prompts/supervisor_modo1.md
      reason: "prompt versionado em markdown com frontmatter (versao, modelo_recomendado, custo_estimado)"
    - path: src/llm/supervisor.py
      reason: "Modo 1: itera sobre transações Outros/Questionáveis e grava sugestões em mappings/proposicoes/YYYY-MM-DD_HHMM.yaml"
    - path: src/llm/mascarar_pii.py
      reason: "normaliza CPF/CNPJ para placeholders antes de enviar ao provedor"
    - path: mappings/proposicoes/.gitkeep
      reason: "pasta nova, inicialmente vazia"
    - path: src/dashboard/paginas/inteligencia.py
      reason: "lista proposições, André aprova/rejeita por clique"
    - path: src/dashboard/app.py
      reason: "registrar nova página 'Inteligência Pendente'"
    - path: run.sh
      reason: "adicionar flag --supervisor que chama python -m src.llm.supervisor"
    - path: Makefile
      reason: "target 'supervisor' wrap de ./run.sh --supervisor"
    - path: tests/test_llm_mascarar_pii.py
      reason: "garante que CPF/CNPJ nunca sai em claro"
    - path: tests/test_llm_cache.py
      reason: "cache hit evita nova chamada; versão diferente de prompt invalida"
  n_to_n_pairs:
    - [src/llm/supervisor.py, mappings/proposicoes/]
    - [src/llm/cost_tracker.py, .env.example]
    - [src/dashboard/paginas/inteligencia.py, mappings/categorias.yaml]
    - [src/dashboard/paginas/inteligencia.py, mappings/overrides.yaml]
  forbidden:
    - src/transform/irpf_tagger.py  # LLM NUNCA substitui CNPJ extraído determinísticamente
    - src/pipeline.py  # supervisor é comando separado, não entra no pipeline principal
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_llm_mascarar_pii.py -x -q"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_llm_cache.py -x -q"
      timeout: 60
    - cmd: "./run.sh --supervisor --dry-run"
      timeout: 60
  acceptance_criteria:
    - "Sistema inicia e passa em make lint mesmo sem ANTHROPIC_API_KEY configurada"
    - "./run.sh --supervisor --dry-run executa sem chamada externa, só mostra quantas transações entrariam"
    - "Ao ser configurado com chave, ./run.sh --supervisor gera mappings/proposicoes/YYYY-MM-DD_HHMM.yaml"
    - "Custo acumulado <= US$ 2 após 1 semana rodando semanalmente"
    - "Ao menos 1 proposição aprovada via dashboard gera commit local atualizando mappings/categorias.yaml ou mappings/overrides.yaml"
    - "Pydantic valida schema fechado; outputs fora do schema são descartados com logger.warning"
    - "tests/test_llm_mascarar_pii.py verifica que CPF e CNPJ nunca aparecem no payload enviado"
    - "tests/test_llm_cache.py verifica hit/miss por hash(prompt+input+versao)"
    - "Dashboard mostra métricas: % determinístico, custo acumulado, nº de regras adicionadas"
    - "Acentuação PT-BR correta e zero emojis"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 31 -- Infra LLM + Supervisor de Melhoria Contínua (Modo 1)

**Status:** PENDENTE
**Data:** 2026-04-18
**Prioridade:** CRÍTICA
**Tipo:** Feature
**Dependências:** Sprint 30 (Base Honesta)
**Desbloqueia:** Sprints 32, 33, 34, 35, 36
**Issue:** --
**Implementa:** ADR-08 (Supervisor-Aprovador), ADR-09 (Autossuficiência Progressiva)
**ADR:** ADR-08, ADR-09 (criados 2026-04-18)

---

## Como Executar

**Comandos principais:**
- `make lint`
- `make test`
- `./run.sh --supervisor --dry-run` -- simula sem chamar API
- `./run.sh --supervisor` -- roda supervisor em Modo 1
- `make supervisor` -- wrapper do comando acima
- `make dashboard` -- nova página "Inteligência Pendente"

### O que NÃO fazer

- NÃO deixar o provedor LLM escrever direto em `mappings/*.yaml`. Sempre passa por proposição + aprovação humana.
- NÃO substituir CNPJ extraído determinísticamente pelo tagger IRPF por sugestão do LLM.
- NÃO enviar CPF, CNPJ ou senhas em claro ao provedor: mascarar antes.
- NÃO tornar o supervisor parte do pipeline principal; é comando opcional.
- NÃO adicionar dependência nova além de `anthropic` e `pydantic`.
- NÃO confundir o prompt da versão anterior com a atual: versionar em markdown com frontmatter.

---

## Problema

O plano 30/60/90 (§1.6) define que o sistema precisa de um supervisor que propõe regras novas toda vez que encontra transações mal categorizadas (`categoria == "Outros"` ou `classificacao == "Questionável"`). Hoje não há infra LLM alguma: nenhuma dependência, nenhum cache, nenhum controle de custo, nenhum schema.

Sem essa infra, o projeto não aprende -- fica preso em 85% de cobertura determinística e depende de edição manual do YAML para melhorar. Com ela:

1. Supervisor roda em batch (1x/semana).
2. Gera sugestões versionadas em `mappings/proposicoes/`.
3. André aprova/rejeita no dashboard.
4. Cada aprovação vira commit no `mappings/categorias.yaml` ou `mappings/overrides.yaml`.
5. Pipeline determinístico cresce; LLM vai ficando menos necessário (meta: 85% → 98% em 90 dias).

**Princípio arquitetural central:** o provedor LLM propõe, humano aprova, código incorpora. O LLM nunca executa escrita direta em produção.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Categorizador determinístico | `src/transform/categorizer.py` | 111 regras + overrides + fallback |
| Categorias YAML | `mappings/categorias.yaml` | Fonte da verdade das regras |
| Overrides YAML | `mappings/overrides.yaml` | Correções manuais |
| IRPF tagger | `src/transform/irpf_tagger.py` | 21 regras, CNPJ via regex (Sprint 23) |
| Logger | `src/utils/logger.py` | Rotacionado, sem print |
| Dashboard | `src/dashboard/app.py` | 8 páginas Streamlit, tema Dracula |

---

## Implementação

### Fase 1: dependências e configuração

**Arquivo:** `pyproject.toml`

Adicionar em `[project.optional-dependencies.llm]`:

```toml
[project.optional-dependencies]
llm = [
    "anthropic>=0.40",
    "pydantic>=2.0",
]
```

**Arquivo:** `.env.example`

Adicionar linhas comentadas:

```
# Provedor de IA (opcional: sistema roda sem)
ANTHROPIC_API_KEY=
LLM_MONTHLY_BUDGET_USD=5.00
LLM_MODEL=claude-opus-4-7
```

### Fase 2: pacote `src/llm/`

**Arquivo:** `src/llm/__init__.py`

Exporta `ProvedorLLM`, `obter_provedor()`, `SUPERVISOR_PROMPT_VERSAO`.

**Arquivo:** `src/llm/provider.py`

```python
from abc import ABC, abstractmethod

class ProvedorLLM(ABC):
    @abstractmethod
    def chamar(self, prompt: str, payload: dict, versao_prompt: str) -> dict: ...

class ProvedorAnthropic(ProvedorLLM):
    # usa anthropic.Anthropic(); habilita prompt caching.
    ...

def obter_provedor() -> ProvedorLLM | None:
    # lê ANTHROPIC_API_KEY; se ausente, retorna None (sistema segue sem LLM)
    ...
```

**Arquivo:** `src/llm/cache.py`

SQLite em `data/output/llm_cache.sqlite`. Tabela `cache(hash TEXT PK, resposta_json TEXT, versao_prompt TEXT, created_at TIMESTAMP)`. Chave = `sha256(prompt + payload_json + versao_prompt)`.

Funções: `cache_lookup(hash) -> dict | None`, `cache_put(hash, resposta, versao)`.

**Arquivo:** `src/llm/cost_tracker.py`

Registra em `data/output/llm_costs.jsonl`:

```json
{"ts": "2026-04-18T12:34:56", "modelo": "claude-opus-4-7", "tokens_in": 1024, "tokens_out": 256, "custo_usd": 0.0123}
```

Função `checar_orcamento() -> bool`: soma custos do mês corrente; se ultrapassar `LLM_MONTHLY_BUDGET_USD`, retorna `False` e supervisor pula a chamada com `logger.warning`.

**Arquivo:** `src/llm/schemas.py`

Pydantic fechado (enum `Literal`):

```python
from typing import Literal
from pydantic import BaseModel, Field

class SugestaoRegra(BaseModel):
    tipo: Literal["nova_regra_categoria"]
    evidencia_local: str
    ocorrencias: int = Field(ge=1)
    regra_proposta: str  # regex
    categoria: str
    justificativa: str
    confianca: float = Field(ge=0, le=1)

class SugestaoOverride(BaseModel):
    tipo: Literal["novo_override"]
    local: str
    categoria: str
    classificacao: Literal["Obrigatório", "Questionável", "Supérfluo", "N/A"]
    justificativa: str
    confianca: float

class SugestaoTagIRPF(BaseModel):
    tipo: Literal["nova_regra_irpf"]
    padrao: str
    tipo_irpf: str
    justificativa: str
    confianca: float

class AuditoriaClassificacao(BaseModel):
    tipo: Literal["auditoria"]
    transacao_id: str
    classificacao_atual: str
    classificacao_sugerida: str
    justificativa: str
    confianca: float
```

**Arquivo:** `src/llm/mascarar_pii.py`

Funções `mascarar_cpf(texto)`, `mascarar_cnpj(texto)`, `mascarar_tudo(texto)`. Substitui dígitos por `{CPF_MASKED}` e `{CNPJ_MASKED}`. Usado ANTES de qualquer chamada ao provedor.

### Fase 3: prompt versionado

**Arquivo:** `src/llm/prompts/supervisor_modo1.md`

Frontmatter + corpo:

```
---
versao: "1.0.0"
modelo_recomendado: "claude-opus-4-7"
custo_estimado_usd_por_100_transacoes: 0.08
---

Você é um auditor de regras de categorização financeira. Recebe transações
que o pipeline determinístico classificou como "Outros" ou "Questionável".
Sua tarefa: propor regras novas para mappings/categorias.yaml ou
mappings/overrides.yaml que resolvam os casos de forma reutilizável.

Restrições:
- NUNCA inventar CNPJ ou CPF. Se não vier no input, não tente adivinhar.
- Cada sugestão deve vir com evidência de pelo menos 2 ocorrências.
- Confiança < 0.7 implica descarte.
- Saída em JSON válido contra o schema Pydantic fornecido.

Input: lista de transações mascaradas (CPF/CNPJ já substituídos).
Output: JSON com lista "sugestoes", cada item seguindo um dos quatro schemas.
```

### Fase 4: supervisor

**Arquivo:** `src/llm/supervisor.py`

Fluxo:

1. Carrega XLSX consolidado.
2. Filtra `df[(df.categoria == "Outros") | (df.classificacao == "Questionável")]`.
3. Agrupa por `local` (para achar padrões, não casos únicos).
4. Mascarar PII (`mascarar_pii.mascarar_tudo`).
5. Para cada grupo >= 2 ocorrências: monta payload, consulta cache, se miss chama provedor.
6. Valida saída com Pydantic. Descarta inválidos.
7. Grava `mappings/proposicoes/YYYY-MM-DD_HHMM.yaml`.
8. Registra custo no `cost_tracker`.

Flag `--dry-run`: executa passos 1-4, imprime quantas chamadas seriam feitas, sem contatar provedor.

Entrypoint: `python -m src.llm.supervisor [--dry-run]`.

### Fase 5: dashboard -- página "Inteligência Pendente"

**Arquivo:** `src/dashboard/paginas/inteligencia.py`

Streamlit:

- Lista arquivos em `mappings/proposicoes/*.yaml`.
- Para cada sugestão: mostra evidência (3 exemplos), regra proposta, confiança, justificativa.
- Botões por sugestão: Aprovar / Rejeitar / Adiar.
- **Aprovar:** append no YAML destino (`categorias.yaml` ou `overrides.yaml`), registra commit local com mensagem `feat: incorpora regra aprovada via supervisor (<hash>)`.
- **Rejeitar:** move sugestão para `mappings/proposicoes/rejeitadas.yaml`, guarda hash para não reaparecer.
- **Adiar:** deixa no arquivo original.

Métricas no topo da página:

- % de transações resolvidas só por regra determinística (últimos 30 dias).
- Custo LLM do mês corrente (lendo `llm_costs.jsonl`).
- Nº de regras aprovadas no mês.
- Nº de sugestões pendentes.

**Arquivo:** `src/dashboard/app.py`

Registrar a nova página no menu lateral.

### Fase 6: integração com `run.sh` e Makefile

**Arquivo:** `run.sh`

Nova flag `--supervisor` chama `python -m src.llm.supervisor`. Suporta `--dry-run` passado adiante.

**Arquivo:** `Makefile`

```
supervisor:
	./run.sh --supervisor
```

### Fase 7: testes

**Arquivo:** `tests/test_llm_mascarar_pii.py`

- CPF `123.456.789-01` → `{CPF_MASKED}` (e variantes sem pontuação).
- CNPJ `12.345.678/0001-90` → `{CNPJ_MASKED}`.
- Texto sem PII passa inalterado.
- Teste "nenhum dígito sequencial de 11 ou 14 passa pelo mascarador".

**Arquivo:** `tests/test_llm_cache.py`

- Hit: mesma chave retorna sem chamar provedor (mockar `ProvedorLLM`).
- Miss: chave diferente dispara chamada.
- Versão de prompt diferente invalida cache.

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A31-1 | LLM aluucina CNPJ e contamina aba IRPF | Regra absoluta: tagger IRPF nunca aceita CNPJ vindo do LLM. Sprint 23 já extrai via regex. |
| A31-2 | Custo explode em iteração não controlada | `cost_tracker.checar_orcamento()` barra chamadas quando excede `LLM_MONTHLY_BUDGET_USD` |
| A31-3 | PII vaza pro provedor externo | `mascarar_pii` roda antes de qualquer payload; teste unitário garante |
| A31-4 | Prompt evolui e cache fica incoerente | Chave do cache inclui `versao_prompt` vindo do frontmatter markdown |
| A31-5 | Pydantic enum aberto deixa passar categoria inventada | Usar `Literal[...]` fechado |
| A31-6 | Sugestão rejeitada reaparece na próxima execução | Guardar hash canônico da sugestão em `rejeitadas.yaml`; supervisor pula |
| A31-7 | Aprovação sem revisão leva a regra ruim | Dashboard exige clique individual + 3 exemplos por sugestão |
| A31-8 | Usuário roda sem `anthropic` instalado | `obter_provedor()` retorna `None`; supervisor avisa e sai com código 0 |
| A31-9 | Sincronização N-para-N: nova regra em `categorias.yaml` precisa ser testada contra suíte da Sprint 30 | Dashboard roda `make test` após aprovar antes de commit |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] `make lint` passa sem erros
- [ ] `make test` passa com testes novos de LLM
- [ ] `./run.sh --supervisor --dry-run` roda sem chave de API e imprime contagem
- [ ] `./run.sh --supervisor` (com chave) gera `mappings/proposicoes/*.yaml` válido
- [ ] `data/output/llm_costs.jsonl` recebe entrada por chamada
- [ ] Após 7 dias rodando 1x/semana, custo acumulado <= US$ 2
- [ ] Dashboard "Inteligência Pendente" lista proposições com 3 exemplos cada
- [ ] Aprovar uma sugestão incorpora regra no YAML e cria commit local
- [ ] Rejeitar guarda hash em `rejeitadas.yaml`
- [ ] Testes de mascaramento de PII passam
- [ ] Testes de cache passam
- [ ] ADR novo publicado: "Arquitetura Supervisor-Aprovador"

---

## Verificação end-to-end

```bash
make lint
make test
./run.sh --supervisor --dry-run
# (com ANTHROPIC_API_KEY configurada no .env)
./run.sh --supervisor
ls mappings/proposicoes/
tail -n 5 data/output/llm_costs.jsonl
make dashboard   # navegar até "Inteligência Pendente"
```

---

*"A liberdade começa quando o sistema deixa de precisar de um tutor." -- Ludwig von Mises (parafraseado)*
