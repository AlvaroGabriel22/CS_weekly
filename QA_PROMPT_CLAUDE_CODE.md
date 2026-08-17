# Prompt para Claude Code — QA exaustivo do QWI

> Cole o bloco abaixo inteiro no Claude Code (modelo capaz / Opus ou equivalente).
> O agente deve executar os testes, criar agentes especializados e documentar **tudo** em `QA_testes.md`.

---

## PROMPT (copiar a partir daqui)

```
Você é o lead de QA do projeto Quality Weekly Intelligence (QWI) em /home/alvaro/Documentos/Quality_weekly_AI.

## Missão
Realizar testes robustos, ponta a ponta, em TODO o projeto (backend + frontend + banco + IA + PPTX + ACL + ops + carga/limites). Criar agentes/subtarefas especializados por domínio. Para CADA erro, bug, falha, inconsistência, gap de cobertura, contrato quebrado, regra de negócio violada, saturação, timeout, degradação ou risco arquitetural encontrado, documentar em:

**arquivo obrigatório:** `/home/alvaro/Documentos/Quality_weekly_AI/QA_testes.md`

Não invente sucesso. Se não conseguir rodar algo, registre como BLOQUEIO com causa. Código é a fonte da verdade; `docs/DOCUMENTACAO-COMPLETA.md` ajuda mas está parcialmente desatualizado (ignore menções a Timeline/Dashboard antigos; use Agenda/Relatórios/Departamentos e as rotas reais do código).

## Regras de execução
1. Antes de testar, leia a estrutura real: `backend/app/main.py`, `backend/app/api/routes/*`, `backend/app/models/*`, `backend/app/services/*`, `frontend/src/App.tsx`, `frontend/src/lib/api.ts`, `docker-compose.yml`, `backend/.env.example`, testes existentes em `backend/tests/` e `frontend/src/__tests__/`.
2. Rode a suíte existente primeiro (`cd backend && pytest tests/ -v`; `cd frontend && npm run test:run` se aplicável) e capture falhas.
3. Amplie testes quando necessário (pytest / Vitest / scripts HTTP / checks de schema). Prefira testes automatizados executáveis; quando for só inspeção estática, diga claramente.
4. Use mocks/stubs para LLM quando o Ollama não estiver disponível, MAS também teste o caminho real se o serviço estiver up — e sempre teste o FALLBACK quando a IA falha.
5. NÃO faça commit, NÃO altere secrets, NÃO apague dados de produção. Use SQLite de teste / DB de dev / TestClient.
6. Testes de carga SOMENTE no ambiente local/docker deste repo. Nunca contra Ollama/OpenAI de produção de terceiros nem URLs externas. Pare o ramp-up no primeiro sinal de OOM host, disco cheio ou instabilidade do SO.
7. Ao final, `QA_testes.md` deve estar completo, priorizado e acionável. Inclua a seção **Limites de carga** com números reais.

## Agentes obrigatórios (crie e execute cada um; pode paralelizar)
Para cada agente: objetivo, escopo, passos, evidências, achados → append em `QA_testes.md`.

### Agente A — Arquitetura & camadas
- Validar separação routes → services → repositories → models.
- Dependências circulares, god-services, lógica de negócio em rotas.
- Startup: `create_all`, `run_migrations()`, seed de template.
- CORS, static `/uploads`, health `GET /api/health`.
- Drift entre docs e código.
- Redis/Celery no compose vs BackgroundTasks no caminho de atividades (documentar inconsistência se houver).

### Agente B — Banco & modelagem
Arquivos: `backend/app/models/postgres_models.py`, `models/permissions.py`, `core/database.py`, `core/migrations.py`, `db/migrations/`, seeds.
Validar:
- Tabelas: users, writing_profiles, templates, activities, activity_metadata, attachments, weekly_reports, slide_layout_prefs, department_rollups, user_flags, weekly_access_grants, email_recipients; ACL (ActivityShare, WeeklyPermission, FileShare, AuditLog, PermissionChange, DepartmentRole).
- Constraints: week 1–53; unique email/employee_id; unique weekly (user+year+week+version); unique rollup sector+week; unique grants.
- Cascades/FKs, índices, nullability, enums/roles/sectors.
- Migrations vs `create_all` (risco de drift).
- Integridade: deletar user/activity e efeitos colaterais.
- Relatórios de versão: regenerar não sobrescreve download antigo.

### Agente C — Auth, segurança & ACL
Rotas: `/api/auth/*`, `/api/users/*`, deps em `api/deps.py`, `core/security.py`, `domain/permission_rules.py`, `services/permission_service.py`.
Testar:
- register/login/me/reset-password/roles/sectors.
- JWT inválido/expirado/ausente → 401.
- Usuário inativo → 401.
- Contratos de erro de campo no register: `{field, message, hint}`.
- reset-password: exige email + employee_id; sem enumeração; sem envio de e-mail.
- ACL weeklies de colegas: self/admin; MANAGEMENT_ROLES; mesmo **sector** (NUNCA `department`); WeeklyAccessGrant.
- access-grants CRUD; role change; password change; photo upload (limites mime/tamanho).
- Tentativas de acessar activity/weekly/attachment de outro usuário → 403/404 conforme design.

### Agente D — APIs & rotas (contrato HTTP completo)
Cobrir TODAS as rotas registradas em `main.py` / routers:
- Auth, Users, Activities, Weekly, AI (department-rollup, deck-draft, email-suggestion, translate), PPTX (`/api/pptx/*`), Health.
Para cada endpoint:
- método, path, auth, status happy-path, validações 400/422, 401/403/404, 503 quando SMTP/LLM off.
- Paginação activities (`page`, `page_size` ≤ 200), filtros week/year/dates/timezone.
- Upload attachments: multipart, `MAX_UPLOAD_SIZE_MB` (50), tipos.
- Weekly generate: `activity_ids` min 1; regenerate/versioning; download.
- send-email sem SMTP → 503 claro.
Documentar qualquer endpoint morto, sem schema, ou divergente do frontend.

### Agente E — Regras de negócio & services
Arquivos: `services/business.py`, `ai_processor.py`, `text_sanitize.py`, `core/activity_directives.py`, `core/dates.py`.
Regras críticas a provar/refutar:
1. Atividade mínima: title obrigatório; description/attachments opcionais; auto department, activity_date, ISO week/year, include_in_weekly=true.
2. HTTP retorna ANTES da IA terminar (BackgroundTasks).
3. Vision de imagem só com diretiva (`/analisar imagem`, `/analyze image`, variantes EN).
4. Processamento de anexos: image (condicional), xlsx/csv (KPI), pdf/docx/txt, pptx só armazena.
5. Pipeline weekly: validate owned → GENERATING → analyze attachments → dossier → 3 passos LLM → JSON (`schemas/weekly_content.py`) → PPTX → COMPLETED; fallback se LLM falhar.
6. Versionamento user/year/week; path `uploads/reports/weekly_{report_id}.pptx`.
7. Mandato de escrita: sem frases filler; charts só com números reais; layout profiles executive|operational|analytical|field_case.
8. Datas ISO week consistentes (`core/dates.py` + frontend `lib/dates.ts`).

### Agente F — Estrutura da chamada à IA (obrigatório e profundo)
Arquivos: `llm_service.py`, `prompt_composer.py`, `ai_processor.py`, `config.py`, `ai_features.py`, `translate.py`.
Testar/inspecionar:
- Seleção de provider: `LLM_PROVIDER` ollama vs openai_compat; fallback `LLM_FALLBACK_TO_OLLAMA`.
- `LLMService.generate(prompt, system_prompt?, images?, json_mode?)` — contrato de resposta, rate limit, timeouts, erros.
- Prompts: activity analysis, weekly analysis, presentation plan, sector playbooks (`SECTOR_PLAYBOOKS`), `ANALYSIS_MANDATE`.
- json_mode + validação Pydantic de `weekly_content`; sanitize (`text_sanitize`).
- translate: preserva ordem; targets pt|en|ko; 503 se LLM down.
- department-rollup: só management; cache sector/year/week; `force`.
- deck-draft e email-suggestion: inputs, falhas, idiomas.
- Comportamento com Ollama down: fallback de conteúdo weekly SEMPRE gera PPT.
- Prompt injection / diretivas maliciosas em description (pelo menos análise de risco + testes básicos).
- Tokens/contexto: OLLAMA_NUM_CTX / NUM_PREDICT — riscos de truncamento.

### Agente G — PPTX
Arquivos: `pptx_service.py`, `pptx_builder.py`, `pptx_layout.py`, `pptx/*`, testes existentes.
- Blocos: device_info, measurement_table, generic_table, countermeasure_table, chart, image_row, text/highlight.
- Layouts; imagens resolvidas vs quebradas; conteúdo vazio/fallback.
- Download binário válido (.pptx).
- Rotas paralelas `/api/pptx/*` vs fluxo weekly principal (duplicação/risco).

### Agente H — Frontend
Stack: React 18, Vite, TanStack Query, Axios, Router, i18n PT/EN/KO.
Rotas: `/login`, `/register`, `/recuperar-senha`, `/`, `/agenda`, `/relatorios`, `/departamentos`, `/departamentos/:sector`, `/colegas/:userId`, `/perfil`, `/configuracoes` + redirects legacy.
Testar (Vitest + inspeção + fluxos manuais/scriptados se possível):
- Guard de auth; 401 limpa `qwi_token` e redireciona `/login`.
- `lib/api.ts` proxy `/api` e `/uploads`.
- Agenda: CRUD, optimistic IDs `otimista-*`, calendário, painel.
- Relatórios: wizard generate, history, slides, email dialog, erros 502/503.
- Org chart + rollup panel (management).
- `parseApiError` / ErrorBoundary / Empty/Error/Loading.
- i18n keys faltando; formulários alinhados a Pydantic (senha ≥6, nome ≥2).
- Tour flags; slide-layout prefs; writing-profile.
- Acessibilidade básica e responsividade crítica (quebra óbvia).
- Divergências frontend↔API (campos, paths, enums).

### Agente I — Tratamento de erros & resiliência
- Hierarquia `QWIException` → 404/401/403/422; handler global `{"detail": ...}`.
- Falha SMTP, LLM, disco uploads cheio, arquivo inexistente, DB down.
- Race: delete activity enquanto gera weekly; generate duplicado.
- Uploads inválidos / oversized.
- Consistência de mensagens PT no backend vs i18n frontend.

### Agente J — E2E ponta a ponta (fluxo ouro)
Executar (ou simular com TestClient + asserts de arquivo) o fluxo:
1. Register usuário
2. Login → token
3. Create activity (com e sem anexo; com e sem `/analisar imagem`)
4. List/filter na agenda (API)
5. Generate weekly
6. Poll/get report COMPLETED (ou fallback)
7. Download PPTX (magic bytes / open com python-pptx)
8. Regenerate → version incrementa; download antigo ainda ok
9. Colleague path: user B mesmo sector vê; outro sector sem grant não vê
10. Forgot password com matrícula
11. send-email com SMTP off → 503
12. translate + email-suggestion se LLM disponível

Documentar tempo aproximado e pontos de flakiness.

### Agente K — Ops / config / Docker
- `.env.example` vs `Settings` em `config.py` (vars documentadas mas não lidas).
- `docker-compose.yml`: postgres, redis, app, celery queues, flower, frontend.
- Healthchecks; portas (cuidado com drift README 5433 vs 5432).
- CORS_ORIGINS; SECRET_KEY fraca em exemplo.

### Agente L — Carga, saturação e até onde o sistema aguenta (obrigatório)
Objetivo: descobrir o **ponto de ruptura** do QWI (API, banco, uploads, PPTX e especialmente a IA) e documentar capacidade útil vs. colapso.

**Ferramentas (use o que estiver disponível; se faltar, escreva um script Python `httpx`/`asyncio` em `/tmp` ou `backend/scripts/` sem commitar se não for necessário):** locust, k6, wrk, vegeta, ou script async próprio. Meça CPU/RAM/disco do host, Postgres, Redis, processo uvicorn e Ollama (`nvidia-smi` se GPU). Capture p50/p95/p99, taxa de erro, timeouts, 429/503, fallback da IA.

**Segurança do teste:** só localhost/docker; usuários/dados sintéticos; limpe uploads gerados no fim se possível; não deixe o host ir a 100% RAM.

#### L1 — Baseline (1 usuário, 1 fluxo)
Medir tempos médios de:
- `POST /api/auth/login`
- `GET /api/health`
- `GET /api/activities` (página)
- `POST /api/activities` (sem IA pesada)
- `POST /api/weekly/generate` até COMPLETED ou fallback
- `GET /api/weekly/{id}/download`
- 1 chamada `LLMService.generate` (se Ollama up) e 1 `POST /api/ai/translate`

Registrar hardware (CPU cores, RAM, GPU se houver), `LLM_PROVIDER`, `LLM_RATE_LIMIT_PER_MIN`, workers uvicorn, Celery on/off.

#### L2 — API / sistema (sem LLM real — mockar provider se preciso para isolar o app)
Ramp-up: 1 → 5 → 10 → 25 → 50 → 100 usuários virtuais (ou conexões concorrentes). Duração ~30–60s por degrau, ou até quebrar.
Cenários:
- Login + GET me + GET dashboard (leitura)
- CRUD de atividades concorrente (vários users)
- Listagem paginada + filtros de semana
- Upload paralelo de anexos (vários arquivos 1–5MB; também 1 arquivo perto do limite 50MB)
- Download concorrente de PPTX
- Mix 70% leitura / 20% escrita / 10% generate (generate pode ser mockado aqui)

Critérios de saturação a registrar:
- latência p95 > 2s em rotas leves ou > 30s em generate
- error rate > 5%
- 500/502/503, connection reset, pool do SQLAlchemy esgotado
- event loop bloqueado (BackgroundTasks acumulando)
- disco `uploads/` crescendo sem bound

#### L3 — Carga na IA (o mais importante)
Se Ollama/LLM estiver down: rode o mesmo plano contra o **fallback** e marque como “IA indisponível — capacidade do fallback”. Ainda assim teste fila/`LLM_RATE_LIMIT_PER_MIN`.

Se LLM estiver up, rampe **chamadas concorrentes à IA** (não só HTTP vazio):
1. `LLMService.generate` direto (texto curto, texto longo, `json_mode=true`)
2. `POST /api/ai/translate` com N textos (1, 10, 50)
3. `POST /api/ai/email-suggestion`
4. `POST /api/ai/deck-draft` com vários `activity_ids`
5. `GET/POST /api/ai/department-rollup` (cache hit vs `force` miss)
6. Pipeline weekly completo (3 passos LLM + PPTX) com 1, 3, 5, 10 gerações simultâneas de usuários diferentes
7. Criar N atividades que disparam `process_activity_in_background` (com e sem `/analisar imagem` + anexo)
8. Mix: 5 weekly generate + 20 translates + 30 activity creates ao mesmo tempo

Degraus sugeridos de concorrência na IA: 1, 2, 4, 8, 16 (pare antes se timeout 300s, OOM no Ollama, ou host instável).

O que medir na IA:
- tempo até primeiro token / tempo total (se observável)
- timeouts `httpx` 300s vs 5s de health
- eficácia do `RateLimitedProvider` / `LLM_RATE_LIMIT_PER_MIN` (fila vs 429 vs espera silenciosa)
- fallback `LLM_FALLBACK_TO_OLLAMA` sob pressão
- qualidade degradada: JSON inválido, truncamento `OLLAMA_NUM_CTX`/`NUM_PREDICT`, PPT via `_build_fallback_content`
- vision: 1 vs N imagens concorrentes (pesado — poucos workers)
- fila Celery `ai_tasks` vs BackgroundTasks in-process (documentar qual caminho realmente aguenta)
- saturacão GPU/CPU do Ollama vs FastAPI ocioso ou vice-versa (gargalo)

#### L4 — Banco e persistência sob carga
- inserts concorrentes de activities/attachments
- unique weekly (user+year+week+version) sob generate duplicado simultâneo
- rollup unique sector+week com `force` paralelo
- pool de conexões: esgotamento, queries lentas em listagens com muita activity
- locks / race no status GENERATING → COMPLETED

#### L5 — PPTX sob carga
- N gerações de deck ao mesmo tempo
- tamanho do .pptx e tempo de build
- downloads simultâneos do mesmo arquivo

#### L6 — Ponto de ruptura (breaking point)
Continue o ramp-up até UM destes:
- error rate ≥ 10%
- p95 explode (>10× baseline)
- timeouts em massa
- processo morto (OOM, uvicorn hang)
- LLM para de responder / fallback 100%
- Postgres recusa conexões

Documente: **último degrau estável** vs **primeiro degrau que quebra**, com números.

Entregáveis obrigatórios em `QA_testes.md` (seção Limites de carga):
- tabela degrau × VU/concorrência × rps × p50/p95/p99 × %erro × CPU/RAM (app, DB, Ollama)
- gargalo dominante (IA, event loop, DB pool, disco, Celery, GPU)
- capacidade recomendada para uso real (ex.: “até X weekly/min e Y translates concorrentes com qualidade”)
- o que acontece além do limite (fila, 503, fallback, perda de job, 500)
- achados QA-xxx para ausência de backpressure, rate limit ineficaz, memory leak, jobs órfãos, etc.

## Formato obrigatório de `QA_testes.md`

```markdown
# QA Testes — Quality Weekly Intelligence (QWI)

- Data: YYYY-MM-DD
- Branch/commit: ...
- Ambiente: (local/docker, LLM on/off, DB)
- Executado por: Claude Code (agentes A–L)

## Sumário executivo
- Total de achados: N
- Críticos / Altos / Médios / Baixos / Informativos
- Suítes rodadas: pytest X failed, vitest Y failed, E2E Z, carga (último degrau estável / ruptura)
- Veredito: APROVADO COM RESSALVAS | REPROVADO | BLOQUEADO

## Matriz de cobertura
| Área | Cobertura | Status | Notas |
|------|-----------|--------|-------|
| Arquitetura | | | |
| Banco | | | |
| Auth/ACL | | | |
| APIs | | | |
| Regras de negócio | | | |
| IA / prompts | | | |
| PPTX | | | |
| Frontend | | | |
| Erros/resiliência | | | |
| E2E | | | |
| Ops | | | |
| Carga API/sistema | | | |
| Carga IA | | | |
| Ponto de ruptura | | | |

## Achados
### [QA-001] Título curto
- Severidade: Crítica|Alta|Média|Baixa|Info
- Área: ...
- Agente: ...
- Evidência: comando, arquivo:linha, response HTTP, stacktrace
- Impacto: ...
- Como reproduzir: passos
- Esperado vs obtido
- Sugestão de correção (curta)

(repita QA-002...)

## Falhas de testes automatizados
- lista com nome do teste + mensagem

## Gaps (não testado / bloqueado)
- ...

## Riscos arquiteturais / dívida
- ...

## Checklist E2E ouro
- [ ] cada passo com PASS/FAIL

## Limites de carga
### Ambiente de carga
- hardware, workers, LLM on/off, rate limit, ferramenta usada

### Baseline (1 VU)
| Endpoint/fluxo | p50 | p95 | p99 | notas |
|----------------|-----|-----|-----|-------|

### Ramp-up API
| Degrau (VU) | rps | p95 | %erro | CPU/RAM | status estável/quebra |

### Ramp-up IA
| Concorrência LLM | fluxo | latência | timeouts | fallback% | GPU/CPU Ollama | status |

### Ponto de ruptura
- Último estável: ...
- Primeiro quebra: ...
- Gargalo dominante: ...
- Capacidade recomendada: ...

## Anexos
- comandos exatos usados
- versões relevantes (python, node, se possível)
- scripts de carga (path) e raw metrics se gerados
```

## Severidade
- Crítica: perda de dados, bypass auth/ACL, PPT/IA corrompe fluxo principal, secret leak, OOM/crash sob carga baixa, jobs de IA perdidos sem rastreio
- Alta: regra de negócio quebrada, 500 em fluxo feliz, versionamento errado, ruptura cedo (poucos usuários), rate limit da IA inútil, pool DB esgota
- Média: contrato API inconsistente, UX de erro ruim, gap de validação, latência p95 ruim mas sem perda
- Baixa: docs drift, naming, DX
- Info: melhoria, observação, capacidade acima do esperado

## Critérios de pronto
1. Todos os agentes A–L executados (ou marcados bloqueados com motivo).
2. `QA_testes.md` criado na raiz do repo com achados numerados.
3. Achados com evidência reproduzível.
4. Suíte existente rodada e resultados registrados.
5. Seção E2E preenchida.
6. Seção **Limites de carga** preenchida com números (não só opinião): baseline, ramp-up, ruptura, gargalo, capacidade recomendada.
7. Nenhuma falha silenciosa: se pulou teste, está em Gaps.

Comece agora: explore o repo, rode as suítes existentes, dispare os agentes, e vá preenchendo `QA_testes.md` de forma incremental até cobrir tudo.
```

---

## Como usar
1. Abra o Claude Code na pasta do projeto.
2. Cole o prompt completo (bloco acima).
3. Deixe rodar; ao final abra `QA_testes.md` na raiz.
4. Se quiser foco parcial, acrescente no final: “Priorize agora só Agente F (IA), Agente J (E2E) e Agente L (carga)”.
