#!/usr/bin/env python3
"""
Reconstrói ordem topológica de pontos em DXF para criar polilinha VPro-safe.
Sem dependências externas - parse manual de DXF, geometria com Python puro.
"""

import re
import math
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Dict, Set
from collections import defaultdict


@dataclass
class Point2D:
    x: float
    y: float

    def dist_to(self, other):
        dx = self.x - other.x
        dy = self.y - other.y
        return (dx*dx + dy*dy) ** 0.5

    def angle_from_centroid(self, centroid):
        """Ângulo em relação ao centróide (em radianos)."""
        dx = self.x - centroid.x
        dy = self.y - centroid.y
        return math.atan2(dy, dx)

    def __eq__(self, other, tol=1e-6):
        return abs(self.x - other.x) < tol and abs(self.y - other.y) < tol

    def __hash__(self):
        return hash((round(self.x, 8), round(self.y, 8)))

    def __repr__(self):
        return f"({self.x:.6f}, {self.y:.6f})"


def parse_dxf_entities(dxf_path: str) -> List[Point2D]:
    """Extrai pontos do DXF parseando manualmente o formato ASCII."""
    print(f"[*] Lendo DXF: {dxf_path}")

    with open(dxf_path, 'r') as f:
        content = f.read()

    # Encontra a seção ENTITIES
    entities_match = re.search(r'ENTITIES\s*\n\s*0\n', content)
    endsec_match = re.search(r'ENDSEC', content[entities_match.start():])

    if not entities_match or not endsec_match:
        raise ValueError("Não conseguiu encontrar seção ENTITIES no DXF")

    entities_section = content[entities_match.start():entities_match.start() + endsec_match.start()]

    # Procura por LWPOLYLINE (mais comum em DXF moderno)
    lwpoly_matches = list(re.finditer(r'LWPOLYLINE\s*\n\s*5', entities_section))
    print(f"    Encontradas {len(lwpoly_matches)} LWPOLYLINE(s)")

    points = []

    for match in lwpoly_matches:
        # Extrai do inicio deste LWPOLYLINE até o próximo entity type
        start = match.start()
        next_entity = re.search(r'\n\s*0\n\s*[A-Z]+\s*\n', entities_section[start + 10:])

        if next_entity:
            poly_section = entities_section[start:start + next_entity.start() + 10]
        else:
            poly_section = entities_section[start:]

        # Encontra todos os códigos 10 (X coordinate) e 20 (Y coordinate)
        x_codes = [(m.start(), float(m.group(1)))
                   for m in re.finditer(r'10\s*\n\s*([-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)\s*\n', poly_section)]
        y_codes = [(m.start(), float(m.group(1)))
                   for m in re.finditer(r'20\s*\n\s*([-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)\s*\n', poly_section)]

        # Ordena pelos offsets para manter sincronismo X/Y
        x_codes.sort(key=lambda x: x[0])
        y_codes.sort(key=lambda x: x[0])

        # Agrupa X e Y em pares
        for i in range(min(len(x_codes), len(y_codes))):
            x = x_codes[i][1]
            y = y_codes[i][1]
            points.append(Point2D(x, y))

    print(f"[+] Pontos extraídos: {len(points)}")
    return points


def merge_coincident_points(points: List[Point2D], tolerance: float = 1e-6) -> List[Point2D]:
    """Agrupa pontos coincidentes."""
    print(f"\n[*] Unindo pontos coincidentes (tolerância={tolerance})")

    merged = []
    used = set()

    for i, p1 in enumerate(points):
        if i in used:
            continue

        cluster = [p1]
        for j in range(i + 1, len(points)):
            if j in used:
                continue
            if p1.dist_to(points[j]) < tolerance:
                cluster.append(points[j])
                used.add(j)

        # Média dos pontos
        avg_x = sum(p.x for p in cluster) / len(cluster)
        avg_y = sum(p.y for p in cluster) / len(cluster)
        merged.append(Point2D(avg_x, avg_y))

    print(f"[+] Após merge: {len(merged)} pontos")
    return merged


def build_adjacency_graph(points: List[Point2D], max_edge_ratio: float = 3.0) -> Dict[Point2D, Set[Point2D]]:
    """Constrói grafo de adjacência por proximidade."""
    print(f"\n[*] Construindo grafo de adjacência")

    graph = {p: set() for p in points}

    # Calcula distâncias médias
    distances = []
    for i in range(len(points) - 1):
        d = points[i].dist_to(points[i+1])
        if d > 0:
            distances.append(d)

    if distances:
        avg_dist = sum(distances) / len(distances)
        max_edge = avg_dist * max_edge_ratio
        print(f"    Distância média: {avg_dist:.6f}, max_edge: {max_edge:.6f}")
    else:
        print(f"    Aviso: não conseguiu calcular distância média")
        return graph

    # Conecta cada ponto aos seus vizinhos mais próximos
    for i, p1 in enumerate(points):
        # Calcula distância para todos os outros pontos
        neighbors = [(j, p1.dist_to(points[j])) for j in range(len(points)) if i != j]
        neighbors.sort(key=lambda x: x[1])

        # Conecta aos 3 vizinhos mais próximos que estejam dentro de max_edge
        for j, dist in neighbors[:4]:
            if dist > 1e-6 and dist < max_edge:
                graph[p1].add(points[j])
                graph[points[j]].add(p1)

    degrees = [len(neighbors) for neighbors in graph.values()]
    print(f"    Graus: min={min(degrees) if degrees else 0}, "
          f"max={max(degrees) if degrees else 0}, "
          f"média={sum(degrees)/len(degrees) if degrees else 0:.1f}")

    return graph


def find_loops(graph: Dict[Point2D, Set[Point2D]], points: List[Point2D]) -> List[List[Point2D]]:
    """Detecta loops fechados no grafo."""
    print(f"\n[*] Detectando loops fechados")

    loops = []
    visited_edges = set()

    def trace_loop(start, current, origin, path, max_steps):
        if len(path) > max_steps:
            return None

        path = path + [current]

        if len(path) > 3 and current == origin:
            return path[:-1]

        for neighbor in graph.get(current, set()):
            if len(path) > 2 and neighbor == path[-2]:
                continue

            if neighbor in path[:-1]:
                if neighbor == origin and len(path) > 3:
                    return path
                continue

            result = trace_loop(start, neighbor, origin, path, max_steps)
            if result:
                return result

        return None

    for start_point in points:
        if len(graph.get(start_point, set())) < 2:
            continue

        for first_neighbor in graph[start_point]:
            edge_key = tuple(sorted([id(start_point), id(first_neighbor)]))
            if edge_key in visited_edges:
                continue

            loop = trace_loop(start_point, first_neighbor, start_point, [start_point], len(points) + 10)
            if loop and len(loop) >= 3:
                loop_key = tuple(sorted([(p.x, p.y) for p in loop]))
                is_dup = any(tuple(sorted([(p.x, p.y) for p in existing])) == loop_key for existing in loops)

                if not is_dup:
                    loops.append(loop)
                    for i in range(len(loop)):
                        p1 = loop[i]
                        p2 = loop[(i+1) % len(loop)]
                        ek = tuple(sorted([id(p1), id(p2)]))
                        visited_edges.add(ek)

    print(f"[+] Loops encontrados: {len(loops)}")

    for i, loop in enumerate(loops):
        area = polygon_area(loop)
        print(f"    Loop {i}: {len(loop)} pontos, área={area:.6f}")

    return loops


def polygon_area(points: List[Point2D]) -> float:
    """Calcula área assinada usando Shoelace formula."""
    if len(points) < 3:
        return 0

    area = 0
    for i in range(len(points)):
        p1 = points[i]
        p2 = points[(i+1) % len(points)]
        area += p1.x * p2.y - p2.x * p1.y

    return abs(area) / 2


def select_outer_loop(loops: List[List[Point2D]]) -> List[Point2D]:
    """Seleciona o loop com maior área."""
    print(f"\n[*] Selecionando contorno externo")

    if not loops:
        raise ValueError("Nenhum loop encontrado!")

    areas = [polygon_area(loop) for loop in loops]
    max_idx = areas.index(max(areas))

    print(f"[+] Contorno selecionado: Loop {max_idx} com {len(loops[max_idx])} pontos")
    return loops[max_idx]


def ensure_ccw_order(loop: List[Point2D]) -> List[Point2D]:
    """Garante ordem anti-horária (CCW)."""
    print(f"\n[*] Validando ordem (CCW)")

    area_signed = 0
    for i in range(len(loop)):
        p1 = loop[i]
        p2 = loop[(i+1) % len(loop)]
        area_signed += p1.x * p2.y - p2.x * p1.y

    if area_signed < 0:
        print("    Invertendo para CCW")
        return loop[::-1]
    else:
        print("    Já está em CCW ✓")
        return loop


def rotate_to_topleft(loop: List[Point2D]) -> List[Point2D]:
    """Rotaciona para começar no ponto superior esquerdo."""
    print(f"\n[*] Rotacionando para superior esquerdo")

    max_idx = 0
    max_y = loop[0].y
    min_x = loop[0].x

    for i, p in enumerate(loop):
        if p.y > max_y or (abs(p.y - max_y) < 1e-8 and p.x < min_x):
            max_idx = i
            max_y = p.y
            min_x = p.x

    print(f"[+] Ponto inicial: {loop[max_idx]}")
    return loop[max_idx:] + loop[:max_idx]


def remove_consecutive_duplicates(loop: List[Point2D], tolerance: float = 1e-6) -> List[Point2D]:
    """Remove duplicatas consecutivas."""
    print(f"\n[*] Removendo duplicatas consecutivas")

    cleaned = []
    for i, p in enumerate(loop):
        if i == 0 or p.dist_to(loop[i-1]) > tolerance:
            cleaned.append(p)

    removed = len(loop) - len(cleaned)
    if removed > 0:
        print(f"[+] Removidos {removed} duplicatas")

    return cleaned


def validate_loop(loop: List[Point2D]) -> bool:
    """Valida o loop."""
    print(f"\n[*] Validando loop")

    checks = {
        "Mínimo 3 pontos": len(loop) >= 3,
        "Nenhuma duplicata consecutiva": all(
            loop[i].dist_to(loop[i+1]) > 1e-6 for i in range(len(loop)-1)
        ),
        "Área > 0": polygon_area(loop) > 0,
        "Primeiro e último próximos": loop[0].dist_to(loop[-1]) < 1e-4,
    }

    for check, result in checks.items():
        status = "✓" if result else "✗"
        print(f"    {status} {check}")

    return all(checks.values())


def write_dxf_r12(points: List[Point2D], output_path: str):
    """Escreve um DXF R12 limpo com uma LWPOLYLINE fechada."""
    print(f"\n[*] Escrevendo DXF R12")

    dxf_content = """  0
SECTION
  2
HEADER
  9
$ACADVER
  1
AC1015
  9
$INSBASE
 10
0.0
 20
0.0
 30
0.0
  9
$INSUNITS
 70
6
  9
$EXTMIN
 10
-1.0
 20
-1.0
 30
0.0
  9
$EXTMAX
 10
10.0
 20
10.0
 30
0.0
  9
$LIMMIN
 10
0.0
 20
0.0
  9
$LIMMAX
 10
420.0
 20
297.0
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
  0
TABLE
  2
STYLE
 70
1
  0
STYLE
  2
Standard
 70
0
 40
0.0
 41
1.0
 50
0.0
 71
0
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

    # Adiciona os pontos
    for point in points:
        dxf_content += f" 10\n{point.x:.15g}\n 20\n{point.y:.15g}\n"

    dxf_content += """  0
ENDSEC
  0
EOF
"""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write(dxf_content.format(num_points=len(points)))

    print(f"[+] DXF escrito: {output_path}")


def write_preview_txt(loop: List[Point2D], output_path: str):
    """Gera um preview em texto ASCII."""
    print(f"\n[*] Gerando preview")

    # Normaliza para viewport 0-100
    if len(loop) < 2:
        return

    xs = [p.x for p in loop]
    ys = [p.y for p in loop]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    range_x = max_x - min_x if max_x > min_x else 1
    range_y = max_y - min_y if max_y > min_y else 1

    width, height = 80, 40
    grid = [['.' for _ in range(width)] for _ in range(height)]

    for i, p in enumerate(loop):
        norm_x = (p.x - min_x) / range_x
        norm_y = (p.y - min_y) / range_y

        col = int(norm_x * (width - 1))
        row = int((1 - norm_y) * (height - 1))

        if 0 <= col < width and 0 <= row < height:
            if i == 0:
                grid[row][col] = 'S'  # Start
            else:
                grid[row][col] = '*'

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write(f"Preview da polilinha (S=início, *=vértices)\n")
        f.write(f"Bounds: X=[{min_x:.6f}, {max_x:.6f}], Y=[{min_y:.6f}, {max_y:.6f}]\n\n")
        for row in grid:
            f.write(''.join(row) + '\n')

    print(f"[+] Preview: {output_path}")


def print_report(loop: List[Point2D]):
    """Imprime relatório final."""
    print(f"\n{'='*60}")
    print(f"RELATÓRIO FINAL")
    print(f"{'='*60}")

    area = polygon_area(loop)

    area_signed = 0
    for i in range(len(loop)):
        p1 = loop[i]
        p2 = loop[(i+1) % len(loop)]
        area_signed += p1.x * p2.y - p2.x * p1.y

    direction = "Anti-horário (CCW)" if area_signed > 0 else "Horário (CW)"

    print(f"Pontos no contorno:    {len(loop)}")
    print(f"Área:                  {area:.6f}")
    print(f"Sentido:               {direction}")
    print(f"Ponto inicial:         {loop[0]}")
    print(f"{'='*60}\n")


def process_dxf(input_path: str, output_dxf: str, output_preview: str):
    """Pipeline completo."""
    print(f"\n{'='*60}")
    print(f"REORDENAÇÃO DE POLILINHA PARA VPRO-SAFE")
    print(f"{'='*60}")

    # Extrai e processa pontos
    points = parse_dxf_entities(input_path)
    points = merge_coincident_points(points)
    graph = build_adjacency_graph(points)
    loops = find_loops(graph, points)
    outer_loop = select_outer_loop(loops)
    outer_loop = ensure_ccw_order(outer_loop)
    outer_loop = rotate_to_topleft(outer_loop)
    outer_loop = remove_consecutive_duplicates(outer_loop)

    # Valida
    is_valid = validate_loop(outer_loop)

    # Escreve saída
    write_dxf_r12(outer_loop, output_dxf)
    write_preview_txt(outer_loop, output_preview)
    print_report(outer_loop)

    return is_valid


if __name__ == "__main__":
    input_dxf = "/home/hcmelo/projects/secpro/section/DXF/LA25_vpro.dxf"
    output_dxf = "/home/hcmelo/projects/secpro/section/DXF/LA25_vpro_safe.dxf"
    output_preview = "/tmp/LA25_vpro_safe_preview.txt"

    try:
        success = process_dxf(input_dxf, output_dxf, output_preview)
        if success:
            print("[✓] Processamento concluído com sucesso!")
        else:
            print("[!] Processamento concluído com avisos.")
    except Exception as e:
        print(f"[✗] Erro: {e}")
        import traceback
        traceback.print_exc()
