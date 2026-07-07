"""Wrappers finos sobre os executaveis do LibreDWG.

Esta e a UNICA camada que deve falar com dwgread/dwg2dxf/dxf2dwg/dxfwrite.
Nenhum codigo deste pacote escreve DXF manualmente por concatenacao de string;
a geracao/validacao final de DXF sempre passa por aqui.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

_CANDIDATE_NAMES = ("dwgread", "dwg2dxf", "dxf2dwg", "dxfwrite", "dwgadd")

_FALLBACK_DIR = Path("/home/hcmelo/projects/libredwg/programs")

_ERROR_MARKERS = ("ERROR", "FATAL", "CRITICAL", "segmentation fault", "Segmentation fault")


def find_tool(name: str) -> Path:
    """Localiza um executavel do LibreDWG: primeiro no PATH, depois no fallback local."""
    if name not in _CANDIDATE_NAMES:
        raise ValueError(f"ferramenta desconhecida: {name}")

    on_path = shutil.which(name)
    if on_path:
        return Path(on_path)

    fallback = _FALLBACK_DIR / name
    if fallback.is_file() and fallback.stat().st_mode & 0o111:
        return fallback

    raise FileNotFoundError(
        f"nao encontrei '{name}' no PATH nem em {_FALLBACK_DIR}. "
        f"Confira a build do LibreDWG em /home/hcmelo/projects/libredwg."
    )


def run_checked(
    command: list[str], log_file: Path, timeout: int = 60
) -> subprocess.CompletedProcess:
    """Executa um comando, grava log e falha (RuntimeError) em erro real.

    Warnings sao tolerados mas registrados no log. Falha se:
    - returncode != 0
    - stdout/stderr contiver ERROR, FATAL, CRITICAL ou segmentation fault
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    log_lines = [
        f"$ {' '.join(command)}",
        f"returncode={result.returncode}",
        "--- stdout ---",
        result.stdout or "",
        "--- stderr ---",
        result.stderr or "",
    ]
    log_file.write_text("\n".join(log_lines), encoding="utf-8")

    combined = f"{result.stdout}\n{result.stderr}"
    hit_error = any(marker in combined for marker in _ERROR_MARKERS)

    if result.returncode != 0:
        raise RuntimeError(
            f"comando falhou (returncode={result.returncode}): {' '.join(command)}\n"
            f"veja log em {log_file}"
        )
    if hit_error:
        raise RuntimeError(
            f"comando reportou erro na saida: {' '.join(command)}\nveja log em {log_file}"
        )

    if "warning" in combined.lower():
        # warnings sao aceitos, mas ja estao gravados no log_file para auditoria.
        pass

    return result


def libredwg_versions() -> dict[str, str]:
    """Retorna a string de versao de cada ferramenta LibreDWG encontrada."""
    versions: dict[str, str] = {}
    for name in _CANDIDATE_NAMES:
        try:
            tool = find_tool(name)
        except FileNotFoundError:
            versions[name] = "nao encontrado"
            continue
        try:
            result = subprocess.run(
                [str(tool), "--version"], capture_output=True, text=True, timeout=10
            )
            output = (result.stdout or result.stderr).strip().splitlines()
            versions[name] = output[0] if output else "versao desconhecida"
        except Exception as exc:  # noqa: BLE001 - relatorio de diagnostico, nao critico
            versions[name] = f"erro ao consultar versao: {exc}"
    return versions


def dwg_to_dxf(
    dwg_path: Path, dxf_path: Path, log_dir: Path, timeout: int = 60, overwrite: bool = False
) -> Path:
    """Converte DWG -> DXF usando dwg2dxf."""
    tool = find_tool("dwg2dxf")
    dxf_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{dwg_path.stem}.dwg2dxf.log"
    command = [str(tool)]
    if overwrite:
        command.append("-y")
    command += ["-o", str(dxf_path), str(dwg_path)]
    run_checked(command, log_file, timeout=timeout)
    return dxf_path


def dxf_to_dwg(
    dxf_path: Path, dwg_path: Path, log_dir: Path, timeout: int = 60, overwrite: bool = False
) -> Path:
    """Converte DXF -> DWG usando dxf2dwg (usado para validar DXFs sem DWG de origem)."""
    tool = find_tool("dxf2dwg")
    dwg_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{dxf_path.stem}.dxf2dwg.log"
    command = [str(tool)]
    if overwrite:
        command.append("-y")
    command += ["-o", str(dwg_path), str(dxf_path)]
    run_checked(command, log_file, timeout=timeout)
    return dwg_path


def dwg_to_json(dwg_path: Path, json_path: Path, log_dir: Path, timeout: int = 60) -> Path:
    """Extrai estrutura do DWG para JSON usando dwgread -O JSON."""
    tool = find_tool("dwgread")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{dwg_path.stem}.dwgread.log"
    run_checked(
        [str(tool), "-O", "JSON", "-o", str(json_path), str(dwg_path)],
        log_file,
        timeout=timeout,
    )
    return json_path


def load_dwgread_json(json_path: Path) -> dict:
    """Le e faz parse do JSON gerado por dwgread -O JSON."""
    with json_path.open(encoding="utf-8") as fh:
        return json.load(fh)
