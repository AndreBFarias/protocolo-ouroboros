---
concluida_em: 2026-04-24
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: F
  title: "Testes dedicados para 8 extratores bancários sem cobertura direta"
  depends_on:
    - sprint_id: 93
      artifact: "docs/auditoria_extratores_2026-04-23.md"
    - sprint_id: E
      artifact: "docs/auditoria_tecnica_2026-04-23.md §P1-02"
  touches:
    - path: tests/test_itau_pdf.py
      reason: "novo -- fixture sintética + parse de layout Itaú"
    - path: tests/test_santander_pdf.py
      reason: "novo -- fixture + parse do Santander Elite Visa 7342"
    - path: tests/test_c6_cc.py
      reason: "novo -- fixture XLS + decrypt msoffcrypto"
    - path: tests/test_c6_cartao.py
      reason: "novo -- fixture CSV layout C6 cartão"
    - path: tests/test_nubank_cartao.py
      reason: "novo -- fixture CSV date,title,amount (layout Nubank cartão)"
    - path: tests/test_nubank_cc.py
      reason: "novo -- fixture CSV Data,Valor,Identificador,Descrição (layout Nubank CC)"
    - path: tests/test_ofx_parser.py
      reason: "novo -- fixture OFX (Banking + CreditCard)"
    - path: tests/test_energia_ocr.py
      reason: "novo -- fixture PNG sintético + mock tesseract"
    - path: tests/fixtures/bancos/
      reason: "novo diretório com fixtures sintéticas por banco"
  forbidden:
    - "Usar arquivos reais do casal como fixtures (LGPD + reprodutibilidade)"
    - "Ativar testes @pytest.mark.slow no gauntlet regular -- fixtures binárias só rodam sob flag"
    - "Alterar código dos extratores durante esta sprint (primeiro testa, depois conserta em sprints-filhas)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "8 arquivos novos em tests/ (1 por extrator)"
    - "Cada arquivo com pelo menos 3 testes: parse básico, corner case (parcela/estorno/juros), layout inválido retorna lista vazia"
    - "Baseline de testes cresce de 1261 para >=1285 (+24 testes novos mínimo)"
    - "Fixtures sintéticas em tests/fixtures/bancos/<banco>/ sem dados reais"
    - "Zero regressão nos 1261 testes atuais"
    - "make smoke continua 8/8 contratos aritméticos"
```

---

# Sprint F — testes dedicados para extratores bancários

**Status:** BACKLOG (resolve P1-02 da Auditoria Técnica 2026-04-23)
**Prioridade:** P1 (cobertura mínima direta -- hoje só há cobertura indireta via test_deduplicator e test_pipeline_*)
**Tempo estimado:** ~3h (boa parte em criar fixtures)
**Origem:** `docs/auditoria_tecnica_2026-04-23.md` §P1-02 + `docs/auditoria_extratores_2026-04-23.md` (onde 8/9 bancos divergem em volume real)

## Problema

Auditoria 2026-04-23 identificou 8 extratores bancários sem teste dedicado:

| Extrator | tests/test_<nome>.py existe? |
|---|:-:|
| `c6_cartao.py` | NÃO |
| `c6_cc.py` | NÃO |
| `energia_ocr.py` | NÃO |
| `itau_pdf.py` | NÃO |
| `nubank_cartao.py` | NÃO |
| `nubank_cc.py` | NÃO |
| `ofx_parser.py` | NÃO |
| `santander_pdf.py` | NÃO |

Cobertura atual é INDIRETA via `tests/test_deduplicator.py`, `tests/test_pipeline_tipo_contrato.py`, `tests/test_transferencia_interna.py` -- não expõe bug de parser específico.

Sprint 93 expôs que 8/9 bancos têm delta não-zero entre extrator bruto e XLSX consolidado. Sem teste direto, regressão silenciosa é inevitável.

## Escopo

### Fase 1 -- Fixtures sintéticas (~1h)

Criar `tests/fixtures/bancos/<banco>/`:

- `nubank_cartao/sample.csv`: 3 linhas (compra, estorno, IOF).
- `nubank_cc/sample.csv`: 3 linhas (Pix recebido, Pix enviado, boleto).
- `c6_cartao/sample.csv`: 3 linhas (compra, cashback, juros).
- `c6_cc/sample_decrypted.xls`: XLS gerado em memória via `xlwt` (sem password, pré-decrypt) -- 3 linhas representativas.
- `itau_pdf/sample_texto.txt`: texto-proxy emulando output do pdfplumber (evita PDF binário no repo).
- `santander_pdf/sample_texto.txt`: idem.
- `ofx_parser/sample.ofx`: OFX sintético com `BANKTRANSLIST` + `CCSTMTRS`.
- `energia_ocr/sample_mock_output.txt`: saída textual esperada após tesseract.

**Critério:** fixture tem dados **sintéticos puros**, zero info real do casal. Valores e datas fictícios.

### Fase 2 -- Testes por extrator (~2h)

Cada arquivo de teste segue o padrão:

```python
"""Testes dedicados de <extrator> (Sprint F 2026-04-23).

Cobre: parse básico, corner cases específicos do layout, robustez com
entrada inválida. Não substitui test_deduplicator + test_pipeline_*
(cobertura integração); este é parse-unit.
"""

class TestParseBasico:
    def test_3_transacoes_sao_parseadas(self, fixture): ...
    def test_valores_convertidos_para_float(self, fixture): ...
    def test_datas_convertidas_para_date(self, fixture): ...

class TestCornerCases:
    def test_estorno_tem_valor_negativo_preservado(self): ...  # nubank
    def test_parcela_agrupa_corretamente(self): ...  # santander
    def test_fatura_com_iof_juros_multa(self): ...  # c6, itau

class TestEntradaInvalida:
    def test_arquivo_vazio_retorna_lista_vazia(self): ...
    def test_arquivo_corrompido_levanta_ou_loga(self): ...
```

Cada extrator recebe **mínimo 3 testes** (parse + corner + invalid). Meta: 24+ testes novos.

### Fase 3 -- Validação

- Run: `.venv/bin/pytest tests/test_itau_pdf.py tests/test_santander_pdf.py ... -v`
- Baseline geral: `.venv/bin/pytest tests/ -q` >= 1285 passed (1261 + 24).
- Smoke: 8/8 OK (nada de dados mudou, só testes novos).

## Fora do escopo (sprints-filhas candidatas)

- **Bugs descobertos pelos testes novos:** se algum teste falha expondo bug real do parser (ex: Santander ignorando linhas com cashback), registrar como sprint-filha `sprint_Fa_<banco>.md`, NÃO consertar aqui.
- **Testes @pytest.mark.slow** com PDFs reais: fica para sprint-filha opcional, com fixtures em branch não-default.

## Armadilhas

- **c6_cc usa XLS encriptado.** Fixture descriptografada sintética é OK para teste de parse; teste de decriptação deve usar fixture encriptada sintética gerada em memória (não commitar senha real no repo).
- **energia_ocr precisa mockar tesseract.** Usar `pytest-mock` para `pytesseract.image_to_string`.
- **OFX tem múltiplos schemas** (SGML, XML). Sprint 37 padronizou para encoding; fixture aqui cobre ambos.
- **Ordem de registro:** arquivos de teste seguem prefixo `test_<nome-do-arquivo-do-extrator>.py` para auto-discovery via pytest.

## Proof-of-work

- `ls tests/test_{itau,santander,c6_cc,c6_cartao,nubank_cartao,nubank_cc,ofx_parser,energia_ocr}*.py | wc -l` = 8.
- `.venv/bin/pytest tests/ -q` >= 1285 passed.
- `make smoke` 8/8 contratos OK.
- `git diff src/extractors/` = vazio (nenhum extrator alterado).

---

*"Sem teste direto, sem refactor honesto." -- princípio de cobertura como contrato*
