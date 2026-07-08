"""Simplificacao geometrica da caminhada VPRO-safe, validada por propriedades.

Estrategia: NAO simplificar a polilinha densa "no escuro". A fonte primaria
(JSON do LibreDWG) descreve os alveolos como arcos verdadeiros (bulges), entao
a reducao de pontos e feita REDISCRETIZANDO cada arco na ordem da propria
entidade, com `circle_points` pontos por circulo completo. Os vertices da
entidade fonte (cantos externos, entrada/saida dos canais dos alveolos,
extremidades de arco, mudancas bruscas de direcao) sao ANCORAS: nunca sao
movidos nem removidos, e a conectividade da caminhada e preservada por
construcao.

Compensacao de raio (area-preserving): um poligono inscrito subestima a area
do setor circular em ~(2*pi^2/3)/n^2 por circulo - com 32 pontos isso ja
estoura tolerancia de 0.1% de area na LA25. Por isso os pontos INTERIORES de
cada arco sao colocados num raio r' > r calculado em forma fechada para que o
leque (fan) do arco tenha exatamente a area do setor verdadeiro, mantendo as
extremidades fixas nos vertices fonte. O desvio radial e ~r*(theta/m)^2/12
(fracao de mm nos alveolos da LA25) e quem da o veredito final e sempre a
validacao de propriedades (validation.validate_section_properties).

Os passos adicionais (simplify_collinear, simplify_rdp_topology_safe) sao
conservadores: nunca removem ancoras e nunca aceitam resultado que crie
self-intersection.
"""

from __future__ import annotations

import math

from . import walk as walk_mod

Point = tuple[float, float]

# escada de escalonamento automatico (requisito): 24 -> 32 -> 48 -> 64
CIRCLE_POINTS_LADDER = (24, 32, 48, 64)

# acima disso a compensacao deixa de ser um ajuste fino e o arco e mantido
# inscrito (so acontece com pouquissimos segmentos por arco).
MAX_COMPENSATION_RATIO = 1.05

MIN_ARC_SEGMENTS = 4


def circle_points_candidates(start: int) -> list[int]:
    """Valores de circle_points a tentar: o pedido e depois a escada acima dele."""
    ladder = sorted(set(CIRCLE_POINTS_LADDER) | {start})
    return [v for v in ladder if v >= start]


def _arc_center_radius(p1: Point, p2: Point, bulge: float) -> tuple[Point, float, float, float]:
    """Centro, raio, angulo inicial e angulo incluido (assinado) do arco de bulge.

    Mesmas formulas ja usadas em scripts/generate_vpro_ahk_from_libredwg.py:
    theta = 4*atan(bulge); radius = chord / (2*sin(|theta|/2)).
    """
    x1, y1 = p1
    x2, y2 = p2
    chord = math.hypot(x2 - x1, y2 - y1)
    theta = 4.0 * math.atan(bulge)
    radius = chord / (2.0 * math.sin(abs(theta) / 2.0))
    mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    ux, uy = (x2 - x1) / chord, (y2 - y1) / chord
    h = radius * math.cos(abs(theta) / 2.0)
    sign = 1.0 if bulge > 0 else -1.0
    cx = mx - sign * uy * h
    cy = my + sign * ux * h
    a1 = math.atan2(y1 - cy, x1 - cx)
    return (cx, cy), radius, a1, theta


def _compensated_interior_radius(radius: float, theta: float, segments: int) -> float:
    """Raio r' dos pontos interiores para o leque poligonal ter a area exata
    do setor circular (extremidades fixas em `radius`).

    Igualando area do leque `(sin(a)/2) * [2*r*r' + (m-2)*r'^2]` (a = theta/m)
    a area do setor `r^2*theta/2`:
      m == 2: r' = r*theta / (2*sin(theta/2))
      m >  2: r' = r * (sqrt(1 + (m-2)*theta/sin(a)) - 1) / (m - 2)
    """
    m = segments
    t = abs(theta)
    a = t / m
    if m == 2:
        return radius * t / (2.0 * math.sin(t / 2.0))
    return radius * (math.sqrt(1.0 + (m - 2) * t / math.sin(a)) - 1.0) / (m - 2)


def arc_points_compensated(
    p1: Point,
    p2: Point,
    bulge: float,
    circle_points: int,
    compensate: bool = True,
    min_arc_segments: int = MIN_ARC_SEGMENTS,
) -> list[Point]:
    """Pontos INTERIORES (excluindo p1 e p2) do arco de bulge, rediscretizado
    com `circle_points` pontos por circulo completo (2*pi)."""
    if abs(bulge) < 1e-12:
        return []
    if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) <= 1e-12:
        # arco degenerado (extremidades coincidentes): existe na fonte da LA25
        # (segmentos de 0.67 graus com corda zero pareados com o arco de
        # ~359.33 graus de cada alveolo) e nao contribui geometria - o pipeline
        # denso tambem o descarta via dedup.
        return []
    (cx, cy), radius, a1, theta = _arc_center_radius(p1, p2, bulge)
    segments = max(min_arc_segments, round(circle_points * abs(theta) / (2.0 * math.pi)))
    if segments < 2:
        return []

    r_interior = radius
    if compensate:
        r_prime = _compensated_interior_radius(radius, theta, segments)
        if r_prime / radius <= MAX_COMPENSATION_RATIO:
            r_interior = r_prime
        # senao: arco com segmentos demais de menos para compensar com
        # seguranca - mantem inscrito e deixa a validacao decidir.

    points = []
    for k in range(1, segments):
        angle = a1 + theta * (k / segments)
        points.append((cx + r_interior * math.cos(angle), cy + r_interior * math.sin(angle)))
    return points


def expand_polyline_lowres(
    raw_points: list[Point],
    raw_bulges: list[float],
    circle_points: int,
    compensate: bool = True,
) -> tuple[list[Point], list[int]]:
    """Expande a LWPOLYLINE fonte (fechada) rediscretizando os arcos em baixa
    resolucao, NA ORDEM da entidade.

    Retorna (pontos, indices_de_ancora). Ancoras = os proprios vertices da
    entidade fonte (cantos externos, entradas/saidas dos canais dos alveolos,
    extremos de arco/mudancas bruscas de direcao). Como os pontos ainda serao
    recentralizados/deduplicados pelo chamador, as ancoras saem como INDICES
    na lista expandida - o chamador converte para chaves walk.node_key DEPOIS
    de qualquer transformacao de coordenadas (chaves por valor sobrevivem a
    dedup/inversao/rotacao da lista).
    """
    n = len(raw_points)
    expanded: list[Point] = []
    anchor_indices: list[int] = []
    for i in range(n):
        p1 = raw_points[i]
        p2 = raw_points[(i + 1) % n]
        bulge = raw_bulges[i] if i < len(raw_bulges) else 0.0
        anchor_indices.append(len(expanded))
        expanded.append(p1)
        expanded.extend(arc_points_compensated(p1, p2, bulge, circle_points, compensate))
    return expanded, anchor_indices


def _turn_angle_deg(prev: Point, cur: Point, nxt: Point) -> float:
    """Desvio angular (graus) em `cur` em relacao a seguir reto de prev->nxt."""
    a1 = math.atan2(cur[1] - prev[1], cur[0] - prev[0])
    a2 = math.atan2(nxt[1] - cur[1], nxt[0] - cur[0])
    d = abs(a2 - a1) % (2.0 * math.pi)
    if d > math.pi:
        d = 2.0 * math.pi - d
    return math.degrees(d)


def _point_segment_distance(p: Point, a: Point, b: Point) -> float:
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0.0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def simplify_collinear(
    coords: list[Point],
    angle_tol_deg: float = 1.0,
    dist_tol: float = 1e-6,
    protected: set | None = None,
) -> list[Point]:
    """Remove vertices quase colineares de uma polilinha FECHADA (circular).

    Conservador: um vertice so cai se o desvio angular for <= angle_tol_deg
    E a distancia dele a corda (vizinho anterior -> proximo) for <= dist_tol.
    Vertices em `protected` (chaves walk.node_key) nunca caem. Repete ate
    estabilizar. Nunca reduz abaixo de 3 vertices.
    """
    protected = protected or set()
    points = list(coords)
    changed = True
    while changed and len(points) > 3:
        changed = False
        kept: list[Point] = []
        n = len(points)
        i = 0
        while i < n:
            cur = points[i]
            if walk_mod.node_key(cur) in protected:
                kept.append(cur)
                i += 1
                continue
            prev = kept[-1] if kept else points[i - 1]
            nxt = points[(i + 1) % n]
            if (
                len(points) - 1 >= 3
                and _turn_angle_deg(prev, cur, nxt) <= angle_tol_deg
                and _point_segment_distance(cur, prev, nxt) <= dist_tol
            ):
                changed = True
                n -= 1
                points.pop(i)
                continue
            kept.append(cur)
            i += 1
    return points


def _rdp(points: list[Point], tolerance: float) -> list[Point]:
    """Ramer-Douglas-Peucker classico numa cadeia ABERTA (extremos mantidos)."""
    if len(points) <= 2:
        return list(points)
    a, b = points[0], points[-1]
    worst_d = -1.0
    worst_i = 0
    for i in range(1, len(points) - 1):
        d = _point_segment_distance(points[i], a, b)
        if d > worst_d:
            worst_d = d
            worst_i = i
    if worst_d <= tolerance:
        return [a, b]
    left = _rdp(points[: worst_i + 1], tolerance)
    right = _rdp(points[worst_i:], tolerance)
    return left[:-1] + right


def simplify_rdp_topology_safe(
    coords: list[Point],
    tolerance: float,
    protected: set | None = None,
) -> list[Point]:
    """RDP seguro para a caminhada VPRO-safe (polilinha fechada).

    - roda o RDP separadamente em cada subcadeia entre ancoras consecutivas
      (ancoras NUNCA sao removidas; se nao houver ancoras, usa o 1o ponto);
    - rejeita o resultado (devolve a entrada) se a polilinha simplificada
      criar self-intersection transversal - "topology safe".
    """
    if tolerance <= 0 or len(coords) <= 4:
        return list(coords)
    protected = protected or set()

    anchor_idx = [i for i, p in enumerate(coords) if walk_mod.node_key(p) in protected]
    if not anchor_idx:
        anchor_idx = [0]

    n = len(coords)
    result: list[Point] = []
    for k, start in enumerate(anchor_idx):
        end = anchor_idx[(k + 1) % len(anchor_idx)]
        chain = (
            coords[start : end + 1]
            if end > start
            else coords[start:] + coords[: end + 1]  # subcadeia que cruza o fechamento
        )
        simplified_chain = _rdp(chain, tolerance)
        result.extend(simplified_chain[:-1])  # ultimo ponto = ancora da proxima cadeia

    if len(result) < 3:
        return list(coords)
    if walk_mod.self_intersections(result, closed=True):
        return list(coords)  # nao aceita simplificacao que cruza a borda
    return result
