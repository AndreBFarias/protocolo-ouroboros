---
id: MOB-spec-galeria-memorias
titulo: Formato .capsula.md canonico para Galeria de Memorias/Eventos lido por app e dashboard
status: concluída  <!-- noqa: accent -->
concluida_em: 2026-05-13  <!-- noqa: accent -->
prioridade: P2
data_criacao: 2026-05-12
fase: BRIDGE_MOBILE
depende_de: [MOB-bridge-4-inbox-subtipos-reader]
esforco_estimado_horas: 2
origem: Plano 2026-05-12 secao Fase B; brief do dono pediu galeria de Memorias/Eventos; auditor C1 confirmou galeria mobile existe mas e read-only; dashboard ja tem be_memorias.py com renderer aguardando schema.  <!-- noqa: accent -->
mockup: novo-mockup/mockups/M-memorias.html  <!-- noqa: accent -->
---

# Sprint MOB-spec-galeria-memorias -- contrato .capsula.md compartilhado

## Contexto

Brief do dono: "Cada coisa que eu salvar, eu preciso conseguir voltar, ver, ler e editar. Não temos um espaço de galeria dos eventos eu não consigo ver nada."

Auditor C1 (2026-05-12) confirmou:
- `/galeria` no app mobile existe com 15 tipos, mas **detalhe é read-only** (itens da Home não-tappáveis).
- Edição fica pro desktop ou para novas telas `/[tipo]/[id]/editar`.

Dashboard backend já tem `src/dashboard/paginas/be_memorias.py` (Onda V Sprint UX-V-2.11) com renderer canônico aguardando vault populado. ADR-25 + `mappings/schema_memorias.json` (Sprint INFRA-MEMORIAS-SCHEMA) já existem.

Esta sprint **fecha o ciclo app → vault → dashboard** definindo o formato `.capsula.md` que ambos os lados consomem.

## Objetivo

1. Documentar o **formato `.capsula.md` canônico** em ADR-25 (atualização) ou novo ADR-25-extensao:
   - Frontmatter YAML completo (campos obrigatórios + opcionais).
   - Corpo livre em markdown.
   - Convenção de nomes: `<YYYY-MM-DD>-<HHmmss>-<slug>.capsula.md`.
   - Pasta: `inbox/memorias/<YYYY>/<MM>/`.
   - Binários associados: `<basename>.<jpg|mp4|m4a|...>` ao lado.
2. Criar 2 cápsulas exemplo em `tests/fixtures/capsulas/`:
   - `2026-05-12-100000-aniversario-vitoria.capsula.md` (texto + 3 fotos).
   - `2026-05-12-180000-show-rock-band.capsula.md` (texto + 1 video + 1 audio).
3. Refactor `src/dashboard/paginas/be_memorias.py` para consumir o formato canônico (carregar `.capsula.md`, parsear frontmatter, listar binários companion, exibir grid).
4. Estender `mappings/schema_memorias.json` se necessário para cobrir o formato `.capsula.md` (provavelmente extends os campos existentes com `binarios_companion[]`).
5. Testes em `tests/test_capsula_md.py`.

## Validação ANTES (grep -- padrão (k))

```bash
ls src/dashboard/paginas/be_memorias.py
grep -n "schema_memorias\|capsula" mappings/schema_memorias.json
ls docs/adr/ADR-25-*
ls ~/Protocolo-Ouroboros/inbox/memorias/ 2>/dev/null
grep -rn "galeria\|memorias" ~/Desenvolvimento/Protocolo-Mob-Ouroboros/app/ 2>/dev/null | head
```

Confirma: (a) be_memorias.py existe (Onda V Sprint UX-V-2.11), (b) schema parcial existe, (c) ADR-25 existe, (d) vault tem pasta memorias com cápsulas reais ou não.

## Não-objetivos (padrão (t))

- **NÃO** implementar UI de edição no app — esperar sprint do lado mobile.
- **NÃO** mover/deletar cápsulas existentes.
- **NÃO** redactar conteúdo do corpo do `.md` (cápsulas são memórias do casal, intocáveis).
- **NÃO** sincronizar Syncthing programaticamente.
- **NÃO** depender de XLSX ou grafo SQLite para renderizar a galeria — cápsulas são o "estado real" (similar a Recap).

## Spec de implementação

### Formato `.capsula.md` canônico

```yaml
---
_schema_version: 1
tipo: memoria
data: 2026-05-12
hora: 10:00:00
titulo: Aniversario da Vitoria
slug: aniversario-vitoria
area: outros
subtipo: memoria
pessoas: [andre, vitoria]
local:
  nome: Casa
  cidade: Maceio
  coordenadas: [-9.6498, -35.7089]
tags: [aniversario, casal, especial]
emocao_principal: alegria
intensidade: 9
companions:
  - tipo: foto
    arquivo: 2026-05-12-100000-aniversario-vitoria-1.jpg
    legenda: bolo no balcao
  - tipo: foto
    arquivo: 2026-05-12-100000-aniversario-vitoria-2.jpg
  - tipo: audio
    arquivo: 2026-05-12-100000-parabens.m4a
    legenda: parabens cantado
duracao_estimada_min: null
evento_vinculado_uuid: <opcional, se a memoria liga a evento da agenda>
---

# Aniversario da Vitoria

A gente acordou e ela ja tava com bolo na cozinha...
(corpo livre em markdown, longo se quiser, com referencia a companions)
```

### Atualização schema_memorias.json

Adicionar bloco `companions[]` com `tipo`, `arquivo`, `legenda` opcional.

### Renderer dashboard

```python
# src/dashboard/paginas/be_memorias.py
def carregar_capsulas(vault_path: Path) -> list[Capsula]:
    capsulas = []
    for caminho in (vault_path / "inbox" / "memorias").rglob("*.capsula.md"):
        frontmatter, corpo = parsear_md(caminho)
        validar_contra_schema(frontmatter)
        capsulas.append(Capsula(frontmatter=frontmatter, corpo=corpo, caminho=caminho))
    return sorted(capsulas, key=lambda c: c.frontmatter["data"], reverse=True)


def render_galeria(capsulas):
    grid = st.columns(3)
    for i, capsula in enumerate(capsulas[:9]):
        with grid[i % 3]:
            st.markdown(card_capsula_html(capsula), unsafe_allow_html=True)
```

## Proof-of-work (padrão (u))

```bash
# 1. Validar fixtures
.venv/bin/python -c "
import yaml, json, jsonschema
from pathlib import Path
schema = json.load(open('mappings/schema_memorias.json'))
for fix in Path('tests/fixtures/capsulas/').glob('*.capsula.md'):
    txt = fix.read_text()
    front, _ = txt.split('---', 2)[1:]
    parsed = yaml.safe_load(front)
    jsonschema.validate(parsed, schema)
    print(f'OK: {fix.name}')
"

# 2. Carregar via dashboard
.venv/bin/python -c "
from pathlib import Path
from src.dashboard.paginas.be_memorias import carregar_capsulas
print(len(carregar_capsulas(Path('tests/fixtures/'))))  # esperado: 2
"

# 3. Rodar dashboard manual
./run.sh --dashboard
# Acessar Bem-estar > Memorias

# 4. Gauntlet
make lint && make smoke
.venv/bin/pytest tests/test_capsula_md.py -v
```

## Critério de aceitação (gate (z))

1. `mappings/schema_memorias.json` estendido com bloco `companions[]`.
2. 2 fixtures `.capsula.md` em `tests/fixtures/capsulas/` validam contra schema.
3. `src/dashboard/paginas/be_memorias.py::carregar_capsulas` funciona e exibe grid.
4. `tests/test_capsula_md.py` ≥ 6 testes.
5. ADR-25 atualizada (ou ADR-25-extensao criado) com formato canônico.
6. App mobile pode começar implementação de tela de edição em outra sessão a partir do schema.
7. Gauntlet verde + validação visual via screenshot.

## Referência

- Auditoria C1: `docs/auditorias/AUDITORIA_APP_MOBILE_2026-05-12.md` (galeria mobile read-only).
- Sprint Onda V Memórias: `docs/sprints/concluidos/sprint_ux_v_2_11_memorias.md`.
- Sprint INFRA-MEMORIAS-SCHEMA: `docs/sprints/concluidos/sprint_INFRA_memorias_schema.md`.
- ADR-25: `docs/adr/ADR-25-memorias-schema.md`.
- Plano de origem: `~/.claude/plans/preciso-que-use-o-crispy-stroustrup.md` Fase B.

*"Memoria sem galeria fica no fundo do baú; galeria sem memoria fica vazia de sentido." — princípio MOB-spec-galeria-memorias*
