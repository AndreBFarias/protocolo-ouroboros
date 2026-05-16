# MANUAL_INBOX_WATCHER

Guia de operação do watcher de `inbox/` (Sprint `INFRA-INBOX-WATCHER`, 2026-05-15).

## O que é

Sistema que dispara `./run.sh --inbox` automaticamente quando arquivos novos chegam em `inbox/`. Implementado com **systemd path-unit** (modo usuário, sem precisar de root).

Componentes:

| Arquivo | Função |
|---|---|
| `infra/systemd/ouroboros-inbox.service` | Unit de execução (chama o script). |
| `infra/systemd/ouroboros-inbox.path` | Unit de observação (dispara o service quando `inbox/` muda). |
| `scripts/inbox_watcher.sh` | Script de execução (debounce + lockfile + run.sh). |
| `scripts/install_inbox_watcher.sh` | Instala/desinstala as units. |

## Filosofia

Pipeline que espera ordem humana é pipeline meio-mecanizado. Esta sprint elimina o passo "dono lembra de rodar `./run.sh --inbox`". Quando algo é depositado em `inbox/`, em 60 segundos o pipeline ETL é disparado sozinho.

## Instalação

Você precisa de uma distro Linux com systemd (Ubuntu, Pop!\_OS, Fedora, Arch — qualquer um). O modo "usuário" não precisa de senha.

```bash
make inbox-watcher-install
```

Ou diretamente:

```bash
./scripts/install_inbox_watcher.sh
```

O script:

1. Copia os 2 unit files para `~/.config/systemd/user/`.
2. Roda `systemctl --user daemon-reload`.
3. Garante que `scripts/inbox_watcher.sh` é executável.
4. Habilita e inicia `ouroboros-inbox.path`.
5. Mostra o status.

### Dry-run (recomendado na primeira vez)

```bash
./scripts/install_inbox_watcher.sh --dry-run
```

Mostra o plano sem aplicar.

## Verificação

```bash
make inbox-watcher-status
# ou
systemctl --user status ouroboros-inbox.path
```

Esperado: `active (waiting)`.

Teste rápido (não em produção):

```bash
touch inbox/teste_watcher.tmp
sleep 90   # 60s debounce + processamento
tail logs/inbox_watcher.log
# linha "inbox_processed exit_code=0"
rm inbox/teste_watcher.tmp
```

## Debounce e lockfile

- **Debounce 60s**: depois de detectar mudança, aguarda 60s. Se durante a espera outro arquivo chegar (mtime mudou), aborta o ciclo — o próximo path-change re-dispara. Evita processar `copy` parcial.
- **Lockfile**: se `data/.ouroboros.lock` existe (porque `./run.sh --tudo` está rodando manualmente), watcher faz skip. Convive com a Sprint INFRA-CONCORRENCIA-PIDFILE.

Variáveis de ambiente (opcionais):

| Var | Default | Função |
|---|---|---|
| `OUROBOROS_RAIZ` | `/home/andrefarias/Desenvolvimento/protocolo-ouroboros` | Raiz do projeto. |
| `INBOX_WATCHER_DEBOUNCE` | `60` | Segundos de debounce. |
| `OUROBOROS_LOCKFILE` | `<raiz>/data/.ouroboros.lock` | Lockfile a respeitar. |

Edite `~/.config/systemd/user/ouroboros-inbox.service` se precisar customizar (`Environment="VAR=valor"`).

## Logs

`logs/inbox_watcher.log` — todas as decisões do watcher (linha por evento, formato `ISO-8601 [NIVEL] inbox_watcher: chave=valor`).

```bash
tail -f logs/inbox_watcher.log
```

## Desinstalação

```bash
make inbox-watcher-uninstall
# ou
./scripts/install_inbox_watcher.sh --uninstall
```

Para de observar `inbox/` e remove os unit files.

## Fallback cron (sem systemd)

Se você não tem systemd usuário disponível (raríssimo em distros modernas), use cron como alternativa simples:

```cron
# Roda a cada 5 minutos, processa inbox se houver algo.
*/5 * * * * cd /home/andrefarias/Desenvolvimento/protocolo-ouroboros && /home/andrefarias/Desenvolvimento/protocolo-ouroboros/scripts/inbox_watcher.sh >> /home/andrefarias/Desenvolvimento/protocolo-ouroboros/logs/inbox_watcher.log 2>&1
```

Diferenças:
- Cron polleia (~5 min); systemd path-unit reage em segundos.
- Cron não respeita debounce de 60s do watcher (o próprio script o aplica).
- Tradeoff: mais latência, mais simples.

Para registrar:

```bash
crontab -e   # adicione a linha acima
crontab -l   # confirme
```

## Diagnóstico

| Sintoma | Investigar |
|---|---|
| `systemctl --user status` mostra `failed` | `journalctl --user -u ouroboros-inbox.service -n 50` |
| Watcher dispara mas pipeline não roda | `tail logs/inbox_watcher.log` — procure `inbox_falha` ou `lockfile_ativo`. |
| Arquivo chegou mas nada acontece | Verifique `PathChanged=` aponta para `/home/andrefarias/Desenvolvimento/protocolo-ouroboros/inbox`. |
| Disparo em cópia parcial (arquivo grande sendo escrito) | Debounce padrão 60s já cobre. Aumente via `INBOX_WATCHER_DEBOUNCE=120`. |

## Testes

`tests/test_inbox_watcher.py` cobre estrutura + comportamento via `--dry-run`. Roda com pytest comum:

```bash
make test
# ou
.venv/bin/python -m pytest tests/test_inbox_watcher.py -v
```

---

*"Pipeline que espera ordem humana é pipeline meio-mecanizado; pipeline que se dispara é pipeline pronto." — princípio da autonomia local*
