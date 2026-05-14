---
id: FASE-A-RESTAURAR-3-TIPOS-2026-05-13
titulo: Restaurar graduação de holerite + das_parcsn + nfce_modelo_65 após regressão silenciosa de dossiê
status: concluída
concluida_em: 2026-05-13
data_criacao: 2026-05-13
prioridade: P0
fase: A
epico: 1
depende_de: []
origem: regressão silenciosa observada em 2026-05-13. Sessão de 2026-05-12 (Fase A completa) graduou 4 tipos (cupom, holerite, das_parcsn, nfce_modelo_65). Entre a sessão anterior e esta (2026-05-13 17:42 BRT), os dossiês em `data/output/dossies/<tipo>/` foram resetados a esqueletos PENDENTE com `historico: []`. Como `data/output/` é gitignored, não há histórico para investigar a causa-raiz. Caches OCR em `data/output/opus_ocr_cache/` também sumiram para holerite/das/nfce (zero arquivos); apenas cupom_fiscal_foto (5 caches) e comprovante_pix_foto (3 caches) sobreviveram.
---

# Sprint FASE-A-RESTAURAR-3-TIPOS-2026-05-13

## Contexto

Sessão 2026-05-13 (esta) abriu para graduar `comprovante_pix_foto` (CALIBRANDO → GRADUADO). Ao validar estado dos demais tipos no `graduacao_tipos.json`, descobriu-se que `cupom_fiscal_foto`, `holerite`, `das_parcsn`, `nfce_modelo_65` -- todos GRADUADOS ontem -- estão como PENDENTE/historico=[].

Esta sprint cumpre o **padrão (ll) re-trabalho em loop fechado**: regressão detectada → sprint-filha imediata com brief executável, em vez de adiar.

- `comprovante_pix_foto`: GRADUADO esta sessão (3 amostras Itaú/C6/Nubank).
- `cupom_fiscal_foto`: GRADUADO esta sessão (3 amostras: NSP 27/04, Atacadão Drogaria, NSP 24/04).
- `holerite`, `das_parcsn`, `nfce_modelo_65`: ALVO desta sprint.

## Hipótese (padrão (s) Validação ANTES)

H1: amostras PDF originais persistem em `data/raw/<pessoa>/holerites/`, `data/raw/<pessoa>/impostos/das_parcsn/`, `data/raw/<pessoa>/nfs_fiscais/nfce/`.

H2: extratores de cada tipo (`holerite`, `das_parcsn`, `nfce_pdf` em src/extractors/) seguem produzindo output canônico conforme schema em `mappings/schema_opus_ocr.json`.

H3: leitura multimodal do supervisor Opus 4.7 contra a amostra produz dict que bate com cache OCR existente ou gerado pelo extrator dentro da tolerância numérica/string definida em `scripts/dossie_tipo.py`.

### Validação ANTES (grep runtime)

```bash
find data/raw -type f -iname "HOLERITE_*.pdf" | wc -l   # esperado >= 10
find data/raw -type f -name "DAS_PARCSN_*.pdf" | wc -l   # esperado >= 10
find data/raw -type f -iname "NFCE_*.pdf" -o -iname "nfce_*.pdf" | wc -l   # esperado >= 3
ls data/output/opus_ocr_cache/ | wc -l   # mostra caches OCR sobreviventes
```

## Entregável

Para cada tipo X em {holerite, das_parcsn, nfce_modelo_65}:

1. Selecionar 2+ amostras representativas (emissor/competência distintos quando aplicável).
2. Supervisor Opus principal lê cada PDF via Read multimodal (etapas 3+5 do CICLO -- *somente Opus interativo*).
3. Gerar `data/output/dossies/<X>/provas_artesanais/<sha256>.json` com `campos_canonicos` conforme `mappings/schema_opus_ocr.json`.
4. Confrontar contra cache OCR (gerado pelo pipeline OU prova mútua quando cache ausente).
5. `scripts/dossie_tipo.py comparar X <sha>` retorna `GRADUADO_OK` para >= 2 amostras.
6. `scripts/dossie_tipo.py graduar-se-pronto X` transiciona PENDENTE → GRADUADO.

## Acceptance (padrão (kk) Sprint encerra com produto final)

- `data/output/graduacao_tipos.json` mostra `GRADUADOS: 5` ao fim (PIX + cupom + holerite + das_parcsn + nfce).
- `dossie_tipo.py abrir holerite` mostra `status: GRADUADO`.
- `dossie_tipo.py abrir das_parcsn` mostra `status: GRADUADO`.
- `dossie_tipo.py abrir nfce_modelo_65` mostra `status: GRADUADO`.
- `make lint`, `make smoke 10/10`, cobertura D7 sem violação -- mantidos.
- Spec movida para `docs/sprints/concluidos/` com `concluida_em: 2026-05-13`.

## Não-objetivos (padrão (t))

- Não diagnosticar causa-raiz da regressão silenciosa (separada -- abrir sprint META se reincidir).
- Não rodar `./run.sh --tudo` (regenera XLSX/relatórios -- destrutivo no estado atual).
- Não despachar executor-sprint para etapas 3-5 do ritual (multimodal é exclusividade do Opus principal -- padrão (jj)).

## Proof-of-work runtime-real (padrão (u))

```bash
.venv/bin/python scripts/dossie_tipo.py comparar holerite <sha_g4f>
.venv/bin/python scripts/dossie_tipo.py comparar holerite <sha_infobase>
.venv/bin/python scripts/dossie_tipo.py graduar-se-pronto holerite
# Saida esperada: PENDENTE -> GRADUADO (amostras OK: 2)

.venv/bin/python scripts/dossie_tipo.py comparar das_parcsn <sha1>
.venv/bin/python scripts/dossie_tipo.py comparar das_parcsn <sha2>
.venv/bin/python scripts/dossie_tipo.py graduar-se-pronto das_parcsn

.venv/bin/python scripts/dossie_tipo.py comparar nfce_modelo_65 <sha1>
.venv/bin/python scripts/dossie_tipo.py comparar nfce_modelo_65 <sha2>
.venv/bin/python scripts/dossie_tipo.py graduar-se-pronto nfce_modelo_65

.venv/bin/python -c "import json; d=json.load(open('data/output/graduacao_tipos.json')); print(d['totais'])"
# Saida esperada: {'PENDENTE': 3, 'CALIBRANDO': 0, 'GRADUADO': 5, 'REGREDINDO': 0}
```

## Padrões canônicos aplicáveis

- **(jj)** Dossiê obrigatório antes de código -- provas artesanais geradas antes de qualquer comparação.
- **(kk)** Sprint encerra com produto final -- veredito do `comparar` é a entrega.
- **(ll)** Re-trabalho em loop fechado -- sprint nasceu de divergência detectada em sessão.
- **(gg)** Cache sintético é placeholder honesto -- se cache não existir, supervisor lê o PDF independente; se cache existir mas vier de propagação (`_observacao` indica), supervisor confirma campos critérios na imagem.
- **(s)** Validação ANTES, **(t)** Não-objetivos, **(u)** Proof-of-work runtime-real -- esta spec carrega os três.

## Riscos conhecidos

- PDFs de holerite têm 2 páginas em alguns layouts -- Read multimodal lê só a primeira sem `pages: "1-2"`. Mitigação: usar `pages` se schema exigir campos de página 2 (totais consolidados em alguns INFOBASE).
- NFCe modelo 65 PDF tem chave de acesso de 44 dígitos no QR + abaixo em texto. Verificar match exato no `chave_44` da prova.
- Schema `holerite` exige `proventos`, `descontos`, `liquido`, `competencia`, `empresa`, `funcionario` -- prova ficará grande (~30 linhas JSON). Aceitável.

---

*"Regressão silenciosa cura-se com ciclo fechado, não com lamentação." -- princípio do reparo na hora*
