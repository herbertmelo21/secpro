#!/usr/bin/env python3
"""
Reconstrói ordem topológica de pontos DXF para criar uma polilinha VPro-safe.
Detecta o contorno externo, remove furos internos, ordena pontos de forma contínua.
"""

import ezdxf
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Dict, Set
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Polygon as MPLPolygon
from scipy.spatial import distance_matrix


@dataclass
class Point2D:
    x: float
    y: float

    def __eq__(self, other, tol=1e-6):
        return abs(self.x - other.x) < tol and abs(self.y - other.y) < tol

    def __hash__(self):
        return hash((round(self.x, 8), round(self.y, 8)))

    def dist_to(self, other):
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def __repr__(self):
        return f"({self.x:.6f}, {self.y:.6f})"


class PolylineOrderer:
    def __init__(self, dxf_path: str, tolerance: float = 1e-6):
        self.dxf_path = dxf_path
        self.tolerance = tolerance
        self.points: List[Point2D] = []
        self.merged_points: List[Point2D] = []
        self.graph: Dict[Point2D, Set[Point2D]] = {}
        self.loops: List[List[Point2D]] = []
        self.outer_loop: List[Point2D] = []

    def read_dxf(self):
        """Extrai pontos do DXF."""
        print(f"[*] Lendo {self.dxf_path}")
        doc = ezdxf.readfile(self.dxf_path)
        msp = doc.modelspace()

        # Procura por LWPOLYLINE e LINE
        for entity in msp.query('LWPOLYLINE, LINE, POLYLINE'):
            if entity.dxftype() == 'LWPOLYLINE':
                print(f"    LWPOLYLINE com {len(entity.get_points())} pontos")
                for pt in entity.get_points('xy'):
                    self.points.append(Point2D(pt[0], pt[1]))
            elif entity.dxftype() == 'LINE':
                print(f"    LINE: {entity.dxf.start} -> {entity.dxf.end}")
                self.points.append(Point2D(entity.dxf.start[0], entity.dxf.start[1]))
                self.points.append(Point2D(entity.dxf.end[0], entity.dxf.end[1]))
            elif entity.dxftype() == 'POLYLINE':
                print(f"    POLYLINE com {len(list(entity.points()))} pontos")
                for pt in entity.points():
                    self.points.append(Point2D(pt[0], pt[1]))

        print(f"[+] Total de pontos extraídos: {len(self.points)}")
        return doc

    def merge_coincident_points(self):
        """Agrupa pontos coincidentes (com tolerância)."""
        print(f"\n[*] Unindo pontos coincidentes (tolerância={self.tolerance})")
        self.merged_points = []
        used = set()

        for i, p1 in enumerate(self.points):
            if i in used:
                continue

            cluster = [p1]
            for j in range(i + 1, len(self.points)):
                if j in used:
                    continue
                p2 = self.points[j]
                if p1.dist_to(p2) < self.tolerance:
                    cluster.append(p2)
                    used.add(j)

            # Média dos pontos no cluster
            avg_x = np.mean([p.x for p in cluster])
            avg_y = np.mean([p.y for p in cluster])
            merged = Point2D(avg_x, avg_y)
            self.merged_points.append(merged)

        print(f"[+] Pontos após merge: {len(self.merged_points)} (removidos {len(self.points) - len(self.merged_points)})")

    def build_adjacency_graph(self):
        """Constrói um grafo de adjacência baseado em proximidade de pontos."""
        print(f"\n[*] Construindo grafo de adjacência")
        self.graph = {p: set() for p in self.merged_points}

        # Distância média entre pontos vizinhos na polilinha original
        distances = []
        for i in range(len(self.points) - 1):
            d = self.points[i].dist_to(self.points[i+1])
            if d > 0:
                distances.append(d)

        if distances:
            avg_dist = np.mean(distances)
            max_edge_len = avg_dist * 2.5  # tolerância para conectar pontos
            print(f"    Distância média entre pontos: {avg_dist:.6f}")
            print(f"    Comprimento máximo de aresta: {max_edge_len:.6f}")
        else:
            max_edge_len = 0.1

        # Cria matriz de distância
        coords = np.array([(p.x, p.y) for p in self.merged_points])
        dm = distance_matrix(coords, coords)

        # Conecta cada ponto aos seus vizinhos próximos (máximo 2-3 para formar um contorno)
        for i, p1 in enumerate(self.merged_points):
            neighbors_idx = np.argsort(dm[i])[1:4]  # 3 vizinhos mais próximos, exclui self
            for j in neighbors_idx:
                p2 = self.merged_points[j]
                d = p1.dist_to(p2)
                if d < max_edge_len and d > self.tolerance:
                    self.graph[p1].add(p2)
                    self.graph[p2].add(p1)

        # Verifica grau de cada vértice
        degrees = [len(neighbors) for neighbors in self.graph.values()]
        print(f"    Graus dos vértices: min={min(degrees)}, max={max(degrees)}, média={np.mean(degrees):.1f}")

    def find_loops(self):
        """Detecta loops fechados no grafo."""
        print(f"\n[*] Detectando loops fechados")
        self.loops = []
        visited_edges = set()

        for start_point in self.merged_points:
            if len(self.graph[start_point]) < 2:
                continue

            # Tenta encontrar um loop começando deste ponto
            for first_neighbor in self.graph[start_point]:
                edge_key = (min(start_point, first_neighbor), max(start_point, first_neighbor))
                if edge_key in visited_edges:
                    continue

                loop = self._trace_loop(start_point, first_neighbor, start_point)
                if loop and len(loop) >= 3:
                    # Normaliza o loop para comparação
                    loop_key = tuple(sorted([(p.x, p.y) for p in loop]))

                    # Evita duplicatas
                    is_duplicate = False
                    for existing_loop in self.loops:
                        existing_key = tuple(sorted([(p.x, p.y) for p in existing_loop]))
                        if existing_key == loop_key:
                            is_duplicate = True
                            break

                    if not is_duplicate:
                        self.loops.append(loop)
                        for i in range(len(loop)):
                            p1 = loop[i]
                            p2 = loop[(i + 1) % len(loop)]
                            ek = (min(p1, p2), max(p1, p2))
                            visited_edges.add(ek)

        print(f"[+] Loops encontrados: {len(self.loops)}")
        for i, loop in enumerate(self.loops):
            area = self._polygon_area(loop)
            print(f"    Loop {i}: {len(loop)} pontos, área={area:.6f}")

    def _trace_loop(self, start: Point2D, current: Point2D, origin: Point2D, path: List[Point2D] = None, max_steps: int = None) -> List[Point2D]:
        """Traça um loop começando de 'start' via 'current', voltando a 'origin'."""
        if path is None:
            path = [start]
            if max_steps is None:
                max_steps = len(self.merged_points) + 10

        if len(path) > max_steps:
            return None

        path.append(current)

        # Se voltamos ao início e temos pelo menos 3 pontos
        if len(path) > 3 and current == origin:
            return path[:-1]  # Remove a duplicação do ponto inicial

        # Continua o rastreamento
        for neighbor in self.graph[current]:
            # Não volta imediatamente para o ponto anterior
            if len(path) > 2 and neighbor == path[-2]:
                continue

            # Evita revisitar pontos (exceto o ponto de retorno ao final)
            if neighbor in path[:-1]:
                if neighbor == origin and len(path) > 3:
                    return path  # Encontrou um loop!
                continue

            result = self._trace_loop(start, neighbor, origin, path.copy(), max_steps)
            if result:
                return result

        return None

    def _polygon_area(self, points: List[Point2D]) -> float:
        """Calcula área assinada de um polígono usando Shoelace formula."""
        if len(points) < 3:
            return 0

        area = 0
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            area += p1.x * p2.y - p2.x * p1.y

        return abs(area) / 2

    def select_outer_loop(self):
        """Seleciona o loop com maior área como contorno externo."""
        print(f"\n[*] Selecionando contorno externo (maior área)")
        if not self.loops:
            raise ValueError("Nenhum loop encontrado!")

        areas = [self._polygon_area(loop) for loop in self.loops]
        max_idx = np.argmax(areas)
        self.outer_loop = self.loops[max_idx]

        print(f"[+] Contorno externo selecionado: Loop {max_idx} com {len(self.outer_loop)} pontos, área={areas[max_idx]:.6f}")

    def order_loop_continuous(self):
        """Garante que o loop seja percorrido continuamente (sem saltos)."""
        print(f"\n[*] Ordenando loop para caminhada contínua")

        if len(self.outer_loop) < 3:
            raise ValueError("Loop inválido")

        # Reconstrói o loop caminhando pela adjacência
        ordered = [self.outer_loop[0]]
        current = self.outer_loop[0]
        prev = None

        while len(ordered) < len(self.outer_loop):
            next_point = None
            for neighbor in self.graph[current]:
                if neighbor not in ordered or (neighbor == self.outer_loop[0] and len(ordered) == len(self.outer_loop)):
                    if neighbor != prev:
                        next_point = neighbor
                        break

            if next_point is None:
                print(f"    Aviso: não conseguiu continuar a caminhada em {current}")
                break

            ordered.append(next_point)
            prev = current
            current = next_point

        self.outer_loop = ordered
        print(f"[+] Loop ordenado: {len(self.outer_loop)} pontos")

    def ensure_ccw_order(self):
        """Garante que o loop está em ordem anti-horária (CCW)."""
        print(f"\n[*] Validando ordem (anti-horária)")

        area_signed = 0
        for i in range(len(self.outer_loop)):
            p1 = self.outer_loop[i]
            p2 = self.outer_loop[(i + 1) % len(self.outer_loop)]
            area_signed += p1.x * p2.y - p2.x * p1.y

        if area_signed < 0:
            print("    Loop está em ordem horária, invertendo...")
            self.outer_loop.reverse()
        else:
            print("    Loop está em ordem anti-horária ✓")

    def rotate_to_topleft(self):
        """Rotaciona a lista para começar no ponto superior esquerdo."""
        print(f"\n[*] Rotacionando para começar no ponto superior esquerdo")

        # Encontra o ponto com maior Y (mais para cima)
        # Em caso de empate, escolhe o com menor X (mais à esquerda)
        max_idx = 0
        max_y = self.outer_loop[0].y
        min_x = self.outer_loop[0].x

        for i, p in enumerate(self.outer_loop):
            if p.y > max_y or (p.y == max_y and p.x < min_x):
                max_idx = i
                max_y = p.y
                min_x = p.x

        self.outer_loop = self.outer_loop[max_idx:] + self.outer_loop[:max_idx]
        print(f"[+] Ponto inicial: {self.outer_loop[0]}")

    def remove_consecutive_duplicates(self):
        """Remove pontos consecutivos duplicados."""
        print(f"\n[*] Removendo pontos consecutivos duplicados")
        cleaned = []
        for i, p in enumerate(self.outer_loop):
            if i == 0 or p.dist_to(self.outer_loop[i-1]) > self.tolerance:
                cleaned.append(p)

        removed = len(self.outer_loop) - len(cleaned)
        if removed > 0:
            print(f"[+] Removidos {removed} pontos duplicados")

        self.outer_loop = cleaned

    def validate_loop(self) -> bool:
        """Valida o loop antes de exportar."""
        print(f"\n[*] Validando loop")

        checks = {
            "Mínimo de pontos": len(self.outer_loop) >= 3,
            "Primeiro == Último": self.outer_loop[0].dist_to(self.outer_loop[-1]) <= self.tolerance,
            "Nenhuma duplicata consecutiva": all(
                self.outer_loop[i].dist_to(self.outer_loop[i+1]) > self.tolerance
                for i in range(len(self.outer_loop)-1)
            ),
        }

        # Verifica auto-intersecção com Shapely
        coords = [(p.x, p.y) for p in self.outer_loop]
        try:
            poly = Polygon(coords)
            checks["Sem auto-interseção"] = poly.is_valid
            checks["Área > 0"] = poly.area > 0
        except Exception as e:
            print(f"    Erro ao validar com Shapely: {e}")
            checks["Sem auto-interseção"] = False
            checks["Área > 0"] = False

        for check, result in checks.items():
            status = "✓" if result else "✗"
            print(f"    {status} {check}")

        all_pass = all(checks.values())
        return all_pass

    def write_clean_dxf(self, output_path: str):
        """Escreve um DXF limpo com apenas a polilinha externa."""
        print(f"\n[*] Escrevendo DXF limpo")

        doc = ezdxf.new('R12')
        msp = doc.modelspace()

        # Cria LWPOLYLINE fechada
        points = [(p.x, p.y) for p in self.outer_loop]
        lwpoly = msp.add_lwpolyline2d(points)
        lwpoly.close(True)

        doc.saveas(output_path)
        print(f"[+] DXF escrito: {output_path}")

        return doc

    def generate_preview(self, output_path: str):
        """Gera uma preview PNG do loop."""
        print(f"\n[*] Gerando preview PNG")

        fig, ax = plt.subplots(figsize=(10, 10))

        # Desenha o loop
        coords = np.array([(p.x, p.y) for p in self.outer_loop] + [(self.outer_loop[0].x, self.outer_loop[0].y)])
        ax.plot(coords[:, 0], coords[:, 1], 'b-', linewidth=2, label='Contorno Externo')

        # Marca os vértices
        ax.scatter(coords[:-1, 0], coords[:-1, 1], c='red', s=20, zorder=5)

        # Marca o ponto inicial
        ax.scatter(self.outer_loop[0].x, self.outer_loop[0].y, c='green', s=100, marker='*', zorder=6, label='Ponto Inicial')

        # Desenha os outros loops (furos internos) em cinza
        for i, loop in enumerate(self.loops):
            if loop != self.outer_loop:
                coords_inner = np.array([(p.x, p.y) for p in loop] + [(loop[0].x, loop[0].y)])
                ax.plot(coords_inner[:, 0], coords_inner[:, 1], 'gray', linewidth=1, alpha=0.5, linestyle='--')

        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_title(f'Contorno Externo VPro-Safe\n({len(self.outer_loop)} pontos)')

        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
        print(f"[+] Preview salvo: {output_path}")

    def print_report(self):
        """Imprime um relatório do processamento."""
        print(f"\n{'='*60}")
        print(f"RELATÓRIO FINAL")
        print(f"{'='*60}")

        area = self._polygon_area(self.outer_loop)
        area_signed = 0
        for i in range(len(self.outer_loop)):
            p1 = self.outer_loop[i]
            p2 = self.outer_loop[(i + 1) % len(self.outer_loop)]
            area_signed += p1.x * p2.y - p2.x * p1.y

        direction = "Anti-horário (CCW)" if area_signed > 0 else "Horário (CW)"

        print(f"Pontos extraídos (originais):  {len(self.points)}")
        print(f"Pontos após merge:             {len(self.merged_points)}")
        print(f"Loops detectados:              {len(self.loops)}")
        print(f"Pontos no contorno externo:    {len(self.outer_loop)}")
        print(f"Área assinada:                 {area:.6f}")
        print(f"Sentido da polilinha:          {direction}")
        print(f"Ponto inicial:                 {self.outer_loop[0]}")
        print(f"{'='*60}\n")

    def process(self, output_dxf: str, output_preview: str):
        """Executa todo o pipeline de processamento."""
        print(f"\n{'='*60}")
        print(f"REORDENAÇÃO DE POLILINHA PARA VPRO-SAFE")
        print(f"{'='*60}")

        self.read_dxf()
        self.merge_coincident_points()
        self.build_adjacency_graph()
        self.find_loops()
        self.select_outer_loop()
        self.order_loop_continuous()
        self.ensure_ccw_order()
        self.rotate_to_topleft()
        self.remove_consecutive_duplicates()

        is_valid = self.validate_loop()
        if not is_valid:
            print("\n[!] AVISO: Loop não passou em todas as validações!")

        self.write_clean_dxf(output_dxf)
        self.generate_preview(output_preview)
        self.print_report()

        return is_valid


if __name__ == "__main__":
    # Caminhos
    dxf_input = Path("/home/hcmelo/projects/secpro/section/DXF/LA25_vpro.dxf")
    dxf_output = Path("/home/hcmelo/projects/secpro/section/DXF/LA25_vpro_safe.dxf")
    preview_output = Path("/home/hcmelo/projects/secpro/section/reports/LA25_vpro_safe_order.png")

    orderer = PolylineOrderer(str(dxf_input), tolerance=1e-6)
    success = orderer.process(str(dxf_output), str(preview_output))

    if success:
        print("[✓] Processamento concluído com sucesso!")
    else:
        print("[!] Processamento concluído com avisos - verifique o arquivo gerado.")
