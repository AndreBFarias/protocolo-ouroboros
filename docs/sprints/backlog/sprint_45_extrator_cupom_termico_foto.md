## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 45
  title: "Extrator de Cupom Fiscal Térmico (foto JPG/PNG/HEIC)"
  touches:
    - path: src/extractors/cupom_termico_foto.py
      reason: "OCR tesseract + heurística de parsing para cupom fiscal fotografado"
    - path: src/extractors/_ocr_comum.py
      reason: "utilitários OCR compartilhados: rotação EXIF, binarização, cache"
    - path: mappings/ocr_cupom_regex.yaml
      reason: "regex por emissor (Mercados, Farmácia, Posto, Americanas) para aumentar recall"
    - path: src/pipeline.py
      reason: "registra extrator"
  n_to_n_pairs:
    - [mappings/ocr_cupom_regex.yaml, src/extractors/cupom_termico_foto.py]
  forbidden:
    - src/extractors/energia_ocr.py  # referência apenas
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_cupom_termico_foto.py -x -q"
      timeout: 120
  acceptance_criteria:
    - ">= 3 fotos de cupom extraídas com recall de itens >= 80%"
    - "Cupom com OCR confidence < 70% vai automaticamente para fallback supervisor"
    - "EXIF rotation respeitado (foto tirada em portrait)"
    - "Grafo recebe Documento tipo=cupom_fiscal + Itens + Fornecedor"
    - "Cache OCR em data/cache/ocr/ evita reprocessar mesma foto"
    - "Acentuação PT-BR correta"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 45 -- Extrator de Cupom Fiscal Térmico

**Status:** PENDENTE
**Data:** 2026-04-19
**Prioridade:** ALTA
**Tipo:** Feature
**Dependências:** Sprint 41 (intake classifica cupom), Sprint 42 (grafo), Sprint 43 (fallback supervisor)
**Desbloqueia:** Análise de consumo diário granular
**Issue:** --
**ADR:** ADR-14, ADR-15

---

## Como Executar

- `./run.sh --tudo`
- `.venv/bin/pytest tests/test_cupom_termico_foto.py -v`

### O que NÃO fazer

- NÃO confiar cegamente em OCR -- sempre calcular confidence
- NÃO duplicar lógica de rotação EXIF (usar `_ocr_comum.py`)
- NÃO substituir o `energia_ocr.py` existente (ele continua específico)

---

## Problema

Cupom fiscal é a principal fonte de granularidade do consumo diário. O usuário tira foto no celular, joga na inbox. Hoje a foto é descartada (Sprint 41 resolve o roteamento, esta aqui faz a extração).

OCR de cupom térmico é desafio real:
- Papel fino, amassa
- Impressão desbotada
- Foto com reflexo, sombra, rotação
- Letras pequenas, tabelas mal alinhadas
- Cada emissor tem layout diferente (Americanas, Drogaria, Supermercado, Posto)

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Extrator energia OCR | `src/extractors/energia_ocr.py` | Referência de uso tesseract + PIL |
| Contracheque OCR | `src/extractors/contracheque_pdf.py` | Fallback OCR pra PDFs |
| Ingestor documento | `src/graph/ingestor_documento.py` (Sprint 44) | Persistência no grafo |
| pytesseract + pypdfium2 | Já em deps | Infra OCR |

## Implementação

### Fase 1: `_ocr_comum.py`

```python
from PIL import Image, ImageOps
import pytesseract

def carregar_imagem_normalizada(caminho: Path) -> Image.Image:
    img = Image.open(caminho)
    img = ImageOps.exif_transpose(img)  # respeita rotação EXIF
    img = img.convert("L")               # escala cinza
    img = ImageOps.autocontrast(img)
    return img

def ocr_com_confidence(img: Image.Image, lang: str = "por") -> tuple[str, float]:
    dados = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
    confidences = [int(c) for c in dados["conf"] if c != "-1"]
    media = sum(confidences) / len(confidences) if confidences else 0.0
    texto = "\n".join(w for w, c in zip(dados["text"], dados["conf"]) if c != "-1" and int(c) > 30)
    return texto, media

def cache_key(caminho: Path) -> str:
    import hashlib
    return hashlib.sha256(caminho.read_bytes()).hexdigest()[:16]
```

Cache em `data/cache/ocr/<hash>.txt` para não reprocessar mesma foto.

### Fase 2: parser do cupom

`_parse_cabecalho_cupom(texto: str) -> dict`:
- CNPJ emissor
- Razão social (primeira linha alfabética)
- Data e hora
- Número do cupom (CCF, COO, SAT)

`_parse_itens_cupom(texto: str) -> list[dict]`:

Regex por linha -- cupom térmico segue padrão `<descricao> <qtd>X<valor_unit> <valor_total>`:

```python
REGEX_ITEM_CUPOM = re.compile(
    r"^\s*(?:\d{3}\s+)?"            # código do produto (opcional)
    r"(?P<descricao>.+?)"
    r"\s+(?P<qtd>\d+(?:,\d+)?)\s*[Xx]\s*"
    r"(?P<valor_unit>\d+,\d{2})"
    r"\s+(?P<valor_total>\d+,\d{2})"
)
```

Layout varia; manter regex especializadas por emissor em `mappings/ocr_cupom_regex.yaml`:

```yaml
emissores:
  americanas:
    identificador: "AMERICANAS"
    regex_item: "^(?P<codigo>\\d+)\\s+(?P<descricao>.+?)\\s+(?P<valor_total>\\d+,\\d{2})"
  mercado_sao_joao:
    identificador: "MERCADO.*SÃO JOÃO"
    regex_item: "..."
```

### Fase 3: fallback supervisor

Se `confidence < 70%` OU `recall < 70%` (comparando total lido vs soma dos itens):

1. Arquivo vai para `data/raw/_conferir/<uuid>/`
2. Proposta criada em `docs/propostas/extracao_cupom/<uuid>.md` com:
   - Foto (link relativo)
   - Texto OCR bruto
   - Itens parseados
   - Texto do supervisor Opus:  "Por favor leia a foto e compare. Proponha correções."
3. Claude Code abre a imagem (via leitura de arquivo) e corrige manualmente; virando proposta aprovada.

### Fase 4: registro no pipeline

Igual Sprint 44.

### Fase 5: testes

Fixtures em `tests/fixtures/cupons/`:
- `cupom_americanas.jpg`
- `cupom_mercado.jpg`
- `cupom_posto.jpg`

Testes:
- `test_cupom_americanas_extrai_5_itens`
- `test_cupom_com_rotacao_exif_reconhece`
- `test_cupom_ilegivel_vai_para_fallback`
- `test_cache_ocr_reusa_resultado`

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A45-1 | OCR confunde "0" e "O", "1" e "l" em valores monetários | Pós-processar valores numéricos substituindo caracteres prováveis |
| A45-2 | Descrição vira "LEITE 1L INT 2X 4,99 9,98" -- qtd detectada errada | Preferir regex que casa "NxV,VV" e validar qtd * unit = total |
| A45-3 | Foto invertida (de cabeça pra baixo) mesmo com EXIF correto | Se texto OCR começa com padrão esperado mas nada casa, rotacionar 180° e retentar |
| A45-4 | Cupom com reflexo -- meio da tabela ilegível | Detectar quebra na sequência numérica e marcar incompleto |
| A45-5 | Tesseract em português lusitano vs brasileiro diferem | Usar sempre `lang="por"` e complementar com `osd` quando orientação incerta |
| A45-6 | Cache OCR não invalida quando foto é re-tirada com mesmo nome | Chave do cache é hash do conteúdo, não do nome |
| A45-7 | HEIC exige pillow-heif; sem ele, falha silenciosa | Import condicional com erro explícito |

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] 3 fixtures extraem com recall >= 80%
- [ ] Fallback supervisor abre proposta corretamente quando confidence baixa
- [ ] Cache em `data/cache/ocr/` reduz tempo na segunda rodada em >= 50%
- [ ] Testes passam
- [ ] Grafo recebe Documento + Items

## Verificação end-to-end

```bash
cp tests/fixtures/cupons/*.jpg data/raw/andre/nfs_fiscais/
./run.sh --tudo

.venv/bin/python -c "
from src.graph.db import GrafoDB
from pathlib import Path
db = GrafoDB(Path('data/output/grafo.sqlite'))
rows = db.conn.execute(\"SELECT COUNT(*) FROM node WHERE tipo='item' AND JSON_EXTRACT(metadata, '\$.origem_tipo')='cupom_fiscal'\").fetchone()
print(f'Itens de cupom extraídos: {rows[0]}')
"

ls data/cache/ocr/  # deve ter arquivos
```

## Conferência Artesanal Opus

**Arquivos originais a ler:**

- Cada foto de cupom em `data/raw/andre/nfs_fiscais/*.jpg` (via leitura visual direta pela sessão)
- Texto OCR cacheado em `data/cache/ocr/<hash>.txt`
- Query SQL dos itens extraídos vs o que o humano leria na foto

**Checklist:**

1. A lista de itens extraídos bate visualmente com a foto?
2. Valores (qtd × unit) somam o total do cupom?
3. Fornecedor inferido corresponde ao cabeçalho visível?
4. Data/hora batem com a visível no topo do cupom?
5. Itens "zerados" ou com descrição truncada precisam de regra nova?

**Relatório esperado em `docs/propostas/sprint_45_conferencia.md`**:

- Tabela: foto → itens-OCR → itens-esperados → recall → observação
- Layouts novos para acrescentar em `mappings/ocr_cupom_regex.yaml`
- Substituições de OCR-pós (ex: "leite 1l" → "LEITE 1L")

**Critério de aprovação**: 3 fotos de emissores diferentes com recall >= 80%; fallback funciona corretamente.

---

*"Um cupom fiscal é um diário de apetites. Ler é conhecer-se." -- princípio de consumidor consciente*
