#!/usr/bin/env python3
"""Procura em /tmp, /var/tmp, /home/hcmelo/tmp e /home/hcmelo/projects por artefatos
de rodadas anteriores de trabalho com secoes (DXF/DWG/JSON/logs/scripts) e copia
(nunca move) os candidatos uteis para dentro desta repo.

Modo padrao: dry-run (so lista candidatos).
Para copiar de fato: --copy

Nunca apaga nada fora da repo. Nunca sobrescreve arquivo ja existente na repo
com o mesmo nome, a menos que --force seja passado.
"""

from __future__ import annotations

import argparse
import datetime
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SEARCH_ROOTS = [
    Path("/tmp"),
    Path("/var/tmp"),
    Path("/home/hcmelo/tmp"),
    Path("/home/hcmelo/projects"),
]

# Diretorios que sao repos/projetos ativos de terceiros (nao "lixo temporario")
# e nunca devem ser varridos como fonte de recuperacao automatica.
EXCLUDE_DIR_NAMES = {"secpro", ".git", ".venv", "node_modules", "__pycache__"}

NAME_KEYWORDS = ("la26", "coordenada", "section", "libredwg")
EXTENSIONS = {".dxf", ".dwg", ".json", ".log", ".py"}

DEST_BY_SUFFIX = {
    ".dxf": "section/DXF",
    ".dwg": "section/json",  # sera sobrescrito abaixo para DWG real
    ".json": "section/json",
    ".log": "section/reports",
    ".py": "scripts/recovered",
}
DEST_BY_SUFFIX[".dwg"] = "section/DWG"


def is_excluded(path: Path) -> bool:
    if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
        return True
    # Sob /home/hcmelo/projects, nao varrer outros repos git (sao projetos ativos
    # de terceiros, nao lixo temporario), a menos que o nome do proprio repo
    # sugira ser parte do experimento (ex.: uma pasta "section-tmp" qualquer).
    projects_root = Path("/home/hcmelo/projects")
    try:
        rel = path.relative_to(projects_root)
    except ValueError:
        return False
    if not rel.parts:
        return False
    top_level = projects_root / rel.parts[0]
    if top_level.name == REPO_ROOT.name:
        return False
    # Qualquer outro repo git em ~/projects e um projeto ativo de terceiros
    # (ex.: libredwg, midas-8345-181-nb), nao lixo de experimento anterior.
    if (top_level / ".git").is_dir():
        return True
    return False


def matches_candidate(path: Path) -> bool:
    if path.suffix.lower() not in EXTENSIONS:
        return False
    name_lower = path.name.lower()
    if path.suffix.lower() == ".py":
        # scripts python so contam se o nome ou algum ancestral sugerir o experimento
        haystack = str(path).lower()
        return any(k in haystack for k in NAME_KEYWORDS)
    if any(k in name_lower for k in NAME_KEYWORDS):
        return True
    return path.suffix.lower() in (".dxf", ".dwg", ".json")


def find_candidates() -> list[Path]:
    candidates: list[Path] = []
    for root in SEARCH_ROOTS:
        if not root.is_dir():
            continue
        try:
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if is_excluded(path):
                    continue
                # limita profundidade para nao varrer a maquina inteira
                try:
                    depth = len(path.relative_to(root).parts)
                except ValueError:
                    continue
                if depth > 4:
                    continue
                if matches_candidate(path):
                    candidates.append(path)
        except PermissionError:
            continue
    return sorted(set(candidates))


def classify(path: Path) -> tuple[str, str]:
    """Retorna (destino_relativo, motivo)."""
    suffix = path.suffix.lower()
    if suffix == ".dwg":
        return "section/DWG", "DWG de entrada/intermediario"
    if suffix == ".dxf":
        return "section/DXF", "DXF final ou candidato"
    if suffix == ".json":
        return "section/json", "JSON de geometria/LibreDWG"
    if suffix == ".log":
        return "section/reports", "log de conversao/validacao"
    if suffix == ".py":
        return "scripts/recovered", "script util da rodada anterior"
    return "section/reports", "sem categoria clara"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--copy", action="store_true", help="copia de fato (padrao: dry-run)")
    parser.add_argument("--force", action="store_true", help="sobrescreve destino existente")
    args = parser.parse_args(argv)

    candidates = find_candidates()

    if not candidates:
        print("Nenhum candidato de rodada anterior encontrado fora da repo.")
        return 0

    print(f"{'COPIANDO' if args.copy else 'DRY-RUN'} - {len(candidates)} candidato(s) encontrado(s):\n")

    copied = []
    skipped = []
    for path in candidates:
        dest_dir, reason = classify(path)
        dest_path = REPO_ROOT / dest_dir / path.name
        status = "copiaria" if not args.copy else "copiado"

        if dest_path.exists() and not args.force:
            print(f"  [SKIP - ja existe] {path} -> {dest_path}")
            skipped.append((path, dest_path, "destino ja existe (use --force)"))
            continue

        print(f"  [{status}] {path} -> {dest_path}  ({reason})")

        if args.copy:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest_path)
            copied.append((path, dest_path, reason))

    if args.copy:
        write_recovery_report(candidates, copied, skipped)
        print(f"\n{len(copied)} arquivo(s) copiado(s). Relatorio: section/reports/recovery_report.md")
    else:
        print("\nNenhum arquivo copiado (dry-run). Rode novamente com --copy para copiar de fato.")

    return 0


def write_recovery_report(
    candidates: list[Path],
    copied: list[tuple[Path, Path, str]],
    skipped: list[tuple[Path, Path, str]],
) -> None:
    now = datetime.datetime.now().isoformat(timespec="seconds")
    lines = [
        "# Relatorio de recuperacao de arquivos temporarios",
        "",
        f"Gerado em: {now}",
        "",
        "## Criterio de selecao",
        "",
        "Busca em /tmp, /var/tmp, /home/hcmelo/tmp e /home/hcmelo/projects (profundidade <= 4), "
        "excluindo esta propria repo e diretorios de build/VCS, por arquivos com extensao "
        ".dxf/.dwg/.json/.log/.py cujo nome (ou caminho, no caso de .py) contenha uma das "
        "palavras-chave: la26, coordenada, section, libredwg; ou qualquer .dxf/.dwg/.json "
        "encontrado nas raizes de busca.",
        "",
        "## Arquivos copiados",
        "",
    ]
    if copied:
        for src, dest, reason in copied:
            lines.append(f"- `{src}` -> `{dest.relative_to(REPO_ROOT)}` ({reason})")
    else:
        lines.append("- nenhum")

    lines += ["", "## Arquivos ignorados (destino ja existia)", ""]
    if skipped:
        for src, dest, reason in skipped:
            lines.append(f"- `{src}` -> `{dest.relative_to(REPO_ROOT)}` : {reason}")
    else:
        lines.append("- nenhum")

    lines += ["", "## Observacao", "", "Os arquivos originais em /tmp (ou onde foram encontrados) NAO foram apagados."]

    report_path = REPO_ROOT / "section" / "reports" / "recovery_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
