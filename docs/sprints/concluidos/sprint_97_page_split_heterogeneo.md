---
concluida_em: 2026-04-26
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 97
  title: "Page-split por classificação heterogenea: PDF com tipos diferentes por pagina"
  prioridade: P0
  estimativa: 3-4h
  origem: "auditoria 2026-04-26 -- 3 PDFs em _classificar/ são NFC-e + cupom seguro misturados em 4 paginas"
  touches:
    - path: src/intake/heterogeneidade.py
      reason: "ampliar e_heterogeneo para detectar pages com tipos diferentes apos classifier"
    - path: src/intake/extractors_envelope.py
      reason: "expandir_pdf_multipage produz N PaginaPdf, cada uma classifica separado"
    - path: src/intake/orchestrator.py
      reason: "se PDF heterogeneo, rotear cada pagina para destino canonico distinto"
    - path: tests/test_pdf_heterogeneo_multitype.py
      reason: "regressao: PDF NFC-e + cupom-seguro -> 2 destinos diferentes"
  forbidden:
    - "Quebrar contrato de envelope (originais/<sha8>.pdf preservado integralmente)"
    - "Roteador classifier mover paginas individuais sem preservar PDF original em originais/"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_pdf_heterogeneo_multitype.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "_CLASSIFICAR_6c1cc203.pdf (4 paginas: NFC-e + 2 seguros + NFC-e) e processado e produz: 2 nfce_modelo_65 + 2 cupom_garantia_estendida"
    - "PDF homogeneo (todas paginas mesmo tipo) continua funcionando como hoje (regression)"
    - "Originais preservados: data/raw/originais/<sha8>.pdf intacto"
    - "Pelo menos 4 testes: PDF heterogeneo NFC-e+seguro, PDF homogeneo NFC-e, PDF heterogeneo NFC-e+boleto, PDF apenas 1 pagina"
  proof_of_work_esperado: |
    # Antes
    ls data/raw/_classificar/
    # = 3 PDFs idênticos (mesmo SHA, classifier não soube fatiar)
    
    sqlite3 data/output/grafo.sqlite "
      SELECT COUNT(*) FROM node WHERE tipo='documento' 
        AND json_extract(metadata, '\$.arquivo_origem') LIKE '%6c1cc203%';"
    # = 4 (apolices + nfce ja extraidos via originais/, mas não a partir do _classificar/)
    
    # Depois (apos rodar classifier melhorado em runtime)
    ./run.sh --inbox
    ls data/raw/_classificar/
    # = vazio (3 PDFs heterogeneos foram fatiados e roteados)
    
    ls data/raw/casal/nfs_fiscais/nfce/ data/raw/casal/garantias_estendidas/
    # Cada pagina foi roteada para destino correto
```

---

# Sprint 97 -- Page-split por classificação heterogenea

**Status:** BACKLOG (P0, criada 2026-04-26)
**Origem:** auditoria 2026-04-26 -- bucket `_classificar/` tem 3 PDFs identicos (mesmo SHA `6c1cc203`) que são na verdade fotografia composita de envelope com 4 paginas: NFC-e Americanas + 2 cupons-bilhete de seguro garantia + outra NFC-e da mesma compra.

## Motivacao

Sprint 41d implementou `e_heterogeneo` mas o predicado opera em **caracteristicas estruturais** (tamanho variavel, paginas com tabela vs prosa). Não opera em **classificação textual diferente**. Resultado: PDF com NFC-e na pag 1 + seguro na pag 2 + seguro na pag 3 + NFC-e na pag 4 cai todo no `_classificar/` porque `detectar_tipo` so olha o documento inteiro.

Para fechar o circuito do "controle de bordo" (cada NF item-a-item, cada cupom de seguro vinculado), precisamos:
1. Fatiar PDFs multi-pagina via `expandir_pdf_multipage`.
2. Classificar **cada PaginaPdf** separadamente.
3. Se pelo menos 2 paginas casaram tipos diferentes -> rotear cada para destino canonico distinto.
4. PDF original preservado em `originais/<sha8>.pdf` (auditoria).

## Escopo

### Fase 1 -- Detectar heterogeneidade por classificação (1h)

`src/intake/heterogeneidade.py::e_heterogeneo` ganha modo `por_classificacao`:

```python
def e_heterogeneo_por_classificacao(paginas: list[PaginaPdf]) -> bool:
    """Retorna True se ao menos 2 paginas casam tipos diferentes."""
    tipos = []
    for p in paginas:
        decisao = detectar_tipo(p.path_temp, mime='application/pdf', preview=p.texto_nativo)
        if decisao.tipo:
            tipos.append(decisao.tipo)
    tipos_unicos = set(tipos) - {None}
    return len(tipos_unicos) >= 2
```

### Fase 2 -- Roteamento heterogeneo (1.5h)

`orchestrator.py::processar_arquivo_inbox`:

```python
if mime == 'application/pdf':
    paginas = expandir_pdf_multipage(caminho)
    if e_heterogeneo_por_classificacao(paginas):
        # Rotear cada pagina como artefato distinto
        for pagina in paginas:
            decisao = detectar_tipo(pagina.path_temp, ...)
            artefatos.append(rotear_artefato(pagina.path_temp, decisao, ...))
    else:
        # Comportamento atual: classificar PDF inteiro
        ...
```

### Fase 3 -- Preservacao de originais (30 min)

Confirmar que `expandir_pdf_multipage` ja preserva o PDF original em `data/raw/originais/<sha8>.pdf`. Se não, adicionar.

### Fase 4 -- Testes regressivos (1h)

4 fixtures sinteticas:
1. PDF NFC-e + Cupom Seguro -> 2 destinos diferentes.
2. PDF homogeneo NFC-e (3 paginas) -> 1 destino (regression).
3. PDF NFC-e + Boleto -> 2 destinos.
4. PDF 1 pagina apenas -> path original (sem fatiar).

## Armadilhas

- **PDF generico do Adobe Acrobat junta paginas avulsas em arquivo único**. Padrao real (cliente coloca cupom + comprovantes no mesmo PDF). Eh o caso comum, não excecao.
- **Performance**: classificar N paginas dobra o trabalho. Cache OCR ja existente (Sprint 41) ajuda.
- **Idempotencia**: re-rodar com `_CLASSIFICAR_6c1cc203` ja existente não deve gerar dup. Apolices 7379/7382 ja foram extraidas de `originais/6c1cc2035c99d68f.pdf` -- garantir que a sprint não crie duplicatas.

## Dependencias

- Sprint 90a (holerite no inbox) -- não bloqueia, mas roda antes melhora dataset.
- Sprint 96 (classifier robusto cupons curtos) -- não bloqueia, mas roda junto melhora confianca.

## Pos-fix

Limpar `data/raw/_classificar/_CLASSIFICAR_6c1cc203*.pdf` (3 cópias, ja processadas via `originais/`).

---

*"Um PDF com 4 paginas pode ter 4 historias diferentes. Trate cada uma." -- principio da heterogeneidade real*
