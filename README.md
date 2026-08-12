# Quality Weekly Intelligence (QWI)

Plataforma corporativa de produtividade baseada em Inteligência Artificial para criação automática de Weekly Reports.

## Visão Geral

O QWI reduz o processo manual de construção de relatórios semanais. Durante a semana, o funcionário registra em segundos o que realizou e anexa evidências. Ao final, a IA analisa e organiza o conteúdo, enquanto o sistema cria um PowerPoint profissional automaticamente.

O MVP foi desenhado para reduzir o esforço semanal de aproximadamente 4 horas para uma revisão final de 15–30 minutos.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend | React, TypeScript, Vite, TailwindCSS, Shadcn/UI, React Query |
| Backend | FastAPI (Python) |
| Banco | PostgreSQL + SQLAlchemy |
| IA | Gemma4 via Ollama (camada LLMService desacoplada) |

## Arquitetura

```
backend/
├── app/
│   ├── api/routes/     # Endpoints REST
│   ├── core/           # Config, database, security, exceptions
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic schemas
│   └── services/
│       ├── llm_service.py      # Camada de abstração IA
│       ├── prompt_composer.py  # Engenharia de prompt modular
│       └── business.py         # Lógica de negócio
frontend/
├── src/
│   ├── components/     # UI components (Shadcn)
│   ├── pages/          # Páginas da aplicação
│   ├── contexts/       # Auth context
│   └── lib/            # API client, utils
```

## Pré-requisitos

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 (ou Docker)
- Ollama com modelo Gemma4 (opcional para IA)

## Início Rápido

### 1. Banco de dados

```bash
docker compose up -d db
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

### Ou use o script de desenvolvimento:

```bash
chmod +x scripts/dev.sh
./scripts/dev.sh
```

Acesse: **http://localhost:3000**

## Funcionalidades MVP

- **Autenticação** — Registro e login com JWT
- **Dashboard** — Atividades, dias preenchidos, arquivos e ações principais
- **Timeline** — Registro cronológico simples e editável
- **Registro Inteligente** — IA extrai metadados estruturados de cada atividade
- **Upload de Arquivos** — Imagens, Excel, CSV, PDF, Word, PowerPoint e TXT
- **Análise em background** — O registro não espera a IA terminar
- **Geração de Weekly** — IA organiza o conteúdo e o script cria o PowerPoint
- **PowerPoint sem template** — Layout corporativo criado automaticamente pelo sistema
- **Histórico** — Versões anteriores disponíveis para download

## Fluxo do MVP

1. O funcionário registra **o que fez** e, se necessário, adiciona detalhes.
2. Evidências e documentos podem ser anexados sem configuração adicional.
3. A IA processa atividades e arquivos em background.
4. No final da semana, o funcionário clica em **Gerar Weekly**.
5. O sistema cria e disponibiliza o arquivo `.pptx` para revisão e download.

O menu do MVP contém somente: **Dashboard, Timeline, Relatórios e Perfil**.

## API

Documentação interativa: **http://localhost:8000/docs**

### Endpoints principais

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/auth/register` | Criar conta |
| POST | `/api/auth/login` | Login |
| GET | `/api/dashboard` | Estatísticas da semana |
| GET/POST | `/api/activities` | Listar/criar atividades |
| POST | `/api/weekly/generate` | Gerar weekly report |
| GET | `/api/weekly` | Listar relatórios |
| PATCH | `/api/users/writing-profile` | Configurar IA |

## Identidade Visual

- Tema claro obrigatório
- Cor institucional: `#0C379C` (uso moderado)
- Inspiração: Linear, Notion, Vercel, Stripe
- Tipografia: Inter
- Micro-animações suaves

## Testes

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

## Licença

Proprietário — Uso interno corporativo.
