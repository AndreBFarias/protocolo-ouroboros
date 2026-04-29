---
concluida_em: 2026-04-23
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 90
  title: "Pessoa detector por razão social + CNPJ + nome completo (não só CPF literal)"
  touches:
    - path: src/intake/pessoa_detector.py
      reason: "expandir heurística: aceita razão social ('ANDRE DA SILVA BATISTA DE FARIAS'), CNPJ conhecido, nome completo via mappings/pessoas.yaml"
    - path: mappings/pessoas.yaml
      reason: "novo: declara identificadores de André e Vitória (CPF, CNPJ, razão social, aliases)"
    - path: tests/test_intake_pessoa_detector.py
      reason: "+5 testes com fixtures reais (certidão Receita CNPJ, DAS PARCSN com razão social)"
  forbidden:
    - "Quebrar comportamento para CPFs já detectados corretamente"
    - "Hardcoded de pessoa no código -- tudo via YAML"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "./run.sh --inbox-dry"
  acceptance_criteria:
    - "mappings/pessoas.yaml declara identificadores: {pessoa: {cpfs: [...], cnpjs: [...], razao_social: [...], aliases: [...]}}"
    - "pessoa_detector casa razão social 'ANDRE DA SILVA BATISTA DE FARIAS' → 'andre'"
    - "pessoa_detector casa CNPJ 45.850.636 → 'andre' (MEI desativado)"
    - "pessoa_detector casa CNPJ 52.488.753 → 'vitoria' (MEI ativo)"
    - "Fallback 'casal' só se nenhum identificador casar (não default silencioso quando razão social existe)"
    - "Os 19 DAS PARCSN + 3 certidões do inbox Sprint 88 agora vão para 'andre/' em vez de 'casal/'"
    - "Baseline de testes cresce: 1138 → 1143+ passed"
  proof_of_work_esperado: |
    # Antes (estado pós-Sprint 88)
    ls data/raw/casal/impostos/das_parcsn/ | wc -l   # = 19 (errado -- deveria ser andre)
    ls data/raw/casal/documentos/certidoes_receita/ | wc -l  # = 3 (errado)

    # Depois (re-rodar --inbox com arquivos no inbox/ ou via teste)
    # Esperado: pastas casal/ vazias para esses tipos; andre/ populado
```

---

# Sprint 90 — Pessoa detector robusto (razão social + CNPJ + nome completo)

**Status:** BACKLOG
**Prioridade:** P2 (qualidade de dados; afeta categorização IRPF e atribuição de despesas)
**Dependências:** Sprint 70 (adapter), Sprint 88 (regras YAML ajustadas)
**Origem:** achado durante ingestão real 2026-04-24 — 19 DAS PARCSN + 3 certidões explicitamente do André foram para `casal/` porque o pessoa_detector só casa CPF literal

## Problema-raiz

`src/intake/pessoa_detector.py` atual procura CPF literal no conteúdo (pattern `\d{3}\.\d{3}\.\d{3}-\d{2}`). Se encontra CPF do André (051.273.731-22) ou Vitória, retorna a pessoa correspondente. Caso contrário, retorna 'casal'.

Limitações:
- **Certidão Receita CNPJ**: tem `CNPJ: 45.850.636/0001-60 - ANDRE DA SILVA BATISTA DE FARIAS` mas sem CPF → caiu em 'casal'.
- **DAS PARCSN**: tem `45.850.636/0001-60 ANDRE DA SILVA BATISTA DE FARIAS` (razão social explícita) mas sem CPF → caiu em 'casal'.
- **Extrato C6 PDF**: tem `ANDRE DA SILVA BATISTA DE FARIAS • 051.273.731-22` — deveria casar, mas não casou; verificar motivo (talvez ordem de parsing).

Consequência: arquivos que são **claramente** do André ficam em `data/raw/casal/`. Categorização futura (item_categorizer, irpf_tagger) não consegue atribuir corretamente.

## Contexto: Sprint 70 R70-1 previu isso

VALIDATOR_BRIEF.md §130 já documentou a ressalva: "pessoa_detector busca CPF no conteúdo; boleto Sesc não tem CPF, cai em 'casal'". Sprint 90 generaliza a solução — não só para boletos SESC, mas para qualquer documento com razão social ou CNPJ conhecido.

## Escopo

### 90.1 — Criar `mappings/pessoas.yaml`

Registro declarativo dos identificadores de cada pessoa do casal:

```yaml
# mappings/pessoas.yaml -- identificadores únicos para atribuição de pessoa
# Usado por src/intake/pessoa_detector.py (Sprint 90)

pessoas:
  andre:
    cpfs:
      - "051.273.731-22"
    cnpjs:
      - "45.850.636/0001-60"   # MEI desativado (parcelamento ativo)
    razao_social:
      - "ANDRE DA SILVA BATISTA DE FARIAS"
    aliases:   # nomes curtos que aparecem em cupons/recibos
      - "ANDRE FARIAS"
      - "ANDRE DA SILVA"
  vitoria:
    cpfs:
      - "XXX.XXX.XXX-XX"   # a preencher pelo usuário
    cnpjs:
      - "52.488.753/0001-XX"   # MEI ativo (Vitória)
    razao_social:
      - "VITORIA ..."   # a preencher
    aliases:
      - "VITORIA"

# Fallback quando nenhum identificador casa
fallback_pessoa: casal
```

Decisão: `pessoa=casal` continua como fallback quando nenhum identificador casa. Não é erro -- é afirmação de incerteza honesta.

### 90.2 — Refatorar `pessoa_detector`

```python
# src/intake/pessoa_detector.py (pseudo)

def detectar_pessoa(texto: str) -> str:
    config = _carregar_pessoas_yaml()
    for pessoa, ids in config["pessoas"].items():
        # Ordem: CPF > CNPJ > razão social > alias (mais específico → menos)
        for cpf in ids.get("cpfs", []):
            if cpf in texto:
                return pessoa
        for cnpj in ids.get("cnpjs", []):
            # Aceita com/sem "/0001-60" no match (match só na raiz)
            raiz = cnpj.split("/")[0]
            if raiz in texto:
                return pessoa
        for razao in ids.get("razao_social", []):
            if razao.upper() in texto.upper():
                return pessoa
        for alias in ids.get("aliases", []):
            if alias.upper() in texto.upper():
                return pessoa
    return config.get("fallback_pessoa", "casal")
```

### 90.3 — Tests

`tests/test_intake_pessoa_detector.py` ganha 5 testes com fixtures reais:
- `test_detecta_andre_por_cpf` (regression)
- `test_detecta_andre_por_cnpj_mei_desativado`
- `test_detecta_andre_por_razao_social_em_das_parcsn`
- `test_detecta_andre_por_razao_social_em_certidao_receita`
- `test_fallback_casal_quando_nenhum_identificador_casa`

### 90.4 — Re-executar ingestão

Após a mudança, re-rodar `./run.sh --inbox` (ou teste de migração lote) para reposicionar os 19 + 3 + 1 arquivos de `casal/` para `andre/`. Idempotente via `_preservar_original` + hash.

## Armadilhas

- `mappings/pessoas.yaml` contém CPFs/CNPJs sensíveis; **precisa estar no .gitignore** igual `senhas.yaml`. Verificar antes do commit.
- CPF da Vitória e outros dados: Vitória só estão parcialmente documentados (CONTEXTO.md tem CNPJ mas não CPF explícito). Spec pede preenchimento pelo usuário antes de merge.
- Ordem de casamento em pessoa_detector: CPF > CNPJ > razão social. Evita falso-positivo caso dois irmãos tenham nomes similares (não é o caso do casal mas é boa prática).
- Case-insensitive em razão social (alguns PDFs têm tudo MAIÚSCULO, outros capitalizam).

---

*"Quem é identificado pelo nome não precisa ser adivinhado pelo CPF." -- princípio de identificação robusta*
