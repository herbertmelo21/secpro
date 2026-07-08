#Requires AutoHotkey v2.0
SetKeyDelay(30, 30)

; ═══════════════════════════════════════════════════════════════════════════
; CONFIGURAÇÃO DE NAVEGAÇÃO NO GRID
; ═══════════════════════════════════════════════════════════════════════════

; Coordenadas do botão "+" para criar nova linha
PLUS_X := 38
PLUS_Y := 137

; Modo de navegação após clicar no "+":
; "tab_tab"      → Send Tab, Tab (simples, pode falhar se grid tiver foco)
; "down_left"    → Send Down, Left (alternativa ao Tab)
; "click_x_cell" → Clica direto na célula x(m) da linha (mais preciso)
AFTER_PLUS_MODE := "click_x_cell"

; Constantes para modo "click_x_cell":
; Use Window Spy do AutoHotkey para medir essas distâncias:
; - X_CELL_X: posição X da célula x(m) dentro da linha
; - X_CELL_Y_FIRST: posição Y da célula x(m) da primeira linha (após "+")
; - ROW_HEIGHT: altura de cada linha do grid
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
; USO DO SCRIPT:
; ═══════════════════════════════════════════════════════════════════════════
;
; 1. Abra VPro/SecPro e navegue até a tabela de coordenadas
; 2. Clique UMA VEZ no botão "+" para criar a linha 1
; 3. Clique na célula x(m) da linha 1
; 4. Aperte F8 no teclado
; 5. Aguarde o script preencher todas as 130 coordenadas
;
; ═══════════════════════════════════════════════════════════════════════════
; MODO DE NAVEGAÇÃO:
; ═══════════════════════════════════════════════════════════════════════════
;
; Se o script não funcionar corretamente, mude AFTER_PLUS_MODE:
;
; • Use "tab_tab" se o grid responde bem a teclas Tab
; • Use "down_left" se preferir utilizar setas do teclado
; • Use "click_x_cell" para ser mais preciso (requer ajuste das constantes)
;
; Para ajustar as constantes do modo "click_x_cell":
; 1. Abra Window Spy (AutoHotkey Tools)
; 2. Mova o mouse sobre a célula x(m) da linha 1
;    → Anote o valor X (será X_CELL_X)
;    → Anote o valor Y (será X_CELL_Y_FIRST)
; 3. Mova o mouse sobre a célula x(m) da linha 2
;    → Calcule: ROW_HEIGHT = Y_linha2 - X_CELL_Y_FIRST
;
; ═══════════════════════════════════════════════════════════════════════════

F8:: {
    CoordMode("Mouse", "Window")

    for i, row in coords {
        SendText(row[1])     ; Digita X
        Send("{Tab}")      ; Move para Y
        SendText(row[2])     ; Digita Y

        if i < coords.Length {
            Click(PLUS_X, PLUS_Y)
            Sleep(80)

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
                ; Calcula posição Y da célula x(m) para a linha i+1
                ; Linhas de dados começam em X_CELL_Y_FIRST
                clickY := X_CELL_Y_FIRST + (i - 1) * ROW_HEIGHT
                Click(X_CELL_X, clickY)
                Sleep(50)
            }
        }
    }
}
