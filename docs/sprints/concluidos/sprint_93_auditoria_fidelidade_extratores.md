---
concluida_em: 2026-04-23
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 93
  title: "Auditoria de fidelidade dos extratores -- compara outputs com arquivos originais"
  touches:
    - path: scripts/auditar_extratores.py
      reason: "novo: para cada banco, abre N arquivos originais representativos, soma manualmente, compara com XLSX gerado"
    - path: docs/auditoria_extratores_YYYY-MM-DD.md
      reason: "relatório: para cada banco, (tot_original, tot_extraido, delta, linhas_ausentes, linhas_fantasma)"
    - path: tests/test_auditoria_fidelidade.py
      reason: "teste lento (@pytest.mark.slow) que roda 1 arquivo por banco"
  forbidden:
    - "Alterar extratores nesta sprint -- primeiro audita, depois fix (sprints filhas 93a, 93b, ...)"
    - "Confiar em fixtures sintéticas -- cada asserção usa arquivo REAL"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_auditoria_fidelidade.py -v -m slow"
  acceptance_criteria:
    - "scripts/auditar_extratores.py aceita --banco {itau|santander|c6_cc|c6_cartao|nubank_cartao|nubank_cc|nubank_pf_cc|nubank_pj_cc|nubank_pj_cartao} --mes YYYY-MM"
    - "Para cada banco, script abre arquivo bruto, extrai via extrator, compara com linhas do XLSX pelo mesmo (banco, mes_ref)"
    - "Relatório mostra: total no bruto, total no XLSX, delta absoluto, linhas presentes em um mas não em outro"
    - "Pelo menos 5 bancos auditados com delta = 0 (fidelidade 100%)"
    - "Bancos com delta != 0 geram sprint-filha 93x com diagnóstico"
    - "Tag pytest @pytest.mark.slow para não rodar no gauntlet rápido"
```

---

# Sprint 93 -- Auditoria de fidelidade dos extratores

**Status:** BACKLOG
**Prioridade:** P1 (crítica; sem confiança nos extratores, todo o resto é ruído)
**Dependências:** Sprint 88 (regras YAML calibradas), Sprint 90 (pessoa_detector robusto)
**Origem:** usuário questionou se extratores estão realmente funcionando em volume real (2026-04-24)

## Problema

Temos 1139 testes verdes, smoke 8/8, pipeline exit 0. Mas:
- Testes unitários usam fixtures sintéticas (não arquivos reais).
- Smoke aritmético valida 8 contratos globais (ex.: receita <= salário × limiar), não fidelidade por linha.
- Pipeline exit 0 só significa que não levantou exceção; pode silenciosamente perder linhas.

Sprint 88 provou isso em outro contexto: 87.4 validada com fixtures sintéticas falhou em volume real (26/27 arquivos skipped). O mesmo risco existe nos extratores bancários.

## Método

Para cada banco (10 extratores ativos), escolher **1 arquivo representativo**:
1. Abrir o arquivo bruto manualmente (pdfplumber / openpyxl / pandas).
2. Extrair **todas** as transações com os dados disponíveis (data, valor, descrição).
3. Somar o total absoluto.
4. Ler o XLSX `data/output/ouroboros_2026.xlsx` e filtrar `banco_origem=<banco> AND mes_ref=<mes>`.
5. Somar o total absoluto das linhas correspondentes.
6. **Delta esperado:** 0.00 (com tolerância de R$ 0,02 por erros de arredondamento).
7. Se delta != 0, listar linhas presentes em um e não em outro.

## Escopo de arquivos (candidatos)

- **Itaú CC:** uma fatura `itau_*.pdf` de 2025 com >= 10 transações
- **Santander Cartão:** uma fatura `fatura-*.pdf` de 2025
- **C6 CC:** um extrato `c6_*.xls` protegido (testa msoffcrypto)
- **C6 Cartão:** fatura C6
- **Nubank Cartão:** CSV Nubank `date,title,amount`
- **Nubank CC (André):** CSV Nubank `Data,Valor,Identificador,Descrição`
- **Nubank PF (Vitória):** CSV conta corrente PF
- **Nubank PJ CC:** conta corrente PJ
- **Nubank PJ Cartão:** cartão PJ
- **Contracheque G4F:** 1 holerite PDF nativo
- **Contracheque Infobase:** 1 holerite PDF escaneado (testa OCR fallback)

11 arquivos auditados manualmente.

## Protocolo de execução

```python
# scripts/auditar_extratores.py
import argparse
import pandas as pd
from pathlib import Path

def auditar_banco(banco: str, mes_ref: str, arquivo_raw: Path) -> dict:
    # 1. Extrair via pipeline
    extrator = _importar_extrator(banco)
    transacoes_extraidas = extrator().extrair(arquivo_raw)
    total_extraido = sum(abs(t["valor"]) for t in transacoes_extraidas)

    # 2. Ler XLSX oficial
    df = pd.read_excel("data/output/ouroboros_2026.xlsx", sheet_name="extrato")
    df_filtro = df[(df["banco_origem"] == banco) & (df["mes_ref"] == mes_ref)]
    total_xlsx = df_filtro["valor"].abs().sum()

    # 3. Comparar
    delta = abs(total_extraido - total_xlsx)
    return {
        "banco": banco,
        "mes_ref": mes_ref,
        "arquivo": arquivo_raw.name,
        "total_extraido": total_extraido,
        "total_xlsx": total_xlsx,
        "delta": delta,
        "n_transacoes_extrator": len(transacoes_extraidas),
        "n_transacoes_xlsx": len(df_filtro),
    }

# Uso:
# python scripts/auditar_extratores.py --banco itau --mes 2025-03 --arquivo data/raw/andre/itau_cc/fatura_202503.pdf
```

## Relatório

`docs/auditoria_extratores_2026-04-XX.md`:

```markdown
# Auditoria de fidelidade -- 2026-04-XX

## Resumo

| Banco | Mês | Arquivo | Tot extrator | Tot XLSX | Delta | N_ex | N_xlsx | Veredito |
|---|---|---|---|---|---|---|---|---|
| itau_cc | 2025-03 | fatura_202503.pdf | 4523,91 | 4523,91 | 0,00 | 47 | 47 | OK |
| santander_cartao | 2025-04 | fatura_...pdf | 3201,77 | 3200,50 | 1,27 | 33 | 33 | **DIVERGENCIA** |
| ...

## Divergências detectadas

### santander_cartao 2025-04 -- delta R$ 1,27
- Linha presente no bruto, ausente no XLSX: `2025-04-15 IOF Internacional R$ 1,27`
- Provável causa: extrator não captura IOF. Filtra por padrão X?
- Sprint-filha: 93a

## Recomendações

- [ ] Sprint 93a (santander IOF)
- [ ] ...
```

## Proof-of-work

```bash
# Auditar todos os 11 candidatos
for banco in itau_cc santander_cartao c6_cc c6_cartao nubank_cartao nubank_cc nubank_pf_cc nubank_pj_cc nubank_pj_cartao; do
    python scripts/auditar_extratores.py --banco "$banco" --mes 2025-03 --arquivo data/raw/...
done

# Relatorio consolidado
python scripts/auditar_extratores.py --consolidar > docs/auditoria_extratores_$(date +%Y-%m-%d).md

# Gauntlet
make lint && .venv/bin/pytest tests/ -q
```

## Armadilhas

- Nem todo arquivo tem "total oficial" declarado no próprio (ex.: CSV Nubank não tem). Comparar soma de linhas extraídas vs soma linhas XLSX após filtrar banco+mes.
- Transferências internas podem aparecer em dois bancos; não confundir como duplicata.
- Contracheque tem componente líquido + 13º + INSS + IRRF; auditoria precisa comparar linha-a-linha, não só total.
- Arquivo bruto pode ter transações canceladas/estornadas; deduplicator do pipeline remove, bruto original mostra.
- OCR do Infobase tem recall ~67% em energia (Armadilha #10). Auditoria de OCR precisa de tolerância explícita.

## Valor

Após Sprint 93, temos confiança EMPÍRICA (não teórica) de que os extratores estão fiéis. Sem isso, todo o dashboard é potencialmente "lindo e errado".

---

*"Teste automatizado prova que o código não quebra; auditoria prova que o código faz o que deveria." -- princípio de fidelidade*
