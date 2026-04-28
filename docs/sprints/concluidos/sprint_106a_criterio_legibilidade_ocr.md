## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 106a
  title: "Refinar criterio de legibilidade OCR (palavras conhecidas em PT-BR + ratio non-letras)"
  prioridade: P2
  estimativa: ~2h
  origem: "Sprint 106 entregou motor de fallback similar mas o criterio _ocr_e_ilegivel atual (chars uteis < 50) não detecta garbage do Tesseract. Em runtime real, 2 cupons-foto retornaram 2610 chars cada (em sua maioria caracteres lixo) e não acionaram o motor"
  touches:
    - path: src/intake/ocr_fallback_similar.py
      reason: "_ocr_e_ilegivel: substituir chars-count por composite (palavras conhecidas + ratio non-letras + comprimento de palavras)"
    - path: mappings/ocr_fallback_config.yaml
      reason: "novos parametros: min_palavras_conhecidas, max_ratio_non_letras"
    - path: tests/test_ocr_fallback_similar.py
      reason: "regressao: texto coerente passa, garbage falha mesmo com >2000 chars"
  forbidden:
    - "Quebrar comportamento atual em testes (limiar default ainda valido para texto coerente curto)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_ocr_fallback_similar.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "_ocr_e_ilegivel devolve True para texto com 2000+ chars onde maioria sao non-alpha (cupom-foto garbage)"
    - "_ocr_e_ilegivel devolve False para texto coerente PT-BR de 100+ chars (extracao limpa)"
    - "Novo helper _contar_palavras_conhecidas usa whitelist de top 200 palavras PT-BR (de, da, do, para, valor, total, R$, etc.)"
    - "Em runtime real: os 2 cupons em data/raw/_conferir/ passam a ser detectados como ilegiveis e Sprint 106 motor pode ser acionado"
  proof_of_work_esperado: |
    .venv/bin/python -c "
    from src.intake.ocr_fallback_similar import _ocr_e_ilegivel
    garbage = 'CI Ma Fat 6 A UND imbacia, usb toa LM CU LOTE 04 DAE 08...' * 50
    assert _ocr_e_ilegivel(garbage, 'cupom_fiscal_foto') is True
    coerente = 'TOTAL DA NOTA: R\\$ 100,00. FORMA DE PAGAMENTO PIX. CNPJ 00.776.574/0160-79.'
    assert _ocr_e_ilegivel(coerente, 'cupom_fiscal_foto') is False
    print('OK')
    "
```

---

# Sprint 106a -- Criterio de legibilidade OCR

**Status:** BACKLOG (P2, criada 2026-04-28 como achado da execução Sprint 106)

## Motivação

Sprint 106 entregou o motor de fallback por arquivo similar, mas o **criterio que decide se OCR e ilegivel** ainda e simples: `chars_uteis < limiar` onde `chars_uteis = sum(c.isalnum())`. Em runtime real:

- Cupom 1 `CUPOM_2e43640d.jpeg`: 2610 chars OCR. Quase tudo garbage (`"CI Ma Fat 6 A UND imbaçia, usb toa LM CU LOTE..."`). Mas `isalnum()` count > 1000 -- considerado legivel.
- Cupom 2 `CUPOM_6554d704.jpeg`: similar.

Resultado: motor da Sprint 106 nunca e acionado para esses dois arquivos, justamente os que mais precisariam.

## Diagnostico empirico

Caracteristicas distintivas de OCR garbage:
- **Ratio non-letras alto**: cupom-foto borrado tem muitos `\\`, `|`, `.`, `(`, `)`, `:` espalhados sem semantica.
- **Palavras curtas (< 3 chars) excessivas**: `CI`, `Ma`, `LM`, `CU`, `Po`, `k`, `E`.
- **Zero palavras conhecidas em PT-BR**: garbage não casa com `de`, `da`, `do`, `para`, `valor`, `total`, `r$`, etc.

OCR coerente:
- Ratio non-letras ~ 0.15-0.25 (espacos + pontuacao normal).
- Maioria de palavras tem >= 3 chars.
- 5+ palavras conhecidas em PT-BR.

## Implementação

### Helper `_contar_palavras_conhecidas`

```python
_PALAVRAS_PT_BR_COMUNS: set[str] = {
    "de", "da", "do", "das", "dos", "para", "com", "em", "no", "na",
    "valor", "total", "pagamento", "forma", "documento", "data", "nota",
    "fiscal", "consumidor", "cnpj", "cpf", "r$", "rs", "r ",
    "loja", "endereco", "produto", "quantidade", "unidade", "preco",
    "compra", "boleto", "vencimento", "beneficiario", "pagador",
    # ... (top 200 do dicionario PT-BR)
}

def _contar_palavras_conhecidas(texto: str) -> int:
    palavras = re.findall(r"\b\w+\b", texto.lower())
    return sum(1 for p in palavras if p in _PALAVRAS_PT_BR_COMUNS)
```

### Novo `_ocr_e_ilegivel` composite

```python
def _ocr_e_ilegivel(texto: str, tipo: str, config: dict | None = None) -> bool:
    cfg = config or _carregar_config()
    if not texto:
        return True

    # Criterio 1 (existente): chars uteis abaixo de limiar
    chars_uteis = sum(1 for c in texto if c.isalnum())
    limiar_chars = cfg.get("limiar_chars_uteis_por_tipo", {}).get(tipo, 50)
    if chars_uteis < limiar_chars:
        return True

    # Criterio 2 (novo): palavras conhecidas em PT-BR
    min_pal = cfg.get("min_palavras_conhecidas_por_tipo", {}).get(tipo, 5)
    if _contar_palavras_conhecidas(texto) < min_pal:
        return True

    # Criterio 3 (novo): ratio non-letras > limite
    chars_total = len(texto)
    chars_non_alpha = sum(1 for c in texto if not c.isalpha() and not c.isspace())
    max_ratio = cfg.get("max_ratio_non_letras_por_tipo", {}).get(tipo, 0.40)
    if chars_total > 100 and (chars_non_alpha / chars_total) > max_ratio:
        return True

    return False
```

### Config `mappings/ocr_fallback_config.yaml` extendida

```yaml
min_palavras_conhecidas_por_tipo:
  cupom_fiscal_foto: 5
  recibo_nao_fiscal: 3
  default: 5

max_ratio_non_letras_por_tipo:
  cupom_fiscal_foto: 0.40
  default: 0.45
```

## Testes regressivos

1. Garbage com 2000+ chars (90% non-alpha) -> True (ilegivel).
2. Texto coerente curto com `R$ 100,00 TOTAL CNPJ` -> False (legivel).
3. Texto curto vazio -> True (limiar chars existente).
4. Texto coerente longo (NFC-e completa) -> False.
5. Em runtime real (2 cupons em `_conferir/`): `_ocr_e_ilegivel` retorna True para ambos.

## Dependencias

- Sprint 106 (commit `a05ebdb`) entregou motor; esta sprint refina o criterio de ativacao.

---

*"O Tesseract sempre devolve algo; cabe a nos saber quando esse algo não e nada." -- principio do criterio honesto*
