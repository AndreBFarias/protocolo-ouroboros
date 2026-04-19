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
      reason: "orquestra: lê inbox → expande ZIP/EML → classificador → router"
    - path: src/utils/file_detector.py
      reason: "adiciona detectores de imagem e XML (conteúdo, não nome)"
    - path: mappings/tipos_documento.yaml
      reason: "cria registro canônico de tipos suportados com regex de detecção e pasta destino"
    - path: docs/CONVENCOES_NOMES.md
      reason: "novo documento com convenções de renomeação por tipo"
    - path: pyproject.toml
      reason: "adiciona python-magic e pillow-heif se necessário"
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
    - "ZIP com múltiplos arquivos é expandido recursivamente; arquivo original preservado em data/raw/_zipados/"
    - "mappings/tipos_documento.yaml tem pelo menos 13 tipos registrados"
    - "Acentuação PT-BR correta"
    - "Zero emojis"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 41 -- Intake Universal Multiformato

**Status:** PENDENTE
**Data:** 2026-04-19
**Prioridade:** CRÍTICA
**Tipo:** Feature
**Dependências:** Sprint 42 (pode rodar em paralelo, mas grafo ajuda a registrar roteamentos)
**Desbloqueia:** Sprints 44-47b (extratores de documento assumem arquivo já classificado)
**Issue:** --
**ADR:** ADR-15 (Intake Universal Multiformato)

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

Schema:
```yaml
tipos:
  - id: danfe_nfe
    descricao: "DANFE PDF de NFe"
    mimes: ["application/pdf"]
    regex_conteudo: ["DANFE", "CHAVE DE ACESSO", "\\d{44}"]
    pasta_destino_template: "data/raw/{pessoa}/nfs_fiscais/"
    renomear_template: "NF_{data:%Y%m%d}_{fornecedor}_{numero}.pdf"

  - id: cupom_fiscal
    descricao: "Cupom fiscal térmico (foto)"
    mimes: ["image/jpeg", "image/png", "image/heic"]
    regex_conteudo: ["CUPOM FISCAL", "CCF:", "SAT"]
    pasta_destino_template: "data/raw/{pessoa}/nfs_fiscais/"
    renomear_template: "CUPOM_{data:%Y%m%d}_{fornecedor}.{ext}"

  - id: xml_nfe
    mimes: ["application/xml", "text/xml"]
    regex_conteudo: ["<infNFe", "<?xml"]
    pasta_destino_template: "data/raw/{pessoa}/nfs_fiscais/xml/"
    renomear_template: "NFe_{chave44}.xml"

  - id: receita_medica
    mimes: ["application/pdf", "image/jpeg", "image/png"]
    regex_conteudo: ["CRM", "POSOLOGIA", "PRESCRIÇÃO", "USO CONTÍNUO"]
    pasta_destino_template: "data/raw/{pessoa}/saude/receitas/"
    renomear_template: "RECEITA_{data:%Y%m%d}_{medico_nome}.{ext}"

  - id: garantia
    mimes: ["application/pdf", "image/jpeg", "image/png", "message/rfc822"]
    regex_conteudo: ["GARANTIA", "TERMO DE GARANTIA", "PRAZO DE GARANTIA"]
    pasta_destino_template: "data/raw/{pessoa}/garantias/"
    renomear_template: "GARANTIA_{produto}_{data:%Y%m%d}.{ext}"

  - id: holerite
    mimes: ["application/pdf"]
    regex_conteudo: ["Demonstrativo de Pagamento de Salário", "Folha Mensal", "Holerite"]
    pasta_destino_template: "data/raw/{pessoa}/holerites/"
    renomear_template: "HOLERITE_{mes_ref}_{empresa}.pdf"

  # ... (extrato_bancario, fatura_cartao, conta_luz, conta_agua,
  #      boleto_servico, contrato, recibo)
```

Pelo menos 13 tipos registrados. Regras simples primeiro; refinamento vira proposta do supervisor.

### Fase 3: detecção de pessoa em inbox flat

Se `arquivo.parent.name in {"andre", "vitoria"}` -> usa path. Senão:
1. Extrair CPF do preview (`\d{3}\.\d{3}\.\d{3}-\d{2}`)
2. Comparar com `mappings/cpfs_pessoas.yaml` (novo, sem segredo: apenas mapeamento CPF->Pessoa)
3. Se não casar, pasta `_classificar/` e proposta

### Fase 4: suporte a ZIP e EML

- `src/intake/extractors_envelope.py`: `expandir_zip(arquivo) -> list[Path]`, `extrair_anexos_eml(arquivo) -> list[Path]`.
- Arquivo original vai pra `data/raw/_envelopes/<tipo>/<nome>` (cria se não existir).
- No grafo (Sprint 42): nó `Envelope` com aresta `contem` apontando para cada arquivo extraído.

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

**Arquivos originais a ler** (amostras reais do usuário, colocadas em `data/inbox/` ou em `data/raw/_classificar/` após primeiro rodar):

- 3 imagens de cupom fiscal (JPG/HEIC) de fornecedores diferentes
- 2 DANFE PDF
- 1 XML NFe
- 1 receita médica fotografada
- 1 termo de garantia (PDF ou EML)

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

**Critério de aprovação**: taxa de recall >= 90% em amostra de 20 arquivos; fallbacks restantes viram propostas de novas regras.

---

*"Conhecer é saber onde cada coisa mora." -- Aristóteles (parafraseado)*
