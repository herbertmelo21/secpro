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
    start_angle_deg: float = 0.0,
) -> list[Point]:
    """Gera pontos aproximando um circulo/poligono regular inscrito.

    Com segments=20 e start_angle_deg=-90, gera um poligono regular de 20 lados com um
    vertice exatamente no ponto mais baixo (util para conectar um alveolo a uma fenda
    vertical na face inferior da secao, no mesmo espirito de um circulo tangente).
    """
    if segments < 3:
        raise ValueError("segments deve ser >= 3")
    direction = -1.0 if clockwise else 1.0
    offset = math.radians(start_angle_deg)
    points = []
    for i in range(segments):
        theta = direction * 2.0 * math.pi * i / segments + offset
        points.append((cx + radius * math.cos(theta), cy + radius * math.sin(theta)))
    if close:
        points.append(points[0])
    return points


def polygon_moments(points: list[Point]) -> tuple[float, float, float, float, float]:
    """Momentos de um poligono simples em relacao a ORIGEM (0,0), pelo metodo do shoelace.

    Retorna (area, area*cx, area*cy, Ixx_origem, Iyy_origem), onde Ixx/Iyy sao os
    segundos momentos de area em relacao aos eixos x/y que passam pela origem (nao pelo
    centroide). area e positiva para CCW e negativa para CW - isso e proposital: permite
    somar contribuicoes de contorno externo (CCW) e furos (CW) diretamente, sem tratamento
    especial, para obter as propriedades da secao composta (contorno menos furos).
    """
    n = len(points)
    area2 = 0.0
    cx_a = 0.0
    cy_a = 0.0
    ixx = 0.0
    iyy = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        cross = x1 * y2 - x2 * y1
        area2 += cross
        cx_a += (x1 + x2) * cross
        cy_a += (y1 + y2) * cross
        ixx += (y1 * y1 + y1 * y2 + y2 * y2) * cross
        iyy += (x1 * x1 + x1 * x2 + x2 * x2) * cross
    area = area2 / 2.0
    return area, cx_a / 6.0, cy_a / 6.0, ixx / 12.0, iyy / 12.0


def composite_section_properties(
    loops: list[list[Point]],
) -> dict:
    """Propriedades de uma secao composta por varios loops (1 contorno externo CCW + N
    furos CW, ou vice-versa - o sinal da area de cada loop e que decide a contribuicao).

    Retorna dict com area, centroid (cx, cy), e Ix/Iy em relacao ao PROPRIO CENTROIDE da
    secao composta (nao em relacao a origem), via teorema dos eixos paralelos.
    """
    area = 0.0
    cx_a = 0.0
    cy_a = 0.0
    ixx_origin = 0.0
    iyy_origin = 0.0
    for loop in loops:
        a, cxa, cya, ixx, iyy = polygon_moments(loop)
        area += a
        cx_a += cxa
        cy_a += cya
        ixx_origin += ixx
        iyy_origin += iyy

    if abs(area) < 1e-15:
        return {"area": 0.0, "centroid": (0.0, 0.0), "ix": 0.0, "iy": 0.0}

    cx = cx_a / area
    cy = cy_a / area
    # eixos paralelos: I_origem = I_centroide + A*d^2  =>  I_centroide = I_origem - A*d^2
    ix = ixx_origin - area * cy * cy
    iy = iyy_origin - area * cx * cx
    return {"area": area, "centroid": (cx, cy), "ix": ix, "iy": iy}


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


def polygon_area_centroid_inertia(coords: list[Point]) -> dict:
    """Propriedades seccionais de um poligono simples fechado (shoelace).

    Retorna dict com:
      area  - area (sempre positiva; orientacao e normalizada internamente)
      cx/cy - centroide
      ix/iy - segundos momentos de area em relacao aos eixos QUE PASSAM PELO
              CENTROIDE (teorema dos eixos paralelos ja aplicado)
      ixy   - produto de inercia centroidal

    A caminhada VPRO-safe percorre os alveolos por dentro (via canais), entao
    o shoelace da unica polilinha ja devolve as propriedades LIQUIDAS da secao
    (contorno menos alveolos) sem tratamento especial de furos.
    """
    n = len(coords)
    if n < 3:
        return {"area": 0.0, "cx": 0.0, "cy": 0.0, "ix": 0.0, "iy": 0.0, "ixy": 0.0}

    area2 = sx6 = sy6 = ixx12 = iyy12 = ixy24 = 0.0
    for i in range(n):
        x1, y1 = coords[i]
        x2, y2 = coords[(i + 1) % n]
        cross = x1 * y2 - x2 * y1
        area2 += cross
        sx6 += (x1 + x2) * cross
        sy6 += (y1 + y2) * cross
        ixx12 += (y1 * y1 + y1 * y2 + y2 * y2) * cross
        iyy12 += (x1 * x1 + x1 * x2 + x2 * x2) * cross
        ixy24 += (x1 * y2 + 2.0 * x1 * y1 + 2.0 * x2 * y2 + x2 * y1) * cross

    if area2 < 0:  # normaliza orientacao (CW -> mesmos valores da lista invertida)
        area2, sx6, sy6, ixx12, iyy12, ixy24 = (
            -area2, -sx6, -sy6, -ixx12, -iyy12, -ixy24,
        )

    area = area2 / 2.0
    if abs(area) < 1e-15:
        return {"area": 0.0, "cx": 0.0, "cy": 0.0, "ix": 0.0, "iy": 0.0, "ixy": 0.0}

    cx = sx6 / (6.0 * area)
    cy = sy6 / (6.0 * area)
    ixx_origin = ixx12 / 12.0
    iyy_origin = iyy12 / 12.0
    ixy_origin = ixy24 / 24.0
    return {
        "area": area,
        "cx": cx,
        "cy": cy,
        "ix": ixx_origin - area * cy * cy,
        "iy": iyy_origin - area * cx * cx,
        "ixy": ixy_origin - area * cx * cy,
    }


def relative_error(a: float, b: float) -> float:
    """Erro relativo |a - b| / |b| (b = referencia). b ~ 0 -> inf se a != b."""
    if b == 0.0:
        return 0.0 if a == 0.0 else float("inf")
    return abs(a - b) / abs(b)


def is_probably_scaled_by_001(points: list[Point], expected_min: float = 0.05) -> bool:
    """Heuristica: sinaliza quando a maior dimensao da bbox e suspeita de estar em mm/100.

    Se a maior dimensao for menor que expected_min (metros), a secao provavelmente
    ainda esta em unidades erradas (ex.: milimetros interpretados como metros apos
    uma conversao com fator 0.01 aplicado por engano).
    """
    min_x, min_y, max_x, max_y = bbox(points)
    largest = max(max_x - min_x, max_y - min_y)
    return largest < expected_min


def signed_area(coords: list[Point]) -> float:
    """Area orientada da polilinha (metodo shoelace, positiva=CCW, negativa=CW)."""
    return polygon_area(coords)


def rotate_to_start(coords: list[Point], y_tol: float = 0.0) -> list[Point]:
    """Rotaciona a lista para começar no ponto superior esquerdo: maior Y, depois menor X.

    `y_tol` define a banda de empate em Y: todos os pontos com
    y >= max_y - y_tol sao candidatos, e entre eles vence o de menor X.
    Com y_tol=0.0 (padrao historico) o empate exige igualdade EXATA de
    float - em geometria real (coordenadas com ruido de ~1e-7 vindas do
    DWG) isso faz a escolha cair em qualquer canto cujo Y seja
    microscopicamente maior (ex.: o canto superior DIREITO da LA25).
    Para uma face superior nominalmente plana, use uma banda pequena
    proporcional a altura da secao (ex.: 1e-3 * altura) para obter o
    canto superior esquerdo de verdade.
    """
    if not coords:
        return coords
    max_y = max(y for _x, y in coords)
    idx_best: int | None = None
    for i, (x, y) in enumerate(coords):
        if y < max_y - y_tol:
            continue
        if idx_best is None:
            idx_best = i
            continue
        bx, by = coords[idx_best]
        if x < bx or (x == bx and y > by):
            idx_best = i
    assert idx_best is not None  # ha pelo menos o proprio ponto de max_y
    return coords[idx_best:] + coords[:idx_best]


def ensure_clockwise(coords: list[Point], y_tol: float = 0.0) -> list[Point]:
    """Inverte a lista se signed_area > 0 (CCW), depois rotaciona para manter início no ponto superior esquerdo."""
    area = signed_area(coords)
    if area > 0:
        coords = list(reversed(coords))
    return rotate_to_start(coords, y_tol=y_tol)


def make_vpro_safe_order(coords: list[Point], y_tol: float = 0.0) -> list[Point]:
    """Remove ponto final repetido, aplica ensure_clockwise e rotate_to_start.

    IMPORTANTE: esta funcao NAO reordena pontos por criterio geometrico
    (centroide/angulo) - ela preserva a caminhada original da entidade
    (incluindo os canais dos alveolos), apenas normalizando sentido
    (horario) e ponto inicial (superior esquerdo, ver rotate_to_start).
    """
    if not coords:
        return coords
    cleaned = list(coords)
    if len(cleaned) > 1:
        first, last = cleaned[0], cleaned[-1]
        if math.hypot(last[0] - first[0], last[1] - first[1]) < 1e-9:
            cleaned.pop()
    return ensure_clockwise(cleaned, y_tol=y_tol)
