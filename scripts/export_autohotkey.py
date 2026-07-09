#!/usr/bin/env python3
"""Converte o JSON ordenado VPRO-safe em script AutoHotkey v2 para o VPro.

Fonte: outputs/<secao>_outer_ordered.json (gerado por scripts/geometry_vpro_safe.py,
ja validado: caminhada continua, sem cordas, canal dos alveolos preservado).
Este gerador NAO reordena nada e NAO fecha alveolos - digita a sequencia
exatamente como validada.

O AHK gerado segue as convencoes ja testadas em section/ahk/LA25.ahk
(AutoHotkey v2, virgula decimal pt-BR, janela "Seção poligonal", modo
ControlSetText/ControlClick com fallback Send/Click), acrescentando:

  - F8 inicia; Esc ABORTA a qualquer momento (hotkey global);
  - antes de cada ponto verifica se a janela do VPro existe e esta ativa;
    tenta reativar UMA vez e, se continuar sem foco, PARA com mensagem
    clara (nunca fica clicando as cegas);
  - progresso em ToolTip + log em arquivo ao lado do .ahk;
  - pausa entre pontos configuravel (POINT_DELAY_MS);
  - linha final opcional repetindo o primeiro ponto para fechar a
    poligonal (convencao do LA25.ahk).

Precisao do grid: com --decimals 3 (padrao, como no VPro) vertices a menos
de 1 mm um do outro podem colidir apos o arredondamento; linhas consecutivas
que ficarem IDENTICAS na precisao escolhida sao removidas (registrado no
terminal) para nao digitar segmentos de comprimento zero no VPro.

Uso:
  .venv/bin/python scripts/export_autohotkey.py
  .venv/bin/python scripts/export_autohotkey.py --decimals 4 --point-delay-ms 200
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", default="outputs/LA25_outer_ordered.json")
    parser.add_argument("--output", default="outputs/autohotkey/LA25_draw_polyline.ahk")
    parser.add_argument("--decimals", type=int, default=3, help="casas decimais (padrao 3)")
    parser.add_argument(
        "--point-delay-ms", type=int, default=150,
        help="pausa base entre acoes de digitacao, em ms (padrao 150 - conservador)",
    )
    parser.add_argument("--window-title", default="Seção poligonal")
    parser.add_argument(
        "--no-closing-point", action="store_true",
        help="nao repete o primeiro ponto no final (padrao: repete, fechando a poligonal)",
    )
    parser.add_argument("--force", action="store_true", help="sobrescreve o .ahk existente")
    return parser.parse_args(argv)


def fmt_br(value: float, decimals: int) -> str:
    """Formato pt-BR com virgula decimal (convencao do grid do VPro)."""
    return f"{value:.{decimals}f}".replace(".", ",")


def load_ordered_points(json_path: Path) -> list[tuple[float, float]]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    rows = sorted(data, key=lambda r: int(r["i"]))
    return [(float(r["x"]), float(r["y"])) for r in rows]


def to_grid_rows(
    points: list[tuple[float, float]], decimals: int, closing_point: bool
) -> tuple[list[tuple[str, str]], int]:
    """Formata na precisao do grid e remove linhas consecutivas identicas.

    Retorna (linhas, n_duplicatas_removidas). A remocao so acontece entre
    linhas CONSECUTIVAS que colidiram no arredondamento - a caminhada
    continua intacta (os vizinhos da linha removida ja eram adjacentes na
    borda real, a menos da resolucao do grid).
    """
    rows: list[tuple[str, str]] = []
    dropped = 0
    for x, y in points:
        row = (fmt_br(x, decimals), fmt_br(y, decimals))
        if rows and row == rows[-1]:
            dropped += 1
            continue
        rows.append(row)
    if closing_point and rows and rows[-1] != rows[0]:
        rows.append(rows[0])
    return rows, dropped


AHK_TEMPLATE = r'''#Requires AutoHotkey v2.0
; ═══════════════════════════════════════════════════════════════════════════
; __NAME__ - digita a polilinha VPRO-safe no VPro/SecPro, ponto a ponto,
; NA ORDEM VALIDADA (caminhada continua; alveolos ligados por canal - NAO
; fechados como loops independentes). Gerado por scripts/export_autohotkey.py
; a partir de __SOURCE__ - nao editar os pontos a mao.
;
; USO:
;   1. Abra o VPro na tela "__TITLE__" (grid de coordenadas visivel).
;   2. Modo controle (recomendado): descubra os ClassNN com
;      scripts/vpro_control_discovery.ahk e preencha as constantes abaixo.
;      Modo fallback: clique no "+" uma vez e depois na celula x(m) da
;      linha 1 antes de comecar.
;   3. F8 inicia. Esc ABORTA imediatamente a qualquer momento.
;   4. Progresso: ToolTip no canto da tela + log em __LOGNAME__
;      (mesma pasta deste script). Em caso de aborto, o log diz o ultimo
;      ponto concluido - ajuste INICIO_EM para retomar (modo controle).
;
; AVISO (modo fallback "click_x_cell"): a posicao da celula e estimada por
; X_CELL_Y_FIRST + i*ROW_HEIGHT e SO vale enquanto a linha alvo estiver
; visivel sem rolagem. Para __TOTAL__ linhas, prefira o modo controle.
; ═══════════════════════════════════════════════════════════════════════════

SetTitleMatchMode(2)
SetKeyDelay(100, 100)

; ── Configuracao ─────────────────────────────────────────────────────────────
VPRO_TITULO := "__TITLE__"
POINT_DELAY_MS := __DELAY__       ; pausa base entre acoes (conservador)
INICIO_EM := 1                    ; 1 = do comeco; >1 retoma apos aborto

; Modo controle (recomendado): preencha com vpro_control_discovery.ahk
USAR_CONTROL_MODE := false
X_CELL_CLASSNN := ""              ; ex.: "Edit1"
Y_CELL_CLASSNN := ""              ; ex.: "Edit2"
PLUS_BUTTON_CLASSNN := ""         ; ex.: "Button1"

; Modo precreate (recomendado para grids longos; evita perder ponto)
PRECREATE_ROWS := true
ROW_CREATE_DELAY_MS := 700  ; delay entre cliques do "+" durante phase 1
TYPE_DELAY_MS := 300        ; delay ao digitar x/y
AFTER_Y_DELAY_MS := 500     ; delay apos y antes de Tab para proxima linha

; Modo fallback legado (Send/Click) - constantes herdadas de section/ahk/LA25.ahk
; Nao recomendado para grids > ~50 linhas.
PLUS_X := 38
PLUS_Y := 137
AFTER_PLUS_MODE := "click_x_cell" ; "tab_tab" | "down_left" | "click_x_cell"
X_CELL_X := 135
X_CELL_Y_FIRST := 181
ROW_HEIGHT := 19

LOG_FILE := A_ScriptDir . "\__LOGNAME__"

coords := [
    __COORDS__
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

; Ctrl+Alt+Q tambem encerra (tecla rapida alternativa)
^!q:: ExitApp()

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
    Log("Inicio: " . total . " pontos, a partir do indice " . INICIO_EM)

    ; ── Estrategia PRECREATE + FILL (recomendado para grid longo) ─────────────
    if (PRECREATE_ROWS and !USAR_CONTROL_MODE) {
        Log("FASE 1: criando " . (total - 1) . " linhas vazias...")
        for i := 2 to total {
            if g_abort
                return
            if !JanelaOk(vpro_hwnd) {
                AbortarExecucao("Janela perdeu foco durante criacao de linhas.", i - 1)
                return
            }
            ToolTip("Criando linha " . i . " de " . total)
            Click(PLUS_X, PLUS_Y)
            Sleep(ROW_CREATE_DELAY_MS)
        }
        Log("FASE 1 concluida. Preenchendo valores...")

        ; Clicar na celula x(m) da linha 1 para comecar o preenchimento
        Click(X_CELL_X, X_CELL_Y_FIRST)
        Sleep(300)

        Log("FASE 2: preenchendo pontos...")
        for i, row in coords {
            if (i < INICIO_EM)
                continue
            if g_abort
                return

            if !JanelaOk(vpro_hwnd) {
                AbortarExecucao("Janela perdeu foco durante preenchimento.", i - 1)
                return
            }

            x_value := row[1]
            y_value := row[2]
            ToolTip("Preenchendo ponto " . i . " de " . total . ": " . x_value . " , " . y_value)

            ; Digita x, Tab, y, Tab (Tab move para x da proxima linha)
            SendText(x_value)
            Sleep(TYPE_DELAY_MS)
            Send("{Tab}")
            Sleep(TYPE_DELAY_MS)
            SendText(y_value)
            Sleep(AFTER_Y_DELAY_MS)
            Send("{Tab}")
            Sleep(TYPE_DELAY_MS)

            if (Mod(i, 25) = 0)
                Log("progresso: " . i . " / " . total)
        }

        ToolTip()
        Log("FASE 2 concluida: " . total . " pontos preenchidos.")
        MsgBox("Preenchimento de " . total . " coordenadas concluido com sucesso!", "Sucesso", 64)
        return
    }

    ; ── Estrategia legada (ponto a ponto com criacao de linha) ────────────────
    Log("Usando modo legado (ponto a ponto)...")
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
        ToolTip("Ponto " . i . " de " . total . ": " . x_value . " , " . y_value . " - Esc cancela")

        if (USAR_CONTROL_MODE and X_CELL_CLASSNN != "") {
            ; ── modo controle ─────────────────────────────
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
            ; ── modo fallback legado ──────────────────────────────
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
'''


def build_ahk(
    rows: list[tuple[str, str]],
    title: str,
    delay_ms: int,
    source: str,
    name: str,
) -> str:
    coords = ",\n    ".join(f'["{x}", "{y}"]' for x, y in rows)
    return (
        AHK_TEMPLATE
        .replace("__COORDS__", coords)
        .replace("__TITLE__", title)
        .replace("__DELAY__", str(delay_ms))
        .replace("__TOTAL__", str(len(rows)))
        .replace("__SOURCE__", source)
        .replace("__NAME__", name)
        .replace("__LOGNAME__", f"{name}.log")
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_json = Path(args.input_json)
    output = Path(args.output)

    if output.exists() and not args.force:
        print(f"[ERRO] {output} ja existe - use --force para sobrescrever.")
        return 1
    if not input_json.exists():
        print(f"[ERRO] {input_json} nao existe - rode scripts/geometry_vpro_safe.py antes.")
        return 1

    points = load_ordered_points(input_json)
    rows, dropped = to_grid_rows(points, args.decimals, closing_point=not args.no_closing_point)

    ahk_text = build_ahk(
        rows,
        title=args.window_title,
        delay_ms=args.point_delay_ms,
        source=str(input_json),
        name=output.stem,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(ahk_text, encoding="utf-8")

    est_s = len(rows) * (args.point_delay_ms * 5) / 1000.0
    print(f"[OK] {output} gerado")
    print(f"  pontos de entrada:          {len(points)} (ordem validada de {input_json})")
    print(f"  linhas no grid:             {len(rows)} "
          f"({'com' if not args.no_closing_point else 'sem'} linha de fechamento)")
    print(f"  duplicatas por arredondamento removidas: {dropped} "
          f"(precisao {args.decimals} casas = {10**-args.decimals:g} m)")
    print(f"  pausa base entre acoes:     {args.point_delay_ms} ms "
          f"(duracao estimada ~{est_s/60.0:.0f} min)")
    print(f"  janela alvo:                '{args.window_title}'")
    print("  hotkeys:                    F8 inicia | Esc aborta")
    print("  ordem NAO e corrigida pelo AHK - usa exatamente a sequencia VPRO-safe.")
    if dropped:
        print(f"  [AVISO] {dropped} vertices colidiram na precisao do grid; "
              f"use --decimals 4 se quiser preservar todos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
