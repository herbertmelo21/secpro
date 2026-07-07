#!/usr/bin/env python3
"""Valida os DXF em section/DXF por round-trip LibreDWG + checagens geometricas.

Para cada .dxf em --dxf:
  1. dxf2dwg (temporario) - confirma que o DXF abre no LibreDWG
  2. dwgread -O JSON no DWG temporario - confirma que o DWG gerado abre e produz JSON valido
  3. leitura auxiliar com ezdxf (apenas leitura, nunca escrita) para:
     - contar entidades principais (LWPOLYLINE, CIRCLE, ARC, LINE)
     - bounding box
     - $INSUNITS
  4. se o nome do arquivo sugerir LA26, roda as checagens especificas de
     section_pipeline.validation.validate_la26_section (largura ~1.25 m,
     altura ~0.265 m, 5 alveolos, sem diagonais grandes, sem duplicatas).

Gera section/reports/validation_summary.md com o resultado agregado.
"""

from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from collections import Counter
from pathlib import Path

import ezdxf

from section_pipeline import validation
from section_pipeline.libredwg import dxf_to_dwg, dwg_to_json, load_dwgread_json

logger = logging.getLogger("validate_sections")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dxf", default="section/DXF", help="pasta com os DXF a validar")
    parser.add_argument("--reports", default="section/reports", help="pasta de relatorios")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def roundtrip_check(dxf_path: Path, reports_dir: Path) -> tuple[bool, str]:
    try:
        with tempfile.TemporaryDirectory(prefix="section_pipeline_validate_") as tmp:
            tmp_dwg = Path(tmp) / f"{dxf_path.stem}.dwg"
            tmp_json = Path(tmp) / f"{dxf_path.stem}.json"
            dxf_to_dwg(dxf_path, tmp_dwg, reports_dir, overwrite=True)
            dwg_to_json(tmp_dwg, tmp_json, reports_dir)
            load_dwgread_json(tmp_json)
        return True, "dxf2dwg + dwgread -O JSON OK, JSON valido"
    except Exception as exc:  # noqa: BLE001
        return False, f"round-trip LibreDWG falhou: {exc}"


def read_geometry_summary(dxf_path: Path) -> dict:
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    kinds = Counter(e.dxftype() for e in msp)

    all_points: list[tuple[float, float]] = []
    for e in msp:
        if e.dxftype() == "LWPOLYLINE":
            all_points.extend((float(x), float(y)) for x, y in e.get_points("xy"))

    insunits = doc.header.get("$INSUNITS")

    summary = {
        "entity_counts": dict(kinds),
        "lwpolyline_count": kinds.get("LWPOLYLINE", 0),
        "has_circle": kinds.get("CIRCLE", 0) > 0,
        "has_arc": kinds.get("ARC", 0) > 0,
        "has_line": kinds.get("LINE", 0) > 0,
        "insunits": insunits,
        "points": all_points,
    }
    if all_points:
        xs = [p[0] for p in all_points]
        ys = [p[1] for p in all_points]
        summary["bbox"] = (min(xs), min(ys), max(xs), max(ys))
    else:
        summary["bbox"] = None
    return summary


def validate_one(dxf_path: Path, reports_dir: Path) -> tuple[bool, list[str]]:
    lines = [f"## {dxf_path.name}", ""]
    ok = True

    rt_ok, rt_message = roundtrip_check(dxf_path, reports_dir)
    lines.append(f"- Round-trip LibreDWG (dxf2dwg + dwgread -O JSON): {'OK' if rt_ok else 'FALHOU'} - {rt_message}")
    ok = ok and rt_ok

    try:
        summary = read_geometry_summary(dxf_path)
    except Exception as exc:  # noqa: BLE001
        lines.append(f"- Leitura geometrica (ezdxf) FALHOU: {exc}")
        return False, lines

    lines.append(f"- Entidades: {summary['entity_counts']}")
    lines.append(f"- LWPOLYLINE: {summary['lwpolyline_count']}")
    lines.append(
        f"- CIRCLE: {summary['has_circle']}, ARC: {summary['has_arc']}, LINE: {summary['has_line']}"
    )
    lines.append(f"- $INSUNITS: {summary['insunits']} (6 = metros)")
    if summary["bbox"]:
        min_x, min_y, max_x, max_y = summary["bbox"]
        width = max_x - min_x
        height = max_y - min_y
        lines.append(
            f"- Bounding box: x=[{min_x:.4f}, {max_x:.4f}] y=[{min_y:.4f}, {max_y:.4f}] "
            f"(largura={width:.4f} m, altura={height:.4f} m)"
        )

    if summary["insunits"] != 6:
        lines.append("- AVISO: \\$INSUNITS diferente de 6 (metros) - conferir unidade do desenho.")

    points = summary["points"]
    if points:
        basic = validation.validate_polygon_basic(points)
        for c in basic.checks:
            lines.append(f"  - {c}")
        for w in basic.warnings:
            lines.append(f"  - AVISO: {w}")
        for e in basic.errors:
            lines.append(f"  - ERRO: {e}")
        ok = ok and basic.ok

    if "la26" in dxf_path.stem.lower() and points:
        lines.append("")
        lines.append("### Checagens especificas LA26")
        la26 = validation.validate_la26_section(points)
        for c in la26.checks:
            lines.append(f"  - {c}")
        for w in la26.warnings:
            lines.append(f"  - AVISO: {w}")
        for e in la26.errors:
            lines.append(f"  - ERRO: {e}")
        ok = ok and la26.ok

    lines.append("")
    lines.append(f"**Resultado: {'PASSOU' if ok else 'FALHOU'}**")
    lines.append("")
    return ok, lines


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    dxf_dir = Path(args.dxf)
    reports_dir = Path(args.reports)
    reports_dir.mkdir(parents=True, exist_ok=True)

    dxf_files = sorted(dxf_dir.glob("*.dxf"))
    if not dxf_files:
        logger.warning("nenhum .dxf encontrado em %s", dxf_dir)

    all_lines = ["# Relatorio de validacao de secoes", ""]
    all_ok = True

    for dxf_path in dxf_files:
        logger.info("validando %s", dxf_path.name)
        ok, lines = validate_one(dxf_path, reports_dir)
        all_lines.extend(lines)
        all_ok = all_ok and ok

    summary_path = reports_dir / "validation_summary.md"
    summary_path.write_text("\n".join(all_lines) + "\n", encoding="utf-8")
    logger.info("resumo gravado em %s", summary_path)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
