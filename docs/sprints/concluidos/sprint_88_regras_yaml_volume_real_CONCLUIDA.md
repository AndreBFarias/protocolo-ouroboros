## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 88
  title: "Ajuste de regras YAML de tipos_documento em volume real (27 arquivos do inbox/)"
  touches:
    - path: mappings/tipos_documento.yaml
      reason: "corrigir regex de das_mei; criar regras novas das_parcsn, certidao_receita_cnpj, extrato_c6_pdf; ajustar cupom_fiscal_foto"
    - path: mappings/inbox_routing.yaml
      reason: "registrar tipos novos na lista tipos_absorvidos"
    - path: tests/test_tipos_documento_sprint87.py
      reason: "6 testes com fixtures reais extraídas dos PDFs do inbox"
    - path: tests/test_intake_classifier.py
      reason: "atualizar baseline hardcoded de 18 para 21 tipos"
    - path: contexto/CONTEXTO.md
      reason: "registrar que André teve MEI (CNPJ 45.850.636) agora DESATIVADO com parcelamento ativo (25 parcelas)"
  forbidden:
    - "Alterar extratores existentes (cupom_termico_foto.py etc) -- ajuste é só em YAML + classifier"
    - "Remover regras existentes -- apenas adicionar/ajustar"
    - "Tocar grafo de produção (Sprint 88 é roteamento puro)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "./run.sh --inbox-dry"
  acceptance_criteria:
    - "das_mei regex ajustada: detecta 'DAS de (MEI|SIMEI)' como âncora distintiva de MEI ativo"
    - "Regra nova das_parcsn: 19 arquivos (17 'X PARCELA.pdf' + 2 'ExibirDAS-*.pdf') detectados"
    - "Regra nova certidao_receita_cnpj: 3 'ANDRE DA SILVA BATISTA DE FARIAS (N).pdf' detectados"
    - "Regra nova extrato_c6_pdf: 1 'extrato dos debitos.pdf' detectado"
    - "Regra ajustada cupom_fiscal_foto com âncoras OCR-tolerantes: 2 WhatsApp jpeg detectados"
    - "./run.sh --inbox-dry >=26/27 arquivos roteados (vs 1/27 antes)"
    - "Baseline de testes cresce: 1132 → 1137+ passed"
  proof_of_work_esperado: |
    # Antes
    ./run.sh --inbox-dry 2>&1 | grep -c 'skip_nao_identificado'   # = 26
    ./run.sh --inbox-dry 2>&1 | grep -c '\[move\]'                # = 1

    # Depois
    ./run.sh --inbox-dry 2>&1 | tee /tmp/sprint88_dry.log
    grep -c 'skip_nao_identificado' /tmp/sprint88_dry.log         # <= 1
    grep -c '\[move\]' /tmp/sprint88_dry.log                      # >= 26

    # Gauntlet
    make lint && .venv/bin/pytest tests/ -q && make smoke
```

---

# Sprint 88 — Ajuste de regras YAML em volume real

**Status:** BACKLOG
**Prioridade:** P1 (bloqueia Sprint 86.12 — ingestão em volume real)
**Dependências:** Sprint 70 (adapter), 87.4 (regras iniciais irpf_parcela/das_mei/comprovante_cpf)
**Origem:** dry-run 2026-04-24 revelou 26/27 arquivos em skip_nao_identificado

## Problema-raiz

Sprint 87.4 criou 3 regras (`irpf_parcela`, `das_mei`, `comprovante_cpf`) validadas com **fixtures sintéticas**. Em volume real (27 arquivos do inbox/), apenas `comprovante_cpf` detecta.

- **`das_mei`** regex exige `DAS\s*-?\s*Documento\s+de\s+Arrecada[çc][ãa]o` mas o layout real da Receita traz `Documento de Arrecadação / do Simples Nacional` sem "DAS" literal antes. "DAS" só aparece em "DAS de PARCSN" bem depois no corpo.
- **`irpf_parcela`** exige DARF + Receita Federal. Os 17 arquivos "X PARCELA.pdf" do inbox não são DARF nem IRPF — são DAS do parcelamento do MEI desativado do André (CNPJ 45.850.636/0001-60). Regra permanece, mas não casa.
- **Faltam regras** para: certidão CNPJ da Receita, extrato bancário C6 em PDF. E `.DEC` (binário proprietário IRPF) cai em skip_extensao (correto: sem parser OSS).

## Contexto descoberto pela auditoria

André teve MEI (CNPJ 45.850.636/0001-60, CNAE 5819-1/00 Edição, aberto 30/03/2022) hoje DESATIVADO. O parcelamento do Simples Nacional continua ativo em 25 parcelas (atualmente na 17ª). Isso precisa ser registrado em `contexto/CONTEXTO.md` porque:

1. Os 19 DAS PARCSN são do MEI desativado do André — destino `data/raw/andre/impostos/das_parcsn/`, não `vitoria/`.
2. CONTEXTO.md menciona apenas o MEI da Vitória (CNPJ 52.488.753); o projeto precisa saber que existem DOIS históricos MEI (um ativo: Vitória; um desativado em parcelamento: André).
3. Categorização IRPF/Imposto das transações bancárias do André que pagam essas parcelas precisa cruzar com esse contexto.

## Escopo (6 itens)

### 88.1 — Corrigir `das_mei` em `mappings/tipos_documento.yaml`

Regex nova (mais fiel ao layout real da Receita) exige `DAS de (MEI|SIMEI)` como âncora distintiva do MEI ativo. Sem isso, PARCSN poderia casar das_mei por terem "Documento de Arrecadação" + "Simples Nacional" em comum.

### 88.2 — Criar `das_parcsn` novo

Para os 19 arquivos de parcelamento do Simples Nacional. Âncora distintiva: "DAS de PARCSN" OU "PARCSN" OU "Parcelamento.*Simples" OU "Número do Parcelamento". Ordem em tipos_documento.yaml: `das_parcsn` ANTES de `das_mei` (âncora mais específica primeiro).

### 88.3 — Criar `certidao_receita_cnpj` novo

Para os 3 arquivos "ANDRE DA SILVA BATISTA DE FARIAS (N).pdf". Âncoras: "MINISTÉRIO DA FAZENDA" + "INFORMAÇÕES DE APOIO" OR "EMISSÃO DE CERTIDÃO" OR "PROCURADORIA-GERAL DA FAZENDA" + padrão CNPJ.

### 88.4 — Criar `extrato_c6_pdf` novo (diferenciado do extrator CSV)

"extrato dos debitos.pdf" do C6 (11 páginas) não tem extrator PDF no projeto (c6_cc.py processa CSV/XLS). Por ora roteamos para a pasta de extratos bancários para catalogação, sem extrator associado. Extrator PDF dedicado fica como sprint futura.

Âncoras: "Extrato exportado" OR "Extrato Período" + expressões específicas do C6 ("Saldo do dia", "CDB C6", "FAT CARTAO C6", "C6 LIM. GARANT").

### 88.5 — Ajustar `cupom_fiscal_foto` para OCR sujo

Os 2 WhatsApp jpeg são cupons fiscais fotografados pelo celular. OCR preview não retorna "CUPOM FISCAL" / "CCF" / "SAT" claramente (qualidade baixa). Adicionar âncoras OCR-tolerantes:

- `Tributos` OR `Consumidor` (palavras que sobrevivem no OCR de NFC-e)
- `78\d{11,12}` (código EAN-13/14 em cupons de mercado — marcador forte e estável)

### 88.6 — Atualizar contexto/CONTEXTO.md

Adicionar parágrafo sobre o MEI desativado do André (CNPJ 45.850.636) com parcelamento ativo. Distinguir do MEI ativo da Vitória (CNPJ 52.488.753).

## Proof-of-work obrigatório

```bash
# Antes (estado 2026-04-24)
./run.sh --inbox-dry 2>&1 | grep -c 'skip_nao_identificado'   # = 26
./run.sh --inbox-dry 2>&1 | grep -c '\[move\]'                # = 1

# Depois
./run.sh --inbox-dry 2>&1 | tee /tmp/sprint88_dry.log
grep -c 'skip_nao_identificado' /tmp/sprint88_dry.log         # <= 1
grep -c '\[move\]' /tmp/sprint88_dry.log                      # >= 26

# Detalhamento por tipo
grep -oE 'tipo=\S+' /tmp/sprint88_dry.log | sort | uniq -c

# Gauntlet
make lint                                                      # exit 0
.venv/bin/pytest tests/ -q                                     # >= 1137 passed
make smoke                                                     # 23/0 + 8/8
```

## Armadilhas

- **Ordem importa em YAML**: `das_parcsn` deve vir ANTES de `das_mei` (âncora mais específica primeiro).
- **inbox_routing.yaml lista `tipos_absorvidos`**: adicionar os ids novos (`das_parcsn`, `certidao_receita_cnpj`, `extrato_c6_pdf`) senão o adapter ignora mesmo com regra casando.
- **Simetria nome arquivo vs tipo**: "10ª PARCELA.pdf" pode parecer IRPF pelo nome mas é DAS PARCSN pelo conteúdo. Classifier confia em conteúdo (regex), não em nome. Correto.
- **Baseline hardcoded em test_intake_classifier.py**: `test_yaml_real_passa_validacao` tem `assert len(tipos) == 18`. Atualizar para 21 (15 + 3 Sprint 87.4 + 3 Sprint 88).

## Follow-up emitido

- **Sprint 89** — OCR pré-classificação para PDFs-imagem sem texto extraível. "notas de garantia e compras.pdf" do inbox/ é PDF composto por imagens puras (pdfplumber retorna 0 chars em 4 páginas). Fica em skip_nao_identificado mesmo após Sprint 88. Solução proposta: fallback OCR em `src/intake/preview.py` quando pdfplumber retorna vazio.

---

*"A regra é tão boa quanto o corpus que ela vê." -- lição empírica da sprint 88*
