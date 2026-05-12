---
id: INFRA-OPUS-SCHEMA-EXTENDIDO
titulo: Estender mappings/schema_opus_ocr.json para cobrir holerite, DAS, NFCe PDF, boleto, DANFE e extrato bancário
status: concluída
concluida_em: 2026-05-12  <!-- noqa: accent -->
prioridade: P0
data_criacao: 2026-05-12
fase: CONCLUSAO_REAL
depende_de: []
bloqueia: [INFRA-VALIDACAO-ARTESANAL-CUPOM, INFRA-VALIDACAO-ARTESANAL-HOLERITE, INFRA-VALIDACAO-ARTESANAL-NFCE, INFRA-VALIDACAO-ARTESANAL-DAS]  <!-- noqa: accent -->
esforco_estimado_horas: 2
origem: Plano 2026-05-12 secao Fase A0; schema atual cobre so foto-cupom; bloqueia validacao artesanal de outros tipos.  <!-- noqa: accent -->
adr_associada: ADR-26 (proposta -- Opus como OCR canonico para imagens)  <!-- noqa: accent -->
commit: ver `git log -- docs/sprints/concluidos/sprint_INFRA_opus_schema_extendido.md` para SHA exato do commit que conclui esta sprint.  <!-- noqa: accent -->
---

# Sprint INFRA-OPUS-SCHEMA-EXTENDIDO -- ampliar schema canônico Opus OCR

## Contexto

O schema `mappings/schema_opus_ocr.json` (criado pela Sprint INFRA-OCR-OPUS-VISAO em 2026-05-08) cobre apenas `tipo_documento ∈ {cupom_fiscal_foto, comprovante_pix_foto, recibo_foto, outro, pendente}`. Isso bloqueia a validação artesanal de outros tipos canônicos do ETL, porque o cache `data/output/opus_ocr_cache/<sha>.json` deve respeitar o schema declarado para manter idempotência via `src/extractors/opus_visao.py::extrair_via_opus()`.

Hoje há 9 pedidos pendentes em `data/output/opus_ocr_pendentes/` e 4 caches preenchidos. Próxima sessão precisa validar 2 amostras × 4 tipos (cupom, holerite, NFCe PDF, DAS PARCSN). Sem schema, validação artesanal não persiste.

## Objetivo

Estender `mappings/schema_opus_ocr.json` com:

1. Novos valores no enum `tipo_documento`: `holerite`, `das_parcsn`, `nfce_modelo_65`, `boleto_pdf`, `danfe_55`, `extrato_bancario_pdf`.
2. Blocos opcionais por tipo (`oneOf` ou `if-then-else` JSON Schema):
   - **holerite**: campos `proventos[]` (`codigo, descricao, referencia, valor`), `descontos[]` (`codigo, descricao, valor`), `liquido`, `competencia` (regex `^\d{4}-\d{2}$`), `empresa: {cnpj, razao_social}`, `funcionario: {cpf_mascarado, nome}`, `salario_base`, `base_inss`, `base_irrf`.
   - **das_parcsn**: campos `principal`, `multa`, `juros`, `codigo_barras` (47 dígitos), `vencimento` (ISO date), `competencia`, `contribuinte: {cpf_cnpj_mascarado}`, `numero_da_inscricao`.
   - **nfce_modelo_65**: campos `chave_44` (regex `^\d{44}$`), `xml_correlato_sha256` (opcional), `protocolo_autorizacao`, e `itens[]` com `ean` (string 13 dígitos ou `null`).
   - **boleto_pdf**: campos `linha_digitavel` (regex `^\d{47}$`), `vencimento`, `beneficiario: {nome, cnpj}`, `valor_documento`, `valor_pago` (opcional), `nosso_numero`, `instrucoes` (string).
   - **danfe_55**: campos `chave_44`, `protocolo_autorizacao`, `transporte: {transportadora, placa_veiculo}` (opcional), `itens[]` com `ean` ou `null`, `valor_frete`, `valor_seguro`.
   - **extrato_bancario_pdf**: campos `banco`, `agencia`, `conta`, `periodo: {inicio, fim}`, `saldo_inicial`, `saldo_final`, `lancamentos[]` com `data, descricao, valor_assinado, saldo_apos`.
3. Atualizar `additionalProperties: false` nos blocos para travar drift de schema.
4. Atualizar regex de `data_emissao` aceitando ISO date OU ISO datetime.
5. Manter retrocompatibilidade: schema antigo continua válido (`tipo_documento ∈ {cupom_fiscal_foto, comprovante_pix_foto, recibo_foto, outro, pendente}` permanece aceito).

## Validação ANTES (grep -- padrão (k))

```bash
cat mappings/schema_opus_ocr.json | head -40
grep -n "tipo_documento" mappings/schema_opus_ocr.json
ls data/output/opus_ocr_cache/ | wc -l    # esperado: 4
ls data/output/opus_ocr_pendentes/ | wc -l # esperado: 9
.venv/bin/python -c "import jsonschema, json; jsonschema.Draft202012Validator.check_schema(json.load(open('mappings/schema_opus_ocr.json'))); print('schema atual valido')"
```

Confirma que: (a) schema atual existe e é Draft-2020-12-válido, (b) cache tem 4 entradas a preservar, (c) há 9 pedidos pendentes a popular após esta sprint.

## Não-objetivos (padrão (t))

- **NÃO** mexer em `src/extractors/opus_visao.py` — schema é dado, função é estável.
- **NÃO** alterar os 4 caches existentes em `data/output/opus_ocr_cache/` — eles devem continuar válidos sob o schema estendido (retrocompat hard).
- **NÃO** mudar o cálculo de `sha256` — chave de cache permanece a mesma.
- **NÃO** chamar Anthropic API. ADR-13 inviolável.
- **NÃO** redactar PII no schema; mascaramento é responsabilidade do produtor (`extrair_via_opus`) ou consumidor (relatório), não da camada de validação.
- **NÃO** criar arquivos `.py` novos — só editar JSON Schema.

## Spec de implementação

Edit em `mappings/schema_opus_ocr.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Opus OCR Schema -- protocolo-ouroboros",
  "type": "object",
  "required": ["sha256", "tipo_documento", "extraido_via", "ts_extraido"],
  "properties": {
    "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
    "tipo_documento": {
      "type": "string",
      "enum": [
        "cupom_fiscal_foto", "comprovante_pix_foto", "recibo_foto",
        "holerite", "das_parcsn", "nfce_modelo_65", "boleto_pdf",
        "danfe_55", "extrato_bancario_pdf",
        "outro", "pendente"
      ]
    },
    ... (campos comuns: estabelecimento, data_emissao, total, extraido_via, ts_extraido, aguardando_supervisor, confianca_global)
  },
  "allOf": [
    {
      "if": {"properties": {"tipo_documento": {"const": "holerite"}}},
      "then": {
        "required": ["proventos", "descontos", "liquido", "competencia"],
        "properties": {
          "proventos": {"type": "array", "items": {...}},
          "descontos": {"type": "array", "items": {...}},
          ...
        }
      }
    },
    ... (blocos análogos para das_parcsn, nfce, boleto, danfe, extrato)
  ]
}
```

Padronizar `additionalProperties: false` em cada bloco condicional para evitar drift silencioso.

## Proof-of-work (padrão (u))

```bash
# 1. Validar schema é Draft-2020-12 valido
.venv/bin/python -c "import jsonschema, json; jsonschema.Draft202012Validator.check_schema(json.load(open('mappings/schema_opus_ocr.json'))); print('OK')"

# 2. Validar cada cache existente permanece válido sob schema estendido (retrocompat)
.venv/bin/python -c "
import jsonschema, json, glob
schema = json.load(open('mappings/schema_opus_ocr.json'))
caches = sorted(glob.glob('data/output/opus_ocr_cache/*.json'))
print(f'cache files: {len(caches)}')
for c in caches:
    payload = json.load(open(c))
    jsonschema.validate(payload, schema)
    print(f'  OK: {c}')
"
# Esperado: 4 caches passam sem erro.

# 3. Validar exemplo sintetico de cada novo tipo (criar em tests/fixtures/opus_ocr_schemas/)
.venv/bin/pytest tests/test_opus_ocr_schema.py -q

# 4. Gauntlet padrao
make lint && make smoke
```

## Critério de aceitação (gate (z))

1. `mappings/schema_opus_ocr.json` declara enum `tipo_documento` com 11 valores (5 antigos + 6 novos).
2. 4 caches existentes em `data/output/opus_ocr_cache/` permanecem 100% válidos sob o schema estendido (zero falsos negativos de retrocompat).
3. 6 fixtures sintéticas em `tests/fixtures/opus_ocr_schemas/<tipo>.json` validam contra schema (1 por novo tipo).
4. `tests/test_opus_ocr_schema.py` (novo) verifica retrocompat + novos tipos. Mínimo 12 testes (validação positiva e negativa por tipo).
5. `make lint` exit 0. `make smoke` 10/10. `pytest -q` baseline ≥ 2752.
6. Pytest baseline cresce de 2752 para ≥ 2764 (+12 testes novos).
7. Spec movida para `docs/sprints/concluidos/` com frontmatter `concluida_em: 2026-MM-DD` + `commit: <sha>` na sessão de execução.

## Referência

- Spec dependente (pai): `docs/sprints/concluidos/sprint_INFRA_ocr_opus_visao.md` (commit `d7f8805`).
- Plano de origem: `~/.claude/plans/preciso-que-use-o-crispy-stroustrup.md` Fase A0.
- Schema atual: `mappings/schema_opus_ocr.json` (criado em commit `0efe0ef`).
- ADR-26 (proposta — formalizar Opus como OCR canônico): `docs/auditorias/ESTADO_DO_TODO_2026-05-08.md` seção 5.

*"Schema fechado é contrato; schema aberto é incertezza acumulada." — princípio INFRA-OPUS-SCHEMA-EXTENDIDO*
