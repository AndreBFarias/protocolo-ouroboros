---
id: MOB-spec-transcricao-audio
titulo: Pipeline canonico para audio capturado pelo app -- aterrissagem em inbox/audio + escolha do motor (ADR-28)
status: backlog
concluida_em: null
prioridade: P2
data_criacao: 2026-05-12
fase: BRIDGE_MOBILE
depende_de: [MOB-bridge-4-inbox-subtipos-reader]
esforco_estimado_horas: 3
origem: "Plano 2026-05-12 secao Fase B; brief do dono pediu transcricao automatica live + app Onda Q ja entrega live transcribe; backend precisa receber audio + transcricao + persistir.  <!-- noqa: accent -->"
adr_associada: "ADR-28 (motor canonico de transcricao -- whisper local vs Opus multimodal)  <!-- noqa: accent -->"
---

# Sprint MOB-spec-transcricao-audio -- contrato + stub backend de transcricao de audio

## Contexto

Onda Q (2026-05-12) do app entregou transcrição live via `MicrofoneButton.tsx:322` (achado da auditoria C1). Backend precisa:

1. Receber `.m4a` capturado pelo app (via Share Intent ou via captura direta de "registrar momento").
2. Decidir: usar a transcrição que veio do app OU rodar uma segunda transcrição de fallback?
3. Persistir transcrição + áudio + metadata em vault canônico.

ADR-28 fica em **decisão técnica**: motor canônico para transcrição de fallback no backend. Opções:

- **whisper.cpp local** (offline, ADR-07 compliant, baixo custo, qualidade variável).
- **Opus multimodal** (ADR-13, supervisor humano lê via Read tool, alta qualidade, custo zero porque eu sou interativo).
- **Whisper API** (não conformidade ADR-13/07; descartado).

Esta sprint estabelece contrato + stub. Implementação real do motor escolhido fica para sprint-filha (ex: `INFRA-TRANSCRICAO-WHISPER-LOCAL` ou `INFRA-TRANSCRICAO-OPUS`).

## Objetivo

1. Criar `src/intake/audio_transcricao.py` com:
   - `aterrissar(caminho_m4a: Path) -> AudioAterrissado`: move/sidecar áudio em `inbox/audio/YYYY-MM-DD-HHmmss-<slug>.m4a` + companion `.md` com frontmatter (`_schema_version: 1, tipo: audio, transcricao_live: <do app>, transcricao_backend: <pendente>`).
   - `transcrever(caminho_m4a: Path, motor: str = "stub") -> str`: stub que aceita `motor in {stub, whisper_local, opus_artesanal}` e retorna placeholder por enquanto.
   - `validar_transcricao_dual(transcricao_app: str, transcricao_backend: str) -> dict`: compara as duas; flag quando divergem (peso > 30%).
2. Spec da decisão arquitetural em `docs/adr/ADR-28-motor-transcricao-audio.md`:
   - Opções (whisper local vs Opus artesanal).
   - Critérios de escolha (custo, qualidade, soberania, simplicidade).
   - Recomendação técnica (Opus artesanal como primário; whisper local como fallback offline).
3. Schema do `.md` companion canônico documentado.
4. Fixture: `tests/fixtures/audio/exemplo_curto.m4a` (3-5s, conteúdo "Audio teste protocolo Ouroboros").
5. Testes em `tests/test_audio_transcricao.py`.

## Validação ANTES (grep -- padrão (k))

```bash
ls src/intake/ | grep -i audio
ls ~/Desenvolvimento/Protocolo-Mob-Ouroboros/src/components/microfone/ 2>/dev/null
grep -rn "MicrofoneButton\|transcribeStream" ~/Desenvolvimento/Protocolo-Mob-Ouroboros/ 2>/dev/null | head
ls docs/adr/ADR-2*
which whisper 2>/dev/null
which whisper.cpp 2>/dev/null
.venv/bin/python -c "import whisper" 2>&1 || echo "whisper Python nao instalado (OK)"
```

Confirma: (a) sem audio_transcricao.py atual, (b) app tem MicrofoneButton com live transcribe, (c) sem ADR-28, (d) sem whisper local pré-instalado (decisão técnica em aberto).

## Não-objetivos (padrão (t))

- **NÃO** chamar Whisper API externa (viola ADR-13/07).
- **NÃO** instalar whisper.cpp nesta sprint — decisão técnica.
- **NÃO** sobrescrever transcrição live que veio do app — usar como referência canônica primária.
- **NÃO** transcrever áudios pessoais para humilhar; sempre redactar PII se presente (CPF, endereço, telefone).
- **NÃO** misturar áudio + texto extraído no mesmo `.md` — separação clara.

## Spec de implementação

### Schema do `.md` companion

```yaml
---
_schema_version: 1
tipo: audio
data: 2026-05-12
area: outros
subtipo: audio
binario_companion: 2026-05-12-153014-audio.m4a
duracao_seg: 12
transcricao_live: |
  Esta foi a transcricao gerada pelo app no momento da gravacao.
transcricao_backend: |
  Esta sera preenchida quando o motor escolhido (ADR-28) processar.
transcricao_motor: stub | whisper_local | opus_artesanal | pendente
divergencia_app_backend: false
notas: <opcional>
---

# (corpo do .md livre)
```

### CLI stub

```python
# src/intake/audio_transcricao.py
@dataclass
class AudioAterrissado:
    binario_path: Path
    md_companion_path: Path
    transcricao_live: str | None
    duracao_seg: float


def aterrissar(caminho_origem: Path, destino_vault: Path, transcricao_live: str | None = None) -> AudioAterrissado:
    ...


def transcrever(caminho_audio: Path, motor: str = "stub") -> str:
    if motor == "stub":
        return "<transcricao stub -- motor canonico nao escolhido (ADR-28)>"
    if motor == "whisper_local":
        raise NotImplementedError("whisper_local sera implementado em INFRA-TRANSCRICAO-WHISPER-LOCAL")
    if motor == "opus_artesanal":
        raise NotImplementedError("opus_artesanal sera implementado em INFRA-TRANSCRICAO-OPUS")
    raise ValueError(f"motor desconhecido: {motor}")


def validar_transcricao_dual(app: str, backend: str) -> dict:
    """Compara transcricao do app vs backend.

    Returns dict com {peso_divergencia, sugere_revisao_humana}.
    """
    if not app or not backend:
        return {"peso_divergencia": None, "sugere_revisao_humana": True}
    similaridade = razao_levenshtein(app, backend)
    return {
        "peso_divergencia": 1.0 - similaridade,
        "sugere_revisao_humana": similaridade < 0.7,
    }
```

### ADR-28

```markdown
# ADR-28 — Motor canônico para transcrição de áudio backend

## Status
Proposto, 2026-05-12.

## Contexto
App mobile (Onda Q) faz transcrição live no celular via expo-speech. Backend precisa de transcrição secundária para:
- Validar/refinar a transcrição live (especialmente se o áudio é longo).
- Transcrever áudios que chegam por outros canais (ex: cliente envia .m4a via WhatsApp e salva manualmente em `inbox/audio/`).

## Opções

### Opção A — whisper.cpp local (CRNN multilingual offline)
- Prós: offline, ADR-07 compliant, custo zero, mantém soberania.
- Contras: qualidade média em PT-BR coloquial; requer apt install + build local; latência ~30s para áudios de 1min.

### Opção B — Opus multimodal artesanal (Read tool + supervisor)
- Prós: alta qualidade, custo zero (sou interativo), ADR-13 compliant.
- Contras: latência humana (depende de eu estar em sessão); não escala para muitos áudios.

### Opção C — Whisper API externa
- Descartada: viola ADR-07 e ADR-13.

## Decisão
Adotar **Opção B (Opus artesanal) como primária** e **Opção A (whisper local) como fallback** quando supervisor não está em sessão. Implementação real em sprints-filhas:
- INFRA-TRANSCRICAO-OPUS (primária).
- INFRA-TRANSCRICAO-WHISPER-LOCAL (fallback offline).

## Consequências
- Soberania local mantida.
- Custo zero.
- Quando supervisor está ausente, transcrições ficam pendentes (sinalizadas no relatório do audit_vault_md).
```

## Proof-of-work (padrão (u))

```bash
# 1. Aterrissar audio sintetico
.venv/bin/python -c "
from src.intake.audio_transcricao import aterrissar
from pathlib import Path
import shutil
shutil.copy('tests/fixtures/audio/exemplo_curto.m4a', '/tmp/audio_in.m4a')
r = aterrissar(Path('/tmp/audio_in.m4a'), Path('/tmp/vault_audio_teste'), transcricao_live='Hello world')
print(f'binario={r.binario_path}, md={r.md_companion_path}')
"

# 2. Transcrever stub
.venv/bin/python -c "
from src.intake.audio_transcricao import transcrever
print(transcrever(None, motor='stub'))
"

# 3. ADR-28 existe
ls docs/adr/ADR-28-*

# 4. Validar dual
.venv/bin/python -c "
from src.intake.audio_transcricao import validar_transcricao_dual
print(validar_transcricao_dual('hello world', 'hello world'))   # divergencia 0
print(validar_transcricao_dual('hello world', 'goodbye'))       # alta divergencia
"

# 5. Gauntlet
make lint && make smoke
.venv/bin/pytest tests/test_audio_transcricao.py -v
```

## Critério de aceitação (gate (z))

1. `src/intake/audio_transcricao.py` exporta `aterrissar`, `transcrever`, `validar_transcricao_dual`.
2. ADR-28 escrita.
3. Fixture audio + 6 testes mínimos.
4. Stub funcional (raise NotImplementedError nos motores reais).
5. Sprint-filha INFRA-TRANSCRICAO-OPUS aberta em backlog.
6. Sprint-filha INFRA-TRANSCRICAO-WHISPER-LOCAL aberta em backlog.
7. Gauntlet verde.

## Referência

- Auditoria C1 (app): `docs/auditorias/AUDITORIA_APP_MOBILE_2026-05-12.md` linha sobre MicrofoneButton.
- App: `~/Desenvolvimento/Protocolo-Mob-Ouroboros/src/components/microfone/`.
- ADR-13 (supervisor): `docs/adr/ADR-13-supervisor-artesanal-via-claude-code.md`.
- Plano de origem: `~/.claude/plans/preciso-que-use-o-crispy-stroustrup.md` Fase B.

*"Audio sem transcricao e arquivo pesado; transcricao sem audio e texto orfao." — princípio MOB-spec-transcricao-audio*
