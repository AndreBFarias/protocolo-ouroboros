---
titulo: Auditoria empírica do app mobile Protocolo-Mob-Ouroboros
data: 2026-05-12
auditor: agente Opus background
escopo: 9 dores do dono + share intent + sync + publicação
---

# Auditoria empírica do app mobile

## TL;DR

A "Onda Q" (commits `557319f` 2026-05-12 19:26 e `47f5564` 2026-05-12 19:50)
endereçou as 9 dores em código antes desta auditoria. Estado real:
**6 FIXADAS**, **3 PARCIAIS**, **0 não-fixadas**. Galeria existe e cobre
Q9 com filtros por tipo, mas é read-only. FAB de Tarefas/Contadores
permanece 56dp/roxo, não 64dp como FABMenu+FABCaptura. Camera "registrar
momento" usa fix com setTimeout 120ms + retry 800ms — defensivo, sem
prova de runtime. Pendente: I2-OAUTH Google Calendar (Q0 liberou consent,
runtime ainda não validado em /agenda).

## Dores do dono (1-9)

### 1. Renomear "ouroboros-mobile" -> "Ouroboros"
- **Status**: FIXADO
- **Evidência**: `app.json:3` `"name": "Ouroboros"`. `package.json:2`
  `"name": "ouroboros"`. Slug e Android package permanecem
  `ouroboros-mobile` / `com.ouroboros.mobile` (preserva EAS projectId
  `27c5d3d3-1110-49c1-8457-a99c6249f320`).
- **Achado**: Display name e package npm trocados, identificadores
  técnicos mantidos. Decisão durável (Q1 changelog).

### 2. Botão Recap invisível na Home
- **Status**: FIXADO (5 iterações Q2 → Q2.4)
- **Evidência**: `/home/andrefarias/Desenvolvimento/Protocolo-Mob-Ouroboros/app/index.tsx:45-96`
  componente `BotaoRecap` (Pressable custom, pill purple `rgba(189,147,249,0.16)`
  + borda purple/45, Sparkles 14dp + label 14dp). Header.tsx slot direito
  ganhou `minWidth: 40 + alignSelf: flex-end + flexShrink: 0` (armadilha A33).
- **Achado**: Variante `pill` do Button.tsx removida; abandonado em
  favor de Pressable inline (~30 linhas). MotiView do Button colapsava
  flex row no New Arch (A34).

### 3. Menu lateral "muito poing"
- **Status**: FIXADO
- **Evidência**: `MenuLateral.tsx:320` aplica `withSpring(0, { damping: 32,
  stiffness: 170, mass: 1 })` — preset `springs.smooth` adicionado em
  `src/lib/motion.ts:13`. Substituiu `springs.subtle` (damping 22 /
  stiffness 220) reportado como excessivo.
- **Achado**: Curva nova só usada no PainelDrawer (drawer 280dp). Outros
  spots seguem `subtle/default/bouncy/snappy`.

### 4. Áudio gravado gera transcrição automática no diário
- **Status**: FIXADO
- **Evidência**: `src/components/diario/MicrofoneButton.tsx:322` dispara
  `transcribeStream` em paralelo a `Audio.Recording`. Parciais chegam ao
  textarea via callback `onTextoTranscrito(parcial)` enquanto usuário
  fala. `expo-speech-recognition` no `app.json:102-108`.
- **Achado**: Transcrição é LIVE (streaming, durante gravação), não pós-stop.
  Respeita `settings.privacidade.ocultarTranscricoes` (suprime parciais
  na UI mas grava transcrição no companion .md). Save áudio + companion
  é não-bloqueante: erro de transcribe vira `console.error` silencioso.

### 5. Conquista exige mídia obrigatória + visualizador inline
- **Status**: FIXADO
- **Evidência**: `src/lib/schemas/evento.ts:40-43` refine bloqueia save
  positivo sem mídia (`positivo exige pelo menos uma midia`).
  `app/eventos.tsx:225-228` valida antes do submit com toast warn.
  `src/components/screens/DetalheConquista.tsx:155-196` Modal nativo
  fullscreen para foto (tap no cover abre, resizeMode contain). Linha
  259 substitui fallback "indisponível" por `WaveformPreview` real
  (play/pause + duração).
- **Achado**: Cobre foto e áudio. YouTube/Spotify abrem via `Linking.openURL`
  (external). **Vídeo NÃO está no schema Midia** — anotado para pós-1.0.

### 6. Câmera "registrar momento" não funciona
- **Status**: FIXADO (defensivamente)
- **Evidência**: `app/captura.tsx` ramifica em 2 rotas: "Registrar
  momento" → `/saude-fisica?abrirCaptura=1`; "Escanear documento" →
  `/scanner`. `MenuCapturaVerde.tsx:217-235` useEffect com `abrirNoMount`:
  `setTimeout(120ms) + retry em 800ms` se sheet ainda fechado. Cobre
  armadilha A30 (gorhom v5 + Reanimated 4 + New Arch sheet offscreen
  em HyperOS lento).
- **Achado**: Fix é heurístico (timing). Validação visual confirmada
  no celular Xiaomi 2312DRAABG segundo `docs/ONDA-Q-2026-05-12.md:5`
  apenas para Q1+Q2+Q4. **Q7 ainda não validado live** (commit
  declara "pendente reabrir app sem ANR").

### 7. Botões "+" no menu — mesma altura, mesmo tamanho, cores distintas
- **Status**: PARCIAL
- **Evidência**: `FABMenu.tsx:43` `FAB_SIZE = 64` (roxo, esquerda).
  `MenuCapturaVerde.tsx:62` `FAB_SIZE = 64` (verde, direita). Ambos
  consomem `useSafeBottomMargin(insets.bottom)` (mesma altura).
- **Achado**: O componente genérico `src/components/ui/FAB.tsx:21`
  permanece em `SIZE = 56` e cor `colors.purple`. Usado em
  `app/todo.tsx:563` (Tarefas) e `app/contadores/index.tsx`. Esses
  botões ainda divergem em tamanho (56 vs 64) e cor (mesma cor do FAB
  do menu lateral). A queixa "cores diferentes" só é atendida para o
  par FABMenu↔MenuCapturaVerde, não para FABs de listas.

### 8. Ciclo menstrual: usuário não consegue ver/acompanhar
- **Status**: FIXADO
- **Evidência**: `app/ciclo/index.tsx:179-209` mini-stats no topo ("Dia
  X do ciclo", "Duração média Y dias"). Linhas 240-264 seção "Últimos
  registros" com até 14 itens; tap navega para `/ciclo/registrar?data=...`
  pré-preenchido. `ItemRegistroCiclo` componente local (lines 289-373)
  com chip de fase Dracula (folicular=cyan, ovulatória=pink, lútea=orange,
  menstrual=red) e sintomas resumidos.
- **Achado**: Q8 commit `47f5564` (1h após Q1-Q7) corrigiu bug
  bloqueador: load usava `pessoaAtiva` direto, save usava
  `autorPadrao(tipoCompanhia, sexoA, sexoB)`. Em casal masc+fem, save
  gravava `pessoa_b` (feminina inferida) e load filtrava por `pessoa_a`
  default → empty state apesar do registro persistir. Linhas 77-80
  replicam inferência no load para simetria.

### 9. Galeria/timeline de eventos
- **Status**: PARCIAL
- **Evidência**: `app/galeria/index.tsx` é o Vault Explorer unificado;
  filtros chip Tudo/Fotos/Áudios/Vídeos/Textos/Mais. `listarItensGaleria`
  lê só frontmatter dos .md (não carrega binários). Cobre 15 tipos:
  humor, diario, evento, marco, foto, audio, video, frase, tarefa,
  alarme, contador, nota, ciclo, exercicio, scanner. Item no MenuLateral
  linha 157. Detalhe em `app/galeria/detalhe/[slug].tsx`.
- **Achado**: Detalhe é **read-only** (line 4 comentário confirma:
  "tap em item abre /galeria/detalhe/[slug] read-only"). Não há fluxo
  edit-in-place na galeria; usuário tem que abrir a tela canônica de
  cada tipo para editar. Timeline da Home (`SecaoDiariosEventosAgrupado.tsx`)
  também não é tappável — itens em View, não Pressable. Dor "poder
  editar tudo que salvou" ainda não atendida.

## Adicionais

### 10. Share Intent Receiver
- **Estado**: FUNCIONAL para imagens + PDFs. `app.json:42-56` declara
  intentFilter SEND com mimeType `image/*` e `application/pdf`.
  `app/share-receive.tsx` orquestra; UI em
  `src/components/screens/ShareReceiver`. Cancela / save via
  `router.dismissAll()` (CONTRACT 1.7 — devolve foco ao app de origem
  em <5s).
- **Categorias suportadas (8 subtipos / 4 áreas)**: pix, extrato, nota,
  exame, receita, garantia, contrato, outro
  (`src/lib/share/categorias.ts:30-79`). Chip "PIX" aparece primeiro
  (verde), alinhado ao "flow PIX em 5s".
- **Classificação automática**: regex em `categorias.ts:191-258`
  `classificarFinanceiro`. Detecta:
  - Pix (EndToEndID `E[A-Z0-9]{14}` ou palavra "Pix"+valor/instituição)
  - Boleto (linha digitável 47 dígitos)
  - Extrato (banco brasileiro + palavra-chave Saldo/Lançamentos/Extrato)
  - Extrai valor (R$ regex), instituição (Nubank/Itaú/Bradesco/...).
  Retorna null quando nada bate, mantendo flow manual.

### 11. Estrutura `inbox/<area>/<subtipo>/`
- **Áreas**: financeiro, saude, casa, outros.
- **Subtipos por área** (`categorias.ts:30-79`):
  - financeiro: `pix`, `extrato`, `nota`
  - saude: `exame`, `receita`
  - casa: `garantia`, `contrato`
  - outros: `outro` (path achatado: `inbox/outros`)
- **Exemplo de filename** (`path-resolver.ts:45-59`):
  `inbox/financeiro/pix/2026-05-12-143052-comprovante.pdf` +
  companion `inbox/financeiro/pix/2026-05-12-143052-comprovante.md`.

### 12. Frontmatter `.md`
- **Schema mínimo** (`src/lib/vault/frontmatter.ts:43`):
  `_schema_version: 1` carimbado SEMPRE no topo do YAML por
  `stringifyFrontmatter` (Q12 contrato com backend Python). Tudo
  serializado via `yaml.stringify({ lineWidth: 0 })`.
- **Campos canônicos** (varia por tipo, exemplo Evento em
  `src/lib/schemas/evento.ts:20-43`): `tipo`, `data` (ISO 8601 com
  fuso), `autor` (pessoa_a/pessoa_b), `modo`, `lugar?`, `bairro?`,
  `com[]`, `categoria?`, `intensidade` (1-5), `fotos[]`, `midia[]`,
  `para`. Inbox arquivo: `tipo: 'inbox_arquivo'`, `subtipo`, `arquivo`
  (path relativo), `mime_type`, `tamanho_bytes`, `origem`, `revisar:
  true` (flag para backend processar).

### 13. Syncthing
- **Status**: documentado, sem onboarding embutido no app.
- **Path esperado**: `~/Protocolo-Ouroboros/` (ADR-0014
  `docs/ADRs/0014-vault-pasta-dedicada.md`) — pasta nova dedicada,
  separada do Vault humano do Obsidian (`~/Controle de Bordo/`).
- **Vault default em runtime**: `FileSystem.documentDirectory + 'Ouroboros/'`
  (V4.0.2 fix em `src/lib/vault/permissions.ts:67-84` — HyperOS-proof,
  Armadilha A31). Usuário escolhe "Outra pasta" via SAF picker quando
  quer apontar para diretório visível no `/sdcard/X` (que aí pode ser
  sincronizado pelo Syncthing).
- **Documentação**: README.md:78 menciona "Nível C — celular físico
  via ADB. Só para Syncthing real". Sem onboarding interno guiado.
  Listado como Sprint M38 ("Compartilhamento via Syncthing — 4
  dispositivos") em `docs/FEATURES-CANONICAS.md:548`, status backlog.

### 14. Publicação
- **Tag mais recente**: `v1.0.0` (2026-05-02). Tags: `v0.1.0-m01`,
  `v0.2.0-m00-docs`, `v1.0.0`.
- **APK**: v1.0.0 **retirado do GitHub Releases** em 2026-05-02
  (README.md:11-14). Tag git permanece em main por histórico, release
  público deletado. Estado atual: **alpha-3** ("APK alpha-3 2026-05-09
  madrugada", README.md:21), com 21 sprints de refundação H-O fechadas
  + Onda E + Onda Q (2026-05-12). Pendente para v1.0 público:
  I2-OAUTH runtime + Bloco P (field test 7 dias).

## Achados colaterais

- **FAB genérico desalinhado**: `src/components/ui/FAB.tsx:21` usa
  `SIZE = 56` (não 64 como FABMenu/MenuCapturaVerde) e cor `colors.purple`
  (mesmo do FAB do menu lateral). Em Tarefas (`app/todo.tsx:563`) e
  Contadores (`app/contadores/index.tsx`) o "+" não obedece a regra
  Q4 de 64dp + cor distinta. Dor 7 só atendida no par lateral.
- **Timeline da Home não tappável**: `SecaoDiariosEventosAgrupado.tsx:105-138`
  renderiza itens em `View`, não `Pressable`. Não navega para detalhe
  nem para edição. Dor 9 fica meio truncada — galeria é o caminho,
  mas a Home ainda não é o atalho.
- **Galeria detalhe read-only**: `app/galeria/detalhe/[slug].tsx:1-15`
  comentário explícito. Não há rotas de edição por id
  (`/eventos/[id]/editar`, `/conquistas/[id]/editar`) — só `/exercicios/[slug]/editar`
  e `/contadores/[slug]` existem. Editar evento exige fluxo separado
  (não há tela de edição de evento; só registrar novo).
- **Slug do app permanece `ouroboros-mobile`**: deep links (intent
  filter, scheme `ouroboros`, EAS) usam slug antigo. Display name
  ficou OK; backend que recebe push/intent ainda referencia
  `com.ouroboros.mobile`.
- **Validação visual Onda Q parcial**: changelog admite apenas Q1+Q2+Q4
  validados no celular real (`ONDA-Q-2026-05-12.md:5`). Q3, Q5, Q6, Q7,
  Q8 dependem de validação live em dev-client ainda pendente.
- **OAuth Google Calendar**: Q0 liberou Console (Calendar API enabled,
  consent screen com 3 test users, SHA-1 confirmado). Runtime real
  (login Google + lista eventos em `/agenda`) NÃO validado.
- **A36 latente**: ANR em `DevLauncherErrorActivity` indica crash JS
  antes do React errboundary pegar. Apontado como risco para próximas
  sessões em `ONDA-Q-2026-05-12.md:188-199`.

## Recomendações para sprints no backend

- **Spec backend `processar-inbox-share` para áreas restantes**: o
  share intent já produz `inbox/financeiro/{pix,extrato,nota}/` +
  `inbox/saude/{exame,receita}/` + `inbox/casa/{garantia,contrato}/`
  + `inbox/outros/`. Validar que o pipeline ETL do `protocolo-ouroboros`
  consome todos 8 subtipos. Hoje só "financeiro/pix" tem extrator
  declarado (vide `feat(skill-d7-log): adiciona opus_visao ao _CATALOGO`).
- **Spec backend para `_schema_version: 1`**: o app SEMPRE carimba
  esse campo (`frontmatter.ts:43`). Backend Python deve ler e ignorar
  versões desconhecidas (forward-compat), e log de warning quando
  diferente da atual. Q12 já documenta o contrato em
  `docs/CONTRACT-MOBILE-BACKEND.md` (a verificar no app).
- **Spec backend `gerar-cache-galeria`**: o app lê só frontmatter dos
  .md para popular `/galeria`. Considerar cache leve no backend (em
  `.ouroboros/cache/galeria.json`) com pares (path, tipo, data, autor)
  para acelerar listagem em vaults grandes. Mobile carrega sob demanda.
- **Spec backend ETL para `inbox_arquivo.revisar: true`**: o flag é
  setado no share-receive (`app/share-receive.tsx` linha do
  `InboxArquivoMeta`). Backend deve consumir essa flag para listar
  arquivos pendentes de classificação humana e baixá-la quando o
  registro for processado em workflow Opus.
- **Spec coordenada para edição cross-platform**: galeria detalhe
  mobile é read-only por design. Edição "tudo que salvou" passa pelo
  desktop (Obsidian/editor `.md` direto) ou por novas telas
  `/<tipo>/[id]/editar`. Decidir contrato: mobile só captura + read,
  desktop edita. Ou abrir specs para 5 telas de edição faltantes
  (evento, marco, frase, foto, audio).
