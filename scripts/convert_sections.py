#!/usr/bin/env python3
"""Converte DWGs de section/DWG para DXF + JSON, com relatorio e preview.

Fluxo por arquivo .dwg em --input:
  1. dwg2dxf         -> section/DXF/<nome>.dxf
  2. dwgread -O JSON -> section/json/<nome>.json
  3. valida o JSON (jq se disponivel, senao json.load)
  4. gera section/reports/<nome>.convert.md
  5. gera preview em section/preview/<nome>.png (se houver LWPOLYLINE simples)

Se houver um .dxf em --dxf sem .dwg correspondente em --input, o script
tambem aceita gerar o JSON a partir do DXF (dxf2dwg -> dwgread -O JSON),
sem nunca escrever DXF manualmente.

Nunca sobrescreve saida existente sem --force.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from section_pipeline import io as sp_io
from section_pipeline.libredwg import dwg_to_dxf, dwg_to_json, dxf_to_dwg

logger = logging.getLogger("convert_sections")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="section/DWG", help="pasta com os DWG de entrada")
    parser.add_argument("--dxf", default="section/DXF", help="pasta de saida dos DXF")
    parser.add_argument("--json", default="section/json", help="pasta de saida dos JSON")
    parser.add_argument("--reports", default="section/reports", help="pasta de relatorios")
    parser.add_argument("--preview", default="section/preview", help="pasta de previews")
    parser.add_argument("--force", action="store_true", help="sobrescreve saidas existentes")
    parser.add_argument("--verbose", action="store_true", help="log detalhado")
    return parser.parse_args(argv)


def validate_json_file(json_path: Path) -> tuple[bool, str]:
    """Valida com jq se disponivel, senao com json.load. Retorna (ok, mensagem)."""
    jq = shutil.which("jq")
    if jq:
        result = subprocess.run(
            [jq, "empty", str(json_path)], capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return True, "validado com jq"
        return False, f"jq reportou erro: {result.stderr.strip()}"

    try:
        json.loads(json_path.read_text(encoding="utf-8"))
        return True, "validado com json.load (jq nao encontrado no PATH)"
    except json.JSONDecodeError as exc:
        return False, f"json.load falhou: {exc}"


def try_generate_preview(json_path: Path, preview_path: Path) -> str | None:
    """Gera um PNG simples a partir de LWPOLYLINEs encontradas no JSON do dwgread.
    Retorna None se nao foi possivel (ex.: sem matplotlib ou sem entidades reconheciveis).
    """
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return "matplotlib nao instalado - preview nao gerado"

    data = sp_io.load_json(json_path)
    polylines = sp_io.extract_lwpolylines(data)
    if not polylines:
        return "nenhuma LWPOLYLINE encontrada no JSON para preview"

    fig, ax = plt.subplots(figsize=(10, 4))
    for entity in polylines:
        points = entity.get("points") or entity.get("vertices") or []
        coords = [(p[0], p[1]) for p in points if len(p) >= 2]
        if not coords:
            continue
        flag = entity.get("flag", 0)
        is_closed = bool(entity.get("closed")) or (isinstance(flag, int) and bool(flag & 1))
        if is_closed:
            coords = coords + [coords[0]]
        xs, ys = zip(*coords)
        ax.plot(xs, ys, "-o", markersize=2, linewidth=1)

    ax.set_aspect("equal")
    ax.set_title(json_path.stem)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(preview_path, dpi=150)
    plt.close(fig)
    return None


def convert_one_dwg(
    dwg_path: Path,
    dxf_dir: Path,
    json_dir: Path,
    reports_dir: Path,
    preview_dir: Path,
    force: bool,
) -> bool:
    name = dwg_path.stem
    dxf_path = dxf_dir / f"{name}.dxf"
    json_path = json_dir / f"{name}.json"
    report_path = reports_dir / f"{name}.convert.md"
    preview_path = preview_dir / f"{name}.png"

    report_lines = [f"# Relatorio de conversao - {name}", "", f"Fonte: `{dwg_path}`", ""]

    if dxf_path.exists() and not force:
        report_lines.append(f"DXF ja existe em `{dxf_path}` - use --force para sobrescrever.")
        logger.info("pulando %s (DXF existe, use --force)", name)
    else:
        dwg_to_dxf(dwg_path, dxf_path, reports_dir, overwrite=force)
        report_lines.append(f"DXF gerado com `dwg2dxf` em `{dxf_path}`.")
        logger.info("DXF gerado: %s", dxf_path)

    if json_path.exists() and not force:
        report_lines.append(f"JSON ja existe em `{json_path}` - use --force para sobrescrever.")
    else:
        dwg_to_json(dwg_path, json_path, reports_dir)
        report_lines.append(f"JSON gerado com `dwgread -O JSON` em `{json_path}`.")
        logger.info("JSON gerado: %s", json_path)

    ok, message = validate_json_file(json_path)
    report_lines.append(f"Validacao do JSON: {'OK' if ok else 'FALHOU'} - {message}")

    preview_message = try_generate_preview(json_path, preview_path)
    if preview_message is None:
        report_lines.append(f"Preview gerado em `{preview_path}`.")
    else:
        report_lines.append(f"Preview nao gerado: {preview_message}")

    sp_io.save_report(report_path, "\n".join(report_lines) + "\n")
    logger.info("relatorio: %s", report_path)
    return ok


def convert_orphan_dxf(
    dxf_path: Path, json_dir: Path, reports_dir: Path, preview_dir: Path, force: bool
) -> bool:
    """DXF sem DWG correspondente: gera JSON via dxf2dwg (temporario) -> dwgread -O JSON."""
    name = dxf_path.stem
    json_path = json_dir / f"{name}.json"
    report_path = reports_dir / f"{name}.convert.md"
    preview_path = preview_dir / f"{name}.png"

    if json_path.exists() and not force:
        sp_io.save_report(
            report_path,
            f"# Relatorio de conversao - {name}\n\n"
            f"JSON ja existe em `{json_path}` - use --force para sobrescrever.\n",
        )
        return True

    with tempfile.TemporaryDirectory(prefix="section_pipeline_") as tmp:
        tmp_dwg = Path(tmp) / f"{name}.dwg"
        dxf_to_dwg(dxf_path, tmp_dwg, reports_dir, overwrite=True)
        dwg_to_json(tmp_dwg, json_path, reports_dir)

    ok, message = validate_json_file(json_path)
    preview_message = try_generate_preview(json_path, preview_path)

    lines = [
        f"# Relatorio de conversao - {name}",
        "",
        f"Fonte: `{dxf_path}` (sem DWG correspondente em section/DWG)",
        "",
        f"JSON gerado via `dxf2dwg` (temporario) + `dwgread -O JSON` em `{json_path}`.",
        "",
        f"Validacao do JSON: {'OK' if ok else 'FALHOU'} - {message}",
    ]
    if preview_message is None:
        lines.append(f"Preview gerado em `{preview_path}`.")
    else:
        lines.append(f"Preview nao gerado: {preview_message}")
    sp_io.save_report(report_path, "\n".join(lines) + "\n")
    return ok


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    input_dir = Path(args.input)
    dxf_dir = Path(args.dxf)
    json_dir = Path(args.json)
    reports_dir = Path(args.reports)
    preview_dir = Path(args.preview)

    for d in (dxf_dir, json_dir, reports_dir, preview_dir):
        d.mkdir(parents=True, exist_ok=True)

    if not input_dir.is_dir():
        logger.error("pasta de entrada nao encontrada: %s", input_dir)
        return 1

    dwg_files = sorted(input_dir.glob("*.dwg"))
    all_ok = True

    if not dwg_files:
        logger.warning("nenhum .dwg encontrado em %s", input_dir)

    for dwg_path in dwg_files:
        try:
            ok = convert_one_dwg(dwg_path, dxf_dir, json_dir, reports_dir, preview_dir, args.force)
            all_ok = all_ok and ok
        except Exception as exc:  # noqa: BLE001 - queremos seguir para os demais arquivos
            logger.error("falha convertendo %s: %s", dwg_path.name, exc)
            all_ok = False

    dwg_stems = {p.stem for p in dwg_files}
    orphan_dxfs = [p for p in sorted(dxf_dir.glob("*.dxf")) if p.stem not in dwg_stems]
    for dxf_path in orphan_dxfs:
        logger.info("DXF sem DWG correspondente, gerando JSON via dxf2dwg: %s", dxf_path.name)
        try:
            ok = convert_orphan_dxf(dxf_path, json_dir, reports_dir, preview_dir, args.force)
            all_ok = all_ok and ok
        except Exception as exc:  # noqa: BLE001
            logger.error("falha processando %s: %s", dxf_path.name, exc)
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
