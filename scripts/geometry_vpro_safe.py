#!/usr/bin/env python3
"""Exporta a polilinha global VPRO-safe (caminhada continua) com validacao por grafo.

Fonte primaria: o JSON do LibreDWG (`dwgread -O JSON`, ex.: section/json/LA25.json).
A LWPOLYLINE principal ja descreve UMA caminhada continua pela borda externa,
incluindo o desvio por dentro de cada alveolo atraves de um canal estreito
("furinho") que liga o alveolo a borda. Esse canal e INTENCIONAL e obrigatorio:
o VPRO so aceita a secao se tudo for uma unica poligonal caminhavel - alveolos
NUNCA podem virar circulos/loops fechados independentes.

O que este script faz (e o que NAO faz):
  1. Reusa o pipeline geometrico de scripts/process_vpro_dxf.py (selecao da
     LWPOLYLINE principal, discretizacao de bulges NA ORDEM da entidade,
     dedup, recentralizacao sem escala).
  2. NAO reordena pontos por centroide/angulo/distancia (isso cria cordas).
     Apenas normaliza a caminhada existente: sentido horario consistente e
     inicio no vertice superior esquerdo (maior Y; empate por banda de
     tolerancia -> menor X).
  3. Constroi um grafo de arestas (section_pipeline.walk) a partir da
     caminhada original e VALIDA que a sequencia final percorre somente
     arestas reais (nenhum salto/corda), que existe exatamente 1 loop global
     fechado, que nao ha self-intersection e que o canal dos alveolos
     continua aberto (folga minima > 0).
  4. Escreve DXF R12 (POLYLINE/VERTEX/SEQEND fechada, via ezdxf - nunca por
     concatenacao de string) e valida com round-trip LibreDWG
     (dxf2dwg + dwgread -O JSON), reusando process_vpro_dxf.

Saidas:
  outputs/dxf/<secao>_vpro_safe_ordered.dxf   (+ copia em section/DXF/)
  outputs/previews/<secao>_order_check.png/.svg (+ copia PNG em section/preview/)
  outputs/<secao>_outer_ordered.json          ([{"i":1,"x":...,"y":...}, ...])
  section/reports/<secao>_vpro_safe_ordered_report.md (+ artefatos round-trip)

Uso:
  .venv/bin/python scripts/geometry_vpro_safe.py                # LA25 (padrao)
  .venv/bin/python scripts/geometry_vpro_safe.py --force        # sobrescreve
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for extra in (REPO_ROOT / "src", REPO_ROOT / "scripts"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from section_pipeline import geometry, simplify, walk  # noqa: E402
from section_pipeline import io as sp_io  # noqa: E402
from section_pipeline import validation  # noqa: E402
import process_vpro_dxf as pvd  # noqa: E402  (pipeline geometrico + writers + round-trip)

Point = tuple[float, float]

# Banda de empate para "maior Y" como fracao da altura da secao (ver
# geometry.rotate_to_start): pontos ate 0.1% da altura abaixo do Y maximo
# contam como "na face superior" e o desempate escolhe o menor X.
Y_TOL_FRACTION = 1e-3


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", default="section/json/LA25.json")
    parser.add_argument("--section-name", default="LA25")
    parser.add_argument("--outputs", default="outputs", help="pasta raiz das saidas pedidas")
    parser.add_argument("--reports", default="section/reports")
    parser.add_argument("--force", action="store_true", help="sobrescreve saidas existentes")
    parser.add_argument(
        "--simplify", action="store_true",
        help="gera a variante SIMPLIFICADA (rediscretiza arcos dos alveolos com "
        "--circle-points, validando area/inercia contra a polilinha densa)",
    )
    parser.add_argument(
        "--circle-points", type=int, default=32,
        help="pontos por circulo completo nos arcos dos alveolos (padrao 32); "
        f"escala automaticamente por {simplify.CIRCLE_POINTS_LADDER} ate passar",
    )
    parser.add_argument(
        "--max-area-error", type=float, default=0.001,
        help="erro relativo maximo de area aceito (padrao 0.001 = 0.1%%)",
    )
    parser.add_argument(
        "--max-inertia-error", type=float, default=0.002,
        help="erro relativo maximo de Ix e Iy aceito (padrao 0.002 = 0.2%%)",
    )
    parser.add_argument(
        "--max-vpro-points", type=int, default=None,
        help="limite rigido de pontos para compatibilidade VPro (padrao None = sem limite); "
        "reduz circle_points automaticamente (32→28→24→20→16) ate caber",
    )
    return parser.parse_args(argv)


def order_points_vpro_safe(points_local: list[Point]) -> tuple[list[Point], float]:
    """Aplica a normalizacao (horario + inicio superior esquerdo com banda de Y)."""
    min_x, min_y, max_x, max_y = geometry.bbox(points_local)
    y_tol = (max_y - min_y) * Y_TOL_FRACTION
    return geometry.make_vpro_safe_order(points_local, y_tol=y_tol), y_tol


def write_ordered_json(points: list[Point], json_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {"i": i + 1, "x": round(x, 9), "y": round(y, 9)} for i, (x, y) in enumerate(points)
    ]
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_order_check_previews(
    points: list[Point], png_path: Path, svg_path: Path, title: str
) -> str | None:
    """Preview do contorno EM ORDEM: linha, ponto inicial destacado e setas
    tangentes ao proprio caminho indicando o sentido - nenhuma linha para o
    centro ou entre pontos nao consecutivos."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return "matplotlib nao instalado - previews nao gerados"

    n = len(points)
    xs = [p[0] for p in points] + [points[0][0]]
    ys = [p[1] for p in points] + [points[0][1]]

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(xs, ys, "b-", linewidth=1.1, label="contorno (ordem de desenho)")

    # setas tangentes: amostra ~24 posicoes; a seta segue o segmento local real
    min_x, min_y, max_x, max_y = geometry.bbox(points)
    arrow_len = 0.03 * max(max_x - min_x, max_y - min_y)
    step = max(1, n // 24)
    ax_x, ax_y, ax_u, ax_v = [], [], [], []
    for i in range(0, n, step):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        seg = math.hypot(x2 - x1, y2 - y1)
        if seg < 1e-12:
            continue
        ax_x.append(x1)
        ax_y.append(y1)
        ax_u.append((x2 - x1) / seg * arrow_len)
        ax_v.append((y2 - y1) / seg * arrow_len)
    ax.quiver(
        ax_x, ax_y, ax_u, ax_v,
        angles="xy", scale_units="xy", scale=1,
        color="darkorange", width=0.0035, zorder=5, label="sentido da caminhada",
    )

    ax.plot(
        points[0][0], points[0][1], marker="*", markersize=16, color="green",
        markeredgecolor="darkgreen", zorder=6, linestyle="none", label="ponto inicial",
    )
    for i in range(min(3, n)):
        ax.annotate(
            str(i + 1), points[i], textcoords="offset points", xytext=(4, 6),
            fontsize=8, color="darkgreen",
        )

    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_title(title)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    fig.tight_layout()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=150)
    fig.savefig(svg_path)
    plt.close(fig)
    return None


def shapely_second_opinion(points: list[Point]) -> list[str]:
    """Checagem independente com shapely (somente leitura/validacao)."""
    try:
        from shapely.geometry import LinearRing, Polygon
    except ImportError:
        return ["shapely nao instalado - segunda opiniao pulada"]
    messages = []
    ring = LinearRing(points)
    poly = Polygon(points)
    messages.append(f"shapely LinearRing.is_simple = {ring.is_simple}")
    messages.append(f"shapely Polygon.is_valid = {poly.is_valid}")
    messages.append(f"shapely Polygon.area = {poly.area:.6f} m^2")
    return messages


def build_simplified_walk(
    geo_dense: dict, circle_points: int
) -> tuple[list[Point], set]:
    """Caminhada em baixa resolucao NO MESMO frame local do pipeline denso.

    Rediscretiza os arcos (bulges) da entidade fonte com `circle_points` por
    circulo completo e compensacao de raio (area do setor preservada), depois
    recentraliza usando EXATAMENTE os offsets do pipeline denso (mid_x/min_y
    da bbox expandida densa) para que as propriedades sejam comparaveis no
    mesmo sistema de coordenadas. Ancoras = vertices da entidade fonte.
    """
    expanded, anchor_idx = simplify.expand_polyline_lowres(
        geo_dense["raw_points"], geo_dense["raw_bulges"], circle_points, compensate=True
    )
    min_x, min_y, max_x, _max_y = geo_dense["expanded_bbox"]
    mid_x = (min_x + max_x) / 2.0
    local = [(x - mid_x, y - min_y) for x, y in expanded]
    anchors = {walk.node_key(local[i]) for i in anchor_idx}
    return pvd.dedup_consecutive(local), anchors


def find_best_circle_points_for_limit(
    geo_dense: dict, ordered_dense: list[Point], max_points: int,
    max_area_error: float = 0.005, max_inertia_error: float = 0.01,
) -> tuple[int, list[Point]] | tuple[None, None]:
    """Encontra o maior circle_points que produz total_pontos <= max_points,
    com erros de area/inercia dentro dos limites. Tenta 32, 28, 24, 20, 16.

    Retorna (circle_points_escolhido, pontos_simplificados) ou (None, None) se falhar.
    """
    ladder = (32, 28, 24, 20, 16)
    for cp in ladder:
        walk_pts, _ = build_simplified_walk(geo_dense, cp)
        ordered, _ = order_points_vpro_safe(walk_pts)
        if len(ordered) > max_points:
            continue
        props = validation.validate_section_properties(
            ordered_dense, ordered, max_area_error, max_inertia_error
        )
        if props["ok"]:
            return cp, ordered
    return None, None


def write_simplified_preview(points: list[Point], png_path: Path, title: str) -> str | None:
    """PNG da polilinha simplificada: contorno, 30 primeiros pontos numerados,
    ponto inicial destacado, titulo com o numero de pontos."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return "matplotlib nao instalado - imagem nao gerada"

    xs = [p[0] for p in points] + [points[0][0]]
    ys = [p[1] for p in points] + [points[0][1]]
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(xs, ys, "b-o", linewidth=1.0, markersize=2.5, label="polilinha simplificada")
    ax.plot(
        points[0][0], points[0][1], marker="*", markersize=16, color="green",
        markeredgecolor="darkgreen", linestyle="none", zorder=6, label="ponto inicial",
    )
    for i in range(min(30, len(points))):
        ax.annotate(
            str(i + 1), points[i], textcoords="offset points", xytext=(4, 5),
            fontsize=7, color="darkred",
        )
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_title(title)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    fig.tight_layout()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=150)
    plt.close(fig)
    return None


def run_simplified(args: argparse.Namespace) -> int:
    """Variante --simplify: reduz pontos com validacao por propriedades.

    Escala circle_points automaticamente (24 -> 32 -> 48 -> 64, a partir do
    valor pedido) ate os erros de area/inercia ficarem dentro dos limites.
    So escreve saidas se TODOS os portoes passarem.
    """
    name = args.section_name
    outputs = Path(args.outputs)
    reports_dir = Path(args.reports)

    out_dxf = outputs / "dxf" / f"{name}_vpro_safe_simplified.dxf"
    out_json = outputs / f"{name}_outer_ordered_simplified.json"
    canonical_dxf = Path("section/DXF") / f"{name}_vpro_safe_simplified.dxf"
    report_md = reports_dir / f"{name}_simplification_report.md"
    png_path = reports_dir / f"{name}_simplified_vpro_safe.png"
    png_copy = outputs / "previews" / f"{name}_simplified_vpro_safe.png"
    csv_path = reports_dir / f"{name}_simplified_coords.csv"

    for target in (out_dxf, out_json, canonical_dxf):
        if target.exists() and not args.force:
            print(f"[ERRO] {target} ja existe - use --force para sobrescrever.")
            return 1

    # ── referencia densa (mesmo pipeline do modo padrao, so em memoria) ────
    data = sp_io.load_json(Path(args.input_json))
    geo = pvd.compute_section_points(data)
    ordered_dense, _ = order_points_vpro_safe(geo["points_local"])

    # ── escada de circle_points ate passar nos portoes de propriedades ─────
    attempts: list[dict] = []
    chosen = None
    for cp in simplify.circle_points_candidates(args.circle_points):
        walk_pts, anchors = build_simplified_walk(geo, cp)
        walk_pts = simplify.simplify_collinear(
            walk_pts, angle_tol_deg=1.0, dist_tol=1e-6, protected=anchors
        )
        walk_pts = simplify.simplify_rdp_topology_safe(
            walk_pts, tolerance=1e-6, protected=anchors
        )
        ordered, y_tol = order_points_vpro_safe(walk_pts)
        props = validation.validate_section_properties(
            ordered_dense, ordered, args.max_area_error, args.max_inertia_error
        )
        attempts.append({"circle_points": cp, "n_points": len(ordered), "props": props})
        if props["ok"]:
            chosen = {
                "circle_points": cp, "walk_pts": walk_pts, "ordered": ordered,
                "y_tol": y_tol, "props": props,
            }
            break

    if chosen is None:
        print(f"[FALHOU] nenhuma resolucao {simplify.circle_points_candidates(args.circle_points)} "
              f"atendeu area<={args.max_area_error} e inercia<={args.max_inertia_error}:")
        for a in attempts:
            e = a["props"]["errors"]
            print(f"  circle_points={a['circle_points']}: {a['n_points']} pts, "
                  f"area_err={e['area']:.4%}, ix_err={e['ix']:.4%}, iy_err={e['iy']:.4%}")
        print("Nenhuma saida foi escrita.")
        return 1

    ordered = chosen["ordered"]
    props = chosen["props"]
    cp = chosen["circle_points"]

    # ── validacoes topologicas (mesma bateria do modo padrao) ──────────────
    graph = walk.build_edge_graph(chosen["walk_pts"], closed=True)
    cycles = graph.cycle_census()
    single_global_cycle = len(cycles) == 1 and cycles[0]["is_simple_cycle"]
    continuous, chord_indices = walk.check_continuous_walk(ordered, graph, closed=True)
    crossings = walk.self_intersections(ordered, closed=True)
    clearance, ci, cj = walk.min_nonadjacent_clearance(ordered)
    basic = validation.validate_polygon_basic(ordered)

    lengths = geometry.segment_lengths(ordered, closed=True)
    max_len = max(lengths)
    max_idx = lengths.index(max_len)
    max_seg_is_real_edge = graph.has_edge(ordered[max_idx], ordered[(max_idx + 1) % len(ordered)])

    min_x, min_y, max_x, max_y = geometry.bbox(ordered)
    start_is_top_left = (
        ordered[0][1] >= max_y - (max_y - min_y) * Y_TOL_FRACTION
        and ordered[0][0] <= (min_x + max_x) / 2
    )
    area_signed = geometry.signed_area(ordered)
    direction = "horario (CW)" if area_signed < 0 else "anti-horario (CCW)"
    gap_preserved = clearance > 1e-9

    ok_topology = (
        single_global_cycle and continuous and not crossings and basic.ok
        and gap_preserved and max_seg_is_real_edge and start_is_top_left
        and area_signed < 0
    )

    # ── DXF R12 + round-trip LibreDWG ──────────────────────────────────────
    out_dxf.parent.mkdir(parents=True, exist_ok=True)
    doc = pvd.build_r12_polyline_document(ordered)
    doc.saveas(str(out_dxf))
    pvd.inject_r12_insunits(out_dxf, insunits=6)

    ezdxf_check = pvd.validate_r12_structure_ezdxf(out_dxf, "POLYLINE")
    roundtrip = pvd.roundtrip_validate_r12(
        out_dxf, reports_dir, f"{name}_vpro_safe_simplified", expect_polyline=True
    )
    rt_count = roundtrip.get("roundtrip_point_count")
    if rt_count != len(ordered):
        roundtrip["ok"] = False
        roundtrip["messages"].append(
            f"round-trip retornou {rt_count} vertices, esperado {len(ordered)}"
        )
    single_entity_ok = (
        ezdxf_check["ok"]
        and ezdxf_check.get("entity_counts", {}).get("POLYLINE", 0) == 1
        and ezdxf_check.get("closed") is True
    )
    ok = ok_topology and single_entity_ok and roundtrip["ok"]

    canonical_dxf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out_dxf, canonical_dxf)

    # ── saidas auxiliares ──────────────────────────────────────────────────
    write_ordered_json(ordered, out_json)
    csv_msg = pvd.write_vpro_safe_csv(ordered, csv_path)
    preview_msg = write_simplified_preview(
        ordered, png_path,
        f"{name} VPRO-safe SIMPLIFICADA - {len(ordered)} pontos "
        f"({cp} pts/circulo, {direction})",
    )
    if preview_msg is None and png_path.exists():
        png_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(png_path, png_copy)

    # ── relatorio de simplificacao ─────────────────────────────────────────
    po, ps, err = props["original"], props["simplified"], props["errors"]
    n_orig, n_simp = len(ordered_dense), len(ordered)
    reduction = 100.0 * (1.0 - n_simp / n_orig)
    check = lambda flag: "OK" if flag else "FALHOU"  # noqa: E731

    lines = [
        f"# Relatorio de simplificacao VPRO-safe - {name}",
        "",
        f"Fonte primaria: `{args.input_json}`; referencia densa: {n_orig} pontos "
        f"(100 seg/semicirculo). Metodo: rediscretizacao dos arcos dos alveolos NA "
        f"ORDEM da entidade com compensacao de raio (area do setor preservada), "
        f"ancoras (cantos/canais/extremos de arco) intocadas; sem ordenacao global "
        f"por angulo.",
        "",
        "## Reducao de pontos",
        "",
        f"- Pontos originais: {n_orig}",
        f"- Pontos simplificados: {n_simp}",
        f"- Reducao: {reduction:.1f}%",
        f"- circle_points usado: {cp} (pedido: {args.circle_points}; "
        f"tentativas: {[(a['circle_points'], a['n_points']) for a in attempts]})",
        "",
        "## Propriedades seccionais (originais vs simplificadas)",
        "",
        f"| Propriedade | Original | Simplificada | Erro rel. | Limite |",
        f"|---|---|---|---|---|",
        f"| Area A (m^2) | {po['area']:.8f} | {ps['area']:.8f} | {err['area']:.4%} | {args.max_area_error:.2%} |",
        f"| Ix (m^4) | {po['ix']:.6e} | {ps['ix']:.6e} | {err['ix']:.4%} | {args.max_inertia_error:.2%} |",
        f"| Iy (m^4) | {po['iy']:.6e} | {ps['iy']:.6e} | {err['iy']:.4%} | {args.max_inertia_error:.2%} |",
        f"| Ixy (m^4) | {po['ixy']:.6e} | {ps['ixy']:.6e} | (informativo) | - |",
        f"| Cx (m) | {po['cx']:.6f} | {ps['cx']:.6f} | dif abs {err['cx']:.2e} m | - |",
        f"| Cy (m) | {po['cy']:.6f} | {ps['cy']:.6f} | dif abs {err['cy']:.2e} m | - |",
        "",
        f"- [{check(err['area'] <= args.max_area_error)}] erro de area dentro do limite",
        f"- [{check(err['ix'] <= args.max_inertia_error)}] erro de Ix dentro do limite",
        f"- [{check(err['iy'] <= args.max_inertia_error)}] erro de Iy dentro do limite",
        "",
        "## Topologia e caminhada (mesma bateria do export denso)",
        "",
        f"- Maior salto entre pontos consecutivos: {max_len:.6f} m "
        f"(indice {max_idx}; aresta real da borda: {max_seg_is_real_edge})",
        f"- [{check(single_global_cycle)}] 1 loop global fechado (graus: {graph.degree_census()})",
        f"- [{check(continuous)}] caminhada continua sem cordas"
        + (f" (violacoes: {chord_indices[:10]})" if chord_indices else ""),
        f"- [{check(not crossings)}] sem self-intersection"
        + (f" (cruzamentos: {crossings[:10]})" if crossings else ""),
        f"- [{check(gap_preserved)}] canal dos alveolos preservado: folga minima "
        f"{clearance * 1000:.3f} mm (indices {ci} e {cj})",
        f"- [{check(start_is_top_left)}] inicio no canto superior esquerdo: "
        f"({ordered[0][0]:.6f}, {ordered[0][1]:.6f})",
        f"- [{check(area_signed < 0)}] sentido: {direction}",
        f"- [{check(basic.ok)}] sem duplicatas/segmentos nulos",
        f"- [{check(single_entity_ok)}] DXF R12 com 1 POLYLINE fechada: "
        f"{ezdxf_check.get('entity_counts')}",
        f"- [{check(roundtrip['ok'])}] round-trip LibreDWG: {rt_count} vertices",
    ]
    lines += [f"  - {m}" for m in roundtrip["messages"]]
    lines += [
        "",
        "## Saidas",
        "",
        f"- DXF: `{out_dxf}` (copia canonica `{canonical_dxf}`)",
        f"- JSON ordenado: `{out_json}`",
        f"- CSV: `{csv_path}`" + (f" (erro: {csv_msg})" if csv_msg else ""),
        f"- PNG: `{png_path}`" + (f" (erro: {preview_msg})" if preview_msg else ""),
        "",
        f"**Resultado: {'PASSOU' if ok else 'FALHOU'} - "
        + (
            "gerar o AHK a partir do JSON simplificado e validar import no VPRO**"
            if ok
            else "NAO usar no VPRO ate corrigir os itens acima**"
        ),
        "",
    ]
    sp_io.save_report(report_md, "\n".join(lines))
    print("\n".join(lines))
    print(f"relatorio salvo em {report_md}")
    return 0 if ok else 1


def run_vpro_limited(args: argparse.Namespace) -> int:
    """Modo --max-vpro-points: reduz circle_points automaticamente ate caber no limite.

    Tenta ladder (32→28→24→20→16) e aceita a primeira que passa na validacao
    E cabe dentro do limite.
    """
    name = args.section_name
    max_points = args.max_vpro_points
    outputs = Path(args.outputs)
    reports_dir = Path(args.reports)

    out_dxf = outputs / "dxf" / f"{name}_vpro_simplified_{max_points}.dxf"
    out_json = outputs / f"{name}_outer_ordered_{max_points}.json"
    out_png = reports_dir / f"{name}_vpro_simplified_{max_points}.png"
    out_csv = reports_dir / f"{name}_vpro_simplified_{max_points}.csv"
    canonical_dxf = Path("section/DXF") / f"{name}_vpro_simplified_{max_points}.dxf"
    canonical_ahk = Path("section/ahk") / f"{name}.ahk"
    report_md = reports_dir / f"{name}_vpro_limited_{max_points}.md"

    for target in (out_dxf, canonical_dxf):
        if target.exists() and not args.force:
            print(f"[ERRO] {target} ja existe - use --force para sobrescrever.")
            return 1

    # ── referencia densa (mesmo pipeline do modo padrao) ────────────────────
    data = sp_io.load_json(Path(args.input_json))
    geo = pvd.compute_section_points(data)
    ordered_dense, _ = order_points_vpro_safe(geo["points_local"])

    # ── encontra o melhor circle_points que cabe no limite ─────────────────
    cp, ordered = find_best_circle_points_for_limit(
        geo, ordered_dense, max_points,
        args.max_area_error, args.max_inertia_error
    )
    if cp is None:
        print(f"[FALHOU] nenhuma resolucao da escada (32,28,24,20,16) atendeu:")
        print(f"  limite: {max_points} pontos")
        print(f"  area_err <= {args.max_area_error:.4%}")
        print(f"  inercia_err <= {args.max_inertia_error:.4%}")
        return 1

    # ── validacoes topologicas (mesma bateria) ─────────────────────────────
    walk_pts = ordered  # ja validado
    graph = walk.build_edge_graph(walk_pts, closed=True)
    cycles = graph.cycle_census()
    single_global_cycle = len(cycles) == 1 and cycles[0]["is_simple_cycle"]
    continuous, chord_indices = walk.check_continuous_walk(ordered, graph, closed=True)
    crossings = walk.self_intersections(ordered, closed=True)
    clearance, ci, cj = walk.min_nonadjacent_clearance(ordered)
    basic = validation.validate_polygon_basic(ordered)

    lengths = geometry.segment_lengths(ordered, closed=True)
    max_len = max(lengths) if lengths else 0
    max_idx = lengths.index(max_len) if lengths else 0
    max_seg_is_real_edge = graph.has_edge(ordered[max_idx], ordered[(max_idx + 1) % len(ordered)])

    min_x, min_y, max_x, max_y = geometry.bbox(ordered)
    start_is_top_left = (
        ordered[0][1] >= max_y - (max_y - min_y) * Y_TOL_FRACTION
        and ordered[0][0] <= (min_x + max_x) / 2
    )
    area_signed = geometry.signed_area(ordered)
    direction = "horario (CW)" if area_signed < 0 else "anti-horario (CCW)"
    gap_preserved = clearance > 1e-9

    ok_topology = (
        single_global_cycle and continuous and not crossings and basic.ok
        and gap_preserved and max_seg_is_real_edge and start_is_top_left
        and area_signed < 0
    )

    # ── DXF R12 + round-trip LibreDWG ──────────────────────────────────────
    out_dxf.parent.mkdir(parents=True, exist_ok=True)
    doc = pvd.build_r12_polyline_document(ordered)
    doc.saveas(str(out_dxf))
    pvd.inject_r12_insunits(out_dxf, insunits=6)

    ezdxf_check = pvd.validate_r12_structure_ezdxf(out_dxf, "POLYLINE")
    roundtrip = pvd.roundtrip_validate_r12(
        out_dxf, reports_dir, f"{name}_vpro_limited_{max_points}", expect_polyline=True
    )
    rt_count = roundtrip.get("roundtrip_point_count")
    if rt_count != len(ordered):
        roundtrip["ok"] = False
        roundtrip["messages"].append(
            f"round-trip retornou {rt_count} vertices, esperado {len(ordered)}"
        )
    single_entity_ok = (
        ezdxf_check["ok"]
        and ezdxf_check.get("entity_counts", {}).get("POLYLINE", 0) == 1
        and ezdxf_check.get("closed") is True
    )
    ok = ok_topology and single_entity_ok and roundtrip["ok"]

    canonical_dxf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out_dxf, canonical_dxf)

    # ── saidas auxiliares ──────────────────────────────────────────────────
    write_ordered_json(ordered, out_json)
    write_simplified_preview(
        ordered, out_png,
        f"{name} VPro Limited - {len(ordered)} pontos ({cp} pts/circulo, {direction})",
    )
    pvd.write_vpro_safe_csv(ordered, out_csv)

    # ── relatorio ──────────────────────────────────────────────────────────
    po, ps, err = (
        geometry.polygon_area_centroid_inertia(ordered_dense),
        geometry.polygon_area_centroid_inertia(ordered),
        None,
    )
    props = validation.validate_section_properties(
        ordered_dense, ordered, args.max_area_error, args.max_inertia_error
    )
    po, ps, err = props["original"], props["simplified"], props["errors"]
    n_orig, n_simp = len(ordered_dense), len(ordered)
    reduction = 100.0 * (1.0 - n_simp / n_orig)
    check = lambda flag: "OK" if flag else "FALHOU"  # noqa: E731

    lines = [
        f"# Relatorio VPro Limited - {name} ({max_points} pontos max)",
        "",
        f"Limite rigido: {max_points} pontos. Circle_points escadado automaticamente.",
        f"Fonte: `{args.input_json}` (LibreDWG JSON).",
        f"Saida DXF: `{out_dxf}` (copia canonica `{canonical_dxf}`)",
        f"Formato: DXF R12, 1 POLYLINE 2D fechada, $INSUNITS=6",
        "",
        "## Reducao de pontos",
        "",
        f"- Pontos originais (100 seg/semicirculo): {n_orig}",
        f"- Pontos limitados: {n_simp}",
        f"- Reducao: {reduction:.1f}%",
        f"- Circle_points usado: {cp}",
        "",
        "## Propriedades seccionais (originais vs limitadas)",
        "",
        f"| Propriedade | Original | Limitada | Erro rel. | Limite |",
        f"|---|---|---|---|---|",
        f"| Area A (m^2) | {po['area']:.8f} | {ps['area']:.8f} | {err['area']:.4%} | {args.max_area_error:.2%} |",
        f"| Ix (m^4) | {po['ix']:.6e} | {ps['ix']:.6e} | {err['ix']:.4%} | {args.max_inertia_error:.2%} |",
        f"| Iy (m^4) | {po['iy']:.6e} | {ps['iy']:.6e} | {err['iy']:.4%} | {args.max_inertia_error:.2%} |",
        "",
        f"- [{check(err['area'] <= args.max_area_error)}] erro de area dentro do limite",
        f"- [{check(err['ix'] <= args.max_inertia_error)}] erro de Ix dentro do limite",
        f"- [{check(err['iy'] <= args.max_inertia_error)}] erro de Iy dentro do limite",
        "",
        "## Topologia",
        "",
        f"- [{check(single_global_cycle)}] 1 loop global (graus: {graph.degree_census()})",
        f"- [{check(continuous)}] caminhada continua" + (f" (violacoes: {chord_indices[:5]})" if chord_indices else ""),
        f"- [{check(not crossings)}] sem self-intersection" + (f" (cruzamentos: {crossings[:5]})" if crossings else ""),
        f"- [{check(gap_preserved)}] canal preservado: folga {clearance*1000:.3f} mm",
        f"- [{check(start_is_top_left)}] inicio no canto superior esquerdo",
        f"- [{check(basic.ok)}] sem duplicatas/segmentos nulos",
        f"- [{check(single_entity_ok)}] DXF com 1 POLYLINE fechada",
        f"- [{check(roundtrip['ok'])}] round-trip LibreDWG: {rt_count} vertices",
        "",
        "## Saidas",
        "",
        f"- DXF: `{out_dxf}`",
        f"- JSON: `{out_json}`",
        f"- PNG: `{out_png}`",
        f"- CSV: `{out_csv}`",
        f"- AHK: `{canonical_ahk}`",
        "",
        f"**Resultado: {'PASSOU' if ok else 'FALHOU'}**",
        "",
    ]
    sp_io.save_report(report_md, "\n".join(lines))
    print("\n".join(lines))

    # ── copiar para AHK canonica ───────────────────────────────────────────
    if ok:
        export_ahk = Path("scripts/export_autohotkey.py")
        print(f"\nGerando AHK em `{canonical_ahk}`...")
        import subprocess
        subprocess.run([
            str(Path(".venv") / "bin" / "python"),
            str(export_ahk),
            "--force",
            "--input-json", str(out_json),
            "--output", str(canonical_ahk),
        ], check=True)
        print(f"AHK salvo em {canonical_ahk}")

    print(f"relatorio salvo em {report_md}")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.max_vpro_points:
        return run_vpro_limited(args)
    if args.simplify:
        return run_simplified(args)
    name = args.section_name
    outputs = Path(args.outputs)
    reports_dir = Path(args.reports)

    out_dxf = outputs / "dxf" / f"{name}_vpro_safe_ordered.dxf"
    out_json = outputs / f"{name}_outer_ordered.json"
    out_png = outputs / "previews" / f"{name}_order_check.png"
    out_svg = outputs / "previews" / f"{name}_order_check.svg"
    canonical_dxf = Path("section/DXF") / f"{name}_vpro_safe_ordered.dxf"
    canonical_png = Path("section/preview") / f"{name}_vpro_safe_ordered.png"
    report_md = reports_dir / f"{name}_vpro_safe_ordered_report.md"

    for target in (out_dxf, out_json, canonical_dxf):
        if target.exists() and not args.force:
            print(f"[ERRO] {target} ja existe - use --force para sobrescrever.")
            return 1

    # ── 1. fonte primaria: JSON do LibreDWG ────────────────────────────────
    data = sp_io.load_json(Path(args.input_json))
    geo = pvd.compute_section_points(data)
    points_walk: list[Point] = geo["points_local"]  # caminhada ORIGINAL da entidade
    n_bulges = sum(1 for b in geo["raw_bulges"] if abs(b) > 1e-9)

    # ── 2. grafo de arestas da caminhada original ──────────────────────────
    graph = walk.build_edge_graph(points_walk, closed=True)
    cycles = graph.cycle_census()
    degree_census = graph.degree_census()
    single_global_cycle = len(cycles) == 1 and cycles[0]["is_simple_cycle"]

    # ── 3. normalizacao (sem reordenar a caminhada) ────────────────────────
    ordered, y_tol = order_points_vpro_safe(points_walk)
    area_signed = geometry.signed_area(ordered)
    direction = "horario (CW)" if area_signed < 0 else "anti-horario (CCW)"

    # ── 4. validacoes topologicas ──────────────────────────────────────────
    continuous, chord_indices = walk.check_continuous_walk(ordered, graph, closed=True)
    crossings = walk.self_intersections(ordered, closed=True)
    clearance, ci, cj = walk.min_nonadjacent_clearance(ordered)
    basic = validation.validate_polygon_basic(ordered)
    shapely_msgs = shapely_second_opinion(ordered)

    lengths = geometry.segment_lengths(ordered, closed=True)
    max_len = max(lengths)
    max_idx = lengths.index(max_len)
    max_seg_is_real_edge = graph.has_edge(ordered[max_idx], ordered[(max_idx + 1) % len(ordered)])

    min_x, min_y, max_x, max_y = geometry.bbox(ordered)
    start_is_top_left = (
        ordered[0][1] >= max_y - (max_y - min_y) * Y_TOL_FRACTION
        and ordered[0][0] <= (min_x + max_x) / 2
    )

    gap_preserved = clearance > 1e-9
    ok_topology = (
        single_global_cycle
        and continuous
        and not crossings
        and basic.ok
        and gap_preserved
        and max_seg_is_real_edge
        and start_is_top_left
    )

    # ── 5. escrita do DXF R12 via ezdxf + round-trip LibreDWG ─────────────
    out_dxf.parent.mkdir(parents=True, exist_ok=True)
    doc = pvd.build_r12_polyline_document(ordered)
    doc.saveas(str(out_dxf))
    pvd.inject_r12_insunits(out_dxf, insunits=6)

    ezdxf_check = pvd.validate_r12_structure_ezdxf(out_dxf, "POLYLINE")
    roundtrip = pvd.roundtrip_validate_r12(
        out_dxf, reports_dir, f"{name}_vpro_safe_ordered", expect_polyline=True
    )
    rt_count = roundtrip.get("roundtrip_point_count")
    count_matches = rt_count == len(ordered)
    if not count_matches:
        roundtrip["ok"] = False
        roundtrip["messages"].append(
            f"round-trip retornou {rt_count} vertices, esperado {len(ordered)}"
        )

    single_entity_ok = (
        ezdxf_check["ok"]
        and ezdxf_check.get("entity_counts", {}).get("POLYLINE", 0) == 1
        and ezdxf_check.get("closed") is True
    )

    ok = ok_topology and single_entity_ok and roundtrip["ok"]

    # copias canonicas (section/ e a casa versionada oficial do repo)
    canonical_dxf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out_dxf, canonical_dxf)

    # ── 6. saidas auxiliares ───────────────────────────────────────────────
    write_ordered_json(ordered, out_json)
    preview_msg = write_order_check_previews(
        ordered, out_png, out_svg,
        f"{name} VPRO-safe - caminhada continua ({len(ordered)} vertices, {direction})",
    )
    if preview_msg is None and out_png.exists():
        canonical_png.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_png, canonical_png)

    # ── 7. relatorio (terminal + markdown) ─────────────────────────────────
    check = lambda flag: "OK" if flag else "FALHOU"  # noqa: E731
    report_lines = [
        f"# Relatorio VPRO-safe ordered - {name}",
        "",
        f"Fonte primaria: `{args.input_json}` (LibreDWG `dwgread -O JSON`)",
        f"Saida DXF: `{out_dxf}` (copia canonica em `{canonical_dxf}`)",
        f"Formato: DXF R12/AC1009, 1 POLYLINE 2D fechada (VERTEX+SEQEND), $INSUNITS=6",
        "",
        "## Geometria e caminhada",
        "",
        f"- Vertices originais da LWPOLYLINE: {len(geo['raw_points'])} (bulges nao-zero: {n_bulges})",
        f"- Vertices apos discretizacao dos arcos NA ORDEM da entidade: {len(points_walk)}",
        f"- Vertices na polilinha final: {len(ordered)}",
        f"- Arestas no grafo da caminhada: {graph.n_edges}",
        f"- Loops fechados encontrados no grafo: {len(cycles)} "
        f"(graus dos vertices: {degree_census})",
        f"- Area orientada: {area_signed:.6f} m^2 (|area| = {abs(area_signed):.6f} m^2)",
        f"- Sentido: {direction}",
        f"- Ponto inicial (superior esquerdo, banda y_tol={y_tol:.2e} m): "
        f"({ordered[0][0]:.6f}, {ordered[0][1]:.6f})",
        f"- Maior segmento consecutivo: {max_len:.6f} m (indice {max_idx}; "
        f"aresta real da borda: {max_seg_is_real_edge})",
        f"- Bounding box local: x=[{min_x:.4f}, {max_x:.4f}] y=[{min_y:.4f}, {max_y:.4f}]",
        "",
        "## Validacoes topologicas (grafo de arestas)",
        "",
        f"- [{check(single_global_cycle)}] exatamente 1 loop global fechado, todo vertice com grau 2",
        f"- [{check(continuous)}] caminhada continua: todo segmento vi->vi+1 e aresta original"
        + (f" (VIOLACOES nos indices {chord_indices[:10]})" if chord_indices else ""),
        f"- [{check(not crossings)}] sem self-intersection transversal"
        + (f" (cruzamentos: {crossings[:10]})" if crossings else ""),
        f"- [{check(gap_preserved)}] canal/gap dos alveolos preservado: folga minima "
        f"{clearance * 1000:.3f} mm entre vertices nao adjacentes (indices {ci} e {cj})",
        f"- [{check(len(cycles) == 1)}] alveolos NAO fechados como loops independentes "
        f"(fazem parte do unico ciclo global, ligados pelos canais)",
        f"- [{check(start_is_top_left)}] primeiro ponto na face superior, metade esquerda",
        f"- [{check(basic.ok)}] sem duplicatas consecutivas / segmentos nulos",
    ]
    report_lines += [f"  - {m}" for m in basic.checks + basic.warnings + basic.errors]
    report_lines += [f"  - {m}" for m in shapely_msgs]
    report_lines += [
        "",
        "## Estrutura do DXF final (ezdxf, leitura auxiliar)",
        "",
        f"- [{check(single_entity_ok)}] unica entidade POLYLINE fechada; "
        f"entidades: {ezdxf_check.get('entity_counts')}; "
        f"CIRCLE/ARC/LWPOLYLINE proibidas ausentes",
        f"- Versao: {ezdxf_check.get('dxfversion')} (AC1009 = R12)",
        "",
        "## Round-trip LibreDWG (dxf2dwg + dwgread -O JSON)",
        "",
        f"- [{check(roundtrip['ok'])}] round-trip com {rt_count} vertices "
        f"(esperado {len(ordered)}: {check(count_matches)})",
    ]
    report_lines += [f"  - {m}" for m in roundtrip["messages"]]
    report_lines += [
        "",
        "## Saidas",
        "",
        f"- DXF: `{out_dxf}` e `{canonical_dxf}`",
        f"- JSON ordenado: `{out_json}`",
        f"- Previews: `{out_png}`, `{out_svg}`"
        + (f" (nao gerados: {preview_msg})" if preview_msg else ""),
        "",
        f"**Resultado: {'PASSOU' if ok else 'FALHOU'} - "
        + (
            "estrutura validada; importar no VPRO para validacao final manual**"
            if ok
            else "NAO usar no VPRO ate corrigir os itens acima**"
        ),
        "",
    ]
    sp_io.save_report(report_md, "\n".join(report_lines))

    print("\n".join(report_lines))
    print(f"relatorio salvo em {report_md}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
