## 0. SPEC (machine-readable)

```yaml
sprint:
  id: INFRA-RENAME-HOLERITES
  title: "Rename holerites para nome legivel (atual eh hash truncado de 8 chars)"
  prioridade: P1
  estimativa: 2h
  origem: "feedback dono 2026-04-27 (image 20) -- 'sistema de rename ta ruim viu? olha o nome dos holerites'. Atual: HOLERITE|70E3A6BDE1D8 (hash truncado). Desejado: HOLERITE_<mes-ref>_<empresa>_<valor-liquido>.pdf"
  pre_requisito_de: []
  touches:
    - path: scripts/migrar_holerites_retroativo.py
      reason: "atualizar template de naming canonico do gerar_nome_canonico() ou equivalente"
    - path: src/intake/registry.py (ou onde holerite tem template)
      reason: "alinhar com migrar_holerites_retroativo.py"
    - path: scripts/renomear_holerites_v2.py
      reason: "NOVO -- script idempotente que detecta os 24 holerites em data/raw/casal/holerites/ (e similares), le metadata do grafo (mes_ref, empresa, valor_liquido), constroi nome legivel novo, renomeia atomicamente, atualiza grafo (caminho_canonico)"
    - path: tests/test_rename_holerites_v2.py
      reason: "NOVO -- 8 testes: template gera nome esperado, fallback quando metadata incompleto, idempotencia rodando 2x, mascarar PII no relatorio, dry-run nao escreve"
  forbidden:
    - "Apagar arquivo originais (data/raw/_originais/ preservados, ADR-18)"
    - "Quebrar idempotencia: 2a rodada apos --executar = 0 mudancas"
    - "Default destrutivo -- --dry-run eh default; --executar explicito"
    - "Renomear o arquivo SEM atualizar grafo (caminho_canonico no metadata fica stale)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_rename_holerites_v2.py -v"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Template novo: 'HOLERITE_<YYYY-MM>_<empresa-norm>_<liquido-int>.pdf' (ex: HOLERITE_2026-04_G4F_5000.pdf, HOLERITE_2026-03_INFOBASE_3500.pdf)"
    - "Empresa normalizada via slug: maiusculas + sem espacos + sem acentos (G4F, INFOBASE; nao 'G4F TECNOLOGIA' ou 'Infobase Servicos')"
    - "Quando metadata incompleto (sem empresa ou sem liquido), fallback para 'HOLERITE_<mes>_<sha8>.pdf' mascarando origem"
    - "Script idempotente: 2a rodada apos --executar nao muda nada (relatorio = '0 holerites renomeados')"
    - "Atualiza node.metadata['caminho_canonico'] e edge.peso quando aplicavel apos rename"
    - "Relatorio em data/output/rename_holerites_v2_<ts>.{csv,md} com colunas: item_id, nome_antigo, nome_novo, mudou (bool), motivo (template/fallback)"
    - "PII mascarada em relatorio: nome de empresa eh OK (publico), valor eh mascarado (R$ XXX,XX)"
    - "Pelo menos 8 testes regressivos cobrindo template, fallback, idempotencia, atualizacao do grafo, dry-run, PII"
  proof_of_work_esperado: |
    # Antes
    ls data/raw/casal/holerites/ | head -3
    # = HOLERITE|70E3A6BDE1D8.pdf, HOLERITE|D959C9C010F7.pdf, ...

    # Dry-run (default)
    .venv/bin/python scripts/renomear_holerites_v2.py
    cat data/output/rename_holerites_v2_*.md | head -30
    # = 24 holerites listados, mostrando nome_antigo -> nome_novo proposto

    # Executar
    .venv/bin/python scripts/renomear_holerites_v2.py --executar
    ls data/raw/casal/holerites/ | head -3
    # = HOLERITE_2026-04_G4F_5000.pdf, HOLERITE_2026-03_INFOBASE_3500.pdf, ...

    # Idempotencia
    .venv/bin/python scripts/renomear_holerites_v2.py --executar
    grep "0 holerites renomeados" data/output/rename_holerites_v2_*.md
    # = match
```

---

# Sprint INFRA-RENAME-HOLERITES -- Rename holerites legivel

**Status:** CONCLUÍDA em DRY-RUN (commit `9618ec6`, 2026-04-27 — 22 testes novos, 24/24 holerites cobertos, --executar aguarda autorização explícita do dono)

A Sprint 98 (concluida 2026-04-27) renomeou 24 holerites usando template `HOLERITE|<sha8>` (hash truncado SHA-256[:8]). O dono detectou que os nomes ficam ilegiveis: `HOLERITE|70E3A6BDE1D8` nao ajuda a navegar o vault.

Sprint troca template para `HOLERITE_<YYYY-MM>_<empresa>_<liquido>.pdf` lendo metadata ja extraido pelo grafo (mes_ref, empresa, valor_liquido do contracheque). Idempotente, dry-run default, atualiza grafo.

Sprint depende da Sprint 98 (engine de rename) ja entregue. Apenas estende com template novo.

---

*"Nome de arquivo bom e o que humano consegue ler em meio segundo." -- principio do nome legivel*
