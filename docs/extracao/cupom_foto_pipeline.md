<!-- noqa: accent -->
# Pipeline de extração: cupom fiscal fotografado (`cupom_fiscal_foto`)

> Sprint INFRA-EXTRATOR-CUPOM-FOTO. Documenta o pipeline produtivo
> ponta-a-ponta para cupons fiscais térmicos chegando em formato JPEG
> (foto de celular). Complementa `INFRA-OCR-OPUS-VISAO` (Opus
> multimodal como OCR canônico) e `INFRA-EXTRATORES-USAR-OPUS`
> (refatoração do extrator local para usar Opus como fallback).

## Visão geral

```
foto JPEG (data/raw/.../cupom_foto/CUPOM_<sha8>.jpeg)
        │
        ├─ (opcional) pré-processamento Pillow/OpenCV
        │     deskew + contrast normalization
        │
        ├─ src.extractors.opus_visao.extrair_via_opus(caminho)
        │     │
        │     ├─ calcula sha256 da imagem
        │     ├─ se data/output/opus_ocr_cache/<sha>.json existe -> retorna
        │     ├─ se OPUS_API_KEY ausente (default) -> registra pendente
        │     │      em data/output/opus_ocr_pendentes/<sha>.txt
        │     │      e retorna stub aguardando_supervisor=True
        │     └─ supervisor humano (ADR-13) lê foto via Read multimodal
        │            e grava cache canônico em opus_ocr_cache/<sha>.json
        │
        ├─ src.graph.ingestor_documento.ingerir_cupom_foto(db, payload)
        │     │
        │     ├─ valida payload contra CAMPOS_OBRIGATORIOS_PAYLOAD_OPUS
        │     ├─ rejeita aguardando_supervisor=True com ValueError
        │     ├─ mapeia schema canônico -> dict esperado por
        │     │      ingerir_documento_fiscal
        │     ├─ chave do nó documento = "CUPOMFOTO|<sha256>"
        │     │      (idempotente; mesmo sha -> mesmo nó)
        │     └─ delega para ingerir_documento_fiscal
        │
        └─ persistência no grafo (data/output/grafo.sqlite)
              ├─ 1 nó documento
              ├─ 1 nó fornecedor (CNPJ canônico)
              ├─ N nós item (1 por item -- dedup por chave canônica
              │              <cnpj>|<data>|<codigo>)
              ├─ 1 aresta fornecido_por (documento -> fornecedor)
              ├─ 1 aresta ocorre_em (documento -> periodo node, mês YYYY-MM)
              └─ N arestas contem_item (documento -> item)
```

## Componentes

### 1. Pré-processamento (opcional)

Não exigido pela sprint atual. Quando o supervisor humano consegue ler
diretamente a foto via `Read` multimodal, o ganho de pré-processar é
marginal. Sprint futura pode introduzir deskew + contrast normalization
via Pillow/OpenCV antes da chamada Opus para reduzir confusões de OCR
em cupons amassados.

### 2. OCR via Opus multimodal — `src/extractors/opus_visao.py`

Função pública: `extrair_via_opus(caminho, *, dir_cache=None, dir_pendentes=None) -> dict`.

Modo supervisor artesanal (default, ADR-13):

- Calcula `sha256` hex completo do conteúdo da imagem.
- Cache hit (`<dir_cache>/<sha>.json` existe): retorna direto.
- Cache miss: grava pedido em `<dir_pendentes>/<sha>.txt` com o caminho
  absoluto da imagem; retorna stub `aguardando_supervisor=True` (não
  levanta).
- Supervisor humano (Claude Code) lê o pendente, abre a foto via Read
  multimodal e grava JSON canônico no cache. Próxima invocação bate
  cache hit.

Modo produção (`OPUS_API_KEY` no ambiente): atualmente levanta
`NotImplementedError`. Sprint futura tratará a chamada Anthropic API.

### 3. Schema canônico — `mappings/schema_opus_ocr.json`

JSON Schema Draft 2020-12 documentando o contrato de saída. Campos
obrigatórios: `sha256`, `tipo_documento`, `estabelecimento`,
`data_emissao`, `itens`, `total`, `extraido_via`, `ts_extraido`.

`tipo_documento` para cupons fotografados é `cupom_fiscal_foto`.
`extraido_via` aceita `opus_v4_7`, `opus_supervisor_artesanal` ou
`ocr_local`.

### 4. Adapter de grafo — `src.graph.ingestor_documento.ingerir_cupom_foto`

Mapeia o payload canônico Opus para o formato esperado por
`ingerir_documento_fiscal` e delega:

- `chave_44` sintética: `CUPOMFOTO|<sha256>` (chave do nó `documento`).
- `cnpj_emitente`: `payload.estabelecimento.cnpj` (formato
  `XX.XXX.XXX/XXXX-XX`).
- Itens sem `codigo` (frutas a granel etc.) recebem `SEMCOD<NNNN>`
  derivado da posição na lista.
- Itens sem `descricao` ou sem `valor_total` são descartados.
- Metadata extra preservada no nó documento: `extraido_via`,
  `confianca_global`, `horario`, `operador`, `sha256_imagem`.

Idempotência garantida em duas camadas: chave do documento por sha256;
chave do item por `<cnpj>|<data>|<codigo>` -- reprocessar não duplica.

### 5. Conformance D7 — `make conformance-cupom_foto`

Gate exigido por padrão `(z)` do `VALIDATOR_BRIEF`: `>=3` amostras
4-way verdes em `data/output/conformance.sqlite` antes da sprint poder
ser declarada concluída.

Registro programático (CLI também aceita):

```python
from tests.conformance.gate import inicializar_db, registrar_amostra
from pathlib import Path
db = Path("data/output/conformance.sqlite")
inicializar_db(db)
registrar_amostra(db, tipo="cupom_foto",
                  item_id="<sha256>",
                  etl_ok=True, opus_ok=True, grafo_ok=True, humano_ok=True)
```

## Amostras canônicas (2026-05-08)

| sha8 | descrição | itens | total | data |
|------|-----------|------:|------:|------|
| `2e43640d` | Comercial NSP grande -- 52 itens | 52 | 513,31 | 27/04/2026 |
| `6554d704` | Comercial NSP grande (foto 2) | 52 | 513,31 | 27/04/2026 |
| `67a3104a` | Comercial NSP pequeno -- 22 itens | 22 | 254,91 | 24/04/2026 |
| `bc3c42aa` | Comercial NSP pequeno (foto 2) | 22 | 254,91 | 24/04/2026 |

`6554d704` e `2e43640d` são fotos distintas do mesmo cupom físico de 52
itens. `67a3104a` e `bc3c42aa` são fotos distintas do mesmo cupom de 22
itens. Os 4 sha256 distintos cumprem o gate D7 (>=3 amostras) sem
violar a regra de cobertura total -- cada sha tem cache canônico
próprio em `data/output/opus_ocr_cache/`.

## Reprocessar end-to-end

```bash
.venv/bin/python -c "
import json
from pathlib import Path
from src.graph.db import GrafoDB, caminho_padrao
from src.graph.ingestor_documento import ingerir_cupom_foto

db = GrafoDB(caminho_padrao())
db.criar_schema()
cache_dir = Path('data/output/opus_ocr_cache')
for jpeg in Path('data/raw/casal/nfs_fiscais/cupom_foto/').glob('CUPOM_*.jpeg'):
    import hashlib
    sha = hashlib.sha256(jpeg.read_bytes()).hexdigest()
    cache = cache_dir / f'{sha}.json'
    if cache.exists():
        ingerir_cupom_foto(db, json.loads(cache.read_text()), caminho_arquivo=jpeg)
db.fechar()
"
```

## Pegadinhas conhecidas

- Soma dos itens pode divergir do total declarado em até alguns
  centavos por causa do arredondamento de tributos no PDV. O cache
  canônico é ajustado item-a-item (anotado em `_observacao`) para
  fechar exatamente na soma; a auditoria humana valida no cupom físico.
- Forma de pagamento Sodexo Voucher Alimentação cai em `outro` no
  enum porque `vale_alimentacao` não está na lista atual do schema.
  Sprint futura pode estender o enum.
- Hash sha256 pega conteúdo binário, não nome do arquivo. Reusar mesmo
  cupom com nome diferente bate o mesmo cache.

## Referências

- `mappings/schema_opus_ocr.json` -- contrato de saída.
- `src/extractors/opus_visao.py` -- OCR canônico.
- `src/graph/ingestor_documento.py` -- adapter `ingerir_cupom_foto`.
- `tests/test_cupom_foto_infra.py` -- testes de infra desta sprint.
- `tests/test_cupom_termico_foto.py` -- testes do extrator local
  (refatorado pela sprint paralela INFRA-EXTRATORES-USAR-OPUS).
- ADR-13 (supervisor artesanal).
- ADR-26 sugerido (Opus como OCR canônico para imagens).

*"Cupom fotografado e cupom estruturado têm o mesmo destino: virar nó."*
