"""Validacao topologica de caminhadas (walks) de polilinha via grafo de arestas.

Motivacao (VPRO): o importador do VPRO valida a poligonal incrementalmente -
cada ponto novo precisa continuar uma caminhada continua pela borda. Qualquer
"corda" (salto para um ponto nao adjacente, atravessando o interior) quebra a
importacao. Estes utilitarios NAO reordenam nada por criterio geometrico
global (centroide/angulo/distancia - isso gera cordas); eles apenas VALIDAM
que uma sequencia de pontos e uma caminhada continua sobre as arestas reais
da geometria de origem.

Convencao de nos: cada vertice vira um no identificado por (round(x, ndigits),
round(y, ndigits)). Com ndigits=9 (0.5 nm em metros) o snap e essencialmente
exato - pontos distintos a ~1e-6 m (ex.: paredes do canal de um alveolo, ~1 mm)
NUNCA sao fundidos por engano. Os alveolos de secoes alveolares (LA25 etc.)
sao ligados a borda externa por canais estreitos intencionais; fundir essas
paredes fecharia o alveolo como loop independente, exatamente o que o VPRO
nao aceita.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

Point = tuple[float, float]
NodeKey = tuple[float, float]

DEFAULT_NDIGITS = 9


def node_key(p: Point, ndigits: int = DEFAULT_NDIGITS) -> NodeKey:
    """Chave de no com snap por arredondamento (ver docstring do modulo)."""
    return (round(p[0], ndigits), round(p[1], ndigits))


@dataclass
class EdgeGraph:
    """Grafo nao direcionado de vertices/arestas de uma ou mais polilinhas."""

    adjacency: dict[NodeKey, set[NodeKey]] = field(default_factory=dict)
    edges: set[frozenset[NodeKey]] = field(default_factory=set)
    ndigits: int = DEFAULT_NDIGITS

    @property
    def n_nodes(self) -> int:
        return len(self.adjacency)

    @property
    def n_edges(self) -> int:
        return len(self.edges)

    def add_edge(self, p1: Point, p2: Point) -> None:
        k1 = node_key(p1, self.ndigits)
        k2 = node_key(p2, self.ndigits)
        if k1 == k2:
            return  # aresta degenerada (comprimento ~zero) nao entra no grafo
        self.adjacency.setdefault(k1, set()).add(k2)
        self.adjacency.setdefault(k2, set()).add(k1)
        self.edges.add(frozenset((k1, k2)))

    def has_edge(self, p1: Point, p2: Point) -> bool:
        k1 = node_key(p1, self.ndigits)
        k2 = node_key(p2, self.ndigits)
        return frozenset((k1, k2)) in self.edges

    def degree_census(self) -> dict[int, int]:
        """{grau: quantidade de nos com esse grau}."""
        census: dict[int, int] = {}
        for neighbors in self.adjacency.values():
            census[len(neighbors)] = census.get(len(neighbors), 0) + 1
        return census

    def connected_components(self) -> list[set[NodeKey]]:
        seen: set[NodeKey] = set()
        components: list[set[NodeKey]] = []
        for start in self.adjacency:
            if start in seen:
                continue
            stack = [start]
            component: set[NodeKey] = set()
            while stack:
                node = stack.pop()
                if node in component:
                    continue
                component.add(node)
                stack.extend(self.adjacency[node] - component)
            seen |= component
            components.append(component)
        return components

    def cycle_census(self) -> list[dict]:
        """Descreve cada componente conexa: e um ciclo simples? quantos nos/arestas?

        Um componente e um ciclo simples (loop fechado) quando todo no tem grau 2
        e o numero de arestas internas e igual ao de nos. Para a caminhada global
        VPRO-safe espera-se exatamente UM componente, que e UM ciclo cobrindo
        todos os nos (alveolos NAO aparecem como ciclos separados - eles fazem
        parte do mesmo ciclo global, ligados pelos canais).
        """
        result = []
        for component in self.connected_components():
            degrees = [len(self.adjacency[node]) for node in component]
            internal_edges = sum(
                1 for edge in self.edges if all(node in component for node in edge)
            )
            result.append(
                {
                    "n_nodes": len(component),
                    "n_edges": internal_edges,
                    "is_simple_cycle": all(d == 2 for d in degrees)
                    and internal_edges == len(component),
                    "degree_min": min(degrees),
                    "degree_max": max(degrees),
                }
            )
        return result


def build_edge_graph(
    points: list[Point], closed: bool = True, ndigits: int = DEFAULT_NDIGITS
) -> EdgeGraph:
    """Constroi o grafo a partir de vertices consecutivos de uma polilinha.

    A ordem de `points` deve ser a ordem original da entidade (a caminhada como
    desenhada), incluindo os canais dos alveolos. `closed=True` acrescenta a
    aresta de fechamento ultimo->primeiro.
    """
    graph = EdgeGraph(ndigits=ndigits)
    n = len(points)
    limit = n if closed else n - 1
    for i in range(limit):
        graph.add_edge(points[i], points[(i + 1) % n])
    return graph


def check_continuous_walk(
    ordered: list[Point], graph: EdgeGraph, closed: bool = True
) -> tuple[bool, list[int]]:
    """Verifica que cada par consecutivo de `ordered` e uma aresta real do grafo.

    Retorna (ok, indices i cujo segmento ordered[i] -> ordered[i+1] NAO existe
    no grafo original - ou seja, uma corda/salto inventado).
    """
    n = len(ordered)
    limit = n if closed else n - 1
    violations = [
        i for i in range(limit) if not graph.has_edge(ordered[i], ordered[(i + 1) % n])
    ]
    return not violations, violations


def _orient(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _proper_crossing(p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
    """Cruzamento proprio (transversal) entre os segmentos p1p2 e p3p4.

    Toques em extremidade e sobreposicoes colineares NAO contam - contato
    intencional de canal (se existir na geometria) nao e reprovado aqui;
    apenas cruzamentos de fato, que inverteriam a regiao fechada.
    """
    d1 = _orient(p3, p4, p1)
    d2 = _orient(p3, p4, p2)
    d3 = _orient(p1, p2, p3)
    d4 = _orient(p1, p2, p4)
    return ((d1 > 0) != (d2 > 0)) and (d1 != 0 and d2 != 0) and (
        (d3 > 0) != (d4 > 0)
    ) and (d3 != 0 and d4 != 0)


def self_intersections(points: list[Point], closed: bool = True) -> list[tuple[int, int]]:
    """Pares (i, j) de segmentos nao adjacentes que se cruzam transversalmente.

    O(n^2) simples - suficiente para as ~1e3 aresta destas secoes.
    """
    n = len(points)
    limit = n if closed else n - 1
    crossings: list[tuple[int, int]] = []
    for i in range(limit):
        a1 = points[i]
        a2 = points[(i + 1) % n]
        for j in range(i + 2, limit):
            if i == 0 and j == limit - 1 and closed:
                continue  # segmento de fechamento e adjacente ao primeiro
            b1 = points[j]
            b2 = points[(j + 1) % n]
            if _proper_crossing(a1, a2, b1, b2):
                crossings.append((i, j))
    return crossings


def min_nonadjacent_clearance(
    points: list[Point], min_index_gap: int = 8
) -> tuple[float, int, int]:
    """Menor distancia entre vertices distantes ao longo da caminhada.

    Mede a folga fisica minima entre trechos diferentes da borda - nas secoes
    alveolares isso corresponde a largura do canal/furinho que liga cada
    alveolo a borda externa. Um valor > 0 evidencia que o canal esta
    PRESERVADO (paredes nao foram fundidas nem o alveolo fechado).

    Retorna (distancia_minima, i, j). `min_index_gap` ignora vizinhos
    imediatos ao longo da caminhada (distancia circular de indices).
    """
    n = len(points)
    best = (math.inf, -1, -1)
    for i in range(n):
        xi, yi = points[i]
        for j in range(i + min_index_gap, n):
            if (n - (j - i)) < min_index_gap:  # distancia circular tambem conta
                continue
            xj, yj = points[j]
            d = math.hypot(xj - xi, yj - yi)
            if d < best[0]:
                best = (d, i, j)
    return best
