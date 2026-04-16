# Sprint 27 -- Ingestão Universal de Documentos

## Status: Pendente (proposta 2026-04-16)
Issue: #11

## Objetivo

Transformar qualquer documento financeiro jogado no sistema (boleto, fatura, NF, cupom fiscal, contrato, recibo) em um **nó `Documento` estruturado** com metadados extraídos: valor, datas, CNPJ, código de barras, emissor, tipo. Hoje o pipeline só processa extratos bancários estruturados (OFX/CSV/PDF de banco conhecido). Esta sprint abre a porta para tudo mais.

Sem esta sprint, a Sprint 28 (Grafo) não tem nós `Documento` pra linkar -- fica só com transações, perdendo metade do valor.

---

## Motivação

O usuário quer jogar qualquer PDF/imagem de documento financeiro e ter o sistema reconhecendo, extraindo dados e preparando pra linking. Exemplos reais:

- PDF de segunda-via de conta de energia com nome zoado (`segunda-via-neoenergia-123.pdf`).
- Foto de um cupom fiscal no WhatsApp que ele salva em JPG.
- Boleto bancário de mensalidade escolar.
- Contrato de aluguel em PDF.
- Informe de rendimentos do empregador.
- Nota fiscal de serviço emitida pela Vitória no MEI.

O sistema atual ignora tudo isso. Só extratos bancários são processados.

---

## Entregas

### 1. Detecção automática de tipo de documento

- [ ] `src/ingest/document_classifier.py` -- classifica PDF/imagem em:
  - `boleto` (tem linha digitável de 47 dígitos + código de barras)
  - `nota_fiscal_servico` (NFS-e, modelo 1/1A)
  - `nota_fiscal_eletronica` (NFe, chave de 44 dígitos)
  - `cupom_fiscal` (modelo 2D, NFC-e, SAT)
  - `fatura_utilitario` (energia, água, gás, internet, telefone)
  - `fatura_cartao` (layout de cartão crédito)
  - `extrato_bancario` (já tratado por extractors; só identifica tipo)
  - `informe_rendimento` (layout Receita Federal)
  - `contrato` (texto longo, assinaturas, cláusulas)
  - `recibo_avulso` (tudo mais)
- [ ] Classificação por heurísticas determinísticas primeiro (padrões regex + estrutura do PDF), com fallback para Claude Code na Sprint 29.

### 2. OCR inteligente multi-estratégia

- [ ] `src/ingest/ocr.py` com cascata:
  1. Se PDF tem texto embutido (não é imagem escaneada), usar `pdfplumber` direto (rápido, preciso).
  2. Se PDF é imagem ou imagem pura (JPG/PNG/HEIC), rodar **Tesseract** (já no projeto).
  3. Para documentos com layout estruturado (tabelas, formulários), testar **Donut** ou **LayoutLMv3** localmente.
  4. Fallback opcional: API externa (Google Document AI / AWS Textract) se o usuário aceitar. **Desligado por padrão**.
- [ ] Suporte a HEIC (foto de iPhone) -- converter via `pillow-heif` ou `imagemagick`.
- [ ] Normalização de imagem antes do OCR: deskew, contraste, binarização.

### 3. Extração estruturada de campos

- [ ] `src/ingest/extractors/` -- um módulo por tipo de documento:
  - `boleto_extractor.py` -- linha digitável (47 dígitos), valor, vencimento, beneficiário, código de barras. Validação via dígito verificador.
  - `nfe_extractor.py` -- chave NFe (44 dígitos), CNPJ emitente, CNPJ destinatário, valor total, data emissão, itens.
  - `nfse_extractor.py` -- NFS-e municipal (formato varia por cidade; suportar Brasília prioritário).
  - `cupom_fiscal_extractor.py` -- CNPJ, valor, data, itens (mesmo sem todos os campos).
  - `fatura_utilitario_extractor.py` -- emissor (regex da Sprint 4 expandido), valor, mês de referência, vencimento.
  - `informe_rendimento_extractor.py` -- empregador, CNPJ, ano-base, rendimentos tributáveis, IRRF, INSS, isentos.
  - `contrato_extractor.py` -- início, fim, valor mensal, partes, índice de reajuste. Extração via heurísticas; fallback para LLM Claude (Sprint 29).
- [ ] Cada extrator devolve um dict com schema consistente:
  ```python
  {
      "tipo": "boleto",
      "valor": 450.23,
      "data_emissao": "2026-03-02",
      "data_vencimento": "2026-03-20",
      "emissor": {"nome": "NEOENERGIA", "cnpj": "01.083.200/0001-18"},
      "identificadores": {"linha_digitavel": "82660000000...", "codigo_barras": "826600..."},
      "arquivo_original": "data/raw/docs/neoenergia-2026-03.pdf",
      "arquivo_hash": "sha256:...",
      "confianca_extracao": 0.92,
  }
  ```

### 4. Entrada de arquivos: 4 caminhos

- [ ] **Inbox watchdog**: processo em background (`src/ingest/watcher.py`) escuta `inbox/` via `watchdog` lib. Novo arquivo aparece -> processa em segundos. Rodar via systemd user unit ou tmux/screen (decidir na execução).
- [ ] **Drag-and-drop no dashboard**: nova página Streamlit em `src/dashboard/paginas/upload.py` com `st.file_uploader` multi-arquivo. Ao enviar, salva em `inbox/` e dispara o processamento.
- [ ] **Gmail/Drive integration**: a Sprint 25 já previa Gmail API para Nubank CSV. Expandir para:
  - Gmail: baixar anexos com assuntos contendo palavras-chave configuráveis em `mappings/gmail_filtros.yaml` (ex.: "conta de luz", "fatura", "boleto", "informe de rendimentos").
  - Google Drive: monitorar pasta específica.
  - Código existente em `src/integrations/gmail_csv.py` vira `gmail_docs.py` genérico.
- [ ] **CLI manual**: `python -m src.ingest.cli --arquivo caminho/doc.pdf` processa pontual.

### 5. Validação e rastreabilidade

- [ ] Cada documento processado gera entrada em `data/output/docs_processados.jsonl` (append-only log):
  ```json
  {"timestamp": "2026-04-16T18:30:00", "arquivo": "...", "hash": "...", "tipo": "boleto", "status": "extraido", "campos": {...}}
  ```
- [ ] Dedup por hash: se o mesmo arquivo for jogado duas vezes, detectar e pular.
- [ ] Documentos com `confianca_extracao < 0.6` vão para `data/output/docs_revisar/` com um `.yaml` editável ao lado do PDF, com os campos extraídos. Usuário revisa e move de volta.

### 6. Integração com o pipeline

- [ ] `src/pipeline.py` chama `src/ingest/processar_documentos()` ANTES da etapa de extração bancária.
- [ ] Documentos viram nós no grafo (Sprint 28) via `src/graph/ingest_doc.py`.
- [ ] Nada quebra se a Sprint 28 ainda não estiver pronta: documentos ficam só no JSONL até o grafo existir.

---

## Arquivos novos/modificados

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| `src/ingest/__init__.py` | novo | Init do módulo |
| `src/ingest/document_classifier.py` | novo | Detector de tipo |
| `src/ingest/ocr.py` | novo | Cascata de OCR |
| `src/ingest/watcher.py` | novo | Watchdog de inbox |
| `src/ingest/cli.py` | novo | Entrypoint CLI |
| `src/ingest/extractors/*.py` | novos | Um por tipo |
| `src/dashboard/paginas/upload.py` | novo | Tela de upload |
| `src/integrations/gmail_docs.py` | refactor de `gmail_csv.py` | Genérico para docs |
| `mappings/gmail_filtros.yaml` | novo | Palavras-chave |
| `src/pipeline.py` | editar | Chama ingest antes do extract |
| `pyproject.toml` | editar | `watchdog`, `pillow-heif` opcional, `donut-python` opcional |

---

## Armadilhas

1. **HEIC no Linux** sem `pillow-heif` não abre. Marcar como opcional e avisar no `install.sh`.
2. **NFS-e varia por cidade**: começar só com layout de Brasília (onde moram). Outros municípios entram sob demanda.
3. **Tesseract em boletos**: layout gráfico confunde. Usar `pdfplumber` primeiro (quase sempre extrai linha digitável se for PDF nativo).
4. **Dedup por hash nem sempre basta**: mesmo boleto pode chegar como JPG e PDF. Hash será diferente, mas o documento é o mesmo. Segundo nível de dedup via linha digitável/chave NFe (Sprint 28 no grafo).
5. **Watchdog consumindo bateria**: desligável via `RUN_WATCHER=false` no `.env`. Documentar bem.
6. **Arquivos muito grandes** (PDF escaneado de 100 páginas): timeout generoso, logar warning.
7. **Claude Code para contratos**: extrair cláusulas de contratos via LLM é Sprint 29. Aqui deixar stub que retorna `{"status": "pendente_llm"}`.
8. **Segurança**: alguns documentos têm PII forte (CPF, endereço). Logs devem mascarar. Usar o `_mascarar_dados()` existente em `src/utils/logger.py`.

---

## Critério de sucesso

1. Jogar 10 PDFs variados (conta de luz, boleto escola, NFSe, fatura cartão, contrato) em `inbox/` -- todos viram entrada em `docs_processados.jsonl` com campos extraídos e `confianca >= 0.6` em 8 deles.
2. Upload pelo dashboard funciona: selecionar 3 arquivos, processar, ver resultado na mesma página.
3. Gmail puxa automaticamente anexos de emails com "fatura" ou "boleto" em assunto.
4. Watcher processa arquivo novo em menos de 5 segundos (PDFs pequenos <2MB).
5. Documentos já no projeto em `data/raw/andre/neoenergia/*` (se existirem) são reclassificados automaticamente sem intervenção.
6. Pipeline principal (`make process`) não regride: rodar duas vezes produz mesmo XLSX (idempotência).

---

## Dependências

- Esta é a **base** das sprints 28, 29, 30. Sem ela, documento não entra no sistema.
- Sprint 04 (Inteligência): extratores OCR de energia/água já existem, serão absorvidos em `fatura_utilitario_extractor.py`.
- Sprint 25 (Automação bancária): Gmail API já desenhada, vira fundação de `gmail_docs.py`.

---

## Decisão registrada

- **OCR externo (Google/AWS) permanecerá desligado por padrão.** Local First vale. Habilitar só se o usuário decidir e assumir o custo/privacidade.
- **Documentos contratuais terão extração heurística + LLM (Sprint 29).** Heurística sozinha é insuficiente.

---

*"O que não pode ser medido não pode ser gerenciado." -- Peter Drucker*
