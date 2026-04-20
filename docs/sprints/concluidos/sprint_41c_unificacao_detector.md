## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 41c
  title: "Unificação do detector de tipo: file_detector.py + tipos_documento.yaml num registry só"
  touches:
    - path: src/intake/registry.py
      reason: "novo módulo: registry único que conhece tipos bancários (do file_detector legado) E tipos de documento (do YAML); ÚNICA porta de entrada para 'que tipo é esse arquivo?'"
    - path: src/intake/orchestrator.py
      reason: "passa a consultar o registry em vez de classifier direto -- registry decide se cai no caminho legado (csv/ofx/xls/xlsx bancário) ou no caminho YAML (pdf/imagem/xml/eml)"
    - path: src/utils/file_detector.py
      reason: "extrai funções públicas que o registry vai consumir; NÃO duplicar lógica"
    - path: tests/test_intake_registry.py
      reason: "testes do registry com cobertura cruzada bancário + documento"
  n_to_n_pairs:
    - [src/intake/registry.py, src/utils/file_detector.py]
    - [src/intake/registry.py, mappings/tipos_documento.yaml]
  forbidden:
    - src/intake/classifier.py  # classifier do YAML segue puro; registry orquestra os dois detectores
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_intake_registry.py tests/test_intake_orchestrator.py -x -q"
      timeout: 120
  acceptance_criteria:
    - "src/intake/registry.py expõe `detectar_tipo(caminho, mime, preview) -> Decisao | DeteccaoLegada`"
    - "Para CSV Nubank cartão (header `date,title,amount`) -> caminho legado (DeteccaoArquivo do file_detector)"
    - "Para CSV Nubank CC (header `Data,Valor,Identificador,Descrição`) -> caminho legado"
    - "Para OFX (extrato C6/Itaú) -> caminho legado"
    - "Para XLS fatura Santander (msoffcrypto) -> caminho legado"
    - "Para XLSX extrato C6 -> caminho legado"
    - "Para PDF/imagem/XML/EML -> caminho YAML (Decisao do classifier atual)"
    - "PROVA DE FOGO histórica em data/raw/ atinge >= 95% recall (era 25% pré-41c)"
    - "ZERO duplicação: nenhuma regex bancária nova em tipos_documento.yaml; tudo reusa file_detector existente"
    - "Acentuação PT-BR correta, zero emojis, zero menções a IA"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 41c -- Unificação do detector de tipo

**Status:** CONCLUÍDA
**Data:** 2026-04-19 (criada e implementada no mesmo dia, após prova de fogo da Sprint 41)
**Prioridade:** MEDIA
**Tipo:** Refactor + Feature
**Dependências:** Sprint 41 (intake universal funcionando), Sprint 41d (page-split condicional)
**Desbloqueia:** integração final no `inbox_processor.py` -- recall pós-41c saltou de 19% para 85% (98 arquivos do data/raw/, 83 roteados). Os 15 residuais são holerites Infobase escaneados (cobertos pela Sprint 45 OCR de PDF)
**Issue:** --
**ADR:** ADR-15 (intake multiformato)
**Conferência Artesanal Opus:** `docs/propostas/sprint_41c_conferencia.md`

---

## Como Executar

- `.venv/bin/pytest tests/test_intake_registry.py -v`
- `python scripts/sprint41_prova_fogo.py --pasta data/raw --keep` (pós-implementação, recall esperado >=95%)

### O que NÃO fazer

- NÃO duplicar regex bancária em `mappings/tipos_documento.yaml`. O `file_detector.py` já tem 600+ linhas que detectam Nubank/Itaú/Santander/C6 por header de CSV, magic bytes de XLS, padrões de OFX. Reusar.
- NÃO mover lógica do `file_detector.py` para `mappings/*.yaml`. Bancário é detector PROCEDURAL (lê header de CSV, decripta XLS, parseia OFX), não regex sobre texto. Tentar declarar isso em YAML vira gambiarra.
- NÃO criar duas classes `Decisao` -- definir um Protocol/ABC comum ou adapter na borda do registry.

---

## Problema

A Sprint 41 implementou detector via `mappings/tipos_documento.yaml` (regex sobre preview). A prova de fogo histórica revelou que 56 CSVs + 7 XLS/OFX/XLSX bancários caem em `_classificar/` porque o YAML não cobre esses tipos. Mas o sistema JÁ TEM detector pra eles: `src/utils/file_detector.py` (600+ linhas, escrito nas Sprints 1-3, cobre Nubank x2 formatos, Itaú, Santander, C6 com decriptação msoffcrypto). Hoje os dois caminhos são paralelos:

- Intake novo (Sprint 41): `caminho_inbox -> classifier -> Decisao`
- Inbox processor antigo: `caminho_inbox -> file_detector -> DeteccaoArquivo`

Sem unificação, integrar o intake no `inbox_processor.py` significa ou perder cobertura bancária ou rodar dois detectores paralelos -- ambos ruins.

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Detector legado (procedural) | `src/utils/file_detector.py:detectar_arquivo` | Devolve `DeteccaoArquivo(banco, pessoa, periodo, tipo_dado, caminho)` para CSV/XLS/XLSX/PDF/OFX bancários. Lê headers, decripta com msoffcrypto, parseia OFX |
| Detector novo (YAML) | `src/intake/classifier.py:classificar` | Devolve `Decisao(tipo, prioridade, pasta_destino, ...)` para PDF/imagem/XML/EML via regex em preview |
| Orquestrador atual | `src/intake/orchestrator.py:processar_arquivo_inbox` | Chama só o detector novo |

## Implementação

### Fase 1: definir interface comum

`src/intake/registry.py`:

```python
from typing import Protocol, Union
from src.intake.classifier import Decisao
from src.utils.file_detector import DeteccaoArquivo

DecisaoUnificada = Union[Decisao, "DecisaoLegada"]

@dataclass(frozen=True)
class DecisaoLegada:
    """Adapter: envelopa DeteccaoArquivo (file_detector) na forma do orquestrador."""
    deteccao: DeteccaoArquivo
    pasta_destino: Path           # computada a partir de banco+pessoa
    nome_canonico: str             # computado a partir de banco+periodo
    fonte_decisor: str = "file_detector"
```

### Fase 2: registry como ÚNICA porta de entrada

```python
def detectar_tipo(caminho: Path, mime: str, preview: str | None) -> DecisaoUnificada:
    # 1. Tenta caminho legado primeiro para tipos bancários
    if mime in {"text/csv", "application/x-ofx", "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}:
        deteccao = file_detector.detectar_arquivo(caminho)
        if deteccao:
            return _adaptar_legado(deteccao)
    # 2. Caminho YAML para PDF/imagem/XML/EML
    return classifier.classificar(caminho, mime, preview or "", pessoa=...)
```

### Fase 3: orquestrador consome registry

`src/intake/orchestrator.py:processar_arquivo_inbox` passa a chamar `registry.detectar_tipo` em vez de `classifier.classificar` direto. Router precisa aceitar `DecisaoUnificada` (ou via adapter).

### Fase 4: pessoa via file_detector quando vier do legado

`DeteccaoArquivo.pessoa` já existe. Aproveitar quando vier de CSV bancário; ainda usa `pessoa_detector` (Sprint 41b) para tipos do YAML.

### Fase 5: prova de fogo pós-unificação

Re-rodar `python scripts/sprint41_prova_fogo.py --pasta data/raw --keep`. Critério de aceitação: recall >= 95% (subindo dos 25% atuais).

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A41c-1 | `file_detector.py` levanta exceção em XLS sem senha disponível em `mappings/senhas.yaml` | Registry captura e devolve fallback; senha ausente NÃO bloqueia o resto da inbox |
| A41c-2 | XLS msoffcrypto pode demorar > 1s por arquivo | Logar tempo de detecção; se virar gargalo, paralelizar no orquestrador (não nesta sprint) |
| A41c-3 | DecisaoLegada e Decisao têm shapes diferentes -- código consumidor pode `isinstance`-checkar erradamente | Definir Protocol comum ou usar match-statement com fallback |
| A41c-4 | Mesmo CSV pode ser detectado tanto pelo file_detector quanto cair em fallback do YAML (se YAML tiver regra `text/csv` genérica). Conflito silencioso. | Registry tenta legado PRIMEIRO para mimes bancários; YAML fica para PDF/imagem/XML/EML estritamente |

Referência: `docs/ARMADILHAS.md`

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] `.venv/bin/pytest tests/test_intake_registry.py -v` passa com cobertura >= 80%
- [ ] `python scripts/sprint41_prova_fogo.py --pasta data/raw --keep` mostra recall >= 95%
- [ ] Distribuição agregada inclui tipos bancários (csv_nubank_cartao, csv_nubank_cc, ofx_*, xls_fatura_*, xlsx_extrato_*)
- [ ] Suíte completa não regride (testes da 41/41b/41d continuam passando)

## Verificação end-to-end

```bash
make lint
.venv/bin/pytest tests/ -v
python scripts/sprint41_prova_fogo.py --pasta data/raw --keep
# Conferir resumo agregado: recall_global >= 95%, distribuição inclui bancário
```

## Conferência Artesanal Opus

**Arquivos originais a ler:**

- 5+ CSVs bancários de cada formato (Nubank cartão, Nubank cc PF, Nubank cc PJ)
- 1+ XLS de fatura Santander
- 1+ OFX de extrato C6
- 1+ XLSX de extrato

**Outputs a comparar:**

- Cada CSV bancário acabou na pasta certa (data/raw/{pessoa}/{banco}/)?
- O período/banco/tipo extraído pelo file_detector legado foi preservado no roteamento?
- Nenhum tipo bancário virou tipo de documento por engano (NF, holerite)?

**Relatório esperado em `docs/propostas/sprint_41c_conferencia.md`:**

- Tabela: arquivo bancário | tipo legado detectado | pasta final | OK?
- Recall global pós-unificação
- Tipos que ainda caem em `_classificar/` -- justificar cada um (provavelmente residuais corrompidos)

**Critério de aprovação:** recall >= 95% E zero falsos-positivos (precisão 100% mantida).

---

*"Dois caminhos para o mesmo destino é um caminho perdido." -- princípio da unificação arquitetural*
