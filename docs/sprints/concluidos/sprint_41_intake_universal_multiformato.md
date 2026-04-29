---
concluida_em: 2026-04-19
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 41
  title: "Intake Universal Multiformato: qualquer arquivo na inbox"
  touches:
    - path: src/intake/__init__.py
      reason: "novo pacote dedicado a classificação e roteamento de arquivos de entrada"
    - path: src/intake/classifier.py
      reason: "classifica tipo_documento via MIME + conteúdo + fallback supervisor"
    - path: src/intake/router.py
      reason: "move arquivo para pasta determinística conforme tipo detectado"
    - path: src/intake/preview.py
      reason: "preview rápido (OCR baixa resolução ou extract_text) para alimentar o classificador"
    - path: src/inbox_processor.py
      reason: "orquestra: lê inbox → expande envelopes (ZIP/EML/PDF-multipage) → classifica página-a-página → router"
    - path: src/intake/extractors_envelope.py
      reason: "expande envelopes: ZIP, EML e PDF compilado (page-split + diagnóstico scan/nativo por página)"
    - path: src/intake/glyph_tolerant.py
      reason: "regex e helpers tolerantes a glyphs corrompidos em PDF nativo (Armadilha #20)"
    - path: src/utils/file_detector.py
      reason: "adiciona detectores de imagem e XML (conteúdo, não nome)"
    - path: mappings/tipos_documento.yaml
      reason: "cria registro canônico de tipos suportados com regex de detecção e pasta destino; inclui cupom_garantia_estendida (só roteamento, extração é Sprint 47c)"
    - path: docs/CONVENCOES_NOMES.md
      reason: "novo documento com convenções de renomeação por tipo"
    - path: pyproject.toml
      reason: "adiciona python-magic, pillow-heif e pikepdf (page-split) se necessário"
  n_to_n_pairs:
    - [mappings/tipos_documento.yaml, src/intake/classifier.py]
    - [mappings/tipos_documento.yaml, docs/CONVENCOES_NOMES.md]
  forbidden:
    - src/extractors/  # extratores só consomem arquivos já classificados; esta sprint não mexe em extração
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_intake_classifier.py -x -q"
      timeout: 60
    - cmd: "./run.sh --inbox"
      timeout: 120
  acceptance_criteria:
    - "src/intake/classifier.py classifica sample de 10 arquivos heterogêneos (PDF, JPG, PNG, XML, CSV, EML) sem crash"
    - "JPG de cupom fiscal (amostra em data/fixtures/) é roteado para data/raw/andre/nfs_fiscais/"
    - "Arquivos não cobertos por regra vão para data/raw/_classificar/ e geram proposta em docs/propostas/classificar/"
    - "ZIP com múltiplos arquivos é expandido recursivamente; arquivo original preservado em data/raw/_envelopes/zip/"
    - "PDF compilado (várias páginas, vários documentos lógicos) é page-splittado: cada página vira PDF de 1 página em data/raw/_envelopes/pdf_split/<sha8>/pgN.pdf, e a classificação roda PÁGINA-A-PÁGINA -- 1 PDF de N páginas pode produzir N tipos diferentes e ser roteado para N pastas distintas"
    - "Diagnóstico scan vs nativo é por página, não por arquivo: PDF misto (algumas páginas com texto extraível, outras só com imagem) é tratado corretamente; páginas-imagem entram em data/raw/_classificar/_aguardando_ocr/ até OCR (Sprint 45/47b cobrem o OCR específico)"
    - "Detector de tipo usa src/intake/glyph_tolerant.py para tolerar pares conhecidos de glyph corrompido (CNPJ↔CNP), S↔5, O↔Q em palavra-chave) -- testado contra fixture com pdf_notas.pdf (texto nativo de cupom de garantia Americanas com fonte ToUnicode quebrada)"
    - "mappings/tipos_documento.yaml tem pelo menos 14 tipos registrados (13 originais + cupom_garantia_estendida só para roteamento, sem extrator -- isso é Sprint 47c)"
    - "Roteamento dos 2 PDFs reais da inbox (`inbox/notas de garantia e compras.pdf` 4 pg e `inbox/pdf_notas.pdf` 3 pg) gera, ao final: 2 NFC-e em data/raw/<pessoa>/nfs_fiscais/_aguardando_ocr/, 4 cupons de garantia em data/raw/<pessoa>/garantias_estendidas/ (3 nativos + 1 scan), e o relatório docs/propostas/sprint_41_conferencia.md detalha cada página"
    - "Dedup intra-PDF por identificador natural (chave 44 para NFC-e, número de bilhete para cupom de garantia): pg1==pg2 do pdf_notas.pdf é detectado e a duplicata vai para data/raw/_envelopes/duplicatas/, não para a pasta canônica"
    - "Acentuação PT-BR correta"
    - "Zero emojis"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 41 -- Intake Universal Multiformato

**Status:** CONCLUÍDA
**Data:** 2026-04-19 (implementada e validada via prova de fogo no mesmo dia)
**Prioridade:** CRÍTICA
**Tipo:** Feature
**Dependências:** Sprint 42 (pode rodar em paralelo, mas grafo ajuda a registrar roteamentos)
**Desbloqueia:** Sprints 41b, 41c, 41d (sprints filhas para gaps revelados pela prova de fogo), 44-47b (extratores de documento assumem arquivo já classificado)
**Issue:** --
**ADR:** ADR-15 (Intake Universal Multiformato)
**Conferência Artesanal Opus:** `docs/propostas/sprint_41_conferencia.md` (aprovada 2026-04-19; precisão 100% em 98 arquivos diversos)
**Integração no inbox_processor.py:** PENDENTE -- aguarda Sprint 41d (heterogeneity) + re-prova de fogo

---

## Como Executar

**Comandos principais:**
- `make lint` -- ruff check + format + acentuação
- `./run.sh --inbox` -- processa arquivos na inbox
- `./run.sh --check` -- valida dependências
- `.venv/bin/pytest tests/test_intake_classifier.py -x -q`

### O que NÃO fazer

- NÃO extrair conteúdo de itens de NF nesta sprint (Sprint 44+)
- NÃO tentar parsear dados bancários nesta sprint (Sprint 37 já entrega via extractors existentes)
- NÃO hardcodar caminhos; tudo via `Path` e `mappings/tipos_documento.yaml`
- NÃO adicionar dependência sem discutir em ADR; se `python-magic` for escolhido, documentar

---

## Problema

Hoje `src/inbox_processor.py:14` aceita só `{.csv, .xlsx, .xls, .pdf, .ofx}`. Fotos do celular (JPG/HEIC) e XMLs NFe são descartados. A visão do catalogador universal exige aceitar QUALQUER arquivo e o sistema decidir o que fazer.

Falta também convenção de renomeação (hoje `holerite_1776557416464.pdf` coexiste com `document(10).pdf` -- ambos são Infobase janeiro/2026). O pipeline precisa renomear para formato estável `HOLERITE_202601_INFOBASE.pdf`.

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Inbox processor | `src/inbox_processor.py` | Varre inbox, detecta tipo, move para `data/raw/` -- extensões limitadas |
| File detector | `src/utils/file_detector.py:542-589` | Inspeção de conteúdo para CSV/PDF/XLSX |
| Logger | `src/utils/logger.py` | `obter_logger("intake")` disponível |
| Deteção de pessoa | `src/extractors/base.py:44-51` | `_detectar_pessoa` via path |
| Diretórios pessoa/tipo | `data/raw/andre/*`, `data/raw/vitoria/*` | Estrutura existente a respeitar |

## Implementação

### Fase 1: criar pacote `src/intake/`

Arquivos novos:

- `src/intake/__init__.py` -- export das APIs públicas
- `src/intake/classifier.py`
- `src/intake/router.py`
- `src/intake/preview.py`

**classifier.py (pseudocódigo):**
```python
from pathlib import Path
import yaml
from src.utils.logger import obter_logger

logger = obter_logger("intake.classifier")
MAPPINGS = Path(__file__).parents[2] / "mappings" / "tipos_documento.yaml"

def classificar(arquivo: Path) -> dict:
    """Retorna {tipo, pessoa, pasta_destino, renomear_para, confianca}."""
    mime = _detectar_mime(arquivo)
    preview = _preview_conteudo(arquivo, mime)
    regras = _carregar_regras()
    for regra in regras:
        if _casa(regra, mime, preview, arquivo):
            return _hidratar(regra, arquivo, preview)
    return _fallback_classificar(arquivo)
```

### Fase 2: criar `mappings/tipos_documento.yaml`

**Fonte canônica de execução:** `mappings/tipos_documento.yaml`. O bloco YAML abaixo é SPEC/documentação -- ao alterar uma regra, manter os dois sincronizados (meta-regra N-para-N #1 do AI.md). O `src/intake/classifier.py` carrega o arquivo `mappings/tipos_documento.yaml`, NÃO este markdown.

Schema (regras avaliadas em 3 níveis: `especifico` antes de `normal`, `normal` antes de `fallback`. Dentro do mesmo nível, primeiro que casa todos os `regex_conteudo` segundo `match_mode` vence. Empate dentro do nível resolve por ordem de declaração no YAML, mas a expectativa é que `match_mode: all` em "específico" elimine ambiguidade real):

```yaml
# ===========================================================================
# Esquema de cada entrada:
#   id:                       identificador único (snake_case)
#   descricao:                o que é (humano-legível)
#   prioridade:               especifico | normal | fallback
#   match_mode:               all | any -- AND ou OR sobre regex_conteudo
#   mimes:                    lista de MIMEs aceitos no preview
#   regex_conteudo:           padrões aplicados ao texto extraído (preview)
#                             usar src/intake/glyph_tolerant.py para PDFs nativos (Armadilha #20)
#   extrator_modulo:          caminho de import do extrator (null = só roteamento, sem extrator ainda)
#   origem_sprint:            sprint que criou a regra (rastreabilidade -- só metadado)
#   pasta_destino_template:   destino com placeholder {pessoa}
#   renomear_template:
#     com_data:               usado quando a detecção rasa extrai data (regex DD/MM/YYYY)
#     sem_data:               fallback quando não há data extraível
#   Convenção do nome canônico no intake: <TIPO>[_<YYYY-MM-DD>]_<sha8>.<ext>
#   Renomeação rica (com fornecedor/número/empresa) é responsabilidade do EXTRATOR dedicado.
# ===========================================================================

tipos:

  # ============================================================
  # === ESPECÍFICO (4) -- assinaturas únicas, match_mode: all ===
  # ============================================================

  - id: cupom_garantia_estendida
    descricao: "Bilhete de Seguro de Garantia Estendida (apólice SUSEP -- NÃO é Termo de Garantia do fabricante)"
    prioridade: especifico
    match_mode: all
    mimes: ["application/pdf", "image/jpeg", "image/png"]
    regex_conteudo:
      - "CUPOM\\s+[B8]ILHETE\\s+DE\\s+SEGURO"
      - "GARANTIA\\s+ESTENDIDA"
      - "Processo\\s+[S5]USEP"
    extrator_modulo: null   # roteamento apenas; extrator é Sprint 47c
    origem_sprint: 41
    pasta_destino_template: "data/raw/{pessoa}/garantias_estendidas/"
    renomear_template:
      com_data: "GARANTIA_EST_{data:%Y-%m-%d}_{sha8}.{ext}"
      sem_data: "GARANTIA_EST_{sha8}.{ext}"

  - id: nfce_consumidor_eletronica
    descricao: "NFC-e modelo 65 (mini-cupom 80mm com QR SEFAZ)"
    prioridade: especifico
    match_mode: all
    mimes: ["application/pdf"]
    regex_conteudo:
      - "Documento\\s+Auxiliar\\s+da\\s+Nota\\s+Fiscal\\s+de\\s+Consumidor"
      - "fazenda\\.\\w+\\.gov\\.br/nfce"
    extrator_modulo: src.extractors.nfce_pdf
    origem_sprint: 44b
    pasta_destino_template: "data/raw/{pessoa}/nfs_fiscais/nfce/"
    renomear_template:
      com_data: "NFCE_{data:%Y-%m-%d}_{sha8}.pdf"
      sem_data: "NFCE_{sha8}.pdf"

  - id: danfe_nfe55
    descricao: "DANFE PDF (NFe modelo 55, formal A4 com destinatário)"
    prioridade: especifico
    match_mode: all
    mimes: ["application/pdf"]
    regex_conteudo:
      - "DANFE"
      - "DOCUMENTO\\s+AUXILIAR\\s+DA\\s+NOTA\\s+FISCAL\\s+ELETR[ÔO]NICA"
      - "DESTINAT[ÁA]RIO"   # NFe55 sempre tem bloco; NFC-e não -- evita falso-positivo
    extrator_modulo: src.extractors.danfe_pdf
    origem_sprint: 44
    pasta_destino_template: "data/raw/{pessoa}/nfs_fiscais/danfe55/"
    renomear_template:
      com_data: "NF55_{data:%Y-%m-%d}_{sha8}.pdf"
      sem_data: "NF55_{sha8}.pdf"

  - id: xml_nfe
    descricao: "XML NFe (modelo 55 ou 65) -- caminho preferencial quando disponível"
    prioridade: especifico
    match_mode: any   # MIME já filtra; basta a tag <infNFe>
    mimes: ["application/xml", "text/xml"]
    regex_conteudo:
      - "<infNFe"
    extrator_modulo: src.extractors.xml_nfe
    origem_sprint: 46
    pasta_destino_template: "data/raw/{pessoa}/nfs_fiscais/xml/"
    renomear_template:
      com_data: "XMLNFe_{data:%Y-%m-%d}_{sha8}.xml"
      sem_data: "XMLNFe_{sha8}.xml"

  # ===================================================
  # === NORMAL (9) -- documentos pessoais e bancários ===
  # ===================================================

  - id: holerite
    descricao: "Contracheque G4F ou Infobase (PDF nativo ou escaneado)"
    prioridade: normal
    match_mode: any
    mimes: ["application/pdf"]
    regex_conteudo:
      - "Demonstrativo\\s+de\\s+Pagamento\\s+de\\s+Sal[áa]rio"
      - "Folha\\s+Mensal"
      - "Holerite"
    extrator_modulo: src.extractors.contracheque_pdf
    origem_sprint: 41   # extrator existe desde antes; regra de roteamento é da 41
    pasta_destino_template: "data/raw/{pessoa}/holerites/"
    renomear_template:
      com_data: "HOLERITE_{data:%Y-%m-%d}_{sha8}.pdf"
      sem_data: "HOLERITE_{sha8}.pdf"

  - id: receita_medica
    descricao: "Receita médica ou prescrição (PDF nativo ou foto)"
    prioridade: normal
    match_mode: any
    mimes: ["application/pdf", "image/jpeg", "image/png"]
    regex_conteudo:
      - "CRM[\\s:/-]+\\d"
      - "POSOLOGIA"
      - "PRESCRI[ÇC][ÃA]O"
      - "USO\\s+CONT[ÍI]NUO"
    extrator_modulo: null   # Sprint 47a
    origem_sprint: 47a
    pasta_destino_template: "data/raw/{pessoa}/saude/receitas/"
    renomear_template:
      com_data: "RECEITA_{data:%Y-%m-%d}_{sha8}.{ext}"
      sem_data: "RECEITA_{sha8}.{ext}"

  - id: garantia_fabricante
    descricao: "Termo de Garantia do fabricante (cobertura de defeito; distinto de cupom_garantia_estendida)"
    prioridade: normal
    match_mode: any
    mimes: ["application/pdf", "image/jpeg", "image/png", "message/rfc822"]
    regex_conteudo:
      - "TERMO\\s+DE\\s+GARANTIA"
      - "PRAZO\\s+DE\\s+GARANTIA"
      - "MANUAL\\s+DO\\s+PROPRIET[ÁA]RIO"
    extrator_modulo: null   # Sprint 47b
    origem_sprint: 47b
    pasta_destino_template: "data/raw/{pessoa}/garantias/"
    renomear_template:
      com_data: "GARANTIA_{data:%Y-%m-%d}_{sha8}.{ext}"
      sem_data: "GARANTIA_{sha8}.{ext}"

  - id: fatura_cartao
    descricao: "Fatura de cartão de crédito em PDF (Santander/Nubank/C6) -- declarada ANTES de extrato_bancario porque 'Limite do cartão' e 'Total da fatura' são fingerprint forte e exclusivo"
    prioridade: normal
    match_mode: any
    mimes: ["application/pdf"]
    regex_conteudo:
      - "Fatura\\s+do\\s+Cart[ãa]o"
      - "Total\\s+da\\s+fatura"
      - "Limite\\s+do\\s+cart[ãa]o"
      - "Vencimento\\s+da\\s+fatura"
    extrator_modulo: null   # extratores específicos por bandeira já existem
    origem_sprint: 41
    pasta_destino_template: "data/raw/{pessoa}/faturas/"
    renomear_template:
      com_data: "FATURA_{data:%Y-%m-%d}_{sha8}.pdf"
      sem_data: "FATURA_{sha8}.pdf"

  - id: extrato_bancario
    descricao: "Extrato de conta corrente em PDF (Itaú/Santander/C6/Nubank PF)"
    prioridade: normal
    match_mode: any
    mimes: ["application/pdf"]
    regex_conteudo:
      - "EXTRATO\\s+DE\\s+CONTA"
      - "EXTRATO\\s+CONSOLIDADO"
      - "Saldo\\s+Anterior"
      - "Saldo\\s+do\\s+per[íi]odo"
    extrator_modulo: null   # extratores específicos por banco já existem em src/extractors/{itau,santander,c6,nubank_cc}.py
    origem_sprint: 41
    pasta_destino_template: "data/raw/{pessoa}/extratos/"
    renomear_template:
      com_data: "EXTRATO_{data:%Y-%m-%d}_{sha8}.pdf"
      sem_data: "EXTRATO_{sha8}.pdf"

  - id: conta_luz
    descricao: "Fatura de energia (Neoenergia/CEB) -- PDF ou foto"
    prioridade: normal
    match_mode: any
    mimes: ["application/pdf", "image/jpeg", "image/png"]
    regex_conteudo:
      - "Neoenergia"
      - "CEB\\s+Distribui[çc][ãa]o"
      - "Fatura\\s+de\\s+Energia"
      - "kWh"
    extrator_modulo: src.extractors.energia_ocr
    origem_sprint: 41
    pasta_destino_template: "data/raw/{pessoa}/contas/luz/"
    renomear_template:
      com_data: "LUZ_{data:%Y-%m-%d}_{sha8}.{ext}"
      sem_data: "LUZ_{sha8}.{ext}"

  - id: conta_agua
    descricao: "Fatura de água da CAESB -- PDF ou foto"
    prioridade: normal
    match_mode: any
    mimes: ["application/pdf", "image/jpeg", "image/png"]
    regex_conteudo:
      - "CAESB"
      - "Companhia\\s+de\\s+Saneamento\\s+Ambiental"
      - "Consumo\\s+de\\s+[ÁA]gua"
      - "m[³3]\\s*de\\s*[áa]gua"
    extrator_modulo: null   # extrator de água ainda não existe
    origem_sprint: 41
    pasta_destino_template: "data/raw/{pessoa}/contas/agua/"
    renomear_template:
      com_data: "AGUA_{data:%Y-%m-%d}_{sha8}.{ext}"
      sem_data: "AGUA_{sha8}.{ext}"

  - id: boleto_servico
    descricao: "Boleto bancário (linha digitável + vencimento)"
    prioridade: normal
    match_mode: any
    mimes: ["application/pdf"]
    regex_conteudo:
      - "Linha\\s+digit[áa]vel"
      - "C[óo]digo\\s+de\\s+barras"
      - "\\d{5}\\.\\d{5}\\s+\\d{5}\\.\\d{6}\\s+\\d{5}\\.\\d{6}\\s+\\d\\s+\\d{14}"   # padrão linha digitável
      - "Vencimento.{0,40}\\d{2}/\\d{2}/\\d{4}"
    extrator_modulo: null   # extrator de boleto ainda não existe
    origem_sprint: 41
    pasta_destino_template: "data/raw/{pessoa}/boletos/"
    renomear_template:
      com_data: "BOLETO_{data:%Y-%m-%d}_{sha8}.pdf"
      sem_data: "BOLETO_{sha8}.pdf"

  - id: contrato
    descricao: "Contrato (locação/prestação/financiamento/compra-e-venda) -- exige CONTRATANTE E CONTRATAD[OA] em qualquer posição do texto, sem janela de proximidade"
    prioridade: normal
    match_mode: all
    mimes: ["application/pdf"]
    regex_conteudo:
      - "CONTRATANTE"
      - "CONTRATAD[OA]"
    extrator_modulo: null   # contratos não são extraídos automaticamente; intake só arquiva
    origem_sprint: 41
    pasta_destino_template: "data/raw/{pessoa}/contratos/"
    renomear_template:
      com_data: "CONTRATO_{data:%Y-%m-%d}_{sha8}.pdf"
      sem_data: "CONTRATO_{sha8}.pdf"

  # =============================================================
  # === FALLBACK (2) -- assinaturas fracas; só pegam se NORMAL falhar ===
  # =============================================================

  - id: cupom_fiscal_foto
    descricao: "Cupom fiscal térmico fotografado (chega como imagem; OCR no extrator da Sprint 45)"
    prioridade: fallback
    match_mode: any
    mimes: ["image/jpeg", "image/png", "image/heic"]
    regex_conteudo:   # OCR de baixa resolução no preview; aceita qualquer pista
      - "CUPOM\\s+FISCAL"
      - "CCF[\\s:]"
      - "EXTRATO\\s+CF[-\\s]?e"
      - "SAT[-\\s]"
    extrator_modulo: null   # Sprint 45
    origem_sprint: 45
    pasta_destino_template: "data/raw/{pessoa}/nfs_fiscais/cupom_foto/"
    renomear_template:
      com_data: "CUPOM_{data:%Y-%m-%d}_{sha8}.{ext}"
      sem_data: "CUPOM_{sha8}.{ext}"

  - id: recibo_nao_fiscal
    descricao: "Recibo simples sem CNPJ formal (aluguel/mensalidade/autônomo)"
    prioridade: fallback
    match_mode: any
    mimes: ["application/pdf", "image/jpeg", "image/png"]
    regex_conteudo:
      - "RECEBI\\s+DE"
      - "Recibo\\s+No?\\.?\\s*\\d"
      - "RECIBO\\s+DE\\s+PAGAMENTO"
    extrator_modulo: null   # Sprint 47
    origem_sprint: 47
    pasta_destino_template: "data/raw/{pessoa}/recibos/"
    renomear_template:
      com_data: "RECIBO_{data:%Y-%m-%d}_{sha8}.{ext}"
      sem_data: "RECIBO_{sha8}.{ext}"
```

**Total: 15 tipos registrados** (4 específicos + 9 normais + 2 fallback). Critério de aceitação "≥14" satisfeito.

**Convenção do nome canônico no intake:** `<TIPO>[_<YYYY-MM-DD>]_<sha8>.<ext>`. Data é detectada por regex rasa (primeira ocorrência `\d{2}/\d{2}/\d{4}` no preview); se ausente, cai no template `sem_data`. Renomeação rica (com fornecedor, número, empresa, seguradora, bilhete) é **responsabilidade do EXTRATOR dedicado** (Sprints 44/44b/45/.../47c), porque exige conteúdo parseado que o classificador raso não tem.

**Estado computado `_aguardando_ocr`:** páginas detectadas como `scan` por `diagnosticar_pagina` que não tenham assinatura forte de tipo via OCR rápido vão para `data/raw/_classificar/_aguardando_ocr/` -- isso é estado, não tipo. Não polui o YAML.

**Glyph tolerance:** toda regex marcada com classes `[B8]`, `[S5]`, `[ÔO]`, `[ÁA]`, `[ÇC]`, `[ÍI]` etc. usa o vocabulário canonicalizado em `src/intake/glyph_tolerant.py` (Armadilha #20). Refinamento de variantes vira proposta do supervisor.

### Fase 3: detecção de pessoa em inbox flat

Se `arquivo.parent.name in {"andre", "vitoria"}` -> usa path. Senão:
1. Extrair CPF do preview (`\d{3}\.\d{3}\.\d{3}-\d{2}`)
2. Comparar com `mappings/cpfs_pessoas.yaml` (novo, sem segredo: apenas mapeamento CPF->Pessoa)
3. Se não casar, pasta `_classificar/` e proposta

### Fase 4: envelopes -- ZIP, EML e PDF compilado (page-split obrigatório)

`src/intake/extractors_envelope.py` (MVP, não opcional):

```python
def expandir_zip(arquivo: Path) -> list[Path]: ...
def extrair_anexos_eml(arquivo: Path) -> list[Path]: ...
def expandir_pdf_multipage(arquivo: Path) -> list[Path]:
    """Quebra PDF em N PDFs de 1 página via pikepdf.
    SEMPRE roda para PDFs com >= 2 páginas. Retorna paths em
    data/raw/_envelopes/pdf_split/<sha8_arquivo_original>/pgN.pdf.
    Decisão de tipo é por página, não por arquivo."""

def diagnosticar_pagina(pdf_pagina: Path) -> Literal["nativo", "scan", "misto"]:
    """Para cada página: extract_text() não vazio -> 'nativo';
    text vazio + >=1 imagem cobrindo >80% da área -> 'scan';
    senão 'misto' (raro, vai para _classificar)."""

def hash_identificador_natural(texto: str, tipo: str) -> str | None:
    """Extrai chave única do conteúdo para dedup intra-arquivo:
    - nfce_consumidor_eletronica / danfe_nfe55: chave 44 dígitos
    - cupom_garantia_estendida: número do bilhete individual (13-18 dígitos)
    Devolve None se não detectar -- a dedup global fica para o grafo (Sprint 42)."""
```

**Regra de armazenamento de envelopes:**

- Arquivo original sempre preservado em `data/raw/_envelopes/<tipo>/<nome_original>` (zip/eml/pdf_compilado).
- Páginas/anexos extraídos vão para `data/raw/_envelopes/pdf_split/<sha8>/pgN.pdf` ou `data/raw/_envelopes/eml_anexos/<eml_id>/<nome_anexo>`.
- Duplicata intra-arquivo (mesmo identificador natural) vai para `data/raw/_envelopes/duplicatas/`, não polui pasta canônica.
- No grafo (Sprint 42): nó `Envelope` com aresta `contem` para cada documento lógico extraído. Páginas duplicadas viram apenas uma aresta `contem` + nota `pagina_origem: [1, 2]` em metadata.

**Por que page-split é MVP:** as amostras reais (`inbox/notas de garantia e compras.pdf` e `inbox/pdf_notas.pdf`) são 100% PDFs compilados heterogêneos. Sem page-split, o intake teria que decidir UM tipo para o arquivo inteiro, o que é impossível quando o mesmo PDF mistura NFC-e + cupom de garantia. Detectado na Conferência Artesanal Opus de 2026-04-19 (`/tmp/amostras_sprint41.md`).

### Fase 5: fallback supervisor

Arquivos sem match vão para `data/raw/_classificar/<uuid>/<nome_original>`. Automaticamente:

1. Proposta criada em `docs/propostas/classificar/<uuid>_proposta.md` (template em `docs/templates/PROPOSTA_CLASSIFICACAO.md`)
2. `scripts/supervisor_contexto.sh` (Sprint 43) inclui contagem e lista primeiros itens pendentes
3. Humano + Claude Code decidem tipo, adicionam regra ao `mappings/tipos_documento.yaml`, e reclassificam via `./run.sh --reclassificar _classificar/<uuid>`

### Fase 6: testes

`tests/test_intake_classifier.py`:
- `test_jpg_cupom_vai_para_nfs_fiscais` (fixture em `tests/fixtures/cupom_sample.jpg`)
- `test_xml_nfe_vai_para_xml_dir`
- `test_pdf_holerite_G4F_vai_para_holerites`
- `test_arquivo_desconhecido_vai_para_classificar`
- `test_zip_expande_e_classifica_interno`
- `test_eml_extrai_anexos`

Fixtures mínimas: criar arquivos sintéticos a partir de texto simulado, não usar dados reais do usuário.

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A41-1 | HEIC requer `pillow-heif` no Linux; silencia sem ele | Dep explícita em pyproject.toml + fallback que loga warning ("instale pillow-heif") |
| A41-2 | Imagens de WhatsApp mantêm rotação EXIF | Sempre aplicar `ImageOps.exif_transpose` antes de OCR |
| A41-3 | E-mails HTML com anexos nested quebram parser ingênuo | Usar `email.policy.default` em `email.message_from_bytes` |
| A41-4 | Pessoa inferida errado envia cupom de Vitória pra pasta do André | Sempre registrar `confianca` e mandar para `_classificar/` se < 0.7 |
| A41-5 | `python-magic` tem dois pacotes com mesmo import (`python-magic` e `python-magic-bin`) | Documentar escolha em pyproject.toml e pinnear versão |
| A41-6 | Alguns cupons fiscais fotografados têm reflexos que quebram OCR preview | Preview rodar com confidence mínima; abaixo, vai pra `_classificar/` |
| A41-7 | Renomeação com `fornecedor` vazio cria nome `NF_20260419__1234.pdf` | Template exige todos os campos preenchidos; se faltar, fallback pra `NF_20260419_INDEFINIDO.pdf` e proposta |
| A41-8 | PDF compilado heterogêneo: detector roda no arquivo inteiro e escolhe um tipo só | Page-split SEMPRE em PDFs com >=2 páginas; classificador roda página-a-página; arquivo original vira `Envelope` no grafo |
| A41-9 | Página com pouco texto extraído (rodapé só com QR) é classificada como "scan" e mandada pra OCR sem necessidade | Heurística `nativo` exige >50 chars úteis OU presença de marcador-âncora conhecido (chave 44, palavra "BILHETE"); senão fallback para `scan` é seguro |
| A20 (cross) | Glyphs corrompidos em PDF nativo (`CNP)` em vez de `CNPJ`) deixam regex passar por arquivo válido | Toda regex de detecção usa `src/intake/glyph_tolerant.py`. Ver ARMADILHAS.md #20 |

Referência: `docs/ARMADILHAS.md`

## Evidências Obrigatórias

- [ ] `make lint` passa sem erros
- [ ] `.venv/bin/pytest tests/test_intake_classifier.py -x -q` passa com cobertura >= 70%
- [ ] `./run.sh --inbox` processa lote de 10 arquivos heterogêneos sem crash
- [ ] 13+ tipos em `mappings/tipos_documento.yaml`
- [ ] `docs/CONVENCOES_NOMES.md` publicado com exemplo de cada tipo
- [ ] Dashboard inicia sem erro
- [ ] `CLAUDE.md` e `ROADMAP.md` atualizados se o schema do XLSX mudar (não deve)

## Verificação end-to-end

```bash
make lint
./run.sh --check

# preparar lote de teste (arquivos sintéticos)
cp tests/fixtures/samples_intake/*.* data/inbox/

./run.sh --inbox 2>&1 | tee /tmp/intake_log.txt
grep -E "classificado como|classificar/" /tmp/intake_log.txt | wc -l
# esperado: == número de arquivos copiados

ls data/raw/_classificar/ 2>/dev/null && echo "fallback funcionou"
ls data/raw/andre/nfs_fiscais/ | grep "^(NF_|CUPOM_)"
# esperado: pelo menos 1 renomeado

.venv/bin/pytest tests/test_intake_classifier.py -v
```

## Conferência Artesanal Opus

**Arquivos originais a ler** (amostras reais do usuário; já existem na inbox e foram inspecionadas em 2026-04-19, relatório em `/tmp/amostras_sprint41.md`):

- `inbox/notas de garantia e compras.pdf` -- 4 páginas, **scan puro** (cada página é uma imagem). Compilação heterogênea: pg1 = NFC-e Americanas R$ 629,98 / pg2 = bilhete garantia base carregamento P55 / pg3 = bilhete garantia controle P55 / pg4 = NFC-e supermercado denso (~30 itens). 3 tipos diferentes no mesmo arquivo.
- `inbox/pdf_notas.pdf` -- 3 páginas, **texto nativo com fonte ToUnicode quebrada** (Armadilha #20). Compilação homogênea: pg1 = bilhete garantia base carregamento (NumCupom 86, bilhete 781000129322124) / pg2 = duplicata literal da pg1 / pg3 = bilhete garantia controle P55 (NumCupom 85, bilhete 781000129322123).
- (futuro) 3 imagens de cupom fiscal (JPG/HEIC) de fornecedores diferentes -- coletar conforme aparecerem
- (futuro) 1 DANFE PDF NFe modelo 55, 1 XML NFe, 1 receita médica, 1 termo de garantia (não-bilhete) -- coletar conforme aparecerem

**Outputs a comparar:**

- Log do `./run.sh --inbox` (linhas `classificado como <tipo>`)
- Conteúdo de `data/raw/<pessoa>/<pasta_destino>/` (arquivos renomeados)
- `docs/propostas/classificar/*.md` (fallbacks que precisaram de decisão)

**Checklist de conferência:**

1. Cada arquivo acabou na pasta correta?
2. Nome renomeado segue o template do tipo?
3. Pessoa inferida (André/Vitória/Casal) está certa?
4. Tipos que a priori deveriam casar foram para `_classificar/`? (regra precisa ser afinada)
5. ZIP/EML foram expandidos e seus anexos também classificados?

**Relatório esperado em `docs/propostas/sprint_41_conferencia.md`**:

- Tabela: arquivo original → tipo detectado → pasta final → nome final → observação
- Lista de regras novas propostas (ex: "adicionar `regex_conteudo: 'AMERICANAS'` ao tipo cupom_fiscal para aumentar recall")
- Percentual de recall (arquivos classificados corretamente) e precisão

**Critério de aprovação**: taxa de recall >= 90% em amostra de 20 arquivos; fallbacks restantes viram propostas de novas regras. Para os 2 PDFs reais da inbox (que são a fixture mínima), recall esperado é 100% -- 4 páginas de `notas de garantia e compras.pdf` viram 4 documentos lógicos (2 NFC-e + 2 cupons garantia), 3 páginas de `pdf_notas.pdf` viram 2 cupons garantia + 1 duplicata detectada.

---

*"Conhecer é saber onde cada coisa mora." -- Aristóteles (parafraseado)*
