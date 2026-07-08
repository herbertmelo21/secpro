#!/usr/bin/env python3
"""
Reordena polilinha DXF mantendo estrutura original como template.
"""

import re
import math
from pathlib import Path
from typing import List


class Point2D:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def dist_to(self, other):
        return ((self.x - other.x)**2 + (self.y - other.y)**2) ** 0.5

    def __repr__(self):
        return f"({self.x:.6f}, {self.y:.6f})"


def parse_dxf_points(dxf_path: str) -> List[Point2D]:
    """Extrai pontos da LWPOLYLINE."""
    print(f"[*] Lendo DXF: {dxf_path}")

    with open(dxf_path, 'r') as f:
        content = f.read()

    entities_match = re.search(r'ENTITIES\s*\n\s*0\n', content)
    endsec_match = re.search(r'ENDSEC', content[entities_match.start():])
    entities_section = content[entities_match.start():entities_match.start() + endsec_match.start()]

    lwpoly_matches = list(re.finditer(r'LWPOLYLINE\s*\n\s*5', entities_section))
    points = []

    for match in lwpoly_matches:
        start = match.start()
        next_entity = re.search(r'\n\s*0\n\s*[A-Z]+\s*\n', entities_section[start + 10:])
        poly_section = entities_section[start:start + next_entity.start() + 10] if next_entity else entities_section[start:]

        x_codes = [(m.start(), float(m.group(1)))
                   for m in re.finditer(r'10\s*\n\s*([-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)\s*\n', poly_section)]
        y_codes = [(m.start(), float(m.group(1)))
                   for m in re.finditer(r'20\s*\n\s*([-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)\s*\n', poly_section)]

        x_codes.sort(key=lambda x: x[0])
        y_codes.sort(key=lambda x: x[0])

        for i in range(min(len(x_codes), len(y_codes))):
            points.append(Point2D(x_codes[i][1], y_codes[i][1]))

    print(f"[+] Pontos extraídos: {len(points)}")
    return points


def sort_polar(points: List[Point2D]) -> List[Point2D]:
    """Ordena por ângulo polar."""
    cx = sum(p.x for p in points) / len(points)
    cy = sum(p.y for p in points) / len(points)

    def angle_key(p):
        return math.atan2(p.y - cy, p.x - cx)

    return sorted(points, key=angle_key)


def ensure_ccw(points: List[Point2D]) -> List[Point2D]:
    """Garante CCW."""
    area = 0
    for i in range(len(points)):
        p1 = points[i]
        p2 = points[(i+1) % len(points)]
        area += p1.x * p2.y - p2.x * p1.y
    if area < 0:
        return points[::-1]
    return points


def rotate_to_topleft(points: List[Point2D]) -> List[Point2D]:
    """Começa no superior esquerdo."""
    max_idx = 0
    for i, p in enumerate(points):
        if p.y > points[max_idx].y or (abs(p.y - points[max_idx].y) < 1e-8 and p.x < points[max_idx].x):
            max_idx = i
    return points[max_idx:] + points[:max_idx]


def process(input_path: str, output_path: str):
    """Pipeline completo."""
    print(f"\n{'='*60}")
    print(f"VPRO-SAFE POLILINHA")
    print(f"{'='*60}\n")

    # Lê e processa
    points = parse_dxf_points(input_path)
    print(f"\n[*] Processando {len(points)} pontos")
    points = sort_polar(points)
    points = ensure_ccw(points)
    points = rotate_to_topleft(points)

    # Remove duplicatas consecutivas
    cleaned = [points[0]]
    for i in range(1, len(points)):
        if points[i].dist_to(cleaned[-1]) > 1e-6:
            cleaned.append(points[i])

    print(f"[+] Após limpeza: {len(cleaned)} pontos")

    # Calcula área
    area = 0
    for i in range(len(cleaned)):
        p1 = cleaned[i]
        p2 = cleaned[(i+1) % len(cleaned)]
        area += p1.x * p2.y - p2.x * p1.y
    area = abs(area) / 2

    # Carrega arquivo original e substitui a polilinha
    print(f"\n[*] Carregando template do arquivo original")
    with open(input_path, 'r') as f:
        original_content = f.read()

    # Encontra a LWPOLYLINE original
    entities_match = re.search(r'ENTITIES\s*\n\s*0\n', original_content)
    endsec_match = re.search(r'ENDSEC', original_content[entities_match.start():])
    entities_start = entities_match.start() + entities_match.end()
    entities_end = entities_match.start() + endsec_match.start()

    # Extrai header e tables do arquivo original
    header_start = 0
    header_end = original_content.find('\nENDSEC\n') + len('\nENDSEC\n')

    # Encontra início de TABLES
    tables_match = re.search(r'SECTION\s*\n\s*2\s*\nTABLES', original_content)
    tables_start = tables_match.start()
    tables_end = original_content.find('\nENDSEC', tables_start) + len('\nENDSEC')

    # Reconstrói o arquivo com header, tables e nova polilinha
    new_dxf = original_content[header_start:tables_end]
    new_dxf += "\n  0\nSECTION\n  2\nENTITIES\n  0\nLWPOLYLINE\n  5\n30\n330\n0\n100\nAcDbEntity\n  8\n0\n100\nAcDbPolyline\n 90\n"
    new_dxf += str(len(cleaned)) + "\n 70\n1\n"

    for pt in cleaned:
        new_dxf += f" 10\n{pt.x:.15g}\n 20\n{pt.y:.15g}\n"

    new_dxf += "  0\nENDSEC\n  0\nEOF\n"

    # Salva
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(new_dxf)

    print(f"[+] DXF escrito: {output_path}")

    # Relatório
    print(f"\n{'='*60}")
    print(f"RESULTADO")
    print(f"{'='*60}")
    print(f"Pontos originais:       {len(points)}")
    print(f"Pontos finais:          {len(cleaned)}")
    print(f"Duplicatas removidas:   {len(points) - len(cleaned)}")
    print(f"Área:                   {area:.6f}")
    print(f"Ponto inicial:          {cleaned[0]}")
    print(f"{'='*60}\n")

    return cleaned


if __name__ == "__main__":
    input_dxf = "/home/hcmelo/projects/secpro/section/DXF/LA25_vpro.dxf"
    output_dxf = "/home/hcmelo/projects/secpro/section/DXF/LA25_vpro_safe.dxf"

    process(input_dxf, output_dxf)
