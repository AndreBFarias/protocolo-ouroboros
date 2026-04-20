## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 41b
  title: "Auto-detecção de pessoa no intake (CPF do conteúdo + path heurístico)"
  touches:
    - path: src/intake/pessoa_detector.py
      reason: "novo módulo: detecta pessoa a partir de CPF do preview ou de pista no path"
    - path: src/intake/orchestrator.py
      reason: "passa a chamar pessoa_detector quando pessoa==None ou '_indefinida'"
    - path: mappings/cpfs_pessoas.yaml
      reason: "novo mapeamento CPF (sem máscara) -> pessoa canônica (andre/vitoria/casal)"
    - path: tests/test_intake_pessoa_detector.py
      reason: "testes unitários e integração com orchestrator"
  n_to_n_pairs:
    - [mappings/cpfs_pessoas.yaml, src/intake/pessoa_detector.py]
  forbidden:
    - src/intake/classifier.py  # detector de pessoa é decisão SEPARADA da decisão de tipo
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_intake_pessoa_detector.py tests/test_intake_orchestrator.py -x -q"
      timeout: 60
  acceptance_criteria:
    - "Detecta pessoa a partir do PRIMEIRO CPF encontrado no preview (regex tolerante de glyph_tolerant.py)"
    - "Cobertura mínima do mappings/cpfs_pessoas.yaml: CPFs do casal já registrados"
    - "Quando CPF do preview não consta no mapping, devolve 'casal' (fallback seguro -- nunca chuta André/Vitória)"
    - "Quando preview não traz CPF, cai no fallback de path: pasta pai 'andre'/'vitoria' do arquivo da inbox vence; senão 'casal'"
    - "Orquestrador chama pessoa_detector ANTES de classificar quando pessoa não foi explicitada (default '_indefinida' vira detect)"
    - "Logs registram a fonte da decisão (CPF X / path Y / fallback) -- auditoria"
    - "mappings/cpfs_pessoas.yaml NÃO é commitado com CPFs reais -- entra no .gitignore (decisão LGPD); fica em .gitignore com template em mappings/cpfs_pessoas.yaml.example"
    - "Acentuação PT-BR correta, zero emojis, zero menções a IA"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 41b -- Auto-detecção de pessoa no intake

**Status:** CONCLUÍDA
**Data:** 2026-04-19 (criada e implementada no mesmo dia)
**Prioridade:** MEDIA
**Tipo:** Feature
**Dependências:** Sprint 41 (intake universal funcionando; orquestrador exposto)
**Desbloqueia:** integração final do intake no `inbox_processor.py` -- pessoa deixa de ser parâmetro hardcoded
**Issue:** --
**ADR:** ADR-15 (intake multiformato)

---

## Como Executar

- `.venv/bin/pytest tests/test_intake_pessoa_detector.py -v`
- `python scripts/sprint41_prova_fogo.py --keep --pessoa _detect` (quando o flag for adicionado)

### O que NÃO fazer

- NÃO fundir detecção de pessoa com classificação de tipo. São decisões ortogonais; misturar polui o `classifier.py` que hoje é puro.
- NÃO inferir pessoa a partir do TIPO do documento (ex.: "holerite -> André"). Documentos do casal trafegam pelos dois lados; inferir por tipo gera erro silencioso.
- NÃO commitar `mappings/cpfs_pessoas.yaml` com CPFs reais. Arquivo entra no `.gitignore` (decisão LGPD). Repo só carrega `mappings/cpfs_pessoas.yaml.example` com placeholders.

---

## Problema

Hoje o orquestrador (`src/intake/orchestrator.py`) recebe `pessoa` como parâmetro com default `_indefinida`. A prova de fogo da Sprint 41 rodou com `pessoa="andre"` hardcoded. Em produção, isso significa que:

- Documentos da Vitória chegando à inbox vão pra pasta do André.
- Documentos do casal (cupons compartilhados) também.
- O `pasta_destino_template: "data/raw/{pessoa}/garantias_estendidas/"` vira uma decisão sem base.

A Sprint 41 deixou isso em aberto deliberadamente (princípio "uma sprint, um escopo"). Esta sprint fecha o ciclo.

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Extrator de CPF | `src/intake/glyph_tolerant.py:extrair_cpf` | Devolve CPF canônico tolerante a glyphs (`051.273. 731-22` -> `051.273.731-22`). **Reusar.** |
| Detecção por path | `src/extractors/base.py:_detectar_pessoa` | Heurística antiga: pasta pai `andre`/`vitoria` -> pessoa. Considerar reuso ou cópia adaptada. |
| Logger | `src/utils/logger.py:configurar_logger` | Reusar para auditoria das decisões. |

## Implementação

### Fase 1: módulo `src/intake/pessoa_detector.py`

```python
from pathlib import Path
from typing import Literal
import yaml

from src.intake.glyph_tolerant import extrair_cpf
from src.utils.logger import configurar_logger

logger = configurar_logger("intake.pessoa")
Pessoa = Literal["andre", "vitoria", "casal", "_indefinida"]

_PATH_MAPPING = Path(__file__).resolve().parents[2] / "mappings" / "cpfs_pessoas.yaml"
_CACHE_CPFS: dict[str, Pessoa] | None = None


def detectar_pessoa(
    caminho_arquivo: Path,
    preview_texto: str | None,
) -> tuple[Pessoa, str]:
    """Devolve (pessoa, fonte_da_decisao).

    Ordem de tentativas:
      1. CPF no preview -> consulta mappings/cpfs_pessoas.yaml
      2. Pasta pai do arquivo (`andre`, `vitoria`) -> usa direto
      3. Fallback `casal` (NUNCA chuta André/Vitória sem evidência)
    """
    if preview_texto:
        cpf = extrair_cpf(preview_texto)
        if cpf:
            mapeamento = _carregar_mapeamento()
            cpf_chave = cpf.replace(".", "").replace("-", "")
            if cpf_chave in mapeamento:
                return mapeamento[cpf_chave], f"CPF {cpf}"
    pasta_pai = caminho_arquivo.parent.name.lower()
    if pasta_pai in {"andre", "vitoria"}:
        return pasta_pai, f"path '{pasta_pai}/'"
    return "casal", "fallback (sem CPF identificável + pasta pai não-pessoa)"


def recarregar_mapeamento(path: Path | None = None) -> dict[str, Pessoa]:
    """Recarrega mapping de CPFs. Use em testes ou após editar o YAML."""
    ...
```

### Fase 2: integração no orquestrador

`src/intake/orchestrator.py:processar_arquivo_inbox`:

```python
def processar_arquivo_inbox(
    caminho_inbox: Path,
    pessoa: str | None = None,   # None = auto-detect
) -> RelatorioRoteamento:
    ...
    if pessoa in (None, "_indefinida"):
        # Detect com base no PRIMEIRO artefato com preview disponível
        preview_para_detect = _primeiro_preview_disponivel(...)
        pessoa, fonte = detectar_pessoa(caminho_inbox, preview_para_detect)
        logger.info("pessoa auto-detectada: %s (fonte: %s)", pessoa, fonte)
    ...
```

Decisão de design: detecta UMA vez por arquivo da inbox (não por artefato). Cupons de garantia do mesmo PDF têm o mesmo CPF; bater repetidamente seria desperdício.

### Fase 3: `mappings/cpfs_pessoas.yaml.example`

```yaml
# CPFs sem máscara (apenas dígitos), valor = pessoa canônica
# 'casal' para CPFs compartilhados (CNPJ-MEI vinculado aos dois)
# COPIE este arquivo para mappings/cpfs_pessoas.yaml e preencha
# (cpfs_pessoas.yaml está no .gitignore -- LGPD)

cpfs:
  "00000000000": andre
  "11111111111": vitoria
  # adicione conforme necessário
```

`.gitignore` ganha entrada `mappings/cpfs_pessoas.yaml`.

### Fase 4: testes

- `test_detect_via_cpf_no_preview_casa_no_yaml`
- `test_detect_via_path_quando_cpf_ausente`
- `test_detect_fallback_casal_quando_nada_identifica`
- `test_detect_cpf_glyph_corrompido_funciona` (reusa fixture do glyph_tolerant)
- `test_orchestrator_chama_detector_quando_pessoa_e_None`
- `test_orchestrator_respeita_pessoa_explicita_e_pula_detector`

### Fase 5: prova de fogo atualizada

`scripts/sprint41_prova_fogo.py` ganha flag `--pessoa _detect` que passa `None` ao orquestrador. Roda contra os mesmos 2 PDFs e mostra qual pessoa foi inferida + fonte.

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A41b-1 | CPF no PDF de cupom de garantia é do SEGURADO, NÃO necessariamente da pessoa que comprou | Para CASOS de produto compartilhado (presente, conta conjunta) o CPF do segurado pode discordar de quem efetivamente recebe a NFC-e. Em ambiguidade, fica `casal` -- supervisor revisa |
| A41b-2 | CPF aparece com glyph corrompido (`051.273. 731-22` no `pdf_notas.pdf`) | `extrair_cpf` da peça 1 já normaliza; não reescrever |
| A41b-3 | YAML de CPFs vazado em commit = LGPD violada | `.gitignore` + commit-hook que bloqueia `mappings/cpfs_pessoas.yaml` (reusa lógica do `senhas.yaml`) |
| A41b-4 | Inbox flat: arquivo direto em `inbox/` não tem pasta pai informativa | Por isso o fallback é `casal`, NUNCA chuta André/Vitória |
| A41b-5 | Reescrita de pessoa em reprocessamento (mesmo arquivo, ano diferente, casal mudou de CPF) | Pessoa é decidida na PRIMEIRA passada; reprocessar requer apagar entrada no grafo (Sprint 42) |

Referência: `docs/ARMADILHAS.md`

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] `.venv/bin/pytest tests/test_intake_pessoa_detector.py -v` passa com cobertura >= 85%
- [ ] `python scripts/sprint41_prova_fogo.py --pessoa _detect` mostra "pessoa auto-detectada" no log para os 2 PDFs reais
- [ ] `mappings/cpfs_pessoas.yaml.example` publicado; `mappings/cpfs_pessoas.yaml` no `.gitignore`

## Verificação end-to-end

```bash
make lint
.venv/bin/pytest tests/test_intake_pessoa_detector.py tests/test_intake_orchestrator.py -v
python scripts/sprint41_prova_fogo.py --pessoa _detect --keep
# Conferir log: "pessoa auto-detectada: andre (fonte: CPF 051.273.731-22)"
```

## Conferência Artesanal Opus

**Arquivos originais a ler:**

- `inbox/pdf_notas.pdf` (CPF do segurado: `051.273.731-22` -- esperado: andre, fonte CPF)
- `inbox/notas de garantia e compras.pdf` (mesmo CPF nas garantias; NFC-e tem `CONSUMIDOR CPF: 051.273.731-22` -- esperado: andre)
- (futuro) arquivo da Vitória; arquivo sem CPF claro

**Outputs a comparar:**

- Log do orquestrador (linhas `pessoa auto-detectada: <X> (fonte: <Y>)`)
- Pasta final em `data/raw/<pessoa>/...` -- cada artefato deve ir para a pessoa correta

**Checklist:**

1. CPF no preview foi extraído pelo `extrair_cpf` (com glyph-tolerance)?
2. Mapeamento CPF -> pessoa funcionou?
3. Sem CPF e sem pasta-pai informativa, caiu em `casal` (não chutou)?
4. Pessoa explícita (passada por parâmetro) ainda funciona, sem detector ser chamado?

**Relatório esperado em `docs/propostas/sprint_41b_conferencia.md`:**

- Tabela: arquivo | CPF detectado | pessoa inferida | fonte | esperado | OK?
- Variantes de fallback que apareceram em produção

**Critério de aprovação:** 100% dos arquivos da inbox real são roteados para a pessoa correta OU para `casal` (nunca chutado errado para André/Vitória sem evidência).

---

*"Onde não há prova, não há acusação." -- princípio do direito civilizado*
