## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 66
  title: "Normalização de acentuação e preservação de razão social (S/A, &, pontuação)"
  touches:
    - path: src/transform/normalizer.py
      reason: "extrair_local perde acentuação e corrompe razão social"
    - path: src/transform/canonicalizer_fornecedor.py
      reason: "novo: aplicar heurística de acentuação plausível em nomes de fornecedor"
    - path: mappings/fornecedores_acentos.yaml
      reason: "dicionário de substituições conhecidas (BRASILIA→Brasília, AGENCIA→Agência)"
    - path: tests/test_canonicalizer.py
      reason: "testes com casos reais do extrato"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_canonicalizer.py -v"
      timeout: 60
  acceptance_criteria:
    - "Nomes conhecidos recebem acentuação: 'BRASILIA' → 'Brasília', 'AGENCIA' → 'Agência', 'SERVICO' → 'Serviço', 'RECUPERACAO' → 'Recuperação'"
    - "'Americanas Sa - 0337' preserva como 'Americanas S/A — 0337' OU 'Americanas S.A. (Loja 0337)' quando extrator detecta Americanas"
    - "Substituição respeita lista whitelist — não aplica heurística em strings técnicas (CPF, CNPJ, códigos)"
    - "Dict fornecedores_acentos.yaml tem >=30 substituições comuns"
    - "Idempotente: rodar 2x não muda o resultado"
  proof_of_work_esperado: |
    .venv/bin/python <<'EOF'
    from src.transform.canonicalizer_fornecedor import canonicalizar
    assert canonicalizar("ICANAS S A EM RECUPERACAO JUDICIAL") != "ICANAS S A EM RECUPERACAO JUDICIAL"
    assert "Recuperação" in canonicalizar("ICANAS S A EM RECUPERACAO JUDICIAL")
    assert canonicalizar("00.776.574/0160-79") == "00.776.574/0160-79"  # CNPJ intocado
    print("OK")
    EOF
```

---

# Sprint 66 — Canonicalização de nomes

**Status:** BACKLOG
**Prioridade:** P3
**Issue:** AUDIT-2026-04-21-UX-12 + UX-13

## Problema

CSVs da Nubank (conta PJ / CC) vêm sem acentuação: "BRASILIA", "AGENCIA DE RESTAURANTES ONLINE S.A.", "AMERICANAS S A EM RECUPERACAO JUDICIAL". Dashboard exibe tal e qual. Normalizer atual também perde `S/A`, `.`, pontuação em alguns casos ("Americanas Sa - 0337" em vez de "Americanas S/A — Loja 0337").

## Implementação

### Fase 1 — Dicionário de substituições

`mappings/fornecedores_acentos.yaml`:

```yaml
# Palavras comuns com e sem acento
substituicoes:
  BRASILIA: Brasília
  AGENCIA: Agência
  SERVICO: Serviço
  SERVIÇOS: Serviços
  RECUPERACAO: Recuperação
  PAO: Pão
  SAO: São
  # ... mais 25+
razao_social_mapping:
  ICANAS: Americanas  # quando começa com "ICANAS" é Americanas truncada
  OLETO SESC: Boleto Sesc
```

### Fase 2 — Canonicalizer

`src/transform/canonicalizer_fornecedor.py`:

```python
def canonicalizar(nome: str) -> str:
    if _e_codigo_tecnico(nome):  # CPF, CNPJ, hash
        return nome
    
    for sem_acento, com_acento in SUBSTITUICOES.items():
        nome = re.sub(rf'\b{sem_acento}\b', com_acento, nome, flags=re.IGNORECASE)
    
    # Preservar S/A, S.A.
    nome = re.sub(r'\bSA\b(?![A-Za-z])', 'S/A', nome)
    
    return nome
```

### Fase 3 — Integração no pipeline

Chamar após `extrair_local` em `normalizer.py`:

```python
local = extrair_local(descricao_limpa)
local = canonicalizar(local)
```

## Evidências Obrigatórias

- [ ] Teste com 10 casos reais passa
- [ ] Dashboard mostra "Brasília" em vez de "BRASILIA"
- [ ] "Americanas S/A" preservado

---

*"Linguagem é forma, e forma é identidade." — princípio cultural*
