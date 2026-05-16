---
id: META-VALIDATOR-BRIEF-TRACKEADO
titulo: Mover padrões canônicos (a..ll) para arquivo trackeado pelo git
status: concluída  <!-- noqa: accent -->
concluida_em: 2026-05-13
prioridade: P0
data_criacao: 2026-05-13
fase: SANEAMENTO
epico: 8
depende_de: []
origem: auditoria de discoverability 2026-05-13. VALIDATOR_BRIEF.md está em .gitignore -- padrões (a..ll) incluindo os 3 novos (jj)(kk)(ll) só existem na máquina do dono. Nova sessão clonando o repo NÃO conhece esses padrões.
---

# Sprint META-VALIDATOR-BRIEF-TRACKEADO

## Contexto

`VALIDATOR_BRIEF.md` foi criado como arquivo local (gitignored) para acumular padrões empíricos descobertos sprint a sprint. Hoje contém os padrões `(a)..(ll)` -- inclui os 3 novos formalizados em 2026-05-13: (jj) Dossie obrigatório antes de código, (kk) Sprint encerra com produto final, (ll) Re-trabalho em loop fechado.

Como está gitignored, próxima sessão Claude Code clonando o repo NÃO tem acesso. Toda a "memória empírica" do projeto fica órfã.

## Hipótese

O conteúdo de padrões canônicos NÃO tem PII (são regras técnicas e operacionais). Pode ser trackeado sem risco.

## Entregável

1. **Decisão**: trackear `VALIDATOR_BRIEF.md` direto OU criar `docs/PADROES_CANONICOS.md` (trackeado) espelhando os padrões + manter VALIDATOR_BRIEF como link/symlink local.
   - Recomendação: criar `docs/PADROES_CANONICOS.md` (público, sem PII). Manter VALIDATOR_BRIEF.md local apenas para histórico/anotações.

2. **Migrar conteúdo**: padrões (a..ll) viram seção do novo arquivo. Estrutura preservada.

3. **Referências atualizadas**:
   - `contexto/COMO_AGIR.md` aponta para `docs/PADROES_CANONICOS.md`.
   - `docs/CICLO_GRADUACAO_OPERACIONAL.md` referencia o arquivo trackeado.
   - `docs/sprints/ROADMAP_ATE_PROD.md` cita o arquivo trackeado.

4. **Política futura**: novos padrões nascem em `docs/PADROES_CANONICOS.md` primeiro; VALIDATOR_BRIEF local é apenas espaço de rascunho.

## Acceptance

- `git ls-files docs/PADROES_CANONICOS.md` retorna o arquivo.
- Conteúdo do arquivo trackeado tem TODOS os padrões (a..ll).
- COMO_AGIR aponta para o trackeado.
- Lint zero. Smoke 10/10.

## Padrão canônico aplicável

(e) data/ no .gitignore -- distinção entre PII (gitignored) e padrões técnicos (trackeados).

---

*"Padrão que vive só na cabeça do supervisor morre quando muda a sessão." -- princípio do padrão público*
