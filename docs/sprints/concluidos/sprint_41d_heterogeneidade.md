---
concluida_em: 2026-04-20
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 41d
  title: "Heterogeneity Detection: page-split condicional baseado em identificadores únicos"
  touches:
    - path: src/intake/heterogeneidade.py
      reason: "novo módulo: detecta se PDF tem >1 documento lógico distinto via scan de identificadores únicos (chave NFe 44, bilhete 12-18 dígitos, CNPJ, CPF). Retorna boolean."
    - path: src/intake/orchestrator.py
      reason: "passa a chamar `e_heterogeneo(pdf)` ANTES de decidir entre expandir_pdf_multipage (heterogeneo) e _envelope_single_file (homogeneo)"
    - path: src/intake/extractors_envelope.py
      reason: "expandir_pdf_multipage continua existindo igual; orchestrator decide quando chamar"
    - path: tests/test_intake_heterogeneidade.py
      reason: "10 testes: PDFs reais (pdf_notas heterogeneo, hipotético extrato bancário homogeneo) + sintéticos"
  n_to_n_pairs:
    - [src/intake/heterogeneidade.py, src/intake/orchestrator.py]
  forbidden:
    - src/intake/classifier.py  # heterogeneidade é decisão SEPARADA da decisão de tipo
    - src/intake/extractors_envelope.py  # já está pronto; só muda quem chama
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_intake_heterogeneidade.py tests/test_intake_orchestrator.py -x -q"
      timeout: 120
  acceptance_criteria:
    - "src/intake/heterogeneidade.py:e_heterogeneo(pdf_path) -> bool"
    - "Definição operacional: PDF é heterogeneo se >= 2 identificadores únicos DISTINTOS aparecem em páginas distintas (chave NFe 44, número de bilhete 12-18 dígitos, CNPJ, CPF)"
    - "PDF com 3 cupons de garantia (3 bilhetes diferentes em pgs distintas) -> True"
    - "PDF com extrato bancário de 4 páginas (mesmo CNPJ no header da pg1, sem outros identificadores nas pgs 2-4) -> False"
    - "PDF com 1 página só (qualquer conteúdo) -> False"
    - "PDF compilado mistuando NFC-e + cupons garantia (>1 chave NFe + >1 bilhete) -> True"
    - "Orquestrador: heterogeneo -> expandir_pdf_multipage; homogeneo -> _envelope_single_file"
    - "PROVA DE FOGO histórica em data/raw/ atinge >= 60% recall (sobe dos 25% pré-41d apenas pela mudança de page-split; YAML continua incompleto -- 95% só com 41c)"
    - "Acentuação PT-BR correta, zero emojis, zero menções a IA"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 41d -- Heterogeneity Detection

**Status:** CONCLUÍDA
**Data:** 2026-04-19 (criada após prova de fogo histórica da Sprint 41 -- gap revelado: PDFs multipage com cabeçalho só na pg1 perdem cobertura porque page-split classifica cada página independentemente)
**Prioridade:** ALTA
**Tipo:** Feature
**Dependências:** Sprint 41 (envelope + orchestrator implementados)
**Desbloqueia:** integração final do intake no `inbox_processor.py` (extratos/faturas bancárias deixam de fragmentar)
**Issue:** --
**ADR:** ADR-15 (intake multiformato)

---

## Como Executar

- `.venv/bin/pytest tests/test_intake_heterogeneidade.py -v`
- `python scripts/sprint41_prova_fogo.py --pasta data/raw --keep` (pós-implementação, recall >= 60%)

### O que NÃO fazer

- NÃO usar heurística frouxa tipo "número de páginas > N" para decidir heterogeneidade. Definição precisa ser operacional, baseada em CONTEÚDO -- caso contrário vira chute.
- NÃO duplicar leitura do PDF: o page-split já lê a primeira vez via pikepdf+pdfplumber. A detecção de heterogeneidade deve aproveitar esse mesmo pass quando possível, ou abrir UMA vez extra no máximo.
- NÃO mudar `extractors_envelope.py` -- ele continua expondo `expandir_pdf_multipage` igual. A mudança é só no orquestrador (quem decide chamar).

---

## Problema

A Sprint 41 implementou page-split SEMPRE para PDFs com >= 2 páginas. Isso é correto para PDFs heterogêneos (cupom de garantia + NFC-e no mesmo arquivo, caso real do `pdf_notas.pdf`/`notas de garantia e compras.pdf`). MAS a prova de fogo histórica revelou que extratos bancários (Itaú, Santander) e faturas têm cabeçalho do tipo SÓ na pg1 -- as pgs 2-N são continuação. Page-split fragmenta o documento e as pgs 2-N caem em `_classificar/` por falta de assinatura.

Diagnóstico real (PDF amostra `_CLASSIFICAR_6b5f082a.pdf`):
```
chars=2571  imagens_pg1=True  primeira_linha='2/4'
```
Pg1 desse PDF foi classificada como extrato; pgs 2/3/4 caíram em `_classificar/` por não terem "EXTRATO DE CONTA" no início.

**Decisão tomada (alinhada no chat 2026-04-19):** page-split apenas quando heterogeneidade for OPERACIONALMENTE detectada via identificadores únicos.

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Extração de chave NFe 44 | `src/intake/glyph_tolerant.py:extrair_chave_nfe44` | Devolve 44 dígitos sem espaço, ou None |
| Extração de CNPJ (plural) | `src/intake/glyph_tolerant.py:extrair_cnpjs` | Devolve TODOS os CNPJs do texto, deduplicado |
| Extração de CPF | `src/intake/glyph_tolerant.py:extrair_cpf` | Devolve primeiro CPF canônico |
| Regex bilhete | `src/intake/extractors_envelope.py:_REGEX_BILHETE_INDIVIDUAL` | `BILHETE\s+INDIVIDUAL[:\s]+(\d{12,18})` -- tornar pública |
| Page-split via pikepdf | `src/intake/extractors_envelope.py:expandir_pdf_multipage` | Splitta + diagnóstico no mesmo pass |

## Implementação

### Fase 1: módulo `src/intake/heterogeneidade.py`

```python
from pathlib import Path
import pdfplumber
import re
from src.intake.glyph_tolerant import (
    extrair_cnpjs, extrair_cpf, extrair_chave_nfe44,
)
from src.utils.logger import configurar_logger

logger = configurar_logger("intake.heterogeneidade")

_REGEX_BILHETE = re.compile(
    r"[B8]ILHETE\s+INDIVIDUAL[:\s]+(\d{12,18})", re.IGNORECASE
)


def e_heterogeneo(pdf_path: Path) -> bool:
    """Devolve True se o PDF tem >= 2 documentos lógicos distintos.

    Definição operacional: scan página-a-página em busca de
    identificadores únicos (chave NFe 44, bilhete 12-18 dígitos, CPF).
    Se >= 2 identificadores DISTINTOS aparecem em páginas diferentes,
    o PDF é heterogêneo -> deve ser splittado.
    Senão é homogêneo -> envelope `single`.

    NÃO usa CNPJ como identificador para esta decisão -- o mesmo CNPJ
    aparece em todas as páginas de um extrato bancário (do banco emissor).
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) <= 1:
                return False  # 1 página nunca é heterogêneo
            ids_por_pagina: list[set[str]] = []
            for pagina in pdf.pages:
                texto = pagina.extract_text() or ""
                ids = _coletar_identificadores(texto)
                ids_por_pagina.append(ids)
        return _ha_identificadores_distintos_em_paginas_distintas(ids_por_pagina)
    except Exception as exc:
        logger.warning("e_heterogeneo(%s) falhou: %s -- assumindo homogêneo", pdf_path, exc)
        return False


def _coletar_identificadores(texto: str) -> set[str]:
    ids: set[str] = set()
    chave = extrair_chave_nfe44(texto)
    if chave:
        ids.add(f"chave44:{chave}")
    bilhete = _REGEX_BILHETE.search(texto)
    if bilhete:
        ids.add(f"bilhete:{bilhete.group(1)}")
    cpf = extrair_cpf(texto)
    if cpf:
        ids.add(f"cpf:{cpf}")
    return ids


def _ha_identificadores_distintos_em_paginas_distintas(
    ids_por_pagina: list[set[str]],
) -> bool:
    """True se >= 2 IDs distintos aparecem em páginas distintas."""
    todos_ids: set[str] = set()
    for ids_pg in ids_por_pagina:
        todos_ids.update(ids_pg)
    if len(todos_ids) < 2:
        return False
    # Confirmação: os IDs distintos não estão TODOS na mesma página
    for id_a in todos_ids:
        for id_b in todos_ids:
            if id_a == id_b:
                continue
            paginas_a = {i for i, ids in enumerate(ids_por_pagina) if id_a in ids}
            paginas_b = {i for i, ids in enumerate(ids_por_pagina) if id_b in ids}
            if paginas_a != paginas_b:  # IDs em conjuntos diferentes de páginas
                return True
    return False
```

### Fase 2: orquestrador chama heterogeneidade

`src/intake/orchestrator.py:_expandir`:

```python
if tipo_envelope == "pdf":
    if e_heterogeneo(caminho_inbox):
        resultado = expandir_pdf_multipage(caminho_inbox)
        return resultado, resultado.paginas
    # PDF homogêneo: envelope single, classifica como UM artefato
    resultado = _envelope_single_file(caminho_inbox, sha8, env._ENVELOPES_BASE)
    return resultado, ()
```

### Fase 3: testes (10 mínimos)

- `test_heterogeneo_pdf_notas_real_3_bilhetes_distintos` (usa `inbox/pdf_notas.pdf`)
- `test_heterogeneo_pdf_scan_real_4_paginas_misto` (usa `inbox/notas de garantia e compras.pdf` -- 2 chaves NFe + 2 bilhetes)
- `test_homogeneo_extrato_bancario_sintético_4_pgs_mesmo_cpf` (PDF sintético: mesmo CPF em todas as páginas)
- `test_homogeneo_pdf_uma_pagina` (sempre False)
- `test_homogeneo_pdf_sem_identificadores_legíveis` (texto bobo, sem chave/bilhete/CPF -> False, single envelope)
- `test_heterogeneo_dois_bilhetes_em_paginas_diferentes` (sintético)
- `test_homogeneo_mesmo_bilhete_repetido_em_2_paginas` (duplicata interna -- não conta como heterogêneo)
- `test_orchestrator_pdf_heterogeneo_chama_expandir_pdf_multipage` (integração)
- `test_orchestrator_pdf_homogeneo_chama_envelope_single` (integração)
- `test_e_heterogeneo_pdf_corrompido_devolve_false_sem_levantar` (defensivo)

### Fase 4: prova de fogo pós-41d

Re-rodar `python scripts/sprint41_prova_fogo.py --pasta data/raw --keep`. Critério: recall >= 60% (sobe dos 25% atuais APENAS pela correção do page-split; chegar a 95% exige Sprint 41c).

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A41d-1 | CNPJ como identificador desambigua MAL: extrato bancário tem só o CNPJ do banco em todas as pgs, nem por isso é heterogêneo | Usar CNPJ NÃO entra na decisão; só chave 44, bilhete e CPF |
| A41d-2 | PDF com QR code grande mas SEM texto extraível devolve identificadores vazios -> assume homogêneo | Correto: sem texto, não há como saber; envelope single roteia para `_classificar/` ou OCR (Sprint 45) |
| A41d-3 | Mesmo bilhete repetido em 2 pgs (caso real do pdf_notas pgs 1-2) NÃO é heterogêneo | A função verifica se há IDs DIFERENTES; mesmo bilhete em 2 pgs vira 1 ID único -> homogêneo |
| A41d-4 | Documento misto onde chave NFe e bilhete aparecem na MESMA página (ex.: NFC-e citando o seguro adicional) | Função verifica se IDs estão em CONJUNTOS DE PÁGINAS DIFERENTES, não só se existem -- evita falso-positivo |
| A41d-5 | Custo de abrir PDF duas vezes (1x heterogeneidade, 1x page-split) | Aceitar overhead -- 2x leitura é tolerável; otimizar depois cacheando o objeto pdfplumber se virar gargalo |

Referência: `docs/ARMADILHAS.md`

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] `.venv/bin/pytest tests/test_intake_heterogeneidade.py -v` passa com cobertura >= 90%
- [ ] `python scripts/sprint41_prova_fogo.py` (modo fixo) ainda funciona: pdf_notas vira heterogêneo (3 cupons), notas-de-garantia vira heterogêneo (mistura)
- [ ] `python scripts/sprint41_prova_fogo.py --pasta data/raw --keep` mostra recall >= 60% (sobe dos 25% atuais)
- [ ] PDFs bancários multipage do `data/raw/andre/` deixam de fragmentar -- aparecem como artefato único no relatório

## Verificação end-to-end

```bash
make lint
.venv/bin/pytest tests/test_intake_heterogeneidade.py tests/test_intake_orchestrator.py -v
python scripts/sprint41_prova_fogo.py --pasta data/raw --keep
# Conferir resumo: recall >= 60%, contagem de _NAO_CLASSIFICADO_ caiu significativamente
```

## Conferência Artesanal Opus

**Arquivos originais a ler:**

- `inbox/pdf_notas.pdf` -- 3 cupons garantia, 3 bilhetes distintos -> heterogêneo (esperado True)
- `inbox/notas de garantia e compras.pdf` -- mistura NFC-e + cupons -> heterogêneo (esperado True)
- 1 extrato bancário multipage do `data/raw/andre/` (sintetizar se não houver) -> homogêneo (esperado False)

**Outputs a comparar:**

- `e_heterogeneo` para cada PDF amostral -- conferir contra leitura visual humana
- Após 41d, contagem de artefatos por arquivo cai (extratos viram 1 artefato, não 4)
- `_classificar/` reduz drasticamente para PDFs bancários

**Relatório esperado em `docs/propostas/sprint_41d_conferencia.md`:**

- Tabela: PDF | nº pgs | identificadores únicos detectados | heterogêneo? | esperado | OK?
- Recall global pré e pós-41d
- Casos onde a heurística errou (registrar como armadilha)

**Critério de aprovação:** 100% dos PDFs amostrais classificados corretamente entre heterogêneo/homogêneo. Recall global >= 60% na prova de fogo histórica.

---

*"Não toda multidão é desordem; nem toda página é documento à parte." -- princípio do diagnóstico"*
