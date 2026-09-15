# GridNote

Editor desktop portátil (um único `GridNote.exe`, sem instalação) para **CSV, TXT, XLSX e XLS**,
com visual azul-escuro inspirado no OneNote.

- **Pasta vinculada** na barra lateral (ou embaixo, em *Exibir*), com os arquivos da pasta e subpastas.
- **Colunas | Linhas** no topo: define o que um clique seleciona e o que o filtro esconde.
- **Substituir** (Ctrl+H): troca um texto por outro ou preenche a seleção inteira (ex.: coluna 5, "A" → "B").
- Células alteradas ficam em amarelo; arquivo com alteração mostra **● bolinha branca**.
- Fechar exige **Salvar**, **Descartar** ou **Voltar**.
- **Salvar como**: Excel (.xlsx/.xls), CSV, TXT (inclusive largura fixa, tipo CNAB), Word (.docx) e PDF.

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
| `gridnote/model.py` | dados da grade, filtro, desfazer/refazer, estado "não salvo" |
| `gridnote/editor.py` | página central: Colunas/Linhas, filtro, Substituir, grade |
| `gridnote/sidebar.py` | pasta vinculada e lista de abertos |
| `gridnote/mainwindow.py` | janela, menus, barra Salvar/Cancelar, fechamento obrigatório |
| `gridnote/theme.py` | cores, estilo e ícones |

## Limites conhecidos

- Excel é gravado só com **valores**: cores, fórmulas e mesclagens da planilha original não são mantidas (o app avisa no primeiro salvamento).
- `.xls`: até 65.536 linhas × 256 colunas. Word: até 63 colunas.
- Preferências ficam em `%APPDATA%\GridNote\config.json`.
