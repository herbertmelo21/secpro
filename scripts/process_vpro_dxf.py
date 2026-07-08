#!/usr/bin/env python3
"""Reconstroi um DXF limpo e seguro para o VPRO a partir do JSON do LibreDWG.

Problema que este script resolve: `dwgread -O DXF` / `dwg2dxf` sobre o DWG
original produz um DXF "bruto" (traz blocos, layers, estilos e metadados
pesados do DWG de origem, alem de entidades residuais como LINEs de
comprimento zero) que o VPRO nao le. Esse DXF bruto nunca deve ser o produto
final para o VPRO.

Fonte geometrica: o JSON gerado por `dwgread -O JSON` (nao o DXF bruto).

Fluxo:
  1. le o JSON e localiza a LWPOLYLINE principal (maior bbox aproximado),
     ignorando LINE/ARC/CIRCLE/demais entidades residuais;
  2. converte bulges (arcos) em segmentos retos, com resolucao proporcional
     ao angulo (100 segmentos por semicircunferencia, minimo 8 por arco);
  3. limpa pontos consecutivos coincidentes e segmentos de comprimento zero;
  4. recentraliza em coordenadas locais, SEM aplicar escala:
       x_local = x - (x_min + x_max) / 2
       y_local = y - y_min
  5. escreve um DXF minimo com ezdxf (1 LWPOLYLINE fechada, layer SECTION,
     $INSUNITS=6, sem blocos/layouts/estilos herdados);
  6. valida o resultado via round-trip LibreDWG (dxf2dwg + dwgread -O JSON),
     reaproveitando `section_pipeline.libredwg`;
  7. gera relatorio em section/reports/<nome>_vpro_report.md e preview em
     section/preview/<nome>_vpro.png.

Nunca sobrescreve o DXF de saida sem --force. Nunca escreve bulge no DXF final
(todo arco ja chega discretizado em segmentos retos).
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import ezdxf
from ezdxf.math import bulge_to_arc

from section_pipeline import geometry
from section_pipeline import io as sp_io
from section_pipeline import validation
from section_pipeline.libredwg import dxf_to_dwg, dwg_to_json, load_dwgread_json

logger = logging.getLogger("process_vpro_dxf")

Point = tuple[float, float]

MIN_ARC_SEGMENTS = 8
SEGMENTS_PER_SEMICIRCLE = 100
LOWRES_SEGMENTS_PER_SEMICIRCLE = 20
DEDUP_TOL = 1e-9

WRITER_CHOICES = ("ezdxf-lwpolyline", "r12-polyline", "r12-polyline-lowres", "r12-lines-lowres")

# ezdxf.new() sempre cria um dicionario de objetos padrao (ACAD_MATERIAL,
# ACAD_MLEADERSTYLE, ACAD_COLOR etc.) mesmo para um documento vazio - isso nao
# vem do DWG original, e o proprio template minimo do ezdxf. Esses dicionarios
# nao sao necessarios para uma LWPOLYLINE simples, entao sao removidos antes de
# salvar (fica so o que e estritamente necessario: ACAD_MATERIAL/ACAD_PLOTSTYLENAME,
# dos quais toda LAYER depende, e ACAD_LAYOUT, do qual o modelspace depende).
PURGEABLE_ROOTDICT_KEYS = (
    "ACAD_COLOR",
    "ACAD_GROUP",
    "ACAD_MLEADERSTYLE",
    "ACAD_MLINESTYLE",
    "ACAD_PLOTSETTINGS",
    "ACAD_SCALELIST",
    "ACAD_TABLESTYLE",
    "ACAD_VISUALSTYLE",
)

# Mesmo apos a purga acima, o dicionario ACAD_MATERIAL nao pode ser removido
# (ezdxf.Drawing.save() depende dele internamente para atualizar variaveis de
# header, e toda LAYER referencia um material). O `dxf2dwg` desta instalacao do
# LibreDWG (0.14.8390) reporta, de forma reproduzivel, um unico
# "ERROR: Duplicate handle ... already points to object 0" relacionado a esse
# MATERIAL padrao do ezdxf - mesmo para um documento novo, vazio, sem nenhuma
# entidade nossa. Verificado empiricamente: o `dxf2dwg` ainda retorna rc=0 e o
# DWG resultante abre e gera JSON valido via `dwgread -O JSON`. Tratamos esse
# padrao especifico como aviso conhecido (nao fatal), sem afrouxar a deteccao
# de erro para qualquer outro caso.
KNOWN_BENIGN_DXF2DWG_ERROR = "Duplicate handle"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", required=True, help="JSON gerado por dwgread -O JSON")
    parser.add_argument("--output-dxf", required=True, help="DXF final limpo para o VPRO")
    parser.add_argument("--section-name", required=True, help="nome da secao (ex.: LA25)")
    parser.add_argument("--reports", default="section/reports", help="pasta de relatorios")
    parser.add_argument("--preview", default="section/preview", help="pasta de previews")
    parser.add_argument("--force", action="store_true", help="sobrescreve o DXF de saida")
    parser.add_argument(
        "--writer",
        choices=WRITER_CHOICES,
        default="ezdxf-lwpolyline",
        help=(
            "ezdxf-lwpolyline (padrao): DXF R2000 com LWPOLYLINE, via ezdxf. "
            "r12-polyline: DXF R12/AC1009 legacy com POLYLINE/VERTEX/SEQEND, para VPRO. "
            "r12-polyline-lowres / r12-lines-lowres: variantes diagnosticas de baixa "
            "resolucao (20 segmentos/semicircunferencia) do modo r12, para testar limites do VPRO."
        ),
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def entity_bbox_area(entity: dict) -> float:
    points = [(float(p[0]), float(p[1])) for p in entity.get("points", []) if len(p) >= 2]
    if len(points) < 2:
        return 0.0
    min_x, min_y, max_x, max_y = geometry.bbox(points)
    return (max_x - min_x) * (max_y - min_y)


def select_main_lwpolyline(entities: list[dict]) -> dict:
    """Seleciona a LWPOLYLINE de maior area de bbox aproximada (largura x altura)."""
    if not entities:
        raise ValueError("nenhuma entidade LWPOLYLINE encontrada no JSON")
    return max(entities, key=entity_bbox_area)


def arc_segment_points(
    p1: Point, p2: Point, bulge: float, segments_per_semicircle: int = SEGMENTS_PER_SEMICIRCLE
) -> list[Point]:
    """Pontos intermediarios (excluindo p1 e p2) que discretizam o arco de bulge entre p1 e p2.

    bulge = tan(theta/4); theta e o angulo incluido, com sinal (positivo = CCW de p1 para p2).
    O centro/raio vem de `ezdxf.math.bulge_to_arc` (formula de Lee Mac, so usamos center e
    radius - o angulo e recalculado aqui a partir do proprio bulge para controlar o sentido
    de varredura sem depender da convencao de troca de angulos que o ezdxf usa para bulges
    negativos).

    `segments_per_semicircle` so e diferente do padrao (100) nas variantes diagnosticas
    lowres (20) - a geometria em si (centro/raio/angulo) e sempre a mesma, so a resolucao
    de discretizacao muda.
    """
    if abs(bulge) < 1e-12:
        return []

    center, _start_angle, _end_angle, radius = bulge_to_arc(p1, p2, bulge)
    theta = 4.0 * math.atan(bulge)

    a1 = math.atan2(p1[1] - center.y, p1[0] - center.x)

    segments = max(MIN_ARC_SEGMENTS, round(segments_per_semicircle * abs(theta) / math.pi))

    points = []
    for k in range(1, segments):
        angle = a1 + theta * (k / segments)
        points.append((center.x + radius * math.cos(angle), center.y + radius * math.sin(angle)))
    return points


def expand_polyline(
    points: list[Point], bulges: list[float], segments_per_semicircle: int = SEGMENTS_PER_SEMICIRCLE
) -> list[Point]:
    """Expande vertices + bulges em uma lista de pontos com os arcos discretizados em retas.

    Trata a polilinha como fechada (segmento de fechamento incluido, do ultimo vertice de
    volta ao primeiro, usando o ultimo bulge) - mesma convencao ja usada em
    `section_pipeline.geometry.segment_lengths`/`has_consecutive_duplicates` (closed=True),
    e consistente com o requisito de o DXF final sair sempre com closed=True.
    """
    n = len(points)
    expanded: list[Point] = []
    for i in range(n):
        p1 = points[i]
        p2 = points[(i + 1) % n]
        bulge = bulges[i] if i < len(bulges) else 0.0
        expanded.append(p1)
        expanded.extend(arc_segment_points(p1, p2, bulge, segments_per_semicircle))
    return expanded


def dedup_consecutive(points: list[Point], tol: float = DEDUP_TOL) -> list[Point]:
    """Remove pontos consecutivos coincidentes (incluindo o fechamento ultimo->primeiro)."""
    if not points:
        return points
    cleaned = [points[0]]
    for p in points[1:]:
        prev = cleaned[-1]
        if math.hypot(p[0] - prev[0], p[1] - prev[1]) > tol:
            cleaned.append(p)
    if len(cleaned) > 1:
        first, last = cleaned[0], cleaned[-1]
        if math.hypot(last[0] - first[0], last[1] - first[1]) <= tol:
            cleaned.pop()
    return cleaned


def compute_section_points(data: dict, segments_per_semicircle: int = SEGMENTS_PER_SEMICIRCLE) -> dict:
    """Pipeline geometrico compartilhado por todos os writers: le entidades, seleciona a
    LWPOLYLINE principal, discretiza bulges, limpa duplicatas e recentraliza (sem escala).

    Isolado numa funcao para que os writers r12-*-lowres reusem exatamente a mesma logica
    da LWPOLYLINE principal (`ezdxf-lwpolyline`/`r12-polyline`), variando apenas a resolucao
    de discretizacao dos arcos - a selecao de entidade e a normalizacao de coordenadas nunca
    mudam entre variantes.
    """
    all_entities = sp_io.extract_entities(data)
    lwpolylines = sp_io.extract_lwpolylines(data)

    ignored_counts: dict[str, int] = {}
    for e in all_entities:
        kind = str(e.get("entity", "?")).upper()
        if kind != "LWPOLYLINE":
            ignored_counts[kind] = ignored_counts.get(kind, 0) + 1

    selected = select_main_lwpolyline(lwpolylines)
    raw_points = [(float(p[0]), float(p[1])) for p in selected.get("points", []) if len(p) >= 2]
    raw_bulges = [float(b) for b in selected.get("bulges", [])]

    original_bbox = geometry.bbox(raw_points)

    expanded = expand_polyline(raw_points, raw_bulges, segments_per_semicircle)
    expanded_bbox = geometry.bbox(expanded)
    cleaned = dedup_consecutive(expanded)

    min_x, min_y, max_x, max_y = expanded_bbox
    mid_x = (min_x + max_x) / 2.0
    points_local = [(x - mid_x, y - min_y) for x, y in cleaned]

    local_bbox = geometry.bbox(points_local)

    return {
        "selected": selected,
        "ignored_counts": ignored_counts,
        "raw_points": raw_points,
        "raw_bulges": raw_bulges,
        "original_bbox": original_bbox,
        "expanded_bbox": expanded_bbox,
        "points_local": points_local,
        "local_bbox": local_bbox,
        "width": local_bbox[2] - local_bbox[0],
        "height": local_bbox[3] - local_bbox[1],
        "segments_per_semicircle": segments_per_semicircle,
    }


def validate_json_file(json_path: Path) -> tuple[bool, str]:
    """Valida com jq se disponivel, senao com json.load (mesmo criterio de scripts/convert_sections.py)."""
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


def write_preview(points: list[Point], preview_path: Path, title: str) -> str | None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return "matplotlib nao instalado - preview nao gerado"

    coords = points + [points[0]]
    xs, ys = zip(*coords)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(xs, ys, "-o", markersize=2, linewidth=1)
    ax.set_aspect("equal")
    ax.set_title(title)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(preview_path, dpi=150)
    plt.close(fig)
    return None


def build_minimal_document(points_local: list[Point]) -> "ezdxf.document.Drawing":
    """Monta um ezdxf.Drawing minimo: 1 LWPOLYLINE fechada, layer SECTION, $INSUNITS=6.

    Remove os dicionarios padrao que o ezdxf sempre cria em um documento novo
    (ver PURGEABLE_ROOTDICT_KEYS) e que nao tem nenhuma relacao com o DWG de
    origem - sao apenas boilerplate do template do ezdxf.
    """
    doc = ezdxf.new("R2000")
    doc.header["$INSUNITS"] = 6

    if "SECTION" not in doc.layers:
        doc.layers.add("SECTION")

    msp = doc.modelspace()
    msp.add_lwpolyline(points_local, format="xy", close=True, dxfattribs={"layer": "SECTION"})

    rootdict = doc.rootdict
    for key in PURGEABLE_ROOTDICT_KEYS:
        if key not in rootdict:
            continue
        obj = rootdict.get(key)
        if hasattr(obj, "items"):
            for _name, child in list(obj.items()):
                try:
                    doc.objects.delete_entity(child)
                except Exception:  # noqa: BLE001 - purga best-effort, nao critica
                    pass
        try:
            doc.objects.delete_entity(obj)
            del rootdict[key]
        except Exception:  # noqa: BLE001 - dicionario ainda em uso, mantem
            pass

    return doc


def inject_r12_insunits(dxf_path: Path, insunits: int = 6) -> None:
    """Injeta \\$INSUNITS/70/<valor> logo apos \\$ACADVER/1/AC1009 no HEADER.

    O ezdxf recusa escrever \\$INSUNITS para DXF R12 ("Drawing units ($INSUNITS) are not
    exported for DXF R12"), pois essa variavel so faz parte do padrao a partir do R2000.
    Isso e apenas um pequeno patch textual de 4 linhas no HEADER ja escrito pelo ezdxf -
    nao e uma reescrita manual do DXF (que continua sendo gerado inteiramente pelo ezdxf).
    """
    lines = dxf_path.read_text(encoding="utf-8").splitlines()
    try:
        acadver_idx = lines.index("$ACADVER")
    except ValueError as exc:
        raise RuntimeError(f"'$ACADVER' nao encontrado em {dxf_path}") from exc

    # lines[acadver_idx-1] == '9', lines[acadver_idx+1] == '1', lines[acadver_idx+2] == 'AC1009'
    insert_at = acadver_idx + 3
    patch = ["9", "$INSUNITS", "70", str(insunits)]
    lines[insert_at:insert_at] = patch
    dxf_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_r12_polyline_document(points_local: list[Point], layer: str = "SECTION") -> "ezdxf.document.Drawing":
    """Monta um ezdxf.Drawing R12/AC1009 com POLYLINE 2D classica (VERTEX + SEQEND),
    fechada, sem LWPOLYLINE/CIRCLE/ARC/LINE.

    Tentativa alternativa (manual, header+ENTITIES puro, sem TABLES/BLOCKS) foi testada e
    descartada: o `dxf2dwg` desta instalacao do LibreDWG rejeita esse arquivo com
    "ERROR: dwg.block_control and HEADER.BLOCK_CONTROL_OBJECT missing" - R12 ainda precisa
    de um BLOCK_CONTROL/Model_Space minimo para o LibreDWG aceitar. Por isso usamos o
    caminho ezdxf (`add_polyline2d`), que ja inclui esse minimo necessario, mantendo o
    arquivo bem mais enxuto que a variante R2000/LWPOLYLINE (sem OBJECTS, sem CLASSES,
    sem dicionarios ACAD_*, que so existem a partir do R2000).
    """
    doc = ezdxf.new("R12")
    if layer not in doc.layers:
        doc.layers.add(layer)
    msp = doc.modelspace()
    msp.add_polyline2d(points_local, close=True, dxfattribs={"layer": layer})
    return doc


def build_r12_lines_document(points_local: list[Point], layer: str = "SECTION") -> "ezdxf.document.Drawing":
    """Variante diagnostica: R12 com segmentos LINE independentes (sem POLYLINE), fechando
    o contorno (ultimo ponto -> primeiro ponto incluido). So para testar import no VPRO."""
    doc = ezdxf.new("R12")
    if layer not in doc.layers:
        doc.layers.add(layer)
    msp = doc.modelspace()
    n = len(points_local)
    for i in range(n):
        msp.add_line(points_local[i], points_local[(i + 1) % n], dxfattribs={"layer": layer})
    return doc


def validate_r12_structure_ezdxf(dxf_path: Path, expect_entity: str) -> dict:
    """Le o DXF gerado com ezdxf (leitura auxiliar, nunca escrita) e confirma estrutura basica.

    expect_entity: "POLYLINE" ou "LINE".
    """
    result: dict = {"ok": True, "messages": []}
    doc = ezdxf.readfile(dxf_path)
    result["dxfversion"] = doc.dxfversion
    if doc.dxfversion != "AC1009":
        result["ok"] = False
        result["messages"].append(f"versao inesperada: {doc.dxfversion} (esperado AC1009)")

    msp = doc.modelspace()
    counts = Counter(e.dxftype() for e in msp)
    result["entity_counts"] = dict(counts)

    for forbidden in ("LWPOLYLINE", "CIRCLE", "ARC", "SPLINE"):
        if counts.get(forbidden, 0) > 0:
            result["ok"] = False
            result["messages"].append(f"entidade proibida presente: {forbidden} ({counts[forbidden]}x)")

    if expect_entity == "POLYLINE":
        if counts.get("LINE", 0) > 0:
            result["ok"] = False
            result["messages"].append(f"LINE presente ({counts['LINE']}x), esperado 0 no modo polyline")
        if counts.get("POLYLINE", 0) != 1:
            result["ok"] = False
            result["messages"].append(f"esperado exatamente 1 POLYLINE, encontrado {counts.get('POLYLINE', 0)}")
        points: list[Point] = []
        is_closed = None
        for e in msp:
            if e.dxftype() == "POLYLINE":
                is_closed = bool(e.is_closed)
                points = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
        result["closed"] = is_closed
        if not is_closed:
            result["ok"] = False
            result["messages"].append("POLYLINE nao fechada (is_closed=False)")
        result["points"] = points
    else:  # LINE-based diagnostic: so reporta contagem/bbox, sem exigir "closed"
        result["points"] = None
        if counts.get("POLYLINE", 0) > 0:
            result["ok"] = False
            result["messages"].append("POLYLINE inesperada no modo lines-lowres")

    all_points = []
    for e in msp:
        if e.dxftype() == "POLYLINE":
            all_points.extend((v.dxf.location.x, v.dxf.location.y) for v in e.vertices)
        elif e.dxftype() == "LINE":
            all_points.append((e.dxf.start.x, e.dxf.start.y))
            all_points.append((e.dxf.end.x, e.dxf.end.y))
    result["bbox"] = geometry.bbox(all_points) if all_points else None

    return result


_NAN_TOKEN_RE = re.compile(r"(?<![\w.])-?nan(?![\w])")


def _load_dwgread_json_lenient(json_path: Path) -> dict:
    """Como `section_pipeline.libredwg.load_dwgread_json`, mas tolera tokens `-nan`/`nan`
    soltos que o `dwgread -O JSON` as vezes escreve em campos irrelevantes de objetos
    auxiliares (ex.: `base_pt` de um BLOCK_HEADER sem xref real) - invalido em JSON estrito,
    mas aceito por parsers tolerantes como `jq` (por isso `jq empty` passa nesses arquivos
    mesmo quando `json.load` reclama). Isolado aqui de proposito: nao mexe na funcao
    compartilhada `load_dwgread_json`, que deve continuar estrita para o resto do pipeline.
    """
    text = json_path.read_text(encoding="utf-8")
    sanitized = _NAN_TOKEN_RE.sub("0.0", text)
    return json.loads(sanitized)


def roundtrip_validate_r12(
    dxf_path: Path, reports_dir: Path, roundtrip_stem: str, expect_polyline: bool = True
) -> dict:
    """dxf2dwg + dwgread -O JSON + jq empty, com artefatos PERSISTIDOS (nao tempdir), como
    pedido explicitamente para o perfil r12: section/reports/<stem>_roundtrip.dwg/.json.

    NOTA (limitacao conhecida do LibreDWG 0.14.8390 para JSON de origem R12, verificada
    empiricamente): o `dwgread -O JSON` sempre imprime "ERROR: iconv "" failed with errno 84"
    para DWGs de origem R12 e, em alguns objetos auxiliares sem geometria real (ex.: bloco
    sem xref), escreve um token `-nan` em vez de `0.0` num campo `base_pt` - invalido em JSON
    estrito. Isso NAO trunca o arquivo nem afeta a POLYLINE/VERTEX da nossa secao; e tratado
    de forma tolerante em `_load_dwgread_json_lenient`. Mesmo assim, por causa dessa mensagem
    "ERROR:" e da nao-conformidade estrita do JSON, o resultado deste writer nunca deve ser
    chamado de "validado" - so "VPRO legacy candidate", como pedido.

    No formato antigo, a POLYLINE nao guarda os vertices embutidos (ao contrario da
    LWPOLYLINE): cada VERTEX e um objeto separado no JSON (entity=VERTEX_2D, campo `point`),
    ligados por handle a entity=POLYLINE_2D e terminados por um SEQEND.
    """
    report: dict = {"ok": True, "commands": [], "messages": []}

    roundtrip_dwg = reports_dir / f"{roundtrip_stem}_roundtrip.dwg"
    roundtrip_json = reports_dir / f"{roundtrip_stem}_roundtrip.json"

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
        # `run_checked` trata a mensagem "ERROR: iconv..." (ver nota acima) como fatal e
        # levanta RuntimeError, mas o dwgread normalmente ainda termina com "SUCCESS" e
        # escreve o JSON inteiro (rc=0). Seguimos para inspecionar o JSON mesmo assim.
        report["messages"].append(
            "dwgread -O JSON reportou 'ERROR: iconv' (limitacao conhecida do LibreDWG para "
            f"JSON de origem R12 - ver nota da funcao); {exc}"
        )
        report["commands"].append(f"dwgread -O JSON -o {roundtrip_json} {roundtrip_dwg}")

    if not roundtrip_json.exists():
        report["ok"] = False
        report["messages"].append(f"{roundtrip_json} nao foi gerado - round-trip incompleto")
        return report

    jq_ok, jq_message = validate_json_file(roundtrip_json)
    report["commands"].append(f"jq empty {roundtrip_json}")
    report["messages"].append(f"jq empty / json.load: {'OK' if jq_ok else 'FALHOU'} - {jq_message}")
    report["ok"] = report["ok"] and jq_ok

    if not jq_ok:
        return report

    try:
        data = _load_dwgread_json_lenient(roundtrip_json)
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

    polyline_like = [e for e in entities if str(e.get("entity", "")).upper() in ("POLYLINE", "POLYLINE_2D")]
    report["polyline_count"] = len(polyline_like)

    if expect_polyline and len(polyline_like) != 1:
        report["ok"] = False
        report["messages"].append(
            f"esperada exatamente 1 entidade tipo POLYLINE/POLYLINE_2D, encontrada {len(polyline_like)}"
        )
    for residual in ("LWPOLYLINE", "ARC", "CIRCLE"):
        if counts.get(residual, 0) > 0:
            report["ok"] = False
            report["messages"].append(f"entidade residual {residual} encontrada ({counts[residual]}x)")
    if expect_polyline and counts.get("LINE", 0) > 0:
        report["ok"] = False
        report["messages"].append(f"LINE residual encontrada ({counts['LINE']}x), esperado 0 no modo polyline")

    if polyline_like:
        entity = polyline_like[0]
        flag = entity.get("flag", 0)
        # POLYLINE_2D usa o bit 0 (valor 1) do grupo 70 padrao do DXF para "closed" -
        # diferente do bit 512 que o dwgread usa para LWPOLYLINE (ver roundtrip_validate).
        is_closed = isinstance(flag, int) and bool(flag & 1)
        report["closed"] = is_closed
        if not is_closed:
            report["ok"] = False
            report["messages"].append("POLYLINE do round-trip nao esta fechada (flag sem bit 0)")

        vertex_entities = [e for e in entities if str(e.get("entity", "")).upper() in ("VERTEX", "VERTEX_2D")]
        rt_points = [
            (float(v["point"][0]), float(v["point"][1]))
            for v in vertex_entities
            if isinstance(v.get("point"), list) and len(v["point"]) >= 2
        ]
        report["roundtrip_point_count"] = len(rt_points)
        if rt_points:
            basic = validation.validate_polygon_basic(rt_points)
            report["messages"].extend(f"round-trip: {c}" for c in basic.checks)
            report["messages"].extend(f"round-trip AVISO: {w}" for w in basic.warnings)
            report["messages"].extend(f"round-trip ERRO: {e}" for e in basic.errors)
            report["ok"] = report["ok"] and basic.ok
            report["roundtrip_bbox"] = geometry.bbox(rt_points)

    return report


def _dxf2dwg_log_has_only_known_benign_errors(log_path: Path) -> bool:
    """True se as unicas linhas 'ERROR' do log do dxf2dwg baterem com KNOWN_BENIGN_DXF2DWG_ERROR."""
    if not log_path.exists():
        return False
    error_lines = [line for line in log_path.read_text(encoding="utf-8").splitlines() if "ERROR" in line]
    return bool(error_lines) and all(KNOWN_BENIGN_DXF2DWG_ERROR in line for line in error_lines)


def roundtrip_validate(dxf_path: Path, reports_dir: Path) -> dict:
    """dxf2dwg + dwgread -O JSON em pasta temporaria, depois inspeciona o JSON resultante."""
    report: dict = {"commands": [], "ok": True, "messages": []}

    with tempfile.TemporaryDirectory(prefix="process_vpro_dxf_") as tmp:
        tmp_dwg = Path(tmp) / f"{dxf_path.stem}.dwg"
        tmp_json = Path(tmp) / f"{dxf_path.stem}.json"

        try:
            dxf_to_dwg(dxf_path, tmp_dwg, reports_dir, overwrite=True)
            report["commands"].append(f"dxf2dwg -y -o {tmp_dwg} {dxf_path}")
        except Exception as exc:  # noqa: BLE001
            dxf2dwg_log = reports_dir / f"{dxf_path.stem}.dxf2dwg.log"
            if tmp_dwg.exists() and _dxf2dwg_log_has_only_known_benign_errors(dxf2dwg_log):
                report["messages"].append(
                    "dxf2dwg AVISO (conhecido, nao fatal): 'Duplicate handle' no dicionario "
                    "ACAD_MATERIAL padrao do ezdxf (nao relacionado a geometria da secao); "
                    f"rc=0 e DWG gerado normalmente - ver {dxf2dwg_log}"
                )
                report["commands"].append(f"dxf2dwg -y -o {tmp_dwg} {dxf_path}")
            else:
                report["ok"] = False
                report["messages"].append(f"dxf2dwg falhou: {exc}")
                return report

        try:
            dwg_to_json(tmp_dwg, tmp_json, reports_dir)
            report["commands"].append(f"dwgread -O JSON -o {tmp_json} {tmp_dwg}")
        except Exception as exc:  # noqa: BLE001
            report["ok"] = False
            report["messages"].append(f"dwgread -O JSON falhou: {exc}")
            return report

        ok, message = validate_json_file(tmp_json)
        report["messages"].append(f"validacao JSON (jq/json.load): {'OK' if ok else 'FALHOU'} - {message}")
        report["ok"] = report["ok"] and ok

        data = load_dwgread_json(tmp_json)
        entities = sp_io.extract_entities(data)
        counts: dict[str, int] = {}
        for e in entities:
            kind = str(e.get("entity", "?")).upper()
            counts[kind] = counts.get(kind, 0) + 1
        report["entity_counts"] = counts

        polylines = sp_io.extract_lwpolylines(data)
        report["lwpolyline_count"] = len(polylines)

        if len(polylines) != 1:
            report["ok"] = False
            report["messages"].append(f"esperado exatamente 1 LWPOLYLINE, encontrado {len(polylines)}")
        for residual in ("LINE", "ARC", "CIRCLE"):
            if counts.get(residual, 0) > 0:
                report["ok"] = False
                report["messages"].append(f"entidade residual {residual} encontrada ({counts[residual]}x)")

        if polylines:
            entity = polylines[0]
            # No JSON de `dwgread -O JSON` o bit "closed" da LWPOLYLINE fica no valor
            # 512 (0x200), NAO no bit 0 do grupo 70 do DXF puro. Confirmado
            # empiricamente: uma LWPOLYLINE escrita com close=True pelo ezdxf, apos
            # round-trip dxf2dwg->dwgread, sai com flag=512; com close=False, flag=0.
            # (flag&1 e a convencao certa para o group-70 de um DXF lido direto, por
            # isso ainda checamos os dois bits aqui.)
            flag = entity.get("flag", 0)
            is_closed = bool(entity.get("closed")) or (
                isinstance(flag, int) and bool(flag & 1 or flag & 512)
            )
            report["closed"] = is_closed
            if not is_closed:
                report["ok"] = False
                report["messages"].append("LWPOLYLINE do round-trip nao esta fechada (flag sem bit 'closed')")

            rt_points = [(float(p[0]), float(p[1])) for p in entity.get("points", []) if len(p) >= 2]
            report["roundtrip_points"] = rt_points

            basic = validation.validate_polygon_basic(rt_points)
            report["messages"].extend(f"round-trip: {c}" for c in basic.checks)
            report["messages"].extend(f"round-trip AVISO: {w}" for w in basic.warnings)
            report["messages"].extend(f"round-trip ERRO: {e}" for e in basic.errors)
            report["ok"] = report["ok"] and basic.ok

            if geometry.is_probably_scaled_by_001(rt_points):
                report["ok"] = False
                report["messages"].append("round-trip: bbox sugere fator de escala 0.01 aplicado por engano")

            if rt_points:
                min_x, min_y, max_x, max_y = geometry.bbox(rt_points)
                report["roundtrip_bbox"] = (min_x, min_y, max_x, max_y)

    return report


def run_ezdxf_lwpolyline(
    geo: dict, input_json: Path, output_dxf: Path, reports_dir: Path, preview_dir: Path, section_name: str
) -> int:
    """Writer padrao (existente, inalterado em comportamento): DXF R2000 com LWPOLYLINE via ezdxf."""
    report_path = reports_dir / f"{section_name}_vpro_report.md"
    preview_path = preview_dir / f"{section_name}_vpro.png"

    points_local = geo["points_local"]
    basic = validation.validate_polygon_basic(points_local)

    doc = build_minimal_document(points_local)
    doc.saveas(str(output_dxf))
    logger.info("DXF VPRO-safe escrito em %s", output_dxf)

    roundtrip = roundtrip_validate(output_dxf, reports_dir)
    ok = basic.ok and roundtrip["ok"]

    lines = [
        f"# Relatorio VPRO-safe DXF - {section_name}",
        "",
        f"Fonte: `{input_json}`",
        f"Saida: `{output_dxf}`",
        "",
        "## Selecao da entidade",
        "",
        f"- Entidade selecionada: LWPOLYLINE index={geo['selected'].get('index')} handle={geo['selected'].get('handle')}",
        f"- Entidades ignoradas (nao LWPOLYLINE): {geo['ignored_counts'] or 'nenhuma'}",
        "",
        "## Geometria original",
        "",
        f"- Numero original de pontos (vertices): {len(geo['raw_points'])}",
        f"- Numero original de bulges: {len(geo['raw_bulges'])} (nao-zero: {sum(1 for b in geo['raw_bulges'] if abs(b) > 1e-9)})",
        f"- Bounding box original (vertices, coords absolutas do DWG): {geo['original_bbox']}",
        f"- Bounding box original apos discretizar arcos (coords absolutas): {geo['expanded_bbox']}",
        f"- Numero final de pontos apos discretizacao e limpeza: {len(points_local)}",
        "",
        "## Geometria local (sem escala aplicada)",
        "",
        f"- Bounding box local: {geo['local_bbox']}",
        f"- Largura: {geo['width']:.4f} m",
        f"- Altura: {geo['height']:.4f} m",
        "",
        "## Validacao geometrica (local, pre-escrita)",
        "",
    ]
    lines += [f"  - {c}" for c in basic.checks]
    lines += [f"  - AVISO: {w}" for w in basic.warnings]
    lines += [f"  - ERRO: {e}" for e in basic.errors]

    lines += [
        "",
        "## Round-trip LibreDWG (dxf2dwg + dwgread -O JSON)",
        "",
        f"- Comandos executados: {roundtrip['commands']}",
        f"- Entidades no DXF final (round-trip): {roundtrip.get('entity_counts', {})}",
        f"- LWPOLYLINE no round-trip: {roundtrip.get('lwpolyline_count', 0)}",
        f"- Fechada (closed): {roundtrip.get('closed')}",
        f"- Bounding box (round-trip): {roundtrip.get('roundtrip_bbox')}",
    ]
    lines += [f"  - {m}" for m in roundtrip["messages"]]

    preview_message = write_preview(points_local, preview_path, f"{section_name} (VPRO-safe)")
    if preview_message is None:
        lines.append("")
        lines.append(f"Preview gerado em `{preview_path}`.")
    else:
        lines.append("")
        lines.append(f"Preview nao gerado: {preview_message}")

    lines.append("")
    lines.append(f"**Resultado: {'PASSOU' if ok else 'FALHOU'} - {'VPRO-safe' if ok else 'NAO VPRO-safe'}**")
    lines.append("")

    sp_io.save_report(report_path, "\n".join(lines))
    logger.info("relatorio: %s", report_path)
    return 0 if ok else 1


def run_r12_family(
    writer: str,
    geo: dict,
    input_json: Path,
    output_dxf: Path,
    reports_dir: Path,
    preview_dir: Path,
) -> int:
    """Writers legacy R12: r12-polyline (principal), r12-polyline-lowres e r12-lines-lowres
    (diagnosticos). Nomeia relatorio/preview/round-trip a partir do stem de --output-dxf,
    para bater exatamente com os caminhos pedidos (ex.: LA25_vpro_r12_polyline_report.md).
    """
    stem = output_dxf.stem
    report_path = reports_dir / f"{stem}_report.md"
    preview_path = preview_dir / f"{stem}.png"
    points_local = geo["points_local"]

    is_lines = writer == "r12-lines-lowres"
    entity_kind = "LINE" if is_lines else "POLYLINE"

    if is_lines:
        doc = build_r12_lines_document(points_local)
    else:
        doc = build_r12_polyline_document(points_local)
    doc.saveas(str(output_dxf))
    inject_r12_insunits(output_dxf, insunits=6)
    logger.info("DXF R12 (%s) escrito em %s", writer, output_dxf)

    ezdxf_check = validate_r12_structure_ezdxf(output_dxf, entity_kind)
    roundtrip = roundtrip_validate_r12(output_dxf, reports_dir, stem, expect_polyline=not is_lines)

    ok = ezdxf_check["ok"] and roundtrip["ok"]

    lines = [
        f"# Relatorio DXF legacy R12 ({writer}) - {stem}",
        "",
        f"Fonte: `{input_json}`",
        f"Saida: `{output_dxf}`",
        f"Writer: `{writer}`",
        f"Segmentos por semicircunferencia usados na discretizacao: {geo['segments_per_semicircle']}",
        "",
        "## Selecao da entidade (mesma geometria do preview LA25_vpro.png, sem recalculo)",
        "",
        f"- Entidade fonte selecionada: LWPOLYLINE index={geo['selected'].get('index')} handle={geo['selected'].get('handle')}",
        f"- Numero de pontos apos discretizacao/limpeza: {len(points_local)}",
        f"- Bounding box local: {geo['local_bbox']}",
        f"- Largura: {geo['width']:.4f} m",
        f"- Altura: {geo['height']:.4f} m",
        "",
        "## Leitura estrutural com ezdxf (versao, entidades, bbox)",
        "",
        f"- Versao DXF: {ezdxf_check.get('dxfversion')} (esperado AC1009)",
        f"- Entidades no arquivo: {ezdxf_check.get('entity_counts')}",
        f"- Fechada (POLYLINE): {ezdxf_check.get('closed')}" if not is_lines else "- (modo LINE: sem conceito de 'fechada' unico)",
        f"- Bounding box (ezdxf): {ezdxf_check.get('bbox')}",
    ]
    lines += [f"  - ERRO: {m}" for m in ezdxf_check["messages"]]

    lines += [
        "",
        "## Round-trip LibreDWG (dxf2dwg + dwgread -O JSON + jq empty)",
        "",
        f"- Comandos executados: {roundtrip['commands']}",
        f"- Entidades no round-trip: {roundtrip.get('entity_counts', {})}",
        f"- Entidades tipo POLYLINE/POLYLINE_2D no round-trip: {roundtrip.get('polyline_count')}",
        f"- Fechada (round-trip): {roundtrip.get('closed')}",
        f"- Bounding box (round-trip): {roundtrip.get('roundtrip_bbox')}",
    ]
    lines += [f"  - {m}" for m in roundtrip["messages"]]

    preview_message = write_preview(points_local, preview_path, f"{stem} ({writer})")
    if preview_message is None:
        lines.append("")
        lines.append(f"Preview gerado em `{preview_path}`.")
    else:
        lines.append("")
        lines.append(f"Preview nao gerado: {preview_message}")

    lines.append("")
    lines.append(
        f"**Resultado: {'estrutura OK' if ok else 'FALHOU'} - VPRO legacy candidate "
        "(NAO declarar VPRO-safe; validar importando no VPRO antes de confiar neste arquivo)**"
    )
    lines.append("")

    sp_io.save_report(report_path, "\n".join(lines))
    logger.info("relatorio: %s", report_path)
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    input_json = Path(args.input_json)
    output_dxf = Path(args.output_dxf)
    reports_dir = Path(args.reports)
    preview_dir = Path(args.preview)
    section_name = args.section_name
    writer = args.writer

    reports_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    output_dxf.parent.mkdir(parents=True, exist_ok=True)

    if output_dxf.exists() and not args.force:
        logger.warning("%s ja existe - use --force para sobrescrever", output_dxf)
        if writer == "ezdxf-lwpolyline":
            report_path = reports_dir / f"{section_name}_vpro_report.md"
        else:
            report_path = reports_dir / f"{output_dxf.stem}_report.md"
        sp_io.save_report(
            report_path,
            f"# Relatorio - {output_dxf.stem}\n\n`{output_dxf}` ja existe - nao sobrescrito (use --force).\n",
        )
        return 1

    data = sp_io.load_json(input_json)

    if writer in ("r12-polyline-lowres", "r12-lines-lowres"):
        geo = compute_section_points(data, segments_per_semicircle=LOWRES_SEGMENTS_PER_SEMICIRCLE)
    else:
        geo = compute_section_points(data, segments_per_semicircle=SEGMENTS_PER_SEMICIRCLE)

    if writer == "ezdxf-lwpolyline":
        return run_ezdxf_lwpolyline(geo, input_json, output_dxf, reports_dir, preview_dir, section_name)
    return run_r12_family(writer, geo, input_json, output_dxf, reports_dir, preview_dir)


if __name__ == "__main__":
    sys.exit(main())
