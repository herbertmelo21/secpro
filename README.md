# secpro — laboratorio pessoal de caracterizacao do VPRO/SecPro

Repositorio pessoal e experimental de **characterization testing /
black-box reverse engineering** do VPRO/SecPro. Nao e um produto de
equipe nem uma biblioteca publica: e o caderno de laboratorio + pipeline
que transforma uma secao alveolar em DWG numa entrada operacional
confiavel para o VPRO — hoje, principalmente via **AutoHotkey**.

Este repositorio **nao** edita arquivos do projeto MIDAS Civil.

## Objetivo real (fluxo operacional)

```
section/DWG/LA25.dwg                        (fonte de verdade da geometria)
  -> dwgread -O JSON  -> section/json/LA25.json
  -> extracao + ordenacao VPRO-safe + simplificacao (<= 160 pontos)
  -> section/json/LA25_outer_ordered_160.json   (fonte direta do AHK)
  -> section/ahk/LA25.ahk                       (150 pontos, 2 fases)
  -> execucao no Windows (F8) + VALIDACAO VISUAL/MANUAL no VPRO
```

- **Limite pratico atual do VPRO: <= 160 pontos** (com 190 linhas a tabela
  parou de aceitar valores por volta do ponto 180 — ver
  `docs/notes/BLACKBOX_FINDINGS.md` §2.4).
- **Artefato operacional atual: `section/ahk/LA25.ahk` com 150 pontos**
  (circle_points=24; erro de area 0,0102%, Ix 0,0082%, Iy 0,0089% em
  relacao a geometria densa). Status: **aguardando validacao manual no VPRO**.
- Taxa de erro aceita no preenchimento: **0%**. Se o AHK falhar no meio,
  o procedimento e apagar no VPRO e refazer — nao remendar a mao.

## As duas rotas

1. **Rota AHK (operacional)** — preenche o grid "Secao poligonal" do VPRO
   ponto a ponto, na ordem validada. E a rota em uso e a unica com
   comportamento confirmado no VPRO real.
2. **Rota DXF (experimental)** — gera DXF R12 com 1 POLYLINE fechada via
   ezdxf + round-trip LibreDWG. A importacao de DXF **nunca foi confirmada
   no VPRO** nesta investigacao; a rota existe como hipotese de trabalho e
   laboratorio de geometria (ver BLACKBOX_FINDINGS §1.4).

## Como rodar o fluxo operacional

Rodar sempre da raiz do repo (os scripts usam caminhos relativos e a
`.venv/` local — nao criar outra venv):

```bash
# 1. Regenerar geometria limitada + AHK (so se a geometria mudar):
.venv/bin/python scripts/geometry_vpro_safe.py --max-vpro-points 160 --force
#    -> section/ahk/LA25.ahk (150 pts) + relatorio + PNG + CSV

# 2. Carregar o AHK no Windows (VPro aberto na tela "Seção poligonal";
#    criar a linha 1 no "+" e clicar na celula x(m) antes do F8):
bash scripts/run_vpro_ahk_from_wsl.sh section/ahk/LA25.ahk

# 3. F8 inicia (FASE 1: cria 149 linhas; FASE 2: preenche com setas).
#    Esc ou Ctrl+Alt+Q aborta. Log ao lado do .ahk.
```

O AHK e **deterministico**: regenerar a partir do mesmo JSON produz
arquivo byte-identico (comprovado na auditoria de 2026-07-09).

## Fonte de verdade

| O que | Fonte | Observacao |
|---|---|---|
| Geometria da secao | `section/DWG/*.dwg` | Entrada canonica; em discrepancia, o DWG prevalece |
| JSON intermediario | `section/json/LA25.json` | `dwgread -O JSON` do DWG; regeneravel |
| Sequencia de pontos do AHK | `section/json/LA25_outer_ordered_160.json` | Fonte DIRETA de `section/ahk/LA25.ahk`; versionada |
| Comportamento do VPRO | `docs/notes/BLACKBOX_FINDINGS.md` | Achados com status (CONFIRMADO/HIPOTESE/PENDENTE) |
| Requisitos do projeto | `docs/notes/QUESTIONS_FOR_HERBERT.md` | Questionario respondido em 2026-07-09 |
| Veredito final | Validacao visual/manual no VPRO | Nenhuma checagem local substitui |

## Criterios de aceitacao

Geometria simplificada (contra a polilinha densa de 1030 pontos):

- erro de area <= 0,5% e erro de Ix/Iy <= 1,0% (aceite do usuario;
  o pipeline aplica portoes mais rigidos por padrao: 0,1% / 0,2%);
- <= 160 pontos no total;
- uma unica polilinha fechada caminhavel — alveolos percorridos pelo canal
  de 1 mm, NUNCA como loops/circulos independentes;
- inicio no canto superior esquerdo, sentido horario, sem cordas
  (validado por grafo de arestas), sem self-intersection;
- inspecao visual do PNG numerado antes de usar.

Automacao (AHK):

- 0% de celulas erradas, conferido visualmente no VPRO;
- se falhar no meio: apagar no VPRO e refazer (fluxo principal);
- so marcar como validado (tag `vpro-ok-*`) apos conferencia manual.

## Arquivos versionados vs gerados

Classificacao completa: `docs/notes/FILE_CLASSIFICATION.md`.

**Versionado (permanece no Git):** `section/DWG/` (fonte), scripts Python
e `src/section_pipeline/`, `section/json/` (JSON fonte), AHK final
(`section/ahk/`), DXF finais e experimentos (`section/DXF/` — historico
da investigacao), relatorios `.md` e previews documentais, `docs/notes/`.

**Gerado/ignorado (novos arquivos):** `outputs/` (scratch de build),
`*.log` (flight recorder local — achados vao para BLACKBOX_FINDINGS),
`*_roundtrip.*` novos, `audit_pack/`, `.venv/`. Arquivos gerados que JA
estao rastreados continuam no Git ate uma rodada futura de limpeza
(decisao registrada em FILE_CLASSIFICATION).

## Black-box findings do VPRO (resumo)

Detalhes e evidencias: `docs/notes/BLACKBOX_FINDINGS.md`.

- Uma unica poligonal caminhavel; alveolos ligados por canal de 1 mm;
  nunca CIRCLE/ARC/loop fechado independente; nunca ordenar por angulo.
- Grid: **Tab embaralha x/y** — navegar com setas (Right/Down/Left).
- Criar todas as linhas ANTES de preencher (2 fases; ~700 ms por linha).
- **Teto pratico ~180 pontos** observado; operar com <= 160 (atual: 150).
- Virgula decimal, 3 casas; janela "Seção poligonal"; linha 1 criada
  manualmente + clique na celula x(m) antes do F8.
- 190 pontos e geometricamente otimo, mas NAO e a variante operacional.

## Rota DXF (laboratorio)

Ambiente: `.venv/` local (Python 3.14; ezdxf/matplotlib/shapely — leitura
e validacao auxiliar; a escrita final passa por LibreDWG). Binarios
LibreDWG (`dwgread`, `dxf2dwg`, `dwg2dxf`...) no `PATH` ou em
`~/projects/libredwg/programs/`. Nenhum DXF final e escrito por
concatenacao de string.

```bash
source .venv/bin/activate
python scripts/recover_previous_temp.py      # dry-run; nunca apaga
python scripts/convert_sections.py           # DWG -> DXF + JSON + relatorio
python scripts/validate_sections.py          # round-trip LibreDWG + geometria
# variantes de estudo (nao operacionais):
python scripts/geometry_vpro_safe.py --force              # densa (1030 pts)
python scripts/geometry_vpro_safe.py --simplify --force   # 190 pts por propriedades
```

Nota conhecida: o resumo estrito `section/reports/validation_summary.md`
marca FALHOU em todo DXF de origem R12 por limitacao benigna do LibreDWG
(`ERROR: iconv`) — nao e regressao (DECISOES §6).

## Estrutura

```
.
├── section/
│   ├── DWG/        # FONTE: DWG originais
│   ├── json/       # JSON LibreDWG + JSON fonte do AHK (LA25_outer_ordered_160.json)
│   ├── ahk/        # LA25.ahk = artefato operacional (150 pts)
│   ├── DXF/        # DXF finais + experimentos da rota DXF
│   ├── reports/    # relatorios .md, PNG/CSV documentais
│   └── preview/    # previews de conferencia
├── scripts/        # CLIs (geometry_vpro_safe, export_autohotkey, runner WSL...)
├── src/section_pipeline/  # pacote (geometry, io, libredwg, validation, walk, simplify)
├── docs/notes/     # BLACKBOX_FINDINGS, FILE_CLASSIFICATION, DECISOES,
│                   # RELATORIO_FINAL, QUESTIONS_FOR_HERBERT (requisitos)
├── outputs/        # scratch gerado (ignorado para novos arquivos)
└── .venv/          # ambiente local (nao versionado; nao recriar)
```

## Documentos

- `docs/notes/BLACKBOX_FINDINGS.md` — caderno de achados do VPRO (com status)
- `docs/notes/QUESTIONS_FOR_HERBERT.md` — requisitos respondidos (2026-07-09)
- `docs/notes/FILE_CLASSIFICATION.md` — classificacao de arquivos + politica Git
- `docs/notes/DECISOES.md` — decisoes de cada rodada, com justificativa
- `docs/notes/RELATORIO_FINAL.md` — relatorios das rodadas de trabalho
- `section/reports/LA25_vpro_limited_160.md` — relatorio do artefato atual
