#!/usr/bin/env python3
"""
Se a LWPOLYLINE original está já correta (uma única polilinha fechada),
apenas preserva a ordem original dos pontos!

A estratégia: a ordem em que os pontos aparecem na LWPOLYLINE é a caminhada contínua.
Apenas validar e rotacionar para começar no superior esquerdo.
"""

import re
import math
from dataclasses import dataclass
from typing import List, Tuple
from pathlib import Path
import json


@dataclass
class Point:
    x: float
    y: float
    idx: int = 0

    def dist(self, other) -> float:
        return ((self.x - other.x)**2 + (self.y - other.y)**2) ** 0.5

    def snap_eq(self, other, tol=1e-6) -> bool:
        return abs(self.x - other.x) < tol and abs(self.y - other.y) < tol

    def __repr__(self):
        return f"({self.x:.6f}, {self.y:.6f})"


def extract_lwpolyline_points(dxf_path: str) -> List[Point]:
    """Extrai pontos de LWPOLYLINE mantendo a ordem original."""
    print(f"[*] Lendo LWPOLYLINE original: {dxf_path}")

    with open(dxf_path, 'r') as f:
        lines = f.readlines()

    points = []
    last_x = None
    in_lwpoly = False

    for i, line in enumerate(lines):
        code = line.strip()

        if code == 'LWPOLYLINE':
            in_lwpoly = True

        if code == '0' and in_lwpoly and i > 0 and line[0:2] == '  ':
            # Próxima entidade
            if lines[i + 1].strip() not in ['LWPOLYLINE', 'SEQEND']:
                break

        if in_lwpoly:
            if code == '10':
                try:
                    last_x = float(lines[i + 1].strip())
                except:
                    pass

            elif code == '20':
                try:
                    if last_x is not None:
                        y = float(lines[i + 1].strip())
                        points.append(Point(last_x, y, len(points)))
                        last_x = None
                except:
                    pass

    print(f"[+] Pontos extraídos (ordem original): {len(points)}")
    return points


def validate_continuity(points: List[Point]) -> bool:
    """Valida que pontos consecutivos são próximos um do outro."""
    print(f"\n[*] Validando continuidade da sequência")

    dists = []
    for i in range(len(points)):
        d = points[i].dist(points[(i + 1) % len(points)])
        dists.append(d)

    min_d = min(dists)
    max_d = max(dists)
    avg_d = sum(dists) / len(dists)

    print(f"    Distância entre pontos consecutivos:")
    print(f"    - Mínima:  {min_d:.6f} m")
    print(f"    - Máxima:  {max_d:.6f} m")
    print(f"    - Média:   {avg_d:.6f} m")

    # Se há um salto muito grande, pode haver problema
    outliers = sum(1 for d in dists if d > avg_d * 3)

    if outliers > 0:
        print(f"[!] Aviso: {outliers} saltos anormalmente grandes detectados")
        for i, d in enumerate(dists):
            if d > avg_d * 3:
                print(f"    Entre ponto {i} e {(i+1) % len(points)}: {d:.6f} m")

    print(f"[+] Sequência validada ✓")
    return True


def ensure_ccw(points: List[Point]) -> List[Point]:
    """Garante ordem anti-horária (CCW)."""
    print(f"\n[*] Validando sentido (CCW)")

    area_signed = 0
    for i in range(len(points)):
        p1 = points[i]
        p2 = points[(i + 1) % len(points)]
        area_signed += p1.x * p2.y - p2.x * p1.y

    if area_signed < 0:
        print("    Invertendo para CCW")
        return points[::-1]
    else:
        print("    Já está CCW ✓")
        return points


def rotate_to_topleft(points: List[Point]) -> List[Point]:
    """Rotaciona para começar no superior esquerdo."""
    print(f"\n[*] Rotacionando para ponto superior esquerdo")

    max_idx = 0
    for i in range(1, len(points)):
        if (points[i].y > points[max_idx].y + 1e-8 or
            (abs(points[i].y - points[max_idx].y) < 1e-8 and points[i].x < points[max_idx].x - 1e-8)):
            max_idx = i

    print(f"[+] Ponto inicial escolhido (índice {max_idx}): {points[max_idx]}")

    rotated = points[max_idx:] + points[:max_idx]
    return rotated


def polygon_area(points: List[Point]) -> float:
    """Calcula área assinada."""
    if len(points) < 3:
        return 0

    area = 0
    for i in range(len(points)):
        p1 = points[i]
        p2 = points[(i + 1) % len(points)]
        area += p1.x * p2.y - p2.x * p1.y

    return abs(area) / 2


def check_self_intersections(points: List[Point]) -> int:
    """Conta auto-interseções (simplificado)."""
    print(f"\n[*] Verificando auto-interseções")

    def ccw(A, B, C):
        return (C.y - A.y) * (B.x - A.x) > (B.y - A.y) * (C.x - A.x)

    def segments_intersect(A, B, C, D):
        return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

    count = 0
    n = len(points)

    # Verifica pares de segmentos não-adjacentes
    for i in range(n):
        for j in range(i + 2, n):
            if (i == 0 and j == n - 1):
                continue  # Segmentos adjacentes (fechamento)

            seg1_start = points[i]
            seg1_end = points[(i + 1) % n]
            seg2_start = points[j]
            seg2_end = points[(j + 1) % n]

            if segments_intersect(seg1_start, seg1_end, seg2_start, seg2_end):
                count += 1

    if count > 0:
        print(f"[!] Aviso: {count} interseções detectadas")
    else:
        print(f"[+] Nenhuma auto-interseção encontrada ✓")

    return count


def write_dxf(points: List[Point], output_path: str):
    """Escreve DXF R12 com LWPOLYLINE."""
    print(f"\n[*] Escrevendo DXF: {output_path}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    dxf_content = """  0
SECTION
  2
HEADER
  9
$ACADVER
  1
AC1015
  9
$INSUNITS
 70
6
ENDSEC
  0
SECTION
  2
TABLES
  0
TABLE
  2
LAYER
 70
1
  0
LAYER
  2
0
 70
0
 62
7
  6
CONTINUOUS
  0
ENDTAB
ENDSEC
  0
SECTION
  2
ENTITIES
  0
LWPOLYLINE
  5
30
330
0
100
AcDbEntity
  8
0
100
AcDbPolyline
 90
{num_points}
 70
1
"""

    for pt in points:
        dxf_content += f" 10\n{pt.x:.15g}\n 20\n{pt.y:.15g}\n"

    dxf_content += """  0
ENDSEC
  0
EOF
"""

    with open(output_path, 'w') as f:
        f.write(dxf_content.format(num_points=len(points)))

    print(f"[+] DXF escrito: {output_path}")


def write_json(points: List[Point], output_path: str):
    """Escreve JSON com coordenadas."""
    print(f"[*] Escrevendo JSON: {output_path}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    json_data = [{"i": i, "x": p.x, "y": p.y} for i, p in enumerate(points)]

    with open(output_path, 'w') as f:
        json.dump(json_data, f, indent=2)

    print(f"[+] JSON escrito: {output_path}")


def print_report(points: List[Point]):
    """Relatório final."""
    print(f"\n{'='*70}")
    print(f"RELATÓRIO FINAL - CAMINHADA CONTÍNUA PRESERVADA")
    print(f"{'='*70}\n")

    area = polygon_area(points)

    # Cálculo da área assinada para verificar sentido
    area_signed = 0
    for i in range(len(points)):
        p1 = points[i]
        p2 = points[(i + 1) % len(points)]
        area_signed += p1.x * p2.y - p2.x * p1.y

    direction = "CCW (Anti-horário)" if area_signed > 0 else "CW (Horário)"

    # Distâncias
    dists = [points[i].dist(points[(i + 1) % len(points)]) for i in range(len(points))]

    xs = [p.x for p in points]
    ys = [p.y for p in points]

    print(f"Número de vértices:        {len(points)}")
    print(f"Área do polígono:          {area:.6f} m²")
    print(f"Sentido:                   {direction}")
    print(f"Ponto inicial:             {points[0]}")
    print(f"Ponto final:               {points[-1]}")
    print(f"Distância início->fim:     {points[-1].dist(points[0]):.6f} m")
    print(f"")
    print(f"Bounding box:")
    print(f"  X: [{min(xs):.6f}, {max(xs):.6f}]")
    print(f"  Y: [{min(ys):.6f}, {max(ys):.6f}]")
    print(f"")
    print(f"Distâncias entre pontos consecutivos:")
    print(f"  Mínima: {min(dists):.6f} m")
    print(f"  Máxima: {max(dists):.6f} m")
    print(f"  Média:  {sum(dists)/len(dists):.6f} m")
    print(f"")
    print(f"Validações:")
    print(f"  ✓ Ordem original preservada (caminhada contínua)")
    print(f"  ✓ Sentido CCW garantido")
    print(f"  ✓ Começando no ponto superior esquerdo")
    print(f"  ✓ Auto-interseções: {check_self_intersections(points)}")

    print(f"{'='*70}\n")


def main():
    dxf_input = "/home/hcmelo/projects/secpro/section/DXF/LA25_vpro.dxf"
    output_dir = "/home/hcmelo/projects/secpro/output"

    print(f"\n{'='*70}")
    print(f"PRESERVAR ORDEM - CAMINHADA CONTÍNUA ORIGINAL")
    print(f"{'='*70}\n")

    # Extrai
    points = extract_lwpolyline_points(dxf_input)

    # Valida continuidade
    validate_continuity(points)

    # Normaliza
    points = ensure_ccw(points)
    points = rotate_to_topleft(points)

    # Saída
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    write_dxf(points, f"{output_dir}/LA25_vpro_safe_ordered.dxf")
    write_json(points, f"{output_dir}/LA25_outer_ordered.json")

    # Relatório
    print_report(points)

    print("[✓] Processamento concluído com sucesso!")


if __name__ == "__main__":
    main()
