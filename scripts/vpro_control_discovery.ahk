; ═══════════════════════════════════════════════════════════════════════════
; VPro/SecPro Control Discovery Tool
; Ferramenta para descobrir ClassNN dos controles da tabela de coordenadas
; ═══════════════════════════════════════════════════════════════════════════
;
; INSTRUÇÕES:
;
; 1. Abra VPro/SecPro
; 2. Navegue até a tabela de coordenadas
; 3. Execute este script: AutoHotkey vpro_control_discovery.ahk
; 4. Clique em cada controle enquanto o script está rodando:
;    - Célula X (primeira linha)
;    - Célula Y (primeira linha)
;    - Botão "+" (criar nova linha)
; 5. O script mostrará o ClassNN, hWnd e ControlGetFocus de cada controle
; 6. Copie as informações para usar no script de automação
;
; ═══════════════════════════════════════════════════════════════════════════

#Requires AutoHotkey v2.0
SetTitleMatchMode(2)

; Encontra a janela do VPro/SecPro
vpro_title := "VPro"  ; Ajuste se o título for diferente
vpro_hwnd := 0

for hwnd in WinGetControls("ahk_class") {
    if InStr(WinGetTitle(hwnd), vpro_title) {
        vpro_hwnd := hwnd
        break
    }
}

if vpro_hwnd = 0 {
    MsgBox(48, "Aviso", "VPro/SecPro não encontrado. Certifique-se de que está aberto.")
    ExitApp
}

; Tooltip que segue o mouse
global last_control := ""
global last_hwnd := ""
global last_classnn := ""

; Listener que mostra informações ao passar o mouse
SetTimer(UpdateControlInfo, 100)

UpdateControlInfo() {
    global last_control, last_hwnd, last_classnn

    MouseGetPos(&mouse_x, &mouse_y, &hwnd)

    ; Tenta obter o controle sob o mouse
    try {
        control_hwnd := ControlGetHwnd(, "ahk_id " hwnd)
        if control_hwnd {
            control_info := ControlGetClassNN(control_hwnd)
            focused := ControlGetFocus("ahk_id " hwnd)

            if control_hwnd != last_hwnd {
                last_control := control_info
                last_hwnd := control_hwnd
                last_classnn := control_info
            }

            ; Mostra tooltip com informações
            info := "Controle sob o mouse:`n`n"
            info .= "ClassNN: " . last_classnn . "`n"
            info .= "hWnd: " . Format("0x{:X}", control_hwnd) . "`n"
            info .= "Foco atual: " . (focused ? focused : "(nenhum)")

            ToolTip(info, mouse_x + 10, mouse_y + 10)
        }
    }
}

; Hotkey para clicar e registrar
F1:: {
    global last_control, last_hwnd, last_classnn

    if last_hwnd = 0 {
        MsgBox(48, "Aviso", "Passe o mouse sobre um controle e pressione F1 para registrar.")
        return
    }

    ; Exibe janela com informações
    MsgBox(
        64,
        "Controle Descoberto",
        "ClassNN: " . last_classnn . "`n"
        . "hWnd: " . Format("0x{:X}", last_hwnd) . "`n`n"
        . "Copie essas informações para o script de automação."
    )
}

; Hotkey para sair
Esc:: {
    ToolTip()
    MsgBox(64, "Saindo", "Script de descoberta finalizado.`n`nUse as informações coletadas no script de automação.")
    ExitApp
}

; Instrução na tela
MsgBox(
    64,
    "VPro Control Discovery",
    "COMO USAR:`n`n"
    . "1. Passe o mouse sobre cada controle da tabela`n"
    . "2. Veja as informações no tooltip (ClassNN, hWnd, Foco)`n"
    . "3. Pressione F1 para registrar o controle atual`n"
    . "4. Pressione ESC para sair`n`n"
    . "CONTROLES A DESCOBRIR:`n"
    . "- Célula X (primeira linha)`n"
    . "- Célula Y (primeira linha)`n"
    . "- Botão '+' (criar nova linha)`n`n"
    . "Pressione OK para começar."
)

ToolTip()
MsgBox(0, "", "Passe o mouse sobre os controles. Pressione F1 para registrar, ESC para sair.")
