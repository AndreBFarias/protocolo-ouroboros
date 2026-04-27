## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 98-1
  title: "Engine de envelope clona PDF inteiro em vez de fatiar paginas"
  prioridade: P2
  estimativa: "2-3h"
  origem: "achado colateral durante execucao da Sprint 98 -- dry-run revelou 13 holerites únicos -> 91 cópias bit-a-bit em pastas bancarias"
  touches:
    - path: src/intake/extractors_envelope.py
      reason: "expandir_pdf_multipage e/ou roteador estao gerando arquivos identicos em vez de paginas"
    - path: src/intake/orchestrator.py
      reason: "branch heterogeneo da Sprint 97 ja revisa, mas pode estar invocado em condicoes onde clona"
    - path: tests/test_envelope_nao_clona_paginas.py
      reason: "regressão com PDF multi-pagina sintético verificando que cada arquivo gerado tem SHA-256 distinto"
  forbidden:
    - "Mover/deletar holerites em data/raw/ -- migração real eh tarefa do --executar da Sprint 98"
    - "Mexer no contrato envelope (originais/<sha8>.pdf preservado)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_envelope_nao_clona_paginas.py tests/test_pdf_heterogeneo_multitype.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Para PDF multi-pagina, cada arquivo derivado tem SHA-256 distinto OU eh marcado como single-page (não split)"
    - "Diagnóstico produzido: por que 13 holerites únicos viraram 91 cópias bit-a-bit (mesmo size 63419 bytes, mesmo SHA-256 integral)"
    - "Fix não introduz regressão na Sprint 97 (page-split heterogeneo + reversao continua funcionando)"
    - "Nenhum arquivo novo em pastas bancarias apos rodar --inbox em conjunto teste"
  proof_of_work_esperado: |
    # Antes (estado atual)
    .venv/bin/python << 'EOF'
    import hashlib
    from pathlib import Path
    pasta = Path('data/raw/andre/itau_cc')
    sha_count = {}
    for pdf in pasta.glob('BANCARIO_ITAU_CC_*.pdf'):
        h = hashlib.sha256(pdf.read_bytes()).hexdigest()[:16]
        sha_count[h] = sha_count.get(h, 0) + 1
    multiplos = {h: c for h, c in sha_count.items() if c > 1}
    print(f"SHAs com >1 cópia: {len(multiplos)}, total clones: {sum(multiplos.values())}")
    EOF
    # Esperado: SHAs com clones identificados
    
    # Depois do fix
    # Rodar inbox processor com PDF holerite mock 
    # SHAs em pastas devem ser únicos
```

---

# Sprint 98-1 -- Engine de envelope clona PDF em vez de fatiar

**Status:** BACKLOG (P2, criada 2026-04-26 como sprint-filha da Sprint 98)
**Origem:** Achado colateral CRITICO durante o dry-run da Sprint 98 (script `migrar_holerites_retroativo.py`).

## Motivação

Dry-run da Sprint 98 reportou 121 propostas de migração -- esperava-se ~37 (13 holerites em pastas bancarias + 24 com nomes brutos). Investigacao revelou:

- 13 holerites únicos por SHA-256 estao presentes em `data/raw/andre/itau_cc/` e `data/raw/andre/santander_cartao/`.
- Cada um aparece em **7 cópias bit-a-bit** (`BANCARIO_ITAU_CC_<sha>.pdf`, `BANCARIO_ITAU_CC_<sha>_1.pdf`, ..., `BANCARIO_ITAU_CC_<sha>_6.pdf`).
- Todos com mesmo `sha256` integral. Mesmo size (63419 bytes para o exemplo).
- Total: 91 cópias bit-a-bit do mesmo conteudo.

Isso indica que **a engine de envelope/page-split, em algum ponto da historia do projeto, gerou clones do PDF inteiro em vez de paginas individuais**. Sprint 97 (page-split heterogeneo) opera APOS o expansao multipage; o bug deve estar no `expandir_pdf_multipage` (Sprint 41d) OU no roteador de envelope (Sprint 41c) OU em uma sprint anterior não identificada.

A Sprint 98 mascara o sintoma (script remove cópias quando aplica `--executar`), mas a engine continua expondo o bug se um novo PDF holerite chegar via `--inbox`. Sprint 98-1 vai a causa raiz.

## Hipoteses a investigar

1. **`expandir_pdf_multipage` não splita.** Pode estar copiando o PDF inteiro N vezes (uma por pagina) em vez de extrair cada pagina. Validar com fixture sintética multi-pagina.
2. **Roteador legado pre-Sprint 41 ainda ativo.** Bug pode ser de uma versão antiga que ja foi corrigida; mas os arquivos atuais são resíduo historico.
3. **Bug no contrato `_envelopes/originais/`.** Algum extrator pode estar lendo `originais/<sha>.pdf` e gravando em pasta canônica varias vezes (uma por iteracao do pipeline).

## Escopo

### Fase 1 -- Diagnóstico (1h)
- Rodar `git log --all -p src/intake/extractors_envelope.py | head -200` para ver historia.
- Validar `expandir_pdf_multipage` com PDF sintético de 4 paginas: cada pagina deve ter SHA distinto.
- Verificar se algum extrator chama o expandir 2x (looping bug).

### Fase 2 -- Fix dirigido (1h)
Conforme hipotese confirmada.

### Fase 3 -- Teste regressivo (30min)
`tests/test_envelope_nao_clona_paginas.py`:
- Fixture: PDF de 3 paginas com texto distinto em cada (`PAGINA 1`, `PAGINA 2`, `PAGINA 3`).
- Rodar `expandir_pdf_multipage`.
- Verificar 3 arquivos com SHA-256 distintos.

### Fase 4 -- Validação em volume real (15min)
- Rodar `--inbox` em conjunto teste com PDF multi-pagina.
- Confirmar que nenhuma cópia bit-a-bit e gerada.

## Armadilhas

- **Sprint 97 (heterogeneidade reversivel):** o branch heterogeneo da Sprint 97 ja faz split tentativo + reversao. Bug deve estar antes do branch heterogeneo, no expandir básico.
- **Idempotencia:** dedupe por hash (Sprint 41 P2.3) deveria ter detectado os clones e não roteado os 6 extras. Ou seja, ha um segundo bug no router.

## Dependências

- Sprint 98 ja em main (commit `835f0a7`). Script de migração mascara o sintoma; esta sprint trata a causa.
- Pode ser feita antes ou depois de rodar `--executar` da 98 -- independente.

---

*"Mascarar sintoma e bom; consertar causa raiz e melhor." -- principio do fix-no-tronco
