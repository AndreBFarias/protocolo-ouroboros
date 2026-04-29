---
concluida_em: 2026-04-23
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 82
  title: "Canonicalizer: variantes curtas do casal + conta-espelho de cartão"
  touches:
    - path: mappings/contas_casal.yaml
      reason: "adicionar seção 'nomes_variantes' com tokens parciais + contexto bancário"
    - path: src/transform/canonicalizer_casal.py
      reason: "novo modo variantes_curtas(descricao) que casa 'Vitória' + marcador Itaú, 'Andre Silva Batista Farias' sem 'DA', etc."
    - path: src/extractors/nubank_cartao.py
      reason: "emitir contraparte virtual em PAGAMENTO DE FATURA (gera TI-espelho)"
    - path: src/extractors/c6_cartao.py
      reason: "idem"
    - path: src/extractors/santander_cartao.py
      reason: "idem"
    - path: tests/test_canonicalizer_variantes.py
      reason: "testes para as ~280 linhas de abril/2026 que hoje viram Despesa indevidamente"
  n_to_n_pairs:
    - ["nomes_variantes YAML", "canonicalizer_casal.variantes_curtas"]
  forbidden:
    - "Afrouxar o matcher canônico e_transferencia_do_casal (ele deve continuar rigoroso)"
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_canonicalizer_variantes.py tests/test_transferencia_interna.py -v"
      timeout: 60
    - cmd: ".venv/bin/python scripts/smoke_aritmetico.py --strict"
      timeout: 30
  acceptance_criteria:
    - "Descrição 'PIX TRANSF Vitória09/04' (Itaú, forma abreviada) é classificada como Transferência Interna"
    - "Descrição 'ANDRE SILVA BATISTA FARIAS' (sem 'DA') casa canonicalizer via nomes_variantes"
    - "Descrições genéricas como 'ANDRE BARATA' continuam NÃO casando (zero regressão vs Sprint 68)"
    - "Contraparte virtual de PAGAMENTO DE FATURA cria linha TI-espelho no extrato, permitindo pareamento completo"
    - "Taxa de órfãos TI cai de 72% para <50% sem afrouxar matcher canônico"
    - "Receita abril/2026 cai de R$ 15.622 (atual) para <R$ 13.000 (real = salário + rendimentos + reembolsos + PJ legítimos)"
  proof_of_work_esperado: |
    .venv/bin/python <<'EOF'
    from src.transform.canonicalizer_casal import variantes_curtas
    assert variantes_curtas("PIX TRANSF Vitória09/04", banco_origem="Itaú") is True
    assert variantes_curtas("ANDRE SILVA BATISTA FARIAS", banco_origem="Nubank") is True
    assert variantes_curtas("ANDRE BARATA", banco_origem="Nubank") is False
    assert variantes_curtas("DEIVID DA SILVA ALVES SANTANA", banco_origem="Nubank") is False
    print("OK")
    EOF
    .venv/bin/python scripts/smoke_aritmetico.py --strict
```

---

# Sprint 82 — Canonicalizer variantes curtas + conta-espelho

**Status:** BACKLOG
**Prioridade:** P1
**Dependências:** Sprints 55, 56, 67, 68, 68b (base completa de classificação)
**Issue:** SMOKE-M68b-A
**ADR:** --

## Problema

Achado 68b-A registrado pelo executor-sprint 68b:

> ~280 transações em abril/2026 com descrições como `"PIX TRANSF Vitória09/04"` (Itaú usa forma abreviada) ou `"ANDRE SILVA BATISTA FARIAS"` (sem "DA") NÃO casam `mappings/contas_casal.yaml`, caem como Receita/Despesa em vez de Transferência Interna.

Evidência:
- Receita abril/2026 real: R$ 15.622 (ante Sprint 55: R$ 7.963; ante fix 68b: reclassificou 316 TIs mas ainda tem ~280 que deveriam ser TI).
- Top candidatos suspeitos:
  - `PIX TRANSF Vitória09/04` = R$ 2.000 (TI provável)
  - `ANDRE SILVA BATISTA FARIAS` = R$ 2.000 (TI provável — falta "DA" no meio)
  - `PIX QRS NU PAGAMENT11/04` = R$ 3.301 (ambíguo — pode ser recebimento PJ legítimo ou TI)

Sprint 68 deliberadamente usou matcher rigoroso (word-boundary + nome completo) pra zerar falsos-positivos. Isso foi correto. Agora precisamos de um SEGUNDO nível: matcher permissivo CONDICIONADO a contexto (marcador bancário, combinação de tokens).

## Implementação

### Fase 1 — Ampliar `contas_casal.yaml`

```yaml
andre:
  cpf: "<CPF_ANDRE>"
  nomes_aceitos:
    - "ANDRE DA SILVA BATISTA DE FARIAS"
    - "ANDRE DA SILVA"
    - "ANDRE FARIAS"
  # NOVO: variantes curtas que só casam em contexto específico
  nomes_variantes:
    - tokens: ["ANDRE", "SILVA", "BATISTA"]
      min_matches: 3              # precisa bater ao menos 3 tokens
      bancos: ["Nubank", "Itaú", "C6", "Santander"]
    - tokens: ["ANDRE", "FARIAS"]
      min_matches: 2
      bancos: ["Nubank", "Itaú"]
      marcadores: ["PIX", "TRANSF", "TED"]  # ao menos 1 marcador na descrição

vitoria:
  cpf: "<CPF_VITORIA>"
  nomes_aceitos:
    - "VITORIA MARIA SILVA DOS SANTOS"
    - "VITORIA MARIA"
  nomes_variantes:
    - tokens: ["Vitória"]           # só Vitória é pouco
      min_matches: 1
      bancos: ["Itaú"]              # mas é aceito SE vier pelo Itaú
      marcadores: ["PIX TRANSF", "TRANSF"]
      data_no_texto: true           # casa se tem DD/MM na mesma linha
```

### Fase 2 — `variantes_curtas(descricao, banco_origem)`

```python
def variantes_curtas(descricao: str, banco_origem: str) -> bool:
    """Nível 2: matcher permissivo condicionado a contexto bancário.
    
    Só retorna True se passar PELO MENOS UMA regra variante. Jamais
    retorna True se e_transferencia_do_casal() já retornou (evita dupla-contagem).
    """
    config = _load_yaml("mappings/contas_casal.yaml")
    desc_upper = _normalize_nfd(descricao.upper())
    for pessoa in ("andre", "vitoria"):
        for regra in config[pessoa].get("nomes_variantes", []):
            if banco_origem not in regra["bancos"]:
                continue
            tokens_hit = sum(1 for t in regra["tokens"] if t.upper() in desc_upper)
            if tokens_hit < regra["min_matches"]:
                continue
            if "marcadores" in regra:
                if not any(m.upper() in desc_upper for m in regra["marcadores"]):
                    continue
            if regra.get("data_no_texto") and not re.search(r"\b\d{2}/\d{2}", descricao):
                continue
            return True
    return False
```

### Fase 3 — Integrar no pipeline

Em `normalizer.inferir_tipo_transacao` e extratores:

```python
if e_transferencia_do_casal(descricao):
    return "Transferência Interna"
if variantes_curtas(descricao, banco_origem=banco):
    return "Transferência Interna"
# ... resto
```

### Fase 4 — Conta-espelho de cartão

Para extratores de cartão (`nubank_cartao`, `c6_cartao`, `santander_cartao`), quando detectarem `PAGAMENTO DE FATURA` com valor X:
- Emitir linha virtual no lado cartão: `{data, +X, "PAGAMENTO DE FATURA (espelho)", tipo=Transferência Interna}`
- Isso cria o par que o `deduplicator.marcar_transferencias_internas` precisa (entrada no cartão + saída na conta-corrente).

Benefício: taxa de órfãos cai drasticamente porque hoje ~40% dos órfãos são exatamente esse descasamento (CC tem saída, mas fatura do cartão não aparece como entrada-virtual correspondente).

### Fase 5 — Testes

`tests/test_canonicalizer_variantes.py`:

```python
@pytest.mark.parametrize("desc,banco,esperado", [
    ("PIX TRANSF Vitória09/04", "Itaú", True),
    ("ANDRE SILVA BATISTA FARIAS", "Nubank", True),
    ("ANDRE FARIAS TRANSF", "Nubank", True),
    ("ANDRE BARATA", "Nubank", False),
    ("DEIVID DA SILVA ALVES SANTANA", "Nubank", False),
    ("VITORIA Vitória", "C6", False),  # C6 não está na whitelist de variantes
    ("Vitória", "Itaú", False),         # falta marcador PIX/TRANSF e data
    ("PIX TRANSF Vitória", "Itaú", False),  # falta data no texto
])
def test_variantes_curtas(desc, banco, esperado):
    assert variantes_curtas(desc, banco) is esperado
```

## Armadilhas

| Ref | Armadilha | Como evitar |
|---|---|---|
| A82-1 | Regra muito permissiva reintroduz falsos-positivos | Exigir pelo menos 2 condições (tokens + marcador OU tokens + data) para passar |
| A82-2 | Conta-espelho duplicar valor no total | Marcar espelho com flag `_virtual=True` e deduplicator ignora-a no somatório |
| A82-3 | `Vitória` token único caseia com "Vitória-da-Conquista" (cidade) | Regra exige marcador PIX/TRANSF + data junto |

## Evidências obrigatórias

- [ ] Zero regressão em testes de Sprint 68 (DEIVID/JOAO/JEFFERSON/NAYANE continuam Despesa)
- [ ] Variantes casam os casos reais citados
- [ ] Taxa de órfãos <50% após reprocessamento
- [ ] Receita abril/2026 <R$ 13.000

---

*"Rigor não é sinônimo de rigidez — é saber QUANDO afrouxar." — princípio"*
