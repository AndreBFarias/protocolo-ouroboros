---
id: META-NORMALIZAR-TIPO-DOCUMENTO-ETL
titulo: "ETL grava `metadata.tipo_documento` com nomes divergentes do YAML canônico"
status: concluída
concluida_em: 2026-05-16
prioridade: P1
data_criacao: 2026-05-16
fase: QUALIDADE
epico: 3
depende_de: []
esforco_estimado_horas: 2
origem: "achado da Sprint META-AUDITORIA-CRUZADA-XLSX (2026-05-16). XLSX gerado mostrou que `tipo_etl` aparece vazio na maioria das linhas porque o ETL grava nomes divergentes do YAML canônico no campo `metadata.tipo_documento` dos nodes documento. Exemplos detectados: cupom_fiscal_foto (YAML) vs cupom_fiscal (ETL grafo); nfce_consumidor_eletronica (YAML) vs nfce_modelo_65 (ETL grafo); holerite (concordam, 24 nodes); dirpf_retif (1 node no grafo, PENDENTE no dossiê). Sprint META-TIPOS-ALIAS-BIDIRECIONAL (Onda α P0) adicionou alias_graduacao no YAML mas extratores ainda não consomem."
---

# Sprint META-NORMALIZAR-TIPO-DOCUMENTO-ETL

## Contexto

O XLSX de auditoria cruzada (`make auditoria-xlsx`) revela quebra entre 2
fontes de verdade do projeto:

| YAML canônico (`mappings/tipos_documento.yaml`) | ETL gravou no grafo |
|---|---|
| `cupom_fiscal_foto` | `cupom_fiscal` (52 nodes) |
| `nfce_consumidor_eletronica` | `nfce_modelo_65` (2 nodes) |
| `holerite` | `holerite` (24 nodes) — concorda |
| `dirpf_retif` | (tipo gravado mas não está no YAML) |

Resultado: o cruzamento Opus × ETL fica difícil de ler porque os mesmos
documentos têm IDs diferentes nas duas fontes. Sprint META-TIPOS-ALIAS-BIDIRECIONAL
(Onda α P0, concluída) adicionou campo `alias_graduacao` no YAML, mas os
extratores em `src/extractors/` ainda gravam o nome antigo.

## Hipótese e validação ANTES

```bash
# H1: confirmar que tipo_documento no grafo diverge do YAML
sqlite3 data/output/grafo.sqlite "
SELECT json_extract(metadata, '\$.tipo_documento'), COUNT(*)
FROM node WHERE tipo='documento' GROUP BY 1
"
# Esperado: linhas com nomes não-canônicos

# H2: localizar onde extratores gravam tipo_documento
grep -rln "tipo_documento.*[\"']" src/extractors/ | head -10
# Esperado: hits em cupom_termico_foto.py, nfce_pdf.py, etc.

# H3: confirmar que YAML tem alias_graduacao
grep "alias_graduacao\|aliases_graduacao" mappings/tipos_documento.yaml | head -5
```

## Objetivo

1. Auditoria empírica: identificar TODOS os pontos onde `tipo_documento` é
   gravado em metadata de node documento. Listar em
   `docs/auditorias/normalizar_tipo_documento_etl_2026-05-16.md`.

2. Para cada extrator que grava nome divergente:
   - Atualizar para gravar o ID canônico do YAML.
   - Adicionar teste regressivo que checa `metadata.tipo_documento in IDS_YAML`.

3. Migração retroativa via script `scripts/normalizar_tipo_documento_grafo.py`:
   - Lê mapping de aliases.
   - UPDATE no grafo: `cupom_fiscal` → `cupom_fiscal_foto`, etc.
   - Idempotente.
   - Log estruturado em `data/output/normalizar_tipo_documento_log.json`.

4. Atualizar `data/output/graduacao_tipos.json` para usar IDs canônicos
   após migração.

## Não-objetivos

- Não tocar `mappings/tipos_documento.yaml` (já está canônico).
- Não tocar dossiês (já usam IDs canônicos).
- Não criar tipos novos.

## Proof-of-work runtime-real

```bash
# 1. Auditoria empírica:
.venv/bin/python -c "
import sqlite3
from collections import Counter
con = sqlite3.connect('data/output/grafo.sqlite')
c = Counter()
for (m,) in con.execute(\"SELECT metadata FROM node WHERE tipo='documento'\"):
    import json
    try:
        d = json.loads(m)
        c[d.get('tipo_documento', '')] += 1
    except: pass
for tipo, n in c.most_common(): print(f'{tipo:40s} {n}')
"

# 2. Após migração:
.venv/bin/python scripts/normalizar_tipo_documento_grafo.py --dry-run
.venv/bin/python scripts/normalizar_tipo_documento_grafo.py --apply
# Esperado: nodes migrados

# 3. Verificação:
make auditoria-xlsx
# Esperado: aba auditoria_cruzada agora mostra tipo_etl populado
```

## Acceptance

- Auditoria empírica documenta todos os divergentes.
- Extratores gravam IDs canônicos do YAML.
- Script de migração retroativa funciona idempotente.
- XLSX de auditoria cruzada mostra `tipo_match=True` em maioria das linhas.
- Testes regressivos para cada extrator afetado.
- Pytest > 3145. Lint exit 0. Smoke 10/10.

## Padrões aplicáveis

- (n) Defesa em camadas: aliases no YAML + nomes canônicos no grafo + testes.
- (cc) Refactor revela teste frágil: testes de extrator podem precisar update.
- (m) Branch reversível: script tem `--dry-run` antes de `--apply`.

## Arquivos a modificar

- `src/extractors/cupom_termico_foto.py` — gravar `cupom_fiscal_foto`
- `src/extractors/nfce_pdf.py` — gravar `nfce_consumidor_eletronica`
- Outros conforme auditoria
- `scripts/normalizar_tipo_documento_grafo.py` (CRIAR)
- `tests/test_normalizar_tipo_documento_grafo.py` (CRIAR)
- `docs/auditorias/normalizar_tipo_documento_etl_2026-05-16.md` (CRIAR)

---

*"Duas fontes de verdade são uma fonte e um boato." — princípio da fonte canônica única*
