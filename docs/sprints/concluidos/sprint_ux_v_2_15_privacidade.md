---
id: UX-V-2.15
titulo: Privacidade granular A↔B com 4 níveis × bidirecional × 6 campos (24 radios)
status: concluída
prioridade: altissima
data_criacao: 2026-05-07
concluida_em: 2026-05-07
commit: 7e6b113
fase: PARIDADE_VISUAL
depende_de: [UX-V-02, UX-V-03]
co_executavel_com: [UX-V-2.9, UX-V-2.11, UX-V-2.12, UX-V-2.13]
esforco_estimado_horas: 10
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (página 27)
mockup: novo-mockup/mockups/27-privacidade.html
decisao_dono_2026_05_07: Feature granular completa (4 níveis × bidirecional)
adr_potencial: ADR-23 Privacidade Granular A↔B (a criar se necessário)
---

# Sprint UX-V-2.15 -- Privacidade granular feature nova

## Contexto

Auditoria: dashboard tem 6 toggles binários simples. Mockup tem privacidade granular **4 níveis** (Oculto/Agregado/Resumo/Total) **bidirecional** (A→B e B→A separados) por **6 campos** (humor/diário/eventos/medidas/treinos/ciclo) + cards laterais (vault id, último sync, features opcionais) + Audit log.

Decisão dono 2026-05-07: **Feature granular completa**. Requer schema TOML novo (`permissoes.toml`) + ADR potencial.

## Página afetada

`src/dashboard/paginas/be_privacidade.py` apenas.

## Objetivo

1. Schema canônico em `<vault>/.ouroboros/permissoes.toml`:
   ```toml
   [a_to_b]
   humor.base = "resumo"
   humor.energia_ansiedade_foco = "agregado"
   diario.entradas_para_b = "total"
   diario.entradas_privadas = "oculto"
   eventos.lugar = "total"
   medidas.peso = "agregado"
   ciclo = "agregado"
   
   [b_to_a]
   # mesmo shape
   ```
2. Renderizar 24 radio buttons (6 campos × 4 níveis) por direção, com tabs (A→B / B→A).
3. Cards laterais: vault id + última sync + features opcionais (Notificar / Modo férias / Recap conjunto).
4. Audit log button no topbar.
5. Botão Salvar persiste no TOML.

## Validação ANTES

```bash
wc -l src/dashboard/paginas/be_privacidade.py
ls .ouroboros/permissoes.toml 2>/dev/null
grep -n "permissoes\|toggle" src/dashboard/paginas/be_privacidade.py | head -5
```

## Spec de implementação

```python
NIVEIS = ["oculto", "agregado", "resumo", "total"]
NIVEIS_LABEL = {"oculto": "OCULTO", "agregado": "AGREGADO", "resumo": "RESUMO", "total": "TOTAL"}
CAMPOS = [
    ("humor.base", "humor base", "humor"),
    ("humor.extras", "energia / ansiedade / foco", "humor"),
    ("diario.entradas_para_b", "entradas marcadas como 'para B'", "DIÁRIO EMOCIONAL"),
    ("diario.privadas", "entradas privadas", "DIÁRIO EMOCIONAL"),
    ("eventos.lugar", "lugar do evento", "EVENTOS"),
    ("eventos.detalhes", "detalhes (foto, descrição)", "EVENTOS"),
    ("medidas.peso", "peso", "MEDIDAS"),
    ("treinos.tipo", "tipo de treino", "TREINOS"),
    ("ciclo", "ciclo menstrual", "CICLO MENSTRUAL"),
]


def _carregar_permissoes(vault_root: Path | None) -> dict:
    if vault_root is None:
        return {"a_to_b": {}, "b_to_a": {}}
    arq = vault_root / ".ouroboros" / "permissoes.toml"
    if not arq.exists():
        return {"a_to_b": {}, "b_to_a": {}}
    try:
        import tomllib
        return tomllib.loads(arq.read_text(encoding='utf-8'))
    except Exception:
        return {"a_to_b": {}, "b_to_a": {}}


def _renderizar_grade_permissoes(direcao: str, perms: dict) -> None:
    """Tabela 6 campos × 4 níveis com radio em cada célula."""
    import streamlit as st
    st.markdown('<div class="perm-grid-header"><span>CAMPO / FONTE</span><span>OCULTO</span><span>AGREGADO</span><span>RESUMO</span><span>TOTAL</span></div>', unsafe_allow_html=True)
    for chave, label, secao in CAMPOS:
        atual = perms.get(direcao, {}).get(chave, "oculto")
        cols = st.columns([2, 1, 1, 1, 1])
        with cols[0]:
            st.markdown(f'<span class="perm-campo">{label}</span><br><span class="perm-fonte">.ouroboros/{secao.lower().replace(" ", "_")}</span>', unsafe_allow_html=True)
        for i, nivel in enumerate(NIVEIS):
            with cols[i + 1]:
                checked = "checked" if atual == nivel else ""
                st.markdown(f'<input type="radio" name="{direcao}_{chave}" value="{nivel}" {checked}>', unsafe_allow_html=True)
```

CSS em `be_privacidade.css`: `.perm-grid-header`, `.perm-campo`, `.perm-fonte`, `.legenda-niveis`, `.parceira-card`, `.audit-log-btn`.

## Validação DEPOIS

```bash
make lint && make smoke
.venv/bin/python -m pytest tests/test_be_resto.py -q
```

## Proof-of-work

Validação visual em `cluster=Bem-estar&tab=Privacidade`. Mostrar:
1. Direção A→B / B→A em tabs
2. Grade 9 campos × 4 níveis com radios
3. Cards laterais (Você A / Parceira B)
4. Botão Salvar permissões + Audit log

## Critério de aceitação

1. Schema `permissoes.toml` lido (mesmo se vazio).
2. Grade renderizando com radios.
3. Cards laterais.
4. Botão Salvar (placeholder OK; persistência real opcional).
5. CSS + lint OK + cluster pytest verde.

## Não-objetivos

- NÃO implementar Audit log persistência completa (botão visual OK).
- NÃO criar ADR-23 nesta sprint (sprint-filha futura se necessário).
- NÃO implementar enforcement das permissões em sync_rico.py (escopo separado).

## Referência

- Mockup: 27-privacidade.html.
- Decisão dono 2026-05-07: feature granular completa.
- VALIDATOR_BRIEF: (a)/(b)/(k)/(o)/(u).

*"Privacidade é a base do casal honesto." -- princípio V-2.15*
