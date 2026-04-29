---
concluida_em: 2026-04-21
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 47a
  title: "Extrator de Receita Médica e Prescrição"
  touches:
    - path: src/extractors/receita_medica.py
      reason: "parser receita (foto/PDF): médico (CRM), paciente, medicamentos, posologia, validade"
    - path: mappings/medicamentos_dedutiveis.yaml
      reason: "medicamentos de uso contínuo que entram como dedutíveis IRPF (com aval médico)"
    - path: src/pipeline.py
      reason: "registra extrator"
  n_to_n_pairs:
    - [src/extractors/receita_medica.py, src/transform/irpf_tagger.py]
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_receita_medica.py -x -q"
      timeout: 60
  acceptance_criteria:
    - "Extrai CRM, médico, paciente, >= 1 medicamento com posologia"
    - "Nó Prescricao no grafo com aresta prescreve para nodes Item (medicamento)"
    - "Quando transação de farmácia casa com medicamento prescrito, aresta prescreve_cobre é criada (auditor humano valida)"
    - "Receita médica com mais de 6 meses gera aviso (validade normalmente expirada)"
    - "Acentuação PT-BR correta"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 47a -- Extrator de Receita Médica e Prescrição

**Status:** CONCLUÍDA
**Data:** 2026-04-19
**Prioridade:** MEDIA
**Tipo:** Feature
**Dependências:** Sprint 41, 42, 45 (OCR), 48 (linking)
**Desbloqueia:** Dedutível médico IRPF com base documental; controle de medicação
**Issue:** --
**ADR:** ADR-14

---

## Como Executar

- `./run.sh --tudo`
- `.venv/bin/pytest tests/test_receita_medica.py`

### O que NÃO fazer

- NÃO sugerir substituição de medicamento -- só registra
- NÃO extrair dados do paciente além do nome (evitar dados sensíveis desnecessários)
- NÃO expor receita em dashboard (Sprint 51 decide permissão)

---

## Problema

Receitas médicas são:
- Comprovante necessário para dedução IRPF (despesas médicas)
- Fonte de informação sobre uso contínuo de medicamento (previsibilidade de gastos)
- Documento que chega em foto (celular no consultório) ou PDF (telemedicina)

Sem extrator, não há como associar um gasto em farmácia a uma prescrição real -- perde-se tanto o benefício fiscal quanto a análise de saúde.

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| OCR comum | `src/extractors/_ocr_comum.py` | Normalização de imagem e tesseract |
| IRPF tagger | `src/transform/irpf_tagger.py` | Tag `dedutivel_medico` já existe para contas de consulta |
| Grafo extensível | `src/graph/models.py` | Tipo `prescricao` previsto em ADR-14 |

## Implementação

### Fase 1: parser de receita

`_parse_receita(texto: str) -> dict`:

Regex específicas:
- CRM: `CRM[\s-]*([A-Z]{2})?[\s-]*(\d+)` (ex: `CRM/SP 123456`)
- Médico: linha com "Dr.", "Dra.", "Prof." ou nome antes do CRM
- Paciente: linha com "Paciente:" ou após CPF
- Medicamentos: regex por padrão "Nome DosageForm Dose" + "TOMAR X COMPRIMIDOS DE Y EM Y HORAS POR Z DIAS"

Retorna:
```python
{
    "medico": {"nome": str, "crm": str, "especialidade": Optional[str]},
    "paciente": {"nome": str},
    "data_emissao": date,
    "validade_meses": int,  # default 6 se não declarado
    "medicamentos": [
        {
            "nome": str,
            "dosagem": str,      # "500mg"
            "forma": str,        # "comprimido revestido"
            "posologia": str,    # "1 comp 12/12h por 7 dias"
            "continuo": bool,
        }
    ]
}
```

### Fase 2: grafo

- Node `prescricao` (nome_canonico = id único derivado de data + médico)
- Node `pessoa_medico` (nome_canonico = CRM) -- tipo novo
- Arestas:
  - `prescricao` → `pessoa_medico` (emitida_por)
  - `prescricao` → `item` (medicamento) (prescreve) - item criado na Sprint 48 após linking com farmácia
- Se `medicamento.continuo == True`, adicionar tag em `mappings/medicamentos_dedutiveis.yaml`

### Fase 3: linking com farmácia

Heurística em Sprint 48:
- Quando extrator DANFE/cupom identifica medicamento com nome similar a prescrito, aresta `prescreve_cobre(prescricao → item, peso=similaridade)`
- Threshold alto (>= 90) é automático; entre 70-90 vira proposta para supervisor

### Fase 4: testes

Fixtures anonimizadas (receitas com dados fictícios em `tests/fixtures/receitas/`):
- `receita_uso_continuo.jpg`
- `receita_antibiotico.pdf`

Testes:
- `test_extrai_crm_medico`
- `test_extrai_medicamento_com_posologia`
- `test_receita_expirada_gera_aviso`

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A47a-1 | Receita manuscrita é OCR ruim | Sempre registrar confidence e usar fallback supervisor |
| A47a-2 | Nome comercial vs princípio ativo (Tylenol vs Paracetamol) | Mappings/medicamentos_dedutiveis.yaml unifica via aliases |
| A47a-3 | Dados sensíveis do paciente -- LGPD implícita | Guardar só o nome; nunca CPF, diagnóstico, CID |
| A47a-4 | Receita de controle especial (retinoada) tem validade de 30 dias | Regex específica para tarja preta/vermelha altera `validade_meses` |
| A47a-5 | "Uso contínuo" é flag que muda a dedução IRPF | Regex explícito para "USO CONTÍNUO" na receita |

## Evidências Obrigatórias

- [ ] `make lint` passa
- [ ] 2 fixtures extraídas com CRM, médico, pelo menos 1 medicamento
- [ ] Grafo contém `prescricao` + `pessoa_medico`
- [ ] Receita expirada gera aviso no log

## Verificação end-to-end

```bash
cp tests/fixtures/receitas/*.* data/raw/andre/saude/receitas/
./run.sh --tudo
sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM node WHERE tipo='prescricao';"
```

## Conferência Artesanal Opus

**Arquivos originais a ler:** cada receita em `data/raw/andre/saude/receitas/`.

**Checklist:**

1. CRM lido bate com a receita?
2. Medicamentos prescritos são listados corretamente com dosagem e posologia?
3. Prescrição "uso contínuo" foi marcada?
4. Validade está no grafo e alerta aciona se vencida?

**Relatório em `docs/propostas/sprint_47a_conferencia.md`**: medicamentos que precisam entrar no `mappings/medicamentos_dedutiveis.yaml`.

**Critério**: 2 receitas diferentes processadas sem perda dos medicamentos; prescrição vinculada a médico.

---

*"A receita é palavra do médico em papel -- honra quem lê." -- princípio do paciente*
