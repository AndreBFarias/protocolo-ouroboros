---
id: INFRA-PDF-TIMEOUT
titulo: "PDFs corrompidos podem hangar pipeline indefinidamente (pdfplumber sem timeout)"
status: concluída
concluida_em: 2026-05-17
prioridade: P2
data_criacao: 2026-05-17
fase: ROBUSTEZ
epico: 2
depende_de: []
esforco_estimado_horas: 1
origem: "auditoria independente 2026-05-17. `pdfplumber.open(caminho)` em vários extratores (danfe_pdf.py, garantia.py, contracheque_pdf.py, etc) não tem timeout. Se PDF corrompido ou muito grande (>50MB), Pipeline ETL pode travar indefinidamente. ETL `./run.sh --tudo` é serial — uma travada bloqueia o pipeline inteiro."
---

# Sprint INFRA-PDF-TIMEOUT

## Contexto

10+ extratores usam pdfplumber sem proteção de timeout:

```python
import pdfplumber
with pdfplumber.open(caminho) as pdf:
    texto = pdf.pages[0].extract_text()
```

PDF corrompido ou muito grande pode causar:
- Hang indefinido (pdfminer parsing loop).
- Memória explodindo (PDFs com milhões de paths).
- Crash do pipeline inteiro porque é serial.

Hoje não há defesa. Apenas log de erro se exceção ocorrer — não há "deu timeout, pulei".

## Hipótese e validação ANTES

```bash
grep -rn "pdfplumber.open" src/extractors/ | wc -l
# Esperado: 10+

# Procurar mecanismo de timeout existente:
grep -rn "signal\|timeout\|SIGALRM" src/extractors/ | head -5
# Esperado: 0 hits
```

## Objetivo

1. **Helper `src/extractors/_pdf_timeout.py`** (NOVO):
   ```python
   import signal
   from contextlib import contextmanager

   @contextmanager
   def pdf_timeout(segundos: int = 30):
       """Context manager que aborta via signal se demorar mais que N segundos."""
       def handler(signum, frame):
           raise TimeoutError(f"PDF processing excedeu {segundos}s")
       old = signal.signal(signal.SIGALRM, handler)
       signal.alarm(segundos)
       try:
           yield
       finally:
           signal.alarm(0)
           signal.signal(signal.SIGALRM, old)
   ```

2. **Wrap em extratores** usando pdfplumber:
   ```python
   from src.extractors._pdf_timeout import pdf_timeout
   try:
       with pdf_timeout(30):
           with pdfplumber.open(caminho) as pdf:
               ...
   except TimeoutError:
       logger.error("PDF %s travou; pulando", caminho)
       return {}
   ```

3. **Limite configurável** via env var `OUROBOROS_PDF_TIMEOUT=30` (default).

4. **Skip-log** `data/output/pdfs_pulados_timeout_<ts>.json` para auditoria.

5. **Testes regressivos**:
   - `test_pdf_timeout_aborta_em_segundos_excedidos` (PDF que dorme via mock)
   - `test_pdf_timeout_passa_em_pdf_normal`
   - `test_pdf_timeout_skip_log_grava_path`

## Não-objetivos

- Não rodar timeout em processos não-PDF.
- Não implementar fork/multiprocess (overhead alto para um signal).
- Linux/macOS only: `signal.SIGALRM` não está disponível no Windows. Documentar.

## Proof-of-work runtime-real

```bash
# Teste com PDF sintético "lento":
.venv/bin/python -c "
from src.extractors._pdf_timeout import pdf_timeout
import time
try:
    with pdf_timeout(2):
        time.sleep(5)
except TimeoutError as e:
    print(f'OK abortou: {e}')
"
# Esperado: TimeoutError em ~2s, não 5s
```

## Acceptance

- `src/extractors/_pdf_timeout.py` criado.
- 5+ extratores usam o helper.
- 3 testes regressivos verdes.
- `OUROBOROS_PDF_TIMEOUT` documentado em `docs/BOOTSTRAP.md`.

## Padrões aplicáveis

- (n) Defesa em camadas — try/except continua existindo.
- (e) PII never in INFO — só path no log.
- (m) Branch reversível — timeout não corrompe estado.

---

*"Pipeline serial morre em 1 travada; timeout é o despertador honesto." — princípio do crash predictable*
