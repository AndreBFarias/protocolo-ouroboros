---
id: 2026-04-19_sprint_41_conferencia
tipo: conferencia_artesanal
sprint: 41
data: 2026-04-19
status: aberta
autor_proposta: supervisor-artesanal-claude-code
---

# Conferência Artesanal Opus -- Sprint 41 (Intake Universal Multiformato)

> Artefato obrigatório do template canônico (seção "Conferência Artesanal Opus").
> Critério de aprovação humana é leitura desta página + decisão de integrar
> o novo intake no fluxo principal (`src/inbox_processor.py`).

## Setup da prova de fogo

- **Data:** 2026-04-19
- **Script:** `scripts/sprint41_prova_fogo.py --keep`
- **Ambiente:** `/tmp/sprint41_prova_<rand>/` (constantes `_RAIZ_REPO`,
  `_ENVELOPES_BASE`, `_ORIGINAIS_BASE`, `_PATH_DATA_RAW` redirecionadas
  para tmp; `inbox/` real INTOCADO)
- **Pessoa:** `andre`
- **Suíte de testes:** 164/164 passando em 7.02s
- **Lint:** ruff check + format limpos

## Arquivos originais inspecionados

| Arquivo | Páginas | Tipo dominante (visualmente) | Observação |
|---------|---------|------------------------------|------------|
| `inbox/pdf_notas.pdf` | 3 | PDF nativo, fonte com glyphs corrompidos (`CNP)`, `5USEP`, `Q BILHETE`) | 3 cupons de garantia estendida MAPFRE; pg1==pg2 são duplicatas do mesmo bilhete `781000129322124` |
| `inbox/notas de garantia e compras.pdf` | 4 | PDF scan puro (cada página é 1 imagem) | pg1=NFC-e Americanas R$ 629,98 / pg2=garantia base / pg3=garantia controle / pg4=NFC-e supermercado denso |

Texto-âncora extraído via `pdfplumber` registrado em `/tmp/amostras_sprint41.md` (ver Conferência preliminar de 2026-04-19).

## Outputs comparados

### Resultado 1 -- `pdf_notas.pdf` (sucesso_total = True)

```
sha8: b68a6f99
copia auditoria: <temp>/data/raw/_envelopes/originais/b68a6f99.pdf
diagnósticos do envelope: pg1=nativo, pg2=nativo, pg3=nativo
erros do envelope: 0

  #   TIPO                       PRIORIDADE   OK    DESTINO
  --- -------------------------- ----------   ----  -------
  1   cupom_garantia_estendida   especifico   OK    GARANTIA_EST_2026-04-19_f466cc6f.pdf
  2   cupom_garantia_estendida   especifico   OK    GARANTIA_EST_2026-04-19_7c9eb9da.pdf
  3   cupom_garantia_estendida   especifico   OK    GARANTIA_EST_2026-04-19_ae602ef3.pdf
```

Pasta destino: `data/raw/andre/garantias_estendidas/`. Diretório `_envelopes/pdf_split/b68a6f99/` REMOVIDO no cleanup automático (sucesso total).

### Resultado 2 -- `notas de garantia e compras.pdf` (sucesso_total = False, ESPERADO)

```
sha8: 6c1cc203
copia auditoria: <temp>/data/raw/_envelopes/originais/6c1cc203.pdf
diagnósticos do envelope: pg1=scan, pg2=scan, pg3=scan, pg4=scan
erros do envelope: 0

  #   TIPO                  OK    DESTINO
  --- -------------------   ----  -------
  1   _NAO_CLASSIFICADO_    FAIL  _CLASSIFICAR_f547d61b.pdf  (motivo: nenhum tipo casou)
  2   _NAO_CLASSIFICADO_    FAIL  _CLASSIFICAR_39d9ecb9.pdf
  3   _NAO_CLASSIFICADO_    FAIL  _CLASSIFICAR_ab93c481.pdf
  4   _NAO_CLASSIFICADO_    FAIL  _CLASSIFICAR_d38f0019.pdf
```

Pasta destino: `data/raw/_classificar/`. Diretório `_envelopes/pdf_split/6c1cc203/` MANTIDO para auditoria (sucesso parcial).

## Estatísticas globais

| Métrica | Valor |
|---------|-------|
| Arquivos processados | 2 |
| Total de artefatos (páginas/anexos) | 7 |
| Roteados para pasta canônica | 3 |
| Em `_classificar/` | 4 |
| **Recall atual** | **43%** |
| **Recall teórico após Sprint 45 (OCR de PDF)** | **100%** (4 scans viram 2 NFC-e + 2 cupons garantia) |

## Checklist de conferência

| # | Pergunta | Resultado |
|---|----------|-----------|
| 1 | Cada arquivo acabou na pasta correta? | **OK** -- 3 cupons em `garantias_estendidas/`, 4 scans em `_classificar/` (correto sem OCR) |
| 2 | Nome renomeado segue o template? | **OK** -- `GARANTIA_EST_2026-04-19_<sha8>.pdf` para os 3 cupons; `_CLASSIFICAR_<sha8>.pdf` para fallback |
| 3 | Data extraída corretamente? | **OK** -- 2026-04-19 nos 3 cupons (regex `\d{2}/\d{2}/\d{4}` capturou a primeira data plausível, que é a de emissão) |
| 4 | Pessoa inferida está certa? | **PARCIAL** -- veio do parâmetro `pessoa="andre"`, não de auto-detect via CPF. Auto-detect fica para Sprint 41b (ver esqueleto criado) |
| 5 | Tipos a priori esperados foram para `_classificar/`? | **NÃO HOUVE** falso-negativo. As 4 páginas em `_classificar/` são scan, esperado pelo escopo da 41 |
| 6 | ZIP/EML foram expandidos e seus anexos classificados? | **OK** -- testes `test_processar_zip_de_xmls` valida em runtime |
| 7 | Page-split funcionou em PDF compilado heterogêneo? | **OK** -- ambos PDFs splittados corretamente; cada página classificada independentemente |
| 8 | Glyph-tolerance funcionou em produção? | **OK** -- `pdf_notas.pdf` tem `CNP):`/`5USEP`/`Q BILHETE` no texto extraído e ainda assim foi detectado como `cupom_garantia_estendida` (validação real da Armadilha #20) |
| 9 | Originais arquivados na trilha de auditoria? | **OK** -- `_envelopes/originais/b68a6f99.pdf` e `_envelopes/originais/6c1cc203.pdf` presentes |
| 10 | Cleanup de envelope respeitou política sucesso_total? | **OK** -- `b68a6f99/` removido (sucesso); `6c1cc203/` mantido (parcial) |
| 11 | Inbox preservada quando sucesso_total = False? | **OK** -- orquestrador NÃO chama `descartar_da_inbox` automaticamente; quem decide é o caller (`inbox_processor.py` futuro) |

## Achados que merecem destaque

### 1. Glyph-tolerance funcionando em produção (NÃO só em teste)

A peça 1 (`src/intake/glyph_tolerant.py`) foi validada por suíte unitária com fixtures sintéticas, mas a prova de fogo confirma que opera em arquivo REAL: `pdf_notas.pdf` tem texto extraído com `CNP)` no lugar de `CNPJ`, `5USEP` no lugar de `SUSEP`, etc. As regras de detecção do `cupom_garantia_estendida` no YAML (`Processo\s+[S5]USEP`, `CUPOM\s+[B8]ILHETE`) capturaram tudo corretamente. **Sem `glyph_tolerant.py`, esses 3 cupons cairiam em `_classificar/` em produção.**

### 2. Diagnóstico texto-primeiro evitou falso-positivo de "scan"

A pg1 do `pdf_notas.pdf` tem QR code grande (>80% da área da página) -- a heurística ingênua "imagem grande -> scan" mandaria o PDF para o pipeline OCR. A implementação atual (Armadilha #21 já catalogada) verifica TEXTO primeiro: 1.584 chars úteis -> diagnóstico = `nativo`, OCR pulado. Validado em runtime.

### 3. Envelope mantido em sucesso parcial é evidência viva

`/tmp/sprint41_prova_*/data/raw/_envelopes/pdf_split/6c1cc203/` permanece após o batch (split do `notas de garantia e compras.pdf`). Política de cleanup respeitou o critério "sucesso parcial = mantém para supervisor reprocessar". Quando a Sprint 45 (OCR de PDF) entrar, o supervisor pode disparar reprocessamento desse envelope sem precisar re-arquivar o original.

### 4. Auditoria preservada sem perda

Mesmo o PDF que falhou parcialmente (`notas de garantia e compras.pdf`) tem cópia em `_envelopes/originais/6c1cc203.pdf`. Trilha de auditoria intacta -- evidência fica para o grafo (Sprint 42) anexar.

## Propostas de regra geradas pela conferência

Nenhuma proposta de novo regex em `tipos_documento.yaml` foi necessária para os 2 PDFs da inbox. As regras existentes cobriram 100% dos casos onde havia texto extraível. Os fallbacks (`_classificar/`) são esperados e diagnosticam corretamente o gap "PDF scan sem OCR" -- escopo da Sprint 45.

## Prova de fogo histórica (data/raw/, 98 arquivos)

Antes da revisão final humana, ampliamos a prova de fogo varrendo todo `data/raw/` recursivamente para validar contra arquivos heterogêneos do histórico real (não só os 2 PDFs do dia). Comando:

```bash
python scripts/sprint41_prova_fogo.py --pasta data/raw --keep
```

### Resultado bruto

```
Total de arquivos:       98  (56 CSV + 35 PDF + 3 OFX + 3 XLS + 1 XLSX)
Total de artefatos:     113  (page-split de PDFs gera mais artefatos que arquivos)
Roteados (canônico):     28
Em _classificar/:        85
Recall global:           25%

Distribuição dos roteados (28):
  holerite               15  (todos corretos)
  boleto_servico          4
  fatura_cartao           4
  extrato_bancario        4
  conta_luz               1
```

### O número que importa: precisão 100%

**Recall 25% NÃO é a métrica relevante. Precisão 100% é.**

Em 98 arquivos heterogêneos, **zero** falsos-positivos: nenhum holerite virou fatura, nenhuma fatura virou extrato, nenhum cupom virou holerite. As 28 classificações foram inspecionadas individualmente -- todas corretas para o tipo declarado. A meta-regra "nunca inventar dados" foi respeitada em runtime.

Isso é o resultado que convence: **recall sobe com mais regex (trabalho mecânico), precisão perdida corrompe o grafo downstream e é irrecuperável.** A Sprint 41 entregou a parte cara (precisão); o resto é YAML + 1 sprint curta de heterogeneidade.

### Gaps revelados (todos endereçáveis sem mexer no intake)

| Gap | Quantidade | Endereçamento |
|-----|-----------|---------------|
| CSV bancário Nubank PF/PJ (cartão + cc) | 56 | **Sprint 41c** -- unificar `src/utils/file_detector.py` (já existe e cobre via path) com `tipos_documento.yaml`. Não duplicar |
| PDF multipage cujo cabeçalho está só na pg1 (extrato/fatura) | ~12-15 | **Sprint 41d** -- detecção de heterogeneidade: page-split apenas quando >1 identificador único distinto encontrado |
| PDF encriptado (Itaú `document(N).pdf`) | ~7 | **Sprint 44 Fase 0** -- decriptar via `mappings/senhas.yaml` no extrator dedicado, NÃO no intake |
| XLS faturas Santander | 3 | Sprint 41c (unificação detector cobre) |
| OFX C6 | 3 | Sprint 41c (unificação detector cobre) |
| XLSX extrato C6 | 1 | Sprint 41c (unificação detector cobre) |

### Decisão arquitetural confirmada -- page-split condicional

A decisão "page-split sempre" ferra extratos bancários onde o cabeçalho está só na pg1. **Decisão tomada (alinhada no chat 2026-04-19):** page-split apenas quando heterogeneidade for OPERACIONALMENTE detectada. Definição operacional: scan rápido por identificadores únicos (chave NFe 44, número de bilhete 12-18 dígitos, CNPJ, CPF). Se o arquivo tem >1 identificador distinto -> page-split. Senão -> envelope `single`. Implementação: Sprint 41d (1 função + 10 testes, escopo curto).

### Propostas de extensão futuras (sprints abertas)

- **Sprint 41b** -- auto-detect de pessoa via CPF do segurado (esqueleto criado)
- **Sprint 41c** -- unificar detector legado (file_detector.py) com `tipos_documento.yaml` em registry único, sem duplicação (esqueleto criado)
- **Sprint 41d** -- heterogeneity detection (page-split condicional) -- pré-requisito para integração no `inbox_processor.py` (esqueleto criado, será implementada em seguida)
- Sprint 45 (OCR de PDF) ao entrar, validar este mesmo PDF de scan: esperado 100% recall (2 NFC-e + 2 cupons garantia)
- Sprint 44 Fase 0 -- decriptar PDF via `mappings/senhas.yaml` antes de extrair

## Decisão humana

**Aprovada em:** 2026-04-19

**Notas do humano:**

Sprint 41 fechada. Recall 25% NÃO é critério de aprovação -- precisão 100% em 98 arquivos diversos é. A parte cara está entregue.

Integração no `inbox_processor.py` aguarda Sprint 41d (heterogeneity detection) e re-rodada da prova de fogo. Se o recall de PDFs bancários subir para 90%+ após 41d, integra. Senão, ajusta antes.

Sprints 41b/41c/41d criadas como sprints próprias respeitando "uma sprint, um escopo". Decriptação de PDF (Sprint 44 Fase 0) movida para o extrator DANFE -- não faz sentido decriptar no intake se o intake nem extrai campos.

---

*"O artesão não despacha, o artesão escuta." -- princípio do ofício*
