---
id: INFRA-VALIDACAO-ARTESANAL-CUPOM  <!-- noqa: accent -->
titulo: Validacao artesanal cupom_foto -- 2 amostras lidas por Opus multimodal versus ETL  <!-- noqa: accent -->
status: backlog
concluida_em: null
prioridade: P0
data_criacao: 2026-05-12
fase: VALIDACAO_ARTESANAL
depende_de: [INFRA-OPUS-SCHEMA-EXTENDIDO, INFRA-OCR-OPUS-VISAO, INFRA-EXTRATORES-USAR-OPUS]
esforco_estimado_horas: 2
origem: Plano 2026-05-12 secao Fase A1 -- cupom_foto e o caso-mae do fallback Opus (gap 0/5 processados em 2026-05-08; OCR local erra P55 vs PS5).  <!-- noqa: accent -->
mockup: novo-mockup/mockups/10-validacao-arquivos.html  <!-- noqa: accent -->
---

# Sprint INFRA-VALIDACAO-ARTESANAL-CUPOM -- prova de paridade ETL × Opus em cupom_foto  <!-- noqa: accent -->

## Contexto

Cupom fiscal foto é o caso-mãe do fallback Opus (ADR-13). Auditoria fim-a-fim 2026-05-08 reportou 0/5 cupons JPEG processados. O pipeline produtivo está em `src/extractors/cupom_termico_foto.py` (classe `ExtratorCupomTermicoFoto`, ExtratorBase canônico — commit `25170a0` em 2026-05-08). INFRA-EXTRATORES-USAR-OPUS (commit `b4ddf37`) garantiu fallback Opus em 5 extratores. Falta provar empíricamente que o ETL agora bate com o Opus multimodal lido artesanalmente.

Há 5 amostras reais em `data/raw/casal/nfs_fiscais/cupom_foto/` — `CUPOM_2e43640d.jpeg` já tem cache Opus (52 itens, R$ 513,31, Comercial NSP LTDA).

## Objetivo

Executar o loop canônico de validação artesanal em 2 amostras de cupom_foto:

1. Selecionar 2 amostras: `CUPOM_2e43640d.jpeg` (gabarito já em cache) + 1 segunda amostra diferente.
2. Para cada amostra:
   - Capturar dict ETL via `from src.extractors.cupom_foto import extrair`.
   - Capturar dict Opus via Read tool multimodal sobre o JPEG (supervisor humano, eu).
   - Persistir dict Opus em `data/output/opus_ocr_cache/<sha256>.json` (idempotente via `extrair_via_opus`).
   - Fazer diff campo-a-campo entre ETL e Opus no schema canônico estendido.
   - Marcar status no CSV `data/output/validacao_arquivos.csv` via `scripts/validar_arquivo.py --marcar`.
3. Produzir relatório `docs/auditorias/VALIDACAO_ARTESANAL_CUPOM_2026-MM-DD.md` com side-by-side dos 2 dicts + classificação de divergências.
4. Veredito: APROVADO / APROVADO_COM_RESSALVAS / REPROVADO.
5. Se REPROVADO: gerar sprint-filha em `docs/sprints/backlog/sprint_cupom_fix_*.md` com hipótese da correção.

## Validação ANTES (grep -- padrão (k))

```bash
ls data/raw/casal/nfs_fiscais/cupom_foto/   # esperado: 4 JPEGs (CUPOM_2e43640d, _6554d704, _67a3104a, _bc3c42aa)
ls data/output/opus_ocr_cache/ | wc -l       # esperado: >=4 (gabarito artesanal ja em cache)
.venv/bin/python -c "from src.extractors.cupom_termico_foto import ExtratorCupomTermicoFoto; print('importa OK')"
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM node WHERE tipo='documento' AND json_extract(metadata,'\$.tipo_documento')='cupom_fiscal_foto'"
# esperado: >=1 apos pipeline produtivo
```

## Não-objetivos (padrão (t))

- **NÃO** validar mais de 2 amostras nesta sprint — gate 3 amostras fica para sprint canônica `INFRA-CUPOM-GATE-4WAY` futura.
- **NÃO** mexer no extrator se a validação reprovar — sprint-filha cuida.
- **NÃO** rodar `./run.sh --reextrair-tudo` — escopo é leitura + comparação local.
- **NÃO** persistir PII (CPF dono no cupom) em log INFO; mascarar antes de gravar.
- **NÃO** alterar `mappings/schema_opus_ocr.json` (responsabilidade de INFRA-OPUS-SCHEMA-EXTENDIDO).
- **NÃO** declarar APROVADO com erro classe A (diferença ≥ R$ 0,01 em `total` ou erro em `cnpj_emitente`).

## Spec de implementação (loop canônico passo-a-passo)

Para cada uma das 2 amostras:

### Passo 1 — Seleção

```bash
ls data/raw/casal/nfs_fiscais/cupom_foto/ | sort
# Pegar CUPOM_2e43640d.jpeg (gabarito) + 2ª amostra escolhida
```

### Passo 2 — Captura ETL

```python
from pathlib import Path
from src.extractors.cupom_termico_foto import ExtratorCupomTermicoFoto

caminho = Path("data/raw/casal/nfs_fiscais/cupom_foto/CUPOM_<sha8>.jpeg")
extrator = ExtratorCupomTermicoFoto(caminho)
documento, itens, confidence, recall = extrator.extrair_cupom(caminho)
print(f"total={documento.total}, itens={len(itens)}, est={documento.estabelecimento}, confianca={confidence:.2f}, recall={recall:.2f}")
```

### Passo 3 — Captura Opus multimodal (supervisor lê via Read)

```
# Eu (Opus principal da sessão) executo:
Read(file_path=str(caminho.absolute()))
# E produzo dict no schema canônico:
dict_opus = {
    "sha256": "...",
    "tipo_documento": "cupom_fiscal_foto",
    "estabelecimento": {"razao_social": "...", "cnpj": "..."},
    "data_emissao": "YYYY-MM-DD",
    "horario": "HH:MM:SS",
    "itens": [{"codigo": "...", "descricao": "...", "qtd": ..., "unidade": "...", "valor_unit": ..., "valor_total": ...}, ...],
    "total": ...,
    "forma_pagamento": "...",
    "extraido_via": "opus_v4_7_artesanal",
    "confianca_global": 0.95,
    "ts_extraido": "2026-MM-DDTHH:MM:SSZ"
}
```

### Passo 4 — Persistir cache (idempotente)

```python
import json, hashlib
sha = hashlib.sha256(caminho.read_bytes()).hexdigest()
Path(f"data/output/opus_ocr_cache/{sha}.json").write_text(json.dumps(dict_opus, ensure_ascii=False, indent=2))
```

### Passo 5 — Diff campo-a-campo

```python
def comparar(etl, opus):
    divergencias = []
    # Classe A (criticas)
    if abs(etl.total - opus["total"]) > 0.01:
        divergencias.append(("A", "total", etl.total, opus["total"]))
    if etl.estabelecimento.cnpj != opus["estabelecimento"]["cnpj"]:
        divergencias.append(("A", "cnpj", etl.estabelecimento.cnpj, opus["estabelecimento"]["cnpj"]))
    if etl.data_emissao != opus["data_emissao"]:
        divergencias.append(("A", "data_emissao", etl.data_emissao, opus["data_emissao"]))
    # Classe B (itens)
    if len(etl.itens) != len(opus["itens"]):
        divergencias.append(("B", "len_itens", len(etl.itens), len(opus["itens"])))
    # ... iterar itens
    return divergencias
```

### Passo 6 — Marcar CSV

```bash
.venv/bin/python scripts/validar_arquivo.py --marcar --sha8 <sha8> --campo total --valor "513.31" --status ok
.venv/bin/python scripts/validar_arquivo.py --marcar --sha8 <sha8> --campo itens --valor "52" --status ok
.venv/bin/python scripts/validar_arquivo.py --marcar --sha8 <sha8> --campo cnpj --valor "56.525.495/0004-70" --status ok
# ... 1 chamada por campo critico
```

### Passo 7 — Relatório

```markdown
# docs/auditorias/VALIDACAO_ARTESANAL_CUPOM_<data>.md

## Amostra 1 -- CUPOM_2e43640d.jpeg
| Campo | ETL | Opus | Classe | Veredito |
|---|---|---|---|---|
| total | 513.31 | 513.31 | — | OK |
| cnpj | 56.525.495/0004-70 | 56.525.495/0004-70 | — | OK |
| itens (qtd) | 52 | 52 | — | OK |
| item[0].descricao | "PEPSI 2L" | "PEPSI 2L" | — | OK |
| ... | | | | |

Veredito: APROVADO

## Amostra 2 -- CUPOM_<sha8>.jpeg
...
```

## Proof-of-work (padrão (u))

```bash
# 1. Confirmar que extrator funciona
.venv/bin/python -c "
from src.extractors.cupom_termico_foto import ExtratorCupomTermicoFoto
from pathlib import Path
extrator = ExtratorCupomTermicoFoto(Path('data/raw/casal/nfs_fiscais/cupom_foto/CUPOM_2e43640d.jpeg'))
doc, itens, conf, recall = extrator.extrair_cupom(Path('data/raw/casal/nfs_fiscais/cupom_foto/CUPOM_2e43640d.jpeg'))
print(f'total={doc.total}, itens={len(itens)}, conf={conf:.2f}, recall={recall:.2f}')
"
# Esperado: total=513.31, itens=52, conf>=0.85

# 2. Confirmar cache popular (apos artesanal)
ls data/output/opus_ocr_cache/ | grep -c "json$"
# Esperado: cresce de 4 para >=6 (2 novos caches de cupom)

# 3. Conferir CSV
.venv/bin/python scripts/validar_arquivo.py --resumo
# Esperado: concordancia 3-way OK aumenta

# 4. Relatorio gerado
ls docs/auditorias/VALIDACAO_ARTESANAL_CUPOM_*.md

# 5. Gauntlet
make lint && make smoke
.venv/bin/pytest tests/ -q
```

## Critério de aceitação (gate (z))

1. 2 amostras processadas com ETL+Opus capturados.
2. Cache `data/output/opus_ocr_cache/` cresce em pelo menos 2 entradas.
3. Relatório `docs/auditorias/VALIDACAO_ARTESANAL_CUPOM_<data>.md` existe com side-by-side completo.
4. CSV `data/output/validacao_arquivos.csv` marcado para cada campo crítico das 2 amostras.
5. Veredito final declarado APROVADO / APROVADO_COM_RESSALVAS / REPROVADO.
6. Se REPROVADO: sprint-filha em backlog.
7. `make lint` exit 0, `make smoke` 10/10, pytest baseline ≥ 2752 (ou ≥ 2764 se A0 fechou antes).
8. Spec movida para `concluidos/` com frontmatter `concluida_em: 2026-MM-DD`.

## Critério de gate (4-way + classes)

- **Classe A (crítica fiscal, peso 3)**: `data_emissao`, `total`, `cnpj_emitente`. Divergência ≥ R$ 0,01 em `total` ou erro literal em `cnpj`/`data_emissao` → REPROVADO imediato.
- **Classe B (semântica, peso 2)**: `itens[].descricao`, `itens[].valor_total`, `estabelecimento.razao_social`. Erro em ≥ 20% dos itens → REPROVADO; erro em < 20% → APROVADO_COM_RESSALVAS.
- **Classe C (auxiliar, peso 1)**: `operador`, `endereco`, `horario`. Erros não bloqueiam.
- **Classe D (cosmética)**: acento, capitalização. Não conta para gate.

## Referência

- Extrator canônico: `src/extractors/cupom_termico_foto.py::ExtratorCupomTermicoFoto` (classe ExtratorBase). Função-chave `extrair_cupom(caminho, texto_override=None)` retorna `(documento, itens, confidence, recall)`.
- Sprint-pai (fallback Opus): `docs/sprints/concluidos/sprint_INFRA_extratores_usar_opus.md` (commit `b4ddf37`).
- Sprint-pai (schema): `docs/sprints/backlog/sprint_INFRA_opus_schema_extendido.md` (bloqueia).
- Plano de origem: `~/.claude/plans/preciso-que-use-o-crispy-stroustrup.md` Fase A1.
- Auditoria base: `docs/auditorias/VALIDACAO_END2END_2026-05-08.md` caso 2.

*"O cupom é o teste mais honesto do OCR: tudo está ali, sem floreio, sem retoque." — princípio INFRA-VALIDACAO-ARTESANAL-CUPOM*  <!-- noqa: accent -->
