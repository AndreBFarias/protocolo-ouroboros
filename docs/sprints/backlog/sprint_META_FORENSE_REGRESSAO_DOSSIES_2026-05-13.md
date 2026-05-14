---
id: META-FORENSE-REGRESSAO-DOSSIES-2026-05-13
titulo: Descobrir o que zera dossiês entre sessões e impedir reincidência
status: pendente
data_criacao: 2026-05-13
prioridade: P0
fase: SANEAMENTO
epico: 8
depende_de: []
origem: sessão 2026-05-13 detectou que 4 dossiês graduados ontem (cupom, holerite, das, nfce) estavam PENDENTE com historico=[] hoje. Sessão restaurou os 4 + adicionou pix e boleto (6 GRADUADOS). Se a causa não for descoberta, próxima sessão pode perder de novo.
---

# Sprint META-FORENSE-REGRESSAO-DOSSIES-2026-05-13

## Hipóteses sobre o agente da regressão

H1 -- **Hook session-start-projeto.py** com lógica de reset. Hipotese baixa: já li o hook, ele só monta texto. Mas pode haver outro hook downstream.

H2 -- **Sprint META anterior** (qualquer das `META-PROMPT-NOVA-SESSAO`, `META-HOOK-SESSION-START-PROJETO`, etc) executou cleanup em `data/output/dossies/` como side effect.

H3 -- **`./run.sh` ou subcomando** regenera dossiê esqueleto quando snapshot detecta inconsistência. `cmd_snapshot` em `dossie_tipo.py` é candidato a investigar.

H4 -- **Ação manual** do dono em sessão anterior (`rm -rf data/output/dossies/*/estado.json` ou similar para reset de teste).

H5 -- **Comando `--abrir` em massa** rodado por script ou por terminal: como `_garantir_estrutura_dossie` escreve estado.json novo se não existir, isso explica `historico: []` mas não explica perda do conteúdo prévio. A menos que `estado.json` tenha sido deletado antes.

## Validação ANTES

```bash
# Quem tocou os 4 dossiês entre 2026-05-12 e 2026-05-13 17:42 BRT
stat -c "%y %n" data/output/dossies/*/estado.json | sort

# Procurar qualquer rm -rf em scripts e hooks
grep -RnE "rm -rf.*dossies|rm.*estado\.json|shutil\.rmtree.*dossies" .claude/ scripts/ src/ 2>/dev/null

# Procurar qualquer reset/limpeza/zerar nos scripts do projeto
grep -RnE "(zerar|limpar|reset|clear).*dossie" .claude/ scripts/ src/ docs/ 2>/dev/null

# `cmd_snapshot` regenera dossiês?
grep -nE "_gravar_estado|mkdir|write_text" scripts/dossie_tipo.py | head -20

# Git log dos commits do dia que mexem em data/output/
git log --since="2026-05-12 00:00" --until="2026-05-13 18:00" --name-only --format='%h %ai %s'
```

## Entregável

1. **Forense escrita** (`docs/auditorias/2026-05-13_regressao_dossies.md`): cronologia, evidências, conclusão sobre H1-H5.
2. **Guarda preventiva** -- 1 das 3 medidas (mutuamente exclusivas, escolher a mais barata):
   - (a) Hook `PreToolUse` que bloqueia `rm` / `shutil.rmtree` em `data/output/dossies/`.
   - (b) Backup automático de `data/output/dossies/` antes de qualquer rodada de pipeline ou sprint META (snapshot tar.gz em `data/output/_backups/dossies_<ts>.tar.gz`, retenção 7 dias).
   - (c) Adicionar `estado.json` ao git tracking (sem conteúdo PII -- só status/contadores) -- vira append-only, histórico imune a wipe local.
3. **Teste de regressão** automatizado: simula reset, roda smoke, garante que graduação anterior persiste.

## Acceptance

- Forense identifica causa-raiz (ou prova negativa exaustiva sobre H1-H5).
- Medida preventiva implementada.
- Pytest passa.

## Não-objetivos

- Não restaurar graduações que já foram restauradas nesta sessão.
- Não migrar `data/output/` para fora do gitignore amplamente -- só estado.json se for o caminho.

## Proof-of-work runtime-real

```bash
# Após implementar guarda (b):
ls data/output/_backups/dossies_*.tar.gz | tail -3   # mostra 3 últimos backups
.venv/bin/python scripts/restore_dossies.py --listar # CLI complementar
.venv/bin/python scripts/restore_dossies.py --ts 2026-05-13_17h42 --dry-run
```

## Padrões aplicáveis

- (k) Hipótese não é dogma -- validar com grep antes de implementar fix.
- (n) Defesa em camadas -- 1 das 3 guardas é suficiente, escolher a mais robusta.
- (gg) Cache sintético é placeholder honesto -- guarda deve preservar conteúdo real, não recriar esqueleto.

---

*"Bug que apaga trabalho silenciosamente eh o pior dos bugs; bug que ressuscita silenciosamente eh o segundo pior." -- princípio do guardião visível*
