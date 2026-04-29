---
concluida_em: 2026-04-23
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 33
  title: "Resumo Mensal Narrativo: LLM transforma diagnóstico em texto legível"
  touches:
    - path: src/load/narrativa.py
      reason: "novo módulo que gera YYYY-MM_narrativa.md a partir do diagnóstico e histórico"
    - path: src/load/relatorio.py
      reason: "dispara narrativa apenas se NARRATIVA_LLM_HABILITADA=1"
    - path: src/llm/prompts/narrativa_mensal.md
      reason: "prompt versionado com frontmatter e bloco fixo compatível com prompt caching"
  n_to_n_pairs:
    - [src/load/narrativa.py, src/llm/prompts/narrativa_mensal.md]
    - [src/load/narrativa.py, src/load/relatorio.py]
  forbidden:
    - src/transform/  # narrativa é consumo de dados, nunca altera classificação
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: "NARRATIVA_LLM_HABILITADA=1 ./run.sh --mes 2026-03"
      timeout: 180
  acceptance_criteria:
    - "data/output/YYYY-MM_narrativa.md gerado para 2026-03 e 2026-04"
    - "Todo valor R$ citado na narrativa bate com tabela do diagnóstico; inconsistência aborta com ValueError"
    - "Narrativa cita >= 3 insights específicos baseados em flags/outliers do diagnóstico"
    - "Prompt caching ativo: bloco fixo >90% reutilizado entre meses"
    - "Default off: sistema funciona sem ANTHROPIC_API_KEY"
    - "Custo mensal < $0.30"
    - "Acentuação PT-BR correta e zero emojis"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 33 -- Resumo Mensal Narrativo: LLM transforma diagnóstico em texto legível

**Status:** PENDENTE
**Data:** 2026-04-18
**Prioridade:** MÉDIA
**Tipo:** Feature
**Dependências:** Sprint 21 (Relatório Diagnóstico), Sprint 31 (Infra LLM)
**Desbloqueia:** Sprint 36 (Métricas IA)
**Issue:** --
**ADR:** --

---

## Como Executar

**Comandos principais:**
- `make lint`
- `NARRATIVA_LLM_HABILITADA=1 ./run.sh --mes 2026-03` -- gera narrativa do mês
- `make process` -- gera diagnósticos e narrativas em batch quando env habilitada

### O que NÃO fazer

- NÃO deixar habilitado por padrão: env var `NARRATIVA_LLM_HABILITADA` controla.
- NÃO inventar números: prompt proíbe explicitamente; validação pós-geração aborta.
- NÃO alterar classificação ou categoria no fluxo da narrativa: puramente consumo.
- NÃO mexer no relatório diagnóstico da Sprint 21: narrativa é arquivo novo.

---

## Problema

O `YYYY-MM_diagnostico.md` da Sprint 21 entrega dados estruturados (tabelas, flags, top outliers), mas ainda exige leitura técnica. Para o André, leitor casual, a evolução do mês continua opaca.

Uma camada de narrativa acima do diagnóstico resolve isso:

- Converte tabelas em parágrafos legíveis.
- Destaca o que mudou em relação aos 12 meses anteriores.
- Mantém ancoragem obrigatória em números reais (nenhum LLM hallucinando valor).

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Relatório diagnóstico | `src/load/relatorio.py` | Gera `YYYY-MM_diagnostico.md` com flags, outliers, comparativo 3 meses |
| Relatório descritivo | `src/load/relatorio.py` | Gera `YYYY-MM_relatorio.md` (retrocompatível) |
| Infra LLM | `src/llm/*` | Provedor, cache, schemas, cost_tracker (Sprint 31) |
| XLSX consolidado | `data/output/extrato_consolidado.xlsx` | Fonte de 12 meses de contexto histórico |

---

## Implementação

### Fase 1: prompt versionado com bloco fixo

**Arquivo:** `src/llm/prompts/narrativa_mensal.md`

```
---
versao: "1.0.0"
modelo_recomendado: "claude-opus-4-7"
custo_estimado_usd_por_mes: 0.25
---

Você é um analista financeiro pessoal que redige resumos mensais curtos.

Princípios invioláveis:
- TODO número citado (R$, %, unidades) DEVE vir do diagnóstico estruturado abaixo.
- Se um dado não aparece na entrada, escreva "dado não disponível". Nunca adivinhe.
- Tom: direto, sem floreio, sem emoji.
- Tamanho: 400-600 palavras.

Estrutura:
1. Abertura com saldo do mês e como se compara ao trimestre.
2. Três insights específicos escolhidos entre flags (NOVO/ALTA/SUMIU) e top outliers.
3. Comentário sobre metas (se a seção estiver presente).
4. Fechamento com uma recomendação prática baseada em padrão observado.

Input abaixo: diagnóstico completo do mês + contexto de 12 meses.
```

Bloco fixo (princípios + estrutura) é versionado e reutilizado entre meses para ativar prompt caching.

### Fase 2: módulo `narrativa.py`

**Arquivo:** `src/load/narrativa.py`

```python
def gerar_narrativa(mes_ref: str) -> Path | None:
    if not env_habilitada():
        logger.info("narrativa: NARRATIVA_LLM_HABILITADA=0, pulando")
        return None
    diagnostico = ler_diagnostico(mes_ref)
    contexto = montar_contexto_12_meses(mes_ref)
    prompt_fixo = carregar_prompt_fixo()  # bloco estático cacheado
    payload = {"diagnostico": diagnostico, "contexto": contexto}
    resposta = provedor.chamar(prompt_fixo, payload, versao_prompt)
    validar_ancoragem_numerica(resposta, diagnostico)  # aborta se inventado
    caminho = Path(f"data/output/{mes_ref}_narrativa.md")
    caminho.write_text(resposta, encoding="utf-8")
    return caminho
```

### Fase 3: validação pós-geração

**Arquivo:** `src/load/narrativa.py`

```python
VALOR_REGEX = re.compile(r"R\$\s?([\d\.,]+)")

def validar_ancoragem_numerica(texto: str, diagnostico: str) -> None:
    valores_narrativa = set(_normalizar(v) for v in VALOR_REGEX.findall(texto))
    valores_diagnostico = set(_normalizar(v) for v in VALOR_REGEX.findall(diagnostico))
    fora = valores_narrativa - valores_diagnostico
    if fora:
        raise ValueError(f"narrativa cita valores não presentes no diagnóstico: {fora}")
```

Se algum valor R$ da narrativa não aparece no diagnóstico, aborta.

### Fase 4: integração no pipeline

**Arquivo:** `src/load/relatorio.py`

Após gerar diagnóstico, chama `narrativa.gerar_narrativa(mes_ref)` se env habilitada. Nunca bloqueia o pipeline: falha na narrativa vira warning, não crash.

### Fase 5: prompt caching

**Arquivo:** `src/llm/provider.py`

Garantir que a chamada use `cache_control` no bloco fixo (princípios + estrutura). Só o payload (diagnóstico do mês + contexto) varia, então >90% dos tokens de input ficam em cache entre execuções.

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A33.1 | Narrativa genérica sem insight específico | Prompt exige >= 3 insights baseados em flags/outliers reais; auditoria manual nos 2 primeiros meses |
| A33.2 | Prompt caching quebra se texto fixo varia | Versionar em `narrativa_mensal.md` com frontmatter; leitura binária-equivalente entre runs |
| A33.3 | Validação regex perde números percentuais | Estender regex para `%` também; cobrir formatos `R$ 1.234,56` e `R$ 1234.56` |
| A33.4 | Inclusão em pipeline principal quebra `make process` se API offline | Try/except com warning; falha é não-fatal |
| A33.5 | Custo acumulado sobe se cada mês gera 2x (regenerar manualmente) | Cache de conteúdo por `hash(diagnostico)`: mesmo input não gera nova chamada |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] `make lint` passa sem erros
- [ ] `data/output/2026-03_narrativa.md` e `2026-04_narrativa.md` gerados
- [ ] Auditoria manual confirma: 0 números inventados, >= 3 insights específicos
- [ ] Tokens de input cacheados >= 90% na 2ª execução do mesmo mês
- [ ] Sistema sem `ANTHROPIC_API_KEY` pula narrativa e continua funcional
- [ ] Custo mensal registrado em `llm_costs.jsonl` < $0.30

---

## Verificação end-to-end

```bash
make lint
NARRATIVA_LLM_HABILITADA=1 ./run.sh --mes 2026-03
NARRATIVA_LLM_HABILITADA=1 ./run.sh --mes 2026-04
ls data/output/*_narrativa.md
tail -n 5 data/output/llm_costs.jsonl
```

---

*"O que sabemos é uma gota; o que ignoramos é um oceano." -- Isaac Newton*
