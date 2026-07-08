#!/usr/bin/env python3
"""Gera variantes simplificadas (poligono regular de 20 lados) dos alveolos da LA25,
para maximizar compatibilidade com VPRO e com REGION/SUBTRACT/MASSPROP no AutoCAD.

Reaproveita a mesma fonte geometrica ja validada (`section/json/LA25.json`, saida de
`dwgread -O JSON`) e a mesma infraestrutura de escrita/validacao R12 de
`scripts/process_vpro_dxf.py` (importado como modulo - mesmo diretorio, mesmo padrao
usado em `scripts/libredwg_tools.py`). Nao reescreve DXF moderno, nao usa bulge em
nenhum lugar: cada alveolo circular do desenho original e substituido por um poligono
regular de 20 lados (reto), aproximando a mesma geometria ja validada anteriormente
(mesmo centro vertical, mesmos centros horizontais nominais, mesmo raio nominal).

Gera 3 arquivos DXF R12/AC1009:
  - LA25_region_r12_20gon.dxf: 6 POLYLINE fechadas independentes (1 contorno externo
    CCW + 5 furos CW), para REGION/SUBTRACT/MASSPROP no AutoCAD.
  - LA25_vpro_slots_r12_20gon_2mm.dxf / _5mm.dxf: 1 unica POLYLINE fechada, com os 5
    alveolos conectados a face inferior por fendas finas (slot_width = 2mm / 5mm),
    candidatos simplificados para importar no VPRO.

Nao sobrescreve nenhum arquivo das rodadas anteriores (LA25.dxf, LA25_vpro.dxf,
LA25_vpro_r12_polyline*.dxf, LA25_vpro_r12_lines_lowres.dxf) - todos os nomes de saida
sao novos.
"""

from __future__ import annotations

import logging
import math
import sys
from collections import Counter
from pathlib import Path

import ezdxf
import shapely.geometry as shp
from ezdxf.math import bulge_to_arc

sys.path.insert(0, str(Path(__file__).resolve().parent))
from section_pipeline import geometry
from section_pipeline import io as sp_io
from section_pipeline.libredwg import dxf_to_dwg, dwg_to_json

import process_vpro_dxf as vpro  # reaproveita inject_r12_insunits, validate_json_file,
# _load_dwgread_json_lenient (tolerante ao "-nan" do dwgread para R12), dedup_consecutive

logger = logging.getLogger("generate_la25_20gon_variants")

Point = tuple[float, float]

INPUT_JSON = Path("section/json/LA25.json")
DXF_DIR = Path("section/DXF")
REPORTS_DIR = Path("section/reports")
PREVIEW_DIR = Path("section/preview")

# Parametros nominais dados pela tarefa (nao inventar nova escala - reusar o que ja foi
# validado para a LA25: bbox ~1.25 x 0.2502 m, 5 alveolos).
ALVEOLO_CENTERS_X = [-0.4625, -0.23125, 0.0, 0.23125, 0.4625]
ALVEOLO_RADIUS = 0.0980
NGON_SIDES = 20
LAYER = "SECTION"

CLOSING_DUP_TOL = 1e-4
EXCURSION_Y_TOL = 0.01
CIRCLE_BULGE_THRESHOLD = 50.0


# --------------------------------------------------------------------------------------
# 1. Leitura da fonte + extracao do contorno externo (sem alveolos) e dos centros reais
# --------------------------------------------------------------------------------------


def load_raw_la25(input_json: Path = INPUT_JSON) -> tuple[list[Point], list[float]]:
    """Le a LWPOLYLINE principal da LA25 (pontos+bulges brutos, coordenadas absolutas do
    DWG). Remove o ultimo ponto se for uma duplicata do primeiro (fechamento redundante
    ja presente na fonte, independente da flag 'closed')."""
    data = sp_io.load_json(input_json)
    lwp = sp_io.extract_lwpolylines(data)[0]
    points = [(float(p[0]), float(p[1])) for p in lwp["points"]]
    bulges = [float(b) for b in lwp.get("bulges", [])]
    if len(points) > 1:
        x0, y0 = points[0]
        x1, y1 = points[-1]
        if math.hypot(x1 - x0, y1 - y0) < CLOSING_DUP_TOL:
            points = points[:-1]
            bulges = bulges[:-1]
    return points, bulges


def find_circle_segments(bulges: list[float], threshold: float = CIRCLE_BULGE_THRESHOLD) -> list[int]:
    """Indices k onde o segmento points[k]->points[k+1] tem bulge >> 1: e a assinatura de
    um arco de quase 360 graus usada no desenho original para tracar cada alveolo circular
    (chord quase nula, bulge enorme). Ha exatamente 5 (um por alveolo)."""
    return [k for k, b in enumerate(bulges) if abs(b) > threshold]


def extract_outer_contour_and_excursions(
    points: list[Point], bulges: list[float], y_tol: float = EXCURSION_Y_TOL
) -> tuple[list[Point], list[tuple[int, int]], list[tuple[float, float, float]]]:
    """Separa o contorno externo (topo + detalhes de canto + base plana) dos desvios que
    entram em cada alveolo (sobe pelo canal -> arco quase-360 -> desce pelo canal).

    Deteccao: cada arco-circulo (find_circle_segments) fica "elevado" (y bem acima do
    y minimo global) junto com o canal de acesso que o liga a face inferior; andando
    para tras/frente a partir do arco ate encontrar pontos com y ~ y_min, encontramos os
    dois pontos de fixacao do canal na face inferior (que sao mantidos - a base fica
    praticamente reta entre eles) e todo o interior (canal+arco) e removido.

    Retorna (contorno_externo, lista_de_desvios, lista_de_centros_abs) onde cada desvio e
    (indice_antes, indice_depois) no array `points` original (sem o fechamento duplicado),
    e cada centro e (cx, cy, raio) em coordenadas absolutas do DWG, calculado com
    `ezdxf.math.bulge_to_arc` a partir do proprio arco da fonte (nao estimado).
    """
    n = len(points)
    circle_ks = find_circle_segments(bulges)
    y_min = min(p[1] for p in points)

    excursions: list[tuple[int, int]] = []
    centers: list[tuple[float, float, float]] = []
    remove: set[int] = set()

    for k in circle_ks:
        i = k
        while points[i % n][1] > y_min + y_tol:
            i -= 1
        before = i % n
        j = (k + 1) % n
        while points[j][1] > y_min + y_tol:
            j = (j + 1) % n
        after = j

        idx = (before + 1) % n
        while idx != after:
            remove.add(idx)
            idx = (idx + 1) % n

        excursions.append((before, after))
        center, _sa, _ea, radius = bulge_to_arc(points[k], points[(k + 1) % n], bulges[k])
        centers.append((center.x, center.y, radius))

    outer = [p for i, p in enumerate(points) if i not in remove]
    return outer, excursions, centers


# --------------------------------------------------------------------------------------
# 2. Transformacao para coordenadas locais (sem escala) e construcao dos poligonos
# --------------------------------------------------------------------------------------


def compute_local_transform(outer_points: list[Point]) -> tuple[float, float]:
    """(mid_x, y_min) do contorno externo - mesma convencao ja usada em
    scripts/process_vpro_dxf.py: x_local = x - mid_x, y_local = y - y_min. So translacao,
    nenhuma escala."""
    min_x, min_y, max_x, max_y = geometry.bbox(outer_points)
    return (min_x + max_x) / 2.0, min_y


def to_local(points: list[Point], mid_x: float, y_min: float) -> list[Point]:
    return [(x - mid_x, y - y_min) for x, y in points]


def ensure_orientation(points: list[Point], want_ccw: bool) -> list[Point]:
    area = geometry.polygon_area(points)
    is_ccw = area > 0
    if is_ccw == want_ccw:
        return points
    return list(reversed(points))


def make_ngon_hole(cx: float, cy: float, radius: float, sides: int = NGON_SIDES) -> list[Point]:
    """Poligono regular de `sides` lados, com um vertice exatamente no ponto mais baixo
    (start_angle_deg=-90), orientado horario (furo)."""
    pts = geometry.make_circle_points(
        cx, cy, radius, segments=sides, clockwise=True, start_angle_deg=-90.0
    )
    return ensure_orientation(pts, want_ccw=False)


def make_slot_detour(
    cx: float, y_c: float, radius: float, slot_width: float, sides: int = NGON_SIDES
) -> list[Point]:
    """Fenda fina (largura slot_width) ligando a face inferior (y=0) a um poligono
    regular de `sides` lados centrado em (cx, y_c). Mesma tecnica do desenho original
    (canal ida-e-volta quase coincidente), so que com largura controlada e sem bulge."""
    half = slot_width / 2.0
    # sentido OPOSTO ao do contorno bruto (que sai da fonte em sentido horario, ver
    # extract_outer_contour_and_excursions) - dentro de um caminho unico so-com-fenda,
    # o "furo" precisa girar ao contrario do contorno externo para a area se subtrair
    # corretamente (mesma regra de CCW-externo/CW-furo, so que dentro do mesmo caminho).
    ngon = geometry.make_circle_points(
        cx, y_c, radius, segments=sides, clockwise=False, start_angle_deg=-90.0
    )
    bottom_vertex = ngon[0]
    # ngon[0] e o vertice mais baixo; ngon[1] sai para a DIREITA (CCW a partir de -90 graus)
    # e ngon[-1] chega pela ESQUERDA. O contorno bruto percorre a base em x decrescente
    # (da direita para a esquerda), entao a parede de entrada (lado de x maior) deve ligar
    # em ngon[0]/ngon[1] e a de saida (lado de x menor) em ngon[-1] - senao a aresta de
    # fechamento do poligono cruzaria as paredes da fenda (auto-intersecao).
    return (
        [(cx + half, 0.0), (cx + half, bottom_vertex[1])]
        + ngon
        + [(cx - half, bottom_vertex[1]), (cx - half, 0.0)]
    )


def build_region_loops(input_json: Path = INPUT_JSON) -> dict:
    """Contorno externo (CCW) + 5 furos 20-gon (CW), em coordenadas locais. Tambem
    devolve dados auxiliares (centros computados vs nominais, y_c) para o relatorio."""
    points, bulges = load_raw_la25(input_json)
    outer_abs, excursions, centers_abs = extract_outer_contour_and_excursions(points, bulges)

    mid_x, y_min = compute_local_transform(outer_abs)
    outer_local = to_local(outer_abs, mid_x, y_min)
    outer_local = ensure_orientation(outer_local, want_ccw=True)

    centers_local_computed = sorted((cx - mid_x, cy - y_min, r) for cx, cy, r in centers_abs)
    y_c = sum(c[1] for c in centers_local_computed) / len(centers_local_computed)

    holes = [make_ngon_hole(cx, y_c, ALVEOLO_RADIUS) for cx in ALVEOLO_CENTERS_X]

    return {
        "outer_local": outer_local,
        "holes": holes,
        "y_c": y_c,
        "mid_x": mid_x,
        "y_min": y_min,
        "centers_local_computed": centers_local_computed,
        "points_raw": points,
        "bulges_raw": bulges,
        "excursions": excursions,
    }


def build_slots_path(region_data: dict, slot_width: float) -> list[Point]:
    """Constroi o caminho unico (contorno + 5 fendas+20-gon) reaproveitando o MESMO
    contorno externo e os MESMOS indices de desvio ja calculados para o arquivo region -
    so insere a fenda no lugar de cada excursao circular original."""
    points_raw = region_data["points_raw"]
    excursions = region_data["excursions"]
    mid_x, y_min = region_data["mid_x"], region_data["y_min"]
    y_c = region_data["y_c"]
    n = len(points_raw)

    points_local_all = to_local(points_raw, mid_x, y_min)

    excursions_sorted = sorted(excursions, key=lambda pair: points_local_all[pair[0]][0])
    before_to_detour = {
        before: (after, cx)
        for (before, after), cx in zip(excursions_sorted, ALVEOLO_CENTERS_X)
    }

    # Remove o desvio ORIGINAL inteiro (before, interior E after) - o "before"/"after" da
    # fonte marcam o canal antigo, de largura ~1mm nao controlada; o novo detour (slot_width
    # exato) substitui tudo isso, senao os dois canais (antigo residual + novo) ficam quase
    # coincidentes na base e se cruzam (self-intersection).
    remove_all: set[int] = set()
    for before, after in excursions:
        remove_all.add(before)
        remove_all.add(after)
        idx = (before + 1) % n
        while idx != after:
            remove_all.add(idx)
            idx = (idx + 1) % n

    result: list[Point] = []
    for i in range(n):
        if i in before_to_detour:
            _after, cx = before_to_detour[i]
            result.extend(make_slot_detour(cx, y_c, ALVEOLO_RADIUS, slot_width))
            continue
        if i in remove_all:
            continue
        result.append(points_local_all[i])

    result = vpro.dedup_consecutive(result)
    return ensure_orientation(result, want_ccw=True)


# --------------------------------------------------------------------------------------
# 3. Escrita do DXF R12 (reaproveita o padrao de process_vpro_dxf.py)
# --------------------------------------------------------------------------------------


def build_r12_multi_polyline_document(loops: list[list[Point]], layer: str = LAYER) -> "ezdxf.document.Drawing":
    doc = ezdxf.new("R12")
    if layer not in doc.layers:
        doc.layers.add(layer)
    msp = doc.modelspace()
    for loop in loops:
        msp.add_polyline2d(loop, close=True, dxfattribs={"layer": layer})
    return doc


def write_r12_dxf(loops: list[list[Point]], output_dxf: Path) -> None:
    output_dxf.parent.mkdir(parents=True, exist_ok=True)
    doc = build_r12_multi_polyline_document(loops)
    doc.saveas(str(output_dxf))
    vpro.inject_r12_insunits(output_dxf, insunits=6)


# --------------------------------------------------------------------------------------
# 4. Validacao: ezdxf (estrutura) + LibreDWG (round-trip) + shapely (geometria)
# --------------------------------------------------------------------------------------


def validate_structure_ezdxf(dxf_path: Path, expected_polyline_count: int) -> dict:
    result: dict = {"ok": True, "messages": []}
    doc = ezdxf.readfile(dxf_path)
    result["dxfversion"] = doc.dxfversion
    if doc.dxfversion != "AC1009":
        result["ok"] = False
        result["messages"].append(f"versao inesperada: {doc.dxfversion}")

    msp = doc.modelspace()
    counts = Counter(e.dxftype() for e in msp)
    result["entity_counts"] = dict(counts)

    for forbidden in ("LWPOLYLINE", "CIRCLE", "ARC", "SPLINE", "LINE"):
        if counts.get(forbidden, 0) > 0:
            result["ok"] = False
            result["messages"].append(f"entidade proibida presente: {forbidden} ({counts[forbidden]}x)")

    polylines = [e for e in msp if e.dxftype() == "POLYLINE"]
    result["polyline_count"] = len(polylines)
    if len(polylines) != expected_polyline_count:
        result["ok"] = False
        result["messages"].append(
            f"esperado {expected_polyline_count} POLYLINE, encontrado {len(polylines)}"
        )

    loops = []
    closed_flags = []
    for p in polylines:
        closed_flags.append(bool(p.is_closed))
        loops.append([(v.dxf.location.x, v.dxf.location.y) for v in p.vertices])
    result["closed_flags"] = closed_flags
    if not all(closed_flags):
        result["ok"] = False
        result["messages"].append(f"nem todas as POLYLINE estao fechadas: {closed_flags}")

    all_points = [pt for loop in loops for pt in loop]
    result["bbox"] = geometry.bbox(all_points) if all_points else None
    result["loops"] = loops
    return result


def roundtrip_validate_multi(dxf_path: Path, reports_dir: Path, stem: str, expected_polyline_count: int) -> dict:
    """dxf2dwg + dwgread -O JSON + jq empty, artefatos persistidos (mesmo padrao usado
    para o perfil r12-polyline em process_vpro_dxf.py, generalizado para N POLYLINE)."""
    report: dict = {"ok": True, "commands": [], "messages": []}
    roundtrip_dwg = reports_dir / f"{stem}_roundtrip.dwg"
    roundtrip_json = reports_dir / f"{stem}_roundtrip.json"

    try:
        dxf_to_dwg(dxf_path, roundtrip_dwg, reports_dir, overwrite=True)
        report["commands"].append(f"dxf2dwg -y -o {roundtrip_dwg} {dxf_path}")
    except Exception as exc:  # noqa: BLE001
        report["ok"] = False
        report["messages"].append(f"dxf2dwg falhou: {exc}")
        return report

    try:
        dwg_to_json(roundtrip_dwg, roundtrip_json, reports_dir)
        report["commands"].append(f"dwgread -O JSON -o {roundtrip_json} {roundtrip_dwg}")
    except Exception as exc:  # noqa: BLE001
        report["messages"].append(
            f"dwgread -O JSON reportou 'ERROR: iconv' (limitacao conhecida do LibreDWG "
            f"para JSON de origem R12, ver process_vpro_dxf.roundtrip_validate_r12): {exc}"
        )
        report["commands"].append(f"dwgread -O JSON -o {roundtrip_json} {roundtrip_dwg}")

    if not roundtrip_json.exists():
        report["ok"] = False
        report["messages"].append(f"{roundtrip_json} nao foi gerado")
        return report

    jq_ok, jq_message = vpro.validate_json_file(roundtrip_json)
    report["commands"].append(f"jq empty {roundtrip_json}")
    report["messages"].append(f"jq empty / json.load: {'OK' if jq_ok else 'FALHOU'} - {jq_message}")
    report["ok"] = report["ok"] and jq_ok
    if not jq_ok:
        return report

    try:
        data = vpro._load_dwgread_json_lenient(roundtrip_json)
    except Exception as exc:  # noqa: BLE001
        report["ok"] = False
        report["messages"].append(f"nao foi possivel inspecionar o JSON do round-trip: {exc}")
        return report

    entities = sp_io.extract_entities(data)
    counts: dict[str, int] = {}
    for e in entities:
        kind = str(e.get("entity", "?")).upper()
        counts[kind] = counts.get(kind, 0) + 1
    report["entity_counts"] = counts

    polylines = [e for e in entities if str(e.get("entity", "")).upper() in ("POLYLINE", "POLYLINE_2D")]
    report["polyline_count"] = len(polylines)
    if len(polylines) != expected_polyline_count:
        report["ok"] = False
        report["messages"].append(
            f"esperado {expected_polyline_count} POLYLINE/POLYLINE_2D, encontrado {len(polylines)}"
        )
    for residual in ("LWPOLYLINE", "LINE", "ARC", "CIRCLE"):
        if counts.get(residual, 0) > 0:
            report["ok"] = False
            report["messages"].append(f"entidade residual {residual} encontrada ({counts[residual]}x)")

    closed_flags = []
    for p in polylines:
        flag = p.get("flag", 0)
        closed_flags.append(isinstance(flag, int) and bool(flag & 1))
    report["closed_flags"] = closed_flags
    if not all(closed_flags):
        report["ok"] = False
        report["messages"].append(f"nem todas fechadas no round-trip: {closed_flags}")

    seqend_count = counts.get("SEQEND", 0)
    vertex_count = counts.get("VERTEX_2D", 0) + counts.get("VERTEX", 0)
    report["seqend_count"] = seqend_count
    report["vertex_count"] = vertex_count
    if seqend_count != expected_polyline_count:
        report["ok"] = False
        report["messages"].append(f"esperado {expected_polyline_count} SEQEND, encontrado {seqend_count}")

    return report


# --------------------------------------------------------------------------------------
# 5. Propriedades geometricas (shapely + section_pipeline.geometry) e comparacao ideal
# --------------------------------------------------------------------------------------


def ideal_circle_loops(y_c: float, radius: float = ALVEOLO_RADIUS, segments: int = 400) -> list[Point]:
    """Furo circular 'quase perfeito' (alta resolucao) para comparacao - nao e escrito em
    nenhum DXF, so usado para calcular a propriedade de secao de referencia."""
    return geometry.make_circle_points(0.0, y_c, radius, segments=segments, clockwise=True, start_angle_deg=-90.0)


def relative_error(approx: float, ideal: float) -> float:
    if abs(ideal) < 1e-15:
        return 0.0
    return (approx - ideal) / ideal


def compare_to_ideal_circles(outer_local: list[Point], holes_20gon: list[list[Point]], y_c: float) -> dict:
    ideal_holes = [
        [(x + cx, y) for x, y in ideal_circle_loops(y_c)] for cx in ALVEOLO_CENTERS_X
    ]
    props_20gon = geometry.composite_section_properties([outer_local] + holes_20gon)
    props_ideal = geometry.composite_section_properties([outer_local] + ideal_holes)
    return {
        "props_20gon": props_20gon,
        "props_ideal": props_ideal,
        "area_rel_error": relative_error(props_20gon["area"], props_ideal["area"]),
        "ix_rel_error": relative_error(props_20gon["ix"], props_ideal["ix"]),
        "iy_rel_error": relative_error(props_20gon["iy"], props_ideal["iy"]),
    }


def shapely_check_region(outer_local: list[Point], holes: list[list[Point]]) -> dict:
    poly = shp.Polygon(outer_local, holes)
    return {
        "is_valid": poly.is_valid,
        "area": poly.area,
        "centroid": (poly.centroid.x, poly.centroid.y),
    }


def shapely_check_single_ring(points_local: list[Point]) -> dict:
    poly = shp.Polygon(points_local)
    return {
        "is_valid": poly.is_valid,
        "is_simple": shp.LinearRing(points_local).is_simple,
        "area": poly.area,
        "centroid": (poly.centroid.x, poly.centroid.y) if poly.is_valid else None,
    }


# --------------------------------------------------------------------------------------
# 6. Preview e relatorios
# --------------------------------------------------------------------------------------


def write_preview_multi(loops: list[list[Point]], preview_path: Path, title: str) -> str | None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return "matplotlib nao instalado - preview nao gerado"

    fig, ax = plt.subplots(figsize=(10, 4))
    for loop in loops:
        closed = loop + [loop[0]]
        xs, ys = zip(*closed)
        ax.plot(xs, ys, "-", linewidth=1)
    ax.set_aspect("equal")
    ax.set_title(title)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(preview_path, dpi=150)
    plt.close(fig)
    return None


def basic_geometry_checks(points: list[Point]) -> list[str]:
    from section_pipeline import validation as sv

    result = sv.validate_polygon_basic(points)
    lines = [f"  - {c}" for c in result.checks]
    lines += [f"  - AVISO: {w}" for w in result.warnings]
    lines += [f"  - ERRO: {e}" for e in result.errors]
    return lines


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    for d in (DXF_DIR, REPORTS_DIR, PREVIEW_DIR):
        d.mkdir(parents=True, exist_ok=True)

    all_ok = True

    # ------------------------------------------------------------------ region (6 loops)
    region = build_region_loops()
    outer_local = region["outer_local"]
    holes = region["holes"]
    region_dxf = DXF_DIR / "LA25_region_r12_20gon.dxf"
    write_r12_dxf([outer_local] + holes, region_dxf)
    logger.info("escrito %s", region_dxf)

    ez_region = validate_structure_ezdxf(region_dxf, expected_polyline_count=6)
    rt_region = roundtrip_validate_multi(region_dxf, REPORTS_DIR, region_dxf.stem, expected_polyline_count=6)
    shp_region = shapely_check_region(outer_local, holes)
    cmp_region = compare_to_ideal_circles(outer_local, holes, region["y_c"])
    ok_region = ez_region["ok"] and rt_region["ok"] and shp_region["is_valid"]
    all_ok = all_ok and ok_region

    preview_msg_region = write_preview_multi(
        [outer_local] + holes, PREVIEW_DIR / "LA25_region_r12_20gon.png", "LA25_region_r12_20gon"
    )

    write_region_report(region, ez_region, rt_region, shp_region, cmp_region, ok_region, preview_msg_region)

    # ------------------------------------------------------------------ slots (2mm, 5mm)
    slot_results = {}
    for slot_width, suffix in ((0.002, "2mm"), (0.005, "5mm")):
        path_local = build_slots_path(region, slot_width)
        out_dxf = DXF_DIR / f"LA25_vpro_slots_r12_20gon_{suffix}.dxf"
        write_r12_dxf([path_local], out_dxf)
        logger.info("escrito %s", out_dxf)

        ez = validate_structure_ezdxf(out_dxf, expected_polyline_count=1)
        rt = roundtrip_validate_multi(out_dxf, REPORTS_DIR, out_dxf.stem, expected_polyline_count=1)
        shp_check = shapely_check_single_ring(path_local)
        basic = basic_geometry_checks(path_local)
        ok_slot = ez["ok"] and rt["ok"] and shp_check["is_valid"] and shp_check["is_simple"]
        all_ok = all_ok and ok_slot

        preview_msg = write_preview_multi(
            [path_local], PREVIEW_DIR / f"LA25_vpro_slots_r12_20gon_{suffix}.png", out_dxf.stem
        )

        write_slots_report(
            suffix, slot_width, path_local, out_dxf, ez, rt, shp_check, basic, shp_region["area"], ok_slot, preview_msg
        )
        slot_results[suffix] = {
            "ok": ok_slot,
            "area": shp_check["area"],
            "n_points": len(path_local),
        }

    write_summary_report(region, cmp_region, ok_region, slot_results, shp_region["area"])
    write_manual_test_report()

    return 0 if all_ok else 1


def write_region_report(region, ez, rt, shp_check, cmp, ok, preview_msg) -> None:
    lines = [
        "# Relatorio - LA25_region_r12_20gon.dxf",
        "",
        f"Fonte: `{INPUT_JSON}`",
        "Saida: `section/DXF/LA25_region_r12_20gon.dxf`",
        "Finalidade: REGION / SUBTRACT / MASSPROP no AutoCAD; referencia geometrica simples.",
        "",
        "## Geometria",
        "",
        f"- Centro vertical (y_c) usado (validado a partir do arco original): {region['y_c']:.6f} m",
        f"- Centros horizontais nominais usados: {ALVEOLO_CENTERS_X}",
        f"- Centros horizontais computados a partir da fonte (para conferencia): "
        f"{[(round(c[0], 5), round(c[1], 5)) for c in region['centers_local_computed']]}",
        f"- Raio nominal usado: {ALVEOLO_RADIUS} m (raio computado na fonte: "
        f"~{region['centers_local_computed'][0][2]:.4f} m - a tarefa pede o nominal, nao o exato)",
        f"- Poligono por alveolo: {NGON_SIDES} lados",
        f"- Numero de pontos do contorno externo: {len(region['outer_local'])}",
        f"- Numero de pontos por furo (20-gon): {NGON_SIDES}",
        "",
        "## Leitura estrutural com ezdxf",
        "",
        f"- Versao DXF: {ez.get('dxfversion')}",
        f"- Entidades: {ez.get('entity_counts')}",
        f"- POLYLINE: {ez.get('polyline_count')} (esperado 6)",
        f"- Fechadas: {ez.get('closed_flags')}",
        f"- Bounding box: {ez.get('bbox')}",
    ]
    lines += [f"  - ERRO: {m}" for m in ez["messages"]]

    lines += [
        "",
        "## Round-trip LibreDWG (dxf2dwg + dwgread -O JSON + jq empty)",
        "",
        f"- Comandos executados: {rt['commands']}",
        f"- Entidades no round-trip: {rt.get('entity_counts', {})}",
        f"- POLYLINE/POLYLINE_2D no round-trip: {rt.get('polyline_count')}",
        f"- Fechadas (round-trip): {rt.get('closed_flags')}",
        f"- SEQEND: {rt.get('seqend_count')}, VERTEX: {rt.get('vertex_count')}",
    ]
    lines += [f"  - {m}" for m in rt["messages"]]

    lines += [
        "",
        "## Shapely (Polygon com furos)",
        "",
        f"- Valido (is_valid): {shp_check['is_valid']}",
        f"- Area: {shp_check['area']:.6f} m^2",
        f"- Centroide: {shp_check['centroid']}",
        "",
        "## Comparacao com 5 furos circulares ideais (diametro 0.196 m)",
        "",
        f"- Area (20-gon): {cmp['props_20gon']['area']:.6f} m^2",
        f"- Area (circulo ideal): {cmp['props_ideal']['area']:.6f} m^2",
        f"- Erro relativo de area: {cmp['area_rel_error']*100:.4f}%",
        f"- Centroide (20-gon): {cmp['props_20gon']['centroid']}",
        f"- Centroide (circulo ideal): {cmp['props_ideal']['centroid']}",
        f"- Ix (20-gon): {cmp['props_20gon']['ix']:.8e} m^4",
        f"- Ix (circulo ideal): {cmp['props_ideal']['ix']:.8e} m^4",
        f"- Erro relativo de Ix: {cmp['ix_rel_error']*100:.4f}%",
        f"- Iy (20-gon): {cmp['props_20gon']['iy']:.8e} m^4",
        f"- Iy (circulo ideal): {cmp['props_ideal']['iy']:.8e} m^4",
        f"- Erro relativo de Iy: {cmp['iy_rel_error']*100:.4f}%",
        "",
    ]

    if preview_msg is None:
        lines.append("Preview gerado em `section/preview/LA25_region_r12_20gon.png`.")
    else:
        lines.append(f"Preview nao gerado: {preview_msg}")

    lines.append("")
    lines.append(f"**Resultado: {'estrutura OK' if ok else 'FALHOU'}**")
    lines.append("")

    sp_io.save_report(REPORTS_DIR / "LA25_region_r12_20gon_report.md", "\n".join(lines))


def write_slots_report(suffix, slot_width, points_local, out_dxf, ez, rt, shp_check, basic_lines, region_area, ok, preview_msg) -> None:
    area_loss = region_area - shp_check["area"] if shp_check.get("area") is not None else None
    area_loss_pct = (area_loss / region_area * 100.0) if area_loss is not None and region_area else None

    lines = [
        f"# Relatorio - LA25_vpro_slots_r12_20gon_{suffix}.dxf",
        "",
        f"Fonte: `{INPUT_JSON}`",
        f"Saida: `{out_dxf}`",
        f"slot_width: {slot_width} m ({suffix})",
        "Finalidade: candidato simplificado (sem circulo/bulge) para importar no VPRO.",
        "",
        f"- Numero de pontos (apos limpeza de duplicatas): {len(points_local)}",
        "",
        "## Validacao geometrica basica (local)",
        "",
    ]
    lines += basic_lines
    lines += [
        "",
        "## Leitura estrutural com ezdxf",
        "",
        f"- Versao DXF: {ez.get('dxfversion')}",
        f"- Entidades: {ez.get('entity_counts')}",
        f"- POLYLINE: {ez.get('polyline_count')} (esperado 1)",
        f"- Fechada: {ez.get('closed_flags')}",
        f"- Bounding box: {ez.get('bbox')}",
    ]
    lines += [f"  - ERRO: {m}" for m in ez["messages"]]

    lines += [
        "",
        "## Round-trip LibreDWG (dxf2dwg + dwgread -O JSON + jq empty)",
        "",
        f"- Comandos executados: {rt['commands']}",
        f"- Entidades no round-trip: {rt.get('entity_counts', {})}",
        f"- POLYLINE/POLYLINE_2D no round-trip: {rt.get('polyline_count')} (esperado 1)",
        f"- Fechada (round-trip): {rt.get('closed_flags')}",
        f"- SEQEND: {rt.get('seqend_count')}, VERTEX: {rt.get('vertex_count')}",
    ]
    lines += [f"  - {m}" for m in rt["messages"]]

    lines += [
        "",
        "## Shapely (poligono simples, anel unico)",
        "",
        f"- Valido (is_valid): {shp_check['is_valid']}",
        f"- Simples / sem auto-intersecao (is_simple): {shp_check['is_simple']}",
        f"- Area: {shp_check['area']:.6f} m^2",
        f"- Centroide: {shp_check['centroid']}",
        "",
        "## Perda de area causada pelas fendas (comparado a LA25_region_r12_20gon.dxf)",
        "",
        f"- Area region (contorno - 5 furos 20-gon, sem fendas): {region_area:.6f} m^2",
        f"- Area {suffix} (contorno com fendas conectando os furos): {shp_check['area']:.6f} m^2",
    ]
    if area_loss is not None:
        lines.append(f"- Perda de area por causa das fendas: {area_loss:.6f} m^2 ({area_loss_pct:.4f}%)")

    if preview_msg is None:
        lines.append("")
        lines.append(f"Preview gerado em `section/preview/LA25_vpro_slots_r12_20gon_{suffix}.png`.")
    else:
        lines.append("")
        lines.append(f"Preview nao gerado: {preview_msg}")

    lines.append("")
    lines.append(
        f"**Resultado: {'estrutura OK' if ok else 'FALHOU'} - VPRO legacy candidate "
        "(NAO declarar VPRO-safe; validar importando no VPRO antes de confiar neste arquivo)**"
    )
    lines.append("")

    sp_io.save_report(REPORTS_DIR / f"LA25_vpro_slots_r12_20gon_{suffix}_report.md", "\n".join(lines))


def write_summary_report(region, cmp, ok_region, slot_results, region_area) -> None:
    lines = [
        "# Resumo - variantes 20-gon da LA25",
        "",
        "## Qual arquivo usar para o que",
        "",
        "- **CAD / REGION / SUBTRACT / MASSPROP**: `section/DXF/LA25_region_r12_20gon.dxf` "
        "(6 POLYLINE fechadas independentes: 1 contorno externo CCW + 5 furos 20-gon CW).",
        "- **Teste de importacao no VPRO**: `section/DXF/LA25_vpro_slots_r12_20gon_5mm.dxf` "
        "e `section/DXF/LA25_vpro_slots_r12_20gon_2mm.dxf` (1 unica POLYLINE fechada, "
        "furos conectados a face inferior por fendas finas).",
        "",
        "## Erro da aproximacao 20-gon vs furos circulares ideais (diametro 0.196 m)",
        "",
        f"- Erro relativo de area: {cmp['area_rel_error']*100:.4f}%",
        f"- Erro relativo de Ix: {cmp['ix_rel_error']*100:.4f}%",
        f"- Erro relativo de Iy: {cmp['iy_rel_error']*100:.4f}%",
        "",
        f"- Area da secao (region, sem fendas): {region_area:.6f} m^2",
    ]
    for suffix in ("2mm", "5mm"):
        r = slot_results[suffix]
        lines.append(
            f"- Area da secao ({suffix}, com fendas): {r['area']:.6f} m^2 "
            f"({r['n_points']} pontos) - estrutura {'OK' if r['ok'] else 'FALHOU'}"
        )

    lines += [
        "",
        "## Recomendacao de ordem de teste no VPRO",
        "",
        "1. `LA25_region_r12_20gon.dxf` no AutoCAD primeiro (REGION+SUBTRACT+MASSPROP) - "
        "confirma que a geometria 20-gon esta correta antes de mexer com o VPRO.",
        "2. `LA25_vpro_slots_r12_20gon_5mm.dxf` no VPRO - fenda mais larga, maior chance "
        "de o importador aceitar sem problema numerico.",
        "3. `LA25_vpro_slots_r12_20gon_2mm.dxf` no VPRO - fenda mais estreita (mais fiel "
        "ao desenho original), testar depois de confirmar que a 5mm importa bem.",
        "",
        "Ver `section/reports/LA25_manual_test_20gon.md` para o passo a passo detalhado.",
        "",
        f"**Resultado geral: region {'OK' if ok_region else 'FALHOU'}, "
        f"slots 2mm {'OK' if slot_results['2mm']['ok'] else 'FALHOU'}, "
        f"slots 5mm {'OK' if slot_results['5mm']['ok'] else 'FALHOU'}**",
        "",
    ]
    sp_io.save_report(REPORTS_DIR / "LA25_20gon_summary.md", "\n".join(lines))


def write_manual_test_report() -> None:
    content = """# Teste manual recomendado - variantes 20-gon da LA25

## 1. AutoCAD (REGION / SUBTRACT / MASSPROP)

Arquivo: `section/DXF/LA25_region_r12_20gon.dxf`

1. Abrir o DXF no AutoCAD (ou compativel).
2. Selecionar as 6 POLYLINE (1 contorno externo + 5 furos) e rodar `REGION`.
3. Rodar `SUBTRACT`: selecionar a regiao do contorno externo como objeto-fonte, e as 5
   regioes dos furos como objetos a subtrair.
4. Rodar `MASSPROP` na regiao resultante e conferir:
   - Area: comparar com `section/reports/LA25_region_r12_20gon_report.md`
     (secao "Comparacao com 5 furos circulares ideais").
   - Centroide.
   - Momentos de inercia (Ix, Iy).

## 2. VPRO

Testar nesta ordem:

1. `section/DXF/LA25_vpro_slots_r12_20gon_5mm.dxf` (fenda mais larga, 5 mm).
2. `section/DXF/LA25_vpro_slots_r12_20gon_2mm.dxf` (fenda mais estreita, 2 mm).

Para cada um, observar:
- O VPRO consegue importar sem erro?
- A secao aparece com os 5 furos poligonais corretamente reconhecidos como vazios (nao
  como material)?
- Ha diferenca perceptivel de comportamento entre a fenda de 5 mm e a de 2 mm?

Reportar o resultado da comparacao 2mm vs 5mm para decidir qual largura de fenda usar
daqui para frente.

Nenhum destes arquivos deve ser chamado de "VPRO-safe" antes desse teste manual -
apenas "VPRO legacy candidate" (round-trip LibreDWG e leitura ezdxf OK, mas o VPRO em si
ainda nao foi testado).
"""
    sp_io.save_report(REPORTS_DIR / "LA25_manual_test_20gon.md", content)


if __name__ == "__main__":
    sys.exit(main())
