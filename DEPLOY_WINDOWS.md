# QWI — Guia de instalação e deploy (Windows 11, sem Docker)

> **Para quem é este documento:** um agente de codificação que acabou de clonar
> este repositório do GitHub numa máquina **Windows 11** e precisa deixar o
> sistema no ar, acessível pela rede através de um **IP fixo que o dono do
> projeto vai informar**. Siga na ordem. Tudo o que você precisa saber está
> aqui — não invente etapas, não use Docker, não instale PostgreSQL/Redis.

---

## 1. O que é o projeto

**QWI (Quality Weekly Intelligence)** — sistema web para o departamento de
Qualidade registrar atividades semanais e gerar apresentações PPTX (weekly
reports), com recursos de IA opcionais (tradução, montagem de deck, copiloto
do gestor, sugestão de e-mail).

```
Quality_weekly_AI/
├── backend/    → API FastAPI (Python 3.12) — porta 8000
│   ├── app/            código da aplicação
│   ├── requirements.txt
│   ├── uploads/        anexos enviados (criada automaticamente)
│   └── qwi_dev.db      banco SQLite (criado automaticamente)
└── frontend/   → React + TypeScript + Vite — porta 3000
```

## 2. Regras deste deploy (não negociáveis)

- **SEM Docker.** Tudo roda nativo no Windows.
- **Banco = SQLite** (arquivo local). **NÃO** instale PostgreSQL. **NÃO** rode
  Alembic/migrações: o backend cria/atualiza as tabelas sozinho no startup
  (`Base.metadata.create_all`). Banco novo = arquivo novo criado sozinho.
- **NÃO** instale Redis nem suba Celery/Flower (estão no requirements.txt mas
  são opcionais; `ENABLE_ASYNC_PROCESSING=false` os desliga).
- O sistema deve subir escutando em `0.0.0.0` e ser acessado pelo **IP que o
  dono vai colocar no `.env`** (placeholder `<IP_DO_SERVIDOR>` abaixo).

## 3. Pré-requisitos (instalar se faltar)

| Ferramenta | Versão | Verificação |
|---|---|---|
| Python | 3.12.x (3.11 também funciona) | `py -3.12 --version` |
| Node.js | 20 LTS ou superior | `node --version` |
| Git | qualquer recente | `git --version` |

Instale pelo site oficial ou `winget install Python.Python.3.12 OpenJS.NodeJS.LTS`.

## 4. Backend — instalação

Em um **PowerShell** na pasta do repositório:

```powershell
cd backend
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1        # se bloquear: Set-ExecutionPolicy -Scope Process Bypass
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Notas de dependências:
- Tudo tem wheel pré-compilado para Windows (bcrypt, Pillow, matplotlib,
  numpy…) — não precisa de compilador.
- `psycopg2-binary`, `redis`, `celery`, `flower` instalam mas **não são
  usados** neste deploy. Não os configure.

### 4.1 O arquivo `.env` do backend

Crie `backend\.env` com o conteúdo abaixo. Os valores entre `<...>` serão
informados pelo dono do projeto — deixe o placeholder e **pergunte a ele**;
não invente valores.

```ini
# ── Banco (SQLite — NÃO trocar para Postgres) ──────────────────────────
DATABASE_URL=sqlite:///./qwi_dev.db

# ── Segurança ──────────────────────────────────────────────────────────
SECRET_KEY=<GERAR: python -c "import secrets; print(secrets.token_urlsafe(64))">
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# ── Usuário root/admin (criado no 1º start — ver seção 5.1) ────────────
# TROQUE a senha antes de subir. O e-mail deve ter um domínio válido
# (evite .local/.test — são reservados e o login rejeita).
ROOT_EMAIL=admin@qwi.com
ROOT_PASSWORD=<DEFINA uma senha forte>
ROOT_NAME=Administrador
ROOT_EMPLOYEE_ID=ROOT

# ── Rede: IP informado pelo dono do projeto ────────────────────────────
# CORS precisa listar as URLs pelas quais o FRONTEND será acessado.
CORS_ORIGINS=["http://<IP_DO_SERVIDOR>:3000","http://localhost:3000","http://127.0.0.1:3000"]

# ── IA (ver seção 6 — começa desligada/local, o dono informa a API) ────
LLM_PROVIDER=ollama
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
LLM_RATE_LIMIT_PER_MIN=3
LLM_FALLBACK_TO_OLLAMA=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:e2b

# ── E-mail SMTP (ver seção 7 — o dono informa; vazio = recurso desativado) ─
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_TLS=true

# ── App ────────────────────────────────────────────────────────────────
DEBUG=false
ENABLE_ASYNC_PROCESSING=false
UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE_MB=50
LOG_LEVEL=INFO
```

### 4.2 Subir o backend

```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Teste (deve responder `{"status":"healthy",...}`):

```powershell
curl http://localhost:8000/api/health
```

## 5. Banco de dados — o que você precisa saber

- **SQLite**, arquivo `backend\qwi_dev.db`. Criado e atualizado
  **automaticamente** no primeiro start — nenhum comando manual.
- Não há usuários seed: o primeiro acesso é feito pela tela **Criar conta**
  do próprio sistema (nome, e-mail, matrícula, setor, cargo, senha).
- **Backup** = copiar o arquivo `.db` com o backend parado (junto com a pasta
  `uploads/`, que guarda os anexos e os PPTX gerados em `uploads/reports/`).
- Se um dia migrar de máquina: levar `qwi_dev.db` + `uploads/` e pronto.

### 5.1 Usuário root/admin

No **primeiro start**, o sistema cria automaticamente **um** usuário root/admin
com as credenciais `ROOT_*` do `.env` (seção 4.1). Características:
- **Não aparece no organograma** (é conta de administração/testes, não de um
  funcionário real).
- É o **único** que pode, no FAQ (seção do sistema): **fechar e responder**
  solicitações, e **definir quais usuários** recebem por e-mail as novas
  solicitações abertas.
- Login com `ROOT_EMAIL` / `ROOT_PASSWORD`.

Regras importantes:
- **Troque `ROOT_PASSWORD`** no `.env` antes de expor o sistema.
- O `ROOT_EMAIL` precisa de um **domínio válido** — não use `.local`/`.test`
  (TLDs reservados que o login rejeita). O default `admin@qwi.com` funciona.
- O root só é criado se **ainda não existir** nenhum usuário admin — trocar as
  credenciais no `.env` depois do 1º start **não** recria nem atualiza o
  existente. Para redefinir: peça ajuda ao administrador (ou apague a linha do
  usuário admin no banco e reinicie para recriar com as novas credenciais).

## 6. IA — dois modos (controlado 100% pelo `.env`)

O sistema funciona **sem IA nenhuma** (os botões de IA respondem 503 com
mensagem clara; todo o resto opera normal). Não trate 503 nesses endpoints
como bug de instalação.

**Modo A — Ollama local (padrão):** se a máquina tiver
[Ollama](https://ollama.com) com um modelo (`ollama pull gemma4:e2b`), nada a
configurar. Se não tiver, tudo bem — deixe como está.

**Modo B — API aberta do dono (OpenAI-compatível):** o dono do projeto vai
informar a URL, a chave e o modelo. Quando ele passar, basta editar o `.env`
e reiniciar o backend:

```ini
LLM_PROVIDER=openai_compat
LLM_BASE_URL=<URL_DA_API>        # ex.: https://api.exemplo.com/v1 (endpoint /chat/completions)
LLM_API_KEY=<CHAVE_SE_EXIGIR>
LLM_MODEL=<NOME_DO_MODELO>
LLM_RATE_LIMIT_PER_MIN=3         # a API do dono aceita SÓ 3 req/min — NÃO aumente sem ele autorizar
```

- O backend já tem **fila global** que respeita esse limite e **fallback**
  automático para o Ollama se a API cair (`LLM_FALLBACK_TO_OLLAMA=true`).
- Todas as features de IA (tradução, deck, rollup, e-mail) trocam de provedor
  juntas — não há mais nada a configurar.

## 7. E-mail (SMTP)

O dono vai informar servidor e porta depois. Até lá, deixe `SMTP_HOST` vazio —
o botão "Enviar e-mail" responde 503 com a mensagem *"Envio de e-mail ainda
não configurado (SMTP). Avise o administrador."* (comportamento esperado).
Quando ele passar os dados, preencha o bloco SMTP do `.env` e reinicie.

## 8. Frontend — build e servidor

```powershell
cd frontend
npm install
npm run build          # gera dist/ (tsc + vite build — deve terminar sem erros)
npm run preview        # serve o build em 0.0.0.0:3000 com proxy para o backend
```

O `vite.config.ts` já tem o bloco `preview` configurado com proxy de `/api` e
`/uploads` para `http://127.0.0.1:8000` — por isso o **backend e o frontend
devem rodar na mesma máquina**, e o navegador só precisa alcançar a porta
3000. Não crie `.env` no frontend; a API é consumida por caminho relativo
`/api` (nada de URL hardcoded).

Acesso final: **`http://<IP_DO_SERVIDOR>:3000`**

## 9. Firewall e permanência (subir como "servidor")

Libere as portas no Firewall do Windows (PowerShell **como administrador**):

```powershell
New-NetFirewallRule -DisplayName "QWI Frontend 3000" -Direction Inbound -Protocol TCP -LocalPort 3000 -Action Allow
New-NetFirewallRule -DisplayName "QWI Backend 8000"  -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

Para os dois processos sobreviverem a logoff/reinício, registre-os no
**Agendador de Tarefas** (Task Scheduler), um para cada, com gatilho
"Ao inicializar" e "Executar estando o usuário conectado ou não":

- Backend → programa: `C:\<caminho>\backend\venv\Scripts\python.exe`
  argumentos: `-m uvicorn app.main:app --host 0.0.0.0 --port 8000`
  iniciar em: `C:\<caminho>\backend`
- Frontend → programa: `C:\Program Files\nodejs\npm.cmd`
  argumentos: `run preview`
  iniciar em: `C:\<caminho>\frontend`

(Alternativa equivalente: NSSM — `nssm install` para cada processo.)

## 10. Checklist de verificação (faça TODOS antes de encerrar)

1. `curl http://localhost:8000/api/health` → `{"status":"healthy"}`.
2. `curl http://<IP_DO_SERVIDOR>:8000/api/health` de OUTRA máquina da rede → ok.
3. Abrir `http://<IP_DO_SERVIDOR>:3000` no navegador → tela de login carrega.
4. **Criar conta** → entra direto e o guia de primeiro acesso (tour) aparece.
5. Agenda → clicar num dia → criar atividade com um anexo `.xlsx` → salva e o
   anexo aparece.
6. Relatórios → selecionar a atividade → **Montagem** → **Gerar apresentação**
   → baixa um `.pptx` válido.
7. Sem SMTP configurado: menu ⋮ do histórico → Enviar e-mail → Enviar →
   mensagem clara de SMTP não configurado (503) — **esperado, não é bug**.

## 11. Problemas conhecidos e soluções

| Sintoma | Causa/solução |
|---|---|
| `Activate.ps1` bloqueado | `Set-ExecutionPolicy -Scope Process Bypass` na sessão |
| Porta 8000/3000 ocupada | `netstat -ano | findstr :8000` → `taskkill /PID <pid> /F` |
| Erro de CORS no navegador | A URL usada no navegador precisa constar EXATAMENTE em `CORS_ORIGINS` do `.env` (esquema+IP+porta); reinicie o backend após editar |
| Botões de IA retornam 503 | Normal sem Ollama/API configurados (seção 6) |
| Enviar e-mail retorna 503 | Normal sem SMTP (seção 7) |
| PPTX não gera | Veja o log do uvicorn; confirme que a pasta `uploads/` tem permissão de escrita |
| `npm run build` falha em `tsc` | Não "conserte" alterando `tsconfig`; o repositório compila limpo — rode `git status` e confira se nada foi modificado localmente |

## 12. Fatos do sistema que você NÃO deve "corrigir"

- **Semanas**: convenção própria da empresa — W1 é a semana (seg–dom) que
  contém 1º de janeiro e o ano da semana é o do seu **domingo**
  (ex.: 10–16/08/2026 = W33/2026). Implementada em `backend/app/core/dates.py`
  e `frontend/src/lib/dates.ts`, com testes. **Não** troque por ISO-8601.
- **Acesso a weeklys**: mesmo **setor** vê os weeklys dos colegas; cargos de
  gestão (Supervisor, Chefe, Gerentes) veem todos; além disso o dono pode
  conceder acesso individual por matrícula (Configurações → Compartilhamento).
  Regra em `backend/app/api/routes/users.py::can_view_user_weeklys`.
- **Erros de formulário**: o backend responde 400 com
  `{detail: {field, message, hint}}` e o frontend consome via
  `parseApiError` — mantenha esse contrato em qualquer ajuste.
- **IA aprende o padrão do usuário**: cada PPT gerado alimenta
  `user_style_profiles` (não é bug o "Montar com IA" mudar de resultado com o
  tempo — é o esperado).
- Idiomas da interface: pt/en/ko via i18n próprio (`frontend/src/i18n`).

---

*Dúvidas que este documento não cobre (valores de `<IP_DO_SERVIDOR>`, URL/chave
da API de IA, servidor SMTP): pergunte ao dono do projeto. Não chute.*
