---
id: AUTO-TIPO-PROPOSTAS
titulo: Detector automático de tipos novos em `_classificar/` (propostas regex)
status: backlog
concluida_em: null
prioridade: P2
data_criacao: 2026-05-15
fase: AUTONOMIA
epico: 1
depende_de: []
esforco_estimado_horas: 2
origem: auditoria 2026-05-15. Arquivos desconhecidos vão para `data/raw/_classificar/` e ficam lá indefinidamente. Não há heurística para sugerir regex novo em `tipos_documento.yaml`. 12 dos 22 tipos canônicos faltam dossiê (alguns com nomes divergentes). Auto-descoberta destravaria a meta.
---

# Sprint AUTO-TIPO-PROPOSTAS

## Contexto

`src/inbox_processor.py` roteia arquivos para 1 dos 22 tipos via regex em `tipos_documento.yaml`. Quando nenhum casa, arquivo vai para `data/raw/_classificar/` — fica em quarentena. Hoje só o supervisor humano vê isso (manual).

Quando 3+ arquivos com mesma assinatura (extensão + n-grams OCR + nome similar) chegam, isso é sinal forte de tipo NOVO. Auto-detector pode propor entry para o YAML.

## Hipótese e validação ANTES

H1: `_classificar/` tem arquivos antigos:

```bash
ls data/raw/_classificar/ 2>/dev/null | wc -l
# Esperado: ≥1 (pode estar vazio se foi recentemente processado)

find data/raw/_classificar/ -type f -mtime +30 2>/dev/null | wc -l
# Esperado: arquivos antigos > 30 dias = oportunidade
```

H2: não há detector hoje:

```bash
grep -rln "propor_tipo_novo\|detector_tipo_proposta\|sugerir_regex" src/ scripts/
# Esperado: 0 hits
```

## Objetivo

1. Criar `scripts/detectar_tipos_novos.py`:
   - Varre `data/raw/_classificar/` agrupando por:
     - Extensão (.pdf, .jpeg, .xml)
     - N-grams de 3-5 do nome (case-insensitive)
     - Se PDF: extrair primeiras 500 chars via pdfplumber e n-gram
     - Se imagem: extrair via OCR tesseract (sample, 500 chars)
   - Cluster por similaridade Jaccard ≥ 0.4.
   - Para cluster ≥3 arquivos: propõe regex inicial baseado em palavras-chave frequentes.
2. Output `data/output/propostas_tipo_novo.json`:
   ```json
   {
     "propostas": [
       {
         "id_proposta": "tipo_novo_iptu_2026",
         "n_arquivos": 5,
         "amostras_paths": ["...", "..."],
         "palavras_chave": ["IPTU", "Distrito Federal", "imposto predial"],
         "regex_sugerido": ["IPTU", "imposto.*predial"],
         "sugestao_id_yaml": "conta_iptu"
       }
     ]
   }
   ```
3. Dashboard página `tipos_novos_propostos.py`:
   - Lista propostas
   - Botão "criar entry em tipos_documento.yaml" gera YAML + commit
   - Botão "ignorar" move arquivos para `_classificar/_ignorados/`
4. Cron/systemd dispara `make tipos-novos` semanalmente (opcional).

## Não-objetivos

- Não tomar decisão final (humano aprova).
- Não tentar extrair semântica (só sintaxe — palavras-chave repetidas).
- Não OCR de PDFs grandes inteiros (só sample).

## Proof-of-work runtime-real

```bash
.venv/bin/python scripts/detectar_tipos_novos.py --varrer
cat data/output/propostas_tipo_novo.json | python -c "
import json, sys
d = json.load(sys.stdin)
print(f'{len(d[\"propostas\"])} propostas')
for p in d['propostas'][:3]:
    print(f'  [{p[\"id_proposta\"]}] {p[\"n_arquivos\"]} arquivos | regex: {p[\"regex_sugerido\"]}')
"
# Esperado: 0 ou mais propostas dependendo do conteúdo de _classificar/
```

## Acceptance

- `scripts/detectar_tipos_novos.py` criado.
- JSON gerado em `data/output/propostas_tipo_novo.json`.
- Página dashboard exibe propostas (mesmo que 0).
- 5 testes em `tests/test_detectar_tipos_novos.py` (cluster, regex, sample OCR).
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (jj) Dossiê obrigatório — proposta vira dossiê quando aprovada.
- (s) Validação ANTES — n-gram + sample antes de propor.

---

*"O desconhecido recorrente é o conhecido aguardando classificação." — princípio do bibliotecário emergente*
