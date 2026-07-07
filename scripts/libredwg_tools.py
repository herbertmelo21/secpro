#!/usr/bin/env python3
"""Utilitario de linha de comando para localizar e inspecionar o LibreDWG.

A implementacao (find_tool, run_checked, libredwg_versions) mora em
`section_pipeline.libredwg` para ser reutilizada pelos demais scripts; este
arquivo apenas expoe essas funcoes na pasta scripts/ e oferece um modo
`--versions` para diagnostico rapido.

Uso:
    .venv/bin/python scripts/libredwg_tools.py --versions
"""

from __future__ import annotations

import argparse
import json

from section_pipeline.libredwg import find_tool, libredwg_versions, run_checked

__all__ = ["find_tool", "run_checked", "libredwg_versions"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--versions", action="store_true", help="imprime a versao de cada ferramenta LibreDWG"
    )
    parser.add_argument(
        "--which", metavar="TOOL", help="mostra o caminho resolvido de uma ferramenta especifica"
    )
    args = parser.parse_args()

    if args.which:
        print(find_tool(args.which))
        return 0

    if args.versions or not any(vars(args).values()):
        print(json.dumps(libredwg_versions(), indent=2, ensure_ascii=False))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
