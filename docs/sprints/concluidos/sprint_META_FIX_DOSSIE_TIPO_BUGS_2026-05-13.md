---
id: META-FIX-DOSSIE-TIPO-BUGS-2026-05-13
titulo: Consertar 2 bugs em scripts/dossie_tipo.py descobertos na sessão de restauração
status: concluida
concluida_em: 2026-05-14
data_criacao: 2026-05-13
prioridade: P1
fase: SANEAMENTO
epico: 8
depende_de: []
origem: sessão 2026-05-13 (FASE-A-RESTAURAR-3-TIPOS). Bug 1 quebra fallback ao grafo SQLite; bug 2 faz heurística falhar silenciosamente para nomes não-canônicos.
resultado_2026-05-14: |
  Sessao supervisor autonomo Opus 4.7 aplicou os 2 fixes. Bug 1: query do grafo
  usa nome_canonico (coluna real) ao inves de chave_canonica (inexistente).
  Bug 2: introduzido mapa CHAVES_BUSCA explicito cobrindo 22 tipos canonicos
  do mappings/tipos_documento.yaml com fallback retrocompativel para split('_')[0].
  4 testes regressivos adicionados em tests/test_dossie_tipo.py (15 testes totais,
  100% pass). Lint OK, smoke 10/10.  <!-- noqa: accent -->
---

# Sprint META-FIX-DOSSIE-TIPO-BUGS-2026-05-13

## Bug 1 -- query SQLite usa coluna inexistente

`scripts/dossie_tipo.py:262` faz:

```python
cur = con.execute(
    "SELECT metadata FROM node WHERE tipo='documento' "
    "AND (chave_canonica LIKE ? OR metadata LIKE ?)",
    (f"%{sha256}%", f"%{sha256}%"),
)
```

Tabela `node` em `data/output/grafo.sqlite` tem colunas: `id, tipo, nome_canonico, aliases, metadata, created_at, updated_at`. **Não há `chave_canonica`**. Quando o cache OCR está ausente E o grafo está presente, `_carregar_etl_output` crasha com `sqlite3.OperationalError: no such column: chave_canonica`.

**Fix**:
```python
cur = con.execute(
    "SELECT metadata FROM node WHERE tipo='documento' "
    "AND (nome_canonico LIKE ? OR metadata LIKE ?)",
    (f"%{sha256}%", f"%{sha256}%"),
)
```

Adicional: o sha256 raramente está em `nome_canonico` (que é chave semântica como `HOLERITE|G4F|2025-05`). A melhor busca é via `metadata LIKE %sha%`. Manter ambos os critérios por defesa em camadas (padrão (n)).

## Bug 2 -- heurística listar-candidatos quebra para nomes não-canônicos

`scripts/dossie_tipo.py:184`:

```python
chave = tipo.lower().split("_")[0]  # ex: pix de comprovante_pix_foto
```

Para `comprovante_pix_foto` retorna `"comprovante"`, mas as fotos PIX reais estão como `inbox/WhatsApp Image 2026-05-13 at 09.32.30.jpeg` -- nome não contém `"comprovante"`. Retorna 0 candidatos quando há 3 amostras válidas.

**Fix**: usar lista de palavras-chave por tipo via mapa explícito.

```python
CHAVES_BUSCA = {
    "comprovante_pix_foto": ["pix", "comprovante_pix", "whatsapp image"],
    "cupom_fiscal_foto": ["cupom", "nfce_n", "ncfe"],
    "holerite": ["holerite", "contracheque", "pagamento"],
    "das_parcsn": ["das_parcsn", "das ", "parcsn"],
    "nfce_modelo_65": ["nfce", "nf_consumidor"],
    "boleto_servico": ["boleto", "bol_"],
    # Default: split("_")[0] (retrocompatível com tipos não listados)
}

def cmd_listar_candidatos(tipo: str) -> int:
    chaves = CHAVES_BUSCA.get(tipo, [tipo.lower().split("_")[0]])
    ...
```

## Validação ANTES (padrão (s))

```bash
# Bug 1 reproduzido:
.venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from scripts.dossie_tipo import _carregar_etl_output
# Sha de um holerite real (sem cache OCR no momento da reprodução):
_carregar_etl_output('00000000000000000000000000000000000000000000000000000000000fffff')
# Esperado: traceback sqlite3.OperationalError
"

# Bug 2 reproduzido:
.venv/bin/python scripts/dossie_tipo.py listar-candidatos comprovante_pix_foto
# Esperado hoje: "Candidatos: 0" mesmo com inbox/ tendo 3 JPEGs PIX
```

## Entregável

1. `scripts/dossie_tipo.py` corrigido nos 2 pontos.
2. `tests/scripts/test_dossie_tipo.py` (novo) com:
   - test_carregar_etl_output_fallback_grafo_nao_crasha
   - test_listar_candidatos_pix_acha_whatsapp_images
3. Mapa `CHAVES_BUSCA` documentado inline + adicionar entrada quando criar tipo novo (regra (n)).

## Acceptance

- `pytest tests/scripts/test_dossie_tipo.py -q` exit 0.
- `listar-candidatos comprovante_pix_foto` agora retorna >= 1 candidato com inbox populado.
- `make lint` + `make smoke` mantêm verde.
- Spec movida para `concluidos/`.

## Proof-of-work runtime-real (padrão (u))

```bash
.venv/bin/python scripts/dossie_tipo.py listar-candidatos comprovante_pix_foto
# Saída esperada (com inbox/WhatsApp Image *.jpeg presentes):
#   Candidatos para tipo `comprovante_pix_foto` (chaves=['pix', 'comprovante_pix', 'whatsapp image']): 3
#     2a0d6ee773d7  inbox/WhatsApp Image 2026-05-13 at 09.32.30.jpeg
#     3d82d81c6e9d  inbox/WhatsApp Image 2026-05-13 at 09.33.26.jpeg
#     bb6abe1ca9dd  inbox/WhatsApp Image 2026-05-13 at 11.25.02.jpeg
```

## Padrões aplicáveis

- (n) Defesa em camadas (busca por nome_canonico + metadata).
- (s) Validação ANTES.
- (u) Proof-of-work runtime-real.
- (cc) Refactor revela teste frágil -- se o fix expor falha em teste antigo, abrir sprint-filha.

---

*"Bug silencioso eh dívida que sangra; bug com teste de regressão eh dívida quitada." -- princípio do fix com cinto e suspensório*
