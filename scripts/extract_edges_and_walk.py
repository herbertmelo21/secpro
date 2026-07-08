#!/usr/bin/env python3
"""
Extrai segmentos (edges) do DXF e constrói um grafo de conectividade.
Caminha pelo loop externo para gerar a sequência de vértices.
"""

import re
import math
from dataclasses import dataclass
from typing import List, Dict, Tuple, Set, Optional
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
        """Teste de igualdade com tolerância."""
        return abs(self.x - other.x) < tol and abs(self.y - other.y) < tol

    def __hash__(self):
        return hash((round(self.x, 8), round(self.y, 8)))

    def __eq__(self, other):
        return self.snap_eq(other)

    def __repr__(self):
        return f"({self.x:.6f}, {self.y:.6f})"


@dataclass
class Segment:
    """Representa um segmento de linha ou arco."""
    p1: Point
    p2: Point
    seg_type: str = "LINE"  # LINE, ARC_SEGMENT
    bulge: float = 0.0  # para arcos em LWPOLYLINE

    def __repr__(self):
        return f"{self.seg_type}: {self.p1} -> {self.p2}"


class EdgeGraph:
    """Grafo de arestas e vértices extraído do DXF."""

    def __init__(self, tolerance=1e-6):
        self.tolerance = tolerance
        self.vertices: Dict[Tuple[float, float], Point] = {}  # key: (x, y) rounded
        self.edges: List[Segment] = []
        self.adjacency: Dict[Point, List[Point]] = {}

    def add_vertex(self, point: Point) -> Point:
        """Adiciona vértice ou retorna vértice existente se coincidente."""
        key = (round(point.x, 8), round(point.y, 8))

        if key not in self.vertices:
            self.vertices[key] = point
            self.adjacency[point] = []

        return self.vertices[key]

    def add_edge(self, p1: Point, p2: Point, seg_type="LINE", bulge=0.0):
        """Adiciona aresta (segmento) entre dois vértices."""
        p1 = self.add_vertex(p1)
        p2 = self.add_vertex(p2)

        if p1.snap_eq(p2, self.tolerance):
            return  # Skip zero-length edges

        seg = Segment(p1, p2, seg_type, bulge)
        self.edges.append(seg)

        # Grafo não-direcionado: adiciona adjacência em ambas as direções
        if p2 not in self.adjacency[p1]:
            self.adjacency[p1].append(p2)
        if p1 not in self.adjacency[p2]:
            self.adjacency[p2].append(p1)

    def find_loops(self) -> List[List[Point]]:
        """Encontra todos os loops fechados no grafo."""
        loops = []
        visited_edges = set()

        for start_vertex in self.vertices.values():
            if len(self.adjacency[start_vertex]) < 2:
                continue

            for first_neighbor in self.adjacency[start_vertex]:
                edge_key = (id(start_vertex), id(first_neighbor))
                if edge_key in visited_edges:
                    continue

                loop = self._trace_loop(start_vertex, first_neighbor, start_vertex, [start_vertex])

                if loop and len(loop) >= 3:
                    # Marca arestas do loop como visitadas
                    for i in range(len(loop)):
                        v1 = loop[i]
                        v2 = loop[(i + 1) % len(loop)]
                        ek = (id(v1), id(v2))
                        visited_edges.add(ek)

                    loops.append(loop)

        return loops

    def _trace_loop(self, start: Point, current: Point, origin: Point, path: List[Point]) -> Optional[List[Point]]:
        """Traça um loop começando de 'start' via 'current'."""
        if len(path) > len(self.vertices) + 5:
            return None  # Proteção contra loops infinitos

        path.append(current)

        # Se voltamos ao início
        if len(path) > 3 and current.snap_eq(origin, self.tolerance):
            return path[:-1]

        # Continua para vizinhos
        for neighbor in self.adjacency[current]:
            # Não volta imediatamente
            if len(path) > 2 and neighbor.snap_eq(path[-2], self.tolerance):
                continue

            # Evita revisitar (exceto voltando ao fim)
            is_revisit = any(neighbor.snap_eq(p, self.tolerance) for p in path[:-1])

            if is_revisit:
                if neighbor.snap_eq(origin, self.tolerance) and len(path) > 3:
                    return path  # Loop fechado
                continue

            result = self._trace_loop(start, neighbor, origin, path.copy())
            if result:
                return result

        return None

    def polygon_area(self, vertices: List[Point]) -> float:
        """Calcula área assinada de um polígono."""
        if len(vertices) < 3:
            return 0

        area = 0
        for i in range(len(vertices)):
            p1 = vertices[i]
            p2 = vertices[(i + 1) % len(vertices)]
            area += p1.x * p2.y - p2.x * p1.y

        return abs(area) / 2

    def signed_area(self, vertices: List[Point]) -> float:
        """Calcula área assinada (positivo = CCW)."""
        if len(vertices) < 3:
            return 0

        area = 0
        for i in range(len(vertices)):
            p1 = vertices[i]
            p2 = vertices[(i + 1) % len(vertices)]
            area += p1.x * p2.y - p2.x * p1.y

        return area / 2


def parse_dxf_entities(dxf_path: str) -> EdgeGraph:
    """Extrai todas as entidades de desenho (LINE, LWPOLYLINE, etc)."""
    print(f"[*] Lendo DXF: {dxf_path}")

    with open(dxf_path, 'r') as f:
        content = f.read()

    graph = EdgeGraph()

    # Encontra seção ENTITIES
    entities_match = re.search(r'ENTITIES\s*\n\s*0\n', content)
    endsec_match = re.search(r'ENDSEC', content[entities_match.start():])

    if not entities_match or not endsec_match:
        raise ValueError("Seção ENTITIES não encontrada")

    entities_start = entities_match.start()
    entities_end = entities_match.start() + endsec_match.start()
    entities_section = content[entities_start:entities_end]

    # Procura por LWPOLYLINE
    _extract_lwpolylines(entities_section, graph)

    # Procura por POLYLINE
    _extract_polylines(entities_section, graph)

    # Procura por LINE
    _extract_lines(entities_section, graph)

    # Procura por ARC
    _extract_arcs(entities_section, graph)

    print(f"[+] Vértices: {len(graph.vertices)}")
    print(f"[+] Arestas: {len(graph.edges)}")

    return graph


def _extract_lwpolylines(entities_section: str, graph: EdgeGraph):
    """Extrai LWPOLYLINE e adiciona como segmentos."""
    lines = entities_section.split('\n')
    i = 0

    while i < len(lines):
        if lines[i].strip() == 'LWPOLYLINE':
            # Extrai dados até próxima entidade
            x_coords = []
            y_coords = []
            is_closed = False
            last_x = None

            i += 1
            while i < len(lines):
                code = lines[i].strip()
                if code == '0':
                    break  # Próxima entidade

                if code == '70' and i + 1 < len(lines):
                    try:
                        is_closed = bool(int(lines[i + 1].strip()) & 1)
                    except:
                        pass
                    i += 2
                    continue

                if code == '10' and i + 1 < len(lines):
                    try:
                        last_x = float(lines[i + 1].strip())
                    except:
                        pass
                    i += 2
                    continue

                if code == '20' and i + 1 < len(lines):
                    try:
                        if last_x is not None:
                            x_coords.append(last_x)
                            y_coords.append(float(lines[i + 1].strip()))
                            last_x = None
                    except:
                        pass
                    i += 2
                    continue

                i += 1

            # Adiciona segmentos
            for k in range(len(x_coords)):
                if k < len(x_coords) - 1:
                    p1 = Point(x_coords[k], y_coords[k])
                    p2 = Point(x_coords[k + 1], y_coords[k + 1])
                    graph.add_edge(p1, p2, seg_type="LINE")
                elif is_closed and len(x_coords) >= 3:
                    p1 = Point(x_coords[k], y_coords[k])
                    p2 = Point(x_coords[0], y_coords[0])
                    graph.add_edge(p1, p2, seg_type="LINE")
        else:
            i += 1


def _extract_polylines(entities_section: str, graph: EdgeGraph):
    """Extrai POLYLINE (antiga) e seus vértices."""
    # Similar à LWPOLYLINE mas formato mais complexo
    # Simplificado: extrair SEQEND como fim
    pass


def _extract_lines(entities_section: str, graph: EdgeGraph):
    """Extrai LINE (segmentos de reta simples)."""
    line_pattern = r'LINE\s*\n\s*5.*?(?=\n\s*0\n(?:LINE|LWPOLYLINE|POLYLINE|ARC|ENDSEC))'

    for match in re.finditer(line_pattern, entities_section, re.DOTALL):
        line_text = match.group(0)

        # Extrai ponto inicial (10, 20)
        p1_match = re.search(r'10\s*\n\s*([-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)\s*\n\s*20\s*\n\s*([-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)', line_text)

        # Extrai ponto final (11, 21)
        p2_match = re.search(r'11\s*\n\s*([-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)\s*\n\s*21\s*\n\s*([-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)', line_text)

        if p1_match and p2_match:
            p1 = Point(float(p1_match.group(1)), float(p1_match.group(3)))
            p2 = Point(float(p2_match.group(1)), float(p2_match.group(3)))
            graph.add_edge(p1, p2, seg_type="LINE")


def _extract_arcs(entities_section: str, graph: EdgeGraph):
    """Extrai ARC e discretiza em segmentos."""
    # Simplificado: extrair apenas centro e raio, discretizar
    pass


def find_outer_loop(graph: EdgeGraph) -> List[Point]:
    """Encontra o loop com maior área (contorno externo)."""
    loops = graph.find_loops()

    if not loops:
        raise ValueError("Nenhum loop encontrado no grafo")

    print(f"\n[*] Loops encontrados: {len(loops)}")

    areas = [(i, graph.polygon_area(loop)) for i, loop in enumerate(loops)]
    areas.sort(key=lambda x: x[1], reverse=True)

    for idx, area in areas[:5]:
        print(f"    Loop {idx}: {len(loops[idx])} vértices, área={area:.6f}")

    outer_idx = areas[0][0]
    return loops[outer_idx]


def ensure_ccw(vertices: List[Point]) -> List[Point]:
    """Garante ordem anti-horária."""
    signed_area = 0
    for i in range(len(vertices)):
        p1 = vertices[i]
        p2 = vertices[(i + 1) % len(vertices)]
        signed_area += p1.x * p2.y - p2.x * p1.y

    if signed_area < 0:
        print("[*] Invertendo para CCW")
        return vertices[::-1]

    return vertices


def rotate_to_topleft(vertices: List[Point]) -> List[Point]:
    """Rotaciona para começar no superior esquerdo."""
    max_idx = 0
    for i in range(1, len(vertices)):
        v_curr = vertices[i]
        v_max = vertices[max_idx]

        if v_curr.y > v_max.y + 1e-8 or (abs(v_curr.y - v_max.y) < 1e-8 and v_curr.x < v_max.x - 1e-8):
            max_idx = i

    return vertices[max_idx:] + vertices[:max_idx]


def validate_continuity(graph: EdgeGraph, vertices: List[Point]) -> bool:
    """Valida que a sequência é uma caminhada contínua."""
    print(f"\n[*] Validando continuidade")

    errors = []

    for i in range(len(vertices)):
        v_curr = vertices[i]
        v_next = vertices[(i + 1) % len(vertices)]

        # Verifica se há aresta entre v_curr e v_next
        has_edge = v_next in graph.adjacency.get(v_curr, [])

        if not has_edge:
            errors.append(f"    Sem aresta: {v_curr} -> {v_next}")

    if errors:
        print(f"[!] {len(errors)} erros de continuidade encontrados:")
        for err in errors[:5]:
            print(err)
        return False

    print(f"[+] Sequência é contínua ✓")
    return True


def output_results(graph: EdgeGraph, vertices: List[Point], output_dir: str):
    """Escreve os resultados."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # JSON com coordenadas ordenadas
    json_path = Path(output_dir) / "LA25_outer_ordered.json"
    json_data = [{"i": i, "x": v.x, "y": v.y} for i, v in enumerate(vertices)]

    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)

    print(f"\n[+] JSON: {json_path}")

    # DXF com polilinha
    dxf_path = Path(output_dir) / "LA25_vpro_safe_ordered.dxf"
    write_dxf_lwpolyline(vertices, str(dxf_path))
    print(f"[+] DXF: {dxf_path}")


def write_dxf_lwpolyline(vertices: List[Point], output_path: str):
    """Escreve DXF R12 com uma única LWPOLYLINE fechada."""
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

    for pt in vertices:
        dxf_content += f" 10\n{pt.x:.15g}\n 20\n{pt.y:.15g}\n"

    dxf_content += """  0
ENDSEC
  0
EOF
"""

    with open(output_path, 'w') as f:
        f.write(dxf_content.format(num_points=len(vertices)))


def print_report(graph: EdgeGraph, vertices: List[Point]):
    """Relatório no terminal."""
    print(f"\n{'='*70}")
    print(f"RELATÓRIO DE CAMINHADA POR GRAFO")
    print(f"{'='*70}\n")

    area_signed = 0
    for i in range(len(vertices)):
        p1 = vertices[i]
        p2 = vertices[(i + 1) % len(vertices)]
        area_signed += p1.x * p2.y - p2.x * p1.y

    area = abs(area_signed) / 2
    direction = "CCW (Anti-horário)" if area_signed > 0 else "CW (Horário)"

    # Distâncias entre vértices consecutivos
    dists = [vertices[i].dist(vertices[(i + 1) % len(vertices)]) for i in range(len(vertices))]
    max_dist_idx = dists.index(max(dists))

    print(f"Vértices:                  {len(vertices)}")
    print(f"Arestas no grafo:          {len(graph.edges)}")
    print(f"Loops encontrados:         {len(graph.find_loops())}")
    print(f"Área do loop externo:      {area:.6f} m²")
    print(f"Sentido:                   {direction}")
    print(f"Ponto inicial:             {vertices[0]}")
    print(f"Maior segmento:            {dists[max_dist_idx]:.6f} m (entre vértice {max_dist_idx} e {(max_dist_idx+1) % len(vertices)})")
    print(f"Distância média:           {sum(dists)/len(dists):.6f} m")
    print(f"{'='*70}\n")


def main():
    dxf_input = "/home/hcmelo/projects/secpro/section/DXF/LA25_vpro.dxf"
    output_dir = "/home/hcmelo/projects/secpro/output"

    print(f"\n{'='*70}")
    print(f"CAMINHADA POR GRAFO - REORDENAÇÃO VPRO-SAFE")
    print(f"{'='*70}\n")

    # Extrai grafo
    graph = parse_dxf_entities(dxf_input)

    # Encontra loop externo
    print(f"\n[*] Encontrando loop externo")
    outer_loop = find_outer_loop(graph)
    print(f"[+] Loop selecionado: {len(outer_loop)} vértices")

    # Normaliza
    outer_loop = ensure_ccw(outer_loop)
    outer_loop = rotate_to_topleft(outer_loop)

    # Valida
    is_continuous = validate_continuity(graph, outer_loop)

    # Saída
    output_results(graph, outer_loop, output_dir)
    print_report(graph, outer_loop)

    if is_continuous:
        print("[✓] Processamento concluído com sucesso!")
    else:
        print("[!] Avisos durante validação")


if __name__ == "__main__":
    main()
