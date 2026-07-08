#!/usr/bin/env python3
"""
Gera scripts AutoHotkey v2 a partir de JSONs do LibreDWG.

Extrai LWPOLYLINE (maior número de pontos), expande bulges/arcos,
normaliza coordenadas e gera script AHK para digitar pontos no VPro/SecPro.

Uso:
    python scripts/generate_vpro_ahk_from_libredwg.py
    python scripts/generate_vpro_ahk_from_libredwg.py --input-dir section/json --output-dir section/ahk
    python scripts/generate_vpro_ahk_from_libredwg.py --segments-per-arc 30 --decimals 4
"""

import json
import math
from pathlib import Path
import argparse
import sys


def find_lwpolylines(obj):
    """Procura recursivamente por LWPOLYLINE no objeto JSON."""
    found = []
    if isinstance(obj, dict):
        if obj.get("entity") == "LWPOLYLINE":
            found.append(obj)
        for v in obj.values():
            found.extend(find_lwpolylines(v))
    elif isinstance(obj, list):
        for v in obj:
            found.extend(find_lwpolylines(v))
    return found


def arc_points_from_bulge(p1, p2, bulge, n):
    """
    Expande um arco (definido por bulge) em n segmentos retos.

    theta = 4 * atan(bulge)
    radius = chord / (2 * sin(theta/2))
    """
    x1, y1 = p1
    x2, y2 = p2

    if abs(bulge) < 1e-12:
        return [p2]

    chord = math.hypot(x2 - x1, y2 - y1)
    if chord < 1e-12:
        return []

    theta = 4.0 * math.atan(bulge)
    radius = chord / (2.0 * math.sin(abs(theta) / 2.0))

    mx = (x1 + x2) / 2.0
    my = (y1 + y2) / 2.0

    dx = (x2 - x1) / chord
    dy = (y2 - y1) / chord

    h = radius * math.cos(abs(theta) / 2.0)

    sign = 1.0 if bulge > 0 else -1.0
    cx = mx - sign * dy * h
    cy = my + sign * dx * h

    a1 = math.atan2(y1 - cy, x1 - cx)

    pts = []
    for i in range(1, n + 1):
        t = i / n
        a = a1 + theta * t
        pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))

    return pts


def expand_polyline(points, bulges, segments_per_arc):
    """
    Expande polilinha com bulges em lista de pontos.

    Começa com o primeiro ponto, depois para cada segmento:
    - Se bulge > 0: discretiza o arco em segments_per_arc partes
    - Se bulge = 0: apenas adiciona o ponto final
    """
    out = [tuple(points[0][:2])]

    for i in range(len(points) - 1):
        p1 = tuple(points[i][:2])
        p2 = tuple(points[i + 1][:2])
        b = bulges[i] if i < len(bulges) else 0.0

        if abs(b) > 1e-12:
            out.extend(arc_points_from_bulge(p1, p2, b, segments_per_arc))
        else:
            out.append(p2)

    return out


def dedup(points, tol=1e-9):
    """Remove pontos consecutivos duplicados (distância < tol)."""
    out = []
    for p in points:
        if not out:
            out.append(p)
        elif math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > tol:
            out.append(p)
    return out


def fmt_br(x, decimals):
    """Formata número com padrão brasileiro (vírgula decimal)."""
    return f"{x:.{decimals}f}".replace(".", ",")


def normalize(coords):
    """
    Normaliza coordenadas:
    - x0 = (xmin + xmax) / 2
    - y0 = ymin
    - resultado: (x - x0, y - y0)
    """
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]

    x0 = (min(xs) + max(xs)) / 2.0
    y0 = min(ys)

    return [(x - x0, y - y0) for x, y in coords]


def generate_ahk(coords, decimals):
    """Gera script AutoHotkey v2 com lista de coordenadas e 3 modos de navegação."""
    ahk_coords = ",\n    ".join(
        f'["{fmt_br(x, decimals)}", "{fmt_br(y, decimals)}"]'
        for x, y in coords
    )

    return f'''#Requires AutoHotkey v2.0
SetTitleMatchMode(2)
SetKeyDelay(30, 30)

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
VPRO_TITULO := "VPro"

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
    {ahk_coords}
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

F8:: {{
    CoordMode("Mouse", "Window")

    ; Encontra a janela do VPro/SecPro
    vpro_hwnd := WinExist("ahk_class " . VPRO_TITULO)
    if not vpro_hwnd {{
        MsgBox(48, "Erro", "VPro/SecPro não encontrado. Verifique o título.")
        return
    }}

    for i, row in coords {{
        x_value := row[1]
        y_value := row[2]

        if USAR_CONTROL_MODE and (X_CELL_CLASSNN != "") {{
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
            if (Y_CELL_CLASSNN != "") {{
                ControlFocus(Y_CELL_CLASSNN, "ahk_id " . vpro_hwnd)
                Sleep(20)
                ControlSetText(Y_CELL_CLASSNN, y_value, "ahk_id " . vpro_hwnd)
            }} else {{
                ; Fallback para Y (Tab)
                Send("{{Tab}}")
                SendText(y_value)
            }}
            Sleep(20)

            ; Cria nova linha clicando no "+"
            if i < coords.Length {{
                if (PLUS_BUTTON_CLASSNN != "") {{
                    ControlClick(PLUS_BUTTON_CLASSNN, "ahk_id " . vpro_hwnd)
                }} else {{
                    ; Fallback para botão "+" (Click)
                    Click(PLUS_X, PLUS_Y)
                }}
                Sleep(80)

                ; Aguarda a nova linha ser criada
                Sleep(50)
            }}
        }} else {{
            ; ───────────────────────────────────────────────────────────
            ; MODO FALLBACK (Send/Click) - Sem ClassNN
            ; ───────────────────────────────────────────────────────────

            SendText(x_value)     ; Digita X
            Send("{{Tab}}")       ; Move para Y
            SendText(y_value)     ; Digita Y

            if i < coords.Length {{
                Click(PLUS_X, PLUS_Y)
                Sleep(80)

                ; Navega conforme modo selecionado
                if AFTER_PLUS_MODE = "tab_tab" {{
                    Send("{{Tab}}")
                    Send("{{Tab}}")
                }}
                else if AFTER_PLUS_MODE = "down_left" {{
                    Send("{{Down}}")
                    Send("{{Left}}")
                }}
                else if AFTER_PLUS_MODE = "click_x_cell" {{
                    clickY := X_CELL_Y_FIRST + (i - 1) * ROW_HEIGHT
                    Click(X_CELL_X, clickY)
                    Sleep(50)
                }}
            }}
        }}
    }}

    MsgBox(64, "Sucesso", "Preenchimento de " . coords.Length . " coordenadas concluído!")
}}
'''


def process_file(json_path, output_dir, segments_per_arc, decimals):
    """Processa um único JSON e gera arquivo AHK correspondente."""
    try:
        data = json.loads(json_path.read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError as e:
        print(f"[ERR] JSON inválido em {json_path}: {e}")
        return

    polys = find_lwpolylines(data)
    if not polys:
        print(f"[WARN] Nenhuma LWPOLYLINE encontrada em {json_path}")
        return

    poly = max(polys, key=lambda p: len(p.get("points", [])))

    points = poly.get("points", [])
    bulges = poly.get("bulges", [0.0] * len(points))

    if len(points) < 2:
        print(f"[WARN] Polilinha com poucos pontos em {json_path}")
        return

    coords = expand_polyline(points, bulges, segments_per_arc)
    coords = dedup(coords)
    coords = normalize(coords)

    if len(coords) > 1:
        if math.hypot(coords[0][0] - coords[-1][0], coords[0][1] - coords[-1][1]) < 1e-6:
            coords.pop()

    ahk_text = generate_ahk(coords, decimals)

    output_dir.mkdir(parents=True, exist_ok=True)
    ahk_path = output_dir / f"{json_path.stem}.ahk"
    ahk_path.write_text(ahk_text, encoding="utf-8")

    print(f"[OK] {json_path.name} → {ahk_path.name} ({len(coords)} pontos)")


def main():
    parser = argparse.ArgumentParser(
        description="Gera scripts AutoHotkey v2 a partir de JSONs do LibreDWG"
    )
    parser.add_argument(
        "--input-dir",
        default="section/json",
        help="Diretório com JSONs (padrão: section/json)",
    )
    parser.add_argument(
        "--output-dir",
        default="section/ahk",
        help="Diretório para gerar AHK (padrão: section/ahk)",
    )
    parser.add_argument(
        "--segments-per-arc",
        type=int,
        default=20,
        help="Segmentos por arco (padrão: 20)",
    )
    parser.add_argument(
        "--decimals",
        type=int,
        default=3,
        help="Casas decimais (padrão: 3)",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        print(f"[ERR] Diretório {input_dir} não existe", file=sys.stderr)
        sys.exit(1)

    json_files = sorted(input_dir.glob("*.json"))

    if not json_files:
        print(f"[WARN] Nenhum JSON encontrado em {input_dir}")
        return

    print(f"Processando {len(json_files)} arquivo(s) de {input_dir}...")
    for json_path in json_files:
        process_file(
            json_path=json_path,
            output_dir=output_dir,
            segments_per_arc=args.segments_per_arc,
            decimals=args.decimals,
        )
    print(f"\nArquivos AHK gerados em: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
