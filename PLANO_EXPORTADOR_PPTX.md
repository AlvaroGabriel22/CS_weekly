# Plano — Exportador de PPTX por mutação

**Objetivo:** gerar o weekly **mutando o arquivo .pptx do usuário** em vez de reconstruir um
arquivo novo. Fidelidade ao template deixa de depender do que o sistema consegue descrever e
passa a ser garantida por construção: o que não é tocado permanece exatamente como estava.

**Princípio:** a IA sai do posicionamento. Layout, cor, fonte, espaçamento e encaixe são
decisões de código, determinísticas e testáveis.

---

## 1. Por que mudar

O caminho atual (`pptx_layout.py`) cria `Presentation()` do zero e redesenha tudo a partir do
modelo interno produzido por `pptx_import.py`. Auditoria feita sobre o template real do usuário
(`uploads/pptx_templates/b0c873a3-.../None.pptx`, 3 slides, 23 caixas de texto, 2 tabelas,
2 imagens, 1 gráfico nativo):

| Problema | Evidência medida |
|---|---|
| Formatação achatada | 26 de 26 runs sem tamanho/cor explícitos (herdam do master) → tudo virou 28pt ou 16pt e cor única `#1F2937` |
| Conteúdo velho vaza | Slide gerado saiu com `19/07–19/07` (semana do modelo) e com a atividade antiga inteira |
| Título no lugar errado | Regra "maior fonte = título" escolheu o selo `W29` do canto |
| Buracos silenciosos | Atividade sem anexos: slot de gráfico (0,89 × 0,37) e de tabela removidos, sem redistribuição |
| Perda silenciosa | Atividade com 3 imagens: 2 colocadas, a 3ª descartada sem aviso |
| Slot inadequado | Evidência fotográfica encaixada em caixa de 0,08 × 0,11 (ícone) |
| Sem controle de transbordo | Caminho do template não mede texto |

Causas de raiz: (1) reconstrução em vez de mutação; (2) importador lê só formatação de *run*;
(3) não existe conceito de slot; (4) molde escolhido por índice (`molds[min(idx, len-1)]`),
não por encaixe.

---

## 2. Viabilidade — spikes já executados

Todos validados contra o template real, com `python-pptx 0.6.21` (o instalado).

| Primitiva | Resultado |
|---|---|
| Duplicar slide (shapes + rels) | **OK** — arquivo reabre íntegro; texto, tabela e gráfico preservados |
| Trocar texto preservando formatação | **OK** — mantém o 1º run, remove os demais |
| Remover shape (slot não usado) | **OK** |
| Trocar imagem preservando moldura | **OK** — `left/top/width/height` inalterados |
| Clonar part de gráfico + `replace_data` | **OK** — categorias/valores novos, `BAR_CLUSTERED` e estilo preservados |

**Duas armadilhas confirmadas, com solução definida:**

1. **rIds não podem ser reaproveitados.** `_Relationships._add_relationship()` na 0.6.21 gera o
   rId automaticamente. O XML copiado referencia os rIds da origem, então é obrigatório montar o
   mapa `rId_antigo → rId_novo` e reescrever os atributos `r:id`, `r:embed` e `r:link` na árvore
   copiada. Sem isso, imagem e gráfico do slide duplicado apontam para o lugar errado.
2. **Slide duplicado compartilha a part do gráfico.** Verificado: original e duplicata apontam
   ambos para `/ppt/charts/chart1.xml`. Chamar `replace_data` em um alteraria os dois. Sempre
   clonar a `ChartPart` (via `ChartPart.load`, replicando os rels da part — planilha embutida,
   cores, estilo) antes de escrever dados.

**Nota de dependência:** essas primitivas usam APIs privadas do python-pptx (`rels._rels`,
`_add_relationship`), que mudam na série 1.x. Mantemos `0.6.21` pinado e **isolamos todo uso de
API privada em um único módulo**, para que um upgrade futuro toque um arquivo só.

---

## 3. Arquitetura alvo

```
template.pptx (arquivo do usuário, intocado)
        │
        ├── pptx_import.py ──► DeckLayout + SLOTS  (o que é slot, o que é decoração)
        │                          │
   atividades da semana ───────► deck_plan.py      (inventário × variantes → plano)
        │                          │
        └──────────────────► pptx_mutate.py ──► weekly_<id>.pptx
                                   ▲
                            text_metrics.py       (medição com a fonte real)
```

**Módulos novos**

- `app/services/pptx_mutate.py` — primitivas de mutação. Único lugar com API privada do python-pptx.
- `app/services/deck_plan.py` — planejador determinístico: decide qual variante de slide usar,
  o que vai em cada slot, o que transborda para slide extra.
- `app/services/text_metrics.py` — medição de texto com métricas reais da fonte.

**Modelo de slot** — novo campo `slot` no elemento do DeckLayout:

| Valor | Significado |
|---|---|
| `title` | Título da atividade |
| `body` | Descrição da atividade |
| `table` | Tabela de anexo |
| `image` | Imagem/evidência |
| `chart` | Gráfico nativo (preenchido via `replace_data`) |
| `week_label` | Rótulo da semana (W33, período) |
| `static` | Decoração/rótulo fixo — **repete igual, nunca recebe conteúdo** |
| ausente | Tratado como `static` |

Regra que resolve o vazamento de conteúdo velho: **todo elemento não-`static` que não receber
conteúdo é limpo ou removido.** Nada do modelo sobrevive por omissão.

---

## 4. Etapas

Cada etapa termina com a suíte verde e verificação contra o template real.

### Etapa 0 — Higiene (pré-requisito)

- Corrigir o nome do arquivo salvo: hoje os templates viram `None.pptx` (o
  `original_filename` se perde no upload).
- Tratar registro órfão: o template `weekly_modelo` aponta para arquivo **inexistente em disco**
  — gerar com ele hoje quebra. Validar na leitura e devolver erro claro.
- Guardar o `.pptx` original do template (já é guardado) e confirmar que os weeklies do histórico
  também têm arquivo em disco (`uploads/reports/`, 20 arquivos hoje) — é o que permite usar um
  weekly antigo como template de mutação.

### Etapa 1 — Primitivas (`pptx_mutate.py`)

Funções, todas com teste contra o template real:

- `duplicate_slide(prs, index)` — com remapeamento de rIds.
- `delete_slide(prs, index)` / `reorder_slides(prs, ordem)`.
- `set_text(shape, texto)` — preserva formatação do 1º run; remove runs/parágrafos extras.
- `set_paragraphs(shape, linhas)` — múltiplos parágrafos herdando o estilo do primeiro.
- `remove_shape(shape)`.
- `swap_image(pic, caminho)` — troca o blob, mantém moldura; política `contain` documentada.
- `fill_table(shape, colunas, linhas)` — escreve células preservando estilo; clona/remove linhas
  a partir da linha-modelo do template.
- `clone_chart_part(graphic_frame, slide_part, package)` + `set_chart_data(...)`.

**Verificação:** arquivo salvo reabre; contagem de shapes por tipo bate; nenhuma part órfã.

### Etapa 2 — Slots no modelo e na tela

- Backend: campo `slot` no DeckLayout; endpoint `PATCH /api/pptx-templates/{id}/layout`
  (hoje só existe upload, listar e apagar).
- Importação sugere slots automaticamente (a heurística atual de maior fonte/maior área vira
  **sugestão**, não decisão) e marca o resto como `static`.
- Frontend: abrir o template no `SlideEditor` já existente (1.224 linhas, com seleção, arraste,
  barra de propriedades e o conceito de `binding` já renderizado no canvas); adicionar o seletor
  de slot na barra e o rótulo do slot sobre o elemento — mesmo padrão visual dos bindings de IA.

### Etapa 3 — Planejador (`deck_plan.py`)

- Inventário da semana por atividade: nº de textos, tabelas, imagens, gráficos.
- Inventário de cada slide-variante do template: slots disponíveis por tipo.
- Escolha por **encaixe** (pontuação por tipo atendido e penalidade por slot vazio), substituindo
  a escolha por índice.
- Excedente vira slide adicional (duplicando a variante adequada) — **nada é descartado em
  silêncio**; o que não couber vira aviso explícito no retorno da geração.
- Slots vazios: removidos (v1, sem redistribuição — decisão registrada na seção 6).

### Etapa 4 — Medição de texto (`text_metrics.py`)

- Largura por glifo a partir do TTF instalado (`fontTools`/PIL), com cache por (fonte, tamanho).
- Quebra de linha e altura → decide reduzir corpo (até um mínimo), truncar com reticências ou
  paginar.
- Fonte ausente na máquina: **avisa antes de gerar**, em vez de deixar o deck sair torto.
- Substitui o cálculo por contagem de caracteres com fator fixo (`_chars_per_line`), que é
  cego para a fonte.

### Etapa 5 — Integração

- `use_template` passa a usar o exportador novo **nos dois tipos de template**: PPT enviado e
  weekly do histórico (que hoje vai pelo LLM — `clone_only` fica `False` e o modelo decide o
  layout).
- Remover o ramo de posicionamento por LLM do fluxo de template.
- Flag de configuração para voltar ao caminho antigo em caso de problema.

### Etapa 6 — Verificação automática

Invariantes checadas por teste, sobre o arquivo gerado:

1. Nenhum shape fora da área da página.
2. Nenhuma sobreposição entre slots preenchidos.
3. Nenhum texto remanescente do modelo (comparação contra o conteúdo da semana).
4. Nenhum anexo perdido sem aviso.
5. Contagem de slides = esperada pelo plano.

Verificação visual: LibreOffice **não está instalado** nesta máquina. Instalar `soffice` permite
renderizar o .pptx em PNG e comparar automaticamente — fica como opcional recomendado.

---

## 5. Riscos

| Risco | Mitigação |
|---|---|
| API privada do python-pptx muda em upgrade | Todo uso isolado em `pptx_mutate.py`; versão pinada |
| Template com estrutura inesperada (sem slide de conteúdo, tudo agrupado) | Validação na importação com mensagem clara; fallback para o gerador próprio |
| Fonte do template ausente na máquina de deploy | Detecção e aviso antes da geração |
| Gráfico nativo com séries incompatíveis com os dados da semana | Preencher só quando o formato casa; senão, manter o gráfico do template e avisar |
| Regressão no caminho de quem não usa template | Gerador próprio (`pptx_service.py`) permanece intocado |

## 6. Decisões tomadas (registradas para não reabrir)

- **Slot vazio:** remove o elemento, sem redistribuir os demais (v1). Redistribuição exige
  solver de layout e fica para depois, se o uso pedir.
- **Marcação de slot:** visual, no editor existente — cobre tabela, imagem e gráfico, que
  marcador de texto (`{{titulo}}`) não cobre.
- **IA na geração do deck:** fora do posicionamento. Papel de revisora (ortografia, repetição,
  item esquecido) fica como possibilidade futura, sugerindo e nunca alterando.

## 7. Fora de escopo

Preenchimento de SmartArt, animações, correção estética automática ("esse slide ficou pesado"),
e reescrita de texto pela IA.
