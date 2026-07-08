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
│   ├── preview/   # PNG/SVG de conferencia visual
│   └── ahk/       # scripts AutoHotkey historicos por secao
├── outputs/                 # entregaveis da rodada VPRO-safe ordenada
│   ├── dxf/                 # DXF R12 final (copia canonica em section/DXF/)
│   ├── previews/            # PNG/SVG da ordem de desenho (setas de sentido)
│   ├── autohotkey/          # .ahk gerado a partir do JSON ordenado
│   └── <secao>_outer_ordered.json  # sequencia validada [{"i","x","y"}]
├── docs/notes/              # DECISOES.md e RELATORIO_FINAL.md da organizacao
├── scripts/                 # CLI (usa a .venv do projeto)
│   ├── convert_sections.py  # DWG -> DXF + JSON + relatorio + preview
│   ├── validate_sections.py # valida DXF via round-trip LibreDWG + geometria
│   ├── process_vpro_dxf.py  # JSON LibreDWG -> DXF limpo p/ VPRO (writers ezdxf)
│   ├── geometry_vpro_safe.py    # export ordenado + validacao por grafo de arestas
│   ├── export_autohotkey.py     # JSON ordenado -> AutoHotkey v2 (F8/Esc/log)
│   ├── recover_previous_temp.py # recupera artefatos esquecidos em /tmp
│   └── libredwg_tools.py    # localizacao/diagnostico dos binarios LibreDWG
├── src/section_pipeline/    # pacote Python reutilizavel
│   └── (geometry, io, libredwg, validation, walk = grafo/continuidade)
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

## Export VPRO-safe ordenado (caminhada continua)

A LWPOLYLINE das secoes alveolares e UMA caminhada continua pela borda:
os alveolos sao percorridos por dentro atraves de um canal estreito
("furinho") que os liga a borda externa. Esse canal e intencional e
NUNCA deve ser fechado - o VPRO so aceita a secao como uma unica
poligonal caminhavel, sem circulos/loops internos independentes.

```bash
# DXF R12 (1 POLYLINE fechada) + JSON ordenado + previews, com validacao
# por grafo de arestas (continuidade, self-intersection, canal preservado):
.venv/bin/python scripts/geometry_vpro_safe.py --force

# AutoHotkey v2 para digitar a sequencia no VPro (F8 inicia, Esc aborta):
.venv/bin/python scripts/export_autohotkey.py --force
bash scripts/run_vpro_ahk_from_wsl.sh outputs/autohotkey/LA25_draw_polyline.ahk
```

Relatorio: `section/reports/LA25_vpro_safe_ordered_report.md`.
Decisoes e pendencias: `docs/notes/DECISOES.md` e `docs/notes/RELATORIO_FINAL.md`.
