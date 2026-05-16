---
id: INFRA-SUBSTITUIR-CACHE-SINTETICO-CUPOM
titulo: Substituir os 4 caches Opus sintéticos de cupom_fiscal_foto por gabaritos reais artesanais
status: backlog
concluida_em: null
prioridade: P0
data_criacao: 2026-05-12
fase: VALIDACAO_ARTESANAL
depende_de: []
bloqueia: "[INFRA-VALIDACAO-ARTESANAL-CUPOM, INFRA-VALIDACAO-ARTESANAL-HOLERITE, INFRA-VALIDACAO-ARTESANAL-NFCE, INFRA-VALIDACAO-ARTESANAL-DAS]  <!-- noqa: accent -->"
esforco_estimado_horas: 3
origem: "docs/auditorias/VALIDACAO_ARTESANAL_CUPOM_2026-05-12.md -- auditoria revelou que cache Opus 2e43640d eh sintetico (admite em _observacao) e ETL apenas devolve cache. Mesma natureza provavel nos 3 outros caches.  <!-- noqa: accent -->"
adr_associada: "ADR-26 (Opus como OCR canonico para imagens -- precisa formalizar diferenca entre placeholder sintetico e gabarito real)  <!-- noqa: accent -->"
---

# Sprint INFRA-SUBSTITUIR-CACHE-SINTETICO-CUPOM -- promover 4 caches placeholder a gabaritos reais

## Contexto

Validação artesanal CUPOM_2e43640d.jpeg em 2026-05-12 revelou que `data/output/opus_ocr_cache/2e43640d…json` é um **placeholder sintético** (52 itens fabricados para somar R$ 513,31). O próprio cache admite em `_observacao`:

> "Descrições baseadas nas amostras visíveis (MACA, AGUA SNTI, BOMBOM, MACARRAO) extrapoladas com itens canônicos de supermercado plausíveis para cobrir os 52."

`ExtratorCupomTermicoFoto.extrair_cupom` delega ao cache Opus quando disponível (log: "upgrade via Opus") — não roda OCR fresco. Resultado: **ETL e cache "concordam 100%" mas ambos divergem do cupom real**.

Auditoria provável dos 3 outros caches (`6554d704`, `67a3104a`, `bc3c42aa`): mesma natureza placeholder.

## Objetivo

1. **Auditar os 4 caches existentes**:
   - Ler `_observacao` de cada um — confirmar se declara natureza sintética.
   - Comparar primeiros 5 itens de cada cache com a imagem real correspondente (via Read multimodal).
   - Para cada cache, marcar: REAL / SINTETICO / HIBRIDO.
2. **Promover a gabaritos reais** os caches confirmados sintéticos:
   - Para cada JPEG, supervisor lê via Read multimodal.
   - Produz `dict_opus_real` com itens efetivamente legíveis (com `valor_total` e `descricao` reais).
   - Para itens ilegíveis no JPEG (resolução baixa), declarar `"descricao": "<ilegivel>"` em vez de inventar.
   - Persistir como novo cache canônico (mesmo `sha256.json`) com `extraido_via: "opus_supervisor_artesanal"` (real).
3. **Schema flag**: adicionar campo opcional `eh_gabarito_real: bool` no schema cupom_fiscal_foto (default true). Caches que não passem auditoria recebem `eh_gabarito_real: false`.
4. **Re-rodar validação artesanal CUPOM** após cada cache promovido. Veredito deve passar de REPROVADO para APROVADO.

## Validação ANTES (grep -- padrão (k))

```bash
ls data/output/opus_ocr_cache/ | head
# esperado: 4 jsons
for f in data/output/opus_ocr_cache/*.json; do
  echo "=== $f ==="
  .venv/bin/python -c "import json; d=json.load(open('$f')); print('observacao:', d.get('_observacao','—')[:200])"
done
# esperado: pelo menos 1 cache (2e43640d) declara natureza sintetica
```

## Não-objetivos (padrão (t))

- **NÃO** modificar `cupom_termico_foto.py` (cache-first é correto sob ADR-13).
- **NÃO** apagar os caches antigos antes de substituí-los — backup em `data/output/opus_ocr_cache_sintetico_backup/`.
- **NÃO** inventar descrições para itens ilegíveis — usar `"<ilegivel>"` explícito.
- **NÃO** promover cache sem leitura artesanal completa (parcial vira nova armadilha).
- **NÃO** envolver Anthropic API — supervisor lê via Read tool no modo interativo (ADR-13).

## Spec de implementação

### Passo 1 — Auditoria dos 4 caches

```python
import json, glob
for c in sorted(glob.glob("data/output/opus_ocr_cache/*.json")):
    d = json.load(open(c))
    obs = d.get("_observacao", "")
    flag = "SINTETICO" if "extrapolad" in obs.lower() or "plausive" in obs.lower() else "?"
    print(f"{c[-20:]}: {flag} -- itens={len(d.get('itens',[]))} total={d.get('total')}")
```

Marcação manual: SINTETICO / REAL / HIBRIDO.

### Passo 2 — Backup + nova leitura artesanal por cache sintético

Para cada cache flagado SINTETICO:

```bash
mkdir -p data/output/opus_ocr_cache_sintetico_backup/
cp data/output/opus_ocr_cache/<sha>.json data/output/opus_ocr_cache_sintetico_backup/<sha>.json
```

Supervisor (eu) lê o JPEG correspondente via Read tool (multimodal Opus 4.7) e produz `dict_opus_real` no schema canônico atual (cupom_fiscal_foto bloco). Para itens ilegíveis, marcar `"descricao": "<ilegivel_qtd=N_total=X.YY>"`.

### Passo 3 — Persistir novo cache

```python
import json
nova_cache = {
    "sha256": "...",
    "tipo_documento": "cupom_fiscal_foto",
    "estabelecimento": {...},
    "data_emissao": "...",
    "itens": [...],  # gabarito real
    "total": ...,
    "extraido_via": "opus_supervisor_artesanal",  # SEM sufixo sintetico
    "confianca_global": 0.85,  # honesta -- nao 0.95
    "ts_extraido": "2026-05-12T...",
    "_observacao": "Gabarito real lido artesanalmente em 2026-05-12 pelo supervisor Opus 4.7 multimodal (sessao 2026-05-12 parte 3). Substitui cache sintetico anterior preservado em data/output/opus_ocr_cache_sintetico_backup/",
    "eh_gabarito_real": True,
}
json.dump(nova_cache, open("data/output/opus_ocr_cache/<sha>.json", "w"), ensure_ascii=False, indent=2)
```

### Passo 4 — Re-validar

Rerodar ETL e comparar:

```bash
.venv/bin/python -c "
from src.extractors.cupom_termico_foto import ExtratorCupomTermicoFoto
from pathlib import Path
caminho = Path('data/raw/casal/nfs_fiscais/cupom_foto/CUPOM_2e43640d.jpeg')
r = ExtratorCupomTermicoFoto(caminho).extrair_cupom(caminho)
print(f'total={r[\"documento\"].total}, itens={len(r[\"itens\"])}')
"
```

Esperado: ETL devolve o cache **real** agora. Itens lidos batem com cupom real.

### Passo 5 — Schema flag

Adicionar campo opcional ao schema (cláusula `properties` raiz):

```json
"eh_gabarito_real": {
  "type": "boolean",
  "description": "True quando cache eh gabarito real lido artesanalmente; False/ausente quando placeholder sintetico"
}
```

Retrocompat preservada (campo opcional).

## Proof-of-work (padrão (u))

```bash
# 1. Backup completo dos 4 caches
ls data/output/opus_ocr_cache_sintetico_backup/ | wc -l
# Esperado: 4

# 2. Re-leitura artesanal: cada cache novo tem eh_gabarito_real=true
.venv/bin/python -c "
import json, glob
for c in sorted(glob.glob('data/output/opus_ocr_cache/*.json')):
    d = json.load(open(c))
    flag = d.get('eh_gabarito_real')
    extraido = d.get('extraido_via')
    print(f'{c[-20:]}: real={flag}, via={extraido}')
"
# Esperado: 4/4 com eh_gabarito_real=True e extraido_via=opus_supervisor_artesanal

# 3. ETL devolve gabarito real (descrições batem com cupom)
.venv/bin/python -c "
from src.extractors.cupom_termico_foto import ExtratorCupomTermicoFoto
from pathlib import Path
for jpeg in sorted(Path('data/raw/casal/nfs_fiscais/cupom_foto/').glob('*.jpeg')):
    r = ExtratorCupomTermicoFoto(jpeg).extrair_cupom(jpeg)
    descricoes = [i.descricao for i in r['itens'][:3]]
    print(f'{jpeg.name}: total={r[\"documento\"].total}, primeiros_3_itens={descricoes}')
"

# 4. Validação artesanal CUPOM rerodada e APROVADA
ls docs/auditorias/VALIDACAO_ARTESANAL_CUPOM_2026-05-12-v2.md

# 5. Gauntlet
make lint && make smoke
.venv/bin/pytest tests/test_opus_ocr_schema.py -q
```

## Critério de aceitação (gate (z))

1. 4 caches sintéticos backupados em `data/output/opus_ocr_cache_sintetico_backup/`.
2. 4 caches novos lidos artesanalmente, com `eh_gabarito_real: true` + `confianca_global ≤ 0.9` (honesta).
3. ETL devolve descrições batendo com cupom real (validado em 4 amostras).
4. Schema atualizado com campo opcional `eh_gabarito_real` (retrocompat).
5. `docs/auditorias/VALIDACAO_ARTESANAL_CUPOM_2026-05-12-v2.md` veredito APROVADO ou APROVADO_COM_RESSALVAS.
6. `make lint`/`make smoke` verde, pytest baseline 2758+.

## Referência

- Auditoria que gerou a sprint: `docs/auditorias/VALIDACAO_ARTESANAL_CUPOM_2026-05-12.md`.
- Sprint-pai (extrator): `src/extractors/cupom_termico_foto.py::ExtratorCupomTermicoFoto`.
- Sprint INFRA-OCR-OPUS-VISAO (origem dos caches sintéticos): `docs/sprints/concluidos/sprint_INFRA_ocr_opus_visao.md` (commit `d7f8805`).
- ADR-13: supervisor artesanal via Claude Code.
- Padrão `(x)`: schema-extension precede validation — formalizado em `project_sessao_2026-05-12.md`.

*"Cache sintético é placeholder honesto que vira mentira silenciosa quando consumido como gabarito." — princípio descoberto na validação artesanal CUPOM 2026-05-12*
