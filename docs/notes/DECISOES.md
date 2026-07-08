# Decisões desta rodada de organização (2026-07-08)

Registro das decisões tomadas de forma autônoma, com justificativa, para
auditoria posterior. Tudo que foi removido continua recuperável no
histórico do Git (hashes indicados).

## 1. Estrutura de pastas: mantida a convenção existente + `outputs/`

A estrutura `section/{DWG,DXF,json,reports,preview}` + `scripts/` +
`src/section_pipeline/` já era boa, documentada no README e referenciada
pelos scripts. **Não** migrei para o layout genérico `data/raw|processed`:
quebraria paths sem ganho. Adicionei apenas:

- `outputs/` — entregáveis pedidos explicitamente nesta rodada
  (`outputs/dxf/`, `outputs/previews/`, `outputs/autohotkey/`,
  `outputs/LA25_outer_ordered.json`);
- `docs/notes/` — este arquivo e o relatório final.

O DXF final e o preview têm **cópia canônica** em `section/DXF/` e
`section/preview/` (regra do `.claude/CLAUDE.md`: tudo que é útil vive
versionado dentro de `section/`). `outputs/` e `section/` são gerados
pelo mesmo script no mesmo passo — se divergirem, regenerar com
`--force`.

## 2. Artefatos removidos do Git (commit e6105e1)

- `LA25_vpro.dwg` (raiz): subproduto acidental de `dxf2dwg` rodado com
  cwd errado na sessão anterior; regenerável.
- `output/` (raiz): saídas da sessão anterior, substituídas pelas novas
  em `outputs/` (com validação por grafo e canto inicial correto).
- `section/DXF/LA25_vpro_safe.{dxf,dwg}`: gerados por **ordenação polar**
  (ângulo em torno do centróide). Essa ordenação cria cordas
  atravessando o interior — exatamente o que o VPro rejeita. Arquivos
  perigosos de importar; removidos para ninguém usar por engano.
- `section/reports/LA25_vpro_safe_coords.csv`: sobrescrito na sessão
  anterior por um parser que contava códigos `10` do HEADER como
  vértices (1059 "pontos" em vez de 1030) e em ordem polar.
- `section/reports/LA25_vpro_safe_{report.md,summary.txt,plot.txt}` e
  `VPRO_SAFE_README.md`: descreviam o artefato polar com métricas
  absurdas (perímetro ~1e21 m, bounds 1e20) e alegações incorretas
  ("furos removidos", "sem auto-interseções" sem checagem válida).

Mantido: `section/reports/LA25_vpro_safe_order.png` (gerado pelo
pipeline legítimo `process_vpro_dxf.py` às 17:39, antes da sessão
problemática; conteúdo correto).

## 3. Scripts removidos (commit aa243a4)

`vpro_safe_polar_sort.py`, `vpro_safe_final.py`, `vpro_safe_order.py`,
`vpro_safe_reorder_dxf.py`, `extract_edges_and_walk.py`,
`generate_report.py`, `preserve_order_walk.py` — duplicavam o pacote
`section_pipeline` com bugs (ordenação polar; recursão estourando;
parser de DXF por regex frágil) e escreviam DXF por concatenação de
string, violando a regra permanente do repositório. O substituto é
`scripts/geometry_vpro_safe.py`, que reusa os writers ezdxf e o
round-trip LibreDWG de `process_vpro_dxf.py`.

## 4. Bug corrigido: escolha do "canto superior esquerdo"

`geometry.rotate_to_start` usava igualdade exata de float no empate de
Y. A face superior da LA25 tem ruído real de ~2e-4 m entre as
extremidades, então o ponto de Y estritamente máximo era o canto
superior **direito** — e o relatório antigo o rotulava "superior
esquerdo". Corrigido com banda de tolerância (`y_tol`, usada como
0,1% da altura da seção). Retrocompatível: `y_tol=0.0` mantém o
comportamento antigo. `section/DXF/LA25_vpro.dxf` (artefato antigo,
início no canto direito) foi mantido como está — o novo entregável é
`LA25_vpro_safe_ordered.dxf`.

## 5. Sentido horário (CW) mantido

O usuário aceita horário OU anti-horário, desde que consistente. A
convenção existente do repositório (`geometry.ensure_clockwise`) é
horário; mantida. Começando no canto superior esquerdo, o primeiro
traço é a face superior da esquerda para a direita — igual ao AHK
manual que funcionou.

## 6. Falhas conhecidas do `validate_sections.py` não perseguidas

O resumo estrito `section/reports/validation_summary.md` marca FALHOU
para: (a) todo DXF R12 (o `dwgread -O JSON` do LibreDWG 0.14.8390
imprime `ERROR: iconv` benigno para DWG de origem R12 — documentado em
`process_vpro_dxf.roundtrip_validate_r12`); (b) `LA25_vpro.dxf`
(`Duplicate handle` benigno do dicionário MATERIAL padrão do ezdxf);
(c) `LA25.dxf` bruto (segmentos de comprimento zero — é o DXF cru de
entrada, esperado). São limitações pré-existentes e documentadas no
código; o fluxo R12 usa o validador dedicado tolerante. Nenhuma
regressão foi introduzida.

## 7. Ambiente Python / pyproject

- `pyproject.toml` existente mantido intacto (setuptools, deps
  `ezdxf`/`matplotlib`/`shapely` — corretas e já instaladas na `.venv`).
- `.venv` já existia (Python 3.14.4) e o README manda **não** recriar.
- `pip install -e . --no-build-isolation` falha offline porque a venv
  não tem `setuptools` (backend indisponível). Os imports continuam
  funcionando pelo finder editable já instalado no site-packages; os
  scripts novos ainda têm fallback `sys.path` para `src/`. Para
  reinstalar de verdade: com rede, `.venv/bin/python -m pip install -e .`.
- Itens do briefing que citavam ACP/Overleaf/pandas/`build_acp_report.py`
  **não se aplicam a este repositório** (não existe nada de ACP aqui;
  este repo é o secpro de seções transversais). Registrado em vez de
  criar estrutura vazia.

## 8. AutoHotkey neste repositório

O `.claude/CLAUDE.md` diz para não adicionar "integração direta com
MIDAS/VPRO", mas já havia precedente commitado (`section/ahk/`,
`scripts/*ahk*`, commits ab24764..9273165) e o pedido desta rodada é
explícito. Mantido isolado em `scripts/export_autohotkey.py` +
`outputs/autohotkey/`, sem tocar em nada de MIDAS. O `.ahk` gerado NÃO
foi testado contra o VPro real (sessão em WSL, sem GUI) — ver
"pendências" no relatório final.

## 9. Precisão do grid no AHK

Com 3 casas decimais (convenção do VPro no precedente `LA25.ahk`), um
único par de vértices consecutivos (distantes ~6 µm) colide após o
arredondamento; o gerador remove a linha duplicada (1030 → 1029 linhas
+ fechamento) para não digitar segmento de comprimento zero no VPro.
`--decimals 4` preserva todos, se o VPro aceitar.

## 10. `*.BAK` rastreado

`section/DXF/LA25_vpro_slots_r12_20gon_5mm_bare.BAK` continua rastreado
(dado histórico pré-existente; regra: não apagar dados sem certeza).
`*.bak` minúsculo entrou no `.gitignore` apenas para novos temporários
de editor.
