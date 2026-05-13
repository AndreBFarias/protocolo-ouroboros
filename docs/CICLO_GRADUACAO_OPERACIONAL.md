---
titulo: Ciclo de graduacao operacional -- como o Opus principal coordena cada sprint
data: 2026-05-13
autor: supervisor Opus principal
status: canonico
escopo: ritual obrigatorio antes de despachar executor para sprint que toca tipo documental  <!-- noqa: accent -->
---

# Ciclo de graduacao operacional -- ritual artesanal Opus

## Premissa

**O Opus principal sempre coordena como humano artesao.** Os executores (subagents) sao bracos rapidos; o cerebro continua sendo a sessao Claude Code interativa do supervisor. Para cada tipo documental que entra no projeto, ha um ritual de 6 fases que **NAO pode ser pulado**.  <!-- noqa: accent -->

## As 6 fases (sequencia inegociavel)

### Fase 1 -- Abrir o dossie do tipo

```bash
.venv/bin/python scripts/dossie_tipo.py --abrir <tipo>
```

Mostra:
- Status atual (PENDENTE / CALIBRANDO / GRADUADO / REGREDINDO)
- Amostras ja analisadas (sha256 + data + veredito)
- Provas artesanais ja existentes
- Divergencias historicas (se houver)
- Sprint-filhas geradas a partir desse tipo

Se o dossie ainda nao existe, o comando cria a estrutura inicial em `data/output/dossies/<tipo>/`.  <!-- noqa: accent -->

### Fase 2 -- Selecionar amostras reais

Dono fornece arquivos via `inbox/`. Supervisor escolhe 2+ amostras representativas:
- Diferentes emissores quando aplicavel (ex: PIX Itau + C6 + Nubank)
- Layouts distintos (cupom termico antigo + nfce moderno)
- Casos limite (valor zero, CPF mascarado, OCR degradado)

```bash
.venv/bin/python scripts/dossie_tipo.py --listar-candidatos <tipo>
```

Mostra arquivos em `inbox/` ou `data/raw/.../` que parecem ser do tipo (heuristica de nome+pasta).

### Fase 3 -- PROVA DOS 7 ARTESANAL (so o Opus principal faz)

**O coracao do ritual.** Antes de qualquer codigo, o Opus principal:  <!-- noqa: accent -->

1. Le cada amostra via Read multimodal (foto / PDF como imagem).
2. Gera dict canonico esperado segundo `mappings/schema_opus_ocr.json` ou schema do tipo.
3. Grava em `data/output/dossies/<tipo>/prova_artesanal_<sha256>.json`.

```bash
# Stub interativo para o supervisor preencher
.venv/bin/python scripts/dossie_tipo.py --prova-artesanal <tipo> <sha256>
```

O script cria template JSON com campos esperados + comentarios. Supervisor edita inline com valores lidos da imagem. Salvar = registro permanente da "verdade visual".

Campos canonicos da prova:
```json
{
  "sha256": "<hash>",
  "tipo": "<tipo>",
  "lido_por": "opus_4_7_multimodal",
  "lido_em": "<ISO timestamp>",
  "campos_canonicos": {
    "...": "schema especifico do tipo"
  },
  "_notas_supervisor": "observacoes sobre nitidez, ambiguidade, etc"
}
```

### Fase 4 -- Despachar executor com brief especifico

Agora (e so agora) o Opus despacha executor-sprint para implementar/refatorar o extrator. O brief inclui:

- Caminho das amostras
- Caminho das provas artesanais ja criadas (referencia, executor NAO modifica)  <!-- noqa: accent -->
- Schema canonico esperado
- Comando de validacao (`dossie_tipo.py --comparar`)  <!-- noqa: accent -->

Executor faz o trabalho de codigo. Roda ETL contra as amostras. Devolve commit.

### Fase 5 -- Comparacao automatica 4-way

```bash
.venv/bin/python scripts/dossie_tipo.py --comparar <tipo> <sha256>
```

Le:
- `prova_artesanal_<sha256>.json` (Opus)
- Output do ETL para o mesmo sha256 (grafo SQLite + cache OPUS)
- Estado do nó no grafo

Aplica regras de tolerancia por campo (valores numericos: tolerancia 1 centavo; strings: case-insensitive normalizada; datas: ISO exato; etc).

Veredito: `GRADUADO_OK` / `DIVERGENTE` / `INSUFICIENTE`.

### Fase 6 -- Persistir veredito e avancar

- Se `GRADUADO_OK`: incrementa contador no `graduacao_tipos.json`. Se chegou em 2 amostras verdes, tipo passa a `GRADUADO`. Spec movida para `concluidos/`.
- Se `DIVERGENTE`: gera `divergencias_<sha256>.md` com diff campo-a-campo. Registra sprint-filha **dentro do mesmo epico** para correcao. Executor re-disparado com brief de fix.
- Se `INSUFICIENTE`: amostra inadequada (OCR muito ruim, tipo errado). Move amostra para `inbox/_descarte/`, supervisor escolhe outra.

```bash
.venv/bin/python scripts/dossie_tipo.py --graduar-se-pronto <tipo>
```

Tenta graduar o tipo se >= 2 amostras OK. Atualiza JSON, regenera dashboard.

## Estrutura do dossie por tipo

```
data/output/dossies/<tipo>/
  README.md                          # contexto do tipo (gerado uma vez)
  estado.json                        # status atual + historico de eventos
  amostras/
    <sha256>.json                    # metadata da amostra (path, data, fonte)
  provas_artesanais/
    <sha256>.json                    # gabarito Opus
  comparacoes/
    <sha256>_<timestamp>.json        # resultado de cada rodada de comparacao
  divergencias/
    <sha256>_<timestamp>.md          # quando havia divergencia
  sprint_filhas.md                   # log de sprints geradas desse tipo
```

Todo o conteudo de `data/output/` esta no `.gitignore` (PII). Apenas `data/output/graduacao_tipos.json` (sem PII, so contadores) pode ser whitelisted se for util.  <!-- noqa: accent -->

## Auto-gerenciamento: como o ciclo se executa sozinho apos setup

Apos a infra estar pronta (script + JSON + dashboard), o fluxo cotidiano e:

1. Dono ve no dashboard que `tipo X` esta CALIBRANDO (1 amostra verde, faltam 1).
2. Dono joga 1 foto/PDF do tipo X em `inbox/`.
3. `./run.sh --full-cycle` roda; pipeline processa, extrator gera output.
4. Supervisor (sessao Claude Code) abre dossie X, faz prova dos 7 artesanal da nova amostra.
5. `dossie_tipo.py --comparar` decide automaticamente: graduado ou divergente.
6. Se graduado: dashboard atualiza para "GRADUADO". Sem mais trabalho.
7. Se divergente: dashboard mostra alerta; supervisor despacha executor de fix.

**Aqui esta a auto-gerencia**: nao ha "sprint intermediaria" para fechar nada. Cada amostra processada **avanca o tipo** ou **gera fix automatico**. O dashboard de graduacao e o painel mestre.  <!-- noqa: accent -->

## Padroes anti-debito

- **(jj) Dossie obrigatorio antes de codigo** -- nenhum executor toca extrator sem prova artesanal previa no dossie.  <!-- noqa: accent -->
- **(kk) Sprint encerra com produto final** -- nenhum "fechamento posterior", `dossie_tipo.py --comparar` ja decide na hora.
- **(ll) Re-trabalho em loop fechado** -- divergencia gera sprint-filha automatica no mesmo epico, executor proximo recebe brief com o diff.

Padroes registrados em `VALIDATOR_BRIEF.md` (local).

## Relacao com o ROADMAP

`docs/sprints/ROADMAP_ATE_PROD.md` ordena os epicos. Cada sprint do Epico 1 (graduacao) segue este ciclo. Sprints dos Epicos 2-8 nao tocam tipos documentais diretamente -- seguem fluxo classico (spec -> codigo -> teste -> commit).  <!-- noqa: accent -->

---

*"Sem ritual, todo trabalho vira gambiarra. Com ritual, todo gesto vira graduacao." -- principio do artesao automatizado*
