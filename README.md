# secpro

Repositorio para armazenar e processar secoes transversais de lajes/almas/pecas estruturais:
manter os arquivos de entrada em DWG, gerar DXF validado (via LibreDWG) e gerar JSON
intermediario para uso posterior em MIDAS/VPRO/scripts.

Este repositorio **nao** edita arquivos do projeto MIDAS Civil - ele produz DXF/JSON que
depois sao consumidos por outros fluxos.

## Estrutura

```
.
├── section/
│   ├── DWG/       # DWG de entrada
│   ├── DXF/       # DXF gerado/validado (aceito pelo VPRO)
│   ├── json/      # JSON intermediario (saida de `dwgread -O JSON` ou derivado)
│   ├── reports/   # relatorios .md de conversao/validacao
│   └── preview/   # PNG/SVG de conferencia visual
├── scripts/                 # CLI (usa a .venv do projeto)
│   ├── convert_sections.py  # DWG -> DXF + JSON + relatorio + preview
│   ├── validate_sections.py # valida DXF via round-trip LibreDWG + geometria
│   ├── recover_previous_temp.py  # recupera artefatos esquecidos em /tmp
│   └── libredwg_tools.py    # localizacao/diagnostico dos binarios LibreDWG
├── src/section_pipeline/    # pacote Python reutilizavel (geometria, io, libredwg, validacao)
├── .vscode/                 # interpreter, tasks e launch configs
└── .claude/CLAUDE.md        # regras permanentes para trabalho assistido por IA nesta repo
```

## Ambiente

A `.venv/` ja existe neste repositorio (Python 3.14, criada com `python3 -m venv .venv`).
Nao criar uma nova.

Ativar:

```bash
source .venv/bin/activate
```

Instalar dependencias (modo editable, expoe `section_pipeline` no PYTHONPATH):

```bash
.venv/bin/python -m pip install -e .
```

Dependencias principais: `ezdxf` (leitura/validacao auxiliar, nao escrita de DXF final),
`matplotlib` (preview) e `shapely` (validacao geometrica). CLI feita com `argparse` puro.

## LibreDWG

Os scripts usam os binarios do LibreDWG (`dwgread`, `dwg2dxf`, `dxf2dwg`, `dxfwrite`,
`dwgadd`), procurados primeiro no `PATH` e depois em
`/home/hcmelo/projects/libredwg/programs/` como fallback. Toda geracao/validacao de
DWG/DXF passa por esses binarios - nenhum DXF final e escrito manualmente por
concatenacao de string.

## VPRO

O VPRO so aceita DXF. O DXF produzido em `section/DXF/` e sempre passado por
`dxf2dwg` + `dwgread -O JSON` antes de ser considerado valido, garantindo que o
arquivo realmente abre no LibreDWG (proxy razoavel de compatibilidade).

## Uso

Colocar os `.dwg` de entrada em `section/DWG/`.

Recuperar arquivos esquecidos de uma rodada anterior (dry-run por padrao, nunca apaga nada):

```bash
python scripts/recover_previous_temp.py
python scripts/recover_previous_temp.py --copy   # copia de fato
```

Converter DWG -> DXF + JSON (nao sobrescreve saida existente sem `--force`):

```bash
python scripts/convert_sections.py
python scripts/convert_sections.py --force --verbose
```

Validar os DXF em `section/DXF/` (round-trip LibreDWG + checagens geometricas,
incluindo checagens especificas para secoes `LA26`):

```bash
python scripts/validate_sections.py
```

O resumo agregado fica em `section/reports/validation_summary.md`; cada conversao
tambem gera um relatorio individual em `section/reports/<nome>.convert.md`.

### Comando rapido

```bash
source .venv/bin/activate
python scripts/recover_previous_temp.py
python scripts/convert_sections.py
python scripts/validate_sections.py
```
