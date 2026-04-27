## 0. SPEC (machine-readable)

```yaml
sprint:
  id: INFRA-PII-HISTORY
  title: "Limpar PII real do git history (CPF do Andre + CNPJs em docstrings antigas)"
  prioridade: P3
  estimativa: "2-3h (sessão supervisionada com humano + backup completo antes)"
  origem: "achado durante consertodo pre-commit framework em 2026-04-27 -- mascaramento atual cobre o presente, mas history retem PII real"
  pre_requisitos_humanos:
    - "Backup completo do repo (.git inteiro tar.gz arquivado em local externo)"
    - "Coordenação se houver fork/clone em outras maquinas (history rewrite invalida hashes)"
    - "Janela combinada para force-push em main (operação destrutiva e visível)"
    - "Confirmação explicita do dono no início da sessão -- não iniciar sem"
  touches:
    - path: ".git/ (history reescrito via git filter-repo)"
      reason: "operação destrutiva no history; não toca working tree atual"
    - path: tests/test_pii_history.py
      reason: "regressão: grep no log não encontra padrões mascarados"
  forbidden:
    - "Iniciar sem backup confirmado E aprovação explicita do dono"
    - "Usar git filter-branch (deprecated, lento, propenso a erros)"
    - "Force-push antes de validar working tree atual igual a versão limpa"
    - "Mexer em data/raw/ ou data/output/ (gitignored, não entram no history)"
    - "Apagar commits inteiros -- substituir conteudo, preservar mensagem e SHA-history"
  tests:
    - cmd: "git log --all --full-history -p | grep -E '\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}|\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{2}'"
    - cmd: ".venv/bin/pytest tests/test_pii_history.py -v"
    - cmd: "make smoke"
    - cmd: "make lint"
  acceptance_criteria:
    - "git log --all -p não retorna mais nenhum CPF formatado real (51.273.731-22 e variantes)"
    - "git log --all -p não retorna CNPJs '00.776.574/0160-79' nem '61.074.175/0001-38' do historico"
    - "Working tree atual (main HEAD) inalterado: pytest 1.620 + smoke 8/8 + lint verde"
    - "Backup .git anterior preservado em arquivo externo (caminho documentado em docs/INCIDENTES/pii_history_2026-XX-XX.md)"
    - "Force-push autorizado e executado para origin/main"
    - "Coordenação com outros clones documentada (devem clone fresh apos rewrite)"
  proof_of_work_esperado: |
    # Pre-requisito: backup
    cd /home/andrefarias/Desenvolvimento
    tar czf protocolo-ouroboros-backup-pre-pii-rewrite-$(date +%Y%m%d).tar.gz protocolo-ouroboros/
    
    # Confirmar pelo menos os 3 padrões no history atual
    cd protocolo-ouroboros
    git log --all -p | grep -c '051\.273\.731-22'   # número N de ocorrencias
    git log --all -p | grep -c '00\.776\.574/0160-79'
    git log --all -p | grep -c '61\.074\.175/0001-38'
    
    # Sweep amplo para detectar outros CPFs/CNPJs reais que possam ter escapado
    git log --all -p | grep -oE '\d{3}\.\d{3}\.\d{3}-\d{2}' | sort -u
    git log --all -p | grep -oE '\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}' | sort -u
    # Validar manualmente cada hit: real (mascarar) vs sintético de teste (manter)
    
    # Aplicar git filter-repo (instalar antes: pipx install git-filter-repo)
    git filter-repo \
      --replace-text <(echo "
    051.273.731-22==>XXX.XXX.XXX-XX
    00.776.574/0160-79==>XX.XXX.XXX/XXXX-XX
    61.074.175/0001-38==>XX.XXX.XXX/XXXX-XX
    ")
    
    # Validar working tree apos rewrite
    .venv/bin/pytest tests/ -q       # 1.620+ passed
    make smoke                       # 8/8
    make lint                        # verde
    git log --all -p | grep -c '051\.273\.731-22'   # 0
    
    # Force-push (apos confirmação FINAL do dono)
    git push --force-with-lease origin main
```

---

# Sprint INFRA-PII-HISTORY -- Limpar PII real do git history

**Status:** BACKLOG (P3, criada 2026-04-27)
**Origem:** achado durante o conserto do pre-commit framework (commit `75d140f`). Mascaramento atual cobre o presente -- working tree em `main` HEAD não tem mais PII real em docstrings -- mas o git history retem todos os blobs antigos com os valores reais.

## Motivação

Auditoria 2026-04-27 mascarou 3 ocorrencias de PII em docstrings/comentários `src/`:

| Arquivo | Linha | PII mascarada |
|---------|-------|---------------|
| `src/intake/pessoa_detector.py` | 26 | CPF real do dono "051.273.731-22" -> "XXX.XXX.XXX-XX" |
| `src/intake/glyph_tolerant.py` | 26 | CNPJ "00.776.574/0160-79" -> "XX.XXX.XXX/XXXX-XX" |
| `src/extractors/cupom_garantia_estendida_pdf.py` | 133 | CNPJ "61.074.175/0001-38" (corporativo seguradora) -> "XX.XXX.XXX/XXXX-XX" |

A versão atual em `main` esta limpa. Mas:

1. **`git log -p`** ainda revela os valores reais (basta rodar uma vez).
2. **Forks/clones** (se existirem) carregam o history.
3. **GitHub indexa o history** -- valores podem aparecer em busca.

CPF do dono é PII pessoal sensivel (não apenas corporativo público). Mesmo que repo seja privado, principio de minimizacao LGPD recomenda não guardar PII desnecessaria.

## Por que P3 e não P1

- Repo é privado (`AndreBFarias/protocolo-ouroboros`, identidade pessoal via SSH alias).
- Dono único, sem colaboradores externos.
- Risco de vazamento é baixo -- ninguem alem do dono clona.
- Trade-off: history rewrite é destrutivo, requer coordenação, pode quebrar referencias em PRs/issues. So vale o esforco quando há sinal claro de exposição.

Se um dia o repo for tornar público OU houver colaborador externo OU GitHub indexar -- promover para P0 imediato.

## Decisão do supervisor anterior (preservada na memoria)

Em sessões 2026-04-23/24, o dono explicitou: "aceitar PII historico (pre-sessão) como esta; history rewrite destrutivo dispensado". Esta sprint **não reverte essa decisão** -- formaliza o caminho caso a decisão mude no futuro.

## Escopo

### Fase 1 -- Sweep e classificação (45min)

Mapear todos os CPF/CNPJ reais no history. Distinguir:

- **PII real do casal:** CPF Andre + CPF Vitoria + CNPJ MEI Andre + CNPJ MEI Vitoria. Cobertura via memoria `project_identificadores_pessoas.md`.
- **CNPJs corporativos públicos:** G4F (`07.094.346/0002-26`), Itau, Santander, etc. Manter como estao.
- **Fixtures sintéticas em testes:** `XXX.XXX.XXX-XX`, `123.456.789-00`, etc. Manter.

Comando:

```bash
git log --all -p | grep -oE '\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}' | sort -u > /tmp/pii_candidatos.txt
# Revisar manualmente cada linha; classificar real vs público vs sintético.
```

### Fase 2 -- Backup completo (15min)

```bash
cd /home/andrefarias/Desenvolvimento
tar czf protocolo-ouroboros-backup-pre-pii-rewrite-$(date +%Y%m%d-%H%M).tar.gz protocolo-ouroboros/
# Salvar em local externo (pendrive USB ou cloud pessoal). NAO no próprio repo.
```

### Fase 3 -- Aplicar `git filter-repo` (30min)

Pre-requisito de instalacao:
```bash
pipx install git-filter-repo
# OU: sudo apt install git-filter-repo
```

Arquivo de substituições (`/tmp/pii_replacements.txt`):
```
051.273.731-22==>XXX.XXX.XXX-XX
00.776.574/0160-79==>XX.XXX.XXX/XXXX-XX
61.074.175/0001-38==>XX.XXX.XXX/XXXX-XX
# Adicionar os outros candidatos confirmados como reais na Fase 1
```

Comando:
```bash
cd protocolo-ouroboros
git filter-repo --replace-text /tmp/pii_replacements.txt
```

### Fase 4 -- Validação (30min)

```bash
git log --all -p | grep -c '051\.273\.731-22'  # 0
.venv/bin/pytest tests/ -q                       # 1.620+ passed
make smoke                                       # 8/8
make lint                                        # verde
```

Diff vs main remoto:
```bash
git log --oneline origin/main..HEAD     # commits novos? não deve haver
git diff origin/main..HEAD              # working tree diff? não deve haver
```

Se tudo verde, **pedir confirmação FINAL do dono** antes do force-push.

### Fase 5 -- Force-push e documentação (30min)

```bash
git push --force-with-lease origin main
```

Documentar incidente em `docs/INCIDENTES/pii_history_<data>.md`:
- Lista de PII removida.
- SHA antes do rewrite (pode estar no `.git/logs/`).
- Caminho do backup.
- Coordenação com clones externos (se houver).

### Fase 6 -- Teste regressivo (15min)

`tests/test_pii_history.py`:

```python
import subprocess

PII_REAIS = [
    "051.273.731-22",          # CPF Andre
    "00.776.574/0160-79",      # CNPJ exemplo glyph_tolerant
    "61.074.175/0001-38",      # CNPJ seguradora cupom_garantia
    # ... adicionar outros confirmados na Fase 1
]


def test_pii_real_nao_aparece_em_git_log():
    log = subprocess.run(
        ["git", "log", "--all", "-p"],
        capture_output=True, text=True, check=False,
    ).stdout
    achados = [pii for pii in PII_REAIS if pii in log]
    assert not achados, f"PII real encontrada no history: {achados}"
```

## Armadilhas

- **`git filter-branch` esta deprecated** (lento, propenso a corromper objects). Use APENAS `git filter-repo` (Python tool, ~50x mais rapido e seguro).
- **History rewrite invalida todos os SHAs antigos.** Se há referencia a SHA em PRs, issues, ou docs externos, vai quebrar. Auditar antes.
- **Submodules ou LFS** podem não ser afetados. Não temos no projeto, mas validar.
- **`git reflog`** ainda guarda referencias antigas localmente por 90 dias. Para limpeza COMPLETA: `git reflog expire --expire=now --all && git gc --prune=now --aggressive`. Não obrigatório (reflog é local).
- **Backup é inegociável.** Se algo der errado no filter-repo, a forma de voltar é restaurar o tar.gz.

## Dependências

- `git filter-repo` instalado (`pipx install git-filter-repo`).
- Backup completo do repo em local externo.
- Confirmação explicita do dono em sessão supervisionada.
- Janela acordada para force-push (operação visível em GitHub).

## Pos-fix

- Se um dia o repo for ser tornado público, esta sprint torna-se P0 e bloqueante.
- Manter `hooks/check_dados_financeiros.py` ativo no pre-commit framework para impedir reintroducao no futuro.
- Atualizar `mappings/pessoas.yaml` (gitignored) para conter PII real ai e em lugar nenhum mais.

---

*"O passado não se apaga, mas pode ser reescrito quando a privacidade pede." -- principio do history-clean*
