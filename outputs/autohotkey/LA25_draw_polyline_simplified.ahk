#Requires AutoHotkey v2.0
; ═══════════════════════════════════════════════════════════════════════════
; LA25_draw_polyline_simplified - digita a polilinha VPRO-safe no VPro/SecPro, ponto a ponto,
; NA ORDEM VALIDADA (caminhada continua; alveolos ligados por canal - NAO
; fechados como loops independentes). Gerado por scripts/export_autohotkey.py
; a partir de outputs/LA25_outer_ordered_simplified.json - nao editar os pontos a mao.
;
; USO:
;   1. Abra o VPro na tela "Seção poligonal" (grid de coordenadas visivel).
;   2. Modo controle (recomendado): descubra os ClassNN com
;      scripts/vpro_control_discovery.ahk e preencha as constantes abaixo.
;      Modo fallback: clique no "+" uma vez e depois na celula x(m) da
;      linha 1 antes de comecar.
;   3. F8 inicia. Esc ABORTA imediatamente a qualquer momento.
;   4. Progresso: ToolTip no canto da tela + log em LA25_draw_polyline_simplified.log
;      (mesma pasta deste script). Em caso de aborto, o log diz o ultimo
;      ponto concluido - ajuste INICIO_EM para retomar (modo controle).
;
; AVISO (modo fallback "click_x_cell"): a posicao da celula e estimada por
; X_CELL_Y_FIRST + i*ROW_HEIGHT e SO vale enquanto a linha alvo estiver
; visivel sem rolagem. Para 190 linhas, prefira o modo controle.
; ═══════════════════════════════════════════════════════════════════════════

SetTitleMatchMode(2)
SetKeyDelay(100, 100)

; ── Configuracao ─────────────────────────────────────────────────────────────
VPRO_TITULO := "Seção poligonal"
POINT_DELAY_MS := 150       ; pausa base entre acoes (conservador)
INICIO_EM := 1                    ; 1 = do comeco; >1 retoma apos aborto

; Modo controle (recomendado): preencha com vpro_control_discovery.ahk
USAR_CONTROL_MODE := false
X_CELL_CLASSNN := ""              ; ex.: "Edit1"
Y_CELL_CLASSNN := ""              ; ex.: "Edit2"
PLUS_BUTTON_CLASSNN := ""         ; ex.: "Button1"

; Modo fallback (Send/Click) - constantes herdadas de section/ahk/LA25.ahk
PLUS_X := 38
PLUS_Y := 137
AFTER_PLUS_MODE := "click_x_cell" ; "tab_tab" | "down_left" | "click_x_cell"
X_CELL_X := 135
X_CELL_Y_FIRST := 181
ROW_HEIGHT := 19

LOG_FILE := A_ScriptDir . "\LA25_draw_polyline_simplified.log"

coords := [
    ["-0,600", "0,250"],
    ["0,600", "0,250"],
    ["0,600", "0,200"],
    ["0,575", "0,195"],
    ["0,575", "0,060"],
    ["0,625", "0,050"],
    ["0,625", "0,012"],
    ["0,613", "0,000"],
    ["0,441", "0,000"],
    ["0,441", "0,040"],
    ["0,457", "0,042"],
    ["0,473", "0,047"],
    ["0,488", "0,054"],
    ["0,501", "0,065"],
    ["0,511", "0,078"],
    ["0,519", "0,093"],
    ["0,524", "0,109"],
    ["0,525", "0,125"],
    ["0,524", "0,142"],
    ["0,519", "0,158"],
    ["0,511", "0,173"],
    ["0,500", "0,186"],
    ["0,487", "0,196"],
    ["0,473", "0,204"],
    ["0,457", "0,209"],
    ["0,440", "0,210"],
    ["0,423", "0,209"],
    ["0,407", "0,204"],
    ["0,393", "0,196"],
    ["0,380", "0,186"],
    ["0,369", "0,173"],
    ["0,361", "0,158"],
    ["0,356", "0,142"],
    ["0,355", "0,125"],
    ["0,356", "0,109"],
    ["0,361", "0,093"],
    ["0,369", "0,078"],
    ["0,379", "0,065"],
    ["0,392", "0,054"],
    ["0,407", "0,047"],
    ["0,423", "0,042"],
    ["0,440", "0,040"],
    ["0,440", "0,000"],
    ["0,220", "0,000"],
    ["0,220", "0,040"],
    ["0,237", "0,042"],
    ["0,253", "0,047"],
    ["0,268", "0,054"],
    ["0,281", "0,065"],
    ["0,291", "0,078"],
    ["0,299", "0,093"],
    ["0,304", "0,109"],
    ["0,305", "0,125"],
    ["0,304", "0,142"],
    ["0,299", "0,158"],
    ["0,291", "0,173"],
    ["0,280", "0,186"],
    ["0,267", "0,196"],
    ["0,253", "0,204"],
    ["0,237", "0,209"],
    ["0,220", "0,210"],
    ["0,203", "0,209"],
    ["0,187", "0,204"],
    ["0,173", "0,196"],
    ["0,160", "0,186"],
    ["0,149", "0,173"],
    ["0,141", "0,158"],
    ["0,136", "0,142"],
    ["0,135", "0,125"],
    ["0,136", "0,109"],
    ["0,141", "0,093"],
    ["0,149", "0,078"],
    ["0,159", "0,065"],
    ["0,172", "0,054"],
    ["0,187", "0,047"],
    ["0,203", "0,042"],
    ["0,219", "0,040"],
    ["0,219", "0,000"],
    ["0,000", "0,000"],
    ["0,000", "0,040"],
    ["0,017", "0,042"],
    ["0,033", "0,046"],
    ["0,048", "0,054"],
    ["0,061", "0,065"],
    ["0,071", "0,078"],
    ["0,079", "0,093"],
    ["0,084", "0,109"],
    ["0,085", "0,125"],
    ["0,084", "0,142"],
    ["0,079", "0,158"],
    ["0,071", "0,173"],
    ["0,060", "0,186"],
    ["0,047", "0,196"],
    ["0,033", "0,204"],
    ["0,017", "0,209"],
    ["-0,000", "0,210"],
    ["-0,017", "0,209"],
    ["-0,033", "0,204"],
    ["-0,047", "0,196"],
    ["-0,060", "0,186"],
    ["-0,071", "0,173"],
    ["-0,079", "0,158"],
    ["-0,084", "0,142"],
    ["-0,085", "0,125"],
    ["-0,084", "0,109"],
    ["-0,079", "0,093"],
    ["-0,071", "0,078"],
    ["-0,061", "0,065"],
    ["-0,048", "0,054"],
    ["-0,033", "0,046"],
    ["-0,017", "0,042"],
    ["-0,001", "0,040"],
    ["-0,001", "0,000"],
    ["-0,220", "0,000"],
    ["-0,220", "0,040"],
    ["-0,203", "0,042"],
    ["-0,187", "0,046"],
    ["-0,173", "0,054"],
    ["-0,160", "0,065"],
    ["-0,149", "0,078"],
    ["-0,142", "0,093"],
    ["-0,137", "0,109"],
    ["-0,135", "0,125"],
    ["-0,137", "0,142"],
    ["-0,142", "0,158"],
    ["-0,150", "0,173"],
    ["-0,160", "0,185"],
    ["-0,173", "0,196"],
    ["-0,188", "0,204"],
    ["-0,204", "0,209"],
    ["-0,221", "0,210"],
    ["-0,237", "0,209"],
    ["-0,253", "0,204"],
    ["-0,268", "0,196"],
    ["-0,281", "0,185"],
    ["-0,291", "0,173"],
    ["-0,299", "0,158"],
    ["-0,304", "0,142"],
    ["-0,306", "0,125"],
    ["-0,304", "0,109"],
    ["-0,299", "0,093"],
    ["-0,292", "0,078"],
    ["-0,281", "0,065"],
    ["-0,268", "0,054"],
    ["-0,254", "0,046"],
    ["-0,238", "0,042"],
    ["-0,221", "0,040"],
    ["-0,221", "0,000"],
    ["-0,439", "0,000"],
    ["-0,439", "0,040"],
    ["-0,422", "0,041"],
    ["-0,406", "0,046"],
    ["-0,392", "0,054"],
    ["-0,379", "0,065"],
    ["-0,368", "0,078"],
    ["-0,361", "0,093"],
    ["-0,356", "0,109"],
    ["-0,354", "0,125"],
    ["-0,356", "0,142"],
    ["-0,361", "0,158"],
    ["-0,369", "0,173"],
    ["-0,379", "0,185"],
    ["-0,392", "0,196"],
    ["-0,407", "0,204"],
    ["-0,423", "0,209"],
    ["-0,440", "0,210"],
    ["-0,456", "0,209"],
    ["-0,472", "0,204"],
    ["-0,487", "0,196"],
    ["-0,500", "0,185"],
    ["-0,510", "0,173"],
    ["-0,518", "0,158"],
    ["-0,523", "0,142"],
    ["-0,525", "0,125"],
    ["-0,523", "0,109"],
    ["-0,518", "0,093"],
    ["-0,511", "0,078"],
    ["-0,500", "0,065"],
    ["-0,487", "0,054"],
    ["-0,473", "0,046"],
    ["-0,457", "0,041"],
    ["-0,440", "0,040"],
    ["-0,440", "0,000"],
    ["-0,613", "0,000"],
    ["-0,625", "0,012"],
    ["-0,625", "0,050"],
    ["-0,575", "0,060"],
    ["-0,575", "0,195"],
    ["-0,600", "0,200"],
    ["-0,600", "0,250"]
]

; ── Estado global ────────────────────────────────────────────────────────────
global g_abort := false

Log(msg) {
    global LOG_FILE
    FileAppend(FormatTime(A_Now, "yyyy-MM-dd HH:mm:ss") . "  " . msg . "`n", LOG_FILE)
}

AbortarExecucao(motivo, ultimo) {
    global g_abort
    g_abort := true
    ToolTip()
    Log("ABORTADO: " . motivo . " (ultimo ponto concluido: " . ultimo . ")")
    MsgBox(motivo . "`n`nUltimo ponto concluido: " . ultimo
        . "`nPara retomar no modo controle, ajuste INICIO_EM := " . (ultimo + 1)
        . " e pressione F8.", "Automacao interrompida", 48)
}

; Esc aborta a qualquer momento (inclusive durante Sleep)
Esc:: {
    global g_abort
    g_abort := true
    ToolTip()
    Log("ABORTADO: Esc pressionado pelo usuario")
    MsgBox("Automacao abortada pelo usuario (Esc).", "Abortado", 48)
    ExitApp()
}

; Garante que a janela do VPro existe e esta ativa; tenta reativar UMA vez.
; Retorna true se pode continuar; false = parar (sem cliques as cegas).
JanelaOk(vpro_hwnd) {
    if !WinExist("ahk_id " . vpro_hwnd)
        return false
    if WinActive("ahk_id " . vpro_hwnd)
        return true
    WinActivate("ahk_id " . vpro_hwnd)
    return WinWaitActive("ahk_id " . vpro_hwnd, , 2) != 0
}

F8:: {
    global g_abort
    g_abort := false
    CoordMode("Mouse", "Window")

    vpro_hwnd := WinExist(VPRO_TITULO)
    if !vpro_hwnd {
        MsgBox("Janela '" . VPRO_TITULO . "' nao encontrada."
            . "`nAbra o VPro na tela da secao poligonal e tente de novo.",
            "Erro", 48)
        return
    }

    WinActivate("ahk_id " . vpro_hwnd)
    if !WinWaitActive("ahk_id " . vpro_hwnd, , 2) {
        MsgBox("Nao consegui ativar a janela do VPro.", "Erro", 48)
        return
    }
    Sleep(1000)

    total := coords.Length
    Log("Inicio: " . total . " pontos, a partir do indice " . INICIO_EM
        . " (delay " . POINT_DELAY_MS . " ms)")

    for i, row in coords {
        if (i < INICIO_EM)
            continue
        if g_abort
            return

        ; nunca continuar sem a janela do VPro em foco
        if !JanelaOk(vpro_hwnd) {
            AbortarExecucao("Janela do VPro fechada ou sem foco (nao recuperado apos 1 tentativa).", i - 1)
            return
        }

        x_value := row[1]
        y_value := row[2]
        ToolTip("VPro polilinha: ponto " . i . " / " . total . "  (" . x_value . " ; " . y_value . ")  -  Esc aborta")

        if (USAR_CONTROL_MODE and X_CELL_CLASSNN != "") {
            ; ── modo controle (recomendado) ─────────────────────────────
            ControlFocus(X_CELL_CLASSNN, "ahk_id " . vpro_hwnd)
            Sleep(POINT_DELAY_MS // 3)
            ControlSetText(X_CELL_CLASSNN, x_value, "ahk_id " . vpro_hwnd)
            Sleep(POINT_DELAY_MS // 3)
            if (Y_CELL_CLASSNN != "") {
                ControlFocus(Y_CELL_CLASSNN, "ahk_id " . vpro_hwnd)
                Sleep(POINT_DELAY_MS // 3)
                ControlSetText(Y_CELL_CLASSNN, y_value, "ahk_id " . vpro_hwnd)
            } else {
                Send("{Tab}")
                SendText(y_value)
            }
            Sleep(POINT_DELAY_MS)
            if (i < total) {
                if (PLUS_BUTTON_CLASSNN != "")
                    ControlClick(PLUS_BUTTON_CLASSNN, "ahk_id " . vpro_hwnd)
                else
                    Click(PLUS_X, PLUS_Y)
                Sleep(POINT_DELAY_MS * 2)
            }
        } else {
            ; ── modo fallback (Send/Click) ──────────────────────────────
            SendText(x_value)
            Sleep(POINT_DELAY_MS)
            Send("{Tab}")
            Sleep(POINT_DELAY_MS)
            SendText(y_value)
            Sleep(POINT_DELAY_MS)
            if (i < total) {
                Click(PLUS_X, PLUS_Y)
                Sleep(POINT_DELAY_MS * 2)
                if !JanelaOk(vpro_hwnd) {
                    AbortarExecucao("Janela perdeu o foco apos clicar no '+'.", i)
                    return
                }
                if (AFTER_PLUS_MODE = "tab_tab") {
                    Send("{Tab}")
                    Send("{Tab}")
                } else if (AFTER_PLUS_MODE = "down_left") {
                    Send("{Down}")
                    Send("{Left}")
                } else if (AFTER_PLUS_MODE = "click_x_cell") {
                    clickY := X_CELL_Y_FIRST + i * ROW_HEIGHT
                    Click(X_CELL_X, clickY)
                    Sleep(POINT_DELAY_MS * 2)
                }
            }
        }

        if (Mod(i, 25) = 0)
            Log("progresso: " . i . " / " . total)
    }

    ToolTip()
    Log("Concluido: " . total . " pontos digitados.")
    MsgBox("Preenchimento de " . total . " coordenadas concluido!", "Sucesso", 64)
}
