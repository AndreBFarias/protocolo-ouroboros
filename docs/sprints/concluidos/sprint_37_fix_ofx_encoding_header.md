---
concluida_em: 2026-04-19
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 37
  title: "Fix: OFX encoding com espaços no header C6"
  touches:
    - path: src/extractors/ofx_parser.py
      reason: "normalizar valor do header ENCODING antes de passar para ofxparse"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: "./run.sh --tudo"
      timeout: 600
  acceptance_criteria:
    - "ExtratorOFX lê c6_cc_andre_2022-06_2026-04.ofx sem crash"
    - "Ao menos 1.784 transações extraídas do OFX do C6"
    - "Logs sem 'cannot access local variable encoding'"
    - "Acentuação PT-BR correta"
    - "Zero emojis"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 37 -- Fix: OFX encoding com espaços no header C6

**Status:** CONCLUÍDA
**Data:** 2026-04-18
**Prioridade:** ALTA
**Tipo:** Bugfix
**Dependências:** Nenhuma
**Desbloqueia:** Sprint 38 (dedup precisa de transações OFX para evidenciar overlap com XLSX legacy)
**Issue:** --
**ADR:** --

---

## Como Executar

**Comandos principais:**
- `make lint` -- ruff check + format + acentuação
- `./run.sh --tudo` -- pipeline completo com todos os OFX
- `python -c "from src.extractors.ofx_parser import ExtratorOFX; ..."` -- teste pontual

### O que NÃO fazer

- NÃO substituir ofxparse por outra lib (escopo mínimo, fix cirúrgico no header)
- NÃO assumir que todos os OFX têm o mesmo defeito; só normalizar o header ENCODING

---

## Problema

Durante a sessão de 2026-04-18, ao rodar `./run.sh --tudo`, observou-se erro:

```
ERROR:ExtratorOFX:Erro ao parsear OFX c6_cc_andre_2022-06_2026-04.ofx:
  cannot access local variable 'encoding' where it is not associated with a value
```

Investigação via `head -c 400 data/raw/andre/c6_cc/*.ofx` revelou:

```
OFXHEADER: 100
DATA: OFXSGML
VERSION: 102
SECURITY: NONE
ENCODING: UTF - 8       <-- espaços ao redor do hífen
CHARSET: 1252
```

A biblioteca `ofxparse` (20251230) não normaliza espaços no valor do header ENCODING e falha silenciosamente dentro do parser, levantando `UnboundLocalError` em vez de ValueError limpo. Resultado: todas as 1.784 transações do C6 (junho/2022 a abril/2026) ficavam fora do XLSX consolidado, mascaradas por um único erro de log. Outros OFX (Nubank) tinham cabeçalho correto `ENCODING:UTF-8` e funcionavam.

Impacto: aba `extrato` do XLSX estava sistematicamente incompleta no período 2022-06 a 2026-04 para tudo que era do C6 Bank.

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| ExtratorOFX | `src/extractors/ofx_parser.py` | Lê OFX via `ofxparse.OfxParser.parse` |
| Lista de bancos OFX | `src/extractors/ofx_parser.py:19-29` | Mapa de ORG→nome do banco |
| Logger rotacionado | `src/utils/logger.py` | `configurar_logger("ExtratorOFX")` |

---

## Implementação

### Fase 1: normalizar header ENCODING antes do parse

**Arquivo:** `src/extractors/ofx_parser.py`

Adicionado regex de linha-inteira que captura o valor do header ENCODING e remove qualquer espaço em branco interno:

```python
REGEX_ENCODING_HEADER = re.compile(rb"^(ENCODING:\s*)([^\r\n]+)", re.MULTILINE)
```

No método `_processar_arquivo`, a leitura do arquivo foi reestruturada:

```python
with open(arquivo, "rb") as f:
    conteudo = f.read()
conteudo = REGEX_ENCODING_HEADER.sub(
    lambda m: m.group(1) + m.group(2).replace(b" ", b""),
    conteudo,
)
ofx = OfxLib.parse(io.BytesIO(conteudo))
```

Bytes crus são pré-processados e passados para `OfxLib.parse` via `io.BytesIO`. O regex só toca linhas começando com `ENCODING:`, preservando qualquer outra diretiva.

### Fase 2: validação

Teste pontual rodado com o arquivo real:

```python
from pathlib import Path
from src.extractors.ofx_parser import ExtratorOFX
ext = ExtratorOFX(Path("data/raw/andre/c6_cc/c6_cc_andre_2022-06_2026-04.ofx"))
transacoes = ext.extrair()
assert len(transacoes) >= 1784
```

Após o fix, pipeline completo `./run.sh --tudo` passou de 2.859 → 6.136 transações consolidadas (C6 + Nubank OFX destravados).

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A37-1 | `ofxparse` levanta `UnboundLocalError` em vez de ValueError claro quando o header ENCODING está malformado | Pré-processar header via regex antes de passar pra lib; nunca confiar em validação interna de terceiros |
| A37-2 | Bancos brasileiros exportam OFX com variações livres no cabeçalho | Testar cada banco novo com `head -c 400` antes de assumir compatibilidade |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [x] `make lint` passa sem erros
- [x] `./run.sh --tudo` concluído -- 6.136 transações (antes: 2.859)
- [x] Log sem "cannot access local variable 'encoding'"
- [x] `ExtratorOFX` extrai 1.784 transações do OFX C6
- [x] Commit atômico com escopo mínimo (só `ofx_parser.py`)

---

## Verificação end-to-end

```bash
make lint
./run.sh --tudo 2>&1 | grep -E "Erro ao parsear OFX|Total de transações extraídas \(OFX\)"
# Esperado: nenhuma linha de "Erro ao parsear OFX", e duas linhas "Total de transações extraídas (OFX)"
python -c "from pathlib import Path; from src.extractors.ofx_parser import ExtratorOFX; e=ExtratorOFX(Path('data/raw/andre/c6_cc/c6_cc_andre_2022-06_2026-04.ofx')); assert len(e.extrair()) >= 1784, 'C6 OFX voltou a falhar'"
```

---

*"A imperfeição do outro cobre-se consertando o próprio código." -- proverbial do ofício*
