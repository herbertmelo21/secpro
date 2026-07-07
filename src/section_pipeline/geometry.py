"""Funcoes geometricas puras para validacao e construcao de polilinhas de secao.

Nao gera DXF diretamente. Serve para: validar geometria extraida do JSON do
LibreDWG e, quando necessario, produzir listas de pontos que sao entao
escritas por uma etapa que passa por round-trip do LibreDWG (ver libredwg.py).
"""

from __future__ import annotations

import math

Point = tuple[float, float]


def bbox(points: list[Point]) -> tuple[float, float, float, float]:
    """Retorna (min_x, min_y, max_x, max_y)."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def polygon_area(points: list[Point]) -> float:
    """Area assinada pelo metodo do shoelace (positiva = sentido anti-horario)."""
    n = len(points)
    if n < 3:
        return 0.0
    total = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        total += x1 * y2 - x2 * y1
    return total / 2.0


def polygon_centroid(points: list[Point]) -> Point:
    """Centroide do poligono (assume poligono fechado simples)."""
    area = polygon_area(points)
    n = len(points)
    if n < 3 or math.isclose(area, 0.0, abs_tol=1e-12):
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return sum(xs) / n, sum(ys) / n

    cx = 0.0
    cy = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        cross = x1 * y2 - x2 * y1
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    factor = 1.0 / (6.0 * area)
    return cx * factor, cy * factor


def segment_lengths(points: list[Point], closed: bool = True) -> list[float]:
    """Comprimento de cada segmento consecutivo. Se closed, inclui o segmento de fechamento."""
    n = len(points)
    limit = n if closed else n - 1
    lengths = []
    for i in range(limit):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        lengths.append(math.hypot(x2 - x1, y2 - y1))
    return lengths


def has_consecutive_duplicates(points: list[Point], tol: float = 1e-9) -> list[int]:
    """Indices i onde points[i] e points[i+1] (circular) sao coincidentes dentro de tol."""
    n = len(points)
    duplicates = []
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        if math.hypot(x2 - x1, y2 - y1) <= tol:
            duplicates.append(i)
    return duplicates


def make_circle_points(
    cx: float,
    cy: float,
    radius: float,
    segments: int = 200,
    clockwise: bool = True,
    close: bool = False,
) -> list[Point]:
    """Gera pontos aproximando um circulo, para conferencia/preview (nao para DXF final)."""
    if segments < 3:
        raise ValueError("segments deve ser >= 3")
    direction = -1.0 if clockwise else 1.0
    points = []
    for i in range(segments):
        theta = direction * 2.0 * math.pi * i / segments
        points.append((cx + radius * math.cos(theta), cy + radius * math.sin(theta)))
    if close:
        points.append(points[0])
    return points


def make_alveolar_slot_polyline(
    x_start: float,
    y_base: float,
    width: float,
    depth: float,
    chamfer: float,
) -> list[Point]:
    """Gera pontos de um recorte/alveolo trapezoidal simples usado nas bordas de LA26-like sections.

    x_start: coordenada X do inicio do recorte na borda.
    y_base: Y da borda antes do recorte.
    width: largura total do recorte na base.
    depth: profundidade do recorte (positivo, subtraido de y_base).
    chamfer: deslocamento horizontal do chanfro nas duas laterais do recorte.
    """
    if width <= 0 or depth <= 0:
        raise ValueError("width e depth devem ser positivos")
    if chamfer < 0 or 2 * chamfer >= width:
        raise ValueError("chamfer invalido para a largura informada")

    y_bottom = y_base - depth
    return [
        (x_start, y_base),
        (x_start + chamfer, y_bottom),
        (x_start + width - chamfer, y_bottom),
        (x_start + width, y_base),
    ]


def is_probably_scaled_by_001(points: list[Point], expected_min: float = 0.05) -> bool:
    """Heuristica: sinaliza quando a maior dimensao da bbox e suspeita de estar em mm/100.

    Se a maior dimensao for menor que expected_min (metros), a secao provavelmente
    ainda esta em unidades erradas (ex.: milimetros interpretados como metros apos
    uma conversao com fator 0.01 aplicado por engano).
    """
    min_x, min_y, max_x, max_y = bbox(points)
    largest = max(max_x - min_x, max_y - min_y)
    return largest < expected_min
