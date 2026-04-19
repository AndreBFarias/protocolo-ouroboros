> **ARQUIVADA em 2026-04-19** -- absorvida em 45 (Cupom Térmico Foto -- OCR universal cobre também energia). Conteúdo preservado abaixo para referência histórica.

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 32
  title: "OCR de Energia via Visão do LLM: fallback sobre tesseract"
  touches:
    - path: src/extractors/energia_ocr.py
      reason: "adicionar backend de visão do LLM com fallback para tesseract quando API ausente"
    - path: src/llm/schemas.py
      reason: "adicionar EnergiaOCRResult ao conjunto de schemas Pydantic"
    - path: tests/fixtures/energia_gabarito.csv
      reason: "5 imagens de referência com valor_total, kwh, vencimento, mes_ref corretos"
    - path: tests/test_energia_ocr.py
      reason: "comparar saída do extrator contra gabarito; erro absoluto kWh <= 1, valor <= R$ 0,50"
  n_to_n_pairs:
    - [src/extractors/energia_ocr.py, src/llm/schemas.py]
  forbidden:
    - src/pipeline.py  # pipeline já registra o extrator; não mexer aqui
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_energia_ocr.py -x -q"
      timeout: 120
  acceptance_criteria:
    - "EnergiaOCRResult (Pydantic) com campos valor_total, kwh, vencimento, mes_ref, confianca, revisao_humana"
    - "Backend de visão do LLM usado quando ANTHROPIC_API_KEY presente; fallback tesseract caso contrário"
    - "confianca < 0.85 grava proposição em mappings/proposicoes/YYYY-MM-DD_energia.yaml (nunca XLSX direto)"
    - "Mascaramento de CPF e endereço (bbox crop no rodapé) antes de enviar imagem"
    - "Erro absoluto kWh <= 1, erro valor <= R$ 0,50 em fixture de 5 imagens"
    - "Modo usado (vision/tesseract) registrado em log; fallback silencioso é proibido"
    - "Acentuação PT-BR correta e zero emojis"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 32 -- OCR de Energia via Visão do LLM: fallback sobre tesseract

**Status:** OBSOLETA
**Data:** 2026-04-18
**Prioridade:** MÉDIA
**Tipo:** Refactor
**Dependências:** Sprint 31 (Infra LLM)
**Desbloqueia:** --
**Issue:** --
**ADR:** --

---

## Como Executar

**Comandos principais:**
- `make lint`
- `.venv/bin/pytest tests/test_energia_ocr.py -x -q`
- `./run.sh --tudo` -- pipeline completo com OCR de energia via novo backend

### O que NÃO fazer

- NÃO inventar valor: se confiança < 0.85, vira proposição para revisão humana.
- NÃO escrever direto no XLSX com output do LLM; passar por `mappings/proposicoes/`.
- NÃO permitir fallback silencioso: modo usado (vision/tesseract) precisa aparecer no log.
- NÃO enviar CPF ou endereço para o provedor externo: cropar o rodapé da imagem.

---

## Problema

Armadilha 10 do `CLAUDE.md`: tesseract gera 67% de precisão em leitura de kWh porque o layout do app da concessionária confunde o OCR genérico. Valores em R$ saem 100% corretos, mas o consumo em kWh vem errado em 1 a cada 3 contas.

Sem resolver isso, a aba `dividas_ativas` e o acompanhamento de consumo energético ficam poluídos com dados incorretos ou requerem correção manual mensal.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Extrator energia | `src/extractors/energia_ocr.py` | Lê imagem via pytesseract, extrai valor e kWh |
| Gabarito | `tests/fixtures/energia_gabarito.csv` | Planilha de referência com valores corretos |
| Pipeline | `src/pipeline.py:71-76` | Já registra `ExtratorEnergiaOCR` |
| Schemas LLM | `src/llm/schemas.py` | Pydantic fechado com 4 classes na Sprint 31 |

---

## Implementação

### Fase 1: schema `EnergiaOCRResult`

**Arquivo:** `src/llm/schemas.py`

Adicionar:

```python
from datetime import date
from pydantic import BaseModel, Field

class EnergiaOCRResult(BaseModel):
    valor_total: float = Field(gt=0, lt=10000)
    kwh: int = Field(ge=50, le=5000)
    vencimento: date
    mes_ref: str  # YYYY-MM
    confianca: float = Field(ge=0, le=1)
    revisao_humana: bool = False
```

Faixa de `kwh` impede que LLM leia vírgula como ponto (valores fora da faixa viram erro Pydantic).

### Fase 2: backend de visão

**Arquivo:** `src/extractors/energia_ocr.py`

Duas implementações:

- `_extrair_via_vision(imagem_path: Path) -> EnergiaOCRResult | None` -- usa provedor LLM com capacidade de visão. Injeta prompt instruído a retornar JSON no schema.
- `_extrair_via_tesseract(imagem_path: Path) -> EnergiaOCRResult` -- wrapper do código atual com retorno no mesmo schema.

Roteador:

```python
def extrair(imagem_path: Path) -> EnergiaOCRResult:
    provedor = obter_provedor()
    if provedor is None:
        logger.info("energia_ocr: usando tesseract (sem provedor LLM)")
        return _extrair_via_tesseract(imagem_path)
    try:
        resultado = _extrair_via_vision(imagem_path)
        if resultado is not None:
            logger.info("energia_ocr: usando vision (confianca=%.2f)", resultado.confianca)
            return resultado
    except Exception as exc:
        logger.warning("energia_ocr: vision falhou (%s), caindo em tesseract", exc)
    return _extrair_via_tesseract(imagem_path)
```

### Fase 3: mascaramento de PII na imagem

**Arquivo:** `src/extractors/energia_ocr.py`

Função `_mascarar_rodape(imagem_path: Path) -> Path` que retorna caminho de imagem temporária com o terço inferior (onde geralmente aparece CPF/endereço) pintado de branco. Só a imagem mascarada vai para o provedor externo.

### Fase 4: proposição por baixa confiança

**Arquivo:** `src/extractors/energia_ocr.py`

Se `resultado.confianca < 0.85`, gravar em `mappings/proposicoes/YYYY-MM-DD_energia.yaml`:

```yaml
- arquivo: data/raw/.../conta_energia_abril.png
  resultado_proposto:
    valor_total: 320.45
    kwh: 180
    vencimento: "2026-04-20"
    mes_ref: "2026-04"
    confianca: 0.72
  revisao_humana: true
```

Página "Inteligência Pendente" (Sprint 31) já lê `mappings/proposicoes/*.yaml` e mostra proposição para aprovar/rejeitar.

### Fase 5: gabarito e teste

**Arquivo:** `tests/fixtures/energia_gabarito.csv`

Cinco linhas com imagens reais + valores corretos (valor_total, kwh, vencimento, mes_ref).

**Arquivo:** `tests/test_energia_ocr.py`

Para cada linha do gabarito:

- Chama extrator.
- Verifica `abs(resultado.kwh - gabarito.kwh) <= 1`.
- Verifica `abs(resultado.valor_total - gabarito.valor_total) <= 0.50`.
- Marca com `@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), ...)` os que exigem vision.

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A32.1 | LLM inventa valor quando imagem está borrada | `confianca < 0.85` obriga revisão humana via proposição |
| A32.2 | LLM lê vírgula decimal como ponto (valor 180 vira 1.80) | Pydantic `Field(ge=50, le=5000)` em kWh bloqueia; erro de parse vira exceção |
| A32.3 | Fallback silencioso esconde regressão | `logger.info` registra explicitamente o backend usado |
| A32.4 | Cropping de rodapé corta informações úteis da conta | Cropar apenas o terço inferior; testar visual antes de aprovar |
| A32.5 | Volume anual baixo (~12 imagens) não justifica custo alto | ~$0.04/imagem via vision; orçamento ~$0.50/ano |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [ ] `make lint` passa sem erros
- [ ] `tests/test_energia_ocr.py` passa com 5/5 fixtures (erro dentro das tolerâncias)
- [ ] Log mostra explicitamente se usou `vision` ou `tesseract`
- [ ] Proposição em `mappings/proposicoes/*.yaml` gerada quando confiança < 0.85
- [ ] Imagem enviada ao provedor tem terço inferior mascarado (teste visual)
- [ ] Custo acumulado em 1 mês de uso real < $0.10

---

## Verificação end-to-end

```bash
make lint
.venv/bin/pytest tests/test_energia_ocr.py -v
./run.sh --tudo   # com e sem ANTHROPIC_API_KEY para validar roteador
tail -n 5 data/output/llm_costs.jsonl
```

---

*"A medida do homem é o que ele faz com o poder." -- Pítaco de Mitilene*
