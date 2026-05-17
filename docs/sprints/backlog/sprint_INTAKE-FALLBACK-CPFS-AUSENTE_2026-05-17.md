---
id: INTAKE-FALLBACK-CPFS-AUSENTE
titulo: "`pessoa_detector` falha silenciosamente se `mappings/cpfs_pessoas.yaml` ausente"
status: backlog
concluida_em: null
prioridade: P1
data_criacao: 2026-05-17
fase: ROBUSTEZ
epico: 2
depende_de: []
esforco_estimado_horas: 1
origem: "auditoria independente 2026-05-17. `mappings/cpfs_pessoas.yaml.example` existe (trackeado) mas o real `cpfs_pessoas.yaml` é gitignored. Se em clone novo dono esquece de criar, `pessoa_detector.py` carrega dict vazio e tudo cai em fallback 'casal'. Sem log de erro, sem aviso. Roteamento por CPF deixa de funcionar."
---

# Sprint INTAKE-FALLBACK-CPFS-AUSENTE

## Contexto

`src/intake/pessoa_detector.py` carrega `mappings/cpfs_pessoas.yaml` para discriminar documentos por CPF (André vs Vitória vs casal).

Cenário de falha silenciosa:
1. Clone novo do repo.
2. Dono não cria `cpfs_pessoas.yaml` (gitignored).
3. Pipeline rodando: detector retorna fallback `casal` para tudo.
4. Sem aviso. Sem log de erro.

Resultado: documentos do André misturam com docs da Vitória, classificação por pessoa quebra silenciosamente.

## Hipótese e validação ANTES

```bash
ls -la mappings/cpfs_pessoas.yaml*
# Esperado: .example trackeado, .yaml gitignored

grep -A 5 "cpfs_pessoas" src/intake/pessoa_detector.py | head -10
# Verificar fallback atual
```

## Objetivo

1. **Detecção de ausência** em `pessoa_detector.py`:
   ```python
   PATH_CPFS = _RAIZ / "mappings" / "cpfs_pessoas.yaml"
   PATH_CPFS_EXAMPLE = _RAIZ / "mappings" / "cpfs_pessoas.yaml.example"

   def _carregar_cpfs():
       if not PATH_CPFS.exists():
           if PATH_CPFS_EXAMPLE.exists():
               logger.error(
                   "AVISO: mappings/cpfs_pessoas.yaml NAO existe. "
                   "Use mappings/cpfs_pessoas.yaml.example como template. "
                   "Roteamento por pessoa ESTA DESABILITADO (tudo cai em 'casal')."
               )
           else:
               logger.warning(
                   "mappings/cpfs_pessoas.yaml.example tambem nao existe. "
                   "Estado anomalo."
               )
           return {}
       return yaml.safe_load(PATH_CPFS.read_text(encoding="utf-8")) or {}
   ```

2. **Smoke check em `make smoke`** ou `./run.sh --check`:
   ```bash
   # Adicionar contrato:
   if [ ! -f mappings/cpfs_pessoas.yaml ]; then
       echo "[SMOKE-AVISO] cpfs_pessoas.yaml ausente — roteamento por pessoa desabilitado"
   fi
   ```

3. **Dashboard alerta** opcional: badge no cluster Sistema se YAML ausente.

4. **Testes regressivos**:
   - `test_carregar_cpfs_yaml_ausente_loga_error`
   - `test_pessoa_detector_fallback_casal_quando_yaml_ausente`

## Não-objetivos

- Não criar `cpfs_pessoas.yaml` (PII — dono cria localmente).
- Não tocar lógica de detecção quando YAML existe (só fallback).
- Não criar mecanismo de prompt interativo (CLI não pede input).

## Proof-of-work runtime-real

```bash
# Backup do real (se existir):
mv mappings/cpfs_pessoas.yaml /tmp/cpfs_backup.yaml 2>/dev/null || true

# Rodar detector:
.venv/bin/python -c "
from src.intake.pessoa_detector import detectar_pessoa
r = detectar_pessoa({'cnpj_emitente': '123', 'razao_social': 'X'})
print(r)
"
# Esperado: log de ERROR mencionando YAML ausente

# Restaurar:
mv /tmp/cpfs_backup.yaml mappings/cpfs_pessoas.yaml 2>/dev/null
```

## Acceptance

- `_carregar_cpfs` loga ERROR se YAML ausente.
- Smoke check inclui aviso.
- 2 testes regressivos verdes.
- Documentação `BOOTSTRAP.md` menciona criação de `cpfs_pessoas.yaml`.

## Padrões aplicáveis

- (n) Defesa em camadas — log + smoke + dashboard.
- (e) PII never in INFO — não logar CPFs reais.

---

*"Falha silenciosa é o pior tipo de bug." — princípio do erro visível*
