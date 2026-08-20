# Arquivos protegidos por DRM — o que o QWI precisa

Documento para a conversa com o time de Segurança da Informação / TI.
Estado: **em avaliação** — nada foi implementado ainda.

## O problema, em uma frase

Os usuários precisam anexar planilhas e apresentações protegidas às tarefas do
QWI, e hoje o sistema não consegue ler o conteúdo delas: o que ele recebe são
bytes cifrados.

## Por que isso acontece

O DRM corporativo protege por **processo**, através de um driver de filtro do
sistema de arquivos. O agente decide quem enxerga o conteúdo em claro:

- `EXCEL.EXE` está na lista de aplicações autorizadas → lê decifrado.
- O `python.exe` do QWI não está → lê o arquivo cifrado.

Os dois leem **o mesmo arquivo, no mesmo caminho, com o mesmo usuário**. A
diferença é só qual processo está pedindo.

Portanto o QWI não precisa (nem quer) decifrar nada por conta própria. Ele
precisa de **uma forma autorizada de ler**.

## As três formas possíveis, da melhor para a pior

### Opção 1 — Autorizar o processo do QWI na política do DRM

Registrar o executável do backend
(`<caminho>\backend\venv\Scripts\python.exe`) como aplicação autorizada.

- **Esforço de desenvolvimento: nenhum.** O upload de anexos e de templates
  já funciona; ele passaria a enxergar o conteúdo e seguiria o fluxo normal.
- Cobre **todos** os formatos, inclusive PDF e imagem.
- Não muda nada no plano de instalação.
- **Pergunta para a segurança:** é possível autorizar esse processo? Há alguma
  restrição (assinatura digital do executável, caminho fixo, hash)?

### Opção 2 — SDK ou utilitário de servidor do fornecedor

Vários produtos de DRM oferecem um agente/SDK para processamento em lote no
servidor, feito exatamente para este caso.

- Esforço pequeno: um adaptador que chama o utilitário.
- Não exige Office nem sessão gráfica.
- Cobre todos os formatos, dependendo do produto.
- **Pergunta para a segurança:** o produto tem SDK/CLI de servidor? Sob quais
  condições de licença e auditoria?

### Opção 3 — Ponte pelo Microsoft Office (automação COM)

O QWI abriria o arquivo pelo Excel/PowerPoint/Word instalado no servidor (que
o agente já autoriza) e pediria uma cópia limpa para processar.

Funciona, e já foi testado manualmente — mas é a alternativa mais cara:

- **Exige sessão interativa logada.** A automação do Office não funciona em
  Session 0 (serviços do Windows / tarefa agendada com "executar estando o
  usuário conectado ou não"). O plano atual de instalação usa exatamente esse
  modo e **precisaria mudar**.
- **Processamento serial.** COM não é reentrante: um arquivo por vez, com fila,
  timeout e limpeza de processos órfãos do Office.
- **Não cobre PDF nem imagem** — nenhuma aplicação do Office abre esses
  formatos. Se eles também chegam protegidos, só as opções 1 ou 2 resolvem.
- Depende de Office instalado, licenciado e atualizado no servidor.

## O que sai desse processo perde a proteção

Isto precisa ser dito com todas as letras, em qualquer das três opções:

O conteúdo lido é gravado no banco do QWI (tabelas dos anexos) e usado para
gerar apresentações `.pptx` **sem proteção**, que ficam no disco do servidor,
podem ser baixadas e podem ser compartilhadas com colegas dentro do sistema.

Ou seja: o QWI passa a ser um ponto onde conteúdo protegido vira conteúdo
aberto. Isso é inerente ao pedido — o objetivo é justamente montar o weekly a
partir desses dados. Mas é uma decisão de política, não técnica, e precisa do
aval de vocês. Pontos a definir:

- Quem pode anexar arquivos protegidos (todos os usuários? um grupo?).
- Retenção da cópia em claro (proposta: pasta restrita, apagada logo após o
  processamento).
- Registro de auditoria: quem subiu, qual arquivo, quando.
- Se os `.pptx` gerados pelo QWI devem, eles mesmos, ser protegidos ao sair.

## Como responder isto com evidência

Rode no **servidor**, com arquivos protegidos de verdade:

```
python scripts\diagnostico_drm.py C:\caminho\planilha.xlsx C:\caminho\slides.pptx
```

O script informa o ambiente (inclusive se a sessão é interativa), lista
processos que aparentam ser o agente de DRM, e testa cada arquivo pelos dois
caminhos possíveis — leitura direta e via Office. No fim dá um veredito
dizendo qual opção está disponível. Ele é somente-leitura: a cópia limpa do
teste vai para pasta temporária e é apagada.

**Importante:** teste com arquivos comprovadamente protegidos. Uma cópia que
já passou por liberação lê normalmente e daria um falso positivo.

## Onde isto encaixa no sistema (para referência técnica)

O ponto de entrada é pequeno e localizado — os dois lugares onde um arquivo
vira dado:

| Fluxo | Arquivo | Função |
|---|---|---|
| Anexo de tarefa → bloquinho do editor | `app/services/business.py` | `save_attachment` → `extract_table` |
| Template de PPT → slots | `app/api/routes/pptx_templates.py` | `upload_template` → `import_pptx_to_layout` |

Nas opções 2 e 3 entra **uma** etapa antes desses parsers ("bytes possivelmente
protegidos → bytes em claro"); todo o resto do sistema segue igual, e para o
usuário o upload continua sendo o mesmo. Na opção 1 não entra etapa nenhuma.
