---
id: INFRA-LINKING-PROPOSTAS-GC
titulo: Garbage collection de propostas de linking obsoletas em docs/propostas/linking/
status: backlog
concluida_em: null
prioridade: P2
data_criacao: 2026-05-13
fase: SANEAMENTO
depende_de: []
esforco_estimado_horas: 2
origem: auditoria pós-./run.sh --tudo em 2026-05-13 -- 87 propostas no diretório mas pipeline atual gerou apenas 21. 66 são resíduos de execuções anteriores que não foram limpos. Ofusca leitura de quais conflitos são atuais.
---

# Sprint INFRA-LINKING-PROPOSTAS-GC

## Contexto

`docs/propostas/linking/` acumula propostas de cada execução do pipeline sem política de limpeza. Hoje (2026-05-13 00:30), pipeline gerou 21 conflitos novos, mas o diretório tem 87 arquivos — 66 são de execuções anteriores que já foram superadas por:

1. Resolvidos automaticamente (transação foi linkada em run posterior).
2. Documento mudou de nome_canonico (rename estrutural).
3. Transação foi deletada/refundida (dedup C6 OFX+XLSX, NFCe dedup OCR, etc.).
4. São de IDs pix antigos (07182...) que mudaram entre versões do bridge.

Sem GC, supervisor abre o diretório e não sabe quais conflitos são **agora** vs. **antes**.

## Objetivo

1. Política: ao final de cada `linking_documento_transacao`, marcar timestamp `gerado_em` em cada proposta nova.
2. Antes de regerar, mover propostas com mesmo `id` (mesmo número da transação OU mesmo nome_canonico do documento) para `docs/propostas/linking/_obsoletas/`.
3. Script `scripts/gc_propostas_linking.py` para arquivar manualmente o estado atual (semente da automação).

## Decisão pendente

Mover obsoletas vs. deletar? Recomendação: arquivar em `_obsoletas/` com prefixo de data para auditoria humana posterior. Padrão: dado já vivo nunca se descarta.

## Proof-of-work esperado

```bash
# Antes: 87 arquivos
ls docs/propostas/linking/ | wc -l  # 87

# Após script
.venv/bin/python scripts/gc_propostas_linking.py --auditar-atual
ls docs/propostas/linking/ | wc -l  # ~21 (atual)
ls docs/propostas/linking/_obsoletas/ | wc -l  # ~66 (arquivado)
```

---

*"Acumular sem limpar é atalho para não ver o que já viu." -- princípio do arquivista que arruma*
