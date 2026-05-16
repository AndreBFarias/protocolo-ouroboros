---
id: AUTO-TIPO-PROPOSTAS-DASHBOARD
titulo: "Auto-detector de tipos novos em `_classificar/` + dashboard de propostas"
status: concluída
concluida_em: 2026-05-16
prioridade: P2
data_criacao: 2026-05-16
fase: AUTONOMIA
epico: 1
depende_de:
  - META-PROPOSTAS-DASHBOARD (precisa página de propostas estar wired)
esforco_estimado_horas: 2
origem: "Achado P2-7 da auditoria 2026-05-15. Arquivo desconhecido em `inbox/` é roteado para `data/raw/_classificar/` e fica lá indefinidamente. Sem heurística para sugerir adicionar regex em `mappings/tipos_documento.yaml`. 12 dos 22 tipos canônicos ainda sem dossiê (alguns com nomes divergentes do YAML)."
---

# Sprint AUTO-TIPO-PROPOSTAS-DASHBOARD

## Contexto

Hoje quando o intake (`src/intake/classifier.py`) não casa nenhuma regra de `tipos_documento.yaml`, o arquivo cai em `data/raw/_classificar/`. Não há mecanismo de varredura periódica que olhe esses fósseis e proponha regex. Resultado: dono precisa abrir manualmente cada arquivo e adicionar regra.

Proposta: script semanal que agrupa por extensão + n-grams OCR + assinaturas de cabeçalho, gera proposta JSON em `data/output/propostas_tipo_novo.json`, dashboard tem nova aba "Tipos por detectar" com botão "aceitar" que escreve entry em `tipos_documento.yaml` via PR-style.

## Hipótese e validação ANTES

```bash
ls data/raw/_classificar/ 2>/dev/null | wc -l
# Esperado: N arquivos sem classificação

grep -A 3 "FALLBACK\|_classificar" src/intake/classifier.py | head -20
# Confirmar que classificador roteia para _classificar/ em fallback

ls mappings/tipos_documento.yaml && python -c "import yaml; d=yaml.safe_load(open('mappings/tipos_documento.yaml')); print(len(d.get('tipos',[])))"
# Esperado: 22 tipos
```

## Objetivo

1. **Script `scripts/detectar_tipos_novos.py`** que:
   - Varre `data/raw/_classificar/` recursivamente.
   - Agrupa por extensão (pdf, jpeg, png, csv, xml).
   - Para cada grupo: extrai snippets de texto via pdfplumber/OCR.
   - Aplica TF-IDF inter-grupo: identifica n-grams discriminantes.
   - Propõe regex candidatos (ex: `"Documento\\s+Auxiliar\\s+do\\s+CT-e"` para CT-e novo).
   - Gera `data/output/propostas_tipo_novo.json` com schema:
     ```json
     {
       "gerado_em": "ISO",
       "propostas": [
         {
           "id_proposto": "ct_e_carga",
           "n_amostras": 3,
           "exemplos_sha256": ["abc...", "def..."],
           "regex_candidatos": ["Documento\\s+Auxiliar\\s+do\\s+CT-e"],
           "mime_principal": "application/pdf",
           "confianca_global": 0.78
         }
       ]
     }
     ```
2. **Dashboard `src/dashboard/paginas/tipos_pendentes.py`** (5ª aba cluster Sistema):
   - Tabela das propostas atuais (lê JSON).
   - Botão "Aceitar" → cria entry em `tipos_documento.yaml` (append) + move arquivos exemplo de `_classificar/` para `data/raw/casal/<tipo_id>/`.
   - Botão "Rejeitar" → marca proposta como rejeitada em `data/output/propostas_tipo_rejeitadas.json`.

3. **Wiring**: `src/dashboard/app.py` adiciona aba "Tipos por detectar" em cluster Sistema; `src/dashboard/componentes/drilldown.py` mapa de cluster.

## Não-objetivos

- Não tocar `src/intake/classifier.py` (apenas consumir output existente).
- Não criar regex novo sem proposta humana (auto-aceitação fora de escopo).
- Não integrar com pipeline em runtime (script avulso, dono roda quando quer).

## Proof-of-work runtime-real

```bash
.venv/bin/python scripts/detectar_tipos_novos.py 2>&1 | tail -10
# Esperado: gera data/output/propostas_tipo_novo.json com N propostas

cat data/output/propostas_tipo_novo.json | python -c "
import json, sys
d = json.load(sys.stdin)
print(f'{len(d[\"propostas\"])} propostas geradas')
for p in d['propostas']:
    print(f'  {p[\"id_proposto\"]}: {p[\"n_amostras\"]} amostras, confianca {p[\"confianca_global\"]}')
"

streamlit run src/dashboard/app.py
# Manualmente: cluster Sistema → aba "Tipos por detectar" → ver tabela
```

## Acceptance

- Script funcional gera JSON estruturado.
- Dashboard exibe propostas com tabela + botões.
- 3 testes em `tests/test_detectar_tipos_novos.py` (mock de _classificar com 3 arquivos sintéticos, asserir propostas geradas).
- 2 testes em `tests/test_tipos_pendentes_dashboard.py`.
- Pytest > 3100. Lint exit 0. Smoke 10/10.

## Padrões aplicáveis

- (l) Anti-débito — propostas viram entries no YAML quando aprovadas.
- (s) Hipótese ANTES — grep no classifier antes de codar.
- (n) Defesa em camadas — proposta JSON + dashboard + write helper.

## Arquivos a criar/modificar

- `scripts/detectar_tipos_novos.py` (CRIAR)
- `src/dashboard/paginas/tipos_pendentes.py` (CRIAR)
- `src/dashboard/app.py` (Edit: 5ª aba cluster Sistema)
- `src/dashboard/componentes/drilldown.py` (Edit: `MAPA_ABA_PARA_CLUSTER` adiciona `"Tipos por detectar": "Sistema"`)
- `tests/test_detectar_tipos_novos.py` (CRIAR)
- `tests/test_tipos_pendentes_dashboard.py` (CRIAR)
- `data/output/propostas_tipo_novo.json` (gerado em runtime, gitignored)

---

*"Cada arquivo em `_classificar/` é uma pergunta não respondida. Auto-detector convida resposta sem exigir." — princípio da curadoria assistida*
