---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-15
  title: "Inbox real: dropzone + fila + drawer sidecar + skill-instr"
  prioridade: P0
  estimativa: 4h
  onda: 5
  origem: "mockup 16-inbox.html + _inbox-data.js + _inbox-render.js"
  depende_de: [UX-RD-03]
  touches:
    - path: src/dashboard/paginas/inbox.py
      reason: "NOVO -- dropzone (st.file_uploader com drag&drop) + fila (lista lendo data/inbox/ + data/inbox/.extracted/*.json) + drawer sidecar com extração + skill-instr bloco mono + barra status (aguardando/extraído/falhou/duplicado)"
    - path: src/intake/inbox_reader.py
      reason: "NOVO -- listar_inbox() retorna [{sha8, filename, tipo_detectado, estado, ts, sidecar}], lê data/inbox/ + .extracted/, calcula sha8, normaliza"
    - path: tests/test_inbox_real.py
      reason: "NOVO -- 10 testes: dropzone aceita 6 formatos (PDF/CSV/XLSX/OFX/JPG/PNG), fila ordena por ts desc, drawer abre com sidecar, skill-instr texto correto, barra status soma == total"
  forbidden:
    - "Tocar src/inbox_processor.py (lógica de move/classify preservada)"
    - "Tocar src/intake/classifier.py"
    - "Subir arquivo via Streamlit que NÃO é gravado em data/inbox/ -- arquivo em st.file_uploader é temporário, salvar em data/inbox/<filename> com sha8"
  hipotese:
    - "data/inbox/.extracted/ contém JSONs com classificação. Verificar estrutura via ls + cat de 1 arquivo."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_inbox_real.py -v"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Página Inbox no cluster Inbox (cluster próprio, não dentro de Documentos)"
    - "Dropzone aceita drag&drop OU click; 6 formatos: PDF/CSV/XLSX/OFX/JPG/PNG; arquivo salvo em data/inbox/<filename>"
    - "Fila lista arquivos de data/inbox/ com thumb (32px) + filename + tipo_detectado pill + estado pill (cor D7) + ts"
    - "Click linha abre drawer com JSON sidecar formatado"
    - "Animação .row-novo (fade purple 0.8s) em arquivos novos"
    - "Skill-instr block com texto 'Para arquivos com tipo=None, abra Claude Code CLI: `/propor-extrator <tipo>`' (literal mono)"
    - "Barra status no topo: 4 tiles (Aguardando | Extraído | Falhou | Duplicado) com count e cor D7"
    - "Atalho 'g i' (de UX-RD-03) chega aqui"
    - "pytest baseline mantida"
  proof_of_work_esperado: |
    # Hipótese: estrutura sidecar
    ls data/inbox/.extracted/ 2>/dev/null | head -3
    cat data/inbox/.extracted/*.json 2>/dev/null | head -1 | jq .

    # AC: dashboard
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # ?cluster=Inbox -- ver dropzone + fila + barra status
    # Arrastar 1 PDF de teste -> aparece na fila com .row-novo animation
    # Click linha -> drawer abre com sidecar
    ls -la data/inbox/  # confirmar arquivo gravado
    # screenshot
```

---

# Sprint UX-RD-15 — Inbox real

**Status:** BACKLOG

Primeiro vez que o dashboard tem um cluster **só** dele (Inbox). Antes, inbox
era pasta + script CLI (`./run.sh --inbox`); agora vira UI funcional.

**Validação visual + funcional do dono:**
1. Arrastar 3 arquivos de tipos diferentes (PDF NFCe, CSV Nubank, JPG cupom).
2. Confirmar que os 3 aparecem na fila com tipos detectados corretos.
3. Confirmar barra status soma 3.
4. Click em cada um -> drawer com JSON.

---

*"O caos organizado é o primeiro passo da ordem." — princípio do GTD*
