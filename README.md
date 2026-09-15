# GridNote

Editor desktop portátil para **CSV, TXT, XLSX e XLS**, com visual azul-escuro inspirado no OneNote.
É um único `GridNote.exe`: não precisa instalar nada nem ter Python ou Excel no computador.

- **Pasta vinculada** na barra lateral, com os arquivos da pasta e das subpastas.
- **Colunas | Linhas | Célula** no topo: define o que um clique seleciona.
- **Dividir** cada linha por separador ou **por caractere**, para arquivos de posição fixa (CNAB, arquivos de máquina).
- **Salvar ou cancelar obrigatório**: arquivo com alteração mostra a **● bolinha branca**.
- **Salvar como** Excel (.xlsx/.xls), CSV, TXT, Word (.docx) e PDF.

---

## Como usar

### 1. Abrir o programa

Dê dois cliques em `GridNote.exe`. Na primeira vez, o Windows pode mostrar o aviso do SmartScreen,
porque o executável não tem assinatura digital: clique em **Mais informações → Executar assim mesmo**.

### 2. Vincular uma pasta

1. Na barra lateral, clique em **Vincular pasta** e escolha a pasta onde ficam os arquivos.
2. Todos os `.csv`, `.txt`, `.xlsx` e `.xls` dela aparecem na lateral, como os cadernos do OneNote.
3. **Um clique** num arquivo abre ele. A pasta fica salva para as próximas vezes.

Também dá para usar **Abrir arquivo** (Ctrl+O) ou arrastar arquivos para a janela.
Para colocar a pasta embaixo da tela, use **Exibir → Pasta embaixo da tela**.

### 3. Abrir um arquivo de texto (.txt)

Ao abrir um `.txt`, o programa pergunta como dividir cada linha em colunas e mostra uma prévia:

| Opção | Quando usar |
|---|---|
| Detectar automaticamente | Arquivos com separador (`;`, `,`, tabulação ou `\|`) |
| **Cada caractere em uma coluna** | Arquivos de posição fixa: CNAB, remessa/retorno de banco, arquivos de máquina |
| Linha inteira em uma coluna | Textos sem estrutura |

CSV e Excel abrem direto. Se a primeira linha tiver só nomes, **1ª linha é cabeçalho** já vem marcado,
e ela fica protegida das edições.

### 4. Escolher o modo: Colunas, Linhas ou Célula

| Modo | Um clique seleciona | Serve para |
|---|---|---|
| **Colunas** | a coluna inteira | trocar ou preencher uma coluna toda |
| **Linhas** | a linha inteira | trabalhar registro por registro |
| **Célula** | só a célula clicada | corrigir valores um a um |

Segure **Ctrl** para selecionar várias colunas, linhas ou células.

### 5. Editar

- **Editar uma célula:** modo **Célula**, clique na célula e digite (ou F2).
- **Preencher uma coluna inteira:** modo **Colunas**, clique no topo da coluna, digite o valor e aperte **Enter**.
  Todas as células selecionadas recebem o valor.
- **Trocar um valor por outro (Substituir, Ctrl+H):**
  1. Selecione a coluna (ou nada, para valer na tabela toda).
  2. Clique em **Substituir**.
  3. Em **Trocar um texto por outro**, preencha *Procurar* (ex.: `A`) e *Trocar por* (ex.: `B`).
  4. Marque **Só células inteiras iguais** para trocar apenas células cujo valor é exatamente `A`.
  5. Clique em **Aplicar**.
- **Inserir/excluir:** botões **+ Linha**, **+ Coluna** e **Excluir**, ou o clique direito na grade.
- **Copiar e colar:** Ctrl+C / Ctrl+V, compatível com o Excel.
- **Desfazer/refazer:** Ctrl+Z / Ctrl+Y.

Células alteradas ficam **destacadas em amarelo** até salvar.

### 6. Filtrar

No campo de filtro do topo (Ctrl+F):

- **Contém / É igual a / Começa com / Termina com:** mostra só o que tem o texto.
  - No modo **Colunas**, com *em: Todas as colunas*, esconde as colunas que não têm o texto.
  - No modo **Linhas**, ou escolhendo uma coluna em *em:*, mostra só as linhas que combinam.
  - Com a divisão **por caractere**, a busca olha o texto da linha inteira (ex.: `55`).
- **Nº da linha:** digite os números das linhas, ex.: `3, 6, 9, 15, 22` ou `10-20`.

Com o filtro ligado, selecionar uma coluna pega **só as linhas visíveis**.

### 7. Dividir por caractere ou separador

O botão **Dividir** no topo muda como cada linha é separada, em qualquer arquivo aberto:
cada caractere em uma coluna, por `;`, `,`, tabulação, `|`, ou a linha inteira.

Ao salvar em CSV ou TXT, **cada linha volta a ser o texto original**, com os mesmos separadores.

### 8. Exemplo: trocar "55" por "5" em algumas linhas de um arquivo de posição fixa

1. Abra o `.txt` com **Cada caractere em uma coluna** (ou use **Dividir → Cada caractere**).
2. No filtro, escolha **Nº da linha** e digite `3, 6, 9, 15, 22`.
3. No modo **Colunas**, clique no topo da coluna do **segundo 5**.
4. Clique em **Apagar e puxar ←** (Ctrl+-). O caractere some e o resto da linha anda uma casa para a esquerda.
5. Limpe o filtro, confira e clique em **Salvar**.

> **Limpar conteúdo** deixa a posição vazia (vira espaço ao salvar).
> **Apagar e puxar ←** remove a posição de verdade, e a linha fica um caractere menor.
> O contrário é **Inserir célula e empurrar para a direita** (Ctrl++), no clique direito.

### 9. Salvar ou cancelar

Enquanto houver alterações, o arquivo mostra a **● bolinha branca** na lateral e a barra de baixo fica amarela.
Você pode trocar de arquivo à vontade, mas para **fechar** o arquivo ou o programa é preciso escolher:

- **Salvar** (Ctrl+S): grava no próprio arquivo.
- **Cancelar alterações:** volta o arquivo para como estava no último salvamento.
- **Voltar e continuar editando.**

### 10. Salvar como outro formato

Clique em **Salvar como…** (Ctrl+Shift+S), escolha o formato e depois a pasta e o nome:

| Formato | Observação |
|---|---|
| Excel (.xlsx) | Recomendado. Mantém todas as abas. |
| Excel 97-2003 (.xls) | Até 65.536 linhas e 256 colunas. |
| CSV | Escolha separador e codificação (UTF-8 ou ANSI para sistemas antigos). |
| TXT | Com separador ou sem separador (largura fixa). |
| Word (.docx) | Tabela formatada, até 63 colunas. Só para leitura/impressão. |
| PDF | Para imprimir ou enviar. Só para leitura. |

Word e PDF são exportações: o arquivo aberto continua com as alterações pendentes até ser salvo
num formato editável.

### Atalhos

| Atalho | Ação |
|---|---|
| Ctrl+O | Abrir arquivo |
| Ctrl+S / Ctrl+Shift+S | Salvar / Salvar como |
| Ctrl+Z / Ctrl+Y | Desfazer / Refazer |
| Ctrl+F | Filtrar |
| Ctrl+H | Substituir |
| Ctrl+1 / Ctrl+2 | Modo Colunas / Linhas |
| Ctrl+C / Ctrl+V | Copiar / Colar |
| Delete | Limpar a seleção |
| Ctrl+- / Ctrl++ | Apagar e puxar ← / Inserir e empurrar → |
| Ctrl+W | Fechar arquivo |
| F1 | Ajuda |

---

## Gerar o executável

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```

Cria o `.venv`, roda os testes e gera `dist\GridNote.exe` (~26 MB).

## Desenvolver

```powershell
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m unittest discover tests
```

| Arquivo | O que faz |
|---|---|
| `gridnote/fileio.py` | leitura/gravação de todos os formatos (Word e PDF sem biblioteca extra) |
| `gridnote/model.py` | dados da grade, filtro, divisão, desfazer/refazer, estado "não salvo" |
| `gridnote/editor.py` | página central: modos, Dividir, filtro, Substituir, grade |
| `gridnote/sidebar.py` | pasta vinculada e lista de abertos |
| `gridnote/mainwindow.py` | janela, menus, barra Salvar/Cancelar, fechamento obrigatório |
| `gridnote/theme.py` | cores, estilo e ícones |

## Limites conhecidos

- Excel é gravado só com **valores**: cores, fórmulas e mesclagens da planilha original não são mantidas
  (o app avisa no primeiro salvamento).
- `.xls`: até 65.536 linhas × 256 colunas. Word: até 63 colunas.
- Preferências ficam em `%APPDATA%\GridNote\config.json`.
