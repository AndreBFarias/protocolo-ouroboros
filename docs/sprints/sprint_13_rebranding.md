# Sprint 13 -- Protocolo Ouroboros: Rebranding

## Status: Concluída (commit b73068a)

## Objetivo

Renomear o projeto de "Financas" / "Controle de Bordo" para **Protocolo Ouroboros**. Atualizar todas as referências, renomear diretório e repositório Git, criar arquivo `.desktop` com ícone para lançamento direto do menu interativo.

## Contexto

O logo do projeto (assets/icon.png) já carrega a identidade Ouroboros -- serpente estilizada envolvendo o escudo AV, na paleta Dracula. O nome "Controle de Bordo" era provisório. "Protocolo Ouroboros" reflete a natureza cíclica do pipeline financeiro: dados entram, são transformados, geram insights que alimentam decisões que geram novos dados.

## Escopo

### 1. Renomear Diretório e Repositório

- Renomear pasta `~/Desenvolvimento/Financas` para `~/Desenvolvimento/Ouroboros` (ou `protocolo-ouroboros`)
- Renomear repositório no GitHub: `Financas` -> `protocolo-ouroboros`
- Atualizar remote Git: `git remote set-url origin git@github.com-personal:[REDACTED]/protocolo-ouroboros.git`
- Atualizar SSH alias se necessário (Armadilha #8)

### 2. Atualizar Referências Internas

Arquivos com referências ao nome antigo (29 arquivos identificados):

**Código-fonte (crítico):**
- `src/pipeline.py` -- nome do XLSX `controle_bordo_*.xlsx`
- `src/dashboard/dados.py` -- caminho `controle_bordo_2026.xlsx`
- `src/dashboard/app.py` -- título do dashboard
- `src/utils/validator.py` -- referência ao XLSX
- `src/obsidian/sync.py` -- referências ao projeto
- `src/load/formatacao_md.py` -- alt text do logo
- `run.sh` -- banner "CONTROLE DE BORDO", referências ao XLSX
- `Makefile` -- referências ao XLSX
- `install.sh` -- referências ao projeto

**Documentação:**
- `CLAUDE.md` -- missão, estrutura, referências
- `GSD.md` -- onboarding
- `README.md` -- título, descrição, estrutura
- `docs/ARCHITECTURE.md`
- `docs/MODELOS.md`
- `docs/AUDITORIA_SPRINTS.md`
- `docs/ROADMAP.md`
- `docs/adr/ADR-06-obsidian-sync.md`
- `docs/sprints/sprint_*.md` (referências cruzadas)
- `DADOS_FALTANTES.md`

**Scripts e relatórios:**
- `scripts/gauntlet/gauntlet.py`
- `scripts/gauntlet/reporters/markdown_reporter.py`

**Contexto (pode ser removido/ignorado):**
- `contexto/*.md` -- arquivos de contexto histórico

### 3. Renomear XLSX de Saída

- `controle_bordo_2026.xlsx` -> `ouroboros_2026.xlsx`
- Atualizar todas as referências no código que buscam `controle_bordo_*.xlsx`
- Manter compatibilidade: se existir `controle_bordo_*.xlsx` antigo, ler dele também (migração)

### 4. Atualizar Dashboard

- Título da página: "Protocolo Ouroboros"
- Banner/sidebar: usar nome novo
- Favicon: usar `assets/icon.png` se Streamlit suportar

### 5. Criar Arquivo .desktop

Criar `ouroboros.desktop` para lançamento direto no Linux:

```ini
[Desktop Entry]
Name=Protocolo Ouroboros
Comment=Pipeline Financeiro Pessoal
Exec=bash -c 'cd ~/Desenvolvimento/Ouroboros && ./run.sh'
Icon=~/Desenvolvimento/Ouroboros/assets/icon.png
Terminal=true
Type=Application
Categories=Finance;Office;
StartupNotify=false
```

- `Terminal=true` abre o terminal do sistema
- O `run.sh` exibe o menu interativo automaticamente
- Ícone usa o `icon.png` existente
- Adicionar instrução no install.sh para copiar para `~/.local/share/applications/`

### 6. Atualizar run.sh Banner

```
  ╔══════════════════════════════════════════════════╗
  ║                                                  ║
  ║           PROTOCOLO OUROBOROS                     ║
  ║           Pipeline Financeiro Pessoal            ║
  ║                                                  ║
  ╚══════════════════════════════════════════════════╝
```

### 7. Atualizar README.md

- Título: "Protocolo Ouroboros"
- Descrição refletindo o novo nome
- Badges atualizados

## Processo

1. Renomear diretório local e repositório GitHub
2. Buscar e substituir todas as referências (grep + sed automatizado)
3. Atualizar XLSX de saída e compatibilidade
4. Atualizar dashboard
5. Criar .desktop e integrar no install.sh
6. Testar: `make lint`, gauntlet, dashboard, menu interativo
7. Commit + push para novo remote

## Critério de Sucesso

- [x] Diretório e repo renomeados
- [x] Zero referências a "Financas" ou "Controle de Bordo" no código (exceto contexto histórico)
- [x] XLSX de saída com nome novo
- [x] Dashboard com título novo
- [x] `.desktop` funcional (clique abre terminal + menu)
- [x] Gauntlet passando (lint limpo)
- [x] Lint limpo
- [x] Git push para novo remote funcional

## Dependências

Nenhuma. Pode ser executada a qualquer momento.

## Riscos

- Paths hardcoded em scripts externos (Obsidian vault, cron jobs)
- Backups que referenciam caminho antigo
- SSH alias precisa ser atualizado
- XLSX antigo precisa ser migrado ou mantido em compatibilidade

---

*"A serpente que não consegue trocar de pele morre. Da mesma forma, as mentes que não mudam de opinião cessam de ser mentes." -- Friedrich Nietzsche*
