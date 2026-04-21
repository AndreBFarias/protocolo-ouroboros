## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 68
  title: "Fix: falso-positivo em Transferência Interna (60.5% PIX para pessoas externas marcados como TI)"
  touches:
    - path: src/transform/normalizer.py
      reason: "regex de TI casa transferências para terceiros"
    - path: src/transform/deduplicator.py
      reason: "eventual sink; investigar se faz match de par"
    - path: src/extractors/nubank_cc.py
      reason: "REGEX_ANDRE / REGEX_AGENCIA_ANDRE podem estar permissivos"
    - path: tests/test_transferencia_interna.py
      reason: "novos testes regressivos"
    - path: mappings/contas_casal.yaml
      reason: "novo YAML com CPFs/nomes/CNPJs de André e Vitória (contas legítimas)"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_transferencia_interna.py -v"
      timeout: 60
    - cmd: ".venv/bin/python scripts/smoke_aritmetico.py --strict"
      timeout: 30
  acceptance_criteria:
    - "Após reprocessamento, taxa de órfãos em Transferência Interna cai de 60.5% para <5%"
    - "Smoke contrato 'transferencias_internas_batem' passa em strict mode"
    - "mappings/contas_casal.yaml existe com CPF André, CPF Vitória, CNPJs PJ rastreados"
    - "Regex de TI consulta whitelist do YAML em vez de hardcode 'ANDRE'/'VITORIA'"
    - "Transferência para DEIVID/JOAO/JEFFERSON (não casal) vira tipo=Despesa"
  proof_of_work_esperado: |
    .venv/bin/python <<'EOF'
    import pandas as pd
    df = pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato')
    ti = df[df['tipo']=='Transferência Interna']
    # cada linha TI deveria ter par (saída em conta A + entrada em conta B)
    from collections import Counter
    pares = Counter(tuple(sorted([abs(v), m])) for v,m in zip(ti['valor'], ti['mes_ref']))
    orfaos = sum(1 for k,v in pares.items() if v == 1)
    taxa_orfaos = orfaos / max(1, len(pares))
    print(f"Pares TI: {len(pares)}, órfãos: {orfaos} ({taxa_orfaos:.1%})")
    assert taxa_orfaos < 0.05, f"Taxa órfãos {taxa_orfaos:.1%} > 5%"
    EOF
    .venv/bin/python scripts/smoke_aritmetico.py --strict
```

---

# Sprint 68 — Fix falso-positivo Transferência Interna

**Status:** BACKLOG
**Prioridade:** P0
**Dependências:** Sprint 55, 56
**Issue:** SMOKE-M56-3

## Problema

Smoke `contrato_transferencias_internas_batem` reportou 635/1050 transferências internas sem par (60.5%). Drill-down:

```
"Transferência enviada - DEIVID DA SILVA ALVES SANTANA"
"Transferência enviada - Joao Alexandre Vaz Ferreira"
"Transferência enviada - Jefferson Castro Garcia"
```

Todas marcadas como `tipo=Transferência Interna` mas são PIX para pessoas externas. Meta-regra §2 ("filtros sem falso-positivo") violada.

CLAUDE.md §Detecção de Pessoa declara que TI é só André ↔ Vitória.

## Investigação necessária

Antes de fixar, `rg` em:
- `src/transform/normalizer.py:44-54` (padrões de TI)
- `src/extractors/nubank_cc.py:REGEX_ANDRE` e `REGEX_AGENCIA_ANDRE`

Verificar qual regex está casando "DEIVID", "Joao Alexandre" etc. Suspeita: regex genérica demais (ex: `TRANSFERENCIA\s+ENVIADA.*` sem ancorar nome).

## Implementação

### Fase 1 — Whitelist formal

`mappings/contas_casal.yaml` (novo):

```yaml
andre:
  cpf: "XXX.XXX.XXX-XX"  # preencher com CPF real do André
  nomes_aceitos:
    - "ANDRE"
    - "ANDRE DA SILVA"
    - "ANDRE FARIAS"
  contas:
    - {banco: "Itaú", agencia: "6450", conta: "..."}
    - {banco: "Santander", agencia: "...", conta: "..."}
    - {banco: "C6", conta: "..."}
    - {banco: "Nubank", cpf_mask: "***.***.***-XX"}
vitoria:
  cpf: "YYY.YYY.YYY-YY"
  nomes_aceitos:
    - "VITORIA"
    - "VITÓRIA"
    - "VITORIA MARIA"
  contas:
    - {banco: "Nubank PF", conta: "97737068-1"}
    - {banco: "Nubank PJ", conta: "96470242-3"}
```

### Fase 2 — Matcher formal

`src/transform/canonicalizer_casal.py` (novo módulo):

```python
def e_transferencia_do_casal(descricao: str) -> bool:
    """Retorna True SÓ SE a descrição casa explícito com CPF ou nome-completo do casal."""
    config = _load_yaml("mappings/contas_casal.yaml")
    for pessoa, perfil in config.items():
        for nome in perfil["nomes_aceitos"]:
            if re.search(rf"\b{re.escape(nome)}\b", descricao.upper()):
                return True
        if perfil.get("cpf") and perfil["cpf"] in descricao:
            return True
    return False
```

### Fase 3 — Substituir regexes permissivos

Em `src/transform/normalizer.py`:

```python
def inferir_tipo_transacao(valor: float, descricao: str, ...) -> str:
    # ...
    if "TRANSFERENCIA" in desc_upper.upper():
        if e_transferencia_do_casal(descricao):
            return "Transferência Interna"
        # senão cai no default (Despesa se saída, Receita se entrada)
```

### Fase 4 — Reprocessar + testes

```bash
./run.sh --tudo
.venv/bin/pytest tests/test_transferencia_interna.py -v
.venv/bin/python scripts/smoke_aritmetico.py --strict
```

## Armadilhas Conhecidas

| A68-1 | CPFs de André e Vitória precisam ser inseridos no YAML | Usuário preenche manualmente, ou pega do `mappings/senhas.yaml` se documentado |
| A68-2 | Nomes podem vir com e sem acento no CSV bancário | Matcher usa `.upper()` + fuzzy em nomes_aceitos |
| A68-3 | TI legítima entre bancos do mesmo dono (ex: Itaú André → Nubank André) | Deve casar: nome "ANDRE" aparece em ambos os lados |

## Evidências Obrigatórias

- [ ] Taxa de órfãos <5%
- [ ] Smoke strict exit 0 no contrato TI
- [ ] YAML whitelist preenchido
- [ ] Teste com 5 casos: TI legítima André→Vitória, TI entre contas André, PIX externo DEIVID, PIX externo JOAO, PIX com CPF André explícito

---

*"Filtro sem falso-positivo é respeito ao dado." — meta-regra 2*
