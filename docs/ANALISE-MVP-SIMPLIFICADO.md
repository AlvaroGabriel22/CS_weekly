# QWI — Análise do Sistema Atual e Proposta de Simplificação do MVP

**Data:** 13 de julho de 2026  
**Objetivo:** Reduzir o tempo de criação do Weekly Report de ~4 horas/semana para **15–30 minutos**, distribuindo o esforço ao longo da semana, sem exigir configuração complexa dos funcionários.

---

## 1. O Problema Real

Hoje, cada funcionário gasta **pelo menos 4 horas em um dia inteiro** montando o Weekly Report manualmente. Esse documento é, na prática:

- Um **roteiro** de tudo que foi feito na semana
- Com o **impacto** de cada atividade no contexto do departamento
- Sem padrão único de conteúdo — **cada departamento é diferente**

A meta do QWI não é ser um sistema corporativo completo. É ser a **melhor ferramenta possível para eliminar esse trabalho manual**, mantendo ou superando a qualidade do relatório feito à mão.

| Situação atual (manual) | Meta com QWI |
|-------------------------|--------------|
| 4+ horas em um único dia | 15–30 min no final da semana |
| Reconstruir tudo de memória | Registrar em segundos durante a semana |
| Formatar PowerPoint manualmente | IA gera o PPT automaticamente |
| Decidir o que entrou no relatório | IA organiza; usuário só revisa |

---

## 2. Diagnóstico do Sistema Atual

### O que já funciona

| Área | Status | Observação |
|------|--------|------------|
| Autenticação | ✅ Pronto | Login, registro, JWT |
| Registro de atividades | ✅ Parcial | Funciona, mas o formulário é pesado |
| Upload de arquivos | ✅ Parcial | Salva arquivos; análise de IA limitada |
| Geração de Weekly | ✅ Parcial | Pipeline existe, mas depende de template PPT |
| Download de PPT | ✅ Pronto | Endpoint funcional |
| IA local (Ollama) | ✅ Parcial | Integrada, mas frágil se Ollama estiver offline |

### Onde o sistema está mais complexo do que deveria

O sistema atual foi construído como **plataforma corporativa ampla**, não como **ferramenta focada em eliminar o Weekly**. Isso gerou funcionalidades que aumentam carga cognitiva sem reduzir tempo na prática:

#### 2.1 Formulário de atividade muito pesado

O `ActivityFormDialog` exige hoje:
- Título, descrição, projeto, categoria, departamento, data/hora, tags, observações
- Toggle "incluir no weekly" por atividade
- Toggle "incluir no weekly" **por arquivo**
- 5 modos de uso de imagem (armazenar, inserir, IA interpreta, legenda, evidência)
- Legenda manual por imagem

**Problema:** O README promete "pequenas interações", mas o formulário parece um mini-CRM. Para a meta de 15–30 min, o registro deve levar **menos de 1 minuto por atividade**.

#### 2.2 Template PPT obrigatório na prática

A tela de Templates pede upload de `.pptx` com marcadores `{{summary}}`, `{{activities_list}}`, etc. Sem isso, o relatório gerado pode ficar incompleto ou genérico.

**Problema:** Isso transfere trabalho do funcionário para outra etapa (preparar template). No MVP desejado, **a IA deve criar o PPT do zero**, formatado e planejado automaticamente.

#### 2.3 Configurações de IA expostas ao usuário

A tela de Settings oferece:
- Tom da escrita (5 opções)
- Objetividade, nível técnico
- 5 toggles de comportamento da IA
- Campo de "Instruções Permanentes"

**Problema:** Funcionários de qualidade não querem configurar IA — querem **resultado**. Essas opções devem ser **defaults inteligentes por departamento/cargo**, invisíveis no MVP.

#### 2.4 Navegação com telas vazias

Itens no menu lateral sem funcionalidade:
- **Semanas** — placeholder
- **Arquivos** — placeholder

**Problema:** Transmite produto incompleto e confunde o usuário sobre o que é necessário fazer.

#### 2.5 Métricas que não ajudam o funcionário

- **Cobertura do Weekly** no Dashboard mostra 0% até gerar o relatório
- **Índice de Confiança da IA** é calculado por fórmula, não pela IA
- Opções de imagem (`ai_interpret`, `ai_caption`) existem na UI mas **não são executadas** no backend

**Problema:** Métricas que parecem inteligentes mas não orientam ação clara. O funcionário precisa saber apenas: *"Quantas atividades registrei esta semana?"* e *"Meu relatório está pronto?"*.

#### 2.6 Processamento de IA bloqueante e silencioso

Ao salvar uma atividade, o backend tenta chamar o Ollama de forma síncrona. Se falhar, continua sem avisar o usuário.

**Problema:** Pode travar o salvamento e criar expectativa de que a IA já analisou tudo, quando não analisou.

---

## 3. Princípios para o MVP Simplificado

### Princípio 1 — Registrar em segundos, não em minutos

> O funcionário deve conseguir registrar uma atividade em **até 30 segundos**.

Campos essenciais:
1. **O que fez** (título — obrigatório)
2. **Detalhes** (descrição — opcional, 1 campo)
3. **Anexos** (arrastar arquivos — opcional)

Tudo o resto a IA extrai automaticamente.

### Princípio 2 — Distribuir na semana, finalizar em minutos

```
Segunda a Sexta          Sexta (ou quando quiser)
─────────────────        ─────────────────────────
30s por atividade   →    1 clique: "Gerar Weekly"
                         15 min: revisar e baixar PPT
```

O trabalho pesado (organizar, narrar, formatar, inserir evidências) é da IA.

### Princípio 3 — Zero configuração para o funcionário

O funcionário **não deve**:
- Enviar template PowerPoint
- Configurar tom de escrita
- Decidir modo de uso de cada imagem
- Escolher o que vai para cada slide

Tudo isso é responsabilidade do sistema, com defaults por departamento.

### Princípio 4 — A IA cria o PPT, não preenche template

No MVP:
- Não exigir upload de template
- A IA analisa **tudo** que o usuário registrou na semana
- Gera um PowerPoint **novo**, estruturado e profissional
- Inclui automaticamente fotos de evidência anexadas
- O usuário só **revisa e baixa**

Templates corporativos por departamento ficam para uma **fase posterior**.

### Princípio 5 — Cada departamento é diferente, mas o fluxo é igual

A diferença entre departamentos está no **conteúdo** (o que o funcionário escreve e anexa), não no **processo** (como ele usa o sistema). O fluxo é universal:

```
Registrar → Anexar → Gerar → Baixar
```

A IA adapta o relatório ao contexto do departamento/cargo automaticamente.

---

## 4. Fluxo Proposto do MVP Simplificado

### Experiência do funcionário (semana típica)

```
┌─────────────────────────────────────────────────────────────┐
│  SEGUNDA A SEXTA — 30 segundos por atividade                │
│                                                             │
│  1. Abre o QWI                                              │
│  2. Clica "Nova Atividade"                                  │
│  3. Escreve o que fez (1 linha)                             │
│  4. Opcionalmente anexa foto/planilha/PDF                   │
│  5. Salva                                                   │
│                                                             │
│  Repete ao longo da semana, conforme as coisas acontecem    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  SEXTA — 15 a 30 minutos                                    │
│                                                             │
│  1. Abre o Dashboard                                        │
│  2. Vê: "12 atividades registradas esta semana"             │
│  3. Clica "Gerar Weekly"                                    │
│  4. IA processa tudo (atividades + arquivos + impacto)      │
│  5. Revisa o PPT gerado                                     │
│  6. Baixa e envia                                           │
└─────────────────────────────────────────────────────────────┘
```

### O que a IA faz automaticamente (invisível ao usuário)

1. **Ao salvar atividade:** extrai projeto, categoria, palavras-chave, resumo técnico
2. **Ao anexar arquivo:** analisa imagem, lê planilha, extrai KPIs
3. **Ao gerar weekly:**
   - Organiza cronologicamente
   - Agrupa atividades semelhantes
   - Escreve narrativa com impacto por atividade
   - Estrutura slides (capa, resumo, atividades, evidências, conclusões)
   - Insere fotos de evidência
   - Gera PPT formatado
4. **Personalização automática** por departamento, cargo e idioma (sem tela de configuração)

---

## 5. O Que Remover, Simplificar e Manter

### ❌ Remover do MVP (ou esconder)

| Funcionalidade | Motivo |
|----------------|--------|
| Tela de Templates | Usuário não envia PPT no MVP; IA cria do zero |
| Tela de Configurações (Settings) | Defaults automáticos por departamento/cargo |
| Menu "Semanas" | Placeholder; confunde sem agregar valor |
| Menu "Arquivos" | Placeholder; arquivos já aparecem na Timeline |
| 5 modos de uso de imagem | Complexidade desnecessária; IA decide automaticamente |
| Toggle "incluir no weekly" por atividade/arquivo | Tudo registrado na semana entra no relatório |
| Índice de Confiança da IA | Métrica heurística que não ajuda o funcionário |
| Tags manuais | IA extrai palavras-chave automaticamente |
| Campos projeto/categoria/departamento no formulário | Herdados do perfil ou extraídos pela IA |
| Perfil de Escrita com 10+ opções | Configuração interna, não do usuário |

### ⚡ Simplificar

| Funcionalidade atual | Proposta |
|---------------------|----------|
| Formulário de atividade (10+ campos) | **3 campos:** título, descrição, anexos |
| Dashboard com 6 métricas | **2 informações:** atividades da semana + botão gerar |
| Timeline com badges e status | Timeline limpa: data, título, anexos |
| Reports com coverage/confidence | Reports: PPT pronto + botão baixar + resumo colapsável |
| Sidebar com 8 itens | **4 itens:** Dashboard, Timeline, Relatórios, Perfil |

### ✅ Manter e reforçar

| Funcionalidade | Por quê |
|----------------|---------|
| Login/Registro | Necessário para multi-usuário |
| Timeline | Coração do sistema — registro rápido |
| Upload de arquivos | Evidências são parte central do weekly |
| Geração de Weekly com IA | Core do produto |
| Download de PPT | Entregável final |
| Processamento IA em background | Não bloquear o usuário |

---

## 6. Ajustes Concretos no Sistema Atual

### Fase 1 — Concluir o MVP de Weekly (prioridade máxima)

Esta fase deve ser **concluída antes** de qualquer expansão.

#### 6.1 Formulário minimalista

**Arquivo:** `frontend/src/components/activities/ActivityFormDialog.tsx`

```
ANTES (10+ campos, toggles, modos de imagem)
DEPOIS:
  ┌──────────────────────────────────────┐
  │  O que você fez? *                   │
  │  [________________________________]  │
  │                                      │
  │  Detalhes (opcional)                 │
  │  [________________________________]  │
  │  [________________________________]  │
  │                                      │
  │  📎 Arrastar arquivos aqui           │
  │                                      │
  │  [ Salvar ]                          │
  └──────────────────────────────────────┘
```

**Backend:** Manter campos no model, mas preencher automaticamente (departamento do usuário, data = agora, `include_in_weekly = true` sempre).

#### 6.2 IA cria o PPT automaticamente

**Arquivo:** `backend/app/services/pptx_service.py`

- Remover dependência de template uploadado
- A IA define a estrutura de slides com base no conteúdo da semana:
  - Slide 1: Capa (semana, autor, departamento)
  - Slide 2: Resumo executivo
  - Slide 3–N: Atividades agrupadas por tema/dia
  - Slides de evidência: fotos anexadas com legenda IA
  - Último slide: Conclusões e próximos passos
- Layout profissional fixo (cores institucionais, tipografia limpa)
- Número de slides varia conforme quantidade de conteúdo

#### 6.3 Processamento IA em background

**Arquivo:** `backend/app/services/business.py`

- Ao salvar atividade: retornar imediatamente, processar IA em background (task async)
- Ao anexar imagem: gerar legenda automaticamente
- Ao anexar planilha: extrair KPIs automaticamente
- Ao gerar weekly: analisar **todos** os dados acumulados da semana

#### 6.4 Navegação enxuta

**Arquivo:** `frontend/src/components/layout/Sidebar.tsx`

```
ANTES: Dashboard | Timeline | Semanas | Reports | Templates | Arquivos | Config | Perfil
DEPOIS: Dashboard | Timeline | Relatórios | Perfil
```

#### 6.5 Dashboard focado em ação

**Arquivo:** `frontend/src/pages/DashboardPage.tsx`

```
┌─────────────────────────────────────────────┐
│  Semana 28 · 2026                           │
│                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐     │
│  │   12    │  │    5    │  │    3    │     │
│  │Atividad.│  │  Dias   │  │ Arquivos│     │
│  └─────────┘  └─────────┘  └─────────┘     │
│                                             │
│  [ + Nova Atividade ]  [ ✨ Gerar Weekly ]  │
│                                             │
│  Último relatório: Gerado sexta, 11/07     │
└─────────────────────────────────────────────┘
```

#### 6.6 Tela de Relatórios = entrega do PPT

**Arquivo:** `frontend/src/pages/ReportsPage.tsx`

- Foco no arquivo PowerPoint como produto final
- Botão grande "Baixar PPT"
- Resumo da IA colapsável (secundário)
- Remover coverage/confidence da UI principal

#### 6.7 Defaults inteligentes (invisíveis)

**Arquivo:** `backend/app/services/prompt_composer.py`

Configuração automática baseada em:
- `user.department` → contexto do departamento
- `user.role` → tom da escrita (analista, gerente, etc.)
- Sem tela de Settings no MVP

---

## 7. Estimativa de Tempo — Antes vs Depois

| Etapa | Manual (hoje) | QWI simplificado |
|-------|-----------------|------------------|
| Lembrar o que fez na semana | ~1h | 0 min (registrou em tempo real) |
| Escrever descrições | ~1h | ~5 min (revisar o que IA escreveu) |
| Organizar cronologicamente | ~30 min | 0 min (automático) |
| Analisar planilhas/gráficos | ~45 min | 0 min (IA analisa anexos) |
| Selecionar e legendar fotos | ~30 min | 0 min (IA gera legendas) |
| Montar PowerPoint | ~1h+ | 0 min (IA gera) |
| Revisar e ajustar | ~15 min | ~15 min |
| **Total** | **~4+ horas** | **~15–30 min** |

---

## 8. Roadmap — Fases

### ✅ Fase 0 — Concluída
Infraestrutura base: auth, models, API, frontend, IA integrada, pipeline de geração.

### 🎯 Fase 1 — MVP Weekly Simplificado (ATUAL — deve ser concluída)

**Critério de conclusão:** Um funcionário consegue registrar atividades durante a semana em menos de 30 segundos cada, clicar "Gerar Weekly" na sexta, e baixar um PPT profissional em menos de 30 minutos totais.

| # | Tarefa | Impacto |
|---|--------|---------|
| 1 | Formulário minimalista (título + descrição + anexos) | Alto — reduz fricção diária |
| 2 | IA gera PPT automaticamente (sem template do usuário) | Alto — elimina etapa de 1h+ |
| 3 | Processamento IA em background | Médio — não trava o usuário |
| 4 | Navegação enxuta (4 itens) | Médio — menos confusão |
| 5 | Dashboard simplificado | Médio — foco em ação |
| 6 | Análise automática de imagens e planilhas | Alto — elimina trabalho manual |
| 7 | Esconder Templates e Settings | Baixo — mas reduz ruído |

### 🔜 Fase 2 — Pós-MVP (somente após Fase 1 concluída)
- Templates corporativos por departamento (upload opcional de PPT)
- Configuração avançada de IA (para gestores, não funcionários)
- Histórico de semanas anteriores
- Regenerar relatório com ajustes
- Métricas de qualidade reais (baseadas em IA)

### 🔮 Fase 3 — Expansão
- Agentes inteligentes por departamento
- Integração com sistemas corporativos
- Multi-idioma automático
- Dashboard gerencial (visão do time)

---

## 9. Resumo Executivo

O QWI hoje tem a **infraestrutura certa** (auth, IA, pipeline de geração, PPT), mas a **experiência está over-engineered** para o objetivo real.

O funcionário não precisa de:
- 8 telas de navegação
- 10 campos por atividade
- Configurar IA
- Enviar template PowerPoint
- Entender métricas de confiança

O funcionário precisa de:
- **Registrar em 30 segundos** o que fez
- **Anexar evidências** sem pensar em como serão usadas
- **Clicar um botão** na sexta
- **Baixar um PPT pronto** em 15 minutos de revisão

A Fase 1 deve ser concluída com esse escopo reduzido. Somente depois disso faz sentido avançar para templates por departamento, configurações avançadas e funcionalidades corporativas expandidas.

> **Regra de ouro:** Se uma funcionalidade não reduz o tempo do funcionário na criação do weekly, ela não entra no MVP.

---

## 10. Próximo Passo Recomendado

Implementar as 7 tarefas da Fase 1 na ordem de impacto (itens 1, 2 e 6 primeiro). Após isso, testar com um funcionário real simulando uma semana completa e medir o tempo total gasto.

**Meta de validação:** Tempo total na sexta-feira (gerar + revisar + baixar) ≤ 30 minutos.
