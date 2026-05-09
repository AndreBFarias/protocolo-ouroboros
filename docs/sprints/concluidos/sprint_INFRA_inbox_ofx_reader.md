---
id: INFRA-INBOX-OFX-READER
titulo: Completar leitor OFX/PDF da inbox (data/raw/inbox/) populando fila e pipeline
status: concluída
concluida_em: 2026-05-08
commit: 62f71d0
prioridade: alta
data_criacao: 2026-05-08
fase: CONCLUSAO_REAL
depende_de: []
esforco_estimado_horas: 6
origem: docs/auditorias/INVENTARIO_REAL_VS_MOCKUP_2026-05-08.md (inbox em parcial)
mockup: novo-mockup/mockups/16-inbox.html
---

# Sprint INFRA-INBOX-OFX-READER — leitor de fila inbox

## Contexto

Página `inbox` mostra 5 KPIs (Aguardando, Extraído, Falhou, Pulado, Total) e dropzone, mas a fila aparece vazia mesmo quando há arquivos em `data/raw/inbox/`. O leitor `src/intake/inbox_reader.py` está parcial — não detecta novos arquivos via watch nem agrupa por sha256.

## Objetivo

Implementar leitura completa em `src/intake/inbox_reader.py`:

1. Scan recursivo de `data/raw/inbox/` por extensões PDF/CSV/XLSX/OFX/JPG/PNG/HTML/TXT/JSON.
2. Calcular sha256 + tamanho + ts_descoberto + tipo inferido.
3. Persistir em `data/output/inbox_fila.json` com schema:
   ```json
   {"itens": [{"sha256": "...", "filename": "...", "tipo_inferido": "extrato_cc|fatura_cartao|...", "tamanho_kb": 182, "status": "aguardando|extraido|falhou|pulado", "ts_descoberto": "ISO", "ts_processado": "ISO|null", "extractor_versao": "...|null"}]}
   ```
4. Função `processar_fila()` que invoca extrator apropriado + atualiza status.
5. Agrupar duplicatas por sha8 (mostrar contador de duplicados).

## Validação ANTES (grep)

```bash
ls -la src/intake/
grep -n "inbox_reader\|processar_fila\|inbox_fila" src/ -r | head -10
ls data/raw/inbox/ 2>&1 | head -5
```

## Não-objetivos

- NÃO implementar watch em tempo real (cron/webhook fica para sprint futura).
- NÃO mexer na UI da página inbox (skeleton já está pronto).

## Proof-of-work

```bash
python -c "from src.intake.inbox_reader import processar_fila; processar_fila()"
test -f data/output/inbox_fila.json
make lint && make smoke
.venv/bin/pytest tests/ -k inbox -q
```

Validação visual: cluster=Inbox&tab=Inbox mostra fila com >=1 arquivo (em ambiente de teste, criar fixture `tests/fixtures/inbox_amostra/` com 5 arquivos).

## Critério de aceitação

1. `inbox_reader.processar_fila()` retorna lista de itens populada.
2. JSON `inbox_fila.json` segue schema v1.
3. Página renderiza linhas reais quando há arquivos.
4. Detecção de duplicata por sha8 funcional.
5. Lint + smoke + pytest baseline.

## Referência

- Inventário: `docs/auditorias/INVENTARIO_REAL_VS_MOCKUP_2026-05-08.md`.
- Mockup: `16-inbox.html`.
- BLO-J (parser OFX) em `~/.claude/plans/pure-swinging-mitten.md`.

*"Inbox sem leitor é caixa de entrada vazia por design." — princípio INFRA-INBOX-OFX-READER*
