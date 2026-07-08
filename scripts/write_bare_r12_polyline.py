#!/usr/bin/env python3
"""Extrai a POLYLINE de um DXF R12 existente e escreve uma copia "pelada" - so
HEADER minimo ($ACADVER + $INSUNITS) + ENTITIES (1 POLYLINE + VERTEX + SEQEND) + EOF.

Nao usa ezdxf para ESCREVER (ezdxf sempre adiciona TABLES/BLOCKS mesmo para R12 - ver
`process_vpro_dxf.build_r12_polyline_document`); usa ezdxf so para LER a POLYLINE de
entrada. A escrita manual e permitida aqui porque o formato de saida (R12 puro,
POLYLINE/VERTEX/SEQEND) e simples o bastante para ser auditado linha a linha.

Nao recalcula geometria nenhuma: le os vertices tal como estao no arquivo de entrada,
so remove pontos consecutivos coincidentes (tolerancia 1e-12) e o fechamento duplicado.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from collections import Counter
from pathlib import Path

import ezdxf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from section_pipeline import geometry
from section_pipeline import io as sp_io
from section_pipeline.libredwg import dxf_to_dwg, dwg_to_json

import process_vpro_dxf as vpro  # dedup_consecutive, validate_json_file, _load_dwgread_json_lenient
import generate_la25_20gon_variants as gon  # validate_structure_ezdxf

logger = logging.getLogger("write_bare_r12_polyline")

Point = tuple[float, float]

DEDUP_TOL = 1e-12

# Unicos group codes que este escritor emite - usados tambem na validacao textual.
ALLOWED_HEADER_CODES = {"0", "2", "9", "1", "70"}
ALLOWED_ENTITY_CODES = {"0", "8", "66", "70", "10", "20", "30"}

FORBIDDEN_SUBSTRINGS = (
    "TABLES",
    "BLOCKS",
    "OBJECTS",
    "CLASSES",
    "LWPOLYLINE",
    "SPLINE",
    "HATCH",
    "REGION",
    "INSERT",
    "AcDb",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dxf", required=True, help="DXF R12 de entrada (1 POLYLINE)")
    parser.add_argument("--output-dxf", required=True, help="DXF R12 ultraminimo de saida")
    parser.add_argument("--reports", default="section/reports")
    parser.add_argument("--preview", default="section/preview")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


# --------------------------------------------------------------------------------------
# leitura (ezdxf) + limpeza
# --------------------------------------------------------------------------------------


def read_single_polyline(input_dxf: Path) -> tuple[list[Point], bool]:
    doc = ezdxf.readfile(input_dxf)
    msp = doc.modelspace()
    polylines = [e for e in msp if e.dxftype() == "POLYLINE"]
    if len(polylines) != 1:
        raise ValueError(f"esperada exatamente 1 POLYLINE em {input_dxf}, encontrada {len(polylines)}")
    entity = polylines[0]
    points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
    return points, bool(entity.is_closed)


def clean_points(points: list[Point]) -> list[Point]:
    """Remove pontos consecutivos coincidentes (tol 1e-12) e o fechamento duplicado -
    mesma funcao ja usada nos outros writers R12 (process_vpro_dxf.dedup_consecutive)."""
    return vpro.dedup_consecutive(points, tol=DEDUP_TOL)


# --------------------------------------------------------------------------------------
# escrita manual (permitida so para este perfil ultraminimo)
# --------------------------------------------------------------------------------------


def write_bare_r12_polyline_dxf(points: list[Point], output_path: Path, insunits: int = 6) -> None:
    lines: list[str] = []

    def w(code: int | str, value) -> None:
        lines.append(str(code))
        lines.append(str(value))

    w(0, "SECTION")
    w(2, "HEADER")
    w(9, "$ACADVER")
    w(1, "AC1009")
    w(9, "$INSUNITS")
    w(70, insunits)
    w(0, "ENDSEC")

    w(0, "SECTION")
    w(2, "ENTITIES")

    w(0, "POLYLINE")
    w(8, "0")
    w(66, 1)
    w(70, 1)
    w(10, 0.0)
    w(20, 0.0)
    w(30, 0.0)

    for x, y in points:
        w(0, "VERTEX")
        w(8, "0")
        w(10, repr(x))
        w(20, repr(y))
        w(30, 0.0)

    w(0, "SEQEND")
    w(8, "0")

    w(0, "ENDSEC")
    w(0, "EOF")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------
# validacao textual (16.A) - parser de pares group-code/valor, nao grep ingenuo
# --------------------------------------------------------------------------------------


def parse_dxf_pairs(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    return list(zip(lines[0::2], lines[1::2]))


def textual_validation(output_path: Path) -> dict:
    text = output_path.read_text(encoding="utf-8")
    pairs = parse_dxf_pairs(text)

    entity_names = Counter(value.strip() for code, value in pairs if code.strip() == "0")
    codes_used = {code.strip() for code, _ in pairs}

    result: dict = {"ok": True, "messages": [], "entity_counts": dict(entity_names)}

    if entity_names.get("POLYLINE", 0) != 1:
        result["ok"] = False
        result["messages"].append(f"esperada exatamente 1 ocorrencia de POLYLINE, encontrada {entity_names.get('POLYLINE', 0)}")
    if entity_names.get("VERTEX", 0) < 1:
        result["ok"] = False
        result["messages"].append("nenhuma ocorrencia de VERTEX")
    if entity_names.get("SEQEND", 0) != 1:
        result["ok"] = False
        result["messages"].append(f"esperada exatamente 1 SEQEND, encontrada {entity_names.get('SEQEND', 0)}")

    for forbidden_entity in ("LWPOLYLINE", "LINE", "ARC", "CIRCLE", "SPLINE"):
        if entity_names.get(forbidden_entity, 0) > 0:
            result["ok"] = False
            result["messages"].append(f"entidade proibida presente: {forbidden_entity}")

    for substr in FORBIDDEN_SUBSTRINGS:
        if substr in text:
            result["ok"] = False
            result["messages"].append(f"substring proibida encontrada no arquivo: {substr!r}")

    allowed_codes = ALLOWED_HEADER_CODES | ALLOWED_ENTITY_CODES
    extra_codes = codes_used - allowed_codes
    if extra_codes:
        result["ok"] = False
        result["messages"].append(f"group codes fora do permitido: {sorted(extra_codes)}")

    if not result["ok"]:
        result["messages"].insert(0, "validacao textual FALHOU")
    else:
        result["messages"].append("validacao textual OK (POLYLINE unica, sem TABLES/BLOCKS/OBJECTS/CLASSES/AcDb/entidades proibidas)")

    return result


# --------------------------------------------------------------------------------------
# round-trip LibreDWG - tolerante ao aviso conhecido "BLOCK_CONTROL missing"
# --------------------------------------------------------------------------------------

# Um DXF R12 sem secao BLOCKS/TABLES (pedido explicitamente neste perfil "bare") nao tem
# BLOCK_CONTROL/Model_Space - o `dxf2dwg` desta instalacao do LibreDWG reporta isso como
# "ERROR:", mas (verificado empiricamente) ainda termina com rc=0 e escreve um DWG que o
# `dwgread -O JSON` consegue ler por completo (POLYLINE_2D/VERTEX_2D/SEQEND intactos).
# Tratamos esse padrao especifico como aviso conhecido, sem afrouxar a deteccao de erro
# para qualquer outro caso (mesmo espirito de KNOWN_BENIGN_DXF2DWG_ERROR em process_vpro_dxf.py).
KNOWN_BENIGN_MISSING_BLOCK_CONTROL = "block_control"


def _dxf2dwg_log_is_known_benign(log_path: Path) -> bool:
    if not log_path.exists():
        return False
    error_lines = [line for line in log_path.read_text(encoding="utf-8").splitlines() if "ERROR" in line]
    return bool(error_lines) and all(
        KNOWN_BENIGN_MISSING_BLOCK_CONTROL in line.lower() for line in error_lines
    )


def roundtrip_validate_bare(dxf_path: Path, reports_dir: Path, stem: str) -> dict:
    report: dict = {"ok": True, "commands": [], "messages": []}
    roundtrip_dwg = reports_dir / f"{stem}_roundtrip.dwg"
    roundtrip_json = reports_dir / f"{stem}_roundtrip.json"

    try:
        dxf_to_dwg(dxf_path, roundtrip_dwg, reports_dir, overwrite=True)
        report["commands"].append(f"dxf2dwg -y -o {roundtrip_dwg} {dxf_path}")
    except Exception as exc:  # noqa: BLE001
        log = reports_dir / f"{dxf_path.stem}.dxf2dwg.log"
        if roundtrip_dwg.exists() and _dxf2dwg_log_is_known_benign(log):
            report["messages"].append(
                "dxf2dwg AVISO (conhecido, nao fatal): 'HEADER.BLOCK_CONTROL_OBJECT missing' "
                "- esperado para um DXF R12 sem secao BLOCKS/TABLES (pedido explicitamente "
                f"neste perfil bare); rc=0 e DWG gerado normalmente - ver {log}"
            )
            report["commands"].append(f"dxf2dwg -y -o {roundtrip_dwg} {dxf_path}")
        else:
            report["ok"] = False
            report["messages"].append(f"dxf2dwg falhou: {exc}")
            return report

    try:
        dwg_to_json(roundtrip_dwg, roundtrip_json, reports_dir)
        report["commands"].append(f"dwgread -O JSON -o {roundtrip_json} {roundtrip_dwg}")
    except Exception as exc:  # noqa: BLE001
        report["messages"].append(f"dwgread -O JSON reportou erro: {exc}")
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
    if len(polylines) != 1:
        report["ok"] = False
        report["messages"].append(f"esperada exatamente 1 POLYLINE/POLYLINE_2D, encontrada {len(polylines)}")
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

    report["seqend_count"] = counts.get("SEQEND", 0)
    report["vertex_count"] = counts.get("VERTEX_2D", 0) + counts.get("VERTEX", 0)
    if report["seqend_count"] != 1:
        report["ok"] = False
        report["messages"].append(f"esperado 1 SEQEND, encontrado {report['seqend_count']}")

    vertex_entities = [e for e in entities if str(e.get("entity", "")).upper() in ("VERTEX", "VERTEX_2D")]
    rt_points = [
        (float(v["point"][0]), float(v["point"][1]))
        for v in vertex_entities
        if isinstance(v.get("point"), list) and len(v["point"]) >= 2
    ]
    if rt_points:
        report["roundtrip_bbox"] = geometry.bbox(rt_points)
        from section_pipeline import validation as sv

        basic = sv.validate_polygon_basic(rt_points)
        report["messages"].extend(f"round-trip: {c}" for c in basic.checks)
        report["messages"].extend(f"round-trip AVISO: {w}" for w in basic.warnings)
        report["messages"].extend(f"round-trip ERRO: {e}" for e in basic.errors)
        report["ok"] = report["ok"] and basic.ok

    return report


# --------------------------------------------------------------------------------------
# preview
# --------------------------------------------------------------------------------------


def write_preview(points: list[Point], preview_path: Path, title: str) -> str | None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return "matplotlib nao instalado - preview nao gerado"

    closed = points + [points[0]]
    xs, ys = zip(*closed)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(xs, ys, "-", linewidth=1)
    ax.set_aspect("equal")
    ax.set_title(title)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(preview_path, dpi=150)
    plt.close(fig)
    return None


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s"
    )

    input_dxf = Path(args.input_dxf)
    output_dxf = Path(args.output_dxf)
    reports_dir = Path(args.reports)
    preview_dir = Path(args.preview)
    reports_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    report_path = reports_dir / f"{output_dxf.stem}_report.md"

    if output_dxf.exists() and not args.force:
        logger.warning("%s ja existe - use --force para sobrescrever", output_dxf)
        sp_io.save_report(
            report_path,
            f"# Relatorio - {output_dxf.stem}\n\n`{output_dxf}` ja existe - nao sobrescrito (use --force).\n",
        )
        return 1

    size_before = input_dxf.stat().st_size

    raw_points, was_closed = read_single_polyline(input_dxf)
    n_original = len(raw_points)
    cleaned_points = clean_points(raw_points)
    n_final = len(cleaned_points)

    if not was_closed:
        logger.warning("POLYLINE de entrada nao esta com flag closed - escrevendo mesmo assim com flag 70=1 (fechada), sem repetir o primeiro ponto")

    write_bare_r12_polyline_dxf(cleaned_points, output_dxf, insunits=6)
    size_after = output_dxf.stat().st_size
    logger.info("DXF bare escrito em %s", output_dxf)

    # --- validacoes ---
    text_check = textual_validation(output_dxf)

    ez_check = gon.validate_structure_ezdxf(output_dxf, expected_polyline_count=1)
    ez_bbox = ez_check.get("bbox")
    input_bbox = geometry.bbox(raw_points)
    bbox_matches = ez_bbox is not None and all(
        abs(a - b) < 1e-6 for a, b in zip(ez_bbox, input_bbox)
    )
    if not bbox_matches:
        ez_check["ok"] = False
        ez_check["messages"].append(f"bbox nao bate com o arquivo de entrada: {ez_bbox} vs {input_bbox}")

    basic = None
    from section_pipeline import validation as sv

    basic = sv.validate_polygon_basic(cleaned_points, zero_length_tol=DEDUP_TOL)

    rt_check = roundtrip_validate_bare(output_dxf, reports_dir, output_dxf.stem)

    ok = text_check["ok"] and ez_check["ok"] and basic.ok and rt_check["ok"]

    preview_path = preview_dir / f"{output_dxf.stem}.png"
    preview_msg = write_preview(cleaned_points, preview_path, output_dxf.stem)

    write_report(
        input_dxf=input_dxf,
        output_dxf=output_dxf,
        n_original=n_original,
        n_final=n_final,
        input_bbox=input_bbox,
        ez_check=ez_check,
        text_check=text_check,
        basic=basic,
        rt_check=rt_check,
        size_before=size_before,
        size_after=size_after,
        preview_path=preview_path,
        preview_msg=preview_msg,
        ok=ok,
        report_path=report_path,
    )

    return 0 if ok else 1


def write_report(
    *, input_dxf, output_dxf, n_original, n_final, input_bbox, ez_check, text_check, basic,
    rt_check, size_before, size_after, preview_path, preview_msg, ok, report_path,
) -> None:
    width = input_bbox[2] - input_bbox[0]
    height = input_bbox[3] - input_bbox[1]

    lines = [
        f"# Relatorio - {output_dxf.stem}",
        "",
        f"Entrada: `{input_dxf}`",
        f"Saida: `{output_dxf}`",
        "",
        "## Geometria",
        "",
        f"- Numero de vertices original: {n_original}",
        f"- Numero de vertices final (apos limpeza tol=1e-12): {n_final}",
        f"- Bounding box: {input_bbox}",
        f"- Largura: {width:.6f} m",
        f"- Altura: {height:.6f} m",
        "",
        "## Presenca de secoes/entidades proibidas (validacao textual)",
        "",
        f"- Contagem de entidades/secoes no arquivo: {text_check['entity_counts']}",
        f"- TABLES presente: {'TABLES' in text_check['entity_counts']}",
        f"- BLOCKS presente: {'BLOCKS' in text_check['entity_counts']}",
        f"- OBJECTS presente: {'OBJECTS' in text_check['entity_counts']}",
        f"- CLASSES presente: {'CLASSES' in text_check['entity_counts']}",
        f"- LWPOLYLINE presente: {text_check['entity_counts'].get('LWPOLYLINE', 0) > 0}",
        f"- LINE presente: {text_check['entity_counts'].get('LINE', 0) > 0}",
        f"- ARC presente: {text_check['entity_counts'].get('ARC', 0) > 0}",
        f"- CIRCLE presente: {text_check['entity_counts'].get('CIRCLE', 0) > 0}",
        f"- SPLINE presente: {text_check['entity_counts'].get('SPLINE', 0) > 0}",
    ]
    lines += [f"  - {m}" for m in text_check["messages"]]

    lines += [
        "",
        "## Validacao geometrica basica (sem pontos duplicados / segmentos nulos)",
        "",
    ]
    lines += [f"  - {c}" for c in basic.checks]
    lines += [f"  - AVISO: {w}" for w in basic.warnings]
    lines += [f"  - ERRO: {e}" for e in basic.errors]

    lines += [
        "",
        "## Resultado ezdxf",
        "",
        f"- Versao DXF: {ez_check.get('dxfversion')} (esperado AC1009)",
        f"- Entidades: {ez_check.get('entity_counts')}",
        f"- POLYLINE: {ez_check.get('polyline_count')} (esperado 1)",
        f"- Fechada: {ez_check.get('closed_flags')}",
        f"- Bounding box (ezdxf): {ez_check.get('bbox')}",
    ]
    lines += [f"  - ERRO: {m}" for m in ez_check["messages"]]

    lines += [
        "",
        "## Resultado LibreDWG (dxf2dwg + dwgread -O JSON + jq empty)",
        "",
        f"- Comandos executados: {rt_check['commands']}",
        f"- Entidades no round-trip: {rt_check.get('entity_counts', {})}",
        f"- POLYLINE/POLYLINE_2D no round-trip: {rt_check.get('polyline_count')} (esperado 1)",
        f"- Fechada (round-trip): {rt_check.get('closed_flags')}",
        f"- SEQEND: {rt_check.get('seqend_count')}, VERTEX: {rt_check.get('vertex_count')}",
        f"- Bounding box (round-trip): {rt_check.get('roundtrip_bbox')}",
    ]
    lines += [f"  - {m}" for m in rt_check["messages"]]

    lines += [
        "",
        "## Tamanho do arquivo",
        "",
        f"- Antes (entrada, {input_dxf.name}): {size_before} bytes",
        f"- Depois (saida, {output_dxf.name}): {size_after} bytes",
        f"- Reducao: {size_before - size_after} bytes ({(1 - size_after / size_before) * 100:.1f}%)",
        "",
    ]

    if preview_msg is None:
        lines.append(f"Preview gerado em `{preview_path}`.")
    else:
        lines.append(f"Preview nao gerado: {preview_msg}")

    lines.append("")
    lines.append(
        f"**Resultado: {'estrutura OK' if ok else 'FALHOU'} - bare R12 single-polyline candidate "
        "(NAO declarar VPRO-safe; validar importando no VPRO antes de confiar neste arquivo)**"
    )
    lines.append("")

    sp_io.save_report(report_path, "\n".join(lines))
    logger.info("relatorio: %s", report_path)


if __name__ == "__main__":
    sys.exit(main())
