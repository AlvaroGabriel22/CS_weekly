# QWI — Quality Weekly Intelligence

**Documentação completa do projeto**  
**Versão:** 0.1.0 (MVP)  
**Última atualização:** agosto de 2026

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Problema e objetivo](#2-problema-e-objetivo)
3. [O que o sistema faz](#3-o-que-o-sistema-faz)
4. [O que já está implementado](#4-o-que-já-está-implementado)
5. [Como funciona — fluxos principais](#5-como-funciona--fluxos-principais)
6. [Arquitetura do sistema](#6-arquitetura-do-sistema)
7. [Stack tecnológica](#7-stack-tecnológica)
8. [Modelo de dados](#8-modelo-de-dados)
9. [Camada de Inteligência Artificial](#9-camada-de-inteligência-artificial)
10. [Geração de PowerPoint](#10-geração-de-powerpoint)
11. [API REST](#11-api-rest)
12. [Frontend](#12-frontend)
13. [Infraestrutura e execução](#13-infraestrutura-e-execução)
14. [Testes](#14-testes)
15. [Identidade visual e UX](#15-identidade-visual-e-ux)
16. [Limitações conhecidas e roadmap](#16-limitações-conhecidas-e-roadmap)
17. [Glossário](#17-glossário)

---

## 1. Visão geral

O **QWI (Quality Weekly Intelligence)** é uma plataforma corporativa de produtividade baseada em Inteligência Artificial, desenvolvida para o departamento de **Qualidade da divisão MX CS**. Seu propósito central é **automatizar a criação de Weekly Reports** — relatórios semanais que documentam atividades, impactos e evidências de qualidade.

Em vez de o funcionário reconstruir manualmente, no final da semana, tudo o que fez durante cinco dias, o QWI permite **registrar atividades em segundos ao longo da semana** e, com um clique, gerar um **PowerPoint profissional** organizado pela IA.

### Meta de produto

| Situação manual (hoje) | Meta com QWI |
|------------------------|--------------|
| ~4 horas em um único dia | 15–30 minutos no final da semana |
| Reconstruir tudo de memória | Registrar em tempo real (~30 s/atividade) |
| Formatar PowerPoint manualmente | IA gera o `.pptx` automaticamente |
| Decidir o que entrou no relatório | IA organiza; usuário só revisa |

### Público-alvo

Funcionários dos setores de Qualidade:

| Setor | Descrição |
|-------|-----------|
| **QM** | Quality Management — sistema de qualidade, auditorias, procedimentos |
| **QA** | Quality Assurance — garantia de processo e prevenção |
| **OQC** | Outgoing Quality Control — inspeção final de produtos |
| **IQC** | Incoming Quality Control — inspeção de materiais recebidos |
| **FIELD** | Qualidade de campo — falhas de mercado, retornos, análise de cliente |
| **CSI** | Inovação em qualidade — software, automação e soluções digitais |

---

## 2. Problema e objetivo

### O problema

Cada funcionário gasta **pelo menos 4 horas em um dia inteiro** montando o Weekly Report manualmente. Esse documento funciona como:

- Um **roteiro** de tudo que foi feito na semana
- Com o **impacto** de cada atividade no contexto do departamento
- Sem padrão único — **cada setor e cargo produz conteúdo diferente**

O processo manual inclui lembrar atividades, redigir descrições, organizar cronologicamente, analisar planilhas, selecionar fotos, legendar evidências e montar slides no PowerPoint.

### O objetivo do QWI

Ser a **melhor ferramenta possível para eliminar esse trabalho manual**, mantendo ou superando a qualidade do relatório feito à mão, com estas premissas:

1. **Registrar em segundos, não em minutos** — formulário minimalista (título + descrição + anexos)
2. **Distribuir o esforço na semana** — captura contínua vs. maratona de sexta-feira
3. **Zero configuração para o funcionário** — defaults inteligentes por departamento/setor
4. **A IA cria o PPT, não preenche template** — layout corporativo gerado automaticamente
5. **Fluxo universal, conteúdo adaptado** — mesmo processo para todos os setores; a IA adapta a narrativa

---

## 3. O que o sistema faz

### Funcionalidades de alto nível

```
┌─────────────────────────────────────────────────────────────────┐
│  DURANTE A SEMANA (30 segundos por atividade)                   │
│                                                                 │
│  Registrar atividade → Anexar evidências → IA processa em BG   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  FINAL DA SEMANA (15–30 minutos)                                │
│                                                                 │
│  Selecionar período → Gerar Weekly → Revisar PPT → Baixar     │
└─────────────────────────────────────────────────────────────────┘
```

### Capacidades principais

| Capacidade | Descrição |
|------------|-----------|
| **Autenticação multi-usuário** | Registro, login e sessão via JWT |
| **Registro de atividades** | Título, descrição opcional, data automática |
| **Upload de evidências** | Imagens, planilhas (Excel/CSV), PDF, Word, PowerPoint, TXT |
| **Enriquecimento por IA** | Extração de metadados, análise de imagens/planilhas/documentos |
| **Timeline cronológica** | Visualização e edição das atividades da semana |
| **Dashboard semanal** | Métricas simples: atividades, dias preenchidos, arquivos |
| **Geração de Weekly** | Pipeline de 3 etapas com IA + montagem de PPT |
| **Download de relatórios** | Histórico versionado de `.pptx` gerados |
| **Perfil de usuário** | Dados pessoais, departamento, setor e cargo |

---

## 4. O que já está implementado

### Backend (FastAPI)

| Módulo | Status | Detalhes |
|--------|--------|----------|
| Autenticação JWT | ✅ Completo | Registro, login, `/auth/me`, bcrypt |
| CRUD de atividades | ✅ Completo | Criar, listar, editar, excluir com filtros por semana/período |
| Upload de anexos | ✅ Completo | Até 50 MB, tipos múltiplos, armazenamento por usuário/atividade |
| Processamento IA em background | ✅ Completo | `BackgroundTasks` do FastAPI; não bloqueia HTTP |
| Extração de metadados | ✅ Completo | Projeto, fornecedor, KPIs, keywords, resumo técnico |
| Análise de imagens | ✅ Parcial | Vision via Ollama; ativada por diretiva `/analisar imagem` |
| Análise de planilhas | ✅ Completo | openpyxl + IA para KPIs, tendências, anomalias |
| Análise de documentos | ✅ Completo | PDF, DOCX, TXT extraídos e analisados pela IA |
| Geração de Weekly | ✅ Completo | Pipeline 3 etapas + fallback determinístico |
| Geração de PPT | ✅ Completo | Layout executivo sem template externo |
| Dashboard stats | ✅ Completo | Contadores da semana corrente |
| Templates (legado) | ⚠️ Mantido | API existe; MVP não exige upload de template |
| Perfil de escrita | ⚠️ Backend pronto | Defaults automáticos; UI de settings removida do MVP |
| Migrations | ✅ Completo | SQLAlchemy + script de migrações customizado |
| Testes automatizados | ✅ Completo | 10 arquivos de teste cobrindo serviços críticos |

### Frontend (React)

| Tela | Status | Detalhes |
|------|--------|----------|
| Login / Registro | ✅ Completo | Com seleção de setor de qualidade |
| Dashboard | ✅ Completo | 3 métricas + CTAs "Nova Atividade" e "Gerar Weekly" |
| Timeline | ✅ Completo | Lista cronológica, edição, anexos visíveis |
| Formulário de atividade | ✅ Simplificado | 3 campos: título, descrição, anexos |
| Gerar Weekly (dialog) | ✅ Completo | Calendário de período, seleção de atividades, idioma |
| Relatórios | ✅ Completo | Lista de PPTs, download, resumo IA colapsável |
| Perfil | ✅ Completo | Dados do usuário |
| Templates / Settings / Semanas / Arquivos | ↪️ Redirecionados | Rotas antigas redirecionam para páginas do MVP |

### Infraestrutura

| Componente | Status |
|------------|--------|
| Docker Compose (PostgreSQL) | ✅ |
| Dockerfiles (backend + frontend) | ✅ |
| Script de dev (`scripts/dev.sh`) | ✅ |
| Proxy Vite → API | ✅ |

---

## 5. Como funciona — fluxos principais

### 5.1 Registro de atividade

```
Usuário                    Frontend                  Backend                    IA (Ollama)
   │                          │                         │                          │
   │── Preenche título ──────►│                         │                          │
   │── Anexa arquivos ───────►│                         │                          │
   │── Clica "Salvar" ───────►│── POST /activities ────►│                          │
   │                          │                         │── Salva no PostgreSQL    │
   │                          │◄── 201 Created ─────────│                          │
   │◄── Dialog fecha ─────────│                         │                          │
   │                          │                         │── BackgroundTask ───────►│
   │                          │                         │   process_activity_      │
   │                          │                         │   metadata()             │
   │                          │                         │                          │
   │                          │                         │── Para cada anexo ──────►│
   │                          │                         │   process_attachment()   │
```

**Comportamentos automáticos ao salvar:**

- `department` = departamento do usuário
- `activity_date` = data/hora atual (se não informada)
- `week_number` / `year` = calculados pela data ISO
- `include_in_weekly` = sempre `true`
- `project`, `category`, `tags` = preenchidos pela IA em background

### 5.2 Processamento de anexos

| Tipo de arquivo | Extensões | Processamento |
|-----------------|-----------|---------------|
| **Imagem** | jpg, png, gif, webp, bmp | Vision IA se diretiva `/analisar imagem` presente; senão, apenas referência visual no PPT |
| **Planilha** | xlsx, xls, csv | Extração local (50 linhas/aba) + análise IA de KPIs |
| **Documento** | pdf, docx, txt | Extração de texto + análise IA de fatos e conclusões |
| **Outros** | pptx, ppt | Armazenados; sem análise automática |

**Diretiva especial na descrição:**

O usuário pode incluir na descrição da atividade uma linha como:

```
/analisar imagem
```

Isso ativa a análise visual completa das imagens anexadas (OCR, medições visíveis, legendas técnicas).

### 5.3 Geração do Weekly Report

```
1. Usuário seleciona período e atividades no dialog "Gerar Weekly"
2. POST /api/weekly/generate
3. Backend:
   a. Valida atividades do período
   b. Cria WeeklyReport (status: GENERATING)
   c. Garante que anexos foram analisados (_ensure_attachments_analyzed)
   d. Monta "evidence dossier" — dossiê textual com todas as evidências
   e. PromptComposer monta prompt contextualizado (setor, tom, idioma)
   f. LLM — 3 etapas:
      • Análise profunda das evidências
      • Plano de apresentação (estrutura de slides)
      • Formatação em JSON estruturado
   g. Se IA falhar → fallback determinístico (_build_fallback_content)
   h. PptxService monta slides a partir do JSON
   i. Salva .pptx em uploads/reports/
   j. Atualiza WeeklyReport (status: COMPLETED)
4. Frontend redireciona para /reports
5. Usuário baixa o PowerPoint
```

### 5.4 Versionamento de relatórios

Cada geração para a mesma semana/ano incrementa a `version` (v1, v2, v3…). Relatórios anteriores permanecem disponíveis para download.

---

## 6. Arquitetura do sistema

### Diagrama de componentes

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React + Vite)                        │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐            │
│  │ Dashboard  │ │  Timeline  │ │ Relatórios │ │   Perfil   │            │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘            │
│        └──────────────┴──────────────┴──────────────┘                    │
│                              │ Axios (/api → proxy)                      │
└──────────────────────────────┼───────────────────────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────────────────┐
│                        BACKEND (FastAPI)                                 │
│  ┌───────────────────────────▼──────────────────────────────────────┐   │
│  │                     API Routes (REST)                             │   │
│  │  /auth  /users  /activities  /weekly  /dashboard  /templates      │   │
│  └───────────────────────────┬──────────────────────────────────────┘   │
│                              │                                           │
│  ┌───────────────────────────▼──────────────────────────────────────┐   │
│  │                    Services (Lógica de Negócio)                     │   │
│  │  ActivityService │ FileService │ WeeklyService │ PptxService       │   │
│  └───────┬──────────────────┬───────────────────┬────────────────────┘   │
│          │                  │                   │                        │
│  ┌───────▼──────┐  ┌────────▼────────┐  ┌──────▼───────┐               │
│  │ PromptComposer│  │   LLMService    │  │ ai_processor │               │
│  │ (engenharia   │  │  (abstração IA) │  │ (background) │               │
│  │  de prompts)  │  │                 │  │              │               │
│  └───────────────┘  └────────┬────────┘  └──────────────┘               │
│                              │                                           │
└──────────────────────────────┼───────────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
   ┌──────▼──────┐    ┌────────▼────────┐   ┌──────▼──────┐
   │ PostgreSQL  │    │  Ollama (local) │   │  Filesystem │
   │   (dados)   │    │  Gemma4 model   │   │  (uploads/) │
   └─────────────┘    └─────────────────┘   └─────────────┘
```

### Estrutura de diretórios

```
Quality_weekly_AI/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py              # Dependências FastAPI (auth, DB)
│   │   │   └── routes/
│   │   │       ├── auth.py          # Autenticação
│   │   │       ├── users.py         # Perfil e writing profile
│   │   │       ├── activities.py    # CRUD atividades + anexos
│   │   │       └── weekly.py        # Dashboard, geração, download
│   │   ├── core/
│   │   │   ├── config.py            # Settings (Pydantic)
│   │   │   ├── database.py          # SQLAlchemy engine/session
│   │   │   ├── security.py          # JWT + bcrypt
│   │   │   ├── exceptions.py        # Exceções customizadas
│   │   │   ├── dates.py             # Utilitários de data/timezone
│   │   │   ├── migrations.py        # Migrações de schema
│   │   │   ├── logging.py           # Configuração de logs
│   │   │   └── activity_directives.py  # Parser de diretivas (/analisar imagem)
│   │   ├── models/
│   │   │   └── __init__.py          # Todos os modelos SQLAlchemy
│   │   ├── schemas/
│   │   │   ├── user.py              # Schemas Pydantic de usuário
│   │   │   ├── activity.py          # Schemas de atividade
│   │   │   ├── weekly.py            # Schemas de relatório
│   │   │   └── weekly_content.py    # Schema do JSON estruturado
│   │   ├── services/
│   │   │   ├── business.py          # ActivityService, FileService, WeeklyService
│   │   │   ├── llm_service.py       # Abstração de LLM (Ollama)
│   │   │   ├── prompt_composer.py   # Engenharia de prompts modular
│   │   │   ├── ai_processor.py      # Tasks de background
│   │   │   ├── pptx_service.py      # Geração de PowerPoint
│   │   │   ├── text_sanitize.py     # Sanitização de conteúdo IA
│   │   │   └── pptx/
│   │   │       ├── charts.py        # Renderização de gráficos
│   │   │       ├── profiles.py      # Perfis de layout (executivo, operacional…)
│   │   │       └── strings.py       # Strings i18n e constantes visuais
│   │   └── main.py                  # Entry point FastAPI
│   ├── tests/                       # Testes pytest
│   ├── uploads/
│   │   ├── templates/               # Templates PPT (legado)
│   │   └── reports/                 # PPTs gerados
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/Sidebar.tsx   # Layout + navegação
│   │   │   ├── activities/          # Formulário de atividade
│   │   │   ├── weekly/              # Dialog de geração + calendário
│   │   │   └── ui/                  # Componentes Shadcn/UI
│   │   ├── contexts/AuthContext.tsx # Estado de autenticação
│   │   ├── pages/                   # Páginas da aplicação
│   │   ├── lib/
│   │   │   ├── api.ts               # Cliente Axios
│   │   │   ├── activity.ts          # Helpers do formulário
│   │   │   └── utils.ts             # Utilitários (cn, etc.)
│   │   └── types/index.ts           # Tipos TypeScript
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docs/
│   ├── ANALISE-MVP-SIMPLIFICADO.md  # Análise de simplificação
│   └── DOCUMENTACAO-COMPLETA.md     # Este documento
├── scripts/dev.sh                   # Script de desenvolvimento
├── docker-compose.yml
└── README.md
```

### Padrões arquiteturais

| Padrão | Aplicação |
|--------|-----------|
| **Separação em camadas** | Routes → Services → Models/DB |
| **Injeção de dependência** | FastAPI `Depends()` para DB e auth |
| **Provider pattern** | `LLMProvider` abstrato com implementação `OllamaProvider` |
| **Background processing** | FastAPI `BackgroundTasks` para IA não-bloqueante |
| **Repository implícito** | Services acessam SQLAlchemy diretamente |
| **Schema validation** | Pydantic v2 na API; TypeScript no frontend |

---

## 7. Stack tecnológica

### Backend

| Tecnologia | Versão | Função |
|------------|--------|--------|
| **Python** | 3.12+ | Linguagem principal |
| **FastAPI** | 0.115.6 | Framework web assíncrono |
| **Uvicorn** | 0.34.0 | Servidor ASGI |
| **SQLAlchemy** | 2.0.36 | ORM |
| **PostgreSQL** | 16 | Banco de dados relacional |
| **Pydantic** | 2.10.3 | Validação de schemas |
| **python-jose** | 3.3.0 | JWT |
| **passlib + bcrypt** | — | Hash de senhas |
| **httpx** | 0.28.1 | Cliente HTTP async (Ollama) |
| **python-pptx** | 1.0.2 | Geração de PowerPoint |
| **Pillow** | 11.0.0 | Processamento de imagens |
| **openpyxl** | 3.1.5 | Leitura de Excel |
| **pypdf** | 6.14.2 | Extração de PDF |
| **python-docx** | 1.2.0 | Extração de Word |
| **Ollama + Gemma4** | e2b | LLM local (vision + texto) |

### Frontend

| Tecnologia | Versão | Função |
|------------|--------|--------|
| **React** | 18.3.1 | UI library |
| **TypeScript** | 5.6.2 | Tipagem estática |
| **Vite** | 6.0.5 | Build tool e dev server |
| **TailwindCSS** | 3.4.17 | Estilização utility-first |
| **Shadcn/UI + Radix** | — | Componentes acessíveis |
| **TanStack React Query** | 5.62.8 | Cache e fetching de dados |
| **React Router** | 7.1.1 | Roteamento SPA |
| **Axios** | 1.7.9 | Cliente HTTP |
| **date-fns** | 4.1.0 | Manipulação de datas |
| **Framer Motion** | 11.15.0 | Animações |
| **Lucide React** | — | Ícones |

### Infraestrutura

| Tecnologia | Função |
|------------|--------|
| **Docker Compose** | Orquestração local (db, backend, frontend) |
| **PostgreSQL 16 Alpine** | Container de banco |
| **Alembic** | Migrations (dependência instalada) |

---

## 8. Modelo de dados

### Diagrama entidade-relacionamento

```
┌─────────────┐       ┌──────────────────┐       ┌─────────────┐
│    User     │───1:1─│ WritingProfile   │───N:1─│  Template   │
└──────┬──────┘       └──────────────────┘       └─────────────┘
       │
       │ 1:N
       ▼
┌─────────────┐       ┌──────────────────┐       ┌─────────────┐
│  Activity   │───1:1─│ ActivityMetadata │       │ Attachment  │
└──────┬──────┘       └──────────────────┘       └──────┬──────┘
       │                                                 │
       │ 1:N                                             │ N:1
       └─────────────────────────────────────────────────┘

┌─────────────┐
│WeeklyReport │─── N:1 ─── User
└─────────────┘─── N:1 ─── Template (opcional)
```

### Entidades principais

#### User
Representa um funcionário do departamento de Qualidade.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID | Identificador único |
| email | string | Login (único) |
| name | string | Nome completo |
| department | string | Departamento |
| role | string | Cargo |
| sector | enum | QM, QA, OQC, IQC, FIELD, CSI |
| is_active | bool | Conta ativa |
| is_admin | bool | Administrador |

#### Activity
Registro de uma atividade realizada.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| title | string | O que foi feito (obrigatório) |
| description | text | Detalhes opcionais |
| activity_date | datetime | Quando ocorreu |
| week_number / year | int | Semana ISO |
| status | enum | registered → processed → used_in_report |
| include_in_weekly | bool | Sempre true no MVP |

#### ActivityMetadata
Metadados extraídos pela IA de cada atividade.

| Campo | Descrição |
|-------|-----------|
| project, supplier, line, process, product | Contexto industrial |
| category, activity_type, defect_type | Classificação |
| related_kpis, keywords | Arrays extraídos |
| technical_summary | Resumo analítico gerado pela IA |

#### Attachment
Arquivo anexado a uma atividade.

| Campo | Descrição |
|-------|-----------|
| file_type | image, spreadsheet, document, other |
| image_usage | Modo de uso (insert_report por padrão) |
| ai_caption | Legenda gerada pela IA |
| ai_analysis | JSON com análise completa |
| kpi_data | Dados extraídos de planilhas |

#### WeeklyReport
Relatório semanal gerado.

| Campo | Descrição |
|-------|-----------|
| week_number / year | Período |
| version | Incremento a cada regeneração |
| status | draft, generating, completed, failed |
| content | JSON com raw + structured + activity_ids |
| pptx_path | Caminho do arquivo gerado |
| ai_summary | Resumo executivo |
| prompt_used | Prompt completo (auditoria) |

#### WritingProfile
Preferências de escrita (defaults automáticos no MVP).

| Campo | Descrição |
|-------|-----------|
| writing_tone | analyst, specialist, supervisor, manager, director |
| objectivity | low, medium, high |
| technical_level | low, medium, high |
| auto_* flags | Conclusões, próximos passos, impacto, imagens, gráficos |
| personal_prompt | Instruções permanentes customizadas |

---

## 9. Camada de Inteligência Artificial

### Arquitetura desacoplada

A comunicação com LLMs passa por uma camada de abstração que permite trocar o provedor sem alterar a lógica de negócio:

```
LLMService
    └── LLMProvider (ABC)
            └── OllamaProvider (implementação atual)
```

**Configuração (`.env`):**

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_NUM_CTX=16384      # Janela de contexto (evita truncamento)
OLLAMA_NUM_PREDICT=4096     # Tokens máximos de resposta
```

### PromptComposer

Módulo de engenharia de prompts que monta instruções contextuais com base em:

- **Idioma** (PT ou EN)
- **Tom de escrita** (analista, especialista, gerente…)
- **Objetividade e nível técnico**
- **Setor de qualidade** (playbooks específicos por QM, QA, OQC, IQC, FIELD, CSI)
- **Mandato executivo** — regras de escrita (sem frases genéricas de IA)

#### Sector Playbooks

Cada setor possui instruções especializadas. Exemplo para **FIELD**:

- Classificar atividades: field_failure, market_return, customer_complaint…
- Extrair: modelo, serial, failure mode, localização
- Blocos visuais típicos: device_info, measurement_table, image_row

### Pipeline de geração (3 etapas)

```
Etapa 1: ANÁLISE
├── Input: evidence dossier (todas as atividades + análises de anexos)
├── Output: rascunho analítico profundo
└── System: "Expert corporate weekly report writer"

Etapa 2: PLANO DE APRESENTAÇÃO
├── Input: rascunho da etapa 1 + inventário de anexos
├── Output: estrutura de slides, blocos visuais, layout profile
└── System: "Presentation editor for executive quality reports"

Etapa 3: FORMATAÇÃO JSON
├── Input: rascunho + plano
├── Output: JSON estruturado validado
└── System: "Convert to strict JSON for PowerPoint generator"
```

### Fallback determinístico

Se o Ollama estiver offline ou retornar resposta inválida, o sistema gera conteúdo básico a partir dos dados das atividades (`_build_fallback_content`), garantindo que o usuário sempre receba um PPT — mesmo que simplificado.

### Processamento em background

```python
# activities.py — retorno imediato ao usuário
background_tasks.add_task(process_activity_in_background, activity.id)

# ai_processor.py — executa após resposta HTTP
asyncio.run(ActivityService(database).process_activity_metadata(activity))
```

---

## 10. Geração de PowerPoint

### Filosofia de design

O PPT é **criado do zero** pelo sistema, sem depender de template uploadado pelo usuário. O design segue princípios executivos:

- Fonte **Arial**, tamanhos compactos (8–12pt)
- Layout **duas colunas**: atividades à esquerda, sidebar à direita
- Barras de acento azul (`#0C379C`) nos títulos de seção
- Imagens como **thumbnails inline** (referência visual)
- **Paginação automática** baseada em medição de texto

### Estrutura típica de slides

| Slide | Conteúdo |
|-------|----------|
| 1 — Capa | Semana, ano, autor, departamento, título |
| 2+ — Conteúdo | Atividades agrupadas com narrativa, impacto, fatos |
| Sidebar | Síntese, KPIs, highlights, conclusões, próximos passos |
| Evidências | Fotos inline, tabelas de medição, gráficos |

### Blocos visuais suportados

| Tipo | Uso |
|------|-----|
| `device_info` | Identificação de produto/dispositivo |
| `measurement_table` | Medições paramétricas |
| `generic_table` | Dados tabulares genéricos |
| `countermeasure_table` | Plano de ação (ação, owner, status, prazo) |
| `chart` | Gráficos (barras, linhas) com dados reais |
| `image_row` | Linha de fotos de evidência |
| `text` / `highlight` | Ênfase textual |

### Perfis de layout

Resolvidos automaticamente com base no setor e conteúdo:

- **executive** — visão gerencial
- **operational** — foco operacional
- **analytical** — dados e KPIs
- **field_case** — casos de campo com device info

### Arquivo gerado

Salvo em: `backend/uploads/reports/weekly_{report_id}.pptx`  
Download via: `GET /api/weekly/{report_id}/download`

---

## 11. API REST

**Base URL:** `http://localhost:8000/api`  
**Documentação interativa:** `http://localhost:8000/docs`

### Autenticação

Todas as rotas (exceto register/login) exigem header:

```
Authorization: Bearer <jwt_token>
```

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/auth/register` | Criar conta |
| POST | `/auth/login` | Login (retorna token) |
| GET | `/auth/me` | Usuário autenticado |

### Atividades

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/activities` | Listar (filtros: week, year, start_date, end_date, timezone) |
| POST | `/activities` | Criar atividade |
| GET | `/activities/{id}` | Detalhe |
| PATCH | `/activities/{id}` | Atualizar |
| DELETE | `/activities/{id}` | Excluir |
| POST | `/activities/{id}/attachments` | Upload de arquivo |
| PATCH | `/activities/{id}/attachments/{aid}` | Atualizar anexo |
| DELETE | `/activities/{id}/attachments/{aid}` | Remover anexo |

### Weekly Reports

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/dashboard` | Estatísticas da semana corrente |
| POST | `/weekly/generate` | Gerar relatório |
| GET | `/weekly` | Listar relatórios |
| GET | `/weekly/{id}` | Detalhe |
| GET | `/weekly/{id}/download` | Download do `.pptx` |

### Usuários

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/users/profile` | Perfil |
| PATCH | `/users/profile` | Atualizar perfil |
| GET | `/users/writing-profile` | Perfil de escrita |
| PATCH | `/users/writing-profile` | Atualizar perfil de escrita |

### Utilitários

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/health` | Health check |

---

## 12. Frontend

### Rotas

| Rota | Página | Proteção |
|------|--------|----------|
| `/login` | LoginPage | Pública |
| `/register` | RegisterPage | Pública |
| `/` | DashboardPage | Autenticada |
| `/timeline` | TimelinePage | Autenticada |
| `/reports` | ReportsPage | Autenticada |
| `/profile` | ProfilePage | Autenticada |

Rotas legadas redirecionam: `/weeks`, `/files` → `/timeline`; `/templates` → `/reports`; `/settings` → `/profile`.

### Estado e dados

- **AuthContext** — token JWT em `localStorage` (`qwi_token`), user em memória
- **React Query** — cache de dashboard, atividades, relatórios (staleTime: 30s)
- **Axios interceptors** — injeta token; redireciona para login em 401

### Componentes principais

| Componente | Função |
|------------|--------|
| `AppLayout` / `Sidebar` | Layout responsivo (sidebar desktop + bottom nav mobile) |
| `ActivityFormDialog` | Formulário minimalista de atividade |
| `GenerateWeeklyDialog` | Seleção de período, atividades e geração |
| `PeriodCalendar` | Calendário para escolher intervalo de datas |
| `ReportCard` | Card de relatório com download |

### Proxy de desenvolvimento

O Vite proxy redireciona `/api` → `http://localhost:8000`, eliminando problemas de CORS em dev.

---

## 13. Infraestrutura e execução

### Pré-requisitos

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 (ou Docker)
- Ollama com modelo `gemma4:e2b` (opcional, mas necessário para IA completa)

### Início rápido com script

```bash
chmod +x scripts/dev.sh
./scripts/dev.sh
```

O script:
1. Sobe PostgreSQL via Docker Compose
2. Cria venv e instala dependências Python
3. Inicia backend (uvicorn :8000)
4. Instala npm e inicia frontend (:3000)

### Início manual

```bash
# Banco
docker compose up -d db

# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

### Docker Compose completo

```bash
docker compose up --build
```

Serviços:
- **db** — PostgreSQL na porta 5433 (host) → 5432 (container)
- **backend** — FastAPI na porta 8000
- **frontend** — Vite na porta 3000

### Variáveis de ambiente

| Variável | Default | Descrição |
|----------|---------|-----------|
| `DATABASE_URL` | postgresql://qwi:qwi_secret@localhost:5432/qwi_db | Conexão PostgreSQL |
| `SECRET_KEY` | (dev) | Chave JWT |
| `OLLAMA_BASE_URL` | http://localhost:11434 | URL do Ollama |
| `OLLAMA_MODEL` | gemma4:e2b | Modelo LLM |
| `OLLAMA_NUM_CTX` | 16384 | Context window |
| `OLLAMA_NUM_PREDICT` | 4096 | Max tokens de resposta |

---

## 14. Testes

### Executar

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

### Cobertura por módulo

| Arquivo de teste | O que testa |
|------------------|-------------|
| `test_business.py` | ActivityService, WeeklyService |
| `test_prompt_composer.py` | Composição de prompts |
| `test_llm_service` (via business) | Integração LLM |
| `test_pptx_service.py` | Geração de slides |
| `test_pptx_blocks.py` | Blocos visuais no PPT |
| `test_weekly_content.py` | Parsing do JSON estruturado |
| `test_evidence_dossier.py` | Montagem do dossiê de evidências |
| `test_activity_directives.py` | Parser de `/analisar imagem` |
| `test_sector_playbooks.py` | Playbooks por setor |
| `test_text_sanitize.py` | Sanitização de conteúdo IA |
| `test_dates.py` | Utilitários de data/timezone |

---

## 15. Identidade visual e UX

### Diretrizes

| Aspecto | Especificação |
|---------|---------------|
| Tema | Claro (obrigatório) |
| Cor institucional | `#0C379C` (uso moderado) |
| Tipografia | Inter |
| Inspiração | Linear, Notion, Vercel, Stripe |
| Animações | Micro-animações suaves (Framer Motion) |
| Mobile | Bottom navigation + layout responsivo |

### Princípios de UX do MVP

1. **Máximo 4 itens no menu** — Dashboard, Timeline, Relatórios, Perfil
2. **Formulário de 3 campos** — título, descrição, anexos
3. **CTAs claros** — "Nova Atividade" e "Gerar Weekly" sempre visíveis
4. **Feedback de geração** — steps animados durante processamento IA
5. **Entrega clara** — botão grande "Baixar PowerPoint" na tela de relatórios

---

## 16. Limitações conhecidas e roadmap

### Limitações atuais

| Limitação | Impacto | Mitigação |
|-----------|---------|-----------|
| Ollama offline | IA degradada; fallback determinístico | Mensagem implícita via PPT simplificado |
| Análise de imagem opt-in | Imagens não analisadas por padrão | Diretiva `/analisar imagem` na descrição |
| Modelo local (Gemma4) | Qualidade depende do hardware | Camada LLMService permite trocar provedor |
| Sem fila de jobs | Background tasks in-process | Suficiente para MVP single-server |
| Templates corporativos | Não disponível no MVP | PPT gerado automaticamente |
| Multi-idioma parcial | PT e EN na geração; UI só PT | Expansão futura |

### Roadmap

#### Fase 0 — Concluída ✅
Infraestrutura base: auth, models, API, frontend, IA integrada, pipeline de geração.

#### Fase 1 — MVP Weekly Simplificado (atual) 🎯
Critério: funcionário registra em <30s, gera weekly em <30min total.

- [x] Formulário minimalista
- [x] IA gera PPT sem template
- [x] Processamento IA em background
- [x] Navegação enxuta (4 itens)
- [x] Dashboard simplificado
- [x] Análise automática de planilhas e documentos
- [x] Esconder Templates e Settings

#### Fase 2 — Pós-MVP 🔜
- Templates corporativos por departamento (upload opcional)
- Configuração avançada de IA (para gestores)
- Histórico de semanas anteriores expandido
- Regenerar relatório com ajustes
- Métricas de qualidade baseadas em IA

#### Fase 3 — Expansão 🔮
- Agentes inteligentes por departamento
- Integração com sistemas corporativos
- Multi-idioma automático na UI
- Dashboard gerencial (visão do time)

### Regra de ouro

> Se uma funcionalidade não reduz o tempo do funcionário na criação do weekly, ela não entra no MVP.

---

## 17. Glossário

| Termo | Definição |
|-------|-----------|
| **Weekly Report** | Relatório semanal de atividades e impactos, entregue em PowerPoint |
| **Atividade** | Registro unitário do que o funcionário fez (título + descrição + anexos) |
| **Evidência** | Arquivo anexado que comprova ou ilustra uma atividade |
| **Evidence Dossier** | Compilação textual de todas as atividades e análises para a IA |
| **Sector Playbook** | Conjunto de instruções especializadas por setor de qualidade |
| **Writing Profile** | Preferências de tom, objetividade e comportamento da IA |
| **Layout Profile** | Perfil visual do PPT (executivo, operacional, analítico, field) |
| **Ollama** | Runtime local para executar LLMs (Gemma4) |
| **Fallback determinístico** | Geração de conteúdo básico quando a IA não está disponível |
| **NC** | Non-Conformity (não-conformidade) |
| **PPM** | Parts Per Million (defeitos por milhão) |
| **FPY** | First Pass Yield (rendimento de primeira passagem) |
| **FMEA** | Failure Mode and Effects Analysis |
| **8D** | Metodologia de resolução de problemas em 8 disciplinas |

---

## Referências

- [README.md](../README.md) — Guia de início rápido
- [ANALISE-MVP-SIMPLIFICADO.md](./ANALISE-MVP-SIMPLIFICADO.md) — Análise detalhada de simplificação
- API Docs — `http://localhost:8000/docs` (Swagger UI)

---

*Documento gerado para uso interno corporativo. QWI v0.1.0 — Quality Weekly Intelligence.*
