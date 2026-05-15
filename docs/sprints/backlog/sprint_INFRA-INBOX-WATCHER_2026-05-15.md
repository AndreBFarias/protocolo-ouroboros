---
id: INFRA-INBOX-WATCHER
titulo: Watcher systemd dispara `./run.sh --inbox` ao detectar arquivos novos
status: backlog
concluida_em: null
prioridade: P2
data_criacao: 2026-05-15
fase: AUTONOMIA
epico: 6
depende_de:
  - INFRA-CONCORRENCIA-PIDFILE (lockfile evita concorrência se dono também rodar)
esforco_estimado_horas: 2
origem: auditoria 2026-05-15. `inbox/` tem 4 arquivos (1 PDF + 3 JPEGs WhatsApp) há 2-3 dias. Sem cron/watcher; sistema espera dono rodar `./run.sh --inbox` manualmente. Falha-soft em design local-first, mas oportunidade real de autonomia.
---

# Sprint INFRA-INBOX-WATCHER

## Contexto

Filosofia prod-ready do roadmap: "dono joga arquivo em `inbox/`, roda `./run.sh --full-cycle`, e tudo aparece classificado sem revisão humana".

O `./run.sh` é manual hoje. Watcher elimina o passo "dono lembra de rodar".

## Hipótese e validação ANTES

H1: nenhum cron/watcher hoje:

```bash
crontab -l 2>/dev/null | grep -i ouroboros
# Esperado: 0 hits

systemctl --user list-units | grep -i ouroboros
# Esperado: 0 hits

ls /home/andrefarias/.config/systemd/user/*ouroboros* 2>/dev/null
# Esperado: 0 hits
```

H2: arquivos pendentes:

```bash
ls inbox/ | wc -l
# Esperado: ≥1 (4 atualmente)

stat -c "%y %n" inbox/* 2>/dev/null | sort | head
# Esperado: timestamps de 2026-05-12/13
```

## Objetivo

1. Criar `infra/systemd/ouroboros-inbox.service`:
   ```
   [Unit]
   Description=Ouroboros inbox watcher
   After=local-fs.target

   [Service]
   Type=simple
   WorkingDirectory=/home/andrefarias/Desenvolvimento/protocolo-ouroboros
   ExecStart=/home/andrefarias/Desenvolvimento/protocolo-ouroboros/scripts/inbox_watcher.sh
   Restart=on-failure
   RestartSec=30

   [Install]
   WantedBy=default.target
   ```
2. Criar `infra/systemd/ouroboros-inbox.path` (path-unit que dispara o service):
   ```
   [Unit]
   Description=Watch inbox/ for new files

   [Path]
   PathChanged=/home/andrefarias/Desenvolvimento/protocolo-ouroboros/inbox
   Unit=ouroboros-inbox.service

   [Install]
   WantedBy=paths.target
   ```
3. Criar `scripts/inbox_watcher.sh`:
   - Debounce: aguarda 60s após última mudança (evita disparar em copy parcial).
   - Verifica lockfile (Sprint INFRA-CONCORRENCIA-PIDFILE): se outro pipeline está rodando, espera ou skip.
   - Roda `./run.sh --inbox`.
   - Log estruturado em `logs/inbox_watcher.log`.
4. Criar `scripts/install_inbox_watcher.sh` que:
   - Copia .service e .path para `~/.config/systemd/user/`
   - Roda `systemctl --user daemon-reload`
   - `systemctl --user enable --now ouroboros-inbox.path`
   - Mostra status.
5. Adicionar `make inbox-watcher-install` no Makefile.

## Não-objetivos

- Não rodar `./run.sh --tudo` (só `--inbox`, leve).
- Não criar dependência de systemd — fallback cron documentado no README.
- Não rodar em background contínuo (path-unit é o trigger).

## Proof-of-work runtime-real

```bash
# 1. Instalar watcher
make inbox-watcher-install
systemctl --user status ouroboros-inbox.path
# Esperado: active (waiting)

# 2. Trigger
touch inbox/teste_watcher.tmp
sleep 90  # debounce + execução
tail logs/inbox_watcher.log
# Esperado: linha "inbox_processed" recente

# 3. Cleanup teste
rm inbox/teste_watcher.tmp

# 4. Desinstalar
systemctl --user disable --now ouroboros-inbox.path
```

## Acceptance

- 2 unit files systemd criados.
- Script install funciona idempotente.
- Watcher dispara após debounce 60s.
- Lockfile respeitado (não roda em paralelo).
- README documenta como instalar + alternativa cron.
- Pytest > 3019. Smoke 10/10. Lint exit 0.

## Padrões aplicáveis

- (n) Defesa em camadas — debounce + lockfile + restart on failure.
- (f) Paths via Path Python (não bash hardcoded).

---

*"Pipeline que espera ordem humana é pipeline meio-mecanizado; pipeline que se dispara é pipeline pronto." — princípio da autonomia local*
