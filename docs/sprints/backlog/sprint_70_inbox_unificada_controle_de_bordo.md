## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 70
  title: "Inbox unificada: Ouroboros consome ~/Controle de Bordo/Inbox/"
  touches:
    - path: src/integrations/controle_bordo.py
      reason: "novo adapter que lê vault e roteia arquivos financeiros"
    - path: src/inbox_processor.py
      reason: "integrar adapter ao fluxo atual; preservar lógica legada"
    - path: run.sh
      reason: "flag --inbox agora varre vault também"
    - path: mappings/inbox_routing.yaml
      reason: "novo: regras de roteamento (tipo -> destino) + lista de INBOX_SOURCES"
    - path: tests/test_controle_bordo_adapter.py
      reason: "testes do adapter com fixture de vault"
  n_to_n_pairs:
    - ["src/integrations/controle_bordo.py::VAULT_ROOT", "$BORDO_DIR env var"]
  forbidden:
    - "Modificar ~/Controle de Bordo/.sistema/"
    - "Mexer em ~/Controle de Bordo/Trabalho/"
    - "Mexer em ~/Controle de Bordo/Segredos/"
    - "Mexer em ~/Controle de Bordo/Arquivo/"
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_controle_bordo_adapter.py -v"
      timeout: 60
  acceptance_criteria:
    - "Variável de ambiente BORDO_DIR (default ~/Controle de Bordo) controla onde o vault está"
    - "Adapter varre 3 inbox sources: BORDO_DIR/Inbox/, ./inbox/ (raiz do projeto, legado), ./data/inbox/ (legado)"
    - "./run.sh --inbox consome as 3 sources na ordem acima"
    - "Arquivos financeiros (OFX/CSV bancário/PDF extrato/DANFE/NFC-e/holerite/cupom/boleto/receita médica/conta luz) SAEM das inbox sources e entram em data/raw/{pessoa}/{banco-ou-tipo}/"
    - "Arquivos NÃO-financeiros permanecem na vault inbox para o motor do vault processar (motor do vault é soberano)"
    - "Cópia do original preservada em data/raw/originais/{hash-sha256}{extensao} ANTES de qualquer processamento"
    - "Relatório de roteamento: lista por arquivo [origem, tipo detectado, destino, ação (move/copy/skip)]"
    - "mappings/inbox_routing.yaml declara as regras (tipos financeiros + lista de INBOX_SOURCES)"
    - "GOLDEN TEST: inbox/natacao_andre.pdf + inbox/natacao_andre2.pdf (já presentes) são detectados como boleto, movidos para data/raw/andre/boletos/ com cópia em data/raw/originais/"
  proof_of_work_esperado: |
    # Criar vault de teste sintético com 5 arquivos:
    #   2 CSVs Nubank, 1 PDF Itaú, 1 JPG recibo Pix, 1 MD de nota pessoal
    # Rodar adapter
    .venv/bin/python -m src.integrations.controle_bordo --dry-run --vault=/tmp/vault_test
    # esperado: 4 arquivos roteados (financeiros), 1 ignorado (MD)
    # com BORDO_DIR real:
    BORDO_DIR="$HOME/Controle de Bordo" .venv/bin/python -m src.integrations.controle_bordo --dry-run
    # relatório mostra inventário real da inbox
```

---

# Sprint 70 — Inbox unificada

**Status:** BACKLOG
**Prioridade:** P0 (fundação da integração com Controle de Bordo)
**Dependências:** ADR-18 aprovado
**Desbloqueia:** 71, 74, 80
**ADR:** ADR-18
**Issue:** INTEGRACAO-01 <!-- noqa: accent -->


## Problema

Hoje o Andre tem VÁRIOS lugares pra jogar arquivo e todos funcionam parcialmente:

1. `~/Controle de Bordo/Inbox/` — motor do vault Obsidian (ativo).
2. `~/Desenvolvimento/protocolo-ouroboros/inbox/` — legado no raiz do projeto; **hoje contém `natacao_andre.pdf`, `natacao_andre2.pdf`, `notas de garantia e compras.pdf`, `extrato dos debitos.pdf` que não estão sendo processados por ninguém** (descoberto em 2026-04-21).
3. `~/Desenvolvimento/protocolo-ouroboros/data/inbox/` — destino atual do pipeline, mas vazio hoje.

Fricção múltipla. Visão: uma inbox lógica que aceita qualquer ponto físico como entrada.

## O que já existe

- `src/inbox_processor.py` (Ouroboros) — detecta tipo via `src/intake/registry.py`, move para `data/raw/`.
- `~/Controle de Bordo/.sistema/scripts/inbox_processor.py` — motor do vault, detecta notas/documentos pessoais.
- ADR-18 define o contrato: arquivo financeiro é do Ouroboros, o resto é do vault.

## Implementação

### Fase 1 — Adapter

`src/integrations/controle_bordo.py`:

```python
"""Adapter que varre ~/Controle de Bordo/Inbox/ e roteia arquivos financeiros para o Ouroboros."""
import os
import shutil
import hashlib
from pathlib import Path
from src.intake.registry import detectar_tipo

VAULT_ROOT = Path(os.environ.get("BORDO_DIR", Path.home() / "Controle de Bordo"))
VAULT_INBOX = VAULT_ROOT / "Inbox"

TIPOS_FINANCEIROS = {
    "ofx", "csv_nubank_cc", "csv_nubank_cartao",
    "pdf_itau", "pdf_santander", "pdf_c6",
    "danfe", "nfce", "xml_nfe", "cupom_termico",
    "receita_medica", "cupom_garantia",
    "holerite_g4f", "holerite_infobase",
    "boleto", "conta_luz", "conta_agua",
}

def rotear(dry_run: bool = True) -> list[dict]:
    """Varre vault/Inbox e retorna plano de roteamento."""
    plano = []
    for arquivo in VAULT_INBOX.rglob("*"):
        if not arquivo.is_file():
            continue
        tipo = detectar_tipo(arquivo)
        destino = _destino(arquivo, tipo)
        acao = "move" if tipo in TIPOS_FINANCEIROS else "skip"
        plano.append({"arquivo": arquivo, "tipo": tipo, "destino": destino, "acao": acao})
    if not dry_run:
        for item in plano:
            if item["acao"] == "move":
                _preservar_original(item["arquivo"])
                shutil.move(str(item["arquivo"]), str(item["destino"]))
    return plano
```

### Fase 2 — Preservação obrigatória

```python
def _preservar_original(arquivo: Path) -> Path:
    hash_ = hashlib.sha256(arquivo.read_bytes()).hexdigest()[:16]
    dest = Path("data/raw/originais") / f"{hash_}{arquivo.suffix}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(arquivo, dest)
    return dest
```

### Fase 3 — Configuração

`mappings/inbox_routing.yaml`:

```yaml
# Múltiplas fontes de inbox, processadas em ordem:
inbox_sources:
  - path: "${BORDO_DIR}/Inbox"       # vault Obsidian (canônica, doravante)
    prioridade: 1
  - path: "./inbox"                  # legado na raiz do projeto
    prioridade: 2
  - path: "./data/inbox"             # legado dentro de data/
    prioridade: 3

# Tipos financeiros absorvidos pelo Ouroboros:
ouroboros:
  - ofx
  - csv_nubank_cc
  - csv_nubank_cartao
  - pdf_itau
  - pdf_santander
  - pdf_c6
  - danfe
  - nfce
  - xml_nfe
  - cupom_termico
  - receita_medica
  - cupom_garantia
  - holerite_g4f
  - holerite_infobase
  - boleto
  - conta_luz
  - conta_agua

# Destino por tipo (subpath dentro de data/raw/<pessoa>/)
destinos:
  boleto: boletos
  pdf_c6: c6_cc
  # ... (demais derivados do intake atual)

preservar_original: true
original_dir: data/raw/originais
```

### Fase 4 — Integração em run.sh

`run.sh --inbox` agora roda:
1. `src/integrations/controle_bordo.py` (varre vault inbox, roteia financeiros)
2. `src/inbox_processor.py` (processa data/inbox/ local caso ainda haja arquivos antigos)
3. Pipeline normal (`_detectar_extrator` + `ingerir`)

### Fase 5 — Testes

```python
def test_adapter_roteia_csv_nubank(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    inbox = vault / "Inbox"
    inbox.mkdir(parents=True)
    (inbox / "BANCARIO_NUBANK_CC_2026-04.csv").write_text("Data,Valor,...")
    monkeypatch.setenv("BORDO_DIR", str(vault))
    plano = rotear(dry_run=True)
    assert any(p["acao"] == "move" and "nubank" in str(p["tipo"]) for p in plano)

def test_adapter_preserva_nota_pessoal(tmp_path, monkeypatch):
    # nota .md deve ficar na inbox
    ...

def test_adapter_copia_para_originais_antes_de_mover(tmp_path, monkeypatch):
    # garantir que data/raw/originais/ tem cópia por hash
    ...
```

## Armadilhas

| A70-1 | Vault pode ter subpasta `Inbox/Pendentes/` que motor do vault usa | Varrer apenas arquivos diretos em `Inbox/`, não recursivo em `Pendentes/` |
| A70-2 | Permissão de mover arquivo que o Obsidian tem aberto | Usar `shutil.move` com retry + log warning se falhar |
| A70-3 | BORDO_DIR não existe no CI | Detectar via env e pular teste com `pytest.skip` se path não existe |
| A70-4 | Motor do vault roda periodicamente e pode conflitar | Documentar ordem: Ouroboros primeiro (move financeiros), vault depois (processa o resto) |

## Evidências

- [ ] `./run.sh --inbox` processa vault inbox real sem quebrar arquivos não-financeiros
- [ ] `data/raw/originais/{hash}.ext` tem cópia de cada arquivo movido
- [ ] Relatório stdout lista roteamento
- [ ] Testes verdes
- [ ] Documentação em `docs/GUIA_INGESTAO.md` (Sprint 57) atualizada para fluxo unificado

---

*"Uma porta só, um fluxo só." — princípio"*
