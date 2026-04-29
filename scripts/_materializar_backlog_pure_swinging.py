"""Gerador one-shot das specs do plan pure-swinging-mitten em backlog/.

Sprint ANTI-MIGUE-* da Onda 1 já implementadas em sessão (03, 04, 07, 02);
outras ondas materializadas como specs formais para execução futura
(modo 3 do COMO_AGIR.md). Cada spec é um contrato anti-migué:
problema + hipótese + implementação + proof-of-work + acceptance.

Uso: python scripts/_materializar_backlog_pure_swinging.py
Idempotente: regrava se executado novamente.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BACKLOG = RAIZ / "docs" / "sprints" / "backlog"


SPECS: list[dict] = [
    # ---------- ONDA 0 (blueprint + CI fix — vem antes de tudo) ----------
    {
        "id": "CI-01",
        "slug": "corrigir_ci_workflow",
        "titulo": "Corrigir CI: pytest com fallback silencioso + falta smoke + falta acentuação",
        "prio": "P0",
        "onda": 0,
        "esf": "1h",
        "dep": [],
        "fecha_itens": ["achado da auditoria visual+devops 2026-04-29"],
        "problema": (
            ".github/workflows/ci.yml tem 3 problemas críticos:\n"
            "1. `pytest tests/ -v --tb=short || echo 'Nenhum teste'` — o `||` "
            "MASCARA falha. CI nunca falha por causa de teste vermelho.\n"
            "2. Não roda `make smoke` (10 contratos aritméticos).\n"
            "3. Não roda `scripts/check_acentuacao.py` (regra inviolável #1).\n"
            "Resultado: CI verde dá falsa segurança. Sprint 55 (1.761 tx "
            "classificadas erradas) passou direto pelo CI antigo."
        ),
        "hipotese": (
            "Remover `||` do passo de pytest. Adicionar steps para `make smoke` "
            "e `python scripts/check_acentuacao.py --all`. CI passa a falhar de "
            "verdade quando regressão é introduzida."
        ),
        "implementacao": (
            "1. Editar .github/workflows/ci.yml: trocar pytest por linha sem `||`.\n"
            "2. Adicionar step 'Smoke aritmético': `make smoke` (precisa do XLSX, "
            "rodar `make process` com fixture sintética antes OU pular se não "
            "houver XLSX e marcar como warning).\n"
            "3. Adicionar step 'Acentuação PT-BR': "
            "`python scripts/check_acentuacao.py --all`.\n"
            "4. Adicionar status badge no README."
        ),
        "proof": (
            "Forçar PR com teste falhando → CI vermelho. "
            "Forçar PR com 'funcao' sem acento → CI vermelho."
        ),
        "acceptance": [
            "ci.yml sem `||` em pytest.",
            "Step de smoke + acentuação.",
            "Badge no README.",
            "PR de teste forçado falha o CI.",
        ],
    },
    # ---------- ONDA 0 (blueprint de design — vem antes de tudo) ----------
    {
        "id": "DESIGN-01",
        "slug": "blueprint_outputs_relacionamentos",
        "titulo": "Blueprint: outputs esperados + docs esperados + relacionamentos + aparência de relatórios",  # noqa: E501
        "prio": "P0",
        "onda": 0,
        "esf": "6h",
        "dep": [],
        "fecha_itens": ["item AA da revisão 2026-04-29 (visão do dono)"],
        "problema": (
            "Antes de codar Onda 3-6, falta consolidar a visão de outputs em "
            "documento único: quais relatórios o sistema gera, quais documentos "
            "espera receber por pessoa, qual a aparência canônica de cada "
            "relatório, quais relações entre dados são primárias vs derivadas. "
            "Sem esse blueprint, cada sprint executa palpite isolado e a "
            "central de vida adulta vira agregado sem cara."
        ),
        "hipotese": (
            "Documento `docs/BLUEPRINT_VIDA_ADULTA.md` declarativo cobrindo: "
            "(1) catálogo de tipos de documento esperados por pessoa por domínio "
            "(financeiro, identidade, saúde, profissional, acadêmico); "
            "(2) outputs canônicos do dashboard (XLSX, JSON cache, ZIP IRPF, "
            "ZIP pacote anual de vida); (3) relacionamentos entre nodes do grafo "
            "com diagrama; (4) aparência de cada relatório (mockup ASCII ou "
            "wireframe link); (5) gaps de cobertura aceitáveis vs inaceitáveis."
        ),
        "implementacao": (
            "1. Criar `docs/BLUEPRINT_VIDA_ADULTA.md` (~400 linhas, 5 seções).\n"
            "2. Mockup ASCII das 5 telas-âncora dos 5 clusters do dashboard.\n"
            "3. Diagrama de classes do grafo (mermaid ou ASCII).\n"
            "4. Tabela tipos esperados × pessoa × domínio × prioridade.\n"
            "5. Sprints existentes ganham referência cruzada para o blueprint."
        ),
        "proof": (
            "Documento publicado e linkado de CLAUDE.md + SPRINTS_INDEX.md. "
            "Cada sprint da Onda 3-6 cita seção do blueprint que endereça."
        ),
        "acceptance": [
            "BLUEPRINT publicado.",
            "5 mockups ASCII das telas-âncora.",
            "Tabela cobertura tipos × pessoa × domínio.",
            "Referência cruzada nas sprints DOC-* e OMEGA-*.",
        ],
    },
    # ---------- ONDA 1 (anti-migué + restaurar débitos) ----------
    {
        "id": "ANTI-MIGUE-01",
        "slug": "gate_4way_conformance",
        "titulo": "Gate 4-way conformance ≥3 amostras",
        "prio": "P0",
        "onda": 1,
        "esf": "4h",
        "dep": [],
        "fecha_itens": ["fundação para Onda 3"],
        "problema": (
            "Tipos novos de documento entram em produção sem prova empírica de que "
            "ETL × Opus × Grafo × Humano concordam. Sprint pode declarar 'concluída' "
            "sem ter validado em amostras reais."
        ),
        "hipotese": (
            "Implementar `tests/conformance/4way_gate.py` que recebe `tipo` e exige "
            "≥3 amostras com 4 dimensões batendo (output ETL, transcrição Opus, "
            "node no grafo, marcação humana). Comando `make conformance-<tipo>` "
            "fica obrigatório antes de mover spec de extrator de backlog para "
            "concluidos."
        ),
        "implementacao": (
            "1. Tabela `conformance_amostras` em SQLite (tipo, item_id, etl_ok, "
            "opus_ok, grafo_ok, humano_ok, ts).\n"
            "2. CLI `python -m tests.conformance.4way_gate <tipo>` retorna exit 0 "
            "se ≥3 linhas verdes; exit 1 caso contrário.\n"
            "3. `make conformance-<tipo>` integra ao Makefile.\n"
            "4. `scripts/check_anti_migue.sh` chama o gate ao tentar mover spec de "
            "extrator para concluidos."
        ),
        "proof": (
            "Para tipo 'cnh' (que ainda não existe), comando deve retornar exit 1 "
            "com mensagem 'apenas N amostras 4-way' onde N<3. Após inserir 3 linhas "
            "verdes, retorna exit 0."
        ),
        "acceptance": [
            "Comando `make conformance-cnh` funciona em runtime real.",
            "Tabela SQLite criada com schema versionado.",
            "5+ testes pytest cobrindo gate liberado, gate negado, gate com 1 dimensão falha.",
            "Linha em VALIDATOR_BRIEF.md rodapé descrevendo o gate.",
        ],
    },
    {
        "id": "ANTI-MIGUE-05",
        "slug": "fechar_87d_uuid_para_hash",
        "titulo": "Fechar Sprint 87d: UUID → hash determinístico em fallback supervisor cupom",
        "prio": "P1",
        "onda": 1,
        "esf": "2h",
        "dep": [],
        "fecha_itens": ["item 35 da auditoria honesta"],
        "problema": (
            "Sprint 87d ficou com UUID aleatório no fallback supervisor de cupom "
            "(docs/propostas/extracao_cupom/), gerando 6 propostas órfãs por rodada."
        ),
        "hipotese": (
            "Trocar `uuid4()` por `sha256(arquivo+tipo+data)[:16]` no nome do "
            "arquivo de proposta. Idempotência garantida: mesma entrada = mesmo "
            "arquivo, em vez de duplicata por execução."
        ),
        "implementacao": (
            "1. Localizar gerador em src/intake/extractors_envelope.py ou módulo "
            "correlato.\n"
            "2. Substituir uuid por hash determinístico.\n"
            "3. Limpar 6 propostas órfãs antes do merge.\n"
            "4. Teste regressivo: 2 execuções consecutivas → 1 arquivo, não 2."
        ),
        "proof": "ls docs/propostas/extracao_cupom/ | wc -l antes/depois.",
        "acceptance": [
            "0 duplicatas após 2 execuções consecutivas com mesmo input.",
            "Teste regressivo cobrindo idempotência.",
            "6 órfãos pré-existentes removidos.",
        ],
    },
    {
        "id": "ANTI-MIGUE-06",
        "slug": "ramificar_sprint_87_em_10_filhas",
        "titulo": "Ramificar Sprint 87 (10 sub-tasks abertas) em sprints-filhas formais",
        "prio": "P1",
        "onda": 1,
        "esf": "6h",
        "dep": [],
        "fecha_itens": ["itens 11 e 34 da auditoria honesta"],
        "problema": (
            "Sprint 87 declarada concluída deixou 10 dependências abertas: boleto_pdf "
            "novo extrator, MOC mensal, reconciliação boleto↔transação, drill-down "
            "em mais plots, regras YAML para IRPF/DAS/CPF, backfill arquivo_original, "
            "reconciliação via grafo, legenda_abaixo em 4 plots, etc."
        ),
        "hipotese": (
            "Cada sub-task vira spec dedicada em backlog/ com prio + esforço + "
            "acceptance próprios. Spec mãe (Sprint 87) ganha link para as 10 "
            "filhas no frontmatter."
        ),
        "implementacao": (
            "Criar 10 specs sprint_87_1*.md a sprint_87_10*.md em backlog/, cada "
            "uma com mínimo 30 linhas (problema + hipótese + acceptance)."
        ),
        "proof": "ls docs/sprints/backlog/ | grep -c 'sprint_87_' deve retornar 10.",
        "acceptance": [
            "10 sprints-filhas formais em backlog/.",
            "Spec original anota 'concluida_em: <data>' e link para filhas.",
            "Zero TODO solto — cada item tem ID rastreável.",
        ],
    },
    {
        "id": "ANTI-MIGUE-08",
        "slug": "refatorar_arquivos_acima_800_linhas",
        "titulo": "Refatorar 4 arquivos > 800 linhas (CLAUDE.md §convenções)",
        "prio": "P2",
        "onda": 1,
        "esf": "8h",
        "dep": [],
        "fecha_itens": ["item 40 da auditoria honesta"],
        "problema": (
            "Quatro arquivos violam o limite de 800 linhas: tema.py (1.191), "
            "ingestor_documento.py (940), revisor.py (888), dados.py (830). "
            "Arquivos grandes degradam manutenibilidade."
        ),
        "hipotese": (
            "Cada arquivo tem responsabilidades extraíveis: tema.py → "
            "tokens/helpers/icones; ingestor → ingestor_doc/ingestor_item/"
            "ingestor_metadata; revisor → revisor_dimensoes/revisor_render/"
            "revisor_export; dados → dados/dados_revisor."
        ),
        "implementacao": (
            "1 arquivo por sub-sprint (4 sub-sprints). Cada uma: extrair módulo, "
            "atualizar imports, garantir testes verdes, garantir lint verde."
        ),
        "proof": "wc -l src/dashboard/tema.py etc. — todos < 800.",
        "acceptance": [
            "0 arquivos > 800 linhas em src/.",
            "Pytest baseline mantido.",
            "Lint exit 0.",
        ],
    },
    {
        "id": "ANTI-MIGUE-09",
        "slug": "teste_idempotencia_reextrair_tudo",
        "titulo": "Teste de idempotência para `--reextrair-tudo`",
        "prio": "P2",
        "onda": 1,
        "esf": "3h",
        "dep": [],
        "fecha_itens": ["item 38 da auditoria honesta"],
        "problema": (
            "`./run.sh --reextrair-tudo` é destrutivo (limpa nodes documento) mas "
            "não tem teste de idempotência. Se rodar 2x seguidas, grafo deveria "
            "convergir; sem teste, é assumido."
        ),
        "hipotese": (
            "Teste sintético com fixtures conhecidas: rodar reextração 2x e "
            "comparar contagem de nodes/edges. Tolerância 0 (idempotente)."
        ),
        "implementacao": (
            "tests/test_run_sh_idempotente.py com fixture mínima (1 PDF DAS, "
            "1 holerite). Rodar reextração via subprocess 2x, comparar counts."
        ),
        "proof": "Teste passa em ambiente CI limpo.",
        "acceptance": ["Teste regressivo no pytest baseline."],
    },
    {
        "id": "ANTI-MIGUE-10",
        "slug": "docs_bootstrap",
        "titulo": "Documentar bootstrap em install.sh + docs/BOOTSTRAP.md",
        "prio": "P3",
        "onda": 1,
        "esf": "1h",
        "dep": [],
        "fecha_itens": ["item 41 da auditoria honesta"],
        "problema": (
            "Hooks git são locais; em fresh clone, dependem de install.sh. Sem "
            "documentação clara, novo usuário/sessão pode pular setup e quebrar "
            "validações."
        ),
        "hipotese": (
            "Criar docs/BOOTSTRAP.md com passos numerados: clone → install.sh → "
            "verificar hooks → rodar make smoke → rodar pytest. install.sh já "
            "deve copiar hooks para .git/hooks/."
        ),
        "implementacao": (
            "1. Auditar install.sh (verificar se já copia hooks).\n"
            "2. Se não, adicionar bloco de cópia idempotente.\n"
            "3. Criar docs/BOOTSTRAP.md com checklist."
        ),
        "proof": "Em VM/clone limpo: rodar install.sh + git commit malformado → hook bloqueia.",
        "acceptance": [
            "install.sh copia hooks idempotentemente.",
            "docs/BOOTSTRAP.md publicado.",
            "CLAUDE.md §estrutura aponta para BOOTSTRAP.md.",
        ],
    },
    {
        "id": "ANTI-MIGUE-11",
        "slug": "pin_pyvis_lock",
        "titulo": "Pin pyvis<1.0 em pyproject.toml + lock file",
        "prio": "P3",
        "onda": 1,
        "esf": "30min",
        "dep": [],
        "fecha_itens": ["item 42 da auditoria honesta"],
        "problema": (
            "pyvis>=0.3 sem upper-bound. Major release pode quebrar grafo full-page sem warning."
        ),
        "hipotese": "Pinar `pyvis>=0.3,<1.0` + adicionar uv.lock ou requirements-lock.txt.",
        "implementacao": "Editar pyproject.toml + gerar lock + commit.",
        "proof": "pip install --dry-run resolve para versão < 1.0.",
        "acceptance": ["pyproject.toml com upper-bound", "Lock file versionado."],
    },
    {
        "id": "ANTI-MIGUE-12",
        "slug": "frontmatter_concluida_em",
        "titulo": "Frontmatter concluida_em: YYYY-MM-DD em sprints concluídas",
        "prio": "P2",
        "onda": 1,
        "esf": "2h",
        "dep": [],
        "fecha_itens": ["item 46 da auditoria honesta"],
        "problema": (
            "Specs em concluidos/ sem campo de data de conclusão. Auditoria "
            "forense precisa cruzar com git log."
        ),
        "hipotese": (
            "Adicionar campo `concluida_em: YYYY-MM-DD` no frontmatter YAML de "
            "cada spec ao mover para concluidos/. Backfill: ler git log do mv "
            "para inferir data de specs antigas."
        ),
        "implementacao": (
            "1. Script scripts/backfill_concluida_em.py com `git log --diff-filter=A` "
            "para cada spec em concluidos/.\n"
            "2. Padronizar checklist anti-migué a sempre incluir o campo."
        ),
        "proof": "100% das specs em concluidos/ com campo concluida_em.",
        "acceptance": [
            "Backfill aplicado.",
            "Hook ou check_anti_migue.sh valida presença do campo.",
        ],
    },
    # ---------- ONDA 2 (ADR-08 LLM vivo) ----------
    {
        "id": "LLM-01",
        "slug": "infra_anthropic_basica",
        "titulo": "Infraestrutura LLM básica (anthropic SDK + cost_tracker + cache)",
        "prio": "P0",
        "onda": 2,
        "esf": "4h",
        "dep": [],
        "fecha_itens": ["item 29 da auditoria honesta (ADR-08 órfã)"],
        "problema": (
            "ADR-08 aprovada em 2025; zero implementação. src/llm/ não existe, "
            "anthropic não em deps."
        ),
        "hipotese": (
            "Camada mínima: src/llm/__init__.py + supervisor.py (chamada única) + "
            "cost_tracker.py (registra tokens). Cache LRU em-memória + fallback "
            "para SQLite persistente."
        ),
        "implementacao": (
            "1. Adicionar `anthropic>=0.40` em pyproject.toml.\n"
            "2. src/llm/supervisor.py com classe Supervisor + método `chamar()`.\n"
            "3. src/llm/cost_tracker.py com SQLite data/output/llm_costs.sqlite.\n"
            "4. .env-exemplo com ANTHROPIC_API_KEY documentado.\n"
            "5. Cache LRU @ functools.lru_cache em prompts determinísticos."
        ),
        "proof": "supervisor.chamar('teste') retorna resposta + custo registrado em SQLite.",
        "acceptance": [
            "Pasta src/llm/ criada com 3 arquivos.",
            "anthropic em deps + .env-exemplo.",
            "10+ testes cobrindo cache hit, cost tracking, fallback offline.",
        ],
    },
    {
        "id": "LLM-02",
        "slug": "supervisor_propor_extractor",
        "titulo": "Supervisor propõe spec de extractor quando classifier=None",
        "prio": "P1",
        "onda": 2,
        "esf": "6h",
        "dep": ["LLM-01"],
        "fecha_itens": ["item 19 da auditoria (8 documentos sem regra YAML)"],
        "problema": (
            "Quando classifier não reconhece tipo, arquivo cai em _classificar/ "
            "sem disparar nenhuma ação. Resultado: documento órfão silencioso."
        ),
        "hipotese": (
            "Integrar Supervisor no fluxo: ao detectar tipo desconhecido, chamar "
            "LLM com amostra OCR + pedido de spec. Output YAML em "
            "mappings/proposicoes/. Marca arquivo como 'aguardando_extractor' "
            "no relatório anti-órfão."
        ),
        "implementacao": (
            "1. supervisor.propor_extractor(amostra: str) -> SugestaoExtractor.\n"
            "2. Schema Pydantic com tipo, regex_tentativa, campos_a_extrair.\n"
            "3. Output em mappings/proposicoes/YYYY-MM-DD_HHMM_<topico>.yaml.\n"
            "4. Hook em src/intake/registry.py quando classifier retorna None.\n"
            "5. SHA-guard: proposta com mesmo SHA não duplica."
        ),
        "proof": (
            "Subir PDF Amazon (tipo desconhecido) em _classificar/ → após inbox "
            "rodar, mappings/proposicoes/ tem 1 YAML novo com sugestão."
        ),
        "acceptance": [
            "Diretório mappings/proposicoes/ + .gitkeep.",
            "Schema Pydantic versionado.",
            "Hook em registry.py disparado em runtime real.",
            "8+ testes (cache, idempotência, schema válido, fallback offline).",
        ],
    },
    {
        "id": "LLM-03",
        "slug": "supervisor_propor_regra_categoria",
        "titulo": "Supervisor propõe regra de categoria para fornecedor frequente",
        "prio": "P1",
        "onda": 2,
        "esf": "4h",
        "dep": ["LLM-01"],
        "fecha_itens": [],
        "problema": (
            "Fornecedores frequentes que caem em 'Outros' deveriam virar regra. "
            "Hoje requer humano editar mappings/categorias.yaml manualmente."
        ),
        "hipotese": (
            "Após pipeline, supervisor analisa fornecedores em 'Outros' com >=3 "
            "ocorrências e propõe regra YAML em mappings/proposicoes/."
        ),
        "implementacao": (
            "1. Supervisor.propor_regra(fornecedor, ocorrencias) → "
            "SugestaoRegra(regex, categoria, classificacao).\n"
            "2. Hook no relatório mensal: lista propostas pendentes.\n"
            "3. Revisor 4-way ganha aba Proposições com aceitar/rejeitar."
        ),
        "proof": "Após pipeline com ≥3 transações 'Vivendas' em Outros, mappings/proposicoes/ tem regra sugerida.",  # noqa: E501
        "acceptance": [
            "Schema Pydantic SugestaoRegra.",
            "Hook em pipeline ou relatório.",
            "Aba Proposições no Revisor.",
        ],
    },
    {
        "id": "LLM-04",
        "slug": "supervisor_modo_auditor",
        "titulo": "Supervisor Modo 2 (Auditor) — audita N% das classificações",
        "prio": "P2",
        "onda": 2,
        "esf": "6h",
        "dep": ["LLM-01"],
        "fecha_itens": [],
        "problema": (
            "Pipeline determinístico (regex + YAML) classifica 100%, mas pode ter "
            "erros sistemáticos não detectáveis sem amostragem externa."
        ),
        "hipotese": (
            "Auditor lê amostra estratificada (10% por categoria, mín 5 por mês) "
            "e produz relatório de divergências. Gera PR de correção quando "
            "encontra padrão sistemático."
        ),
        "implementacao": (
            "1. supervisor.auditor(amostra, regras_atuais) → AuditoriaClassificacao.\n"
            "2. CLI `python -m src.llm.auditor --mes 2026-04`.\n"
            "3. Relatório data/output/auditoria_classificacao_<mes>.md."
        ),
        "proof": "Rodar auditor em mês com erro conhecido (ex: bug Sprint 55 reproduzido) → reporta divergência.",  # noqa: E501
        "acceptance": ["CLI funcional.", "Relatório gerado.", "Schema versionado."],
    },
    {
        "id": "LLM-05",
        "slug": "revisor_diff_proposicoes",
        "titulo": "UI no Revisor 4-way para aceitar/rejeitar proposições LLM",
        "prio": "P1",
        "onda": 2,
        "esf": "5h",
        "dep": ["LLM-02", "LLM-03"],
        "fecha_itens": [],
        "problema": "Proposições em mappings/proposicoes/ ficam sem revisão visual.",
        "hipotese": (
            "Adicionar aba 'Proposições' no Revisor que lista cada YAML pendente "
            "com botão aceitar/rejeitar/modificar. Aceitar move para mappings/ "
            "definitivo + commit. Rejeitar move para mappings/proposicoes/_rejeitadas/ "
            "com SHA registrado."
        ),
        "implementacao": (
            "src/dashboard/paginas/proposicoes.py + integração com sync_rico para "
            "commit automático ao aceitar."
        ),
        "proof": "Subir proposição manual → aba mostra → aceitar → mappings/categorias.yaml atualizado + git diff visível.",  # noqa: E501
        "acceptance": [
            "Aba live no Revisor.",
            "Fluxo aceitar/rejeitar/modificar funcional.",
            "Commit automático ao aceitar (com confirmação humana).",
        ],
    },
    {
        "id": "LLM-06",
        "slug": "proposicao_sha_guard",
        "titulo": "SHA-guard: proposta rejeitada com mesmo SHA não volta",
        "prio": "P2",
        "onda": 2,
        "esf": "2h",
        "dep": ["LLM-02"],
        "fecha_itens": [],
        "problema": "Sem guard, mesma proposta volta em cada rodada do supervisor.",
        "hipotese": (
            "Tabela `proposicoes_rejeitadas (sha, motivo, ts)`. Antes de gravar "
            "proposta nova, supervisor verifica SHA na tabela."
        ),
        "implementacao": "SQLite simples + lookup pré-gravação.",
        "proof": "Rejeitar proposição → 2ª rodada do supervisor não regenera.",
        "acceptance": ["Tabela criada.", "Teste regressivo de não-duplicação."],
    },
    {
        "id": "AUDITOR-01",
        "slug": "relatório_cobertura_documental_por_pessoa",
        "titulo": "Relatório de cobertura documental por pessoa (Claude lê tudo + fala dos faltantes)",  # noqa: E501
        "prio": "P1",
        "onda": 2,
        "esf": "5h",
        "dep": ["LLM-01", "DESIGN-01"],
        "fecha_itens": ["item N da revisão 2026-04-29 (visão do dono)"],
        "problema": (
            "Visão do dono: 'eu quero que o claude leia cada arquivo atual, fale "
            "dos faltantes, gere os outputs, compare com os dele, veja como "
            "podemos integrar'. Hoje o Revisor 4-way mostra divergência item a "
            "item, mas falta visão agregada por pessoa (André, Vitória) e por "
            "domínio (financeiro, identidade, saúde, profissional, acadêmico) "
            "do que está presente vs faltante."
        ),
        "hipotese": (
            "Comparar `data/raw/<pessoa>/` + nodes do grafo com a tabela do "
            "BLUEPRINT (DESIGN-01) e gerar relatório por pessoa: lista de "
            "tipos esperados × tipos presentes × tipos faltantes. Para cada "
            "faltante, sugerir ação (subir foto, baixar do gov.br, pedir do "
            "RH, etc.). Output em `data/output/cobertura_<pessoa>.md`."
        ),
        "implementacao": (
            "1. `src/analysis/cobertura_documental.py` — função `gerar_relatório_pessoa(pessoa: str)`.\n"  # noqa: E501
            "2. Lê tabela do BLUEPRINT (YAML estruturado, derivado).\n"
            "3. Cruza com nodes do grafo + arquivos físicos.\n"
            "4. Aba 'Cobertura Pessoal' no dashboard com 2 colunas (André × Vitória).\n"
            "5. Encadear em `--full-cycle` para regenerar a cada rodada."
        ),
        "proof": (
            "Para cada pessoa, relatório lista pelo menos 30 tipos esperados "
            "com status presente/faltante/parcial."
        ),
        "acceptance": [
            "Módulo + função.",
            "Relatórios MD em runtime real.",
            "Aba dashboard.",
            "Encadeado em --full-cycle.",
        ],
    },
    {
        "id": "LLM-07",
        "slug": "metricas_autossuficiencia",
        "titulo": "Métricas de autossuficiência (ADR-09) no dashboard",
        "prio": "P2",
        "onda": 2,
        "esf": "3h",
        "dep": ["LLM-01"],
        "fecha_itens": [],
        "problema": (
            "ADR-09 declara que LLM é provisório; métrica-chave é % determinístico. "
            "Sem dashboard, não há controle de evolução."
        ),
        "hipotese": (
            "Calcular % de classificações que vieram só de regex/YAML vs % que "
            "precisaram de LLM. Mostrar tendência mensal."
        ),
        "implementacao": "Página/aba 'Autossuficiência' com line chart.",
        "proof": "Gráfico exibe valor numérico real.",
        "acceptance": ["Aba live.", "% calculado a partir de dados reais."],
    },
    # ---------- ONDA 3 (cobertura documental universal) ----------
    *[
        {
            "id": f"DOC-{i:02d}",
            "slug": slug,
            "titulo": f"Extrator: {nome}",
            "prio": "P1",
            "onda": 3,
            "esf": esf,
            "dep": ["LLM-01", "ANTI-MIGUE-01"],
            "fecha_itens": ["itens 19, 22 da auditoria honesta"],
            "problema": (
                f"{nome} é documento cotidiano sem regra YAML nem extrator. "
                "Cai silenciosamente em _classificar/ ou roteamento-only."
            ),
            "hipotese": (
                "Spec do tipo + regra de classificação + extrator dedicado + "
                "fixtures sintéticas + 3 amostras reais para gate 4-way."
            ),
            "implementacao": (
                f"1. Adicionar tipo em mappings/tipos_documento.yaml.\n"
                f"2. Criar src/extractors/{slug}.py.\n"
                "3. Registrar em src/intake/registry.py.\n"
                "4. Fixture sintética em tests/fixtures/.\n"
                "5. 3 amostras reais validadas no Revisor 4-way."
            ),
            "proof": (f"`make conformance-{slug}` retorna exit 0 (≥3 amostras 4-way verdes)."),
            "acceptance": [
                "Tipo em tipos_documento.yaml.",
                f"Extrator src/extractors/{slug}.py com 8+ testes.",
                "Fixture sintética + 3 amostras reais.",
                "Gate 4-way verde.",
            ],
        }
        for i, (slug, nome, esf) in enumerate(
            [
                ("amazon_pedido", "pedido Amazon (HTML/PDF com itens)", "5h"),
                ("mercado_nf_fisica", "NF de mercado físico (Vivendas e similares)", "5h"),
                ("carteira_estudante", "carteira de estudante (JPEG/PDF + validade)", "3h"),
                ("cnh", "CNH digital (JPEG/PDF + validade + categoria)", "3h"),
                ("rg", "RG digital (JPEG/PDF)", "3h"),
                ("diploma", "diploma (PDF + instituição + curso + ano)", "3h"),
                ("historico_escolar", "histórico escolar (PDF + grade + CR)", "4h"),
                ("certidao_nascimento", "certidão de nascimento", "3h"),
                ("exame_medico", "exame médico (PDF/foto + paciente + médico + parâmetros)", "5h"),
                ("receita_medica_v2", "receita médica registry-driven (refator)", "3h"),
                ("plano_saude_carteirinha", "carteirinha de plano de saúde + ANS", "3h"),
                ("govbr_pdf", "PDF emitido pelo gov.br (auto-detect)", "4h"),
            ],
            start=1,
        )
    ],
    {
        "id": "DOC-13",
        "slug": "multi_foto_selector",
        "titulo": "Multi-foto: escolher melhor entre N fotos do mesmo documento",
        "prio": "P0",
        "onda": 3,
        "esf": "4h",
        "dep": [],
        "fecha_itens": ["item 20 da auditoria (P0 duplicação garantida)"],
        "problema": ("Usuário tira 3 fotos da mesma NF; OCR extrai 3x e cria 3 transações."),
        "hipotese": (
            "Heurística: para cada grupo de fotos com timestamp próximo (±5min) "
            "+ similaridade phash, calcular score (nitidez Laplaciana + OCR "
            "confidence + % de texto). Escolher a de maior score."
        ),
        "implementacao": (
            "src/intake/multi_foto_selector.py com função "
            "`escolher_melhor(fotos: list[Path]) -> Path`. Integrar em "
            "inbox_processor antes do OCR."
        ),
        "proof": "Subir 3 fotos da mesma NF → pipeline cria 1 transação, não 3.",
        "acceptance": [
            "Função pura testável.",
            "8+ testes (1 foto, 3 fotos similares, 2 docs diferentes).",
            "Hook em inbox_processor.",
        ],
    },
    {
        "id": "DOC-14",
        "slug": "anti_duplicacao_semantica",
        "titulo": "Anti-duplicação semântica em data/raw/<pessoa>/<banco>/",
        "prio": "P2",
        "onda": 3,
        "esf": "3h",
        "dep": [],
        "fecha_itens": ["item 25 da auditoria"],
        "problema": (
            "dedup_classificar varre só _classificar/. Arquivo duplicado em "
            "data/raw/andre/itau_cc/ não é detectado."
        ),
        "hipotese": (
            "Estender varredura para data/raw/<pessoa>/<banco>/ com chave "
            "(tipo, pessoa, data_emissao, valor_total). Variantes de mesmo "
            "extrato são detectadas via similaridade."
        ),
        "implementacao": "Generalizar dedup_classificar.py para receber raiz arbitrária.",
        "proof": "Subir 2 PDFs do mesmo extrato com nomes diferentes em raw/andre/itau_cc/ → dedup detecta.",  # noqa: E501
        "acceptance": ["Função generalizada.", "5+ testes."],
    },
    {
        "id": "DOC-15",
        "slug": "parse_data_br_centralizado",
        "titulo": "parse_data_br() em src/utils/parse_br.py + remover regex local de 22 extratores",
        "prio": "P2",
        "onda": 3,
        "esf": "4h",
        "dep": [],
        "fecha_itens": ["item 26 da auditoria"],
        "problema": ("22 extratores fazem regex próprio para data DD/MM/YYYY. Inconsistente."),
        "hipotese": (
            "parse_data_br(s: str, formatos: tuple = ('%d/%m/%Y', '%d-%m-%Y', "
            "'%Y-%m-%d')) -> date | None com fallback. Substituir em todos os 22."
        ),
        "implementacao": "Adicionar função + grep+sed substitui em cada extrator.",
        "proof": "grep para regex de data deve voltar 0 fora de parse_br.py.",
        "acceptance": ["Função coberta.", "Migração completa.", "Pytest baseline mantido."],
    },
    {
        "id": "DOC-16",
        "slug": "danfe_validar_ingestao",
        "titulo": "DANFE valida ingestão antes de retornar []",
        "prio": "P0",
        "onda": 3,
        "esf": "1h",
        "dep": [],
        "fecha_itens": ["item 21 da auditoria"],
        "problema": "danfe_pdf.py:224 retorna [] sem checar se db.adicionar_edge funcionou.",
        "hipotese": "Trocar por try/except + log.error em falha + raise se modo strict.",
        "implementacao": "Edit cirúrgico em danfe_pdf.py.",
        "proof": "Forçar erro SQL em fixture → log.error registrado, não silêncio.",
        "acceptance": ["Patch aplicado.", "Teste regressivo.", "Log estruturado em falhas."],
    },
    {
        "id": "DOC-17",
        "slug": "ocr_energia_cleanup",
        "titulo": "OCR energia com cleanup pré-regex (kWh distorcido)",
        "prio": "P1",
        "onda": 3,
        "esf": "3h",
        "dep": [],
        "fecha_itens": ["item 23 da auditoria"],
        "problema": "Regex `(\\d{2,4})\\s*[Kk][Ww][Hh]` falha em kwhh, khwh, kWHh.",
        "hipotese": (
            "Pré-cleanup: re.sub para normalizar variantes de kWh para 'kWh'. "
            "Validação anti-zero (consumo == 0 dispara warning)."
        ),
        "implementacao": "Editar src/extractors/energia_ocr.py.",
        "proof": "3 amostras reais com OCR distorcido → kWh correto.",
        "acceptance": ["Função normalize_kwh().", "Teste com 5+ variantes.", "Gate 4-way."],
    },
    {
        "id": "DOC-18",
        "slug": "holerite_detectar_novas_empresas",
        "titulo": "Holerite: declarativo em YAML + supervisor LLM detecta novo empregador",
        "prio": "P1",
        "onda": 3,
        "esf": "4h",
        "dep": ["LLM-02"],
        "fecha_itens": ["item 24 da auditoria"],
        "problema": (
            "_ASSINATURAS_HOLERITE em registry.py é hardcoded G4F+Infobase. "
            "Novo empregador cai silenciosamente."
        ),
        "hipotese": (
            "Mover assinaturas para mappings/assinaturas_holerite.yaml. Quando "
            "supervisor detecta PDF com layout de holerite mas sem casamento, "
            "propõe nova assinatura."
        ),
        "implementacao": "Refator + hook supervisor.",
        "proof": "Subir holerite de empresa nova → proposta gerada em mappings/proposicoes/.",
        "acceptance": ["YAML criado.", "Hook supervisor.", "5+ testes."],
    },
    {
        "id": "DOC-20",
        "slug": "extrato_investimento_corretora",
        "titulo": "Extrator: extrato de investimento (B3, NuInvest, Rico, XP, BTG)",
        "prio": "P1",
        "onda": 3,
        "esf": "5h",
        "dep": ["LLM-01", "ANTI-MIGUE-01"],
        "fecha_itens": ["item G da revisão 2026-04-29 — IRPF-01 sem investimentos"],
        "problema": (
            "Visão do dono: 'gerar IRPF do ano X' deve incluir investimentos. "
            "Hoje IRPF-01 cobre NFs, holerites, transações, parcelamentos, DAS — "
            "mas não há extrator de extrato de corretora. Ações, FIIs, RF, "
            "tesouro direto e cripto ficam invisíveis para tributação e patrimônio."
        ),
        "hipotese": (
            "Extrator unificado por corretora (PDF + CSV). B3 disponibiliza "
            "informe consolidado anual; corretoras geram extratos mensais. "
            "Tipo `extrato_investimento` com campos: ativo, quantidade, "
            "preco_medio, valor_aplicado, valor_atual, rendimento, data, corretora."
        ),
        "implementacao": (
            "1. Tipo em mappings/tipos_documento.yaml.\n"
            "2. src/extractors/extrato_investimento.py com sub-extratores.\n"
            "3. Node novo `investimento` no grafo + edge `posicao_em`.\n"
            "4. Coluna `tipo=Investimento` no XLSX (separa de Receita/Despesa).\n"
            "5. Fixture sintética + 3 amostras reais para gate 4-way.\n"
            "6. IRPF-01 consome via grafo."
        ),
        "proof": "make conformance-extrato_investimento exit 0.",
        "acceptance": [
            "Tipo + extrator + node novo.",
            "8+ testes.",
            "Gate 4-way verde.",
            "IRPF-01 consome.",
        ],
    },
    {
        "id": "DOC-19",
        "slug": "holerite_contem_item_sem_codigo",
        "titulo": "Holerite cria edge contem-item mesmo sem código de produto",
        "prio": "P3",
        "onda": 3,
        "esf": "1h",
        "dep": [],
        "fecha_itens": ["item 27 da auditoria"],
        "problema": (
            "ingestor_documento.py:563 pula entrada se faltar o campo de código "
            "do produto. Holerite tem "
            "verbas sem código → drill-down item-a-item impossível."
        ),
        "hipotese": "Gerar código sintético `holerite_<slug_descricao>` quando ausente.",
        "implementacao": "Edit cirúrgico em ingestor_documento.py.",
        "proof": "Holerite real → 3+ edges contem_item criadas.",
        "acceptance": ["Patch.", "Teste regressivo."],
    },
    {
        "id": "TEST-AUDIT-01",
        "slug": "expandir_fixtures_reais_para_30_amostras",
        "titulo": "Expandir fixtures reais de 6 para 30+ (item 28 da auditoria honesta)",
        "prio": "P1",
        "onda": 3,
        "esf": "8h",
        "dep": [],
        "fecha_itens": ["item 28 da auditoria honesta 2026-04-29"],
        "problema": (
            "1.987 testes mas só 6 fixtures reais (PDF/PNG/XML) em "
            "tests/fixtures/. Resto é sintético via factory. Bug Sprint 55 "
            "(1.761 tx classificadas erradas) passou por 1.530 testes verdes "
            "porque nenhum cobria o caso real. Risco continua até hoje."
        ),
        "hipotese": (
            "Para cada extrator (22), incluir pelo menos 1 fixture real "
            "redactada (PII mascarada com sed). Total: ~30 fixtures. Cada "
            "uma com teste regressivo que carrega o arquivo e valida output."
        ),
        "implementacao": (
            "1. Coletar 1 amostra real por extrator (22 extratores).\n"
            "2. Mascarar PII via script `scripts/mascarar_pii_fixture.py`.\n"
            "3. Salvar em tests/fixtures/<extrator>/<amostra>.pdf.\n"
            "4. tests/test_fixture_real_<extrator>.py com teste de carga + "
            "validação de campos extraídos.\n"
            "5. CI roda fixture real em todo PR (CI-01 dependência)."
        ),
        "proof": (
            "Cobertura de fixtures reais: 6 -> 30+. CI roda os 22 testes "
            "em <30s. Zero PII versionada (grep regex CPF/CNPJ vazio)."
        ),
        "acceptance": [
            "30+ fixtures reais redactadas.",
            "22 testes regressivos em CI.",
            "Script de mascaramento PII auditado.",
            "Zero PII em git.",
        ],
    },
    {
        "id": "GRAFO-XLSX-01",
        "slug": "investigar_discrepancia_xlsx_grafo",
        "titulo": "Investigar discrepância 6.093 XLSX vs 6.086 grafo (7 transações órfãs)",
        "prio": "P2",
        "onda": 4,
        "esf": "2h",
        "dep": [],
        "fecha_itens": ["achado da auditoria visual 2026-04-29 §1.2"],
        "problema": (
            "XLSX tem 6.093 linhas no extrato. Grafo SQLite tem 6.086 nodes "
            "tipo transação. Delta de 7. Não há explicação documentada. "
            "Possível causa: dedup tardio no ingestor do grafo ou pipeline "
            "que escreve XLSX antes de escrever grafo."
        ),
        "hipotese": (
            "Comparar dataframes: para cada (data, valor, local) do XLSX, "
            "buscar node correspondente no grafo. Listar as 7 órfãs. "
            "Identificar padrão (tipo, banco, mês)."
        ),
        "implementacao": (
            "scripts/auditar_discrepancia_grafo_xlsx.py com lookup completo "
            "+ relatório data/output/discrepancia_grafo_xlsx.md."
        ),
        "proof": "Lista das 7 órfãs com (data, valor, local, banco, hash).",
        "acceptance": [
            "Relatório com causa raiz.",
            "Fix aplicado OU justificativa documentada.",
            "Smoke arit aceita delta documentado.",
        ],
    },
    {
        "id": "MAKE-AM-01",
        "slug": "target_make_anti_migue",
        "titulo": "Adicionar target make anti-migue + make conformance-<tipo>",
        "prio": "P1",
        "onda": 1,
        "esf": "1h",
        "dep": ["ANTI-MIGUE-01"],
        "fecha_itens": ["achado da auditoria visual 2026-04-29 §3.1"],
        "problema": (
            "Makefile não tem target `make anti-migue` nem "
            "`make conformance-<tipo>`. Sem eles, o gate anti-migué de 9 "
            "checks não tem entry point único — cada Opus precisa lembrar "
            "de rodar lint+smoke+pytest+conformance separados."
        ),
        "hipotese": (
            "Targets compostos: `make anti-migue` roda lint+smoke+pytest+"
            "conformance-todos. Falha se qualquer um falhar."
        ),
        "implementacao": (
            "1. Makefile: target `anti-migue: lint smoke test`.\n"
            "2. Makefile: target `conformance-%:` que roda "
            "`pytest tests/conformance/ -k $*`.\n"
            "3. Documentar no CLAUDE.md §workflow."
        ),
        "proof": "make anti-migue exit 0 quando tudo verde; exit 1 se qualquer falhar.",
        "acceptance": [
            "Target funcional.",
            "Documentado em CLAUDE.md.",
            "Hook pre-push opcional usa.",
        ],
    },
    {
        "id": "OCR-AUDIT-01",
        "slug": "validar_qualidade_ocr_amostras",
        "titulo": "Auditoria de qualidade de OCR (5 amostras por extrator com OCR)",
        "prio": "P1",
        "onda": 3,
        "esf": "5h",
        "dep": ["ANTI-MIGUE-01"],
        "fecha_itens": ["achado da auditoria de banco 2026-04-29"],
        "problema": (
            "Extratores que dependem de OCR (energia_ocr, contracheque_pdf "
            "fallback Infobase, cupom_termico_foto, nfce com OCR de imagem) "
            "podem extrair valores errados sem o pipeline detectar. ARMADILHA "
            "#10 do CLAUDE.md confirma: energia_ocr tem 67% precisão em consumo "
            "kWh. Outros extratores OCR podem ter problemas similares não-medidos."
        ),
        "hipotese": (
            "Amostrar 5 documentos por extrator OCR. Para cada amostra, "
            "comparar: (a) texto OCR bruto vs (b) campos extraídos pelo "
            "pipeline vs (c) verdade ground-truth marcada por humano via "
            "Revisor 4-way. Computar precisão por campo."
        ),
        "implementacao": (
            "1. tests/ocr_audit/ com fixtures reais (5 PDFs/fotos por extrator "
            "OCR, total ~25).\n"
            "2. scripts/auditar_ocr.py que roda extrator e compara com "
            "ground-truth em YAML.\n"
            "3. Relatório data/output/auditoria_ocr.md com precisão por campo "
            "por extrator.\n"
            "4. Para campos com precisão <90%, criar sprint-filha de fix."
        ),
        "proof": (
            "Relatório com >=25 amostras, precisão por campo, lista de campos "
            "abaixo de 90% com sprint-filha apontada."
        ),
        "acceptance": [
            "Fixtures + ground-truth.",
            "Script + relatório.",
            "Sprints-filhas para gaps detectados.",
            "Baseline de qualidade documentado.",
        ],
    },
    # ---------- ONDA 4 (cruzamento micro + IRPF) ----------
    {
        "id": "LINK-AUDIT-01",
        "slug": "investigar_documentos_sem_aresta_documento_de",
        "titulo": "Investigar documentos catalogados sem aresta documento_de (linking heuristico falha)",  # noqa: E501
        "prio": "P0",
        "onda": 4,
        "esf": "4h",
        "dep": [],
        "fecha_itens": ["achado da auditoria de banco 2026-04-29"],
        "problema": (
            "Auditoria do grafo SQLite 2026-04-29 detectou taxas de vinculação "
            "muito baixas em alguns tipos:\n"
            "- holerite: 20/24 = 83% (aceitável)\n"
            "- das_parcsn_andre: 5/19 = 26% (RUIM)\n"
            "- boleto_servico: 0/2 = 0% (CRITICO)\n"
            "- nfce_modelo_65: 0/2 = 0% (CRITICO)\n"
            "Documentos sem documento_de não aparecem no Extrato com Doc=ok, e "
            "o pacote IRPF (IRPF-01) não os incluirá. Perda silenciosa."
        ),
        "hipotese": (
            "3 hipóteses a validar empiricamente:\n"
            "(a) janela temporal do linker está apertada para alguns tipos.\n"
            "(b) tolerância de valor (diff_valor) esta rígida.\n"
            "(c) pessoa do documento não casa com pessoa da transação "
            "(documento marcado como 'andre' mas transação como 'casal' por "
            "exemplo)."
        ),
        "implementacao": (
            "1. Para cada tipo problemático, listar os documentos sem aresta.\n"
            "2. Para cada um, buscar transação candidata (mesmo mês ±1, valor "
            "+-5%, qualquer pessoa).\n"
            "3. Se encontrar, identificar qual critério bloqueia o linking.\n"
            "4. Ajustar mappings/linking_config.yaml por tipo (boleto: janela "
            "75d 0.005; nfce: janela 5d 0.001 estrita; das: já tem 60d).\n"
            "5. Re-rodar linker e validar 80%+ vinculação por tipo."
        ),
        "proof": (
            "Após fix: das_parcsn 26%->=70%; boleto 0%->=80%; nfce 0%->=80%."
        ),
        "acceptance": [
            "Diagnóstico documentado por tipo.",
            "Config ajustada por tipo.",
            "Linker re-rodado com vinculação melhorada.",
            "Teste regressivo cobrindo o cenário detectado.",
        ],
    },
    # ---------- ONDA 4 continua ----------
    {
        "id": "MICRO-01",
        "slug": "linking_micro_runtime",
        "titulo": "Edges transação→nfce→item no grafo em runtime",
        "prio": "P1",
        "onda": 4,
        "esf": "5h",
        "dep": ["DOC-02", "DOC-19"],
        "fecha_itens": [],
        "problema": (
            "Drill-down 'paguei R$ 800 Vivendas → 3 itens granulares' impossível "
            "porque edge transação→item não existe."
        ),
        "hipotese": (
            "Após linking transação↔documento (Sprint 95), expandir: para cada "
            "edge documento_de, criar edges transação→nfce e nfce→item."
        ),
        "implementacao": "src/transform/linking_micro.py + integração no pipeline.",
        "proof": "Transação Vivendas tem 1 nfce + 3 itens acessíveis via grafo.",
        "acceptance": ["Edges criadas em runtime real.", "8+ testes."],
    },
    {
        "id": "MICRO-02",
        "slug": "items_canonicos_yaml",
        "titulo": "mappings/items_canonicos.yaml + categorização granular",
        "prio": "P2",
        "onda": 4,
        "esf": "3h",
        "dep": ["MICRO-01"],
        "fecha_itens": [],
        "problema": "Itens granulares (balinha, leite, pão) sem categoria final.",
        "hipotese": "YAML declarativo: regex_descricao → categoria_final + classificacao.",
        "implementacao": "mappings/items_canonicos.yaml + função aplicar em ingestor_item.",
        "proof": "100 itens variados → 80%+ categorizados (sem ficar em Outros).",
        "acceptance": ["YAML inicial com 50+ regras.", "Função.", "Cobertura ≥80% em corpus."],
    },
    {
        "id": "MICRO-03",
        "slug": "aba_cruzamento_micro",
        "titulo": "Aba Cruzamento Micro no dashboard (drill-down item-a-item)",
        "prio": "P2",
        "onda": 4,
        "esf": "4h",
        "dep": ["MICRO-01", "MICRO-02"],
        "fecha_itens": [],
        "problema": "Sem visualização de fluxo transação → item.",
        "hipotese": (
            "Aba dedicada: clique numa transação (Vivendas R$ 800) → tabela "
            "explode os itens (R$ 40 balinha, R$ 200 mercado, R$ 560 outros)."
        ),
        "implementacao": "src/dashboard/paginas/cruzamento_micro.py.",
        "proof": "Aba live exibe drill-down em runtime real.",
        "acceptance": ["Aba.", "Drill-down funcional.", "Validação visual."],
    },
    {
        "id": "IRPF-01",
        "slug": "pacote_irpf_botao",
        "titulo": "Botão 'Gerar pacote IRPF <ano>' → ZIP completo on-demand",
        "prio": "P1",
        "onda": 4,
        "esf": "5h",
        "dep": ["MICRO-01"],
        "fecha_itens": [],
        "problema": (
            "Pacote IRPF requer hoje compilar manualmente NFs, holerites, "
            "comprovantes, parcelamentos, DAS."
        ),
        "hipotese": (
            "Botão consulta grafo e empacota ZIP com: tabela XLSX (transações + "
            "fontes), pasta NFs/, pasta holerites/, pasta DAS/, pasta médico/, "
            "summary.md com totais por categoria IRPF."
        ),
        "implementacao": "src/analysis/pacote_irpf.py + UI no dashboard.",
        "proof": "Gerar pacote 2025 → ZIP com 100% das fontes vinculadas.",
        "acceptance": ["Botão funcional.", "ZIP estruturado.", "Summary com totais."],
    },
    {
        "id": "GAP-01",
        "slug": "alerta_proativo_transacao_sem_nf",
        "titulo": "Alerta proativo: transação alta sem NF/comprovante correspondente",
        "prio": "P1",
        "onda": 4,
        "esf": "4h",
        "dep": ["MICRO-01"],
        "fecha_itens": ["item E da revisão 2026-04-29 (visão do dono)"],
        "problema": (
            "Visão do dono: 'gastei 800 na amazon com idiotice, falta a nota "
            "fiscal'. Hoje sistema não reage proativamente: transação aparece "
            "no XLSX, mas se não vem NF, fica invisível. IRPF anual chega "
            "incompleto sem alerta intermediário."
        ),
        "hipotese": (
            "Detector cruzando extrato vs grafo: para cada transação acima de "
            "limiar configurável (ex: R$ 100), verificar se existe edge "
            "documento_de apontando para ela. Se não, listar como 'gap "
            "documental'. Alertar via aba dedicada + relatório mensal + sync "
            "para mobile companion (notificação)."
        ),
        "implementacao": (
            "1. src/analysis/gap_documental_proativo.py — `detectar_gaps(limiar)`.\n"
            "2. mappings/limiares_gap.yaml por categoria (Mercado: R$ 100; "
            "Eletrônicos: R$ 50; etc.).\n"
            "3. Aba 'Gaps documentais' no dashboard com lista filtrada.\n"
            "4. Relatório mensal com top-N gaps.\n"
            "5. Cache JSON para mobile (vault/.ouroboros/cache/gaps.json)."
        ),
        "proof": (
            "Corpus real → detecta >=10 gaps em transações > R$ 100 sem doc."
        ),
        "acceptance": [
            "Módulo + 8 testes.",
            "Aba dashboard.",
            "Relatório mensal.",
            "Cache mobile.",
        ],
    },
    {
        "id": "IRPF-02",
        "slug": "irpf_dedutivel_medico",
        "titulo": "Link automático receita médica + exame + pagamento bancário",
        "prio": "P2",
        "onda": 4,
        "esf": "3h",
        "dep": ["DOC-09", "DOC-10"],
        "fecha_itens": [],
        "problema": "Despesas médicas dedutíveis precisam cruzamento manual.",
        "hipotese": "Heurística (CPF do paciente + data ±30d + valor ±10%) cria edge dedutivel_medico.",  # noqa: E501
        "implementacao": "src/transform/linking_medico.py.",
        "proof": "Casal tem 5+ despesas médicas → 5+ edges dedutivel_medico criadas.",
        "acceptance": ["Heurística testada.", "Edges em runtime real."],
    },
    # ---------- ONDA 5 (mobile bridge + fontes adicionais) ----------
    {
        "id": "MOB-01",
        "slug": "vault_bridge_md",
        "titulo": "Backend lê .md do mobile e roteia para inbox",
        "prio": "P0",
        "onda": 5,
        "esf": "5h",
        "dep": [],
        "fecha_itens": ["item 31 da auditoria"],
        "problema": (
            "Mob-Ouroboros escreve .md em vault/daily/, vault/eventos/, etc. Backend não lê."
        ),
        "hipotese": (
            "src/intake/vault_bridge.py varre as 6 pastas-alvo no vault, lê "
            "frontmatter YAML, roteia para o pipeline conforme tipo. "
            "Idempotência via hash de conteúdo."
        ),
        "implementacao": "Módulo + integração em --full-cycle.",
        "proof": "Subir .md em vault/daily/ → backend captura no próximo full-cycle.",
        "acceptance": [
            "Módulo testado.",
            "6 tipos cobertos (humor, evento, diario, treino, medida, financeiro).",
            "Idempotência por hash.",
        ],
    },
    {
        "id": "MOB-02",
        "slug": "mobile_cache_gen",
        "titulo": "Backend gera vault/.ouroboros/cache/{financas,humor-heatmap}.json",
        "prio": "P0",
        "onda": 5,
        "esf": "4h",
        "dep": ["MOB-01"],
        "fecha_itens": ["item 31 da auditoria"],
        "problema": (
            "Mob-Ouroboros tela 22 (Mini Financeiro) e 21 (Mini Humor) precisam "
            "destes JSONs. Não são gerados."
        ),
        "hipotese": (
            "src/cache/mobile_cache.py com 2 funções: gerar_financas_cache() e "
            "gerar_humor_heatmap_cache(). Encadear em --full-cycle."
        ),
        "implementacao": "Módulo + JSON schemas documentados em docs/MOBILE_CACHE.md.",
        "proof": "Após --full-cycle, ambos JSONs existem com dados válidos.",
        "acceptance": [
            "Módulo testado.",
            "JSONs gerados em runtime.",
            "Schema documentado para o mobile consumir.",
        ],
    },
    {
        "id": "MOB-03",
        "slug": "pessoa_a_b_refactor",
        "titulo": "Refactor PESSOA_A/PESSOA_B + mappings/pessoas.yaml (paridade com mobile)",
        "prio": "P2",
        "onda": 5,
        "esf": "4h",
        "dep": [],
        "fecha_itens": [],
        "problema": (
            "Mob-Ouroboros usa convenção PESSOA_A/PESSOA_B. Backend hardcoda "
            "'André'/'Vitória'. Quebra anonimato e portabilidade."
        ),
        "hipotese": (
            "Substituir literais por lookup em mappings/pessoas.yaml. "
            "Manter compatibilidade backward via aliases."
        ),
        "implementacao": "Refactor + script backfill no XLSX.",
        "proof": "grep 'André\\|Vitória' src/ → 0 matches em código.",
        "acceptance": ["Mappings + lookup.", "Refactor completo.", "Pytest baseline."],
    },
    {
        "id": "FONTE-01",
        "slug": "google_calendar_ics",
        "titulo": "src/integrations/google_calendar.py — sync .ics",
        "prio": "P1",
        "onda": 5,
        "esf": "4h",
        "dep": [],
        "fecha_itens": ["item 37 da auditoria"],
        "problema": "Agendas do casal não estão integradas à central de vida adulta.",
        "hipotese": (
            "Lib `icalendar` lê .ics exportado/sincronizado. Eventos viram nodes "
            "tipo 'evento_agenda' no grafo."
        ),
        "implementacao": "Módulo + node tipo + página dedicada (Onda 6).",
        "proof": "Subir .ics com 10 eventos → 10 nodes criados.",
        "acceptance": ["Módulo + 5+ testes.", "Schema de node.", "Cron de sync configurável."],
    },
    {
        "id": "FONTE-02",
        "slug": "thunderbird_email_local",
        "titulo": "src/integrations/thunderbird_email.py — lê maildir local + roteia anexos",
        "prio": "P1",
        "onda": 5,
        "esf": "5h",
        "dep": [],
        "fecha_itens": ["item 37 da auditoria"],
        "problema": "Anexos de email (boletos, NFs) ficam parados no Thunderbird.",
        "hipotese": (
            "Lib `mailbox` lê ~/.thunderbird/<perfil>/Mail/ (formato Maildir/Mbox). "
            "Anexos em formato suportado são copiados para data/raw/_classificar/."
        ),
        "implementacao": "Módulo + filtros (remetente, assunto) configuráveis em YAML.",
        "proof": "Email com anexo PDF de boleto → arquivo copiado para inbox.",
        "acceptance": ["Módulo + 8+ testes.", "Filtros YAML.", "Idempotência por hash."],
    },
    {
        "id": "FONTE-03",
        "slug": "thunderbird_ics_local",
        "titulo": "src/integrations/thunderbird_ics.py — calendars locais",
        "prio": "P2",
        "onda": 5,
        "esf": "3h",
        "dep": ["FONTE-01"],
        "fecha_itens": [],
        "problema": "Thunderbird Lightning armazena calendars em SQLite local.",
        "hipotese": "Reusar parser do FONTE-01 mas apontando para storage do Thunderbird.",
        "implementacao": "Módulo + path detection.",
        "proof": "Eventos do Thunderbird aparecem no grafo.",
        "acceptance": ["Módulo + testes.", "Doc do path no Pop!_OS."],
    },
    {
        "id": "FONTE-04",
        "slug": "assinaturas_detector",
        "titulo": "src/analysis/assinaturas.py — recorrências em cartão",
        "prio": "P1",
        "onda": 5,
        "esf": "3h",
        "dep": [],
        "fecha_itens": [],
        "problema": (
            "Serviços por assinatura (Spotify, Netflix, iCloud) só aparecem como "
            "transação avulsa. Sem visão consolidada."
        ),
        "hipotese": (
            "Detector: para cada (fornecedor, valor±5%) com ≥3 ocorrências em "
            "datas próximas (±3d/mês), marca como assinatura."
        ),
        "implementacao": "Módulo + aba 'Assinaturas' no dashboard.",
        "proof": "Corpus real → detecta ≥10 assinaturas conhecidas (Spotify, Amazon, etc.).",
        "acceptance": ["Detector.", "Aba.", "Tabela com previsão de gasto mensal."],
    },
    # ---------- ONDA 6 (UX/UI + OMEGA) ----------
    {
        "id": "UX-01",
        "slug": "callouts_dracula",
        "titulo": "Migrar 4 arquivos st.error/warning/info/success → callout_html",
        "prio": "P0",
        "onda": 6,
        "esf": "2h",
        "dep": [],
        "fecha_itens": ["itens 1–4 da auditoria"],
        "problema": (
            "preview_documento.py, app.py, modal_transacao.py, busca.py usam "
            "componentes nativos do Streamlit fora do tema Dracula."
        ),
        "hipotese": "Replace direto por callout_html (Sprint 92c).",
        "implementacao": "Edits cirúrgicos nos 4 arquivos.",
        "proof": "grep st.error|warning|info|success em src/dashboard/ → 0 matches.",
        "acceptance": ["Migração 100%.", "Validação visual."],
    },
    {
        "id": "UX-02",
        "slug": "treemap_heatmap_wcag",
        "titulo": "Treemap + heatmap WCAG-AA em viewport ≤1200px",
        "prio": "P1",
        "onda": 6,
        "esf": "3h",
        "dep": [],
        "fecha_itens": ["itens 5, 6 da auditoria"],
        "problema": "Contraste falha em viewport pequena.",
        "hipotese": "_cor_texto_por_fundo() aplicada em toda paleta + teste em 1200×700.",
        "implementacao": "Refactor categorias.py + analise_avancada.py.",
        "proof": "Screenshot WCAG-AA em 1200×700.",
        "acceptance": ["Contraste medido ≥4.5:1.", "Screenshot evidência."],
    },
    {
        "id": "UX-03",
        "slug": "drilldown_em_5_plots",
        "titulo": "Drill-down em Sankey + Heatmap + Bar Pagamentos + Line Projeções + Bar Completude",  # noqa: E501
        "prio": "P2",
        "onda": 6,
        "esf": "5h",
        "dep": [],
        "fecha_itens": ["itens 7–11 da auditoria"],
        "problema": "5 gráficos sem clique→filtro. Exploração presa em top-level.",
        "hipotese": "Aplicar helper aplicar_drilldown() (Sprint 73) em cada um.",
        "implementacao": "Edits em 5 páginas.",
        "proof": "Cada gráfico filtra Extrato ao clicar.",
        "acceptance": ["5 drill-downs ativos.", "Validação visual."],
    },
    {
        "id": "UX-04",
        "slug": "revisor_responsivo_50_itens",
        "titulo": "Revisor responsivo + scroll/expand em documentos com 50+ itens",
        "prio": "P2",
        "onda": 6,
        "esf": "3h",
        "dep": [],
        "fecha_itens": ["itens 12, 13 da auditoria"],
        "problema": "Layout 4 colunas quebra em <1200px. 50+ subitens renderizam inline.",
        "hipotese": ("use_container_width + media query CSS + expander para listas longas."),
        "implementacao": "revisor.py refactor.",
        "proof": "Screenshot em 900px legível + documento 50+ itens com expander.",
        "acceptance": ["Responsividade.", "Expander."],
    },
    {
        "id": "UX-05",
        "slug": "pyvis_fallback_decente",
        "titulo": "Pyvis fallback decente (spinner, timeout, mensagem útil)",
        "prio": "P3",
        "onda": 6,
        "esf": "1h",
        "dep": [],
        "fecha_itens": ["item 15 da auditoria"],
        "problema": "Quando bzip2 ausente, retorna `<p>` simples sem feedback.",
        "hipotese": "Detectar ambiente, mostrar instruções + botão regenerar.",
        "implementacao": "grafo_pyvis.py refactor.",
        "proof": "Sem bzip2 → mensagem útil em vez de tela em branco.",
        "acceptance": ["UX clara em fallback."],
    },
    {
        "id": "UX-06",
        "slug": "doc_coluna_observabilidade",
        "titulo": "Coluna 'Doc?' com observabilidade (logs em falhas do grafo)",
        "prio": "P3",
        "onda": 6,
        "esf": "1h",
        "dep": [],
        "fecha_itens": ["item 16 da auditoria"],
        "problema": "Falha no grafo cai em set vazio sem log.",
        "hipotese": "logger.warning + métrica de erro.",
        "implementacao": "Edit cirúrgico em extrato.py.",
        "proof": "Forçar erro SQL → log estruturado.",
        "acceptance": ["Log + teste."],
    },
    {
        "id": "UX-07",
        "slug": "snapshot_timestamp_dinamico",
        "titulo": "Snapshot histórico com timestamp dinâmico em Inventário/Prazos/Dívidas Ativas",
        "prio": "P3",
        "onda": 6,
        "esf": "1h",
        "dep": [],
        "fecha_itens": ["item 17 da auditoria"],
        "problema": "Aviso 'snapshot 2023' hardcoded sem data dinâmica.",
        "hipotese": "Ler mtime do XLSX + exibir em rodapé.",
        "implementacao": "Edit em paginas/contas.py + estender para Inventário/Prazos/Dívidas Ativas.",  # noqa: E501
        "proof": "UI mostra 'Snapshot atualizado em <data>'.",
        "acceptance": ["Timestamp em 4 abas."],
    },
    {
        "id": "UX-08",
        "slug": "deep_link_test_completo",
        "titulo": "Cobertura de teste deep-link ?tab= em todas 13 abas + 5 clusters",
        "prio": "P3",
        "onda": 6,
        "esf": "2h",
        "dep": [],
        "fecha_itens": ["item 18 da auditoria"],
        "problema": "Sprint 100 deu por encerrada sem teste cobrindo todas as combinações.",
        "hipotese": "Pytest parametrizado com 13×5 cenários.",
        "implementacao": "tests/test_dashboard_deeplink_tab.py.",
        "proof": "Pytest passa todos os cenários.",
        "acceptance": ["65 cenários cobertos."],
    },
    {
        "id": "UX-09",
        "slug": "cleanup_docstrings_quebradas",
        "titulo": "Cleanup 6 docstrings com acentuação quebrada",
        "prio": "P3",
        "onda": 6,
        "esf": "30min",
        "dep": [],
        "fecha_itens": ["item 14 da auditoria"],
        "problema": "6 docstrings com acentuação errada apesar de # noqa: accent.",
        "hipotese": "Acentuação correta sempre. # noqa só onde de fato é símbolo externo.",
        "implementacao": "Edits cirúrgicos.",
        "proof": "make lint exit 0 + docstrings PT-BR ortográficas.",
        "acceptance": ["6 fixes."],
    },
    {
        "id": "UX-10",
        "slug": "clarificar_cluster_vs_aba_nomenclatura",
        "titulo": "Clarificar hierarquia cluster vs aba (mesmos rótulos confundem usuário)",
        "prio": "P2",
        "onda": 6,
        "esf": "2h",
        "dep": [],
        "fecha_itens": ["achado da auditoria visual 2026-04-29"],
        "problema": (
            "Cluster 'Home' tem aba 'Finanças'; cluster 'Documentos' tem aba "
            "'Catalogação'. A sidebar mostra dropdown 'Área' com clusters; o "
            "topo mostra abas. Mas alguns rótulos repetem (cluster 'Análise' "
            "tem aba 'Análise' interna). Usuário não sabe se está em cluster "
            "ou em aba. Auditoria visual 2026-04-29 detectou ambiguidade."
        ),
        "hipotese": (
            "Renomear sidebar 'Área' para 'Domínio' (5 domínios) e diferenciar "
            "visualmente domínio (sidebar, label maiúsculo) de aba (top, "
            "lowercase mono). Eliminar nomes duplicados: cluster 'Análise' "
            "vira 'Análise & Categorias'."
        ),
        "implementacao": (
            "1. Renomear label sidebar.\n"
            "2. Auditar MAPA_ABA_PARA_CLUSTER e renomear duplicatas.\n"
            "3. Adicionar breadcrumb 'Domínio › Aba' em cada página.\n"
            "4. Validação visual em 5 clusters."
        ),
        "proof": "Screenshot lado-a-lado antes/depois mostrando hierarquia clara.",
        "acceptance": [
            "Sidebar com label 'Domínio'.",
            "Zero duplicação de rótulos.",
            "Breadcrumb por página.",
        ],
    },
    {
        "id": "OMEGA-94a",
        "slug": "aba_saude",
        "titulo": "Aba Saúde (receitas, exames, plano + alertas validade)",
        "prio": "P2",
        "onda": 6,
        "esf": "5h",
        "dep": ["DOC-09", "DOC-10", "DOC-11"],
        "fecha_itens": [],
        "problema": "Documentos de saúde não têm visualização integrada.",
        "hipotese": "Aba dedicada + alertas (CNH, exame, receita prestes a vencer).",
        "implementacao": "src/dashboard/paginas/saude.py + mappings/categorias_saude.yaml.",
        "proof": "Aba live com dados do casal.",
        "acceptance": ["Aba.", "Alertas.", "Mappings."],
    },
    {
        "id": "OMEGA-94b",
        "slug": "aba_identidade",
        "titulo": "Aba Identidade (RG/CNH/passaporte + alertas validade)",
        "prio": "P2",
        "onda": 6,
        "esf": "4h",
        "dep": ["DOC-04", "DOC-05"],
        "fecha_itens": [],
        "problema": "Documentos de identidade sem aba dedicada.",
        "hipotese": "Aba + alerta T-90d antes do vencimento.",
        "implementacao": "src/dashboard/paginas/identidade.py.",
        "proof": "Aba live.",
        "acceptance": ["Aba.", "Alertas."],
    },
    {
        "id": "OMEGA-94c",
        "slug": "aba_profissional",
        "titulo": "Aba Profissional (contratos, registrato, rescisão)",
        "prio": "P2",
        "onda": 6,
        "esf": "3h",
        "dep": [],
        "fecha_itens": [],
        "problema": "Vida profissional sem aba.",
        "hipotese": "Aba + listagem cronológica + alertas de cláusula prestes a expirar.",
        "implementacao": "src/dashboard/paginas/profissional.py.",
        "proof": "Aba live.",
        "acceptance": ["Aba."],
    },
    {
        "id": "OMEGA-94d",
        "slug": "aba_academica",
        "titulo": "Aba Acadêmica (diplomas, históricos, certificados)",
        "prio": "P2",
        "onda": 6,
        "esf": "3h",
        "dep": ["DOC-06", "DOC-07"],
        "fecha_itens": [],
        "problema": "Vida acadêmica sem aba.",
        "hipotese": "Aba + filtro por instituição/curso.",
        "implementacao": "src/dashboard/paginas/academica.py.",
        "proof": "Aba live.",
        "acceptance": ["Aba."],
    },
    {
        "id": "ADR-23-DRAFT",
        "slug": "adr_23_envelope_vs_pessoa_canonico",
        "titulo": "ADR-23: decisão envelope vs pessoa como path canônico",
        "prio": "P3",
        "onda": 6,
        "esf": "1h (decisão) + variável (execução)",
        "dep": [],
        "fecha_itens": ["item 47 da auditoria + AUDIT2-ENVELOPE-VS-PESSOA-CANONICO"],
        "problema": "ADR-21 aprovou fusão; sem ADR-23 detalhando próximos passos.",
        "hipotese": "Decisão arquitetural com supervisor humano sobre path canônico.",
        "implementacao": "Discussão + draft ADR + execução conforme decisão.",
        "proof": "ADR-23 publicada.",
        "acceptance": ["ADR.", "Pipeline padroniza canônico."],
    },
    {
        "id": "DASH-01",
        "slug": "pacote_anual_de_vida",
        "titulo": "Botão 'Gerar pacote anual de vida <ano>' (não só IRPF)",
        "prio": "P2",
        "onda": 6,
        "esf": "4h",
        "dep": ["IRPF-01", "OMEGA-94a", "OMEGA-94b", "OMEGA-94c", "OMEGA-94d"],
        "fecha_itens": ["item AB da revisão 2026-04-29 (visão do dono)"],
        "problema": (
            "Visão do dono: pacote IRPF é só 1 dos pacotes anuais. Pessoa "
            "também precisa: pacote Saúde (todas consultas, exames, despesas), "
            "pacote Profissional (contratos, certificados, holerites), pacote "
            "Acadêmico (histórico, diplomas, atividades), pacote Identidade "
            "(estado dos documentos com alertas de validade)."
        ),
        "hipotese": (
            "Generalizar IRPF-01: botão único 'Pacote anual de vida <ano>' "
            "gera ZIP com 5 pastas (financeiro/saude/profissional/academico/"
            "identidade), cada uma com summary.md + arquivos vinculados via "
            "grafo. Filtro por pessoa (André/Vitória/Casal)."
        ),
        "implementacao": (
            "1. src/analysis/pacote_anual_vida.py reusa IRPF-01 + adiciona "
            "agregadores por domínio.\n"
            "2. Aba dashboard 'Pacote anual' com seletor (pessoa, ano, "
            "domínios marcados).\n"
            "3. summary.md por domínio + summary geral cross-domínio.\n"
            "4. ZIP estruturado: pacote_<pessoa>_<ano>.zip."
        ),
        "proof": (
            "Gerar pacote 2025 do casal → ZIP com 5 pastas + 5 summaries + "
            "todos arquivos vinculados via grafo."
        ),
        "acceptance": [
            "Botão funcional.",
            "ZIP estruturado.",
            "5 summaries por domínio.",
            "Filtro por pessoa.",
        ],
    },
    {
        "id": "MON-01",
        "slug": "vault_obsidian_dessincronia",
        "titulo": "Monitor de dessincronia do Vault Obsidian",
        "prio": "P1",
        "onda": 6,
        "esf": "3h",
        "dep": [],
        "fecha_itens": ["item 32 da auditoria"],
        "problema": (
            "sync_rico depende de tag `#sincronizado-automaticamente`. Sem monitor, "
            "nota editada manualmente sem tag pode ser sobrescrita."
        ),
        "hipotese": (
            "Cron diário compara hash de cada nota com último hash conhecido. "
            "Divergência sem tag → alerta."
        ),
        "implementacao": "src/obsidian/monitor_dessincronia.py + relatório.",
        "proof": "Editar nota sem tag → próximo cron alerta.",
        "acceptance": ["Cron + relatório.", "Teste."],
    },
]


TEMPLATE = """# Sprint {id} -- {titulo}

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: {prio}
**Onda**: {onda}
**Esforço estimado**: {esf}
**Depende de**: {dep_str}
**Fecha itens da auditoria**: {fecha_str}

## Problema

{problema}

## Hipótese

{hipotese}

## Implementação proposta

{implementacao}

## Proof-of-work (runtime real)

{proof}

## Acceptance criteria

{acceptance_str}

## Gate anti-migué

Para mover esta spec para `docs/sprints/concluidos/`:

1. Hipótese declarada validada com `grep` antes de codar.
2. Proof-of-work runtime real capturado em log.
3. `make conformance-<tipo>` exit 0 quando aplicável (>=3 amostras 4-way).
4. `make lint` exit 0.
5. `make smoke` 10/10 contratos.
6. `pytest` baseline mantida ou crescida.
7. Achados colaterais viraram sprint-ID OU Edit-pronto. Zero TODO solto.
8. Validador (humano ou subagent) APROVOU.
9. Frontmatter `concluida_em: YYYY-MM-DD` adicionado.
"""


def materializar() -> int:
    BACKLOG.mkdir(parents=True, exist_ok=True)
    criados = 0
    for spec in SPECS:
        nome = f"sprint_{spec['id'].lower().replace('-', '_')}_{spec['slug']}.md"
        caminho = BACKLOG / nome
        dep_str = ", ".join(spec["dep"]) if spec["dep"] else "nenhuma"
        fecha_str = ", ".join(spec["fecha_itens"]) if spec["fecha_itens"] else "nenhum"
        acceptance_str = "\n".join(f"- {item}" for item in spec["acceptance"])
        conteudo = TEMPLATE.format(
            id=spec["id"],
            titulo=spec["titulo"],
            prio=spec["prio"],
            onda=spec["onda"],
            esf=spec["esf"],
            dep_str=dep_str,
            fecha_str=fecha_str,
            problema=spec["problema"],
            hipotese=spec["hipotese"],
            implementacao=spec["implementacao"],
            proof=spec["proof"],
            acceptance_str=acceptance_str,
        )
        caminho.write_text(conteudo, encoding="utf-8")
        criados += 1
    print(f"[BACKLOG] {criados} specs materializadas em {BACKLOG}")
    return 0


if __name__ == "__main__":
    sys.exit(materializar())


# "Cada sprint que vira spec é uma promessa que não pode ser quebrada
# sem registro." -- princípio anti-migué
