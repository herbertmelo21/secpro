#Requires AutoHotkey v2.0
SetTitleMatchMode(2)
SetKeyDelay(100, 100)

; ═══════════════════════════════════════════════════════════════════════════
; CONFIGURAÇÃO DE NAVEGAÇÃO NO GRID
; ═══════════════════════════════════════════════════════════════════════════

; ┌─────────────────────────────────────────────────────────────────────────┐
; │ MODO 1: Navegação por CONTROLES (USE ClassNN)                          │
; │                                                                          │
; │ VANTAGEM: Funciona independente de cliques/mouse, mais confiável        │
; │ DESVANTAGEM: Precisa descobrir ClassNN dos controles                    │
; │                                                                          │
; │ Para descobrir ClassNN:                                                 │
; │ 1. Execute: AutoHotkey vpro_control_discovery.ahk                       │
; │ 2. Passe mouse sobre cada controle                                      │
; │ 3. Pressione F1 para registrar                                          │
; │ 4. Copie o ClassNN para as constantes abaixo                            │
; └─────────────────────────────────────────────────────────────────────────┘

; USAR_CONTROL_MODE := true para usar ControlSetText/ControlClick
; USAR_CONTROL_MODE := false para usar Send/Click (fallback)
USAR_CONTROL_MODE := false

; Título da janela VPro/SecPro (use Window Spy para verificar)
VPRO_TITULO := "Seção poligonal"

; ClassNN dos controles descobertos com vpro_control_discovery.ahk:
; Deixe vazios para usar modo fallback (Send/Click)
X_CELL_CLASSNN := ""      ; Ex: "Edit1", "SysListView321", etc.
Y_CELL_CLASSNN := ""      ; Ex: "Edit2", "SysListView322", etc.
PLUS_BUTTON_CLASSNN := "" ; Ex: "Button1", "SysButton5", etc.

; Coordenadas do botão "+" para modo Click (fallback)
PLUS_X := 38
PLUS_Y := 137

; Modo de navegação (fallback) após clicar no "+":
; "tab_tab"      → Send Tab, Tab (simples, pode falhar se grid tiver foco)
; "down_left"    → Send Down, Left (alternativa ao Tab)
; "click_x_cell" → Clica direto na célula x(m) da linha (mais preciso)
AFTER_PLUS_MODE := "click_x_cell"

; Constantes para modo "click_x_cell" (fallback):
X_CELL_X := 135
X_CELL_Y_FIRST := 181
ROW_HEIGHT := 19

coords := [
    ["0,441", "0,000"],
    ["0,441", "0,040"],
    ["0,467", "0,044"],
    ["0,490", "0,057"],
    ["0,509", "0,075"],
    ["0,521", "0,099"],
    ["0,525", "0,125"],
    ["0,521", "0,152"],
    ["0,509", "0,175"],
    ["0,490", "0,194"],
    ["0,466", "0,206"],
    ["0,440", "0,210"],
    ["0,414", "0,206"],
    ["0,390", "0,194"],
    ["0,371", "0,175"],
    ["0,359", "0,152"],
    ["0,355", "0,125"],
    ["0,359", "0,099"],
    ["0,371", "0,075"],
    ["0,390", "0,057"],
    ["0,413", "0,044"],
    ["0,440", "0,040"],
    ["0,440", "0,000"],
    ["0,220", "0,000"],
    ["0,220", "0,040"],
    ["0,247", "0,044"],
    ["0,270", "0,057"],
    ["0,289", "0,075"],
    ["0,301", "0,099"],
    ["0,305", "0,125"],
    ["0,301", "0,152"],
    ["0,289", "0,175"],
    ["0,270", "0,194"],
    ["0,246", "0,206"],
    ["0,220", "0,210"],
    ["0,194", "0,206"],
    ["0,170", "0,194"],
    ["0,151", "0,175"],
    ["0,139", "0,152"],
    ["0,135", "0,125"],
    ["0,139", "0,099"],
    ["0,151", "0,075"],
    ["0,170", "0,057"],
    ["0,193", "0,044"],
    ["0,219", "0,040"],
    ["0,219", "0,000"],
    ["0,000", "0,000"],
    ["0,000", "0,040"],
    ["0,027", "0,044"],
    ["0,050", "0,057"],
    ["0,069", "0,075"],
    ["0,081", "0,099"],
    ["0,085", "0,125"],
    ["0,081", "0,152"],
    ["0,069", "0,175"],
    ["0,050", "0,194"],
    ["0,026", "0,206"],
    ["-0,000", "0,210"],
    ["-0,026", "0,206"],
    ["-0,050", "0,194"],
    ["-0,069", "0,175"],
    ["-0,081", "0,152"],
    ["-0,085", "0,125"],
    ["-0,081", "0,099"],
    ["-0,069", "0,075"],
    ["-0,050", "0,057"],
    ["-0,027", "0,044"],
    ["-0,001", "0,040"],
    ["-0,001", "0,000"],
    ["-0,220", "0,000"],
    ["-0,220", "0,040"],
    ["-0,194", "0,044"],
    ["-0,170", "0,057"],
    ["-0,152", "0,075"],
    ["-0,140", "0,099"],
    ["-0,136", "0,125"],
    ["-0,140", "0,152"],
    ["-0,152", "0,175"],
    ["-0,171", "0,194"],
    ["-0,194", "0,206"],
    ["-0,221", "0,210"],
    ["-0,247", "0,206"],
    ["-0,270", "0,194"],
    ["-0,289", "0,175"],
    ["-0,301", "0,152"],
    ["-0,306", "0,125"],
    ["-0,301", "0,099"],
    ["-0,290", "0,075"],
    ["-0,271", "0,057"],
    ["-0,247", "0,044"],
    ["-0,221", "0,040"],
    ["-0,221", "0,000"],
    ["-0,439", "0,000"],
    ["-0,439", "0,040"],
    ["-0,413", "0,044"],
    ["-0,389", "0,056"],
    ["-0,371", "0,075"],
    ["-0,359", "0,099"],
    ["-0,355", "0,125"],
    ["-0,359", "0,152"],
    ["-0,371", "0,175"],
    ["-0,390", "0,194"],
    ["-0,413", "0,206"],
    ["-0,440", "0,210"],
    ["-0,466", "0,206"],
    ["-0,489", "0,194"],
    ["-0,508", "0,175"],
    ["-0,520", "0,152"],
    ["-0,525", "0,125"],
    ["-0,520", "0,099"],
    ["-0,509", "0,075"],
    ["-0,490", "0,056"],
    ["-0,466", "0,044"],
    ["-0,440", "0,040"],
    ["-0,440", "0,000"],
    ["-0,613", "0,000"],
    ["-0,625", "0,012"],
    ["-0,625", "0,050"],
    ["-0,575", "0,060"],
    ["-0,575", "0,195"],
    ["-0,600", "0,200"],
    ["-0,600", "0,250"],
    ["0,600", "0,250"],
    ["0,600", "0,200"],
    ["0,575", "0,195"],
    ["0,575", "0,060"],
    ["0,625", "0,050"],
    ["0,625", "0,012"],
    ["0,613", "0,000"],
    ["0,441", "0,000"]
]

; ═══════════════════════════════════════════════════════════════════════════
; USO DO SCRIPT
; ═══════════════════════════════════════════════════════════════════════════
;
; MODO COM CONTROLES (USE CLASSNN):
; 1. Execute: AutoHotkey vpro_control_discovery.ahk
; 2. Descubra ClassNN dos controles X, Y e botão "+"
; 3. Preencha as constantes X_CELL_CLASSNN, Y_CELL_CLASSNN, PLUS_BUTTON_CLASSNN
; 4. Ajuste USAR_CONTROL_MODE := true
; 5. Abra VPro/SecPro
; 6. Pressione F8
;
; MODO FALLBACK (SEM CLASSNN):
; 1. Deixe X_CELL_CLASSNN, Y_CELL_CLASSNN, PLUS_BUTTON_CLASSNN vazios
; 2. Defina USAR_CONTROL_MODE := false
; 3. Abra VPro/SecPro
; 4. Clique no "+" uma vez
; 5. Clique na célula x(m) da linha 1
; 6. Pressione F8
;
; ═══════════════════════════════════════════════════════════════════════════

F8:: {
    ; CoordMode("Mouse", "Window") garante que Click() usa coordenadas relativas à janela
    ; e não absolutas da tela. Isso é crítico para evitar cliques fora do VPro.
    CoordMode("Mouse", "Window")

    ; Encontra a janela do VPro/SecPro
    vpro_hwnd := WinExist(VPRO_TITULO)
    if not vpro_hwnd {
        MsgBox(48, "Erro", "VPro/SecPro não encontrado. Verifique o título.")
        return
    }

    ; Ativa a janela e aguarda
    WinActivate("ahk_id " . vpro_hwnd)
    WinWaitActive("ahk_id " . vpro_hwnd, , 2)
    Sleep(1000)

    for i, row in coords {
        ; Verifica se a janela foi fechada (não apenas se perdeu foco)
        if !WinExist("ahk_id " . vpro_hwnd) {
            MsgBox(48, "Erro", "A janela do VPro foi fechada. Automação interrompida.")
            return
        }

        ; Reativa a janela e aguarda
        WinActivate("ahk_id " . vpro_hwnd)
        Sleep(200)

        x_value := row[1]
        y_value := row[2]

        if USAR_CONTROL_MODE and (X_CELL_CLASSNN != "") {
            ; ───────────────────────────────────────────────────────────
            ; MODO COM CONTROLES (RECOMENDADO)
            ; ───────────────────────────────────────────────────────────

            ; Foca a célula X
            ControlFocus(X_CELL_CLASSNN, "ahk_id " . vpro_hwnd)
            Sleep(20)

            ; Define texto na célula X
            ControlSetText(X_CELL_CLASSNN, x_value, "ahk_id " . vpro_hwnd)
            Sleep(20)

            ; Foca a célula Y
            if (Y_CELL_CLASSNN != "") {
                ControlFocus(Y_CELL_CLASSNN, "ahk_id " . vpro_hwnd)
                Sleep(20)
                ControlSetText(Y_CELL_CLASSNN, y_value, "ahk_id " . vpro_hwnd)
            } else {
                ; Fallback para Y (Tab)
                Send("{Tab}")
                SendText(y_value)
            }
            Sleep(20)

            ; Cria nova linha clicando no "+"
            if i < coords.Length {
                if (PLUS_BUTTON_CLASSNN != "") {
                    ControlClick(PLUS_BUTTON_CLASSNN, "ahk_id " . vpro_hwnd)
                } else {
                    ; Fallback para botão "+" (Click)
                    ; Coordenadas PLUS_X, PLUS_Y são relativas à janela do VPro (por CoordMode)
                    Click(PLUS_X, PLUS_Y)
                }
                Sleep(300)

                ; Reativa janela após clique no "+"
                WinActivate("ahk_id " . vpro_hwnd)
                Sleep(200)

                ; Aguarda a nova linha ser criada
                Sleep(300)
            }
        } else {
            ; ───────────────────────────────────────────────────────────
            ; MODO FALLBACK (Send/Click) - Sem ClassNN
            ; ───────────────────────────────────────────────────────────

            SendText(x_value)     ; Digita X
            Sleep(150)

            Send("{Tab}")         ; Move para Y
            Sleep(150)

            SendText(y_value)     ; Digita Y
            Sleep(150)

            if i < coords.Length {
                ; Clica no botão "+" para criar nova linha
                ; Coordenadas PLUS_X, PLUS_Y são relativas à janela do VPro (por CoordMode)
                Click(PLUS_X, PLUS_Y)
                Sleep(300)

                ; Reativa janela após clique no "+"
                WinActivate("ahk_id " . vpro_hwnd)
                Sleep(200)

                ; Navega conforme modo selecionado
                if AFTER_PLUS_MODE = "tab_tab" {
                    Send("{Tab}")
                    Send("{Tab}")
                }
                else if AFTER_PLUS_MODE = "down_left" {
                    Send("{Down}")
                    Send("{Left}")
                }
                else if AFTER_PLUS_MODE = "click_x_cell" {
                    ; Clica na célula x(m) da próxima linha
                    ; Coordenadas X_CELL_X e clickY são relativas à janela do VPro (por CoordMode)
                    clickY := X_CELL_Y_FIRST + i * ROW_HEIGHT
                    Click(X_CELL_X, clickY)
                    Sleep(300)
                }
            }
        }
    }

    MsgBox(64, "Sucesso", "Preenchimento de " . coords.Length . " coordenadas concluído!")
}
