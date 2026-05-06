---
id: UX-M-03
titulo: CSS canônico do mockup centralizado em css/components.css
status: backlog
prioridade: alta
data_criacao: 2026-05-06
data_revisao: 2026-05-06
fase: MODULARIZAÇÃO
depende_de: [UX-M-01, UX-M-02]
bloqueia: [UX-M-02.A, UX-M-02.B, UX-M-02.C, UX-M-02.D]
esforco_estimado_horas: 4-6
---

# Sprint UX-M-03 — CSS canônico do mockup centralizado

## Contexto

Após UX-M-02 entregar componentes universais (`ui.py`), cada componente precisa de seu CSS canônico para renderizar idêntico ao mockup.

**Achado da auditoria 2026-05-06**: a fonte canônica de CSS **JÁ EXISTE** em `novo-mockup/_shared/components.css` (387 linhas, 87 classes: `.shell`, `.sidebar`, `.page-header`, `.kpi`, `.btn`, `.card`, `.pill`, `.table`, `.drawer`, `.skill-instr`, etc.). Sprint UX-RD-02 trouxe partes desse CSS para `tema_css.py` mas em formato hard-coded dentro de Python.

`tema_css.py` tem 1675 linhas. ~400 linhas vieram de `components.css` (estimativa). Migrar para arquivo CSS separado:

1. Reduz `tema_css.py` em ~400 linhas.
2. Permite designer/humano editar CSS sem entender Python.
3. Mantém sincronia 1:1 com mockup canônico (fonte de verdade).
4. Prepara base para futura divisão por componente (UX-M-03b futuro).

## Objetivo

Extrair as 87 classes do mockup para `src/dashboard/css/components.css` (cópia 1:1 de `novo-mockup/_shared/components.css`). `tema_css.py` carrega via `Path.read_text()` e remove o bloco hard-coded equivalente. Sub-divisão por componente (`css/components/page_header.css`, etc.) é débito separado.

## Hipótese

**A**: 1 arquivo `components.css` monolítico cobrindo todos os componentes do mockup é suficiente para Onda M.
**Não-A** (futuro): dividir em 8 arquivos por componente (`page_header.css`, `kpi.css`, etc.).

Razão A: divisão por componente é over-engineering nesta fase. Monolítico é fonte de verdade clara, fácil grep, fácil diff com mockup. Divisão vira sprint futura quando houver pressão real de manutenção.

## Validação ANTES (grep obrigatório)

```bash
# Volume atual de CSS hard-coded em Python
wc -l src/dashboard/tema_css.py
# Esperado: ~1675 linhas

# Confirmar fonte canônica
wc -l novo-mockup/_shared/components.css
# Esperado: 387 linhas

# Contar classes no mockup
grep -cE "^\.[a-z]" novo-mockup/_shared/components.css
# Esperado: 87 classes

# tokens.css existe (M-01)?
test -f src/dashboard/css/tokens.css && echo "M-01 OK" || echo "BLOQUEADO: M-01 não rodou"

# ui.py existe (M-02)?
test -f src/dashboard/componentes/ui.py && echo "M-02 OK" || echo "BLOQUEADO: M-02 não rodou"
```

## Spec de implementação

### 1. Copiar `components.css` do mockup

```bash
# tokens.css já existe (UX-M-01)
cp novo-mockup/_shared/components.css src/dashboard/css/components.css
```

Adicionar header no topo:

```css
/* Componentes CSS canônicos do dashboard Ouroboros.
 * Fonte: novo-mockup/_shared/components.css (mantida 1:1).
 * 87 classes: shell, sidebar, page-header, kpi, btn, card, pill,
 * table, drawer, skill-instr, etc.
 *
 * Sprint UX-M-03 — Onda M (modularização).
 *
 * REGRA: ao editar uma classe aqui, atualizar o mockup canônico
 * na MESMA sprint. Inconsistência = drift visual silencioso.
 */
```

### 2. Refatorar `tema_css.py`

Adicionar no topo:

```python
_COMPONENTS_CSS = (_RAIZ_DASHBOARD / "css" / "components.css").read_text(encoding="utf-8")
```

Identificar bloco hard-coded em `tema_css.py` que veio de `components.css` (Sprint UX-RD-02). Substituir por:

```python
def _components_redesign() -> str:
    """Classes canônicas do mockup. Sprint UX-M-03.

    Fonte: src/dashboard/css/components.css.
    """
    return f"\n{_COMPONENTS_CSS}\n"
```

E na função `css_global()`, garantir que `_components_redesign()` é chamado UMA vez (não duplicar com bloco hard-coded antigo).

### 3. Validação cruzada com mockup

Criar teste de sincronia (opcional, se houver tempo):

```python
# tests/test_components_css_sync.py
def test_components_css_identico_ao_mockup():
    """Sincronia: src/dashboard/css/components.css == novo-mockup/_shared/components.css."""
    raiz = Path(__file__).resolve().parent.parent
    src_css = (raiz / "src" / "dashboard" / "css" / "components.css").read_text("utf-8")
    mockup_css = (raiz / "novo-mockup" / "_shared" / "components.css").read_text("utf-8")
    # Remover header comment do src se diferir
    src_sem_header = re.sub(r"^/\*.*?\*/\s*", "", src_css, count=1, flags=re.DOTALL)
    assert src_sem_header.strip() == mockup_css.strip(), (
        "Drift detectado entre mockup e dashboard. Sincronizar."
    )
```

## Estratégia gradual (não big-bang)

| Etapa | Quando | Escopo |
|---|---|---|
| Etapa 1 (esta sprint) | UX-M-03 | Copiar `components.css` inteiro para `src/dashboard/css/`. Refatorar `tema_css.py` para ler dele. |
| Etapa 2 (sub-sprints) | UX-M-02.A..D | Páginas migradas para `from ui import ...` consomem classes do `components.css` automaticamente. |
| Etapa 3 (sprint futura UX-M-03b) | OPCIONAL | Dividir `components.css` em arquivos por componente (`page_header.css`, `kpi.css`, etc.). Só se houver pressão real. |

## Validação DEPOIS

```bash
# components.css existe e tem mesmo tamanho do mockup
diff -q src/dashboard/css/components.css novo-mockup/_shared/components.css | head -1
# Esperado: vazio (ou apenas diff em comment header)

# tema_css.py reduziu (≥300 linhas a menos)
wc -l src/dashboard/tema_css.py
# Esperado: ~1300 linhas (era ~1675; M-01 já reduziu ~150)

# 87 classes presentes no CSS servido
curl -s http://127.0.0.1:8765 | grep -c "\.kpi\|\.page-header\|\.sidebar"
# Esperado: ≥3 (classes presentes no HTML)

# Lint, smoke, tests
make lint && make smoke && pytest tests/ -q
```

## Proof-of-work

```bash
# Restart dashboard
pkill -f "streamlit run" 2>/dev/null || true
make dashboard &
sleep 5

# Validação visual: 5 páginas-amostra sem regressão
# - Visão Geral: page-header com gradient idêntico ao mockup
# - Busca Global: search-bar com cor purple, kbd / visível
# - Catalogação: KPIs com bordas semânticas (verde/amarelo/laranja)
# - Contas: cards de banco com .card.interactive
# - Projeções: pills SIMULAÇÃO renderizam com classes corretas
```

## Critério de aceitação

1. `src/dashboard/css/components.css` existe e é cópia 1:1 de `novo-mockup/_shared/components.css` (exceto header comment).
2. `tema_css.py` carrega `components.css` UMA vez via `Path.read_text()`.
3. `tema_css.py` reduziu ≥300 linhas (combinado com M-01: ≥400 linhas reduzidas total).
4. Bloco hard-coded equivalente em `tema_css.py` removido.
5. (Opcional) Teste de sincronia mockup ↔ dashboard adicionado.
6. Lint, smoke, tests verdes.
7. Validação visual: 5 páginas-amostra sem regressão.

## Não-objetivos (escopo fechado)

- NÃO dividir `components.css` em arquivos por componente — débito futuro UX-M-03b.
- NÃO migrar páginas para usar classes canônicas (sub-sprints UX-M-02.A..D fazem).
- NÃO migrar bloco `_root_legado` ou outras seções de `tema_css.py` — débito separado.
- NÃO criar componentes novos não-presentes no mockup — usar `ui.py` (M-02).

## Referência

- `novo-mockup/_shared/components.css` — fonte canônica (387 linhas, 87 classes).
- `src/dashboard/tema_css.py` — destino do refactor.
- UX-M-01 (depende) — tokens CSS.
- UX-M-02 (depende) — componentes universais.
- UX-M-02.A..D (bloqueia) — sub-sprints que CONSOMEM as classes canônicas.

## Dúvidas que NÃO precisam ser perguntadas

- "Devo dividir em 8 arquivos?" Não — monolítico é suficiente nesta fase.
- "E o `_root_legado` e outras seções?" Fora de escopo — débito separado.
- "Como os componentes Streamlit nativos vão usar?" Eles não — só componentes nossos via `ui.py`.
- "E se mockup e dashboard divergirem?" Teste de sincronia detecta (item 5 do critério).

*"O CSS do botão vive perto do botão... e do mockup do botão." — princípio da Onda M*
