# Executar AutoHotkey do Windows a partir do WSL

Script bash para executar arquivos `.ahk` gerados no WSL diretamente no Windows usando AutoHotkey v2.

## Objetivo

Como o projeto está em WSL mas o VPro/SecPro roda no Windows, este script:

1. Localiza o AutoHotkey v2 instalado no Windows
2. Converte o caminho do arquivo AHK de Linux para Windows
3. Executa o arquivo `.ahk` no Windows
4. Exibe instruções de uso no console do WSL

## Pré-requisitos

- **WSL2**: Projeto rodando em WSL (como está)
- **AutoHotkey v2**: Instalado no Windows
  - Download: https://www.autohotkey.com/
  - Instale em: `C:\Program Files\AutoHotkey`
- **VPro/SecPro**: Aberto e visível no Windows

## Uso

### Executar com arquivo padrão (LA25.ahk)

```bash
bash scripts/run_vpro_ahk_from_wsl.sh
```

### Executar com arquivo específico

```bash
bash scripts/run_vpro_ahk_from_wsl.sh section/ahk/LA25.ahk
bash scripts/run_vpro_ahk_from_wsl.sh section/ahk/outra_secao.ahk
```

## Fluxo de Execução

### 1. Preparação no Windows

Antes de executar o script:

```bash
# No WSL
bash scripts/run_vpro_ahk_from_wsl.sh section/ahk/LA25.ahk
```

Instruções aparecerão na tela:

```
📋 INSTRUÇÕES:

1. ✓ Certifique-se de que o VPro/SecPro está aberto no Windows
     e a janela está VISÍVEL

2. ✓ Navegue até a tabela de coordenadas no VPro/SecPro

3. ✓ Clique UMA VEZ no botão "+" para criar a PRIMEIRA linha

4. ✓ Clique na célula x(m) da primeira linha

5. ⏳ Aguarde o script AHK carregar (próximo passo)

6. 🔴 Quando o AHK estiver carregado, pressione F8 para iniciar
```

### 2. Executar no Windows

Após seguir as instruções, o script carrega o AutoHotkey:

```
Carregando script AHK no Windows...

✓ AHK carregado (PID: 1234)

Agora pressione F8 para preencher as coordenadas.
```

### 3. Usar F8 no Windows

Com o VPro/SecPro aberto:

1. Pressione **F8** para iniciar o preenchimento automático
2. Coordenadas serão digitadas e linhas criadas automaticamente
3. Para parar: pressione **Ctrl+C** no WSL ou feche VPro

## Tratamento de Erros

### Erro: Arquivo AHK não encontrado

```
[ERRO] Arquivo AHK não encontrado: section/ahk/LA25.ahk
```

**Solução**: Certifique-se de que:
- O arquivo existe: `ls section/ahk/LA25.ahk`
- Você está no diretório correto: `pwd`
- O caminho está correto (use padrão se necessário): `bash scripts/run_vpro_ahk_from_wsl.sh`

### Erro: AutoHotkey não encontrado

```
[ERRO] AutoHotkey v2 não encontrado no Windows.

Locais procurados:
  ✗ /mnt/c/Program Files/AutoHotkey/v2/AutoHotkey64.exe
  ✗ /mnt/c/Program Files/AutoHotkey/AutoHotkey64.exe
  ✗ /mnt/c/Program Files/AutoHotkey/AutoHotkey.exe
```

**Solução**:
1. Abra PowerShell como administrador no Windows
2. Baixe e instale AutoHotkey v2 de: https://www.autohotkey.com/
3. Certifique-se de instalar em: `C:\Program Files\AutoHotkey`
4. Tente novamente

## Variantes do AutoHotkey

O script procura AutoHotkey em 3 locais (por prioridade):

1. `/mnt/c/Program Files/AutoHotkey/v2/AutoHotkey64.exe`
   - AutoHotkey v2 instalação padrão (versão 64-bit)
2. `/mnt/c/Program Files/AutoHotkey/AutoHotkey64.exe`
   - Variante alternativa
3. `/mnt/c/Program Files/AutoHotkey/AutoHotkey.exe`
   - Versão 32-bit ou genérica

Se o AutoHotkey estiver instalado em outro local, edite o script e adicione o caminho na lista `CANDIDATES`.

## Como Converter o Caminho Linux para Windows

O script usa `wslpath -w` automaticamente:

```bash
# Entrada (Linux em WSL)
section/ahk/LA25.ahk

# Saída (Windows)
\\wsl.localhost\Ubuntu\home\hcmelo\projects\secpro\section\ahk\LA25.ahk
```

Este é o caminho UNC que Windows entende para acessar arquivos no WSL.

## Parar a Execução

Para parar o script a qualquer momento:

**No WSL**:
```bash
# Pressione Ctrl+C
```

**No Windows**:
- Feche a janela do VPro/SecPro
- Ou use `Ctrl+C` no AutoHotkey se houver console visível

## Arquivos Relacionados

- `scripts/generate_vpro_ahk_from_libredwg.py`: Gera arquivos `.ahk`
- `scripts/run_vpro_ahk_from_wsl.sh`: Executa arquivos `.ahk` no Windows (este arquivo)
- `section/ahk/`: Diretório com arquivos `.ahk` gerados
- `README_generate_vpro_ahk.md`: Documentação do gerador de `.ahk`

## Fluxo Completo de Uso

```bash
# 1. No WSL: Gerar arquivo AHK a partir do JSON
python3 scripts/generate_vpro_ahk_from_libredwg.py
# Gera: section/ahk/LA25.ahk

# 2. No WSL: Executar AHK no Windows
bash scripts/run_vpro_ahk_from_wsl.sh section/ahk/LA25.ahk
# Carrega o arquivo no AutoHotkey do Windows

# 3. No Windows: Preparar VPro/SecPro
# - Abrir janela
# - Clicar no "+" uma vez
# - Clicar na célula x(m) linha 1

# 4. No Windows: Pressionar F8
# - Coordenadas preenchidas automaticamente
```

## Exemplos

### Exemplo 1: Usar arquivo padrão

```bash
$ cd ~/projects/secpro
$ bash scripts/run_vpro_ahk_from_wsl.sh

╔════════════════════════════════════════════════════════════════╗
║  AutoHotkey v2 - Executando Script AHK do Windows             ║
╚════════════════════════════════════════════════════════════════╝

📍 Arquivo AHK encontrado:
   Linux:   section/ahk/LA25.ahk
   Windows: \\wsl.localhost\Ubuntu\home\hcmelo\projects\secpro\section\ahk\LA25.ahk

🔧 AutoHotkey encontrado:
   /mnt/c/Program Files/AutoHotkey/AutoHotkey64.exe

📋 INSTRUÇÕES:
1. ✓ Certifique-se de que o VPro/SecPro está aberto no Windows...
```

### Exemplo 2: Usar arquivo específico

```bash
$ bash scripts/run_vpro_ahk_from_wsl.sh section/ahk/outra_secao.ahk
```

### Exemplo 3: Criar alias no `.bashrc`

```bash
# Adicione ao ~/.bashrc:
alias run-vpro='bash ~/projects/secpro/scripts/run_vpro_ahk_from_wsl.sh'

# Depois use:
run-vpro
run-vpro section/ahk/LA25.ahk
```

## Notas

- O script executa o AHK em background (PID mostrado)
- Use `Ctrl+C` para parar
- Se o VPro não estiver visível, o AHK pode não conseguir clicar/digitar
- A janela do AutoHotkey pode não aparecer (roda em background)
- Se nada acontecer, verifique se o modo "click_x_cell" precisa ser calibrado
