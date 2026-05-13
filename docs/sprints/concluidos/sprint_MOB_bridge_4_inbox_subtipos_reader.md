---
id: MOB-bridge-4-inbox-subtipos-reader
titulo: Walk recursivo em inbox_processor + orchestrator + registry para enxergar inbox/<area>/<subtipo>/ do app mobile
status: concluida  <!-- noqa: accent -->
concluida_em: 2026-05-12
prioridade: P0
data_criacao: 2026-05-12
revisao: 2026-05-12 -- alvo do refactor corrigido (inbox_reader e PURO LEITOR de UI; o despacho real esta em inbox_processor + intake/orchestrator + intake/registry)
fase: BRIDGE_MOBILE
depende_de: []
bloqueia: [MOB-bridge-5-classifier-pix, MOB-dashboard-mostra-pix-app, MOB-spec-transcricao-audio, MOB-spec-galeria-memorias]
esforco_estimado_horas: 4
origem: "Plano 2026-05-12 secao Fase B; app mobile (Protocolo-Mob-Ouroboros) exporta .md em inbox/<area>/<subtipo>/ via Share Intent Receiver (src/lib/share/categorias.ts) mas o backend (src/inbox_processor.py linha 173+ usa sorted(iterdir())) so le a raiz inbox/."  # noqa: accent
adr_associada: ADR-27 (proposta -- inbox vault sincronizavel via syncthing como contrato de entrada universal)  <!-- noqa: accent -->
---

# Sprint MOB-bridge-4-inbox-subtipos-reader -- inbox enxerga subpastas do app mobile

## Contexto

O app mobile (`~/Desenvolvimento/Protocolo-Mob-Ouroboros`, Expo SDK 54) implementa Share Intent Receiver na tela M08, com `src/lib/share/categorias.ts` constante `INBOX_SUBTIPOS` declarando **8 subtipos canônicos em 4 áreas** (verificado em 2026-05-12):

| Subtipo | Pasta destino |
|---|---|
| `pix` | `inbox/financeiro/pix/` |
| `extrato` | `inbox/financeiro/extrato/` |
| `nota` | `inbox/financeiro/nota/` |
| `exame` | `inbox/saude/exame/` |
| `receita` | `inbox/saude/receita/` |
| `garantia` | `inbox/casa/garantia/` |
| `contrato` | `inbox/casa/contrato/` |
| `outro` | `inbox/outros/` (raiz da area, sem subpasta) |

Casal compartilha via Syncthing entre PC + 2 celulares; PC tem essa pasta espelhada em `~/Protocolo-Ouroboros/inbox/` (confirmado existindo em 2026-05-12).

**Diagnóstico do alvo de refactor (verificado contra código)**:

- `src/intake/inbox_reader.py` é **PURO LEITOR observacional para UI** (docstring linha 1: *"não move, não classifica, não toca em data/raw/"*). Mexer aqui seria inútil — o despacho ETL não passa por ele.
- O despacho real está em **3 arquivos**:
  - `src/inbox_processor.py::processar_inbox` (linha 173): hoje `sorted(diretorio_inbox.iterdir())` — só raiz.
  - `src/intake/orchestrator.py::processar_arquivo_inbox` (linha 166): processa 1 arquivo após `inbox_processor` selecionar.
  - `src/intake/registry.py::detectar_tipo` (linha ~90): decide tipo via MIME + preview + classifier YAML.

Resultado: tudo o que o app deposita em `inbox/<area>/<subtipo>/` é **invisível** para o pipeline porque `inbox_processor.processar_inbox` não desce.

## Objetivo

1. **Refactor de `src/inbox_processor.py::processar_inbox`** (linha 173-225):
   - Trocar `sorted(diretorio_inbox.iterdir())` por walk recursivo (`rglob("*")` filtrado por `EXTENSOES_SUPORTADAS`).
   - Para cada arquivo encontrado em subpasta, extrair `area` e `subtipo_mobile` do path relativo.
   - Passar esses hints como kwargs para `processar_arquivo`.
2. **Estender `src/intake/orchestrator.py::processar_arquivo_inbox`** (linha 166) para aceitar parâmetro opcional `subtipo_mobile: str | None = None` e propagar para `detectar_tipo`.
3. **Estender `src/intake/registry.py::detectar_tipo`** (linha ~90, assinatura atual: `caminho, mime, preview, pessoa="_indefinida"`) para aceitar `subtipo_mobile: str | None = None` como 5º parâmetro. Quando presente, usa mapping abaixo como hint preferencial sobre classifier YAML:
   - `subtipo_mobile=pix` → `tipo=comprovante_pix_foto` (despacha para extrator do DOC-27 quando disponível) ou fallback `_classificar/`.
   - `subtipo_mobile=extrato` → mantém cascata legada (file_detector resolve Nubank/C6/Itaú/Santander).
   - `subtipo_mobile=nota` → `cupom_fiscal_foto` (imagem) ou `nfce_modelo_65` (PDF, decidido via MIME).
   - `subtipo_mobile=exame` → `exame_medico` (DOC-09 quando concluída) ou `_classificar/`.
   - `subtipo_mobile=receita` → `receita_medica` (DOC-10) ou `_classificar/`.
   - `subtipo_mobile=garantia` → `cupom_garantia_estendida_pdf` ou genérico.
   - `subtipo_mobile=contrato` → `contrato_locacao` (DOC-21) ou `_classificar/`.
   - `subtipo_mobile=outro` → `_classificar/` (fallback explícito).
4. **Rastrear `area` e `subtipo_mobile`** como metadata canônico no sidecar `.extracted/<sha8>.json` (campos novos, retrocompat preservada — arquivos antigos sem esses campos continuam válidos).
5. **Não tocar em `src/intake/inbox_reader.py`** — ele é o leitor observacional da UI (UX-RD-15), permanece intocado.
6. Adicionar teste em `tests/test_inbox_subtipos_mobile.py` com 5 arquivos sintéticos em 5 subpastas distintas.

## Validação ANTES (grep -- padrão (k))

```bash
# (a) Onde esta o walk hoje? Esperado: NENHUM rglob/walk em inbox_processor
grep -n "iterdir\|rglob\|walk" src/inbox_processor.py
# (b) Assinatura atual de detectar_tipo - precisa ganhar subtipo_mobile
grep -n "def detectar_tipo" src/intake/registry.py
# (c) Sidecar canonico onde adicionar campos - existe ja
ls inbox/.extracted/ 2>/dev/null | head -3
# (d) Vault Syncthing real
ls ~/Protocolo-Ouroboros/inbox/ 2>/dev/null
# (e) Categorias.ts canonico do app (8 subtipos, 4 areas)
sed -n '25,90p' ~/Desenvolvimento/Protocolo-Mob-Ouroboros/src/lib/share/categorias.ts
```

Confirma: (a) `inbox_processor.processar_inbox` usa `iterdir()` na raiz (sem walk), (b) `detectar_tipo` atual tem 4 params (precisa do 5º), (c) sidecar `.extracted/` existe e segue contrato sha8.json, (d) vault Syncthing em `~/Protocolo-Ouroboros/inbox/`, (e) app declara `INBOX_SUBTIPOS` com 8 entradas (pix/extrato/nota/exame/receita/garantia/contrato/outro) em 4 áreas (financeiro/saude/casa/outros).

## Não-objetivos (padrão (t))

- **NÃO** alterar o app mobile — mudança apenas no backend ETL.
- **NÃO** mover arquivos dentro de `inbox/<area>/<subtipo>/` — a estrutura compartilhada via Syncthing é intocável.
- **NÃO** apagar arquivos da inbox depois de processados — manter idempotência via sidecar `.extracted/<sha8>.json` (já existe).
- **NÃO** implementar o extrator DOC-27 (pix); essa é outra sprint. Aqui apenas roteamos quando DOC-27 existir.
- **NÃO** sincronizar Syncthing programaticamente; a config Syncthing é responsabilidade do dono (manual).

## Spec de implementação

### Edit 1 — `src/inbox_processor.py` (linhas 173-225, função `processar_inbox`)

Trocar a varredura plana por walk recursivo:

```python
def processar_inbox(diretorio_inbox: Path, diretorio_raw: Path | None = None) -> list[dict]:
    del diretorio_raw

    if not diretorio_inbox.exists():
        logger.warning("diretório inbox não encontrado: %s", diretorio_inbox)
        return []

    # MOB-bridge-4: walk recursivo (era iterdir plano).
    arquivos = sorted(
        f for f in diretorio_inbox.rglob("*")
        if f.is_file() and f.suffix.lower() in EXTENSOES_SUPORTADAS
    )

    if not arquivos:
        logger.info("nenhum arquivo para processar em %s", diretorio_inbox)
        return []

    logger.info("processando %d arquivo(s) do inbox via intake universal", len(arquivos))

    resultados: list[dict] = []
    contadores = {"processado": 0, "duplicata": 0, "nao_identificado": 0, "erro": 0}

    for arquivo in arquivos:
        # MOB-bridge-4: derivar area + subtipo_mobile do path relativo
        rel = arquivo.relative_to(diretorio_inbox)
        partes = rel.parts
        if len(partes) >= 3:
            area, subtipo_mobile = partes[0], partes[1]
        elif len(partes) == 2:
            area, subtipo_mobile = partes[0], None
        else:
            area, subtipo_mobile = None, None
        dicts = processar_arquivo(arquivo, area=area, subtipo_mobile=subtipo_mobile)
        resultados.extend(dicts)
        for d in dicts:
            contadores[d["status"]] = contadores.get(d["status"], 0) + 1
    ...
```

### Edit 2 — `src/intake/orchestrator.py::processar_arquivo_inbox` (linha 166)

Adicionar parâmetro opcional + propagar:

```python
def processar_arquivo_inbox(
    caminho: Path,
    *,
    area: str | None = None,
    subtipo_mobile: str | None = None,
) -> RelatorioRoteamento:
    ...
    decisao = detectar_tipo(
        caminho,
        mime,
        preview,
        pessoa=pessoa_detectada,
        subtipo_mobile=subtipo_mobile,
    )
    # Persistir area + subtipo_mobile no sidecar via router.py
```

### Edit 3 — `src/intake/registry.py::detectar_tipo` (linha ~90)

Adicionar 5º parâmetro + cascata de hint:

```python
_MAPPING_SUBTIPO_MOBILE_TO_TIPO: dict[str, str] = {
    "pix": "comprovante_pix_foto",
    "nota": "cupom_fiscal_foto",     # refinado por MIME abaixo (PDF -> nfce_modelo_65)
    "exame": "exame_medico",          # DOC-09
    "receita": "receita_medica",      # DOC-10
    "garantia": "cupom_garantia_estendida_pdf",
    "contrato": "contrato_locacao",   # DOC-21
    "outro": "indeterminado",          # cai em _classificar/
    # 'extrato': deliberadamente NAO mapeado -- cascata bancaria legada decide
}


def detectar_tipo(
    caminho: Path,
    mime: str,
    preview: str | None,
    pessoa: str = "_indefinida",
    subtipo_mobile: str | None = None,
) -> Decisao:
    """Hint subtipo_mobile (vindo do app) tem precedencia sobre classifier YAML
    quando mapeado em _MAPPING_SUBTIPO_MOBILE_TO_TIPO. Casos:

    1. subtipo_mobile=extrato OU sem hint => cascata atual (legado + YAML).
    2. subtipo_mobile mapeado => devolve Decisao com tipo canonico (sem rodar
       classifier YAML); preview ainda usado para extrair data_emissao_iso.
    3. tipo nao tem extrator pronto => Decisao com pasta_destino=_classificar/.
    """
    if subtipo_mobile and subtipo_mobile in _MAPPING_SUBTIPO_MOBILE_TO_TIPO:
        tipo_canonico = _MAPPING_SUBTIPO_MOBILE_TO_TIPO[subtipo_mobile]
        if subtipo_mobile == "nota" and mime == "application/pdf":
            tipo_canonico = "nfce_modelo_65"
        return _decidir_via_hint_mobile(caminho, mime, preview, pessoa, tipo_canonico)

    # ... cascata atual permanece intacta
```

### Edit 4 — sidecar `inbox/.extracted/<sha8>.json` ganha 2 campos

`src/intake/router.py` (onde o sidecar é gravado) precisa incluir os novos campos quando presentes:

```json
{
  "sha8": "abc12345",
  "tipo_arquivo": "comprovante_pix_foto",
  "area": "financeiro",
  "subtipo_mobile": "pix",
  "caminho_relativo": "inbox/financeiro/pix/2026-05-12-153014-pix.jpg",
  ...
}
```

Retrocompat: arquivos antigos sem esses campos continuam válidos; ler com `.get("area")` default None.

### Schema sidecar `.extracted/<sha8>.json`

Adicionar 2 campos:

```json
{
  "sha8": "abc12345",
  "tipo_arquivo": "comprovante_pix_foto",
  "area": "financeiro",                  // novo
  "subtipo_mobile": "pix",                // novo
  "caminho_relativo": "inbox/financeiro/pix/2026-05-12-153014-pix.jpg",
  ...
}
```

Retrocompat: arquivos antigos sem esses campos continuam válidos; novos sempre os têm.

### Testes (5 mínimos)

`tests/test_inbox_subtipos_mobile.py`:

1. `processar_inbox` faz walk recursivo: encontra 5 arquivos em 5 subpastas distintas.
2. Sidecar grava `area` e `subtipo_mobile` corretamente para arquivos em subpasta.
3. Hint `subtipo_mobile=pix` em JPEG roteia para `tipo=comprovante_pix_foto` (mesmo sem DOC-27 fechado, pasta destino vira `_classificar/` mas tipo é correto).
4. Hint `subtipo_mobile=exame` em PDF roteia para `tipo=exame_medico`.
5. Arquivo em `inbox/` raiz (sem subpasta) tem `area=None`, `subtipo_mobile=None` (retrocompat — cascata legada decide).

## Proof-of-work (padrão (u))

```bash
# 1. Criar arvore sintetica
mkdir -p /tmp/inbox_teste/{financeiro/pix,saude/exame,juridico/garantia,outros/outro}
touch /tmp/inbox_teste/financeiro/pix/teste-pix.jpg
touch /tmp/inbox_teste/saude/exame/teste-exame.pdf
touch /tmp/inbox_teste/juridico/garantia/teste-garantia.pdf
touch /tmp/inbox_teste/outros/outro/teste.txt
touch /tmp/inbox_teste/legado-na-raiz.csv  # retrocompat

# 2. Rodar listar_inbox
.venv/bin/python -c "
from src.intake.inbox_reader import listar_inbox
from pathlib import Path
arquivos = listar_inbox(Path('/tmp/inbox_teste'))
print(f'total={len(arquivos)}')
for a in arquivos:
    print(f'  area={a.area} subtipo={a.subtipo_mobile} caminho={a.caminho.name}')
"
# Esperado: total=5; cada um com area/subtipo corretos; legado-na-raiz tem area=None

# 3. Pytest
.venv/bin/pytest tests/test_inbox_subtipos_mobile.py -q -v

# 4. Gauntlet
make lint && make smoke
.venv/bin/pytest tests/ -q
```

## Critério de aceitação (gate (z))

1. `src/inbox_processor.py::processar_inbox` faz walk recursivo via `rglob("*")` filtrado por `EXTENSOES_SUPORTADAS`.
2. `src/intake/orchestrator.py::processar_arquivo_inbox` aceita kwargs `area`/`subtipo_mobile`.
3. `src/intake/registry.py::detectar_tipo` aceita parâmetro opcional `subtipo_mobile` e devolve `Decisao` canônico conforme `_MAPPING_SUBTIPO_MOBILE_TO_TIPO`.
4. Sidecar `inbox/.extracted/<sha8>.json` inclui novos campos `area` e `subtipo_mobile` quando aplicável; arquivos antigos permanecem válidos (retrocompat: getters com `.get(...)` default None).
5. `tests/test_inbox_subtipos_mobile.py` tem ≥ 5 testes, todos verdes.
6. Pytest baseline cresce de ≥ 2752 para ≥ 2757.
7. **`src/intake/inbox_reader.py` permanece intocado** (é leitor observacional de UI; padrão (a) cirurgia mínima).
8. `make lint` exit 0, `make smoke` 10/10.
9. Spec movida para `concluidos/` com commit-ref.

## Referência

- App mobile (categorias canônicas): `~/Desenvolvimento/Protocolo-Mob-Ouroboros/src/lib/share/categorias.ts` (constante `INBOX_SUBTIPOS`).
- Bridge 1/2/3 já concluídas: `docs/sprints/concluidos/MOB-bridge-{1,2,3}-spec.md` (se houver).
- **Alvo do refactor (3 arquivos)**: `src/inbox_processor.py` linha 173 + `src/intake/orchestrator.py` linha 166 + `src/intake/registry.py` linha ~90.
- `src/intake/inbox_reader.py` **NÃO É alvo** — é leitor UI puro (UX-RD-15).
- Sidecar: `inbox/.extracted/<sha8>.json` (path real, no repo).
- Vault Syncthing: `~/Protocolo-Ouroboros/inbox/` (path do dono em 2026-05-12).
- Plano de origem: `~/.claude/plans/preciso-que-use-o-crispy-stroustrup.md` Fase B.

*"Caminho profundo é caminho rico; quem só lê a raiz da inbox lê o título sem o livro." — princípio MOB-bridge-4*
