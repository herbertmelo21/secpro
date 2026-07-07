"""Validacoes geometricas gerais e checks especificos da secao LA26."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import geometry

Point = tuple[float, float]


@dataclass
class ValidationResult:
    ok: bool
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add_pass(self, message: str) -> None:
        self.checks.append(f"OK - {message}")

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.ok = False


def validate_polygon_basic(points: list[Point], zero_length_tol: float = 1e-9) -> ValidationResult:
    """Validacoes genericas: sem pontos coincidentes consecutivos, sem segmentos de comprimento zero."""
    result = ValidationResult(ok=True)

    if len(points) < 3:
        result.add_error(f"poligono com menos de 3 vertices ({len(points)})")
        return result

    duplicates = geometry.has_consecutive_duplicates(points, tol=zero_length_tol)
    if duplicates:
        result.add_error(f"pontos consecutivos coincidentes nos indices {duplicates}")
    else:
        result.add_pass("sem pontos consecutivos coincidentes")

    lengths = geometry.segment_lengths(points, closed=True)
    zero_length = [i for i, length in enumerate(lengths) if length <= zero_length_tol]
    if zero_length:
        result.add_error(f"segmentos de comprimento zero nos indices {zero_length}")
    else:
        result.add_pass("sem segmentos de comprimento zero")

    if geometry.is_probably_scaled_by_001(points):
        result.add_warning(
            "bounding box menor que 0.05 m na maior dimensao - possivel erro de escala/unidade"
        )

    return result


def validate_la26_section(
    points: list[Point],
    expected_width: float = 1.25,
    expected_height: float = 0.265,
    tol_width: float = 0.01,
    tol_height: float = 0.01,
    expected_notches: int = 5,
    max_diagonal_ratio: float = 3.0,
    axis_angle_tol_deg: float = 2.0,
    min_diagonal_bbox_fraction: float = 0.1,
) -> ValidationResult:
    """Validacoes especificas para a secao alveolar LA26.

    Um segmento e tratado como "diagonal grande" apenas se: (a) for MAIOR
    que max_diagonal_ratio vezes a mediana dos comprimentos, (b) for maior
    que min_diagonal_bbox_fraction da maior dimensao da bbox, E (c) NAO
    estiver alinhado a um eixo (0/90/180/270 graus, +/- axis_angle_tol_deg).
    O criterio (b) evita falsos positivos em DXFs com arcos discretizados
    em muitos segmentos curtos (onde a transicao arco/reta pode ter poucos
    graus de desvio de eixo mas comprimento irrelevante); o criterio (a)+(c)
    evita falsos positivos nas bordas retas longas (topo/fundo da secao),
    que sao legitimas, e captura o caso real de uma reta espuria fechando
    o poligono na diagonal (ex.: ligando o fundo de um recorte lateral
    direto ao canto oposto, pulando o retorno simetrico esperado).
    """
    result = validate_polygon_basic(points)

    min_x, min_y, max_x, max_y = geometry.bbox(points)
    width = max_x - min_x
    height = max_y - min_y

    if abs(width - expected_width) <= tol_width:
        result.add_pass(f"largura {width:.4f} m dentro da tolerancia de {expected_width} m")
    else:
        result.add_error(
            f"largura {width:.4f} m fora da tolerancia (esperado {expected_width} +/- {tol_width} m)"
        )

    if abs(height - expected_height) <= tol_height:
        result.add_pass(f"altura {height:.4f} m dentro da tolerancia de {expected_height} m")
    else:
        result.add_error(
            f"altura {height:.4f} m fora da tolerancia (esperado {expected_height} +/- {tol_height} m)"
        )

    n = len(points)
    lengths = geometry.segment_lengths(points, closed=True)
    if lengths:
        sorted_lengths = sorted(lengths)
        mid = len(sorted_lengths) // 2
        median = (
            sorted_lengths[mid]
            if len(sorted_lengths) % 2
            else (sorted_lengths[mid - 1] + sorted_lengths[mid]) / 2
        )
        threshold = median * max_diagonal_ratio if median > 0 else float("inf")
        min_absolute_length = max(width, height) * min_diagonal_bbox_fraction

        big_diagonals = []
        for i, length in enumerate(lengths):
            if length <= threshold or length <= min_absolute_length:
                continue
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % n]
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180
            axis_deviation = min(angle, abs(angle - 90), abs(angle - 180))
            if axis_deviation > axis_angle_tol_deg:
                big_diagonals.append(i)

        if big_diagonals:
            result.add_error(
                f"possivel diagonal grande conectando pontos distantes nos indices {big_diagonals} "
                f"(nao alinhada a eixo, limiar de comprimento {threshold:.4f} m, mediana {median:.4f} m)"
            )
        else:
            result.add_pass("sem diagonais grandes conectando alveolos")

    notch_count = _estimate_notch_count(points)
    if notch_count == expected_notches:
        result.add_pass(f"{notch_count} recortes/alveolos detectados, conforme esperado")
    else:
        result.add_warning(
            f"{notch_count} recortes/alveolos detectados, esperado {expected_notches} "
            "(heuristica de contagem, revisar visualmente se divergente)"
        )

    return result


def _estimate_notch_count(points: list[Point]) -> int:
    """Heuristica: conta quantas vezes a coordenada Y minima local da secao e revisitada
    na borda inferior, como proxy do numero de recortes/alveolos.
    """
    min_x, min_y, max_x, max_y = geometry.bbox(points)
    tol = (max_y - min_y) * 0.02 if max_y > min_y else 1e-6
    near_bottom = [i for i, (_, y) in enumerate(points) if y - min_y <= tol]

    if not near_bottom:
        return 0

    groups = 1
    for a, b in zip(near_bottom, near_bottom[1:]):
        if b - a > 1:
            groups += 1
    return groups
