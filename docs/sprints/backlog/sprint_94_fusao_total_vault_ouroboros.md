## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 94
  title: "Fusão total (Modelo B) -- Ouroboros vira a Central de Controle de Vida"
  touches:
    - path: docs/adr/ADR-21-central-controle-vida.md
      reason: "formaliza decisão arquitetural de longo prazo"
    - path: docs/ROADMAP.md
      reason: "adiciona Fase OMEGA -- fusão total"
    - path: contexto/CONTEXTO.md
      reason: "atualiza Visão de Futuro como roadmap definitivo"
    - path: docs/sprints/backlog/sprint_94a_*.md
      reason: "sub-sprints do plano em fases"
  forbidden:
    - "Quebrar contrato ADR-18 (forbidden zones) sem migração explícita domínio por domínio"
    - "Implementar absorção de domínio novo sem extrator + regra YAML + teste (mesma rigor do financeiro)"
    - "Deixar o financeiro regredir em qualidade durante expansão"
  tests:
    - cmd: "make lint"
    - cmd: "ls docs/adr/ADR-21-*.md"
  acceptance_criteria:
    - "ADR-21 criado formalizando Modelo B como norte canônico do projeto"
    - "Roadmap ganha Fase OMEGA com 4-6 sub-sprints (94a...94f), uma por domínio absorvido"
    - "CONTEXTO.md atualiza Visão de Futuro como plano concreto, não aspiração"
    - "Priorização declarada: quais domínios absorver primeiro (provável: saúde + documentos pessoais)"
    - "Princípios invioláveis declarados: inbox unificado continua único ponto de entrada; forbidden zones viram zonas_em_migracao_por_fase; financeiro permanece prioridade em qualidade"
```

---

# Sprint 94 -- Fusão total (Modelo B)

**Status:** BACKLOG
**Prioridade:** P3 estratégica (guia arquitetural de longo prazo; não-bloqueante no curto)
**Dependências:** Sprint 86 (coabitação estruturalmente validada), Sprint 90 (pessoa_detector como pré-req para absorção cross-domínio)
**Decisão do dono (2026-04-24):** Modelo B é o destino. "Virar uma central completa de controle de vida. Inbox único funciona para ambos."

## Decisão arquitetural

**ADR-21 formaliza:** Ouroboros é, em sua forma madura, a **Central de Controle de Vida** do casal. O que hoje é "Protocolo Ouroboros" e o que hoje é "Controle de Bordo" convergem num único sistema onde:

- **Inbox único** absorve qualquer arquivo da vida (financeiro, acadêmico, profissional, pessoal, saúde).
- **Extratores especializados** por domínio extraem dados estruturados.
- **Grafo de conhecimento** cruza informação entre domínios (transação ↔ documento ↔ fornecedor ↔ categoria ↔ pessoa ↔ prazo).
- **Dashboard consolidado** oferece visões por domínio + meta-visões cross-domínio.
- **Vault Obsidian** é o substrato visual + edição humana livre; Ouroboros é o motor de ingestão + indexação + análise.
- **ADR-18 (coabitação estrutural)** evolui: forbidden zones viram "zonas não-absorvidas ainda", migradas fase a fase.

## Plano em fases (Fase OMEGA)

**Sprint 94a -- Saúde** (prioridade alta; integra com IRPF)
- Absorve: receitas médicas (JÁ -- Sprint 47a), exames, planos, consultas.
- Extrator: expandir `src/extractors/receita_medica.py` para exames/laudos.
- Novo: regra YAML `exame_laboratorial`, `laudo_medico`, `plano_saude_mensalidade`.
- Grafo: node tipo `exame` com edge `prescrito_por` para médico.
- Dashboard: nova aba "Saúde" (timeline + custos + alertas de validade).

**Sprint 94b -- Documentos pessoais** (prioridade alta; fundação identitária)
- Absorve: RG, CNH, CPF (JÁ -- Sprint 87.4), título eleitoral, passaporte, certidão nascimento/casamento.
- Extrator: novo `src/extractors/documento_identidade.py`.
- Regras YAML: `rg`, `cnh`, `titulo_eleitoral`, `passaporte`.
- Grafo: node tipo `documento_identidade` com validade (data expiração → alertas).
- Dashboard: aba "Identidade" com cards expirando.

**Sprint 94c -- Vida profissional** (prioridade média; fortalece IRPF + histórico)
- Absorve: contratos CLT/PJ, holerites (JÁ), comprovantes de trabalho, registrato BCB, rescisão.
- Extrator: `src/extractors/contrato_trabalho.py`, `src/extractors/registrato_bcb.py`.
- Regras YAML novas.
- Grafo: node `vinculo_profissional` com edges para `holerite`, `pessoa`.

**Sprint 94d -- Vida acadêmica** (prioridade média; integra com Vitória NEES)
- Absorve: histórico escolar, diplomas, certificados cursos, grade disciplinas.
- Extrator: `src/extractors/documento_academico.py`.
- Grafo: `disciplina`, `certificado_curso`.

**Sprint 94e -- Meta: busca global cross-domínio**
- Expandir `src/dashboard/paginas/busca.py` para pesquisar em todos os domínios absorvidos.
- Ranking por relevância cross-tipo.

**Sprint 94f -- Obsidian mobile integration**
- Sincronização com celular via Obsidian Sync (pago) ou Syncthing (grátis).
- Inbox mobile: fotos de cupom/recibo direto do celular caem no vault.
- Notificações push para alertas (documento expirando, boleto vencendo).

## Princípios invioláveis (durante migração)

1. **Inbox único.** `./inbox/` + `~/Controle de Bordo/Inbox/` continuam sendo os únicos pontos de entrada. Sprint 70 (adapter) já suporta isso.
2. **Financeiro não regride.** Nenhuma sprint OMEGA pode quebrar testes/gauntlet do financeiro. Gate: `make smoke` + baseline pytest.
3. **Forbidden zones de ADR-18 migram explicitamente.** Cada domínio absorvido sai das forbidden zones e vira declarado em `tipos_absorvidos` no `inbox_routing.yaml`.
4. **Cada domínio tem extrator + regra YAML + testes próprios.** Mesmo rigor do financeiro.
5. **Vault permanece editável por humano.** Ouroboros sincroniza mas não sobrescreve edição manual (tag `#sincronizado-automaticamente` ou frontmatter `sincronizado: true`).
6. **Dashboard por cluster (Sprint 92).** Cada domínio novo vira cluster na sidebar ou aba de primeiro nível.

## Priorização sugerida

Ordem recomendada de execução:

1. **Primeiro fechar: financeiro + UX.** Sprints 89, 90, 91 (ou 92 direto), 93.
2. **94a (saúde)** -- maior retorno (integra IRPF, alerta validade).
3. **94b (documentos identidade)** -- baixo esforço, alto valor preventivo (CNH vencendo, etc.).
4. **94e (busca global cross-domínio)** -- destrava valor dos anteriores.
5. **94c (profissional)** + **94d (acadêmico)** -- conforme demanda.
6. **94f (mobile)** -- quando produto estiver maduro.

## Armadilhas

- **Scope creep mortal.** Absorver 4 domínios novos = 4× complexidade do financeiro atual. Sem priorização rigorosa, Ouroboros vira monstro.
- **Obsidian tem plugins que fazem parte disso.** Dataview, Templater, Calendar. Absorver o que ESSES plugins não fazem bem.
- **Privacidade.** CPFs, CNPJs, documentos médicos sensíveis. Reforçar `.gitignore` + considerar criptografia em `mappings/pessoas.yaml`.
- **Obsidian mobile sync custa ($10/mês) ou exige VPS próprio.** Decisão financeira.
- **Substituir Obsidian como editor? NÃO.** Ouroboros é motor de ingestão + grafo + dashboard; Obsidian permanece editor livre.

## Valor

Ao fim da Fase OMEGA (prazo: 12-18 meses), o casal tem **um sistema único para toda a vida digital**:
- IRPF automático com documentos médicos tagueados.
- Alertas de CNH/plano de saúde/vencimentos.
- Histórico profissional completo para comprovar tempo de trabalho.
- Grafo que mostra "onde o dinheiro vai" + "com quem" + "por quê" em uma única visão.
- Busca global que responde "mostre tudo sobre natação da Vitória" em < 1s.

---

*"Uma vida bem indexada é uma vida bem vivida." -- princípio de sistemas integrados*
