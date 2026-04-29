---
concluida_em: 2026-04-26
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 96
  title: "Classifier robusto: NFs imagem-only com OCR curto não devem cair em _classificar/"
  prioridade: P0
  estimativa: 2-3h
  origem: "auditoria 2026-04-26 -- inbox/1.jpeg classificou tipo:None mesmo com OCR funcional"
  touches:
    - path: mappings/tipos_documento.yaml
      reason: "regra cupom_fiscal_foto exige termos genericos (NOTA FISCAL + valor + CNPJ)"
    - path: src/intake/classifier.py
      reason: "fallback heuristico quando OCR < 800 chars mas tem CNPJ + RS valor"
    - path: tests/test_classifier_cupons_curtos.py
      reason: "fixtures sinteticas + cupom real anonimizado"
  forbidden:
    - "Bypassar classifier yaml: novas regras devem entrar declarativamente"
    - "Aceitar qualquer JPEG/PNG -- precisa de pelo menos 1 marcador (CNPJ ou 'Nota Fiscal' ou 'CUPOM')"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_classifier_cupons_curtos.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "inbox/1.jpeg (NF do shopping setor comercial sul) deixa de classificar tipo:None e passa a casar 'cupom_fiscal_foto'"
    - "Regra YAML cupom_fiscal_foto ganha alternativa 'OCR-curto' que casa com CNPJ + RS valor + nota_fiscal/cupom como pista"
    - "Pelo menos 5 fixtures sinteticas em tests/ cobrindo: cupom curto OK, cupom curto sem CNPJ rejeitado, cupom longo (regression), JPEG aleatorio rejeitado, PNG legivel mas sem marcadores rejeitado"
    - "Sprint roda com OCR via tesseract local (sem dep externa)"
  proof_of_work_esperado: |
    # Antes
    .venv/bin/python -c "
    from pathlib import Path
    from src.intake.preview import gerar_preview
    from src.intake.registry import detectar_tipo
    from src.intake.orchestrator import detectar_mime
    p = Path('inbox/1.jpeg')
    mime = detectar_mime(p)
    txt = gerar_preview(p, mime) or ''
    d = detectar_tipo(p, mime, txt)
    print(f'Antes: tipo={d.tipo} motivo={d.motivo_fallback}')
    "
    # = Antes: tipo=None motivo='nenhum tipo casou'
    
    # Depois (apos fix)
    [mesmo teste]
    # = Depois: tipo=cupom_fiscal_foto motivo=None match_mode=ocr_curto
```

---

# Sprint 96 -- Classifier robusto para cupons curtos

**Status:** BACKLOG (P0, criada 2026-04-26)
**Origem:** Auditoria 2026-04-26 -- supervisor postou 4 NFs novas no inbox; 1.jpeg (NF shopping setor comercial sul, R$ 254,51 cartao debito) classificou `tipo: None` mesmo com OCR extraindo 534 chars com palavras "Nota Fiscal", "Cartao Debito", CNPJ explicito.

## Motivação

OCR funciona. Conteúdo eh rico. Mas regra YAML do `cupom_fiscal_foto` em `mappings/tipos_documento.yaml` exige marcadores especificos (provavelmente "CUPOM FISCAL" ou "DANFE" ou "NFC-E") que NF-curta de cartao em estabelecimento generico não tem.

Resultado: NFs validas vao para `_classificar/` e o usuario nem sabe. Esse cenario eh exatamente "o sistema renomeia, organiza, classifica" que o supervisor pediu -- e quebra silenciosamente em casos comuns.

## Escopo

### Fase 1 -- Investigar regra atual (30 min)

Ler `mappings/tipos_documento.yaml` entry `cupom_fiscal_foto`. Listar todos os termos usados como marcador.

### Fase 2 -- Adicionar alternativa OCR-curto (1h)

Nova entry no YAML ou expansao da existente:

```yaml
cupom_fiscal_foto:
  prioridade: fallback
  match_mode: any
  mime: ['image/jpeg', 'image/png', 'image/heic']
  regras:
    - tipo: completa  # caminho atual
      requer_todos: ['CUPOM FISCAL', 'CNPJ', 'TOTAL']
    - tipo: ocr_curto  # caminho NOVO
      requer_todos: ['CNPJ', 'R\$']
      requer_qualquer: ['Nota Fiscal', 'CUPOM', 'NFC-E', 'TEF', 'Cartao', 'Debito', 'Credito']
      ocr_minimo: 200
      ocr_maximo: 900
```

### Fase 3 -- Testes sinteticos (1h)

Criar `tests/test_classifier_cupons_curtos.py` com 5 cenarios:
1. Cupom curto OCR=400 chars com CNPJ + "Nota Fiscal" + valor -> casa OCR-curto.
2. Cupom curto OCR=300 chars sem CNPJ -> rejeitado.
3. Cupom longo OCR=1200 chars com "CUPOM FISCAL" -> casa regra completa (regression).
4. JPEG aleatoria sem texto significativo -> rejeitada.
5. PNG legivel mas sem CNPJ ou valor -> rejeitada.

### Fase 4 -- Validação em runtime real

```bash
.venv/bin/python << 'EOF'
from pathlib import Path
from src.intake.preview import gerar_preview
from src.intake.registry import detectar_tipo
from src.intake.orchestrator import detectar_mime
for img in Path('inbox').glob('*.jpeg'):
    mime = detectar_mime(img)
    txt = gerar_preview(img, mime) or ''
    d = detectar_tipo(img, mime, txt)
    print(f'{img.name}: {d.tipo} ({d.match_mode})')
EOF
# Espera: todos os 4 casam (1.jpeg, 2.jpeg, WhatsApp x2)
```

## Armadilhas

- **Risco de falso-positivo:** ampliar a regra demais pode classificar cupons como cupom_fiscal_foto que não são. Por isso `requer_todos: ['CNPJ', 'R\$']` -- mínimo absoluto.
- **OCR ruim eh inerente em foto de celular.** Não tentar 100% recall. Aceitar que 5-10% vai para _classificar/.
- **Glyph-tolerant (Sprint 41).** Regex deve aceitar variacoes (`R$`, `R $`, `R\$`, `RS`).

## Dependencias

- Nenhuma. Pode rodar antes ou depois de Sprint 95 (linking runtime).

---

*"Uma foto de cupom no shopping vale tanto quanto um DANFE formal." -- principio do match-pelo-conteúdo*
