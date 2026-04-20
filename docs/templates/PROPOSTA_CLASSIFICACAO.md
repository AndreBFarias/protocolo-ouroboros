---
id: <yyyy-mm-dd>_<slug>
tipo: classificacao  # noqa: accent
data: <yyyy-mm-dd>
status: aberta
autor_proposta: claude-code-opus
sprint_contexto: none
---

# Proposta de classificação: <nome original do arquivo em _classificar/>

## Arquivo

- **Caminho atual:** `data/raw/_classificar/_CLASSIFICAR_<hash>.pdf`
- **Nome original na inbox:** `<nome humano>`
- **MIME detectado:** `application/pdf`
- **Tamanho:** `N bytes`
- **Motivo da não-classificação:** (ex.: nenhuma regex de `mappings/tipos_documento.yaml`
  casou; 0 chars extraíveis via pdfplumber; arquivo encriptado sem senha conhecida.)

## Tipo sugerido

Proposta de classificação: **<tipo>** (escolher um de `mappings/tipos_documento.yaml`
ou sugerir tipo novo).

- **Evidência:** (texto/regex/visual que sugere este tipo)
- **Destino:** `data/raw/<pessoa>/<pasta>/`
- **Renomeação:** `<TIPO>_YYYY-MM-DD_<sha8>.pdf`

## Regra nova (opcional)

Se o tipo é novo ou a regra existente deveria ter casado mas não casou,
incluir diff para `mappings/tipos_documento.yaml`:

```diff
- id: ...
```

## Decisão humana

**Aprovada em:** (preencher ao aprovar)
**Ação realizada ao aprovar:**
- [ ] Arquivo movido para `<destino>` com nome canônico
- [ ] Regra em `mappings/tipos_documento.yaml` adicionada (se aplicável)
- [ ] `./run.sh --tudo` rodado para processar o arquivo

**Rejeitada em:** (preencher ao rejeitar)
**Motivo:** (opções: arquivo irrelevante, tipo já existe mas falha de regra, duplicata de outro arquivo)

---

*"A classificação é o primeiro ato de leitura." -- princípio de arquivista*
