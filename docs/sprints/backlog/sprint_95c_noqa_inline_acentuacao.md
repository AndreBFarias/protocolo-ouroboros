## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 95c
  title: "noqa inline acentuação não suprime palavra dentro de string literal"
  prioridade: P3
  estimativa: ~30min
  origem: "achado colateral ACH95-3 durante execução da Sprint 95 (pré-existente, não introduzido pela 95)"
  touches:
    - path: src/graph/linking.py
      reason: "linha 137 -- string literal com 'parsear' (correto, sem acento) que ruff sinaliza como falso positivo"
    - path: scripts/check_acentuacao.py
      reason: "(opcional) heurística para reconhecer string em arg de logger e ignorar palavras técnicas"
  forbidden:
    - "Mudar o conteúdo da mensagem de erro -- é convenção do log e não afeta usuário"
  tests:
    - cmd: "make lint"
  acceptance_criteria:
    - "ruff não emite mais 'Invalid noqa directive' em src/graph/linking.py:137 (e em outros locais com mesmo padrão)"
    - "check_acentuacao.py continua reconhecendo violações reais em comentários e docstrings"
  proof_of_work_esperado: |
    grep -rn "noqa: accent" src/ | wc -l
    # Antes vs depois: contagem deve permanecer ou cair (sem novos warnings)
    .venv/bin/ruff check src/graph/linking.py 2>&1 | grep -c "Invalid noqa"
    # Esperado: 0
```

---

# Sprint 95c -- noqa inline acentuação

**Status:** BACKLOG (P3, criada 2026-04-26 como sprint-filha da Sprint 95)
**Origem:** Achado colateral ACH95-3. Pré-existente ao baseline -- não introduzido pela Sprint 95. ruff emite `Invalid noqa directive` em ~8 lugares onde supressão de acentuação foi aplicada na linha mas a palavra alvo está dentro de string literal técnica.

## Motivação

Padrão atual:
```python
logger.error("erro ao parsear %s: %s", caminho, erro)  # noqa: accent
```

ruff lê `# noqa: accent` mas não reconhece `accent` como código ruff válido (ruff só conhece `E`, `F`, `B`, `W` etc). Solução simples: mudar para `# noqa` puro (sem código) -- ruff aceita.

OU melhor: refatorar `scripts/check_acentuacao.py` para reconhecer chaves técnicas em strings de log (`parsear`, `descricao` como chave de dict, `total` como nome de campo) e ignorar.

## Escopo

### Fase 1 (10min)
Mapear todos os ~8 sítios com `# noqa: accent` em src/. Listar e categorizar.

### Fase 2 (15min)
Para cada sítio, escolher:
- (a) trocar `# noqa: accent` por `# noqa` (mais simples, ruff aceita).
- (b) refatorar a string para usar palavra com acento (`"erro ao analisar"`).

### Fase 3 (5min)
Rodar `make lint` confirmando que ruff exit 0 sem warning.

## Armadilhas

- **Não trocar o significado da mensagem.** Se "parsear" é jargão técnico aceito, manter. Se for descuido, acentuar.
- **`scripts/check_acentuacao.py` pode ter regra que precisa do código `accent` específico.** Verificar se trocar para `# noqa` puro ainda suprime corretamente.

## Dependências

- Independente. Pode ser feita a qualquer momento em janela livre.

---

*"O ferramental que reclama deve ser configurado, não calado." -- princípio anti-supressão-cega*
