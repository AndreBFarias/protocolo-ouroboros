---
id: UX-V-05
titulo: Glyphs prefixados em todos os botões de topbar-actions conforme mockup
status: concluída
prioridade: media
data_criacao: 2026-05-07
concluida_em: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-M-04]
co_executavel_com: [UX-V-01, UX-V-02, UX-V-03, UX-V-04]
esforco_estimado_horas: 2
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (P5)
ressalva: |
  Spec original propunha catálogo ASCII (+/^/v/~). Hipótese refutada pelo grep
  (padrão (k)): sistema JÁ usa SVG inline canônico desde UX-RD-FIX-07/UX-U-02
  (52 glyphs em componentes/glyphs.py com paridade 1:1 com novo-mockup/_shared
  /glyphs.js). Sprint adotou catálogo SVG como fonte canônica e formalizou:
  GLYPHS_CANONICOS (subconjunto curado de 27 IDs validados) + ACOES_PARA_GLYPH
  (54 mapeamentos label->id). Regredir SVG para ASCII violaria padrão (a) (não
  apagar código funcional).
---

# Sprint UX-V-05 — Glyphs em topbar-actions

## Contexto

Auditoria 2026-05-07 (P5) constatou que mockups canônicos têm glyphs prefixando todos os botões de topbar-actions (ex.: "+ Nova meta", "↑ Importar OFX", "↓ Exportar", "↻ Recalibrar"), mas o dashboard renderiza só texto na maioria dos casos.

A Onda U-02 (`renderizar_grupo_acoes`) já entregou a fronteira canônica de topbar-actions e suporta o parâmetro `glyph` (visto em alguns lugares: `{"label": "Importar OFX", "glyph": "upload", ...}`), mas a maioria das chamadas omite o glyph.

Esta sprint **inventaria todas as topbar-actions de todas as páginas + adiciona glyphs onde mockup tem**.

## Páginas afetadas

Todas as 30 páginas que chamam `renderizar_grupo_acoes(...)`. Auditoria visual nas 22 páginas com mockup confirma divergência.

## Objetivo

1. Mapear cada botão de topbar de cada página dashboard contra o mockup correspondente.
2. Adicionar parâmetro `glyph` em cada chamada conforme mockup.
3. Validar que `componentes/topbar_actions.py` renderiza o glyph corretamente (já deve renderizar — verificar).
4. Catálogo de glyphs canônicos centralizado em uma constante (DRY).

## Validação ANTES (grep obrigatório)

```bash
# Glyph já é suportado pelo componente?
grep -n "glyph" src/dashboard/componentes/topbar_actions.py | head -10
# Esperado: matches (Onda U-02 implementou)

# Quais páginas chamam renderizar_grupo_acoes?
grep -rln "renderizar_grupo_acoes" src/dashboard/paginas/ | wc -l
# Esperado: ≥30

# Quais já usam glyph?
grep -rn '"glyph"' src/dashboard/paginas/ | head -20
# Lista de chamadas com glyph (parcial)

# Catálogo de glyphs disponíveis
test -f src/dashboard/componentes/glyphs.py && cat src/dashboard/componentes/glyphs.py | head -30
ls novo-mockup/_shared/glyphs.js
# Mockup tem glyphs.js — fonte canônica
```

Se `glyph` parameter já existe e funciona em algumas páginas, esta sprint é **só preencher os que estão sem**.

## Spec de implementação

### 1. Catálogo canônico de glyphs

Criar `src/dashboard/componentes/glyphs_canonicos.py` (ou estender `componentes/glyphs.py` se já existir):

```python
"""Catálogo canônico de glyphs para topbar-actions.

Origem: novo-mockup/_shared/glyphs.js. Cada glyph tem ID curto que
``renderizar_grupo_acoes`` consome via ``{"glyph": "<id>"}``.

Mantido como dict literal para que:
1. Lint catch typos (KeyError em runtime quando ID invented).
2. ``renderizar_grupo_acoes`` valide ``glyph in GLYPHS_CANONICOS``.
3. Auditoria visual cruze IDs com mockup.
"""

# Cada entrada: id -> caractere/HTML que vai antes do label.
# Caracteres seguros (ASCII ou tipograficamente estáveis -- não emojis).
GLYPHS_CANONICOS: dict[str, str] = {
    # Adicionar
    "plus": "+",
    "novo": "+",          # alias semântico
    # Salvar / commit
    "check": ">",         # placeholder; ajustar se houver SVG canônico
    "salvar": ">",
    # Atualizar / sincronizar
    "refresh": "~",       # placeholder ASCII
    "sync": "~",
    "atualizar": "~",
    # Importar / exportar
    "upload": "^",
    "importar": "^",
    "download": "v",
    "exportar": "v",
    # Comparar
    "diff": "=",
    "comparar": "=",
    # Listas
    "logs": "*",
    "auditoria": "*",
    # Calendário
    "calendar": "@",
    "calendario": "@",
}

# Mapeamento auxiliar: ação semântica -> glyph_id
ACOES_PARA_GLYPH: dict[str, str] = {
    "Nova meta": "plus",
    "Adicionar conta": "plus",
    "Adicionar tipo": "plus",
    "Novo evento": "plus",
    "Capturar": "plus",
    "Registrar": "plus",
    "Salvar": "salvar",
    "Salvar humor": "salvar",
    "Salvar permissões": "salvar",
    "Salvar (commit)": "salvar",
    "Atualizar": "atualizar",
    "Atualizar fila": "atualizar",
    "Recalibrar": "atualizar",
    "Recalcular": "atualizar",
    "Re-gerar agora": "atualizar",
    "Reprocessar": "atualizar",
    "Importar OFX": "upload",
    "Importar Mi Fit": "upload",
    "Sincronizar OFX": "sync",
    "Exportar": "download",
    "Exportar relatório": "download",
    "Exportar 90d": "download",
    "Exportar gaps": "download",
    "Baixar": "download",
    "Baixar lote": "download",
    "Comparar cenários": "comparar",
    "Logs": "logs",
    "Audit log": "logs",
    "Auditoria": "logs",
    "Histórico": "logs",
    "Histórico (git log)": "logs",
    "Calendário": "calendario",
    "Hoje": "calendario",
}
```

### 2. Inventário + correção página a página

Para cada página, abrir o mockup correspondente e listar os botões de topbar. Aplicar `glyph` conforme `ACOES_PARA_GLYPH`. Exemplo:

```python
# ANTES (catalogacao.py)
renderizar_grupo_acoes([
    {"label": "Reprocessar", "title": "Re-extrair documentos"},
    {"label": "Adicionar tipo", "primary": True,
     "title": "Cadastrar novo tipo de documento"},
])

# DEPOIS
renderizar_grupo_acoes([
    {"label": "Reprocessar", "glyph": "atualizar",
     "title": "Re-extrair documentos"},
    {"label": "Adicionar tipo", "glyph": "plus", "primary": True,
     "title": "Cadastrar novo tipo de documento"},
])
```

### 3. Validação no componente

Em `src/dashboard/componentes/topbar_actions.py`, adicionar (se não existe) validação opcional de glyph:

```python
def renderizar_grupo_acoes(acoes: list[dict]) -> None:
    """...docstring existente..."""
    from src.dashboard.componentes.glyphs_canonicos import GLYPHS_CANONICOS
    for acao in acoes:
        glyph_id = acao.get("glyph")
        if glyph_id and glyph_id not in GLYPHS_CANONICOS:
            # Log warning, não quebra (graceful)
            import logging
            logging.warning(
                "Glyph desconhecido: %s. Disponíveis: %s",
                glyph_id, list(GLYPHS_CANONICOS.keys()),
            )
            acao = {**acao, "glyph": None}  # remove glyph inválido
    # ...resto da renderização...
```

E na renderização, prefixar o glyph:

```python
# Pseudo-código (adaptar à implementação real do componente)
glyph_char = GLYPHS_CANONICOS.get(glyph_id, "") if glyph_id else ""
prefix_html = f'<span class="btn-glyph">{glyph_char}</span> ' if glyph_char else ""
btn_html = f'<button class="btn ..."><span>{prefix_html}{label}</span></button>'
```

### 4. CSS para `.btn-glyph`

Adicionar em `src/dashboard/css/components.css` se não existe:

```css
.btn-glyph {
    display: inline-block;
    margin-right: 4px;
    font-family: var(--ff-mono);
    font-size: 0.95em;
    opacity: 0.85;
}
```

### 5. Páginas a tocar (estimativa)

Inventário rápido grep:

```bash
grep -l "renderizar_grupo_acoes" src/dashboard/paginas/*.py
```

Espera-se ~28 páginas. Para cada uma, cruzar com mockup correspondente. Lista mínima de botões a adicionar glyph (auditoria 2026-05-07):

| Página | Botões com glyph faltando |
|---|---|
| visao_geral | Atualizar (atualizar), Ir para Validação (check) |
| extrato | Importar OFX (upload), Exportar (download) |
| contas | Adicionar conta (plus), Sincronizar OFX (sync) |
| pagamentos | Marcar pago (check), Adicionar (plus) |
| projecoes | Comparar cenários (comparar), Salvar cenário (salvar) |
| busca | Filtros avançados (não tem glyph; só primary) |
| catalogacao | Reprocessar (atualizar), Adicionar tipo (plus) |
| completude | Reprocessar (atualizar), Exportar gaps (download) |
| revisor | (TBD após auditoria de revisor) |
| validacao_arquivos | Baixar lote (download), Salvar validações (salvar) |
| categorias | Nova regra (plus), Recategorizar (atualizar) |
| analise_avancada | Categorias (sem glyph), Exportar relatório (download) |
| metas | Skills D7 (sem glyph), Nova meta (plus) |
| skills_d7 | Recalibrar (atualizar), Logs (logs) |
| irpf | Recalcular (atualizar), Gerar pacote (download) |
| inbox | Abrir pasta (sem glyph), Atualizar fila (atualizar) |
| be_hoje | Diário emocional (sem glyph), Salvar humor (salvar) |
| be_humor | Exportar 90d (download), Registrar agora (plus) |
| be_diario | Heatmap (sem glyph), Hoje (calendario) |
| be_eventos | Calendário (calendario), Novo evento (plus) |
| be_rotina | Hoje (calendario), Novo (plus) |
| be_recap | Re-gerar agora (atualizar), Cruzamentos (sem glyph), Compartilhar com Pessoa B (sem glyph; opcional check) |
| be_memorias | Random (sem glyph; opcional sync), Capturar (plus) |
| be_medidas | Importar Mi Fit (upload), Registrar (plus) |
| be_ciclo | Histórico (logs), Registrar dia (plus) |
| be_cruzamentos | Salvar como bloco do Recap (salvar), Voltar ao Recap (sem glyph; opcional logs) |
| be_privacidade | Audit log (logs), Salvar permissões (salvar) |
| be_editor_toml | Histórico (git log) (logs), Salvar (commit) (salvar) |

## Validação DEPOIS

```bash
# Catálogo existe
test -f src/dashboard/componentes/glyphs_canonicos.py && \
  grep -c "GLYPHS_CANONICOS" src/dashboard/componentes/glyphs_canonicos.py

# Maioria das chamadas tem glyph
total=$(grep -rE 'renderizar_grupo_acoes\(\s*\[' src/dashboard/paginas/*.py -l | wc -l)
com_glyph=$(grep -rE '"glyph"' src/dashboard/paginas/*.py -l | wc -l)
echo "$com_glyph de $total páginas tem glyph"
# Esperado: com_glyph >= 25 (de ~28-30)

# Lint, smoke, pytest
make lint
make smoke
.venv/bin/python -m pytest tests/test_topbar*.py -q 2>&1 | tail -5
# Esperado: 0 fails
```

## Proof-of-work runtime-real

```bash
# Restart dashboard
pkill -f "streamlit run" 2>/dev/null
setsid -f sh -c '.venv/bin/python -m streamlit run src/dashboard/app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false > /tmp/dash.log 2>&1 &'
sleep 7

# Validação visual em 6 páginas (1 por cluster + 1 amostra Bem-estar):
# - Visão Geral, Extrato, Catalogação, Categorias, Inbox, Be / Eventos
# Cada screenshot deve mostrar botões topbar com glyph prefixado:
# - "+ Nova meta", "+ Adicionar conta", "↑ Importar OFX" (placeholder ASCII +/^/v/~)
```

## Critério de aceitação

1. `glyphs_canonicos.py` criado com `GLYPHS_CANONICOS` + `ACOES_PARA_GLYPH`.
2. ≥25 páginas dashboard têm `glyph` adicionado em chamadas de `renderizar_grupo_acoes`.
3. `topbar_actions.py` valida glyph contra catálogo (warning para inválidos).
4. CSS `.btn-glyph` em `components.css`.
5. `make lint && make smoke && pytest tests/test_topbar*.py` verde.
6. Validação visual: 6 páginas-amostra mostram glyphs.

## Não-objetivos

- NÃO usar emojis (proibido pelo `(c)` do VALIDATOR_BRIEF) — usar ASCII estável (+/-/^/v/~/*/@/=).
- NÃO migrar para SVG icons (lucide-react) — escopo de sprint futura se necessário.
- NÃO adicionar glyph em páginas sem mockup correspondente (Recap não-mockup, Editor TOML novas funcs).
- NÃO mudar layout dos botões — só prefixar glyph.

## Referência

- Auditoria 2026-05-07 P5 (`docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md`).
- Mockup canônico: cada `mockups/NN-*.html` mostra glyph nos botões topbar.
- Onda U-02 (já fechada): `renderizar_grupo_acoes` em `componentes/topbar_actions.py`.
- VALIDATOR_BRIEF padrões: `(c)` zero emojis, `(b)` acentuação PT-BR, `(u)` proof-of-work runtime real.

*"O glyph é a primeira leitura; o label é a segunda." — princípio V-05*
