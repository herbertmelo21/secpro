# Descoberta de Controles VPro/SecPro

Guia para descobrir os ClassNN dos controles da tabela de coordenadas e configurar automação robusta usando `ControlSetText` e `ControlClick` em vez de `Send` e `Click`.

## Problema

A navegação por `Send()` e `Click()` é frágil porque depende de:
- Foco da janela
- Estado do grid
- Configuração do teclado
- Timing e delays

A solução é usar **controles diretos** (`ControlSetText`, `ControlClick`, `ControlFocus`) que funcionam independentemente do foco da janela.

## Solução

### Passo 1: Descobrir ClassNN dos Controles

1. **Abra VPro/SecPro** com a tabela de coordenadas visível

2. **Execute o script de descoberta:**
   ```bash
   # No Windows (PowerShell ou Cmd)
   AutoHotkey vpro_control_discovery.ahk
   ```

3. **Siga as instruções na tela:**
   - Passe o mouse sobre a **célula X** (primeira linha)
   - Veja o ClassNN no tooltip
   - Pressione **F1** para registrar
   - Repita para **célula Y** e **botão "+"**

### Exemplo de Descoberta

Quando você passar o mouse sobre os controles, verá algo como:

```
Controle sob o mouse:

ClassNN: Edit1
hWnd: 0x00123456
Foco atual: (nenhum)
```

Registre os ClassNN descobertos:
- X (célula de entrada para coordenada X): `Edit1`
- Y (célula de entrada para coordenada Y): `Edit2`
- Botão "+" (criar nova linha): `Button1`

### Passo 2: Configurar o Script AHK

1. **Edite `section/ahk/LA25.ahk`**

2. **Preencha as constantes descobertas:**
   ```autohotkey
   USAR_CONTROL_MODE := true

   X_CELL_CLASSNN := "Edit1"        ; Célula X descoberta
   Y_CELL_CLASSNN := "Edit2"        ; Célula Y descoberta
   PLUS_BUTTON_CLASSNN := "Button1" ; Botão "+" descoberto
   ```

3. **Salve o arquivo**

### Passo 3: Usar o Script

1. **Abra VPro/SecPro** com a tabela de coordenadas

2. **Execute o script:**
   ```bash
   # No Windows
   AutoHotkey section/ahk/LA25.ahk
   ```

3. **Pressione F8** para iniciar a automação

4. **Aguarde o preenchimento automático**

## Modos de Operação

### Modo 1: ControlSetText + ControlClick (RECOMENDADO)

```autohotkey
USAR_CONTROL_MODE := true
X_CELL_CLASSNN := "Edit1"
Y_CELL_CLASSNN := "Edit2"
PLUS_BUTTON_CLASSNN := "Button1"
```

**Vantagens:**
- ✅ Funciona sem foco da janela
- ✅ Mais confiável e rápido
- ✅ Independente de configuração de teclado
- ✅ Não depende de mouse

**Desvantagens:**
- ⚠️ Precisa descobrir ClassNN (1-2 minutos)
- ⚠️ ClassNN pode variar entre versões do VPro

**Como funciona:**
```autohotkey
ControlFocus(X_CELL_CLASSNN, "ahk_id " . vpro_hwnd)     ; Foca célula X
ControlSetText(X_CELL_CLASSNN, x_value, ...)            ; Define valor X
ControlFocus(Y_CELL_CLASSNN, "ahk_id " . vpro_hwnd)     ; Foca célula Y
ControlSetText(Y_CELL_CLASSNN, y_value, ...)            ; Define valor Y
ControlClick(PLUS_BUTTON_CLASSNN, "ahk_id " . vpro_hwnd) ; Clica "+"
```

### Modo 2: Send + Click (FALLBACK)

```autohotkey
USAR_CONTROL_MODE := false
; ou deixe X_CELL_CLASSNN, Y_CELL_CLASSNN, PLUS_BUTTON_CLASSNN vazios
```

**Vantagens:**
- ✅ Funciona sem descobrir ClassNN
- ✅ Compatível com versões antigas

**Desvantagens:**
- ⚠️ Depende de foco da janela
- ⚠️ Pode falhar se grid tiver comportamento especial
- ⚠️ Timing pode ser crítico

**Como funciona:**
```autohotkey
SendText(x_value)              ; Digita valor X
Send("{Tab}")                  ; Move para célula Y
SendText(y_value)              ; Digita valor Y
Click(PLUS_X, PLUS_Y)          ; Clica botão "+"
Send("{Tab}") ou Send("{Down}") ; Navega para próxima linha
```

## Troubleshooting

### Problema: Script de Descoberta não mostra controles

**Solução:**
1. Certifique-se de que VPro/SecPro está aberto
2. Passe o mouse sobre a tabela (não fora dela)
3. Verifique se o título da janela é "VPro" (ajuste se necessário)

### Problema: ClassNN muda entre execuções

**Solução:**
- ClassNN é determinístico para a mesma versão do VPro
- Se mudar de versão, re-execute o script de descoberta
- Tomar nota dos ClassNN para referência futura

### Problema: ControlSetText não funciona

**Solução:**
1. Verifique se o ClassNN está correto
2. Tente aumentar `Sleep(20)` para `Sleep(50)`
3. Use modo fallback como alternativa

### Problema: ControlClick não funciona no botão

**Solução:**
1. Verifique o ClassNN do botão
2. Aumente `Sleep(80)` para `Sleep(150)`
3. Use Click() no modo fallback como alternativa

## Exemplos

### Exemplo 1: Descobrir ClassNN

```bash
# Execute no Windows
AutoHotkey scripts/vpro_control_discovery.ahk

# Resultado esperado:
# Passe o mouse sobre célula X → ClassNN: Edit1
# Passe o mouse sobre célula Y → ClassNN: Edit2
# Passe o mouse sobre botão "+" → ClassNN: Button1
```

### Exemplo 2: Configurar com ClassNN

```autohotkey
; section/ahk/LA25.ahk

USAR_CONTROL_MODE := true

X_CELL_CLASSNN := "Edit1"
Y_CELL_CLASSNN := "Edit2"
PLUS_BUTTON_CLASSNN := "Button1"

; Rest of the script...
```

### Exemplo 3: Usar Fallback

```autohotkey
; section/ahk/LA25.ahk

USAR_CONTROL_MODE := false

; Deixe ClassNN vazios:
X_CELL_CLASSNN := ""
Y_CELL_CLASSNN := ""
PLUS_BUTTON_CLASSNN := ""

; Rest of the script...
```

## Como Encontrar ClassNN Manualmente

Se o script de descoberta não funcionar, você pode usar **Window Spy**:

1. **Abra Window Spy** (AutoHotkey Tools → Window Spy)
2. **Mova o mouse sobre cada controle**
3. **Procure pela linha "ClassNN" no painel de controles**

Exemplo de saída:
```
Control Info:
ClassNN: Edit1
hWnd: 0x001234AB
ControlRef: ahk_id 0x001234AB
```

## Fluxo Completo

```bash
# 1. Gerar arquivo AHK (WSL)
python3 scripts/generate_vpro_ahk_from_libredwg.py

# 2. Descobrir ClassNN (Windows)
AutoHotkey scripts/vpro_control_discovery.ahk
# Anote: Edit1, Edit2, Button1

# 3. Configurar arquivo AHK (Windows)
# Edite section/ahk/LA25.ahk:
#   USAR_CONTROL_MODE := true
#   X_CELL_CLASSNN := "Edit1"
#   Y_CELL_CLASSNN := "Edit2"
#   PLUS_BUTTON_CLASSNN := "Button1"

# 4. Executar automação (Windows)
AutoHotkey section/ahk/LA25.ahk
# Pressione F8

# 5. Aguardar preenchimento
# ✓ 130 coordenadas preenchidas automaticamente
```

## Referência de Funções AHK

### ControlFocus
```autohotkey
ControlFocus(Control, WinTitle, WinText, ExcludeTitle, ExcludeText)
```
Move o foco para o controle especificado.

### ControlSetText
```autohotkey
ControlSetText(Control, NewText, WinTitle, WinText, ExcludeTitle, ExcludeText)
```
Define o texto do controle (como digitar, mas direto no controle).

### ControlClick
```autohotkey
ControlClick(Control, WinTitle, WinText, WhichButton, ClickCount, Options)
```
Clica no controle (como clicar com mouse, mas no controle específico).

### ControlGetFocus
```autohotkey
ControlGetFocus(WinTitle, WinText, ExcludeTitle, ExcludeText)
```
Retorna o ClassNN do controle que tem foco.

## Notas Importantes

1. **ClassNN é específico do VPro**: Se mudar de versão, re-descubra
2. **Use Tab para navegar entre controles**: Se ControlFocus não funcionar
3. **Aumente Sleep se não funcionar**: Timing é crítico em alguns casos
4. **Sempre tenha fallback**: Configure USAR_CONTROL_MODE := false como backup

## Documentação Relacionada

- `README_generate_vpro_ahk.md`: Documentação do gerador Python
- `README_run_vpro_ahk.md`: Como executar de WSL para Windows
