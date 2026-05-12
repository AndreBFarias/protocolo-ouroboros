---
id: MOB-bug-camera-momento-repro
titulo: Reproduzir bug "registrar momento" da camera + relatorio para equipe mobile (Onda Q fixou parcialmente)
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-12
fase: BRIDGE_MOBILE
depende_de: []
esforco_estimado_horas: 1
origem: Plano 2026-05-12 secao Fase B; brief do dono pediu "registrar momento" funcionar; auditor C1 confirmou Onda Q (commit MenuCapturaVerde.tsx:217-235) fixou heuristicamente mas validacao live pendente.  <!-- noqa: accent -->
---

# Sprint MOB-bug-camera-momento-repro -- reproduzir e documentar bug "registrar momento"

## Contexto

Brief: "camera escanear documento funciona mas o registrar momento não."

Auditor C1 (2026-05-12) reportou:
- **Status**: FIXADO* (heurístico).
- **Evidência**: `MenuCapturaVerde.tsx:217-235` — setTimeout 120ms + retry 800ms.
- **Validação live pendente**: o fix foi aplicado mas o dono ainda não confirmou no celular real.

Esta sprint **reproduz o bug**, captura evidência, valida o fix e — se ainda falhar — escreve relatório operacional para a sessão mobile.

## Objetivo

1. **Reproduzir** no celular USB conectado (modo dev autorizado pelo dono):
   - Abrir app, navegar para tela `index.tsx` (Home).
   - Tocar botão de captura verde (MenuCapturaVerde).
   - Tentar "registrar momento" 5 vezes em sequência.
   - Capturar comportamento: abre câmera nativa? Trava? Volta para Home sem ação?
2. **Confrontar com fix da Onda Q** (`MenuCapturaVerde.tsx:217-235`):
   - Setup heurístico: `setTimeout(open, 120); setTimeout(retry, 800)`.
   - Em quais condições o fix funciona vs não funciona?
3. **Relatório operacional** `docs/auditorias/BUG_CAMERA_MOMENTO_REPRO_2026-MM-DD.md`:
   - Repro passo-a-passo.
   - Frequência (5/5? 3/5?).
   - Trace do log (via `adb logcat | grep -i ouroboros`).
   - Compatibilidade Android/iOS.
   - Status: CONFIRMA_FIX | FIX_PARCIAL (cita cenário falho) | REGREDIU.
4. Se `FIX_PARCIAL` ou `REGREDIU`: criar spec **para o app mobile** (em outra sessão, outro repo) com hipótese da correção.

## Validação ANTES (grep -- padrão (k))

```bash
adb devices    # confirmar celular USB conectado
grep -n "setTimeout.*120\|registrar.*momento\|MenuCapturaVerde" ~/Desenvolvimento/Protocolo-Mob-Ouroboros/src/components/MenuCapturaVerde.tsx | head -20
git -C ~/Desenvolvimento/Protocolo-Mob-Ouroboros/ log --oneline -20 | head    # confirmar Onda Q
```

Confirma: (a) ADB enxerga celular, (b) fix está no código, (c) repo do app está atualizado.

## Não-objetivos (padrão (t))

- **NÃO** modificar código do app mobile aqui (outro repo, outra sessão).
- **NÃO** persistir log com PII (nomes/endereços/CPFs do conteúdo das memórias capturadas).
- **NÃO** validar outras telas além de Home > MenuCapturaVerde > Registrar Momento.
- **NÃO** assumir que o celular do dono é o canônico — testar em pelo menos 1 device se possível.

## Spec de implementação

### Passo 1 — Setup adb

```bash
adb devices
adb -s <serial> shell pidof com.protocoloouroboros.ouroboros    # ou app id correto
adb logcat -c    # limpar log antigo
adb logcat | grep -i "ouroboros\|MenuCapturaVerde\|camera" > /tmp/logcat_repro.txt &
LOGCAT_PID=$!
```

### Passo 2 — Repro 5 tentativas

Pelo celular ou via `adb shell input tap`:

```bash
# Abrir app
adb shell monkey -p com.protocoloouroboros.ouroboros -c android.intent.category.LAUNCHER 1
sleep 5

# Tap no botao captura verde (precisa coordenadas reais via screencap)
# Tap em "Registrar momento"
# Aguardar e capturar resultado
```

Tirar screenshot a cada tentativa via `adb shell screencap -p > /tmp/repro_$N.png`.

### Passo 3 — Parar log + analisar

```bash
kill $LOGCAT_PID
grep -i "error\|exception\|crash" /tmp/logcat_repro.txt | head -20
```

### Passo 4 — Relatório

```markdown
---
titulo: Bug "registrar momento" -- reproducao 2026-05-12
data: 2026-05-12
auditor: supervisor Opus + dono interativo
escopo: validacao live do fix MenuCapturaVerde Onda Q
status_final: CONFIRMA_FIX | FIX_PARCIAL | REGREDIU
---

# Bug "registrar momento"

## Repro
- Dispositivo: <modelo + Android version>
- App version: <git sha do mobile>
- Cenarios testados: 5 tentativas em sequencia

## Resultado
- Tentativas com sucesso: N/5
- Tentativas com falha: M/5
- Screenshots: /tmp/repro_*.png (anexadas)

## Trace (top 5 linhas relevantes do logcat)
<paste>

## Diagnostico
<se FIX_PARCIAL: cita cenario falho e hipotese da causa raiz>

## Recomendacao
<se OK: arquivar bug com prova>
<se FIX_PARCIAL: criar spec no repo mobile com nome sugerido `mobile-camera-momento-fix-v2`>
```

## Proof-of-work (padrão (u))

```bash
# 1. ADB conectado
adb devices

# 2. Logcat captura algo durante repro
test -s /tmp/logcat_repro.txt && echo "log captured: $(wc -l < /tmp/logcat_repro.txt) linhas"

# 3. Relatorio gerado
ls docs/auditorias/BUG_CAMERA_MOMENTO_REPRO_*.md

# 4. Gauntlet (esta sprint nao modifica codigo backend)
make lint && make smoke
```

## Critério de aceitação (gate (z))

1. ADB enxerga ≥ 1 dispositivo.
2. 5 tentativas de repro executadas e documentadas.
3. Logcat captura ≥ 1 entrada relevante.
4. Relatório markdown em `docs/auditorias/` com status final declarado.
5. Se `FIX_PARCIAL`: spec sugerida para repo do app (não cria neste repo, só sugere).
6. Gauntlet verde (nenhuma alteração no backend).

## Referência

- Auditoria C1: `docs/auditorias/AUDITORIA_APP_MOBILE_2026-05-12.md` linha do FIX heurístico.
- Fix da Onda Q: `~/Desenvolvimento/Protocolo-Mob-Ouroboros/src/components/MenuCapturaVerde.tsx:217-235`.
- Plano de origem: `~/.claude/plans/preciso-que-use-o-crispy-stroustrup.md` Fase B.

*"Repro nao prova o caminho mas elimina suposicao; e o ato mais barato de honestidade tecnica." — princípio MOB-bug-camera-momento-repro*
