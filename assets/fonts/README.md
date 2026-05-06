# assets/fonts/

Diretório reservado para self-host das fontes Variable do redesign UX-RD-02.

## Decisão Sprint UX-RD-02

A migração inicial do `tema_css.py` para os tokens dos mockups foi feita
usando **fallbacks nativos** declarados na cascata de `--ff-sans` e
`--ff-mono`:

- `--ff-sans: 'Inter', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif`
- `--ff-mono: 'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace`

Quando o browser não encontra `Inter` ou `JetBrains Mono` instalados,
recai para `ui-sans-serif` / `ui-monospace` (fontes do sistema operacional).
Resultado visual aceitável e 100% compatível com Local First (ADR-07) -
zero requisição externa, zero dependência de rede no boot do dashboard.

## Como adicionar self-host (sprint futura)

1. Baixar os arquivos `.woff2` Variable de fontes livres:
   - Inter: <https://rsms.me/inter/download/> (Inter-Variable.woff2)
   - JetBrains Mono: <https://www.jetbrains.com/lp/mono/> (JetBrainsMono-Variable.woff2)

2. Salvar em `assets/fonts/Inter-Variable.woff2` e
   `assets/fonts/JetBrainsMono-Variable.woff2`.

3. Em `src/dashboard/tema_css.py`, ler os bytes e injetar via base64
   data URL no bloco `@font-face` (Streamlit não tem servidor estático
   nativo confiável para `assets/`):

```python
import base64
from pathlib import Path

_INTER = Path("assets/fonts/Inter-Variable.woff2")
_MONO = Path("assets/fonts/JetBrainsMono-Variable.woff2")

def _woff2_b64(p: Path) -> str:
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode("ascii")
```

4. Concatenar no início do `<style>` retornado por `css_global()`:

```css
@font-face {
  font-family: 'Inter';
  src: url(data:font/woff2;base64,<base64>) format('woff2-variations');
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
}
@font-face {
  font-family: 'JetBrains Mono';
  src: url(data:font/woff2;base64,<base64>) format('woff2-variations');
  font-weight: 100 800;
  font-style: normal;
  font-display: swap;
}
```

5. Adicionar teste: `tests/test_tema_css_redesign.py::test_fontes_self_hosted_em_b64`.

## Por que não fizemos agora

- Sprint UX-RD-02 já é grande (tokens + 388 linhas de classes utilitárias).
- Self-host obriga commitar binários (~600 KB total) - melhor isolar em
  sprint dedicada (UX-RD-02b futura) com revisão de licença das fontes.
- Fallback `ui-sans-serif` é aceitável visualmente para o casal validar
  o resto do redesign (cores, espaçamento, pills, KPIs) sem ruído.
