# ADR-15: Intake Universal Multiformato

## Status: Aceita

## Contexto

Até a Sprint 22, a inbox do projeto aceitava apenas CSV, XLSX, XLS, PDF e OFX — estendido em `src/inbox_processor.py:14` (`EXTENSOES_SUPORTADAS`). Essa lista exclui as fontes dominantes da vida real do usuário:

- **JPG/PNG/HEIC** — fotos de cupom fiscal térmico, recibo não-fiscal, receita médica em papel, certificado de garantia em papel
- **XML** — NFe estruturada
- **EML** — garantias que chegam por e-mail
- **TXT** — notas estruturadas exportadas de alguns PDVs
- **ZIP** — conjuntos de NFs baixadas do portal da Receita ou e-mail compactado

A consequência é que o usuário precisa pré-classificar e converter arquivos antes de jogar na inbox. A fricção mata a adoção diária.

A visão do catalogador universal exige que **qualquer arquivo do dia a dia possa ir pra inbox sem pré-processamento**. A detecção de tipo, classificação e roteamento para a pasta certa são responsabilidade do sistema.

Alternativas avaliadas:
- **Extensão do `EXTENSOES_SUPORTADAS`:** simples mas não resolve — detectar tipo de JPG exige inspeção do conteúdo, não do nome.
- **Camada nova `src/intake/classifier.py`:** dedicada a classificar "que tipo de documento é esse?" usando heurísticas determinísticas (MIME, regex em OCR preview, cabeçalhos XML) com fallback para supervisor artesanal (Claude Opus via sessão).
- **Deixar a responsabilidade no extrator:** cada extrator tenta processar o arquivo; o primeiro que aceita vence. Explode combinatoriamente e acopla detecção a extração.

## Decisão

Implementar **Intake Universal Multiformato** como camada separada (Sprint 41):

1. **Extensões suportadas** passam a incluir: `.csv .xlsx .xls .pdf .ofx .jpg .jpeg .png .heic .xml .eml .txt .zip`. ZIP é expandido recursivamente na entrada.

2. **`src/intake/classifier.py`** (novo) decide o `tipo_documento` de cada arquivo via cascata:
   - **MIME / magic bytes** (via `python-magic` ou heurística manual) para categorizar em {imagem, pdf, planilha, texto, xml, email, zip}
   - **Conteúdo** — pra imagens e PDFs, preview do texto (OCR rápido com tesseract ou `pdfplumber.extract_text`) é matched contra regex catalogadas em `mappings/tipos_documento.yaml`
   - **Fallback supervisor** — se nenhuma regra casa, o arquivo vai pra `data/raw/_classificar/` e uma proposta é aberta em `docs/propostas/classificar/<arquivo>.md` para o Claude Code resolver interativamente com o humano

3. **Tipos de documento reconhecidos** (extensível via `mappings/tipos_documento.yaml`):
   - `extrato_bancario` → `data/raw/{pessoa}/{banco}_{produto}/`
   - `fatura_cartao` → `data/raw/{pessoa}/{banco}_cartao/`
   - `danfe_nfe` → `data/raw/{pessoa}/nfs_fiscais/`
   - `cupom_fiscal` → `data/raw/{pessoa}/nfs_fiscais/`
   - `xml_nfe` → `data/raw/{pessoa}/nfs_fiscais/xml/`
   - `recibo` → `data/raw/{pessoa}/recibos/`
   - `holerite` → `data/raw/{pessoa}/holerites/`
   - `receita_medica` → `data/raw/{pessoa}/saude/receitas/`
   - `garantia` → `data/raw/{pessoa}/garantias/`
   - `conta_luz` → `data/raw/{pessoa}/contas/energia/`
   - `conta_agua` → `data/raw/{pessoa}/contas/agua/`
   - `boleto_servico` → `data/raw/{pessoa}/boletos/`
   - `contrato` → `data/raw/{pessoa}/contratos/`

4. **Regra de renomeação determinística** por tipo, documentada em `docs/CONVENCOES_NOMES.md`. Ex: NF → `NF_YYYYMMDD_<FORNECEDOR>_<NUMERO>.pdf`; holerite → `HOLERITE_YYYYMM_<EMPRESA>.pdf`.

5. **Fallback de detecção de pessoa**: hoje via caminho (`data/raw/andre/...`). Mantido. Para inbox flat (sem subpasta de pessoa), o classificador infere via conteúdo (CPF, nome do titular em extrato) ou deposita em `_classificar/` pedindo proposta.

6. **ZIP**: descompactação recursiva ao entrar, cada arquivo interno roteado individualmente. Arquivo ZIP original vai pra `data/raw/_zipados/` com referência no grafo.

7. **EML**: parser extrai anexos; anexos viram arquivos na inbox; corpo do e-mail vira documento tipo `email_transacional` linkado aos anexos.

## Consequências

**Positivas:**
- O usuário joga QUALQUER arquivo na inbox sem pensar — a arquitetura prometida.
- Roteamento determinístico é auditável (`mappings/tipos_documento.yaml`).
- Casos de borda viram propostas explícitas, nunca falhas silenciosas.
- Compatível com o workflow do supervisor artesanal (ADR-13).

**Negativas:**
- `python-magic` é dep nova (ou fallback manual). Sprint 41 decide.
- HEIC exige pillow-heif ou conversão via `imagemagick`; dep adicional.
- OCR preview de imagem é custoso em lote — mitigado por cache em `data/cache/ocr/`.
- `data/raw/_classificar/` pode crescer se o usuário jogar muitos arquivos não cobertos por regra.

## Relações com outras decisões

- Depende implicitamente do ADR-07 (Local First) — todos os arquivos ficam no disco local.
- Compatível com ADR-11 (Classificação em Camadas) — a classificação de tipo usa a mesma hierarquia "regra determinística > fallback LLM (supervisor)".
- Pré-requisito das sprints 44-47b (extratores de documento): cada extrator assume que o arquivo já chegou classificado e na pasta certa.

---

*"A inteligência começa em abrir a porta para qualquer visitante."* -- princípio de hospitalidade
