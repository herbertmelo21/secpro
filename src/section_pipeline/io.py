"""Leitura do JSON do LibreDWG e escrita de relatorios em Markdown."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

Point = tuple[float, float]


def load_json(json_path: Path) -> dict[str, Any]:
    with json_path.open(encoding="utf-8") as fh:
        return json.load(fh)


def extract_entities(dwgread_json: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai a lista de entidades de um JSON gerado por `dwgread -O JSON`.

    O formato do dwgread coloca as entidades sob OBJECTS/ENTITIES conforme a
    versao; tentamos os layouts conhecidos e caimos para lista vazia.
    """
    for key in ("ENTITIES", "entities"):
        if key in dwgread_json and isinstance(dwgread_json[key], list):
            return dwgread_json[key]

    objects = dwgread_json.get("OBJECTS") or dwgread_json.get("objects")
    if isinstance(objects, list):
        return [obj for obj in objects if _looks_like_entity(obj)]

    return []


def _looks_like_entity(obj: Any) -> bool:
    return isinstance(obj, dict) and "entity" in obj


def extract_lwpolylines(dwgread_json: dict[str, Any]) -> list[dict[str, Any]]:
    """Retorna as entidades LWPOLYLINE encontradas no JSON do dwgread."""
    entities = extract_entities(dwgread_json)
    return [e for e in entities if str(e.get("entity", "")).upper() == "LWPOLYLINE"]


def vertices_from_simple_json(simple_json: dict[str, Any]) -> list[Point]:
    """Le o formato simplificado usado neste repo (ver section/json/coordenada_la26.json):
    {"vertices": [[x, y], ...], "closed": bool, ...}
    """
    vertices = simple_json.get("vertices", [])
    return [(float(p[0]), float(p[1])) for p in vertices]


def save_report(report_path: Path, content: str) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(content, encoding="utf-8")
